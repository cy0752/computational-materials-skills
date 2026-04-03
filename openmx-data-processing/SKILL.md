---
name: openmx-data-processing
description: Prepare split-local OpenMX preprocessing inputs and hand actual remote execution to the customizable `remote-task-submit` adapter.
---

# OpenMX Data Processing

## Standalone Use

This skill must remain independently usable outside `structure-openmx-hamgnn-training-pipeline`.

Use it whenever the user already has one dataset split of structure files and wants to preprocess that split into HamGNN-ready graph data without invoking the full structure pipeline.
Do not assume this skill was entered only from an upstream pipeline stage.

Minimum standalone inputs:

- one logical dataset split of structure files such as CIFs or POSCAR-derived inputs
- a split-local OpenMX workdir
- rendered placeholder values for the copied templates, including `SYSTEM_NAME`, `POSCAR_GLOB`, `OPENMX_INPUT_ROOT`, `OPENMX_DATASET_ROOT`, `GRAPH_DATA_SAVE_DIR`, and related OpenMX graph-generation fields
- a remote execution path through `remote-task-submit`, or a local execution path if the user explicitly wants local runs

1. Prepare one split-local OpenMX workdir per dataset split. Do not run train and test processing against one shared in-place `interfaces/openmx` directory.
2. Seed each split-local workdir from `<skill_root>/templates/openmx/`:
- `poscar2openmx.yaml`
- `run_openmx.sh`
- `graph_data_gen.yaml`
- `dat_gen.sh`
- `graphgen.sh`
3. Render the copied templates into the split-local workdir. Do not edit the skill-owned templates in place.
4. In `run_openmx.sh`, only render split-specific values such as `SYSTEM_NAME`, `INPUT_ROOT`, and `DATASET_ROOT`. Preserve the runtime environment contract.
5. Use `remote-task-submit` for the actual OpenMX submission. Keep queue, node shape, launcher, image, and other cluster-specific defaults inside `remote-task-submit`.
6. Default split-local execution policy:
- default OpenMX task budget is `tasks=16`, `cpus-per-task=2`
- `omp_threads` defaults to `2`
- default material parallelism is therefore `16`
- `jobs` defaults to auto-calculation from the task's total CPUs
- total CPUs must come from the submitted task budget
- detect total CPUs from SLURM first, then from explicit task environment variables such as `OPENMX_TOTAL_CPUS` or `OPENMX_TASKS * OPENMX_CPUS_PER_TASK`
- do not infer total CPUs from the local interactive session CPU set
- explicit `jobs` / `omp_threads` overrides are still allowed
7. Submit the split-local entry command that runs `<skill_root>/scripts/data_processing.sh --workdir <openmx_split_root> [--jobs <jobs>] [--omp-threads <omp_threads>]` through `remote-task-submit`.
8. Use as many CPUs as practical for the split, but do not exceed the number of data points.
9. Return the generated `.npz` path for the processed split so downstream HamGNN stages or a standalone HamGNN user can consume it.
