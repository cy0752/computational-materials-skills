---
name: structure-openmx-hamgnn-training-pipeline
description: Structure-file-driven OpenMX/ABACUS-to-HamGNN training pipeline. Use when users provide a crystal structure file such as CIF or POSCAR and want to build a perturbed CIF dataset, run DFT preprocessing (OpenMX by default, ABACUS when explicitly requested), and train a HamGNN model, stopping at the trained checkpoint.
---

# Structure-Driven OpenMX/ABACUS HamGNN Training Pipeline

## Objective

Train HamGNN from a user-specified structure file with this strict sequential loop:
`structure file -> primitive CIF -> perturbed CIF dataset -> DFT preprocessing -> HamGNN training`.

Never skip, reorder, or merge stages.

## Required Inputs

1. `work_root` (default: current working directory)
2. `structure_path` (required; input structure file path)
3. `num_perturb` (must be confirmed with the user before changing or assuming a total sample count)
4. `train_split_ratio` (default: `0.8`)
5. `target_dir` (create this dir and place all new files inside it, default: `hamgnn_train_{timestamp}`)
6. `dft_engine` (optional: `openmx` or `abacus`; default: `openmx`)
7. `execution_mode` (optional: `submit` or `local`; default: `submit`)

## Local Environment Policy

1. Before running each stage locally, first try a stage-matched conda env, then fall back to `base` if unavailable:
- Stage 0/1 Python preprocessing: prefer `OpenMX`, fallback `base`
- Stage 2B ABACUS local run: prefer `abacus_env`, fallback `base`
- Stage 3 HamGNN local run: prefer `HamGNN`, fallback `base`
2. Do not create a new local conda env unless the user explicitly asks.
3. If local Python dependencies such as `pymatgen` or `ase` are missing, install them into the selected fallback env.
4. In `submit` mode, remote OpenMX jobs must use the canonical OpenMX submission flow and its configured runtime environment.
5. In `submit` mode, remote ABACUS jobs must use the canonical ABACUS submission flow and its configured runtime environment.

## Stage 0: Normalize Structure Input to Primitive CIF

1. Accept a user-specified structure file such as `CIF`, `POSCAR`, `CONTCAR`, `vasp`, or another periodic structure format readable by `pymatgen` or `ASE`.
2. Use local conda env `OpenMX` when available, otherwise `base`, and run `<skill_root>/scripts/structure_to_cif.py`.
3. Convert the input structure into a primitive-cell CIF and write it under `<work_root>/<target_dir>/structure/primitive.cif`.
4. Preserve the original input structure file unchanged.
5. Run:

```bash
conda run -n <stage01_env> python <skill_root>/scripts/structure_to_cif.py \
  --input <structure_path> \
  --output <work_root>/<target_dir>/structure/primitive.cif \
  --primitive
```

6. Stage 0 output: a single selected primitive-cell CIF path `stage0_cif_path`.

## Stage 1: Generate Perturbed CIF Dataset

1. Use local conda env `OpenMX` when available, otherwise `base`, and run `<skill_root>/scripts/prepare_perturbed_dataset.py`.
2. Use the Stage 0 CIF as the only structural input source for this stage.
3. Keep the train/test split ratio logic, but do not silently choose or change the total number of perturbed structures without discussing it with the user first.
4. Apply a hard perturbation cap of `0.06 Å` per atom via `--max-displacement`.
5. Run:

```bash
conda run -n <stage01_env> python <skill_root>/scripts/prepare_perturbed_dataset.py \
  --cif <stage0_cif_path> \
  --workdir <work_root>/<target_dir>/crystal_pipeline \
  --num-perturb <num_perturb> \
  --train-split-ratio <train_split_ratio> \
  --train-output-dir <work_root>/<target_dir>/cif/train \
  --test-output-dir <work_root>/<target_dir>/cif/test \
  --max-displacement 0.06
```

6. Stage 1 outputs:
- `<work_root>/<target_dir>/crystal_pipeline/perturbed_cif/*.cif`
- `<work_root>/<target_dir>/crystal_pipeline/manifest.json`
- `<work_root>/<target_dir>/cif/train/*.cif`
- `<work_root>/<target_dir>/cif/test/*.cif`
7. Train/test split is generated directly by the script. No extra manual split step is needed.
8. Stage 1 runs locally. No Inspire submission is needed.

## Stage 2: DFT Data Processing (OpenMX or ABACUS)

Route selection rule:
1. If the user does not explicitly specify a DFT engine, use the OpenMX route by default.
2. Only use the ABACUS route when the user explicitly asks for ABACUS.
3. Once a route is selected for this run, keep train/test in the same DFT route and do not mix OpenMX and ABACUS outputs in one Stage 2 execution.

### Stage 2A (default): OpenMX route

