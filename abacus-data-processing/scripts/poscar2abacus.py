# Copyright (c) 2021-2026 HamGNN Team
# SPDX-License-Identifier: GPL-3.0-only

"""Generate per-structure ABACUS INPUT/KPT/STRU case directories."""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple

import natsort
import numpy as np
import yaml
from ase import Atoms
from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Structure
from pymatgen.io.ase import AseAtomsAdaptor


PP_DICT = {
    'Ag':'Ag_ONCV_PBE-1.0.upf',  'Co':'Co_ONCV_PBE-1.0.upf',  'Ir':'Ir_ONCV_PBE-1.0.upf',  'Os':'Os_ONCV_PBE-1.0.upf',  'S' :'S_ONCV_PBE-1.0.upf',
    'Al':'Al_ONCV_PBE-1.0.upf',  'Cr':'Cr_ONCV_PBE-1.0.upf',  'K' :'K_ONCV_PBE-1.0.upf',   'Pb':'Pb_ONCV_PBE-1.0.upf',  'Sr':'Sr_ONCV_PBE-1.0.upf',
    'Ar':'Ar_ONCV_PBE-1.0.upf',  'Cs':'Cs_ONCV_PBE-1.0.upf',  'Kr':'Kr_ONCV_PBE-1.0.upf',  'Pd':'Pd_ONCV_PBE-1.0.upf',  'Ta':'Ta_ONCV_PBE-1.0.upf',
    'As':'As_ONCV_PBE-1.0.upf',  'Cu':'Cu_ONCV_PBE-1.0.upf',  'La':'La_ONCV_PBE-1.0.upf',  'P' :'P_ONCV_PBE-1.0.upf',   'Tc':'Tc_ONCV_PBE-1.0.upf',
    'Au':'Au_ONCV_PBE-1.0.upf',  'Fe':'Fe_ONCV_PBE-1.0.upf',  'Li':'Li_ONCV_PBE-1.0.upf',  'Pt':'Pt_ONCV_PBE-1.0.upf',  'Te':'Te_ONCV_PBE-1.0.upf',
    'Ba':'Ba_ONCV_PBE-1.0.upf',  'F' :'F_ONCV_PBE-1.0.upf',   'Mg':'Mg_ONCV_PBE-1.0.upf',  'Rb':'Rb_ONCV_PBE-1.0.upf',  'Ti':'Ti_ONCV_PBE-1.0.upf',
    'Be':'Be_ONCV_PBE-1.0.upf',  'Ga':'Ga_ONCV_PBE-1.0.upf',  'Mn':'Mn_ONCV_PBE-1.0.upf',  'Re':'Re_ONCV_PBE-1.0.upf',  'Tl':'Tl_ONCV_PBE-1.0.upf',
    'Bi':'Bi_ONCV_PBE-1.0.upf',  'Ge':'Ge_ONCV_PBE-1.0.upf',  'Mo':'Mo_ONCV_PBE-1.0.upf',  'Rh':'Rh_ONCV_PBE-1.0.upf',  'V' :'V_ONCV_PBE-1.0.upf',
    'B' :'B_ONCV_PBE-1.0.upf',   'He':'He_ONCV_PBE-1.0.upf',  'Na':'Na_ONCV_PBE-1.0.upf',  'Ru':'Ru_ONCV_PBE-1.0.upf',  'W' :'W_ONCV_PBE-1.0.upf',
    'Br':'Br_ONCV_PBE-1.0.upf',  'Hf':'Hf_ONCV_PBE-1.0.upf',  'Nb':'Nb_ONCV_PBE-1.0.upf',  'Sb':'Sb_ONCV_PBE-1.0.upf',  'Xe':'Xe_ONCV_PBE-1.0.upf',
    'Ca':'Ca_ONCV_PBE-1.0.upf',  'Hg':'Hg_ONCV_PBE-1.0.upf',  'Ne':'Ne_ONCV_PBE-1.0.upf',  'Sc':'Sc_ONCV_PBE-1.0.upf',  'Y' :'Y_ONCV_PBE-1.0.upf',
    'Cd':'Cd_ONCV_PBE-1.0.upf',  'H' :'H_ONCV_PBE-1.0.upf',   'Ni':'Ni_ONCV_PBE-1.0.upf',  'Se':'Se_ONCV_PBE-1.0.upf',  'Zn':'Zn_ONCV_PBE-1.0.upf',
    'Cl':'Cl_ONCV_PBE-1.0.upf',  'In':'In_ONCV_PBE-1.0.upf',  'N' :'N_ONCV_PBE-1.0.upf',   'Si':'Si_ONCV_PBE-1.0.upf',  'Zr':'Zr_ONCV_PBE-1.0.upf',
    'C' :'C_ONCV_PBE-1.0.upf',   'I' :'I_ONCV_PBE-1.0.upf',   'O' :'O_ONCV_PBE-1.0.upf',   'Sn':'Sn_ONCV_PBE-1.0.upf'
}

