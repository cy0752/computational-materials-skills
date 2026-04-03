#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
from dataclasses import dataclass


PUBLIC_PLACEHOLDER_MARKERS = (
    "<submit-binary>",
    "<scheduler-arguments>",
    "<launcher-arguments>",
)


@dataclass(frozen=True)
class TemplateConfig:
    env_var: str
    default_template: str
    template_label: str


def add_common_arguments(
    parser: argparse.ArgumentParser,
    *,
    default_queue: str,
    default_resource_profile: str,
    default_memory: str,
    default_time_limit: str,
) -> None:
    parser.add_argument("--name", "-n", required=True, help="Logical job name")
    parser.add_argument("--command", "-c", required=True, help="Runnable command on the remote side")
    parser.add_argument("--workdir", default=".", help="Remote or shared working directory")
    parser.add_argument("--queue", default=default_queue, help="Queue, partition, or pool placeholder")
    parser.add_argument("--account", default="<account>", help="Account or project placeholder")
    parser.add_argument(
        "--resource-profile",
        default=default_resource_profile,
        help="Site-specific resource profile placeholder",
    )
    parser.add_argument("--image", default="<container-image>", help="Container image or runtime profile")
    parser.add_argument("--nodes", type=int, default=1, help="Node count placeholder")
    parser.add_argument("--tasks", type=int, default=1, help="Task or rank count placeholder")
    parser.add_argument("--cpus-per-task", type=int, default=1, help="CPU count per task placeholder")
    parser.add_argument("--memory", default=default_memory, help="Memory placeholder")
    parser.add_argument("--time-limit", default=default_time_limit, help="Walltime placeholder")
    parser.add_argument(
        "--template",
        help="Explicit shell template. Overrides the environment variable and script default.",
    )
    parser.add_argument(
        "--export",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra environment assignment. Accessible through {exports} or {export_prefix}.",
    )
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional placeholder mapping. Example: --extra partition=gpu makes {partition} available.",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Raw scheduler argument fragment appended into {extra_args}.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Render the command without executing it")
    parser.add_argument(
        "--print-template",
        action="store_true",
        help="Print the current template and available placeholders, then exit",
    )


def parse_key_value_pairs(entries: list[str], *, flag_name: str, reserved_keys: set[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise SystemExit(f"{flag_name} expects KEY=VALUE entries. Got: {entry!r}")
        key, value = entry.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"{flag_name} requires a non-empty key. Got: {entry!r}")
        if key in reserved_keys:
            raise SystemExit(
                f"{flag_name} key {key!r} collides with a built-in placeholder. "
                "Choose a different name."
            )
        parsed[key] = value
    return parsed


def quote(value: object) -> str:
    return shlex.quote(str(value))


def resolve_template(config: TemplateConfig, explicit_template: str | None) -> tuple[str, str]:
    if explicit_template:
        return explicit_template, "--template"
    from_env = os.environ.get(config.env_var, "").strip()
    if from_env:
        return from_env, config.env_var
    return config.default_template, f"default:{config.template_label}"


def build_context(args: argparse.Namespace) -> dict[str, str]:
    raw_context: dict[str, str] = {
        "name": args.name,
        "command": args.command,
        "workdir": args.workdir,
        "queue": args.queue,
        "account": args.account,
        "resource_profile": args.resource_profile,
        "image": args.image,
        "nodes": str(args.nodes),
        "tasks": str(args.tasks),
        "cpus_per_task": str(args.cpus_per_task),
        "memory": args.memory,
        "time_limit": args.time_limit,
    }
    extra_context = parse_key_value_pairs(
        args.extra,
        flag_name="--extra",
        reserved_keys=set(raw_context),
    )
    raw_context.update(extra_context)

    exports = parse_key_value_pairs(
        args.export,
        flag_name="--export",
        reserved_keys=set(),
    )
    raw_context["exports"] = " ".join(f"{key}={quote(value)}" for key, value in exports.items())
    raw_context["export_prefix"] = f"env {raw_context['exports']}" if raw_context["exports"] else ""
    raw_context["extra_args"] = " ".join(args.extra_arg)

    quoted_context = {
        f"{key}_quoted": quote(value)
        for key, value in raw_context.items()
    }
    return {**raw_context, **quoted_context}


def render_template(template: str, context: dict[str, str]) -> str:
    try:
        return template.format(**context).strip()
    except KeyError as exc:
        available = ", ".join(sorted(context))
        raise SystemExit(
            f"Unknown placeholder {exc.args[0]!r} in submission template. "
            f"Available placeholders: {available}"
        ) from exc


def print_template(config: TemplateConfig, template: str, source: str, context: dict[str, str]) -> None:
    payload = {
        "template_source": source,
        "template_env_var": config.env_var,
        "template": template,
        "available_placeholders": sorted(context),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_submission(config: TemplateConfig, args: argparse.Namespace) -> int:
    context = build_context(args)
    template, source = resolve_template(config, args.template)

    if args.print_template:
        print_template(config, template, source, context)
        return 0

    rendered = render_template(template, context)
    if args.dry_run:
        payload = {
            "template_source": source,
            "template_env_var": config.env_var,
            "rendered_command": rendered,
            "context": context,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if any(marker in rendered for marker in PUBLIC_PLACEHOLDER_MARKERS):
        raise SystemExit(
            "Refusing to execute a public placeholder template. "
            f"Replace the markers in {config.template_label} or set {config.env_var} first."
        )

    completed = subprocess.run(
        rendered,
        shell=True,
        executable="/bin/bash",
        check=False,
    )
    return completed.returncode
