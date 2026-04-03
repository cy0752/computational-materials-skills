---
name: structure-openmx-hamgnn-training-pipeline
description: Structure-file-driven OpenMX-to-HamGNN pipeline. Use when users provide a crystal structure file such as CIF or POSCAR and want to build a perturbed CIF dataset, run OpenMX preprocessing, train a HamGNN model, and evaluate it on the held-out test dataset.
---

# Structure-Driven OpenMX HamGNN Training Pipeline

## Objective

Train HamGNN from a user-specified structure file with this strict sequential loop:
`structure file -> primitive CIF -> perturbed CIF dataset -> OpenMX -> HamGNN training -> HamGNN test`.

Never skip, reorder, or merge stages.
All child skills used by this pipeline must also remain independently usable outside this orchestration layer.

## Required Inputs

1. `work_root` (default: current working directory)
2. `structure_path` (required; input structure file path)
3. `num_perturb` (must be confirmed with the user before changing or assuming a total sample count)
4. `train_split_ratio` (default: `0.8`)
5. `target_dir` (create this dir and place all new files inside it, default: `hamgnn_train_{timestamp}`)

## Local Environment Policy

1. Prefer local conda env `base` for this pipeline's local Python stages.
2. Do not create a new local conda env unless the user explicitly asks.
3. If local Python dependencies such as `pymatgen` or `ase` are missing, install them into `base`.
4. Remote OpenMX jobs must use the repository's customizable remote submission flow. Do not hardcode site-specific remote runtime choices in this pipeline skill.

## Stage 0: Normalize Structure Input to Primitive CIF

1. Accept a user-specified structure file such as `CIF`, `POSCAR`, `CONTCAR`, `vasp`, or another periodic structure format readable by `pymatgen` or `ASE`.
2. Use local conda env `base` and `<skill_root>/scripts/structure_to_cif.py`.
3. Convert the input structure into a primitive-cell CIF and write it under `<work_root>/<target_dir>/structure/primitive.cif`.
4. Preserve the original input structure file unchanged.
5. Run:

```bash
conda run -n base python <skill_root>/scripts/structure_to_cif.py \
  --input <structure_path> \
  --output <work_root>/<target_dir>/structure/primitive.cif \
  --primitive
```

6. Stage 0 output: a single selected primitive-cell CIF path `stage0_cif_path`.

## Stage 1: Generate Perturbed CIF Dataset

1. Use local conda env `base` and `<skill_root>/scripts/prepare_perturbed_dataset.py`.
2. Use the Stage 0 CIF as the only structural input source for this stage.
3. Keep the train/test split ratio logic, but do not silently choose or change the total number of perturbed structures without discussing it with the user first.
4. Apply a hard perturbation cap of `0.06 Å` per atom via `--max-displacement`.
5. Run:

```bash
conda run -n base python <skill_root>/scripts/prepare_perturbed_dataset.py \
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
8. Stage 1 runs locally. No remote submission is needed.

## Stage 2: OpenMX Data Processing

1. Use `openmx-data-processing` to prepare split-local OpenMX inputs for the CIF datasets generated in Stage 1.
2. Submit the actual OpenMX jobs through `remote-task-submit`.
3. `remote-task-submit` is the sole authority for cluster-specific submission parameters such as queue, node shape, launcher, account, image, and runtime wrapper shape.
4. Do not hardcode site-specific OpenMX submission parameters in this pipeline skill.
5. Render split-local OpenMX workdirs from `openmx-data-processing/templates/openmx/`.
6. Submit the training split first. Submit the test split separately only when Stage 1 actually created a non-empty external test split.
7. Do not let multiple splits mutate one shared in-place OpenMX directory.
8. Default per-split OpenMX policy:
- default OpenMX task budget is `tasks=16`, `cpus-per-task=2`
- `omp_threads=2`
- default material parallelism is `16`
- material parallelism is auto-calculated from the task's total CPUs
- total CPUs must come from the submitted task budget
- detect total CPUs from SLURM first, then from explicit task environment variables
- if no task budget is exported at runtime, fall back to the canonical OpenMX default profile `16 * 2 = 32` CPUs
- do not infer total CPUs from the local interactive session CPU set
- explicit overrides are still allowed when needed
9. Stage 2 outputs:
- a training `.npz` path derived from the Stage 1 train CIF split
- an optional external test `.npz` path derived from the Stage 1 test CIF split when that split exists

## Stage 3: HamGNN Training

1. Use `hamgnn-training` to prepare the stage-local training config and runnable entry command.
2. Submit the actual HamGNN training job through `remote-task-submit`.
3. `remote-task-submit` is the sole authority for cluster-specific HamGNN submission parameters such as queue, accelerator request, image, launcher, and account mapping.
4. Do not hardcode site-specific HamGNN submission parameters in this pipeline skill.
5. Render a run-local training config from `hamgnn-training/templates/HamGNN/train_config.yaml.template` into `<work_root>/<target_dir>/HamGNN/`.
6. This stage consumes the training `.npz` from Stage 2.
7. Ordinary HamGNN training must keep `uni_model_pkl_path: null` unless the user explicitly asks to load a Uni model.
8. If the upstream OpenMX dataset includes `H0`, keep `add_H0: true` in the rendered config.
9. If Stage 2 produced an external test `.npz`, do not allocate an additional internal HamGNN test split from the training `.npz`.
10. Stage 3 output: the trained model or checkpoint path.

## Stage 4: HamGNN Test / Inference

1. Use `hamgnn-inference` to prepare the stage-local inference config and runnable entry command.
2. Submit the actual HamGNN inference job through `remote-task-submit`.
3. `remote-task-submit` is the sole authority for cluster-specific HamGNN inference submission parameters such as queue, accelerator request, image, launcher, and account mapping.
4. Do not hardcode site-specific inference submission parameters in this pipeline skill.
5. Render a run-local inference config from `hamgnn-inference/templates/HamGNN/test_config.yaml.template` into `<work_root>/<target_dir>/HamGNN/`.
6. This stage consumes:
- the trained model or checkpoint path from Stage 3
- the external test `.npz` from Stage 2
7. If Stage 2 did not produce an external test `.npz`, stop and report that the held-out test stage cannot run. Do not silently reuse the training `.npz` as the external test set.
8. Render the config so HamGNN runs with `stage: test` against the full external test `.npz`. Do not ask HamGNN to resplit that dataset internally.
9. Continue monitoring until inference is complete.
10. Stage 4 outputs:
- the rendered inference config path
- the inference submission record or job id summary
- prediction artifacts and test metrics emitted by HamGNN
- any output directory needed by downstream plotting or analysis stages

## Final Deliverables

1. Return the rendered training config path.
2. Return the rendered inference config path when Stage 4 runs.
3. Return the HamGNN training submission record or job id summary.
4. Return the HamGNN inference submission record or job id summary when Stage 4 runs.
5. Return the best checkpoint path when training completes.
6. Return the generated train `.npz` path, and return the external test `.npz` path when it exists.
7. Return the test prediction artifacts and metrics when Stage 4 runs successfully.
