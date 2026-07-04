"""
Top-level pipeline API: generate -> render -> include files, backed by one `ProductStore`
`.db` file per output directory. `TrendifyPipeline` is the single implementation both the
`trendify` CLI (`trendify.cli`) and direct Python callers use. The CLI is a thin
argument-parsing layer over this class, not a separate code path.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel, Field

from trendify.base.data_product import ProductGenerator
from trendify.generator.generate import generate_products
from trendify.generator.render import render_assets
from trendify.store.product_store import ProductStore

__all__ = ["TrendifyPipeline"]

logger = logging.getLogger(__name__)


class TrendifyPipeline(BaseModel):
    """
    Runs the trendify pipeline (generate -> render -> include files) against one output
    directory, backed by a single `ProductStore` `.db` file.

    Args:
        output_dir (Path): directory the pipeline reads/writes under. Holds `trendify.db`
            (the `ProductStore`) and an `assets/` subdirectory (rendered CSVs/figures).
        n_procs (int): number of worker processes used by `generate`.

    """

    output_dir: Path
    n_procs: int = Field(default=1, ge=1)

    @property
    def db_path(self) -> Path:
        return self.output_dir / "trendify.db"

    @property
    def assets_dir(self) -> Path:
        return self.output_dir / "assets"

    def generate(
        self,
        product_generator: ProductGenerator,
        data_dirs: list[Path],
    ) -> int:
        """
        Maps `product_generator` over `data_dirs`, writing products directly to this
        pipeline's `ProductStore`. See `trendify.generator.generate.generate_products`.

        Returns:
            (int): total number of products written

        """
        logger.info(
            f"Generating products for {len(data_dirs)} directory(ies) into {self.db_path} "
            f"({self.n_procs} worker process{'es' if self.n_procs > 1 else ''})"
        )
        total = generate_products(
            product_generator=product_generator,
            data_dirs=data_dirs,
            db_path=self.db_path,
            n_procs=self.n_procs,
        )
        logger.info(f"Generated {total} product(s)")
        return total

    def render(
        self,
        dpi: int = 500,
        no_tables: bool = False,
        no_xy_plots: bool = False,
        no_histograms: bool = False,
    ) -> None:
        """
        Renders CSV tables and matplotlib figures for every tag into `self.assets_dir`. See
        `trendify.generator.render.render_assets`.

        """
        logger.info(f"Rendering assets from {self.db_path} into {self.assets_dir}")
        with ProductStore.open(self.db_path, readonly=True) as store:
            render_assets(
                store,
                self.assets_dir,
                dpi=dpi,
                no_tables=no_tables,
                no_xy_plots=no_xy_plots,
                no_histograms=no_histograms,
            )
        logger.info(f"Finished rendering assets into {self.assets_dir}")

    def run(
        self,
        product_generator: ProductGenerator,
        data_dirs: list[Path],
        dpi: int = 500,
        no_tables: bool = False,
        no_xy_plots: bool = False,
        no_histograms: bool = False,
    ) -> int:
        """
        Runs the full pipeline: generate, then render (unless all three asset kinds are
        suppressed).

        Returns:
            (int): total number of products written by `generate`

        """
        logger.info(f"Running full pipeline (generate -> render) for {self.output_dir}")
        total = self.generate(product_generator=product_generator, data_dirs=data_dirs)

        no_assets = no_tables and no_xy_plots and no_histograms
        if not no_assets:
            self.render(
                dpi=dpi,
                no_tables=no_tables,
                no_xy_plots=no_xy_plots,
                no_histograms=no_histograms,
            )

        logger.info(f"Finished full pipeline for {self.output_dir}")
        return total
