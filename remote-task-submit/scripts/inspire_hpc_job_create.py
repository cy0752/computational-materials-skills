#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _inspire_runtime import bootstrap_inspire_imports


bootstrap_inspire_imports()

from inspire.cli.utils.auth import AuthManager
from inspire.config import Config, ConfigError
from inspire.config.workspaces import select_workspace_id
from inspire.platform.web.session import clear_session_cache, get_web_session, request_json
from inspire.platform.web.session.auth import login_with_playwright


PROXY_ENV_VARS = (
    "http_proxy",
    "https_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "all_proxy",
    "NO_PROXY",
    "no_proxy",
)
DEFAULT_HPC_IMAGE = "docker.sii.shaipower.online/infly-dev/slurm-k8s-cluster:20250101841"
DEFAULT_HPC_IMAGE_TYPE = "SOURCE_OFFICIAL"
HPC_CREATE_ENDPOINT = "/openapi/v1/hpc_jobs/create"
HPC_DETAIL_ENDPOINT = "/openapi/v1/hpc_jobs/detail"


@dataclass(frozen=True)
class HPCNodeSpec:
    spec_id: str
    name: str
    cpu_count: int
    memory_gib: int
    raw: dict[str, Any]


@dataclass(frozen=True)
class ComputeGroup:
    group_id: str
    name: str
    raw: dict[str, Any]


def clear_proxy_env() -> None:
    for key in PROXY_ENV_VARS:
        os.environ.pop(key, None)


def _load_account_secret_from_config(config_path: Path | None, account_name: str, key: str) -> str | None:
    if not config_path or not config_path.exists():
        return None
    try:
        raw = Config._load_toml(config_path)
    except Exception:
        return None

    accounts = raw.get("accounts")
    if not isinstance(accounts, dict):
        return None
    account = accounts.get(account_name)
    if not isinstance(account, dict):
        return None
    value = account.get(key)
    if value in (None, ""):
        return None
    return str(value)


