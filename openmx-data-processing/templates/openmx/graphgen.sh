#!/bin/bash
set -euo pipefail

# Runtime contract (machine-specific, supplied by the caller):
# - PYTHONBIN: a Python interpreter where `DFT_interfaces` is importable and
#   torch/torch_geometric are available.
#   That is true when HamGNN is pip-installed, or when HAMGNN_ROOT points at a
#   HamGNN source checkout (exported onto PYTHONPATH below).
# - This skill does not assume any dedicated conda environment.

PYTHONBIN="${PYTHONBIN:-python}"
if [[ -n "${HAMGNN_ROOT:-}" ]]; then
    export PYTHONPATH="${HAMGNN_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
fi

mkdir -p logs/graphgen
"${PYTHONBIN}" -m DFT_interfaces.openmx.graph_data_gen \
    --config "${GRAPH_DATA_GEN_CONFIG:-graph_data_gen.yaml}" \
    > logs/graphgen/graphgen.out 2>&1
