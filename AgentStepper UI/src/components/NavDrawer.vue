<script setup>
import { mdiTimelineText, mdiTimelineTextOutline, mdiDotsHorizontal, mdiImport } from '@mdi/js';
import SvgIcon from '@jamescoyle/vue-icon';
import { ref, reactive } from 'vue';

/**
 * Props for the RunMenu component
 * @prop {Array} runs - List of run objects to display
 * @prop {Object} selectedRun - Currently selected run object
 */
defineProps(['runs', 'selectedRun'])

/**
 * Emits events for run interactions
 * @event select-run - Emitted when a run is selected
 * @type {Object} run - The selected run object
 * @event run-renamed - Emitted when a run is renamed
 * @type {Object} { uuid, name } - The run UUID and new name
 * @event download-run - Emitted when run download is requested
 * @type {string} uuid - The run UUID
 * @event import-run - Emitted when import run is requested
 */
const emit = defineEmits(['select-run', 'run-renamed', 'download-run', 'import-run'])

/** @type {Ref<string|null>} - UUID of the run being renamed, or null if none */
const editingRunUuid = ref(null);

/** @type {Ref<string>} - Temporary name for the run being edited */
const tempRunName = ref('');

/** @type {Object} - Tracks menu open state for each run UUID */
const menuStates = reactive({});

/**
 * Starts the rename operation for a run
 * @param {Object} run - The run to rename
 */
function startRename(run) {
  editingRunUuid.value = run.uuid;
  tempRunName.value = run.name;
  menuStates[run.uuid] = false;
}

/**
 * Confirms the rename operation
 * @param {string} uuid - The UUID of the run
 */
function confirmRename(uuid) {
  if (tempRunName.value.trim()) {
    emit('run-renamed', uuid, tempRunName.value.trim());
  }
  cancelRename();
}

/**
 * Cancels the rename operation
 */
function cancelRename() {
  editingRunUuid.value = null;
  tempRunName.value = '';
}

/**
 * Handles keydown events for rename input
 * @param {KeyboardEvent} event - The keydown event
 * @param {string} uuid - The UUID of the run
 */
function handleKeydown(event, uuid) {
  if (event.key === 'Enter') {
    confirmRename(uuid);
  } else if (event.key === 'Escape') {
    cancelRename();
  }
}

/** Emits the download-run event */
const downloadRun = (uuid) => emit('download-run', uuid);

/** Emits the import-run event */
const importRun = () => emit('import-run');

/** Emits the delete-run event */
const deleteRun = (uuid) => emit('delete-run', uuid);
</script>

<template>
  <v-navigation-drawer permanent>
    <v-sheet class="pa-4 transition-transform hover:scale-101" :elevation="6" color="#1976d2">
      <h2 class="text-white text-center font-weight-bold text-h6 hover:text-cyan-lighten-3">
        Agent Runs
      </h2>
    </v-sheet>
    <div v-if="runs.length == 0" class="pa-5 text-caption text-grey-darken-3 text-center">
      Previous agent runs will appear here
    </div>
    <v-list v-else density="compact" nav>
      <v-list-item v-for="run in runs" :key="run.uuid" :title="editingRunUuid === run.uuid ? undefined : run.name"
        :active="selectedRun && selectedRun.uuid === run.uuid" color="primary" class="transition-colors"
        @click="emit('select-run', run)">
        <template v-slot:prepend>
          <svg-icon type="mdi"
            :path="(selectedRun && selectedRun.uuid === run.uuid) ? mdiTimelineText : mdiTimelineTextOutline"
            class="mr-2"></svg-icon>
        </template>
        <template v-slot:title v-if="editingRunUuid === run.uuid">
          <v-text-field v-model="tempRunName" hide-details density="compact" variant="underlined" autofocus
            @blur="cancelRename" @keydown="event => handleKeydown(event, run.uuid)"></v-text-field>
        </template>
        <template v-slot:append>
          <v-menu v-model="menuStates[run.uuid]">
            <template v-slot:activator="{ props }">
              <svg-icon type="mdi" :path="mdiDotsHorizontal" class="mr-2 cursor-pointer options-icon"
                v-bind="props"></svg-icon>
            </template>
            <v-list class="pa-0">
              <v-list-item @click="startRename(run)">Rename</v-list-item>
              <v-list-item @click="downloadRun(run.uuid)">Download Run</v-list-item>
              <v-divider></v-divider>
              <v-list-item @click="deleteRun(run.uuid)">Delete Run</v-list-item>
            </v-list>
          </v-menu>
        </template>
      </v-list-item>
    </v-list>
    <v-divider></v-divider>
    <v-list density="compact" nav>
      <v-list-item title="Import Agent Run" color="primary" class="transition-colors" @click="importRun">
        <template v-slot:prepend>
          <svg-icon type="mdi" :path="mdiImport" class="mr-2"></svg-icon>
        </template>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<style scoped>
.transition-colors:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.nav-banner {
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
}

.nav-message {
  background: rgba(255, 255, 255, 0.8);
}

.options-icon {
  display: none;
}

.v-list-item:hover .options-icon {
  display: block;
}
</style>