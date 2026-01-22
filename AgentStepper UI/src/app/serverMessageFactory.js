/**
 * Creates a step message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @returns {Object} The step message object.
 */
export function createStepMessage(runUuid) {
  return {
    event: 'step',
    content: { run: runUuid }
  };
}

/**
 * Creates a continue message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @returns {Object} The continue message object.
 */
export function createContinueMessage(runUuid) {
  return {
    event: 'continue',
    content: { run: runUuid }
  };
}

/**
 * Creates a halt message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @returns {Object} The halt message object.
 */
export function createHaltMessage(runUuid) {
  return {
    event: 'halt',
    content: { run: runUuid }
  };
}

/**
 * Creates a rename run message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @param {string} name - The new name for the run.
 * @returns {Object} The rename run message object.
 */
export function createRenameRunMessage(runUuid, name) {
  return {
    event: 'rename_run',
    content: { run: runUuid, name: name }
  };
}

/**
 * Creates a download run request message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @returns {Object} The download run request message object.
 */
export function createDownloadRunRequestMessage(runUuid) {
  return {
    event: 'download_run_request',
    content: { run: runUuid }
  };
}

/**
 * Creates a delete run message for the specified run.
 * @param {string} runUuid - The UUID of the run.
 * @returns {Object} The delete run message object.
*/
export function createDeleteRunMessage(runUuid) {
  return {
    event: 'delete_run',
    content: { run: runUuid }
  };
}

/**
 * Creates an import run message with the specified base64 encoded run.
 * @param {String} bytes - The base64 encoded string of the run to import.
 * @returns {Object} The import run message object.
 */
export function createImportRunMessage(bytes) {
  return {
    event: 'import_run',
    content: { data: bytes }
  };
}

/**
 * Creates an update message content message for the specified run and message.
 * @param {string} runUuid - The UUID of the run.
 * @param {string} messageUuid - The UUID of the message.
 * @param {string|Object} content - The new content for the message.
 * @returns {Object} The update message content message object.
 */
export function createUpdateMessageContentMessage(runUuid, messageUuid, content) {
  return {
    event: 'update_msg_content',
    content: { run: runUuid, message: messageUuid, content: content }
  };
}