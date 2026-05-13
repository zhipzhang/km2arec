# Roadmap

Each phase is a small, self-contained unit of work that leaves the repository in a working, tested state. Phases build on each other but each one has clear entry and exit criteria.

## Pipeline overview

```
ROOT file (event tree)
        │
        ▼
   io.py: uproot reader
        │
        ├──── geometry.py ─────┐
        ├──── calibration.py ──┤
        │                      ▼
        └──────────────► trigger.py
                              │
                              ▼
                      filters.py (spacetimefilter)
                              │
                              ▼
                      direction.py (planarfit)
                              │
                              ▼
                        core.py (core_centre2)
                              │
                              ▼
                      direction.py (conicalfit)
                              │
                              ▼
                       core.py (noisefilter)
                              │
                              ▼
                    core.py (NKG likelihood)          MD hits (from io.py)
                              │                                  │
                              └──────────────┬───────────────────┘
                                             ▼
                                      observables.py
                               (ED particle counts by ring,
                                muon counts by ring from MD,
                                R_edge, live MD counts)
                              │
                              ▼
                    io.py: uproot writer
                              │
                              ▼
                   ROOT file (Rec tree)
```

---

## Phase 0 — Project hygiene

**Goal:** The packaging metadata is accurate and the `specs/` constitution is committed.

- Update `pyproject.toml`: set `requires-python = ">=3.14"` and add runtime dependencies (`uproot`, `awkward-array`, `numpy`, `scipy`, `pandas`).
- Add `km2arec/py.typed` marker (referenced in `pyproject.toml` but missing).
- Commit `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` (this file).

**Exit criteria:** `pip install -e .` succeeds; `pytest tests/` passes the placeholder test.

---

## Phase 1 — Data model & I/O

**Goal:** Read raw simulation data and define the output schema using `ak.zip`. No reconstruction yet.

### Input data model (`km2arec/io.py`)

Reading from the `event` tree produces three `ak.zip` records. Field names map directly to the ROOT branches in `LHEvent`/`LHHit`.

**ED hits** (ragged — variable number per event):
```python
ed_hits = ak.zip({
    "id":     data["HitsE.id"],
    "time":   data["HitsE.time"],    # ns
    "pe":     data["HitsE.pe"],      # photoelectrons
    "np":     data["HitsE.np"],      # number of secondary particles (MC)
    "status": data["HitsE.status"],  # 5=good, 2/1/0=noise levels, -1=bad detector
})
```

**MD hits** (ragged):
```python
md_hits = ak.zip({
    "id":     data["HitsM.id"],
    "time":   data["HitsM.time"],
    "pe":     data["HitsM.pe"],
    "np":     data["HitsM.np"],
    "status": data["HitsM.status"],
})
```

**Simulation truth** (flat — one value per event, MC only):
```python
truth = ak.zip({
    "energy": data["E"],      # TeV
    "id":     data["Id"],     # particle type (PDG-like)
    "theta":  data["Theta"],  # rad
    "phi":    data["Phi"],    # rad
    "corex":  data["Corex"],  # m
    "corey":  data["Corey"],  # m
    "NpE":    data["NpE"],    # true number of e/γ reaching ED
    "NuM":    data["NuM"],    # true number of muons reaching MD
})
```

### Output data model — two representations

The output lives in two forms that are kept in sync by `km2arec/io.py`:

**On disk (ROOT TTree):** a flat `ak.zip` whose branch names mirror `LHRecEvent`. This is what `uproot` writes and what `ROOT::RDataFrame` reads without any conversion.

```python
# flat form — written to / read from ROOT
flat_rec = ak.zip({
    "ev_n":     ...,
    # truth
    "id":       ...,  "E":        ...,
    "theta":    ...,  "phi":      ...,  "corex":    ...,  "corey": ...,
    # direction
    "rec_theta": ..., "rec_phi":  ...,
    "rec_x":    ...,  "rec_y":    ...,  "rec_a":    ...,
    # NKG
    "rec_Esize": ..., "rec_Eage": ...,  "rec_Echi": ...,  "rec_Endf": ...,
    # counts
    "NhitE":    ...,  "NhitM":    ...,  "NfiltE":   ...,  "NfiltM":  ...,  "NtrigE": ...,
    # observables
    "Redge":    ...,
    "NpE1":     ...,  "NpE2":     ...,  "NpE3":     ...,
    "NuM1":     ...,  "NuM2":     ...,  "NuM3":     ...,  "NuM4":    ...,  "NuM5": ...,
    "NliveM1":  ...,  "NliveM2":  ...,  "NliveM3":  ...,
})
```

