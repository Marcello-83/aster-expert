"""Base partagée des constats Code_Aster (lot 41, étape 4) : contenu extrait de la
fiche du quai, références de la fiche, recherche, outil MCP, rejeu (exécuteur
factice : aucun Docker)."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    FindingReference,
    HypothesesSheet,
)
from aster_expert.constats.base import (
    ConstatBaseError,
    base_dir,
    build_constat,
    externalize_sheet,
    identifiers,
    load_base,
    load_resolved_sheet,
    resolve_sheet,
    write_constat,
)
from aster_expert.constats.models import Constat, FindingOrigin
from aster_expert.constats.rejeu import ReplayError, replay_base, value_printed
from aster_expert.constats.search import search_constats
from aster_expert.execution.models import ExecutionReport
from aster_expert.mcp.tools import search_constats as search_tool

_ROOT = Path(__file__).resolve().parents[2]
_FICHE = (
    _ROOT
    / "projets"
    / "quai_cw_test_01"
    / "fiche"
    / "hypotheses_combiwall_reference_arbitree.json"
)


def _base() -> dict[str, Constat]:
    return load_base(base_dir(_ROOT))


def test_the_base_holds_the_45_findings_of_the_quay() -> None:
    # Lot 43 : la base porte aussi les constats de la dalle (CA-046 à CA-052,
    # test suivant) ; ceux du quai sont inchangés.
    base = {k: c for k, c in _base().items() if int(k[3:]) <= 45}

    assert list(base) == [f"CA-{n:03d}" for n in range(1, 46)]
    levels = Counter(c.validation_level for c in base.values())
    # 18 constats établis par exécution (12 D, 6 C), 20 par le catalogue, 7 par la
    # seule documentation : les chiffres de l'audit du lot 40 (§ 3.3)
    assert levels == {"D": 12, "C": 6, "B": 20, "A": 7}
    assert {c.aster_version for c in base.values()} == {"17.4.0"}
    assert all(
        c.origin.project.startswith("Exemple de référence") for c in base.values()
    )
    assert sum(len(c.trial_cases) for c in base.values()) == 47
    assert "LIAISON_SOLIDE" in base["CA-008"].keywords
    assert "AFFE_CHAR_MECA" in base["CA-008"].commands


def test_the_slab_adds_seven_findings_of_its_own() -> None:
    """Lot 43 : six constats documentaires externalisés de la fiche de la dalle
    (CA-046 à CA-051) et un constat d'exécution (CA-052, niveau D)."""
    base = {k: c for k, c in _base().items() if int(k[3:]) > 45}

    assert list(base) == [f"CA-{n:03d}" for n in range(46, 53)]
    assert all(c.origin.project == "DALLE-APPUYEE-01" for c in base.values())
    assert base["CA-052"].validation_level == "D"
    assert "CALC_FERRAILLAGE" in base["CA-052"].commands
    assert len(base["CA-052"].trial_cases) == 1


def test_every_trial_case_is_versioned_with_its_bytes() -> None:
    import hashlib

    for constat in _base().values():
        for case in constat.trial_cases:
            path = _ROOT / case.case_path
            assert path.is_file(), case.case_path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == case.case_sha256
            assert case.mess_path is not None
            assert (_ROOT / case.mess_path).is_file()


def test_the_fiche_cites_the_base_and_resolves_to_the_same_sheet() -> None:
    raw = HypothesesSheet.model_validate_json(_FICHE.read_text(encoding="utf-8"))
    resolved = load_resolved_sheet(_FICHE)

    assert len(raw.finding_references()) == 45
    assert not any(isinstance(e, CodeAsterHypothesisEntry) for e in raw.entries)
    assert raw.generation_blockers()[0].startswith(
        "constat référencé non résolu contre la base partagée : CA-001"
    )
    assert resolved.finding_references() == ()
    assert resolved.generation_blockers() == ()
    assert externalize_sheet(resolved, _base()) == raw
    first = next(e for e in resolved.entries if isinstance(e, CodeAsterHypothesisEntry))
    assert first.point_label == "1"


def test_an_entry_that_differs_from_the_base_is_not_externalized() -> None:
    resolved = load_resolved_sheet(_FICHE)
    entries = list(resolved.entries)
    index = next(
        i for i, e in enumerate(entries) if isinstance(e, CodeAsterHypothesisEntry)
    )
    entry = entries[index]
    assert isinstance(entry, CodeAsterHypothesisEntry)
    entries[index] = entry.model_copy(
        update={"notes": (entry.notes or "") + " modifié"}
    )
    changed = resolved.model_copy(update={"entries": tuple(entries)})

    with pytest.raises(ConstatBaseError, match="0 constat"):
        externalize_sheet(changed, _base())


