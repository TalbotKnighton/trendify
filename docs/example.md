
# Example

An example is provided with the `trendify` package to demonstrate functionality.  The example commands below genereate sample data and run a pre-defined post-processor to produce and sort products as well as generating assets.

After pip installing `trendify`, open an terminal and run the following shell commands.

``` sh
workdir=./workdir
generator=trendify.examples:example_data_product_generator
trendify_make_sample_data -wd $workdir -n 10  
trendify make all -g $generator -i $workdir/models/*/ -o $workdir/trendify_output/ -n 10 --port 8000
```

See the source code and documentation of the methods used in this example:

- [trendify_make_sample_data][trendify.examples.make_example_data]
- [example_data_product_generator][trendify.examples.example_data_product_generator]

The static outputs should include the following image:

![Example Generated Static Asset](assets/static/trace_plot.jpg)
