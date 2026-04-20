#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_NAME="${SYSTEM_NAME:-__SYSTEM_NAME__}"
INPUT_ROOT="${INPUT_ROOT:-__ABACUS_INPUT_ROOT__}"
DATASET_ROOT="${DATASET_ROOT:-__ABACUS_DATASET_ROOT__}"
ABACUS_BIN="${ABACUS_BIN:-abacus}"
ABACUS_CMD="${ABACUS_CMD:-${ABACUS_BIN}}"
PARALLEL_BIN="${PARALLEL_BIN:-parallel}"
TASKSET_BIN="${TASKSET_BIN:-taskset}"
ABACUS_CONDA_ENV="${ABACUS_CONDA_ENV:-abacus_env}"
ABACUS_OVERWRITE_WORKDIR="${ABACUS_OVERWRITE_WORKDIR:-1}"
DEFAULT_OMP_THREADS=2
DEFAULT_ABACUS_TASKS=16
DEFAULT_ABACUS_CPUS_PER_TASK=2

LOG_DIR="${SCRIPT_DIR}/logs"
RUN_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/run_abacus_${RUN_TIMESTAMP}.log"
PARALLEL_JOBLOG="${LOG_DIR}/parallel_job_${RUN_TIMESTAMP}.log"
PROGRESS_DIR="${LOG_DIR}/progress_${RUN_TIMESTAMP}"
CASE_LIST_FILE="${LOG_DIR}/case_list_${RUN_TIMESTAMP}.txt"
mkdir -p "${LOG_DIR}" "${PROGRESS_DIR}" "${DATASET_ROOT}"
exec > >(tee -a "${LOG_FILE}") 2>&1

conda_activated=0
if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    if conda activate "${ABACUS_CONDA_ENV}" >/dev/null 2>&1; then
        conda_activated=1
    fi
elif [ -f "/root/miniconda3/bin/activate" ]; then
    if source /root/miniconda3/bin/activate "${ABACUS_CONDA_ENV}" >/dev/null 2>&1; then
        conda_activated=1
    fi
fi

if [[ "${conda_activated}" != "1" ]]; then
    echo "Warning: failed to activate conda environment '${ABACUS_CONDA_ENV}'. Continuing with current shell environment."
fi

if [[ "${ABACUS_CMD}" == "${ABACUS_BIN}" ]] && ! command -v "${ABACUS_BIN}" >/dev/null 2>&1; then
    echo "Error: ABACUS binary not found: ${ABACUS_BIN}" >&2
    echo "Set ABACUS_BIN to an executable path, or set ABACUS_CMD to a full launcher command." >&2
    exit 1
fi

set +u
source /opt/intel/oneapi/setvars.sh >/dev/null 2>&1 || true
set -u
ulimit -s unlimited
export OMP_PROC_BIND="${OMP_PROC_BIND:-close}"
export OMP_PLACES="${OMP_PLACES:-cores}"

expand_cpu_list() {
    local cpu_spec="$1"
    local result=()
    local part start end cpu
    IFS=',' read -ra parts <<< "${cpu_spec}"
    for part in "${parts[@]}"; do
        if [[ "${part}" == *-* ]]; then
            start="${part%-*}"
            end="${part#*-}"
            for ((cpu=start; cpu<=end; cpu++)); do
                result+=("${cpu}")
            done
        elif [[ -n "${part}" ]]; then
            result+=("${part}")
        fi
    done
    printf '%s\n' "${result[@]}"
}

