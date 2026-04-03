#!/bin/bash
set -euo pipefail

activate_conda_env() {
    local env_name="$1"
    local conda_base="${CONDA_BASE:-}"
    local conda_sh=""

    if [[ -n "${conda_base}" ]] && [[ -f "${conda_base}/etc/profile.d/conda.sh" ]]; then
        conda_sh="${conda_base}/etc/profile.d/conda.sh"
    elif command -v conda >/dev/null 2>&1; then
        conda_base="$(conda info --base 2>/dev/null || true)"
        if [[ -n "${conda_base}" ]] && [[ -f "${conda_base}/etc/profile.d/conda.sh" ]]; then
            conda_sh="${conda_base}/etc/profile.d/conda.sh"
        fi
    fi

    if [[ -z "${conda_sh}" ]]; then
        echo "Error: unable to locate conda.sh. Set CONDA_BASE to your conda installation root." >&2
        exit 1
    fi

    # shellcheck disable=SC1090
    source "${conda_sh}"
    conda activate "${env_name}"
}

activate_conda_env "${OPENMX_CONDA_ENV:-OpenMX}"

mkdir -p logs/datgen
python poscar2openmx.py --config "${POSCAR2OPENMX_CONFIG:-poscar2openmx.yaml}" \
    > logs/datgen/datgen.out 2>&1
