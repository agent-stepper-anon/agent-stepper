<template>
  <WindowBase
    :id="props.id"
    :initial-x="props.initialX"
    :initial-y="props.initialY"
    :initial-width="props.initialWidth"
    :initial-height="props.initialHeight"
    :initial-z-index="props.initialZIndex"
    :main-div="props.mainDiv"
    title="Message Inspector"
    @close="emit('close', props.id)"
    @updateZIndex="emit('updateZIndex', props.id)"
  >
    <div class="message-container">
      <div class="message-metadata">
        <p class="metadata-line">From: {{ props.message.from }}</p>
        <p class="metadata-line">To: {{ props.message.to }}</p>
        <p class="metadata-line">Message:</p>
      </div>
      <div class="button-group">
        <button v-if="props.message.relatedMessage" class="action-button" @click="emit('openRelatedMessage', $event, props.message)">
          <span class="icon">📄</span> {{ relatedMessageButtonTitle }}
        </button>
        <button class="action-button" @click="emit('compare', props.message)">
          <span class="icon">📄</span> Compare
        </button>
      </div>
    </div>
    <div v-if="props.message.contentType === 'text'" class="message-viewer">
      <div
        v-if="!isEditing"
        class="message-content"
        v-text="props.message.content"
      ></div>
      <textarea
        v-else
        ref="contentTextarea"
        class="message-content editable"
        v-model="editedContent"
      ></textarea>
    </div>
    <div v-else :id="getJsonEditorDivID()" class="message-viewer json_editor"></div>
    <button
      v-if="props.editable"
      class="edit-button"
      @click="toggleEditMode"
      :title="isEditing ? 'Save changes' : 'Edit message'"
    >
      <span class="edit-icon">{{ isEditing ? '✔' : '✏' }}</span>
    </button>
  </WindowBase>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import JSONEditor from 'jsoneditor';
import WindowBase from './WindowBase.vue';

const props = defineProps({
  id: { type: String, required: true },
  initialX: { type: Number, default: 100 },
  initialY: { type: Number, default: 100 },
  initialWidth: { type: Number, default: 400 },
  initialHeight: { type: Number, default: 300 },
  initialZIndex: { type: Number, default: 1 },
  editable: { type: Boolean, default: false },
  mainDiv: { type: Object, default: null },
  message: {
    type: Object,
    required: true,
    validator: (msg) => ['from', 'to', 'content', 'contentType', 'uuid'].every((key) => key in msg),
  },
});

const emit = defineEmits(['close', 'updateZIndex', 'openRelatedMessage', 'compare', 'updateContent', 'error']);

const isEditing = ref(false);
const editedContent = ref('');
const contentTextarea = ref(null);
let jsonEditor = null;

/**
 * Computes the title for the related message button based on message direction.
 * @returns {string} The title for the related message button.
 */
const relatedMessageButtonTitle = computed(() => {
  const { from, to } = props.message;
  if (from === 'LLM' && to === 'Core') return 'Open Prompt';
  if (from === 'Core' && to === 'LLM') return 'Open Response';
  if (from === 'Tools' && to === 'Core') return 'Open Tool Call';
  if (from === 'Core' && to === 'Tools') return 'Open Result';
  return 'Open Related Message';
});

/**
 * Returns the ID of the div containing the JSON editor.
 * @returns {string} ID of the div container containing the JSON editor.
 */
function getJsonEditorDivID() {
  return props.id + '_json_editor';
}

/**
 * Sets the JSON editor to code mode for editing.
 */
async function startJsonEditing() {
  if (jsonEditor) {
    jsonEditor.setMode('code');
  }
}

/**
 * Validates and saves JSON content, switching back to view mode if valid.
 * @returns {Promise<boolean>} True if content was valid and saved, false otherwise.
 */
async function saveJsonContent() {
  if (!jsonEditor) return false;
  const errors = await jsonEditor.validate();
  if (errors.length > 0) {
    emit('error', "Can't save changes, JSON invalid...");
    return false;
  }
  const newContent = jsonEditor.get();
  if (!isDeepEqual(props.message.content, newContent)) {
    emit('updateContent', { uuid: props.message.uuid, content: newContent });
  }
  jsonEditor.setMode('view');
  return true;
}

