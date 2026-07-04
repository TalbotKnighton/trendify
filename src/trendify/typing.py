"""
Shared numeric array type aliases (`VecN`, `MatN`) used across `trendify.plotting`/
`trendify.styling` for fields like `Trace2D.x`/`Trace2D.y` and `HistogramStyle.bins`. Backed by
`numpydantic.NDArray` for runtime pydantic validation, with a plain `TypeAlias` swapped in under
`TYPE_CHECKING` so static type checkers see an ordinary array/list/tuple union instead of
`numpydantic`'s shape-annotated generic.
"""

from typing import TYPE_CHECKING, Annotated

import numpy as np
from numpydantic import NDArray, Shape

__all__ = ["MatN", "VecN"]

if TYPE_CHECKING:
    type _VecBase = np.ndarray | list[float | int] | tuple[float | int, ...]

    type VecN = _VecBase
    """An N-element numeric array of arbitrary length."""

    type MatN = _VecBase
    """An NxN numeric matrix of arbitrary length."""
else:
    VecN = Annotated[NDArray[Shape["*"], float | int], ...]  # type: ignore  # noqa: F722
    MatN = Annotated[NDArray[Shape["*, *"], float | int], ...]  # type: ignore  # noqa: F722
