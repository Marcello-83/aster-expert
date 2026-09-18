"""Human arbitration channel for `pratique` entries (lot 15, amended lot 17).

Lot 14b gave an LLM drafting session exactly two write paths
(`aster_expert.agent.drafting.record_code_aster_finding`/
`record_unfounded_point`), neither able to produce a decided `pratique`
entry -- by design, since deciding engineering practice is never that
session's call. That barrier also left no path at all for a *human*
decision: `PracticeSource` has existed since lot 14 (M1), yet nothing
before this lot ever built a `PracticeHypothesisEntry(status="tranche",
...)`. The combi-wall reference fiche's eight `pratique`/`non_tranche`
entries (`data/examples/hypotheses_combiwall_reference.json`) were
consequently, and permanently, unable to leave that state --
`is_ready_for_generation` could never become true for that fiche, not
because the questions were unanswerable, but because no function in this
project could record an answer.

This module is that path, and mirrors `drafting.py`'s own discipline: one
function builds the decision (`record_practice_decision`), delegating
every safety property -- a source, an option, a justification, a domain of
validity, at least one discarded variant, who decided and when -- to
`PracticeHypothesisEntry`'s own validators (`aster_expert.agent.hypotheses`,
P1/P2, R1) rather than re-checking them here, so hand-building the entry
directly is held to the exact same rules; this function's own signature
adds nothing beyond making the correct call convenient. A second function,
`apply_decision`, is the only way a decided entry is folded back into a
`HypothesesSheet`: it replaces exactly the entry it decided, and refuses
to run when it cannot find that entry unambiguously -- never inserting a
new question. A third, `insert_practice_entry` (R2, lot 17), is the
opposite operation: it folds in a decided entry for a point that has no
`non_tranche` counterpart to replace at all -- the gap lot 16 hit for its
"Objet et périmètre du calcul" entry, which had no place in the fiche to
land (`docs/development-plan.md`, clôture lot 16, Q2). A fourth,
`render_decision_sheet`, turns a sheet's unresolved `pratique` entries
into a document an engineer can arbitrate from, built entirely out of
what the sheet's own `code_aster` entries and the entry's own search
notes already say. It never adds an opinion of its own (CLAUDE.md,
principe 6 : distinguer faits, déductions, recommandations -- this
document carries no recommendation at all).

No arbitration in this module is ever invented by this project itself:
this lot ships the channel, never an answer travelling through it. The
combi-wall fiche stays `is_ready_for_generation=False` at the end of this
lot (see `docs/development-plan.md`, clôture lot 15) -- lot 16's real
attempt to use this channel diagnosed the two gaps closed here (R1's
`validity_domain`, R2's `insert_practice_entry`) but still recorded no
decision of its own; this lot closes the channel's gaps, not lot 16's
nine pending decisions, which are resubmitted separately, against the
field names this module now actually exposes.
"""

from __future__ import annotations

from datetime import datetime

from aster_expert.agent.hypotheses import (
    CatalogueSource,
    CodeAsterHypothesisEntry,
    DiscardedVariant,
    DocumentarySource,
    HypothesesSheet,
    PracticeHypothesisEntry,
    PracticeSource,
    PriorDecision,
)


