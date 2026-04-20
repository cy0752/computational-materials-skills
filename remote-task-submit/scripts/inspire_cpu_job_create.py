#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _inspire_runtime import bootstrap_inspire_imports


bootstrap_inspire_imports()

from inspire.cli.utils import job_submit
from inspire.cli.utils.auth import AuthManager
from inspire.config import Config, ConfigError
from inspire.config.workspaces import select_workspace_id
from inspire.platform.web.browser_api.core import _get_base_url
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


@dataclass(frozen=True)
class CPUResourceSpec:
    spec_id: str
    cpu_count: int
    memory_gib: int
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
        description="Submit a CPU training job through Inspire using the existing CLI config."
    )
    parser.add_argument("--name", "-n", required=True, help="Job name")
    parser.add_argument("--command", "-c", required=True, help="Command to run remotely")
    parser.add_argument(
        "--project",
        "-p",
        help="Project alias or project-... id (defaults to config job project)",
    )
    parser.add_argument(
        "--workspace",
        help="Workspace alias from config, such as cpu or a custom [workspaces] entry",
    )
    parser.add_argument(
        "--workspace-id",
        help="Explicit workspace id override",
    )
    parser.add_argument(
        "--location",
        help="Preferred compute group location/name, for example 高性能计算",
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=1,
        help="Minimum CPU cores required when selecting a CPU spec",
    )
    parser.add_argument(
        "--memory-gib",
        type=int,
        default=10,
        help="Minimum memory in GiB required when selecting a CPU spec",
    )
    parser.add_argument(
        "--spec-id",
        help="Explicit CPU training spec/quota id; skips resource price lookup when provided",
    )
    parser.add_argument(
        "--priority",
        type=int,
        help="Task priority 1-10 (defaults to config job priority)",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=1.0,
        help="Max runtime in hours",
    )
    parser.add_argument(
        "--image",
        help="Custom image; defaults to Inspire fallback image when omitted",
    )
    parser.add_argument(
        "--framework",
        default="pytorch",
        help="Framework label passed to train_job/create",
    )
    parser.add_argument(
        "--web-password",
        default=os.environ.get("INSPIRE_WEB_PASSWORD"),
        help=(
            "Optional password used only for browser-session login when CPU spec lookup "
            "falls back to web APIs. Defaults to INSPIRE_WEB_PASSWORD, then account "
            "web_password, then config password."
        ),
    )
    parser.add_argument(
        "--nodes",
        type=int,
        default=1,
        help="Instance count for the training job",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve CPU workspace/spec and print the payload without creating a job",
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


def _workspace_ids(group: dict[str, Any]) -> list[str]:
    raw = group.get("workspace_ids") or []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _is_cpu_group(group: dict[str, Any]) -> bool:
    gpu_type = str(group.get("gpu_type") or "").strip().upper()
    return gpu_type in {"", "CPU"}


def _group_id(group: dict[str, Any]) -> str:
    return str(group.get("id") or group.get("logic_compute_group_id") or "").strip()


def _group_label(group: dict[str, Any]) -> str:
    return str(group.get("name") or group.get("location") or _group_id(group)).strip()


def resolve_cpu_compute_group(
    *,
    config: Config,
    workspace_id: str,
    location: str | None,
) -> dict[str, Any]:
    candidates = [
        group
        for group in config.compute_groups
        if _is_cpu_group(group) and workspace_id in _workspace_ids(group)
    ]
    if not candidates:
        raise ConfigError(
            f"No CPU compute group configured for workspace {workspace_id}. "
            "Check [[compute_groups]] in config.toml."
        )

    if location:
        needle = location.casefold()
        exact = []
        fuzzy = []
        for group in candidates:
            labels = {
                _group_label(group),
                str(group.get("location") or "").strip(),
                _group_id(group),
            }
            for label in labels:
                if not label:
                    continue
                hay = label.casefold()
                if hay == needle:
                    exact.append(group)
                    break
                if needle in hay:
                    fuzzy.append(group)
                    break
        if exact:
            return exact[0]
        if fuzzy:
            return fuzzy[0]

        available = ", ".join(sorted({_group_label(group) for group in candidates}))
        raise ConfigError(
            f"Location {location!r} not found in CPU compute groups for workspace {workspace_id}. "
            f"Available: {available}"
        )

    for group in candidates:
        if "CPU" in _group_label(group).upper():
            return group
    return candidates[0]


def _browser_prefix(config: Config) -> str:
    return (config.browser_api_prefix or "/api/v1").rstrip("/")


def fetch_training_resource_prices(
    api: Any,
    *,
    config: Config,
    workspace_id: str,
    logic_compute_group_id: str,
    web_password: str | None,
) -> list[dict[str, Any]]:
    body = {
        "workspace_id": workspace_id,
        "schedule_config_type": "SCHEDULE_CONFIG_TYPE_TRAIN",
        "logic_compute_group_id": logic_compute_group_id,
    }
    endpoint = f"{_browser_prefix(config)}/resource_prices/logic_compute_groups/"

    data: Any
    try:
        # Training resource prices live under the browser API prefix even though
        # the job itself is created through the OpenAPI training endpoint.
        result = api._make_request("POST", endpoint, body)
        if result.get("code") != 0:
            raise ValueError(result.get("message") or "Failed to fetch training resource prices")
        data = result.get("data", [])
    except Exception as token_error:  # noqa: BLE001
        if web_password:
            clear_session_cache()
            session = login_with_playwright(
                config.username,
                web_password,
                base_url=config.base_url,
            )
            session.save(account=config.username)
        else:
            session = get_web_session()
        result = request_json(
            session,
            "POST",
            f"{_get_base_url()}{endpoint}",
            headers={"Referer": f"{_get_base_url()}/jobs/distributedTraining"},
            body=body,
            timeout=30,
        )
        if result.get("code") != 0:
            raise ValueError(
                "Failed to fetch training resource prices via token and browser session: "
                f"{token_error}; {result.get('message')}"
            ) from token_error
        data = result.get("data", [])

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get(
            "lcg_resource_spec_prices",
            data.get("resource_spec_prices", data.get("list", [])),
        )
    return []


def _as_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def choose_cpu_spec(
    prices: list[dict[str, Any]],
    *,
    min_cpu_count: int,
    min_memory_gib: int,
) -> CPUResourceSpec:
    candidates: list[CPUResourceSpec] = []
    for entry in prices:
        if _as_int(entry.get("gpu_count")) != 0:
            continue
        spec_id = str(entry.get("spec_id") or entry.get("quota_id") or entry.get("id") or "").strip()
        if not spec_id:
            continue
        candidates.append(
            CPUResourceSpec(
                spec_id=spec_id,
                cpu_count=_as_int(entry.get("cpu_count")),
                memory_gib=_as_int(entry.get("memory_size_gib"), _as_int(entry.get("memory_gb"))),
                raw=entry,
            )
        )

    if not candidates:
        raise ValueError("No CPU resource specs returned for the selected compute group")

    matches = [
        spec
        for spec in candidates
        if spec.cpu_count >= min_cpu_count and spec.memory_gib >= min_memory_gib
    ]
    if not matches:
        available = ", ".join(
            f"{spec.cpu_count} CPU / {spec.memory_gib} GiB (spec_id={spec.spec_id})"
            for spec in sorted(candidates, key=lambda item: (item.cpu_count, item.memory_gib))
        )
        raise ValueError(
            f"No CPU spec satisfies >= {min_cpu_count} CPU and >= {min_memory_gib} GiB. "
            f"Available specs: {available}"
        )

    return sorted(matches, key=lambda item: (item.cpu_count, item.memory_gib))[0]


def submit_cpu_job(
    api: Any,
    *,
    config: Config,
    name: str,
    command: str,
    framework: str,
    project_id: str,
    workspace_id: str,
    compute_group_id: str,
    spec: CPUResourceSpec,
    image: str | None,
    priority: int,
    max_time_hours: float,
    nodes: int,
) -> tuple[dict[str, Any], str, str | None]:
    wrapped_command = job_submit.wrap_in_bash(command)
    final_command, log_path = job_submit.build_remote_logged_command(config, command=wrapped_command)

    max_time_ms = str(int(max_time_hours * 3600 * 1000))
    framework_item = {
        "image_type": api.DEFAULT_IMAGE_TYPE if image else api._get_default_image_type(),
        "image": image or api._get_default_image(),
        "instance_count": nodes,
        "spec_id": spec.spec_id,
    }
    if config.shm_size is not None:
        shm_gi = int(config.shm_size)
        if shm_gi >= 1:
            framework_item["shm_gi"] = shm_gi

    payload = {
        "name": name,
        "command": final_command,
        "framework": framework,
        "logic_compute_group_id": compute_group_id,
        "project_id": project_id,
        "workspace_id": workspace_id,
        "task_priority": priority,
        "max_running_time_ms": max_time_ms,
        "framework_config": [framework_item],
    }

    result = api._make_request("POST", api.endpoints.TRAIN_JOB_CREATE, payload)
    if result.get("code") != 0:
        raise ValueError(result.get("message") or "CPU training job creation failed")

    return result, wrapped_command, log_path


def main() -> int:
    args = parse_args()

    if not args.keep_proxy:
        clear_proxy_env()

    try:
        config, _ = Config.from_files_and_env(require_target_dir=True)
        project_id = resolve_project_id(config, args.project)
        workspace_id = resolve_workspace_id(config, args)
        web_password = resolve_web_password(config, args.web_password)
        compute_group = resolve_cpu_compute_group(
            config=config,
            workspace_id=workspace_id,
            location=args.location,
        )
        compute_group_id = _group_id(compute_group)
        if not compute_group_id:
            raise ConfigError("Selected CPU compute group does not define an id")

        api = AuthManager.get_api(config)
        api.session.trust_env = False
        api.session.proxies.clear()

        if args.spec_id:
            spec = CPUResourceSpec(
                spec_id=args.spec_id,
                cpu_count=args.cpus,
                memory_gib=args.memory_gib,
                raw={},
            )
        else:
            prices = fetch_training_resource_prices(
                api,
                config=config,
                workspace_id=workspace_id,
                logic_compute_group_id=compute_group_id,
                web_password=web_password,
            )
            spec = choose_cpu_spec(
                prices,
                min_cpu_count=args.cpus,
                min_memory_gib=args.memory_gib,
            )

        priority = args.priority if args.priority is not None else config.job_priority

        payload_preview = {
            "project_id": project_id,
            "workspace_id": workspace_id,
            "compute_group_id": compute_group_id,
            "compute_group_name": _group_label(compute_group),
            "spec_id": spec.spec_id,
            "cpu_count": spec.cpu_count,
            "memory_gib": spec.memory_gib,
            "framework": args.framework,
            "priority": priority,
            "max_time_hours": args.max_time,
            "command": args.command,
        }

        if args.dry_run:
            print(json.dumps(payload_preview, ensure_ascii=False, indent=2))
            return 0

        result, wrapped_command, log_path = submit_cpu_job(
            api,
            config=config,
            name=args.name,
            command=args.command,
            framework=args.framework,
            project_id=project_id,
            workspace_id=workspace_id,
            compute_group_id=compute_group_id,
            spec=spec,
            image=args.image,
            priority=priority,
            max_time_hours=args.max_time,
            nodes=args.nodes,
        )

        job_id = str(((result.get("data") or {}).get("job_id") or "")).strip()
        if job_id:
            job_submit.cache_created_job(
                config,
                job_id=job_id,
                name=args.name,
                resource=f"{spec.cpu_count}CPU/{spec.memory_gib}GiB",
                command=wrapped_command,
                log_path=log_path,
                project=project_id,
            )

        summary = {
            "job_id": job_id,
            "project_id": project_id,
            "workspace_id": workspace_id,
            "compute_group_id": compute_group_id,
            "compute_group_name": _group_label(compute_group),
            "spec_id": spec.spec_id,
            "cpu_count": spec.cpu_count,
            "memory_gib": spec.memory_gib,
            "log_path": log_path,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
