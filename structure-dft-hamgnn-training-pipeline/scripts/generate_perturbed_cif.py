#!/usr/bin/env python3
"""
Generate perturbed CIF structure(s) from an input CIF file.

Examples:
  # Single output from CIF
  python generate_perturbed_cif.py --cif input.cif --stdev 0.02 --seed 7 --output out.cif

  # Multiple outputs from CIF
  python generate_perturbed_cif.py --cif input.cif --num 50 --stdev 0.03 \
    --mode cartesian --output ./perturbed_set --prefix sample
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

import numpy as np
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate perturbed CIF files from an input CIF file.'
    )
    parser.add_argument('--cif', type=Path, required=True, help='Input CIF file path.')

    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output path. If --num>1, can be a directory or a .cif template path.',
    )
    parser.add_argument(
        '--prefix',
        default='perturbed',
        help='Filename prefix when writing multiple CIF files.',
    )
    parser.add_argument('--num', type=int, default=1, help='Number of perturbed structures.')
    parser.add_argument(
        '--stdev',
        type=float,
        default=0.01,
        help='Gaussian perturbation strength (Ang for cartesian, frac for fractional).',
    )
    parser.add_argument(
        '--mode',
        choices=['cartesian', 'fractional'],
        default='cartesian',
        help='Apply perturbation in cartesian or fractional coordinates.',
    )
    parser.add_argument(
        '--max-displacement',
        type=float,
        default=None,
        help='Optional per-atom displacement norm cap (same unit as --mode).',
    )
    parser.add_argument(
        '--min-distance',
        type=float,
        default=None,
        help='Reject structures with any inter-atomic distance below this value (Ang).',
    )
    parser.add_argument(
        '--max-attempts',
        type=int,
        default=50,
        help='Max retries per output when min-distance rejection is active.',
    )
    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility.')
    parser.add_argument(
        '--zero-mean',
        action='store_true',
        help='Subtract average displacement to avoid global translation.',
    )
    parser.add_argument(
        '--wrap',
        action='store_true',
        default=True,
        help='Wrap atoms back into the periodic cell (default: on).',
    )
    parser.add_argument(
        '--no-wrap',
        dest='wrap',
        action='store_false',
        help='Disable wrapping.',
    )
    parser.add_argument('--quiet', action='store_true', help='Reduce stdout logs.')
    return parser.parse_args()


def structure_from_input(args: argparse.Namespace) -> Structure:
    if not args.cif.is_file():
        raise FileNotFoundError(f'CIF file not found: {args.cif}')
    return Structure.from_file(str(args.cif))


def clip_displacements(displacements: np.ndarray, max_norm: float | None) -> np.ndarray:
    if max_norm is None:
        return displacements
    if max_norm <= 0:
        raise ValueError('max-displacement must be > 0 when provided.')

    clipped = displacements.copy()
    norms = np.linalg.norm(clipped, axis=1)
    mask = norms > max_norm
    if np.any(mask):
        clipped[mask] *= (max_norm / norms[mask])[:, None]
    return clipped


def min_interatomic_distance(structure: Structure) -> float:
    if len(structure) <= 1:
        return float('inf')
    distances = np.array(structure.distance_matrix, copy=True)
    np.fill_diagonal(distances, np.inf)
    return float(np.min(distances))


def generate_single_perturbation(
    base_structure: Structure,
    args: argparse.Namespace,
    rng: np.random.Generator,
) -> Tuple[Structure, float]:
    num_atoms = len(base_structure)
    if num_atoms == 0:
        raise ValueError('Input structure has no atoms.')

    lattice = base_structure.lattice
    species = list(base_structure.species)
    frac_positions = np.array(base_structure.frac_coords)
    cart_positions = np.array(base_structure.cart_coords)
    cell = np.array(lattice.matrix)

    if args.mode == 'cartesian':
        displacements = rng.normal(0.0, args.stdev, size=(num_atoms, 3))
        if args.zero_mean:
            displacements -= np.mean(displacements, axis=0, keepdims=True)
        displacements = clip_displacements(displacements, args.max_displacement)

        perturbed_positions = cart_positions + displacements
        if args.wrap:
            perturbed_frac = np.linalg.solve(cell.T, perturbed_positions.T).T % 1.0
            perturbed = Structure(
                lattice=lattice,
                species=species,
                coords=perturbed_frac,
                coords_are_cartesian=False,
                to_unit_cell=False,
            )
        else:
            perturbed = Structure(
                lattice=lattice,
                species=species,
                coords=perturbed_positions,
                coords_are_cartesian=True,
                to_unit_cell=False,
            )
        max_disp_ang = float(np.max(np.linalg.norm(displacements, axis=1)))
        return perturbed, max_disp_ang

    frac_displacements = rng.normal(0.0, args.stdev, size=(num_atoms, 3))
    if args.zero_mean:
        frac_displacements -= np.mean(frac_displacements, axis=0, keepdims=True)
    frac_displacements = clip_displacements(frac_displacements, args.max_displacement)

    perturbed_frac_positions = frac_positions + frac_displacements
    if args.wrap:
        perturbed_frac_positions %= 1.0
    perturbed = Structure(
        lattice=lattice,
        species=species,
        coords=perturbed_frac_positions,
        coords_are_cartesian=False,
        to_unit_cell=False,
    )

    cart_displacements = frac_displacements @ cell
    max_disp_ang = float(np.max(np.linalg.norm(cart_displacements, axis=1)))
    return perturbed, max_disp_ang


def resolve_output_paths(args: argparse.Namespace) -> List[Path]:
    if args.num <= 0:
        raise ValueError('--num must be >= 1.')

    output = args.output
    if args.num == 1 and output.suffix.lower() == '.cif':
        output.parent.mkdir(parents=True, exist_ok=True)
        return [output]

    if output.suffix.lower() == '.cif':
        out_dir = output.parent
        prefix = output.stem
    else:
        out_dir = output
        prefix = args.prefix

    out_dir.mkdir(parents=True, exist_ok=True)
    return [out_dir / f'{prefix}_{idx + 1:04d}.cif' for idx in range(args.num)]


def main() -> int:
    args = parse_args()
    try:
        base_structure = structure_from_input(args)
        output_paths = resolve_output_paths(args)
        rng = np.random.default_rng(args.seed)

        if not args.quiet:
            print(f'Atoms: {len(base_structure)}')
            print(f'Mode: {args.mode}, stdev={args.stdev}, num={len(output_paths)}')
            if args.seed is not None:
                print(f'Seed: {args.seed}')

        for index, out_path in enumerate(output_paths, start=1):
            perturbed = None
            max_disp = None
            last_min_dist = None

            for _ in range(args.max_attempts):
                candidate, candidate_max_disp = generate_single_perturbation(base_structure, args, rng)
                current_min_dist = min_interatomic_distance(candidate)
                last_min_dist = current_min_dist
                if args.min_distance is None or current_min_dist >= args.min_distance:
                    perturbed = candidate
                    max_disp = candidate_max_disp
                    break

            if perturbed is None:
                raise RuntimeError(
                    f'Failed to generate sample {index} after {args.max_attempts} attempts '
                    f'(last min distance={last_min_dist:.6f} Ang).'
                )

            CifWriter(perturbed).write_file(str(out_path))
            if not args.quiet:
                min_dist = min_interatomic_distance(perturbed)
                print(
                    f'[{index}/{len(output_paths)}] Wrote {out_path} '
                    f'(max_disp={max_disp:.6f} Ang, min_dist={min_dist:.6f} Ang)'
                )

        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
