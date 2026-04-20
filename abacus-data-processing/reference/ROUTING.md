# ABACUS Reference Routing (Agent Quick Lookup)

Purpose:
- Provide a fast, high-precision routing index from user intent to the most relevant reference markdown(s).
- Help agents decide when to keep defaults and when to switch to case-specific parameter patterns.

How to use this file:
1. Match user intent with the table below using both task type and physics context.
2. If one route is a strong match, open the linked markdown and align key parameters with that case.
3. If no strong match is found, keep the skill default template settings.

Strong-match rule (recommended):
- A route is "strongly matched" when at least two of the following align:
  - workflow/task type (for example: SCF, MD, SDFT, DOS/PDOS, surface, elastic),
  - system context (for example: magnetic metal, heterojunction, high-temperature WDM),
  - method/basis hint (for example: PW, LCAO, stochastic DFT).

## Intent Routing Table

| User intent (examples) | Trigger keywords (CN / EN) | Primary reference markdown(s) | Companion examples | Notes for configuration |
|---|---|---|---|---|
| "一般结构批量 SCF 数据生成" | 批量、结构转 INPUT、SCF、默认 / batch, structure-to-input, default | (skill template default) | `templates/abacus/abacus_input_gen.yaml` | Use baseline config unless a specialized route below is a strong match. |
| "平面波典型基准（10 case）" | 平面波、10例、benchmark、cg、dav_subspace / PW, benchmark | `test-10cases2.md` | `examples/pw2-cg`, `examples/pw2-ds` | Prefer updated benchmark settings in V2026.1.27 cases. |
| "LCAO 典型基准（10 case）" | LCAO、轨道基、10例 / LCAO, NAO benchmark | `test-10cases-lcao.md` | `examples/lcao-gv` | Use LCAO-specific tested patterns. |
| "难收敛磁性异质结（TiC-Ni 类）" | 异质结、磁性、Ni、收敛困难 / heterojunction, magnetic, hard convergence | `test-ticni.md`, `abacus-conv.md` | `examples/TiC-Ni` | Borrow robust SCF mixing and spin-related settings from the case. |
| "高温/温稠密物质（SDFT/MDFT）" | 高温、WDM、随机DFT、MDFT / high temperature, stochastic DFT | `test-sdft.md`, `abacus-sdft.md` | `examples/sdft_bench`, `examples/stochastic` | Switch to `esolver_type=sdft` pattern and related stochastic parameters. |
| "分子动力学（AIMD/LJMD/DPMD）" | 分子动力学、md、nvt、npt / molecular dynamics, MD | `abacus-md.md`, `abacus-dpmd.md` | `examples/md` | Use `calculation=md` families and thermostat/integrator controls from docs. |
| "DOS/能带" | 态密度、能带、DOS、band / DOS, band structure | `abacus-dos.md` | `examples/dos_band` | Follow SCF + band/DOS post-process workflow in the guide. |
| "PDOS" | PDOS、投影态密度 / projected DOS | `abacus-pdos.md` | (see `abacus-pdos.md`) | Use PDOS-specific post-processing settings. |
| "电荷密度/波函数导出与可视化" | 电荷密度、CHG、cube、波函数 / charge density, wavefunction | `abacus-chg.md` | (see `abacus-chg.md`) | Enable output controls required for CHG/WFC extraction. |
| "ELF 电子局域函数" | ELF、局域函数 / ELF | `abacus-elf.md` | `examples/elf` | Apply ELF-specific output settings and workflow. |
| "Bader 电荷分析" | Bader、电荷分析 / Bader charge | `abacus-bader.md` | (see `abacus-bader.md`) | Requires compatible charge-density outputs first. |
| "弹性常数" | 弹性常数、应变 / elastic constants | `abacus-elastic.md`, `abacus-elastic2.md` | `examples/elastic` | Use strain workflow and post-processing scripts as documented. |
| "声子/热导（Phonopy/ShengBTE）" | 声子、Phonopy、热导 / phonon, thermal conductivity | `abacus-phonopy.md`, `abacus-shengbte.md`, `abacus-phonopy-heat.md` | `examples/interface_Phonopy`, `examples/interface_ShengBTE` | Route by property target (phonon spectrum vs conductivity vs thermodynamics). |
| "Wannier90 接口" | Wannier、MLWF / Wannier90 | `abacus-wannier.md`, `algorithm-wannier.md` | `examples/interface_Wannier90` | Follow interface-specific file/output requirements. |
| "表面功函数/静电势" | 表面、功函数、静电势 / surface, work function | `abacus-surface1.md` | (see `abacus-surface1.md`) | Use surface-vacuum conventions from the tutorial. |
| "表面偶极修正" | 偶极修正、slab / dipole correction | `abacus-surface2.md` | `examples/dipole_correction` | Apply dipole-correction pattern for slab/vacuum systems. |
| "表面能" | 表面能 / surface energy | `abacus-surface3.md` | `examples/surface_energy` | Use bulk+slab paired workflow as documented. |
| "表面缺陷/吸附能" | 缺陷、吸附 / vacancy, adsorption | `abacus-surface4.md` | `examples/surface_vacancy_adsorption` | Follow reference-state consistency and energy-difference workflow. |
| "外加电场" | 外电场、电场 / electric field | `abacus-surface5.md` | `examples/electric_field` | Apply field-direction and spin/SCF workflow in examples. |
| "补偿电荷" | 补偿电荷 / compensating charge | `abacus-surface6.md` | `examples/compensating_charge` | Use compensating-charge setup for charged slab-type problems. |
| "杂化泛函" | 杂化泛函、HSE、EXX / hybrid functional | `abacus-exx.md`, `abacus-libri.md` | `examples/hybrid_functional` | Replace baseline SCF settings with hybrid-functional workflow controls. |
| "机器学习势流程接口（DPGEN/DeePKS）" | DPGEN、DeePKS、数据标注 / DPGEN, DeePKS | `abacus-dpgen.md`, `abacus-deepks-es.md`, `abacus-deepks-toturial-rh111.md` | `examples/abacus-dpgen`, `examples/deepks-es`, `examples/deepks-CO` | Use as workflow references, not a direct replacement for default SCF generation unless explicitly requested. |

## Not primary for runtime config generation

These are valuable but usually not the first stop for input generation:
- Build/installation docs (`abacus-gcc.md`, `abacus-oneapi.md`, `abacus-gpu.md`, etc.).
- Developer internals (`develop-*.md`, `algorithm-delta.md`).
- Project/news/contribution pages.

Use them only when the user's request is explicitly about build environment, code internals, or development workflow.