ORB_DICT = {
    'Ag':'Ag_gga_7au_100Ry_4s2p2d1f.orb',   'Cu':'Cu_gga_8au_100Ry_4s2p2d1f.orb',    'Mo':'Mo_gga_7au_100Ry_4s2p2d1f.orb',  'Sc':'Sc_gga_8au_100Ry_4s2p2d1f.orb',
    'Al':'Al_gga_7au_100Ry_4s4p1d.orb',     'Fe':'Fe_gga_8au_100Ry_4s2p2d1f.orb',    'Na':'Na_gga_8au_100Ry_4s2p1d.orb',    'Se':'Se_gga_8au_100Ry_2s2p1d.orb',
    'Ar':'Ar_gga_7au_100Ry_2s2p1d.orb',     'F' :'F_gga_7au_100Ry_2s2p1d.orb',       'Nb':'Nb_gga_8au_100Ry_4s2p2d1f.orb',  'S' :'S_gga_7au_100Ry_2s2p1d.orb',
    'As':'As_gga_7au_100Ry_2s2p1d.orb',     'Ga':'Ga_gga_8au_100Ry_2s2p2d1f.orb',    'Ne':'Ne_gga_6au_100Ry_2s2p1d.orb',    'Si':'Si_gga_7au_100Ry_2s2p1d.orb',
    'Au':'Au_gga_7au_100Ry_4s2p2d1f.orb',   'Ge':'Ge_gga_8au_100Ry_2s2p2d1f.orb',    'N' :'N_gga_7au_100Ry_2s2p1d.orb',     'Sn':'Sn_gga_7au_100Ry_2s2p2d1f.orb',
    'Ba':'Ba_gga_10au_100Ry_4s2p2d1f.orb',  'He':'He_gga_6au_100Ry_2s1p.orb',        'Ni':'Ni_gga_8au_100Ry_4s2p2d1f.orb',  'Sr':'Sr_gga_9au_100Ry_4s2p1d.orb',
    'Be':'Be_gga_7au_100Ry_4s1p.orb',       'Hf':'Hf_gga_7au_100Ry_4s2p2d2f1g.orb',  'O' :'O_gga_7au_100Ry_2s2p1d.orb',     'Ta':'Ta_gga_8au_100Ry_4s2p2d2f1g.orb',
    'B' :'B_gga_8au_100Ry_2s2p1d.orb',      'H' :'H_gga_6au_100Ry_2s1p.orb',         'Os':'Os_gga_7au_100Ry_4s2p2d1f.orb',  'Tc':'Tc_gga_7au_100Ry_4s2p2d1f.orb',
    'Bi':'Bi_gga_7au_100Ry_2s2p2d1f.orb',   'Hg':'Hg_gga_9au_100Ry_4s2p2d1f.orb',    'Pb':'Pb_gga_7au_100Ry_2s2p2d1f.orb',  'Te':'Te_gga_7au_100Ry_2s2p2d1f.orb',
    'Br':'Br_gga_7au_100Ry_2s2p1d.orb',     'I' :'I_gga_7au_100Ry_2s2p2d1f.orb',     'Pd':'Pd_gga_7au_100Ry_4s2p2d1f.orb',  'Ti':'Ti_gga_8au_100Ry_4s2p2d1f.orb',
    'Ca':'Ca_gga_9au_100Ry_4s2p1d.orb',     'In':'In_gga_7au_100Ry_2s2p2d1f.orb',    'P' :'P_gga_7au_100Ry_2s2p1d.orb',     'Tl':'Tl_gga_7au_100Ry_2s2p2d1f.orb',
    'Cd':'Cd_gga_7au_100Ry_4s2p2d1f.orb',   'Ir':'Ir_gga_7au_100Ry_4s2p2d1f.orb',    'Pt':'Pt_gga_7au_100Ry_4s2p2d1f.orb',  'V' :'V_gga_8au_100Ry_4s2p2d1f.orb',
    'C' :'C_gga_7au_100Ry_2s2p1d.orb',      'K' :'K_gga_9au_100Ry_4s2p1d.orb',       'Rb':'Rb_gga_10au_100Ry_4s2p1d.orb',   'W' :'W_gga_8au_100Ry_4s2p2d2f1g.orb',
    'Cl':'Cl_gga_7au_100Ry_2s2p1d.orb',     'Kr':'Kr_gga_7au_100Ry_2s2p1d.orb',      'Re':'Re_gga_7au_100Ry_4s2p2d1f.orb',  'Xe':'Xe_gga_8au_100Ry_2s2p2d1f.orb',
    'Co':'Co_gga_8au_100Ry_4s2p2d1f.orb',   'Li':'Li_gga_7au_100Ry_4s1p.orb',        'Rh':'Rh_gga_7au_100Ry_4s2p2d1f.orb',  'Y' :'Y_gga_8au_100Ry_4s2p2d1f.orb',
    'Cr':'Cr_gga_8au_100Ry_4s2p2d1f.orb',   'Mg':'Mg_gga_8au_100Ry_4s2p1d.orb',      'Ru':'Ru_gga_7au_100Ry_4s2p2d1f.orb',  'Zn':'Zn_gga_8au_100Ry_4s2p2d1f.orb',
    'Cs':'Cs_gga_10au_100Ry_4s2p1d.orb',    'Mn':'Mn_gga_8au_100Ry_4s2p2d1f.orb',    'Sb':'Sb_gga_7au_100Ry_2s2p2d1f.orb',  'Zr':'Zr_gga_8au_100Ry_4s2p2d1f.orb'
}

