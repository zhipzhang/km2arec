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

## Phase 2 — Geometry & calibration

**Goal:** Load detector layout and bad-detector masks; expose position lookup by detector ID.

Files:
- `km2arec/geometry.py` — `load_geometry(arrayflag, config_dir) -> GeometryTable`
  - Reads `ED_pos_*.txt` / `MD_pos_*.txt` from `config/`
  - Returns a dataclass with arrays `detector_id`, `x`, `y`, `z` for ED and MD separately
  - `arrayflag` selects which layout file to use (matching C++ `arrayflag` CLI argument)
- `km2arec/calibration.py` — `load_calibration(status_file) -> CalibrationMask`
  - Reads detector status text file
  - Returns a boolean mask array indexed by detector ID (True = good)

Tests:
- `tests/test_geometry.py`: known detector IDs map to expected (x, y, z) coordinates.
- `tests/test_calibration.py`: bad detectors in a sample status file are correctly masked.

**Exit criteria:** Can look up any detector's position and status by ID without ROOT.

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
  - `eventrecline(hits_ed, hits_md, geometry, calibration, **options) -> dict`
    - Calls trigger → spacetimefilter → planarfit → core_centre2 → conicalfit → noisefilter → core_likelihood (ED only) → observables (ED counts + raw MD muon counts)
    - Returns a flat dict of all reconstructed quantities (one event at a time)
  - `reconstruct_file(in_path, out_path, arrayflag, status_file, time_resolution=0.0)`
    - Iterates over all events; accumulates per-event result dicts into a flat awkward array; calls `write_rec`
- `km2arec/__main__.py`:
  - CLI entry point via `python -m km2arec`
  - Arguments mirror the C++ interface: `arrayflag outfile timecalibrationresolution maskdetector in_file [in_file ...]`

Tests:
- `tests/test_pipeline.py`: end-to-end run on `data/km2a_simulation.root`; output ROOT file is opened and reconstructed quantities are compared against the C++ golden reference (stored in `tests/reference/`).

**Exit criteria:** `python -m km2arec 6 out.root 0.0 config/status.txt data/km2a_simulation.root` completes and the output passes the regression test.

---

## Phase 8 — Validation & documentation

**Goal:** Establish ongoing numerical validation and complete the API reference docs.

- `notebooks/validation.ipynb` — distribution-level comparison of km2arec vs KM2AMCrec_V3 output on a larger sample: θ, φ, core residuals, Size, Age histograms side by side.
- Update `docs/source/overview.md` with architecture description and pipeline diagram.
- Generate API reference pages for all public modules via Sphinx autodoc.
- Update `README.md` with installation, quick-start example, and link to docs.

**Exit criteria:** Validation notebook shows agreement; `make docs` builds without errors; `make run-checks` passes.
