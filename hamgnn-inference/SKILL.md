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
12. For universal general-purpose inference, use the author-released `uni-hamgnn_2_1.pkl` (Zenodo record 17239078; md5 `7f99cba551b4a0cbb84827cfe359cdac`). Checksum a newly obtained weight file before first use. Load it through the Uni-HamGNN route (rule 13), not the main `test_config.yaml` route (rule 7).
13. For the universal weights, use the official `Uni-HamGNN` route (see rule 7 for why the main config has no Uni keys): start from the shipped `Uni-HamGNN/Input.yaml` example config and run the author's script directly — `python <HamGNN_repo>/Uni-HamGNN/Uni-HamiltonianPredictor.py --config <Input.yaml>` — with a config carrying `model_pkl_path`, `non_soc_data_dir`, `soc_data_dir`, `output_dir`, `device`, `calculate_mae`. The script must be executed as `__main__` (the pickle's top-level class is `__main__.HamiltonianPredictor`; importing it from another module breaks unpickling). It self-registers the `HamGNN_v_2_1.*` legacy package aliases and applies post-load attribute patches.
14. In the Uni-HamGNN config, disable SOC with `soc_data_dir: null` (YAML null), never the bare word `None`: YAML parses that as a string, which bypasses the script's None-guard and fails with `FileNotFoundError: 'None/graph_data.npz'`. The pkl ships dual SOC + non-SOC models; `null` selects the non-SOC path even though `soc_enabled=True` is baked into the pickle.
15. On newer environments (e3nn 0.5.6 / torch 2.5.0) the v2.1 pickle needs unpickle-compatibility shims in addition to the official `_patch_legacy_attributes` (which only patches post-load attributes): e3nn `CodeGenMixin.__setstate__` codegen-format migration (legacy bare torchscript bytes -> `(format, bytes)` tuples), torch 2.x Module container fields (`_backward_pre_hooks` etc.), `SphericalHarmonics.sph_func`, `LinearScaleWithWeights._cached_ones`, and `Activation.paths`. Install the shims first, then execute the official script via `runpy.run_path(..., run_name="__main__")`; do not modify the official script itself. A validated wrapper exists at `ky26049/agent_test/agent1_inference/04_rerun_true_weights/run_official_compat.py`. The v2.1 non-SOC model is single-channel (`collinear_spin=False`), `nao_max=26`.
16. `num_k` is the TOTAL number of k-path points (pythTB semantics), not points per segment; seekpath auto paths for real structures have more vertices than small `num_k` values and generation fails silently — use an explicit `k_path` with `num_k` larger than the path's vertex count.
