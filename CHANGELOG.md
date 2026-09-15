# Changelog

## Version 2.0.3 (2026-09-14)

- Added a changelog
- Patched dependency security vulnerabilities (`httpx2`, `httpcore2`, `tornado`)
- Removed unused MkDocs-only doc dependencies now that the docs build on Zensical

## Version 2.0.0 (2026-07-05)

### Core

- Now formally supporting Python 3.14
- Versioning is now controlled by `hatchling-vcs` (when a new tag "vX.Y.Z" is pushed to main the test+publish CI/CD automatically fires)
- Overhauled the pipeline for running and processing data products (now called records to reduce confusion)
    - Records are stored in a SQLite database with concurrent write protection for multiprocessing
        - Records are no longer serialized as JSON in the input directories
        - Records are no longer sorted and duplicated into a `data_products` folder
        - This change cut the storage required (and therefore runtime) more than in half
    - SQLite database allows for better tag indexing and the reduced file size greatly improves runtime
- Format2D now supports a new `renderer` with options currently `Raster` (for JPG (default), PNG, etc.) and `Vector` (SVG)
- Logger has been completely redone to use `Rich` logs and a rolling file backup
    - This includes a fix for concurrent logs being broken on Windows
- The CLI was completely rewritten using `typer` to allow for better scalability

### Asset Generator

- Scatter2D was added as another option (Trace2D can also now optionally have no line style)
- Histograms can now be plotted with Trace2D, Point2D, and Scatter2D (previously they could only have AxLine)
- Table maker now uses `polars` instead of `pandas`
- Overhauled the previous interactive dashboard tool to use the new DB and also rewrote it to work as a FastAPI app (removing `streamlit`)
    - The new dashboard is much more performant, user friendly, and now also include table views for `TableEntry` records
    - It also comes with light/dark/system theming and a proper toast/notification system

### Misc.

- Example data generator was updated to provide more "interesting" data (it is also now part of the `trendify` CLI namespace)
- The documentation site was transitioned to Zensical and branding was updated across the package
    - User guide was rewritten to summarize how to use `trendify` and now include examples of the assets it produces
    - The README/index was updated to match one another
    - This also updated the CI/CD
- Pyright and Ruff are now part of the pre-commit to improve code quality
- Improved `__init__.py` to match [PEP 8](https://peps.python.org/pep-0008/#imports)
- Added a bunch of unit tests

### Broke

- Format2D is now its own tagged Record (no longer an attribute of Trace2D, Point2D, etc.)
   - This also removed the slow, and seldom used, union step that would be performed on every Format2D for every run
   - Breaking this greatly reduces the DB size, especially since it usually just stored redundant information
- Trace2D.from_xy was removed since Point2D was removed from it (Trace2D now instantiated the same way as all other types)
- Trace2D was optimized to remove the ability to set a different style for each Point2D (which actually was never even possible but this includes a schema change)
- `trendify_make_sample_data` CLI exe moved to `trendify` (see Misc change)
- Python 3.11 no longer supported due to old generic typing system

## v1.2.11 (2025-09-23)

- Added `figure_size` (width and height) support to `Format2D` (#30)

## v1.2.7 (2025-09-23)

- Fixed nested quotes breaking generated histogram files
- Fixed the logo and favicon
- Added `zorder` control for Plotly traces/markers/histograms and Matplotlib histograms/legends
- Fixed log-scaled plots not displaying correctly in Plotly

## v1.2.6 (2025-09-21)

- Changed plot title behavior
- Added a tooltip selector and improved tooltip button UX
- Added opacity/alpha support for traces, markers, and Plotly histogram edges
- Fixed tooltip text color not adapting to the line color, making it unreadable in some cases (#25)
- Dashboard tag keys are now sorted for easier browsing

## v1.2.5 (2025-09-21)

- Now requires Python >= 3.11
- Fixed dashboard pushbuttons using the full tag name instead of a shorter key (#17)
- Fixed `trendify make dashboard` not treating the given path as a raw string (#18)
- Fixed the table builder, which was broken (#19)

## v1.2.0 (2025-09-18)

- Added a Streamlit dashboard, reusing the existing `dashboard` CLI argument to launch it
- Added pushbutton controls for selecting a chart within nested expanders
- Fixed the documentation site build
- Adjusted logging levels

## v1.1.16 (2025-09-10)

- Updated documentation and fixed an indexing bug

## v1.1.15 (2025-09-10)

- Data products now record their source file in metadata

## v1.1.14 (2025-09-10)

- Sorting now overwrites existing products for a given source directory instead of duplicating them

## v1.1.6 (2025-08-02)

- Added a `Legend` object for customizing legend location and styling
- Added log-scale support for the x and y axes

## v1.1.1 (2025-07-28)

- Added configurable logging with multiple verbosity levels
- Grid styling now uses the `Pen` object instead of one-off custom settings
- Added a tuple option for line style
- Added noise to the example data generator for more realistic sample output
- `XYDataPlot` can now be plotted together with histograms
- Fixed histogram bins with no values still showing their edges, making empty bins look populated
- Improved the auto-dashboard tool, including working Plotly support
- Added support for multiple tags, plus a product gallery view
- Fixed mean and max being swapped in the stats table
- Added the ability to specify the data products JSON filename
