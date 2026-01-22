<template>
  <div
    class="window-base"
    :class="{ 'with-transition': useTransition }"
    :style="windowStyles"
    @mousedown="bringToFront"
    ref="windowRef"
  >
    <div class="top-bar" @mousedown="startDragging" @dblclick="toggleFullScreen">
      <div class="close-button" @click="closeWindow"></div>
      <div class="fullscreen-button" @click="toggleFullScreen"></div>
      <div class="window-title">{{ title }}</div>
    </div>
    <div class="content-area">
      <slot></slot>
    </div>
    <div class="resize-handle right" @mousedown="startResizing('right', $event)"></div>
    <div class="resize-handle bottom" @mousedown="startResizing('bottom', $event)"></div>
    <div class="resize-handle bottom-right" @mousedown="startResizing('bottom-right', $event)"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  id: { type: String, required: true },
  initialX: { type: Number, default: 100 },
  initialY: { type: Number, default: 100 },
  initialWidth: { type: Number, default: 400 },
  initialHeight: { type: Number, default: 300 },
  initialZIndex: { type: Number, default: 1 },
  mainDiv: { type: Object, default: null },
  title: { type: String, default: 'Window' },
});

const emit = defineEmits(['close', 'updateZIndex']);

const windowPosition = ref({
  x: Number.isFinite(props.initialX) ? props.initialX : 100,
  y: Number.isFinite(props.initialY) ? Math.max(64, props.initialY) : 100,
});
const windowSize = ref({
  width: props.initialWidth,
  height: props.initialHeight,
});
const isDragging = ref(false);
const isResizing = ref(false);
const resizeDirection = ref('');
const dragOffset = ref({ x: 0, y: 0 });
const windowRef = ref(null);
const isFullScreen = ref(false);
const previousState = ref(null);
const useTransition = ref(false);
const initialMousePosition = ref(null);
const initialWindowSize = ref(null);

/**
 * Computes the CSS styles for the window based on position, size, and z-index.
 * @returns {Object} CSS styles for the window.
 */
const windowStyles = computed(() => ({
  left: `${windowPosition.value.x}px`,
  top: `${windowPosition.value.y}px`,
  width: `${windowSize.value.width}px`,
  height: `${windowSize.value.height}px`,
  zIndex: props.initialZIndex,
}));

/**
 * Retrieves the current viewport dimensions with fallbacks.
 * @returns {{width: number, height: number}} Viewport dimensions.
 */
function getViewportDimensions() {
  return {
    width: props.mainDiv?.getBoundingClientRect().width || 800,
    height: props.mainDiv?.getBoundingClientRect().height || 600,
  };
}

/**
 * Validates a number, returning a fallback if invalid.
 * @param {number} value - The number to validate.
 * @param {number} fallback - The fallback value.
 * @returns {number} Valid number or fallback.
 */
function ensureValidNumber(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}

/**
 * Initiates window dragging if not clicking the close button.
 * @param {MouseEvent} event - The mousedown event.
 */
function startDragging(event) {
  if (event.target.classList.contains('close-button')) return;
  if (!isFullScreen.value) useTransition.value = false;
  initialMousePosition.value = { x: event.clientX, y: event.clientY };
  const clientX = ensureValidNumber(event.clientX, 0);
  const clientY = ensureValidNumber(event.clientY, 0);
  const posX = ensureValidNumber(windowPosition.value.x, 100);
  const posY = ensureValidNumber(windowPosition.value.y, 100);

  isDragging.value = true;
  dragOffset.value = {
    x: clientX - posX,
    y: clientY - posY,
  };
  document.addEventListener('mousemove', moveWindow);
  document.addEventListener('mouseup', stopDragging);
}

/**
 * Calculates constrained window position during dragging.
 * @param {MouseEvent} event - The mousemove event.
 * @returns {{x: number, y: number}} Constrained position.
 */
function calculateWindowPosition(event) {
  const clientX = ensureValidNumber(event.clientX, 0);
  const clientY = ensureValidNumber(event.clientY, 0);
  const offsetX = ensureValidNumber(dragOffset.value.x, 0);
  const offsetY = ensureValidNumber(dragOffset.value.y, 0);
  const { width: viewportWidth, height: viewportHeight } = getViewportDimensions();
  const windowWidth = ensureValidNumber(windowSize.value.width, 400);

  const minX = -(Math.max(200, windowWidth) - 50);
  const newX = Math.max(minX, Math.min(clientX - offsetX, viewportWidth - 50));
  const newY = Math.max(0, Math.min(clientY - offsetY, viewportHeight - 50));

  return { x: newX, y: newY };
}

/**
 * Updates window position during dragging.
 * @param {MouseEvent} event - The mousemove event.
 */
function moveWindow(event) {
  if (!isDragging.value) return;
  const { x, y } = calculateWindowPosition(event);
  if (isFullScreen.value && initialMousePosition.value) {
    const dx = Math.abs(event.clientX - initialMousePosition.value.x);
    const dy = Math.abs(event.clientY - initialMousePosition.value.y);
    if (dx > 10 || dy > 10) {
      useTransition.value = false;
      isFullScreen.value = false;
      previousState.value = null;
      initialMousePosition.value = null;
    }
  }
  if (Number.isFinite(x) && Number.isFinite(y)) {
    windowPosition.value.x = x;
    windowPosition.value.y = y;
  } else {
    windowPosition.value.x = 100;
    windowPosition.value.y = 100;
  }
}

