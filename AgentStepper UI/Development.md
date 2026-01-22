# Development Guide — `AgentStepper UI`

> **Notice**: this development guide is LLM generated but has been reviewed by the developer of the software.

## What this document is

This is the **developer-facing** guide for the web **User Interface** of AgentStepper. It explains how the UI:

* connects to the **Core** over WebSocket,
* keeps local application state (runs, messages, selection),
* reacts to server → UI events,
* sends UI → Core control messages,
* and where to safely extend behavior.

If you’re here to:

* **Add a feature** → jump to [Extension points](#extension-points)
* **Understand flows** → see [Lifecycle & Flows](#lifecycle--flows) and [Events & Messaging](#events--messaging)

---

## High-level responsibilities

* Maintain **in-memory state** of all runs plus the currently displayed run.
* Provide **transport** to the Core via a single WebSocket.
* **Render behavior hooks** (not covered here) call into `App` methods for control actions.
* Process **server -> UI events** (`init_app_state`, `new_run`, `new_message`, `update_run_state`, `new_commit`, `run_export`, `error`).
* Issue **UI -> Core commands** (step/continue/halt/rename/download/import/update/delete).

---

## Modules overview

### `app.js`

Owns state and imperative actions.

```js
export class App {
  constructor()
  loadAppState(state)
  handleMessage(message, errorCallback)
  handlePlayPause()
  handleStep()
  importRun()
  sendMessage(message)
  renameRun(uuid, name)
  downloadRun(uuid)
  deleteRun(uuid)
  editMessage(uuid, content)
  // internal
  _linkRelatedMessages(run)
  // getters/setters
  get runs()
  get displayedRun()
  set displayedRun(run)
  set socket(socket)
}
```

### `serverMessageFactory.js`

Typed constructors for **UI → Core** payloads:

* `createStepMessage(runUuid)`
* `createContinueMessage(runUuid)`
* `createHaltMessage(runUuid)`
* `createRenameRunMessage(runUuid, name)`
* `createDownloadRunRequestMessage(runUuid)`
* `createDeleteRunMessage(runUuid)`
* `createImportRunMessage(bytes)`
* `createUpdateMessageContentMessage(runUuid, messageUuid, content)`

---

## Concurrency & bundling model

* Runs on the **browser’s single event loop**.
* All Core communications happen on **one WebSocket** (stored in `App._socket`). UI guards operations with `WebSocket.OPEN`.

> **Don’t block the UI thread.** File reads (import) use `FileReader` async APIs; large DOM updates should be chunked by view layer if needed.

---

## State model (UI side)

`App` maintains:

* `_runs: Run[]` — **sorted** by `startTime` (descending on initial load). On `NEW_RUN`, new runs are **unshifted** to the front.
* `_displayedRun: Run|null` — selection logic:

  * On app init: picks the **active run** if present, else stable.
  * On `NEW_RUN`: auto-switches to the new run **unless** the current displayed run is halted (to avoid context switch while debugging).
* `haltedAt` is tracked per run (UUID of the pending message if HALTED).
* `_socket: WebSocket|null` — transport.

**Message linking:** `_linkRelatedMessages(run)` pairs adjacent request/response messages when `Message.isRelatedMessage(...)` returns true, and sets `relatedMessage` on both. New messages arriving live in `handleNewMessage` also attempt this pairing with the previous message.

---

## Lifecycle & Flows

### 1) UI boot

1. Create `App` instance.
2. Establish WebSocket and assign to `app.socket`.
3. Core connects the UI and emits `init_app_state`; UI calls `app.loadAppState(...)`.

### 2) User actions (control)

* **Play/Pause** (`App.handlePlayPause`)

  * If displayed run is `HALTED` → send `continue`.
  * If displayed run is `CONTINUE` or `STEP` → send `halt`.
* **Step** (`App.handleStep`)

  * If displayed run is `HALTED` → send `step`.
* **Rename** (`App.renameRun`)

  * Optimistically updates local name and sends `rename_run`.
* **Download** (`App.downloadRun`)

  * Sends `download_run_request`; on response, `messageHandler` triggers browser download.
* **Import** (`App.importRun`)

  * Prompts for `.run` file → `FileReader.readAsText` → sends `import_run` with file contents (string).
* **Delete** (`App.deleteRun`)

  * Allowed **only** when run `state === IDLE`. Removes locally and sends `delete_run`.
* **Edit message** (`App.editMessage`)

  * Updates in-memory message content and sends `update_msg_content` with new content.

### 3) Server → UI updates

* **INIT_APP_STATE**

  * Replace runs via `Run.fromDictList`, relink related messages, pick displayed run, sync `haltedAt`.
* **NEW_RUN**

  * Unshift run, relink its messages, maybe switch selection.
* **NEW_MESSAGE**

  * Append `Message` to run; link with previous when related.
* **UPDATE_RUN_STATE**

  * Update `run.state`, `run.agentState`, and `run.haltedAt`.
* **NEW_COMMIT**

  * `run.addCommit(Commit)`.
* **RUN_EXPORT**

  * Creates a Blob and triggers a **client-side download** named `<sanitized-run-name>.run`.
* **ERROR**

  * Invokes the `errorCallback` passed by the UI shell (surface to user).

---

## Events & Messaging

### Server → UI (handled in `messageHandler`)

| Event              | Payload shape (selected)                                         | Effect                                               |
| ------------------ | ---------------------------------------------------------------- | ---------------------------------------------------- |
| `init_app_state`   | `{ runs: RunDict[], activeRun?: uuid, haltedAt?: uuid }`         | Rehydrate runs & selection.                          |
| `new_run`          | `{ run: RunDict }`                                               | Add run & maybe select.                              |
| `new_message`      | `{ run: uuid, message: MessageDict }`                            | Append & link.                                       |
| `update_run_state` | `{ run: uuid, state: State, agentState: AgentState, haltedAt? }` | Update state fields.                                 |
| `new_commit`       | `{ run: uuid, commit: CommitDict }`                              | Add commit to run.                                   |
| `run_export`       | `{ name: string, data: string }`                                 | Download `.run` file (data is used as text payload). |
| `error`            | `{ message: string }`                                            | Surface via provided `errorCallback`.                |

> **Note:** The UI trusts server payloads to conform to the API/Core’s model contracts (`Run.fromDict`, `Message.fromDict`, etc.). Validation beyond constructor parsing is not performed here.

### UI → Server (built in `serverMessageFactory`, sent via `App.sendMessage`)

| Action UI intent | Event emitted          | Content shape                             |
| ---------------- | ---------------------- | ----------------------------------------- |
| Step             | `step`                 | `{ run }`                                 |
| Continue         | `continue`             | `{ run }`                                 |
| Halt             | `halt`                 | `{ run }`                                 |
| Rename run       | `rename_run`           | `{ run, name }`                           |
| Download run     | `download_run_request` | `{ run }`                                 |
| Delete run       | `delete_run`           | `{ run }`                                 |
| Import run       | `import_run`           | `{ data }` (string read from `.run` file) |
| Edit msg content | `update_msg_content`   | `{ run, message, content }`               |

These event names and shapes **match** the Core’s `_ui_event_handlers` in the Core guide.

---

## Selection & control rules

* Only one run is “displayed”; the **control buttons** act on `displayedRun`.
* `Play/Pause` toggles *continue ↔ halt* based on the run’s **current state** (`State.HALTED`, `State.CONTINUE`, `State.STEP`).
* `Step` only sends if `HALTED`. (No-op otherwise.)
* `Delete` is client-gated to `State.IDLE` to match Core’s constraint (Core will also enforce).

---

## Error handling philosophy (UI layer)

* **Transport guardrails**: Almost all actions check that `WebSocket.OPEN` before sending; otherwise they throw an `Error('No connection to server!')`.
* **Server errors**: The `error` event is routed to an **external `errorCallback`**, allowing the surrounding UI to display a toast/dialog. The UI code does **not** retry or roll back optimistic updates (e.g., renames) on error—leave this to surrounding UX if needed.
* **Optimistic updates**: `renameRun` mutates local state before server confirmation. If you need pessimistic flow, gate the local change behind a success callback or await a server echo event.

---

## Import/Export

* **Import**: `.run` files are read as **text** (not binary). The read string is passed as `content` → `createImportRunMessage(content)`. The Core expects **base64/zlib** per its guide; the UI forwards the **raw file string** (which should already be base64). Keep this consistent with how runs are generated/exported by the Core.
* **Export**: On `run_export`, the UI **saves the provided string as text** to `<sanitized_name>.run`. Sanitization lowercases, strips non-alphanumerics, and converts spaces to underscores.

---

## Sequence sketches (ASCII)

### Initial sync

```
Core: init_app_state{runs, activeRun, haltedAt} ▶ UI
UI:   App.loadAppState(...) → build runs, link related, set displayedRun
```

### Debug step from halt

```
User: clicks Step
UI:   createStepMessage(run) → send
Core: processes → sends update_run_state (STEP or HALTED next) and possibly new_message
UI:   messageHandler updates run.state/agentState/haltedAt and appends message(s)
```

### Continue / halt toggle

```
User: clicks Play/Pause
UI:   if HALTED → send continue
      if CONTINUE/STEP → send halt
Core: updates → emits update_run_state (CONTINUE or HALTING→HALTED on next bp)
UI:   applies state changes
```

---

## Extension points

### Add a new **server → UI** event

1. Add a new key to `EventType` in `messageHandler.js`.
2. Extend `handleMessage(...)` `switch` with a handler that **mutates App state** deterministically.
3. If the view needs additional derived data, compute it here or in model constructors.

### Add a new **UI → Core** action

1. Add a creator in `serverMessageFactory.js`:

   ```js
   export function createMyActionMessage(runUuid, payload) {
     return { event: 'my_action', content: { run: runUuid, ...payload } };
   }
   ```

2. Call it from an `App` method (or a component), after guarding `WebSocket.OPEN`.

3. Update Core: add `UIEventTypes.MY_ACTION` and a handler.
4. 
---

## Gotchas & best practices

* Always check `this._socket.readyState === WebSocket.OPEN` before sending. The code already does; keep that pattern for new actions.
* `importRun()` reads with `readAsText`. If your `.run` payloads become binary, switch to `readAsArrayBuffer` and base64-encode before sending.
* `handleRunExport` currently writes the **raw string** as file content. If Core sends base64, decode before blob creation, or keep symmetry (base64 in, base64 out).