"""
Builds the nested tag hierarchy the sidebar renders, shared by the server-rendered page
(`routes.pages`) and the JSON API (`routes.api`).
"""

from __future__ import annotations

import logging
from typing import Literal

from pydantic import BaseModel

from trendify.base.helpers import Tag
from trendify.formats.format2d import PlottableData2D
from trendify.store.record_store import RecordStore
from trendify.store.tags import tag_to_path_parts

__all__ = ["TagNode", "build_tag_tree"]

logger = logging.getLogger(__name__)


class TagNode(BaseModel):
    """One node of the sidebar's nested tag hierarchy."""

    key: Tag
    """The tag (or tag-path segment) this node represents."""

    label: str
    """Display label shown in the sidebar."""

    children: list[TagNode]
    """Nested tag nodes one level below this one."""

    has_records: bool
    """Whether records are tagged with this exact node's `key`, as opposed to only a
    descendant's."""

    record_kinds: list[Literal["plot", "table"]]
    """Kinds of records tagged with this exact node's `key`."""

    size_bytes: int
    """Total payload bytes of records tagged with this exact node's `key` (0 for a node with
    no records of its own). Used by the viewer's background hydration to pick the largest
    sibling tag at whatever level the user is currently browsing."""

    def search_blob(self) -> str:
        """
        Lowercase text of this node's label and every descendant's label, for substring
        search matching without needing to walk the tree again client-side.
        """
        parts = [self.label]
        for child in self.children:
            parts.append(child.search_blob())
        return " ".join(parts).lower()

    def subtree_kinds(self) -> list[Literal["plot", "table"]]:
        """
        Union of this node's own `record_kinds` and every descendant's, so a folder can be
        filtered by record type without needing to walk the tree again client-side (a folder
        should stay visible under a "table" filter if any record anywhere inside it is a
        table, even if the folder itself has no records of its own).
        """
        kinds = set(self.record_kinds)
        for child in self.children:
            kinds.update(child.subtree_kinds())
        return sorted(kinds)

    def record_count(self) -> int:
        """
        Recursive count of self-and-descendant nodes with `has_records`, shown as a
        subtle badge next to folder labels in the sidebar.
        """
        count = 1 if self.has_records else 0
        for child in self.children:
            count += child.record_count()
        return count


class _TrieNode:
    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.tag: Tag | None = None


def _record_kinds(store: RecordStore, tag: Tag) -> list[Literal["plot", "table"]]:
    kinds: list[Literal["plot", "table"]] = []
    if store.has_records(tag=tag, object_type=PlottableData2D):
        kinds.append("plot")
    if store.has_table_entries(tag):
        kinds.append("table")
    return kinds


def _category_rank(node: TagNode) -> int:
    """Folders sort before plot leaves, which sort before table leaves."""
    if node.children:
        return 0
    if "plot" in node.record_kinds:
        return 1
    if "table" in node.record_kinds:
        return 2
    return 3


def build_tag_tree(store: RecordStore) -> list[TagNode]:
    """
    Walks `store.tag_tree()`'s flat, tuple-encoded tags into a nested `TagNode` hierarchy: a
    tag `("a", "b")` becomes a folder `"a"` containing a leaf `"b"`. A tuple prefix (e.g. `"a"`
    from that same tag) may never itself have been used as a real tag, so `has_records` is
    tracked separately from `children` being non-empty, since a node can be a pure folder, a
    pure leaf, or both at once.
    """
    root: dict[str, _TrieNode] = {}

    for tag in store.tag_tree():
        parts = tag_to_path_parts(tag)
        level = root
        node: _TrieNode | None = None
        for part in parts:
            node = level.setdefault(part, _TrieNode())
            level = node.children
        if node is not None:
            node.tag = tag

    sizes = store.get_tag_byte_sizes()

    def to_nodes(level: dict[str, _TrieNode]) -> list[TagNode]:
        nodes = []
        for label, node in level.items():
            tag = node.tag
            nodes.append(
                TagNode(
                    key=tag if tag is not None else label,
                    label=label,
                    children=to_nodes(node.children),
                    has_records=tag is not None,
                    record_kinds=_record_kinds(store, tag) if tag is not None else [],
                    size_bytes=sizes.get(tag, 0) if tag is not None else 0,
                )
            )
        # Two stable sorts: alphabetical first, then by category. The second sort's stability
        # preserves the alphabetical order within each category group.
        nodes.sort(key=lambda n: n.label.lower())
        nodes.sort(key=_category_rank)
        return nodes

    return to_nodes(root)
