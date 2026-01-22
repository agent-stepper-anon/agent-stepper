<script setup>
import { ref, computed } from 'vue';
import SvgIcon from '@jamescoyle/vue-icon';
import { mdiSquare, mdiDebugStepOver, mdiPlay } from '@mdi/js';
import { State } from '@/app/run.js';

const emit = defineEmits(['pausePlay', 'step']);

const props = defineProps({
  state: {
    type: String,
    required: true,
    validator: (value) => Object.values(State).includes(value),
  },
  agentState: {
    type: String,
    required: true
  },
  mainDiv: {
    type: Object,
    required: true
  }
});

const isTooltipVisiblePausePlay = ref(false);
const isTooltipVisibleStep = ref(false);
const tooltipX = ref(0);
const tooltipY = ref(0);
let tooltipTimeoutPausePlay = null;
let tooltipTimeoutStep = null;

/**
 * Computes the tooltip text for the pause/play button based on state.
 * @returns {string} The tooltip text
 */
const pausePlayTooltipText = computed(() => {
  return props.state === State.IDLE ? 'Continue' : (props.state === State.CONTINUE || props.state === State.STEP ? 'Halt' : 'Continue');
});

/**
 * Computes the tooltip text for the step button.
 * @returns {string} The tooltip text
 */
const stepTooltipText = computed(() => {
  return 'Step';
});

/**
 * Handles pause/play button click and hides tooltip.
 */
function handlePausePlay() {
  if (props.state !== State.IDLE) {
    emit('pausePlay');
  }
  isTooltipVisiblePausePlay.value = false;
  clearTimeout(tooltipTimeoutPausePlay);
}

/**
 * Handles step button click and hides tooltip.
 */
function handleStep() {
  if (props.state === State.HALTED) {
    emit('step');
  }
  isTooltipVisibleStep.value = false;
  clearTimeout(tooltipTimeoutStep);
}

/**
 * Handles mouse enter event for pause/play button, showing tooltip after a delay.
 */
function onMouseEnterPausePlay() {
  tooltipTimeoutPausePlay = setTimeout(() => {
    isTooltipVisiblePausePlay.value = true;
  }, 500);
}

/**
 * Handles mouse enter event for step button, showing tooltip after a delay.
 */
function onMouseEnterStep() {
  tooltipTimeoutStep = setTimeout(() => {
    isTooltipVisibleStep.value = true;
  }, 500);
}

/**
 * Handles mouse move event, updating the tooltip position relative to mainDiv.
 * @param {MouseEvent} event - The mouse move event
 */
function onMouseMove(event) {
  if (!props.mainDiv) return;
  const rect = props.mainDiv.getBoundingClientRect();
  tooltipX.value = event.clientX - rect.left;
  tooltipY.value = event.clientY - rect.top;
}

/**
 * Handles mouse leave event for pause/play button, hiding tooltip and clearing timeout.
 */
function onMouseLeavePausePlay() {
  clearTimeout(tooltipTimeoutPausePlay);
  isTooltipVisiblePausePlay.value = false;
}

/**
 * Handles mouse leave event for step button, hiding tooltip and clearing timeout.
 */
function onMouseLeaveStep() {
  clearTimeout(tooltipTimeoutStep);
  isTooltipVisibleStep.value = false;
}

/**
 * Computes the CSS styles for the tooltips based on cursor position relative to mainDiv.
 * @returns {Object} The CSS styles for the tooltip
 */
const tooltipStyle = computed(() => ({
  position: 'absolute',
  left: `${tooltipX.value + 10}px`,
  top: `${tooltipY.value + 10}px`,
}));
</script>

<template>
  <div class="toolbar">
    <div class="button-group">
      <v-btn variant="flat" density="compact" class="button pause-play-button" id="pausePlayButton"
        :disabled="state === State.IDLE" @click="handlePausePlay" @mouseenter="onMouseEnterPausePlay"
        @mousemove="onMouseMove" @mouseleave="onMouseLeavePausePlay">
        <svg-icon type="mdi" :path="state === State.CONTINUE || state === State.STEP ? mdiSquare : mdiPlay"
          color="primary" size="24"></svg-icon>
      </v-btn>
      <div v-show="isTooltipVisiblePausePlay" class="tooltip" :style="tooltipStyle">
        {{ pausePlayTooltipText }}
      </div>
      <v-btn variant="flat" density="compact" class="button step-button" id="stepButton"
        :disabled="state !== State.HALTED" @click="handleStep" @mouseenter="onMouseEnterStep" @mousemove="onMouseMove"
        @mouseleave="onMouseLeaveStep">
        <svg-icon type="mdi" :path="mdiDebugStepOver" color="primary" size="24"></svg-icon>
      </v-btn>
      <div v-show="isTooltipVisibleStep" class="tooltip" :style="tooltipStyle">
        {{ stepTooltipText }}
      </div>
    </div>
    <span class="status-text"
      :class="{ 'running': ['Agent running...', 'LLM thinking...', 'Tool executing...', 'Halting at breakpoint...'].includes(agentState) }">
      {{ agentState }}
    </span>
  </div>
</template>

<style lang="css" scoped>
.toolbar {
  background-color: white;
  border-top: 1px solid #e0e0e0;
  border-right: 1px solid #e0e0e0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 44px;
}

.button-group {
  display: flex;
  gap: 8px;
  margin-left: 8px;
}

.button {
  background: linear-gradient(-45deg, #1976d2, #42a5f5);
  color: white;
  width: 36px;
  height: 36px;
  min-width: 36px;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.status-text {
  font-style: italic;
  margin-right: 16px;
}

.status-text.running {
  animation: pulse 1.5s ease-in-out infinite;
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

@keyframes pulse {
  0% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }

  100% {
    opacity: 1;
  }
}
</style>