def record_practice_decision(
    *,
    entry: PracticeHypothesisEntry,
    option_retained: str,
    justification: str,
    validity_domain: str,
    sources: tuple[PracticeSource, ...],
    discarded_variants: tuple[DiscardedVariant, ...],
    decided_by: str,
    decided_at: datetime,
) -> PracticeHypothesisEntry:
    """Arbitrate one `pratique` entry (P1; `validity_domain`, R1 lot 17).

    The only function in this project that can move a `pratique` entry to
    `status="tranche"`. `PracticeHypothesisEntry.sources` accepts nothing
    but `PracticeSource` -- a `CodeAsterSource`/`DocumentarySource`/
    `CatalogueSource` is not a member of that field's type at all (M2, lot
    14), so a documentary Code_Aster source stays structurally impossible
    here, exactly as at lot 14. `sources`, `discarded_variants`,
    `decided_by`, `decided_at` and `validity_domain` are required keyword
    parameters with no default: this function cannot be called into
    producing a decision missing any of them, and `PracticeHypothesisEntry`'s
    own validator (P1/P2, R1) rejects the result again regardless -- the
    guarantee is never this function's alone to keep. `validity_domain`
    states the known limits of this decision (R1) -- distinct from
    `justification` (why the option was retained): lot 16's own diagnostic
    is the reason the two are kept apart rather than merged into one field
    (`docs/development-plan.md`, clôture lot 16, Q1).

    `entry` names the question being decided; its `topic`/`point_label`/
    `options_considered`/`notes` carry over unchanged, only the decision
    itself is new. If `entry` was already `tranche` (a re-arbitration), its
    current decision -- including its `validity_domain` -- is preserved as
    a `PriorDecision` rather than discarded (P2), appended to
    `decision_history`, never edited in place.
    """
    history = entry.decision_history
    if (
        entry.status == "tranche"
        and entry.decided_by is not None
        and entry.decided_at is not None
        and entry.option_retained is not None
        and entry.justification is not None
        and entry.validity_domain is not None
    ):
        history = history + (
            PriorDecision(
                option_retained=entry.option_retained,
                justification=entry.justification,
                validity_domain=entry.validity_domain,
                sources=entry.sources,
                discarded_variants=entry.discarded_variants,
                decided_by=entry.decided_by,
                decided_at=entry.decided_at,
            ),
        )
    return PracticeHypothesisEntry(
        point_label=entry.point_label,
        topic=entry.topic,
        options_considered=entry.options_considered,
        notes=entry.notes,
        option_retained=option_retained,
        justification=justification,
        validity_domain=validity_domain,
        sources=sources,
        discarded_variants=discarded_variants,
        status="tranche",
        decided_by=decided_by,
        decided_at=decided_at,
        decision_history=history,
    )


def apply_decision(
    sheet: HypothesesSheet, decided_entry: PracticeHypothesisEntry
) -> HypothesesSheet:
    """Fold `decided_entry` back into `sheet` (P4), replacing exactly the
    entry it arbitrates.

    Matches by `(point_label, topic)` against the sheet's `pratique`
    entries -- never by position. Raises if no entry matches (this
    function never inserts a new question a typo'd `topic` would
    otherwise smuggle in unvetted) and if more than one does (an ambiguous
    match is refused rather than guessed).
    """
    matches = [
        i
        for i, e in enumerate(sheet.entries)
        if e.nature == "pratique"
        and e.point_label == decided_entry.point_label
        and e.topic == decided_entry.topic
    ]
    if not matches:
        message = (
            "aucune entrée pratique correspondante dans la fiche "
            f"(point_label={decided_entry.point_label!r}, "
            f"topic={decided_entry.topic!r}) -- apply_decision ne crée jamais "
            "de nouvelle question"
        )
        raise ValueError(message)
    if len(matches) > 1:
        message = (
            "plusieurs entrées pratique partagent "
            f"(point_label={decided_entry.point_label!r}, "
            f"topic={decided_entry.topic!r}) -- correspondance ambiguë, refusée"
        )
        raise ValueError(message)
    entries = list(sheet.entries)
    entries[matches[0]] = decided_entry
    return sheet.model_copy(update={"entries": tuple(entries)})


def insert_practice_entry(
    sheet: HypothesesSheet, decided_entry: PracticeHypothesisEntry
) -> HypothesesSheet:
    """Add `decided_entry` to `sheet` as a brand-new entry (R2, lot 17).

    The path `apply_decision` deliberately does not provide: `apply_decision`
    only ever replaces an entry the fiche already carries as `non_tranche`,
    and lot 16 hit a real question with no `non_tranche` counterpart to
    replace at all (its own "Objet et périmètre du calcul", never anticipated
    when the fiche was first drafted -- `docs/development-plan.md`, clôture
    lot 16, Q2). This function is that missing path, held to its own,
    narrower set of guarantees rather than reusing `apply_decision`'s:

    - `decided_entry`'s type is `PracticeHypothesisEntry`, never the
      `HypothesisEntry` union -- a `CodeAsterHypothesisEntry` is not a
      member of this parameter's type at all, so inserting one this way is
      structurally impossible, mirroring M2's own discipline for `sources`.
    - `decided_entry.status` must be `"tranche"`: an entry not yet decided
      has no business entering a fiche through an *insertion* path, which
      by definition adds no `non_tranche` counterpart it could later be
      arbitrated against.
    - No existing `pratique` entry may already share `decided_entry`'s
      `(point_label, topic)` -- symmetric with `apply_decision`'s own
      ambiguity guard, refused rather than silently duplicated.
    """
    if decided_entry.status != "tranche":
        message = (
            "insert_practice_entry n'accepte qu'une entrée pratique déjà "
            f"tranchée (status={decided_entry.status!r} refusé) -- ce chemin "
            "ajoute une décision, jamais une question ouverte"
        )
        raise ValueError(message)
    collisions = [
        e
        for e in sheet.entries
        if e.nature == "pratique"
        and e.point_label == decided_entry.point_label
        and e.topic == decided_entry.topic
    ]
    if collisions:
        message = (
            "une entrée pratique porte déjà "
            f"(point_label={decided_entry.point_label!r}, "
            f"topic={decided_entry.topic!r}) -- insert_practice_entry ne "
            "remplace jamais une entrée existante, voir apply_decision"
        )
        raise ValueError(message)
    return sheet.model_copy(update={"entries": sheet.entries + (decided_entry,)})


