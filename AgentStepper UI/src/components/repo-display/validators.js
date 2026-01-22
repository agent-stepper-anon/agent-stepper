export function validateChanges(changes) {
  return changes.every(
    (change) =>
      change.path &&
      typeof change.path === 'string' &&
      change.changeType &&
      ['new file', 'deleted file', 'change'].includes(change.changeType) &&
      change.diff !== undefined,
  );
}