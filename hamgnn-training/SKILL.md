---
name: hamgnn-training
description: Train HamGNN from labeled OpenMX or ABACUS graph data. Reuse the upstream dataset or ask where it is, prepare a training config, and run locally or through the HamGNN Inspire flow.
---

# HamGNN Training

## Start from the user's goal

- A request such as “帮我训练一个 Si HamGNN 模型” is enough to start. Reuse the requested dataset, a clearly associated project dataset such as `dataset/graph_data.npz`, or an upstream result. Ask for the graph data path only if it is missing or ambiguous. Use `structure-dft-hamgnn-training-pipeline` when the user wants to start from structures and generate training labels.
- Before starting training or submitting a job, show the effective GPU count, learning rate, epoch limit, batch size, data split, and output path. Ask the user to choose **Use these settings** or specify changes. Bundle any missing dataset question when the proposed settings can already be determined. Default to one GPU, `HamGNN_pre`, up to `200` epochs, batch size `1`, learning rate `0.0001`, and an isolated run in `work/train/`. Choose a fresh timestamped sibling if the default directory is occupied.
- Wait for the parameter choice before starting training or submission. Inspect inputs and prepare configs while waiting. If the interface cannot wait for an answer, ask in the reply and end the turn before launching. An explicit request to use defaults or run with the stated settings covers this choice. Reuse choices already confirmed by the parent pipeline.
- Inspect the graph count, labels, and metadata before rendering the config. Resolve `ham_type`, `nao_max`, SOC, spin channels, and H0 availability from the packing config and graph schema. For standard flattened graph matrices, infer `nao_max` from the square root of the overlap width and verify it agrees across the dataset and with the backend. Check the Hamiltonian fields and shapes against the inferred SOC and spin route. Set `add_H0` from compatible reference fields and render losses against the actual label fields. Ask only when a required compatibility choice is unresolved. For an explicit learning rate such as `0.01`, set `optim_params.lr` accordingly and disclose the separate `muon_lr` if the Muon optimizer is enabled.

## Data split

- For standalone training on one unsplit dataset, default to `80/10/10` train/validation/test. Save disjoint `train_idx`, `val_idx`, and `test_idx` arrays in a run-local `split.npz` and set `dataset_params.split_file` to it. Use a reproducible seed such as `42`. Round to whole graphs while keeping at least one in each group when there are at least three graphs. Three graphs yield a `1/1/1` demonstration and only a one-graph test result.
- Reuse supplied splits. When a dedicated training dataset or a separate test dataset is supplied, default to a `90/10` train/validation split within the training data and evaluate only on the separate test data if available. With just two graphs and no split, use one for training and one for validation. Report independent test metrics as unavailable when no test graphs are available. A validation-selected run needs both training and validation graphs, so ask for more data if that split is impossible.

## Execution

1. Start from `<skill_root>/templates/HamGNN/train_config.yaml.template`, then render `train_config.yaml` inside the chosen run directory. Keep the pipeline's own `HamGNN/` directory when called as a stage. Set `profiler_params.train_dir` to a run-local directory for TensorBoard logs and checkpoints.
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
11. Continue monitoring until training is complete and verify the deliverables below.
12. For band-energy training, `num_k` counts the total points across the entire k path. Use an explicit `k_path` with `num_k` larger than the path's vertex count.
13. Render `__NAO_MAX__` to a supported basis layout. OpenMX training supports `14`, `19`, and `26`. ABACUS training supports `13`, `27`, and `40`.
14. `scripts/train.sh` uses `HAMGNN_CONDA_ENV` (default `HamGNN`) and locates conda through `CONDA_BASE` or `PATH`. It falls back to `base` if activation fails. Export `CONDA_ENVS_PATH` when the environment is installed outside the default envs directory.

## Deliverables

- After a standalone run, use the training environment and the same workdir to run `python <skill_root>/scripts/report_training.py --config train_config.yaml --run-dir <profiler_train_dir>/version_N`. Pass `--test-data <path>` for a separate test dataset. For remote execution, run the report with the allocated GPU or as a follow-up evaluation job. Use the `version_N` created for this fit. Upstream fit tests the final weights, so the report reruns evaluation using the checkpoint saved for the minimum validation loss. Internal evaluation uses the recorded test indices.
- Return the best checkpoint, `training_curves.png`, `test_metrics.json`, `train_config.yaml`, and `log.out`. Also provide the split file when generated and state the train/validation/test counts. For use as a pipeline stage, honor the pipeline's requested deliverables.
