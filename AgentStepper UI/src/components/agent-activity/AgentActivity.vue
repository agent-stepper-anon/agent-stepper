<template>
  <div class="fill-height d-flex flex-column">
    <HeaderBar class="flex-0-0" />
    <ChatColumn class="chat-column flex-1-1-0" :messages="sortedMessages" :haltedAt="haltedAt"
      :selectedCommit="selectedCommit" :selectMode="isComparing" @open-details="openDetails"
      @messageClicked="onMessageClicked" :mainDiv="mainDiv" />
  </div>
  <div v-if="isComparing" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <p class="text-white text-lg font-semibold bg-gray-800 bg-opacity-75 px-4 py-2 rounded">
      Select a message to compare to or press Esc to cancel
    </p>
  </div>
  <template v-else v-for="window in windows" :key="window.id">
    <MessageInspector v-if="window.type === 'message' || !window.type" :id="window.id" :initial-x="window.x"
      :initial-y="window.y" :initial-z-index="window.zIndex" :message="window.message"
      :editable="isEditable(window.message)" :mainDiv="mainDiv" :initial-width="initialWindowSize.width"
      :initial-height="initialWindowSize.height" @close="closeWindow" @updateZIndex="updateZIndex"
      @updateContent="onContentUpdated" @error="onError" @openRelatedMessage="onOpenRelatedMessage"
      @compare="onCompare" />
    <CompareMessageInspector v-if="window.type === 'compare'" :id="window.id" :initial-x="window.x"
      :initial-y="window.y" :initial-z-index="window.zIndex" :previousMessage="window.previousMessage"
      :currentMessage="window.currentMessage" :mainDiv="mainDiv" :initial-width="initialWindowSize.width"
      :initial-height="initialWindowSize.height" @close="closeWindow" @updateZIndex="updateZIndex" />
  </template>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, toRaw } from 'vue';
import HeaderBar from './HeaderBar.vue';
import ChatColumn from './ChatColumn.vue';
import MessageInspector from './inspectors/MessageInspector.vue';
import CompareMessageInspector from './inspectors/CompareMessageInspector.vue';
import { Commit } from '@/app/commit';

const initialWindowSize = { width: 600, height: 500 }

const props = defineProps({
  messages: {
    type: Array,
    required: true,
  },
  haltedAt: {
    type: String,
    required: true
  },
  mainDiv: {
    type: Object,
    required: true
  },
  selectedCommit: {
    type: Commit,
    required: false
  }
});

const emit = defineEmits(['updateMessage', 'error']);

const sortedMessages = computed(() => {
  return props.messages.sort((a, b) => {
    return new Date(a.sentAt) - new Date(b.sentAt);
  });
});

const windows = ref([]);
const zIndexCounter = ref(1);
const isComparing = ref(false);
const comparingMessage = ref(null);

/**
 * Opens a new window (MessageInspector or CompareMessageInspector) with initial position and z-index.
 * @param {Object} message - The message to display (for MessageInspector) or current message (for CompareMessageInspector).
 * @param {Event|null} event - The event containing position information, or null for default positioning.
 * @param {string} type - The type of window ('message' or 'compare').
 * @param {Object} [previousMessage] - The previous message for CompareMessageInspector.
 */
const openNewWindow = (message, event, type = 'message', previousMessage = null) => {
  const id = `window-${Date.now()}`;
  const offset = 10;
  const rect = props.mainDiv.getBoundingClientRect();
  const x = (event?.clientX || 100) + offset - rect.left;
  const y = (event?.clientY || 100) + offset - rect.top;

  windows.value.push({
    id,
    x,
    y,
    zIndex: zIndexCounter.value++,
    message,
    type,
    previousMessage: type === 'compare' ? previousMessage : null,
    currentMessage: type === 'compare' ? message : null,
  });
};

/**
 * Closes the window with the specified ID.
 * @param {string} id - The ID of the window to close.
 */
const closeWindow = (id) => {
  windows.value = windows.value.filter((w) => w.id !== id);
};

/**
 * Updates the z-index of the window with the specified ID to bring it to the front.
 * @param {string} id - The ID of the window to update.
 */
const updateZIndex = (id) => {
  zIndexCounter.value += 1;
  windows.value = windows.value.map((w) =>
    w.id === id ? { ...w, zIndex: zIndexCounter.value } : w
  );
};

/**
 * Handles keydown events, closing the topmost window or exiting comparison mode when 'Esc' or 'q' is pressed.
 * @param {KeyboardEvent} event - The keydown event.
 */
const handleKeydown = (event) => {
  if (event.key === 'Escape' || event.key === 'q') {
    if (isComparing.value) {
      isComparing.value = false;
      comparingMessage.value = null;
    } else {
      const topWindow = windows.value.reduce((top, w) =>
        (!top || w.zIndex > top.zIndex) ? w : top, null);
      if (topWindow) {
        closeWindow(topWindow.id);
      }
    }
  }
};

/**
 * Checks if a message is editable based on its UUID.
 * @param {Object} message - The message to check.
 * @returns {boolean} True if the message is editable, false otherwise.
 */
const isEditable = (message) => {
  return message.uuid === props.haltedAt;
};

/**
 * Opens a new MessageInspector window for the specified message.
 * @param {Object} message - The message to display.
 * @param {Event} event - The event containing position information.
 */
const openDetails = (message, event) => {
  openNewWindow(toRaw(message), event);
};

/**
 * Emits an event to update the message content.
 * @param {Object} params - Object containing uuid and content.
 */
const onContentUpdated = ({ uuid, content }) => {
  emit('updateMessage', uuid, content);
};

/**
 * Opens a new MessageInspector window for a related message.
 * @param {Event} event - The event containing position information.
 * @param {Object} message - The message containing the related message.
 */
const onOpenRelatedMessage = (event, message) => {
  openNewWindow(message.relatedMessage, event);
};

/**
 * Emits an error event.
 * @param {string} errorMessage - The error message to emit.
 */
const onError = (errorMessage) => {
  emit('error', errorMessage);
};

/**
 * Initiates comparison mode for the specified message.
 * @param {Object} message - The message to compare.
 */
const onCompare = (message) => {
  isComparing.value = true;
  comparingMessage.value = toRaw(message);
};

/**
 * Handles message click events, opening a new CompareMessageInspector in comparison mode or a MessageInspector otherwise.
 * @param {Object} message - The clicked message.
 * @param {Event} event - The click event.
 */
const onMessageClicked = (message, event) => {
  if (isComparing.value) {
    openNewWindow(toRaw(message), event, 'compare', comparingMessage.value);
    isComparing.value = false;
    comparingMessage.value = null;
  }
};

// Lifecycle hooks
onMounted(() => {
  window.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown);
});
</script>

<style scoped>
.chat-column {
  border-right: 1px solid #e0e0e0;
}
</style>