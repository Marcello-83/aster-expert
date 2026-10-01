"""Rebuild `projets/quai_cw_test_01/fiche/hypotheses_combiwall_reference_arbitree.json`.

The versioned fiche is produced by replaying, on the unarbitrated
`hypotheses_combiwall_reference.json`, every recorded step (lots 18 to 20),
always through the project's own write paths -- never by editing the JSON:

1. lot 18: MM's v2 decisions (`record_practice_decision` then
   `apply_decision`/`insert_practice_entry`), parsed from
   `combiwall_inputs/arbitrage_combiwall_MM_v2.md`;
2. lot 19: MM's v3 revisions and decision 9 (same functions; the v2 decision
   goes to `decision_history`), the group naming convention, from
   `combiwall_inputs/arbitrage_combiwall_MM_v3.md`;
3. lots 19-20: Code_Aster findings and unfounded points (the three
   placeholders lot 19 recorded are superseded by lot 20's entries and not
   replayed), from
   `combiwall_inputs/lot20_recherche.json` (verbatim excerpts in
   `combiwall_inputs/lot20_extraits.json`), through
   `record_code_aster_finding`/`record_unfounded_point`;
4. lot 21: MM's decision on the tube shell choice (point 1, from
   `combiwall_inputs/arbitrage_combiwall_MM_lot21.md`), and the nodal-spring
   finding that replaces the unfounded surface-stiffness entry of point 4
   (`lot21_recherche.json`, `lot21_extraits.json`); the replaced entry's
   search trace is kept verbatim in the finding's notes;
5. lot 22: findings established by execution (`lot22_essais.json`, cases in
   `data/examples/lot22_essais/` and `fcoque_essai/`), recorded with an
   `ExecutionSource` through `record_execution_finding` -- the case file's
   sha256 and the relative deviation are computed here, never typed; the
   nodal-spring finding of point 4 is replaced by its executed version (the
   former option and notes kept verbatim in the notes); and the entries of
   decisions 2 and 9 are declared « en révision » (`declare_under_revision`)
   because `arbitrage_combiwall_MM_v4.md` still carries `[À CONFIRMER MM]`
   mentions and is therefore not recorded;
6. lot 23: findings on post-processing under ELAS_COQUE (`lot23_essais.json`,
   `lot23_extraits.json`, cases in `data/examples/lot23_essais/`), and MM's v4
   decisions 8 and 9 (`arbitrage_combiwall_MM_v4.md`, whose `[À CONFIRMER MM]`
   passages were removed); decision 2 of v4 is not recorded;
7. lot 24: the generalised-force finding of point 1 extended with the D6 trials
   (`lot24_essais.json`, cases in `data/examples/lot24_essais/`), then MM's v5
   decision 2 (`arbitrage_combiwall_MM_v5_decision2.md`, copied verbatim), which
   closes the revision of point 1; its `decided_at` is the recording time
   (`lot24_enregistrement.json`), MM having written none;
8. lot 25: the D7 finding on the axes of ELAS_COQUE in a vertical plane
   (`lot25_essais.json`, `lot25_extraits.json`, cases in
   `data/examples/lot25_essais/`), and MM's decision on the global frame (point 9,
   `arbitrage_combiwall_MM_lot25_repere.md`, copied verbatim), inserted with
   `insert_practice_entry`; its `decided_at` is the recording time
   (`lot25_enregistrement.json`);
9. lot 27: MM's decision 11 (point 10, part B of
   `donnees_complementaires_combiwall_v1.md`, copied verbatim), inserted with
   `insert_practice_entry`; its `decided_at` is the recording time
   (`lot27_enregistrement.json`). `ECRAN_POUSSEE` is grounded on point 10.
10. lot 28: MM's decision 12 (point 11, `decision12_appui_vertical.md`, copied
    verbatim), inserted with `insert_practice_entry`; its `decided_at` is the
    recording time (`lot28_enregistrement.json`). `PIED_TUBES` (nodes of the
    tubes at Z = -26.00) is added to the group naming convention, grounded on
    point 11.
11. lot 31: the documentary finding on the null-pivot mechanism of
    `LIAISON_SOLIDE` (point 3, `lot31_facts.json`/`lot31_extraits.json`),
    added as a new `code_aster` entry (never replacing the existing point-3
    findings, which cover a different question: syntax, not failure
    mechanism); then the point-3 practice entry ("Choix entre maillage
    coïncident...", decision 4) declared « en révision »
    (`declare_under_revision`, `lot31_enregistrement.json`) -- the decision
    itself is not touched, per this lot's own instructions.
12. lot 32: the point-3 revision closed (`lift_revision`,
    `lot32_enregistrement.json`) once the boundary-condition construction
    rule (étape 1: no dof a `LIAISON_SOLIDE` relation determines is imposed
    directly on more than one node of the tied set) removed the null pivot
    on the reduced quay -- decision 4 itself is not changed, per this lot's
    own instructions.
13. lot 33: MM's decision 13 (point 12, `decision13_poussee_poutre.md`,
    copied verbatim), inserted with `insert_practice_entry`; its `decided_at`
    is the recording time (`lot33_enregistrement.json`). Then the
    `FORCE_POUTRE` code_aster finding (point 12, `lot33_facts.json`/
    `lot33_extraits.json`) the decision's own generation relies on.

14. lot 35: the four `code_aster` findings established by execution at lot 34
    (`lot35_essais.json`): evaluation at the nodes of `FORCE_COQUE/PRES` (point 5,
    REPLACES the "doubling at Z +/- 1 mm is safe" finding, kept in the notes),
    `CREA_POI1` one point cell per node (point 4), the continuous beam with several
    `LIAISON_SOLIDE` (point 12), `REAC_NODA` at tied nodes (point 3). Evidence in
    `data/examples/lot35_constats/` (`projets/quai_cw_test_01/scripts/build_lot35_constats.py`).

15. lot 37: MM's decisions 14 (revision of decision 4, point 3: Timoshenko beam), 15
    and 16 (additions to the validity domain of decisions 7 and 5), recorded as
    worded (`arbitrage_combiwall_MM_lot37.md`, `lot37_enregistrement.json`); then the
    `code_aster` finding that establishes the beam identifier
    (`lot37_facts.json`/`lot37_extraits.json`).

Usage: python projets/quai_cw_test_01/scripts/build_combiwall_reference.py [--output PATH]
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import argparse
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from aster_expert.agent.arbitration import (
    apply_decision,
    declare_under_revision,
    insert_practice_entry,
    lift_revision,
    record_practice_decision,
)
from aster_expert.agent.drafting import (
    SearchAttempt,
    record_code_aster_finding,
    record_execution_finding,
    record_unfounded_point,
)
from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterSource,
    DiscardedVariant,
    DocumentarySource,
    ExecutionSource,
    FindingReference,
    HypothesesSheet,
    HypothesisEntry,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.constats.base import base_dir, externalize_sheet, load_base

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / "projets" / "quai_cw_test_01"
INPUTS = PROJECT / "donnees" / "combiwall_inputs"
BASE_PATH = PROJECT / "fiche" / "hypotheses_combiwall_reference.json"
DEFAULT_OUTPUT = PROJECT / "fiche" / "hypotheses_combiwall_reference_arbitree.json"

_FIELDS = (
    "option_retained",
    "justification",
    "validity_domain",
    "discarded_variants",
    "sources supplémentaires",
)

# point_label of the fiche point that grounds each group (lot 20, step 5).
_GROUP_POINTS: tuple[tuple[str, str], ...] = (
    (r"TUBE_\d+|TUBES|PALP_\d+|PALPS|ECRAN", "1"),
    (r"TIRANT_\d+|TIRANTS|ANC_\d+|ANCRAGES", "2"),
    (r"POUTRE_COUR|TETE_TUBE_\d+", "3"),
    (r"RESS_AV_ARGI|RESS_AV_MARNE", "4"),
    (r"ECRAN_POUSSEE", "10"),
    (r"SYM_G|SYM_D", "7"),
    (r"BOLLARD|DEFENSE", "8"),
)


def _unwrap(block: str) -> str:
    """Join composition line breaks with spaces; keep one line per list item
    or table row."""
    paragraphs = []
    for para in re.split(r"\n\s*\n", block.strip()):
        text = ""
        for i, raw in enumerate(para.split("\n")):
            line = raw.strip()
            if i == 0:
                text = line
            elif re.match(r"(\d+\. |- |\|)", line):
                text += "\n" + line
            else:
                text += " " + line
        paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _collapse(text: str) -> str:
    return " ".join(part.strip() for part in text.split("\n"))


def _fields(section: str) -> dict[str, str]:
    parts = re.split(r"^\*\*(" + "|".join(_FIELDS) + r")\*\*\s*$", section, flags=re.M)
    return {k: v.strip() for k, v in zip(parts[1::2], parts[2::2], strict=True)}


def _variants(block: str) -> tuple[DiscardedVariant, ...]:
    variants = []
    for item in re.split(r"^\d+\. ", block, flags=re.M)[1:]:
        m = re.fullmatch(
            r"\*description\* : (.*?) \*reason\* : (.*)", _collapse(item).strip()
        )
        if m is None:
            message = f"variante écartée illisible : {item!r}"
            raise ValueError(message)
        variants.append(DiscardedVariant(description=m[1], reason=m[2]))
    return tuple(variants)


def _decision_sections(text: str) -> dict[str, str]:
    """Return {"Décision N": body} of an arbitration file."""
    chunks = re.split(r"^## (Décision \d+)(?: — .*)?$", text, flags=re.M)
    return {
        name: re.split(r"^---\s*$", body, flags=re.M)[0]
        for name, body in zip(chunks[1::2], chunks[2::2], strict=True)
    }


def _record_decisions(
    sheet: HypothesesSheet,
    path: Path,
    only: frozenset[str] | None = None,
    decided_at_override: datetime | None = None,
) -> HypothesesSheet:
    """Record the decisions of an arbitration file (all, or the sections in `only`).

    A file that writes no `decided_at` (v5, lot 24) needs `decided_at_override`
    (the recording time, declared in `lot24_enregistrement.json`); its source
    date is then that day, as the file says.
    """
    text = path.read_text(encoding="utf-8")
    common = re.split(r"^## Conventions[^\n]*$", text, maxsplit=1, flags=re.M)[1]
    common = common.split("\n## ")[0]
    decided_by = re.search(r"`decided_by` : `\"(.*?)\"`", common)
    decided_at = re.search(r"`decided_at` : `(\S+?)`", common)
    reference = re.search(r"- `reference` : `\"(.*?)\"`", common, flags=re.S)
    source_date = re.search(r"- `date` : `(\d{4}-\d{2}-\d{2})`", common)
    assert decided_by and reference, path
    if decided_at_override is not None:
        assert decided_at is None and source_date is None, path
        decision_time = decided_at_override
        decision_day = decided_at_override.date()
    else:
        assert decided_at and source_date, path
        decision_time = datetime.fromisoformat(decided_at[1])
        decision_day = date.fromisoformat(source_date[1])
    decision_source = PracticeSource(
        origin="decision_ingenieur",
        reference=_collapse(reference[1]),
        date=decision_day,
    )
    for name, body in _decision_sections(text).items():
        if only is not None and name not in only:
            continue
        head_part, _, rest = body.partition("**option_retained**")
        f = _fields("**option_retained**" + rest)
        point_label = re.search(r"- `point_label` : `\"(.*?)\"`", head_part)
        topic = re.search(r"- `topic` : `\"(.*)\"`\s*$", head_part, flags=re.M)
        assert point_label and topic, name
        sources = [decision_source]
        if "sources supplémentaires" in f:
            norm = re.search(
                r"- `reference` : `\"(.*?)\"`\s*\n- `date`",
                f["sources supplémentaires"],
                flags=re.S,
            )
            assert norm, name
            # The schema's `date` is a full date; the file gives "2009-03", a
            # month: recorded as None, the month stays in `reference` (lot 19).
            sources.append(
                PracticeSource(origin="norme", reference=_collapse(norm[1]), date=None)
            )
        decision: dict[str, Any] = {
            "option_retained": _unwrap(f["option_retained"]),
            "justification": _unwrap(f["justification"]),
            "validity_domain": _unwrap(f["validity_domain"]),
            "sources": tuple(sources),
            "discarded_variants": _variants(f["discarded_variants"]),
            "decided_by": decided_by[1],
            "decided_at": decision_time,
        }
        matches = [
            e
            for e in sheet.entries
            if isinstance(e, PracticeHypothesisEntry)
            and e.point_label == point_label[1]
            and e.topic == topic[1]
        ]
        if matches:
            assert len(matches) == 1, name
            sheet = apply_decision(
                sheet, record_practice_decision(entry=matches[0], **decision)
            )
        else:
            new_point = PracticeHypothesisEntry(
                point_label=point_label[1], topic=topic[1], status="non_tranche"
            )
            sheet = insert_practice_entry(
                sheet, record_practice_decision(entry=new_point, **decision)
            )
    return sheet


def _group_naming(path: Path) -> tuple[MeshGroupNaming, ...]:
    section = path.read_text(encoding="utf-8").split("## Convention de nommage")[1]
    groups: list[MeshGroupNaming] = []
    kind: Any = None
    for line in section.split("\n"):
        if line.startswith("**Groupes de mailles**"):
            kind = "maille"
        elif line.startswith("**Groupes de nœuds**"):
            kind = "noeud"
        elif kind and line.startswith("| `"):
            names_cell, description = (
                c.strip() for c in line.strip("| ").split("|", 1)
            )
            description = description.rstrip("| ").strip()
            span = re.fullmatch(r"`(\w+?)(\d+)` … `\w+?(\d+)`", names_cell)
            if span:
                width = len(span[2])
                names = [
                    f"{span[1]}{i:0{width}d}"
                    for i in range(int(span[2]), int(span[3]) + 1)
                ]
            else:
                names = re.findall(r"`(\w+)`", names_cell)
            for n in names:
                point = next(
                    p for pattern, p in _GROUP_POINTS if re.fullmatch(pattern, n)
                )
                groups.append(
                    MeshGroupNaming(
                        group_name=n,
                        kind=kind,
                        description=description,
                        status="tranche",
                        point_label=point,
                    )
                )
    return tuple(groups)


def _replace(
    sheet: HypothesesSheet,
    *,
    nature: str,
    point_label: str,
    topic: str,
    new: HypothesisEntry,
    status: str = "non_tranche",
) -> HypothesesSheet:
    """Swap the one entry (nature, point_label, topic, status) for `new`."""
    idx = [
        i
        for i, e in enumerate(sheet.entries)
        if not isinstance(e, FindingReference)
        and e.nature == nature
        and e.point_label == point_label
        and e.topic == topic
        and e.status == status
    ]
    if len(idx) != 1:
        message = f"remplacement ambigu ou introuvable : {(nature, point_label, topic)}"
        raise ValueError(message)
    entries = list(sheet.entries)
    entries[idx[0]] = new
    return sheet.model_copy(update={"entries": tuple(entries)})


def _load_extracts(name: str) -> dict[str, Any]:
    return {x["id"]: x for x in json.loads((INPUTS / name).read_text("utf-8"))}


def _documentary(extracts: dict[str, Any], ids: list[str]) -> list[DocumentarySource]:
    return [
        DocumentarySource(
            document_id=extracts[i]["document_id"],
            aster_version=extracts[i]["aster_version"],
            section_path=tuple(extracts[i]["section_path"]),
            source_path=extracts[i]["source_path"],
            source_commit=extracts[i]["source_commit"],
            profile="methode",
            excerpt=extracts[i]["text"],
        )
        for i in ids
    ]


def _finding_sources(
    f: dict[str, Any], cat: dict[str, Any], extracts: dict[str, Any]
) -> tuple[CodeAsterSource, ...]:
    return (
        *_documentary(extracts, f["extraits"]),
        *(
            CatalogueSource(
                command=ref["command"],
                keyword_path=tuple(ref["keyword_path"]),
                aster_version=cat["aster_version"],
                catalogue_source=cat["catalogue_source"],
                catalogue_hash=cat["catalogue_hash"],
                image_digest=cat["image_digest"],
            )
            for ref in f["catalogue_refs"]
        ),
    )


def _lot20(sheet: HypothesesSheet) -> HypothesesSheet:
    research = json.loads((INPUTS / "lot20_recherche.json").read_text("utf-8"))
    extracts = _load_extracts("lot20_extraits.json")
    cat = research["catalogue"]

    for f in research["code_aster_findings"]:
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
        )
        if "replaces_topic" in f:
            replaced = [
                e
                for e in sheet.entries
                if not isinstance(e, FindingReference)
                and e.status == "non_tranche"
                and e.topic == f["replaces_topic"]
            ]
            assert len(replaced) == 1, f["replaces_topic"]
            sheet = _replace(
                sheet,
                nature=replaced[0].nature,
                point_label=replaced[0].point_label or "",
                topic=f["replaces_topic"],
                new=entry,
            )
        else:
            sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})

    def searches(raw: list[dict[str, str]]) -> tuple[SearchAttempt, ...]:
        return tuple(SearchAttempt.model_validate(s) for s in raw)

    for u in research["unfounded_points"]:
        sheet = sheet.model_copy(
            update={
                "entries": (
                    *sheet.entries,
                    record_unfounded_point(
                        point_label=u["point_label"],
                        topic=u["topic"],
                        searches=searches(u["searches"]),
                        deduction=u["deduction"],
                    ),
                )
            }
        )
    ref = research["practice_referral"]
    return sheet.model_copy(
        update={
            "entries": (
                *sheet.entries,
                record_unfounded_point(
                    point_label=ref["point_label"],
                    topic=ref["topic"],
                    searches=searches(ref["searches"]),
                    deduction=ref["deduction"],
                    options_considered=tuple(ref.get("options_considered", ())),
                ),
            )
        }
    )


def _lot21(sheet: HypothesesSheet) -> HypothesesSheet:
    """Replace the unfounded point-4 entry by the nodal-spring finding.

    The finding's notes end with the replaced entry's own notes, verbatim, so
    that the search trace of the former unfounded point is kept.
    """
    research = json.loads((INPUTS / "lot21_recherche.json").read_text("utf-8"))
    extracts = _load_extracts("lot21_extraits.json")
    cat = json.loads((INPUTS / "lot20_recherche.json").read_text("utf-8"))["catalogue"]
    for f in research["code_aster_findings"]:
        replaced = [
            e
            for e in sheet.entries
            if not isinstance(e, FindingReference)
            and e.status == "non_tranche"
            and e.topic == f["replaces_topic"]
        ]
        assert len(replaced) == 1, f["replaces_topic"]
        old = replaced[0]
        history = f"Historique du point non fondé remplacé (lot 20) : {old.notes}"
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f"{f['notes']} {history}",
        )
        sheet = _replace(
            sheet,
            nature=old.nature,
            point_label=old.point_label or "",
            topic=f["replaces_topic"],
            new=entry,
        )
    return sheet


def _execution_source(raw: dict[str, Any], contexts: dict[str, Any]) -> ExecutionSource:
    ctx = contexts[raw["context"]]
    obtained, reference = raw["value_obtained"], raw["reference_value"]
    case_bytes = (ROOT / raw["case_path"]).read_bytes()
    return ExecutionSource(
        aster_version=ctx["aster_version"],
        image_digest=ctx["image_digest"],
        repo_commit=ctx["repo_commit"],
        working_tree_modified=ctx["working_tree_modified"],
        case_path=raw["case_path"],
        case_sha256=hashlib.sha256(case_bytes).hexdigest(),
        mess_path=raw["mess_path"],
        quantity=raw["quantity"],
        value_obtained=obtained,
        reference=raw["reference"],
        reference_value=reference,
        relative_deviation=(obtained - reference) / reference,
        validation_level=raw["validation_level"],
    )


def _lot22(sheet: HypothesesSheet) -> HypothesesSheet:
    """Executed findings, the executed nodal-spring finding, revision flags."""
    data = json.loads((INPUTS / "lot22_essais.json").read_text("utf-8"))
    for f in data["findings"]:
        executions = tuple(_execution_source(x, data["contexts"]) for x in f["sources"])
        if "replaces_topic" not in f:
            entry = record_execution_finding(
                topic=f["topic"],
                sources=executions,
                option_retained=f["option_retained"],
                justification=f["justification"],
                point_label=f["point_label"],
                notes=f["notes"],
                repo_root=ROOT,
            )
            sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
            continue
        replaced = [
            e
            for e in sheet.entries
            if e.nature == "code_aster" and e.topic == f["replaces_topic"]
        ]
        assert len(replaced) == 1, f["replaces_topic"]
        old = replaced[0]
        history = (
            "Historique du constat remplacé (lot 21, niveau A) : option retenue : "
            f"{old.option_retained} Notes : {old.notes}"
        )
        entry = record_execution_finding(
            topic=f["replaces_topic"],
            sources=(*old.sources, *executions),
            option_retained=f["option_retained"],
            justification=f"{old.justification} {f['justification_extra']}",
            point_label=old.point_label,
            notes=f"{f['notes']} {history}",
            repo_root=ROOT,
        )
        sheet = _replace(
            sheet,
            nature="code_aster",
            point_label=old.point_label or "",
            topic=f["replaces_topic"],
            new=entry,
            status="tranche",
        )
    for r in data["revisions"]:
        matches = [
            i
            for i, e in enumerate(sheet.entries)
            if isinstance(e, PracticeHypothesisEntry)
            and e.point_label == r["point_label"]
            and e.topic == r["topic"]
        ]
        assert len(matches) == 1, r["topic"]
        entries = list(sheet.entries)
        target = entries[matches[0]]
        assert isinstance(target, PracticeHypothesisEntry)
        entries[matches[0]] = declare_under_revision(
            target,
            reason=r["reason"],
            declared_by=r["declared_by"],
            declared_at=datetime.fromisoformat(r["declared_at"]),
        )
        sheet = sheet.model_copy(update={"entries": tuple(entries)})
    return sheet


def _apply_findings(
    sheet: HypothesesSheet, data: dict[str, Any], extracts: dict[str, Any]
) -> HypothesesSheet:
    """Record the executed findings of a lot file (lots 23, 24).

    A finding with `replaces_topic` extends the entry of that topic: its sources
    are kept, its former option and notes go to the notes.
    """
    for f in data["findings"]:
        executions = tuple(_execution_source(x, data["contexts"]) for x in f["sources"])
        documents = tuple(_documentary(extracts, f["extraits"]))
        if "replaces_topic" not in f:
            entry = record_execution_finding(
                topic=f["topic"],
                sources=(*documents, *executions),
                option_retained=f["option_retained"],
                justification=f["justification"],
                point_label=f["point_label"],
                notes=f["notes"],
                repo_root=ROOT,
            )
            sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
            continue
        replaced = [
            e
            for e in sheet.entries
            if e.nature == "code_aster" and e.topic == f["replaces_topic"]
        ]
        assert len(replaced) == 1, f["replaces_topic"]
        old = replaced[0]
        history = (
            f"Historique du constat remplacé ({f['history_label']}) : option retenue : "
            f"{old.option_retained} Notes : {old.notes}"
        )
        entry = record_execution_finding(
            topic=f["replaces_topic"],
            sources=(*old.sources, *documents, *executions),
            option_retained=f["option_retained"],
            justification=f"{old.justification} {f['justification_extra']}",
            point_label=old.point_label,
            notes=f"{f['notes']} {history}",
            repo_root=ROOT,
        )
        sheet = _replace(
            sheet,
            nature="code_aster",
            point_label=old.point_label or "",
            topic=f["replaces_topic"],
            new=entry,
            status="tranche",
        )
    return sheet


def _lot23(sheet: HypothesesSheet) -> HypothesesSheet:
    """Post-processing findings under ELAS_COQUE, then MM's v4 decisions 8 and 9.

    Decision 2 of v4 is deliberately not recorded (superseded by v5, lot 24).
    Recording decision 9 closes the revision declared for point 8 at lot 22.
    """
    data = json.loads((INPUTS / "lot23_essais.json").read_text("utf-8"))
    sheet = _apply_findings(sheet, data, _load_extracts("lot23_extraits.json"))
    return _record_decisions(
        sheet,
        INPUTS / "arbitrage_combiwall_MM_v4.md",
        only=frozenset({"Décision 8", "Décision 9"}),
    )


def _lot24(sheet: HypothesesSheet) -> HypothesesSheet:
    """Generalised forces of a full ELAS_COQUE plate (D6), then MM's v5 decision 2.

    Recording decision 2 closes the revision of the entry at point 1. Its
    `decided_at` is the recording time (`lot24_enregistrement.json`): the file
    carries none.
    """
    data = json.loads((INPUTS / "lot24_essais.json").read_text("utf-8"))
    sheet = _apply_findings(sheet, data, {})
    record = json.loads((INPUTS / "lot24_enregistrement.json").read_text("utf-8"))
    return _record_decisions(
        sheet,
        INPUTS / "arbitrage_combiwall_MM_v5_decision2.md",
        decided_at_override=datetime.fromisoformat(
            record["decision_2_v5"]["decided_at"]
        ),
    )


def _lot25(sheet: HypothesesSheet) -> HypothesesSheet:
    """Axes of ELAS_COQUE on a vertical shell (D7), then MM's frame decision (point 9).

    The D7 finding is recorded as a new entry (its criterion failed on one point,
    reported in its notes); the frame decision is recorded as worded.
    """
    data = json.loads((INPUTS / "lot25_essais.json").read_text("utf-8"))
    sheet = _apply_findings(sheet, data, _load_extracts("lot25_extraits.json"))
    record = json.loads((INPUTS / "lot25_enregistrement.json").read_text("utf-8"))
    return _record_decisions(
        sheet,
        INPUTS / "arbitrage_combiwall_MM_lot25_repere.md",
        decided_at_override=datetime.fromisoformat(
            record["decision_repere"]["decided_at"]
        ),
    )


def _record_decision_11(
    sheet: HypothesesSheet, path: Path, decided_at: datetime
) -> HypothesesSheet:
    """Insert decision 11 (part B of the complementary-data file) as worded.

    The part has the fields of an arbitration file, in a header list (`point_label`,
    `topic`, `decided_by`, `sources`) followed by the `**…**` blocks.
    """
    part = path.read_text(encoding="utf-8").split("## Partie B", 1)[1]
    head, _, rest = part.partition("**option_retained**")
    f = _fields("**option_retained**" + rest)
    point_label = re.search(r"- `point_label` : `\"(.*?)\"`", head)
    topic = re.search(r"- `topic` : `\"(.*)\"`\s*$", head, flags=re.M)
    decided_by = re.search(r"- `decided_by` : `\"(.*?)\"`", head)
    reference = re.search(r"avec la référence `\"(.*?)\"`", head, flags=re.S)
    assert point_label and topic and decided_by and reference, path
    entry = PracticeHypothesisEntry(
        point_label=point_label[1], topic=topic[1], status="non_tranche"
    )
    return insert_practice_entry(
        sheet,
        record_practice_decision(
            entry=entry,
            option_retained=_unwrap(f["option_retained"]),
            justification=_unwrap(f["justification"]),
            validity_domain=_unwrap(f["validity_domain"]),
            sources=(
                PracticeSource(
                    origin="decision_ingenieur",
                    reference=_collapse(reference[1]),
                    date=decided_at.date(),
                ),
            ),
            discarded_variants=_variants(f["discarded_variants"]),
            decided_by=decided_by[1],
            decided_at=decided_at,
        ),
    )


def _lot27(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's decision 11 (point 10), recorded as worded; `decided_at` is the
    recording time (`lot27_enregistrement.json`)."""
    record = json.loads((INPUTS / "lot27_enregistrement.json").read_text("utf-8"))
    return _record_decision_11(
        sheet,
        INPUTS / "donnees_complementaires_combiwall_v1.md",
        datetime.fromisoformat(record["decision_11"]["decided_at"]),
    )


