---
name: abacus-data-processing
description: Prepare ABACUS calculation inputs from CIF/POSCAR with default settings and generate per-structure INPUT/KPT/STRU run directories.
---

# ABACUS Data Processing

Reference usage policy:
- Do not bulk-read `reference/*` during normal execution.
- Before finalizing generated config files, quickly scan `reference/ROUTING.md` for strong intent matches.
- If a very close route is found, open only the mapped markdown(s) (and minimal companion example files if needed), then adapt parameters to that pattern instead of blindly keeping defaults.
- If no strong route is found, keep the template/script defaults.
- When discussing setup choices with the user, you may reference relevant files under `reference/*` as supporting evidence.
- Keep reference loading minimal and targeted; do not ingest unrelated documents.

1. Prepare one split-local ABACUS workdir per dataset split. Do not run train and test generation in one shared mutable directory.
2. Seed each split-local workdir from `<skill_root>/templates/abacus/`:
- `abacus_input_gen.yaml`
- `run_abacus.sh`
3. Render the copied template into the split-local workdir. Do not edit skill-owned templates in place.
4. In `abacus_input_gen.yaml`, render split-specific fields only:
- `structure_glob`
- `output_root`
- optional `system_name`
5. In `run_abacus.sh`, only render split-specific values such as `SYSTEM_NAME`, `INPUT_ROOT`, and `DATASET_ROOT`. Preserve the runtime environment contract.
6. Keep default settings unless the user explicitly requests overrides. Default baseline:
- `calculation=scf`
- `basis_type=lcao`
- `ecutwfc=100`, `scf_thr=1e-7`, `scf_nmax=200`
- `out_mat_hs2=1` (export sparse H/S matrices for downstream graph generation)
- `kpt=Gamma 4x4x4`
7. Runtime environment policy:
- run via `<skill_root>/scripts/data_processing.sh`
- for input generation, default conda env is `${ABACUS_CONDA_ENV:-OpenMX}` (contains `pymatgen` and `pyyaml`); if unavailable, fall back to `base`
- for ABACUS execution via `run_abacus.sh`, default conda env is `${ABACUS_CONDA_ENV:-abacus_env}`
- only override `ABACUS_CONDA_ENV` or `PYTHON_BIN` when explicitly needed
- logs are written to `<workdir>/logs/abacus_input_gen.log`
8. Use the split-local entry command:
- `<skill_root>/scripts/data_processing.sh --workdir <abacus_split_root> --config abacus_input_gen.yaml`
9. For ABACUS batch execution against generated case directories, use:
- `bash ./run_abacus.sh [jobs] [omp_threads]`
- default command is `ABACUS_CMD=${ABACUS_CMD:-${ABACUS_BIN}}` and can be overridden for site-specific launchers.
10. Input policy:
- CIF input is first-class
- POSCAR/CONTCAR/vasp-like files are also allowed when readable by `pymatgen`
- fail fast when `structure_glob` resolves to zero files
- placeholders like `__CIF_GLOB__` / `__ABACUS_INPUT_ROOT__` must be rendered before execution
11. Generation policy:
- output is one run folder per structure under `output_root`
- each run folder contains `INPUT`, `KPT`, `STRU`, and `source.*` for traceability
- default naming is `index_stem`
- default `overwrite=false`; existing run dirs must fail instead of silent overwrite
- default `copy_source_file=true`
- default `move_flags=[1,1,1]`
12. Mapping and safety guardrails:
- validate pseudopotential mapping (`PP_DICT`) for all species
- when `basis_type=lcao`, validate orbital mapping (`ORB_DICT`) for all species
- if any element mapping is missing, stop and report missing symbols; do not guess
13. Multi-split isolation:
- train/test (or other splits) must use independent `output_root`
- do not let one split overwrite another split's generated run folders
14. Returnables for downstream stages:
- generated `output_root` per split
- generated run-folder list
- generation log path (`logs/abacus_input_gen.log`)
- when `run_abacus.sh` is executed, return ABACUS run log path (`logs/run_abacus_*.log`)
- clear failure reason when generation stops
