"""`ExecutionSource` (lot 22, E1): the origin of a fact established by execution.

Covers the three refusals the lot names (a practice entry, a missing field,
a missing case path) plus the guarantees around them (sha256 pin, path kept
inside the repository, deviation recomputed, level limited to C or D). No
Docker, no network: cases are tiny files in `tmp_path`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from aster_expert.agent.drafting import (
    check_execution_source,
    record_code_aster_finding,
    record_execution_finding,
)
from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    DocumentarySource,
    ExecutionSource,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.constats.base import base_dir, load_base, load_resolved_sheet

_ROOT = Path(__file__).resolve().parents[2]
_DIGEST = "sha256:" + "ab" * 32
_COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _case(tmp_path: Path, name: str = "essai/cas.comm") -> tuple[Path, str]:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("DEBUT()\nFIN()\n", encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _fields(sha: str, **overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "aster_version": "17.4.0",
        "image_digest": _DIGEST,
        "repo_commit": _COMMIT,
        "working_tree_modified": True,
        "case_path": "essai/cas.comm",
        "case_sha256": sha,
        "quantity": "flèche en bout",
        "value_obtained": 0.5,
        "reference": "P·L³/(3·E·I)",
        "reference_value": 0.5,
        "relative_deviation": 0.0,
        "validation_level": "D",
    }
    fields.update(overrides)
    return fields


def test_a_complete_source_is_accepted(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)

    source = ExecutionSource(**_fields(sha))

    assert source.validation_level == "D"
    check_execution_source(source, repo_root=tmp_path)


def test_a_practice_entry_refuses_an_execution_source(tmp_path: Path) -> None:
    """M2 kept: `PracticeHypothesisEntry.sources` is typed `PracticeSource`."""
    _, sha = _case(tmp_path)
    source = ExecutionSource(**_fields(sha))

    with pytest.raises(ValidationError):
        PracticeHypothesisEntry(
            topic="t",
            status="tranche",
            option_retained="o",
            justification="j",
            sources=(source,),  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "missing",
    [
        "aster_version",
        "image_digest",
        "repo_commit",
        "case_path",
        "quantity",
        "value_obtained",
        "reference",
        "relative_deviation",
        "validation_level",
    ],
)
def test_a_missing_mandatory_field_is_refused(tmp_path: Path, missing: str) -> None:
    _, sha = _case(tmp_path)
    fields = _fields(sha)
    del fields[missing]

    with pytest.raises(ValidationError):
        ExecutionSource(**fields)


def test_a_nonexistent_case_path_is_refused_when_recording(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)
    source = ExecutionSource(**_fields(sha, case_path="essai/absent.comm"))

    with pytest.raises(ValueError, match="inexistant"):
        record_execution_finding(
            topic="t",
            sources=(source,),
            option_retained="o",
            justification="j",
            repo_root=tmp_path,
        )


def test_a_changed_case_file_is_refused(tmp_path: Path) -> None:
    path, sha = _case(tmp_path)
    source = ExecutionSource(**_fields(sha))
    path.write_text("DEBUT()\nFIN()\n# modifié\n", encoding="utf-8")

    with pytest.raises(ValueError, match="case_sha256"):
        check_execution_source(source, repo_root=tmp_path)


def test_a_missing_mess_copy_is_refused(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)
    source = ExecutionSource(**_fields(sha, mess_path="essai/absent.mess"))

    with pytest.raises(ValueError, match="mess_path inexistant"):
        check_execution_source(source, repo_root=tmp_path)


@pytest.mark.parametrize("bad", ["/etc/passwd", "../cas.comm", "essai//cas.comm", ""])
def test_a_case_path_must_be_relative_and_stay_inside(tmp_path: Path, bad: str) -> None:
    _, sha = _case(tmp_path)

    with pytest.raises(ValidationError):
        ExecutionSource(**_fields(sha, case_path=bad))


def test_a_symbolic_link_leaving_the_repository_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "hors"
    outside.mkdir()
    target = outside / "cas.comm"
    target.write_text("FIN()\n", encoding="utf-8")
    repo = tmp_path / "depot"
    repo.mkdir()
    (repo / "lien.comm").symlink_to(target)
    sha = hashlib.sha256(target.read_bytes()).hexdigest()
    source = ExecutionSource(**_fields(sha, case_path="lien.comm"))

    with pytest.raises(ValueError, match="sort du dépôt"):
        check_execution_source(source, repo_root=repo)


def test_the_deviation_is_recomputed_and_a_slip_refused(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)

    ExecutionSource(
        **_fields(sha, value_obtained=0.55, reference_value=0.5, relative_deviation=0.1)
    )
    with pytest.raises(ValidationError, match="incohérent"):
        ExecutionSource(
            **_fields(
                sha, value_obtained=0.55, reference_value=0.5, relative_deviation=0.2
            )
        )


def test_a_zero_reference_is_refused(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)

    with pytest.raises(ValidationError, match="référence nulle"):
        ExecutionSource(**_fields(sha, reference_value=0.0))


@pytest.mark.parametrize("level", ["A", "B", "E"])
def test_only_levels_c_and_d_are_admitted(tmp_path: Path, level: str) -> None:
    _, sha = _case(tmp_path)

    with pytest.raises(ValidationError):
        ExecutionSource(**_fields(sha, validation_level=level))


@pytest.mark.parametrize(
    "field,value",
    [
        ("image_digest", "sha256:court"),
        ("repo_commit", "abc123"),
        ("case_sha256", "xyz"),
        ("quantity", "  "),
    ],
)
def test_malformed_identifiers_are_refused(
    tmp_path: Path, field: str, value: str
) -> None:
    _, sha = _case(tmp_path)

    with pytest.raises(ValidationError):
        ExecutionSource(**_fields(sha, **{field: value}))


def test_a_finding_needs_at_least_one_execution_source(tmp_path: Path) -> None:
    doc = DocumentarySource(
        document_id="U4.44.01", aster_version="17.4.0", excerpt="un extrait lu"
    )

    with pytest.raises(ValueError, match="au moins une source d'exécution"):
        record_execution_finding(
            topic="t",
            sources=(doc,),
            option_retained="o",
            justification="j",
            repo_root=tmp_path,
        )


def test_a_finding_builds_a_code_aster_tranche_entry(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)
    source = ExecutionSource(**_fields(sha))
    doc = DocumentarySource(
        document_id="U4.44.01", aster_version="17.4.0", excerpt="un extrait lu"
    )

    entry = record_execution_finding(
        topic="t",
        sources=(doc, source),
        option_retained="o",
        justification="j",
        repo_root=tmp_path,
        point_label="8",
    )

    assert isinstance(entry, CodeAsterHypothesisEntry)
    assert entry.status == "tranche" and entry.point_label == "8"
    assert entry.sources == (doc, source)
    # the generic path does not check the filesystem: the difference is stated
    assert record_code_aster_finding(
        topic="t", sources=(source,), option_retained="o", justification="j"
    ).sources == (source,)


def test_an_execution_source_survives_a_json_round_trip(tmp_path: Path) -> None:
    _, sha = _case(tmp_path)
    entry = record_execution_finding(
        topic="t",
        sources=(ExecutionSource(**_fields(sha)),),
        option_retained="o",
        justification="j",
        repo_root=tmp_path,
    )
    sheet = HypothesesSheet(
        project_name="p",
        structure_description="s",
        created_at="2026-09-21T00:00:00",  # type: ignore[arg-type]
        entries=(entry,),
    )

    reloaded = HypothesesSheet.model_validate_json(sheet.model_dump_json())

    assert reloaded == sheet
    assert isinstance(reloaded.entries[0], CodeAsterHypothesisEntry)
    assert isinstance(reloaded.entries[0].sources[0], ExecutionSource)


# --- the shared base of findings (lot 41: the fiche's findings live there) -----

_FICHE = (
    _ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)


def _fiche_execution_sources() -> list[tuple[str, ExecutionSource]]:
    """Every execution source of the shared base (`connaissances/
    constats_code_aster/`), where the 45 findings of the quay's fiche went."""
    base = load_base(base_dir(_ROOT))
    return [
        (c.entry.topic, s)
        for c in base.values()
        for s in c.entry.sources
        if isinstance(s, ExecutionSource)
    ]


