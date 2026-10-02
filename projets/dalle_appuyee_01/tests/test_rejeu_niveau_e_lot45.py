"""Lot 45 : rejeu de E0, E1, E2 sur le `.comm` actuel (EYS = 200 GPa)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aster_expert.projet.paquet import compare_comm

_ROOT = Path(__file__).resolve().parents[3]
_REF = _ROOT / "projets" / "dalle_appuyee_01" / "references"


def _replay() -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        (_REF / "rejeu_niveau_e_lot45.json").read_text(encoding="utf-8")
    )
    return loaded


def test_the_three_criteria_of_lot_43_pass_on_the_three_versioned_meshes() -> None:
    replay = _replay()
    verdicts = replay["verdicts"]
    assert isinstance(verdicts, dict)
    assert [verdicts[k]["verdict"] for k in ("E0", "E1", "E2")] == ["RÉUSSI"] * 3
    series = replay["series"]
    assert isinstance(series, list)
    assert [s["maillage"]["mesh_check"] for s in series] == ["48/48"] * 3
    assert all(s["execution"]["statut"] == "completed_ok" for s in series)
    assert replay["criteres"]["commit"] == "4093f126b4829bec8fc07a97c67beba010c80fce"  # type: ignore[index]


def test_the_replayed_comm_differs_from_lot_43_by_eys_and_a_comment_only() -> None:
    old = (_REF / "cas" / "dalle_h0p125.comm").read_text(encoding="utf-8")
    new = (_REF / "rejeu_lot45" / "dalle_h0p125.comm").read_text(encoding="utf-8")
    result = compare_comm(old, new)
    assert result["identique_hors_commentaires"] is False
    changed = [
        line for line in result["difference"] if not line.startswith(("-#", "+#"))
    ]
    assert sorted(set(changed)) == [
        "+            EYS=200000000000.0,",
        "-            EYS=210000000000.0,",
    ]
    assert len(changed) == 8


def test_the_fingerprints_recorded_by_the_replay_are_those_of_the_files() -> None:
    for entry in _replay()["series"]:  # type: ignore[attr-defined]
        comm = _ROOT / entry["comm"]["chemin"]
        assert hashlib.sha256(comm.read_bytes()).hexdigest() == entry["comm"]["sha256"]
        mesh = _ROOT / entry["maillage"]["versionne"]
        assert (
            hashlib.sha256(mesh.read_bytes()).hexdigest() == entry["maillage"]["sha256"]
        )


def test_the_results_of_the_replay_equal_those_of_lot_43_where_eys_cannot_act() -> None:
    old = json.loads((_REF / "niveau_e_lot43.json").read_text(encoding="utf-8"))
    new = json.loads((_REF / "rejeu_niveau_e_lot45.json").read_text(encoding="utf-8"))
    assert len(old["series"]) == len(new["series"]) == 3
    for before, after in zip(old["series"], new["series"], strict=True):
        for case in ("G", "Q"):
            assert before["cas"][case]["DZ"] == after["cas"][case]["DZ"]
            assert before["cas"][case]["MXX"] == after["cas"][case]["MXX"]
    verdicts_old = {k: v["verdict"] for k, v in old["verdicts"].items()}
    verdicts_new = {k: v["verdict"] for k, v in new["verdicts"].items()}
    assert verdicts_old == verdicts_new
