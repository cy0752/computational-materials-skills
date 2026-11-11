# Structure Relaxation Subskill

Detailed guidance for generating or reviewing VASP relaxation settings after the system type has been identified.

## Purpose

Use this subskill after the main skill has already clarified:
- the structure type
- whether the task is a relaxation
- whether cell relaxation is physically appropriate

This subskill is meant to refine the setup, not to blindly apply one template to every structure.

## Main Decision Rule

For relaxations, the most important decision is usually **what is allowed to move**.

### Default choices by system class

| System class | Typical default | Why |
|---|---|---|
| Bulk crystal | `ISIF = 3` | Relax ions and cell together if equilibrium lattice is sought |
| Slab / surface | `ISIF = 2` | Keep vacuum direction fixed by default |
| 2D material | `ISIF = 2` | Avoid changing vacuum direction unless intentionally modeling stress |
| Molecule in a box | `ISIF = 2` | Usually optimize internal coordinates only |
| Defect supercell | `ISIF = 2` initially | Cell often kept fixed unless defect strain is part of the study |

If the user asks for full cell relaxation in a slab, 2D system, or molecule-in-box setup, explicitly warn that this may distort the vacuum direction or change the intended model.

## Base Relaxation Template

Start from this conservative template and adapt it to the system class.

```bash
SYSTEM = structure relaxation
ENCUT = 520
PREC = Accurate
EDIFF = 1E-6
NELM = 100
IBRION = 2
NSW = 100
EDIFFG = -0.02
ISMEAR = 0
SIGMA = 0.05
LREAL = Auto
LWAVE = .FALSE.
LCHARG = .FALSE.
```

Notes:
- `ENCUT = 520` is only a placeholder if `ENMAX` is unknown.
- Prefer `ENCUT ≈ 1.3 × max(ENMAX)` from the actual POTCAR.
- `ISMEAR = 0` / `SIGMA = 0.05` is a safe default when metallicity is unknown.

## Bulk Relaxation

Use when the structure is a 3D periodic solid and the user wants equilibrium lattice parameters or full structural optimization.

Recommended additions:
```bash
ISIF = 3
IBRION = 2
```

Typical smearing:
- likely metal:
```bash
ISMEAR = 1
SIGMA = 0.2
```
- likely semiconductor / insulator:
```bash
ISMEAR = 0
SIGMA = 0.05
```

## Slab / Surface Relaxation

Default goal: relax atomic positions while keeping the simulation cell fixed.

Recommended settings:
```bash
ISIF = 2
IBRION = 2
```

Additional checks:
- confirm vacuum thickness is sufficient
- check whether dipole correction is needed for asymmetric slabs
- use anisotropic k-point sampling, usually dense in-plane and sparse out-of-plane

Do not default to `ISIF = 3` for slab work.

## 2D Material Relaxation

Treat most 2D systems similarly to slabs unless the user explicitly wants in-plane stress optimization.

Recommended default:
```bash
ISIF = 2
```

If the user wants in-plane lattice optimization, say so explicitly and note that vacuum handling must remain controlled.

## Molecule in a Box

Recommended default:
```bash
ISIF = 2
ISMEAR = 0
SIGMA = 0.01
```

Also note:
- Gamma-point sampling is often sufficient
- box size should be checked separately

## Defect Supercell Relaxation

A common conservative starting point is:
```bash
ISIF = 2
```

Why:
- fixed supercell calculations are often easier to compare across charge states or defect configurations
- cell relaxation can be added later if needed

## Convergence Tightness

### Standard
```bash
EDIFF = 1E-6
EDIFFG = -0.02
```

### Tighter relaxation
Use when preparing for phonons, subtle energy differences, or higher-accuracy follow-up work.
```bash
EDIFF = 1E-7
EDIFFG = -0.01
```

## When to Ask the User Before Finalizing

Ask if any of these materially affect correctness:
- Is the system metallic?
- Should the run be spin-polarized?
- Is DFT+U needed?
- Should the cell be relaxed, or only the ions?
- Is this slab / 2D system supposed to keep vacuum fixed?

## Suggested Output Pattern

When proposing a relaxation INCAR, include:
1. inferred system class
2. assumptions
3. recommended INCAR
4. why `ISIF` was chosen
5. what to verify next

## Common Failure Modes

### SCF oscillation
Try, in order:
1. confirm the structure is reasonable
2. use a safer smearing choice
3. increase `NELM`
4. switch `ALGO`
5. adjust mixing only if simpler changes fail

### Relaxation instability
Try, in order:
1. reduce `POTIM`
2. switch to a more robust ionic optimizer if needed
3. inspect the starting geometry for short contacts

### Suspicious slab results
Check:
- vacuum thickness
- `ISIF` choice
- whether dipole correction is needed
- whether k-point sampling is too isotropic for a slab model
