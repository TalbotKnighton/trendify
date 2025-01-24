#! /bin/bash

workdir=./workdir
input=$workdir/models/*/
output=$workdir/output/
generator=trendipy.examples:example_data_product_generator
server_host=localhost
server_port=8001
n_procs=10

trendipy_make_sample_data -wd $workdir -n 1000

trendipy products-make -n $n_procs -g $generator -i $input
trendipy products-sort -n $n_procs -i $input -o $output
# trendipy assets-make-static $output

trendipy assets-make-interactive grafana $output --host $server_host --port $server_port
trendipy products-serve $output --host $server_host --port $server_port
