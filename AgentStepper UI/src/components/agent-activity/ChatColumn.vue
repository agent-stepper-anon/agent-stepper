<script setup>
import { ref, useTemplateRef, watch, nextTick } from 'vue';
import ChatBubble from './ChatBubble.vue';
import { Commit } from '@/app/commit';

const props = defineProps({
  messages: {
    type: Array,
    required: true,
  },
  haltedAt: {
    type: String,
    required: true
  },
  selectedCommit: {
    type: Commit,
    required: false
  },
  selectMode: {
    type: Boolean,
    default: false
  },
  mainDiv: {
    type: Object,
    required: true
  },
});

const emit = defineEmits(['open-details', 'messageClicked']);

/**
 * Determines the column offset for a message based on its sender and recipient.
 * @param {Object} message - The message object containing from and to properties
 * @returns {number} The offset value (0 for LLM messages, 6 for others)
 */
function getOffset(message) {
  return (message.from === 'LLM' || message.to === 'LLM') ? 0 : 6
}

/**
 * Determines the CSS class for adding margin to the chat bubble based on its direction.
 * @param {Object} message - The message object containing from and to properties
 * @returns {string} The CSS class for margin (left-to-right-margin or right-to-left-margin)
 */
function getBubbleMarginClass(message) {
  if (
    (message.from === 'LLM') ||
    (message.from === 'Core' && message.to === 'Tools')
  ) {
    return 'left-to-right-margin';
  } else if (
    (message.from === 'Tools') ||
    (message.from === 'Core' && message.to === 'LLM')
  ) {
    return 'right-to-left-margin';
  }
  return 'left-to-right-margin'; // Fallback
}

/**
 * Checks if a message is a system message.
 * @param {Object} message - The message object to check
 * @returns {boolean} True if the message is from and to System
 */
function isSystemMessage(message) {
  return message.from === 'System' && message.to === 'System'
}

/**
 * Checks if a message is a commit message.
 * @param {Object} message - The message object to check
 * @returns {boolean} True if the message is from and to Repository
 */
function isCommitMessage(message) {
  return message.from === 'Repository' && message.to === 'Repository'
}

/**
 * Checks if the agent is currently halted at the message.
 * @param {Object} message - The message object to check
 * @return {boolean} True if the agent is halted at the message
 */
function isHaltedAtMessage(message) {
  return message.uuid === props.haltedAt;
}

/**
 * Checks if the message is the last non-system message by searching backwards.
 * @param {Object} message - The message object to check
 * @returns {boolean} True if the message is the last non-system message
 */
function isLastMessage(message) {
  for (let i = props.messages.length - 1; i >= 0; i--) {
    if (!isSystemMessage(props.messages[i])) {
      return props.messages[i] === message;
    }
  }
  return false;
}

/**
 * Checks if the message should be highlighted based on selectedCommit.
 * @param {Object} message - The message object to check
 * @returns {boolean} True if the message matches the selected commit's ID and is a commit message
 */
function isHighlightedMessage(message) {
  return props.selectedCommit && message.uuid === props.selectedCommit.id && isCommitMessage(message);
}

/**
 * Reference to the scrollable chat container.
 */
const chatContainer = useTemplateRef('chatContainer');

/**
 * Tracks whether auto-scrolling is enabled.
 */
const isAutoScrollEnabled = ref(true);

/**
 * Tracks which message IDs are currently highlighted to manage animation.
 */
const highlightedMessageIds = ref(new Set());

/**
 * Scrolls the chat container to the bottom with a smooth animation.
 */
function scrollToBottom() {
  if (chatContainer.value) {
    chatContainer.value.scrollTo({
      top: chatContainer.value.scrollHeight,
      behavior: 'smooth'
    });
  }
}

/**
 * Scrolls to a specific message, positioning it at the top if there is enough content below, and highlights it briefly.
 * @param {Object} message - The message to scroll to
 */
