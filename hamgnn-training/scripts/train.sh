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

if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    if ! conda activate "${HAMGNN_CONDA_ENV:-HamGNN}" >/dev/null 2>&1; then
        echo "Warning: failed to activate '${HAMGNN_CONDA_ENV:-HamGNN}', falling back to 'base'." >&2
        conda activate base
    fi
else
    if ! source /root/miniconda3/bin/activate "${HAMGNN_CONDA_ENV:-HamGNN}" >/dev/null 2>&1; then
        echo "Warning: failed to activate '${HAMGNN_CONDA_ENV:-HamGNN}', falling back to 'base'." >&2
        source /root/miniconda3/bin/activate base
    fi
fi

cd "${workdir}"
HamGNN2.0 --config "${config}" > log.out 2>&1
