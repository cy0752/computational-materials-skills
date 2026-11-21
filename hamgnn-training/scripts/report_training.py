#!/usr/bin/env python3
"""Plot HamGNN fit losses and evaluate the validation-selected checkpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from matplotlib.figure import Figure
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import torch

from hamgnn.main import (
    build_hamgnn_model,
    load_config,
    load_or_create_model,
    prepare_dataset,
    setup_trainer,
)


def plot_losses(run_dir: Path) -> None:
    events = EventAccumulator(str(run_dir), size_guidance={"scalars": 0}).Reload()
    figure = Figure(figsize=(8, 5), constrained_layout=True)
    axis = figure.subplots()
    for tag, label in (
        ("training/total_loss_epoch", "Training"),
        ("validation/total_loss", "Validation"),
    ):
        if tag not in events.Tags()["scalars"]:
            raise ValueError(f"Missing TensorBoard scalar {tag} in {run_dir}")
        values = events.Scalars(tag)
        axis.plot([point.step for point in values], [point.value for point in values],
                  marker=".", label=label)
    axis.set(xlabel="Training step", ylabel="Total loss")
    axis.legend()
    figure.savefig(run_dir / "training_curves.png", dpi=160)


def evaluate(config, checkpoint: Path, run_dir: Path, test_data: Path | None) -> dict:
    split_file = config.dataset_params.split_file
    if test_data is None and split_file is not None and not Path(split_file).is_file():
        raise FileNotFoundError(f"The recorded training split is missing: {split_file}")

    if test_data is not None:
        training_data = Path(config.dataset_params.graph_data_path).resolve()
        if training_data == test_data or training_data / "graph_data.npz" == test_data:
            raise ValueError("The separate test dataset must differ from the training dataset")
        config.dataset_params.graph_data_path = str(test_data)
        config.dataset_params.data_format = "auto"
        config.setup.stage = "test"

    data_module = prepare_dataset(config)
    data_module.setup("test")
    test_count = len(data_module.test_data)
    result = {
        "checkpoint": str(checkpoint),
        "test_dataset": str(Path(data_module.dataset_input).resolve()),
        "test_split_file": str(Path(split_file).resolve()) if test_data is None and split_file else None,
        "test_count": test_count,
        "metrics": {},
    }
    if test_count == 0:
        return result

    # Evaluate on one device so each test sample contributes exactly once.
    devices = config.setup.num_gpus
    if config.setup.get("accelerator") != "cpu" and devices and devices != "0":
        config.setup.accelerator = "gpu"
        config.setup.num_gpus = devices[:1] if isinstance(devices, (list, tuple)) else 1
    config.setup.resume = False
    config.setup.load_from_checkpoint = True
    config.setup.checkpoint_path = str(checkpoint)
    config.profiler_params.train_dir = str(run_dir / "evaluation")

    representation, output, post_processing = build_hamgnn_model(config)
    dtype = torch.float32 if config.setup.precision == 32 else torch.float64
    torch.set_default_dtype(dtype)
    model = load_or_create_model(
        config, representation.to(dtype), output.to(dtype), post_processing,
        config.losses_metrics.losses, config.losses_metrics.metrics,
    )
    trainer, _ = setup_trainer(config, callbacks=None)
    (metrics,) = trainer.test(model=model, datamodule=data_module)
    result["metrics"] = metrics
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Fit configuration")
    parser.add_argument("--run-dir", type=Path, required=True, help="TensorBoard run directory")
    parser.add_argument("--test-data", type=Path, help="Optional independent test dataset")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    candidates = sorted(path for path in (run_dir / "checkpoints").glob("*.ckpt")
                        if path.is_file() and path.name != "last.ckpt")
    if len(candidates) != 1:
        parser.error(f"Expected one validation-selected checkpoint in {run_dir / 'checkpoints'}")
    config = load_config(str(args.config))
    if config.setup.stage != "fit":
        parser.error("--config must be the configuration used for fitting")

    plot_losses(run_dir)
    test_data = args.test_data.resolve() if args.test_data is not None else None
    result = evaluate(config, candidates[0], run_dir, test_data)
    result["training_config"] = str(args.config.resolve())
    report = run_dir / "test_metrics.json"
    report.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
