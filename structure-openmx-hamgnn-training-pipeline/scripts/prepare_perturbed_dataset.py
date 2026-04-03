#!/usr/bin/env python3
"""
Prepare a perturbed CIF dataset from one primitive CIF, then split it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Prepare perturbed CIF train/test datasets from an input CIF.'
    )
    parser.add_argument('--cif', type=Path, required=True, help='Input primitive CIF path.')
    parser.add_argument(
        '--workdir',
        type=Path,
        default=Path('./dataset_out'),
        help='Output working directory.',
    )
    parser.add_argument('--num-perturb', type=int, default=25)
    parser.add_argument('--rattle', type=float, default=0.02)
    parser.add_argument(
        '--perturb-mode',
        choices=['cartesian', 'fractional'],
        default='cartesian',
    )
    parser.add_argument(
        '--max-displacement',
        type=float,
        default=0.06,
        help='Per-atom hard cap for the perturbation displacement norm.',
    )
    parser.add_argument('--min-distance', type=float, default=None)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument(
        '--train-split-ratio',
        type=float,
        default=0.8,
        help='Train split ratio used to partition perturbed CIFs into train/test.',
    )
    parser.add_argument(
        '--train-output-dir',
        type=Path,
        default=None,
        help='Output dir for train CIF split. Default: <workdir>/train_cif',
    )
    parser.add_argument(
        '--test-output-dir',
        type=Path,
        default=None,
        help='Output dir for test CIF split. Default: <workdir>/test_cif',
    )
    parser.add_argument('--quiet', action='store_true')
    return parser.parse_args()


def run_cmd(cmd: List[str], quiet: bool) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not quiet and result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        err = result.stderr.strip() or 'unknown error'
        raise RuntimeError(f'Command failed: {" ".join(cmd)}\n{err}')
    if not quiet and result.stderr.strip():
        print(result.stderr.strip())


def prepare_cif_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for cif in path.glob('*.cif'):
        cif.unlink()


def split_perturbed_cifs(
    perturbed_dir: Path,
    ratio: float,
    train_dir: Path,
    test_dir: Path,
    quiet: bool,
) -> Dict[str, Any]:
    if ratio <= 0.0 or ratio > 1.0:
        raise ValueError('--train-split-ratio must be in the interval (0, 1].')

    perturbed_files = sorted(perturbed_dir.glob('*.cif'))
    if not perturbed_files:
        raise ValueError(f'No perturbed CIF found in: {perturbed_dir}')

    if len(perturbed_files) == 1 or ratio == 1.0:
        train_files = perturbed_files
        test_files: list[Path] = []
    else:
        n_total = len(perturbed_files)
        n_train = int(round(n_total * ratio))
        n_train = max(1, min(n_total - 1, n_train))
        train_files = perturbed_files[:n_train]
        test_files = perturbed_files[n_train:]

    prepare_cif_dir(train_dir)
    prepare_cif_dir(test_dir)

    for src in train_files:
        shutil.copy2(src, train_dir / src.name)
    for src in test_files:
        shutil.copy2(src, test_dir / src.name)

    split_info = {
        'enabled': True,
        'ratio': ratio,
        'perturbed_total': len(perturbed_files),
        'train_count': len(train_files),
        'test_count': len(test_files),
        'train_dir': str(train_dir.resolve()),
        'test_dir': str(test_dir.resolve()),
    }

    if not quiet:
        print(
            'Split perturbed CIFs: '
            f"total={split_info['perturbed_total']}, "
            f"train={split_info['train_count']}, "
            f"test={split_info['test_count']}"
        )
        print(f"Train CIF dir: {train_dir}")
        print(f"Test CIF dir: {test_dir}")

    return split_info


def main() -> int:
    args = parse_args()
    try:
        script_dir = Path(__file__).resolve().parent
        perturb_script = script_dir / 'generate_perturbed_cif.py'
        if not perturb_script.is_file():
            raise FileNotFoundError(
                f'Missing helper script in skill scripts directory: {perturb_script}'
            )

        args.workdir.mkdir(parents=True, exist_ok=True)

        if not args.cif.is_file():
            raise FileNotFoundError(f'Input CIF not found: {args.cif}')
        reference_cif = args.workdir / 'base_input.cif'
        shutil.copy2(args.cif, reference_cif)
        input_cif = str(args.cif.resolve())

        perturbed_dir = args.workdir / 'perturbed_cif'
        perturb_cmd = [
            sys.executable,
            str(perturb_script),
            '--num',
            str(args.num_perturb),
            '--stdev',
            str(args.rattle),
            '--mode',
            args.perturb_mode,
            '--output',
            str(perturbed_dir),
            '--prefix',
            'perturbed',
            '--seed',
            str(args.seed),
            '--max-displacement',
            str(args.max_displacement),
        ]
        perturb_cmd += ['--cif', str(reference_cif)]
        if args.min_distance is not None:
            perturb_cmd += ['--min-distance', str(args.min_distance)]
        if args.quiet:
            perturb_cmd.append('--quiet')
        run_cmd(perturb_cmd, quiet=args.quiet)

        train_output_dir = args.train_output_dir or (args.workdir / 'train_cif')
        test_output_dir = args.test_output_dir or (args.workdir / 'test_cif')
        split_info = split_perturbed_cifs(
            perturbed_dir=perturbed_dir,
            ratio=args.train_split_ratio,
            train_dir=train_output_dir,
            test_dir=test_output_dir,
            quiet=args.quiet,
        )

        manifest = {
            'input_cif': input_cif,
            'reference_cif': str(reference_cif.resolve()),
            'perturbed_cif_dir': str(perturbed_dir.resolve()),
            'num_perturb': args.num_perturb,
            'rattle': args.rattle,
            'perturb_mode': args.perturb_mode,
            'max_displacement': args.max_displacement,
            'min_distance': args.min_distance,
            'seed': args.seed,
            'train_split_ratio': args.train_split_ratio,
            'train_output_dir': str(train_output_dir.resolve()),
            'test_output_dir': str(test_output_dir.resolve()),
            'split': split_info,
        }
        manifest_path = args.workdir / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

        if not args.quiet:
            print('Dataset preparation completed.')
            print(f'Manifest: {manifest_path}')
            print(f'Reference CIF: {reference_cif}')
            print(f'Perturbed CIF dir: {perturbed_dir}')
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
