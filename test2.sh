#! /bin/bash

workdir=./workdir
inputs=$workdir/models/*/
output=$workdir/output/
generator=trendify.examples:example_data_product_generator
n_procs=1
server_port=8001

rm -r $workdir
trendify_make_sample_data -wd $workdir -n 100

trendify make static -g $generator -i $inputs -o $output -n $n_procs
# trendify make grafana -g $generator -i $inputs -o $output -n $n_procs --port $server_port
# trendify make all -g $generator -i $inputs -o $output -n $n_procs --port $server_port
