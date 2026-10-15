# ruff: noqa: E501
"""`charges.med` tel que Code_Aster l'a écrit et script Salomé-Méca (lot 50 quinquies).

Sans Docker ni Salomé : le gabarit, le titre, le dépôt et l'enchaînement se vérifient sur
un faux `Deliverables` ; l'exécution réelle dans l'image Salomé-Méca est un test lent."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from aster_expert.livrables import chaine, charges_salome, charges_verif
from aster_expert.livrables.charges_salome import (
    MECHANICAL,
    THERMAL,
    deposit,
    read_cases,
    set_med_path,
    write_script,
)
from aster_expert.projet.errors import ProjectError

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = ["DX", "DY", "DZ", "DRX", "DRY", "DRZ"]


class _Livrables:
    """Le plan de post-traitement et les champs de charges d'un modèle de quatre nœuds."""

    def __init__(self) -> None:
        self.mesh = SimpleNamespace(coords=np.zeros((4, 3)))
        self.plan = {
            "charges": [
                {"cas": "Q", "nature": "forces", "nom_med": "FN_Q"},
                {"cas": "TP", "nature": "forces_varc", "nom_med": "FV_TP"},
                {"cas": "TP", "nature": "temperature", "nom_med": "VARC_TP_TEMP_1"},
            ]
        }
        self.fields = {
            "FN_Q": np.array([[0, 0, -1500.0, 0, 0, 0]] * 3 + [[0.0] * 6]),
            "FV_TP": np.array(
                [[1000.0, 0, 0, 0, 0, 0], [-1000.0, 0, 0, 0, 0, 0]] + [[0.0] * 6] * 2
            ),
        }

    def loads(self) -> Iterator[tuple[str, Any, Any, Any, list[str]]]:
        for name, full in self.fields.items():
            n = len(full)
            yield (
                name,
                full.reshape(-1),
                np.zeros(n, dtype=np.int64),
                np.arange(n, dtype=np.int64),
                COMPONENTS,
            )
        yield (
            "VARC_TP_TEMP_1",
            np.array([46.0, 46.0]),
            np.zeros(2, dtype=np.int64),
            np.arange(2, dtype=np.int64),
            [],
        )


def _ctx() -> Any:
    return SimpleNamespace(repo_root=ROOT, declaration=SimpleNamespace(name="essai"))


def test_les_cas_viennent_du_plan_et_le_titre_donne_la_resultante() -> None:
    cases = read_cases(_ctx(), _Livrables())  # type: ignore[arg-type]
    assert [(c["nom"], c["nature"]) for c in cases] == [
        ("Q", MECHANICAL),
        ("TP", THERMAL),
    ]
    q, tp = cases
    assert q["forces"] == "FN_Q" and q["temperature"] is None
    assert tp["forces"] == "FV_TP" and tp["temperature"] == "VARC_TP_TEMP_1"
    assert (
        q["titre"]
        == "Q - charge mécanique - ΣFX = 0,0 kN ; ΣFY = 0,0 kN ; ΣFZ = -4,5 kN"
    )
    assert q["resultante_n"] == [0.0, 0.0, -4500.0]
    assert tp["resultante_n"] == [0.0, 0.0, 0.0] and "TEMP = 46,0" in tp["titre"]


def test_un_cas_sans_champ_de_forces_est_refuse() -> None:
    d = _Livrables()
    d.plan["charges"] = [
        {"cas": "T", "nature": "temperature", "nom_med": "VARC_T_TEMP_1"}
    ]
    with pytest.raises(ProjectError, match="aucun champ de forces"):
        read_cases(_ctx(), d)  # type: ignore[arg-type]


def test_le_script_est_court_sans_manifeste_ni_fichier_voisin(tmp_path: Path) -> None:
    cases = read_cases(_ctx(), _Livrables())  # type: ignore[arg-type]
    med = tmp_path / "charges.med"
    path = write_script(cases, med, tmp_path)
    text = path.read_text(encoding="utf-8")
    compile(text, str(path), "exec")
    assert f"FICHIER_MED = {str(med)!r}" in text
    for parameter in (
        "FICHIER_MED",
        "CAS_AFFICHE",
        "FACTEUR_ECHELLE",
        "SOUS_ECHANTILLONNAGE",
    ):
        assert f"\n{parameter} = " in text
    assert "FACTEUR_ECHELLE = None" in text and 'CAS_AFFICHE = "Q"' in text
    # exec() dans la console ParaVis : ni __file__, ni fichier voisin, ni manifeste.
    for banned in ("__file__", "manifeste", "MANIFESTE", ".vtu", "json"):
        assert banned not in text
    assert "renseigner FICHIER_MED en tête du script" in text
    assert "def afficher_cas(" in text and '"Cas " + nom' in text
    assert len(text.splitlines()) < 220
    assert max(len(line) for line in text.splitlines()) < 400


