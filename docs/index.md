---
hide:
  - navigation
#   - toc
---
<style>
  .md-typeset h1,
  .md-content__button {
    display: none;
  }
  a.badge-link::after {
    content: none !important;
  }
</style>

<p align="center" class="splash">
    <img alt="Trendify" src="assets/logo_pink.svg" style="width: 100%">
</p>

# trendify: Efficient Plotting and Table Building

<p align="center">
  <a href="https://pypi.org/project/trendify/" class="badge-link">
    <img src="https://img.shields.io/pypi/v/trendify.svg?cacheSeconds=300" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/trendify/" class="badge-link">
    <img src="https://img.shields.io/pypi/pyversions/trendify.svg?cacheSeconds=86400" alt="Python versions">
  </a>
  <a href="https://github.com/talbotknighton/trendify/actions/workflows/publish.yml" class="badge-link">
    <img src="https://github.com/talbotknighton/trendify/actions/workflows/publish.yml/badge.svg?branch=main" alt="Tests & Release Status">
  </a>
  <a href="https://github.com/astral-sh/ruff" class="badge-link" style="text-decoration:none;">
    <img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff">
  </a>
  <a href="https://docs.pydantic.dev/latest/" class="badge-link">
    <img src="https://img.shields.io/badge/Pydantic-v2-FF43A1?logo=pydantic&logoColor=white" alt="Pydantic v2">
  </a>
  <a href="https://opensource.org/licenses/MIT" class="badge-link">
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
  </a>
  <a href="https://talbotknighton.github.io/trendify/" class="badge-link">
    <img src="https://img.shields.io/badge/docs-GitHub_Pages-blue.svg" alt="Documentation">
  </a>
</p>

---

## Installation

Install the package via your preferred manager:

=== "`uv`"

    ```bash linenums="0"
    uv add trendify
    ```

=== "`pip`"

    ```bash linenums="0"
    pip install trendify
    ```

---

## Core Features

- **Built to scale**: process thousands of runs without holding every run's data in memory at once. Throughput stays flat whether you have dozens of runs or tens of thousands.
- **Typed records, no migrations**: points, traces, tables, and histograms are validated [Pydantic](https://docs.pydantic.dev/latest/) models. Add your own record types anytime without writing a schema migration.
- **Parallelizable**: `trendify generate` can fan your processing function out across multiple CPU cores with `--n-procs`, with multiprocessing-safe logging that funnels every worker's output through a single queue.
- **Static assets or a live dashboard**: render tagged data straight to Matplotlib images and CSV tables with `trendify render`, or launch an interactive FastAPI dashboard with `trendify viewer` to browse tags, tables, and interactive plots in the browser.

---

## Why use `trendify`?

- **Scalable.** Throughput stays flat whether you're processing dozens of runs or tens of thousands.
- **Memory efficient.** Each run is processed once and cached on disk, nothing needs to stay open or held in memory for the whole sweep. This is critical for processing large amounts of data with less memory than is available when batch processing.
- **Flexible output.** Render static Matplotlib images and CSV tables for a report, or browse the same data interactively in a live dashboard.
