/**
 * Manages the core application state and operations.
 */
export class App {
  /**
   * Creates a new App instance.
   */
  constructor() {
    this._runs = [];
    this._displayedRun = null;
    this._socket = null;
  }

  /**
   * Loads the application state from a dictionary received from the backend.
   * @param {Object} state - The dictionary containing app state (runs, activeRun).
   */
  loadAppState(state) {
    if (state.runs && Array.isArray(state.runs)) {
      this._runs = Run.fromDictList(state.runs).sort((a, b) => b.startTime - a.startTime);
      this._runs.forEach(run => this._linkRelatedMessages(run));
    }
    if (this._displayedRun !== null) {
      this._displayedRun = this._runs.find(run => run.uuid === this._displayedRun.uuid) || null;
    }
    if (this._displayedRun === null && state.activeRun) {
      this._displayedRun = this._runs.find(run => run.uuid === state.activeRun) || null;
    }
    if (state.activeRun) {
      this._runs.find(run => run.uuid === state.activeRun).haltedAt = state.haltedAt || null;
    }
  }

  /**
   * Handles incoming messages from the backend.
   * @param {Object} message - The dictionary containing the message event and content.
   * @param {CallableFunction(String)} errorCallback - Function to call with error message
   * as argument if an error message has been received from the server.
   */
  handleMessage(message, errorCallback) {
    import('./messageHandler.js').then(({ handleMessage }) => {
      console.log(message)
      handleMessage(this, message, errorCallback);
    });
  }

  /**
   * Handles the play/pause button click event by sending a continue or halt message to the server.
   */
  handlePlayPause() {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }
    import('./serverMessageFactory.js').then(({ createContinueMessage, createHaltMessage }) => {
      if (this._displayedRun.state === State.HALTED) {
        this.sendMessage(createContinueMessage(this._displayedRun.uuid));
      } else if (this._displayedRun.state === State.CONTINUE || this._displayedRun.state === State.STEP) {
        this.sendMessage(createHaltMessage(this._displayedRun.uuid));
      }
    });
  }

  /**
   * Handles the step button click event by sending a step message to the server if the run is halted.
   */
  handleStep() {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }
    import('./serverMessageFactory.js').then(({ createStepMessage }) => {
      if (this._displayedRun.state === State.HALTED) {
        this.sendMessage(createStepMessage(this._displayedRun.uuid));
      }
    });
  }

  /**
   * Prompts the user to select a run file to upload, reads its bytes, and sends an import message to the server.
   * @throws {Error} If no file is selected or if there is no connection to the server.
   */
  importRun() {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }

    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.run';
    input.onchange = (event) => {
      const file = event.target.files[0];
      if (!file) {
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const content = reader.result;
        import('./serverMessageFactory.js').then(({ createImportRunMessage }) => {
          const message = createImportRunMessage(content);
          this.sendMessage(message);
        });
      };
      reader.readAsText(file);
    };
    input.click();
  }

  /**
   * Sends a message to the server if the socket is active.
   * @param {Object} message - The message to send to the server.
   */
  sendMessage(message) {
    if (this._socket && this._socket.readyState === WebSocket.OPEN) {
      this._socket.send(JSON.stringify(message));
    }
  }

  /**
   * Renames a run by updating it locally and sending a rename request to the server.
   * @param {string} uuid - The UUID of the run to rename.
   * @param {string} name - The new name for the run.
   * @throws {Error} If the server request fails.
   */
  renameRun(uuid, name) {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }

    const run = this._runs.find(r => r.uuid === uuid);
    import('./serverMessageFactory.js').then(({ createRenameRunMessage }) => {
      this.sendMessage(createRenameRunMessage(uuid, name));
      run.name = name;
    });
  }

  /**
   * Requests a run download from the server.
   * @param {string} uuid - The UUID of the run to download.
   * @throws {Error} If the server request fails.
   */
  downloadRun(uuid) {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }

    import('./serverMessageFactory.js').then(({ createDownloadRunRequestMessage }) => {
      this.sendMessage(createDownloadRunRequestMessage(uuid));
    });
  }

  /**
   * Deletes the run by sending a delete message to the server..
   * @param {string} uuid - The UUID of the run to download.
   * @throws {Error} If the server request fails.
   */
  deleteRun(uuid) {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }
    const index = this._runs.findIndex(run => run.uuid === uuid);
    if (index !== -1 && this._runs[index].state === State.IDLE) {
      this._runs.splice(index, 1);
      if (this._displayedRun && this._displayedRun.uuid === uuid) {
        this._displayedRun = null;
      }
      import('./serverMessageFactory.js').then(({ createDeleteRunMessage }) => {
        this.sendMessage(createDeleteRunMessage(uuid));
      });
    }
  }

  /**
   * Edits the content of a message in the displayed run and sends an update to the server.
   * @param {string} uuid - The UUID of the message to edit.
   * @param {string|Object} content - The new content for the message.
   * @throws {Error} If there is no connection to the server or if the message or run is not found.
   */
  editMessage(uuid, content) {
    if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
      throw new Error('No connection to server!');
    }
    const message = this._displayedRun.getMessageByUuid(uuid);
    message.content = content;
    import('./serverMessageFactory.js').then(({ createUpdateMessageContentMessage }) => {
      this.sendMessage(createUpdateMessageContentMessage(this._displayedRun.uuid, uuid, content));
    });
  }

  /**
   * Links related messages within a run by examining adjacent message pairs.
   * @param {Run} run - The run whose messages should be linked.
   */
  _linkRelatedMessages(run) {
    const messages = run.messages;
    for (let i = 1; i < messages.length; i++) {
      const previous = messages[i - 1];
      const current = messages[i];
      if (current.isRelatedMessage(previous)) {
        current.relatedMessage = previous;
        previous.relatedMessage = current;
        i++;
      }
    }
  }

  /**
   * Gets the array of runs in chronological order.
   * @returns {Array<Run>} The list of runs sorted by start time.
   */
  get runs() {
    return this._runs;
  }

  /**
   * Gets the currently displayed run.
   * @returns {Run|null} The displayed run or null if none.
   */
  get displayedRun() {
    return this._displayedRun;
  }

  /**
   * Sets the currently displayed run.
   * @param {Run|null} run - The run to display or null to clear the displayed run.
   */
  set displayedRun(run) {
    this._displayedRun = run;
  }

  /**
   * Sets the WebSocket connection for server communication.
   * @param {WebSocket|null} socket - The WebSocket instance or null to clear the connection.
   */
  set socket(socket) {
    this._socket = socket;
  }
}

import { Run } from './run.js';
import { State } from './run.js';