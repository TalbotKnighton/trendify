---
hide:
  - navigation
---

# Motivation

This page explains the motivation for the Trendify package in hopes that the reader will better understand what benefit it provides, how to use it, and what features to expect in the future.

## Problem Statement

Data is commonly conveyed through visual assets such as:

- Drawings
- __Graphs__
- __Tables__

Graphs and Tables are intended to present data in a digestible way.

It is easy to write complicted data manipulations for preparing data using a high level language such as Python, but there are several pitfalls when distilling large amounts of data:

1. Computational expense (long processing times)
2. Limited RAM

As discussed below, Trendify provides a scalable framework for quickly distilling graphs and tables from large amounts of data.

### Illustrative Problem Statement

The following bullets provide an illustrative common use case.  Suppose that

- An engineering model has been run through a Monte Carlo simulation for a large number of runs.
- The output data from each run needs to be processed to evaluate target criteria.
- The collected output data from all runs is significant (possibly larger than the available RAM on a device).
- The computational expense of post-processing each run is significant (for example, data needs to be rotated, transformed, smoothed, etc. in expensive ways).

### Brute Force Approaches

#### Nested For Loops, Low Memory Cost

One way to process the data is to perform the following tasks sequentially:

- Loop over figures to be created
- Open a [`matplotlib Figure`][matplotlib.figure.Figure]
- Sequentially loop over each output directory
- Process the data to provide the required information
- Plot to the open [`matplotlib Figure`][matplotlib.figure.Figure]
- Save the [`matplotlib Figure`][matplotlib.figure.Figure]
- Repeat the above steps for a new figure.

This approach prevents a memory overload since only one batch run is loaded and processed at a time.  However, this approach is often unacceptably slow since the same data needs to be loaded over and over for each figure or table to be created.

#### Single For Loop, High Memory Cost

A variation is to open multiple [`matplotlib Figure`][matplotlib.figure.Figure] instances at the same time (eliminateing the outer for loop).  This approach avoids having to redundantly load/process data since the processed results can be added to every relevant figure/table.  But, this can lead to a memory overload if many images and tables are being generated.

### Trendify Approach

Trendify uses multiple concepts to avoid the memory and computation pitfals of brute-force loops.

#### Serialization/Deserialization

JSON serialization is the act of saving Python objects to plain text using the JSON file format.

JSON deserialization is the reverse process of creating Python objects by loading plain text from a JSON file.

The [`Pydantic`](https://docs.pydantic.dev/latest/) package provides an integrated framework for serialization/deserialization in Python.
In the [`Pydantic`](https://docs.pydantic.dev/latest/) framework, type hints serve a double purpose:

- Tells what type of data is expected in each variable (helps with linting hits and auto-completion in IDE)
- Data validation (pydantic closes program if JSON data does not match type hint)

Trendify defines [`Pydantic`](https://docs.pydantic.dev/latest/) data classes to store 2D traces, table entries, etc. and load them back into memory as needed.
Loading distilled data from a JSON file is orders of magnitude faster than loading and processing raw data.
Serialization/deserialization eliminates the need to hold large amounts of data in memory in order to generate assets.
This allows Trendify to decouple the raw data processing stage from the aggregation stage of generating figures and tables by saving the intermediate data products as JSON files.

#### Parallelization

Trendify uses parallel processing to utilize all available machine cores (up to a user specified value) when processing batch data.
This provides a scalable linear speedup based on the number of cores.

#### Data Products

At the moment, Trendify is written to accomodate only a few specific types of data products (distilled data to be aggregated into assets).  These include Trace2D, TableEntry, HistogramEntry, etc.  Trendify can be expanded in the future to allow any arbitrary data type and aggregation step.

#### Data Product Generators

Functions are "first-class citizens" of Python, meaning that they can be passed into other functions as arguments.  This allows function composition such as shown in the following example:

```python
def apply_binary_function(some_binary_function, argument_1, argument_2):
    return some_binary_function(argument_1, argument_2)

def add(a, b):
    return a + b

result = apply_some_binary_function(add, 1, 1)  # The `add` function is passed as an argument to `apply_binary_function`
print(result)  # Prints `2`
```

Trendify provides a framework for applying any user-defined processing function to a set of working directories.
Thus, the end-user only needs to define what processing they want to do as a function (with a pre-determined signature) and pass that function to the Trendify framework via the command line or Python script.

#### Command Line Interface

The `trendify` command line interface allows users to map a data product generator from a Python source file or an installed Python package as discussed in the [recipe][recipe] and the [CLI docs][cli].  In a terminal (with the Python environment to which `trendify` is installed active) run the the command `trendify --help` for more info.