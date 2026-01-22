from typing import Union
from agentstepper.api.common import Event, Breakpoint, Commit
import json

class AgentCoreMessageType:
    EVENT = 'event'
    BREAKPOINT = 'breakpoint'
    COMMIT = 'commit'
    
class AgentCoreMessageFactory:
    '''
    TODO: implement proper error handling
    '''
    
    def newEventMessage(event: Event) -> str:
        return json.dumps({
            'message': AgentCoreMessageType.EVENT,
            'data': event.as_dict()
        })
    
    
    def newBreakpointMessage(breakpoint: Breakpoint) -> str:
        return json.dumps({
            'message': AgentCoreMessageType.BREAKPOINT,
            'data': breakpoint.as_dict()
        })
        
        
    def newCommitMessage(commit: Commit) -> str:
        return json.dumps({
            'message': AgentCoreMessageType.COMMIT,
            'data': commit.as_dict()
        })
    
    
    def parseEventMessage(msg: str) -> Event:
        parsed_msg = json.loads(msg)
        if parsed_msg.get('message') in [AgentCoreMessageType.EVENT] and parsed_msg.get('data'):
            return Event.from_dict(parsed_msg['data'])
        else:
            raise ValueError('Failed to parse client server event message!')
    
    
    def parseBreakpointMessage(msg: str) -> Breakpoint:
        parsed_msg = json.loads(msg)
        if parsed_msg.get('message') in [AgentCoreMessageType.BREAKPOINT] and parsed_msg.get('data'):
            return Breakpoint.from_dict(parsed_msg['data'])
        else:
            raise ValueError('Failed to parse client server event message!')
    
    
    def parseCommitMessage(msg: str) -> Commit:
        parsed_msg = json.loads(msg)
        if parsed_msg.get('message') in [AgentCoreMessageType.COMMIT] and parsed_msg.get('data'):
            return Commit.from_dict(parsed_msg['data'])
        else:
            raise ValueError('Failed to parse client server event message!')
        
        
    def parseMessage(msg: str) -> Union[Event, Breakpoint]:
        parsed_msg = json.loads(msg)
        if parsed_msg.get('message') in [AgentCoreMessageType.EVENT] and parsed_msg.get('data'):
            return Event.from_dict(parsed_msg['data'])
        elif parsed_msg.get('message') in [AgentCoreMessageType.BREAKPOINT] and parsed_msg.get('data'):
            return Breakpoint.from_dict(parsed_msg['data'])
        elif parsed_msg.get('message') in [AgentCoreMessageType.COMMIT] and parsed_msg.get('data'):
            return Commit.from_dict(parsed_msg['data'])
        else:
            raise ValueError('Failed to parse client server event message!')