UNRENDERED_PLACEHOLDER = re.compile(r"__[A-Z0-9_]+__")
DEFAULT_MOVE_FLAGS = (1, 1, 1)
DEFAULT_KPT = {
    "mode": "Gamma",
    "mesh": (4, 4, 4),
    "shift": (0, 0, 0),
}
VALID_RUN_DIR_NAMING = {"index_stem", "index", "stem"}


@dataclass
class CaseJob:
    index: int
    source_path: Path
    case_name: str
    atoms: Atoms
    species: Tuple[str, ...]


@dataclass
class GeneratorConfig:
    system_name: str
    structure_globs: List[str]
    output_root: Path
    run_dir_naming: str
    overwrite: bool
    copy_source_file: bool
    orbital_subdir_pattern: Optional[str]
    move_flags: Tuple[int, int, int]
    input_params: dict
    kpt_mode: str
    kpt_mesh: Tuple[int, int, int]
    kpt_shift: Tuple[float, float, float]
    dry_run: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate ABACUS case directories from structure files.")
    parser.add_argument("--config", type=str, help="Path to abacus_input_gen.yaml.")
    parser.add_argument(
        "--input-glob",
        dest="input_globs",
        action="append",
        help="Glob of structure files. Can be passed multiple times; overrides structure_glob in config.",
    )
    parser.add_argument("--output-root", type=str, help="Output root for generated case directories.")
    parser.add_argument("--system-name", type=str, help="System name used for INPUT suffix fallback.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing case directories.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print planned case generation only.")
    return parser.parse_args()


