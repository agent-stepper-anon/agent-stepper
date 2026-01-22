# Development Guide — `AgentStepper API`

> **Notice**: this development guide is LLM generated but has been reviewed by the developer of the software.

## What this document is

This is the **developer-facing** guide for the **AgentStepper API** (the agent-side SDK your agent process links against). It explains how the API speaks to the **AgentStepper Core**, how you should structure **begin/end breakpoints**, how **git/shadow workspace** commits work, and which pieces are safe to extend.

If you’re here to:

* **Integrate the debugger into an agent** → jump to [Quick start](#quick-start)
* **Understand flows** → see [Lifecycle & Flows](#lifecycle--flows) and [Message contracts](#message-contracts)
* **Wire up git/commit capture** → see [Shadow workspace & Git](#shadow-workspace--git)
* **Extend or harden** → see [Extension points](#extension-points) & [Error handling notes](#error-handling--gotchas)

---

## High-level responsibilities

The **AgentStepper API** (class `AgentStepper`) lives inside your agent process and:

* Manages a **WebSocket client** connection to the Core (`ws://{address}:{port}`).
* Emits **Events**, **Breakpoints**, and **Commits** to the Core using `AgentCoreMessageFactory`.
* Blocks your agent at **breakpoints** (begin/end of LLM queries, begin/end of tool calls, program start) until the Core/UI lets you proceed (possibly with **modified data**).
* Optionally mirrors your agent’s file edits through a **shadow workspace** and creates **git commits**, sending structured diffs to the Core.

The Core owns the **state machine** (STEP / HALTED / CONTINUE). The API is a thin, synchronous/blocking shim that **waits** for the Core’s response at each breakpoint.

---

## Public API overview

```python
class AgentStepper:
    def __init__(program_name: str, address: str, port: int, agent_workspace_path: Optional[str] = None)

    # LLM query breakpoints
    def begin_llm_query_breakpoint(prompt: Union[str, Dict]) -> Union[str, Dict]
    def end_llm_query_breakpoint(response: Union[str, Dict]) -> Union[str, Dict]

    # Tool invocation breakpoints
    def begin_tool_invocation_breakpoint(tool: str, args: Dict) -> Tuple[str, Dict]
    def end_tool_invocation_breakpoint(results: Union[str, Dict]) -> Union[str, Dict]

    # Git / workspace integration
    def commit_agent_changes(commit_summary: str = '', commit_description: str = '') -> bool

    # UI debug stream
    def post_debug_message(message: str) -> None

    # Context manager support (closes socket, finalizes shadow workspace)
    def __enter__() -> AgentStepper
    def __exit__(exc_type, exc_value, traceback) -> None
```

**Blocking model:** `begin_*`/`end_*` calls **block** until the Core returns the updated Breakpoint. Treat them like “synchronous halting points” in your agent.

---

## Quick start

Minimal pattern for an LLM-tool agent:

```python
from agentstepper.api.debugger import AgentStepper

with AgentStepper(program_name="MyAgent",
                  address="127.0.0.1",
                  port=8765,
                  agent_workspace_path="/path/to/workspace") as dbg:

    # 1) LLM query
    prompt = build_prompt()
    prompt = dbg.begin_llm_query_breakpoint(prompt)
    llm_out = call_llm(prompt)
    llm_out = dbg.end_llm_query_breakpoint(llm_out)

    # 2) Tool call
    tool_name, args = dbg.begin_tool_invocation_breakpoint("search_docs", {"q": "vector db"})
    results = run_tool(tool_name, args)
    results = dbg.end_tool_invocation_breakpoint(results)

    # 3) Optional: persist edits your agent made
    dbg.commit_agent_changes("Refactor: split embedder", "Moved code; updated tests")

    # 4) Optional: send a debug line to the UI
    dbg.post_debug_message("Loop finished.")
```

That’s it—your agent is debuggable. The Core/UI decides when you stop at each breakpoint and can **modify** `prompt`, `tool/args`, `results`, and `llm_out` before your code continues.

---

## Lifecycle & Flows

### 1) Construction & connection

* `AgentStepper.__init__` sets up:

  * WebSocket **client** to the Core (`websockets.sync.client.connect`).
  * A background **daemon thread** that reads Core messages and unblocks pending breakpoints.
  * Optional **shadow workspace** + git repo mirroring if `agent_workspace_path` is provided.

* Immediately after connect, the API:

  * Sends `Event(PROGRAM_STARTED)` and a “Program started” **Breakpoint**.
  * If a repo exists (shadow mode), sends an **initial empty Commit** carrying the current head.

> The agent is **halted right away** on the program-start breakpoint, giving the UI a chance to rename/run-label/etc.

### 2) LLM & tool events

* **LLM query**:

  1. `begin_llm_query_breakpoint(prompt)` → sends `Event(LLM_QUERY)` + Breakpoint(begin). **Blocks** until Core replies with modified data; returns possibly updated `prompt`.
  2. Do the LLM call with that prompt.
  3. `end_llm_query_breakpoint(response)` → sends Breakpoint(end). Blocks; returns possibly updated `response`.

* **Tool invocation**:

  1. `begin_tool_invocation_breakpoint(tool, args)` → sends `Event(TOOL_INVOCATION)` + Breakpoint(begin). Returns possibly updated `(tool, args)`.
  2. Invoke tool.
  3. `end_tool_invocation_breakpoint(results)` → sends Breakpoint(end). Returns possibly updated `results`.

> The API internally keeps a **stack** of pending events to ensure every `end_*` matches a preceding `begin_*`.

### 3) Commits & debug messages

* `commit_agent_changes(...)`:

  * Mirrors your **agent workspace** into the **shadow repo**, creates a **git commit** (LLM-assisted message when summary omitted), and sends a structured **Commit** (id, date, title, list of file `Change`s) to the Core.
* `post_debug_message("...")`:

  * Emits `Event(DEBUG_MESSAGE)` displayed live in the UI.

### 4) Teardown

* Context manager `__exit__` (or object finalization) closes the socket and **finalizes the shadow workspace**:

  * Checks out original branch in the shadow repo.
  * Replaces the agent workspace folder with the shadow folder’s content.

---

## Concurrency model (API side)

* Uses `websockets.sync.client` **synchronous** client.
* Spawns a **daemon thread** to read Core messages. When a **Breakpoint** response arrives, it:

  * Parses via `AgentCoreMessageFactory.parseBreakpointMessage(...)`.
  * Writes the `modified_data` back into the **current pending Breakpoint**.
  * Sets a `threading.Event` to unblock the waiting `begin_*`/`end_*` call.

**Key rule:** the public API methods are **blocking** until the Core responds. Avoid calling them from a thread you can’t stall.

---

## Message contracts

### Wire format (API ↔ Core)

Defined in `agent_core_messages.py`:

* Envelope:

  ```json
  { "message": "event|breakpoint|commit", "data": {...} }
  ```

* Factory/helpers:

  ```python
  AgentCoreMessageFactory.newEventMessage(event)        -> str
  AgentCoreMessageFactory.newBreakpointMessage(bp)      -> str
  AgentCoreMessageFactory.newCommitMessage(commit)      -> str

  AgentCoreMessageFactory.parseEventMessage(json)       -> Event
  AgentCoreMessageFactory.parseBreakpointMessage(json)  -> Breakpoint
  AgentCoreMessageFactory.parseCommitMessage(json)      -> Commit
  AgentCoreMessageFactory.parseMessage(json)            -> Union[Event,Breakpoint,Commit]
  ```

### Event ordering / pairing

* `begin_*` sends `Event(X)` + `Breakpoint(begin)` and pushes the event on an internal **stack**.
* `end_*` **must** pop the same event type and send `Breakpoint(end)`.
* The Core expects a Breakpoint to reference the **most recent** `event_id`.

### Start-of-program breakpoint

* API sends `Event(PROGRAM_STARTED)` and immediately halts with a Breakpoint with summary “Agent program started.”

---

## Shadow workspace & Git

The shadow workspace functionality refers to maintaining a private copy of the repository in a temporary location and copying code changes without git changes to this copy if anything happens. This is sometimes needed to prevent the agent's own commits or git commands from interfering with the repository tracking functionality of AgentStepper.

When `agent_workspace_path` is provided:

1. **Initialize shadow repo**

   * Shadow dir: `tempfile.mkdtemp(prefix='AgentDebuggerShadowWksp_')`
   * Copy user workspace → shadow (excluding `.git`).
   * Initialize git if needed (creates README, first commit, sets user.name/email).
   * Record current branch (or create `default`), ensure **worktree clean** (else raise).

2. **Create run branch**

   * Branch name: `"{program}/runs/{timestamp}"` (whitespace stripped).
   * Checkout the branch.
   * Defer cleanup via a **finalizer** so the original workspace is replaced with the shadow contents on exit.

3. **Committing**

   * `commit_agent_changes(...)`:

     * Sync latest user edits into shadow (excluding `.git`).
     * Build changes via `git_utils.get_changes(repo)`.
     * Compose message:

       * If `commit_summary` provided, use it (+ optional description).
       * Else call `git_utils.generate_commit_message(diff_summary, self._llm)`.
     * `repo.git.add(all=True)` then `repo.git.commit(...)`.
     * Package a `Commit` object with `id`, `date`, `title` (first line of message), and `changes`.
     * Send to Core via `newCommitMessage`.

4. **Initial commit**

   * Immediately after `PROGRAM_STARTED`, sends an initial “Initialized repository” commit (no changes, current head hash).

---

## Error handling & gotchas

* **Connection loss while waiting at a breakpoint**:

  * The daemon thread sets the internal signal so your waiting `begin_*`/`end_*` unblocks, and the API raises `ConnectionError('Connection lost…')`. You should handle this at integration boundaries.

* **Unpaired calls**:

  * Calling `end_*` without a preceding `begin_*` raises `RuntimeError("Can't end breakpoint, breakpoint hasn't begun!")`.

* **Dirty workspace at initialization**:

  * If the repo (shadow) is dirty or has untracked files **right after cloning/initial copy**, the API **removes** the shadow dir and raises `RuntimeError('Repository contains uncommitted changes.')`. Ensure your source workspace is clean before starting.

* **No changes to commit**:

  * `commit_agent_changes` returns `False` and prints “No changes to commit...”.

* **Message parsing**:

  * Unknown envelopes raise `ValueError('Failed to parse client server event message!')` in the factory.

---

## Configuration knobs

* **Networking**: `address`, `port`
* **Identity**: `program_name`
* **Workspace mirroring**: `agent_workspace_path` (optional; enables shadow git flow)
* **OpenAI**: uses `openai.__version__` detection and `openai.OpenAI()` if available; requires `OPENAI_API_KEY` env var

---

## Extension points

### Add a new agent event type

* Extend `EventTypes` in `agentstepper.api.common` with your new value.
* Use the same `begin_*` / `end_*` pattern in your code (create/sent `Event`, send Breakpoint(begin), later Breakpoint(end)).
* The Core’s state derivation may need updates if your type implies a special “thinking/executing” state.

---

## Contracts you must respect

* **Single Core connection** per agent process (the Core enforces one agent at a time).
* **Event/Breakpoint pairing**: every `end_*` must match a preceding `begin_*`.
* **Synchronous halting**: your agent must tolerate blocking waits at breakpoints.

---

## Sequence sketches (agent side)

### LLM query (begin/end)

```
Agent code:
  prompt = begin_llm_query_breakpoint(P)
    ├─ send Event(LLM_QUERY) + BP(begin,P)
    └─ BLOCK until Core replies with BP(modified)
  llm_out = call_llm(prompt)
  llm_out = end_llm_query_breakpoint(llm_out)
    ├─ send BP(end,llm_out)
    └─ BLOCK until Core replies with BP(modified)
```

### Tool invocation (begin/end)

```
(tool,args) = begin_tool_invocation_breakpoint(T,A)
  ├─ send Event(TOOL_INVOCATION) + BP(begin,{T,A})
  └─ BLOCK for modified
results = run_tool(tool,args)
results = end_tool_invocation_breakpoint(results)
  ├─ send BP(end,results)
  └─ BLOCK for modified
```