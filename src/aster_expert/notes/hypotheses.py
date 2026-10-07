"""`aster-expert note hypotheses <projet>` (lot 45): the Word note of the hypotheses of
a project, written from its fiche, its data file and its naming convention.

Generic: no section belongs to an ouvrage. The only fixed sentences are the titles and
the labels; every other word comes from the fiche (decisions, sources, dates, deciders,
revisions), from the data file (values, units, sources), from the project declaration
(combinations) or from the shared knowledge base (findings, level, status). A text of
hypothesis is never written here.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from aster_expert.agent.hypotheses import (
    CodeAsterHypothesisEntry,
    FindingReference,
    HypothesesSheet,
    MeshGroupNaming,
    PracticeHypothesisEntry,
    PracticeSource,
)
from aster_expert.agent.model_data import DataValue, ModelData, ValueSource
from aster_expert.combinaisons.enumeration import enumerate_combinations
from aster_expert.connaissances.base import ConstatView, load_knowledge
from aster_expert.notes.docx_style import NoteDocument
from aster_expert.notes.formats import (
    EMPTY,
    fr_date,
    fr_datetime,
    fr_number,
    fr_significant,
)
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import DataRef, Number
from aster_expert.projet.errors import ProjectError

NOTE_NAME = "note_hypotheses.docx"
ORIGIN_LABELS = {
    "norme": "norme",
    "precedent_projet": "précédent de projet",
    "decision_ingenieur": "décision de l'ingénieur",
    "arbitrage_mm": "arbitrage de MM",
    "choix_agent": "choix de l'agent",
}
STATUS_LABELS = {
    "tranche": "décision tranchée",
    "non_tranche": "non tranché",
    "herite": "hérité d'un projet antérieur",
}
POINT_FALLBACK = "sans numéro"


@dataclass(frozen=True)
class Provenance:
    """What the header states about the execution the package describes."""

    aster_version: str
    image_digest: str
    package: dict[str, Any] | None


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo_root: Path) -> str | None:
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return done.stdout.strip() or None if done.returncode == 0 else None


def read_package_manifest(ctx: ProjectContext) -> dict[str, Any] | None:
    """`paquet.json` of the project, if its results package exists."""
    section = ctx.declaration.results_package
    if section is None:
        return None
    path = ctx.results_dir / section.output / "paquet.json"
    if not path.is_file():
        return None
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def provenance_of(ctx: ProjectContext) -> Provenance:
    manifest = read_package_manifest(ctx)
    if manifest is not None:
        aster = manifest.get("code_aster", {})
        version = aster.get("version")
        digest = aster.get("image_digest")
        if version and digest:
            return Provenance(str(version), str(digest), manifest)
    message = (
        "version de Code_Aster et digest de l'image introuvables : aucun paquet de "
        f"résultats pour le projet {ctx.declaration.name} "
        "(`aster-expert projet exporter-resultats`)"
    )
    raise ProjectError(message)


def point_key(label: str | None) -> tuple[int, int, str]:
    """Sort key of a point label: numbers first, in numeric order."""
    if label is None:
        return (2, 0, "")
    digits = "".join(c for c in label if c.isdigit())
    if digits and digits == label:
        return (0, int(digits), "")
    return (1, int(digits) if digits else 0, label)


def point_title(label: str | None) -> str:
    return f"Point {label if label is not None else POINT_FALLBACK}"


# -- sources of a value --------------------------------------------------------------


def _decision_trace(sheet: HypothesesSheet, point: str) -> str:
    entries = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry)
        and e.point_label == point
        and e.status == "tranche"
        and e.decided_at is not None
    ]
    if not entries:
        return ""
    by = sorted({e.decided_by or EMPTY for e in entries})
    # decisions of the fiche mix naive and aware times: compared on the wall clock
    latest = max(
        (e.decided_at for e in entries if e.decided_at is not None),
        key=lambda moment: moment.replace(tzinfo=None),
    )
    return f" ({', '.join(by)}, {fr_date(latest)})"


def source_label(source: ValueSource | None, sheet: HypothesesSheet) -> str:
    if source is None:
        return EMPTY
    if source.kind == "cas_test":
        return f"{source.document}, {source.section}"
    assert source.point_label is not None
    if source.kind == "decision":
        return f"décision du point {source.point_label}" + _decision_trace(
            sheet, source.point_label
        )
    return f"constat du point {source.point_label} ({source.topic_prefix})"


def value_text(value: DataValue) -> str:
    if value.status == "a_fournir":
        return "à fournir"
    if value.profile is not None:
        return f"profil de {len(value.profile)} points (tableau ci-dessous)"
    raw = value.value
    if isinstance(raw, tuple):
        return " ; ".join(fr_number(x) for x in raw)
    if isinstance(raw, int | float):
        return fr_number(raw)
    return "" if raw is None else str(raw)


# -- builders of the sections -------------------------------------------------------


def _split(text: str) -> list[str]:
    return [part for part in text.split("\n") if part.strip()]


def _labelled(note: NoteDocument, label: str, text: str | None) -> None:
    parts = _split(text or "")
    if not parts:
        note.paragraph(EMPTY, label=label)
        return
    note.paragraph(parts[0], label=label)
    for extra in parts[1:]:
        note.paragraph(extra)


def _source_line(source: PracticeSource) -> str:
    text = f"{ORIGIN_LABELS.get(source.origin, source.origin)} — {source.reference}"
    if source.date is not None:
        text += f" ({fr_date(source.date)})"
    return text


def _revision_state(entry: PracticeHypothesisEntry) -> str | None:
    if entry.under_revision:
        event = entry.revision_history[-1]
        return (
            f"en révision depuis le {fr_date(event.at)} ({event.by}) : {event.reason}"
        )
    return None


def render_practice_entry(note: NoteDocument, entry: PracticeHypothesisEntry) -> None:
    """One decision (or open question) of the fiche, field by field."""
    note.paragraph(entry.topic, bold=True)
    note.paragraph(STATUS_LABELS.get(entry.status, entry.status), label="Statut")
    revision = _revision_state(entry)
    if revision is not None:
        note.paragraph(revision, label="Révision")
    if entry.status == "non_tranche":
        if entry.options_considered:
            note.lines("Options considérées", list(entry.options_considered))
        if entry.notes:
            _labelled(note, "Notes", entry.notes)
        return
    _labelled(note, "Option retenue", entry.option_retained)
    _labelled(note, "Justification", entry.justification)
    _labelled(note, "Domaine de validité", entry.validity_domain)
    note.lines(
        "Variantes écartées",
        [f"{v.description} — motif : {v.reason}" for v in entry.discarded_variants]
        or [EMPTY],
    )
    note.lines("Sources", [_source_line(s) for s in entry.sources] or [EMPTY])
    if entry.decided_at is not None:
        note.paragraph(
            f"{entry.decided_by or EMPTY}, le {fr_date(entry.decided_at)}",
            label="Décideur et date",
        )
    if entry.notes:
        _labelled(note, "Notes", entry.notes)


def render_agent_choice(note: NoteDocument, entry: PracticeHypothesisEntry) -> None:
    render_practice_entry(note, entry)
    for source in entry.sources:
        if source.origin != "choix_agent":
            continue
        note.paragraph(source.domain or EMPTY, label="Domaine du choix")
        note.lines("Contrôles qui le vérifient", list(source.verified_by) or [EMPTY])


@dataclass(frozen=True)
class ConstatRow:
    constat_id: str
    point: str | None
    summary: str
    version: str
    level: str
    status: str
    proved_by: str


def constat_rows(
    sheet: HypothesesSheet, repo_root: Path
) -> tuple[list[ConstatRow], list[str]]:
    """The findings the fiche cites, with their level and status in the shared
    knowledge base; the second value lists identifiers the base does not hold."""
    base = load_knowledge(repo_root)
    rows: list[ConstatRow] = []
    missing: list[str] = []
    for entry in sheet.entries:
        if isinstance(entry, FindingReference):
            view: ConstatView | None = base.constats.get(entry.constat_id)
            if view is None:
                missing.append(entry.constat_id)
                continue
            rows.append(
                ConstatRow(
                    entry.constat_id,
                    entry.point_label,
                    view.summary,
                    view.constat.aster_version,
                    view.validation_level,
                    view.status,
                    ", ".join(view.projects) or EMPTY,
                )
            )
    rows.sort(key=lambda r: (point_key(r.point), r.constat_id))
    return rows, missing


def inline_code_aster_entries(sheet: HypothesesSheet) -> list[CodeAsterHypothesisEntry]:
    return [e for e in sheet.entries if isinstance(e, CodeAsterHypothesisEntry)]


def _group_naming_rows(groups: tuple[MeshGroupNaming, ...]) -> list[list[str]]:
    rows = []
    for g in groups:
        rows.append(
            [
                g.group_name,
                "mailles" if g.kind == "maille" else "nœuds",
                g.description,
                g.point_label or EMPTY,
                "choix de l'agent"
                if g.status == "choix_agent"
                else g.status.replace("_", " "),
                ", ".join(g.verified_by) or EMPTY,
            ]
        )
    return rows


def _profile_table(note: NoteDocument, name: str, value: DataValue) -> None:
    assert value.profile is not None
    rows = [
        [
            fr_number(p.z),
            fr_number(p.p),
            p.layer or EMPTY,
            p.component or EMPTY,
        ]
        for p in value.profile
    ]
    note.table(
        ["z", f"p ({value.unit})", "Couche", "Composante"],
        rows,
        widths_cm=[3, 4, 5, 4],
        caption=f"Profil {name} (points z, p)",
    )


def render_data(note: NoteDocument, data: ModelData, sheet: HypothesesSheet) -> None:
    note.paragraph(data.case_reference, label="Référence du cas")
    for group, values in data.groups.items():
        note.heading(f"Groupe de données : {group}", 2)
        rows = [
            [
                key,
                value_text(value),
                value.unit,
                source_label(value.source, sheet),
                value.comment or "",
            ]
            for key, value in values.items()
        ]
        note.table(
            ["Grandeur", "Valeur", "Unité", "Source", "Commentaire"],
            rows,
            widths_cm=[3.4, 3.0, 1.6, 4.0, 5.0],
            caption=f"Données — {group}",
        )
        for key, value in values.items():
            if value.profile is not None:
                _profile_table(note, f"{group}.{key}", value)


def _number_text(ctx: ProjectContext, value: Number) -> str:
    return fr_number(ctx.number(value))


def _reference_text(value: Number) -> str:
    return f"donnée {value.data}" if isinstance(value, DataRef) else "valeur déclarée"


def render_combinations(note: NoteDocument, ctx: ProjectContext) -> bool:
    section = ctx.declaration.combinations
    if section is None:
        return False
    coefficients: list[tuple[str, Number | None]] = [
        ("γG défavorable", section.gamma_g_unfavourable),
        ("γG favorable", section.gamma_g_favourable),
        ("γQ", section.gamma_q),
    ]
    rows = [
        [label, _number_text(ctx, v), _reference_text(v)]
        for label, v in coefficients
        if v is not None
    ]
    note.table(
        ["Coefficient", "Valeur", "Source"],
        rows,
        widths_cm=[5, 3, 9],
        caption="Coefficients partiels",
    )
    psi_rows = [
        [
            v.name,
            _number_text(ctx, v.psi0),
            _number_text(ctx, v.psi1),
            _number_text(ctx, v.psi2),
            _reference_text(v.psi0),
        ]
        for v in section.variables
    ]
    note.table(
        ["Action variable", "ψ0", "ψ1", "ψ2", "Source"],
        psi_rows,
        widths_cm=[4, 2, 2, 2, 7],
        caption="Coefficients de combinaison",
    )
    note.paragraph(", ".join(section.permanent), label="Actions permanentes")
    note.paragraph(
        section.frequent_accompanying.replace("psi", "ψ"),
        label="Coefficient des actions d'accompagnement en ELS fréquent",
    )
    combos = enumerate_combinations(section, ctx.number)
    combo_rows = [
        [
            c.name,
            c.family,
            " ; ".join(
                f"{case} × {fr_number(k)}" for case, k in c.coefficients.items()
            ),
        ]
        for c in combos
    ]
    note.table(
        ["Combinaison", "Famille", "Coefficients par cas"],
        combo_rows,
        widths_cm=[5.5, 3.5, 8],
        caption=f"Combinaisons ({len(combos)})",
    )
    return True


def render_revisions(note: NoteDocument, sheet: HypothesesSheet) -> int:
    """Annex: the former decisions and the revision events of every entry."""
    decisions: list[list[str]] = []
    events: list[list[str]] = []
    for entry in sheet.entries:
        if not isinstance(entry, PracticeHypothesisEntry):
            continue
        point = entry.point_label or POINT_FALLBACK
        for prior in entry.decision_history:
            decisions.append(
                [
                    point,
                    entry.topic,
                    fr_date(prior.decided_at),
                    prior.decided_by,
                    prior.option_retained,
                ]
            )
        for event in entry.revision_history:
            events.append(
                [
                    point,
                    entry.topic,
                    fr_datetime(event.at),
                    event.by,
                    "révision déclarée"
                    if event.kind == "declared"
                    else "révision levée",
                    event.reason,
                ]
            )
    if decisions:
        note.table(
            [
                "Point",
                "Sujet",
                "Date",
                "Décideur",
                "Décision remplacée (option retenue)",
            ],
            decisions,
            widths_cm=[1.3, 4.5, 2.2, 1.8, 7.2],
            caption="Décisions remplacées",
        )
    if events:
        note.table(
            ["Point", "Sujet", "Date", "Par", "Événement", "Motif"],
            events,
            widths_cm=[1.2, 3.6, 2.8, 2.4, 2.0, 5.0],
            caption="Révisions déclarées et levées",
        )
    if not decisions and not events:
        note.paragraph("aucune décision remplacée, aucune révision déclarée")
    return len(decisions) + len(events)


# -- the note ---------------------------------------------------------------------


def build_hypotheses_note(
    ctx: ProjectContext,
    output: Path,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> Path:
    """Write the hypotheses note of the project at `output` and return its path."""
    sheet = HypothesesSheet.model_validate_json(
        ctx.fiche_path.read_text(encoding="utf-8")
    )
    data = ctx.data()
    provenance = provenance_of(ctx)
    declaration = ctx.declaration
    note = NoteDocument(
        title=f"Note d'hypothèses — {declaration.structure}",
        footer=f"Note d'hypothèses {declaration.structure}",
    )
    note.title("Note d'hypothèses", f"{declaration.structure} ({declaration.name})")

    # 1. header ------------------------------------------------------------------
    note.heading("En-tête", 1)
    manifest = provenance.package
    header = [
        ("Ouvrage", declaration.structure),
        ("Projet", declaration.name),
        ("Fiche", sheet.project_name),
        ("Date de génération", fr_date(now())),
        ("Code_Aster", provenance.aster_version),
        ("Digest de l'image", provenance.image_digest),
        ("Empreinte de la fiche (SHA-256)", _sha(ctx.fiche_path)),
        ("Empreinte des données (SHA-256)", _sha(ctx.data_path)),
    ]
    head = _git_head(ctx.repo_root)
    if head is not None:
        header.append(("Commit du dépôt à la génération", head))
    if manifest is not None:
        prints = manifest["empreintes"]
        header += [
            (
                "Empreinte du .comm de l'exécution décrite (SHA-256)",
                prints["comm"]["sha256"],
            ),
            ("Empreinte du maillage (SHA-256)", prints["maillage"]["sha256"]),
            (
                "Empreinte du compte rendu d'exécution (SHA-256)",
                prints["execution"]["compte_rendu_sha256"],
            ),
            (
                "Empreinte de la fiche à l'exportation du paquet (SHA-256)",
                prints["fiche"]["sha256"],
            ),
            (
                "Empreinte des données à l'exportation du paquet (SHA-256)",
                prints["donnees"]["sha256"],
            ),
        ]
    note.key_values(header, headers=("Rubrique", "Valeur"))

    # 2. object and scope ----------------------------------------------------------
    note.heading("Objet et périmètre", 1)
    note.paragraph(sheet.structure_description, label="Ouvrage")
    if declaration.description.strip() != sheet.structure_description.strip():
        note.paragraph(
            " ".join(declaration.description.split()), label="Description du projet"
        )
    practice = [e for e in sheet.entries if isinstance(e, PracticeHypothesisEntry)]
    agent = [e for e in practice if e.is_agent_choice]
    decided = [e for e in practice if e.status == "tranche" and not e.is_agent_choice]
    open_questions = [e for e in practice if e.status == "non_tranche"]
    findings = [e for e in sheet.entries if isinstance(e, FindingReference)]
    inline = inline_code_aster_entries(sheet)
    points = sorted(
        {e.point_label for e in sheet.entries}
        | {g.point_label for g in sheet.group_naming},
        key=point_key,
    )
    scope = [
        ("Points de la fiche", str(len(points))),
        ("Décisions tranchées (hors choix de l'agent)", str(len(decided))),
        ("Choix de l'agent", str(len(agent))),
        ("Questions non tranchées", str(len(open_questions))),
        ("Constats Code_Aster cités", str(len(findings) + len(inline))),
        (
            "Valeurs de données fournies",
            str(sum(1 for v in data.items().values() if v.status == "fourni")),
        ),
        (
            "Valeurs de données à fournir",
            str(sum(1 for v in data.items().values() if v.status == "a_fournir")),
        ),
        ("Groupes nommés", str(len(sheet.group_naming))),
    ]
    note.key_values(scope, headers=("Rubrique", "Nombre"))
    if sheet.planned_commands:
        note.table(
            ["Commande prévue", "Point", "Options", "Couverture"],
            [
                [
                    c.command,
                    c.point_label,
                    "; ".join(f"{k} = {v}" for k, v in c.options.items()) or EMPTY,
                    "; ".join(f"{k} : {v}" for k, v in c.covered_by.items()) or EMPTY,
                ]
                for c in sheet.planned_commands
            ],
            widths_cm=[4, 1.5, 6, 5.5],
            caption="Commandes Code_Aster prévues",
        )

    # 3. data --------------------------------------------------------------------
    note.heading("Données", 1)
    render_data(note, data, sheet)
    if sheet.group_naming:
        note.heading("Convention de nommage des groupes", 2)
        note.table(
            ["Groupe", "Type", "Description", "Point", "Statut", "Contrôle"],
            _group_naming_rows(sheet.group_naming),
            widths_cm=[3.2, 1.6, 5.8, 1.2, 2.4, 2.8],
            caption="Groupes de mailles et de nœuds",
        )

    # 4. points --------------------------------------------------------------------
    note.heading("Points de la fiche", 1)
    by_point: dict[str | None, list[PracticeHypothesisEntry]] = {}
    for entry in practice:
        if not entry.is_agent_choice:
            by_point.setdefault(entry.point_label, []).append(entry)
    cited: dict[str | None, list[str]] = {}
    for finding in findings:
        cited.setdefault(finding.point_label, []).append(finding.constat_id)
    for coded in inline:
        cited.setdefault(coded.point_label, []).append(coded.topic)
    for label in sorted(set(by_point) | set(cited), key=point_key):
        note.heading(point_title(label), 2)
        for entry in by_point.get(label, []):
            render_practice_entry(note, entry)
        if cited.get(label):
            note.paragraph(
                ", ".join(cited[label]),
                label="Constats Code_Aster rattachés (section 5)",
            )
    agent_points = sorted({e.point_label for e in agent}, key=point_key)
    agent_groups = [g for g in sheet.group_naming if g.status == "choix_agent"]
    if agent or agent_groups:
        note.heading("Choix de l'agent", 1)
        for label in agent_points:
            note.heading(point_title(label), 2)
            for entry in (e for e in agent if e.point_label == label):
                render_agent_choice(note, entry)
        if agent_groups:
            note.heading("Noms de groupes choisis par l'agent", 2)
            note.table(
                ["Groupe", "Point", "Contrôle"],
                [
                    [
                        g.group_name,
                        g.point_label or EMPTY,
                        ", ".join(g.verified_by) or EMPTY,
                    ]
                    for g in agent_groups
                ],
                widths_cm=[5, 2, 10],
            )

    # 5. findings ------------------------------------------------------------------
    note.heading("Constats Code_Aster cités", 1)
    rows, missing = constat_rows(sheet, ctx.repo_root)
    if missing:
        message = f"constats cités mais absents de la base : {', '.join(missing)}"
        raise ProjectError(message)
    if rows:
        note.table(
            ["Constat", "Point", "Énoncé", "Version", "Niveau", "Statut"],
            [
                [
                    r.constat_id,
                    r.point or EMPTY,
                    r.summary,
                    r.version,
                    r.level,
                    r.status,
                ]
                for r in rows
            ],
            widths_cm=[1.6, 1.2, 8.4, 1.6, 1.4, 1.8],
            caption=f"Constats cités ({len(rows)})",
        )
    for coded in inline:
        note.paragraph(coded.topic, label="Entrée Code_Aster de la fiche")
    if not rows and not inline:
        note.paragraph("aucun constat cité")

    # 6. combinations --------------------------------------------------------------
    note.heading("Combinaisons et coefficients", 1)
    if not render_combinations(note, ctx):
        note.paragraph("le projet ne déclare pas de combinaisons")

    # annex ------------------------------------------------------------------------
    note.heading("Annexe : historique des révisions", 1)
    render_revisions(note, sheet)

    note.save(output)
    return output


__all__ = [
    "NOTE_NAME",
    "Provenance",
    "build_hypotheses_note",
    "constat_rows",
    "fr_significant",
    "point_key",
    "point_title",
    "provenance_of",
    "read_package_manifest",
    "render_combinations",
    "source_label",
    "value_text",
]