def _ensure_mapping(value: Any, field: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"'{field}' must be a mapping in config.")
    return dict(value)


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    raise ValueError(f"'{field}' must be a boolean value.")


def _parse_triplet(
    value: Any,
    field: str,
    cast_fn,
    *,
    require_positive: bool = False,
) -> Tuple[Any, Any, Any]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"'{field}' must be a length-3 list.")
    parsed: List[Any] = []
    for idx, item in enumerate(value):
        try:
            converted = cast_fn(item)
        except Exception as exc:  # pylint: disable=broad-except
            raise ValueError(f"'{field}[{idx}]' has invalid value: {item}") from exc
        if require_positive and converted <= 0:
            raise ValueError(f"'{field}[{idx}]' must be > 0.")
        parsed.append(converted)
    return parsed[0], parsed[1], parsed[2]


def _parse_move_flags(value: Any) -> Tuple[int, int, int]:
    flags = _parse_triplet(value, "move_flags", int)
    for idx, flag in enumerate(flags):
        if flag not in (0, 1):
            raise ValueError(f"'move_flags[{idx}]' must be 0 or 1.")
    return flags


def _contains_unrendered_placeholder(text: str) -> bool:
    return bool(UNRENDERED_PLACEHOLDER.search(text))


def _resolve_path(path_like: str, *, base_dir: Path) -> Path:
    if _contains_unrendered_placeholder(path_like):
        raise ValueError(f"Unrendered placeholder found in path: {path_like}")
    path = Path(path_like).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_config(config_path: Optional[Path]) -> dict:
    if config_path is None:
        return {}
    with config_path.open("r", encoding="utf-8") as fp:
        loaded = yaml.safe_load(fp) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Config root must be a mapping.")
    return loaded


def _normalize_globs(raw_globs: Any) -> List[str]:
    if raw_globs is None:
        return []
    if isinstance(raw_globs, str):
        globs = [raw_globs]
    elif isinstance(raw_globs, (list, tuple)):
        if not all(isinstance(item, str) for item in raw_globs):
            raise ValueError("'structure_glob' list must contain only strings.")
        globs = list(raw_globs)
    else:
        raise ValueError("'structure_glob' must be a string or list of strings.")
    normalized = [item.strip() for item in globs if item and item.strip()]
    if not normalized:
        raise ValueError("'structure_glob' resolved to an empty list.")
    return normalized


