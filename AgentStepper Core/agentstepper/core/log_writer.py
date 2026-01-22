from datetime import datetime
from time import mktime
from typing import List
from uuid import UUID
from agentstepper.api.common import Event, EventTypes, Breakpoint


def log_run_to_file(run, log_path: str) -> None:
    """
    Saves run details and events to a log file in a formatted, professional manner.
    Args:
        run: Run object containing execution details and events.
        log_path: File path where the log will be saved.
    """
    with open(log_path, 'w') as file:
        write_run_header(file, run)
        events = sort_events_by_time(run.events)
        write_events(file, events)
        

def write_run_header(file, run) -> None:
    start_time = datetime.fromtimestamp(mktime(run.start_time)).strftime('%Y-%m-%d %H:%M:%S')
    file.write(f"{'=' * 50}\n")
    file.write(f"---- RUN: {run.name} ----\n")
    file.write(f"{'=' * 50}\n")
    file.write(f"Agent Program: {run.program_name}\n")
    file.write(f"Started At: {start_time}\n")
    file.write(f"\n{'-' * 50}\n\n")
    

def sort_events_by_time(events: dict[UUID, Event]) -> List[Event]:
    return sorted(events.values(), key=lambda event: event.time)


def write_events(file, events: List[Event]) -> None:
    for index, event in enumerate(events, 1):
        write_event_header(file, event, index, len(events))
        write_breakpoints(file, event)
        file.write(f"\n{'-' * 50}\n\n")
        

def write_event_header(file, event: Event, index: int, total: int) -> None:
    event_time = datetime.fromtimestamp(mktime(event.time)).strftime('%Y-%m-%d %H:%M:%S')
    file.write(f"----- EVENT ({index}/{total}): {event.type.value} -----\n")
    file.write(f"UUID: {event.uuid}\n")
    file.write(f"At: {event_time}\n")
    

def write_breakpoints(file, event: Event) -> None:
    if event.has_begin_breakpoint():
        write_begin_breakpoint(file, event.type, event.get_begin_breakpoint())
    if event.has_end_breakpoint():
        write_end_breakpoint(file, event.type, event.get_end_breakpoint())
        

def write_begin_breakpoint(file, event_type: EventTypes, breakpoint: Breakpoint) -> None:
    if event_type == EventTypes.LLM_QUERY:
        file.write("Prompt:\n")
        data = breakpoint.summary or breakpoint.original_data
        file.write(f"    {data}\n")
    elif event_type == EventTypes.TOOL_INVOCATION:
        file.write("Tool Call:\n")
        data = breakpoint.summary or breakpoint.original_data
        file.write(f"    {data}\n")
        

def write_end_breakpoint(file, event_type: EventTypes, breakpoint: Breakpoint) -> None:
    if event_type == EventTypes.LLM_QUERY:
        file.write("Response:\n")
        data = breakpoint.summary or breakpoint.original_data
        file.write(f"    {data}\n")
    elif event_type == EventTypes.TOOL_INVOCATION:
        file.write("Result:\n")
        data = breakpoint.summary or breakpoint.original_data
        file.write(f"    {data}\n")