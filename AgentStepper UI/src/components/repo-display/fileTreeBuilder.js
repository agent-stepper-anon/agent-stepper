export function buildFileTree(changes, expandedFolders) {
  const tree = [];
  const nodeMap = new Map();

  // Construct tree from file paths
  changes.forEach((change) => {
    const pathParts = change.path.split('/').filter((part) => part);
    let currentPath = '';

    pathParts.forEach((part, index) => {
      const isFile = index === pathParts.length - 1;
      const nodePath = currentPath ? `${currentPath}/${part}` : part;
      currentPath = nodePath;

      if (!nodeMap.has(nodePath)) {
        const node = {
          path: nodePath,
          name: part,
          type: isFile ? 'file' : 'folder',
          level: index,
        };

        if (isFile) {
          node.changeType = change.changeType;
          node.diff = change.diff;
        } else {
          node.children = [];
          node.expanded = expandedFolders.has(nodePath);
        }

        nodeMap.set(nodePath, node);

        // Add to parent or root
        if (index === 0) {
          tree.push(node);
        } else {
          const parentPath = pathParts.slice(0, index).join('/');
          const parent = nodeMap.get(parentPath);
          if (parent && parent.type === 'folder') {
            parent.children.push(node);
          }
        }
      }
    });
  });

  // Sort nodes: folders first, then files, both alphabetically
  const sortNodes = (nodes) =>
    [...nodes].sort((a, b) => {
      if (a.type === b.type) return a.name.localeCompare(b.name);
      return a.type === 'folder' ? -1 : 1;
    });

  const sortedTree = sortNodes(tree);
  sortedTree.forEach((node) => {
    if (node.type === 'folder') {
      node.children = sortNodes(node.children);
    }
  });

  return sortedTree;
}