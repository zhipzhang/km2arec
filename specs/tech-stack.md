# Tech Stack

## Runtime language

**Python 3.14** is the minimum required version. The project targets the current CPython release to take advantage of the latest typing features and performance improvements.

## Core dependencies

### I/O

| Library | Role | Replaces |
|---|---|---|
| `uproot` | Read and write ROOT TTree files without a ROOT installation | `TFile`, `TTree`, ROOT dictionary classes |

`uproot` reads the `event` tree (containing raw `LHEvent`/`LHHit` data) into awkward arrays, and writes the `Rec` tree directly from an awkward array. The ROOT file format is preserved for backward compatibility with existing analysis workflows.

Awkward arrays written by `uproot` produce ROOT TTrees that are fully compatible with `ROOT::RDataFrame`, allowing downstream analyses to load the output with zero format conversion.

### In-memory data representation

| Library | Role | Replaces |
|---|---|---|
| `awkward-array` | All in-memory event data: ragged hit arrays (input) and flat reconstructed-output arrays (output) | `std::vector<LHHit>` inside `LHEvent`; `LHRecEvent` written to TTree |
| `numpy` | Fixed-shape numerical arrays; all fit math | `double[]`, `std::vector<double>` in C++ |

Awkward-array is used end-to-end:
- **Input:** ragged columnar hit arrays (variable number of hits per event) read from the `event` tree.
- **Numerical work:** NumPy slices are extracted from awkward arrays for per-event fit computations.
- **Output:** reconstructed scalars per event are accumulated into a flat awkward array, then written directly to the `Rec` TTree via `uproot`. This output is immediately consumable by `ROOT::RDataFrame` without any format conversion.

### Numerical algorithms

| Library | Role | Replaces |
|---|---|---|
| `numpy.linalg` | Weighted least-squares for planar and conical fits | Hand-rolled Gaussian elimination in `G4KM2A_Reconstruction.cc` |
| `scipy.optimize` | NKG negative log-likelihood minimization (`minimize` with bounds) — **optional, added in Phase 5** | MINUIT (`TMinuit` / `TFitter`) |

`scipy` is not a declared runtime dependency until Phase 5. When added, `scipy.optimize.minimize` with the `L-BFGS-B` method (supports parameter bounds) is the default minimizer for the NKG fits. It operates on the same objective function — negative Poisson log-likelihood — as the C++ MINUIT call.

### Testing

| Library | Role |
|---|---|
| `pytest` | Unit tests for each reconstruction stage; regression tests against C++ reference output |
| `pytest-cov` | Coverage reporting |

Golden reference outputs are generated once from `KM2AMCrec_V3` on a fixed sample file and committed to `tests/reference/`. Regression tests assert that km2arec output agrees with the reference to within a defined numerical tolerance.

### Linting and type checking

| Tool | Role |
|---|---|
| `ruff` | Fast linter (replaces flake8 + isort) |
| `black` | Deterministic code formatting |
| `mypy` | Static type checking |

All are already declared in `pyproject.toml [project.optional-dependencies.dev]`.

## What is explicitly excluded

- **ROOT** — no `import ROOT` anywhere in the package. ROOT is only needed to run the C++ reference for validation.
- **MINUIT / iminuit** — replaced by `scipy.optimize`.
- **pandas** — not used; awkward-array covers both the ragged input and the flat output, and writes directly to ROOT TTree via uproot.
- **Cython / compiled extensions** — the goal is pure Python + NumPy. If a hot inner loop turns out to need acceleration, `numba` (JIT) is the preferred path, not Cython.
- **Dask / Ray** — out of scope for now. Parallelism across events can be added later at the pipeline level without changing reconstruction functions.

## Design conventions

- **Arrays in, arrays out.** Every reconstruction function signature is approximately `f(x: np.ndarray, y: np.ndarray, t: np.ndarray, ...) -> SomeNamedTuple`. No mutable objects are modified in place.
- **Geometry and calibration as plain data.** `GeometryTable` and `CalibrationMask` are `dataclasses` (or simple named tuples) holding NumPy arrays. They are constructed once at startup and passed into functions as arguments.
- **Type annotations on all public functions.** `mypy --strict` is the target for the `km2arec/` package (tests are excluded from strict mode per `pyproject.toml`).
- **No module-level I/O or side effects.** Importing `km2arec` must not open files, print, or allocate large arrays.
