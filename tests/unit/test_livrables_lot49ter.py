"""Lot 49 ter : section en T (E25), bande d'exclusion (E26), coupe interpolée (E24),
moment sur appui (E27), zones disjointes et signe de section (D3), convention
ingénieur (D4), modèles dérivés (transformation du `.comm`), livraison et empreintes.

Sans Docker ni Salomé : chaque test fabrique ses lignes à la main et recalcule
l'attendu par force brute."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from aster_expert.livrables.appuis import design_moment
from aster_expert.livrables.combinaisons import GenericCombination
from aster_expert.livrables.derives import transform_comm
from aster_expert.livrables.donnees import FieldInfo, Mesh
from aster_expert.livrables.ingenieur import (
    disjoint_zones,
    identical_lines,
    opposite_signs,
)
from aster_expert.livrables.livraison import MANIFEST, deliver, verify
from aster_expert.livrables.sections import (
    BAR_SUFFIX,
    Band,
    FamilyRows,
    SectionRows,
    add_level_rows,
    compose_tee,
    rule_mask,
    singular_rows,
)
from aster_expert.livrables.torseurs import Target, engineer_label, kept
from aster_expert.projet.declaration import (
    DerivedModel,
    DesignMoment,
    DesignSection,
    EngineeringSummarySection,
    Level,
    MemberFamily,
    SectionRule,
    TeeSection,
)
from aster_expert.projet.errors import ProjectError

BEAM = ("N", "VY", "VZ", "MT", "MFY", "MFZ")
SHELL = ("NXX", "NYY", "NXY", "MXX", "MYY", "MXY", "QX", "QY")


def _info(field: str, family: str, comps: tuple[str, ...]) -> FieldInfo:
    return FieldInfo(field, field, family, comps, (), (), "repère d'essai")


def _family(**changes: Any) -> MemberFamily:
    data: dict[str, Any] = {
        "name": "chevêtres",
        "kind": "poutre",
        "field": "EFGE_ELNO",
        "groups": ["CHEV"],
        "quantities": list(BEAM),
        "moments": ["MFY"],
        "shears": ["VZ"],
    }
    data.update(changes)
    return MemberFamily.model_validate(data)


def _rows(
    family: MemberFamily,
    info: FieldInfo,
    xyz: np.ndarray[Any, Any],
    cases: dict[str, np.ndarray[Any, Any]],
    *,
    kind: int = 1,
    element: list[int] | None = None,
    local: list[int] | None = None,
    node: list[int] | None = None,
) -> FamilyRows:
    n = len(xyz)
    extra: tuple[str, ...] = ()
    if family.circular:
        extra = ("M_RES", "V_RES")
    elif family.kind == "coque":
        extra = ("V_RES",)
    return FamilyRows(
        family=family,
        info=info,
        index=np.arange(n),
        node=np.array(node if node is not None else range(n)),
        xyz=np.asarray(xyz, dtype=float),
        kind=np.full(n, kind),
        element=np.array(element if element is not None else range(n)),
        local=np.array(local if local is not None else [0] * n),
        level=np.full(n, -1 if kind else 1),
        member=[""] * n,
        columns=(*info.components, *extra),
        cases=cases,
    )


# --- E25 : section en T -----------------------------------------------------------


def test_the_tee_section_adds_the_trapezoid_integral_of_the_band() -> None:
    rng = np.random.default_rng(1)
    beam_xyz = np.array([[0.0, -1.0, 0.0], [0.0, 1.0, 0.0]])
    plate_xyz = np.array(
        [[x, y, 0.0] for y in (-1.0, 1.0) for x in (-0.6, -0.3, 0.0, 0.3, 0.6, 0.9)]
    )
    beam_cases = {"G": rng.normal(size=(2, 6))}
    plate_cases = {"G": rng.normal(size=(len(plate_xyz), 8))}
    beam = _rows(_family(), _info("EFGE_ELNO", "efforts_poutres", BEAM), beam_xyz,
                 copy.deepcopy(beam_cases))  # fmt: skip
    plate_family = MemberFamily.model_validate(
        {
            "name": "tablier",
            "kind": "coque",
            "field": "EFGE_NOEU",
            "groups": ["DALLE"],
            "quantities": list(SHELL),
        }
    )
    plate = _rows(plate_family, _info("EFGE_NOEU", "efforts_coques", SHELL),
                  plate_xyz, plate_cases, kind=0)  # fmt: skip
    tee = TeeSection.model_validate(
        {
            "plate_family": "tablier",
            "half_width": 0.6,
            "across": "X",
            "along": "Y",
            "parts": [
                {"beam": "N", "plate": "NYY"},
                {"beam": "MFY", "plate": "MYY"},
                {"beam": "VZ", "plate": "QY"},
            ],
            "source": "essai de la section en T",
        }
    )
    compose_tee(beam, plate, tee)
    assert beam.added == ("N_barre", "MFY_barre", "VZ_barre")
    assert beam.tee is not None and beam.tee["noeuds_par_bande"] == [5]
    out = beam.cases["G"]
    for r, y in enumerate((-1.0, 1.0)):
        on = (plate_xyz[:, 1] == y) & (np.abs(plate_xyz[:, 0]) <= 0.6 + 1e-9)
        xs = plate_xyz[on, 0]
        for beam_c, plate_c in (("N", "NYY"), ("MFY", "MYY"), ("VZ", "QY")):
            integral = np.trapezoid(plate_cases["G"][on, SHELL.index(plate_c)], xs)
            expected = beam_cases["G"][r, BEAM.index(beam_c)] + integral
            assert out[r, BEAM.index(beam_c)] == pytest.approx(expected, rel=1e-12)
            bar = beam.raw.index(f"{beam_c}{BAR_SUFFIX}")
            assert out[r, bar] == beam_cases["G"][r, BEAM.index(beam_c)]
    # Le point à X = 0,9 est hors de la bande ; VY, MT, MFZ restent ceux de la barre.
    assert out[0, BEAM.index("VY")] == beam_cases["G"][0, BEAM.index("VY")]


# --- E24 : coupe interpolée ---------------------------------------------------------


def _pile() -> FamilyRows:
    family = _family(
        name="pieux", groups=["PIEUX"], circular=True, moments=["MFY", "MFZ"],
        shears=["VY", "VZ"],
    )  # fmt: skip
    # Deux éléments : 0,5 → 0,7 et 0,7 → 1,3 ; une ligne par extrémité.
    xyz = np.array([[0, 0, 0.5], [0, 0, 0.7], [0, 0, 0.7], [0, 0, 1.3]], dtype=float)
    cases = {"G": np.arange(24, dtype=float).reshape(4, 6) + 1.0}
    info = _info("EFGE_ELNO", "efforts_poutres", BEAM)
    return _rows(
        family,
        info,
        xyz,
        cases,
        element=[0, 0, 1, 1],
        local=[0, 1, 0, 1],
        node=[0, 1, 1, 2],
    )


def test_a_level_without_node_is_interpolated_in_the_crossing_element() -> None:
    fr = _pile()
    assert add_level_rows(fr, Level(axis="Z", value=0.6)) == 1
    assert add_level_rows(fr, Level(axis="Z", value=0.6)) == 0  # une fois
    row = 4
    expected = 0.5 * fr.cases["G"][0] + 0.5 * fr.cases["G"][1]
    np.testing.assert_allclose(fr.cases["G"][row], expected)
    place = fr.place(row)
    assert place["noeud_med"] is None and place["coordonnees_m"][2] == 0.6
    assert place["interpolation"]["poids"] == pytest.approx([0.5, 0.5])
    mesh = Mesh({"coords": np.zeros((3, 3))})
    rule = SectionRule.model_validate(
        {"description": "coupe à +0,60 d'essai", "level": {"axis": "Z", "value": 0.6}}
    )
    mask, notes = rule_mask(fr, mesh, rule)
    assert mask.tolist() == [False, False, False, False, True]
    assert "1 ligne(s) interpolée(s)" in notes[0]


def test_an_exclusive_bound_keeps_the_zones_of_one_family_apart() -> None:
    fr = _pile()
    add_level_rows(fr, Level(axis="Z", value=0.6))
    mesh = Mesh({"coords": np.zeros((3, 3))})
    below = SectionRule.model_validate(
        {
            "description": "sous le nu, borne haute exclue",
            "box": {"z": [0.0, 0.7], "exclusive": ["z_max"]},
        }
    )
    mask, _ = rule_mask(fr, mesh, below)
    assert mask.tolist() == [True, False, False, False, True]


# --- E26 : bande d'exclusion ---------------------------------------------------------


def test_the_band_excludes_the_plate_strictly_inside_half_the_beam_width() -> None:
    plate_family = MemberFamily.model_validate(
        {
            "name": "tablier",
            "kind": "coque",
            "field": "EFGE_NOEU",
            "groups": ["DALLE"],
            "quantities": list(SHELL),
        }
    )
    xyz = np.array([[x, 0.0, 0.0] for x in (0.0, 0.3, 0.6, 0.65)])
    fr = _rows(plate_family, _info("EFGE_NOEU", "efforts_coques", SHELL), xyz,
               {"G": np.zeros((4, 8))}, kind=0)  # fmt: skip
    band = Band("chevêtres", np.array([[0.0, y] for y in (-1.0, 0.0, 1.0)]), 0.6, "E26")
    mesh = Mesh({"coords": xyz})
    flagged, reasons = singular_rows(fr, mesh, None, (), (band,))
    assert flagged.tolist() == [True, True, False, False]  # le nu (0,60) est lu
    assert "E26" in reasons[0] and "comparaison" in reasons[0]


# --- D3 : zones disjointes, lignes identiques, signe ---------------------------------


def _section(name: str, **changes: Any) -> DesignSection:
    data: dict[str, Any] = {
        "name": name,
        "label": name,
        "family": "chevêtres",
        "rule": {"description": "règle de la section d'essai"},
        "justification": "section d'essai du lot 49 ter",
        "not_exported": "section d'essai sans export",
    }
    data.update(changes)
    return DesignSection.model_validate(data)


def test_two_sections_of_a_family_must_not_share_a_row() -> None:
    fr = _pile()
    a = SectionRows(
        _section("a"), np.array([1, 1, 0, 0], bool), np.zeros(4, bool), {}, []
    )
    b = SectionRows(
        _section("b"), np.array([0, 1, 1, 0], bool), np.zeros(4, bool), {}, []
    )
    with pytest.raises(ProjectError, match="se recouvrent"):
        disjoint_zones(fr, [a, b])
    shared = SectionRows(_section("b", shared_rows=["a"]), b.mask, b.singular, {}, [])
    check = disjoint_zones(fr, [a, shared])
    assert check["paires"][0]["partage_declare"] is True
    # Même nœud (1) dans deux sections par deux extrémités d'élément différentes.
    c = SectionRows(
        _section("c"), np.array([0, 0, 1, 0], bool), np.zeros(4, bool), {}, []
    )
    with pytest.raises(ProjectError, match="1 nœud"):
        disjoint_zones(fr, [a, c])


def _torsor(section: str, value: float, **changes: Any) -> dict[str, Any]:
    t: dict[str, Any] = {
        "section": section,
        "famille": "chevêtres",
        "etat_limite": "ELU_fondamental",
        "grandeur": "MFY max",
        "colonne": "MFY",
        "sens": "max",
        "valeur_si": value,
        "significative": True,
        "combinaison": "C1",
        "position_mobile": None,
        "lieu": {"noeud_med": 3, "maille_med": 2, "extremite": 1,
                 "coordonnees_m": [0.0, 1.65, 0.0]},
    }  # fmt: skip
    t.update(changes)
    return t


def test_identical_lines_in_two_sections_are_refused() -> None:
    with pytest.raises(ProjectError, match="lignes identiques"):
        identical_lines([_torsor("travee", 1.0), _torsor("appui", 1.0)])
    identical_lines(
        [_torsor("travee", 1.0), _torsor("appui", 1.0, partages=["travee"])]
    )


def test_the_opposite_sign_is_kept_only_when_it_dimensions() -> None:
    small = [
        _torsor("appui", 5.0e5),
        _torsor("travee", 2.0e5, signe_oppose=True, significative=False),
    ]
    opposite_signs(small)
    assert small[1]["dimensionnant"] is False and not small[1]["significative"]
    large = [
        _torsor("appui", 5.0e5),
        _torsor("travee", 7.0e5, signe_oppose=True, significative=False),
    ]
    opposite_signs(large)
    assert large[1]["dimensionnant"] is True and large[1]["significative"]


def test_a_span_section_keeps_the_span_sign_and_names_it() -> None:
    travee = _section("t", zone="travee", moment_signs={"MFY": "negative"})
    beam = _rows(_family(), _info("EFGE_ELNO", "efforts_poutres", BEAM),
                 np.zeros((1, 3)), {})  # fmt: skip
    sag = Target("MFY min", "MFY", "min", "M")
    hog = Target("MFY max", "MFY", "max", "M")
    assert kept(travee, sag) and not kept(travee, hog)
    assert engineer_label(beam, travee, sag) == "moment de travée max"
    assert engineer_label(beam, travee, hog) == "moment de signe opposé"
    n_max = Target("N max", "N", "max", "N")
    assert engineer_label(beam, travee, n_max) == "traction max"
    assert engineer_label(beam, travee, Target("N min", "N", "min", "N")) == (
        "compression max"
    )


# --- E27 : moment sur appui ---------------------------------------------------------


def test_the_support_moment_is_the_max_of_the_face_and_0p65_fixed_end() -> None:
    family = _family()
    info = _info("EFGE_ELNO", "efforts_poutres", BEAM)
    # Deux appuis (Y = ±2) : nus en Y = ±1,65, axes en Y = ±2.
    xyz = np.array([[0, -1.65, 0], [0, 1.65, 0], [0, -2.0, 0], [0, 2.0, 0]], float)
    rng = np.random.default_rng(7)
    names = ("G", "Q", "P1", "P2")
    ref_cases = {c: rng.normal(scale=1e5, size=(4, 6)) for c in names}
    aux_cases = {c: rng.normal(scale=1e5, size=(4, 6)) for c in names}
    ref = _rows(family, info, xyz, ref_cases)
    aux = _rows(family, info, xyz, aux_cases)
    section = _section(
        "nu",
        zone="appui",
        moment_signs={"MFY": "positive"},
        design_moment={
            "quantity": "MFY",
            "fraction": 0.65,
            "auxiliary": "A1",
            "axis_rule": {"description": "axe des pieux d'essai"},
            "supports": {"node_group": "TETES", "axes": ["Y"]},
            "source": "E27 d'essai",
        },
    )
    sec = SectionRows(section, np.array([1, 1, 0, 0], bool), np.zeros(4, bool), {}, [])
    mesh = Mesh(
        {
            "coords": np.array([[0, -2.0, 0], [0, 2.0, 0]], float),
            "gno_TETES": np.array([0, 1]),
        }
    )
    combos = [
        GenericCombination(name="C1", family="ELU", fixed={"G": 1.35, "Q": 1.5}),
        GenericCombination(
            name="C2", family="ELU", fixed={"G": 1.0, "Q": 0.8},
            mobile_coefficient=1.5, mobile_cases=("P1", "P2"),
        ),
    ]  # fmt: skip
    dm = section.design_moment
    assert isinstance(dm, DesignMoment)
    result = design_moment(
        mesh=mesh,
        ref=ref,
        sec=sec,
        ref_axis_rows=np.array([2, 3]),
        aux=aux,
        aux_axis_rows=np.array([2, 3]),
        dm=dm,
        state_combinations={"ELU_fondamental": list(enumerate(combos))},
        excluded=("Q",),
    )["ELU_fondamental"]
    k = BEAM.index("MFY")
    best = -np.inf

    def value(
        comb: GenericCombination,
        p: str | None,
        cases: dict[str, Any],
        skip: tuple[str, ...],
        row: int,
    ) -> float:
        v = sum(c * cases[n][row, k] for n, c in comb.fixed.items() if n not in skip)
        if p is not None:
            v += comb.mobile_coefficient * cases[p][row, k]
        return float(v)

    for comb in combos:
        for p in comb.mobile_cases or (None,):
            for nu_row, axis_row in ((0, 2), (1, 3)):
                m_nu = value(comb, p, ref_cases, (), nu_row)
                m_enc = value(comb, p, aux_cases, ("Q",), axis_row)
                best = max(best, max(m_nu, 0.65 * m_enc))
    assert result.best is not None
    assert result.best["M_dim"] == pytest.approx(best, rel=1e-12)
    assert result.best["terme_gouvernant"] in ("M_nu", "0,65·M_enc")
    assert len(result.per_support) == 2


# --- schéma ---------------------------------------------------------------------------


def test_the_schema_requires_a_design_moment_on_a_support_section() -> None:
    with pytest.raises(ValidationError, match="design_moment"):
        _section("appui", zone="chapeau", moment_signs={"MXX": "positive"})
    length = {"value": 0.5, "unit": "m", "source": "essai"}
    text = {"value": "C35/45", "source": "essai"}
    export = {
        "section_type": "rectangulaire",
        **dict.fromkeys(("h", "b", "ds", "di", "cnom"), length),
        **dict.fromkeys(("concrete", "steel", "exposure"), text),
        "planes": [{"moment": "resultante", "label": "moment résultant"}],
    }
    with pytest.raises(ValidationError, match="comparaison"):
        _section("tete", zone="comparaison", not_exported=None, bending_export=export)
    with pytest.raises(ValidationError, match="ni blocage ni partie rigide"):
        DerivedModel.model_validate(
            {
                "name": "A9",
                "kind": "auxiliaire",
                "label": "modèle vide",
                "purpose": "modèle dérivé sans condition",
                "fields": ["EFGE_ELNO"],
                "source": "essai du schéma",
            }
        )
    with pytest.raises(ValidationError, match="réservés aux poutres"):
        _family(
            kind="coque",
            field="EFGE_NOEU",
            quantities=list(SHELL),
            moments=[],
            shears=[],
            exclusion_band={"half_width": 0.6, "source": "E26 d'essai"},
        )


def test_the_estacade_declares_the_rules_of_lot_49ter() -> None:
    from aster_expert.projet.context import load_project  # noqa: PLC0415

    root = Path(__file__).resolve().parents[2]
    summary = load_project("estacade_pieux_01", root).declaration.engineering_summary
    assert isinstance(summary, EngineeringSummarySection)
    sections = {s.name: s for s in summary.sections}
    assert sections["tete_de_pieu"].zone == "comparaison"
    nu = sections["bouchon_nu_chevetre"]
    assert nu.rule.level == Level(axis="Z", value=0.60)  # E24
    assert nu.design_moment is not None and nu.design_moment.auxiliary == "A3"
    assert sections["chevetre_nu_appui"].design_moment.auxiliary == "A1"  # type: ignore[union-attr]
    assert sections["dalle_chapeau"].design_moment.auxiliary == "A2"  # type: ignore[union-attr]
    chev = next(f for f in summary.families if f.name == "chevêtres")
    assert chev.tee_section is not None and chev.tee_section.half_width == 0.60  # E25
    assert chev.exclusion_band is not None and chev.exclusion_band.half_width == 0.60
    models = {m.name: m for m in summary.derived_models}
    assert {"A1", "A2", "A3", "V1"} == set(models)
    for name in ("A1", "A2", "A3"):
        assert models[name].kind == "auxiliaire"
        assert set(models[name].excluded_cases) == {"FR", "TEP", "TEM"}
    assert models["V1"].kind == "variante" and not models["V1"].excluded_cases


# --- modèles dérivés : transformation du .comm ---------------------------------------

COMM = """DEBUT(CODE="OUI")
MAIL = LIRE_MAILLAGE(FORMAT="MED", UNITE=20)
MODELE = AFFE_MODELE(
    MAILLAGE=MAIL,
    AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="POU_D_T"),
)
CL = AFFE_CHAR_MECA(MODELE=MODELE, DDL_IMPO=_F(GROUP_NO="PIEDS", DZ=0.0))
MB01 = MACRO_ELAS_MULT(
    MODELE=MODELE,
    CHAR_MECA_GLOBAL=CL,
    CAS_CHARGE=(_F(NOM_CAS="PP", CHAR_MECA=CH_PP, OPTION="SANS"),),
)
TEP = MECA_STATIQUE(MODELE=MODELE, EXCIT=_F(CHARGE=CL))
FIN()
"""


def _model(**changes: Any) -> DerivedModel:
    data: dict[str, Any] = {
        "name": "A3",
        "kind": "auxiliaire",
        "label": "modèle dérivé d'essai",
        "purpose": "tronçon rigide et rotations bloquées",
        "rigid": [{"cell_group": "T1", "per_member": "PIEU_*"}],
        "blocks": [{"node_group": "TETES", "dofs": ["DRX", "DRY", "DRZ"]}],
        "excluded_cases": ["FR"],
        "excluded_reason": "charges verticales seulement dans l'essai",
        "fields": ["EFGE_ELNO"],
        "source": "essai de la transformation",
    }
    data.update(changes)
    return DerivedModel.model_validate(data)


def test_a_derived_model_adds_its_load_to_every_solve_and_nothing_else() -> None:
    out = transform_comm(COMM, _model(), ["PIEU_A", "PIEU_B", "T1"])
    text = out.text
    assert out.solves == 2 and out.rigid_groups == ("DRV_R01", "DRV_R02")
    assert 'INTERSEC=("T1", "PIEU_A")' in text
    assert text.index("DEFI_GROUP") < text.index("AFFE_MODELE")
    assert text.index("DRV_A3 = AFFE_CHAR_MECA") < text.index("MACRO_ELAS_MULT")
    assert "CHAR_MECA_GLOBAL=(CL, DRV_A3)" in text
    assert "EXCIT=(_F(CHARGE=CL), _F(CHARGE=DRV_A3))" in text
    assert '_F(GROUP_NO=("TETES",), DRX=0.0, DRY=0.0, DRZ=0.0)' in text
    # Le .comm de production est repris mot pour mot hors des blocs ajoutés.
    kept_lines = [line for line in COMM.splitlines() if "CHAR_MECA_GLOBAL" not in line
                  and "EXCIT" not in line]  # fmt: skip
    for line in kept_lines:
        assert line in text
    blocked = transform_comm(
        COMM,
        _model(rigid=[], blocks=[{"cell_group": "CHEV", "dofs": ["DZ", "DRY"]}]),
        [],
    )
    assert blocked.reaction_groups == ("DRV_B01",)
    assert '_F(GROUP_MA="CHEV", NOM="DRV_B01")' in blocked.text


def test_a_solve_of_unknown_form_is_refused() -> None:
    odd = COMM.replace("EXCIT=_F(CHARGE=CL)", "EXCIT=(_F(CHARGE=CL), _F(CHARGE=X))")
    with pytest.raises(ProjectError, match="forme non reconnue"):
        transform_comm(odd, _model(), ["PIEU_A"])
    with pytest.raises(ProjectError, match="aucun groupe"):
        transform_comm(COMM, _model(), ["AUTRE"])


# --- livraison --------------------------------------------------------------------


def test_a_file_modified_after_delivery_is_reported(
    fake_project: Any, tmp_path: Path
) -> None:
    from aster_expert.projet.context import load_project  # noqa: PLC0415

    project = fake_project()
    ctx = load_project(project.name, project.repo_root)
    root = ctx.results_dir / "livrables"
    (root / "paquet" / "flexion_composee").mkdir(parents=True)
    (root / "paquet" / "diagrammes").mkdir(parents=True)
    (root / "classeur_livrables.xlsx").write_bytes(b"classeur")
    (root / "paquet" / "flexion_composee" / "a.csv").write_text("N;M\r\n1,0;2,0\r\n")
    (root / "paquet" / "diagrammes" / "d.png").write_bytes(b"png")
    target = tmp_path / "echange"
    manifest = deliver(ctx, target)
    assert set(manifest["fichiers"]) == {
        "classeur_livrables.xlsx",
        "flexion_composee/a.csv",
        "diagrammes/d.png",
    }
    assert verify(target)["verdict"] == "INTACT"
    # Réenregistré par un tableur : séparateurs et fins de ligne changés.
    (target / "flexion_composee" / "a.csv").write_text("N,M\n1.0,2.0\n")
    (target / "notes.txt").write_text("ajout")
    (target / "diagrammes" / "d.png").unlink()
    result = verify(target)
    assert result["verdict"] == "MODIFIÉ"
    assert result["modifies"] == ["flexion_composee/a.csv"]
    assert result["absents"] == ["diagrammes/d.png"]
    assert result["ajoutes"] == ["notes.txt"]
    assert (target / MANIFEST).is_file()


# --- preuve de D1 : équilibre d'une coupe ----------------------------------------


def _save(path: Path, **arrays: Any) -> None:
    np.savez(path, **arrays)


def _console(root: Path, mfy: float) -> None:
    """Console selon Y (x_l = −Y, y_l = +X), nœuds Y = 0, 1, 2, et une plaque de deux
    mailles qui partage ses nœuds ; charge P en bout ; MFY imposé à la coupe Y = 1."""
    import json  # noqa: PLC0415

    data = root / "donnees"
    data.mkdir(parents=True)
    (root / "post").mkdir()
    coords = np.array(
        [[0.0, y, 0.0] for y in (0.0, 1.0, 2.0)]
        + [[1.0, y, 0.0] for y in (0.0, 1.0, 2.0)]
    )
    _save(
        data / "maillage.npz",
        coords=coords,
        **{
            "conn_-1": np.array([[2, 1], [1, 0]]),
            "type_-1": np.ones(2, int),
            "conn_0": np.array([[0, 3, 4, 1], [1, 4, 5, 2]]),
            "type_0": np.full(2, 4),
            "gma_-1_CHEV": np.array([0, 1]),
            "gma_0_DALLE": np.array([0, 1]),
            "gno_APPUI": np.array([0]),
        },
    )
    beam = np.zeros((4, 6))
    beam[1, BEAM.index("MFY")] = mfy  # élément Y 2 → 1, extrémité au nœud 1
    beam[2, BEAM.index("MFY")] = mfy  # élément Y 1 → 0, extrémité au nœud 1
    _save(
        data / "EFGE_ELNO.npz",
        row_kind=np.ones(4, int),
        row_entity=np.array([0, 0, 1, 1]),
        row_local=np.array([0, 1, 0, 1]),
        row_level=np.full(4, -1),
        **{"cas/PP": beam},
    )
    _save(
        data / "EFGE_NOEU.npz",
        row_kind=np.zeros(6, int),
        row_entity=np.arange(6),
        row_local=np.zeros(6, int),
        row_level=np.ones(6, int),
        **{"cas/PP": np.zeros((6, 8))},
    )
    _save(
        data / "REAC_NODA.npz",
        row_kind=np.zeros(1, int),
        row_entity=np.array([0]),
        row_local=np.zeros(1, int),
        row_level=np.ones(1, int),
        **{"cas/PP": np.array([[0.0, 0.0, 1000.0]])},
    )
    load = np.zeros((6, 6))
    load[2, 2] = -1000.0  # P = 1 kN au bout (Y = 2)
    _save(
        data / "charges.npz",
        **{
            "val/FN_PP": load,
            "row_kind/FN_PP": np.zeros(6, int),
            "row_entity/FN_PP": np.arange(6),
        },
    )
    plan = {
        "resultats": [
            {
                "champs": [
                    {"cle": "EFGE_NOEU", "groupes": ["DALLE"], "groupes_noeuds": []},
                    {"cle": "EFGE_ELNO", "groupes": ["CHEV"], "groupes_noeuds": []},
                    {"cle": "REAC_NODA", "groupes": [], "groupes_noeuds": ["APPUI"]},
                ]
            }
        ]
    }
    (root / "post" / "plan.json").write_text(json.dumps(plan), "utf-8")
    container = {
        "champs": {
            "EFGE_NOEU": {"composantes": list(SHELL)},
            "EFGE_ELNO": {"composantes": list(BEAM)},
            "REAC_NODA": {"composantes": ["DX", "DY", "DZ"]},
        },
        "charges": {"FN_PP": {"composantes": ["DX", "DY", "DZ", "DRX", "DRY", "DRZ"]}},
    }
    (root / "conteneur.json").write_text(json.dumps(container), "utf-8")
    (root / "spec.json").write_text(
        json.dumps({"cases": {"PP": {"elementary": True}}, "combinations": []}), "utf-8"
    )


@pytest.mark.parametrize(("mfy", "exact"), [(1000.0, True), (900.0, False)])
def test_the_cut_moment_balances_the_free_body(
    tmp_path: Path, mfy: float, exact: bool
) -> None:
    from aster_expert.livrables.coupe import cut_equilibrium  # noqa: PLC0415
    from aster_expert.livrables.donnees import Deliverables  # noqa: PLC0415
    from aster_expert.projet.declaration import (  # noqa: PLC0415
        DeliverableField,
        EquilibriumCut,
    )

    _console(tmp_path, mfy)
    d = Deliverables(tmp_path)
    fields = [
        DeliverableField.model_validate(f)
        for f in (
            {"family": "efforts_coques", "field": "EFGE_NOEU", "groups": ["DALLE"],
             "convention": "plaque d'essai"},
            {"family": "efforts_poutres", "field": "EFGE_ELNO", "groups": ["CHEV"],
             "convention": "console d'essai"},
            {"family": "reactions", "field": "REAC_NODA", "node_groups": ["APPUI"],
             "convention": "appui d'essai"},
        )
    ]  # fmt: skip
    infos = d.field_infos(fields)
    summary = EngineeringSummarySection.model_validate(
        {
            "limit_states": [{"state": "ELU_fondamental", "families": ["ELU"]}],
            "absent_limit_states": [
                {"state": s, "reason": "absent de l'essai de coupe"}
                for s in (
                    "ELU_accidentel",
                    "ELS_caracteristique",
                    "ELS_frequent",
                    "ELS_quasi_permanent",
                )
            ],
            "cracking": {"state": "ELU_fondamental", "source": "essai de coupe"},
            "families": [
                {
                    "name": "chevêtres",
                    "kind": "poutre",
                    "field": "EFGE_ELNO",
                    "groups": ["CHEV"],
                    "quantities": list(BEAM),
                    "moments": ["MFY"],
                    "tee_section": {
                        "plate_family": "tablier",
                        "half_width": 0.6,
                        "across": "X",
                        "along": "Y",
                        "parts": [{"beam": "MFY", "plate": "MYY"}],
                        "source": "essai de coupe",
                    },
                },
                {
                    "name": "tablier",
                    "kind": "coque",
                    "field": "EFGE_NOEU",
                    "groups": ["DALLE"],
                    "quantities": list(SHELL),
                },
            ],
            "sections": [_section("x").model_dump()],
            "no_service_criteria": "aucun critère dans l'essai de coupe",
        }
    )
    cut = EquilibriumCut(
        value=1.0,
        case="PP",
        reference_level=0.0,
        beam_local_x=(0.0, -1.0, 0.0),
        beam_local_y=(1.0, 0.0, 0.0),
    )
    result = cut_equilibrium(d, infos, summary, summary.families[0], cut)
    # Corps libre Y > 1 (côté −x_l) : P au bras 1 m ; moment de la coupe = P × 1.
    assert result["moment_equilibre_Nm"] == pytest.approx(1000.0)
    assert result["moment_total_section_Nm"] == pytest.approx(mfy)
    assert (result["ecart_relatif"] < 1e-12) is exact
