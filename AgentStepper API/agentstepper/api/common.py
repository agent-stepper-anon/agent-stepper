from uuid import UUID, uuid4
from typing import Any, Optional, Dict, List
from enum import Enum
import json
from time import struct_time, localtime, mktime
import time

class Breakpoint:
    '''
    Represents a breakpoint in the execution of the agent program.
    '''
    
    uuid: UUID
    agent: str
    event_id: UUID
    time: struct_time
    summary: str
    original_data: Any
    modified_data: Optional[Any]
    
    def __init__(self, agent: str, data: Any, event_id: UUID):
        '''
        Creates a new breakpoint object.
        
        :param str agent: Name of the agent currently executing as the breakpoint occurred.
        :param Any data: Breakpoint specific data.
        :param UUID event_id: UUID of the event with which the breakpoint is associated.
        '''
        self.uuid = uuid4()
        self.agent = agent
        self.original_data = data
        self.modified_data = None
        self.event_id = event_id
        self.summary = None
        self.time = localtime()
        
        
    def get_data(self) -> Any:
        return self.modified_data if self.modified_data else self.original_data
        
        
    def from_dict(dict) -> "Breakpoint":
        '''
        Parses a dictionary and constructs a breakpoint object from it.
        
        :raises KeyError: If the dictionary is missing any required attribute.
        :return: Breakpoint object of the json representation.
        :rtype: Breakpoint
        '''
        breakpoint = Breakpoint(dict['agent'], dict['original_data'], UUID(dict['event_id']))
        breakpoint.time = localtime(dict.get('time'))
        breakpoint.uuid = UUID(dict['uuid'])
        breakpoint.modified_data = dict.get('modified_data')
        breakpoint.summary = dict.get('summary')
        return breakpoint
    

    def __eq__(self, value):
        if value:
            if isinstance(value, Breakpoint):
                if self.uuid == value.uuid:
                    return True
        return False
    
    
    def as_dict(self):
        '''
        Returns a dictionary representation of the breakpoint's attributes.
        Useful for converting to JSON object.
        '''
        return {
            "uuid": str(self.uuid),
            "agent": self.agent,
            "event_id": str(self.event_id),
            "time": mktime(self.time),
            "original_data": self.original_data,
            "modified_data": self.modified_data,
            "summary": self.summary
        }


class EventTypes(Enum):
    '''
    Enum of different event types that can occur.
    '''
    PROGRAM_STARTED = "program_started"
    '''
    Denotes the start of agent execution. An `PROGRAM_STARTED` event has a single breakpoint.
    '''
    PROGRAM_FINISHED = "program_finished"
    '''
    Denotes the completion of agent execution. An `AGENT_FINISHED` event does not have any breakpoints.
    '''
    LLM_QUERY = "llm_query"
    '''
    Denotes the invocation of an LLM in form of a query.
    '''
    TOOL_INVOCATION = "tool_invocation"
    '''
    Denotes the invocation of a tool.
    '''
    DEBUG_MESSAGE = "debug_message"
    '''
    Denotes a simple debug message. The message is stored in the event's data attribute.
    '''