def resolve_web_password(config: Config, explicit_password: str | None) -> str | None:
    if explicit_password not in (None, ""):
        return explicit_password
    project_config_path, _ = Config.get_config_paths()
    account_name = str(config.context_account or config.username or "").strip()
    project_secret = _load_account_secret_from_config(project_config_path, account_name, "web_password")
    if project_secret:
        return project_secret
    global_secret = _load_account_secret_from_config(
        Config.resolve_global_config_path(), account_name, "web_password"
    )
    if global_secret:
        return global_secret
    if config.password not in (None, ""):
        return config.password
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Submit a high-performance-computing job through Inspire HPC OpenAPI."
    )
    parser.add_argument("--name", "-n", required=True, help="HPC job name")
    parser.add_argument("--command", "-c", required=True, help="Entrypoint command to run")
    parser.add_argument(
        "--project",
        "-p",
        help="Project alias or project-... id (defaults to config job project)",
    )
    parser.add_argument(
        "--workspace",
        help="Workspace alias from config, such as cpu or a custom [workspaces] entry",
    )
    parser.add_argument("--workspace-id", help="Explicit workspace id override")
    parser.add_argument(
        "--location",
        default="高性能计算",
        help="Preferred compute group location/name",
    )
    parser.add_argument(
        "--spec-id",
        help="Explicit HPC predef node spec id; skips automatic spec selection when provided",
    )
    parser.add_argument(
        "--min-spec-cpus",
        type=int,
        default=1,
        help="Minimum CPU count when auto-selecting an HPC spec",
    )
    parser.add_argument(
        "--min-spec-memory-gib",
        type=int,
        default=10,
        help="Minimum memory in GiB when auto-selecting an HPC spec",
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=1,
        help="Node count (instance_count)",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=1,
        help="Number of tasks (number_of_tasks)",
    )
    parser.add_argument(
        "--cpus-per-task",
        type=int,
        default=1,
        help="CPU cores per task",
    )
    parser.add_argument(
        "--memory-per-cpu",
        default="10G",
        help="Memory per CPU, for example 10G",
    )
    parser.add_argument(
        "--ttl-after-finish-seconds",
        type=int,
        default=600,
        help="How long to keep the job after finish",
    )
    parser.add_argument(
        "--image",
        default=DEFAULT_HPC_IMAGE,
        help="Container image address",
    )
    parser.add_argument(
        "--image-type",
        default=DEFAULT_HPC_IMAGE_TYPE,
        help="Image source, for example SOURCE_OFFICIAL",
    )
    parser.add_argument(
        "--enable-hyper-threading",
        action="store_true",
        help="Enable hyper threading",
    )
    parser.add_argument(
        "--web-password",
        default=os.environ.get("INSPIRE_WEB_PASSWORD"),
        help=(
            "Optional password used only for browser-session login. "
            "Defaults to INSPIRE_WEB_PASSWORD, then account web_password, then config password."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve workspace/compute-group/spec and print the payload without creating a job",
    )
    parser.add_argument(
        "--keep-proxy",
        action="store_true",
        help="Keep proxy environment variables instead of clearing them before requests",
    )
    return parser.parse_args()


def resolve_project_id(config: Config, requested: str | None) -> str:
    value = (requested or config.job_project_id or "").strip()
    if not value:
        raise ConfigError(
            "No project configured. Pass --project or set INSPIRE_PROJECT_ID / job.project_id."
        )
    if value.startswith("project-"):
        return value

    for alias, project_id in config.projects.items():
        if alias.lower() == value.lower():
            return project_id

    available = ", ".join(sorted(config.projects)) if config.projects else "(none configured)"
    raise ConfigError(f"Unknown project alias: {value!r}. Available aliases: {available}")


def resolve_workspace_id(config: Config, args: argparse.Namespace) -> str:
    workspace_id = select_workspace_id(
        config,
        cpu_only=True,
        explicit_workspace_id=args.workspace_id,
        explicit_workspace_name=args.workspace,
    )
    if not workspace_id:
        raise ConfigError(
            "No CPU workspace resolved. Pass --workspace-id / --workspace or configure [workspaces].cpu."
        )
    return workspace_id


def get_web_session_for_hpc(config: Config, web_password: str | None):
    if web_password:
        clear_session_cache()
        session = login_with_playwright(
            config.username,
            web_password,
            base_url=config.base_url,
        )
        session.save(account=config.username)
        return session
    return get_web_session()


def find_workspace_id_by_name(session: Any, name: str | None) -> str | None:
    needle = str(name or "").strip().casefold()
    if not needle:
        return None

    all_workspace_names = getattr(session, "all_workspace_names", {}) or {}
    if isinstance(all_workspace_names, dict):
        exact = []
        fuzzy = []
        for workspace_id, workspace_name in all_workspace_names.items():
            label = str(workspace_name or "").strip()
            if not label:
                continue
            folded = label.casefold()
            if folded == needle:
                exact.append(str(workspace_id).strip())
            elif needle in folded:
                fuzzy.append(str(workspace_id).strip())
        if exact:
            return exact[0]
        if fuzzy:
            return fuzzy[0]

    return None


def _group_id(group: dict[str, Any]) -> str:
    return str(group.get("logic_compute_group_id") or group.get("id") or "").strip()


def _group_name(group: dict[str, Any]) -> str:
    return str(group.get("name") or group.get("location") or _group_id(group)).strip()


def _supports_hpc(group: dict[str, Any]) -> bool:
    raw_support_job_types = str(group.get("support_job_type_list") or "")
    raw_support_node_types = str(group.get("support_node_type_list") or "")
    if "hpc_job" in raw_support_job_types or "hpc" in raw_support_node_types:
        return True
    gpu_stats = group.get("gpu_type_stats") or []
    return not gpu_stats


def fetch_hpc_compute_groups(
    *,
    session,
    base_url: str,
    workspace_id: str,
) -> list[dict[str, Any]]:
    result = request_json(
        session,
        "POST",
        f"{base_url}/api/v1/logic_compute_groups/list",
        headers={"Referer": f"{base_url}/jobs/hpc?spaceId={workspace_id}"},
        body={
            "page_size": -1,
            "page_num": 1,
            "filter": {
                "workspace_id": workspace_id,
            },
        },
        timeout=30,
    )
    if result.get("code") != 0:
        raise ValueError(result.get("message") or "Failed to fetch HPC compute groups")
    data = result.get("data") or {}
    groups = data.get("logic_compute_groups") or []
    return [group for group in groups if isinstance(group, dict) and _supports_hpc(group)]


def resolve_hpc_compute_group(
    *,
    session,
    config: Config,
    workspace_id: str,
    location: str | None,
) -> ComputeGroup:
    groups = fetch_hpc_compute_groups(
        session=session,
        base_url=config.base_url.rstrip("/"),
        workspace_id=workspace_id,
    )
    if not groups:
        raise ValueError(f"No HPC compute groups returned for workspace {workspace_id}")

    if location:
        needle = location.casefold()
        exact_matches = []
        fuzzy_matches = []
        for group in groups:
            labels = {_group_name(group), str(group.get("compute_group_name") or "").strip()}
            for label in labels:
                if not label:
                    continue
                label_folded = label.casefold()
                if label_folded == needle:
                    exact_matches.append(group)
                    break
                if needle in label_folded:
                    fuzzy_matches.append(group)
                    break
        if exact_matches:
            target = exact_matches[0]
        elif fuzzy_matches:
            target = fuzzy_matches[0]
        else:
            available = ", ".join(sorted({_group_name(group) for group in groups}))
            raise ValueError(f"Location {location!r} not found. Available HPC groups: {available}")
    else:
        target = groups[0]

    group_id = _group_id(target)
    if not group_id:
        raise ValueError("Selected HPC compute group does not define a logic_compute_group_id")
    return ComputeGroup(group_id=group_id, name=_group_name(target), raw=target)


def fetch_hpc_workspace_config(
    *,
    session,
    base_url: str,
    workspace_id: str,
) -> dict[str, Any]:
    result = request_json(
        session,
        "GET",
        f"{base_url}/api/v1/hpc_jobs/configs/workspace/{workspace_id}",
        headers={"Referer": f"{base_url}/jobs/hpc?spaceId={workspace_id}"},
        timeout=30,
    )
    if result.get("code") != 0:
        raise ValueError(result.get("message") or "Failed to fetch HPC workspace config")
    return result.get("data") or {}


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_hpc_specs(workspace_config: dict[str, Any]) -> list[HPCNodeSpec]:
    raw_specs = workspace_config.get("predef_node_spec") or workspace_config.get("predef_node_specs") or []
    if isinstance(raw_specs, str):
        raw_specs = json.loads(raw_specs or "[]")
    if not isinstance(raw_specs, list):
        raise ValueError("Unexpected HPC workspace config: predef_node_spec is not a list")

    specs: list[HPCNodeSpec] = []
    for entry in raw_specs:
        if not isinstance(entry, dict):
            continue
        spec_id = str(entry.get("id") or entry.get("spec_id") or entry.get("quota_id") or "").strip()
        if not spec_id:
            continue
        specs.append(
            HPCNodeSpec(
                spec_id=spec_id,
                name=str(entry.get("name") or spec_id).strip(),
                cpu_count=_as_int(entry.get("cpu_count")),
                memory_gib=_as_int(
                    entry.get("memory_size_gib"),
                    _as_int(entry.get("memory_size")),
                ),
                raw=entry,
            )
        )

    if not specs:
        raise ValueError("No HPC predef node specs found for the selected workspace")
    return specs


def choose_hpc_spec(
    specs: list[HPCNodeSpec],
    *,
    spec_id: str | None,
    min_cpu_count: int,
    min_memory_gib: int,
) -> HPCNodeSpec:
    if spec_id:
        for spec in specs:
            if spec.spec_id == spec_id:
                return spec
        available = ", ".join(sorted(spec.spec_id for spec in specs))
        raise ValueError(f"Unknown HPC spec_id {spec_id!r}. Available: {available}")

    matches = [
        spec
        for spec in specs
        if spec.cpu_count >= min_cpu_count and spec.memory_gib >= min_memory_gib
    ]
    if not matches:
        available = ", ".join(
            f"{spec.name}: {spec.cpu_count} CPU / {spec.memory_gib} GiB ({spec.spec_id})"
            for spec in sorted(specs, key=lambda item: (item.cpu_count, item.memory_gib))
        )
        raise ValueError(
            f"No HPC spec satisfies >= {min_cpu_count} CPU and >= {min_memory_gib} GiB. "
            f"Available specs: {available}"
        )

    return sorted(matches, key=lambda item: (item.cpu_count, item.memory_gib))[0]


def parse_memory_gib(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+)\s*([gGmM](?:i?[bB])?)?\s*", value)
    if not match:
        raise ValueError(f"Unsupported memory format: {value!r}")
    amount = int(match.group(1))
    unit = (match.group(2) or "G").lower()
    if unit.startswith("m"):
        gib = amount / 1024
        return int(gib) if gib.is_integer() else int(gib) + 1
    return amount


def validate_hpc_request(
    *,
    spec: HPCNodeSpec,
    nodes: int,
    tasks: int,
    cpus_per_task: int,
    memory_per_cpu: str,
) -> None:
    requested_cpu = tasks * cpus_per_task
    requested_memory_gib = tasks * parse_memory_gib(memory_per_cpu)
    available_cpu = spec.cpu_count * nodes
    available_memory_gib = spec.memory_gib * nodes

    if requested_cpu > available_cpu:
        raise ValueError(
            f"Requested {requested_cpu} total CPUs but selected spec provides only "
            f"{available_cpu} CPUs across {nodes} node(s)"
        )
    if requested_memory_gib > available_memory_gib:
        raise ValueError(
            f"Requested {requested_memory_gib} GiB total memory but selected spec provides only "
            f"{available_memory_gib} GiB across {nodes} node(s)"
        )


def create_hpc_job(api: Any, payload: dict[str, Any]) -> dict[str, Any]:
    result = api._make_request("POST", HPC_CREATE_ENDPOINT, payload)
    if result.get("code") != 0:
        raise ValueError(result.get("message") or "HPC job creation failed")
    return result


def get_hpc_job_detail(api: Any, job_id: str) -> dict[str, Any]:
    result = api._make_request("POST", HPC_DETAIL_ENDPOINT, {"job_id": job_id})
    if result.get("code") != 0:
        raise ValueError(result.get("message") or "Failed to fetch HPC job detail")
    return result.get("data") or {}


def main() -> int:
    args = parse_args()

    if not args.keep_proxy:
        clear_proxy_env()

    try:
        config, _ = Config.from_files_and_env(require_target_dir=True)
        project_id = resolve_project_id(config, args.project)
        web_password = resolve_web_password(config, args.web_password)

        session = get_web_session_for_hpc(config, web_password)
        workspace_id = resolve_workspace_id(config, args)
        if not args.workspace_id and not args.workspace:
            preferred_workspace_id = find_workspace_id_by_name(session, args.location)
            if preferred_workspace_id:
                workspace_id = preferred_workspace_id
        compute_group = resolve_hpc_compute_group(
            session=session,
            config=config,
            workspace_id=workspace_id,
            location=args.location,
        )
        workspace_config = fetch_hpc_workspace_config(
            session=session,
            base_url=config.base_url.rstrip("/"),
            workspace_id=workspace_id,
        )
        specs = parse_hpc_specs(workspace_config)
        spec = choose_hpc_spec(
            specs,
            spec_id=args.spec_id,
            min_cpu_count=args.min_spec_cpus,
            min_memory_gib=args.min_spec_memory_gib,
        )
        validate_hpc_request(
            spec=spec,
            nodes=args.nodes,
            tasks=args.tasks,
            cpus_per_task=args.cpus_per_task,
            memory_per_cpu=args.memory_per_cpu,
        )

        payload = {
            "name": args.name,
            "logic_compute_group_id": compute_group.group_id,
            "project_id": project_id,
            "image": args.image,
            "image_type": args.image_type,
            "entrypoint": args.command,
            "instance_count": args.nodes,
            "workspace_id": workspace_id,
            "spec_id": spec.spec_id,
            "ttl_after_finish_seconds": args.ttl_after_finish_seconds,
            "number_of_tasks": args.tasks,
            "cpus_per_task": args.cpus_per_task,
            "memory_per_cpu": args.memory_per_cpu,
            "enable_hyper_threading": args.enable_hyper_threading,
        }

        preview = {
            "workspace_id": workspace_id,
            "workspace_name": workspace_config.get("workspace_name", ""),
            "compute_group_id": compute_group.group_id,
            "compute_group_name": compute_group.name,
            "spec_id": spec.spec_id,
            "spec_name": spec.name,
            "spec_cpu_count": spec.cpu_count,
            "spec_memory_gib": spec.memory_gib,
            "payload": payload,
        }

        if args.dry_run:
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0

        api = AuthManager.get_api(config)
        api.session.trust_env = False
        api.session.proxies.clear()

        result = create_hpc_job(api, payload)
        job_id = str(((result.get("data") or {}).get("job_id") or "")).strip()
        summary = {
            "job_id": job_id,
            "workspace_id": workspace_id,
            "compute_group_id": compute_group.group_id,
            "compute_group_name": compute_group.name,
            "spec_id": spec.spec_id,
            "spec_name": spec.name,
            "spec_cpu_count": spec.cpu_count,
            "spec_memory_gib": spec.memory_gib,
        }

        if job_id:
            summary["detail"] = get_hpc_job_detail(api, job_id)

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
