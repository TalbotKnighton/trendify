#! /bin/bash

workdir=./workdir
input=$workdir/models/*/
output=$workdir/output/
generator=trendify.examples:example_data_product_generator
server_host=localhost
server_port=8001
n_procs=10

trendify_make_sample_data -wd $workdir -n 1000

trendify products-make -n $n_procs -g $generator -i $input
trendify products-sort -n $n_procs -i $input -o $output
# trendify assets-make-static $output

trendify assets-make-interactive grafana $output --host $server_host --port $server_port
trendify products-serve $output --host $server_host --port $server_port
