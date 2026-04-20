#!/usr/bin/env python3
"""
Normalize a crystal structure file into a primitive-cell CIF.

Examples:
  python structure_to_cif.py --input POSCAR --output primitive.cif --primitive
  python structure_to_cif.py --input input.cif --output primitive.cif
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Convert a structure file into a primitive-cell CIF.'
    )
    parser.add_argument('--input', type=Path, required=True, help='Input structure file path.')
    parser.add_argument('--output', type=Path, required=True, help='Output CIF file path.')
    parser.add_argument(
        '--primitive',
        action='store_true',
        default=False,
        help='Reduce the structure to a primitive cell before writing CIF.',
    )
    parser.add_argument(
        '--symprec',
        type=float,
        default=1.0e-5,
        help='Symmetry tolerance used for primitive standardization.',
    )
    parser.add_argument(
        '--angle-tolerance',
        type=float,
        default=5.0,
        help='Angle tolerance used for primitive standardization.',
    )
    parser.add_argument(
        '--reader',
        choices=['auto', 'pymatgen', 'ase'],
        default='auto',
        help='Backend preference used to read the input structure.',
    )
    parser.add_argument('--quiet', action='store_true', help='Reduce stdout logs.')
    return parser.parse_args()


def infer_ase_format(path: Path) -> str | None:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name in {'poscar', 'contcar'} or suffix in {'.vasp', '.poscar', '.contcar'}:
        return 'vasp'
    if suffix == '.cif':
        return 'cif'
    if suffix == '.xsf':
        return 'xsf'
    return None


def load_with_pymatgen(path: Path) -> Structure:
    try:
        from pymatgen.core import Structure  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pymatgen is not installed. Install it first, for example with `pip install pymatgen`."
        ) from exc

    structure = Structure.from_file(str(path))
    if len(structure) == 0:
        raise ValueError(f'No atomic sites found in structure: {path}')
    return structure


def load_with_ase(path: Path) -> Structure:
    try:
        from ase.io import read  # type: ignore
        from pymatgen.io.ase import AseAtomsAdaptor  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "ASE or pymatgen is not installed. Install them first, for example with `pip install ase pymatgen`."
        ) from exc

    fmt = infer_ase_format(path)
    atoms = read(str(path), format=fmt)
    structure = AseAtomsAdaptor.get_structure(atoms)
    if len(structure) == 0:
        raise ValueError(f'No atomic sites found in structure: {path}')
    return structure


def load_structure(path: Path, reader: str) -> Structure:
    if not path.is_file():
        raise FileNotFoundError(f'Input structure file not found: {path}')

    errors: list[str] = []

    if reader in {'auto', 'pymatgen'}:
        try:
            return load_with_pymatgen(path)
        except Exception as exc:
            errors.append(f'pymatgen failed: {exc}')
            if reader == 'pymatgen':
                raise

    if reader in {'auto', 'ase'}:
        try:
            return load_with_ase(path)
        except Exception as exc:
            errors.append(f'ase failed: {exc}')
            if reader == 'ase':
                raise

    raise RuntimeError(
        'Cannot read input structure with the available backends.\n' + '\n'.join(errors)
    )


def to_primitive(structure: Structure, symprec: float, angle_tolerance: float) -> Structure:
    try:
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pymatgen is not installed. Install it first, for example with `pip install pymatgen`."
        ) from exc

    try:
        analyzer = SpacegroupAnalyzer(
            structure,
            symprec=symprec,
            angle_tolerance=angle_tolerance,
        )
        primitive = analyzer.get_primitive_standard_structure()
        if primitive is not None and len(primitive) > 0:
            return primitive
    except Exception:
        pass

    primitive = structure.get_primitive_structure()
    if primitive is None or len(primitive) == 0:
        raise RuntimeError('Failed to reduce the structure to a primitive cell.')
    return primitive


def main() -> int:
    args = parse_args()
    try:
        try:
            from pymatgen.io.cif import CifWriter  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pymatgen is not installed. Install it first, for example with `pip install pymatgen`."
            ) from exc

        structure = load_structure(args.input, args.reader)
        original_sites = len(structure)

        if args.primitive:
            structure = to_primitive(
                structure,
                symprec=args.symprec,
                angle_tolerance=args.angle_tolerance,
            )

        structure = structure.get_sorted_structure()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        CifWriter(structure).write_file(str(args.output))

        if not args.quiet:
            formula = structure.composition.reduced_formula
            print(f'Input: {args.input}')
            print(f'Output CIF: {args.output}')
            print(f'Formula: {formula}')
            print(f'Sites: {original_sites} -> {len(structure)}')
            print(f'Primitive reduction: {"on" if args.primitive else "off"}')
        return 0
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
