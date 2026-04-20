---
name: remote-task-submit
description: Legacy compatibility wrapper for Inspire remote job submission. Redirect to `inspire-cli-training-submit` for the canonical generic submission flow.
---

# Remote Task Submit

## Status

`remote-task-submit` is a legacy compatibility skill.

Use `inspire-cli-training-submit` as the canonical generic Inspire submission base for GPU, CPU, and HPC jobs.
Do not define independent submission defaults, resource policies, or image-selection rules here.

## Compatibility Rule

When an older skill or prompt says to use `remote-task-submit`, reinterpret that as:

- use `inspire-cli-training-submit` for the generic Inspire CLI/helper workflow
- use any loaded workflow-specific submit skill for canonical resource defaults
  - `inspire-openmx-submit` for recognized OpenMX jobs
  - `inspire-vasp-submit` for recognized VASP jobs
  - `inspire-pasp-submit` for recognized PASP jobs
  - `inspire-hamgnn-submit` for recognized HamGNN jobs

## What This Skill Still Means

Use this skill name only as a compatibility alias when existing prompts still reference it.
It does not override the canonical defaults from workflow-specific submit skills.
It does not replace `inspire-cli-training-submit`.

## Delegation Rule

For generic submission or debugging:

- load and follow `inspire-cli-training-submit`

For recognized workflow submissions:

- load and follow the workflow-specific submit skill first
- use `inspire-cli-training-submit` as the underlying execution flow only through that workflow skill

## Guardrails

- Do not introduce a second generic Inspire submission policy here.
- Do not hardcode workspace, compute group, spec, or image defaults here.
- Do not let older prompts use this skill to bypass canonical workflow-specific defaults.
- If a downstream skill still references `remote-task-submit`, preserve backward compatibility by routing to the canonical submit stack rather than inventing new defaults.
