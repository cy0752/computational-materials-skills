#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_NAME="${SYSTEM_NAME:-__SYSTEM_NAME__}"
INPUT_ROOT="${INPUT_ROOT:-__OPENMX_INPUT_ROOT__}"
DATASET_ROOT="${DATASET_ROOT:-__OPENMX_DATASET_ROOT__}"
OPENMX_BIN="${OPENMX_BIN:-/root/openmx}"
OPENMX_POSTPROCESS_BIN="${OPENMX_POSTPROCESS_BIN:-/root/openmx_postprocess}"
PARALLEL_BIN="${PARALLEL_BIN:-parallel}"
TASKSET_BIN="${TASKSET_BIN:-taskset}"
OPENMX_CONDA_ENV="${OPENMX_CONDA_ENV:-OpenMX}"
DEFAULT_OMP_THREADS=2
DEFAULT_OPENMX_TASKS=16
DEFAULT_OPENMX_CPUS_PER_TASK=2

LOG_DIR="${SCRIPT_DIR}/logs"
RUN_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/run_openmx_${RUN_TIMESTAMP}.log"
PARALLEL_JOBLOG="${LOG_DIR}/parallel_job_${RUN_TIMESTAMP}.log"
PROGRESS_DIR="${LOG_DIR}/progress_${RUN_TIMESTAMP}"
mkdir -p "${LOG_DIR}" "${PROGRESS_DIR}" "${DATASET_ROOT}"
exec > >(tee -a "${LOG_FILE}") 2>&1

if [ -f "/root/miniconda3/etc/profile.d/conda.sh" ]; then
    source /root/miniconda3/etc/profile.d/conda.sh
    conda activate "${OPENMX_CONDA_ENV}"
else
    source /root/miniconda3/bin/activate "${OPENMX_CONDA_ENV}"
fi

