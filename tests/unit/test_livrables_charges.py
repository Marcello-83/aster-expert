# ruff: noqa: E501
"""MED de vérification des charges, `.vtu`, script ParaView, résultantes (lot 50 quater).

Sans Docker ni Salomé : le conteneur n'écrit que le MED ; tout le reste (lecture du
`.comm`, champs, `.vtu`, script, résultantes) se vérifie sur un maillage factice de
deux barres et d'un nœud isolé."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from aster_expert.livrables import chaine, charges_verif
from aster_expert.livrables.charges_verif import (
    NODAL_COMPONENTS,
    CaseLoads,
    build_case,
    build_manifest,
    linear_cells,
    read_case_loads,
    resultants,
    write_resultants_csv,
    write_script,
    write_vtus,
)
from aster_expert.livrables.donnees import Mesh
from aster_expert.livrables.inventaire import build_inventory
from aster_expert.livrables.vtu import read_vtu
from aster_expert.parsing.comm_parser import parse_comm_source
from aster_expert.projet.errors import ProjectError

ROOT = Path(__file__).resolve().parents[2]

COMM = """
DEBUT()
MAIL = LIRE_MAILLAGE(FORMAT='MED')
CL = AFFE_CHAR_MECA(MODELE=MODELE, DDL_IMPO=_F(GROUP_NO='APPUI', DX=0.0, DY=0.0, DZ=0.0))
CH_G = AFFE_CHAR_MECA(MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))
CH_Q = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=(
    _F(GROUP_MA='BARRE_A', FZ=-1000.0),
    _F(GROUP_MA='BARRE_B', FZ=-500.0, FY=200.0),
))
CH_P = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_NODALE=_F(GROUP_NO='POINTE', FY=-8000.0))
CH_L = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_POUTRE=_F(GROUP_MA='BARRE_A', N=10.0))
CH_C = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_COQUE=_F(GROUP_MA='DALLE', PRES=1.0))
ELEM = MACRO_ELAS_MULT(
    MODELE=MODELE, CHAM_MATER=MATER, CARA_ELEM=CARA, CHAR_MECA_GLOBAL=CL,
    CAS_CHARGE=(
        _F(NOM_CAS='G', CHAR_MECA=CH_G),
        _F(NOM_CAS='Q', CHAR_MECA=CH_Q),
        _F(NOM_CAS='P', CHAR_MECA=CH_P),
        _F(NOM_CAS='L', CHAR_MECA=CH_L),
        _F(NOM_CAS='C', CHAR_MECA=CH_C),
        _F(NOM_CAS='MOB1', CHAR_MECA=CH_P),
    ),
)
T_T = CREA_CHAMP(OPERATION='AFFE', TYPE_CHAM='NOEU_TEMP_R', MAILLAGE=MAIL,
    AFFE=_F(GROUP_MA=('BARRE_A', 'BARRE_B'), NOM_CMP='TEMP', VALE=30.0))
M_T = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(TOUT='OUI', MATER=ACIER),
    AFFE_VARC=_F(GROUP_MA=('BARRE_A', 'BARRE_B'), NOM_VARC='TEMP', CHAM_GD=T_T, VALE_REF=10.0))
