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

# Runtime contract: the HamGNN conda installation is located portably --
# CONDA_BASE takes precedence, then `conda` on PATH. No machine-specific
# conda path is assumed. Env name comes from HAMGNN_CONDA_ENV (default
# HamGNN); if it is unavailable, fall back to 'base'.
conda_sh=""
if [[ -n "${CONDA_BASE:-}" && -f "${CONDA_BASE}/etc/profile.d/conda.sh" ]]; then
    conda_sh="${CONDA_BASE}/etc/profile.d/conda.sh"
elif command -v conda >/dev/null 2>&1; then
    conda_base="$(conda info --base 2>/dev/null || true)"
    if [[ -n "${conda_base}" && -f "${conda_base}/etc/profile.d/conda.sh" ]]; then
        conda_sh="${conda_base}/etc/profile.d/conda.sh"
    fi
fi

if [[ -n "${conda_sh}" ]]; then
    # shellcheck disable=SC1090
    source "${conda_sh}"
    if ! conda activate "${HAMGNN_CONDA_ENV:-HamGNN}" >/dev/null 2>&1; then
        echo "Warning: failed to activate '${HAMGNN_CONDA_ENV:-HamGNN}', falling back to 'base'." >&2
        conda activate base
    fi
else
    echo "Warning: conda not found (set CONDA_BASE or put conda on PATH); using the current PATH Python." >&2
fi

cd "${workdir}"
HamGNN2.0 --config "${config}" > inference.log 2>&1
