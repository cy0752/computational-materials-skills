---
name: vasp-incar-setup
description: Generate or review structure-aware VASP INCAR and KPOINTS settings from POSCAR, CONTCAR, CIF, or related structure files. Use for relax, static, DOS, band, phonon, MD, spin-polarized, noncollinear, SOC, and DFT+U setup questions before job submission.
---

# VASP INCAR Setup

Use this skill when the user wants to prepare, review, or troubleshoot VASP input settings from a structure and a calculation goal.

This skill is for setup quality, not job submission. If the user wants to run the job through Inspire after the inputs are prepared, pair this skill with `inspire-vasp-submit`.

## Use This Skill For

- generating a first-pass `INCAR`
- reviewing whether an existing `INCAR` matches the intended workflow
- proposing `KPOINTS` defaults when the user has only a structure file
- handling relax, static, DOS, band structure, phonon, MD, hybrid, DFT+U, NCL, or SOC setup
- troubleshooting obvious setup-level problems before or after a failed run

## Core Workflow

1. Read the user goal and identify the task type.
2. Read the structure file if one is available.
3. Infer the system class conservatively:
- bulk
- slab or surface
- 2D material
- molecule in a box
- defect supercell
4. Resolve only the missing inputs that materially affect correctness:
- target quality: `test`, `standard`, or `production`
- metallic, insulating, or unknown
- spin-polarized, non-magnetic, or unknown
- whether `DFT+U` is required
- whether `SOC` is required
- whether vdW corrections matter
- for relaxations, whether to relax ions only or ions plus cell
5. Generate a copyable `INCAR`.
6. Include `KPOINTS` guidance if the user did not provide one.
7. State assumptions and what must be checked before production use.

## NCL and SOC Rules

Read [references/noncollinear-soc.md](references/noncollinear-soc.md) whenever the user mentions any of:

- `NCL`
- noncollinear magnetism
- spin canting
- `LSORBIT`
- magnetic anisotropy
- spin direction
- `SAXIS`

For noncollinear work:

- do not silently invent detailed vector `MAGMOM` values
- ask for or clearly label provisional moment directions
- separate plain noncollinear from noncollinear plus `SOC`
- do not add `ISPIN = 2` by default when `LNONCOLLINEAR = .TRUE.`; VASP ignores `ISPIN` in noncollinear mode, and VASP 6.5.0 errors for `ISPIN = 2` together with `MAGMOM` and `LNONCOLLINEAR`
- use the `vasp_ncl` executable for noncollinear calculations
- if `SOC` is enabled, call out the need to review symmetry, k-point density, and convergence choices
- when `I_CONSTRAINED_M = 1` is active, require an explicit constrained-NCL
  profile review covering `M_CONSTR`, `LAMBDA`, charge/spin mixing, and
  `RWIGS`; do not emit a minimally constrained template that omits those
  decisions
- treat `RWIGS` and density-mixing values as system- and workflow-specific;
  obtain them from user-provided or validated same-project provenance, and
  preserve them across calculations whose energies, forces, stresses, or
  polarization differences will be combined

## Guardrails

- Do not silently invent `LDAU*` values.
- Do not enable `SOC` by default.
- Do not claim `ENCUT = 520` is universal. Prefer `1.3 x max(ENMAX)` when POTCAR information exists.
- Do not default every relaxation to `ISIF = 3`.
- Do not present a band-structure workflow as a single calculation without separating SCF and non-SCF stages.
- Do not claim a setup is production-ready without noting convergence checks.

## Output Pattern

When producing a setup, prefer this structure:

### Assumptions

Short bullet list of what was inferred or defaulted.

### Questions to confirm

Only include unresolved items that change the recommended settings.

### Recommended INCAR

Provide a complete block the user can copy.

### KPOINTS notes

Provide a concrete mesh suggestion or explain what depends on convergence testing.

### What to check next

Call out the main validation items such as `ENMAX`, spin state, `MAGMOM`, `DFT+U`, `SOC`, vacuum handling, or convergence.

## Reference Map

Read only the files needed for the current task:

- [references/relaxation.md](references/relaxation.md): bulk, slab, 2D, molecule, and defect relaxation defaults
- [references/electronic-structure.md](references/electronic-structure.md): static, DOS, and band-structure workflows
- [references/molecular-dynamics.md](references/molecular-dynamics.md): VASP MD ensembles and runtime settings
- [references/phonons.md](references/phonons.md): DFPT and finite-displacement phonon setups
- [references/advanced-functionals.md](references/advanced-functionals.md): DFT+U, hybrids, GW, and advanced methods
- [references/convergence.md](references/convergence.md): `ENCUT` and k-point convergence strategy
- [references/parameter-reference.md](references/parameter-reference.md): quick lookup for common INCAR tags
- [references/troubleshooting.md](references/troubleshooting.md): SCF, relaxation, geometry, and resource failures
- [references/noncollinear-soc.md](references/noncollinear-soc.md): noncollinear and spin-orbit setup details