TEMP = MECA_STATIQUE(MODELE=MODELE, CHAM_MATER=M_T, CARA_ELEM=CARA, EXCIT=_F(CHARGE=CL))
FIN()
"""


def _inventory() -> tuple[Any, Any]:
    analysis = parse_comm_source(COMM, file_path="<essai>")
    return analysis, build_inventory(analysis)


def _mesh() -> Mesh:
    """Nœuds 0-1-2 le long de X (barres A = 0-1, 2 m, et B = 1-2, 3 m), nœud 3 isolé,
    nœud 4 et un quadrangle sans rapport."""
    coords = np.array(
        [[0, 0, 0], [2, 0, 0], [5, 0, 0], [5, 1, 0], [0, 1, 0]], dtype=float
    )
    return Mesh(
        {
            "coords": coords,
            "conn_-1": np.array([[0, 1], [1, 2]]),
            "type_-1": np.array([1, 1]),
            "conn_0": np.array([[0, 1, 3, 4]]),
            "type_0": np.array([4]),
            "gma_-1_BARRE_A": np.array([0]),
            "gma_-1_BARRE_B": np.array([1]),
            "gno_POINTE": np.array([3]),
            "gno_APPUI": np.array([0]),
        }
    )


class _Livrables:
    """Ce que `Deliverables` donne à `build_case` : le maillage et les champs de charges."""

    def __init__(self) -> None:
        self.mesh = _mesh()
        self.fields: dict[str, np.ndarray] = {}

    def loads(self) -> Iterator[tuple[str, Any, Any, Any, list[str]]]:
        for name, full in self.fields.items():
            n = len(full)
            yield (
                name,
                full.reshape(-1),
                np.zeros(n, dtype=np.int64),
                np.arange(n, dtype=np.int64),
                ["DX", "DY", "DZ", "DRX", "DRY", "DRZ"],
            )


def _nodal(fz: float = 0.0, fy: float = 0.0, node: int = 0) -> np.ndarray:
    full = np.zeros((5, 6))
    full[node, 2] = fz
    full[node, 1] = fy
    return full


# --- lecture du .comm ---------------------------------------------------------------


def test_lecture_des_charges_du_comm() -> None:
    analysis, inventory = _inventory()
    cases = {c.name: c for c in read_case_loads(analysis, inventory, {"MOB1"})}
    assert list(cases) == ["G", "Q", "P", "L", "C", "TEMP"]
    assert cases["G"].gravity == [(9.81, (0.0, 0.0, -1.0))]
    assert cases["G"].nature == "pesanteur"
    assert cases["Q"].distributed == [
        (["BARRE_A"], {"FZ": -1000.0}),
        (["BARRE_B"], {"FZ": -500.0, "FY": 200.0}),
    ]
    assert cases["P"].points == [(["POINTE"], {"FY": -8000.0})]
    assert cases["P"].nature == "ponctuelle"
    assert cases["TEMP"].temperature == [(["BARRE_A", "BARRE_B"], 20.0)]
    assert cases["TEMP"].nature == "température"
    # Composantes locales et charges non dessinées : listées, jamais dessinées.
    assert cases["L"].distributed == []
    assert "composantes locales ['N']" in cases["L"].skipped[0]
    assert cases["C"].skipped == ["AFFE_CHAR_MECA CH_C/FORCE_COQUE : non dessiné"]


# --- champs et résultantes -----------------------------------------------------------


def _case(name: str, d: _Livrables) -> Any:
    analysis, inventory = _inventory()
    loads = {c.name: c for c in read_case_loads(analysis, inventory, {"MOB1"})}
    return build_case(loads[name], d, linear_cells(d.mesh))  # type: ignore[arg-type]


def test_intensite_par_element_et_resultante() -> None:
    d = _Livrables()
    d.fields["FN_Q"] = _nodal(fz=-3500.0)
    data = _case("Q", d)
    # BARRE_A (2 m) : -1000 N/m en Z ; BARRE_B (3 m) : -500 N/m en Z et 200 N/m en Y.
    assert data.distributed[0].tolist() == [0, 0, -1000.0, 0, 0, 0]
    assert data.distributed[1].tolist() == [0, 200.0, -500.0, 0, 0, 0]
    assert data.expected == {"FX": 0.0, "FY": 600.0, "FZ": -3500.0}
    assert np.all(data.temperature == 0.0)


def test_ponctuelle_et_temperature() -> None:
    d = _Livrables()
    d.fields["FN_P"] = _nodal(fy=-8000.0, node=3)
    point = _case("P", d)
    assert point.expected == {"FX": 0.0, "FY": -8000.0, "FZ": 0.0}
    assert point.distributed.sum() == 0.0
    d.fields["FV_TEMP"] = np.zeros((5, 6))
    temp = _case("TEMP", d)
    assert temp.temperature.tolist() == [20.0, 20.0]
    assert temp.expected is None


def test_cas_sans_champ_de_forces_refuse() -> None:
    d = _Livrables()
    with pytest.raises(ProjectError, match="FN_/FV_"):
        _case("Q", d)


def test_sommes_fn_et_fv() -> None:
    d = _Livrables()
    d.fields["FN_TEMP"] = _nodal(fz=5.0)
    d.fields["FV_TEMP"] = _nodal(fz=7.0)
    assert _case("TEMP", d).nodal[0, 2] == 12.0


def test_resultantes_verdicts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    d = _Livrables()
    d.fields["FN_Q"] = _nodal(fz=-3500.0, fy=600.0)
    d.fields["FN_G"] = _nodal(fz=-100.0)
    d.fields["FV_TEMP"] = _nodal(fz=1.0)
    cases = [_case(n, d) for n in ("Q", "G", "TEMP")]
    declared = {"G": {"attendu_tel_qu_evalue_n": {"DX": 0.0, "DY": 0.0, "DZ": -100.0}}}
    monkeypatch.setattr(
        "aster_expert.livrables.vues.control_loads", lambda _c, _d: {"cas": declared}
    )
    ctx = SimpleNamespace(declaration=SimpleNamespace(controls=None), repo_root=ROOT)
    rows = {r["cas"]: r for r in resultants(ctx, d, cases)}  # type: ignore[arg-type]
    assert rows["Q"]["verdict"] == "RÉUSSI"
    assert rows["Q"]["ecart_relatif"] == 0.0
    assert rows["G"]["verdict"] == "RÉUSSI"
    assert "controls.cases" in rows["G"]["source"]
    assert rows["TEMP"]["verdict"] == "INFORMATIF"
    # Une charge appliquée de travers est rapportée comme un échec.
    d.fields["FN_Q"] = _nodal(fz=-3000.0, fy=600.0)
    wrong = [_case("Q", d)]
    assert resultants(ctx, d, wrong)[0]["verdict"] == "ÉCHEC"  # type: ignore[arg-type]
    out = tmp_path / "resultantes.csv"
    write_resultants_csv(ctx, out, resultants(ctx, d, cases))  # type: ignore[arg-type]
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith("cas;nature;SFX_kN")
    assert any(line.startswith("Q;répartie;0.0;0.6;-3.5") for line in lines)


# --- .vtu, script ------------------------------------------------------------------------


def test_vtu_script_et_manifeste(tmp_path: Path) -> None:
    d = _Livrables()
    d.fields["FN_Q"] = _nodal(fz=-3500.0)
    d.fields["FN_P"] = _nodal(fy=-8000.0, node=3)
    cases = [_case("Q", d), _case("P", d)]
    cells = linear_cells(d.mesh)
    report = write_vtus(d, tmp_path, cases, cells, {"reactions": ["APPUI"]})  # type: ignore[arg-type]
    assert set(report) == {
        "modele.vtu",
        "charges_Q.vtu",
        "charges_P.vtu",
        "appuis_reactions.vtu",
    }
    assert all(r["identiques"] for r in report.values())
    grid = read_vtu(tmp_path / "charges_Q.vtu")
    assert grid.cell_data["CHARGE_REPARTIE_FZ"].tolist() == [-1000.0, -500.0]
    assert np.allclose(
        grid.cell_data["INTENSITE_REPARTIE_kN_m"], [1.0, np.hypot(0.5, 0.2)]
    )
    assert np.isnan(
        read_vtu(tmp_path / "charges_P.vtu").cell_data["INTENSITE_REPARTIE_kN_m"]
    ).all()
    ctx = SimpleNamespace(declaration=SimpleNamespace(name="essai"), repo_root=ROOT)
    manifest = build_manifest(ctx, d, cases, {"reactions": ["APPUI"]}, ("Q", "ABSENT"))  # type: ignore[arg-type]
    assert manifest["cas_en_plan"] == ["Q"]
    assert [c["nom"] for c in manifest["cas"]] == ["Q", "P"]
    # Échelle commune d'une nature : la flèche la plus longue vaut 12 % de la taille.
    scale = manifest["echelles"]["répartie"]
    assert scale["m_par_kN"] * scale["max_kN"] == pytest.approx(
        0.12 * manifest["taille_du_modele_m"]
    )
    assert manifest["cas"][0]["titre"].startswith("Q - charge répartie - ΣFX = 0,0 kN")
    script = write_script(manifest, tmp_path)
    text = script.read_text(encoding="utf-8")
    assert 'CAS_AFFICHE = "Q"' in text
    assert "CAS_EN_PLAN = ('Q',)" in text
    assert "FACTEUR_ECHELLE = None" in text and "SOUS_ECHANTILLONNAGE = 1" in text
    assert "@@" not in text
    # Le manifeste intégré se relit.
    start = text.index('json.loads(r"""') + len('json.loads(r"""')
    embedded = json.loads(text[start : text.index('""")', start)])
    assert embedded["cas"][1]["nature"] == "ponctuelle"


