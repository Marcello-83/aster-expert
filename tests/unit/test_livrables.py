"""Livrables de résultats (lot 49) : contrat, inventaire des cas, .comm de
post-traitement, combinaisons et enveloppes, VTU, lecture des résultats, scripts
ParaView, règle des fils. Sans Docker ni Salomé : les tableaux des livrables sont
fabriqués ici avec le même code numérique que le conteneur
(`aster_expert.livrables.calcul`)."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from aster_expert.execution.regle_fils import threads_for
from aster_expert.execution.ressources import MachineResources
from aster_expert.livrables import calcul
from aster_expert.livrables.inventaire import inventory_of_text
from aster_expert.livrables.lecture import Query, query
from aster_expert.livrables.paraview import (
    charges_entries,
    result_groups,
    write_scripts,
)
from aster_expert.livrables.postcomm import (
    PostCommError,
    build_post_comm,
    expand_groups,
    field_keys,
)
from aster_expert.livrables.unites import si_unit
from aster_expert.livrables.vtu import Grid, check_identical, read_vtu, write_vtu
from aster_expert.projet.context import load_project
from aster_expert.projet.declaration import DeliverablesSection
from aster_expert.projet.errors import ProjectError

ROOT = Path(__file__).resolve().parents[2]

FIELDS: list[dict[str, Any]] = [
    {
        "family": "deplacements",
        "field": "DEPL",
        "components": ["DX", "DY", "DZ"],
        "convention": "repère global du modèle factice",
    },
    {
        "family": "efforts_poutres",
        "field": "EFGE_ELNO",
        "groups": ["POUTRE"],
        "components": ["N", "MFY"],
        "convention": "repère local de la poutre, N > 0 traction",
    },
    {
        "family": "reactions",
        "field": "REAC_NODA",
        "node_groups": ["APPUI"],
        "components": ["DX", "DY", "DZ"],
        "convention": "repère global, appui DZ = 0",
    },
]
NOT_RELEVANT = [
    {"item": "efforts_coques", "reason": "le modèle factice n'a pas de coque"},
    {"item": "contraintes_volumes", "reason": "le modèle factice n'a pas de volume"},
    {"item": "ressorts", "reason": "le modèle factice n'a pas de ressort"},
]


def _section(**changes: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "fields": FIELDS,
        "not_relevant": NOT_RELEVANT,
        "combinations": "declarees",
    }
    data.update(changes)
    return data


# --- contrat --------------------------------------------------------------------------


def test_the_contract_accepts_a_complete_declaration() -> None:
    section = DeliverablesSection.model_validate(_section())
    assert [f.field for f in section.fields] == ["DEPL", "EFGE_ELNO", "REAC_NODA"]


def test_a_family_neither_written_nor_excused_is_refused() -> None:
    with pytest.raises(ValidationError, match="ni produite ni déclarée.*ressorts"):
        DeliverablesSection.model_validate(_section(not_relevant=NOT_RELEVANT[:2]))


def test_an_excuse_needs_a_written_reason() -> None:
    short = [*NOT_RELEVANT[:2], {"item": "ressorts", "reason": "aucun"}]
    with pytest.raises(ValidationError, match="motif écrit"):
        DeliverablesSection.model_validate(_section(not_relevant=short))


def test_a_field_outside_its_family_is_refused() -> None:
    bad = [{**FIELDS[0], "field": "EFGE_NOEU"}, *FIELDS[1:]]
    with pytest.raises(ValidationError, match="champ EFGE_NOEU non admis"):
        DeliverablesSection.model_validate(_section(fields=bad))


def test_combinations_absent_without_reason_are_refused() -> None:
    data = _section()
    del data["combinations"]
    with pytest.raises(ValidationError, match="combinations` absent sans motif"):
        DeliverablesSection.model_validate(data)


def test_the_three_projects_declare_their_deliverables() -> None:
    for name in ("quai_cw_test_01", "dalle_appuyee_01", "estacade_pieux_01"):
        section = load_project(name, ROOT).declaration.deliverables
        assert section is not None, name
        assert section.fields, name


# --- inventaire et .comm de post-traitement -------------------------------------------

PRODUCTION = """DEBUT()
MA = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)
MO = AFFE_MODELE(
    MAILLAGE=MA,
    AFFE=_F(GROUP_MA="POUTRE", PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),
)
CM = AFFE_MATERIAU(MAILLAGE=MA, AFFE=_F(GROUP_MA="POUTRE", MATER=ACIER))
CA = AFFE_CARA_ELEM(
    MODELE=MO, POUTRE=_F(GROUP_MA="POUTRE", SECTION="CERCLE", CARA="R", VALE=0.1)
)
CL = AFFE_CHAR_MECA(MODELE=MO, DDL_IMPO=_F(GROUP_NO="APPUI", DX=0.0, DY=0.0, DZ=0.0))
CH_G = AFFE_CHAR_MECA(MODELE=MO, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(0.0, 0.0, -1.0)))
CH_Q = AFFE_CHAR_MECA(MODELE=MO, FORCE_POUTRE=_F(GROUP_MA="POUTRE", FZ=-10.0))
CH_P1 = AFFE_CHAR_MECA(MODELE=MO, FORCE_NODALE=_F(GROUP_NO="N1", FZ=-5.0))
MB = MACRO_ELAS_MULT(
    MODELE=MO, CHAM_MATER=CM, CARA_ELEM=CA, CHAR_MECA_GLOBAL=CL,
    CAS_CHARGE=(
        _F(NOM_CAS="G", CHAR_MECA=CH_G, OPTION="SANS"),
        _F(NOM_CAS="P1", CHAR_MECA=CH_P1, OPTION="SANS"),
    ),
)
MB = CALC_CHAMP(reuse=MB, RESULTAT=MB, FORCE=("REAC_NODA",))
IMPR_RESU(FORMAT="MED", UNITE=80, RESU=_F(RESULTAT=MB))
DETRUIRE(NOM=MB)
RESU_Q = MECA_STATIQUE(
    MODELE=MO, CHAM_MATER=CM, CARA_ELEM=CA, EXCIT=(_F(CHARGE=CL), _F(CHARGE=CH_Q))
)
FIN()
"""


def test_the_inventory_reads_the_cases_and_classifies_the_charges() -> None:
    inv = inventory_of_text(PRODUCTION)
    assert [(s.result, [c.name for c in s.cases]) for s in inv.solves] == [
        ("MB", ["G", "P1"]),
        ("RESU_Q", ["Q"]),
    ]
    assert inv.kinematic("CL") and not inv.kinematic("CH_G")
    case_g = inv.solves[0].cases[0]
    assert case_g.charges == ("CL", "CH_G")
    assert inv.loads_of(case_g) == ("CH_G",)
    assert not case_g.stores_sief
    assert inv.computed["MB"] == {"REAC_NODA"}
    assert inv.destroyed_at["MB"] == 24
    assert 80 in inv.units


def test_the_post_comm_inserts_blocks_and_keeps_the_production_text() -> None:
    inv = inventory_of_text(PRODUCTION)
    section = DeliverablesSection.model_validate(_section())
    text, plan = build_post_comm(
        PRODUCTION, inv, section, mobile_cases=["P1"], known_groups=["POUTRE", "APPUI"]
    )
    lines = text.splitlines()
    detruire = lines.index("DETRUIRE(NOM=MB)")
    block = lines[:detruire]
    assert any('NOM_CHAM_MED="CAS_G__DEPL"' in line for line in block)
    assert not any("CAS_P1__" in line for line in lines), "position mobile écrite"
    charge = next(line for line in lines if "CALC_VECT_ELEM" in line)
    assert "CHARGE=(CH_G,)" in charge and "MODELE=" not in charge
    assert "CL" not in charge.split("CHARGE=")[1].split(")")[0]
    assert plan.work_unit not in inv.units and plan.loads_unit not in inv.units
    # Seules des lignes sont ajoutées : la production reste, dans l'ordre.
    production = PRODUCTION.splitlines()
    kept = [line for line in lines if line in production]
    assert [line for line in kept if line.strip()] == [
        line for line in production if line.strip()
    ]
    assert [load.case for load in plan.loads] == ["G", "Q"]


def test_a_charge_mixing_kinematics_and_loads_is_refused() -> None:
    text = PRODUCTION.replace(
        "CH_G = AFFE_CHAR_MECA(MODELE=MO, PESANTEUR=",
        "CH_G = AFFE_CHAR_MECA(MODELE=MO, "
        'DDL_IMPO=_F(GROUP_NO="N1", DX=0.0), PESANTEUR=',
    )
    inv = inventory_of_text(text)
    with pytest.raises(PostCommError, match="non séparables"):
        build_post_comm(text, inv, DeliverablesSection.model_validate(_section()))


def test_group_patterns_and_repeated_fields() -> None:
    assert expand_groups(["R_*", "X"], ["R_1", "R_2", "S"]) == ("R_1", "R_2", "X")
    with pytest.raises(PostCommError, match="ne désigne rien"):
        expand_groups(["Z_*"], ["R_1"])
    section = DeliverablesSection.model_validate(
        _section(
            fields=[*FIELDS, {**FIELDS[1], "groups": ["TIRANT"], "components": ["N"]}]
        )
    )
    assert field_keys(section.fields) == [
        "DEPL",
        "EFGE_ELNO",
        "REAC_NODA",
        "EFGE_ELNO_2",
    ]


# --- calcul ---------------------------------------------------------------------------


def test_combinations_and_envelopes_keep_the_governing_case() -> None:
    arrays = {
        "G": np.array([[1.0], [2.0]]),
        "Q": np.array([[10.0], [0.0]]),
        "P1": np.array([[1.0], [-5.0]]),
        "P2": np.array([[3.0], [4.0]]),
    }
    base = calcul.combine(arrays, {"G": 1.35, "Q": 1.5})
    assert base[:, 0].tolist() == [1.35 + 15.0, 2.7]
    moving = calcul.with_moving(base, arrays, 2.0, ["P1", "P2"])
    assert moving.maximum[:, 0].tolist() == [base[0, 0] + 6.0, 2.7 + 8.0]
    assert moving.arg_max[:, 0].tolist() == [1, 1]
    assert moving.arg_min[:, 0].tolist() == [0, 0]
    fixed = calcul.with_moving(calcul.combine(arrays, {"G": 1.0}), arrays, 0.0, [])
    env = calcul.envelope([moving, fixed])
    assert env.max_combination[:, 0].tolist() == [0, 0]
    assert env.min_combination[:, 0].tolist() == [1, 0]
    assert env.min_position[:, 0].tolist() == [-1, 0]


def test_the_resultant_gives_the_point_of_application() -> None:
    coords = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 4.0, 0.0]])
    forces = np.array([[0.0, 0.0, -1.0], [0.0, 0.0, -1.0], [0.0, 0.0, -2.0]])
    r = calcul.resultant(coords, forces)
    assert r["FZ"] == -4.0
    assert r["X_APPLICATION_FZ"] == pytest.approx(1.5)
    assert r["Y_APPLICATION_FZ"] == pytest.approx(2.0)


def test_units_follow_the_family_not_the_name() -> None:
    assert si_unit("efforts_poutres", "EFGE_ELNO", "N") == "N"
    assert si_unit("efforts_coques", "EFGE_NOEU", "NXX") == "N/m"
    assert si_unit("efforts_coques", "EFGE_NOEU", "MXX") == "N·m/m"
    assert si_unit("deplacements", "DEPL", "DRZ") == "rad"
    with pytest.raises(KeyError):
        si_unit("deplacements", "DEPL", "INCONNUE")


# --- VTU ------------------------------------------------------------------------------


def test_a_vtu_is_read_back_identical(tmp_path: Path) -> None:
    grid = Grid(
        points=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]]),
        connectivity=np.array([0, 1, 2, 0, 1], dtype=np.int64),
        offsets=np.array([3, 5], dtype=np.int64),
        types=np.array([5, 3], dtype=np.uint8),
        point_data={"FN_G_DZ": np.array([-1.0, np.nan, 1.0e-300])},
        cell_data={"IDX": np.array([3, -1], dtype=np.int64)},
    )
    path = tmp_path / "essai.vtu"
    write_vtu(path, grid)
    report = check_identical(grid, path)
    assert report["identiques"], report
    read = read_vtu(path)
    assert np.isnan(read.point_data["FN_G_DZ"][1])
    altered = Grid(
        grid.points,
        grid.connectivity,
        grid.offsets,
        grid.types,
        {"FN_G_DZ": np.array([-1.0, np.nan, 2.0e-300])},
        grid.cell_data,
    )
    assert check_identical(altered, path)["differents"] == ["point:FN_G_DZ"]


# --- lecture des résultats (livrables fabriqués) --------------------------------------


def _write_deliverables(root: Path) -> None:
    """Livrables d'un modèle à 4 nœuds : une maille QUAD4 (DALLE), une SEG2 (POUTRE),
    appui au nœud 0 ; cas G et Q, positions P1 et P2 de la charge mobile."""
    data = root / "donnees"
    data.mkdir(parents=True)
    (root / "post").mkdir()
    mesh: dict[str, Any] = {
        "coords": np.array(
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [2.0, 2.0, 0.0], [0.0, 2.0, 0.0]]
        ),
        "conn_0": np.array([[0, 1, 2, 3]]),
        "type_0": np.array([4]),
        "conn_-1": np.array([[0, 1]]),
        "type_-1": np.array([1]),
        "gno_APPUI": np.array([0]),
        "gma_0_DALLE": np.array([0]),
        "gma_-1_POUTRE": np.array([0]),
    }
    np.savez(data / "maillage.npz", **mesh)
    combos: list[dict[str, Any]] = [
        {
            "name": "C1",
            "family": "ELU",
            "fixed": {"G": 1.35, "Q": 1.5},
            "definition": "C1",
        },
        {
            "name": "C2",
            "family": "ELS",
            "fixed": {"G": 1.0},
            "mobile_coefficient": 1.0,
            "mobile_cases": ["P1", "P2"],
            "mobile_label": "essieu",
            "definition": "C2",
        },
    ]
    cases = {
        "G": [1.0, 2.0, 3.0, 4.0],
        "Q": [0.5, -1.0, 0.0, 2.0],
        "P1": [0.0, 10.0, 0.0, 0.0],
        "P2": [0.0, 0.0, 0.0, -10.0],
    }
    layouts = {
        "DEPL": (np.zeros(4, int), np.arange(4), np.zeros(4, int), np.ones(4, int), 3),
        "EFGE_ELNO": (
            np.ones(2, int),
            np.zeros(2, int),
            np.arange(2),
            np.full(2, -1),
            2,
        ),
        "REAC_NODA": (
            np.zeros(1, int),
            np.zeros(1, int),
            np.zeros(1, int),
            np.ones(1, int),
            3,
        ),
    }
    container: dict[str, Any] = {
        "champs": {},
        "charges": {"FN_G": {"composantes": ["DX", "DY", "DZ"]}},
    }
    for key, (kind, entity, local, level, ncomp) in layouts.items():
        n = len(kind)
        arrays = {}
        for name, scale in cases.items():
            column = np.array([scale[(i * 3) % 4] for i in range(n)], dtype=float)
            arrays[name] = np.stack([column * (c + 1) for c in range(ncomp)], axis=1)
        npz: dict[str, Any] = {
            "row_kind": kind,
            "row_entity": entity,
            "row_local": local,
            "row_level": level,
        }
        for name in ("G", "Q"):
            npz[f"cas/{name}"] = arrays[name]
        for name in ("P1", "P2"):
            npz[f"pos/{name}"] = arrays[name]
        items = []
        for i, c in enumerate(combos):
            base = calcul.combine(arrays, c["fixed"])
            env = calcul.with_moving(
                base,
                arrays,
                float(c.get("mobile_coefficient", 0.0)),
                c.get("mobile_cases", []),
            )
            items.append(env)
            npz[f"comb/{i}/max"], npz[f"comb/{i}/min"] = env.maximum, env.minimum
            if c.get("mobile_cases"):
                npz[f"comb/{i}/max_pos"], npz[f"comb/{i}/min_pos"] = (
                    env.arg_max,
                    env.arg_min,
                )
        e = calcul.envelope(items)
        npz.update(
            {
                "env/max": e.maximum,
                "env/min": e.minimum,
                "env/max_comb": e.max_combination,
                "env/min_comb": e.min_combination,
                "env/max_pos": e.max_position,
                "env/min_pos": e.min_position,
            }
        )
        np.savez(data / f"{key}.npz", **npz)
        comps = {
            "DEPL": ["DX", "DY", "DZ"],
            "EFGE_ELNO": ["N", "MFY"],
            "REAC_NODA": ["DX", "DY", "DZ"],
        }[key]
        container["champs"][key] = {"composantes": comps}
    loads: dict[str, Any] = {
        "val/FN_G": np.zeros((4, 3)),
        "row_kind/FN_G": np.zeros(4, int),
        "row_entity/FN_G": np.arange(4),
    }
    np.savez(data / "charges.npz", **loads)
    plan = {
        "resultats": [
            {
                "champs": [
                    {"cle": "DEPL", "groupes": [], "groupes_noeuds": []},
                    {"cle": "EFGE_ELNO", "groupes": ["POUTRE"], "groupes_noeuds": []},
                    {"cle": "REAC_NODA", "groupes": [], "groupes_noeuds": ["APPUI"]},
                ]
            }
        ]
    }
    (root / "post" / "plan.json").write_text(json.dumps(plan), "utf-8")
    spec = {
        "cases": {n: {"elementary": n in ("G", "Q")} for n in cases},
        "combinations": combos,
        "envelopes": True,
    }
    (root / "spec.json").write_text(json.dumps(spec), "utf-8")
    (root / "conteneur.json").write_text(json.dumps(container), "utf-8")


@pytest.fixture
def delivered(fake_project: Callable[..., Any]) -> Any:
    project = fake_project(deliverables=_section())
    ctx = load_project(project.name, project.repo_root)
    (project.repo_root / "config").mkdir(exist_ok=True)
    shutil.copyfile(
        ROOT / "config" / "arrondis.yaml",
        project.repo_root / "config" / "arrondis.yaml",
    )
    _write_deliverables(ctx.results_dir / "livrables")
    return ctx


def test_an_extremum_gives_place_combination_and_position(delivered: Any) -> None:
    answer = query(
        delivered, Query(champ="DEPL", composantes=("DZ",), cas=("enveloppe",))
    )
    rows = {(r["cas_ou_combinaison"], r["extremum"]): r for r in answer.rows}
    top = rows[("enveloppe (max)", "max")]
    # DZ = 3 × valeur ; au nœud 4 : C1 = 1,35·2 + 1,5·(−1) = 1,2 ; C2 = 2 + max(P1 = 10,
    # P2 = 0) = 12 : C2 gouverne, avec la position P1.
    assert float(top["valeur_si"]) == pytest.approx(36.0)
    assert top["noeud_med"] == 4
    assert (top["combinaison_gouvernante"], top["position_mobile"]) == ("C2", "P1")
    low = rows[("enveloppe (min)", "min")]
    # min : C2 au nœud 2 = 4 + min(P1 = 0, P2 = −10) = −6 ; ×3.
    assert float(low["valeur_si"]) == pytest.approx(-18.0)
    assert (low["combinaison_gouvernante"], low["position_mobile"]) == ("C2", "P2")
    assert answer.provenance.startswith("provenance")


def test_a_point_a_group_and_a_sum(delivered: Any) -> None:
    point = query(
        delivered,
        Query(
            champ="DEPL",
            composantes=("DX",),
            cas=("G",),
            mode="point",
            point=(1.9, 0.1),
        ),
    )
    assert [r["noeud_med"] for r in point.rows] == [2]
    beam = query(
        delivered,
        Query(groupes=("POUTRE",), champ="EFGE_ELNO", cas=("G",), mode="tout"),
    )
    assert {r["extremite"] for r in beam.rows} == {1, 2}
    total = query(
        delivered, Query(champ="DEPL", composantes=("DX",), cas=("G",), mode="somme")
    )
    assert float(total.rows[0]["valeur_si"]) == pytest.approx(1.0 + 4.0 + 3.0 + 2.0)


def test_an_exclusion_disc_removes_the_singular_node(delivered: Any) -> None:
    every = query(delivered, Query(champ="DEPL", composantes=("DX",), cas=("G",)))
    discs = query(
        delivered,
        Query(
            champ="DEPL",
            composantes=("DX",),
            cas=("G",),
            disque_groupe="APPUI",
            disque_rayon=0.5,
        ),
    )
    assert 1 in {r["noeud_med"] for r in every.rows}
    assert 1 not in {r["noeud_med"] for r in discs.rows}
    assert any("disques d'exclusion" in n for n in discs.notes)


def test_an_unknown_case_is_refused_with_the_list(delivered: Any) -> None:
    with pytest.raises(ProjectError, match="cas ou combinaison inconnu : X"):
        query(delivered, Query(champ="DEPL", cas=("X",)))


# --- ParaView -------------------------------------------------------------------------

MANIFEST: dict[str, Any] = {
    "projet": "essai",
    "echelles": {
        "taille_du_modele_m": 10.0,
        "charges": {"FN_G": 100.0, "FN_Q": 50.0},
        "deplacements": {
            "CAS_G__DEPL": 0.01,
            "ENV__DEPL__MAX": 0.02,
            "ENV__DEPL__MIN": 0.02,
        },
        "fleches": {"CAS_G__REAC_NODA": 100.0},
    },
    "charges": [
        {"nom_med": "FN_G", "composantes": ["DX", "DY", "DZ"]},
        {"nom_med": "FN_Q", "composantes": ["DX", "DY", "DZ"]},
    ],
    # Lot 49 bis : grilles de flèches (sous-étape images) et extrema des titres.
    "grilles_charges": {
        "FN_G": {
            "fichier": "grille__FN_G.vtu",
            "fleches": 12,
            "pas_m": 0.5,
            "max_kN": 1.5,
            "somme_kN": [0.0, 0.0, -18.0],
        },
        "FN_Q": {
            "fichier": "grille__FN_Q.vtu",
            "fleches": 4,
            "pas_m": 0.5,
            "max_kN": 2.0,
            "somme_kN": [0.0, 0.0, -8.0],
        },
    },
    "extremes": {},
    "champs": [
        {
            "cle": "DEPL",
            "famille": "deplacements",
            "composantes": [{"nom": c, "unite_si": "m"} for c in ("DX", "DY", "DZ")],
            "noms_med": [
                "CAS_G__DEPL",
                "ENV__DEPL__MAX",
                "ENV__DEPL__MIN",
                "ENV__DEPL__MAX_COMB",
            ],
        },
        {
            "cle": "REAC_NODA",
            "famille": "reactions",
            "composantes": [{"nom": c, "unite_si": "N"} for c in ("DX", "DY", "DZ")],
            "noms_med": ["CAS_G__REAC_NODA"],
        },
    ],
}


def test_the_paraview_scripts_come_from_the_manifest(tmp_path: Path) -> None:
    assert [c["nom"] for c in charges_entries(MANIFEST)] == ["FN_G", "FN_Q"]
    groups = {g["nom"]: g for g in result_groups(MANIFEST)}
    assert set(groups) == {"G", "ENV_MAX", "ENV_MIN"}
    assert groups["G"]["deplacement"]["max"] == 0.01
    path_c, path_r = write_scripts(MANIFEST, tmp_path)
    for path in (path_c, path_r):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    text = path_c.read_text(encoding="utf-8")
    assert "CASES = [" not in text and "DEFAULT_SCALE_FACTOR" not in text
    data = path_c.with_suffix(".json").read_text(encoding="utf-8")  # lot 50 quinquies
    assert '"FN_Q"' in data and "FRACTION * TAILLE / maximum" in text
    # Lot 49 bis : flèches en kN sur la grille, titre, trois vues (iso, plan, élév.).
    assert "grille__FN_Q.vtu" in data and "kN par maille" in text
    for view in ("'iso'", "'plan'", "'elevation'"):
        assert view in text
    groups_text = path_r.read_text(encoding="utf-8") + path_r.with_suffix(
        ".json"
    ).read_text(encoding="utf-8")
    assert "0.001*" in groups_text and "déplacement max" in groups_text


def test_the_paraview_manifest_is_read_from_a_neighbouring_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lot 50 quinquies : le manifeste n'est plus embarqué (une ligne de 10 Mo que le
    Python de `pvbatch` refusait) ; il est lu dans un JSON voisin."""
    import sys  # noqa: PLC0415
    import types  # noqa: PLC0415

    path_c, path_r = write_scripts(MANIFEST, tmp_path)
    for path in (path_c, path_r):
        text = path.read_text(encoding="utf-8")
        assert max(len(line) for line in text.splitlines()) < 1000
        assert path.with_suffix(".json").is_file()
    big = {
        "taille_du_modele_m": 1.0,
        "cas": [],
        "groupes": [],
        "bourrage": "x" * 12_000_000,
    }
    path_c.with_suffix(".json").write_text(json.dumps(big), encoding="utf-8")
    assert path_c.with_suffix(".json").stat().st_size > 10_000_000
    fake = types.ModuleType("paraview.simple")
    monkeypatch.setitem(sys.modules, "paraview", types.ModuleType("paraview"))
    monkeypatch.setitem(sys.modules, "paraview.simple", fake)
    text = path_c.read_text(encoding="utf-8")
    head = text[: text.index("def _vue")]
    namespace: dict[str, object] = {"__file__": str(path_c)}
    exec(compile(head, str(path_c), "exec"), namespace)  # noqa: S102
    assert len(namespace["MANIFESTE"]["bourrage"]) == 12_000_000  # type: ignore[index]


