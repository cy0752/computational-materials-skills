---
name: remote-task-submit
description: Public placeholder skill for remote job submission. Customize this directory for your own scheduler, cluster, or server-side launcher.
---

# Remote Task Submit

## Purpose

`remote-task-submit` is the repository's single cluster-specific submission adapter.

Use it whenever a workflow stage needs to launch work on a remote machine, queue, or scheduler.
Keep site-specific submission details here instead of scattering them across workflow skills.
It must remain independently usable even when no higher-level pipeline skill is involved.

## What To Customize

1. Replace the command templates in `scripts/submit_batch_job.py` and `scripts/submit_hpc_job.py`.
2. Replace placeholder values such as `<submit-binary>`, `<queue>`, `<account>`, `<resource-profile>`, and `<container-image>`.
3. Add or remove arguments so they match the user's scheduler, launcher, or in-house platform.
4. Keep credentials, internal hostnames, machine-room names, and live account identifiers out of this repository.

## Compatibility Rule

When another skill says to use `remote-task-submit`, interpret that as:

1. Prepare the runnable stage command in the workflow-specific skill.
2. Hand the final remote submission shape to `remote-task-submit`.
3. Keep queue, account, resource, image, launcher, and site defaults here.

## Guardrails

- Do not hardcode private endpoints, hostnames, machine-room names, account names, or cluster-only paths here.
- Do not store passwords, tokens, browser sessions, or compiled caches in this skill.
- Prefer documented placeholders or environment variables for anything site-specific.
- Treat the helper scripts in `scripts/` as starter templates, not as universally correct commands.
