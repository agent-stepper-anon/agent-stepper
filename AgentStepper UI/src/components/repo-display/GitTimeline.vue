<template>
  <div v-if="commits.length === 0" class="empty-state">
    Commit history will appear here
  </div>
  <div ref="timelineContainer" class="git-timeline scrollbar-hidden">
    <div v-for="(commit, index) in commits" :key="commit.id" class="commit-item" :class="{ 'no-margin-bottom': index === commits.length - 1 }" @click="selectCommit(commit)" :data-commit-id="commit.id">
      <div class="timeline-connector" v-if="index < commits.length - 1"></div>
      <div class="commit-circle" :class="{ selected: selectedCommit === commit }"></div>
      <div class="commit-title" :class="{ 'font-bold': selectedCommit === commit }">
        {{ commit.title }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, useTemplateRef, watch, nextTick } from 'vue';

/**
 * GitTimeline component displays a vertical timeline of git commits.
 * Each commit is represented by a circle and title, with a connector line between commits.
 * Emits an event when a commit is selected.
 * 
 * @component
 */
const props = defineProps({
  /**
   * Array of commit objects, each containing an id and title.
   * @type {Array<{ id: string, title: string }>}
   */
  commits: {
    type: Array,
    required: true,
    validator: (commits) => commits.every((commit) => commit.id && commit.title),
  },
  /**
   * The currently selected commit object.
   * @type {Object|null}
   */
  selectedCommit: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['commit-selected']);

/**
 * Reference to the scrollable timeline container.
 */
const timelineContainer = useTemplateRef('timelineContainer');

/**
 * Tracks whether auto-scrolling is enabled.
 */
const isAutoScrollEnabled = ref(true);

/**
 * Scrolls the timeline container to the bottom with a smooth animation.
 */
function scrollToBottom() {
  if (timelineContainer.value) {
    timelineContainer.value.scrollTo({
      top: timelineContainer.value.scrollHeight,
      behavior: 'smooth'
    });
  }
}

/**
 * Scrolls to a specific commit, positioning it at the top if there is enough content below.
 * @param {Object} commit - The commit to scroll to
 */
async function scrollToCommit(commit) {
  if (!timelineContainer.value || !commit) return;
  
  const commitId = commit.id;
  const selector = `[data-commit-id="${commitId}"]`;
  const element = timelineContainer.value.querySelector(selector);
  
  if (!element) return;

  const { top, bottom } = element.getBoundingClientRect();
  const { top: containerTop, bottom: containerBottom } = timelineContainer.value.getBoundingClientRect();
  const containerHeight = containerBottom - containerTop;
  const scrollHeight = timelineContainer.value.scrollHeight;
  const elementBottom = bottom - containerTop + timelineContainer.value.scrollTop;
  
  // Check if the commit is outside the viewport
  const isInView = top >= containerTop && bottom <= containerBottom;
  
  if (!isInView) {
    // Check if there's enough content below to justify scrolling to top
    const contentBelow = scrollHeight - elementBottom;
    const blockPosition = contentBelow > containerHeight ? 'start' : 'center';
    
    element.scrollIntoView({ behavior: 'smooth', block: blockPosition });
  }
}

/**
 * Handles scroll events to enable or disable auto-scrolling based on scroll position.
 * Allows a small threshold (e.g., 10 pixels) to account for floating-point imprecision.
 */
function scrollHandler() {
  if (timelineContainer.value) {
    const { scrollTop, scrollHeight, clientHeight } = timelineContainer.value;
    isAutoScrollEnabled.value = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
  }
}

/**
 * Emits the selected commit to the parent component.
 * @param {Object} commit - The commit object to select.
 */
function selectCommit(commit) {
  emit('commit-selected', commit);
}

// Watch for new commits and auto-scroll if enabled
watch(
  () => props.commits,
  () => {
    if (isAutoScrollEnabled.value) {
      nextTick(() => {
        scrollToBottom();
      });
    }
  },
  { deep: true, immediate: true }
);

// Watch for selectedCommit changes to scroll to the matching commit
watch(
  () => props.selectedCommit,
  async (newCommit) => {
    if (newCommit && newCommit.id) {
      await nextTick();
      scrollToCommit(newCommit);
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.empty-state {
  padding: 12px;
  font-size: 12px;
  color: #616161;
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  text-align: center;
}

.git-timeline {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  font-size: 12px;
  padding: 10px;
  overflow-y: auto;
  height: 100%;
}

.commit-item {
  display: flex;
  align-items: center;
  position: relative;
  margin-bottom: 10px;
  cursor: pointer;
}

.commit-item.no-margin-bottom {
  margin-bottom: 0;
}

.commit-circle {
  width: 16px;
  height: 16px;
  min-width: 16px;
  border-radius: 50%;
  background: linear-gradient(45deg, #FBC02D, #FFEB3B);
  border: 2px solid white;
  z-index: 1;
}

.commit-circle.selected {
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.3);
  transform: scale(1.2);
}

.commit-title {
  margin-left: 10px;
  color: #333;
}

.commit-title.font-bold {
  font-weight: 800;
}

.timeline-connector {
  position: absolute;
  top: 18px;
  left: 7px;
  width: 2px;
  height: 40px;
  background-color: #FBC02D;
  z-index: 0;
}

.pa-3 {
  padding: 12px;
}

.text-caption {
  font-size: 12px;
}

.text-grey-darken-3 {
  color: #616161;
}

.text-center {
  text-align: center;
}
</style>