from agentstepper.api.common import Event, EventTypes, Commit
from time import struct_time, localtime, mktime
from typing import List, Dict, Optional, Union, Any
from uuid import UUID, uuid4
from agentstepper.core.log_writer import log_run_to_file
from datetime import datetime
import os
import pickle
import base64
from agentstepper.core.server_version import DEBUGGER_SERVER_VERSION
from enum import Enum
import time
import json

class ExecutionStates:
    '''
    Enum of possible states of agent program execution.
    '''
    IDLE = "idle"
    '''
    Debugger client is not connected, server waiting for a run to start
    '''
    CONTINUE = "continue"
    '''
    Agent program executing in `continue` mode
    '''
    STEP = "step"
    '''
    Agent program is executing in `step` mode
    '''
    HALTED = "halted"
    '''
    Agent program is halted at a breakpoint
    '''

class AgentStates:
    AGENT_RUNNING = "Agent running..."
    LLM_THINKING = "LLM thinking..."
    TOOL_EXECUTING = "Tool executing..."
    HALTED = "Halted at breakpoint..."
    HALTING = "Halting at breakpoint..."
    AGENT_FINISHED = "Agent finished..."
    
class Run:
    '''
    Represents an execution run of an agent program.
    '''
    
    name: str
    program_name: str
    start_time: struct_time
    events: Dict[UUID, Event]
    commits: List[Commit]
    uuid: UUID
    
    def __init__(self, name: str, program_name: str, start_time: struct_time):
        self.uuid = uuid4()
        self.name = name
        self.program_name = program_name
        self.start_time = start_time
        self.events = dict()
        self.commits = list()
        self.server_version = DEBUGGER_SERVER_VERSION
        
    @staticmethod
    def from_bytes(data: Union[str, bytes], is_base64_encoded: bool = True) -> 'Run':
        """
        Parses a byte array or encoded string into a run object.
        
        :param Union[str, bytes] data: Bytes or encoded string representation of the run object.
        :param bool is_base64_encoded: Flag for if the run is a base64 string, or unencoded bytes.
        :return: Run object with new random UUID.
        :rtype: Run
        """
        try:
            decoded_bytes = base64.b64decode(data) if is_base64_encoded else data.decode('utf-8')
            run: Run = Run.from_dict(json.loads(decoded_bytes))
            run.uuid = uuid4()
            return run
        except Exception as e:
            raise
        
    
    def to_bytes(self) -> bytes:
        """
        Returns a byte representation of this run object.
        """
        return json.dumps(self.as_dict()).encode('utf-8')
        
        
    def add_event(self, event: Event):
        '''
        Adds the given event to the run event history.
        
        :param Event event: Event object to add to the run event history.
        '''
        self.events[event.uuid] = event
        
        
    def add_commit(self, commit: Commit):
        '''
        Adds the given commit to the run commit history.
        
        :param Commit commit: Commit object to add to the run commit history.
        '''
        self.commits.append(commit)
        
    
    def get_event_by_id(self, uuid: UUID) -> Event:
        '''
        Returns the event with the given id from the history.
        
        :param UUID uuid: ID of the event to fetch.
        :return: Event object with the given ID.
        :rtype: Event
        :raises KeyError: If there is no event with the given ID.
        '''
        return self.events[uuid]
    
    
    def get_previous_queries(self, before: Optional[Event] = None) -> List[Event]:
        '''
        Returns a time-sorted list of all LLM query events that happened before the given event.
        
        :param Optional[Event] before: Reference event.
        :return: Time-sorted list with oldest event at index 0 containing all event that happened
        before the given event. If none was specified, then all events of the run.
        :rtype: List[Event]
        '''
        if before:
            return sorted([evt for evt in self.events.values() if (evt.type == EventTypes.LLM_QUERY) and (evt.time < before.time)], key=lambda evt: evt.time)
        else:
            return sorted([evt for evt in self.events.values() if evt.type == EventTypes.LLM_QUERY], key=lambda evt: evt.time)
        
        
    def save_to_log(self, log_path: str):
        '''
        Saves the run to a logfile in the specified log folder.
        
        Creates the log directory if it does not exist and generates a log file named with the run name and current date/time in the format `<run_name>_<YYYY-MM-DD_HH-MM-SS>.log`. The log file contains formatted details of the run and its events, including timestamps, UUIDs, and breakpoint data.

        :param Run run: Run object containing execution details and events.
        :param str log_path: Directory path where the log file will be saved.
        '''
        try:
            os.makedirs(log_path, exist_ok=True)
            current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_name = f"{self.name}_{current_time}.log"
            log_run_to_file(self, os.path.join(log_path, file_name))
        except OSError as e:
            print(f"Error writing log to {log_path}: {e}") #TODO: implement proper error handling
    
    
    def as_dict(self):
        '''
        Returns a dictionary representation of this object containing all attributes.
        '''
        return {
            "uuid": str(self.uuid),
            "name": self.name,
            "program_name": self.program_name,
            "start_time": mktime(self.start_time),
            "events": [e.as_dict() for e in self.events.values()],
            "commits": [c.as_dict() for c in self.commits]
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Run':
        """
        Create Run object from dictionary.

        :param Dict[str, Any] data: Dictionary containing run data
        :return: Run object
        :rtype: Run
        """
        run = cls(
            name=data['name'],
            program_name=data['program_name'],
            start_time=time.localtime(data['start_time']),
        )
        run.uuid = UUID(data['uuid'])
        for e in data['events']: run.add_event(Event.from_dict(e)) 
        for c in data['commits']: run.add_commit(Commit.from_dict(c))
        return run
        
        
    def __lt__(self, run) -> bool:
        return self.start_time < run.start_time
        
    def __eq__(self, other) -> bool:
        '''
        Checks if this Run object is equal to another object based on UUID.

        :param other: Object to compare with this Run instance.
        :return: True if the other object is a Run instance with the same UUID, False otherwise.
        :rtype: bool
        '''
        if not isinstance(other, Run):
            return False
        return self.uuid == other.uuid