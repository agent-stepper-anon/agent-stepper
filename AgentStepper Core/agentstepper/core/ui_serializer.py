from agentstepper.core.types import Run, ExecutionStates, AgentStates
from uuid import UUID
from typing import Dict, Union, List
from enum import Enum
from agentstepper.api.common import Breakpoint, Event, EventTypes, Commit, Change
from time import struct_time, strftime
from abc import ABC

class Participant(Enum):
    LLM = 'LLM'
    CORE = 'Core'
    TOOLS = 'Tools'
    SYSTEM = 'System'
    
class ContentType(Enum):
    JSON = 'json'
    TEXT = 'text'

class Message:
    uuid: UUID
    _from: Participant
    _to: Participant
    summary: str
    contentType: ContentType
    content: Union[Dict, str]
    sent_at: struct_time
    
    def __init__(self, uuid: UUID, from_participant: Participant, to_participant: Participant, 
                 summary: str, content_type: ContentType, content: Union[Dict, str], sent_at: struct_time):
        """
        Initializes a Message object with provided attributes.
        
        :param UUID uuid: Unique identifier for the message
        :param Participant from_participant: Source participant of the message
        :param Participant to_participant: Destination participant of the message
        :param str summary: Summary of the message content
        :param ContentType content_type: Type of content (JSON or TEXT)
        :param Union[Dict, str] content: Actual content of the message
        :param struct_time sent_at: Timestamp when the message was sent
        """
        self.uuid = uuid
        self._from = from_participant
        self._to = to_participant
        self.summary = summary
        self.contentType = content_type
        self.content = content
        self.sent_at = sent_at
        
    def serialize(self) -> Dict:
        """
        Converts the Message object to a JSON-serializable dictionary.
        
        :return: Dictionary representation of the message
        :rtype: Dict
        """
        return {
            "uuid": str(self.uuid),
            "from": self._from.value,
            "to": self._to.value,
            "content": self.content,
            "contentType": self.contentType.value,
            "summary": self.summary or None,
            "sentAt": strftime("%Y-%m-%dT%H:%M:%S%z", self.sent_at)
        }
        
    @staticmethod
    def from_debug_event(event: Event) -> 'Message':
        """
        Creates a Message object from an Event that contains a debug message.
        
        :param Event event: Event with type debug message and data containing the message.
        :return: Message object based on the event.
        :rtype: Message
        """
        return Message(event.uuid, Participant.SYSTEM, Participant.SYSTEM, event.data, ContentType.TEXT, None, event.time)
    
    @staticmethod
    def from_breakpoint(breakpoint: 'Breakpoint', event: 'Event') -> 'Message':
        """
        Creates a Message object from a Breakpoint and its associated Event.
        
        :param Breakpoint breakpoint: Breakpoint to create message from
        :param Event event: Associated event for the breakpoint
        :return: Message object based on breakpoint and event data
        :rtype: Message
        """
        from_participant = Message._determine_from_participant(breakpoint, event)
        to_participant = Message._determine_to_participant(breakpoint, event)
        content_type = ContentType.JSON if isinstance(breakpoint.original_data, Dict) else ContentType.TEXT
        summary = breakpoint.summary or ""
        
        return Message(
            breakpoint.uuid,
            from_participant,
            to_participant,
            summary,
            content_type,
            breakpoint.original_data,
            breakpoint.time
        )

    @staticmethod
    def _determine_from_participant(breakpoint: 'Breakpoint', event: 'Event') -> Participant:
        """
        Determines the source participant based on breakpoint and event type.
        
        :param Breakpoint breakpoint: Breakpoint to analyze
        :param Event event: Associated event
        :return: Source participant identifier
        :rtype: Participant
        """
        is_end_breakpoint = event.has_end_breakpoint() and breakpoint == event.get_end_breakpoint()
        if is_end_breakpoint and event.type == EventTypes.LLM_QUERY:
            return Participant.LLM
        if is_end_breakpoint and event.type == EventTypes.TOOL_INVOCATION:
            return Participant.TOOLS
        if event.type in [EventTypes.PROGRAM_FINISHED, EventTypes.PROGRAM_STARTED]:
            return Participant.SYSTEM
        return Participant.CORE

    @staticmethod
    def _determine_to_participant(breakpoint: 'Breakpoint', event: 'Event') -> Participant:
        """
        Determines the destination participant based on breakpoint and event type.
        
        :param Breakpoint breakpoint: Breakpoint to analyze
        :param Event event: Associated event
        :return: Destination participant identifier
        :rtype: Participant
        """
        is_begin_breakpoint = event.has_begin_breakpoint() and breakpoint == event.get_begin_breakpoint()
        if is_begin_breakpoint:
            if event.type == EventTypes.LLM_QUERY:
                return Participant.LLM
            if event.type == EventTypes.TOOL_INVOCATION:
                return Participant.TOOLS
        if event.type in [EventTypes.PROGRAM_FINISHED, EventTypes.PROGRAM_STARTED]:
            return Participant.SYSTEM
        return Participant.CORE
    