def build_generator_config(args: argparse.Namespace, raw_config: dict, *, config_base_dir: Path) -> GeneratorConfig:
    input_globs = args.input_globs if args.input_globs else None
    structure_globs = _normalize_globs(input_globs if input_globs is not None else raw_config.get("structure_glob"))

    output_root_raw = args.output_root if args.output_root else raw_config.get("output_root")
    if not output_root_raw:
        raise ValueError("Missing output_root. Provide it via config or --output-root.")
    output_root = _resolve_path(str(output_root_raw), base_dir=config_base_dir)

    run_dir_naming = str(raw_config.get("run_dir_naming", "index_stem")).strip()
    if run_dir_naming not in VALID_RUN_DIR_NAMING:
        raise ValueError(
            f"Unsupported run_dir_naming: {run_dir_naming}. "
            f"Supported values: {', '.join(sorted(VALID_RUN_DIR_NAMING))}."
        )

    system_name = str(args.system_name if args.system_name else raw_config.get("system_name", "ABACUS")).strip() or "ABACUS"
    overwrite = _parse_bool(raw_config.get("overwrite", False), "overwrite")
    if args.overwrite:
        overwrite = True
    copy_source_file = _parse_bool(raw_config.get("copy_source_file", True), "copy_source_file")
    move_flags = _parse_move_flags(raw_config.get("move_flags", DEFAULT_MOVE_FLAGS))

    orbital_subdir_pattern_raw = raw_config.get("orbital_subdir_pattern")
    orbital_subdir_pattern: Optional[str]
    if orbital_subdir_pattern_raw is None:
        orbital_subdir_pattern = None
    else:
        orbital_subdir_pattern = str(orbital_subdir_pattern_raw).strip()
        if orbital_subdir_pattern == "":
            orbital_subdir_pattern = None

    input_params = _ensure_mapping(raw_config.get("input"), "input")
    input_params.setdefault("stru_file", "STRU")
    input_params.setdefault("kpoint_file", "KPT")
    if args.system_name:
        input_params["suffix"] = system_name
    else:
        input_params.setdefault("suffix", system_name)

    kpt_config = _ensure_mapping(raw_config.get("kpt"), "kpt")
    kpt_mode = str(kpt_config.get("mode", DEFAULT_KPT["mode"])).strip() or DEFAULT_KPT["mode"]
    kpt_mesh = _parse_triplet(kpt_config.get("mesh", DEFAULT_KPT["mesh"]), "kpt.mesh", int, require_positive=True)
    kpt_shift = _parse_triplet(kpt_config.get("shift", DEFAULT_KPT["shift"]), "kpt.shift", float)

    return GeneratorConfig(
        system_name=system_name,
        structure_globs=structure_globs,
        output_root=output_root,
        run_dir_naming=run_dir_naming,
        overwrite=overwrite,
        copy_source_file=copy_source_file,
        orbital_subdir_pattern=orbital_subdir_pattern,
        move_flags=move_flags,
        input_params=input_params,
        kpt_mode=kpt_mode,
        kpt_mesh=kpt_mesh,
        kpt_shift=kpt_shift,
        dry_run=args.dry_run,
    )


def resolve_structure_files(globs_to_expand: Sequence[str], *, base_dir: Path) -> List[Path]:
    matched: List[str] = []
    for pattern in globs_to_expand:
        if _contains_unrendered_placeholder(pattern):
            raise ValueError(f"Unrendered placeholder found in structure_glob: {pattern}")
        pattern_path = Path(pattern).expanduser()
        expanded_pattern = str(pattern_path if pattern_path.is_absolute() else base_dir / pattern_path)
        matched.extend(glob.glob(expanded_pattern, recursive=True))

    unique_paths = sorted({str(Path(path).resolve()) for path in matched})
    sorted_paths = natsort.natsorted(unique_paths)
    if not sorted_paths:
        raise FileNotFoundError(
            f"structure_glob matched zero files (patterns={list(globs_to_expand)}). "
            "Stop by policy (fail-fast)."
        )
    return [Path(path) for path in sorted_paths]


def _sanitize_stem(stem: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "_", stem).strip("._")
    return cleaned if cleaned else "structure"


def build_case_name(index: int, source_path: Path, naming: str) -> str:
    stem = _sanitize_stem(source_path.stem)
    if naming == "index":
        return str(index)
    if naming == "stem":
        return stem
    return f"{index}_{stem}"


def wrap_positions_to_cell(atoms: Atoms) -> None:
    cell = atoms.get_cell().array
    if cell.shape != (3, 3):
        return
    if np.linalg.det(cell) == 0.0:
        return
    positions = atoms.get_positions()
    direct = positions @ np.linalg.inv(cell)
    direct = direct - np.floor(direct)
    atoms.set_positions(direct @ cell)