# --- règle : tout projet livre le MED, le script et les images ---------------------------


def test_la_sous_etape_charges_fait_partie_de_la_chaine_par_defaut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert chaine.SUBSTEPS.index("traiter") < chaine.SUBSTEPS.index("charges")
    assert chaine.SUBSTEPS.index("charges") < chaine.SUBSTEPS.index("vues")
    called: list[str] = []

    def fake_step(_ctx: object, _rt: object = None) -> list[str]:
        called.append("x")
        return []

    monkeypatch.setattr(charges_verif, "step_charges", fake_step)
    for name in ("preparer", "executer", "verifier", "traiter"):
        monkeypatch.setattr(chaine, f"step_{name}", lambda *_a, **_k: [])
    from aster_expert.livrables import ingenieur, paraview, vues

    monkeypatch.setattr(vues, "step_vues", lambda *_a, **_k: [])
    monkeypatch.setattr(ingenieur, "step_ingenieur", lambda *_a, **_k: [])
    monkeypatch.setattr(paraview, "step_images", lambda *_a, **_k: [])
    lines = chaine.run_deliverables(SimpleNamespace(), None)  # type: ignore[arg-type]
    assert "-- livrables : charges" in lines
    assert called == ["x"]


def test_la_declaration_accepte_les_vues_en_plan() -> None:
    from aster_expert.projet.context import load_project

    ctx = load_project("pontons_alu_01", ROOT)
    assert ctx.declaration.deliverables is not None
    assert ctx.declaration.deliverables.load_plan_views == ("Q", "HU_PLATELAGE")
    assert NODAL_COMPONENTS == ("FX", "FY", "FZ", "MX", "MY", "MZ")
    assert CaseLoads("x").nature == "autre"