# --- règle des fils -------------------------------------------------------------------


def test_the_thread_rule_shares_the_machine(tmp_path: Path) -> None:
    machine = MachineResources(
        cpus=14, memory_total_mb=21000, memory_available_mb=18000
    )
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "validation.yaml").write_text(
        "execution:\n  useful_threads_max: 4\n", encoding="utf-8"
    )
    assert threads_for(tmp_path, 1, machine) == 4
    assert threads_for(tmp_path, 3, machine) == 4
    assert threads_for(tmp_path, 5, machine) == 2
    assert threads_for(tmp_path, 20, machine) == 1
    (tmp_path / "config" / "machine.local.yaml").write_text(
        "execution:\n  useful_threads_max: 14\n", encoding="utf-8"
    )
    assert threads_for(tmp_path, 1, machine) == 14
    assert threads_for(tmp_path, 3, machine) == 4


def _loads(ctx: Any, fz: list[float]) -> None:
    data = ctx.results_dir / "livrables" / "donnees"
    forces = np.zeros((4, 3))
    forces[:, 2] = fz
    arrays: dict[str, Any] = {
        "val/FN_G": forces,
        "row_kind/FN_G": np.zeros(4, int),
        "row_entity/FN_G": np.arange(4),
    }
    np.savez(data / "charges.npz", **arrays)