def collect_jobs(files: Sequence[Path], config: GeneratorConfig) -> List[CaseJob]:
    jobs: List[CaseJob] = []
    missing_pp = set()
    missing_orb = set()
    case_name_set = set()
    duplicated_case_names = set()
    basis_type = str(config.input_params.get("basis_type", "lcao")).strip().lower()
    require_orbital = basis_type == "lcao"

    for index, source_path in enumerate(files, start=1):
        try:
            crystal = Structure.from_file(str(source_path))
            atoms = AseAtomsAdaptor.get_atoms(crystal)
        except Exception as exc:  # pylint: disable=broad-except
            raise RuntimeError(f"Failed to read structure file: {source_path}") from exc

        wrap_positions_to_cell(atoms)
        species = tuple(sorted(set(atoms.get_chemical_symbols())))

        for symbol in species:
            if symbol not in PP_DICT:
                missing_pp.add(symbol)
            if require_orbital and symbol not in ORB_DICT:
                missing_orb.add(symbol)

        case_name = build_case_name(index, source_path, config.run_dir_naming)
        if case_name in case_name_set:
            duplicated_case_names.add(case_name)
        case_name_set.add(case_name)

        jobs.append(
            CaseJob(
                index=index,
                source_path=source_path,
                case_name=case_name,
                atoms=atoms,
                species=species,
            )
        )

    if missing_pp:
        symbols = ", ".join(sorted(missing_pp))
        raise RuntimeError(f"Missing PP_DICT mapping for elements: {symbols}")
    if missing_orb:
        symbols = ", ".join(sorted(missing_orb))
        raise RuntimeError(f"Missing ORB_DICT mapping for elements: {symbols}")
    if duplicated_case_names:
        duplicates = ", ".join(sorted(duplicated_case_names))
        raise RuntimeError(
            f"Duplicate case directory names detected with run_dir_naming='{config.run_dir_naming}': {duplicates}"
        )

    if not config.overwrite:
        existing = [job.case_name for job in jobs if (config.output_root / job.case_name).exists()]
        if existing:
            preview = ", ".join(existing[:10])
            extra = "" if len(existing) <= 10 else f" ... (+{len(existing) - 10} more)"
            raise FileExistsError(
                f"Target case directories already exist under {config.output_root}: {preview}{extra}. "
                "Set overwrite=true in config or pass --overwrite."
            )

    return jobs


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return format(value, ".15g")
    return str(value)


def _format_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return " ".join(_format_scalar(item) for item in value)
    return _format_scalar(value)


def render_orbital_entry(symbol: str, orbital_subdir_pattern: Optional[str]) -> str:
    orbital_name = ORB_DICT[symbol]
    if not orbital_subdir_pattern:
        return orbital_name
    try:
        subdir = orbital_subdir_pattern.format(symbol=symbol).strip().strip("/")
    except Exception as exc:  # pylint: disable=broad-except
        raise ValueError(
            f"Invalid orbital_subdir_pattern '{orbital_subdir_pattern}'. "
            "It should support '{symbol}' placeholder."
        ) from exc
    if not subdir:
        return orbital_name
    return f"{subdir}/{orbital_name}"


def generate_stru_text(
    atoms: Atoms,
    species: Iterable[str],
    *,
    basis_type: str,
    move_flags: Tuple[int, int, int],
    orbital_subdir_pattern: Optional[str],
) -> str:
    chemical_symbols = atoms.get_chemical_symbols()
    positions = atoms.get_positions()
    cell = atoms.get_cell().array

    lines: List[str] = ["ATOMIC_SPECIES"]
    for symbol in species:
        lines.append(f"{symbol:2s} {float(Element(symbol).atomic_mass):8.4f}  {PP_DICT[symbol]}")

    if basis_type == "lcao":
        lines.append("")
        lines.append("NUMERICAL_ORBITAL")
        for symbol in species:
            lines.append(render_orbital_entry(symbol, orbital_subdir_pattern))

    lines.append("")
    lines.append("LATTICE_CONSTANT")
    lines.append("1.8897259886")
    lines.append("")
    lines.append("LATTICE_VECTORS")
    for vec in cell:
        lines.append(f" {vec[0]:19.15f} {vec[1]:19.15f} {vec[2]:19.15f}")

    lines.append("")
    lines.append("ATOMIC_POSITIONS")
    lines.append("Cartesian")
    for symbol in species:
        atom_indices = [idx for idx, atom_symbol in enumerate(chemical_symbols) if atom_symbol == symbol]
        lines.append(symbol)
        lines.append("0.0")
        lines.append(str(len(atom_indices)))
        for idx in atom_indices:
            x, y, z = positions[idx]
            lines.append(
                f" {x:15.10f} {y:15.10f} {z:15.10f} "
                f"{move_flags[0]} {move_flags[1]} {move_flags[2]}"
            )
    lines.append("")
    return "\n".join(lines)