**In Python (structured view):** when loading a `Rec` file, `read_rec()` re-zips the flat branches into a nested record with four named sub-records. Awkward-array records support dotted attribute access natively — no wrapper class needed.

```python
rec = ak.zip({
    "simulation": ak.zip({
        "energy": flat["E"],      # TeV
        "id":     flat["id"],
        "theta":  flat["theta"],  # rad
        "phi":    flat["phi"],
        "corex":  flat["corex"],  # m
        "corey":  flat["corey"],
    }),
    "direction": ak.zip({
        "theta": flat["rec_theta"],  # rad
        "phi":   flat["rec_phi"],    # rad
        "a":     flat["rec_a"],      # conical curvature parameter (ns/m)
    }),
    "core": ak.zip({
        "x": flat["rec_x"],  # m
        "y": flat["rec_y"],  # m
    }),
    "nkg": ak.zip({
        "size": flat["rec_Esize"],
        "age":  flat["rec_Eage"],
        "chi":  flat["rec_Echi"],
        "ndf":  flat["rec_Endf"],
    }),
    "observables": ak.zip({
        "Redge":   flat["Redge"],
        "NpE1":    flat["NpE1"],   "NpE2":   flat["NpE2"],   "NpE3":   flat["NpE3"],
        "NuM1":    flat["NuM1"],   "NuM2":   flat["NuM2"],
        "NuM3":    flat["NuM3"],   "NuM4":   flat["NuM4"],   "NuM5":   flat["NuM5"],
        "NliveM1": flat["NliveM1"],"NliveM2":flat["NliveM2"],"NliveM3":flat["NliveM3"],
        "NhitE":   flat["NhitE"],  "NhitM":  flat["NhitM"],
        "NfiltE":  flat["NfiltE"], "NfiltM": flat["NfiltM"],
        "NtrigE":  flat["NtrigE"],
    }),
})

# dotted access just works:
rec.simulation.energy   # true primary energy
rec.simulation.corex    # true shower core x (m)
rec.direction.theta     # reconstructed zenith angle (rad)
rec.core.x              # reconstructed shower core x (m)
rec.nkg.size            # shower size from NKG fit
rec.observables.NuM1    # muon count in innermost ring
```

The flat ↔ structured conversion is the only logic in `read_rec` / `write_rec`; no custom class is needed.

Files:
- `km2arec/io.py`:
  - `read_events(path) -> ak.Array` — returns a single record with three sub-records: `ed_hits`, `md_hits`, `simulation`; uses `depth_limit=1` to merge at the event level without broadcasting into ragged hit arrays
  - `write_rec(path, flat_rec)` — writes the flat `ak.zip` as TTree `Rec`
  - `read_rec(path) -> ak.Array` — reads TTree `Rec` and returns the structured nested record

Tests:
- `tests/test_io.py`: open `data/km2a_simulation.root`, check shapes and field names of all three input records; round-trip write/read of a dummy output `ak.zip` to verify TTree compatibility.

