<script setup>
import { ref } from 'vue';
import { mdiMenu, mdiMenuOpen, mdiInformationOutline } from '@mdi/js';
import SvgIcon from '@jamescoyle/vue-icon'
import AgentStepperLogo from '@/assets/AgentStepperLogoAlt.svg'

defineProps(['drawer'])

</script>

<template>
  <v-app-bar elevation="4" class="px-2">
    <v-app-bar-nav-icon class="nav-icon transition-transform hover:scale-110" @click="$emit('drawer-toggled')">
      <svg-icon type="mdi" :path="drawer ? mdiMenuOpen : mdiMenu" color="white" size="28"></svg-icon>
    </v-app-bar-nav-icon>
    <img :src="AgentStepperLogo" alt="AgentStepper Logo" height="40px"/>
    <v-app-bar-title class="app-title font-weight-bold text-white text-h6 transition-colors hover:text-cyan-lighten-2">
      AgentStepper—Interactive LLM Agent Debugger
    </v-app-bar-title>
    <v-btn icon class="info-btn mr-2 transition-transform hover:rotate-45" color="white">
      <svg-icon type="mdi" :path="mdiInformationOutline" color="white"></svg-icon>
    </v-btn>
  </v-app-bar>
</template>