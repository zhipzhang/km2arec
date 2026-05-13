"""I/O functions for reading G4KM2A simulation files and writing reconstruction output.

Branch naming conventions
--------------------------
Input (`event` TTree, LHEvent/LHHit):
  Scalar MC truth : E, Id, Theta, Phi, Corex, Corey, NpE, NuM, ev_n, NhitE, NhitM, NtrigE
  Ragged ED hits  : HitsE.id, HitsE.time, HitsE.pe, HitsE.np, HitsE.status
  Ragged MD hits  : HitsM.id, HitsM.time, HitsM.pe, HitsM.np, HitsM.status

Output (`Rec` TTree, mirrors LHRecEvent):
  flat branch names — see write_rec docstring for the full list.
"""

from __future__ import annotations

from pathlib import Path

import awkward as ak
import uproot

PathLike = str | Path

# ---------------------------------------------------------------------------
# Branch lists — kept here so read_events and write_rec stay in sync
# ---------------------------------------------------------------------------

_ED_BRANCHES: list[str] = [
    "HitsE.id",
    "HitsE.time",
    "HitsE.pe",
    "HitsE.np",
    "HitsE.status",
]

_MD_BRANCHES: list[str] = [
    "HitsM.id",
    "HitsM.time",
    "HitsM.pe",
    "HitsM.np",
    "HitsM.status",
]

_TRUTH_BRANCHES: list[str] = [
    "E",
    "Id",
    "Theta",
    "Phi",
    "Corex",
    "Corey",
    "NpE",
    "NuM",
]

