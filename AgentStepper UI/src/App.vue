<script setup>
import { onMounted, ref, reactive, useTemplateRef } from 'vue';
import NavDrawer from '@/components/NavDrawer.vue';
import AppBar from '@/components/AppBar.vue';
import Footer from '@/components/Footer.vue';
import AgentActivity from '@/components/agent-activity/AgentActivity.vue';
import GitPanel from '@/components/repo-display/GitPanel.vue';
import AgentControls from './components/AgentControls.vue';
import { App } from '@/app/app.js';
import { connect, showNotification } from '@/app/connectionHandler.js';
import GettingStarted from '@/components/GettingStarted.vue';
import { State } from '@/app/run.js';

const drawer = ref(true)
const app = reactive(new App())
const showError = ref(false)
const errorMessage = ref('')
const mainDivRef = useTemplateRef('main-div')
const leftColWidth = ref(66.67) // Initial width percentage for left column (8/12 equivalent)
const isDragging = ref(false)

/**
 * Displays the error banner with the given text for 5 seconds.
 * @param message Error message text to display.
 */
function displayError(message) {
  errorMessage.value = message;
  showError.value = true;
  setTimeout(() => showError.value = false, 3000);
}

/**
 * Helper method to handle function execution with error display.
 * @param {Function} action - The function to execute.
 * @param {string} errorMessage - The error message to display in case of failure.
 */
const tryOrDisplayError = (action, errorMessage) => {
  try {
    action();
  } catch (error) {
    displayError(errorMessage);
  }
};

const onSelectRun = run => app.displayedRun = run;
const onRunRenamed = (uuid, name) => tryOrDisplayError(() => app.renameRun(uuid, name), "Failed to rename run...");
const onDownloadRun = (uuid) => tryOrDisplayError(() => app.downloadRun(uuid), "Failed to request download...");
const onImportRun = () => tryOrDisplayError(() => app.importRun(), "Can't import run, no connection...");
const onUpdateMessage = (uuid, content) => tryOrDisplayError(() => app.editMessage(uuid, content), "Can't edit message, no connection...");
const onPlayPause = () => tryOrDisplayError(() => app.handlePlayPause(), "Can't complete action, no connection...");
const onStep = () => tryOrDisplayError(() => app.handleStep(), "Can't complete action, no connection...");
const onSelectCommit = (commit) => app.displayedRun.selectedCommit = commit;
const onSelectChange = (change) => app.displayedRun.selectedChange = change;
const onServerConnected = socket => app.socket = socket;
const onServerDisconnected = () => app.socket = null;
const onServerMessage = msg => app.handleMessage(JSON.parse(msg.data), displayError);

/** Deletes the run from the server. Displays an error if that fails. */
const onDeleteRun = (uuid) => {
  const run = app.runs.find(r => r.uuid === uuid);
  if (run && run.state === State.IDLE) {
    tryOrDisplayError(() => app.deleteRun(uuid), "Failed to delete run, no connection...");
  } else {
    displayError("Can't delete run currently active!");
  }
};

const startDragging = (e) => {
  e.preventDefault()
  isDragging.value = true
  document.body.style.userSelect = 'none'
  document.addEventListener('pointermove', handleDragging)
  document.addEventListener('pointerup', stopDragging)
}

const handleDragging = (e) => {
  if (!isDragging.value || !mainDivRef.value) return
  const rect = mainDivRef.value.getBoundingClientRect()
  const offsetX = e.clientX - rect.left
  const containerWidth = rect.width
  const newWidth = (offsetX / containerWidth) * 100
  // Ensure width stays within reasonable bounds (e.g., 20% to 80%)
  leftColWidth.value = Math.max(35, Math.min(80, newWidth))
}

const stopDragging = () => {
  isDragging.value = false
  document.body.style.userSelect = ''
  document.removeEventListener('pointermove', handleDragging)
  document.removeEventListener('pointerup', stopDragging)
}

onMounted(() => {
  connect(onServerConnected, onServerDisconnected, onServerMessage);
});
</script>

<template>
  <v-responsive class="h-screen">
    <v-app class="d-flex flex-column fill-height">
      <NavDrawer v-model="drawer" :runs="app.runs" :selectedRun="app.displayedRun" @select-run="onSelectRun"
        @run-renamed="onRunRenamed" @download-run="onDownloadRun" @delete-run="onDeleteRun" @import-run="onImportRun" />
      <AppBar :drawer="drawer" @drawer-toggled="drawer = !drawer" />

      <v-main class="flex-1-1-0">
        <div ref="main-div" class="fill-height" style="position: relative;">
          <div v-if="app.displayedRun" class="d-flex flex-row fill-height">
            <div :style="{ width: leftColWidth + '%' }" class="d-flex flex-column fill-height">
              <AgentActivity class="flex-1-1-0" :messages="app.displayedRun.messages"
                :haltedAt="app.displayedRun.haltedAt" :mainDiv="mainDivRef"
                :selectedCommit="app.displayedRun.selectedCommit" @error="displayError"
                @updateMessage="onUpdateMessage" />
              <AgentControls class="flex-0-0" :state="app.displayedRun.state" :agentState="app.displayedRun.agentState"
                @pausePlay="onPlayPause" @step="onStep" :mainDiv="mainDivRef" />
            </div>
            <div :style="{ width: (100 - leftColWidth) + '%' }" class="d-flex flex-column fill-height">
              <GitPanel :run="app.displayedRun" @selectCommit="onSelectCommit" @selectChange="onSelectChange" />
            </div>
            <div class="resize-divider" @pointerdown="startDragging"></div>
          </div>
          <div v-else class="d-flex justify-center align-center fill-height">
            <GettingStarted />
          </div>
        </div>
      </v-main>

      <Footer class="flex-0-0" />
    </v-app>
    <div :class="['error-notification', { show: showError }]">
      {{ errorMessage }}
    </div>
    <div :class="['connection-lost-notification', { show: showNotification }]">
      Connection lost, reconnecting...
    </div>
  </v-responsive>
</template>

<style scoped>
@import '@/assets/connection-lost-banner.css';
@import '@/assets/error-banner.css';

a {
  text-decoration: none;
  color: inherit;
}

a:hover,
a:focus,
a:active {
  text-decoration: none;
  color: inherit;
}

.resize-divider {
  position: absolute;
  top: 0;
  left: v-bind('`calc(${leftColWidth}% - 2.5px)`');
  width: 5px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
}
</style>