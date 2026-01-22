<script setup>
import { computed, ref } from 'vue';

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
  highlight: {
    type: Boolean,
    default: false
  },
  lastMessage: {
    type: Boolean,
    default: false
  },
  hideToolTip: {
    type: Boolean,
    default: false
  },
  mainDiv: {
    type: Object,
    required: true
  },
});

const emit = defineEmits(['open', 'select']);

const isAnimating = ref(false);
const isTooltipVisible = ref(false);
const tooltipX = ref(0);
const tooltipY = ref(0);
let tooltipTimeout = null;

/**
 * Computes the CSS class for the chat bubble based on message sender and direction.
 * @returns {string} The CSS class name for the bubble
 */
const bubbleClass = computed(() => {
  let baseClass = '';
  if (props.message.from === 'LLM') {
    baseClass = 'left-to-right llm-message';
  } else if (props.message.from === 'Tools') {
    baseClass = 'right-to-left tools-message';
  } else if (props.message.from === 'Core') {
    baseClass = props.message.to === 'Tools' ? 'left-to-right core-to-tools' : 'right-to-left core-to-llm';
  }
  return props.highlight ? `${baseClass} highlighted` : baseClass;
});

/**
 * Computes the text to display in the chat bubble.
 * Uses summary if available, otherwise uses content with truncation if needed.
 * @returns {string} The text to display
 */
const displayText = computed(() => {
  if (props.message.summary) {
    return props.message.summary;
  }
  const content = props.message.content || '';
  return content.length > 100 ? content.slice(0, 100) + '...' : content;
});

/**
 * Computes the text to display in the tooltip based on highlight state.
 * @returns {string} The tooltip text
 */
const tooltipText = computed(() => {
  return props.highlight ? 'Double-click to edit' : 'Double-click to inspect';
});

/**
 * Handles double-click event on the chat bubble, triggering animation, hiding tooltip, and emitting open event.
 * @param {Event} event - The double-click event
 */
function handleDoubleClick(event) {
  isAnimating.value = true;
  isTooltipVisible.value = false;
  clearTimeout(tooltipTimeout);
  event.preventDefault();
  emit('open', event);
  setTimeout(() => {
    isAnimating.value = false;
  }, 300);
}

/**
 * Handles click event on the chat bubble, hiding tooltip if required and emitting select event.
 * @param {Event} event - The click event
 */
function handleClick(event) {
  if (props.hideToolTip) {
    isTooltipVisible.value = false;
    clearTimeout(tooltipTimeout);
  }
  emit('select', event);
}

/**
 * Handles mouse enter event, showing the tooltip after a delay if not animating.
 */
function onMouseEnter() {
  if (isAnimating.value) return;
  tooltipTimeout = setTimeout(() => {
    isTooltipVisible.value = true;
  }, 500);
}

/**
 * Handles mouse move event, updating the tooltip position.
 * @param {MouseEvent} event - The mouse move event
 */
function onMouseMove(event) {
  if (isAnimating.value) return;
  const rect = props.mainDiv.getBoundingClientRect();
  tooltipX.value = event.clientX - rect.left;
  tooltipY.value = event.clientY - rect.top;
}

/**
 * Handles mouse leave event, hiding the tooltip and clearing the timeout.
 */
function onMouseLeave() {
  clearTimeout(tooltipTimeout);
  isTooltipVisible.value = false;
}

/**
 * Computes the CSS styles for the tooltip based on cursor position.
 * @returns {Object} The CSS styles for the tooltip
 */
const tooltipStyle = computed(() => ({
  position: 'absolute',
  left: `${tooltipX.value + 10}px`,
  top: `${tooltipY.value + 10}px`,
}));
</script>

<template>
  <v-card
    class="chat-bubble mx-auto"
    :class="[bubbleClass, { 'dblclick-animate': isAnimating }]"
    @dblclick="handleDoubleClick($event)"
    @click="handleClick($event)"
    @mouseenter="onMouseEnter"
    @mousemove="onMouseMove"
    @mouseleave="onMouseLeave"
  >
    <v-card-text :class="highlight ? 'chat-text highlighted' : 'chat-text'">
      {{ displayText }}
    </v-card-text>
    <v-card-text v-if="highlight || (lastMessage && !highlight)" class="info-text">
      {{ highlight ? 'Double-click to edit' : 'Double-click to inspect' }}
    </v-card-text>
  </v-card>
  <div v-show="isTooltipVisible && !hideToolTip" class="tooltip" :style="tooltipStyle">
    {{ tooltipText }}
  </div>
</template>

<style scoped>
.chat-bubble {
  max-width: 95%;
  margin: 3px 0;
  border-radius: 12px;
}

.chat-text {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  font-size: 12px;
  color: white;
  padding: 6px 8px;
}

.chat-text.highlighted {
  color: #333;
}

.info-text {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 400;
  font-size: 8pt;
  color: rgba(0, 0, 0, 0.87);
  padding: 0 8px 6px;
}

.left-to-right {
  border-top-left-radius: 0;
}

.right-to-left {
  border-top-right-radius: 0;
}

.left-to-right.llm-message {
  background: linear-gradient(45deg, #66BB6A, #388E3C);
}

.left-to-right.core-to-tools {
  background: linear-gradient(45deg, #42a5f5, #1976d2);
}

.right-to-left.core-to-llm {
  background: linear-gradient(-45deg, #42a5f5, #1976d2);
}

.right-to-left.tools-message {
  background: linear-gradient(-45deg, #66BB6A, #388E3C);
}

.left-to-right.highlighted {
  background: linear-gradient(-45deg, #FFEB3B, #FBC02D);
}

.right-to-left.highlighted {
  background: linear-gradient(45deg, #FFEB3B, #FBC02D);
}

.dblclick-animate {
  animation: pop 0.3s ease;
}

.tooltip {
  background: rgba(0, 0, 0, 0.8);
  color: white;
  font-family: 'Roboto Condensed', sans-serif;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  z-index: 1000;
  pointer-events: none;
}

@keyframes pop {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.03);
  }
  100% {
    transform: scale(1);
  }
}
</style>