def _record_decision_12(
    sheet: HypothesesSheet, path: Path, decided_at: datetime
) -> HypothesesSheet:
    """Insert decision 12 (point 11, vertical support of the screen) as worded.

    The file has the fields of an arbitration file in a header list
    (`point_label`, `topic`, `decided_by`, `sources`) followed by the `**…**`
    blocks -- the same shape as part B of `donnees_complementaires_combiwall_v1.md`
    (lot 27), but its own dedicated file rather than a part of a larger one.
    """
    # The trailing "**Convention de nommage**" paragraph is not one of the
    # decision's own fields (`_FIELDS`) and is handled separately by `_lot28`
    # (the group is added directly, not parsed from this prose).
    text = path.read_text(encoding="utf-8").split("**Convention de nommage**")[0]
    head, _, rest = text.partition("**option_retained**")
    f = _fields("**option_retained**" + rest)
    point_label = re.search(r"- `point_label` : `\"(.*?)\"`", head)
    topic = re.search(r"- `topic` : `\"(.*)\"`\s*$", head, flags=re.M)
    decided_by = re.search(r"- `decided_by` : `\"(.*?)\"`", head)
    reference = re.search(r"la référence `\"(.*?)\"`", head, flags=re.S)
    assert point_label and topic and decided_by and reference, path
    entry = PracticeHypothesisEntry(
        point_label=point_label[1], topic=topic[1], status="non_tranche"
    )
    return insert_practice_entry(
        sheet,
        record_practice_decision(
            entry=entry,
            option_retained=_unwrap(f["option_retained"]),
            justification=_unwrap(f["justification"]),
            validity_domain=_unwrap(f["validity_domain"]),
            sources=(
                PracticeSource(
                    origin="decision_ingenieur",
                    reference=_collapse(reference[1]),
                    date=decided_at.date(),
                ),
            ),
            discarded_variants=_variants(f["discarded_variants"]),
            decided_by=decided_by[1],
            decided_at=decided_at,
        ),
    )


