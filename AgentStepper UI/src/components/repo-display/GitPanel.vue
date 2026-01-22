<script setup>
import HeaderBar from './HeaderBar.vue';
import GitTimeline from './GitTimeline.vue';
import Changes from './Changes.vue';
import Accordion from './Accordion.vue';
import { ref, reactive, watch, useTemplateRef, onMounted } from 'vue';

/**
 * Props definition for the component.
 * @typedef {Object} Props
 * @property {Object} run - The currently displayed run object containing commits and selected commit.
 */
const props = defineProps(['run']);

/**
 * Emits definition for the component.
 * @event selectCommit - Emitted when a commit is selected.
 * @event selectFile - Emitted when a file is selected.
 */
const emit = defineEmits(['selectCommit', 'selectChange']);

/**
 * Reactive reference to the expansion panel state.
 * @type {import('vue').Ref<Array<number>>}
 */
const panels = ref([
    { title: 'Commit Graph', isOpen: true },
    { title: 'Changes', isOpen: true },
    { title: 'Diff', isOpen: true },
]);

/** Handles user selection of a commit by emitting the selectCommit event. */
const handleCommitSelected = (commit) => emit('selectCommit', commit);

/** Handles user selection of a change by emitting the selectFile event. */
const handleChangeSelected = (change) => emit('selectChange', change);

</script>

<template>
    <HeaderBar />
    <Accordion :panels="panels" style="z-index: 0;">
        <template #panel-1>
            <GitTimeline :commits="run.commits" :selectedCommit="run.selectedCommit"
                @commit-selected="handleCommitSelected" />
        </template>
        <template #panel-2>
            <Changes :changes="run.selectedCommit?.changes || []" :selectedChange="run.selectedChange"
                @change-selected="handleChangeSelected" />
        </template>
        <template #panel-3>
            <div v-if="run.selectedChange" :style="styleObject" ref="diff-panel">
                <Diff v-if="run.selectedChange.previousContent || run.selectedChange.content" mode="unified" theme="custom" language="plaintext" :prev="run.selectedChange.previousContent"
                    :current="run.selectedChange.content" />
                <div v-else class="empty-state">
                    No content to show
                </div>    
            </div>
            <div v-else class="empty-state">
                Select change to view diff
            </div>
        </template>
    </Accordion>
</template>

<style lang="scss">
@use '@/assets/diff-viewer-theme.scss';
</style>

<style lang="css" scoped>
.expansion-panel-title {
    background: linear-gradient(90deg, #5293E3, #42a5f5);
    font-family: 'Roboto Condensed', sans-serif;
    font-weight: 600;
    font-size: 16px;
    color: white;
}

.empty-state {
    padding: 12px;
    font-size: 12px;
    color: #616161;
    font-family: 'Roboto Condensed', sans-serif;
    font-weight: 600;
    text-align: center;
}
</style>