def _format_source_reference(source: DocumentarySource | CatalogueSource) -> str:
    if isinstance(source, DocumentarySource):
        if source.section_path:
            section = "/".join(source.section_path)
            return f"{source.document_id} §{section} (v{source.aster_version})"
        return f"{source.document_id} (v{source.aster_version})"
    if source.keyword_path:
        keyword = ".".join(source.keyword_path)
        return f"{source.command} ({keyword}) (v{source.aster_version})"
    return f"{source.command} (v{source.aster_version})"


def _corpus_siblings(
    sheet: HypothesesSheet, entry: PracticeHypothesisEntry
) -> tuple[CodeAsterHypothesisEntry, ...]:
    return tuple(
        e
        for e in sheet.entries
        if isinstance(e, CodeAsterHypothesisEntry)
        and e.point_label == entry.point_label
    )


def render_decision_sheet(sheet: HypothesesSheet) -> str:
    """Render `sheet`'s unresolved `pratique` entries into an arbitrable
    document (P3).

    One section per entry, in `sheet.entries` order -- never reordered or
    ranked by this function. Each section is built only from what `sheet`
    itself already carries: sibling `code_aster`/`tranche` entries sharing
    the same `point_label` supply both "ce que le corpus établit" (their
    own `topic`/`justification`) and "options disponibles au catalogue"
    (their own `option_retained`), each with its source reference; the
    entry's own `notes` supply "cherché et non trouvé" verbatim, since that
    is exactly what a drafting session already recorded there (M5
    correction 4; `aster_expert.agent.drafting.record_unfounded_point`'s
    search trace). Nothing here is invented, ranked, or recommended: a
    point with no established sibling or no catalogue option says so
    explicitly rather than being left blank or filled with a guess.
    """
    unresolved = tuple(
        e for e in sheet.entries if e.nature == "pratique" and e.status == "non_tranche"
    )
    lines = [
        f"# Fiche de décision -- {sheet.project_name}",
        "",
        f"Structure : {sheet.structure_description}",
        f"Version Code_Aster : {sheet.aster_version or 'non renseignée'}",
        "",
        "Ce document rassemble les points que la documentation et le "
        "catalogue Code_Aster indexés ne tranchent pas. Il ne contient "
        "aucune réponse ni recommandation : chaque élément listé "
        "provient tel quel de ce que le corpus établit par ailleurs sur "
        "ce projet, jamais d'un choix fait à la place de l'ingénieur.",
        "",
    ]
    for i, entry in enumerate(unresolved, start=1):
        siblings = _corpus_siblings(sheet, entry)
        established = tuple(s for s in siblings if s.status == "tranche")
        lines += [
            f"## {i}. {entry.topic}",
            "",
            f"*Référence interne : point {entry.point_label or '?'}.*",
            "",
            "### Ce que le corpus établit autour de ce point",
        ]
        if established:
            for s in established:
                refs = ", ".join(_format_source_reference(src) for src in s.sources)
                lines.append(f"- {s.topic} -- {s.justification} ({refs})")
        else:
            lines.append("- Rien de directement établi par le corpus pour ce point.")
        lines += ["", "### Cherché et non trouvé", entry.notes or "Non tracé."]
        lines += ["", "### Options disponibles au catalogue"]
        options = tuple(s for s in established if s.option_retained)
        if options:
            for s in options:
                refs = ", ".join(_format_source_reference(src) for src in s.sources)
                lines.append(f"- {s.option_retained} ({refs})")
        else:
            lines.append("- Aucune option catalogue directement rattachée à ce point.")
        lines.append("")
    return "\n".join(lines)


__all__: list[str] = [
    "apply_decision",
    "insert_practice_entry",
    "record_practice_decision",
    "render_decision_sheet",
]