def _lot28_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Étape 2's five code_aster findings (points 2, 3, 5 ×3, 7), from
    `lot28_facts.json` (research) and `lot28_extraits.json` (verbatim excerpts,
    exact byte ranges of `external/codeaster-doc` located via the aster-expert
    MCP tools). Point 8's existing finding (lot 20) is confirmed current
    (identical catalogue_hash/image_digest) and not re-recorded.

    Two findings (points 3 and 5) supersede thin, catalogue-schema-only notes
    that were already present in the *unarbitrated base fiche* (lot 14,
    `source_commit`/`catalogue_hash` null, no verbatim excerpt, no applicability
    check against the target modélisation) -- `replaces_topic`, mirroring
    `_apply_findings`'s pattern: the old finding's own sources are kept, its
    former option and notes go to the notes.
    """
    research = json.loads((INPUTS / "lot28_facts.json").read_text("utf-8"))
    extracts = _load_extracts("lot28_extraits.json")
    cat = research["catalogue"]
    for f in research["code_aster_findings"]:
        sources = _finding_sources(f, cat, extracts)
        if "replaces_topic" not in f:
            entry = record_code_aster_finding(
                topic=f["topic"],
                sources=sources,
                option_retained=f["option_retained"],
                justification=f["justification"],
                point_label=f["point_label"],
                notes=f["notes"],
            )
            sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
            continue
        replaced = [
            e
            for e in sheet.entries
            if e.nature == "code_aster" and e.topic == f["replaces_topic"]
        ]
        assert len(replaced) == 1, f["replaces_topic"]
        old = replaced[0]
        history = (
            "Historique du constat remplacé (fiche de base, lot 14, niveau A, "
            f"sans excerpt ni cas test) : option retenue : {old.option_retained} "
            f"Notes : {old.notes or '(aucune)'}"
        )
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=(*old.sources, *sources),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=old.point_label,
            notes=f"{f['notes']} {history}",
        )
        sheet = _replace(
            sheet,
            nature="code_aster",
            point_label=old.point_label or "",
            topic=f["replaces_topic"],
            new=entry,
            status="tranche",
        )
    return sheet


def _lot28(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's decision 12 (point 11), recorded as worded; `decided_at` is the
    recording time (`lot28_enregistrement.json`). Adds `PIED_TUBES` (nodes of
    the tubes at Z = -26.00) to the group naming convention, on point 11.
    Then Étape 2's five code_aster findings (`_lot28_facts`)."""
    record = json.loads((INPUTS / "lot28_enregistrement.json").read_text("utf-8"))
    sheet = _record_decision_12(
        sheet,
        INPUTS / "decision12_appui_vertical.md",
        datetime.fromisoformat(record["decision_12"]["decided_at"]),
    )
    sheet = sheet.model_copy(
        update={
            "group_naming": (
                *sheet.group_naming,
                MeshGroupNaming(
                    group_name="PIED_TUBES",
                    kind="noeud",
                    description="Nœuds des tubes à Z = -26,00 (pied).",
                    status="tranche",
                    point_label="11",
                ),
            )
        }
    )
    return _lot28_facts(sheet)


