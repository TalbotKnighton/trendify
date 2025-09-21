#! /bin/bash

export workdir=./sample_data
export input=$workdir/models
export output=$workdir/trendify
export generator=trendify.examples:example_data_product_generator
export server_host=localhost
export server_port=8001
export n_procs=1

rm -rf $output/products

trendify_make_sample_data -wd $workdir -n 10

find $input -name "data_product.json" -type f -delete

# trendify products-make -n $n_procs -g $generator -i $input
# trendify products-sort -n $n_procs -i $input -o $output
# # trendify assets-make-static $output

# trendify assets-make-interactive grafana $output --host $server_host --port $server_port
# trendify products-serve $output --host $server_host --port $server_port

trendify make static -i $input/**/results.csv -g $generator -n $n_procs -o $output -f data_product.json
trendify make dashboard -o $output