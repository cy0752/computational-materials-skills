---
name: hamgnn-training
description: Prepare HamGNN training configs and run locally or submit through the canonical HamGNN Inspire flow.
---

# HamGNN Training

1. Start from `<skill_root>/templates/HamGNN/train_config.yaml.template`, then render a run-local config under `<target_dir>/HamGNN/`.
2. Use `inspire-hamgnn-submit` for the actual remote submission. `inspire-hamgnn-submit` is the sole authority for HamGNN workspace, GPU resource, image, and helper selection.
3. Use `<skill_root>/scripts/train.sh --workdir <hamgnn_workdir> --config <rendered_train_config>` as the required runnable entrypoint for this stage.
4. Do not edit a shared global `HamGNN/train_config.yaml` in place.
5. When the upstream pipeline already produced a dedicated training `.npz`, render the config so it only creates an internal train/validation split inside that training dataset. Do not allocate an extra internal test split from the training `.npz`.
6. This stage consumes the training `.npz` generated from the selected Stage 2 DFT route (OpenMX or ABACUS).
7. Render `__HAM_TYPE__` from the upstream route:
- OpenMX route -> `openmx`
- ABACUS route -> `abacus`
8. Apply the same rendered `__HAM_TYPE__` value to both `output_nets.HamGNN_out.ham_type` and `representation_nets.HamGNN_pre.radius_type`.
9. Local runtime env policy: prefer conda env `HamGNN`; if it is unavailable, fall back to `base`. Do not create new envs unless explicitly requested.
10. For ordinary HamGNN training, render `uni_model_pkl_path: null` by default. Only populate `uni_model_pkl_path` when the user explicitly asks to load a Uni model.
11. This stage must emit the trained model or checkpoint path required by the inference stage.
12. Continue monitoring until training is complete. Since this stage is long-running, poll every 60 minutes.
