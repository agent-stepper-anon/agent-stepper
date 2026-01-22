/**
 * Represents a Commit entity with associated changes.
 */
export class Commit {
  /**
   * Creates a new Commit instance.
   * @param {string} id - The unique identifier of the commit.
   * @param {Date} date - The date of the commit.
   * @param {string} title - The title of the commit.
   */
  constructor(id, date, title) {
    this._id = id;
    this._date = date;
    this._title = title;
    this._changes = [];
  }

  /**
   * Parses a dictionary into a Commit object.
   * @param {Object} dict - The dictionary to parse.
   * @returns {Commit} A new Commit instance.
   */
  static fromDict(dict) {
    const commit = new Commit(dict.id, new Date(dict.date), dict.title);
    if (dict.changes && Array.isArray(dict.changes)) {
      commit._changes = dict.changes.map(Change.fromDict);
    }
    return commit;
  }

  /**
   * Parses a list of dictionaries into a list of Commit objects.
   * @param {Array<Object>} dictList - The list of dictionaries to parse.
   * @returns {Array<Commit>} A list of Commit instances.
   */
  static fromDictList(dictList) {
    return dictList.map(dict => Commit.fromDict(dict));
  }

  /**
   * Converts the commit to a Message object.
   * @returns {Message} A Message instance representing the commit.
   */
  toMessage() {
    const summary = `Commit ${this._id.slice(0, 6)}: ${this._title}`;
    return new Message(this._id, 'Repository', 'Repository', '', ContentType.TEXT, summary, this._date);
  }

  /**
   * Gets the commit ID.
   * @returns {string} The commit ID.
   */
  get id() {
    return this._id;
  }

  /**
   * Gets the commit date.
   * @returns {Date} The commit date.
   */
  get date() {
    return this._date;
  }

  /**
   * Gets the commit title.
   * @returns {string} The commit title.
   */
  get title() {
    return this._title;
  }

  /**
   * Gets the list of changes.
   * @returns {Array<Change>} The list of changes.
   */
  get changes() {
    return this._changes;
  }
}

import { Change } from './change.js';
import { ContentType, Message } from './message.js';