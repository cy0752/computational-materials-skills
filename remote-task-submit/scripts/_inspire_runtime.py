#!/usr/bin/env python3

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Iterable


def _can_import_inspire() -> bool:
    try:
        __import__("inspire")
    except ImportError:
        return False
    return True


def _split_env_paths(name: str) -> list[Path]:
    value = os.environ.get(name, "").strip()
    if not value:
        return []
    return [Path(part).expanduser() for part in value.split(os.pathsep) if part.strip()]


def _iter_site_packages_under(root: Path) -> Iterable[Path]:
    if not root:
        return

    root = root.expanduser()
    direct_candidates = [
        root,
        root / "site-packages",
        root / "lib" / "site-packages",
    ]
    for candidate in direct_candidates:
        if candidate.is_dir():
            yield candidate

    for pattern in ("lib/python*/site-packages", "Lib/site-packages"):
        for candidate in root.glob(pattern):
            if candidate.is_dir():
                yield candidate


def _read_shebang_target(executable: Path) -> Path | None:
    try:
        first_line = executable.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
    except (FileNotFoundError, IndexError, OSError):
        return None

    if not first_line.startswith("#!"):
        return None
    parts = shlex.split(first_line[2:].strip())
    if not parts:
        return None

    interpreter = Path(parts[0]).expanduser()
    if interpreter.name == "env" and len(parts) > 1:
        resolved = shutil.which(parts[1])
        return Path(resolved).expanduser() if resolved else None
    return interpreter


def _iter_site_packages_from_executable(executable: Path) -> Iterable[Path]:
    if not executable.exists():
        return

    resolved = executable.expanduser().resolve()
    for candidate in _iter_site_packages_under(resolved.parent.parent):
        yield candidate

    shebang_target = _read_shebang_target(resolved)
    if shebang_target:
        for candidate in _iter_site_packages_under(shebang_target.parent.parent):
            yield candidate


def _iter_inspire_executables() -> Iterable[Path]:
    env_bin = os.environ.get("INSPIRE_BIN", "").strip()
    if env_bin:
        yield Path(env_bin).expanduser()

    resolved = shutil.which("inspire")
    if resolved:
        yield Path(resolved).expanduser()

    yield Path.home() / ".local" / "bin" / "inspire"
    yield Path.home() / "bin" / "inspire"


def _iter_candidate_site_packages() -> Iterable[Path]:
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent

    for env_name in ("INSPIRE_SITE_PACKAGES", "INSPIRE_PYTHON_SITE_PACKAGES"):
        for candidate in _split_env_paths(env_name):
            yield candidate

    cli_home = os.environ.get("INSPIRE_CLI_HOME", "").strip()
    if cli_home:
        for candidate in _iter_site_packages_under(Path(cli_home)):
            yield candidate

    for local_root in (
        skill_dir / "vendor",
        skill_dir / "scripts" / "vendor",
        script_dir / "vendor",
    ):
        for candidate in _iter_site_packages_under(local_root):
            yield candidate

    for executable in _iter_inspire_executables():
        for candidate in _iter_site_packages_from_executable(executable):
            yield candidate


def bootstrap_inspire_imports() -> None:
    if _can_import_inspire():
        return

    attempted: list[str] = []
    seen: set[str] = set()
    for candidate in _iter_candidate_site_packages():
        candidate_str = str(candidate)
        if candidate_str in seen:
            continue
        seen.add(candidate_str)
        attempted.append(candidate_str)
        if candidate.is_dir() and candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)
        if _can_import_inspire():
            return

    search_summary = ", ".join(attempted) if attempted else "(no candidate paths found)"
    raise ModuleNotFoundError(
        "Unable to import the 'inspire' package. "
        "Checked the current Python environment, skill-local vendor directories, "
        "INSPIRE_SITE_PACKAGES/INSPIRE_PYTHON_SITE_PACKAGES, INSPIRE_CLI_HOME, "
        "and site-packages derived from INSPIRE_BIN, PATH 'inspire', ~/.local/bin/inspire, and ~/bin/inspire. "
        f"Candidate paths: {search_summary}"
    )
