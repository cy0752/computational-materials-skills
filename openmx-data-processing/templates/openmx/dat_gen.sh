#!/bin/bash
set -euo pipefail

if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate "${OPENMX_CONDA_ENV:-OpenMX}"
else
    source /root/miniconda3/bin/activate "${OPENMX_CONDA_ENV:-OpenMX}"
fi

mkdir -p logs/datgen
python poscar2openmx.py --config "${POSCAR2OPENMX_CONFIG:-poscar2openmx.yaml}" \
    > logs/datgen/datgen.out 2>&1
