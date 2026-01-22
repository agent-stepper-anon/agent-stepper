<script>
export default {
  name: 'HeaderBar',
  data() {
    return {
      subtitles: ['LLM', 'Core', 'Tools']
    }
  }
}
</script>

<template>
  <div class="card">
    <header class="toolbar">
      <h1 class="headline">Agent Activity</h1>
      <div class="extension">
        <div class="subtitle-row">
          <span v-for="title in subtitles" class="column-title">{{ title }}</span>
        </div>
      </div>
    </header>
  </div>
</template>

<style scoped>
.card {
  width: 100%;
}

.toolbar {
  background: linear-gradient(90deg, #1976d2, #5293E3);
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  color: white;
  height: 86px; /* 50px for main toolbar + 36px for extension */
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.06);
}

.headline {
  font-size: 16pt;
  font-weight: 600;
  margin: 0;
  line-height: 50px; /* Center vertically in the 50px toolbar height */
  text-align: center;
}

.extension {
  width: 100%;
  height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.subtitle-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  max-width: 1200px; /* Optional: limits max width for better spacing on large screens */
  padding: 0 16px; /* Equal padding on edges */
}

.column-title {
  font-size: 12pt;
  flex: 1;
  text-align: center;
}
</style>