def test_le_script_s_arrete_avant_de_creer_quoi_que_ce_soit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fichier introuvable : message demandé, et aucun appel à `paraview.simple`."""
    import sys
    import types

    cases = read_cases(_ctx(), _Livrables())  # type: ignore[arg-type]
    path = write_script(cases, tmp_path / "absent.med", tmp_path)
    created: list[str] = []
    fake = types.ModuleType("paraview.simple")

    def spy(name: str) -> Any:
        def call(*_a: object, **_k: object) -> None:
            created.append(name)

        return call

    for name in ("MEDReader", "GetActiveViewOrCreate", "Show", "Text", "MergeBlocks"):
        setattr(fake, name, spy(name))
    monkeypatch.setitem(sys.modules, "paraview", types.ModuleType("paraview"))
    monkeypatch.setitem(sys.modules, "paraview.simple", fake)
    with pytest.raises(
        FileNotFoundError, match="renseigner FICHIER_MED en tête du script"
    ):
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), {})  # noqa: S102
    assert created == []


def test_set_med_path_ne_change_que_la_ligne_du_fichier(tmp_path: Path) -> None:
    cases = read_cases(_ctx(), _Livrables())  # type: ignore[arg-type]
    path = write_script(cases, tmp_path / "a.med", tmp_path)
    before = path.read_text(encoding="utf-8").splitlines()
    set_med_path(path, Path("/media/sf_partage/echanges/x/charges.med"))
    after = path.read_text(encoding="utf-8").splitlines()
    changed = [i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b]
    assert len(before) == len(after) and len(changed) == 1
    assert (
        after[changed[0]] == "FICHIER_MED = '/media/sf_partage/echanges/x/charges.med'"
    )


def test_depot_med_identique_script_aux_chemins_du_depot_et_lisezmoi(
    tmp_path: Path,
) -> None:
    source = tmp_path / "res" / "livrables" / "charges_salome"
    (source / "png").mkdir(parents=True)
    (source / "png" / "Q_iso.png").write_bytes(b"png")
    (source / "png" / "charges_salome_direct.log").write_text(
        "journal", encoding="utf-8"
    )
    (source / "charges.med").write_bytes(b"med")
    cases = read_cases(_ctx(), _Livrables())  # type: ignore[arg-type]
    write_script(cases, source / "charges.med", source)
    (source / "cas.json").write_text(json.dumps(cases), encoding="utf-8")
    ctx: Any = SimpleNamespace(
        results_dir=tmp_path / "res", declaration=SimpleNamespace(name="essai")
    )
    dest = tmp_path / "echanges" / "essai"
    names = deposit(ctx, dest, menu="MENU", version="V")
    assert set(names) == {
        "charges.med",
        "charges_salome.py",
        "png/Q_iso.png",
        "LISEZMOI.txt",
    }
    assert (dest / "charges.med").read_bytes() == b"med"
    assert f"FICHIER_MED = {str(dest / 'charges.med')!r}" in (
        dest / "charges_salome.py"
    ).read_text(encoding="utf-8")
    assert len((dest / "LISEZMOI.txt").read_text(encoding="utf-8").splitlines()) <= 5
    lines = (dest / "empreintes.sha256").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(names)
    digest = hashlib.sha256(b"med").hexdigest()
    assert f"{digest}  charges.med" in lines
    with pytest.raises(ProjectError, match="livrables absents"):
        deposit(
            SimpleNamespace(results_dir=tmp_path / "vide"),  # type: ignore[arg-type]
            dest,
            menu="",
            version="",
        )


def test_charges_avance_n_est_pas_dans_la_chaine_par_defaut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "charges_avance" not in chaine.SUBSTEPS
    assert chaine.OPTIONAL_SUBSTEPS == ("charges_avance",)
    calls: list[str] = []

    def fake(name: str) -> Any:
        def step(*_a: object, **_k: object) -> list[str]:
            calls.append(name)
            return []

        return step

    monkeypatch.setattr(charges_verif, "step_charges", fake("med"))
    monkeypatch.setattr(charges_verif, "step_charges_avance", fake("avance"))
    for name in ("preparer", "executer", "verifier", "traiter"):
        monkeypatch.setattr(chaine, f"step_{name}", lambda *_a, **_k: [])
    from aster_expert.livrables import ingenieur, paraview, vues

    monkeypatch.setattr(vues, "step_vues", lambda *_a, **_k: [])
    monkeypatch.setattr(ingenieur, "step_ingenieur", lambda *_a, **_k: [])
    monkeypatch.setattr(paraview, "step_images", lambda *_a, **_k: [])
    chaine.run_deliverables(SimpleNamespace(), None)  # type: ignore[arg-type]
    assert calls == ["med"]
    chaine.run_deliverables(SimpleNamespace(), None, only="charges_avance")  # type: ignore[arg-type]
    assert calls == ["med", "avance"]


def test_la_sous_etape_refuse_sans_traitement_prealable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        charges_salome,
        "load_deliverables_state",
        lambda _c: SimpleNamespace(outputs={}),
    )
    monkeypatch.setattr(charges_salome, "deliverables_dir", lambda _c: tmp_path)
    with pytest.raises(ProjectError, match="étape traiter d'abord"):
        charges_salome.step_charges_med(SimpleNamespace())  # type: ignore[arg-type]
