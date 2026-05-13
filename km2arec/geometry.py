"""Detector geometry loading for KM2A.

Coordinate convention
---------------------
Position files are stored in the **LHAASO frame**.  This module converts all
coordinates to the **CORSIKA frame** on load:

    x_corsika =  lhaaso_y   (3rd column in file)
    y_corsika = -lhaaso_x   (2nd column, negated)
    z_corsika =  z - zeroZ  (4th column minus the header reference altitude)

The full-array layout files bundled with the package (``ED_pos_all.txt``,
``MD_pos_all.txt``) correspond to ``Flag==7`` ("KM2A_all for MC") in the
original C++ geometry loader ``G4KM2A_Geometry.cc``.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import awkward as ak
import numpy as np

PathLike = str | Path

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_ED_POS: Path = _DATA_DIR / "ED_pos_all.txt"
_DEFAULT_MD_POS: Path = _DATA_DIR / "MD_pos_all.txt"


class GeometryArrays(NamedTuple):
    """Detector layout for ED and MD sub-arrays.

    This is a plain ``NamedTuple`` (not a dataclass) holding two ``ak.Array``
    objects.  Each sub-array has fields ``id`` (int32), ``x``, ``y``, ``z``
    (float64, metres) in the CORSIKA coordinate frame.

    Attributes
    ----------
    ed:
        Electromagnetic detector positions. Typically 5216 entries for the
        full KM2A array.
    md:
        Muon detector positions.  Typically 1188 entries for the full array.

    Examples
    --------
    >>> geo = load_geometry()
    >>> geo.ed.x          # CORSIKA x of all ED detectors (np.ndarray-like)
    >>> geo.md.id         # detector IDs of all MD detectors
    """

    ed: ak.Array
    md: ak.Array


def _parse_pos_file(path: Path) -> ak.Array:
    """Parse a KM2A position file and return an ``ak.Array`` in CORSIKA frame.

    Both ED and MD position files share the same data-row layout::

        id   lhaaso_x   lhaaso_y   z

    The header line is scanned for a ``zeroZ`` keyword to extract the
    reference altitude.  An optional ``Rotation`` keyword in the ED header
    is present but not used by this reader.

    Parameters
    ----------
    path:
        Path to a position file (``ED_pos_*.txt`` or ``MD_pos_*.txt``).

    Returns
    -------
    ak.Array with fields ``id``, ``x``, ``y``, ``z`` in CORSIKA frame.
    """
    ids: list[int] = []
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    zero_z = 0.0

    with open(path) as fh:
        header = fh.readline()
        tokens = header.split()
        for i, tok in enumerate(tokens):
            if tok == "zeroZ" and i + 1 < len(tokens):
                zero_z = float(tokens[i + 1])
                break

        for line in fh:
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                det_id = int(parts[0])
                lhaaso_x = float(parts[1])
                lhaaso_y = float(parts[2])
                z = float(parts[3])
            except ValueError:
                continue

            ids.append(det_id)
            xs.append(lhaaso_y)  # x_corsika =  lhaaso_y
            ys.append(-lhaaso_x)  # y_corsika = -lhaaso_x
            zs.append(z - zero_z)  # z_corsika =  z - zeroZ

    return ak.Array(
        {
            "id": np.array(ids, dtype=np.int32),
            "x": np.array(xs, dtype=np.float64),
            "y": np.array(ys, dtype=np.float64),
            "z": np.array(zs, dtype=np.float64),
        }
    )


def load_geometry(
    ed_pos_file: PathLike | None = None,
    md_pos_file: PathLike | None = None,
) -> GeometryArrays:
    """Load KM2A detector geometry.

    Parameters
    ----------
    ed_pos_file:
        Path to an ED position file.  When ``None`` (default) the bundled
        full-array layout ``ED_pos_all.txt`` is used (5216 detectors).
    md_pos_file:
        Path to an MD position file.  When ``None`` (default) the bundled
        full-array layout ``MD_pos_all.txt`` is used (1188 detectors).

    Returns
    -------
    GeometryArrays
        Named tuple with ``ed`` and ``md`` fields.  Each is an ``ak.Array``
        with fields ``id``, ``x``, ``y``, ``z`` in the CORSIKA frame.

    Examples
    --------
    Load the default full array (no arguments needed):

    >>> geo = load_geometry()
    >>> len(geo.ed)           # 5216
    >>> len(geo.md)           # 1188
    >>> geo.ed.x[0]           # CORSIKA x of the first ED detector
    >>> geo.md.id[0]          # detector ID of the first MD detector

    Override with a custom layout:

    >>> geo = load_geometry(ed_pos_file="my_layout/ED_pos_custom.txt")
    """
    ed_path = Path(ed_pos_file) if ed_pos_file is not None else _DEFAULT_ED_POS
    md_path = Path(md_pos_file) if md_pos_file is not None else _DEFAULT_MD_POS

    return GeometryArrays(
        ed=_parse_pos_file(ed_path),
        md=_parse_pos_file(md_path),
    )
