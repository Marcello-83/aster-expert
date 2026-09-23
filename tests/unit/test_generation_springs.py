"""Spring stiffness classes (decision 5, point 4; lot 28)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aster_expert.agent.model_data import load_model_data
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.springs import (
    GROUP_PREFIX,
    build_spring_classes,
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