class Messages(ABC):
    @staticmethod
    def fromEvent(event: 'Event') -> List['Message']:
        """
        Creates a list of Message objects from each breakpoint in the event.
        
        :param Event event: Event containing breakpoints
        :return: List of Message objects in breakpoint order
        :rtype: List[Message]
        """
        if event.breakpoints:
            return [Message.from_breakpoint(breakpoint, event) for breakpoint in event.breakpoints]
        elif event.type == EventTypes.DEBUG_MESSAGE:
            return [Message.from_debug_event(event)]
        else:
            return []

    @staticmethod
    def fromEvents(events: List['Event']) -> List['Message']:
        """
        Creates a list of Message objects from a list of events.
        
        :param List[Event] events: List of events to process
        :return: List of Message objects in event and breakpoint order
        :rtype: List[Message]
        """
        messages = []
        for event in events:
            messages.extend(Messages.fromEvent(event))
        return messages

    @staticmethod
    def serialize(messages: List['Message']) -> List[Dict]:
        """
        Serializes a list of Message objects into JSON-serializable dictionaries.
        
        :param List[Message] messages: List of Message objects to serialize
        :return: List of dictionary representations
        :rtype: List[Dict]
        """
        return [message.serialize() for message in messages]
    
class Serializer(ABC):
    @staticmethod
    def serializeRun(run: Run, state: ExecutionStates, agent_state: AgentStates) -> Dict:
        """
        Serializes a Run object into a JSON-serializable dictionary.
        
        :param Run run: Run object to serialize
        :param ExecutionStates state: The run's execution state
        :param AgentStates agent_state: The run's agent state
        :return: Dictionary representation of the Run
        :rtype: Dict
        """
        messages = Messages.fromEvents(list(run.events.values()))
        return {
            "uuid": str(run.uuid),
            "name": run.name,
            "programName": run.program_name,
            "startTime": strftime("%Y-%m-%dT%H:%M:%S%z", run.start_time),
            "state": state,
            "agentState": agent_state,
            "commits": [Serializer.serializeCommit(commit) for commit in run.commits],
            "messages": Messages.serialize(messages),
            "haltedAt": None  # Assuming no haltedAt UUID unless specified
        }

    @staticmethod
    def serializeChange(change: Change) -> Dict:
        """
        Serializes a Change object into a JSON-serializable dictionary.

        :param Change change: Change object to serialize
        :return: Dictionary representation of the Change
        :rtype: Dict
        """
        return {
            "path": change.path,
            "changeType": change.change_type.value,
            "content": change.content,
            "previousContent": change.previous_content
        }

    @staticmethod
    def serializeCommit(commit: Commit) -> Dict:
        """
        Serializes a Commit object into a JSON-serializable dictionary.
        
        :param Commit commit: Commit object to serialize
        :return: Dictionary representation of the Commit
        :rtype: Dict
        """
        return {
            "id": commit.id,
            "date": strftime("%Y-%m-%dT%H:%M:%S%z", commit.date),
            "title": commit.title,
            "changes": [Serializer.serializeChange(change) for change in commit.changes]
        }