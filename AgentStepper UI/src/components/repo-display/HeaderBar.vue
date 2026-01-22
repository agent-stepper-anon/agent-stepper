<script>
export default {
  name: 'HeaderBar'
}
</script>

<template>
  <header class="toolbar">
    <h1 class="headline">Repository</h1>
  </header>
</template>

<style scoped>
.toolbar {
  background: linear-gradient(90deg, #5293E3, #42a5f5);
  min-height: 50px; /* Use min-height to ensure at least 50px */
  display: flex;
  justify-content: center;
  align-items: center;
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  color: white;
  box-sizing: border-box; /* Ensure padding/border don't affect height */
}

.headline {
  font-size: 16pt;
  font-weight: 600;
  margin: 0;
  line-height: 50px; /* Match the container height for vertical centering */
}
</style>