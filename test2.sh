#! /bin/bash

workdir=./workdir
inputs=$workdir/models/*/
output=$workdir/output/
generator=trendipy.examples:example_data_product_generator
n_procs=1
server_port=8001

rm -r $workdir
trendipy_make_sample_data -wd $workdir -n 100

trendipy make static -g $generator -i $inputs -o $output -n $n_procs
# trendipy make grafana -g $generator -i $inputs -o $output -n $n_procs --port $server_port
# trendipy make all -g $generator -i $inputs -o $output -n $n_procs --port $server_port