def _lot31_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Étape 1's documentary finding on the null-pivot mechanism (point 3),
    from `lot31_facts.json`/`lot31_extraits.json`: a brand-new entry (its own
    topic), never replacing the existing point-3 findings, which answer a
    different question (the syntax of `LIAISON_SOLIDE`, not why it fails)."""
    research = json.loads((INPUTS / "lot31_facts.json").read_text("utf-8"))
    extracts = _load_extracts("lot31_extraits.json")
    cat = research["catalogue"]
    for f in research["code_aster_findings"]:
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
        )
        sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
    return sheet


def _lot31_revision(sheet: HypothesesSheet) -> HypothesesSheet:
    """Declares the point-3 practice entry (decision 4, maillage coïncident /
    `LIAISON_SOLIDE`) « en révision », citing the cause `_lot31_facts` just
    recorded -- the decision itself is not touched (`lot31_enregistrement.json`)."""
    record = json.loads((INPUTS / "lot31_enregistrement.json").read_text("utf-8"))
    r = record["revision"]
    matches = [
        i
        for i, e in enumerate(sheet.entries)
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == r["point_label"]
        and e.topic == r["topic"]
    ]
    assert len(matches) == 1, r["topic"]
    entries = list(sheet.entries)
    target = entries[matches[0]]
    assert isinstance(target, PracticeHypothesisEntry)
    entries[matches[0]] = declare_under_revision(
        target,
        reason=r["reason"],
        declared_by=r["declared_by"],
        declared_at=datetime.fromisoformat(r["declared_at"]),
    )
    return sheet.model_copy(update={"entries": tuple(entries)})


def _lot31(sheet: HypothesesSheet) -> HypothesesSheet:
    """Étape 1's documentary finding (`_lot31_facts`), then the point-3
    revision it grounds (`_lot31_revision`). No decision is taken this lot."""
    return _lot31_revision(_lot31_facts(sheet))


def _lot32(sheet: HypothesesSheet) -> HypothesesSheet:
    """Closes the point-3 revision `_lot31_revision` declared, citing the
    étape 1 correction (`lot32_enregistrement.json`) -- decision 4 itself is
    not touched, per this lot's own instructions."""
    record = json.loads((INPUTS / "lot32_enregistrement.json").read_text("utf-8"))
    r = record["revision"]
    matches = [
        i
        for i, e in enumerate(sheet.entries)
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == r["point_label"]
        and e.topic == r["topic"]
    ]
    assert len(matches) == 1, r["topic"]
    entries = list(sheet.entries)
    target = entries[matches[0]]
    assert isinstance(target, PracticeHypothesisEntry)
    entries[matches[0]] = lift_revision(
        target,
        reason=r["reason"],
        lifted_by=r["lifted_by"],
        lifted_at=datetime.fromisoformat(r["lifted_at"]),
    )
    return sheet.model_copy(update={"entries": tuple(entries)})


