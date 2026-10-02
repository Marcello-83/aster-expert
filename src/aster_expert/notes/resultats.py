"""`aster-expert note resultats <projet>` (lot 45): the Word note of the results of a
project, written from its results package alone (`projets/<nom>/resultats/paquet/`).

Nothing is recomputed and nothing is read from an execution archive: every value is a
value of a file of the package, or of the fiche for the limits of the decisions. The
sections shown depend on what the package holds and on what `projet.yaml` declares
(`results_package`: sections of the items, tables and figures of the note), never on
the name of the project. No verdict of conformity of the ouvrage is ever written: the
levels reached, the controls and the open anomalies are stated as they are.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from aster_expert.agent.hypotheses import (
    FindingReference,
    HypothesesSheet,
    PracticeHypothesisEntry,
)
from aster_expert.connaissances.base import load_anomalies
from aster_expert.notes.docx_style import NoteDocument
from aster_expert.notes.ferraillage_notes import (
    is_beam,
    is_plate,
    render_beam,
    render_generic_json,
    render_plate,
)
from aster_expert.notes.formats import EMPTY, cell, fr_date, fr_datetime
from aster_expert.notes.hypotheses import point_key, read_package_manifest
from aster_expert.notes.tables import resolve_table, table_note
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.declaration import ResultsPackageSection
from aster_expert.projet.errors import ProjectError

NOTE_NAME = "note_resultats.docx"
LEVELS = (
    ("A", "réponse documentaire, non exécutée"),
    ("B", "syntaxe confrontée au catalogue de la version cible"),
    ("C", "fichier exécuté jusqu'à FIN"),
    ("D", "résultats soumis à des contrôles physiques"),
    ("E", "résultats comparés à une référence validée"),
)
SECTION_ORDER = ("controles", "niveau_e", "cas", "combinaisons", "ferraillage")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _yes(flag: object) -> str:
    return "oui" if flag else "non"


def _short(sha: str | None, size: int = 12) -> str:
    return EMPTY if not sha else sha[:size]


class Package:
    """The results package of a project, as the note reads it."""

    def __init__(self, ctx: ProjectContext) -> None:
        declared = ctx.declaration.results_package
        manifest = read_package_manifest(ctx)
        if declared is None or manifest is None:
            message = (
                f"le projet {ctx.declaration.name} n'a pas de paquet de résultats "
                "(`aster-expert projet exporter-resultats`)"
            )
            raise ProjectError(message)
        self.ctx = ctx
        self.declared: ResultsPackageSection = declared
        self.manifest: dict[str, Any] = manifest
        self.directory = ctx.results_dir / declared.output

    def files(self, section: str, suffix: str | None = None) -> list[dict[str, Any]]:
        return [
            f
            for f in self.manifest["fichiers"]
            if f["section"] == section
            and (suffix is None or f["chemin"].lower().endswith(suffix))
        ]

    def json(self, relative: str) -> Any:
        return _read_json(self.directory / relative)

    def sections(self) -> set[str]:
        shown = set(self.manifest["sections"])
        shown |= {t.section for t in self.declared.note_tables}
        shown |= {f.section for f in self.declared.note_figures}
        if self.declared.level_e is not None:
            shown.add("niveau_e")
        return shown


# -- 1. traceability and level -----------------------------------------------------


def render_traceability(note: NoteDocument, package: Package, now: datetime) -> None:
    manifest = package.manifest
    ctx = package.ctx
    prints = manifest["empreintes"]
    execution = prints["execution"]
    current_fiche = _sha_of(ctx.fiche_path)
    current_data = _sha_of(ctx.data_path)

    def compare(recorded: str, current: str, what: str) -> str:
        if recorded == current:
            return f"{recorded} (identique à l'actuelle)"
        return f"{recorded} ; {what} actuelle diffère : {current}"

    note.heading("Traçabilité", 2)
    rows = [
        ("Ouvrage", manifest["ouvrage"]),
        ("Projet", manifest["projet"]),
        ("Note générée le", fr_date(now)),
        ("Paquet exporté le", manifest["exporte_le"]),
        (
            "Dépôt à l'exportation",
            f"{manifest['depot']['commit']} (arbre modifié : "
            f"{_yes(manifest['depot']['arbre_modifie'])})",
        ),
        ("Code_Aster", manifest["code_aster"]["version"]),
        ("Digest de l'image", manifest["code_aster"]["image_digest"]),
        (
            "Fiche (SHA-256 à l'exportation)",
            compare(prints["fiche"]["sha256"], current_fiche, "la fiche"),
        ),
        (
            "Données (SHA-256 à l'exportation)",
            compare(
                prints["donnees"]["sha256"], current_data, "la version des données"
            ),
        ),
        ("Fichier de commandes (SHA-256)", prints["comm"]["sha256"]),
        ("Maillage (SHA-256)", prints["maillage"]["sha256"]),
        (
            "Exécution",
            f"{execution['statut']} ({execution['diagnostic']}), "
            f"{cell(execution['duree_s'])} s, le {execution['execute_le']}",
        ),
        ("Listing .mess (SHA-256)", execution["mess_sha256"] or EMPTY),
        (
            "Contenu du paquet",
            f"{len(manifest['fichiers'])} fichiers, {manifest['taille_octets']} octets "
            f"(plafond {manifest['plafond_octets']})",
        ),
    ]
    note.key_values(rows, headers=("Rubrique", "Valeur"))
    note.table(
        ["Cohérence entre les empreintes", "Tenue"],
        [[c["controle"], _yes(c["ok"])] for c in manifest["coherence"]],
        widths_cm=[13, 4],
    )
    regeneration = manifest["regeneration_comm"]
    text = regeneration["statut"]
    if regeneration["statut"] == "different":
        decisive = regeneration.get("identique_hors_commentaires")
        text += (
            " ; ne diffère que par des commentaires ou l'en-tête"
            if decisive
            else " ; diffère hors commentaires"
            if decisive is False
            else " ; différence tronquée, non décidable"
        )
    note.paragraph(text, label="Régénération du .comm depuis la fiche et les données")
    if regeneration.get("difference"):
        note.lines("Lignes de différence", list(regeneration["difference"]))


def _sha_of(path: Path) -> str:
    import hashlib  # noqa: PLC0415

    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_level(note: NoteDocument, package: Package) -> None:
    level = package.manifest["niveau"]
    note.heading("Niveau de validation atteint", 2)
    reached = level["atteint"] or "aucun"
    note.paragraph(reached, label="Niveau atteint", bold=True)
    not_reached = [s for s in level["par_niveau"] if not s["atteint"]]
    if not_reached:
        first = not_reached[0]
        note.paragraph(
            f"niveau {first['niveau']} non atteint : {first['motif']}",
            label="Premier niveau non atteint",
        )
    note.table(
        ["Niveau", "Atteint", "Motif"],
        [[s["niveau"], _yes(s["atteint"]), s["motif"]] for s in level["par_niveau"]],
        widths_cm=[1.8, 1.8, 13.4],
        caption="Niveaux de B à E (chacun suppose les précédents atteints)",
    )
    conservation = level.get("conservation")
    if conservation is not None:
        note.paragraph(conservation["motif"], label="Conservation des niveaux")
    note.paragraph(level["regle_de_conservation"], label="Règle")
    note.table(
        ["Niveau", "Signification"],
        [[k, v] for k, v in LEVELS],
        widths_cm=[1.8, 15.2],
        caption="Échelle des niveaux de validation",
    )
    validation = package.directory / "validation" / "validation.json"
    if validation.is_file():
        data = _read_json(validation)
        note.paragraph(
            f"{len(data.get('commands_checked', []))} commandes confrontées au "
            f"catalogue de {data.get('aster_version')}, "
            f"{len(data.get('errors', []))} erreur(s), "
            f"{len(data.get('warnings', []))} avertissement(s)",
            label="Validation de niveau B",
        )
    report = package.directory / "maillage" / "rapport_mesh_check.txt"
    if report.is_file():
        lines = [
            x for x in report.read_text(encoding="utf-8").splitlines() if x.strip()
        ]
        note.paragraph(" — ".join(lines[:2]), label="Contrôle du maillage")
    execution = package.directory / "execution" / "compte_rendu.json"
    if execution.is_file():
        record = _read_json(execution)
        alarms = record.get("alarms_by_identifier", {})
        note.paragraph(
            f"{sum(alarms.values()) if alarms else 0} alarme(s), "
            f"{len(record.get('errors', []))} erreur(s) relevée(s) dans le .mess",
            label="Alarmes et erreurs de l'exécution",
        )


# -- 2. controls -------------------------------------------------------------------


def render_criteria(note: NoteDocument, package: Package) -> None:
    criteria = package.manifest["criteres"]
    note.heading("Critères écrits avant l'exécution", 2)
    if not criteria:
        note.paragraph("aucun document de critères déclaré")
        return
    note.table(
        [
            "Niveau",
            "Document",
            "Commit d'introduction",
            "Date",
            "Antériorité démontrable",
        ],
        [
            [
                c["niveau"],
                c["document"],
                _short(c.get("commit_introduction")),
                c.get("date") or EMPTY,
                _yes(c.get("anteriorite_demontrable")),
            ]
            for c in criteria
        ],
        widths_cm=[1.8, 5, 3.2, 4.4, 2.6],
        caption="Documents de critères, commit qui les a introduits",
    )
    weak = [c for c in criteria if not c.get("anteriorite_demontrable", False)]
    if weak:
        note.paragraph(_priority_sentence(weak), label="Antériorité")
        note.table(
            ["Document", "Motif relevé par le paquet"],
            [[c["document"], c["anteriorite_motif"]] for c in weak],
            widths_cm=[5, 12],
        )


def _priority_sentence(weak: list[dict[str, Any]]) -> str:
    """« critères des lots 34, 37 et 39 (documents ...) commités avec les résultats,
    antériorité non démontrable »: built from the flags of the package."""
    numbers: list[str] = []
    for c in weak:
        lot = _lot_of(c.get("message"))
        numbers.append(lot.split()[-1] if lot != EMPTY else "")
    documents = ", ".join(c["document"] for c in weak)
    if all(numbers):
        unique = list(dict.fromkeys(numbers))
        names = (
            ", ".join(unique[:-1]) + f" et {unique[-1]}"
            if len(unique) > 1
            else unique[0]
        )
        who = f"critères des lots {names} (documents {documents})"
    else:
        who = f"critères des documents {documents}"
    how = []
    if any("avec des résultats d'exécution" in c["anteriorite_motif"] for c in weak):
        how.append("commités avec les résultats")
    if any("après l'exécution" in c["anteriorite_motif"] for c in weak):
        how.append("commités après l'exécution")
    if not how:
        how.append("dont l'ordre d'écriture n'est pas démontré par l'historique")
    return f"{who} {' et '.join(how)}, antériorité non démontrable"


def _lot_of(message: str | None) -> str:
    """`Lot 34` from a commit message `Lot 34 : ...`, else the empty mark."""
    if message and message.lower().startswith("lot "):
        return " ".join(message.split(":")[0].split()[:2])
    return EMPTY


def render_controls_d(note: NoteDocument, package: Package) -> None:
    path = package.directory / "controles" / "controles_d.json"
    if not path.is_file():
        return
    data = _read_json(path)
    note.heading("Contrôles de niveau D", 2)
    note.paragraph(
        f"seuil relatif {cell(data['threshold'])} ; "
        f"verdict d'ensemble {data['verdict']}",
        label="Contrôles",
    )
    equilibrium = data.get("equilibrium", {})
    if equilibrium:
        note.table(
            ["Cas", "Écart relatif maximal", "Verdict"],
            [
                [case, cell(v["worst_relative_gap"]), v["verdict"]]
                for case, v in equilibrium.items()
            ],
            widths_cm=[4, 7, 6],
            caption="Équilibre des réactions et des charges appliquées",
        )
    gravity = data.get("gravity", {})
    if gravity:
        note.table(
            [
                "Cas",
                "Composante",
                "Charge appliquée (N)",
                "Réactions bloquées (N)",
                "Écart relatif",
                "Verdict",
            ],
            [
                [
                    case,
                    v["component"],
                    cell(v["applied_n"]),
                    cell(v["reactions_blocked_n"]),
                    cell(v["relative_gap"]),
                    v["verdict"],
                ]
                for case, v in gravity.items()
            ],
            widths_cm=[1.8, 2.6, 3.6, 3.6, 3.2, 2.2],
            caption="Pesanteur",
        )
    symmetry = data.get("symmetry", {})
    if symmetry:
        note.table(
            [
                "Cas",
                "Paires contrôlées",
                "Non appariées",
                "Écart relatif maximal",
                "Verdict",
            ],
            [
                [
                    case,
                    cell(v["n_pairs_checked"]),
                    cell(v["n_unmatched"]),
                    cell(v["worst_relative_gap"]),
                    v["verdict"],
                ]
                for case, v in symmetry.items()
            ],
            widths_cm=[3.6, 3.2, 3.2, 4.4, 2.6],
            caption="Symétrie des déplacements",
        )
    informative = data.get("informative", {})
    if informative:
        render_generic_json(
            note, informative, title="Contrôles informatifs (sans verdict)"
        )


def render_level_e(note: NoteDocument, package: Package) -> None:
    spec = package.declared.level_e
    manifest_e = package.manifest.get("niveau_e")
    if spec is None or manifest_e is None:
        return
    note.heading("Niveau E : comparaison à une référence", 2)
    results = _read_json(package.directory / "niveau_e" / Path(spec.results).name)
    verdicts = results["verdicts"]
    note.table(
        ["Critère", "Verdict", "Compte pour le niveau E"],
        [
            [key, value["verdict"], _yes(key in spec.criteria_ids)]
            for key, value in verdicts.items()
        ],
        widths_cm=[3, 8, 6],
        caption="Verdicts des critères du fichier de résultats",
    )
    note.paragraph(
        f"{manifest_e['resultats']} "
        f"(SHA-256 {_short(manifest_e['resultats_sha256'], 16)})",
        label="Fichier de résultats",
    )
    if "comm_reference" in manifest_e:
        note.key_values(
            [
                ("Fichier de commandes de référence", manifest_e["comm_reference"]),
                ("SHA-256 de la référence", manifest_e["comm_reference_sha256"]),
                (
                    "SHA-256 de l'exécution du paquet",
                    manifest_e.get("comm_execute_sha256", EMPTY),
                ),
                ("Identique à l'octet près", _yes(manifest_e.get("meme_comm_octets"))),
                (
                    "Identique hors commentaires et en-tête",
                    _yes(manifest_e.get("meme_comm_que_l_execution")),
                ),
            ],
            headers=("Rubrique", "Valeur"),
        )
        if manifest_e.get("difference_comm"):
            note.lines("Lignes de différence", list(manifest_e["difference_comm"]))
    others = [
        f
        for f in package.files("niveau_e", ".json")
        if Path(f["chemin"]).name != Path(spec.results).name
    ]
    if others:
        note.paragraph(
            ", ".join(f["chemin"] for f in others),
            label="Autres fichiers de niveau E du paquet",
        )


# -- 3. generic tables and figures of a section ------------------------------------


def render_tables(note: NoteDocument, package: Package, section: str) -> int:
    count = 0
    for table in package.declared.note_tables:
        if table.section != section:
            continue
        resolved = resolve_table(package.directory, table)
        note.table(
            resolved.headers,
            resolved.cells,
            caption=table.title,
        )
        extra = table_note(resolved)
        if extra:
            note.paragraph(extra, italic=True)
        count += 1
    return count


def render_figures(note: NoteDocument, package: Package, section: str) -> int:
    count = 0
    for figures in package.declared.note_figures:
        if figures.section != section:
            continue
        paths = sorted(package.directory.glob(figures.pattern))
        if not paths:
            message = (
                f"figures « {figures.title} » : aucun fichier pour {figures.pattern}"
            )
            raise ProjectError(message)
        note.paragraph(figures.title, bold=True)
        for path in paths[: figures.max_figures]:
            note.figure(
                path,
                figures.caption.format(stem=path.stem),
                width_cm=figures.width_cm,
            )
            count += 1
        if len(paths) > figures.max_figures:
            note.paragraph(
                f"{figures.max_figures} figures sur {len(paths)} (les autres sont dans "
                "le paquet de résultats)",
                italic=True,
            )
    return count


# -- 4/5. combinations and reinforcement ---------------------------------------------


def render_combinations_results(note: NoteDocument, package: Package) -> None:
    render_tables(note, package, "combinaisons")
    for item in package.files("combinaisons", ".json"):
        data = package.json(item["chemin"])
        render_generic_json(
            note, data, title=f"Contrôle manuel ({Path(item['chemin']).name})"
        )


def _anomaly_rows(package: Package) -> list[list[str]]:
    commands = (
        {"CALC_FERRAILLAGE"} if package.ctx.declaration.rebar is not None else set()
    )
    rows = []
    for anomaly in load_anomalies(package.ctx.repo_root):
        if anomaly.status != "ouverte":
            continue
        if not any(s.command in commands for s in anomaly.signatures):
            continue
        rows.append(
            [
                anomaly.id,
                anomaly.title,
                "; ".join(
                    f"{s.entry} ({s.situation}) : {' '.join(s.deviation.split())}"
                    for s in anomaly.signatures
                ),
                " ".join(anomaly.hypothesis.split()),
            ]
        )
    return rows


def render_reinforcement(note: NoteDocument, package: Package) -> None:
    for item in package.files("ferraillage", ".json"):
        name = Path(item["chemin"]).name
        data = package.json(item["chemin"])
        if isinstance(data, dict) and is_beam(data):
            control_file = package.directory / "ferraillage" / "controle_main.json"
            control = _read_json(control_file) if control_file.is_file() else None
            render_beam(note, data, control)
        elif isinstance(data, dict) and is_plate(data):
            render_plate(note, data)
        elif name in {"controle_main.json"}:
            continue
        else:
            note.heading(f"Fichier {name}", 2)
            render_generic_json(note, data, title=name)
    render_tables(note, package, "ferraillage")
    render_figures(note, package, "ferraillage")
    anomalies = _anomaly_rows(package)
    note.heading("Anomalies ouvertes touchant la lecture du ferraillage", 2)
    if anomalies:
        note.table(
            ["Anomalie", "Titre", "Manifestations", "Hypothèse (non établie)"],
            anomalies,
            widths_cm=[1.8, 3.6, 7.2, 4.4],
            caption="connaissances/anomalies_ouvertes.yaml",
        )
    else:
        note.paragraph("aucune anomalie ouverte liée à CALC_FERRAILLAGE")


# -- 6. limits ---------------------------------------------------------------------


def render_limits(note: NoteDocument, ctx: ProjectContext) -> None:
    sheet = HypothesesSheet.model_validate_json(
        ctx.fiche_path.read_text(encoding="utf-8")
    )
    decided = [
        e
        for e in sheet.entries
        if isinstance(e, PracticeHypothesisEntry) and e.status == "tranche"
    ]
    decided.sort(key=lambda e: (point_key(e.point_label), e.topic))
    pending = [e for e in decided if e.under_revision]
    if pending:
        note.heading("Décisions en révision ou en attente d'application", 2)
        note.table(
            ["Point", "Sujet", "Révision déclarée", "Motif"],
            [
                [
                    e.point_label or EMPTY,
                    e.topic,
                    f"{fr_datetime(e.revision_history[-1].at)} "
                    f"({e.revision_history[-1].by})",
                    e.revision_history[-1].reason,
                ]
                for e in pending
            ],
            widths_cm=[1.5, 5, 3.8, 6.7],
        )
    note.heading("Domaine de validité des décisions", 2)
    rows = [
        [
            e.point_label or EMPTY,
            e.topic,
            " ".join((e.validity_domain or EMPTY).split()),
            f"{e.decided_by or EMPTY}, "
            f"{fr_date(e.decided_at) if e.decided_at else EMPTY}",
        ]
        for e in decided
    ]
    covered = {e.point_label for e in decided}
    cited: dict[str | None, list[str]] = {}
    for entry in sheet.entries:
        if isinstance(entry, FindingReference):
            cited.setdefault(entry.point_label, []).append(entry.constat_id)
    others = {e.point_label for e in sheet.entries} | {
        g.point_label for g in sheet.group_naming
    }
    others |= {c.point_label for c in sheet.planned_commands}
    for label in sorted(others - covered, key=point_key):
        rows.append(
            [
                label or EMPTY,
                "aucune décision de pratique tranchée à ce point",
                "constats Code_Aster rattachés : "
                f"{', '.join(cited.get(label, [])) or EMPTY}",
                EMPTY,
            ]
        )
    note.table(
        ["Point", "Sujet", "Domaine de validité", "Décision"],
        rows,
        widths_cm=[1.5, 4.5, 8.4, 2.6],
        caption=f"{len(decided)} décisions tranchées de la fiche",
    )


# -- the note ----------------------------------------------------------------------


def build_results_note(
    ctx: ProjectContext,
    output: Path,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> Path:
    """Write the results note of the project at `output` and return its path."""
    package = Package(ctx)
    declaration = ctx.declaration
    note = NoteDocument(
        title=f"Note de résultats — {declaration.structure}",
        footer=f"Note de résultats {declaration.structure}",
    )
    note.title("Note de résultats", f"{declaration.structure} ({declaration.name})")
    shown = package.sections()

    note.heading("Traçabilité et niveau de validation atteint", 1)
    render_traceability(note, package, now())
    render_level(note, package)

    if shown & {"controles", "niveau_e"} or package.manifest["criteres"]:
        note.heading("Contrôles de niveau D et de niveau E", 1)
        render_criteria(note, package)
        if "controles" in shown:
            render_controls_d(note, package)
            render_tables(note, package, "controles")
        if "niveau_e" in shown:
            render_level_e(note, package)
            render_tables(note, package, "niveau_e")

    if "cas" in shown:
        note.heading("Résultats par cas", 1)
        render_tables(note, package, "cas")
        render_figures(note, package, "cas")

    if "combinaisons" in shown:
        note.heading("Combinaisons", 1)
        render_combinations_results(note, package)

    if "ferraillage" in shown:
        note.heading("Ferraillage", 1)
        render_reinforcement(note, package)

    note.heading("Limites et domaine de validité des décisions", 1)
    render_limits(note, ctx)

    note.save(output)
    return output


__all__ = ["NOTE_NAME", "Package", "build_results_note"]
