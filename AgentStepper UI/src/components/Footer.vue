<template>
  <v-footer class="footer justify-center" :elevation="4">
      <span class="text-white text-caption py-2">
        {{ new Date().getFullYear() }} —
        <a href="https://xxx/index.html"
          class="footer-link text-cyan-lighten-3 font-weight-bold">
          xxxx
        </a>
      </span>
  </v-footer>
</template>

<style scoped>
.footer {
  background: linear-gradient(135deg, #1976d2, #42a5f5);
  animation: gradientShift 8s ease infinite;
  height: 56px;
}

.footer-link {
  text-decoration: none;
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }

  50% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0% 50%;
  }
}
</style>