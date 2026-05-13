"""Tests for km2arec.io: read_events, write_rec, read_rec."""

from __future__ import annotations

from pathlib import Path

import awkward as ak
import numpy as np
import pytest

from km2arec.io import REC_FIELDS, read_events, read_rec, write_rec

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_ROOT = Path(__file__).parent.parent / "data" / "km2a_simulation.root"


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

N_DUMMY = 5  # number of fake events used in round-trip tests


def _make_dummy_flat_rec(n: int = N_DUMMY) -> ak.Array:
    """Build a minimal flat record array with all canonical REC_FIELDS."""
    rng = np.random.default_rng(42)
    fields: dict[str, np.ndarray] = {}
    for field in REC_FIELDS:
        if field in (
            "ev_n",
            "id",
            "rec_Endf",
            "NhitE",
            "NhitM",
            "NfiltE",
            "NfiltM",
            "NtrigE",
            "NliveM1",
            "NliveM2",
            "NliveM3",
        ):
            fields[field] = rng.integers(0, 100, size=n, dtype=np.int32)
        else:
            fields[field] = rng.random(size=n).astype(np.float32)
    return ak.zip(fields)


@pytest.fixture(scope="module")
def sim_arrays() -> tuple[ak.Array, ak.Array, ak.Array]:
    """Read the sample simulation file once for the whole module."""
    return read_events(DATA_ROOT)


