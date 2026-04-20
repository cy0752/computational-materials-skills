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
3. Render the copied templates into the split-local workdir. Do not edit the skill-owned templates in place.
4. In `run_openmx.sh`, only render split-specific values such as `SYSTEM_NAME`, `INPUT_ROOT`, and `DATASET_ROOT`. Preserve the runtime environment contract.
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