# Canonical flat output branch names (mirrors LHRecEvent)
REC_FIELDS: list[str] = [
    "ev_n",
    # MC truth pass-through
    "E",
    "id",
    "theta",
    "phi",
    "corex",
    "corey",
    # reconstructed direction
    "rec_theta",
    "rec_phi",
    "rec_a",
    # reconstructed core
    "rec_x",
    "rec_y",
    # NKG fit (ED only)
    "rec_Esize",
    "rec_Eage",
    "rec_Echi",
    "rec_Endf",
    # hit counts
    "NhitE",
    "NhitM",
    "NfiltE",
    "NfiltM",
    "NtrigE",
    # detection observables
    "Redge",
    "NpE1",
    "NpE2",
    "NpE3",
    "NuM1",
    "NuM2",
    "NuM3",
    "NuM4",
    "NuM5",
    "NliveM1",
    "NliveM2",
    "NliveM3",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_events(path: PathLike) -> tuple[ak.Array, ak.Array, ak.Array]:
    """Read the ``event`` TTree from a G4KM2A simulation ROOT file.

    Parameters
    ----------
    path:
        Path to a ROOT file produced by G4KM2A.  The file must contain a
        TTree named ``event`` with ``LHEvent``/``LHHit`` objects.

    Returns
    -------
    ed_hits:
        Ragged record array — one sub-array of hits per event.
        Fields: ``id`` (int), ``time`` (ns, float), ``pe`` (float),
        ``np`` (int), ``status`` (int, 5=good / -1=bad detector).
    md_hits:
        Same structure for Muon Detector hits.
    truth:
        Flat record array — one scalar per event (MC truth).
        Fields: ``energy`` (TeV), ``id``, ``theta`` (rad), ``phi`` (rad),
        ``corex`` (m), ``corey`` (m), ``NpE``, ``NuM``.
    """
    with uproot.open(path) as f:
        tree = f["event"]
        data = tree.arrays(
            _ED_BRANCHES + _MD_BRANCHES + _TRUTH_BRANCHES,
            library="ak",
        )

    ed_hits = ak.zip(
        {
            "id": data["HitsE.id"],
            "time": data["HitsE.time"],  # ns
            "pe": data["HitsE.pe"],  # photoelectrons
            "np": data["HitsE.np"],  # number of secondary particles (MC)
            "status": data["HitsE.status"],  # 5=good, 2/1/0=noise levels, -1=bad
        }
    )

    md_hits = ak.zip(
        {
            "id": data["HitsM.id"],
            "time": data["HitsM.time"],
            "pe": data["HitsM.pe"],
            "np": data["HitsM.np"],
            "status": data["HitsM.status"],
        }
    )

    truth = ak.zip(
        {
            "energy": data["E"],  # TeV
            "id": data["Id"],  # particle type (PDG-like code)
            "theta": data["Theta"],  # rad
            "phi": data["Phi"],  # rad
            "corex": data["Corex"],  # m
            "corey": data["Corey"],  # m
            "NpE": data["NpE"],  # true number of e/γ reaching ED
            "NuM": data["NuM"],  # true number of muons reaching MD
        }
    )

    return ed_hits, md_hits, truth


def write_rec(path: PathLike, flat_rec: ak.Array) -> None:
    """Write a flat reconstructed record array as TTree ``Rec`` in a ROOT file.

    The output TTree is compatible with ``ROOT::RDataFrame``.  Use
    :func:`read_rec` to load it back with structured dotted-access sub-records.

    Parameters
    ----------
    path:
        Destination ROOT file path.  An existing file is overwritten.
    flat_rec:
        A record ``ak.Array`` (one entry per event) with the canonical branch
        names defined in :data:`REC_FIELDS`:

        * ``ev_n`` — event number
        * MC truth: ``E``, ``id``, ``theta``, ``phi``, ``corex``, ``corey``
        * Reconstructed direction: ``rec_theta``, ``rec_phi``, ``rec_a``
        * Reconstructed core: ``rec_x``, ``rec_y``
        * NKG fit (ED): ``rec_Esize``, ``rec_Eage``, ``rec_Echi``, ``rec_Endf``
        * Hit counts: ``NhitE``, ``NhitM``, ``NfiltE``, ``NfiltM``, ``NtrigE``
        * Observables: ``Redge``, ``NpE1-3``, ``NuM1-5``, ``NliveM1-3``
    """
    with uproot.recreate(path) as f:
        f["Rec"] = {field: flat_rec[field] for field in flat_rec.fields}


def read_rec(path: PathLike) -> ak.Array:
    """Read the ``Rec`` TTree from a km2arec output ROOT file.

    Returns a nested record array with five named sub-records that support
    dotted attribute access (e.g. ``rec.nkg.size``, ``rec.core.x``).

    Parameters
    ----------
    path:
        Path to a ROOT file previously written by :func:`write_rec`.

    Returns
    -------
    ak.Array with sub-records:

    ``simulation``
        MC truth pass-through — ``energy``, ``id``, ``theta``, ``phi``,
        ``corex``, ``corey``.
    ``direction``
        Reconstructed arrival direction — ``theta`` (rad), ``phi`` (rad),
        ``a`` (conical curvature, ns/m).
    ``core``
        Reconstructed shower core on the ground — ``x`` (m), ``y`` (m).
    ``nkg``
        NKG fit outputs (ED only) — ``size``, ``age``, ``chi``, ``ndf``.
    ``observables``
        Detection quantities — ``Redge``, ``NpE1-3``, ``NuM1-5``,
        ``NliveM1-3``, ``NhitE``, ``NhitM``, ``NfiltE``, ``NfiltM``,
        ``NtrigE``.

    Examples
    --------
    >>> rec = read_rec("output.root")
    >>> rec.simulation.energy      # true primary energy (TeV)
    >>> rec.direction.theta        # reconstructed zenith angle (rad)
    >>> rec.core.x                 # reconstructed core x (m)
    >>> rec.nkg.size               # shower size from NKG fit
    >>> rec.observables.NuM1       # muon count in innermost ring
    """
    with uproot.open(path) as f:
        flat = f["Rec"].arrays(library="ak")

    return ak.zip(
        {
            "simulation": ak.zip(
                {
                    "energy": flat["E"],
                    "id": flat["id"],
                    "theta": flat["theta"],
                    "phi": flat["phi"],
                    "corex": flat["corex"],
                    "corey": flat["corey"],
                }
            ),
            "direction": ak.zip(
                {
                    "theta": flat["rec_theta"],
                    "phi": flat["rec_phi"],
                    "a": flat["rec_a"],
                }
            ),
            "core": ak.zip(
                {
                    "x": flat["rec_x"],
                    "y": flat["rec_y"],
                }
            ),
            "nkg": ak.zip(
                {
                    "size": flat["rec_Esize"],
                    "age": flat["rec_Eage"],
                    "chi": flat["rec_Echi"],
                    "ndf": flat["rec_Endf"],
                }
            ),
            "observables": ak.zip(
                {
                    "Redge": flat["Redge"],
                    "NpE1": flat["NpE1"],
                    "NpE2": flat["NpE2"],
                    "NpE3": flat["NpE3"],
                    "NuM1": flat["NuM1"],
                    "NuM2": flat["NuM2"],
                    "NuM3": flat["NuM3"],
                    "NuM4": flat["NuM4"],
                    "NuM5": flat["NuM5"],
                    "NliveM1": flat["NliveM1"],
                    "NliveM2": flat["NliveM2"],
                    "NliveM3": flat["NliveM3"],
                    "NhitE": flat["NhitE"],
                    "NhitM": flat["NhitM"],
                    "NfiltE": flat["NfiltE"],
                    "NfiltM": flat["NfiltM"],
                    "NtrigE": flat["NtrigE"],
                }
            ),
        }
    )