def test_depot_avec_lisezmoi_et_empreintes(tmp_path: Path) -> None:
    source = tmp_path / "res" / "livrables" / "charges"
    (source / "png").mkdir(parents=True)
    (source / "png" / "Q_iso.png").write_bytes(b"png")
    (source / "png" / "charges_paraview.log").write_text("journal", encoding="utf-8")
    (source / "charges.med").write_bytes(b"med")
    (source / "manifeste.json").write_text(
        json.dumps({"projet": "essai", "cas": [{"nom": "G1"}, {"nom": "Q"}]}),
        encoding="utf-8",
    )
    ctx = SimpleNamespace(results_dir=tmp_path / "res")
    dest = tmp_path / "echanges" / "essai"
    names = charges_verif.deposit(ctx, dest)  # type: ignore[arg-type]
    assert "png/Q_iso.png" in names and "LISEZMOI.txt" in names
    assert not (dest / "png" / "charges_paraview.log").exists()
    assert len((dest / "LISEZMOI.txt").read_text(encoding="utf-8").splitlines()) <= 10
    lines = (dest / "empreintes.sha256").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(
        names
    )  # chaque fichier déposé, sauf le fichier d empreintes lui-même
    assert any(line.endswith("  charges.med") for line in lines)
    with pytest.raises(ProjectError, match="livrables absents"):
        charges_verif.deposit(SimpleNamespace(results_dir=tmp_path / "vide"), dest)  # type: ignore[arg-type]