def _record_decision_13(
    sheet: HypothesesSheet, path: Path, decided_at: datetime
) -> HypothesesSheet:
    """Insert decision 13 (point 12, poussée/pression d'eau sur la hauteur de
    la poutre de couronnement) as worded -- same header-list shape as
    decisions 11/12 (`_record_decision_11`/`_record_decision_12`), no
    trailing group-naming paragraph to strip."""
    head, _, rest = path.read_text(encoding="utf-8").partition("**option_retained**")
    f = _fields("**option_retained**" + rest)
    point_label = re.search(r"- `point_label` : `\"(.*?)\"`", head)
    topic = re.search(r"- `topic` : `\"(.*)\"`\s*$", head, flags=re.M)
    decided_by = re.search(r"- `decided_by` : `\"(.*?)\"`", head)
    reference = re.search(r"la référence `\"(.*?)\"`", head, flags=re.S)
    assert point_label and topic and decided_by and reference, path
    entry = PracticeHypothesisEntry(
        point_label=point_label[1], topic=topic[1], status="non_tranche"
    )
    return insert_practice_entry(
        sheet,
        record_practice_decision(
            entry=entry,
            option_retained=_unwrap(f["option_retained"]),
            justification=_unwrap(f["justification"]),
            validity_domain=_unwrap(f["validity_domain"]),
            sources=(
                PracticeSource(
                    origin="decision_ingenieur",
                    reference=_collapse(reference[1]),
                    date=decided_at.date(),
                ),
            ),
            discarded_variants=_variants(f["discarded_variants"]),
            decided_by=decided_by[1],
            decided_at=decided_at,
        ),
    )


