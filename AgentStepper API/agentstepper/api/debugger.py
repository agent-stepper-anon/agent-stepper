import threading
from typing import List, Dict, Union, Tuple
from websockets.sync.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosedError
from websockets.typing import Data, Optional
from agentstepper.api.common import Breakpoint, Event, EventTypes, Commit, Change, ChangeType
from agentstepper.api.agent_core_message import AgentCoreMessageFactory
from git import Repo, InvalidGitRepositoryError, Head, GitCommandError
from datetime import datetime
from packaging.version import Version
import openai
from agentstepper.api import git_utils
import os
import tempfile
import shutil
import weakref
import time
import string
from time import localtime

class AgentStepper:
    '''
    Helps debug LLM agent programs. This class represents the API interface to the AgentStepper interactive LLM agent debugger.
    It communicates with the AgentStepper Core.
    '''
    
    _program_name: str
    _core_uri: str
    _breakpoint_signal: threading.Event
    _pending_breakpoint: Optional[Breakpoint]
    _pending_events: List[Event]
    _core: Optional[ClientConnection]
    _daemon: Optional[threading.Thread]
    _repo: Optional[Repo]
    _default_branch: str
    _agent_workspace_path: Optional[str]
    _shadow_workspace: Optional[str]
    #_llm: openai.OpenAi
    
    def __init__(self, program_name: str, address: str, port: int, agent_workspace_path: Optional[str] = None):
        '''
        Creates a new AgentStepper object and connects to the AgentStepper Core.
        
        :param str program_name: Name of the program as a whole containing the agents to debug.
        :param str address: Address of the AgentStepper Core.
        :param int port: Port through which to connect to the AgentStepper Core.
        :param Optional[str] workspace: Path to workspace edited by the agent.
        :raises ConnectionError: If fails to establish connection to the AgentStepper Core.
        '''
        self._program_name = program_name
        self._pending_breakpoint = None
        self._breakpoint_signal = threading.Event()
        self._core_uri = f'ws://{address}:{port}'
        self._core = None
        self._pending_events = []
        self._repo = None
        self._default_branch = ''
        self._llm = None
        self._agent_workspace_path = agent_workspace_path
        self._shadow_workspace = None
        if Version(openai.__version__) >= Version('1.0.0'):
            try:
                self._llm = openai.OpenAI()
            except openai.OpenAIError:
                print('Failed to read OpenAI API key...')
        self._core_finalizer = None
        self._workspace_finalizer = None
        
        self._connect_to_core()
        
        if agent_workspace_path:
            self._initialize_shadow_workspace(agent_workspace_path)
            print(f'Initialized shadow workspace at {self._shadow_workspace}')
            
        self._hit_program_start_breakpoint()
        
    
    def __enter__(self):
        return self
    
        
    def __exit__(self, exc_type, exc_value, traceback):
        if self._core_finalizer: self._core_finalizer()
        if self._workspace_finalizer: self._workspace_finalizer()
        
    
    def begin_llm_query_breakpoint(self, prompt: Union[str, Dict]) -> Union[str, Dict]:
        '''
        Marks the beginning of an LLM query event, and provides the debugger the option to halt at this point.
        
        :param Union[str,Dict] prompt: Prompt, which will be sent to the LLM as part of the query.
        :return: Updated prompt, if the user modifies it in the debugger's UI. Equal to the prompt argument if left unchanged.
        :raises ConnectionError: If connection to the AgentStepper Core is lost.
        '''
        if not self._core:
            raise ConnectionError('Not connected to AgentStepper Core! Did we lose connection, or stopped the debugger?')
            
        event = Event(EventTypes.LLM_QUERY)
        breakpoint = Breakpoint(self._program_name, data=prompt, event_id=event.uuid)
        self._send_event(event)
        breakpoint = self._await_modified_breakpoint(breakpoint)
        event.begin_breakpoint = breakpoint
        self._pending_events.append(event)
        
        return breakpoint.modified_data if breakpoint.modified_data else prompt
        
    
    def end_llm_query_breakpoint(self, response: Union[str, Dict]) -> Union[str, Dict]:
        '''
        Marks the end of an LLM query event, and provides the debugger the option to halt at this point.
        
        :param Union[str, Dict] prompt: Response received from the LLM as part of the query.
        :return: Updated response, if the user modifies it in the debugger's UI. Equal to the response argument if left unchanged.
        :raises ConnectionError: If connection to the AgentStepper Core is lost.
        '''
        if not self._core:
            raise ConnectionError('Not connected to AgentStepper Core! Did we lose connection, or stopped the debugger?')
        if len(self._pending_events) == 0:
            raise RuntimeError("Can't end breakpoint, breakpoint hasn't begun!")

        event = self._pending_events.pop()
        breakpoint = self._await_modified_breakpoint(Breakpoint(self._program_name, data=response, event_id=event.uuid))
        event.end_breakpoint = breakpoint
        
        return breakpoint.modified_data if breakpoint.modified_data else response
        
        
    def begin_tool_invocation_breakpoint(self, tool: str, args: Dict) -> Tuple[str, Dict]:
        '''
        Encapsulates the beginning of a tool invocation event.
        
        :param str tool: Name of the tool to invoke.
        :param Dict args: Tool invocation arguments.
        :return: Updated tool name and arguments if the user modifies them in the debugger's UI. Unchanged otherwise.
        :raises ConnectionError: If connection to the AgentStepper Core is lost.
        '''
        if not self._core:
            raise ConnectionError('Not connected to AgentStepper Core! Did we lose connection, or stopped the debugger?')
    
        event = Event(EventTypes.TOOL_INVOCATION)
        breakpoint = Breakpoint(self._program_name, data={'Tool': tool, 'Argument': args}, event_id=event.uuid)
        self._send_event(event)
        breakpoint = self._await_modified_breakpoint(breakpoint)
        event.begin_breakpoint = breakpoint
        self._pending_events.append(event)
        
        if breakpoint.modified_data:
            if breakpoint.modified_data.get('Tool') and breakpoint.modified_data.get('Argument'):
                return (breakpoint.modified_data['Tool'], breakpoint.modified_data.get('Argument'))
        return (tool, args)
    
    
    def end_tool_invocation_breakpoint(self, results: Union[str, Dict]) -> Union[str, Dict]:
        '''
        Marks the end of a tool invocation event.
        
        :param Union[str,Dict] results: Result of the tool invocation.
        :return: Updated result if the user modifies it in the debugger's UI. Unchanged otherwise.
        :raises ConnectionError: If connection to the AgentStepper Core is lost.
        '''
        if not self._core:
            raise ConnectionError('Not connected to AgentStepper Core! Did we lose connection, or stopped the debugger?')
        if len(self._pending_events) == 0:
            raise RuntimeError("Can't end breakpoint, breakpoint hasn't begun!")
        
        event = self._pending_events.pop()
        breakpoint = self._await_modified_breakpoint(Breakpoint(self._program_name, data=results, event_id=event.uuid))
        event.end_breakpoint = breakpoint
        
        return breakpoint.modified_data if breakpoint.modified_data else results
            
    
    def commit_agent_changes(self, commit_summary: str = '', commit_description: str = '') -> bool:
        '''
        Commits the latest changes to the agent workspace to the git repository.
        
        Also sends the commit to the core.
        
        :param str commit_summary: Summary of changes made by tha agent. Summary will be generated if left empty.
        :param str commit_description: Description of changes made by the agent. Description will be generated if left empty.
        :return: True if there were changes to commit, otherwise False.
        :rtype: bool
        '''
        if self._shadow_workspace:
            self._update_shadow_workspace()
            commit = self._commit_changes(commit_summary, commit_description)
            if commit:
                self._send_commit(commit)
                return True
            
        return False
            
            
    def post_debug_message(self, message: str):
        '''
        Posts a debug message displayed on the debugger UI.
        
        :param str message: Message to display on the debugger UI.
        '''
        if not self._core:
            raise ConnectionError('Not connected to AgentStepper Core! Did we lose connection, or stopped the debugger?')
        
        event = Event(EventTypes.DEBUG_MESSAGE)
        event.data = message
        self._send_event(event)
        
        
    def _handle_message(self, message: Data):
        '''
        Event handler for when a new message is received from the AgentStepper Core.
        
        :param Data message: Data transmitted from the AgentStepper Core.
        '''
        if isinstance(message, str):
            breakpoint = AgentCoreMessageFactory.parseBreakpointMessage(message)
            self._pending_breakpoint.modified_data = breakpoint.modified_data
            self._breakpoint_signal.set()
        else:
            print(f"Message received: {message}")
        
        
    def _connect_to_core(self):
        '''
        Establishes a connection to the AgentStepper Core's `WebSocket`.
        
        :raises ConnectionError: If fails to connect to the AgentStepper Core.
        '''
        def daemon():
            try:
                for message in self._core:
                    self._handle_message(message)
            except ConnectionClosedError as e:
                print('Connection to AgentStepper Core lost!')
                self._core = None
                self._breakpoint_signal.set()
        
        try:
            self._core = connect(self._core_uri)
            self._daemon = threading.Thread(target=daemon)
            self._daemon.start()
            self._core_finalizer = weakref.finalize(self, self._finalize_core, self._core, self._daemon)
        except:
            raise ConnectionError('Failed to connect to AgentStepper Core!')
        
    def _initialize_shadow_workspace(self, workspace_path: str):
        '''
        Initializes the shadow workspace by copying the user workspace
        and initializing the git repository in the shadow workspace.
        
        :param str workspace_path: Path to the workspace in which the agent works.
        '''
        if not os.path.exists(workspace_path):
            os.mkdir(workspace_path)
        
        self._shadow_workspace = tempfile.mkdtemp(prefix='AgentDebuggerShadowWksp_')
        shutil.copytree(workspace_path, self._shadow_workspace, dirs_exist_ok=True) #TODO: implement error handling and clean up
        
        self._repo = self._initialize_repo(self._shadow_workspace)
        
        self._default_branch = self.get_current_branch()
        if self._repo.is_dirty() or self._repo.untracked_files:
            shutil.rmtree(self._shadow_workspace)
            raise RuntimeError('Repository contains uncommitted changes.')

        self._create_and_checkout_run_branch()
        self._workspace_finalizer = weakref.finalize(self, self._finalize_shadow_workspace, self._repo, self._default_branch, self._shadow_workspace, self._agent_workspace_path)
    
    
    def _initialize_repo(self, path: str) -> Repo:
        '''
        Initializes the repository at the specified path. Creates a new repository if none can be found.
        '''
        repo: Repo
        new_repo_needed = True
        if os.path.exists(path):
            try:
                repo = Repo(path)
                new_repo_needed = False
            except InvalidGitRepositoryError:
                pass
        
        if new_repo_needed:
            repo = Repo.init(path)
            # Commit empty file. Prevents https://stackoverflow.com/questions/36545150/cant-create-add-a-new-branch-to-a-git-repo-with-gitpython
            filename = 'README.md'
            open(os.path.join(path, filename), 'wb').close()
            repo.git.add(all=True)
            
            repo.config_writer().set_value("user", "name", self._program_name).release()
            repo.config_writer().set_value("user", "email", "your.email@example.com").release()
            repo.git.commit(message=f'Initial commit.')
        
        return repo
    
    
    def _send_initial_commit(self) -> None:
        '''
        Sends an initial commit message to the AgentStepper Core.
        
        The commit contains no changes, the current time and the latest commit's hash.
        '''
        self._send_commit(Commit(self._repo.head.commit.hexsha, time.localtime(), 'Initialized repository', []))
    
    
    @staticmethod
    def _finalize_core(core_websocket: Optional[ClientConnection], daemon_thread: Optional[threading.Thread]):
        if core_websocket:
            core_websocket.close()
            daemon_thread.join()
    
    @staticmethod
    def _finalize_shadow_workspace(repo: Optional[Repo], default_branch: Optional[str], shadow_workspace_path: Optional[str], agent_workspace_path: Optional[str]):
        '''
        Checks out the original branch in the shadow workspace
        and replaces the agent workspace with the copy in the shadow workspace.
        
        Finally, it cleans up all resources associated with the shadow workspace.
        '''
        if repo:
            try:
                repo.heads[default_branch].checkout() 
            except GitCommandError as e:
                pass # TODO: add error handling
            shutil.rmtree(agent_workspace_path, ignore_errors=True)
            shutil.move(shadow_workspace_path, agent_workspace_path)
    
    
    def get_current_branch(self) -> str:
        try:
            return self._repo.active_branch.name
        except TypeError:
            self._repo.create_head('default').checkout()
            return 'default'
    
    
    def _create_and_checkout_run_branch(self) -> None:
        branch_name = f'{self._program_name}/runs/{datetime.now().strftime("%m_%d_%Y-%I_%M_%S_%p").lower()}'.translate({ord(c): None for c in string.whitespace})
        branch = self._repo.create_head(branch_name)
        branch.checkout()
        
        
    def _update_shadow_workspace(self):
        '''
        Copies the current version of the user workspace to the shadow workspace excluding git repository information.
        
        Thus, effectively transfers the changes made by the agent to the user workspace to the shadow workspace.
        '''
        def ignore_git_dirs(directory, files):
            return ['.git'] if '.git' in files else []
        
        self._clear_shadow_workspace()
        if os.path.exists(self._agent_workspace_path):
            shutil.copytree(self._agent_workspace_path, self._shadow_workspace, ignore=ignore_git_dirs, dirs_exist_ok=True)
        
        
    def _clear_shadow_workspace(self):
        '''
        Delete all content from the shadow workspace excluding git repository information.
        '''
        for item in os.listdir(self._shadow_workspace):
            item_path = os.path.join(self._shadow_workspace, item)
            if item != '.git': 
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
        
    
    def _commit_changes(self, commit_summary: str = '', commit_description: str = '') -> Union[Commit, None]:
        """
        Commit changes in the repository and return a Commit object.

        :param str commit_summary: Summary of the commit
        :param str commit_description: Detailed description of the commit
        :return: Commit object if changes were committed, None otherwise
        :rtype: Commit | None
        """
        if not self._repo.is_dirty() and not self._repo.untracked_files:
            print('No changes to commit...')
            return None
        
        print('Committing changes to workspace...')
        self._repo.git.reset()
        changes = git_utils.get_changes(self._repo)
        
        commit_msg = self._create_commit_message(commit_summary, commit_description, git_utils.get_summary_of_changes(changes))
        self._repo.git.add(all=True)
        self._repo.git.commit(message=commit_msg)
        
        return self._build_commit_object(commit_msg, changes)
    

    def _create_commit_message(self, commit_summary: str, commit_description: str, diff_summary: dict) -> str:
        """
        Create commit message from summary or diff.

        :param str commit_summary: Summary of the commit
        :param str commit_description: Detailed description of the commit
        :param dict diff_summary: Dictionary containing diff summary
        :return: Commit message
        :rtype: str
        """
        if commit_summary:
            commit_msg = commit_summary
            if commit_description:
                commit_msg += '\n\n' + commit_description
            return commit_msg
        return git_utils.generate_commit_message(diff_summary, self._llm)
    

    def _build_commit_object(self, commit_msg: str, changes: List[Change]) -> Commit:
        """
        Build Commit object from commit and diff summary.

        :param str commit: Commit hash
        :param str commit_msg: Commit message
        :param List[Change] changes: List of change objects.
        :return: Commit object
        :rtype: Commit
        """
        commit_obj = self._repo.head.commit
        return Commit(id=commit_obj.hexsha, date=localtime(), title=commit_msg.split('\n')[0], changes=changes)
        
    
    def _hit_program_start_breakpoint(self):
        '''
        Halts at a breakpoint immediately after start, and creates a program started event.
        '''
        program_started_event = Event(EventTypes.PROGRAM_STARTED)
        program_started_event.data = self._program_name
        breakpoint = Breakpoint("", self._program_name, program_started_event.uuid)
        breakpoint.summary = 'Agent program started.'
        self._send_event(program_started_event)
        if self._repo:
            self._send_initial_commit()
        self._await_modified_breakpoint(breakpoint)
            
        
    def _send_event(self, event: Event):
        '''
        Sends an event object to the AgentStepper Core.
        
        :raises ConnectionClosed: If the transmission fails because there connection has closed.
        '''
        self._core.send(AgentCoreMessageFactory.newEventMessage(event))
    
    
    def _send_commit(self, commit: Commit):
        '''
        Sends a commit object to the AgentStepper Core.
        
        :raises ConnectionClosed: If the transmission fails because there connection has closed.
        '''
        self._core.send(AgentCoreMessageFactory.newCommitMessage(commit))
    
    
    def _await_modified_breakpoint(self, breakpoint: Breakpoint) -> Breakpoint:
        '''
        Waits for the AgentStepper Core to return the updated breakpoint based on the interaction with the user.
        Blocks until the response arrives.
        
        :param Breakpoint breakpoint: Newly occurred breakpoint to send to the AgentStepper Core.
        :return: Breakpoint object potentially modified by the AgentStepper Core depending on the user interaction.
        :rtype: Breakpoint
        :raises ConnectionError: If the connection unexpectedly closes while waiting for the response.
        '''
        self._pending_breakpoint = breakpoint

        self._core.send(AgentCoreMessageFactory.newBreakpointMessage(breakpoint))
        self._breakpoint_signal.wait()
        self._breakpoint_signal.clear()

        if self._core:
            modified_breakpoint = self._pending_breakpoint
            self._pending_breakpoint = None
            return modified_breakpoint
        else:
            self._pending_breakpoint = None
            raise ConnectionError('Connection lost to AgentStepper Core!')