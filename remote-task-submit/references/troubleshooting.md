# Inspire CLI Submit Reference

## Current local defaults

- Conversation and edits usually happen on a CPU cluster shell.
- GPU work is launched through native `inspire job create` or `inspire run`.
- In command examples below, `<skill-dir>` means the directory containing this skill.
- CPU-only training is launched through the bundled helper script:
  - `<skill-dir>/scripts/inspire_cpu_job_create.py`
- HPC jobs are launched through the bundled helper script:
  - `<skill-dir>/scripts/inspire_hpc_job_create.py`
- Native `inspire` does not expose a first-class HPC create/status command in this setup.
- In this environment, the local CLI has been patched to support `job.location` / `INSP_LOCATION`.
- The helper scripts clear `http_proxy` / `https_proxy` by default unless `--keep-proxy` is passed.
- The helper scripts discover the installed `inspire` package from the active Python environment, skill-local vendor directories, `INSPIRE_SITE_PACKAGES` / `INSPIRE_PYTHON_SITE_PACKAGES`, `INSPIRE_CLI_HOME`, and paths derived from `INSPIRE_BIN`, `command -v inspire`, `~/.local/bin/inspire`, or `~/bin/inspire`.
- The helper scripts now resolve browser-login credentials in this order:
  - `--web-password`
  - `INSPIRE_WEB_PASSWORD`
  - `web_password` from the same Inspire account entry used by native CLI
  - `config.password` as the final fallback
- The current project config sets:
  - default job location: `H200-3号机房`
- The local CLI fallback for unspecified images is:
  - image: `ngc-pytorch:24.05-cuda12.4-py3`
  - image type: `SOURCE_OFFICIAL`

## Baseline commands

Submit a GPU training job with project defaults:

```bash
inspire job create -p cq --name "<job-name>" --resource "4xH200" --command "<start-command>"
```

Force a GPU training job to a specific machine room:

```bash
inspire job create -p cq --location "H200-3号机房" --name "<job-name>" --resource "4xH200" --command "<start-command>"
```

Submit a CPU training job through the helper script:

```bash
python3 <skill-dir>/scripts/inspire_cpu_job_create.py --name "<job-name>" --command "<start-command>"
```

Submit a CPU training job and override the browser password only for that command:

```bash
INSPIRE_WEB_PASSWORD="<password>" python3 <skill-dir>/scripts/inspire_cpu_job_create.py --name "<job-name>" --command "<start-command>"
```

Submit an HPC job through the helper script:

```bash
python3 <skill-dir>/scripts/inspire_hpc_job_create.py --name "<job-name>" --command "<start-command>"
```

Force a specific HPC location:

```bash
python3 <skill-dir>/scripts/inspire_hpc_job_create.py --location "高性能计算" --name "<job-name>" --command "<start-command>"
```

Inspect resolved job config:

```bash
inspire config show --filter Job
inspire config show --filter Workspaces
```

Retry native CLI commands without shell proxies:

```bash
env -u http_proxy -u https_proxy inspire resources list
env -u http_proxy -u https_proxy inspire job create -p cq --name "<job-name>" --resource "4xH200" --command "<start-command>"
```

## Common failure patterns

### `Connection error, retrying...` or `SSLEOFError ... UNEXPECTED_EOF_WHILE_READING`

Meaning:
- Native CLI is going through an inherited shell proxy that breaks Inspire HTTPS requests.

Usual fixes:
- Inspect `http_proxy` / `https_proxy`.
- Retry native CLI commands with `env -u http_proxy -u https_proxy ...`.
- Keep the helper-script default of clearing proxies unless you intentionally need proxy routing.

### `logic_compute_group ... does not belong to workspace ...`

Meaning:
- The command resolved one workspace, but the selected compute group belongs to another.

Usual fixes:
- Check `inspire config show --filter Workspaces`.
- Prefer an explicit `--location` in the intended workspace.
- Pass `--workspace-id` only if the directory default is wrong or the user wants a different workspace.

### `no permission to use private image ...`

Meaning:
- The submission is trying to use a private image that the account cannot access.

Usual fixes:
- Omit `--image` and let the patched official fallback apply.
- Or set `job.image` / `--image` to a known accessible image.

### `Session expired, re-authenticating...`

Meaning:
- The cached web session expired and the CLI is refreshing auth.

Usual fixes:
- Re-run once after refresh.
- Only debug credentials if the next API call still fails.

### `Login did not complete; check credentials` or CAS page says `Wrong password`

Meaning:
- Browser-based login used by the helper scripts failed against the current account password.

Usual fixes:
- Update the password in the same account entry used by native CLI, typically `/root/.config/inspire/config.toml`.
- If token auth and browser auth use different working credentials, keep `password` for native CLI and `web_password` for helper scripts in that same account entry.
- Use `INSPIRE_WEB_PASSWORD` or `--web-password` only as a temporary override while validating a new password.

### `No CPU resource specs returned for the selected compute group`

Meaning:
- The selected CPU workspace / compute group exists, but the platform returned no schedulable CPU training spec for it.

Usual fixes:
- Choose a different CPU workspace or `--location`.
- Pass an explicit `--spec-id` if the correct CPU spec is known.
- Treat this as a resource-discovery issue, not an auth failure, if browser login already succeeded.

## Working assumptions for this setup

- Do not assume `workspace`, `location`, and `image` are coupled; inspect each separately.
- Do not assume inherited shell proxy variables are safe for Inspire traffic.
- Prefer account-scoped password fields over ad hoc shell overrides. Native CLI should read `password`; helper scripts should read `web_password` when present, otherwise fall back to `password`.
- Prefer project config defaults over one-off CLI flags when the user wants repeatable behavior.
- If the user asks to change the default machine room or fallback image, patch the local CLI or `.inspire/config.toml` explicitly instead of relying on memory.
