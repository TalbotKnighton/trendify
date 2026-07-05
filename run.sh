set -e

# rm -rf scripts/example_data/trendify

# trendify run \
#     -i "scripts/example_data/models/*" \
#     -g scripts/matrix_generator.py:build_configuration_matrix \
#     -o scripts/example_data/trendify \
#     -n 4

trendify serve \
    scripts/example_data/trendify/trendify.db \
    --host 0.0.0.0 \
    --port 8084
