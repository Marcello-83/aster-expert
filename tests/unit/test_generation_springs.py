"""Spring stiffness classes (decision 5, point 4; lot 28)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.springs import (
    COMBINED_BAND,
    GROUP_PREFIX,
    SpringClass,
    build_spring_classes,
    check_spring_coverage,
    check_spring_sum,
)
from aster_expert.meshing.combiwall import build_params

_ROOT = Path(__file__).resolve().parents[2]
_YAML = _ROOT / "data" / "examples" / "combiwall_model_data.yaml"
_K_H = {"RESS_AV_ARGI": 35.0, "RESS_AV_MARNE": 80.0}


def _params() -> dict[str, object]:
    return build_params(load_model_data(_YAML))


def test_the_invariant_holds_for_both_bands() -> None:
    classes = build_spring_classes(_params(), _K_H)
    check_spring_sum(
        classes,
        band="RESS_AV_ARGI",
        k_h=35.0,
        projected_width_m=20.80,
        projected_height_m=6.00,
    )
    check_spring_sum(
        classes,
        band="RESS_AV_MARNE",
        k_h=80.0,
        projected_width_m=11.36,
        projected_height_m=8.00,
    )


def test_a_broken_invariant_is_refused() -> None:
    classes = build_spring_classes(_params(), _K_H)
    with pytest.raises(GenerationError, match="invariant des ressorts"):
        check_spring_sum(
            classes,
            band="RESS_AV_ARGI",
            k_h=35.0,
            projected_width_m=20.80,
            projected_height_m=6.01,  # wrong height
        )


def test_classes_partition_every_node_without_overlap_or_gap() -> None:
    from aster_expert.meshing.combiwall import spring_node_areas  # noqa: PLC0415

    params = _params()
    classes = build_spring_classes(params, _K_H)
    areas = spring_node_areas(params)
    for band in _K_H:
        from_classes = sorted(n for c in classes if c.band == band for n in c.nodes)
        assert from_classes == sorted(areas[band])


def test_group_names_carry_the_reserved_prefix_and_are_deterministic() -> None:
    classes = build_spring_classes(_params(), _K_H)
    assert all(c.group_name.startswith(GROUP_PREFIX) for c in classes)
    assert len(classes) == len({c.group_name for c in classes})
    again = build_spring_classes(_params(), _K_H)
    assert [c.group_name for c in classes] == [c.group_name for c in again]
    assert [c.stiffness_mn_per_m for c in classes] == [
        c.stiffness_mn_per_m for c in again
    ]


def test_stiffness_classes_are_ordered_by_increasing_value() -> None:
    classes = build_spring_classes(_params(), _K_H)
    for band in _K_H:
        values = [c.stiffness_mn_per_m for c in classes if c.band == band]
        assert values == sorted(values)


def test_si_conversion_is_exact() -> None:
    (one,) = [
        c for c in build_spring_classes(_params(), _K_H) if c.group_name.endswith("01")
    ][:1]
    assert one.stiffness_n_per_m == pytest.approx(one.stiffness_mn_per_m * 1.0e6)


def _shared_nodes(classes: list[SpringClass]) -> set[tuple[float, float, float]]:
    argi = {n for c in classes if c.band == "RESS_AV_ARGI" for n in c.nodes}
    marne = {n for c in classes if c.band == "RESS_AV_MARNE" for n in c.nodes}
    return argi & marne


def test_a_node_shared_by_two_bands_gets_one_common_class_of_summed_stiffness() -> None:
    """`CREA_POI1` ne crée qu'une maille ponctuelle par nœud : sur un nœud partagé
    par deux bandes, la dernière occurrence de `DISCRET` écrase les autres (lot 34,
    constaté nœud par nœud sur le quai réduit : seule la raideur de la marne
    survivait aux 43 nœuds de la limite argile/marne). Chaque nœud partagé doit
    donc être dans une classe commune, de raideur égale à la somme des deux."""
    classes = build_spring_classes(_params(), _K_H)
    shared = _shared_nodes(classes)
    assert shared, "le modèle du quai partage des nœuds entre les deux bandes"
    combined = [c for c in classes if c.band == COMBINED_BAND]
    assert {n for c in combined for n in c.nodes} == shared
    by_node = {n: c for c in combined for n in c.nodes}
    for node in shared:
        parts = [
            c.stiffness_mn_per_m
            for c in classes
            if c.band != COMBINED_BAND and node in c.nodes
        ]
        assert len(parts) == 2
        assert by_node[node].stiffness_mn_per_m == pytest.approx(sum(parts))
    check_spring_coverage(classes)


def test_common_classes_come_last_and_name_their_two_parents() -> None:
    """La règle de surcharge (U4.42.01, U1.03.00) donne le dernier mot à la
    dernière occurrence : les classes communes sont écrites après les classes de
    bande, et leur groupe est l'intersection des groupes de leurs deux parents."""
    classes = build_spring_classes(_params(), _K_H)
    bands = [c.band for c in classes]
    first_combined = bands.index(COMBINED_BAND)
    assert all(b == COMBINED_BAND for b in bands[first_combined:])
    names = {c.group_name for c in classes}
    for c in classes[first_combined:]:
        assert len(c.parents) == 2
        assert set(c.parents) <= names
        assert c.group_name.startswith(GROUP_PREFIX)


def test_common_classes_do_not_enter_a_band_sum() -> None:
    classes = build_spring_classes(_params(), _K_H)
    check_spring_sum(
        classes,
        band="RESS_AV_ARGI",
        k_h=35.0,
        projected_width_m=20.80,
        projected_height_m=6.00,
    )


def test_coverage_refuses_a_shared_node_without_its_common_class() -> None:
    classes = build_spring_classes(_params(), _K_H)
    without = [c for c in classes if c.band != COMBINED_BAND]
    with pytest.raises(GenerationError, match="écraserait"):
        check_spring_coverage(without)


def test_coverage_refuses_a_common_class_of_the_wrong_stiffness() -> None:
    classes = build_spring_classes(_params(), _K_H)
    wrong = [
        c.model_copy(update={"stiffness_mn_per_m": c.stiffness_mn_per_m * 1.01})
        if c.band == COMBINED_BAND
        else c
        for c in classes
    ]
    with pytest.raises(GenerationError, match="écraserait"):
        check_spring_coverage(wrong)


def test_coverage_refuses_a_node_in_two_common_classes() -> None:
    classes = build_spring_classes(_params(), _K_H)
    first = next(c for c in classes if c.band == COMBINED_BAND)
    twin = first.model_copy(update={"group_name": f"{GROUP_PREFIX}RESS_COMM_99"})
    with pytest.raises(GenerationError, match="deux classes communes"):
        check_spring_coverage([*classes, twin])
