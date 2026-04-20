#!/bin/bash
set -euo pipefail

if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate "${OPENMX_CONDA_ENV:-OpenMX}"
else
    source /root/miniconda3/bin/activate "${OPENMX_CONDA_ENV:-OpenMX}"
fi

mkdir -p logs/graphgen
python graph_data_gen.py --config "${GRAPH_DATA_GEN_CONFIG:-graph_data_gen.yaml}" \
    > logs/graphgen/graphgen.out 2>&1
