---
name: hamgnn-inference
description: Prepare HamGNN inference jobs and hand remote execution to the customizable `remote-task-submit` adapter.
---

# HamGNN Inference

## Standalone Use

This skill must remain independently usable outside `structure-openmx-hamgnn-training-pipeline`.

Use it whenever the user already has a trained HamGNN checkpoint and a held-out test dataset and wants to run evaluation without rerunning training.
Do not assume this skill was entered only from an upstream pipeline stage.

Minimum standalone inputs:

- a trained model or checkpoint path
- a processed external test graph dataset path such as a test `.npz`
- a target run directory for inference outputs
- a rendered `test_config.yaml`
- a remote execution path through `remote-task-submit`, or a local execution path if the user explicitly wants local runs

1. Start from `<skill_root>/templates/HamGNN/test_config.yaml.template`, then render a run-local config under `<target_dir>/HamGNN/`.
2. Use `remote-task-submit` for the actual remote submission. Keep queue, accelerator, image, account, and scheduler-specific launcher details inside `remote-task-submit`.
3. Use `<skill_root>/scripts/inference.sh --workdir <hamgnn_workdir> --config <rendered_test_config>` as the required runnable entrypoint for this stage.
4. Do not edit a shared global `HamGNN/test_config.yaml` in place.
5. This stage consumes:
- the trained model or checkpoint path from the training stage
- the test `.npz` generated in the OpenMX data-processing stage
- the inference config in `test_config.yaml`
6. When the input is a dedicated external test `.npz`, render the config so stage `test` consumes that entire dataset as the inference set. Do not ask HamGNN to split the external test dataset again.
7. For ordinary HamGNN inference, render `uni_model_pkl_path: null` by default. Only populate `uni_model_pkl_path` when the user explicitly asks to load a Uni model.
8. This stage must emit the prediction artifacts required by the band-structure plotting stage.
9. Continue monitoring until inference is complete.
