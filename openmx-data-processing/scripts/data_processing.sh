#!/bin/bash
set -euo pipefail

usage() {
    echo "Usage: $0 --workdir DIR [--jobs N] [--omp-threads N]"
}

workdir=""
jobs=""
omp_threads=""
jobs_set=0
omp_threads_set=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workdir)
            workdir="$2"
            shift 2
            ;;
        --jobs)
            jobs="$2"
            jobs_set=1
            shift 2
            ;;
        --omp-threads)
            omp_threads="$2"
            omp_threads_set=1
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

if [[ -z "${workdir}" ]]; then
    echo "Missing required --workdir" >&2
    usage >&2
    exit 1
fi

if [[ ! -d "${workdir}" ]]; then
    echo "OpenMX workdir not found: ${workdir}" >&2
    exit 1
fi

cd "${workdir}"
run_args=()
if [[ "${jobs_set}" -eq 1 ]]; then
    run_args+=("${jobs}")
fi
if [[ "${omp_threads_set}" -eq 1 ]]; then
    if [[ "${jobs_set}" -eq 0 ]]; then
        run_args+=("")
    fi
    run_args+=("${omp_threads}")
fi
bash ./dat_gen.sh
bash ./run_openmx.sh "${run_args[@]}"
bash ./graphgen.sh
