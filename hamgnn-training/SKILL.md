---
name: hamgnn-training
description: Prepare HamGNN training jobs and hand remote execution to the customizable `remote-task-submit` adapter.
---

# HamGNN Training

## Standalone Use

This skill must remain independently usable outside `structure-openmx-hamgnn-training-pipeline`.

Use it whenever the user already has a HamGNN training dataset and wants to train a model without running the full structure-to-OpenMX pipeline first.
Do not assume this skill was entered only from an upstream pipeline stage.

Minimum standalone inputs:

- a training graph dataset path such as a processed `.npz`
- a target run directory for logs and checkpoints
- a rendered `train_config.yaml`
- a remote execution path through `remote-task-submit`, or a local execution path if the user explicitly wants local runs

1. Start from `<skill_root>/templates/HamGNN/train_config.yaml.template`, then render a run-local config under `<target_dir>/HamGNN/`.
2. Use `remote-task-submit` for the actual remote submission. Keep queue, accelerator, image, account, and scheduler-specific launcher details inside `remote-task-submit`.
3. Use `<skill_root>/scripts/train.sh --workdir <hamgnn_workdir> --config <rendered_train_config>` as the required runnable entrypoint for this stage.
4. Do not edit a shared global `HamGNN/train_config.yaml` in place.
5. When the input is a dedicated training `.npz`, render the config so it only creates an internal train/validation split inside that training dataset. Do not allocate an extra internal test split from the training `.npz`.
6. This stage consumes a training `.npz` or equivalent processed graph dataset. That dataset may come from `openmx-data-processing` or from an external preprocessing flow supplied by the user.
7. For ordinary HamGNN training, render `uni_model_pkl_path: null` by default. Only populate `uni_model_pkl_path` when the user explicitly asks to load a Uni model.
8. This stage must emit the trained model or checkpoint path required by the inference stage.
9. Continue monitoring until training is complete. Since this stage is long-running, poll every 60 minutes.
