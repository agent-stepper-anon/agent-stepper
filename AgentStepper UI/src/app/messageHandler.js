/**
 * Enum for EventType values.
 * @readonly
 * @enum {string}
 */
export const EventType = {
  ERROR: 'error',
  INIT_APP_STATE: 'init_app_state',
  NEW_MESSAGE: 'new_message',
  NEW_RUN: 'new_run',
  UPDATE_RUN_STATE: 'update_run_state',
  NEW_COMMIT: 'new_commit',
  RUN_EXPORT: 'run_export'
};

/**
 * Handles incoming messages from the backend and updates the app state accordingly.
 * @param {App} app - The App instance to update.
 * @param {Object} message - The dictionary containing the event and content.
 * @param {CallableFunction(String)} errorCallback - Function to call with error message
 * as argument if an error message has been received from the server.
 */
export function handleMessage(app, message, errorCallback) {
  const { event, content } = message;

  switch (event) {
    case EventType.ERROR:
      errorCallback(content.message);
      break;
    case EventType.INIT_APP_STATE:
      app.loadAppState(content);
      break;
    case EventType.NEW_MESSAGE:
      handleNewMessage(app, content);
      break;
    case EventType.NEW_RUN:
      handleNewRun(app, content);
      break;
    case EventType.UPDATE_RUN_STATE:
      handleUpdateRunState(app, content);
      break;
    case EventType.NEW_COMMIT:
      handleNewCommit(app, content);
      break;
    case EventType.RUN_EXPORT:
      handleRunExport(content);
      break;
    default:
      console.warn(`Unknown event type: ${event}`);
  }
}

/**
 * Handles the NEW_MESSAGE event by adding a message to the specified run.
 * @param {App} app - The App instance to update.
 * @param {Object} content - The content containing run UUID and message dict.
 */
function handleNewMessage(app, content) {
  const run = app.runs.find(r => r.uuid === content.run);
  if (run) {
    const message = Message.fromDict(content.message);
    if (message.isResponse() && run.messages.length > 0) {
      if (message.isRelatedMessage(run.messages.at(-1))) {
        message.relatedMessage = run.messages.at(-1);
        run.messages.at(-1).relatedMessage = message;
      }
    }
    run.messages.push(message);
  }
}

/**
 * Handles the NEW_RUN event by adding a new run to the app state.
 * @param {App} app - The App instance to update.
 * @param {Object} content - The content containing the run dict.
 */
function handleNewRun(app, content) {
  const run = Run.fromDict(content.run);
  app._linkRelatedMessages(run);
  app._runs.unshift(run);
  if (!app._displayedRun || app._displayedRun.state !== State.HALTED) {
    app._displayedRun = run;
  }
}

/**
 * Handles the UPDATE_RUN_STATE event by updating the state of the specified run.
 * @param {App} app - The App instance to update.
 * @param {Object} content - The content containing run UUID and new state.
 */
function handleUpdateRunState(app, content) {
  const run = app.runs.find(r => r.uuid === content.run);
  if (run) {
    run.state = content.state;
    run.agentState = content.agentState;
    run.haltedAt = content.haltedAt || null;
  }
}

/**
 * Handles the NEW_COMMIT event by adding a commit to the specified run.
 * @param {App} app - The App instance to update.
 * @param {Object} content - The content containing run UUID and commit dict.
 */
function handleNewCommit(app, content) {
  const run = app.runs.find(r => r.uuid === content.run);
  if (run) {
    const commit = Commit.fromDict(content.commit);
    run.addCommit(commit);
  }
}

/**
 * Handles the RUN_EXPORT event by decoding a base64 string and prompting file download.
 * @param {Object} content - The content containing name and base64 data string.
 */
function handleRunExport(content) {
  const { name, data } = content;
  const sanitizedName = name
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, '_');
  const filename = `${sanitizedName}.run`;
  
  const blob = new Blob([data], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

import { Run } from './run.js';
import { Message } from './message.js';
import { State } from './run.js';
import { Commit } from './commit.js';