<template>
  <div class="changes">
    <div v-if="!hasChanges" class="empty-state">
      No file changes to display
    </div>
    <ChangesTree v-else :nodes="fileTree" :selected-file-path="selectedChange?.path || null" @file-selected="handleFileSelection" @toggle-folder="toggleFolder" />
  </div>
</template>

<script>
import ChangesTree from './ChangesTree.vue';
import { validateChanges } from './validators';
import { buildFileTree } from './fileTreeBuilder';

export default {
  name: 'Changes',
  components: { ChangesTree },
  props: {
    changes: {
      type: Array,
      required: true,
      validator: validateChanges,
    },
    selectedChange: {
      type: Object,
      default: null
    }
  },
  data() {
    return {
      expandedFolders: new Set(),
    };
  },
  computed: {
    hasChanges() {
      return this.changes.length > 0;
    },
    fileTree() {
      return buildFileTree(this.changes, this.expandedFolders);
    },
  },
  created() {
    this.initializeExpandedFolders();
  },
  methods: {
    initializeExpandedFolders() {
      const folderPaths = this.changes
        .flatMap((change) => {
          const parts = change.path.split('/').filter((part) => part);
          const paths = [];
          let currentPath = '';
          for (let index = 0; index < parts.length - 1; index++) {
            currentPath = currentPath ? `${currentPath}/${parts[index]}` : parts[index];
            paths.push(currentPath);
          }
          return paths;
        })
        .filter((path, index, self) => self.indexOf(path) === index); // Remove duplicates
      this.expandedFolders = new Set(folderPaths);
    },
    toggleFolder(folderPath) {
      const updatedFolders = new Set(this.expandedFolders);
      if (updatedFolders.has(folderPath)) {
        updatedFolders.delete(folderPath);
      } else {
        updatedFolders.add(folderPath);
      }
      this.expandedFolders = updatedFolders;
      this.$forceUpdate(); // Required for tree re-render due to Set mutation
    },
    handleFileSelection(filePath) {
      this.$emit('change-selected', this.changes.find(change => change.path === filePath));
    },
  },
};
</script>

<style scoped>
.changes {
  font-family: 'Roboto Condensed', sans-serif;
  font-weight: 600;
  font-size: 12px;
  color: #333;
  padding: 10px
}

.empty-state {
  padding: 12px;
  font-size: 12px;
  color: #616161;
  text-align: center;
}
</style>