def _lot33_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Étape 2's own code_aster finding (point 12, `FORCE_POUTRE`):
    `lot33_facts.json`/`lot33_extraits.json`, a brand-new entry (this topic
    has no earlier finding to replace or extend)."""
    research = json.loads((INPUTS / "lot33_facts.json").read_text("utf-8"))
    extracts = _load_extracts("lot33_extraits.json")
    cat = research["catalogue"]
    for f in research["code_aster_findings"]:
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
        )
        sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
    return sheet


def _lot33(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's decision 13 (point 12), recorded as worded; `decided_at` is the
    recording time (`lot33_enregistrement.json`). Then the `FORCE_POUTRE`
    finding (`_lot33_facts`) that decision's own generation relies on."""
    record = json.loads((INPUTS / "lot33_enregistrement.json").read_text("utf-8"))
    sheet = _record_decision_13(
        sheet,
        INPUTS / "decision13_poussee_poutre.md",
        datetime.fromisoformat(record["decision_13"]["decided_at"]),
    )
    return _lot33_facts(sheet)


def _lot35_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Lot 35, étape 1 : les quatre constats `code_aster` établis par exécution au
    lot 34 (`lot35_essais.json`), chacun avec ses sources d'exécution (`.comm`
    archivé octet pour octet et extrait de listing, `data/examples/lot35_constats/`)
    et ses références de catalogue. Trois entrées nouvelles (points 4, 12, 3) ; le
    constat du point 5 (évaluation aux nœuds de `FORCE_COQUE/PRES`) **remplace** celui
    du doublement à Z ± 1 mm, dont l'option et les notes restent dans les `notes` du
    nouveau (historique), ses sources conservées -- même mécanisme que
    `_lot28_facts`."""
    data = json.loads((INPUTS / "lot35_essais.json").read_text("utf-8"))
    cat = data["catalogue"]
    for f in data["findings"]:
        executions = tuple(_execution_source(x, data["contexts"]) for x in f["sources"])
        catalogue = tuple(
            CatalogueSource(
                command=ref["command"],
                keyword_path=tuple(ref["keyword_path"]),
                aster_version=cat["aster_version"],
                catalogue_source=cat["catalogue_source"],
                catalogue_hash=cat["catalogue_hash"],
                image_digest=cat["image_digest"],
            )
            for ref in f["catalogue_refs"]
        )
        if "replaces_topic" not in f:
            entry = record_execution_finding(
                topic=f["topic"],
                sources=(*catalogue, *executions),
                option_retained=f["option_retained"],
                justification=f["justification"],
                point_label=f["point_label"],
                notes=f["notes"],
                repo_root=ROOT,
            )
            sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
            continue
        replaced = [
            e
            for e in sheet.entries
            if e.nature == "code_aster" and e.topic == f["replaces_topic"]
        ]
        assert len(replaced) == 1, f["replaces_topic"]
        old = replaced[0]
        history = (
            "Historique du constat remplacé (lot 28, niveau A avec essai du lot 28) : "
            f"sujet : {old.topic} ; option retenue : {old.option_retained} "
            f"Notes : {old.notes or '(aucune)'}"
        )
        entry = record_execution_finding(
            topic=f["topic"],
            sources=(*old.sources, *catalogue, *executions),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=old.point_label,
            notes=f"{f['notes']} {history}",
            repo_root=ROOT,
        )
        sheet = _replace(
            sheet,
            nature="code_aster",
            point_label=old.point_label or "",
            topic=f["replaces_topic"],
            new=entry,
            status="tranche",
        )
    return sheet


def _lot35(sheet: HypothesesSheet) -> HypothesesSheet:
    return _lot35_facts(sheet)


def _lot37_validity_additions(
    sheet: HypothesesSheet, path: Path, names: tuple[str, ...], decided_at: datetime
) -> HypothesesSheet:
    """Decisions 15 and 16 (lot 37): MM's text is appended, as worded, to the
    `validity_domain` of the entry already decided at that point; every other field
    is carried over, the previous decision goes to `decision_history` (the usual
    re-arbitration of `record_practice_decision`)."""
    text = path.read_text(encoding="utf-8")
    common = re.split(r"^## Conventions[^\n]*$", text, maxsplit=1, flags=re.M)[1]
    common = common.split("\n## ")[0]
    reference = re.search(r"- `reference` : `\"(.*?)\"`", common, flags=re.S)
    assert reference, path
    source = PracticeSource(
        origin="decision_ingenieur",
        reference=_collapse(reference[1]),
        date=decided_at.date(),
    )
    for name, body in _decision_sections(text).items():
        if name not in names:
            continue
        point_label = re.search(r"- `point_label` : `\"(.*?)\"`", body)
        topic = re.search(r"- `topic` : `\"(.*)\"`\s*$", body, flags=re.M)
        assert point_label and topic, name
        quoted = [ln[2:] for ln in body.splitlines() if ln.startswith("> ")]
        assert quoted, name
        addition = _collapse("\n".join(quoted))
        matches = [
            e
            for e in sheet.entries
            if isinstance(e, PracticeHypothesisEntry)
            and e.point_label == point_label[1]
            and e.topic == topic[1]
        ]
        assert len(matches) == 1, name
        old = matches[0]
        assert old.option_retained and old.justification and old.validity_domain
        assert old.decided_by
        sheet = apply_decision(
            sheet,
            record_practice_decision(
                entry=old,
                option_retained=old.option_retained,
                justification=old.justification,
                validity_domain=f"{old.validity_domain}\n\n{addition}",
                sources=(*old.sources, source),
                discarded_variants=old.discarded_variants,
                decided_by=old.decided_by,
                decided_at=decided_at,
            ),
        )
    return sheet


def _lot37_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """The identifier of the Timoshenko beam (point 3), asked for by decision 14, from
    `lot37_facts.json`/`lot37_extraits.json`: a brand-new `code_aster` finding."""
    research = json.loads((INPUTS / "lot37_facts.json").read_text("utf-8"))
    extracts = _load_extracts("lot37_extraits.json")
    cat = research["catalogue"]
    for f in research["code_aster_findings"]:
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
        )
        sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
    return sheet


def _lot37(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's decisions 14 (revision of decision 4, point 3), 15 (validity domain of
    decision 7, point 6) and 16 (validity domain of decision 5, point 4), recorded
    as worded (`arbitrage_combiwall_MM_lot37.md`); `decided_at` is the recording time
    (`lot37_enregistrement.json`). Then the finding that establishes decision 14's
    beam identifier."""
    record = json.loads((INPUTS / "lot37_enregistrement.json").read_text("utf-8"))
    decided_at = datetime.fromisoformat(record["decisions_14_15_16"]["decided_at"])
    path = INPUTS / "arbitrage_combiwall_MM_lot37.md"
    sheet = _record_decisions(
        sheet,
        path,
        only=frozenset({"Décision 14"}),
        decided_at_override=decided_at,
    )
    sheet = _lot37_validity_additions(
        sheet, path, ("Décision 15", "Décision 16"), decided_at
    )
    return _lot37_facts(sheet)


