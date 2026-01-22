<template>
  <div v-for="node in nodes" :key="node.path" class="tree-node">
    <div v-if="node.type === 'folder'" class="folder" :style="indentStyle(node.level)"
      @click="$emit('toggle-folder', node.path)">
      <span class="toggle-icon">
        <svg-icon v-if="node.expanded" type="mdi" :path="pathChevronDown"></svg-icon>
        <svg-icon v-if="!node.expanded" type="mdi" :path="pathChevronUp"></svg-icon>
      </span>
      <span class="folder-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="folderGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#1976d2" />
              <stop offset="100%" stop-color="#42a5f5" />
            </linearGradient>
          </defs>
          <path d="M10,4L12,6H20A2,2 0 0,1 22,8V18A2,2 0 0,1 20,20H4A2,2 0 0,1 2,18V6A2,2 0 0,1 4,4H10Z"
            fill="url(#folderGradient)" />
        </svg>
      </span>
      <span class="folder-name">{{ node.name }}</span>
    </div>
    <div v-else class="file" :style="indentStyle(node.level)" @click="$emit('file-selected', node.path)">
      <span class="file-icon">
        <svg v-if="node.changeType === ChangeType.NEW_FILE" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <defs>
            <linearGradient id="docPlusGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#388E3C" />
              <stop offset="100%" stop-color="#66BB6A" />
            </linearGradient>
          </defs>
          <title>file-document-plus</title>
          <path fill="url(#docPlusGradient)"
            d="M14 2H6C4.89 2 4 2.89 4 4V20C4 21.11 4.89 22 6 22H13.81C13.28 21.09 13 20.05 13 19C13 18.67 13.03 18.33 13.08 18H6V16H13.81C14.27 15.2 14.91 14.5 15.68 14H6V12H18V13.08C18.33 13.03 18.67 13 19 13S19.67 13.03 20 13.08V8L14 2M13 9V3.5L18.5 9H13M18 15V18H15V20H18V23H20V20H23V18H20V15H18Z" />
        </svg>
        <svg v-if="node.changeType === ChangeType.DELETED_FILE" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <defs>
            <linearGradient id="docRemoveGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#C62828" />
              <stop offset="100%" stop-color="#EF5350" />
            </linearGradient>
          </defs>
          <title>file-document-remove</title>
          <path fill="url(#docRemoveGradient)"
            d="M21.12 15.46L19 17.59L16.88 15.46L15.46 16.88L17.59 19L15.46 21.12L16.88 22.54L19 20.41L21.12 22.54L22.54 21.12L20.41 19L22.54 16.88M6 2C4.89 2 4 2.89 4 4V20C4 21.11 4.89 22 6 22H13.81C13.28 21.09 13 20.05 13 19C13 18.67 13.03 18.33 13.08 18H6V16H13.81C14.27 15.2 14.91 14.5 15.68 14H6V12H18V13.08C18.33 13.03 18.67 13 19 13C19.34 13 19.67 13.03 20 13.08V8L14 2M13 3.5L18.5 9H13Z" />
        </svg>
        <svg v-if="node.changeType === ChangeType.CHANGE" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
          <defs>
            <linearGradient id="docEditGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#FBC02D" />
              <stop offset="100%" stop-color="#FFEB3B" />
            </linearGradient>
          </defs>
          <title>file-document-edit</title>
          <path fill="url(#docEditGradient)"
            d="M6,2C4.89,2 4,2.89 4,4V20A2,2 0 0,0 6,22H10V20.09L12.09,18H6V16H14.09L16.09,14H6V12H18.09L20,10.09V8L14,2H6M13,3.5L18.5,9H13V3.5M20.15,13C20,13 19.86,13.05 19.75,13.16L18.73,14.18L20.82,16.26L21.84,15.25C22.05,15.03 22.05,14.67 21.84,14.46L20.54,13.16C20.43,13.05 20.29,13 20.15,13M18.14,14.77L12,20.92V23H14.08L20.23,16.85L18.14,14.77Z" />
        </svg>

      </span>
      <span class="file-name" :class="{ 'font-bold': isSelected(node.path) }">
        {{ node.name }}
      </span>
    </div>
    <div v-if="node.type === 'folder' && node.expanded" class="children">
      <ChangesTree :nodes="node.children" :selected-file-path="selectedFilePath"
        @file-selected="$emit('file-selected', $event)" @toggle-folder="$emit('toggle-folder', $event)" />
    </div>
  </div>
</template>

<script>
import SvgIcon from '@jamescoyle/vue-icon';
import { mdiChevronDown, mdiChevronUp } from '@mdi/js';
import { ChangeType } from '@/app/change.js';

export default {
  name: 'ChangesTree',
  components: {
    SvgIcon
  },
  props: {
    nodes: {
      type: Array,
      required: true,
    },
    selectedFilePath: {
      type: String,
      default: null,
    },
  },
  methods: {
    indentStyle(level) {
      return { paddingLeft: `${level * 12}px` };
    },
    isSelected(filePath) {
      return this.selectedFilePath === filePath;
    },
  },
  data() {
    return {
      pathChevronDown: mdiChevronDown,
      pathChevronUp: mdiChevronUp,
      ChangeType: ChangeType
    }
  },
};
</script>

<style scoped>
.tree-node {
  margin-bottom: 4px;
}

.folder,
.file {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 6px;
}

.toggle-icon,
.folder-icon,
.file-icon {
  display: inline-flex;
  align-items: center;
  width: 16px;
  height: 16px;
}

.folder-name,
.file-name {
  user-select: none;
}

.file-name.font-bold {
  font-weight: bold;
}

.children {
  margin-top: 2px;
}
</style>