/**
 * Performs a deep comparison of two objects to check for equivalence.
 * @param {Object} obj1 - First object to compare.
 * @param {Object} obj2 - Second object to compare.
 * @returns {boolean} True if objects are equivalent, false otherwise.
 */
function isDeepEqual(obj1, obj2) {
  if (obj1 === obj2) return true;
  if (typeof obj1 !== 'object' || typeof obj2 !== 'object' || obj1 == null || obj2 == null) {
    return false;
  }
  const keys1 = Object.keys(obj1);
  const keys2 = Object.keys(obj2);
  if (keys1.length !== keys2.length) return false;
  for (const key of keys1) {
    if (!keys2.includes(key) || !isDeepEqual(obj1[key], obj2[key])) {
      return false;
    }
  }
  return true;
}

/**
 * Toggles between editing and view modes for content.
 */
async function toggleEditMode() {
  if (!isEditing.value) {
    if (props.message.contentType === 'text') {
      editedContent.value = props.message.content;
      isEditing.value = true;
      await nextTick();
      contentTextarea.value?.focus();
    } else {
      await startJsonEditing();
      isEditing.value = true;
    }
  } else {
    if (props.message.contentType === 'text') {
      if (editedContent.value !== props.message.content) {
        emit('updateContent', { uuid: props.message.uuid, content: editedContent.value });
      }
      isEditing.value = false;
      contentTextarea.value?.blur();
    } else {
      const saved = await saveJsonContent();
      if (saved) {
        isEditing.value = false;
      }
    }
  }
}

// Watchers
watch(() => props.editable, (newValue, oldValue) => {
  if (oldValue === true && newValue === false && isEditing.value) {
    if (props.message.contentType === 'text') {
      editedContent.value = props.message.content;
      contentTextarea.value?.blur();
    } else if (jsonEditor) {
      jsonEditor.set(props.message.content);
      jsonEditor.setMode('view');
    }
    isEditing.value = false;
  }
});

// Lifecycle Hooks
onMounted(() => {
  if (props.message.contentType !== 'text') {
    const container = document.getElementById(getJsonEditorDivID());
    const options = {
      mode: 'view',
    };
    jsonEditor = new JSONEditor(container, options, props.message.content);
    jsonEditor.expandAll();
  }
});

onUnmounted(() => {
  if (jsonEditor) {
    jsonEditor.destroy();
    jsonEditor = null;
  }
});
</script>

<style>
@import 'jsoneditor/dist/jsoneditor.css';

div.jsoneditor-field,
div.jsoneditor-value,
div.jsoneditor-readonly,
div.jsoneditor-treepath,
span.jsoneditor-treepath-element {
  font-family: 'Roboto', sans-serif;
  font-size: 14px;
}

div.ace_content {
  font-size: 14px;
}

</style>

<style scoped>
@import './window-base.css';

.message-container {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.message-metadata {
  flex: 1;
}

.metadata-line {
  margin: 2px 0;
  font-family: 'Roboto Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  color: #333;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-button {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #444;
  color: white;
  border: none;
  border-radius: 4px;
  font-family: 'Roboto Condensed', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.action-button:hover {
  background: #555;
}

.icon {
  margin-right: 6px;
}

.message-viewer {
  flex: 1;
  background: #ffffff;
  border-radius: 8px;
  padding: 8px;
  overflow-y: auto;
  font-family: 'Roboto Condensed', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #333;
  user-select: text;
}

.message-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-content.editable {
  width: 100%;
  height: 100%;
  resize: none;
  border: none;
  background: #ffffff;
  border-radius: 8px;
  padding: 8px;
  font-family: 'Roboto Condensed', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #333;
}

.message-content.editable:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(0, 0, 0, 0.1) inset;
}

.json_editor {
  padding: 0;
}

.edit-button {
  position: absolute;
  bottom: 18px;
  right: 18px;
  width: 32px;
  height: 32px;
  background: #444;
  color: white;
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 16px;
}

.edit-button:hover {
  background: #555;
}

.edit-icon {
  display: inline-block;
}
</style>