def _variants_v6(fields: dict[str, str], dictated: str) -> tuple[DiscardedVariant, ...]:
    """Variants of a v6 decision: its own field (D14 bis), else those MM dictated."""
    if "discarded_variants" in fields:
        return _variants(fields["discarded_variants"])
    return _variants(dictated)


def _record_decisions_v6(
    sheet: HypothesesSheet, path: Path, decided_at: datetime
) -> HypothesesSheet:
    """Record D14 bis, D17 and D18 of `arbitrage_combiwall_MM_v6.md` as worded.

    The file has its own shape (sections `## D<n> ... `, the reference in the header
    prose, `point_label`/`topic` in the heading or the first lines): D14 bis replaces
    the entry decided by D14 at the same point (`record_practice_decision` keeps the
    previous decision in `decision_history`); D17 and D18 open points 13 and 14.
    """
    text = path.read_text(encoding="utf-8")
    reference = re.search(r"la référence `\"(.*?)\"`", text, flags=re.S)
    assert reference, path
    source = PracticeSource(
        origin="decision_ingenieur",
        reference=_collapse(reference[1]),
        date=decided_at.date(),
    )
    variants_text = (INPUTS / "arbitrage_combiwall_MM_v6_variantes.md").read_text(
        encoding="utf-8"
    )
    parts = re.split(r"^## (D17|D18)\s*$", variants_text, flags=re.M)
    dictated = dict(zip(parts[1::2], parts[2::2], strict=True))
    chunks = re.split(r"^## (D14 bis|D17|D18) — (.*)$", text, flags=re.M)
    for name, title, body in zip(chunks[1::3], chunks[2::3], chunks[3::3], strict=True):
        body = re.split(r"^---\s*$", body, flags=re.M)[0]
        head, _, rest = body.partition("**option_retained**")
        f = _fields("**option_retained**" + rest)
        decision: dict[str, Any] = {
            "option_retained": _unwrap(f["option_retained"]),
            "justification": _unwrap(f["justification"]),
            "validity_domain": _unwrap(f["validity_domain"]),
            "sources": (source,),
            "discarded_variants": _variants_v6(f, dictated.get(name, "")),
            "decided_by": "MM",
            "decided_at": decided_at,
        }
        if name == "D14 bis":
            matches = [
                e
                for e in sheet.entries
                if isinstance(e, PracticeHypothesisEntry)
                and e.point_label == "3"
                and e.topic.startswith("Choix entre maillage coïncident")
            ]
            assert len(matches) == 1, name
            sheet = apply_decision(
                sheet, record_practice_decision(entry=matches[0], **decision)
            )
            continue
        point = re.search(r"point neuf `\"(\d+)\"`", title)
        topic = re.search(r"^`topic` : `\"(.*)\"`\s*$", head, flags=re.M)
        assert point and topic, name
        new_point = PracticeHypothesisEntry(
            point_label=point[1], topic=topic[1], status="non_tranche"
        )
        sheet = insert_practice_entry(
            sheet, record_practice_decision(entry=new_point, **decision)
        )
    return sheet


