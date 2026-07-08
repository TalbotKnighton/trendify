"""
Top-level pipeline API: generate -> render -> include files, backed by one `RecordStore`
`.db` file per output directory. `TrendifyPipeline` is the single implementation both the
`trendify` CLI (`trendify.cli`) and direct Python callers use. The CLI is a thin
argument-parsing layer over this class, not a separate code path.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from trendify.base.record import RecordGenerator
from trendify.generator.generate import generate_records
from trendify.generator.render import render_assets
from trendify.progress import ProgressCallback

__all__ = ["TrendifyPipeline"]

logger = logging.getLogger(__name__)


class TrendifyPipeline(BaseModel):
    """
    Runs the trendify pipeline (generate -> render -> include files) against one output
    directory, backed by a single `RecordStore` `.db` file.
    """

    output_dir: Path
    """Directory the pipeline reads/writes under. Holds `trendify.db` (the `RecordStore`) and
    an `assets/` subdirectory (rendered CSVs/figures)."""

    n_procs: int = Field(default=1, ge=1)
    """Number of worker processes used by `generate`."""

    @property
    def db_path(self) -> Path:
        return self.output_dir / "trendify.db"

    @property
    def assets_dir(self) -> Path:
        return self.output_dir / "assets"

    def generate(
        self,
        record_generator: RecordGenerator,
        data_dirs: list[Path],
        on_progress: ProgressCallback | None = None,
    ) -> int:
        """
        Maps `record_generator` over `data_dirs`, writing records directly to this
        pipeline's `RecordStore`. See `trendify.generator.generate.generate_records`.

        Args:
            record_generator (RecordGenerator): callable mapped over `data_dirs`.
            data_dirs (list[Path]): directories to map `record_generator` over.
            on_progress (ProgressCallback | None): called once per directory finished, e.g.
                to report status from a containerized deployment back to an end user.

        Returns:
            (int): total number of records written

        """
        logger.info(
            f"Generating records for {len(data_dirs)} directory(ies) into {self.db_path} "
            f"({self.n_procs} worker process{'es' if self.n_procs > 1 else ''})"
        )
        total = generate_records(
            record_generator=record_generator,
            data_dirs=data_dirs,
            db_path=self.db_path,
            n_procs=self.n_procs,
            on_progress=on_progress,
        )
        logger.info(f"Generated {total} record(s)")
        return total

    def render(self, on_progress: ProgressCallback | None = None) -> None:
        """
        Renders CSV tables and matplotlib figures for every tag into `self.assets_dir`. See
        `trendify.generator.render.render_assets`.

        Args:
            on_progress (ProgressCallback | None): called once per tag finished, e.g. to
                report status from a containerized deployment back to an end user.

        """
        logger.info(
            f"Rendering assets from '{self.db_path}' into '{self.assets_dir}' "
            f"({self.n_procs} worker process{'es' if self.n_procs > 1 else ''})"
        )
        render_assets(
            self.db_path,
            self.assets_dir,
            n_procs=self.n_procs,
            on_progress=on_progress,
        )
        logger.info(f"Finished rendering assets into '{self.assets_dir}'")

    def run(
        self,
        record_generator: RecordGenerator,
        data_dirs: list[Path],
        on_progress: ProgressCallback | None = None,
    ) -> int:
        """
        Runs the full pipeline: generate, then render (unless all three asset kinds are
        suppressed).

        Args:
            record_generator (RecordGenerator): callable mapped over `data_dirs`.
            data_dirs (list[Path]): directories to map `record_generator` over.
            on_progress (ProgressCallback | None): called once per unit of work finished in
                *both* stages -- `ProgressEvent.stage` distinguishes "generate" from "render"
                for a single handler covering the whole run.

        Returns:
            (int): total number of records written by `generate`

        """
        logger.info(
            f"Running full pipeline (generate -> render) for '{self.output_dir}'"
        )

        total = self.generate(
            record_generator=record_generator,
            data_dirs=data_dirs,
            on_progress=on_progress,
        )

        self.render(on_progress=on_progress)

        logger.info(f"Finished full pipeline for '{self.output_dir}'")
        return total
