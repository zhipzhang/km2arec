# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

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