detect_total_cpus() {
    if [[ -n "${ABACUS_TOTAL_CPUS:-}" ]] && [[ "${ABACUS_TOTAL_CPUS}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="abacus_total_cpus_env"
        DETECTED_TOTAL_CPUS="${ABACUS_TOTAL_CPUS}"
        return 0
    fi

    if [[ -n "${ABACUS_TASKS:-}" && -n "${ABACUS_CPUS_PER_TASK:-}" ]] \
        && [[ "${ABACUS_TASKS}" =~ ^[1-9][0-9]*$ ]] \
        && [[ "${ABACUS_CPUS_PER_TASK}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="abacus_tasks_x_cpus_per_task_env"
        DETECTED_TOTAL_CPUS="$((ABACUS_TASKS * ABACUS_CPUS_PER_TASK))"
        return 0
    fi

    if [[ -n "${SLURM_NTASKS:-}" && -n "${SLURM_CPUS_PER_TASK:-}" ]] \
        && [[ "${SLURM_NTASKS}" =~ ^[1-9][0-9]*$ ]] \
        && [[ "${SLURM_CPUS_PER_TASK}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="slurm_ntasks_x_cpus_per_task"
        DETECTED_TOTAL_CPUS="$((SLURM_NTASKS * SLURM_CPUS_PER_TASK))"
        return 0
    fi

    if [[ -n "${SLURM_CPUS_ON_NODE:-}" && "${SLURM_CPUS_ON_NODE}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="slurm_cpus_on_node"
        DETECTED_TOTAL_CPUS="${SLURM_CPUS_ON_NODE}"
        return 0
    fi

    TOTAL_CPUS_SOURCE="abacus_default_profile"
    DETECTED_TOTAL_CPUS="$((DEFAULT_ABACUS_TASKS * DEFAULT_ABACUS_CPUS_PER_TASK))"
    return 0
}

select_cpu_slice() {
    local slot_index="$1"
    local width="$2"
    local allowed_spec start
    allowed_spec="$(awk '/Cpus_allowed_list/ {print $2}' /proc/self/status)"
    mapfile -t allowed_cpus < <(expand_cpu_list "${allowed_spec}")
    start=$(( (slot_index - 1) * width ))
    if (( start + width > ${#allowed_cpus[@]} )); then
        return 1
    fi
    printf '%s,' "${allowed_cpus[@]:start:width}" | sed 's/,$//'
}

run_single_calculation() {
    local data_id="$1"
    local slot_index="$2"
    local input_case_dir="${INPUT_ROOT}/${data_id}"
    local work_dir="${DATASET_ROOT}/${data_id}"
    local std_file="${SYSTEM_NAME}.std"
    local debug_log="${work_dir}/debug_progress.log"
    local cpu_binding=""

    if [[ ! -f "${input_case_dir}/INPUT" || ! -f "${input_case_dir}/STRU" || ! -f "${input_case_dir}/KPT" ]]; then
        echo "ERROR: Missing INPUT/STRU/KPT in ${input_case_dir}" >&2
        return 1
    fi

    mkdir -p "${work_dir}"
    if [[ "${ABACUS_OVERWRITE_WORKDIR}" == "1" ]]; then
        find "${work_dir}" -mindepth 1 -delete
    elif find "${work_dir}" -mindepth 1 -print -quit | grep -q .; then
        echo "ERROR: Work dir is not empty: ${work_dir}. Set ABACUS_OVERWRITE_WORKDIR=1 to overwrite." >&2
        return 1
    fi

    cp -a "${input_case_dir}/." "${work_dir}/"
    echo "$(date): [START] ${data_id}" > "${debug_log}"
    cd "${work_dir}" || { echo "ERROR: Failed to cd into ${work_dir}." >> "${debug_log}"; return 1; }

    if command -v "${TASKSET_BIN}" >/dev/null 2>&1 && cpu_binding="$(select_cpu_slice "${slot_index}" "${omp_threads}")"; then
        echo "$(date): [BIND] slot=${slot_index} cpus=${cpu_binding}" >> "${debug_log}"
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} ${TASKSET_BIN} -c ${cpu_binding} bash -lc '${ABACUS_CMD}'" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" "${TASKSET_BIN}" -c "${cpu_binding}" bash -lc "${ABACUS_CMD}" > "${std_file}" 2>&1
    else
        echo "$(date): [BIND] slot=${slot_index} unbound" >> "${debug_log}"
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} bash -lc '${ABACUS_CMD}'" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" bash -lc "${ABACUS_CMD}" > "${std_file}" 2>&1
    fi
    echo "$(date): [POST-EXEC] ABACUS exit status: $?" >> "${debug_log}"

    touch "${PROGRESS_DIR}/${data_id}.done"
    local completed_count
    completed_count=$(find "${PROGRESS_DIR}" -maxdepth 1 -type f -name '*.done' | wc -l)
    printf '[%s] Completed %s/%s: %s\n' "$(date '+%F %T')" "${completed_count}" "${TOTAL_TASKS}" "${data_id}"
}

export -f run_single_calculation
export -f expand_cpu_list select_cpu_slice
export SYSTEM_NAME INPUT_ROOT DATASET_ROOT ABACUS_CMD PROGRESS_DIR TOTAL_TASKS TASKSET_BIN ABACUS_OVERWRITE_WORKDIR

jobs_arg="${1:-${ABACUS_JOBS:-}}"
omp_threads="${2:-${ABACUS_OMP_THREADS:-$DEFAULT_OMP_THREADS}}"

if ! [[ "${omp_threads}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: omp_threads must be a positive integer."
    echo "Usage: bash $(basename "$0") [jobs] [omp_threads]"
    exit 1
fi
export omp_threads

if [[ "${INPUT_ROOT}" == *"__ABACUS_INPUT_ROOT__"* || "${DATASET_ROOT}" == *"__ABACUS_DATASET_ROOT__"* ]]; then
    echo "Error: run_abacus.sh placeholders are not rendered (INPUT_ROOT/DATASET_ROOT)." >&2
    exit 1
fi

if [ ! -d "${INPUT_ROOT}" ]; then
    echo "Error: Input directory ${INPUT_ROOT} not found. Exiting."
    exit 1
fi

if ! find "${INPUT_ROOT}" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
    echo "Error: No case directories found in ${INPUT_ROOT}. Exiting."
    exit 1
fi

: > "${CASE_LIST_FILE}"
while IFS= read -r case_path; do
    if [[ -f "${case_path}/INPUT" && -f "${case_path}/STRU" && -f "${case_path}/KPT" ]]; then
        basename "${case_path}" >> "${CASE_LIST_FILE}"
    else
        echo "Skipping invalid case dir (missing INPUT/STRU/KPT): ${case_path}"
    fi
done < <(find "${INPUT_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)

if ! grep -q . "${CASE_LIST_FILE}"; then
    echo "Error: No valid case directories with INPUT/STRU/KPT under ${INPUT_ROOT}. Exiting."
    exit 1
fi

TOTAL_TASKS=$(wc -l < "${CASE_LIST_FILE}")
export TOTAL_TASKS

parallel_enabled=1
if ! command -v "${PARALLEL_BIN}" >/dev/null 2>&1; then
    parallel_enabled=0
fi

TOTAL_CPUS_SOURCE=""
DETECTED_TOTAL_CPUS=""
if ! detect_total_cpus; then
    echo "Error: Failed to detect total CPUs from the submitted task budget." >&2
    echo "Set SLURM task variables or export ABACUS_TOTAL_CPUS / ABACUS_TASKS and ABACUS_CPUS_PER_TASK." >&2
    exit 1
fi
if ! [[ "${DETECTED_TOTAL_CPUS}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Failed to detect a valid total CPU count from the submitted task budget." >&2
    exit 1
fi
total_cpus="${DETECTED_TOTAL_CPUS}"

auto_jobs=$(( total_cpus / omp_threads ))
if (( auto_jobs < 1 )); then
    auto_jobs=1
fi
if (( auto_jobs > TOTAL_TASKS )); then
    auto_jobs="${TOTAL_TASKS}"
fi

if [[ -n "${jobs_arg}" ]]; then
    if ! [[ "${jobs_arg}" =~ ^[1-9][0-9]*$ ]]; then
        echo "Error: jobs must be a positive integer when provided." >&2
        exit 1
    fi
    bash_jobs="${jobs_arg}"
    jobs_source="manual"
else
    bash_jobs="${auto_jobs}"
    jobs_source="auto"
fi

if (( bash_jobs > TOTAL_TASKS )); then
    echo "Requested jobs (${bash_jobs}) exceed case count (${TOTAL_TASKS}); capping to case count."
    bash_jobs="${TOTAL_TASKS}"
fi

if (( bash_jobs * omp_threads > total_cpus )); then
    echo "Warning: requested parallelism (${bash_jobs} x ${omp_threads} = $(( bash_jobs * omp_threads ))) exceeds detected total CPUs (${total_cpus})."
fi

global_start_time=$(date)
global_start_seconds=$SECONDS
echo "=========================================================="
echo "Starting local ABACUS batch run"
echo "Start Time: ${global_start_time}"
echo "Processing Input Directory: ${INPUT_ROOT}"
echo "Saving outputs to: ${DATASET_ROOT}"
echo "Detected total CPUs: ${total_cpus} (source=${TOTAL_CPUS_SOURCE})"
if [[ "${jobs_source}" == "auto" ]]; then
    echo "Auto-calculated parallel workers: ${bash_jobs}"
else
    echo "Using manually specified parallel workers: ${bash_jobs}"
fi
if [[ "${parallel_enabled}" == "1" ]]; then
    echo "Using ${bash_jobs} parallel workers via GNU Parallel."
else
    echo "GNU Parallel not found (${PARALLEL_BIN}); falling back to sequential execution."
fi
echo "ABACUS command: ${ABACUS_CMD}"
echo "OpenMP threads per case: ${omp_threads}"
echo "Total tasks: ${TOTAL_TASKS}"
echo "Total CPU slots: $(( bash_jobs * omp_threads ))"
echo "Run log: ${LOG_FILE}"
echo "Parallel job log: ${PARALLEL_JOBLOG}"
echo "=========================================================="

if [[ "${parallel_enabled}" == "1" ]]; then
    "${PARALLEL_BIN}" --jobs "${bash_jobs}" --no-notice --joblog "${PARALLEL_JOBLOG}" \
        'run_single_calculation "{}" "{%}"' :::: "${CASE_LIST_FILE}"
else
    while IFS= read -r case_id; do
        [[ -z "${case_id}" ]] && continue
        run_single_calculation "${case_id}" "1"
    done < "${CASE_LIST_FILE}"
fi

global_end_time=$(date)
global_elapsed_seconds=$((SECONDS - global_start_seconds))
echo "=========================================================="
echo "Local ABACUS batch run finished."
echo "End Time: ${global_end_time}"
echo "Total Duration: ${global_elapsed_seconds} seconds."
echo "=========================================================="
