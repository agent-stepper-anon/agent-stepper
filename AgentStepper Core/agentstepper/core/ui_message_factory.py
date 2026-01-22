from abc import ABC
from typing import List, Union, Optional
from uuid import UUID
from agentstepper.core.types import Run, ExecutionStates, AgentStates
from agentstepper.api.common import Commit
from agentstepper.core.ui_serializer import Serializer, Message
import json
import base64
import zlib

class UIMessageFactory(ABC):
    @staticmethod
    def create_error_message(error: str) -> str:
        """
        Creates a JSON message to notify the UI of an error.
        
        :param str error: Error message.
        :return: JSON string of message with the error message.
        :rtype: str
        """
        message = {
            "event": "error",
            "content": {
                "message": error
            }
        }
        return json.dumps(message)
    
    @staticmethod
    def create_init_app_state_message(runs: List[Run], activeRun: Run, state: ExecutionStates, agent_state: AgentStates, halted_at: Optional[UUID] = None) -> str:
        """
        Creates a JSON message to initialize the app state with a list of runs.
        
        :param List[Run] runs: List of Run objects to include in the app state
        :param Run activeRun: The currently active Run object, or None
        :param ExecutionStates state: State to use for the active run
        :param AgentStates agent_state: The active run's current agent state
        :param Optional[UUID] halted_at: Optional UUID of the breakpoint the active run is currently halted at.
        :return: JSON string of message with event type and serialized runs
        :rtype: str
        """
        serialized_runs = [
            Serializer.serializeRun(run, state if activeRun == run else ExecutionStates.IDLE, agent_state if activeRun == run else AgentStates.AGENT_FINISHED)
            for run in runs
        ]
        message = {
            "event": "init_app_state",
            "content": {
                "runs": serialized_runs,
                "activeRun": str(activeRun.uuid) if activeRun else None,
                "haltedAt": str(halted_at) if halted_at else None,
            }
        }
        return json.dumps(message)

    @staticmethod
    def create_new_message_message(run_uuid: UUID, message: Message) -> str:
        """
        Creates a JSON message to notify the UI of a new message for a specific run.
        
        :param UUID run_uuid: UUID of the run to which the message belongs
        :param Message message: Message object to send
        :return: JSON string of message with event type and serialized content
        :rtype: str
        """
        message = {
            "event": "new_message",
            "content": {
                "run": str(run_uuid),
                "message": message.serialize()
            }
        }
        return json.dumps(message)

    @staticmethod
    def create_new_run_message(run: Run, state: ExecutionStates, agent_state: AgentStates) -> str:
        """
        Creates a JSON message to notify the UI of a new run.
        
        :param Run run: Run object to send
        :param ExecutionStates state: The run's execution state
        :param AgentStates agent_state: The agent state of the run
        :return: JSON string of message with event type and serialized run
        :rtype: str
        """
        message = {
            "event": "new_run",
            "content": {
                "run": Serializer.serializeRun(run, state, agent_state)
            }
        }
        return json.dumps(message)

    @staticmethod
    def create_update_run_state_message(run_uuid: UUID, state: ExecutionStates, agent_state: AgentStates,
                                      halted_at: Optional[UUID] = None) -> str:
        """
        Creates a JSON message to update the state of a specific run.
        
        :param UUID run_uuid: UUID of the run to update
        :param ExecutionStates state: New state of the run
        :param AgentStates agent_state: New state of the run's agent
        :param Optional[UUID] halted_at: UUID of the message where the run halted, if applicable
        :return: JSON string of message with event type and serialized content
        :rtype: str
        """
        message = {
            "event": "update_run_state",
            "content": {
                "run": str(run_uuid),
                "state": state,
                "agentState": agent_state,
                "haltedAt": str(halted_at) if halted_at else None,
            }
        }
        return json.dumps(message)
    
    @staticmethod
    def create_new_commit_message(run_uuid: UUID, commit: Commit) -> str:
        """
        Creates a JSON message for a new commit.
        
        :param UUID run_uuid: UUID of the run associated with the commit
        :param Commit commit: Commit object to include in the message
        :return: JSON string of message with event type and content
        :rtype: str
        """
        message = {
            "event": "new_commit",
            "content": {
                "run": str(run_uuid),
                "commit": Serializer.serializeCommit(commit)
            }
        }
        return json.dumps(message)
    
    @staticmethod
    def create_run_export_message(run_name: str, run_bytes: bytes) -> str:
        """
        Creates a JSON message containing the export of a run.
        
        :param UUID run_uuid: UUID of the run associated
        :param str run_name: Name of the run, used to generate the export file name
        :return: JSON string of message with event type and content
        :rtype: str
        """
        message = {
            "event": "run_export",
            "content": {
                "name": run_name,
                "data": base64.b64encode(zlib.compress(run_bytes)).decode('utf-8')
            }
        }
        return json.dumps(message)