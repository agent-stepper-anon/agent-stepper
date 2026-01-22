<template>
  <WindowBase
    :id="props.id"
    :initial-x="props.initialX"
    :initial-y="props.initialY"
    :initial-width="props.initialWidth"
    :initial-height="props.initialHeight"
    :initial-z-index="props.initialZIndex"
    :main-div="props.mainDiv"
    title="Message Inspector (Compare)"
    @close="emit('close', props.id)"
    @updateZIndex="emit('updateZIndex', props.id)"
  >
    <Diff
      mode="split"
      theme="custom"
      :language="diffLanguage"
      :prev="prevContent"
      :current="currentContent"
      class="diff-viewer"
    />
  </WindowBase>
</template>

<script setup>
import { computed } from 'vue';
import WindowBase from './WindowBase.vue';

const props = defineProps({
  id: { type: String, required: true },
  initialX: { type: Number, default: 100 },
  initialY: { type: Number, default: 100 },
  initialWidth: { type: Number, default: 400 },
  initialHeight: { type: Number, default: 300 },
  initialZIndex: { type: Number, default: 1 },
  mainDiv: { type: Object, default: null },
  previousMessage: {
    type: Object,
    required: true,
    validator: (msg) => 'content' in msg && 'contentType' in msg && ['text', 'json'].includes(msg.contentType),
  },
  currentMessage: {
    type: Object,
    required: true,
    validator: (msg) => 'content' in msg && 'contentType' in msg && ['text', 'json'].includes(msg.contentType),
  },
});

const emit = defineEmits(['close', 'updateZIndex']);

/**
 * Determines the language for the Diff component based on message content types.
 * @returns {string} 'json' if both messages are JSON, otherwise 'plaintext'.
 */
const diffLanguage = computed(() => {
  return props.previousMessage.contentType === 'json' && props.currentMessage.contentType === 'json' ? 'json' : 'plaintext';
});

/**
 * Processes the previous message content, stringifying if contentType is 'json'.
 * @returns {string} The processed content for the Diff component.
 */
const prevContent = computed(() => {
  const content = props.previousMessage.content;
  return props.previousMessage.contentType === 'json' && typeof content === 'object' && content !== null
    ? JSON.stringify(content, null, 2)
    : content;
});

/**
 * Processes the current message content, stringifying if contentType is 'json'.
 * @returns {string} The processed content for the Diff component.
 */
const currentContent = computed(() => {
  const content = props.currentMessage.content;
  return props.currentMessage.contentType === 'json' && typeof content === 'object' && content !== null
    ? JSON.stringify(content, null, 2)
    : content;
});
</script>

<style lang="scss">
@use '@/assets/diff-viewer-theme.scss';
</style>

<style lang="css" scoped>
@import './window-base.css';

.vue-diff-wrapper {
  flex-grow: 1;
  overflow-y: auto;
  padding: 5px 0;
}
</style>