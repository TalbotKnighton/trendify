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
from trendify.store.product_store import ProductStore
from trendify.store.tags import tag_to_path_parts

__all__ = ["TagNode", "build_tag_tree"]

logger = logging.getLogger(__name__)


class TagNode(BaseModel):
    key: Tag
    label: str
    children: list[TagNode]
    has_products: bool
    product_kinds: list[Literal["plot", "table"]]

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
        Union of this node's own `product_kinds` and every descendant's, so a folder can be
        filtered by product type without needing to walk the tree again client-side (a folder
        should stay visible under a "table" filter if any product anywhere inside it is a
        table, even if the folder itself has no products of its own).
        """
        kinds = set(self.product_kinds)
        for child in self.children:
            kinds.update(child.subtree_kinds())
        return sorted(kinds)

    def product_count(self) -> int:
        """
        Recursive count of self-and-descendant nodes with `has_products`, shown as a
        subtle badge next to folder labels in the sidebar.
        """
        count = 1 if self.has_products else 0
        for child in self.children:
            count += child.product_count()
        return count


class _TrieNode:
    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.tag: Tag | None = None


def _product_kinds(store: ProductStore, tag: Tag) -> list[Literal["plot", "table"]]:
    kinds: list[Literal["plot", "table"]] = []
    if store.get_products_of_type(PlottableData2D, tag=tag):
        kinds.append("plot")
    if store.get_table_entries(tag).height > 0:
        kinds.append("table")
    return kinds


def _category_rank(node: TagNode) -> int:
    """Folders sort before plot leaves, which sort before table leaves."""
    if node.children:
        return 0
    if "plot" in node.product_kinds:
        return 1
    if "table" in node.product_kinds:
        return 2
    return 3


def build_tag_tree(store: ProductStore) -> list[TagNode]:
    """
    Walks `store.tag_tree()`'s flat, tuple-encoded tags into a nested `TagNode` hierarchy: a
    tag `("a", "b")` becomes a folder `"a"` containing a leaf `"b"`. A tuple prefix (e.g. `"a"`
    from that same tag) may never itself have been used as a real tag, so `has_products` is
    tracked separately from `children` being non-empty -- a node can be a pure folder, a pure
    leaf, or both at once.
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

    def to_nodes(level: dict[str, _TrieNode]) -> list[TagNode]:
        nodes = []
        for label, node in level.items():
            tag = node.tag
            nodes.append(
                TagNode(
                    key=tag if tag is not None else label,
                    label=label,
                    children=to_nodes(node.children),
                    has_products=tag is not None,
                    product_kinds=_product_kinds(store, tag) if tag is not None else [],
                )
            )
        # Two stable sorts: alphabetical first, then by category -- the second sort's stability
        # preserves the alphabetical order within each category group.
        nodes.sort(key=lambda n: n.label.lower())
        nodes.sort(key=_category_rank)
        return nodes

    return to_nodes(root)
