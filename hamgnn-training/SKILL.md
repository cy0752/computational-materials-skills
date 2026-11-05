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
6. This stage consumes a training `.npz` or equivalent processed graph dataset. That dataset may come from the selected Stage 2 DFT route (`openmx-data-processing` or `abacus-data-processing`), or from an external preprocessing flow supplied by the user.
7. Render `__HAM_TYPE__` from the upstream route:
- OpenMX route -> `openmx`
- ABACUS route -> `abacus`
8. Apply the same rendered `__HAM_TYPE__` value to both `output_nets.HamGNN_out.ham_type` and `representation_nets.HamGNN_pre.radius_type`.
9. The main training config has no Uni-model option. HamGNN >= 2.3.0 moved Uni models to the separate `Uni-HamGNN` workflow (`Uni-HamiltonianPredictor.py` + `Input.yaml`); `uni_model_pkl_path` no longer exists. If the user asks for a Uni model, treat it as a dedicated out-of-band flow instead of rendering Uni keys here.
10. Keep `representation_nets.HamGNN_pre.legacy_edge_update: false` for fresh training. Set it to `true` only when resuming from a checkpoint trained before the HamGNN 2.3 edge-update fix.
11. This stage must emit the trained model or checkpoint path required by the inference stage.
12. Continue monitoring until training is complete. Since this stage is long-running, poll every 60 minutes.
13. `num_k` is the TOTAL number of k-path points (pythTB semantics), not points per segment; seekpath auto paths for real structures have more vertices than small `num_k` values and generation fails silently — use an explicit `k_path` with `num_k` larger than the path's vertex count.
14. Render `__NAO_MAX__` per route: OpenMX route accepts `14`, `19`, or `26`; ABACUS route accepts `13`, `27`, or `40`. `15` exists only on the ABACUS graph-generation side and has no training-side basis definition — `nao_max: 15` graphs fail at model build with `NotImplementedError`.
15. `scripts/train.sh` resolves its interpreter by conda env name only: `HAMGNN_CONDA_ENV` (default `HamGNN`; on activation failure it warns and falls back to `base`), located via `CONDA_BASE` or `conda` on `PATH`. It has no `PYTHON_BIN` override; when the target env lives outside the default envs directory, export `CONDA_ENVS_PATH` so the name resolves.