def _lot38_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Findings of lot 38 (`lot38_facts.json`/`lot38_extraits.json`): the symmetry
    conditions of `POU_D_T` (point 7), then the reinforcement commands (point 14)."""
    research = json.loads((INPUTS / "lot38_facts.json").read_text("utf-8"))
    extracts = _load_extracts("lot38_extraits.json")
    cat = research["catalogue"]
    for f in research["code_aster_findings"]:
        entry = record_code_aster_finding(
            topic=f["topic"],
            sources=_finding_sources(f, cat, extracts),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
        )
        sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
    return sheet


def _lot38(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's D14 bis (complete revision of decision 4, point 3), D17 (point 13) and D18
    (point 14), recorded as worded (`arbitrage_combiwall_MM_v6.md`); `decided_at` is
    the recording time (`lot38_enregistrement.json`)."""
    record = json.loads((INPUTS / "lot38_enregistrement.json").read_text("utf-8"))
    decided_at = datetime.fromisoformat(record["decisions_14bis_17_18"]["decided_at"])
    sheet = _record_decisions_v6(
        sheet, INPUTS / "arbitrage_combiwall_MM_v6.md", decided_at
    )
    return _lot38_facts(sheet)


def _lot39(sheet: HypothesesSheet) -> HypothesesSheet:
    """MM's decision D19 (point 14, position of the longitudinal bars in the section
    calculations), recorded as worded (`arbitrage_combiwall_MM_lot39_D19.md`);
    `decided_at` is the recording time (`lot39_enregistrement.json`). Then the
    findings of step 2 on `CALC_FERRAILLAGE`."""
    record = json.loads((INPUTS / "lot39_enregistrement.json").read_text("utf-8"))
    decided_at = datetime.fromisoformat(record["decision_19"]["decided_at"])
    sheet = _record_decisions(
        sheet,
        INPUTS / "arbitrage_combiwall_MM_lot39_D19.md",
        decided_at_override=decided_at,
    )
    return _lot39_facts(sheet)


def _lot39_facts(sheet: HypothesesSheet) -> HypothesesSheet:
    """Lot 39, step 2: what `CALC_FERRAILLAGE` does and does not do (point 14), six
    findings established by execution (`lot39_essais.json`, generated by
    `projets/quai_cw_test_01/scripts/build_lot39_constats.py`), each with its documentary extracts
    (`lot39_extraits.json`), catalogue references and execution sources."""
    data = json.loads((INPUTS / "lot39_essais.json").read_text("utf-8"))
    extracts = _load_extracts("lot39_extraits.json")
    cat = data["catalogue"]
    for f in data["findings"]:
        executions = tuple(_execution_source(x, data["contexts"]) for x in f["sources"])
        entry = record_execution_finding(
            topic=f["topic"],
            sources=(*_finding_sources(f, cat, extracts), *executions),
            option_retained=f["option_retained"],
            justification=f["justification"],
            point_label=f["point_label"],
            notes=f["notes"],
            repo_root=ROOT,
        )
        sheet = sheet.model_copy(update={"entries": (*sheet.entries, entry)})
    return sheet


def build_sheet() -> HypothesesSheet:
    sheet = HypothesesSheet.model_validate_json(BASE_PATH.read_text(encoding="utf-8"))
    sheet = _record_decisions(sheet, INPUTS / "arbitrage_combiwall_MM_v2.md")
    v3 = INPUTS / "arbitrage_combiwall_MM_v3.md"
    sheet = _record_decisions(sheet, v3)
    sheet = sheet.model_copy(update={"group_naming": _group_naming(v3)})
    sheet = _lot20(sheet)
    sheet = _record_decisions(sheet, INPUTS / "arbitrage_combiwall_MM_lot21.md")
    sheet = _lot21(sheet)
    sheet = _lot22(sheet)
    sheet = _lot23(sheet)
    sheet = _lot24(sheet)
    sheet = _lot25(sheet)
    sheet = _lot27(sheet)
    sheet = _lot28(sheet)
    sheet = _lot31(sheet)
    sheet = _lot32(sheet)
    sheet = _lot33(sheet)
    sheet = _lot35(sheet)
    sheet = _lot37(sheet)
    sheet = _lot38(sheet)
    return _lot39(sheet)


def build(*, externalize: bool = True) -> HypothesesSheet:
    """The fiche as versioned. Lot 41 : chaque constat `code_aster` y est remplacé
    par une référence à la base partagée `connaissances/constats_code_aster/`
    (`aster_expert.constats.base.externalize_sheet`) -- refusé si un constat ne
    s'y trouve pas à l'identique. `externalize=False` rend la fiche complète, d'où
    `extraire_constats_lot41.py` a tiré la base."""
    sheet = build_sheet()
    if not externalize:
        return sheet
    return externalize_sheet(sheet, load_base(base_dir(ROOT)))


def dump(sheet: HypothesesSheet) -> str:
    return (
        json.dumps(sheet.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    args.output.write_text(dump(build()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
