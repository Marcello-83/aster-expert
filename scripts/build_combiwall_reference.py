"""Rebuild `data/examples/hypotheses_combiwall_reference_arbitree.json`.

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
   (`lot24_enregistrement.json`), MM having written none.

Usage: python scripts/build_combiwall_reference.py [--output PATH]
"""

from __future__ import annotations

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
    HypothesesSheet,
    HypothesisEntry,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "data" / "examples"
INPUTS = EXAMPLES / "combiwall_inputs"
BASE_PATH = EXAMPLES / "hypotheses_combiwall_reference.json"
DEFAULT_OUTPUT = EXAMPLES / "hypotheses_combiwall_reference_arbitree.json"

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
    (r"ECRAN_POUSSEE", "5"),
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
        decision = {
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
        if e.nature == nature
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
                if e.status == "non_tranche" and e.topic == f["replaces_topic"]
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
            if e.status == "non_tranche" and e.topic == f["replaces_topic"]
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


def build_sheet() -> HypothesesSheet:
    sheet = HypothesesSheet.model_validate_json(BASE_PATH.read_text(encoding="utf-8"))
    sheet = _record_decisions(sheet, INPUTS / "arbitrage_combiwall_MM_v2.md")
    v3 = INPUTS / "arbitrage_combiwall_MM_v3.md"
    sheet = _record_decisions(sheet, v3)
    sheet = sheet.model_copy(update={"group_naming": _group_naming(v3)})
    sheet = _lot20(sheet)
    sheet = _record_decisions(sheet, INPUTS / "arbitrage_combiwall_MM_lot21.md")
    return _lot24(_lot23(_lot22(_lot21(sheet))))


def dump(sheet: HypothesesSheet) -> str:
    return (
        json.dumps(sheet.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    args.output.write_text(dump(build_sheet()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
