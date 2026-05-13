# Mission

## What is km2arec?

`km2arec` is a Python-native rewrite of the official LHAASO-KM2A air-shower reconstruction program `KM2AMCrec_V3`. It reads G4KM2A simulation output (ROOT format) and produces reconstructed extensive air shower (EAS) observables from the raw detector hit data.

## Why rewrite in Python?

The original C++ implementation (`KM2AMCrec_V3`) is correct and well-validated, but tightly coupled to ROOT and its class hierarchy. This rewrite pursues three goals:

1. **Eliminate the ROOT runtime dependency.** All file I/O goes through `uproot`, making the package installable with a standard `pip install` and usable in any Python environment.
2. **Enable array-oriented, data-driven processing.** Instead of looping over OOP event objects, we operate on columnar arrays of hits across events. This is a better fit for the scientific Python ecosystem and enables future vectorization and batching.
3. **Improve composability and hackability.** Reconstruction stages are plain functions over NumPy arrays. They can be tested individually, swapped out, or extended without touching an inheritance hierarchy.

## Physics goals

Each event in the input file is a cosmic-ray or gamma-ray air shower detected by the KM2A array. The output record for each event has four distinct sections:

### 1. Simulation truth (pass-through from G4KM2A input)

| Field | Description |
|---|---|
| Primary energy, particle type | True energy and species of the simulated primary |
| True direction (θ_true, φ_true) | Monte Carlo arrival direction |
| True core (x_true, y_true) | Monte Carlo shower core on the ground |

These fields are read directly from the `event` tree and copied into the output unchanged, enabling residual and resolution studies.

### 2. Reconstructed shower parameters

| Field | Description |
|---|---|
| θ (zenith angle), φ (azimuth) | Reconstructed arrival direction |
| x_core, y_core | Reconstructed shower core position |
| Energy | Reconstructed primary energy (derived from Size via a calibration relation) |

### 3. NKG fit outputs

| Field | Description |
|---|---|
| Size (S) | Total number of shower particles at ground level from the ED NKG likelihood fit |
| Age (η) | Lateral shower age parameter from the ED NKG likelihood fit |

These come exclusively from the ED (Electromagnetic Detector) NKG fit. MD hits are not used in the profile fit.

### 4. Detection observables

| Field | Description |
|---|---|
| N_mu (by ring) | Muon hit counts from the MD sub-array in radial rings around the reconstructed core; primary input for gamma/hadron separation |
| N_p (by ring) | ED particle counts in radial rings |
| R_edge | Distance from reconstructed core to the array boundary |
| N_live_MD | Number of live (good) MD units in the relevant radial range |

These are the same observables produced by `LHRecEvent` in the C++ code.

## Design principles

- **Data-driven, not object-driven.** An event is a dict or awkward array of arrays, not an instance of a class with methods. Reconstruction functions take arrays in and return arrays out.
- **Functional pipeline.** Each reconstruction stage (`trigger`, `spacetimefilter`, `planarfit`, `conicalfit`, `core_likelihood`, …) is a pure function. The pipeline module wires them together; no stage calls another internally.
- **No global state.** Geometry and calibration are loaded once and passed explicitly into functions; there are no module-level singletons.
- **Numerical parity with C++.** The algorithms must reproduce the C++ outputs to within floating-point tolerance on the same input data. Validation against `KM2AMCrec_V3` reference runs is part of the test suite.
- **Incremental deliverability.** Each phase of the roadmap produces a working, tested piece of the system. There is no big-bang integration step.