def test_an_unknown_reference_does_not_resolve() -> None:
    sheet = HypothesesSheet(
        project_name="p",
        structure_description="s",
        created_at=datetime(2026, 9, 29, tzinfo=UTC),
        entries=(FindingReference(constat_id="CA-999", point_label="1"),),
    )
    with pytest.raises(ConstatBaseError, match="CA-999"):
        resolve_sheet(sheet, _base())


def test_a_constat_checks_its_derived_fields() -> None:
    constat = _base()["CA-021"]
    data = json.loads(constat.model_dump_json())

    for change, message in (
        ({"summary": "pas de point final"}, "une phrase terminée par un point"),
        ({"summary": "Trois points... ici."}, "points de suspension"),
        ({"validation_level": "A"}, "niveau A déclaré"),
        ({"aster_version": "16.0.0"}, "version 16.0.0 déclarée"),
        ({"constat_id": "X-1"}, "forme CA-nnn"),
        ({"trial_cases": []}, "les cas d'essai ne sont pas ceux"),
    ):
        with pytest.raises(ValueError, match=message):
            Constat.model_validate({**data, **change})
    with pytest.raises(ValueError, match="ne porte pas de point_label"):
        Constat.model_validate({**data, "entry": {**data["entry"], "point_label": "8"}})


def test_identifiers_come_from_the_catalogue_and_the_text() -> None:
    entry = CodeAsterHypothesisEntry(
        topic="Charge FORCE_NODALE sur un nœud",
        status="tranche",
        option_retained="AFFE_CHAR_MECA/FORCE_NODALE avec FX et un mot ABSENT",
        justification="catalogue",
        sources=(
            CatalogueSource(
                command="AFFE_CHAR_MECA",
                aster_version="17.4.0",
                keyword_path=("FORCE_NODALE", "FX"),
            ),
        ),
    )
    commands, keywords = identifiers(
        entry,
        commands={"AFFE_CHAR_MECA", "DEBUT"},
        keywords={"FORCE_NODALE", "FX", "FY"},
    )

    assert commands == ("AFFE_CHAR_MECA",)
    assert keywords == ("FORCE_NODALE", "FX")
    constat = build_constat(
        entry,
        constat_id="CA-900",
        summary="Une force nodale s'écrit par FORCE_NODALE.",
        origin=FindingOrigin(project="p", fiche="f.json", point_label="8"),
        commands={"AFFE_CHAR_MECA"},
        keywords={"FORCE_NODALE", "FX"},
    )
    assert constat.validation_level == "B"
    assert constat.entry.point_label is None


def test_write_and_load_round_trip(tmp_path: Path) -> None:
    constat = _base()["CA-034"]
    write_constat(constat, tmp_path)

    assert load_base(tmp_path) == {"CA-034": constat}
    (tmp_path / "CA-035.json").write_text(
        (tmp_path / "CA-034.json").read_text("utf-8"), encoding="utf-8"
    )
    with pytest.raises(ConstatBaseError, match="porte l'identifiant CA-034"):
        load_base(tmp_path)
    with pytest.raises(ConstatBaseError, match="introuvable"):
        load_base(tmp_path / "absent")


def test_search_by_command_keyword_and_text() -> None:
    base = _base()

    by_command = search_constats(base, command="calc_ferraillage", limit=50)
    assert {h.constat.constat_id for h in by_command} >= {"CA-040", "CA-041", "CA-042"}
    ranks = ["DCBA".index(h.constat.validation_level) for h in by_command]
    assert ranks == sorted(ranks)  # sans texte : les constats éprouvés d'abord

    by_keyword = search_constats(base, keyword="CREA_POI1")
    assert "CA-034" in [h.constat.constat_id for h in by_keyword]

    by_text = search_constats(base, text="évalue aux noeuds pression")
    assert by_text[0].constat.constat_id == "CA-029"
    assert by_text[0].score > 0

    assert search_constats(base, text="mot_introuvable_xyz") == []
    with pytest.raises(ValueError, match="au moins un critère"):
        search_constats(base)
    with pytest.raises(ValueError, match="limit"):
        search_constats(base, text="x", limit=0)


def test_the_mcp_tool_is_logged_and_level_a(tmp_path: Path) -> None:
    log = tmp_path / "log.jsonl"

    result = search_tool(
        project_root=_ROOT, command="AFFE_CHAR_MECA", limit=3, log_path=log
    )

    assert result.validation_level == "A"
    assert result.total_in_base == 52
    assert len(result.results) == 3
    hit = result.results[0]
    assert hit.file.startswith("connaissances/constats_code_aster/CA-")
    assert hit.constat_validation_level in ("A", "B", "C", "D")
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["tool"] == "search_constats"
    assert entry["filters"]["command"] == "AFFE_CHAR_MECA"
    assert [r["identifier"] for r in entry["returned"]] == [
        r.constat_id for r in result.results
    ]


