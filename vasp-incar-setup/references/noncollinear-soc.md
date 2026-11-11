# Noncollinear and SOC Setup

Use this reference when the user asks for noncollinear magnetism, spin canting, magnetic anisotropy, or any setup involving `LNONCOLLINEAR` and `LSORBIT`.

The rules below follow the VASP Wiki pages for [LNONCOLLINEAR](https://vasp.at/wiki/LNONCOLLINEAR), [SAXIS](https://vasp.at/wiki/SAXIS), [LSORBIT](https://vasp.at/wiki/LSORBIT), [MAGMOM](https://vasp.at/wiki/MAGMOM), [ALGO](https://vasp.at/wiki/ALGO), [IALGO](https://vasp.at/wiki/IALGO), and [density mixing](https://vasp.at/wiki/Category:Density_mixing).

## Decide Which Case Applies

### Case 1: Collinear spin only

Typical starting point:

```bash
ISPIN = 2
MAGMOM = ...
```

Use when the moments are expected to lie along a shared axis and the user does not need spin canting or spin-orbit coupling.

### Case 2: Noncollinear without SOC

Typical core tags:

```bash
LNONCOLLINEAR = .TRUE.
MAGMOM = mx1 my1 mz1 mx2 my2 mz2 ...
```

Use when the user wants canted or non-parallel local moments but does not yet need spin-orbit effects.

### Case 3: Noncollinear with SOC

Typical core tags:

```bash
LNONCOLLINEAR = .TRUE.
LSORBIT = .TRUE.
SAXIS = 0 0 1
MAGMOM = mx1 my1 mz1 mx2 my2 mz2 ...
```

Use when the target quantity depends on spin direction, anisotropy, magnetocrystalline energy, or SOC-induced band splitting.

## Minimum Questions Before Finalizing

- Is the task `static`, `relax`, `band`, or `DOS`?
- Is this noncollinear only, or noncollinear plus `SOC`?
- Which atoms are expected to carry local moments?
- What initial moment directions should be used?
- Is `DFT+U` required for the magnetic species?
- Is this a quick test or a production calculation?

If the user cannot specify moment directions, state that the vector `MAGMOM` values are provisional and should be validated against the intended magnetic order.

### VASP version note for `ISPIN`

- In noncollinear mode, VASP ignores `ISPIN`; do not add `ISPIN = 2` to a new NCL input by default.
- VASP 6.5.0 reports an error when `ISPIN = 2`, `MAGMOM`, and `LNONCOLLINEAR = .TRUE.` are combined. Omitting `ISPIN` is compatible with both older and newer VASP versions.
- Use the `vasp_ncl` executable for NCL and SOC calculations.

## Practical Rules

### `MAGMOM`

- In noncollinear mode, `MAGMOM` must be supplied as three components per magnetic site.
- **Values must stay on the SAME line as the tag.** Writing `MAGMOM =` and
  putting the numbers on the following lines is NOT parsed as a continuation
  by VASP 6.4.0: the startup banner reports `In line N: Tag MAGMOM is not
  assigned`, and the run silently falls back to the default 1 uB per atom
  ferromagnetic seed (verified on a live H100 run, 2026-09-18). The same
  applies to `M_CONSTR`. Long single lines (500+ characters) are accepted.
- Do not silently generate arbitrary vectors for chemically ambiguous systems.
- If only the magnetic sublattice is known, use clearly labeled provisional vectors and explain that the final state may converge to a different order.
- When long runs of repeated zero components appear, compress them with VASP repeat notation such as `81*0` instead of writing dozens of trailing `0.0` values.
- In noncollinear mode, the repeat count in `N*0` refers to scalar components, not atoms. For example, `81*0` means 27 nonmagnetic sites with `(0, 0, 0)`.

### `I_CONSTRAINED_M` and `M_CONSTR`

- Enable `I_CONSTRAINED_M = 1` only when the user explicitly needs to hold
  specified local-moment directions, or when the workflow requires controlled
  states for four-state mapping or directional magnetic comparisons. Ordinary
  noncollinear calculations should not be constrained by default.
- By default, set `M_CONSTR` equal to `MAGMOM` so the initial constrained directions match the initial spin seed.
- Do not generate `M_CONSTR` independently. Reuse the exact `MAGMOM` expression verbatim, including any compressed repeat notation such as `81*0`.
- Apply the same formatting rule to `M_CONSTR` as to `MAGMOM`, including compressed repeat notation such as `81*0`.
- When `I_CONSTRAINED_M = 1`, do not stop after writing only
  `MAGMOM`, `M_CONSTR`, and `LAMBDA`. Explicitly review and either write or
  document the provenance of `AMIX`, `BMIX`, `AMIX_MAG`, `BMIX_MAG`, and
  `RWIGS` before calling the INCAR complete.

### `RWIGS` in constrained noncollinear calculations

- With `I_CONSTRAINED_M = 1`, the constraint acts on local moments integrated
  inside atom-centered spheres. `RWIGS` therefore participates in the
  definition and reporting of the constrained local moments; it is not merely
  a projected-DOS formatting choice in this context.
- Supply one radius per POTCAR/POSCAR species, in exactly the same species
  order. Do not infer a universal radius table. Use values explicitly supplied
  by the user, taken from the selected POTCAR/project protocol, or validated in
  a same-system calculation, and label their provenance.
- **UNIT TRAP (hard rule, incident 2026-10-26):** POTCAR prints RWIGS in TWO
  columns — `RWIGS =  2.200; RWIGS =  1.164    wigner-seitz radius (au A)` —
  the first number is Bohr (au), the second is Ångström. **The INCAR `RWIGS`
  expects Ångström: always take the SECOND (A) column.** Copying the au value
  into INCAR inflates every sphere by 1.89×; with nearest-neighbor distances
  of a few Å the spheres then overlap heavily, the constrained "local moment"
  is integrated over a wrong, double-counting region, the penalty force turns
  noisy, and the SCF charge-sloshes without converging (FGT batch incident:
  RWIGS=2.200 instead of 1.164 → 8+ samples oscillated to NELM exhaustion).
  When sourcing radii from a POTCAR, quote both columns in the provenance
  note and record the Å value actually written.
- Keep `RWIGS` identical across all states in a four-state mapping, magnetic
  energy comparison, force/stress difference, or Berry-polarization
  difference. Adding or changing it changes the operationally constrained
  state, so results with different `RWIGS` should not be mixed silently.
- If trustworthy radii are unavailable, leave a visible unresolved item and
  ask for them rather than inventing values. A no-`RWIGS` pilot can be useful
  diagnostically, but it is not automatically equivalent to a production run
  that later adds `RWIGS`.

### `SAXIS`

- `SAXIS` defaults to `0 0 1`, i.e. spinor axes coincide with Cartesian `x,y,z` axes.
- For NCL without SOC, a from-scratch calculation can normally omit `SAXIS`: only relative local-moment directions affect the energy, and `MAGMOM` vectors are given in Cartesian coordinates.
- With `LSORBIT = .TRUE.`, `SAXIS` defines the spinor basis relative to the lattice. Explicitly write `SAXIS = 0 0 1` for clarity, or set a different axis intentionally and transform `MAGMOM` components into that basis.
- When restarting from a collinear magnetization density, `SAXIS` also controls the global interpretation/rotation of the imported magnetization.
- If the user is comparing anisotropy energies, keep every other setting fixed while changing only the spin direction setup.

### Symmetry

- `SOC` and noncollinear magnetism often reduce the usable symmetry.
- If convergence or symmetry behavior looks suspicious, be prepared to test with lower symmetry handling rather than assuming the default symmetry treatment is safe.

### Smearing

- For metallic magnetic systems, use a metal-appropriate smearing choice for relaxations.
- For static total-energy comparisons, prefer a more accurate static setup once the magnetic state is stabilized.

### SCF Mixing and Algorithm

- Prefer `ALGO = Normal` as the robust self-consistency baseline for NCL; in current VASP this selects blocked-Davidson (`IALGO = 38`).
- Do not set `ALGO` and `IALGO` together to conflicting values. If an explicit legacy setting is needed, use `IALGO = 38` without `ALGO = ...`.
- `IALGO = 38` is a plausible NCL troubleshooting fallback when an RMM-DIIS-based choice (`ALGO = VeryFast` or a version-specific equivalent) is unstable, but it does not guarantee that an NCL job will not fail. Prefer the named `ALGO` interface for new inputs.
- Tune `AMIX`, `BMIX`, `AMIX_MAG`, and `BMIX_MAG` from the dielectric-eigenvalue diagnostics in `OUTCAR`; do not treat one set as universal.
- For `I_CONSTRAINED_M = 1`, include both charge-channel (`AMIX`, `BMIX`) and
  magnetization-channel (`AMIX_MAG`, `BMIX_MAG`) settings in the explicit
  setup review. Reuse a validated same-system profile for comparable state
  batches; otherwise label the proposed profile as provisional and verify SCF
  behavior before production.

### Project empirical mixing profile

For the constrained NCL PBE+U static NiCl2 workflow represented by this project, a repeatedly used starting profile is:

```bash
AMIX = 0.4
BMIX = 0.0001
AMIX_MAG = 0.4
BMIX_MAG = 0.0001
```

This profile is an empirical, workflow-specific setting—not a VASP default. It is reasonable to try for similar constrained magnetic slabs or supercells, then verify convergence and final energies. If the charge or magnetization oscillates, reduce the relevant `AMIX*`; if convergence is excessively slow, retune using the `OUTCAR` dielectric-eigenvalue spectrum. VASP Wiki gives other system-dependent candidates (for example `AMIX=0.2`, `AMIX_MAG=0.8`, both `BMIX* = 0.0001`), so retain the project profile as a labeled option rather than replacing the general guidance.

For the validated constrained-NCL/SOC BiFeO3 polarization workflow in
`universaldipole2`, the established same-project profile is:

```bash
AMIX = 0.2
BMIX = 0.0001
AMIX_MAG = 0.4
BMIX_MAG = 0.0001
# Bi Fe O species order; project-specific radii in Angstrom
RWIGS = 1.635 1.164 0.820
```

These numbers are provenance for that BiFeO3 workflow, not general defaults.
The `RWIGS` row is valid only when the POSCAR/POTCAR species order is
`Bi Fe O`. In that project, adding the explicit radii made the Fe sphere
moments visible and changed constrained-SOC energies by about `1e-4 eV` per
80-atom displaced cell, while the derived force-constant RMS changed by about
`0.12%`. This is small but confirms that no-`RWIGS` and explicit-`RWIGS` runs
do not define exactly the same constrained state.

### Convergence

- SOC energy differences can be small, so k-point and electronic convergence usually need to be tighter than a rough relaxation.
- If the user is after anisotropy or band splitting, call out that the result is more sensitive to k-point density than a basic test run.

## First-Pass Templates

### NCL Static Without SOC

```bash
SYSTEM = noncollinear static
ENCUT = 520
PREC = Accurate
EDIFF = 1E-6
NELM = 120
ALGO = Normal
# Project empirical NCL profile; retune for other systems
AMIX = 0.4
BMIX = 0.0001
AMIX_MAG = 0.4
BMIX_MAG = 0.0001
# Required decision for I_CONSTRAINED_M=1; replace with species-ordered,
# same-project values. Do not copy this placeholder into a production run.
# RWIGS = r_species1 r_species2 ...
IBRION = -1
NSW = 0
LNONCOLLINEAR = .TRUE.
MAGMOM = 0 0 5   0 0 -5
I_CONSTRAINED_M = 1
M_CONSTR = 0 0 5   0 0 -5  # copy MAGMOM verbatim
# LAMBDA = <project-validated penalty strength>
ISMEAR = 0
SIGMA = 0.05
LWAVE = .FALSE.
LCHARG = .FALSE.
```

This is only a placeholder pattern. Replace the `MAGMOM` vectors with the
actual magnetic sublattice and expected directions. For an unconstrained NCL
run, remove the linked `I_CONSTRAINED_M`, `M_CONSTR`, `LAMBDA`, and `RWIGS`
constraint block rather than leaving a partial setup.

### NCL Static With SOC

```bash
SYSTEM = noncollinear SOC static
ENCUT = 520
PREC = Accurate
EDIFF = 1E-6
NELM = 120
ALGO = Normal
# Project empirical NCL profile; retune for other systems
AMIX = 0.4
BMIX = 0.0001
AMIX_MAG = 0.4
BMIX_MAG = 0.0001
# Required decision for I_CONSTRAINED_M=1; replace with species-ordered,
# same-project values. Do not copy this placeholder into a production run.
# RWIGS = r_species1 r_species2 ...
IBRION = -1
NSW = 0
LNONCOLLINEAR = .TRUE.
LSORBIT = .TRUE.
SAXIS = 0 0 1
MAGMOM = 0 0 5   0 0 -5
I_CONSTRAINED_M = 1
M_CONSTR = 0 0 5   0 0 -5  # copy MAGMOM verbatim
# LAMBDA = <project-validated penalty strength>
ISMEAR = 0
SIGMA = 0.05
LWAVE = .FALSE.
LCHARG = .FALSE.
```

For an unconstrained NCL+SOC run, remove the linked `I_CONSTRAINED_M`,
`M_CONSTR`, `LAMBDA`, and `RWIGS` constraint block. For magnetic anisotropy
studies, compare multiple spin directions with identical structural, k-point,
and convergence settings.

## Common Failure Modes

### User provides only a POSCAR and says "write NCL INCAR"

You can still generate a first-pass file, but state explicitly that at least these items remain provisional:

- magnetic atoms
- vector `MAGMOM`
- whether `SOC` is required
- whether `DFT+U` is required

### SCF instability after enabling NCL or SOC

Try, in order:

1. Verify the starting magnetic pattern is physically sensible.
2. Use safer smearing for the material class.
3. Increase `NELM`.
4. Tighten the structure quality or start from a converged collinear solution first.
5. Revisit symmetry handling only after the simpler causes are checked.

### A constrained-NCL batch mixes runs with and without `RWIGS`

- Do not treat this as a harmless output-only difference. Confirm the species
  order and radius provenance, then use one `RWIGS` convention consistently
  for every state entering the same energy, force, stress, or polarization
  combination.
- If the batch has already run, retain the mismatch in provenance and rerun
  the inconsistent states when a quantitative state-difference comparison is
  required.

### Relaxation with SOC

- Prefer relaxing first without `SOC` unless the user explicitly needs SOC during relaxation.
- Then run the final noncollinear plus `SOC` static step on the relaxed structure.
