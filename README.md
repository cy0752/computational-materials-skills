# Computational Condensed Matter Physics Skills

A collection of reusable skills for computational condensed matter physics workflows.

This repository organizes skill modules for VASP input setup, structure preparation, OpenMX data processing, HamGNN training and inference, and remote job submission. Each skill is expected to be usable on its own and also composable into higher-level workflows.

## Installation

The repository contains multiple independent skills. Install it by placing the skill directories under the skills directory used by your agent.

### Project-level installation

Project-level installation keeps the skills available only to one project. From the project root, run:

```bash
skill_tmp_dir="$(mktemp -d)"
git clone https://github.com/cy0752/computational-materials-skills.git "$skill_tmp_dir"
mkdir -p .agents/skills
cp -R "$skill_tmp_dir"/* .agents/skills/
rm -rf "$skill_tmp_dir"
```

The resulting layout should contain entries such as `.agents/skills/vasp-incar-setup/SKILL.md` and `.agents/skills/hamgnn-training/SKILL.md`.

### Global installation

Global installation makes the skills available across projects. Copy the skill directories into your global Codex skills directory:

```bash
skill_tmp_dir="$(mktemp -d)"
git clone https://github.com/cy0752/computational-materials-skills.git "$skill_tmp_dir"
mkdir -p ~/.codex/skills
cp -R "$skill_tmp_dir"/* ~/.codex/skills/
rm -rf "$skill_tmp_dir"
```

If `CODEX_HOME` is configured to a custom location, use `${CODEX_HOME}/skills` in place of `~/.codex/skills`. Restart the agent or reload the project after installation so it discovers the new skills.

## Repository Overview

This repository is better understood as a skill library rather than a single application:

- Each subdirectory represents one standalone skill
- `SKILL.md` defines the skill's purpose, inputs, outputs, and constraints
- `scripts/` contains executable helper scripts
- `templates/` contains configuration templates
- `references/` contains supporting notes or troubleshooting material
- `agents/` contains agent configuration files

The design goals are:

- Keep every skill independently usable
- Decouple workflow orchestration from cluster or platform details

## Skills Included

The repository currently contains the following skills:

- `structure-dft-hamgnn-training-pipeline`  
  A full pipeline starting from a structure file and running primitive CIF generation, perturbed dataset creation, DFT preprocessing (OpenMX by default, ABACUS when explicitly requested), and HamGNN training up to the trained checkpoint.

- `openmx-data-processing`  
  Prepares structure data into HamGNN-consumable graph data for standalone preprocessing stages.

- `abacus-data-processing`  
  Prepares structure data into HamGNN-consumable graph data through the ABACUS route, as an alternative DFT backend.

- `hamgnn-training`  
  Prepares HamGNN training jobs from existing graph datasets and produces the training config and runnable entrypoint.

- `hamgnn-inference`  
  Prepares HamGNN inference or evaluation jobs from an existing model and test dataset.

- `vasp-incar-setup` — Generates or reviews structure-aware VASP `INCAR` and `KPOINTS` settings for relaxations, static calculations, DOS, band structures, phonons, molecular dynamics, DFT+U, noncollinear magnetism, and SOC workflows.

- `remote-task-submit`  
  A compatibility adapter for remote job submission that routes to the canonical generic or workflow-specific submission skills.

## Recommended Reading Order

If you are new to this repository, the suggested reading order is:

1. Start with the `SKILL.md` in the skill you want to use
2. Then review the corresponding `scripts/` and `templates/`
3. For VASP input preparation, read `vasp-incar-setup/SKILL.md` and only the reference files relevant to the calculation
4. If remote execution is involved, read `remote-task-submit/SKILL.md`
5. If you want the full workflow, read `structure-dft-hamgnn-training-pipeline/SKILL.md`

## Usage Notes

### 1. Start with a single skill when possible

If you only need one stage, for example:

- OpenMX data processing only
- HamGNN training only
- HamGNN inference only
- VASP INCAR and KPOINTS setup only

it is better to enter the corresponding skill directory directly and follow the input requirements and execution rules described in its `SKILL.md`.

### 2. Keep remote execution details inside `remote-task-submit`

To keep the repository reusable, environment-specific settings such as queues, accounts, images, node shapes, and scheduler arguments should be maintained in `remote-task-submit` instead of being scattered across higher-level skills.

### 3. Do not commit private environment information

Do not put the following into this repository:

- Private hostnames or internal network addresses
- Usernames, passwords, tokens, or browser sessions
- Machine-room identifiers or cluster-only paths
- Hardcoded defaults that only work in one environment

If a skill depends on environment-specific values, prefer placeholders, environment variables, or local customization.

## Suitable Use Cases

This repository is suitable for:

- Breaking computational condensed matter physics workflows into reusable skills
- Giving AI agents or automation systems clear stage boundaries
- Modularizing the path from structure preparation to simulation, training, and inference
- Reducing upper-layer changes when moving across different machines, queues, or platforms

## Contributing

Contributions are welcome in areas such as:

- Adding new reusable skills
- Improving the input and output contracts in existing `SKILL.md` files
- Expanding templates, scripts, and troubleshooting documentation
- Improving interface consistency across skills

## Improvement Suggestions and Issues

If you find any of the following during actual use:

- unclear documentation
- ambiguous input or output conventions
- skills that are inconvenient to use
- workflow defaults that do not make sense
- scripts, templates, or instructions that could be improved

please submit your usage feedback and improvement suggestions in the repository `Issues`.

When opening an `Issue`, it is helpful to include:

- which skill you were using
- what your usage scenario was
- what problem, friction, or inconvenience you encountered
- what change you would like to see
- commands, error messages, or config snippets if relevant

Suggestions based on real usage are especially valuable for improving this repository over time.

## Possible Future Additions

This repository is expected to grow with more skills for widely used computational condensed matter physics software, including packages such as `SIESTA`.

Future additions may also include:

- example workflows
- minimal input examples for each skill

