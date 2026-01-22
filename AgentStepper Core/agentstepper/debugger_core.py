import asyncio
import threading
from typing import Optional, List, Any, Dict, Callable
from asyncio.base_events import Server as AsyncioServer
from websockets.asyncio.server import serve, ServerConnection
from websockets import Data
from websockets import ConnectionClosedError
from agentstepper.api.common import Event, EventTypes, Breakpoint, Commit
from agentstepper.api.agent_core_message import AgentCoreMessageFactory
from agentstepper.core.ui_events import UIEventTypes
from agentstepper.core import ui_serializer
from agentstepper.core.ui_message_factory import UIMessageFactory
from agentstepper.core.types import ExecutionStates, Run, AgentStates
from agentstepper.core.prompt_helper import PromptHelper
from openai import OpenAI, OpenAIError
import json
import uuid
from agentstepper.core.server_version import DEBUGGER_SERVER_VERSION
from logging import Logger, getLogger
import base64, zlib

class AgentStepperCore:
    """
    Core component of the AgentStepper interactive LLM agent debugger. Responsible for managing breakpoints, events, and other aspects of the debugging process.
    Communicates via `WebSocket` with the API and UI.

    :author: XXX
    :date: June 19, 2025
    """
    
    _log_path = 'logs'
    _host: str
    _client_port: int
    _ui_port: int
    _loop: Optional[asyncio.AbstractEventLoop]
    _thread: Optional[threading.Thread]
    _client_server: Optional[AsyncioServer]
    _client: Optional[ServerConnection]
    _ui_server: Optional[AsyncioServer]
    _ui: Optional[ServerConnection]
    _ui_event_handlers: Dict[str, Callable[[Any], None]]
    _llm: Optional[OpenAI]
    _model: str
    
    execution_state: ExecutionStates
    agent_state: AgentStates
    run_history: List[Run]
    active_run: Optional[Run]
    pending_breakpoint: Optional[Breakpoint]

    def __init__(
        self,
        host: str,
        client_port: int,
        ui_port: int,
        model: str,
        logger: Optional[Logger] = None
    ) -> None:
        """
        Creates a new AgentStepper Core object.
        
        :param str host: Hostname of the AgentStepper Core.
        :param int client_port: Port for the AgentStepper API to connect to.
        :param int ui_port: Port for the UI component to connect to.
        :param str model: OpenAI LLM model used for prompt summarization.
        :param Optional[Logger] logger: Logger to use to print informational and debug messages.
        """
        self._host = host
        self._client_port = client_port
        self._ui_port = ui_port
        self._model = model
        self.logger = logger or getLogger(__name__)
        PromptHelper.logger = self.logger
        self._loop = None
        self._thread = None
        self._client_server = None
        self._client = None
        self._ui_server = None
        self._ui = None
        self._ui_event_handlers = {
            UIEventTypes.STEP.value: self._on_ui_step,
            UIEventTypes.CONTINUE.value: self._on_ui_continue,
            UIEventTypes.HALT.value: self._on_ui_halt,
            UIEventTypes.RENAME_RUN.value: self._on_ui_rename_run,
            UIEventTypes.DOWNLOAD_REQUEST.value: self._on_ui_download_request,
            UIEventTypes.IMPORT_RUN.value: self._on_ui_import_run,
            UIEventTypes.UPDATE_MSG_CONTENT.value: self._on_ui_update_message,
            UIEventTypes.DELETE_RUN.value: self._on_ui_delete_run,
        }
        try:
            self._llm = OpenAI()
            self.logger.info('Initialized OpenAI API.')
        except OpenAIError:
            self._llm = None
            self.logger.warning('Failed to initialize OpenAI API. Missing API key.')
        
        self.execution_state = ExecutionStates.IDLE
        self.agent_state = AgentStates.AGENT_FINISHED
        self.run_history = list()
        self.active_run = None
        self.pending_breakpoint = None


    def start(self) -> None:
        """
        Starts the Debugger Server. Opens a `WebSocket` for the agent and the UI component.
        """
        splash_art = """
        ╔════════════════════════════════════════════╗
        ║                                            ║
        ║            AgentStepper Core               ║
        ║       xxxxxxxxxxxxxxxxxxxxxxxxxxx          ║
        ║             xxxxxxxxx, 2025                ║
        ║                                            ║
        ╚════════════════════════════════════════════╝"""
        self.logger.info(splash_art)
        self.logger.info(f'Debugger version: {DEBUGGER_SERVER_VERSION}')
        self._loop = asyncio.new_event_loop()

        def _run_loop() -> None:
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._start_servers())
            self._loop.run_forever()
            self._loop.close()

        self._thread = threading.Thread(target=_run_loop)
        self._thread.start()
        
        
    async def continue_execution(self):
        """
        Sets the debugger's operational mode to `continue`. All breakpoints will be skipped and left unmodified.
        """
        if self.active_run and (self.execution_state not in [ExecutionStates.IDLE, ExecutionStates.CONTINUE]):
            if self.pending_breakpoint:
                event = self.active_run.get_event_by_id(self.pending_breakpoint.event_id)
                self.agent_state = self._get_agent_state(event.get_end_breakpoint() != self.pending_breakpoint, event.type)
                await self._client.send(AgentCoreMessageFactory.newBreakpointMessage(self.pending_breakpoint)) # TODO: implement proper error handling
                self.pending_breakpoint = None
                
            self.execution_state = ExecutionStates.CONTINUE
            if self._ui:
                await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state))
    
    
    async def halt_execution(self):
        """
        Sets the debugger's operational mode to `step`. The debugger will halt the program at the next breakpoint.
        """
        if self.execution_state == ExecutionStates.CONTINUE:
            self.execution_state = ExecutionStates.STEP
            if self._ui:
                if self.pending_breakpoint:
                    self.agent_state = AgentStates.HALTED
                    await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state, self.pending_breakpoint.uuid))
                else:
                    self.agent_state = AgentStates.HALTING
                    await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state))
    
    
    async def step_over(self, data: Optional[Any]):
        """
        Steps over the latest breakpoint with optionally modified data.
        
        :param Optional[Any] data: Optionally modified data of the latest breakpoint.
        """
        if self.execution_state != ExecutionStates.HALTED:
            raise RuntimeError("Debugger in invalid state for stepping over breakpoint.")
        
        self.pending_breakpoint.modified_data = data
        breakpoint = self.pending_breakpoint
        event = self.active_run.get_event_by_id(breakpoint.event_id)
        self.pending_breakpoint = None
        self.execution_state = ExecutionStates.STEP
        self.agent_state = self._get_agent_state(event.get_end_breakpoint() != breakpoint, event.type)
        await self._client.send(AgentCoreMessageFactory.newBreakpointMessage(breakpoint))
        if self._ui:
            await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state))
        
        
    def stop(self) -> None:
        """
        Shuts down the AgentStepper Core. Closes all open sockets, and frees all allocated resources.
        """
        if not self._loop:
            return

        shutdown_future = asyncio.run_coroutine_threadsafe(
            self._stop_servers(), self._loop
        )
        shutdown_future.result()

        self._loop.call_soon_threadsafe(self._loop.stop)

        assert self._thread is not None
        self._thread.join()
        self.logger.info('DebuggerServer stopped.')


    async def _stop_servers(self) -> None:
        """
        Stops the `WebSocket` servers for the client and UI.
        """
        self.logger.info('Closing client server...')
        if self._client_server:
            self._client_server.close()
            await self._client_server.wait_closed()
        self.logger.info('Closing UI server...')
        if self._ui_server:
            self._ui_server.close()
            await self._ui_server.wait_closed()
            
    
    async def _start_servers(self) -> None:
        """
        Starts the `WebSocket` servers for the client and UI.
        """
        self._client_server = await serve(
            self._on_agent_connection_attempt, self._host, self._client_port
        )
        self._ui_server = await serve(
            self._on_ui_connection_attempt, self._host, self._ui_port, max_size=None
        )
        self.logger.info(f'Core listening for API connections on {self._host}:{self._client_port}')
        self.logger.info(f'Core listening for UI connection on   {self._host}:{self._ui_port}')


    async def _on_agent_connection_attempt(self, websocket: ServerConnection) -> None:
        """
        Event handler for when a new connection is established to the `WebSocket`
        designated for communication with the AgentStepper API component.
        
        :param ServerConnection websocket: Newly established connection to an API client.
        """
        if self._client:
            self.logger.warning('Already connected to an agent, second agent not allowed!')
            await websocket.close()
            return
        
        try:
            await self._on_agent_connected(websocket)
            async for message in websocket:
                await self._on_agent_message_received(message)
                
        except ConnectionClosedError:
            pass
        finally:
            await self._on_agent_disconnected()
            
    
    async def _on_agent_connected(self, websocket: ServerConnection):
        """
        Event handler for when the agent has connected to the core through the API.
        
        :param ServerConnection websocket: Newly established connection to the agent.
        """
        self.logger.info('Agent connected')
        self._client = websocket
        
        
    async def _on_agent_disconnected(self):
        """
        Event handler for when the agent has disconnected from the core.
        """
        self.logger.info('Agent disconnected')
        self._client = None
        if self.active_run:
            await self._end_active_run()
            
    
    async def _end_active_run(self):
        """
        Ends the active agent program execution run. Creates a program finished event,
        saves the run to the history, and prepares the debugger for the next run.
        """
        self.execution_state = ExecutionStates.IDLE
        self.agent_state = AgentStates.AGENT_FINISHED
        agent_end_event = Event(EventTypes.PROGRAM_FINISHED)
        breakpoint = Breakpoint('', None, agent_end_event.uuid)
        breakpoint.summary = 'Agent execution finished.'
        agent_end_event.breakpoints.append(breakpoint)
        self.active_run.add_event(agent_end_event)
        
        self.active_run.save_to_log(self._log_path)
        
        self.run_history.append(self.active_run)
        self.active_run = None
        
        if self._ui:
            await self._ui.send(UIMessageFactory.create_new_message_message(self.run_history[-1].uuid, ui_serializer.Message.from_breakpoint(breakpoint, agent_end_event)))
            await self._ui.send(UIMessageFactory.create_update_run_state_message(self.run_history[-1].uuid, self.execution_state, self.agent_state))

    
    async def _on_agent_message_received(self, message: Data):
        """
        Handles a incoming messages from the agent.
        
        :param Data message: Content of the message.
        """
        incoming = AgentCoreMessageFactory.parseMessage(message) #TODO: implement proper event handling
                
        if isinstance(incoming, Event):
            await self._handle_incoming_event(incoming)
        elif isinstance(incoming, Breakpoint):
            await self._handle_incoming_breakpoint(incoming)
        elif isinstance(incoming, Commit):
            await self._handle_incoming_commit(incoming)
        else:
            self.logger.error('Unsupported object type received from API!')
            raise TypeError('Unsupported object type received from API!')
            
            
    async def _handle_incoming_event(self, event: Event):
        """
        Event handler for when an event object is received from the API.
        This denotes the start of a new event triggered by the agent.
        
        :param Event event: Event object received from the debugger API.
        """
        self.logger.debug('Event received.')
        
        if event.type == EventTypes.PROGRAM_STARTED:
            await self._start_new_run(event)
            
        if event.type == EventTypes.DEBUG_MESSAGE and self._ui:
            await self._ui.send(UIMessageFactory.create_new_message_message(self.active_run.uuid, ui_serializer.Message.from_debug_event(event)))
            
        self.active_run.add_event(event)
            
    
    def _get_new_run_name(self, program_name: str) -> str:
        """
        Returns a default name for the newly created name. The name will have the format
        `Run #n of MyAgentProgram`, where n is the index of the run.
        
        :param str program_name: Name of the agent program running. Needed to calculate the index of the run.
        """
        n = 1 + sum(1 for run in self.run_history if run.program_name == program_name)
        return f'Run #{n} of {program_name}'

    
    async def _start_new_run(self, start_event: Event):
        """
        Administers the start of a agent program run.
        
        :param Event start_event: Event denoting the start of agent program execution.
        """
        program_name = str(start_event.data)
        self.active_run = Run(self._get_new_run_name(str(program_name)), program_name, start_event.time)
        self.execution_state = ExecutionStates.STEP
        self.agent_state = AgentStates.AGENT_RUNNING
        if self._ui: # TODO: Implement proper error handling
            await self._ui.send(UIMessageFactory.create_new_run_message(self.active_run, self.execution_state, self.agent_state))
            await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state))
    
    
    async def _handle_incoming_breakpoint(self, breakpoint: Breakpoint):
        """
        Event handler for when a breakpoint object is received from the agent.
        Depending on if the breakpoint is received directly after a new event, the breakpoint may be
        an event beginning or event ending breakpoint.
        
        :param Breakpoint breakpoint: Breakpoint object received from the agent.
        """
        if len(self.active_run.events) == 0:
            self.logger.error('Breakpoint received but no pending event!')
            raise RuntimeError('Breakpoint received but no pending event!')
        if breakpoint.event_id not in self.active_run.events:
            self.logger.error('Breakpoint not associated with any pending event!')
            raise RuntimeError('Breakpoint not associated with any pending event!')
        
        if self.execution_state == ExecutionStates.STEP:
            self.execution_state = ExecutionStates.HALTED
            self.agent_state = AgentStates.HALTED
            self.pending_breakpoint = breakpoint
            
        event = self.active_run.get_event_by_id(breakpoint.event_id)
        event.breakpoints.append(breakpoint)
        if not breakpoint.summary: breakpoint.summary = PromptHelper.summarize_breakpoint(self._llm, self._model, self.active_run, breakpoint)
        
        if self._ui:
            await self._ui.send(UIMessageFactory.create_new_message_message(self.active_run.uuid, ui_serializer.Message.from_breakpoint(breakpoint, event)))
            if self.execution_state == ExecutionStates.HALTED:
                await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, ExecutionStates.HALTED, AgentStates.HALTED, breakpoint.uuid))
        
        if self.execution_state == ExecutionStates.CONTINUE:
            self.agent_state = self._get_agent_state(event.get_end_breakpoint() != breakpoint, event.type)
            await self._client.send(AgentCoreMessageFactory.newBreakpointMessage(breakpoint)) # TODO: implement proper error handling
            
            if self._ui:
                await self._ui.send(UIMessageFactory.create_update_run_state_message(self.active_run.uuid, self.execution_state, self.agent_state))
                
    
    def _get_agent_state(self, is_in_breakpoint: bool, event_type: EventTypes) -> AgentStates:
        """
        Returns the agent's current state based on if it's in a breakpoint and the kind of event.
        
        :param bool is_in_breakpoint: Whether the agent is currently in a breakpoint or not.
        :param EventTypes event_types: The type of event the breakpoint is a part of.
        :return: The current state of the agent.
        :rtype: AgentStates
        """
        if is_in_breakpoint:
            if event_type == EventTypes.LLM_QUERY:
                return AgentStates.LLM_THINKING
            elif event_type == EventTypes.TOOL_INVOCATION:
                return AgentStates.TOOL_EXECUTING
        else:
            return AgentStates.AGENT_RUNNING
        

    async def _handle_incoming_commit(self, commit: Commit):
        """
        Event handler for when a commit object is received from the agent.
        
        :param Commit commit: Commit object received from the agent.
        """
        self.logger.info(f'Commit {commit.id[:6]}, {commit.title}')
        self.active_run.add_commit(commit)
        
        if self._ui:
            await self._ui.send(UIMessageFactory.create_new_commit_message(self.active_run.uuid, commit))
    
    
    async def _on_ui_connection_attempt(self, websocket: ServerConnection) -> None:
        """
        Event handler for when a new connection is established to the `WebSocket` 
        designated for communication with the UI component.
        
        :param ServerConnection websocket: Newly established connection to the UI.
        """
        if self._ui:
            self.logger.warning('Already connected to the UI, second connection not allowed!')
            await websocket.close()
            return
        
        try:
            await self._on_ui_connected(websocket)
            async for message in websocket:
                await self._on_ui_event_received(message)
        except ConnectionClosedError:
            pass
        finally:
            self._ui = None
            self.logger.info('UI disconnected')
            

    async def _on_ui_connected(self, websocket: ServerConnection):
        """
        Event handler for when the UI has connected to the server.
        
        :param ServerConnection websocket: Newly established connection to the UI.
        """
        self.logger.info('UI connected')
        self._ui = websocket
        runs = list(self.run_history)
        if self.active_run: runs.append(self.active_run)
        if self.pending_breakpoint:
            await self._ui.send(UIMessageFactory.create_init_app_state_message(runs, self.active_run, self.execution_state, self.agent_state, self.pending_breakpoint.uuid))
        else:
            await self._ui.send(UIMessageFactory.create_init_app_state_message(runs, self.active_run, self.execution_state, self.agent_state))
            
        
    async def _on_ui_event_received(self, message: Data):
        """
        Handles a incoming events from the UI.
        
        :param Data message: Content of the event message.
        """
        self.logger.debug(f'Received from UI: {message}')
        incoming: Dict = json.loads(message)
        
        try:
            await self._ui_event_handlers[incoming['event']](incoming.get('content'))
        except KeyError:
            self.logger.error('Invalid message received from UI.')
            raise TypeError('Invalid message received from UI.')
        
        
    async def _on_ui_step(self, data: Any):
        """
        Action handler for when the UI sends a `step` message.
        """
        if self.execution_state == ExecutionStates.HALTED:
            await self.step_over(self.pending_breakpoint.modified_data)
        elif self.execution_state == ExecutionStates.CONTINUE:
            self.execution_state = ExecutionStates.STEP
    
    
    async def _on_ui_continue(self, data: Any):
        """
        Handler for when the UI sends a `continue` message.
        """
        await self.continue_execution()
        
        
    async def _on_ui_halt(self, data: Any):
        """
        Handler for when the UI sends a `continue` message.
        """
        await self.halt_execution()

        
    async def _on_ui_rename_run(self, data: Dict):
        """
        Event handler for when the UI sends a `rename run` message.
        """
        run = self._get_run_with_uuid(data.get('run'))
        name: str = data.get('name')
            
        if run:
            self.logger.info(f'Renamed "{run.name}" to "{name}"!')
            run.name = name
        else:
            #TODO: Implement error handling
            self.logger.warning(f"No run found with UUID: {data.get('run')}")


    async def _on_ui_download_request(self, data: Dict):
        """
        Event handler for when the UI sends a `download request` message.
        """
        self.logger.debug(f"Download requested of run {data.get('run')}")
        
        run = self._get_run_with_uuid(data.get('run'))
        if run:
            if self._ui:
                await self._ui.send(UIMessageFactory.create_run_export_message(run.name, run.to_bytes()))
            
            
    async def _on_ui_import_run(self, data: Dict):
        """
        Handles the import run message from the UI by decoding and processing the run data.
        
        :param dict data: The message content containing the base64-encoded run data.
        """
        run = Run.from_bytes(zlib.decompress(base64.b64decode(data.get('data'))), is_base64_encoded=False) # TODO: Add error handling
        if run.server_version == DEBUGGER_SERVER_VERSION:
            self.run_history.append(run)
            if self._ui:
                await self._ui.send(UIMessageFactory.create_new_run_message(run, ExecutionStates.IDLE, AgentStates.AGENT_FINISHED))
        else:
            pass # TODO: implement error handling
            
            
    async def _on_ui_update_message(self, data: Dict):
        """
        Handles the UI update message event by updating the modified_content of the pending breakpoint.
        
        :param Dict data: The message content containing the message UUID and new content.
        :raises ValueError: If no pending breakpoint exists or if the UUIDs do not match.
        """
        if not self.pending_breakpoint:
            self.logger.error("No pending breakpoint to update.") # TODO: implement error handling
            raise ValueError("No pending breakpoint to update.")
        
        message_uuid = data.get('message')
        if str(self.pending_breakpoint.uuid) != message_uuid:
            self.logger.error(f"Breakpoint UUID mismatch: expected {self.pending_breakpoint.uuid}, received {message_uuid}")
            raise ValueError("Breakpoint UUID mismatch.")
        
        self.pending_breakpoint.modified_data = data.get('content')
        self.logger.debug(f"Updated content for breakpoint {self.pending_breakpoint.uuid}")
            
    
    async def _on_ui_delete_run(self, data: Dict):
        uuid = data.get('run')
        if self.active_run:
            if self.active_run.uuid == uuid:
                self.logger.error("Can't delete currently active run.")
                raise ValueError("Can't delete currently active run.") # TODO: Add error handling
            
        original_length = len(self.run_history)
        self.run_history[:] = [run for run in self.run_history if str(run.uuid) != uuid]
            
        if original_length > len(self.run_history):
            self.logger.info(f'Successfully deleted run with UUID: {uuid}.')
        else:
            self.logger.warning(f"No run found with UUID: {uuid}")
    
    def _get_run_with_uuid(self, run_uuid: str) -> Optional[Run]:
        """
        Retrieve a run object from either the active run or the run history based on the provided UUID.

        :param str run_uuid: The UUID string of the run to search for.
        :return: The matching Run object if found, otherwise `None`.
        :returntype: Optional[Run]
        """
        try:
            uuid_obj = uuid.UUID(run_uuid)
            return next(
                filter(lambda r: r.uuid == uuid_obj, [self.active_run] + self.run_history if self.active_run else self.run_history),
                None
            )
        except ValueError:
            return None