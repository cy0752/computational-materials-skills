#!/bin/bash
set -euo pipefail

# Runtime contract (machine-specific, supplied by the caller):
# - PYTHONBIN: a Python interpreter where `DFT_interfaces` is importable.
#   That is true when HamGNN is pip-installed, or when HAMGNN_ROOT points at a
#   HamGNN source checkout (exported onto PYTHONPATH below).
# - This skill does not assume any dedicated conda environment.

PYTHONBIN="${PYTHONBIN:-python}"
if [[ -n "${HAMGNN_ROOT:-}" ]]; then
    export PYTHONPATH="${HAMGNN_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
fi

mkdir -p logs/datgen
"${PYTHONBIN}" -m DFT_interfaces.openmx.poscar2openmx \
    --config "${POSCAR2OPENMX_CONFIG:-poscar2openmx.yaml}" \
    > logs/datgen/datgen.out 2>&1
