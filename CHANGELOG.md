# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [Phase 2] - 2026-05-13

### Added
- `km2arec/geometry.py`: detector geometry loader with four public symbols
  - `GeometryArrays`: plain `NamedTuple` with `ed` and `md` fields, each an `ak.Array` carrying `id`, `x`, `y`, `z` in the CORSIKA coordinate frame
  - `load_geometry(ed_pos_file=None, md_pos_file=None) -> GeometryArrays`: loads the full KM2A array by default (5216 ED + 1188 MD); accepts optional `str | Path` overrides for sub-array or custom layouts; applies the LHAASO→CORSIKA coordinate transform (`x = lhaaso_y`, `y = −lhaaso_x`, `z = z − zeroZ`) on load
  - `build_id_lookup(ids) -> np.ndarray[bool]`: builds a O(1) boolean lookup array (length `max_id + 1`) for testing detector presence; built once at startup
  - `active_hits(hit_ids, lookup) -> np.ndarray[bool]`: pipeline-facing per-event filter; composes with the status predicate (`& (status > 0)`) at numpy-extraction time so simulation inputs are never modified
  - `mark_missing_hits(hits, lookup, absent_status=-2) -> ak.Array`: opt-in annotation utility (not used by the pipeline) that writes `status = absent_status` for geometry-absent hits across all events; provided for diagnostic/pre-filtering workflows
- `km2arec/data/ED_pos_all.txt`: bundled full ED array layout (5216 detectors, `Flag==7` in C++ reference)
- `km2arec/data/MD_pos_all.txt`: bundled full MD array layout (1188 detectors)
- `tests/test_geometry.py`: 38 tests across six groups — default load counts, CORSIKA coordinate correctness for known detector IDs, external file override, `build_id_lookup` correctness, `active_hits` edge cases, `mark_missing_hits` field and structure preservation

### Changed
- `km2arec/__init__.py`: exports `GeometryArrays`, `load_geometry`, `build_id_lookup`, `active_hits`, `mark_missing_hits`
- `pyproject.toml`: added `data/*.txt` to `[tool.setuptools.package-data]` so geometry files are included in the installed package
- `specs/roadmap.md`: Phase 2 redesigned — drops C++ `arrayflag`, bundles full-array geometry as default, documents LHAASO→CORSIKA file format, clarifies that `active_hits` is the pipeline-facing filter (inputs stay pristine) while `mark_missing_hits` is an explicit opt-in utility; calibration deferred to a later phase

## [Phase 1] - 2026-05-13

### Added
- `km2arec/io.py`: three public I/O functions with full type annotations
  - `read_events(path) -> ak.Array`: reads G4KM2A simulation ROOT file (`event` TTree) into a single awkward record with three sub-records — `ed_hits`, `md_hits`, `simulation`; ragged hit arrays merged at event level via `depth_limit=1`
  - `write_rec(path, flat_rec)`: writes flat reconstructed record as TTree `Rec`, compatible with `ROOT::RDataFrame`
  - `read_rec(path) -> ak.Array`: reads `Rec` TTree back as a nested record with five named sub-records (`simulation`, `direction`, `core`, `nkg`, `observables`) supporting dotted attribute access
  - `REC_FIELDS`: exported constant listing all canonical output branch names (mirrors `LHRecEvent`)
- `tests/test_io.py`: 33 tests across `TestReadEvents`, `TestWriteRec`, `TestReadRec` covering field names, ragged shapes, dtypes, hit-count consistency, write/read round-trip, and boolean mask propagation
- `data/km2a_simulation.root`: sample G4KM2A simulation file (234 KB) used as the golden input for IO tests

## [Phase 0] - 2026-05-13

### Added
- `specs/mission.md`: project constitution — physics goals, design principles
- `specs/tech-stack.md`: dependency choices and design conventions
- `specs/roadmap.md`: phased implementation plan (Phases 0–8)
- `km2arec/py.typed`: PEP 561 marker for typed package distribution
- `AGENTS.md`: project-level agent instructions including development workflow and branch naming conventions

### Changed
- `pyproject.toml`: `requires-python >=3.13`; runtime deps `uproot>=5`, `awkward>=2`, `numpy>=1.26`; ruff target updated to `py314`; fixed deprecated `[tool.ruff.lint.per-file-ignores]`
- `Makefile`: `run-checks` now uses `ruff format --check` + `ruff check` + `pytest`; added `format` target
- `.github/workflows/main.yml`: test matrix updated to Python `["3.13", "3.14"]`; lint task uses ruff; removed isort/black/mypy tasks; bumped action versions
