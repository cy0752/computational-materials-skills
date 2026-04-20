---
name: hamgnn-inference
description: Prepare and submit HamGNN inference jobs through the canonical HamGNN Inspire submit flow.
---

# HamGNN Inference

1. Start from `<skill_root>/templates/HamGNN/test_config.yaml.template`, then render a run-local config under `<target_dir>/HamGNN/`.
2. Use `inspire-hamgnn-submit` for the actual remote submission. `inspire-hamgnn-submit` is the sole authority for HamGNN workspace, GPU resource, image, and helper selection.
3. Use `<skill_root>/scripts/inference.sh --workdir <hamgnn_workdir> --config <rendered_test_config>` as the required runnable entrypoint for this stage.
4. Do not edit a shared global `HamGNN/test_config.yaml` in place.
5. This stage consumes:
- the trained model or checkpoint path from the training stage
- the test `.npz` generated in the OpenMX data-processing stage
- the inference config in `test_config.yaml`
6. When the upstream pipeline already produced a dedicated test `.npz`, render the config so stage `test` consumes that entire dataset as the inference set. Do not ask HamGNN to split the external test dataset again.
7. For ordinary HamGNN inference, render `uni_model_pkl_path: null` by default. Only populate `uni_model_pkl_path` when the user explicitly asks to load a Uni model.
8. This stage must emit the prediction artifacts required by the band-structure plotting stage.
9. Continue monitoring until inference is complete.
