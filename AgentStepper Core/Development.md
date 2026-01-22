# Development Guide — `AgentStepperCore`

> **Notice**: this development guide is LLM generated but has been reviewed by the developer of the software.

## What this document is

This is the **developer-facing** guide for `AgentStepperCore`. It explains how the core runs, how it talks to the **AgentStepper API** (agent-side) and the **UI**, how state changes happen, and where to change/extend behavior safely.

**Note, that the core depends on the AgentStepper API**. To learn more about common data types and API-Core messaging, refer to the development guide of the AgentStepper API.

If you’re here to:

* **Add a feature** → jump to [Extension points](#extension-points)
* **Understand flows** → see [Lifecycle & Flows](#lifecycle--flows) and [State machine](#state-machine)

---

## High-level responsibilities

* Hosts **two WebSocket servers**:

  * **API server** for the agent (the “client”) → `_on_agent_connection_attempt`
  * **UI server** for the web UI → `_on_ui_connection_attempt`
* Manages **agent runs**, **events**, **breakpoints**, and **commits**.
* Implements a **debugging state machine** (step/continue/halt).
* Optionally uses OpenAI to **summarize breakpoints** via `PromptHelper`.
* Persists run logs, imports/exports runs, and keeps a run history.

---

## Core class overview

```python
class AgentStepperCore:
    def __init__(host, client_port, ui_port, model, logger=None)
    def start() -> None
    def stop() -> None

    # Execution control (public async)
    async def continue_execution()
    async def halt_execution()
    async def step_over(data: Optional[Any])

    # Internal startup/shutdown
    async def _start_servers()
    async def _stop_servers()

    # Agent server handlers
    async def _on_agent_connection_attempt(websocket)
    async def _on_agent_connected(websocket)
    async def _on_agent_disconnected()
    async def _on_agent_message_received(message)

    # UI server handlers
    async def _on_ui_connection_attempt(websocket)
    async def _on_ui_connected(websocket)
    async def _on_ui_event_received(message)

    # UI actions
    async def _on_ui_step(data)
    async def _on_ui_continue(data)
    async def _on_ui_halt(data)
    async def _on_ui_rename_run(data)
    async def _on_ui_download_request(data)
    async def _on_ui_import_run(data)
    async def _on_ui_update_message(data)
    async def _on_ui_delete_run(data)

    # Event/Breakpoint/Commit processing
    async def _handle_incoming_event(event)
    async def _handle_incoming_breakpoint(breakpoint)
    async def _handle_incoming_commit(commit)

    # Run lifecycle
    async def _start_new_run(start_event)
    async def _end_active_run()
    def _get_new_run_name(program_name) -> str
    def _get_run_with_uuid(run_uuid) -> Optional[Run]

    # State helpers
    def _get_agent_state(is_in_breakpoint: bool, event_type: EventTypes) -> AgentStates
```

---

## Concurrency model

* The Core owns an **`asyncio` event loop** created in `start()` and run on a **dedicated thread**.
* WebSocket servers (`websockets`) are created on that loop.
* Public async APIs (`continue_execution`, `halt_execution`, `step_over`) are intended to be called **on the loop** (usually triggered by UI events). When calling from outside the loop, dispatch via `asyncio.run_coroutine_threadsafe`.

### Threading notes

* `start()` spins `_thread` that runs the loop forever.
* `stop()` schedules `_stop_servers()` onto the loop, waits, then stops the loop and joins the thread.
* Do **not** block the loop. Any long-running CPU work should be offloaded.

---

## Lifecycle & Flows

### 1) Process boot

1. `AgentStepperCore(...).start()`
2. Loop is created, servers are started:

   * API server listens on `host:client_port`
   * UI server listens on `host:ui_port`
3. Log splash + version.

### 2) Connections

* **Agent connects** → `_on_agent_connection_attempt`

  * Enforces **single agent connection**. A second connection is rejected.
  * On connect: `_on_agent_connected`
  * On disconnect: `_on_agent_disconnected` (ends active run if any)

* **UI connects** → `_on_ui_connection_attempt`

  * Enforces **single UI**. A second UI is rejected.
  * On connect: `_on_ui_connected` sends initial app state (runs list, active run, states, and pending message if halted).

### 3) Run start & event flow

```
Agent ---> [Event(PROGRAM_STARTED, data=program_name)] ---> Core
Core  ---> _start_new_run()
              execution_state = STEP
              agent_state     = AGENT_RUNNING
           notify UI: new run + state
```

* Subsequent **events** (LLM queries, tool calls, debug message, etc.) are appended to `active_run`.
* Debug messages are forwarded to UI immediately.

### 4) Breakpoint flow

* Agent sends **Breakpoint** for the most recent event.

* If `execution_state == STEP`:

  * Core **halts**: `execution_state = HALTED`, `agent_state = HALTED`
  * Saves `pending_breakpoint = breakpoint`
  * Notifies UI: new message + halted state (with message UUID)

* If `execution_state == CONTINUE`:

  * Core computes `agent_state` via `_get_agent_state(...)`
  * Immediately **forwards breakpoint back** to the agent (via `AgentCoreMessageFactory.newBreakpointMessage`) → Agent proceeds
  * Notifies UI of state change (still `CONTINUE`)

* **Breakpoint summarization**:

  * If `breakpoint.summary` is empty, Core uses `PromptHelper.summarize_breakpoint(_llm, _model, active_run, breakpoint)` to populate it (if OpenAI is configured; otherwise this may result in a warning or a `None` summary depending on `PromptHelper` behavior).

### 5) Stepping & continuation

* **UI “Step”**:

  * If `HALTED` → calls `step_over(self.pending_breakpoint.modified_data)`:

    * Sends the (possibly modified) breakpoint back to the agent to continue the event.
    * Transitions: `HALTED -> STEP`
    * Updates `agent_state` based on whether we’re still within the event or past its end breakpoint.
  * If `CONTINUE` → sets `STEP` (prepares to halt on next breakpoint)

* **UI “Continue”**:

  * Calls `continue_execution()`:

    * If halted on a pending breakpoint, immediately forwards it to agent (skip/continue).
    * Sets `execution_state = CONTINUE`.
    * Updates UI state.

* **UI “Halt”**:

  * Calls `halt_execution()`:

    * If currently `CONTINUE`, sets `STEP` **and**:

      * If there’s already a pending breakpoint → `agent_state = HALTED`
      * Else → `agent_state = HALTING` (will halt at next breakpoint)

### 6) Run end

* On agent disconnect or explicit program finish:

  * Core creates `Event(PROGRAM_FINISHED)` with a message breakpoint
  * Saves run to logs (`Run.save_to_log(_log_path)`)
  * Moves `active_run` into `run_history`, resets to `None`
  * Signals UI with final message and state `IDLE/AGENT_FINISHED`

---

## State machine

### Execution state transitions

```
IDLE
  └─(PROGRAM_STARTED)──────────▶ STEP
STEP
  ├─(BREAKPOINT RECEIVED)──────▶ HALTED
  ├─(UI CONTINUE)──────────────▶ CONTINUE
  └─(PROGRAM_FINISHED)────────▶ IDLE
HALTED
  ├─(UI STEP)──────────────────▶ STEP (send breakpoint to agent)
  ├─(UI CONTINUE)──────────────▶ CONTINUE (send breakpoint to agent)
  └─(PROGRAM_FINISHED)────────▶ IDLE
CONTINUE
  ├─(UI HALT)──────────────────▶ STEP (HALTING until next breakpoint)
  ├─(BREAKPOINT RECEIVED)──────▶ CONTINUE (forward to agent)
  └─(PROGRAM_FINISHED)────────▶ IDLE
```

### Agent state derivation

`_get_agent_state(is_in_breakpoint, event_type)`:

* If **in breakpoint**:

  * `LLM_QUERY` → `LLM_THINKING`
  * `TOOL_INVOCATION` → `TOOL_EXECUTING`
* Else → `AGENT_RUNNING`

Other states are set explicitly (`HALTED`, `HALTING`, `AGENT_FINISHED`).

---

## Messaging contracts

### Agent → Core

* **Event**: `_handle_incoming_event`

  * `PROGRAM_STARTED` triggers `_start_new_run`
  * `DEBUG_MESSAGE` mirrored to UI immediately
  * Otherwise appended to `active_run`
* **Breakpoint**: `_handle_incoming_breakpoint`

  * Validates an `active_run` exists and the `event_id` is known
  * Halts or forwards depending on `execution_state`
  * Ensures summary exists (LLM summarization if needed)
* **Commit**: `_handle_incoming_commit`

  * Appended to run
  * Mirrored to UI

### Core → Agent

* **Breakpoint**: `AgentCoreMessageFactory.newBreakpointMessage(breakpoint)`

  * Sent on `step_over` and on `continue_execution` if we were halted
  * Also sent immediately when `CONTINUE` on incoming breakpoints

### UI → Core (via `_ui_event_handlers`)

* `STEP`, `CONTINUE`, `HALT`, `RENAME_RUN`, `DOWNLOAD_REQUEST`, `IMPORT_RUN`, `UPDATE_MSG_CONTENT`, `DELETE_RUN`

### Core → UI

* App initialization: `create_init_app_state_message`
* Run control updates: `create_update_run_state_message`
* New run: `create_new_run_message`
* New message: `create_new_message_message` (from breakpoint or debug event)
* New commit: `create_new_commit_message`
* Export: `create_run_export_message(name, bytes)`

---

## Import/Export & Persistence

* **Export (UI → Core)**: `_on_ui_download_request` finds the run and sends `run.to_bytes()` to the UI.
* **Import (UI → Core)**: `_on_ui_import_run`

  * Data is `base64` → `zlib.decompress` → `Run.from_bytes(..., is_base64_encoded=False)`
  * **Version gate**: only accepts runs with `run.server_version == DEBUGGER_SERVER_VERSION`
* **Automatic persistence**: On `_end_active_run()`, calls `Run.save_to_log(self._log_path)`.

---

## Error handling philosophy (current state)

* Many error cases **log** and raise (or `TODO`):

  * Duplicate connections (agent/UI) → refuse, log warnings.
  * Breakpoint without pending event → `RuntimeError`.
  * Parsing unknown message types → `TypeError`.
  * UI update on missing/mismatched pending breakpoint → `ValueError`.
  * Delete active run → `ValueError`.
  * Import version mismatch → currently a silent `pass` (**TODO**).

> **Actionable:** For production hardening, add structured errors back to UI and agent (see [Extension points → Error reporting](#error-reporting)).

---

## Configuration knobs

* **Networking**: `host`, `client_port`, `ui_port`
* **LLM**: `model`, and environment for `OpenAI()` (API key). If unavailable, summarization warnings are logged.
* **Logging**: `logger` or default module logger
* **Persistence**: `_log_path = 'logs'` (constant; make configurable if needed)

---

## Extension points

### Add a new UI action

1. Define event in `UIEventTypes`.
2. Add entry to `_ui_event_handlers` in `__init__`:

   ```python
   UIEventTypes.MY_ACTION.value: self._on_ui_my_action
   ```
3. Implement `async def _on_ui_my_action(self, data: Dict):`
4. If the UI needs confirmation/data back, use `UIMessageFactory` to define a new outbound message.

### Add a new agent event type

1. Extend `EventTypes` (defined in AgentStepper API).
2. Update `_get_agent_state(...)` if the new event type requires a different thinking/executing state.
3. If the UI needs specialized rendering, adjust `ui_serializer.Message.from_breakpoint/from_debug_event`.

### Change breakpoint summarization

* Touch `PromptHelper.summarize_breakpoint(...)` only. You can:

  * Change prompt strategy,
  * Inject model params,
  * Disable entirely when `_llm` is `None`.
* Keep Core unaware of prompt details.

### Error reporting

* Add **structured error messages** to the UI on:

  * Import version mismatch
  * Delete active run
  * Invalid UI command
  * Agent protocol violations
* Implement via new `UIMessageFactory.create_error_message(...)`.

### Multi-agent support (architectural change)

* Replace `_client` single connection with a registry keyed by agent ID.
* Scope `active_run` → `active_runs[agent_id]`.
* Partition `_ui` messages per agent, or add multiplexing in UI.

### Multi-UI observers

* Swap `_ui` with a set of UI connections; broadcast updates.
* Gate “control” actions (step/continue/halt) behind a lock or a leader.

---

## Implementation details & contracts

### Single client invariant

* Only **one agent** and **one UI** may be connected at a time.
* Second connections are rejected **immediately** with a warning and `websocket.close()`.

### Event/Breakpoint ordering

* A **Breakpoint must reference** the **most recently received** event (by `event_id`).
* Receiving a Breakpoint with an unknown `event_id` is an error.

### Stepping contract

* `step_over(data)` is legal **only** when `execution_state == HALTED`. Else → `RuntimeError`.
* `step_over` sends the **pending** breakpoint to the agent and clears it.

### “Halting” vs “Halted”

* When user presses **Halt** during `CONTINUE`, Core enters `STEP` and sets `agent_state = HALTING` to signal intent to stop at **next breakpoint**.
* Once a breakpoint arrives, state becomes **HALTED**.

### Updating pending message content

* `_on_ui_update_message` only updates the **current** `pending_breakpoint.modified_data`.
* UI must provide the **exact** message UUID; otherwise `ValueError`.

### Versioning

* `DEBUGGER_SERVER_VERSION` is enforced on imported runs only.
* Consider including it in network handshakes in the future.

---

## Sequence sketches (ASCII)

### Breakpoint while stepping (halt-on-breakpoint)

```
Agent:  Event(E1) ───────────────▶ Core: add_event(E1), state=STEP
Agent:  Breakpoint(B1,E1) ───────▶ Core: pending=B1, state=HALTED
Core:   UI.new_message(B1)        ▶ UI
Core:   UI.update_state(HALTED)   ▶ UI
```

### Step over

```
UI:     step()                    ▶ Core
Core:   step_over(pending.data), send B1 back to agent
Core:   state=STEP, agent_state=derived
Core:   UI.update_state(STEP)     ▶ UI
```

### Continue from halt

```
UI:     continue()                ▶ Core
Core:   send B1 back to agent, clear pending
Core:   state=CONTINUE
Core:   UI.update_state(CONTINUE) ▶ UI
```

---


## Performance notes

* WebSocket `max_size=None` on the **UI server** (allows large exports/imports/messages). The API server uses defaults.
* Summarization is synchronous from the Core’s perspective (awaiting result inside `_handle_incoming_breakpoint` via `PromptHelper`). If summarization becomes a bottleneck, consider:

  * Offloading summarization to a background task queue and updating the message later.
  * Caching summaries per identical content.

---

## File layout & dependencies

This class lives in `agentstepper/core/agent_stepper_core.py` (or equivalent), with dependencies:

* Protocol: `agentstepper.api.common`, `agentstepper.api.agent_core_message`
* UI: `agentstepper.core.ui_events`, `agentstepper.core.ui_message_factory`, `agentstepper.core.ui_serializer`
* Run/types: `agentstepper.core.types`
* Summarization: `agentstepper.core.prompt_helper`
* Version: `agentstepper.core.server_version`
* Transport: `websockets.asyncio.server`
* Vendor: `openai`

Keep cross-module contracts stable—changes ripple into the UI and agent SDK.