def test_every_execution_source_of_the_fiche_points_to_an_existing_case() -> None:
    """The lot's own check: the case path exists in the repository, its bytes
    are the ones pinned, and the versioned listing exists."""
    sources = _fiche_execution_sources()

    assert (
        len(sources) == 94
    )  # 1 + 3 + 6 + 3 + 2 (lot 22) + 5 + 11 + 1 + 3 (lot 23) + 13 (lot 24) + 7 (lot 25)
    # + 7 (lot 35 : 3 + 2 + 1 + 1, constats du lot 34)
    # + 22 (lot 39 : 4 + 5 + 3 + 5 + 2 + 3, CALC_FERRAILLAGE, point 14)
    # + 2 (lot 43 : CA-052, ELS 2D de CALC_FERRAILLAGE, dalle_appuyee_01)
    # + 4 (lot 47 : CA-054 à CA-057, sonde S1 de estacade_pieux_01)
    # + 4 (lot 47 bis : CA-058, sonde S2 de estacade_pieux_01)
    for _, source in sources:
        check_execution_source(source, repo_root=_ROOT)
        assert source.mess_path is not None
        assert source.validation_level in ("C", "D")
        assert source.aster_version == "17.4.0"


def test_every_value_obtained_is_printed_in_its_versioned_listing() -> None:
    """The number recorded in the fiche is the number the run printed."""
    import re

    for topic, source in _fiche_execution_sources():
        assert source.mess_path is not None
        text = (_ROOT / source.mess_path).read_text("utf-8", errors="replace")
        printed = [abs(float(t)) for t in re.findall(r"[-+]?\d\.\d+E[-+]\d+", text)]
        assert any(
            abs(p - abs(source.value_obtained)) <= 1e-9 * abs(source.value_obtained)
            for p in printed
        ), (topic, source.quantity, source.value_obtained)


