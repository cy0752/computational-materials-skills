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
- the test `.npz` generated in the Stage 2 DFT data-processing stage (OpenMX or ABACUS)
- the inference config in `test_config.yaml`
6. When the upstream pipeline already produced a dedicated test `.npz`, render the config so stage `test` consumes that entire dataset as the inference set. Do not ask HamGNN to split the external test dataset again.
7. The main inference config has no Uni-model option. HamGNN >= 2.3.0 moved Uni models to the separate `Uni-HamGNN` workflow; `uni_model_pkl_path` no longer exists. Do not render Uni keys in `test_config.yaml`.
8. The template hardcodes `ham_type: openmx` and `radius_type: openmx` as sample values only. Render both fields according to the checkpoint's training route: keep `openmx` for OpenMX-trained checkpoints, and override both to `abacus` for checkpoints trained through the ABACUS route (`structure-dft-hamgnn-training-pipeline` Stage 2B + `hamgnn-training` with `__HAM_TYPE__: abacus`). The two fields must always carry the same value; a mismatch makes HamGNN load an inconsistent model.
9. Render `representation_nets.HamGNN_pre.legacy_edge_update` according to the checkpoint: `true` for any checkpoint trained before the HamGNN 2.3 edge-update fix (the common case for pre-existing models), `false` only for models trained on HamGNN >= 2.3. A wrong value fails to load or silently degrades old checkpoints.
10. This stage must emit the prediction artifacts required by the band-structure plotting stage.
11. Continue monitoring until inference is complete.
