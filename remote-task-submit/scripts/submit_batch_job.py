#!/usr/bin/env python3

from __future__ import annotations

import argparse

from _submit_runtime import TemplateConfig, add_common_arguments, run_submission


DEFAULT_BATCH_TEMPLATE = """
<submit-binary> \
  --job-name {name_quoted} \
  --workdir {workdir_quoted} \
  --queue {queue_quoted} \
  --account {account_quoted} \
  --resource-profile {resource_profile_quoted} \
  --cpus-per-task {cpus_per_task} \
  --memory {memory_quoted} \
  --time-limit {time_limit_quoted} \
  --image {image_quoted} \
  <scheduler-arguments> \
  {extra_args} \
  --command {command_quoted}
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Public placeholder helper for ordinary remote batch submission. "
            "Edit the default template or set REMOTE_BATCH_SUBMIT_TEMPLATE to match your site."
        )
    )
    add_common_arguments(
        parser,
        default_queue="<queue>",
        default_resource_profile="<resource-profile>",
        default_memory="8G",
        default_time_limit="01:00:00",
    )
    return parser.parse_args()


def main() -> int:
    return run_submission(
        TemplateConfig(
            env_var="REMOTE_BATCH_SUBMIT_TEMPLATE",
            default_template=DEFAULT_BATCH_TEMPLATE,
            template_label="submit_batch_job.py",
        ),
        parse_args(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
