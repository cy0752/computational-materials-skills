---
name: openmx-data-processing
description: Generate HamGNN labeled graph_data.npz from POSCAR or CIF structures with OpenMX. Find or ask for the structure inputs, use the default calculation settings or a supplied OpenMX DAT template, and run SCF, H0/overlap extraction, and graph packaging.
---

# OpenMX Data Processing

## Start from the user's goal

- A request such as “帮我生成 HamGNN 有标签图数据” is enough to start. Resolve structures from paths, attachments, or an upstream stage first. Inspect the current project for a clearly intended set such as `structs/`, including `POSCAR` files in its subdirectories. Ask for the file, directory, or glob only when missing or ambiguous, and list likely candidates when available. Keep existing splits if provided. Treat a single unsplit collection as one dataset.
- In the same message, briefly state the proposed defaults and ask whether the user wants to change any relevant settings. For example, “结构文件或目录在哪里？默认用 OpenMX 做 PBE 单点计算，输出 `work/preprocess/graph_data.npz`。k 点、截断能、磁性/SOC 和输出目录都可以调整。您有想改的设置或现成的 `input.dat` 吗？” If the structures are resolved, ask only about optional changes. Proceed with defaults once required inputs are known. Reuse preferences already given or settled by an upstream pipeline.
- Prefer an explicitly specified template, then a clearly associated project template such as `inputs/input.dat`. Otherwise use the bundled defaults. Tell the user which template was selected, the structure count and elements, and the output path before running. Resolve execution and installation paths from the selected machine.

## Defaults and preparation

- With the bundled `poscar2openmx.yaml`, use a single-point SCF (`MD.Type Nomd`), GGA-PBE, `150 Ry`, `5×5×5` k points, SCF threshold `1e-7`, up to `300` SCF steps, and spin polarization and SOC off. Use the installed HamGNN OpenMX PAO/VPS tables for the elements. K points, cutoff, convergence, spin/SOC, and PAO/VPS can be adjusted explicitly. For a spin-polarized request, resolve the initial moments and choose the matching OpenMX graph packer. The standard non-SOC generator reads a single spin channel. See the upstream OpenMX magnetism documentation when both spin channels or magnetic metadata are needed.
- Parse all selected structures before launch. Check the count, elements, atom order within each structure, and the associated PAO and VPS files. Preserve site order and map input filenames to generated cases. If a custom template contains per-site values such as spin seeds, check that its sites match before transferring those values. Report ambiguous site mappings or incompatible settings before calculating.
- If supplied with a full `.dat` template, preserve its validated calculation settings and species definitions. Write a new DAT for each structure, updating its coordinate and lattice blocks and their units consistently, plus atom count if appropriate. Keep valid per-site columns. Set the run-local `System.Name`, `System.CurrrentDirectory ./`, and a `DATA.PATH` with the selected PAO/VPS files. Verify `HS.fileout` is enabled for labeled data. A complete DAT already contains geometry and species blocks, so stage the generated `<case>.dat` files in `INPUT_ROOT` and use `--prepared-inputs`. For generic structure input, render `poscar2openmx.yaml` and use the packaged converter through the launcher. If the input selection needs multiple globs or recursive search, stage the resolved files under a single run-local glob with unique, format-recognizable filenames.
- Use `work/preprocess/` for a standalone run unless a destination was supplied. If the default is occupied by an earlier run, use a fresh `work/preprocess_<timestamp>/`. Put configs, intermediate files, logs, and `graph_data.npz` under the chosen root, using distinct workdirs for existing train/test splits. For a requested `.npz` basename other than `graph_data.npz`, validate the generated file first, then save it under that name.
- Copy the templates from `<skill_root>/templates/openmx/` into the run directory and render the copies. Use `<system>.scfout` and `<system>.std` in `graph_data_gen.yaml` for labeled data. `overlap.scfout` supplies H0, while the SCF file supplies the reference Hamiltonian. Choose graph `nao_max` by matching the PAO orbital layout to the installed HamGNN basis tables for every element. Prefer `26` for fresh data when compatible, or use the value required by the target checkpoint. Render `soc_switch` to match the OpenMX calculation.
- With `System.CurrrentDirectory ./`, both `openmx` and `openmx_postprocess` must start inside the structure directory and receive only `${SYSTEM_NAME}.dat`. OpenMX 3.9.9 can fail while writing the final-coordinate DAT when given a directory-qualified filename. Apply the current `run_openmx.sh` fix to existing copies before rerunning them.

## Run and verify

- Use `<skill_root>/scripts/data_processing.sh --workdir <openmx_workdir> [--prepared-inputs] [--jobs <jobs>] [--omp-threads <omp_threads>]` for the standard graph route. The launcher prepares the DAT files unless they are already staged, runs both OpenMX stages, and packages the graphs using the HamGNN >= 2.3.0 modules. Run on the current machine when the user specifies that server or local execution. For Inspire jobs, including the default submitted route, use `inspire-openmx-submit` to resolve and validate the execution profile. The canonical profile uses `16` tasks with `2` CPUs per task, `2` OpenMP threads per structure, and workers calculated from the available job budget and capped by the structure count. Use explicitly requested scheduling overrides.
- Verify that the expected SCF and H0 output files exist and that the generated `.npz` contains the expected number of graphs with reference Hamiltonian, overlap, and H0 fields. The standard packer can skip cases, including cases above its default `max_SCF_skip: 200`. Investigate missing cases and report any remaining failures with their log paths and graph count. Return the verified dataset and workdir paths.
- For prediction inputs routed from `hamgnn-inference`, use `--postprocess-only` and render `graph_data_gen.yaml` with `scfout_file_name: overlap.scfout` and `std_file_name: null`. Use the selected model's basis and spin settings. This graph contains H0 and overlap in place of an SCF reference.

## Runtime contract

This skill does not assume a dedicated conda environment or any particular provenance of the tools. The caller must guarantee, on the execution machine:

- `PYTHONBIN` (default `python`): an interpreter where `DFT_interfaces` is importable — true when HamGNN is pip-installed, or when `HAMGNN_ROOT` points at a HamGNN source checkout (exported to `PYTHONPATH` by the scripts).
- OpenMX executables `openmx` and `openmx_postprocess` are runnable: on `PATH`, or provided via `OPENMX_BIN` / `OPENMX_POSTPROCESS_BIN` absolute paths.
- `read_openmx` is the executable that converts `.scfout` to `HS.json`. Resolve an existing runnable copy on the execution machine or build it from the HamGNN sources. Verify the OpenMX database has both the needed `PAO` and `VPS` files before rendering `DATA.PATH`.
- Optional `OPENMX_CONDA_ENV` activates a conda env inside `run_openmx.sh` only when explicitly set; `ONEAPI_SETVARS`, `MKLROOT`, `GSL_LIB_PATH` remain optional site hooks.
- `graph_data_gen.yaml.nao_max` accepts `14`, `19`, or `26`. The generator writes `graph_data.npz`.
- `band_cal` band plotting requires the flat `Hon`/`Hoff` layout written by `graph_data_gen`, and its input npz must store torch_geometric `Data` objects — a plain dict fails with `'dict' object has no attribute 'Hon'`.
- For a single-channel model (e.g. the v2.1 universal non-SOC pickle), set `spin_colinear: false` in the band_cal config so it takes the non-spin reshape branch.
- The launcher derives total CPUs from the scheduler allocation or explicit runtime values such as `OPENMX_TOTAL_CPUS`. For a local run, set an appropriate CPU budget when needed.