# --- rejeu ------------------------------------------------------------------------


def _fake_runner(tmp_path: Path, printed: str):  # type: ignore[no-untyped-def]
    calls: list[Path] = []

    def run(comm: Path) -> ExecutionReport:
        calls.append(comm)
        work = tmp_path / f"run{len(calls)}"
        work.mkdir()
        mess = work / "fort.6"
        mess.write_text(printed, encoding="utf-8")
        return ExecutionReport(
            comm_path=str(comm),
            aster_version="17.4.0",
            image_digest="sha256:" + "0" * 64,
            status="completed_ok",
            diag="OK",
            return_code=0,
            work_dir=str(work),
            mess_path=str(mess),
            result_files=(),
            duration_s=1.0,
            extracted_by="run_aster.status",
            executed_at=datetime.now(UTC),
        )

    return run, calls


def test_the_replay_finds_the_recorded_values(tmp_path: Path) -> None:
    from aster_expert.agent.hypotheses import ExecutionSource

    values = [
        s.value_obtained
        for s in _base()["CA-020"].entry.sources
        if isinstance(s, ExecutionSource)
    ]
    run, calls = _fake_runner(tmp_path, " ".join(f"{v:.12E}" for v in values) + "\n")

    result = replay_base(
        _ROOT,
        only=("CA-020",),
        output_dir=tmp_path / "rejeu",
        runner=(run, "17.4.0", "sha256:" + "0" * 64),
    )

    assert [c.constat_id for c in result.constats] == ["CA-020"]
    case = next(
        c for c in result.constats[0].cases if c.case_path.endswith("essai_c/c.comm")
    )
    assert case.outcome == "rejoué"
    assert all(s.found for s in case.checks)
    report = json.loads((tmp_path / "rejeu" / "rejeu.json").read_text("utf-8"))
    assert report["constats"][0]["constat_id"] == "CA-020"
    assert (tmp_path / "rejeu" / "rejeu.md").read_text("utf-8").startswith("# Rejeu")
    assert calls


def test_a_value_no_longer_printed_is_flagged(tmp_path: Path) -> None:
    run, _ = _fake_runner(tmp_path, "rien d'imprimé\n")

    result = replay_base(
        _ROOT,
        only=("CA-021",),
        output_dir=tmp_path / "rejeu",
        runner=(run, "17.4.0", "sha256:" + "0" * 64),
    )

    assert not result.all_hold
    assert result.to_review == ["CA-021"]
    assert "CA-021 : à réexaminer" in result.lines()


def test_cases_without_their_mesh_are_reported_not_replayable(tmp_path: Path) -> None:
    # Lot 41 bis: the repository now versions CA-034's mesh and `.export`; the
    # rule is checked on a copy holding the cases alone, as before that lot.
    root = tmp_path / "depot"
    shutil.copytree(base_dir(_ROOT), base_dir(root))
    cases = root / "data" / "examples" / "lot35_constats"
    cases.mkdir(parents=True)
    for comm in sorted((_ROOT / "data/examples/lot35_constats").glob("f2_*.comm")):
        shutil.copy2(comm, cases / comm.name)
    run, calls = _fake_runner(tmp_path, "")

    result = replay_base(
        root,
        only=("CA-034",),
        output_dir=tmp_path / "rejeu",
        runner=(run, "17.4.0", "sha256:" + "0" * 64),
    )

    outcomes = {c.outcome for c in result.constats[0].cases}
    assert outcomes == {"non rejouable"}
    assert result.constats[0].verdict == "non rejouable"
    assert result.to_review == []
    assert not calls


def test_lot41bis_cases_are_replayed_with_their_versioned_mesh(tmp_path: Path) -> None:
    run, calls = _fake_runner(tmp_path, "")

    result = replay_base(
        _ROOT,
        only=("CA-029", "CA-034", "CA-035", "CA-036"),
        output_dir=tmp_path / "rejeu",
        runner=(run, "17.4.0", "sha256:" + "0" * 64),
    )

    assert {c.outcome for r in result.constats for c in r.cases} == {"rejoué"}
    assert len(calls) == 6
    for comm in calls:
        assert comm.with_suffix(".export").is_file()
        assert comm.with_suffix(".mmed").is_file()


def test_unknown_constats_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ReplayError, match="CA-999"):
        replay_base(_ROOT, only=("CA-999",), runner=(lambda p: None, "v", "d"))  # type: ignore[arg-type,return-value]


def test_value_printed_uses_the_criterion_of_the_listings() -> None:
    assert value_printed("x = 2.229820000000E+00", 2.22982)
    assert not value_printed("x = 2.229900000000E+00", 2.22982)
    assert value_printed("0.000000000000E+00", 0.0)
