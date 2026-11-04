---
name: openmx-data-processing
description: Prepare split-local OpenMX preprocessing inputs and submit recognized OpenMX processing jobs through `inspire-openmx-submit`.
---

# OpenMX Data Processing

1. Prepare one split-local OpenMX workdir per dataset split. Do not run train and test processing against one shared in-place `interfaces/openmx` directory.
2. Seed each split-local workdir from `<skill_root>/templates/openmx/`:
- `poscar2openmx.yaml`
- `run_openmx.sh`
- `graph_data_gen.yaml`
- `dat_gen.sh`
- `graphgen.sh`
No HamGNN Python scripts are copied into the workdir. `dat_gen.sh` and `graphgen.sh` run the packaged modules via `python -m DFT_interfaces.openmx.poscar2openmx` / `python -m DFT_interfaces.openmx.graph_data_gen` (HamGNN >= 2.3.0 package layout).
3. Render the copied templates into the split-local workdir. Do not edit the skill-owned templates in place.
4. In `run_openmx.sh`, only render split-specific values such as `SYSTEM_NAME`, `INPUT_ROOT`, and `DATASET_ROOT`. Preserve the runtime environment contract.

### Runtime contract (machine-specific, not assumed by this skill)

This skill does not assume a dedicated conda environment or any particular provenance of the tools. The caller must guarantee, on the execution machine:

- `PYTHONBIN` (default `python`): an interpreter where `DFT_interfaces` is importable — true when HamGNN is pip-installed, or when `HAMGNN_ROOT` points at a HamGNN source checkout (exported to `PYTHONPATH` by the scripts).
- OpenMX executables `openmx` and `openmx_postprocess` are runnable: on `PATH`, or provided via `OPENMX_BIN` / `OPENMX_POSTPROCESS_BIN` absolute paths.
- Optional `OPENMX_CONDA_ENV` activates a conda env inside `run_openmx.sh` only when explicitly set; `ONEAPI_SETVARS`, `MKLROOT`, `GSL_LIB_PATH` remain optional site hooks.
- `graph_data_gen.yaml.nao_max` accepts only `14`, `19`, or `26`.
- Generation writes `graph_data.npz`; reading `npz` / `lmdb` / `auto` via `dataset_params.data_format` is unaffected.
5. Use `inspire-openmx-submit` for the actual OpenMX submission. `inspire-openmx-submit` is the authority for workspace, compute group, spec, image, and HPC submission shape.
6. Default split-local execution policy:
- default OpenMX task budget is `tasks=16`, `cpus-per-task=2`
- `omp_threads` defaults to `2`
- default material parallelism is therefore `16`
- `jobs` defaults to auto-calculation from the task's total CPUs
- total CPUs must come from the submitted task budget
- detect total CPUs from SLURM first, then from explicit task environment variables such as `OPENMX_TOTAL_CPUS` or `OPENMX_TASKS * OPENMX_CPUS_PER_TASK`
- do not infer total CPUs from the local interactive session CPU set
- explicit `jobs` / `omp_threads` overrides are still allowed
7. Submit the split-local entry command that runs `<skill_root>/scripts/data_processing.sh --workdir <openmx_split_root> [--jobs <jobs>] [--omp-threads <omp_threads>]`.
8. Use as many CPUs as practical for the split, but do not exceed the number of data points.
9. Return the generated `.npz` path for the processed split so downstream HamGNN stages can consume it.
