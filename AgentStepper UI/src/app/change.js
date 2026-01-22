/**
 * Enum for changeType values.
 * @readonly
 * @enum {string}
 */
export const ChangeType = {
  CHANGE: 'change',
  NEW_FILE: 'new file',
  DELETED_FILE: 'deleted file'
};

/**
 * Represents a Change entity associated with a Commit.
 */
export class Change {
  /**
   * Creates a new Change instance.
   * @param {string} path - The file path of the change.
   * @param {string} changeType - The type of change.
   * @param {string} content - The current content of the file.
   * @param {string} previousContent - The previous content of the file.
   */
  constructor(path, changeType, content, previousContent) {
    this._path = path;
    this._changeType = changeType;
    this._content = content;
    this._previousContent = previousContent;
  }

  /**
   * Parses a dictionary into a Change object.
   * @param {Object} dict - The dictionary to parse.
   * @returns {Change} A new Change instance.
   */
  static fromDict(dict) {
    return new Change(dict.path, dict.changeType, dict.content, dict.previousContent);
  }

  /**
   * Parses a list of dictionaries into a list of Change objects.
   * @param {Array<Object>} dictList - The list of dictionaries to parse.
   * @returns {Array<Change>} A list of Change instances.
   */
  static fromDictList(dictList) {
    return dictList.map(dict => Change.fromDict(dict));
  }

  /**
   * Gets the file path.
   * @returns {string} The file path.
   */
  get path() {
    return this._path;
  }

  /**
   * Gets the change type.
   * @returns {string} The change type.
   */
  get changeType() {
    return this._changeType;
  }

  /**
   * Gets the current content.
   * @returns {string} The current content.
   */
  get content() {
    return this._content;
  }

  /**
   * Gets the previous content.
   * @returns {string} The previous content.
   */
  get previousContent() {
    return this._previousContent;
  }
}