@pytest.fixture(scope="module")
def round_trip_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write a dummy flat_rec to a temp ROOT file; return the path."""
    out = tmp_path_factory.mktemp("io") / "rec_test.root"
    write_rec(out, _make_dummy_flat_rec())
    return out


# ---------------------------------------------------------------------------
# Group 1: read_events against the real simulation file
# ---------------------------------------------------------------------------


class TestReadEvents:
    def test_returns_three_arrays(self, sim_arrays: tuple) -> None:
        ed_hits, md_hits, truth = sim_arrays
        assert isinstance(ed_hits, ak.Array)
        assert isinstance(md_hits, ak.Array)
        assert isinstance(truth, ak.Array)

    def test_ed_hits_fields(self, sim_arrays: tuple) -> None:
        ed_hits, _, _ = sim_arrays
        assert {"id", "time", "pe", "np", "status"} <= set(ed_hits.fields)

    def test_md_hits_fields(self, sim_arrays: tuple) -> None:
        _, md_hits, _ = sim_arrays
        assert {"id", "time", "pe", "np", "status"} <= set(md_hits.fields)

    def test_truth_fields(self, sim_arrays: tuple) -> None:
        _, _, truth = sim_arrays
        assert {"energy", "id", "theta", "phi", "corex", "corey", "NpE", "NuM"} <= set(truth.fields)

    def test_ed_hits_are_ragged(self, sim_arrays: tuple) -> None:
        ed_hits, _, _ = sim_arrays
        # Each element is itself an array of hits, not a scalar
        assert isinstance(ed_hits["time"][0], ak.Array)

    def test_md_hits_are_ragged(self, sim_arrays: tuple) -> None:
        _, md_hits, _ = sim_arrays
        assert isinstance(md_hits["time"][0], ak.Array)

    def test_truth_is_flat(self, sim_arrays: tuple) -> None:
        _, _, truth = sim_arrays
        # truth["energy"] is a 1-D array (one value per event)
        assert truth["energy"].ndim == 1

    def test_truth_energy_positive(self, sim_arrays: tuple) -> None:
        _, _, truth = sim_arrays
        assert ak.all(truth["energy"] > 0)

    def test_event_count_consistent(self, sim_arrays: tuple) -> None:
        ed_hits, md_hits, truth = sim_arrays
        assert len(ed_hits) == len(md_hits) == len(truth)

    def test_ed_hit_count_matches_nhite(self, sim_arrays: tuple) -> None:
        """len(ed_hits["id"][i]) must equal the NhitE stored in the file."""
        import uproot

        ed_hits, _, _ = sim_arrays
        with uproot.open(DATA_ROOT) as f:
            nhit_e = f["event"].arrays(["NhitE"], library="ak")["NhitE"]
        for i in range(len(ed_hits)):
            assert len(ed_hits["id"][i]) == nhit_e[i]

    def test_ed_time_dtype_is_float(self, sim_arrays: tuple) -> None:
        ed_hits, _, _ = sim_arrays
        assert ak.type(ed_hits["time"]).content.content.primitive == "float64"  # type: ignore[attr-defined]

    def test_ed_id_dtype_is_int(self, sim_arrays: tuple) -> None:
        ed_hits, _, _ = sim_arrays
        assert "int" in str(ak.type(ed_hits["id"]))


# ---------------------------------------------------------------------------
# Group 2: write_rec / read_rec round-trip
# ---------------------------------------------------------------------------


class TestWriteRec:
    def test_creates_file(self, round_trip_path: Path) -> None:
        assert round_trip_path.exists()

    def test_rec_tree_present(self, round_trip_path: Path) -> None:
        import uproot

        with uproot.open(round_trip_path) as f:
            assert "Rec" in f

    def test_all_fields_written(self, round_trip_path: Path) -> None:
        import uproot

        with uproot.open(round_trip_path) as f:
            written = set(f["Rec"].keys())
        assert set(REC_FIELDS) <= written


class TestReadRec:
    @pytest.fixture(scope="class")
    def rec(self, round_trip_path: Path) -> ak.Array:
        return read_rec(round_trip_path)

    @pytest.fixture(scope="class")
    def original(self) -> ak.Array:
        return _make_dummy_flat_rec()

    def test_returns_ak_array(self, rec: ak.Array) -> None:
        assert isinstance(rec, ak.Array)

    def test_has_five_sub_records(self, rec: ak.Array) -> None:
        assert set(rec.fields) == {"simulation", "direction", "core", "nkg", "observables"}

    def test_simulation_sub_fields(self, rec: ak.Array) -> None:
        assert {"energy", "id", "theta", "phi", "corex", "corey"} <= set(rec["simulation"].fields)

    def test_direction_sub_fields(self, rec: ak.Array) -> None:
        assert {"theta", "phi", "a"} <= set(rec["direction"].fields)

    def test_core_sub_fields(self, rec: ak.Array) -> None:
        assert {"x", "y"} <= set(rec["core"].fields)

    def test_nkg_sub_fields(self, rec: ak.Array) -> None:
        assert {"size", "age", "chi", "ndf"} <= set(rec["nkg"].fields)

    def test_observables_sub_fields(self, rec: ak.Array) -> None:
        expected = {
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
            "NhitE",
            "NhitM",
            "NfiltE",
            "NfiltM",
            "NtrigE",
        }
        assert expected <= set(rec["observables"].fields)

    def test_round_trip_length(self, rec: ak.Array) -> None:
        assert len(rec) == N_DUMMY

    def test_round_trip_simulation_energy(self, rec: ak.Array, original: ak.Array) -> None:
        np.testing.assert_allclose(
            ak.to_numpy(rec.simulation.energy),
            ak.to_numpy(original["E"]),
            rtol=1e-5,
        )

    def test_round_trip_nkg_size(self, rec: ak.Array, original: ak.Array) -> None:
        np.testing.assert_allclose(
            ak.to_numpy(rec.nkg.size),
            ak.to_numpy(original["rec_Esize"]),
            rtol=1e-5,
        )

    def test_round_trip_core_x(self, rec: ak.Array, original: ak.Array) -> None:
        np.testing.assert_allclose(
            ak.to_numpy(rec.core.x),
            ak.to_numpy(original["rec_x"]),
            rtol=1e-5,
        )

    def test_round_trip_core_y(self, rec: ak.Array, original: ak.Array) -> None:
        np.testing.assert_allclose(
            ak.to_numpy(rec.core.y),
            ak.to_numpy(original["rec_y"]),
            rtol=1e-5,
        )

    def test_dotted_access_direction_theta(self, rec: ak.Array) -> None:
        _ = rec.direction.theta  # must not raise

    def test_dotted_access_observables_num1(self, rec: ak.Array) -> None:
        _ = rec.observables.NuM1  # must not raise

    def test_event_filter_works(self, rec: ak.Array) -> None:
        """Boolean masking on the top-level record must propagate to sub-records."""
        mask = rec.nkg.size > 0.5
        filtered = rec[mask]
        assert len(filtered) <= N_DUMMY
        # sub-record access still works after masking
        _ = filtered.core.x