**Exit criteria:** Can read the sample ROOT file and access e.g. `ed_hits["time"][0]` (first event's ED hit times) and `truth["energy"]`.

---

## Phase 2 — Geometry

**Goal:** Load detector layout; expose position lookup and a hit-masking helper that filters out hits from detectors absent in the loaded geometry.

> **Calibration / detector status** is deferred to a later phase. The details of the status file format and bad-detector masking are not yet fully understood and will be specified once clarified.

### Geometry design rationale

KM2A is now fully built. The canonical full-array layout files (`ED_pos_all.txt`, `MD_pos_all.txt`) — corresponding to `Flag==7` ("KM2A_all for MC") in the C++ code — are bundled as package data under `km2arec/data/`. By default `load_geometry()` uses these bundled files, so no arguments are needed for the common case. External files can be supplied to support special studies (sub-array analyses, future upgrades, custom MC layouts).

The C++ `arrayflag` integer (which selected one of many partial-build layout files) is **not** part of this Python interface. If sub-array geometry files are ever needed they can simply be passed as explicit paths.

### File format

Both position files share the same structure (verified from `G4KM2A_Geometry.cc`):

- **First line (header):**
  - ED files: `Rotation <deg> deg zeroZ <zeroZ_m>` — rotation angle (unused by the reader) and reference altitude.
  - MD files: `zeroZ <zeroZ_m>` — only the reference altitude.
- **Data rows:** `id  lhaaso_x  lhaaso_y  z` — all coordinates are in the **LHAASO frame**. The transformation to CORSIKA frame is:
  ```
  x_corsika =  lhaaso_y   (3rd column)
  y_corsika = -lhaaso_x   (2nd column, negated)
  z_corsika =  z - zeroZ  (4th column minus header value)
  ```
  `load_geometry` applies this transformation so all returned coordinates are already in the CORSIKA frame.

### In-memory representation

`load_geometry()` returns a `GeometryArrays` — a plain `NamedTuple` (not a dataclass, no methods) with two fields `ed` and `md`, each an `ak.Array` with fields `id`, `x`, `y`, `z`. Because ED (5216 entries) and MD (1188 entries) have different lengths they cannot share a single outer `ak.Array`, but the `NamedTuple` wrapper gives identical dotted-access ergonomics:

```python
geo = load_geometry()
geo.ed.x   # ak.Array of CORSIKA x positions of all ED detectors
geo.md.id  # ak.Array of detector IDs of all MD detectors
```

### Hit masking by geometry presence

When the loaded geometry is a sub-array (partial layout), or when hits reference non-instrumented IDs, those hits must be excluded from reconstruction.

#### Design principle: inputs stay pristine

In the data-driven design, simulation events are **read-only**. The geometry filter is a reconstruction decision, not a property of the event itself. The `status` field in the ROOT file is the simulator's (G4KM2A) assessment of hit quality; overwriting it with a reconstruction-time choice — even functionally, returning a new array — conflates two separate concerns:

- *Simulation quality* — was this hit physically real? (set by G4KM2A, encoded in `status`)
- *Geometry coverage* — is this detector in the loaded layout? (a reconstruction decision)

The correct pattern is to compose the geometry mask with the status predicate **at numpy-extraction time** inside the pipeline, without touching the event arrays:

```python
ed_lookup = build_id_lookup(geo.ed.id)   # built once at startup

# per event, inside the pipeline — original event arrays untouched:
hit_ids = ak.to_numpy(events.ed_hits.id[i])
status  = ak.to_numpy(events.ed_hits.status[i])
mask = active_hits(hit_ids, ed_lookup) & (status > 0)
# use hit_ids[mask], times[mask], pe[mask], ... for reconstruction
```

#### `mark_missing_hits` — opt-in annotation utility (not the pipeline path)

`mark_missing_hits` is provided for cases where a user explicitly wants to persist a geometry-annotated copy of a dataset (diagnostics, pre-filtering a large file before reconstruction). It is **not called by the pipeline**. Callers should be aware that the returned array's `status` field no longer faithfully reflects the simulation output alone.

#### Why not Numba JIT?

Numba is worthwhile when a computation cannot be expressed as vectorised NumPy. Here the core operation is a single fancy-index (`lookup[hit_ids]`), which already runs at C speed. The JIT compilation overhead (~1–2 s on first call) would dominate the actual work for typical hit multiplicities (≲ 1000 hits/event). Numba can be reconsidered if profiling later identifies this as a real bottleneck.

Files:
- `km2arec/geometry.py`:
  - `load_geometry(ed_pos_file=None, md_pos_file=None) -> GeometryArrays`
    - If `ed_pos_file` / `md_pos_file` are `None`, uses the bundled `km2arec/data/ED_pos_all.txt` and `km2arec/data/MD_pos_all.txt` (5216 ED + 1188 MD, full KM2A array).
    - Accepts `str | Path` for either argument to override with an external file.
    - Returns coordinates in CORSIKA frame.
  - `build_id_lookup(ids: ak.Array) -> np.ndarray`
    - Accepts the `id` field of either `geo.ed` or `geo.md`.
    - Returns a `np.ndarray[bool]` of length `max(ids) + 1`; index `i` is `True` iff detector `i` is present in the geometry.
  - `active_hits(hit_ids: np.ndarray, lookup: np.ndarray) -> np.ndarray`
    - **Pipeline-facing function.** Given a 1-D numpy array of hit IDs for one event and a lookup array, returns a boolean mask. IDs exceeding `len(lookup) - 1` are treated as absent. Compose with a status predicate to get the combined per-event selection mask.
  - `mark_missing_hits(hits: ak.Array, lookup: np.ndarray, absent_status: int = -2) -> ak.Array`
    - **Annotation utility only; not used by the pipeline.** Returns a new array with `status = absent_status` for geometry-absent hits across all events. Use for diagnostic or pre-filtering workflows where explicitly marking geometry-absent hits in persistent data is intentional.
- `km2arec/data/ED_pos_all.txt` — bundled full ED array layout (5216 detectors, `Flag==7`).
- `km2arec/data/MD_pos_all.txt` — bundled full MD array layout (1188 detectors).

Tests:
- `tests/test_geometry.py`:
  - Default (no args) loads 5216 ED detectors and 1188 MD detectors.
  - Known detector IDs map to expected (x, y, z) coordinates in CORSIKA frame.
  - External file path override works for both ED and MD independently.
  - `build_id_lookup`: correct length, correct True/False for known IDs.
  - `active_hits`: masks absent and out-of-range IDs; passes present IDs.
  - `mark_missing_hits`: present IDs keep original status; absent and out-of-range IDs get `status = -2`; custom `absent_status` works; ragged structure is preserved.

**Exit criteria:** Can look up any detector's position by ID without ROOT; `load_geometry()` with no arguments returns a `GeometryArrays` with 5216 ED and 1188 MD detectors; `active_hits` is the pipeline-facing filter, composing with the status predicate at numpy-extraction time.

---

## Phase 3 — Trigger & spatial filter

**Goal:** Identify events with enough hits and locate the shower cluster.

Files:
- `km2arec/trigger.py` — `trigger(hit_times, n_min=5, window_ns=400.0) -> bool`
  - Sliding time window over sorted hit times; returns True if ≥ `n_min` ED hits fall within `window_ns`
- `km2arec/filters.py` — `spacetimefilter(x, y, t, ...) -> mask: np.ndarray`
  - Sliding spatial window over hits passing the trigger time window
  - Returns a boolean mask of hits selected as the primary shower cluster

Tests:
- `tests/test_trigger.py`: synthetic hit arrays that should pass/fail the 5-hit-in-400 ns criterion.
- `tests/test_filters.py`: a known spatial cluster is recovered from a noisy hit list.

**Exit criteria:** Trigger and filter functions pass unit tests; can apply them to a real event from the sample file.

---

## Phase 4 — Direction reconstruction

**Goal:** Estimate shower arrival direction from selected hits.

Files:
- `km2arec/direction.py`:
  - `planarfit(x, y, t, weights=None) -> (l, m, t0, theta, phi)`
    - Weighted least-squares: minimizes Σ w_i (t_i − (l·x_i + m·y_i + t0)/c)²
    - Iterative re-weighting with Gaussian σ_t kernel on residuals (mirrors C++ `planarfit`)
  - `conicalfit(x, y, t, x_core, y_core, weights=None) -> (l, m, t0, a, theta, phi)`
    - Adds radial delay term a·r_i where r_i = distance from (x_core, y_core)
    - a fixed at 0.035 ns/m in a first pass; optionally free

Tests:
- `tests/test_direction.py`: compare (θ, φ) against C++ reference output for several sample events (tolerance: < 0.01° for planar, < 0.001° for conical).

**Exit criteria:** planarfit and conicalfit produce results within tolerance of the C++ reference.

---

## Phase 5 — Core & NKG fit

**Goal:** Locate the shower core precisely and fit the lateral distribution.

Files:
- `km2arec/core.py`:
  - `core_centre2(x, y, charges) -> (x_core, y_core)`
    - Charge-weighted centroid; accepts an optional edge-detector weight
  - `nkg_profile(r, S, eta, R_M=130.0) -> rho`
    - NKG function: ρ(r) = S / (2π R_M²) · Γ(4.5−η) / [Γ(η−1.5) Γ(3)] · (r/R_M)^(η−2.5) · (1+r/R_M)^(η−4.5)
  - `nkg_nll(params, x, y, x_core, y_core, n_meas, areas) -> float`
    - Negative Poisson log-likelihood: −Σ (n_meas·ln(n_pred) − n_pred)
  - `core_likelihood(x, y, n_meas, areas, x0, y0) -> (x_core, y_core, S, eta)`
    - Minimizes `nkg_nll` via `scipy.optimize.minimize` (L-BFGS-B) with bounds
  - `noisefilter(x, y, t, l, m, t0, x_core, y_core, time_cut_ns, dist_cut_m) -> mask`
    - Removes hits whose time residual or core distance exceeds cuts

Tests:
- `tests/test_core.py`: NKG profile integral, centroid, noise filter unit tests; NKG likelihood fit tolerance vs C++ for sample events.

**Exit criteria:** Core position, Size, Age agree with C++ reference within tolerance (core < 1 m, Size < 5%, Age < 0.05).

---

## Phase 6 — Muon observables & physical quantities

**Goal:** Extract muon counts from MD hits and compute all auxiliary physics quantities needed for downstream gamma/hadron separation. The NKG fit is ED-only; MD is not fitted — only hit counts in radial rings are recorded.

Files:
- `km2arec/observables.py`:
  - `get_np(x, y, charges, x_core, y_core, r_min, r_max) -> float` — ED particle count in an annular ring around the reconstructed core
  - `get_mu_m(x_md, y_md, n_md, x_core, y_core, r_min, r_max) -> int` — muon hit count in an annular ring (raw MD counts, no fit)
  - `r_edge(x_core, y_core, array_boundary) -> float` — distance from core to array edge
  - `get_live_md(x_md, y_md, mask_md, x_core, y_core, r_min, r_max) -> int` — number of live (good) MD units in a ring

Note: The muon counts output here are the primary input for gamma/hadron separation analyses, which are out of scope for this reconstruction package. `km2arec` stops at providing the counts.

Tests:
- `tests/test_observables.py`: known geometry, check particle counts and edge distance.

**Exit criteria:** All auxiliary quantities match C++ reference for sample events.

---

## Phase 7 — Pipeline & CLI

**Goal:** Wire all stages into a single callable and expose a command-line interface.

Files:
- `km2arec/pipeline.py`:
  - `eventrecline(hits_ed, hits_md, geometry, **options) -> dict`
    - Calls trigger → spacetimefilter → planarfit → core_centre2 → conicalfit → noisefilter → core_likelihood (ED only) → observables (ED counts + raw MD muon counts)
    - Returns a flat dict of all reconstructed quantities (one event at a time)
    - `geometry` is the `ak.Array` returned by `load_geometry()`
  - `reconstruct_file(in_path, out_path, time_resolution=0.0, ed_pos_file=None, md_pos_file=None)`
    - Iterates over all events; accumulates per-event result dicts into a flat awkward array; calls `write_rec`
- `km2arec/__main__.py`:
  - CLI entry point via `python -m km2arec`
  - Required positional arguments: `outfile timecalibrationresolution in_file [in_file ...]`
  - Optional geometry overrides: `--ed-pos ED_POS_FILE` and `--md-pos MD_POS_FILE`; when omitted, the bundled full-array geometry is used automatically.

Tests:
- `tests/test_pipeline.py`: end-to-end run on `data/km2a_simulation.root`; output ROOT file is opened and reconstructed quantities are compared against the C++ golden reference (stored in `tests/reference/`).

**Exit criteria:** `python -m km2arec out.root 0.0 data/km2a_simulation.root` completes using the default full-array geometry and the output passes the regression test.

---

## Phase 8 — Validation & documentation

**Goal:** Establish ongoing numerical validation and complete the API reference docs.

- `notebooks/validation.ipynb` — distribution-level comparison of km2arec vs KM2AMCrec_V3 output on a larger sample: θ, φ, core residuals, Size, Age histograms side by side.
- Update `docs/source/overview.md` with architecture description and pipeline diagram.
- Generate API reference pages for all public modules via Sphinx autodoc.
- Update `README.md` with installation, quick-start example, and link to docs.

**Exit criteria:** Validation notebook shows agreement; `make docs` builds without errors; `make run-checks` passes.
