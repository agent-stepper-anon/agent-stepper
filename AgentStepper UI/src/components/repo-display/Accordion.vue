<template>
  <div class="accordion-container" ref="containerRef">
    <div v-for="(panel, index) in panels" :key="index" class="expansion-panel" :class="{ 'is-closed': !panel.isOpen }">
      <div class="expansion-panel-title" @click="togglePanel(index)">
        {{ panel.title }}
      </div>
      <div class="expansion-panel-content-wrapper" :style="{ height: panel.isOpen ? calculatedPanelHeight + 'px' : '0px' }">
        <div class="expansion-panel-content" ref="contentRefs">
          <slot :name="'panel-' + (index + 1)"></slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, nextTick, watch } from 'vue';

export default {
  name: 'Accordion',
  props: {
    panels: {
      type: Array,
      default: () => [
        { title: 'Panel 1', isOpen: true },
        { title: 'Panel 2', isOpen: true },
        { title: 'Panel 3', isOpen: true }
      ]
    }
  },
  setup(props) {
    const containerRef = ref(null);
    const contentRefs = ref([]);
    const calculatedPanelHeight = ref(0);

    const openPanelCount = computed(() => {
      return props.panels.filter(panel => panel.isOpen).length;
    });

    const updatePanelHeights = () => {
      if (!containerRef.value) return;

      const containerHeight = containerRef.value.offsetHeight;
      const titleHeight = 36; // Fixed title height in pixels
      const totalTitleHeight = props.panels.length * titleHeight;
      const availableContentHeight = containerHeight - totalTitleHeight;
      const openPanels = openPanelCount.value || 1; // Avoid division by zero
      calculatedPanelHeight.value = availableContentHeight / openPanels;
    };

    const togglePanel = async (index) => {
      props.panels[index].isOpen = !props.panels[index].isOpen;
      await nextTick();
      updatePanelHeights();
    };

    onMounted(async () => {
      props.panels.forEach(panel => {
        panel.isOpen = true;
      });
      await nextTick();
      updatePanelHeights();
    });

    // Watch for changes in openPanelCount to recalculate heights
    watch(openPanelCount, () => {
      updatePanelHeights();
    });

    // Watch for window resize to update heights
    watch(() => containerRef.value?.offsetHeight, () => {
      updatePanelHeights();
    });

    return {
      togglePanel,
      openPanelCount,
      contentRefs,
      containerRef,
      calculatedPanelHeight
    };
  }
};
</script>

<style scoped>
.accordion-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.expansion-panel {
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease-in-out;
}

.expansion-panel-title {
  background: linear-gradient(90deg, #5293E3, #42a5f5);
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  font-size: 16px;
  color: white;
  padding: 0 15px;
  cursor: pointer;
  user-select: none;
  height: 36px;
  line-height: 36px;
}

.expansion-panel-content-wrapper {
  overflow: hidden;
  transition: height 0.3s ease-in-out;
}

.expansion-panel-content {
  background: white;
  min-height: 0;
  opacity: 1;
  transition: opacity 0.3s ease-in-out;
  overflow-y: auto;
  height: 100%;
}

.expansion-panel.is-closed .expansion-panel-content {
  opacity: 0;
}

/* Distribute remaining space among open panels */
.expansion-panel {
  flex: 0 0 auto; /* Changed to prevent automatic flex growth */
}

.expansion-panel.is-closed {
  flex: 0 0 auto;
}
</style>