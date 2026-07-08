import type { Tag } from "./api";
import { loadJSON, saveJSON } from "./local-storage";

function folderOpenStorageKey(path: string[]): string {
  return `trendify:folder-open:${JSON.stringify(path)}`;
}

export function tagToParts(tag: Tag | null): string[] {
  if (tag === null) return [];
  return Array.isArray(tag) ? tag.map(String) : [String(tag)];
}

interface SidebarNodeContext {
  open: boolean;
  autoExpanded: boolean;
  selectedTag: Tag | null;
}

/**
 * Alpine data factory for a sidebar folder row. `path` is this node's full label path from
 * the tree root (e.g. `["nested_plots", "group_a"]`), used both as a stable localStorage key
 * (a bare label isn't unique across the tree -- two different folders can share a name at
 * different levels) and to detect whether this folder is an ancestor of `selectedTag` (the
 * ancestor `appShell` scope's currently-viewed tag, restored from the URL on page load), so
 * it auto-expands to reveal it rather than leaving it hidden in a collapsed folder.
 */
export function sidebarNode(path: string[]) {
  const storageKey = folderOpenStorageKey(path);

  return {
    open: false,
    autoExpanded: false,
    init(this: SidebarNodeContext) {
      const saved = loadJSON<boolean>(storageKey);
      if (saved !== null) {
        this.open = saved;
        return;
      }
      const selectedParts = tagToParts(this.selectedTag);
      this.open =
        selectedParts.length > path.length &&
        path.every((part, i) => part === selectedParts[i]);
    },
    toggle(this: SidebarNodeContext) {
      this.open = !this.open;
      saveJSON(storageKey, this.open);
    },
  };
}