class Event:
    '''
    Represents an event that occurs during execution of an agent program.
    '''
    
    uuid: UUID
    time: struct_time
    type: EventTypes
    data: Any
    breakpoints: List[Breakpoint]
    
    def __init__(self, type: EventTypes):
        '''
        Creates a new event object of the given type.
        
        :param EventTypes event: Type of the event to create.
        '''
        self.uuid = uuid4()
        self.type = type
        self.breakpoints = list()
        self.time = localtime()
        self.data = None
        
        
    def has_begin_breakpoint(self) -> bool:
        return len(self.breakpoints) > 0
    
    
    def has_end_breakpoint(self) -> bool:
        return len(self.breakpoints) > 1
    
    
    def get_begin_breakpoint(self) -> Breakpoint:
        if self.has_begin_breakpoint():
            return self.breakpoints[0]
        else:
            return None
    
    
    def get_end_breakpoint(self) -> Breakpoint:
        if self.has_end_breakpoint():
            return self.breakpoints[-1]
        else:
            return None
        
        
    def from_dict(dict: Dict) -> "Event":
        """
        Re-hydrate an Event instance that was produced by `as_dict()`.
        
        :param dict dict: The dictionary created by `Event.as_dict()` (or equivalent).
        :return: A fully-populated Event object.
        :rtype: Event
        """
        evt = Event(EventTypes[dict["type"]])
        evt.uuid = UUID(dict["uuid"])
        evt.data = dict.get("data")
        evt.time = localtime(dict["time"])
        evt.breakpoints = [Breakpoint.from_dict(b) for b in dict["breakpoints"]]

        return evt
    
        
    def as_dict(self):
        '''
        Returns a dictionary representation of the event object.
        Useful for converting to JSON object.
        '''
        return {
            "uuid": str(self.uuid),
            "type": str(self.type.name),
            "time": mktime(self.time),
            "data": self.data,
            "breakpoints": [b.as_dict() for b in self.breakpoints]
        }
        
        
    def json(self) -> str:
        '''
        Returns a JSON representation of the event.
        '''
        return json.dumps(self.as_dict())
    
    def __eq__(self, value):
        if value:
            if isinstance(value, Event):
                if self.uuid == value.uuid:
                    return True
        return False
    
    
    def __lt__(self, event) -> bool:
        return self.time < event.time
    

class ChangeType(Enum):
    """Enum representing types of changes in a git commit."""
    CHANGE = 'change'
    """Represents a modification to an existing file."""
    NEW_FILE = 'new file'
    """Represents the creation of a new file."""
    DELETED_FILE = 'deleted file'
    """Represents the deletion of a file."""

class Change:
    """Represents a single change to a file in a git commit."""
    def __init__(self, path: str, change_type: ChangeType, diff: str, content: str, previous_content: str):
        """
        Initialize a Change object.

        :param str path: The file path affected by the change
        :param ChangeType change_type: The type of change made
        :param str diff: The diff content of the change
        :param str content: The current content of the file
        :param str previous_content: The previous content of the file
        """
        self.path = path
        self.change_type = change_type
        self.diff = diff
        self.content = content
        self.previous_content = previous_content

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert Change object to dictionary for JSON serialization.

        :return: Dictionary representation of the Change
        :rtype: Dict[str, Any]
        """
        return {
            'path': self.path,
            'change_type': self.change_type.value,
            'diff': self.diff,
            'content': self.content,
            'previous_content': self.previous_content
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Change':
        """
        Create Change object from dictionary.

        :param Dict[str, Any] data: Dictionary containing change data
        :return: Change object
        :rtype: Change
        """
        return cls(
            path=data['path'],
            change_type=ChangeType(data['change_type']),
            diff=data['diff'],
            content=data['content'],
            previous_content=data['previous_content']
        )
    
class Commit:
    """Represents a git commit containing a set of changes."""
    def __init__(self, id: str, date: struct_time, title: str, changes: List[Change]):
        """
        Initialize a Commit object.

        :param str id: The unique hash string identifier of the commit
        :param struct_time date: The date and time of the commit
        :param str title: The commit message or title
        :param List[Change] changes: The list of changes in the commit
        """
        self.id = id
        self.date = date
        self.title = title
        self.changes = changes

    def __eq__(self, other: object) -> bool:
        """
        Compare two Commit objects for equality based on their hash.

        :param object other: Object to compare with
        :return: True if objects are equal based on id, False otherwise
        :rtype: bool
        """
        if not isinstance(other, Commit):
            return False
        return self.id == other.id

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert Commit object to dictionary for JSON serialization.

        :return: Dictionary representation of the Commit
        :rtype: Dict[str, Any]
        """
        return {
            'id': self.id,
            'date': mktime(self.date),
            'title': self.title,
            'changes': [change.as_dict() for change in self.changes]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Commit':
        """
        Create Commit object from dictionary.

        :param Dict[str, Any] data: Dictionary containing commit data
        :return: Commit object
        :rtype: Commit
        """
        return cls(
            id=data['id'],
            date=time.localtime(data['date']),
            title=data['title'],
            changes=[Change.from_dict(change) for change in data['changes']]
        )