async function scrollToMessage(message) {
  if (!chatContainer.value || !message) return;
  
  const messageId = message.uuid;
  const selector = `[data-message-id="${messageId}"]`;
  const element = chatContainer.value.querySelector(selector);
  
  if (!element) return;

  const { top, bottom } = element.getBoundingClientRect();
  const { top: containerTop, bottom: containerBottom } = chatContainer.value.getBoundingClientRect();
  const containerHeight = containerBottom - containerTop;
  const scrollHeight = chatContainer.value.scrollHeight;
  const elementBottom = bottom - containerTop + chatContainer.value.scrollTop;
  
  // Check if the message is outside the viewport
  const isInView = top >= containerTop && bottom <= containerBottom;
  
  if (!isInView) {
    // Check if there's enough content below to justify scrolling to top
    const contentBelow = scrollHeight - elementBottom;
    const blockPosition = contentBelow > containerHeight ? 'start' : 'center';
    
    element.scrollIntoView({ behavior: 'smooth', block: blockPosition });
  }
  
  // Apply highlight animation
  if (!highlightedMessageIds.value.has(messageId)) {
    highlightedMessageIds.value.add(messageId);
    await nextTick();
    setTimeout(() => {
      highlightedMessageIds.value.delete(messageId);
    }, 1000); // Match animation duration
  }
}

/**
 * Handles scroll events to enable or disable auto-scrolling based on scroll position.
 * Allows a small threshold (e.g., 10 pixels) to account for floating-point imprecision.
 */
function scrollHandler() {
  if (chatContainer.value) {
    const { scrollTop, scrollHeight, clientHeight } = chatContainer.value;
    isAutoScrollEnabled.value = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
  }
}

// Watch for new messages and auto-scroll if enabled
watch(
  () => props.messages,
  () => {
    if (isAutoScrollEnabled.value) {
      nextTick(() => {
        scrollToBottom();
      });
    }
  },
  { deep: true, immediate: true }
);

// Watch for selectedCommit changes to scroll to and highlight the matching commit message
watch(
  () => props.selectedCommit,
  async (newCommit) => {
    if (newCommit && newCommit.id) {
      const targetMessage = props.messages.find(
        (message) => message.uuid === newCommit.id
      );
      if (targetMessage) {
        await nextTick();
        scrollToMessage(targetMessage);
      }
    }
  },
  { immediate: true }
);
</script>

<template>
    <div ref="chatContainer" class="overflow-auto pb-1 pt-1" @scroll="scrollHandler">
      <v-row v-for="message in messages" no-gutters>
        <v-col
          v-if="isSystemMessage(message) || isCommitMessage(message)"
          cols="12"
          class="system-message"
          :data-message-id="message.uuid"
        >
          <span :class="{ 'highlight-message': isHighlightedMessage(message) }">
            {{ message.summary }}
          </span>
        </v-col>
        <v-col v-else cols="6" :offset="getOffset(message)">
          <div :class="getBubbleMarginClass(message)">
            <ChatBubble
              @open="emit('open-details', message, $event)"
              @select="emit('messageClicked', message, $event)"
              :message="message"
              :highlight="isHaltedAtMessage(message)"
              :lastMessage="isLastMessage(message)"
              :hideToolTip="selectMode"
              :mainDiv="mainDiv"
            />
          </div>
        </v-col>
      </v-row>
    </div>
</template>

<style scoped>

.system-message {
  font-size: 12px;
  color: #616161;
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  font-style: italic;
  text-align: center;
  padding: 5px 0 !important;
}

.highlight-message {
  animation: glow-and-pop 1s ease-in-out;
}

.left-to-right-margin {
  margin-right: 8px;
}

.right-to-left-margin {
  margin-left: 8px;
}

@keyframes glow-and-pop {
  0% {
    text-shadow: 0 0 0 rgba(255, 235, 59, 0);
    transform: scale(1);
  }
  50% {
    text-shadow: 0 0 15px rgba(255, 235, 59, 1);
    transform: scale(1.2);
  }
  100% {
    text-shadow: 0 0 0 rgba(255, 235, 59, 0);
    transform: scale(1);
  }
}
</style>