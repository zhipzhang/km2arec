"""Tests for km2arec.geometry: load_geometry, _parse_pos_file."""

from __future__ import annotations

from pathlib import Path

import awkward as ak
import numpy as np
import pytest

from km2arec.geometry import GeometryArrays, load_geometry

# ---------------------------------------------------------------------------
# Reference values derived from the first data rows of each bundled file
# (LHAASO frame → CORSIKA frame conversion applied manually)
#
# ED_pos_all.txt header: Rotation 0 deg zeroZ 4400
#   row: id=1  lhaaso_x=-154.294  lhaaso_y=296.766  z=4394.831
#   → x_corsika= 296.766,  y_corsika= 154.294,  z_corsika= -5.169
#
# MD_pos_all.txt header: zeroZ 4400
#   row: id=30  lhaaso_x=-526.20  lhaaso_y=-198.43  z=4393.00
#   → x_corsika= -198.43,  y_corsika= 526.20,  z_corsika= -7.00
# ---------------------------------------------------------------------------

_ED_FULL_COUNT = 5216
_MD_FULL_COUNT = 1188

_ED_REF_ID = 1
_ED_REF_X = 296.766
_ED_REF_Y = 154.294
_ED_REF_Z = -5.169

_MD_REF_ID = 30
_MD_REF_X = -198.43
_MD_REF_Y = 526.20
_MD_REF_Z = -7.00


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def geo() -> GeometryArrays:
    """Default full-array geometry, loaded once per module."""
    return load_geometry()


# ---------------------------------------------------------------------------
# Group 1: default (no-argument) load
# ---------------------------------------------------------------------------


class TestDefaultLoad:
    def test_returns_geometry_arrays(self, geo: GeometryArrays) -> None:
        assert isinstance(geo, GeometryArrays)

    def test_ed_is_ak_array(self, geo: GeometryArrays) -> None:
        assert isinstance(geo.ed, ak.Array)

    def test_md_is_ak_array(self, geo: GeometryArrays) -> None:
        assert isinstance(geo.md, ak.Array)

    def test_ed_count(self, geo: GeometryArrays) -> None:
        assert len(geo.ed) == _ED_FULL_COUNT

    def test_md_count(self, geo: GeometryArrays) -> None:
        assert len(geo.md) == _MD_FULL_COUNT

    def test_ed_fields(self, geo: GeometryArrays) -> None:
        assert {"id", "x", "y", "z"} <= set(geo.ed.fields)

    def test_md_fields(self, geo: GeometryArrays) -> None:
        assert {"id", "x", "y", "z"} <= set(geo.md.fields)

    def test_ed_id_dtype(self, geo: GeometryArrays) -> None:
        assert "int" in str(ak.type(geo.ed.id))

    def test_ed_x_dtype(self, geo: GeometryArrays) -> None:
        assert "float" in str(ak.type(geo.ed.x))


# ---------------------------------------------------------------------------
# Group 2: LHAASO → CORSIKA coordinate transformation
# ---------------------------------------------------------------------------


class TestCoordinateTransform:
    def _ed_idx(self, geo: GeometryArrays, det_id: int) -> int:
        ids = ak.to_numpy(geo.ed.id)
        matches = np.where(ids == det_id)[0]
        assert len(matches) == 1, f"ED id={det_id} not found"
        return int(matches[0])

    def _md_idx(self, geo: GeometryArrays, det_id: int) -> int:
        ids = ak.to_numpy(geo.md.id)
        matches = np.where(ids == det_id)[0]
        assert len(matches) == 1, f"MD id={det_id} not found"
        return int(matches[0])

    def test_ed_x_corsika(self, geo: GeometryArrays) -> None:
        idx = self._ed_idx(geo, _ED_REF_ID)
        np.testing.assert_allclose(geo.ed.x[idx], _ED_REF_X, rtol=1e-5)

    def test_ed_y_corsika(self, geo: GeometryArrays) -> None:
        idx = self._ed_idx(geo, _ED_REF_ID)
        np.testing.assert_allclose(geo.ed.y[idx], _ED_REF_Y, rtol=1e-5)

    def test_ed_z_corsika(self, geo: GeometryArrays) -> None:
        idx = self._ed_idx(geo, _ED_REF_ID)
        np.testing.assert_allclose(geo.ed.z[idx], _ED_REF_Z, atol=1e-3)

    def test_md_x_corsika(self, geo: GeometryArrays) -> None:
        idx = self._md_idx(geo, _MD_REF_ID)
        np.testing.assert_allclose(geo.md.x[idx], _MD_REF_X, rtol=1e-4)

    def test_md_y_corsika(self, geo: GeometryArrays) -> None:
        idx = self._md_idx(geo, _MD_REF_ID)
        np.testing.assert_allclose(geo.md.y[idx], _MD_REF_Y, rtol=1e-4)

    def test_md_z_corsika(self, geo: GeometryArrays) -> None:
        idx = self._md_idx(geo, _MD_REF_ID)
        np.testing.assert_allclose(geo.md.z[idx], _MD_REF_Z, atol=1e-3)

    def test_ed_ids_are_unique(self, geo: GeometryArrays) -> None:
        ids = ak.to_numpy(geo.ed.id)
        assert len(ids) == len(np.unique(ids))

    def test_md_ids_are_unique(self, geo: GeometryArrays) -> None:
        ids = ak.to_numpy(geo.md.id)
        assert len(ids) == len(np.unique(ids))


# ---------------------------------------------------------------------------
# Group 3: external file override
# ---------------------------------------------------------------------------


class TestExternalFile:
    def test_ed_override(self, geo: GeometryArrays, tmp_path: Path) -> None:
        """Passing an external ED file replaces the default geometry."""
        # Write a minimal two-detector layout
        layout = tmp_path / "ED_test.txt"
        layout.write_text("Rotation 0 deg zeroZ 4400\n10  0.0  100.0  4400.0\n20  50.0  200.0  4410.0\n")
        custom = load_geometry(ed_pos_file=layout, md_pos_file=None)
        assert len(custom.ed) == 2
        # id=10: lhaaso_x=0, lhaaso_y=100 → x_corsika=100, y_corsika=0, z=0
        np.testing.assert_allclose(custom.ed.x[0], 100.0)
        np.testing.assert_allclose(custom.ed.y[0], 0.0)
        np.testing.assert_allclose(custom.ed.z[0], 0.0)
        # MD should still be the full default
        assert len(custom.md) == _MD_FULL_COUNT

    def test_md_override(self, tmp_path: Path) -> None:
        """Passing an external MD file replaces only the MD geometry."""
        layout = tmp_path / "MD_test.txt"
        layout.write_text("zeroZ 4400\n100  -200.0  300.0  4395.0\n")
        custom = load_geometry(md_pos_file=layout)
        assert len(custom.md) == 1
        # lhaaso_x=-200, lhaaso_y=300 → x_corsika=300, y_corsika=200, z=-5
        np.testing.assert_allclose(custom.md.x[0], 300.0)
        np.testing.assert_allclose(custom.md.y[0], 200.0)
        np.testing.assert_allclose(custom.md.z[0], -5.0)
        # ED should still be the full default
        assert len(custom.ed) == _ED_FULL_COUNT

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_geometry(ed_pos_file=tmp_path / "nonexistent.txt")
