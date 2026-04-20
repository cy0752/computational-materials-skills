#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 [--workdir DIR] [--config FILE] [--input-glob GLOB] [--output-root DIR] [--system-name NAME] [--overwrite] [--dry-run]"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ABACUS_CONDA_ENV="${ABACUS_CONDA_ENV:-OpenMX}"
PYTHON_BIN="${PYTHON_BIN:-python}"

workdir=""
config=""
input_glob=""
output_root=""
system_name=""
overwrite=0
dry_run=0

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
        --input-glob)
            input_glob="$2"
            shift 2
            ;;
        --output-root)
            output_root="$2"
            shift 2
            ;;
        --system-name)
            system_name="$2"
            shift 2
            ;;
        --overwrite)
            overwrite=1
            shift
            ;;
        --dry-run)
            dry_run=1
            shift
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

if [[ -n "${workdir}" ]]; then
    if [[ ! -d "${workdir}" ]]; then
        echo "Workdir not found: ${workdir}" >&2
        exit 1
    fi
    cd "${workdir}"
fi

if [[ -z "${config}" ]]; then
    if [[ -f "abacus_input_gen.yaml" ]]; then
        config="abacus_input_gen.yaml"
    fi
fi

if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    # Use a stage-matched env first, then fall back to base.
    source /root/miniconda3/etc/profile.d/conda.sh
    if ! conda activate "${ABACUS_CONDA_ENV}" >/dev/null 2>&1; then
        echo "Warning: failed to activate '${ABACUS_CONDA_ENV}', falling back to 'base'." >&2
        conda activate base
    fi
elif [ -f "/root/miniconda3/bin/activate" ]; then
    if ! source /root/miniconda3/bin/activate "${ABACUS_CONDA_ENV}" >/dev/null 2>&1; then
        echo "Warning: failed to activate '${ABACUS_CONDA_ENV}', falling back to 'base'." >&2
        source /root/miniconda3/bin/activate base
    fi
fi

mkdir -p logs
log_file="logs/abacus_input_gen.log"

cmd=("${PYTHON_BIN}" "${SCRIPT_DIR}/poscar2abacus.py")
if [[ -n "${config}" ]]; then
    cmd+=(--config "${config}")
fi
if [[ -n "${input_glob}" ]]; then
    cmd+=(--input-glob "${input_glob}")
fi
if [[ -n "${output_root}" ]]; then
    cmd+=(--output-root "${output_root}")
fi
if [[ -n "${system_name}" ]]; then
    cmd+=(--system-name "${system_name}")
fi
if [[ "${overwrite}" -eq 1 ]]; then
    cmd+=(--overwrite)
fi
if [[ "${dry_run}" -eq 1 ]]; then
    cmd+=(--dry-run)
fi

if ! "${cmd[@]}" >"${log_file}" 2>&1; then
    echo "ABACUS input generation failed. See log: ${log_file}" >&2
    exit 1
fi

echo "ABACUS input generation complete. Log: ${log_file}"
