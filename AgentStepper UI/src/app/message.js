/**
 * Enum for contentType values.
 * @readonly
 * @enum {string}
 */
export const ContentType = {
  JSON: 'json',
  TEXT: 'text'
};

/**
 * Represents a Message entity.
 */
export class Message {
  /**
   * Creates a new Message instance.
   * @param {string} uuid - The unique identifier of the message.
   * @param {string} from - The sender of the message.
   * @param {string} to - The recipient of the message.
   * @param {string|Object} content - The content of the message (JSON or String).
   * @param {string} contentType - The type of content.
   * @param {string} [summary] - The optional summary of the message.
   * @param {Date} sentAt - The date and time the message was sent.
   */
  constructor(uuid, from, to, content, contentType, summary = null, sentAt) {
    this._uuid = uuid;
    this._from = from;
    this._to = to;
    this._content = content;
    this._contentType = contentType;
    this._summary = summary;
    this._sentAt = sentAt;
    this._relatedMessage = null;
  }

  /**
   * Parses a dictionary into a Message object.
   * @param {Object} dict - The dictionary to parse.
   * @returns {Message} A new Message instance.
   */
  static fromDict(dict) {
    return new Message(
      dict.uuid,
      dict.from,
      dict.to,
      dict.content,
      dict.contentType,
      dict.summary || null,
      new Date(dict.sentAt)
    );
  }

  /**
   * Parses a list of dictionaries into a list of Message objects.
   * @param {Array<Object>} dictList - The list of dictionaries to parse.
   * @returns {Array<Message>} A list of Message instances.
   */
  static fromDictList(dictList) {
    return dictList.map(dict => Message.fromDict(dict));
  }

  /**
   * Sorts an array of messages by sentAt time, oldest first.
   * @param {Array<Message>} messages - The array of messages to sort.
   * @returns {Array<Message>} The sorted array of messages.
   */
  static sortMessages(messages) {
    return messages.sort((a, b) => a.sentAt - b.sentAt);
  }

  /**
   * Checks if the message is a response.
   * @returns {boolean} True if the sender is not 'Core', otherwise false.
   */
  isResponse() {
    return this._from !== 'Core';
  }

  /**
   * Determines if the given message is related to this message.
   * @param {Message} message - The message to compare with.
   * @returns {boolean} True if the messages are related, otherwise false.
   */
  isRelatedMessage(message) {
    return message.to === this._from || message.from === this._to;
  }

  /**
   * Gets the UUID.
   * @returns {string} The UUID.
   */
  get uuid() {
    return this._uuid;
  }

  /**
   * Gets the sender.
   * @returns {string} The sender.
   */
  get from() {
    return this._from;
  }

  /**
   * Gets the recipient.
   * @returns {string} The recipient.
   */
  get to() {
    return this._to;
  }

  /**
   * Gets the content.
   * @returns {string|Object} The content.
   */
  get content() {
    return this._content;
  }

  /**
   * Sets the content.
   * @param {string|Object} value - The content to set.
   */
  set content(value) {
    this._content = value;
  }

  /**
   * Gets the content type.
   * @returns {string} The content type.
   */
  get contentType() {
    return this._contentType;
  }

  /**
   * Gets the summary.
   * @returns {string|null} The summary or null if not present.
   */
  get summary() {
    return this._summary;
  }

  /**
   * Gets the sent at date.
   * @returns {Date} The date and time the message was sent.
   */
  get sentAt() {
    return this._sentAt;
  }

  /**
   * Gets the related message.
   * @returns {string|Object} The related message.
   */
  get relatedMessage() {
    return this._relatedMessage;
  }

  /**
   * Sets the related message.
   * @param {string|Object} value - The related message to set.
   */
  set relatedMessage(value) {
    this._relatedMessage = value;
  }
}