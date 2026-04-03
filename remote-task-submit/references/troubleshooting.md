# Remote Submit Template Reference

## Current State

- This directory is a public scaffold, not a site-specific scheduler integration.
- In command examples below, `<skill-dir>` means the directory containing this skill.
- Ordinary batch workloads should use:
  - `<skill-dir>/scripts/submit_batch_job.py`
- MPI or multi-node style workloads should use:
  - `<skill-dir>/scripts/submit_hpc_job.py`
- The bundled scripts are intentionally generic. They render a command template and only execute it after the user replaces the public placeholders.
- The recommended customization points are:
  - edit the `DEFAULT_*_TEMPLATE` constant inside the script
  - or set `REMOTE_BATCH_SUBMIT_TEMPLATE` / `REMOTE_HPC_SUBMIT_TEMPLATE`
- Run every new template with `--dry-run` before using it against a real cluster.
- Keep credentials outside the repository. The placeholder scripts do not manage login flows, browser sessions, or token refresh.

## Baseline Commands

Render a batch submission command without executing it:

```bash
python3 <skill-dir>/scripts/submit_batch_job.py \
  --name "<job-name>" \
  --workdir "<shared-workdir>" \
  --queue "<queue>" \
  --resource-profile "<resource-profile>" \
  --command "<start-command>" \
  --dry-run
```

Render an HPC submission command without executing it:

```bash
python3 <skill-dir>/scripts/submit_hpc_job.py \
  --name "<job-name>" \
  --workdir "<shared-workdir>" \
  --queue "<queue>" \
  --nodes 2 \
  --tasks 64 \
  --cpus-per-task 2 \
  --command "<start-command>" \
  --dry-run
```

Print the built-in placeholder template before editing it:

```bash
python3 <skill-dir>/scripts/submit_batch_job.py --name x --command y --print-template
python3 <skill-dir>/scripts/submit_hpc_job.py --name x --command y --print-template
```

Set a site-specific batch template through an environment variable:

```bash
export REMOTE_BATCH_SUBMIT_TEMPLATE='<submit-binary> --job-name {name_quoted} --workdir {workdir_quoted} --queue {queue_quoted} --resource-profile {resource_profile_quoted} --command {command_quoted}'
```

Set a site-specific HPC template through an environment variable:

```bash
export REMOTE_HPC_SUBMIT_TEMPLATE='<submit-binary> --job-name {name_quoted} --workdir {workdir_quoted} --queue {queue_quoted} --nodes {nodes} --tasks {tasks} --cpus-per-task {cpus_per_task} --command {command_quoted}'
```

## Available Placeholders

The helper scripts expose both raw and shell-quoted values for common fields:

- `{name}` / `{name_quoted}`
- `{command}` / `{command_quoted}`
- `{workdir}` / `{workdir_quoted}`
- `{queue}` / `{queue_quoted}`
- `{account}` / `{account_quoted}`
- `{resource_profile}` / `{resource_profile_quoted}`
- `{image}` / `{image_quoted}`
- `{nodes}` / `{nodes_quoted}`
- `{tasks}` / `{tasks_quoted}`
- `{cpus_per_task}` / `{cpus_per_task_quoted}`
- `{memory}` / `{memory_quoted}`
- `{time_limit}` / `{time_limit_quoted}`
- `{exports}` / `{export_prefix}`
- `{extra_args}`

You can also add your own placeholders with repeated `--extra key=value`.

## Common Failure Patterns

### The script says the template still contains public placeholders

Meaning:
- The command template still contains markers such as `<submit-binary>` or `<scheduler-arguments>`.

Usual fixes:
- Edit the default template in the script.
- Or set `REMOTE_BATCH_SUBMIT_TEMPLATE` / `REMOTE_HPC_SUBMIT_TEMPLATE`.
- Keep using `--dry-run` until the rendered command contains only real site-specific values.

### The scheduler rejects queue, account, resource, or image flags

Meaning:
- The placeholder template does not match the real CLI syntax used by the target cluster.

Usual fixes:
- Rename or remove unsupported flags in the template.
- Add site-specific placeholders with `--extra key=value`.
- If the CLI needs multiple commands, wrap them in a shell script and point `--command` at that script instead.

### The remote workdir, image, or input path is not visible on the cluster

Meaning:
- The submit host cannot access the path or runtime artifact passed into the rendered command.

Usual fixes:
- Replace local-only paths with cluster-visible paths.
- Add any required staging, copy, or mount logic outside this public template.
- Document the expected shared filesystem layout in a local site guide rather than hardcoding it here.

### The command runs locally instead of through the scheduler

Meaning:
- The template does not invoke the real submit binary yet.

Usual fixes:
- Replace `<submit-binary>` with the actual scheduler or platform command.
- Verify the rendered command with `--dry-run`.
- Do not remove the submission wrapper unless local execution is intentionally desired.
