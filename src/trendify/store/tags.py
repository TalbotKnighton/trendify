"""
Canonical encoding between the pydantic-facing `Tag` type and the `tag_key` string
stored/indexed in the `record_tags` and `table_entries` SQL tables.

The same `encode_tag` function must be used at write time and query time so lookups are
exact-match index seeks.
"""

from __future__ import annotations

import json

from trendify.base.helpers import Tag

__all__ = ["decode_tag", "encode_tag", "tag_to_path_parts"]


def encode_tag(tag: Tag) -> str:
    """
    Canonicalizes a `Tag` (`str`, `int`, or `tuple[str | int, ...]`) into the `tag_key` string
    used for indexed storage/lookup. Scalars and tuples produce distinguishable encodings
    (`json.dumps` renders a tuple as a JSON array), so `"foo"` and `("foo",)` never collide.

    Args:
        tag (Tag): tag to encode

    Returns:
        (str): canonical, indexable string key

    """
    return json.dumps(tag, separators=(",", ":"))


def decode_tag(tag_key: str) -> Tag:
    """
    Inverse of `encode_tag`. JSON arrays decode back to `tuple`s (the `Tag` type never uses
    plain `list`s) so round-tripping a tag through the store reproduces the original shape.

    Args:
        tag_key (str): canonical string key, as produced by `encode_tag`

    Returns:
        (Tag): decoded tag

    """
    decoded = json.loads(tag_key)
    if isinstance(decoded, list):
        return tuple(decoded)
    return decoded


def tag_to_path_parts(tag: Tag) -> tuple[str, ...]:
    """
    Converts a `Tag` into output-path parts: a tuple tag `("a", "b")` becomes nested path
    segments `("a", "b")`, and a scalar tag `"a"` becomes a single segment `("a",)`.

    Args:
        tag (Tag): tag to convert

    Returns:
        (tuple[str, ...]): path parts, last one being the file stem

    """
    parts = tag if isinstance(tag, tuple) else (tag,)
    return tuple(str(p) for p in parts)