set +u
source /opt/intel/oneapi/setvars.sh >/dev/null 2>&1
set -u
ulimit -s unlimited
export OCL_ICD_FILENAMES="${OCL_ICD_FILENAMES:-}"
export I_MPI_HYDRA_BOOTSTRAP="${I_MPI_HYDRA_BOOTSTRAP:-slurm}"
export I_MPI_FABRICS="${I_MPI_FABRICS:-shm:ofi}"
export I_MPI_OFI_PROVIDER="${I_MPI_OFI_PROVIDER:-tcp}"
unset UCX_TLS
unset UCX_NET_DEVICES
export MKLROOT="${MKLROOT:-/opt/intel/oneapi/mkl/latest}"
export I_MPI_ROOT="${I_MPI_ROOT:-/opt/intel/oneapi/mpi/latest}"
export LD_LIBRARY_PATH="${MKLROOT}/lib/intel64:${I_MPI_ROOT}/lib/release:${I_MPI_ROOT}/lib:${GSL_LIB_PATH:-/inspire/qb-ilm/project/cq-scientific-cooperation-zone/public/openmx3.9/gsl/lib}:/opt/intel/oneapi/compiler/2025.3/lib:/root/miniconda3/envs/${OPENMX_CONDA_ENV}/lib:${LD_LIBRARY_PATH:-}"
export PATH="/root/miniconda3/envs/${OPENMX_CONDA_ENV}/bin:${PATH}"
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
    if [[ -n "${OPENMX_TOTAL_CPUS:-}" ]] && [[ "${OPENMX_TOTAL_CPUS}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="openmx_total_cpus_env"
        echo "${OPENMX_TOTAL_CPUS}"
        return
    fi

    if [[ -n "${OPENMX_TASKS:-}" && -n "${OPENMX_CPUS_PER_TASK:-}" ]] \
        && [[ "${OPENMX_TASKS}" =~ ^[1-9][0-9]*$ ]] \
        && [[ "${OPENMX_CPUS_PER_TASK}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="openmx_tasks_x_cpus_per_task_env"
        echo $((OPENMX_TASKS * OPENMX_CPUS_PER_TASK))
        return
    fi

    if [[ -n "${SLURM_NTASKS:-}" && -n "${SLURM_CPUS_PER_TASK:-}" ]] \
        && [[ "${SLURM_NTASKS}" =~ ^[1-9][0-9]*$ ]] \
        && [[ "${SLURM_CPUS_PER_TASK}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="slurm_ntasks_x_cpus_per_task"
        echo $((SLURM_NTASKS * SLURM_CPUS_PER_TASK))
        return
    fi

    if [[ -n "${SLURM_CPUS_ON_NODE:-}" && "${SLURM_CPUS_ON_NODE}" =~ ^[1-9][0-9]*$ ]]; then
        TOTAL_CPUS_SOURCE="slurm_cpus_on_node"
        echo "${SLURM_CPUS_ON_NODE}"
        return
    fi

    TOTAL_CPUS_SOURCE="openmx_default_profile"
    echo $((DEFAULT_OPENMX_TASKS * DEFAULT_OPENMX_CPUS_PER_TASK))
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
    local work_dir="${DATASET_ROOT}/${data_id}"
    local input_dat_path="${INPUT_ROOT}/${data_id}.dat"
    local target_dat_path="${work_dir}/${SYSTEM_NAME}.dat"
    local std_file="${SYSTEM_NAME}.std"
    local postprocess_std_file="openmx_postprocess.std"
    local debug_log="${work_dir}/debug_progress.log"
    local cpu_binding=""

    mkdir -p "${work_dir}"
    cp "${input_dat_path}" "${target_dat_path}"
    echo "$(date): [START] ${data_id}" > "${debug_log}"
    cd "${work_dir}" || { echo "ERROR: Failed to cd into ${work_dir}." >> "${debug_log}"; return 1; }

    if cpu_binding="$(select_cpu_slice "${slot_index}" "${omp_threads}")"; then
        echo "$(date): [BIND] slot=${slot_index} cpus=${cpu_binding}" >> "${debug_log}"
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} ${TASKSET_BIN} -c ${cpu_binding} ${OPENMX_BIN} ${target_dat_path} -nt ${omp_threads}" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" "${TASKSET_BIN}" -c "${cpu_binding}" "${OPENMX_BIN}" "${target_dat_path}" -nt "${omp_threads}" > "${std_file}" 2>&1
    else
        echo "$(date): [BIND] slot=${slot_index} insufficient cpus in allowed set; running unbound" >> "${debug_log}"
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} ${OPENMX_BIN} ${target_dat_path} -nt ${omp_threads}" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" "${OPENMX_BIN}" "${target_dat_path}" -nt "${omp_threads}" > "${std_file}" 2>&1
    fi
    echo "$(date): [POST-EXEC] OpenMX exit status: $?" >> "${debug_log}"

    if [[ -n "${cpu_binding}" ]]; then
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} ${TASKSET_BIN} -c ${cpu_binding} ${OPENMX_POSTPROCESS_BIN} ${target_dat_path} -nt ${omp_threads}" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" "${TASKSET_BIN}" -c "${cpu_binding}" "${OPENMX_POSTPROCESS_BIN}" "${target_dat_path}" -nt "${omp_threads}" > "${postprocess_std_file}" 2>&1
    else
        echo "$(date): [EXEC] OMP_NUM_THREADS=${omp_threads} ${OPENMX_POSTPROCESS_BIN} ${target_dat_path} -nt ${omp_threads}" >> "${debug_log}"
        OMP_NUM_THREADS="${omp_threads}" "${OPENMX_POSTPROCESS_BIN}" "${target_dat_path}" -nt "${omp_threads}" > "${postprocess_std_file}" 2>&1
    fi
    echo "$(date): [POST-EXEC] openmx_postprocess exit status: $?" >> "${debug_log}"

    touch "${PROGRESS_DIR}/${data_id}.done"
    local completed_count
    completed_count=$(find "${PROGRESS_DIR}" -maxdepth 1 -type f -name '*.done' | wc -l)
    printf '[%s] Completed %s/%s: %s\n' "$(date '+%F %T')" "${completed_count}" "${TOTAL_TASKS}" "${data_id}"
}

export -f run_single_calculation
export -f expand_cpu_list select_cpu_slice
export SYSTEM_NAME INPUT_ROOT DATASET_ROOT OPENMX_BIN OPENMX_POSTPROCESS_BIN PROGRESS_DIR TOTAL_TASKS TASKSET_BIN

jobs_arg="${1:-${OPENMX_JOBS:-}}"
omp_threads="${2:-${OPENMX_OMP_THREADS:-$DEFAULT_OMP_THREADS}}"

if ! [[ "${omp_threads}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: omp_threads must be a positive integer."
    echo "Usage: bash $(basename "$0") [jobs] [omp_threads]"
    exit 1
fi
export omp_threads

if [ ! -d "${INPUT_ROOT}" ]; then
    echo "Error: Input directory ${INPUT_ROOT} not found. Exiting."
    exit 1
fi

if ! find "${INPUT_ROOT}" -maxdepth 1 -type f -name "*.dat" | grep -q .; then
    echo "Error: No .dat files found in ${INPUT_ROOT}. Exiting."
    exit 1
fi

TOTAL_TASKS=$(find "${INPUT_ROOT}" -maxdepth 1 -type f -name "*.dat" | wc -l)
export TOTAL_TASKS

TOTAL_CPUS_SOURCE=""
if ! detected_total_cpus="$(detect_total_cpus)"; then
    echo "Error: Failed to detect total CPUs from the submitted task budget." >&2
    echo "Set SLURM task variables or export OPENMX_TOTAL_CPUS / OPENMX_TASKS and OPENMX_CPUS_PER_TASK." >&2
    exit 1
fi
if ! [[ "${detected_total_cpus}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: Failed to detect a valid total CPU count from the submitted task budget." >&2
    exit 1
fi
total_cpus="${detected_total_cpus}"

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
    echo "Requested jobs (${bash_jobs}) exceed material count (${TOTAL_TASKS}); capping to material count."
    bash_jobs="${TOTAL_TASKS}"
fi

if (( bash_jobs * omp_threads > total_cpus )); then
    echo "Warning: requested parallelism (${bash_jobs} x ${omp_threads} = $(( bash_jobs * omp_threads ))) exceeds detected total CPUs (${total_cpus})."
fi

global_start_time=$(date)
global_start_seconds=$SECONDS
echo "=========================================================="
echo "Starting local OpenMX batch run"
echo "Start Time: ${global_start_time}"
echo "Processing Input Directory: ${INPUT_ROOT}"
echo "Saving outputs to: ${DATASET_ROOT}"
echo "Detected total CPUs: ${total_cpus} (source=${TOTAL_CPUS_SOURCE})"
if [[ "${jobs_source}" == "auto" ]]; then
    echo "Auto-calculated parallel workers: ${bash_jobs}"
else
    echo "Using manually specified parallel workers: ${bash_jobs}"
fi
echo "Using ${bash_jobs} parallel workers via GNU Parallel."
echo "OpenMP threads per material: ${omp_threads}"
echo "Total tasks: ${TOTAL_TASKS}"
echo "Total CPU slots: $(( bash_jobs * omp_threads ))"
echo "Run log: ${LOG_FILE}"
echo "Parallel job log: ${PARALLEL_JOBLOG}"
echo "=========================================================="

find "${INPUT_ROOT}" -maxdepth 1 -type f -name "*.dat" -print0 | \
    "${PARALLEL_BIN}" -0 --jobs "${bash_jobs}" --no-notice --joblog "${PARALLEL_JOBLOG}" \
    'dat_path={}; data_id=$(basename "$dat_path" .dat); run_single_calculation "$data_id" "{%}"'

global_end_time=$(date)
global_elapsed_seconds=$((SECONDS - global_start_seconds))
echo "=========================================================="
echo "Local OpenMX batch run finished."
echo "End Time: ${global_end_time}"
echo "Total Duration: ${global_elapsed_seconds} seconds."
echo "=========================================================="
