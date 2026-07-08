import { getPlot, getTable, getTags, type FetchOptions, type Tag, type TagNode } from "./api";
import { loadConfigForTag } from "./plot-view";
import { resolveTableView } from "./table-view";
import { tagToParts } from "./sidebar-node";

const LOG_PREFIX = "[trendify:prefetch]";

let activeController: AbortController | null = null;

/** `X-Trendify-Hydrate` marks a request as background hydration (as opposed to a real user
 * click), for two reasons: the server logs it, and -- more importantly -- routes it to a
 * dedicated worker thread/connection instead of the main one, so it can never block a real
 * click on this app's single-threaded event loop (see routes/api.py, viewer/hydration.py). This
 * applies to *every* fetch this module makes, including the tag-tree lookup below, not just the
 * per-tag plot/table calls -- any of them can be expensive enough to matter. */
function hydrationOptions(signal: AbortSignal): FetchOptions {
  return { signal, priority: "low", headers: { "X-Trendify-Hydrate": "1" } };
}

/** Walks `tree` down through `parentParts` (matching each level's node by `label`, same as the
 * server-rendered sidebar's trie), returning the children list at that depth -- the root list
 * itself if `parentParts` is empty. */
function findLevel(tree: TagNode[], parentParts: string[]): TagNode[] {
  let level = tree;
  for (const part of parentParts) {
    const node = level.find((n) => n.label === part);
    if (!node) return [];
    level = node.children;
  }
  return level;
}

/** This node's own payload bytes plus every descendant's. Used only to order traversal
 * (biggest branch hydrates first), never reported directly. */
function subtreeBytes(node: TagNode): number {
  return node.children.reduce((sum, child) => sum + subtreeBytes(child), node.size_bytes);
}

/**
 * Flattens `level` (and everything nested under it) into hydration order: a depth-first
 * pre-order walk -- fully descending into a branch before moving on to the next sibling
 * ("wide") -- with siblings at each branching point visited biggest-subtree-first.
 */
function collectHydrationOrder(level: TagNode[]): TagNode[] {
  const ordered = [...level].sort((a, b) => subtreeBytes(b) - subtreeBytes(a));
  const queue: TagNode[] = [];
  for (const node of ordered) {
    if (node.has_records) queue.push(node);
    if (node.children.length > 0) queue.push(...collectHydrationOrder(node.children));
  }
  return queue;
}

/**
 * Builds the full hydration queue by radiating outward from `selectedTag`'s position in the
 * tree: first every *other* branch under its immediate parent folder, walked down to their
 * leaves -- then, once that ring is exhausted, every other branch under the grandparent, and
 * so on out to the tree root. At each ring, exactly one child (the branch leading back toward
 * `selectedTag`, already covered by the previous, deeper ring -- or `selectedTag` itself, at
 * the innermost ring) is skipped; everything else at that level is fully hydrated depth-first.
 * The net effect: the entire tree (minus `selectedTag` itself, already owned by the real click
 * flow) eventually gets cached, nearest branches first.
 */
function buildRadiatingQueue(tree: TagNode[], selectedTag: Tag | null): TagNode[] {
  const fullPath = tagToParts(selectedTag);
  let ancestorParts = fullPath.slice(0, -1);
  let excludeLabel: string | null = fullPath.length > 0 ? fullPath[fullPath.length - 1] : null;
  const queue: TagNode[] = [];

  for (;;) {
    const level = findLevel(tree, ancestorParts);
    const otherBranches = level.filter((node) => node.label !== excludeLabel);
    queue.push(...collectHydrationOrder(otherBranches));
    if (ancestorParts.length === 0) break;
    excludeLabel = ancestorParts[ancestorParts.length - 1];
    ancestorParts = ancestorParts.slice(0, -1);
  }
  return queue;
}

function tagLabel(tag: Tag): string {
  return Array.isArray(tag) ? tag.join("/") : String(tag);
}

/** Warms the cache for one tag's plot and/or table data (whichever kinds it has), concurrently. */
async function hydrateOne(target: TagNode, signal: AbortSignal): Promise<void> {
  const options = hydrationOptions(signal);
  const tasks: Promise<unknown>[] = [];
  if (target.record_kinds.includes("plot")) {
    tasks.push(getPlot(target.key, loadConfigForTag(target.key), options));
  }
  if (target.record_kinds.includes("table")) {
    tasks.push(getTable(target.key, resolveTableView(target.key), options));
  }
  // Best-effort: a prefetch failing or being aborted is expected and silently ignored,
  // Promise.allSettled never rejects.
  await Promise.allSettled(tasks);
}

/**
 * Continuously hydrates the client-side response cache (`api.ts`'s `cachedGet`) for the whole
 * tag tree, radiating outward from wherever the user is currently browsing (see
 * `buildRadiatingQueue`): nearby branches first, each walked all the way down to its leaves
 * before moving on to the next, until every tag is cached or a new selection restarts the walk
 * from wherever the user is now. Already-cached tags resolve instantly (no network call) when
 * the walk reaches them again after a restart, so repeatedly re-selecting tags is cheap.
 *
 * Always cancels whatever hydration was previously in flight first -- even if the new
 * selection lands on a tag mid-walk -- so a real click never has to compete with a
 * low-priority background request for connection slots/bandwidth.
 */
export function schedulePrefetch(selectedTag: Tag | null): void {
  activeController?.abort();
  const controller = new AbortController();
  activeController = controller;
  const { signal } = controller;

  void (async () => {
    let tree: TagNode[];
    try {
      tree = await getTags(hydrationOptions(signal));
    } catch {
      return;
    }
    if (signal.aborted) return;

    const queue = buildRadiatingQueue(tree, selectedTag);
    if (queue.length === 0) return;

    console.info(`${LOG_PREFIX} hydrating ${queue.length} tag(s), radiating out from current selection`);
    for (const target of queue) {
      if (signal.aborted) return;
      console.info(
        `${LOG_PREFIX} hydrating "${tagLabel(target.key)}" (${target.size_bytes} bytes, ${target.record_kinds.join("+")})`,
      );
      await hydrateOne(target, signal);
    }
    if (!signal.aborted) {
      console.info(`${LOG_PREFIX} finished hydrating entire tree`);
    }
  })();
}
