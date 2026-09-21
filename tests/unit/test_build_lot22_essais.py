"""Trial cases of lot 22 (`scripts/build_lot22_essais.py`).

Replays the generator in a temporary directory and compares every file byte
for byte with the versioned ones, checks the meshes against their own
geometry, the analytical references against the generator's constants, and the
versioned listings (`mess/`) against what the fiche says of each run. No
Docker, no network: the executions themselves (level C/D) are reported in
`docs/essais_lot22.md`, not replayed by unit tests.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "build_lot22_essais.py"
_VERSIONED = _ROOT / "data" / "examples" / "lot22_essais"

_spec = importlib.util.spec_from_file_location("build_lot22_essais", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
sys.modules["build_lot22_essais"] = _module
_spec.loader.exec_module(_module)

_CASES = (
    "essai_a/a1",
    "essai_a/a2",
    "essai_a/a3",
    "essai_a/a4",
    "essai_a/a5",
    "essai_a/a6",
    "essai_a/a7",
    "essai_b/b1",
    "essai_b/b2",
    "essai_b/b3",
    "essai_b/b4",
    "essai_c/c",
)
_FAILING = {"b1", "b4"}


def test_replaying_the_generator_reproduces_the_versioned_files(tmp_path: Path) -> None:
    subprocess.run(
        [sys.executable, str(_SCRIPT), "--output-dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    for case in _CASES:
        for suffix in (".mail", ".comm", ".export"):
            name = case + suffix
            assert (tmp_path / name).read_text("utf-8") == (
                _VERSIONED / name
            ).read_text("utf-8"), name
    generated = {
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert generated == {c + s for c in _CASES for s in (".mail", ".comm", ".export")}


def test_the_cases_directory_is_an_allowed_execution_root() -> None:
    config = yaml.safe_load((_ROOT / "config" / "validation.yaml").read_text("utf-8"))

    assert "data/examples/lot22_essais" in config["execution"]["allowed_roots"]


def test_the_strip_mesh_matches_its_geometry() -> None:
    mesh = (_VERSIONED / "essai_a/a1.mail").read_text("utf-8")
    nx, ny = _module.A_NX, _module.A_NY

    assert len(re.findall(r"^N\d+ ", mesh, flags=re.M)) == (nx + 1) * (ny + 1) == 126
    assert len(re.findall(r"^MA\d+ N\d+ N\d+ N\d+ N\d+$", mesh, flags=re.M)) == 100
    # tip edge segments carry their own names: no clash with quadrilateral names
    segs = re.findall(r"^(SG\d+) N\d+ N\d+$", mesh, flags=re.M)
    assert segs == [f"SG{k}" for k in range(1, ny + 1)]
    assert not re.search(r"^MA\d+ N\d+ N\d+$", mesh, flags=re.M)
    xs = {float(x) for x in re.findall(r"^N\d+ ([\d.]+) ", mesh, flags=re.M)}
    assert max(xs) == pytest.approx(_module.A_LENGTH)
    ys = {float(y) for y in re.findall(r"^N\d+ [\d.]+ ([\d.]+) ", mesh, flags=re.M)}
    assert max(ys) == pytest.approx(_module.A_WIDTH)
    for group in ("PLAQUE", "BOUT", "ENCASTR"):
        assert f"\n{group}\n" in mesh


def test_the_three_orientations_and_controls_differ_only_where_intended() -> None:
    a1 = (_VERSIONED / "essai_a/a1.comm").read_text("utf-8")
    a2 = (_VERSIONED / "essai_a/a2.comm").read_text("utf-8")
    a3 = (_VERSIONED / "essai_a/a3.comm").read_text("utf-8")
    a4 = (_VERSIONED / "essai_a/a4.comm").read_text("utf-8")

    assert "ANGL_REP=(0.0, 0.0)" in a1
    assert (
        "VECTEUR=(0.0, 1.0, 0.0)" in a2
        and "ANGL_REP" not in a2.split("CARA =")[1].split("MAT =")[0]
    )
    assert "ANGL_REP=(90.0, 0.0)" in a3
    assert (
        "ELAS_COQUE" in a1
        and "ELAS_COQUE" not in a4.split("MAT =")[1].split("CHMAT")[0]
    )
    # the mandatory group (level-B rule "must be all defined") is complete
    for name in ("CISA_L", "CISA_T", "MEMB_LT", "FLEX_G_LT"):
        assert name in a1


def test_the_analytical_references_recomputed_from_the_generator_constants() -> None:
    p_total = abs(_module.A_LINE_LOAD) * _module.A_WIDTH
    length = _module.A_LENGTH
    ref_l = p_total * length**3 / (3 * _module.A_FLEX["FLEX_L"] * _module.A_WIDTH)
    ref_t = p_total * length**3 / (3 * _module.A_FLEX["FLEX_T"] * _module.A_WIDTH)

    assert ref_l == pytest.approx(0.026666666666667)
    assert ref_t == pytest.approx(0.006666666666667)
    assert ref_l / ref_t == pytest.approx(
        _module.A_FLEX["FLEX_T"] / _module.A_FLEX["FLEX_L"]
    )
    # essai B: the three candidate readings of RHO are distinguishable
    g = _module.B_GRAVITY
    area_mass = _module.B_RHO_SURF * g
    volume_mass = _module.B_RHO_SURF * _module.B_THICK2 * g
    assert (volume_mass, area_mass) == (pytest.approx(19.62), pytest.approx(981.0))
    assert _module.B_RHO_VOL * _module.B_THICK1 * g == pytest.approx(770.085)
    # essai C: uniform displacement p/ks, reaction p x area
    uniform = _module.C_PRESSURE / _module.C_KS
    assert uniform == pytest.approx(1.0e-3)


def test_the_isotropic_sets_satisfy_the_relation_the_reaction_control_tests() -> None:
    """FLEX = MEMB x h^2 / 12 for a5, and not for a1/a6 (see the essay report)."""
    h = 0.01
    iso = _module._ISO_MATERIAL
    a_set = _module.A_MATERIAL

    assert iso["MEMB_L"] * h**2 / 12 == pytest.approx(iso["FLEX_L"])
    assert a_set["MEMB_L"] * h**2 / 12 == pytest.approx(1000.0 / 12)
    # 3 D_eff b / L^3 = 15.625, the coefficient observed in a1, a2, a6
    assert 3 * (
        a_set["MEMB_L"] * h**2 / 12
    ) * _module.A_WIDTH / _module.A_LENGTH**3 == (pytest.approx(15.625))


def test_the_plate_meshes_hold_two_plates_and_three_stiffness_classes() -> None:
    plates = (_VERSIONED / "essai_b/b2.mail").read_text("utf-8")
    springs = (_VERSIONED / "essai_c/c.mail").read_text("utf-8")

    assert len(re.findall(r"^MA\d+ N\d+ N\d+ N\d+ N\d+$", plates, flags=re.M)) == 32
    for group in ("P1", "P2", "APP1", "APP2"):
        assert f"\n{group}\n" in plates
    classes = _module.c_classes()
    assert {name: len(members) for name, (_, members) in classes.items()} == {
        "COIN": 4,
        "BORD": 12,
        "INT": 9,
    }
    assert {name: k for name, (k, _) in classes.items()} == {
        "COIN": pytest.approx(15625.0),
        "BORD": pytest.approx(31250.0),
        "INT": pytest.approx(62500.0),
    }
    total = sum(k * len(members) for k, members in classes.values())
    assert total == pytest.approx(_module.C_KS * 1.0)  # ks x area
    for group in ("PLAQUE", "INT", "BORD", "COIN", "TOUS"):
        assert f"\n{group}\n" in springs


def test_the_c_case_declares_one_poi1_group_per_class_not_per_node() -> None:
    comm = (_VERSIONED / "essai_c/c.comm").read_text("utf-8")

    assert comm.count("NOM_GROUP_MA=") == 3
    assert comm.count('CARA="K_T_D_N"') == 3
    for k in ("62500.0", "31250.0", "15625.0"):
        assert f"(0.0, 0.0, {k})" in comm


@pytest.mark.parametrize("case", _CASES)
def test_the_versioned_listing_of_each_run_says_what_the_report_says(case: str) -> None:
    name = case.split("/")[1]
    text = (_VERSIONED / "mess" / f"mess_{name}.txt").read_text(
        "utf-8", errors="replace"
    )

    assert "aucune alarme" in text and "<A>" not in text
    if name in _FAILING:
        assert "DIAGNOSTIC JOB : <S>_ERROR" in text
        assert "MODELISA9_77" in text and "Le paramètre 'RHO' doit être fourni" in text
    else:
        assert "DIAGNOSTIC JOB : OK" in text
        assert 'ARRET NORMAL DANS "FIN"' in text
        assert "<EXCEPTION>" not in text


def test_the_versioned_listing_of_b4_shows_pesanteur_limited_to_the_elas_plate() -> (
    None
):
    comm = (_VERSIONED / "essai_b/b4.comm").read_text("utf-8")
    listing = (_VERSIONED / "mess" / "mess_b4.txt").read_text("utf-8", errors="replace")

    assert 'PESANTEUR=_F(GROUP_MA="P1", GRAVITE=9.81' in comm
    assert "RHO" not in comm.split("MAT2 =")[1].split("CHMAT")[0]
    assert "GROUP_MA='P1'" in listing