def test_the_loads_control_passes_then_fails_when_a_load_moves(delivered: Any) -> None:
    from aster_expert.livrables.donnees import Deliverables
    from aster_expert.livrables.vues import control_loads

    root = delivered.results_dir / "livrables"
    # G attendu : ΣFZ = −100 N (extension du projet factice).
    _loads(delivered, [-25.0, -25.0, -25.0, -25.0])
    ok = control_loads(delivered, Deliverables(root))
    assert ok["verdict"] == "RÉUSSI"
    assert ok["cas"]["G"]["somme_n"]["X_APPLICATION_FZ"] == pytest.approx(1.0)
    # Charge déplacée sur deux nœuds et réduite de moitié : le contrôle échoue et le
    # point d'application montre le déplacement.
    _loads(delivered, [0.0, -25.0, -25.0, 0.0])
    moved = control_loads(delivered, Deliverables(root))
    assert moved["verdict"] == "ÉCHEC" and moved["echecs"] == ["G"]
    assert moved["cas"]["G"]["ecart_relatif"] == pytest.approx(0.5)
    assert moved["cas"]["G"]["somme_n"]["X_APPLICATION_FZ"] == pytest.approx(2.0)


def test_positions_fixed_combinations_and_sums_are_read(delivered: Any) -> None:
    def value(case: str) -> float:
        answer = query(
            delivered,
            Query(
                champ="DEPL",
                composantes=("DX",),
                cas=(case,),
                mode="point",
                point=(0.0, 2.0),
            ),
        )
        return float(answer.rows[0]["valeur_si"])

    # Nœud 4 (0, 2) : G = 2, Q = −1, P1 = 10, P2 = 0 (DX = 1 × valeur).
    assert value("P1") == 10.0
    assert value("C2@P1") == pytest.approx(12.0)
    assert value("C2@P2") == pytest.approx(2.0)
    assert value("expr:G+Q") == pytest.approx(1.0)
    assert value("expr:1.35*G-2*Q") == pytest.approx(2.7 + 2.0)
    with pytest.raises(ProjectError, match="n'est pas une position de C2"):
        value("C2@G")


def test_the_node_filter_intersects_the_groups(delivered: Any) -> None:
    beam = query(
        delivered,
        Query(
            groupes=("POUTRE",),
            noeuds="APPUI",
            champ="EFGE_ELNO",
            cas=("G",),
            mode="tout",
        ),
    )
    assert {r["noeud_med"] for r in beam.rows} == {1}
    assert {r["extremite"] for r in beam.rows} == {1}
