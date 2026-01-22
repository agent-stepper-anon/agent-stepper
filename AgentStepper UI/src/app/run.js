/**
 * Enum for State values.
 * @readonly
 * @enum {string}
 */
export const State = {
  HALTED: 'halted',
  IDLE: 'idle',
  STEP: 'step',
  CONTINUE: 'continue'
};

/**
 * Represents a Run entity with associated commits and messages.
 */
export class Run {
  /**
   * Creates a new Run instance.
   * @param {string} uuid - The unique identifier of the run.
   * @param {string} name - The name of the run.
   * @param {string} programName - The name of the program.
   * @param {Date} startTime - The start time of the run.
   * @param {string} state - The state of the run.
   * @param {string} agentState - The state of the run's agent.
   */
  constructor(uuid, name, programName, startTime, state, agentState) {
    this._uuid = uuid;
    this._name = name;
    this._programName = programName;
    this._startTime = startTime;
    this._state = state;
    this._agentState = agentState
    this._haltedAt = null;
    this._commits = [];
    this._messages = [];
    this._selectedCommit = null;
    this._selectedChange = null;
  }

  /**
   * Parses a dictionary into a Run object.
   * @param {Object} dict - The dictionary to parse.
   * @returns {Run} A new Run instance.
   */
  static fromDict(dict) {
    const run = new Run(dict.uuid, dict.name, dict.programName, new Date(dict.startTime), dict.state, dict.agentState);
    if (dict.commits && Array.isArray(dict.commits)) {
      run._commits = dict.commits.map(Commit.fromDict);
      run._selectedCommit = run.getLatestCommit();
    }
    if (dict.messages && Array.isArray(dict.messages)) {
      run._messages = dict.messages.map(Message.fromDict);
    }
    if (dict.haltedAt) {
      run._haltedAt = run.getMessageByUuid(dict.haltedAt);
    }
    run._commits.map(c => c.toMessage()).every(m => run._messages.push(m));
    Message.sortMessages(run._messages);
    return run;
  }

  /**
   * Parses a list of dictionaries into a list of Run objects.
   * @param {Array<Object>} dictList - The list of dictionaries to parse.
   * @returns {Array<Run>} A list of Run instances.
   */
  static fromDictList(dictList) {
    return dictList.map(dict => Run.fromDict(dict));
  }

  /**
   * Gets a message by its UUID, searching from newest to oldest.
   * @param {string} uuid - The UUID of the message.
   * @returns {Message|null} The message or null if not found.
   */
  getMessageByUuid(uuid) {
    for (let i = this._messages.length - 1; i >= 0; i--) {
      if (this._messages[i].uuid === uuid) {
        return this._messages[i];
      }
    }
    return null;
  }

  /**
   * Adds a commit to the front of the commit list.
   * @param {Object} commit - The commit to add.
   */
  addCommit(commit) {
    if (this._commits.length === 0 || (this._commits.length > 0 && this._selectedCommit === this._commits.at(-1))) {
      this._selectedCommit = commit;
    }
    this._commits.push(commit);
    this._messages.push(commit.toMessage());
  }

  /**
   * Gets the latest commit from the list.
   * @returns {Object|null} The latest commit or null if the list is empty.
   */
  getLatestCommit() {
    return this._commits.length > 0 ? this._commits.at(-1) : null;
  }

  /**
   * Gets the UUID.
   * @returns {string} The UUID.
   */
  get uuid() {
    return this._uuid;
  }

  /**
   * Gets the name.
   * @returns {string} The name.
   */
  get name() {
    return this._name;
  }

  /**
 * Sets the name.
 * @param {string} value - The new name.
 */
  set name(value) {
    this._name = value;
  }

  /**
   * Gets the program name.
   * @returns {string} The program name.
   */
  get programName() {
    return this._programName;
  }

  /**
   * Gets the start time.
   * @returns {Date} The start time.
   */
  get startTime() {
    return this._startTime;
  }

  /**
   * Gets the state.
   * @returns {string} The state.
   */
  get state() {
    return this._state;
  }

  /**
   * Sets the state.
   * @param {string} value - The state to set.
   */
  set state(value) {
    this._state = value;
  }

  /**
   * Gets the state message.
   * @returns {string|null} The current state message or null if none is set.
   */
  get agentState() {
    return this._agentState;
  }

  /**
   * Sets the state message.
   * @param {string|null} value - The state message to set.
   */
  set agentState(value) {
    this._agentState = value;
  }

  /**
   * Gets the haltedAt message.
   * @returns {Message|null} The message at which the run is halted or null if not halted.
   */
  get haltedAt() {
    return this._haltedAt;
  }

  /**
   * Sets the haltedAt message.
   * @param {Message|null} message The message at which the run is halted or null to unhalt.
   */
  set haltedAt(message) {
    this._haltedAt = message;
  }

  /**
   * Gets the list of commits.
   * The latest commit is at index 0.
   * @returns {Array<Commit>} The list of commits.
   */
  get commits() {
    return this._commits;
  }

  /**
   * Gets the list of messages.
   * @returns {Array<Message>} The list of messages.
   */
  get messages() {
    return this._messages;
  }

  /**
   * Gets the selected commit.
   * @returns {string|null} The selected commit or null if none is selected.
   */
  get selectedCommit() {
    return this._selectedCommit;
  }

  /**
   * Sets the selected commit.
   * @param {string|null} value - The commit to set as selected.
   */
  set selectedCommit(value) {
    this._selectedCommit = value;
    this._selectedChange = null;
  }

  /**
   * Gets the selected change.
   * @returns {Change|null} The selected change or null if none is selected.
   */
  get selectedChange() {
    return this._selectedChange;
  }

  /**
   * Sets the selected change file.
   * @param {Change|null} value - The change to set as selected.
   */
  set selectedChange(value) {
    this._selectedChange = value;
  }

  /**
   * Sets the haltedAt message.
   * @param {Message|null} message - The message to set as haltedAt.
   */
  set haltedAt(message) {
    this._haltedAt = message;
  }
}

import { Commit } from './commit.js';
import { ContentType, Message } from './message.js';