import type { Tag } from "./api";

// Same ancestor-scope-merging convention as `table-view.ts`/`sidebar-node.ts`: `selectedTag`/
// `selectedRecordKinds` live on the `appShell` scope this component is nested inside.
interface ContentTabsContext {
  contentTab: "plot" | "table";
  selectedTag: Tag | null;
  selectedRecordKinds: string[];
  $watch(property: string, callback: (value: unknown) => void): void;
}

/**
 * Alpine data factory for the main view's outer Plot/Table tab switcher. Defaults to "plot"
 * (Plot is the first tab) whenever a newly-selected tag has plot records, falling back to
 * "table" otherwise -- a tag with only one kind never shows the tab bar at all (see
 * `index.html`'s `x-show` guard), so this only matters for tags with both.
 */
export function contentTabs() {
  return {
    contentTab: "plot" as "plot" | "table",
    init(this: ContentTabsContext) {
      this.$watch("selectedTag", () => {
        this.contentTab = this.selectedRecordKinds.includes("plot") ? "plot" : "table";
      });
    },
  };
}
