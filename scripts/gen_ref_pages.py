"""
Generate API reference pages in docs/reference/.

Run this script before building the docs site:

    python scripts/gen_ref_pages.py

The output is written to docs/reference/ and is consumed by zensical (or
mkdocs) via the ::: autodoc directives. The directory is gitignored; this
script must be run as part of the CI pipeline before zensical build.

Pages are generated automatically by walking src/trendify/: every
`foo/bar.py` becomes `reference/trendify/foo/bar.md` and every
`foo/__init__.py` becomes `reference/trendify/foo/index.md`, mirroring the
package layout. Packages whose __init__.py is empty (packaging markers for
non-Python assets, e.g. viewer/templates/static/) are skipped since there is
nothing to document.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
PACKAGE = "trendify"
DOCS_REF = ROOT / "docs" / "reference"


def iter_modules() -> list[tuple[str, Path]]:
    """Return (dotted identifier, output path relative to DOCS_REF) for every documentable module."""
    modules: list[tuple[str, Path]] = []

    for path in sorted((SRC / PACKAGE).rglob("*.py")):
        parts = list(path.relative_to(SRC).with_suffix("").parts)

        if parts[-1] == "__main__":
            continue

        if parts[-1] == "__init__":
            if not path.read_text(encoding="utf-8").strip():
                continue
            parts.pop()
            rel_path = Path(*parts, "index.md")
        else:
            rel_path = Path(*parts).with_suffix(".md")

        modules.append((".".join(parts), rel_path))

    return modules


def main() -> None:
    DOCS_REF.mkdir(parents=True, exist_ok=True)

    modules = iter_modules()
    for identifier, rel_path in modules:
        dest = DOCS_REF / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"::: {identifier}\n", encoding="utf-8")
        print(f"  {dest.relative_to(ROOT)}")

    print(f"\nWrote {len(modules)} pages to {DOCS_REF.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