/**
 * Stops window dragging and removes event listeners.
 */
function stopDragging() {
  isDragging.value = false;
  initialMousePosition.value = null;
  document.removeEventListener('mousemove', moveWindow);
  document.removeEventListener('mouseup', stopDragging);
}

/**
 * Initiates window resizing in the specified direction.
 * @param {string} direction - The resize direction ('right', 'bottom', 'bottom-right').
 * @param {MouseEvent} event - The mousedown event.
 */
function startResizing(direction, event) {
  if (!isFullScreen.value) useTransition.value = false;
  initialWindowSize.value = { width: windowSize.value.width, height: windowSize.value.height };
  isResizing.value = true;
  resizeDirection.value = direction;
  document.addEventListener('mousemove', resizeWindow);
  document.addEventListener('mouseup', stopResizing);
}

/**
 * Updates window size during resizing.
 * @param {MouseEvent} event - The mousemove event.
 */
function resizeWindow(event) {
  if (!isResizing.value) return;
  const rect = windowRef.value.getBoundingClientRect();
  let newWidth = windowSize.value.width;
  let newHeight = windowSize.value.height;
  if (resizeDirection.value.includes('right')) {
    newWidth = Math.max(200, event.clientX - rect.left);
  }
  if (resizeDirection.value.includes('bottom')) {
    newHeight = Math.max(150, event.clientY - rect.top);
  }
  if (isFullScreen.value && initialWindowSize.value) {
    const dw = Math.abs(newWidth - initialWindowSize.value.width);
    const dh = Math.abs(newHeight - initialWindowSize.value.height);
    if (dw > 10 || dh > 10) {
      useTransition.value = false;
      isFullScreen.value = false;
      previousState.value = null;
      initialWindowSize.value = null;
    }
  }
  windowSize.value.width = newWidth;
  windowSize.value.height = newHeight;
}

/**
 * Stops window resizing and removes event listeners.
 */
function stopResizing() {
  isResizing.value = false;
  initialWindowSize.value = null;
  document.removeEventListener('mousemove', resizeWindow);
  document.removeEventListener('mouseup', stopResizing);
}

/**
 * Brings the window to the front by updating its z-index.
 */
function bringToFront() {
  emit('updateZIndex', props.id);
}

/**
 * Closes the window by emitting a close event.
 */
function closeWindow() {
  emit('close', props.id);
}

/**
 * Adjusts window size to fit within viewport constraints.
 * @returns {{width: number, height: number}} Adjusted dimensions.
 */
function adjustWindowSize() {
  const { width: viewportWidth, height: viewportHeight } = getViewportDimensions();
  const currentWidth = ensureValidNumber(windowSize.value.width, 400);
  const currentHeight = ensureValidNumber(windowSize.value.height, 300);

  return {
    width: Math.max(200, Math.min(currentWidth, viewportWidth * 0.8)),
    height: Math.max(150, Math.min(currentHeight, (viewportHeight - 64) * 0.8)),
  };
}

/**
 * Restricts window position to keep the header visible.
 * @param {number} windowWidth - The current window width.
 */
function restrictPositionToViewport(windowWidth) {
  const { width: viewportWidth, height: viewportHeight } = getViewportDimensions();
  const minX = -(Math.max(200, windowWidth) - 50);

  windowPosition.value.x = Math.min(
    ensureValidNumber(windowPosition.value.x, 100),
    viewportWidth - 50
  );
  windowPosition.value.x = Math.max(minX, windowPosition.value.x);
  windowPosition.value.y = Math.min(
    ensureValidNumber(windowPosition.value.y, 100),
    viewportHeight - 50
  );
  windowPosition.value.y = Math.max(64, windowPosition.value.y);
}

/**
 * Handles browser resize by adjusting window size and position.
 */
function handleBrowserResize() {
  const { width, height } = adjustWindowSize();
  windowSize.value.width = width;
  windowSize.value.height = height;
  restrictPositionToViewport(width);
}

/**
 * Toggles the window between full-screen and previous size/position.
 */
function toggleFullScreen() {
  useTransition.value = true;
  if (!isFullScreen.value) {
    previousState.value = {
      x: windowPosition.value.x,
      y: windowPosition.value.y,
      width: windowSize.value.width,
      height: windowSize.value.height,
    };
    const { width: viewportWidth, height: viewportHeight } = getViewportDimensions();
    windowPosition.value.x = 0;
    windowPosition.value.y = 0;
    windowSize.value.width = viewportWidth;
    windowSize.value.height = viewportHeight;
    isFullScreen.value = true;
  } else {
    windowPosition.value.x = previousState.value.x;
    windowPosition.value.y = previousState.value.y;
    windowSize.value.width = previousState.value.width;
    windowSize.value.height = previousState.value.height;
    isFullScreen.value = false;
    previousState.value = null;
  }
  setTimeout(() => {
    useTransition.value = false;
  }, 300);
}

// Lifecycle Hooks
onMounted(() => {
  bringToFront();
  handleBrowserResize();
  window.addEventListener('resize', handleBrowserResize);
});

onUnmounted(() => {
  document.removeEventListener('mousemove', moveWindow);
  document.removeEventListener('mouseup', stopDragging);
  document.removeEventListener('mousemove', resizeWindow);
  document.removeEventListener('mouseup', stopResizing);
  window.removeEventListener('resize', handleBrowserResize);
});
</script>

<style scoped>
@import './window-base.css';
</style>