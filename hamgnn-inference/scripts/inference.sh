#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 --workdir DIR --config FILE"
}

workdir=""
config=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workdir)
            workdir="$2"
            shift 2
            ;;
        --config)
            config="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [[ -z "${workdir}" || -z "${config}" ]]; then
    echo "Both --workdir and --config are required." >&2
    usage >&2
    exit 1
fi

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

activate_conda_env "${HAMGNN_CONDA_ENV:-HamGNN}"

cd "${workdir}"
HamGNN2.0 --config "${config}" > inference.log 2>&1