1. Use `openmx-data-processing` to prepare split-local OpenMX inputs for the CIF datasets generated in Stage 1.
2. `execution_mode` handling:
- `submit`: submit actual OpenMX jobs through `inspire-openmx-submit`; this is the sole authority for OpenMX submission parameters such as workspace, compute group, spec, image, and HPC submission shape.
- `local`: run the split-local OpenMX flow directly in local workdirs (generate input, then execute `run_openmx.sh`).
3. Do not hardcode OpenMX image or resource parameters in this pipeline skill.
4. Render split-local OpenMX workdirs from `openmx-data-processing/templates/openmx/`.
5. Process the training split first. Process the test split separately only when Stage 1 actually created a non-empty external test split.
6. Do not let multiple splits mutate one shared in-place OpenMX directory.
7. Default per-split OpenMX policy:
- default OpenMX task budget is `tasks=16`, `cpus-per-task=2`
- `omp_threads=2`
- default material parallelism is `16`
- material parallelism is auto-calculated from the task's total CPUs
- total CPUs must come from the submitted task budget
- detect total CPUs from SLURM first, then from explicit task environment variables
- if no task budget is exported at runtime, fall back to the canonical OpenMX default profile `16 * 2 = 32` CPUs
- do not infer total CPUs from the local interactive session CPU set
- explicit overrides are still allowed when needed
8. Stage 2A outputs:
- a training `.npz` path derived from the Stage 1 train CIF split
- an optional external test `.npz` path derived from the Stage 1 test CIF split when that split exists

### Stage 2B (explicit opt-in): ABACUS route

1. Use `abacus-data-processing` to prepare split-local ABACUS inputs for the CIF datasets generated in Stage 1.
2. `execution_mode` handling:
- `submit`: submit actual ABACUS jobs through the canonical ABACUS submission flow (sole authority for ABACUS submission parameters such as workspace, compute group, spec, image, and HPC submission shape).
- `local`: run generated split-local ABACUS workdirs directly with `bash ./run_abacus.sh [jobs] [omp_threads]` (prefer env `abacus_env`, fallback `base`).
3. Do not hardcode ABACUS image or resource parameters in this pipeline skill.
4. Render split-local ABACUS workdirs from `abacus-data-processing/templates/abacus/`.
5. Process the training split first. Process the test split separately only when Stage 1 actually created a non-empty external test split.
6. Do not let multiple splits mutate one shared in-place ABACUS directory.
7. Default per-split ABACUS policy:
- default ABACUS task budget is `tasks=16`, `cpus-per-task=2`
- `omp_threads=2`
- default material parallelism is `16`
- material parallelism is auto-calculated from the task's total CPUs
- total CPUs must come from the submitted task budget
- detect total CPUs from SLURM first, then from explicit task environment variables
- if no task budget is exported at runtime, fall back to the canonical ABACUS default profile `16 * 2 = 32` CPUs
- do not infer total CPUs from the local interactive session CPU set
- explicit overrides are still allowed when needed
8. Ensure sparse matrix export is enabled for graph generation:
- in rendered `abacus_input_gen.yaml`, keep `input.out_mat_hs2: 1` so ABACUS writes `data-*-sparse_SPIN0.csr` files.
9. After ABACUS SCF finishes for each split, generate graph dataset files from split-local case dirs:
- run `graph_data_gen_abacus.py` with split-local `--data-dirs` and write to split-local graph output dir
- default graph export `--output-format npz`
- default `--nao-max 19` means auto mode; it resolves to a compatible ABACUS basis profile (typically `27` or `40`) based on detected elements and fails fast on explicit incompatible values
- run graph export in an env with required deps (`torch`, `torch_geometric`; `lmdb` only when LMDB output is requested)
- recommended command:

```bash
conda run -n <stage2_graph_env> python <abacus_skill_root>/templates/abacus/graph_data_gen_abacus.py \
  --data-dirs <abacus_case_dir_1> [<abacus_case_dir_2> ...] \
  --graph-data-folder <abacus_split_root>/graph_data \
  --output-format npz \
  --nao-max 19
```

10. Stage 2B outputs:
- a training `.npz` path derived from the Stage 1 train CIF split
- an optional external test `.npz` path derived from the Stage 1 test CIF split when that split exists

## Stage 3: HamGNN Training

1. Use `hamgnn-training` to prepare the stage-local training config and runnable entry command.
2. `execution_mode` handling:
- `submit`: submit the actual HamGNN training job through `inspire-hamgnn-submit`; it is the sole authority for HamGNN submission parameters such as workspace, GPU resource, image, and GPU helper selection.
- `local`: run `<hamgnn-training>/scripts/train.sh --workdir <hamgnn_workdir> --config <rendered_train_config>` locally (prefer env `HamGNN`, fallback `base`).
3. Do not hardcode HamGNN image, location, or GPU resource parameters in this pipeline skill.
4. Render a run-local training config from `hamgnn-training/templates/HamGNN/train_config.yaml.template` into `<work_root>/<target_dir>/HamGNN/`.
5. This stage consumes the training `.npz` from the selected Stage 2 route (OpenMX or ABACUS).
6. Render `__HAM_TYPE__` from Stage 2 route:
- OpenMX route -> `openmx`
- ABACUS route -> `abacus`
7. Apply the same rendered `__HAM_TYPE__` value to both `ham_type` and `radius_type` in the rendered training config.
8. Ordinary HamGNN training must keep `uni_model_pkl_path: null` unless the user explicitly asks to load a Uni model.
9. If the upstream Stage 2 dataset includes `H0`, keep `add_H0: true` in the rendered config.
10. If Stage 2 produced an external test `.npz`, do not allocate an additional internal HamGNN test split from the training `.npz`.
11. Stage 3 output: the trained model or checkpoint path.

## Final Deliverables

1. Return the rendered training config path.
2. Return the HamGNN training job record path.
3. Return the best checkpoint path when training completes.
4. Return the generated train `.npz` path, and return the external test `.npz` path when it exists.
