"""Lot 37 : sections « efforts d'ensemble des tubes » et « statique à la cote de
dragage » du document de synthèse (`aster_expert.report.render`)."""

from __future__ import annotations

from typing import Any

from aster_expert.report import render
from aster_expert.report.build import Synthesis, TubeSectionProfile
from aster_expert.report.section_statics import SectionStatics, balance
from aster_expert.report.sections import LevelForces, SectionVector


def _vector(scale: float) -> SectionVector:
    return SectionVector(
        n=-100.0e3 * scale,
        mx=50.0e3 * scale,
        my=0.0,
        tx_nxy=20.0e3 * scale,
        ty_nxy=30.0e3 * scale,
        tx_qx=0.0,
        ty_qx=-5.0e3 * scale,
        mx_wall=0.0,
    )


def _synthesis() -> Synthesis:
    levels = [
        LevelForces(z=z, below=_vector(s), above=_vector(s), mean=_vector(s))
        for z, s in ((2.6, 0.1), (0.0, 1.0), (-11.75, 2.0), (-12.0, 2.1))
    ]
    statics = SectionStatics(
        case="G",
        scope="cellule TUBE_05",
        z=-11.75,
        x_range=(-1.3, 1.3),
        tubes=[5],
        t_y=balance(-720.0e3, -727.0e3),
        m_x=balance(458.0e3, 466.0e3),
        n_z=balance(-437.0e3, -450.0e3),
        measured_parts={},
        external_n={},
        palp_normals_toward_terre=1.0,
    )
    case: Any = type("Case", (), {"case": "G"})()
    return Synthesis.model_construct(
        project="ESSAI",
        cases=[case],
        tube_sections=[
            TubeSectionProfile(
                tube=1, label="TUBE_01", half_tube=True, by_case={"G": levels}
            ),
            TubeSectionProfile(
                tube=5, label="TUBE_05", half_tube=False, by_case={"G": levels}
            ),
        ],
        section_statics=[statics],
        section_check_z=-11.75,
        dredge_z=-12.0,
        level_d=None,
    )


def test_section_forces_are_given_per_tube_with_the_half_tube_flagged() -> None:
    text = "\n".join(render._section_forces_section(_synthesis()))
    assert "### TUBE_01 (demi-tube, plan de symétrie)" in text
    assert "### TUBE_05" in text
    assert "dont NXY" in text and "dont QX" in text
    # cotes du tableau : tête, 0, première rangée au-dessus du dragage, dragage
    for z in ("2.60", "0.00", "-11.75", "-12.00"):
        assert f"| {z} | G |" in text


def test_section_forces_are_absent_without_the_med() -> None:
    synthesis = _synthesis().model_copy(update={"tube_sections": None})
    assert render._section_forces_section(synthesis) == []
    assert (
        render._section_statics_section(
            synthesis.model_copy(update={"section_statics": None})
        )
        == []
    )


def test_statics_section_gives_the_cut_level_and_the_gaps() -> None:
    text = "\n".join(render._section_statics_section(_synthesis()))
    assert "-11.75 m, première rangée au-dessus du dragage (-12 m)" in text
    assert "| G | cellule TUBE_05 | -720.000 | -727.000 | 0.96 % |" in text
    assert "sensible à la discrétisation" in text
