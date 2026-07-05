#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workdir="$SCRIPT_DIR/example_data"

rm -f "$workdir/trendify/trendify.db*"

trendify example-data -w "$workdir" -n 20

trendify run \
    -i "$workdir/models/*" \
    -g "$SCRIPT_DIR/example_generator.py:generate_records" \
    -o "$workdir/trendify" \
    -n 4

python "$SCRIPT_DIR/hooks.py"
python "$SCRIPT_DIR/../scripts/gen_ref_pages.py"
