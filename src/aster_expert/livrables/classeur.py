"""Summary workbook of the deliverables (lot 49), built from the results package only.

Nothing is recomputed: every value is read in a file of `resultats/paquet/` (section
`visualisation` of lot 49, and the existing sections `controles`, `niveau_e`,
`contre_calcul`, the manifest of the package). Layout asked by MM: font Arial 10, black
text, table headers on a grey fill, never blue.

Values are shown in their display unit (`aster_expert.livrables.unites`: kN, kN·m,
mm...): the cell holds the value converted exactly (SI value × factor), and only its
number format is rounded, with the decimals of `config/arrondis.yaml`. A test reads
the workbook back (`tests/unit/test_livrables_classeur.py`).
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from aster_expert.arrondis import RoundingTable, load_table
from aster_expert.livrables.unites import display
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError

FONT = Font(name="Arial", size=10, color="FF000000")
HEADER_FONT = Font(name="Arial", size=10, bold=True, color="FF000000")
HEADER_FILL = PatternFill(
    fill_type="solid", start_color="FFD9D9D9", end_color="FFD9D9D9"
)
"""Grey 15 % (never blue: request of MM)."""
WORKBOOK = "classeur_livrables.xlsx"
SHEETS = (
    "Synthèse",
    "Réactions et équilibre",
    "Efforts par élément",
    "Enveloppes",
    "Contrôles D et E",
    "Comparaison externe",
    "Conventions",
    "Provenance",
)


class Sheet:
    """A worksheet written row by row with the layout of the workbook."""

    def __init__(self, workbook: Workbook, title: str, table: RoundingTable) -> None:
        self.ws = workbook.create_sheet(title)
        self.table = table
        self.row = 1
        self.widths: dict[int, int] = {}

    def text(self, value: str) -> None:
        cell = self.ws.cell(row=self.row, column=1, value=value)
        cell.font = FONT
        self.row += 1

    def header(self, labels: Sequence[str]) -> None:
        for column, label in enumerate(labels, 1):
            cell = self.ws.cell(row=self.row, column=column, value=label)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            self.widths[column] = max(self.widths.get(column, 0), min(len(label), 40))
        self.row += 1

    def values(self, items: Sequence[Any], units: Sequence[str | None] = ()) -> None:
        """One row; a number with a display unit gets the format of that unit."""
        for column, value in enumerate(items, 1):
            if isinstance(value, float) and math.isnan(value):
                value = None
            cell = self.ws.cell(row=self.row, column=column, value=value)
            cell.font = FONT
            unit = units[column - 1] if column - 1 < len(units) else None
            if isinstance(value, float) and unit:
                decimals = self.table.decimals(unit)
                cell.number_format = "0" if decimals == 0 else "0." + "0" * decimals
            text = "" if value is None else str(value)
            self.widths[column] = max(self.widths.get(column, 0), min(len(text), 40))
        self.row += 1

    def blank(self) -> None:
        self.row += 1

    def finish(self) -> None:
        for column, width in self.widths.items():
            self.ws.column_dimensions[get_column_letter(column)].width = max(
                8, width + 2
            )


def shown(value: float | None, unit_si: str) -> tuple[float | None, str]:
    """(value in its display unit, display unit): exact conversion, no rounding."""
    target = display(unit_si)
    return (None if value is None else value * target.factor), target.unit


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_verdicts(prefix: str, data: Any) -> Iterable[tuple[str, Any, str]]:
    """(path, value, verdict) of every dict holding a `verdict` key."""
    if isinstance(data, dict):
        if "verdict" in data and isinstance(data["verdict"], str):
            value = next(
                (
                    data[k]
                    for k in (
                        "worst_relative_gap",
                        "relative_gap",
                        "ecart_relatif",
                        "ecart",
                        "valeur",
                    )
                    if k in data
                ),
                None,
            )
            yield prefix, value, data["verdict"]
        for key, sub in data.items():
            if key in ("verdict", "provenance"):
                continue
            yield from _flatten_verdicts(f"{prefix} / {key}" if prefix else key, sub)


def build_workbook(package: Path, table: RoundingTable) -> Workbook:
    vis = package / "visualisation"
    manifest = _load(vis / "manifeste.json")
    paquet = _load(package / "paquet.json")
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {title: Sheet(wb, title, table) for title in SHEETS}

    # 1. Synthèse
    s = sheets["Synthèse"]
    s.text(
        f"Projet {manifest['projet']} -- extrema par famille et par grandeur, sur "
        "l'enveloppe des combinaisons (hors disques d'exclusion déclarés)"
    )
    s.header(
        [
            "Famille",
            "Champ",
            "Composante",
            "Extremum",
            "Valeur",
            "Unité",
            "Groupes",
            "Nœud MED",
            "Maille MED",
            "X (m)",
            "Y (m)",
            "Z (m)",
            "Combinaison",
            "Position mobile",
            "Cas",
        ]
    )
    for e in _load(vis / "synthese.json"):
        value, unit = shown(e["valeur_si"], e["unite_si"])
        x, y, z = e["lieu"]["coordonnees_m"]
        s.values(
            [
                e["famille"],
                e["champ"],
                e["composante"],
                e["extremum"],
                value,
                unit,
                " ".join(e["lieu"].get("groupes", [])),
                e["lieu"]["noeud_med"],
                e["lieu"].get("maille_med"),
                x,
                y,
                z,
                e.get("combinaison"),
                e.get("position_mobile"),
                e.get("cas"),
            ],
            [None, None, None, None, unit, None, None, None, None, "m", "m", "m"],
        )

    # 2. Réactions et équilibre
    s = sheets["Réactions et équilibre"]
    loads = _load(vis / "controle_charges.json")
    balance = _load(vis / "equilibre_livrables.json")
    s.text(
        "Par cas : charge appliquée (Σ des forces nodales du MED des charges), "
        "réactions et forces des ressorts livrées, bilan"
    )
    s.header(
        [
            "Cas",
            "Composante",
            "Charge",
            "Réactions",
            "Ressorts",
            "Bilan",
            "Unité",
            "Écart relatif",
            "Résultante déclarée",
            "Verdict CTL-013",
        ]
    )
    for case, entry in balance["cas"].items():
        load = entry.get("charge_n") or {}
        ctl = loads["cas"].get(case, {})
        scale = max(
            (abs(v) for k, v in load.items() if k in ("FX", "FY", "FZ")), default=0
        )
        for comp in ("FX", "FY", "FZ"):
            bilan = (entry.get("bilan_n") or {}).get(comp)
            values = [
                shown(load.get(comp), "N")[0],
                shown(entry["reactions_n"][comp], "N")[0],
                shown(entry["ressorts_n"][comp], "N")[0],
                shown(bilan, "N")[0],
            ]
            declared = (ctl.get("attendu_tel_qu_evalue_n") or {}).get(
                {"FX": "DX", "FY": "DY", "FZ": "DZ"}[comp]
            )
            s.values(
                [
                    case,
                    comp,
                    *values,
                    "kN",
                    abs(bilan) / scale if bilan is not None and scale else None,
                    shown(declared, "N")[0],
                    ctl.get("verdict"),
                ],
                [None, None, "kN", "kN", "kN", "kN", None, None, "kN"],
            )
    if balance.get("appuis_non_livres"):
        s.blank()
        s.text(
            "Appuis non livrés (motif dans projet.yaml) : "
            + ", ".join(balance["appuis_non_livres"])
        )

    # 3. Efforts par élément (points de lecture)
    s = sheets["Efforts par élément"]
    points = _load(vis / "points.json")
    units = {
        (c["cle"], comp["nom"]): comp["unite_si"]
        for c in manifest["champs"]
        for comp in c["composantes"]
    }
    s.text(
        "Valeurs aux points de lecture déclarés, par cas élémentaire et pour "
        "l'enveloppe"
    )
    s.header(
        [
            "Point",
            "Champ",
            "Source",
            "Nœud MED",
            "Maille MED",
            "Extrémité",
            "X (m)",
            "Y (m)",
            "Z (m)",
            "Composante",
            "Valeur",
            "Unité",
        ]
    )
    for p in points:
        x, y, z = p["lieu"]["coordonnees_m"]
        for comp, value in p["valeurs_si"].items():
            v, unit = shown(value, units[(p["cle"], comp)])
            s.values(
                [
                    p["point"],
                    p["cle"],
                    p["source"],
                    p["lieu"]["noeud_med"],
                    p["lieu"].get("maille_med"),
                    p["lieu"].get("extremite"),
                    x,
                    y,
                    z,
                    comp,
                    v,
                    unit,
                ],
                [None] * 6 + ["m", "m", "m", None, unit],
            )

    # 4. Enveloppes le long des éléments linéiques
    s = sheets["Enveloppes"]
    linear = _load(vis / "enveloppes_lineiques.json")
    s.text("Enveloppe (max et min sur les combinaisons) à chaque extrémité d'élément")
    if linear:
        comps = [k[: -len("_max")] for k in linear[0] if k.endswith("_max")]
        head = [
            "Champ",
            "Maille MED",
            "Extrémité",
            "Nœud MED",
            "X (m)",
            "Y (m)",
            "Z (m)",
        ]
        cols: list[str] = []
        col_units: list[str | None] = [None] * 4 + ["m", "m", "m"]
        for comp in comps:
            unit = display(units[(linear[0]["cle"], comp)]).unit
            cols += [f"{comp}_max", f"{comp}_min"]
            head += [f"{comp} max ({unit})", f"{comp} min ({unit})"]
            col_units += [unit, unit]
        s.header(head)
        for e in linear:
            row = [
                e["cle"],
                e["maille_med"],
                e["extremite"],
                e["noeud_med"],
                e["x_m"],
                e["y_m"],
                e["z_m"],
            ]
            for col in cols:
                comp = col.rsplit("_", 1)[0]
                row.append(shown(e[col], units[(e["cle"], comp)])[0])
            s.values(row, col_units)

    # 5. Contrôles D et E
    s = sheets["Contrôles D et E"]
    dates: dict[str, tuple[str | None, str | None, str]] = {}
    for c in paquet.get("criteres", []):
        dates.setdefault(
            c["niveau"], (c.get("commit_introduction"), c.get("date"), c["document"])
        )
    s.text("Niveau atteint : " + str(paquet["niveau"]["atteint"]))
    s.header(["Niveau", "Atteint", "Motif"])
    for n in paquet["niveau"]["par_niveau"]:
        s.values([n["niveau"], "oui" if n["atteint"] else "non", n["motif"]])
    s.blank()
    s.header(
        [
            "Niveau",
            "Critère",
            "Valeur",
            "Verdict",
            "Document du critère",
            "Commit",
            "Date du commit",
        ]
    )
    controls = package / "controles"
    for path in sorted(controls.glob("*.json")) if controls.is_dir() else []:
        for name, value, verdict in _flatten_verdicts(path.stem, _load(path)):
            commit, date, document = dates.get("D", (None, None, None))
            s.values(
                [
                    "D",
                    name,
                    value if isinstance(value, int | float) else None,
                    verdict,
                    document,
                    commit,
                    date,
                ]
            )
    level_e = paquet.get("niveau_e") or {}
    for name, verdict in (level_e.get("verdicts") or {}).items():
        commit, date, document = dates.get("E", (None, None, None))
        s.values(["E", name, None, verdict, document, commit, date])
    for case, entry in loads["cas"].items():
        s.values(
            [
                "D",
                f"CTL-013 MED des charges / {case}",
                entry.get("ecart_relatif"),
                entry.get("verdict"),
                "lot 49",
                None,
                None,
            ]
        )

    # 6. Comparaison externe
    s = sheets["Comparaison externe"]
    external = package / "contre_calcul"
    files = sorted(external.glob("*.json")) if external.is_dir() else []
    if not files:
        s.text("Sans objet : le projet n'a pas de comparaison à un calcul externe.")
    for path in files:
        data = _load(path)
        rows = data.get("lignes") if isinstance(data, dict) else None
        if not rows or not isinstance(rows, list) or not isinstance(rows[0], dict):
            continue
        s.text(
            f"{path.name} -- contre-calcul d'un modèle non validé, jamais un niveau E"
        )
        keys = [k for k in rows[0] if not isinstance(rows[0][k], dict | list)]
        s.header(keys)
        for row in rows:
            s.values(
                [
                    row.get(k) if not isinstance(row.get(k), dict | list) else None
                    for k in keys
                ]
            )
        s.blank()

    # 7. Conventions
    s = sheets["Conventions"]
    s.header(
        [
            "Famille",
            "Champ",
            "Groupes",
            "Composantes (unité SI → affichage)",
            "Repère et signes",
        ]
    )
    for c in manifest["champs"]:
        s.values(
            [
                c["famille"],
                c["champ"],
                " ".join(c["groupes"] + c["groupes_noeuds"]),
                ", ".join(
                    f"{x['nom']} ({x['unite_si']} → {x['unite_affichage']})"
                    for x in c["composantes"]
                ),
                c["convention"],
            ]
        )

    # 8. Provenance
    s = sheets["Provenance"]
    s.header(["Élément", "Valeur"])
    for label, value in (
        ("Projet", manifest["projet"]),
        ("Code_Aster", manifest["code_aster"].get("version")),
        ("Image", manifest["code_aster"].get("image_digest")),
        ("Exécution de production", manifest["execution_production"]),
        (".comm de production (SHA-256)", manifest["comm_production_sha256"]),
        ("Exécution de post-traitement", manifest["execution_post_traitement"]),
        (".comm de post-traitement (SHA-256)", manifest["comm_post_traitement_sha256"]),
        ("Maillage", manifest["maillage"]["chemin"]),
        ("Maillage (SHA-256)", manifest["maillage"]["sha256"]),
        ("Paquet : commit", paquet["depot"]["commit"]),
        ("Paquet : exporté le", paquet["exporte_le"]),
    ):
        s.values([label, value])
    s.blank()
    s.header(["Fichier", "SHA-256", "Octets"])
    for name, info in manifest["fichiers"].items():
        s.values([name, info["sha256"], info["octets"]])
    for sheet in sheets.values():
        sheet.finish()
    return wb


def write_workbook(ctx: ProjectContext) -> str:
    """`resultats/livrables/classeur_livrables.xlsx` from the exported package."""
    section = ctx.declaration.results_package
    if section is None:
        message = "classeur : le projet ne déclare pas de paquet de résultats"
        raise ProjectError(message)
    package = ctx.results_dir / section.output
    if not (package / "visualisation" / "manifeste.json").is_file():
        message = (
            "classeur : le paquet ne porte pas la section visualisation (exporter "
            "le paquet après les livrables)"
        )
        raise ProjectError(message)
    wb = build_workbook(package, load_table(ctx.repo_root))
    out = ctx.results_dir / "livrables" / WORKBOOK
    wb.save(out)
    return f"Classeur : {out.name} ({len(wb.sheetnames)} feuilles, depuis le paquet)"


__all__ = [
    "FONT",
    "HEADER_FILL",
    "SHEETS",
    "WORKBOOK",
    "build_workbook",
    "shown",
    "write_workbook",
]
