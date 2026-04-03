#!/usr/bin/env python3

from __future__ import annotations

import argparse

from _submit_runtime import TemplateConfig, add_common_arguments, run_submission


DEFAULT_HPC_TEMPLATE = """
<submit-binary> \
  --job-name {name_quoted} \
  --workdir {workdir_quoted} \
  --queue {queue_quoted} \
  --account {account_quoted} \
  --nodes {nodes} \
  --tasks {tasks} \
  --cpus-per-task {cpus_per_task} \
  --memory {memory_quoted} \
  --time-limit {time_limit_quoted} \
  --image {image_quoted} \
  <launcher-arguments> \
  {extra_args} \
  --command {command_quoted}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Public placeholder helper for MPI or multi-node submission. "
            "Edit the default template or set REMOTE_HPC_SUBMIT_TEMPLATE to match your site."
        )
    )
    add_common_arguments(
        parser,
        default_queue="<queue>",
        default_resource_profile="<resource-profile>",
        default_memory="32G",
        default_time_limit="04:00:00",
    )
    return parser.parse_args()


def main() -> int:
    return run_submission(
        TemplateConfig(
            env_var="REMOTE_HPC_SUBMIT_TEMPLATE",
            default_template=DEFAULT_HPC_TEMPLATE,
            template_label="submit_hpc_job.py",
        ),
        parse_args(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
