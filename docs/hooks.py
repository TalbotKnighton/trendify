"""MkDocs hooks that generate documentation assets before each build."""

import csv
from pathlib import Path

import tabulate

_EXAMPLE_TABLES_DIR = Path(__file__).parent / "example_data" / "trendify" / "assets"


def on_pre_build(config: dict) -> None:
    """Regenerate example report tables so docs always reflect the current to_tables output."""
    for csv_path in _EXAMPLE_TABLES_DIR.rglob("*.csv"):
        _csv_to_md(csv_path)


def _csv_to_md(csv_path: Path) -> None:
    """Write a GitHub-flavored markdown table alongside a CSV file."""
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    md = tabulate.tabulate(rows, headers="keys", tablefmt="github")
    csv_path.with_suffix(".md").write_text(md + "\n")


on_pre_build({})