def test_the_fiche_reports_each_trial_at_its_recorded_deviation() -> None:
    by_quantity = {
        (s.case_path.rsplit("/", 1)[-1], s.quantity[:40]): s
        for _, s in _fiche_execution_sources()
    }

    reactions = {
        case: s.relative_deviation
        for (case, quantity), s in by_quantity.items()
        if quantity.startswith("résultante DZ des réactions REAC_NODA")
    }
    # a1/a6 at 1/12 of the load, a2 at 1/48; a4, a5, a7 exact
    assert reactions["a1.comm"] == pytest.approx(-11 / 12, rel=1e-9)
    assert reactions["a6.comm"] == pytest.approx(-11 / 12, rel=1e-9)
    assert reactions["a2.comm"] == pytest.approx(-47 / 48, rel=1e-9)
    for case in ("a4.comm", "a5.comm", "a7.comm"):
        assert abs(reactions[case]) < 1e-10
    force_coque = [
        s
        for _, s in _fiche_execution_sources()
        if s.case_path.endswith("demi_cylindre.comm")
    ]
    assert len(force_coque) == 1
    assert force_coque[0].value_obtained == pytest.approx(2.22982)
    assert abs(force_coque[0].relative_deviation) < 2e-6


def test_the_fiche_is_valid_json_with_the_execution_fields() -> None:
    sheet = load_resolved_sheet(_FICHE)
    raw = json.loads(sheet.model_dump_json())
    with_execution = [
        e for e in raw["entries"] if any("case_sha256" in s for s in e["sources"])
    ]

    assert {e["point_label"] for e in with_execution} == {
        "1",
        "3",
        "4",
        "5",
        "8",
        "12",
        "14",
    }
    assert all(e["nature"] == "code_aster" for e in with_execution)