def write_input_file(path: Path, input_params: Mapping[str, Any]) -> None:
    lines = ["INPUT_PARAMETERS"]
    for key, value in input_params.items():
        if value is None:
            continue
        lines.append(f"{key} {_format_value(value)}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_kpt_file(path: Path, mode: str, mesh: Tuple[int, int, int], shift: Tuple[float, float, float]) -> None:
    lines = [
        "K_POINTS",
        "0",
        mode,
        (
            f"{mesh[0]} {mesh[1]} {mesh[2]} "
            f"{_format_scalar(shift[0])} {_format_scalar(shift[1])} {_format_scalar(shift[2])}"
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def copy_source_file(source_path: Path, target_dir: Path) -> None:
    suffix = source_path.suffix.lower()
    if not suffix:
        suffix = ".structure"
    target_name = f"source{suffix}"
    shutil.copy2(source_path, target_dir / target_name)


def materialize_cases(config: GeneratorConfig, jobs: Sequence[CaseJob]) -> List[Path]:
    generated_dirs: List[Path] = []
    basis_type = str(config.input_params.get("basis_type", "lcao")).strip().lower()
    config.output_root.mkdir(parents=True, exist_ok=True)

    for job in jobs:
        case_dir = config.output_root / job.case_name
        if case_dir.exists() and config.overwrite:
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True, exist_ok=False)

        write_input_file(case_dir / "INPUT", config.input_params)
        write_kpt_file(case_dir / "KPT", config.kpt_mode, config.kpt_mesh, config.kpt_shift)
        stru_text = generate_stru_text(
            atoms=job.atoms,
            species=job.species,
            basis_type=basis_type,
            move_flags=config.move_flags,
            orbital_subdir_pattern=config.orbital_subdir_pattern,
        )
        (case_dir / "STRU").write_text(stru_text, encoding="utf-8")
        if config.copy_source_file:
            copy_source_file(job.source_path, case_dir)
        generated_dirs.append(case_dir)
    return generated_dirs


def print_plan(config: GeneratorConfig, jobs: Sequence[CaseJob]) -> None:
    print("Dry run complete.")
    print(f"system_name: {config.system_name}")
    print(f"output_root: {config.output_root}")
    print(f"run_dir_naming: {config.run_dir_naming}")
    print(f"overwrite: {config.overwrite}")
    print(f"copy_source_file: {config.copy_source_file}")
    print(f"move_flags: {list(config.move_flags)}")
    print(f"matched_structures: {len(jobs)}")
    for job in jobs:
        print(f"- {job.case_name} <= {job.source_path}")


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve() if args.config else None
    config_base_dir = config_path.parent if config_path else Path.cwd()
    raw_config = load_config(config_path)
    config = build_generator_config(args, raw_config, config_base_dir=config_base_dir)

    structure_files = resolve_structure_files(config.structure_globs, base_dir=config_base_dir)
    jobs = collect_jobs(structure_files, config)

    if config.dry_run:
        print_plan(config, jobs)
        return

    generated_dirs = materialize_cases(config, jobs)
    print(f"Generated {len(generated_dirs)} ABACUS case directories under: {config.output_root}")
    for case_dir in generated_dirs:
        print(case_dir)


if __name__ == "__main__":
    main()
