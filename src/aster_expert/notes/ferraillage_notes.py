"""The reinforcement part of the results note (lot 45): what `CALC_FERRAILLAGE`
computed, and what the common core computes outside Code_Aster, with the articles of
EN 1992-1-1.

The two shapes are those written by `aster_expert.ferraillage.poutre` (1D,
`resume.json`) and `aster_expert.ferraillage.plaque` (2D, `ferraillage_<groupe>.json`).
Nothing is recomputed: every number is read from the package.
"""

from __future__ import annotations

import re
from typing import Any

from aster_expert.notes.docx_style import NoteDocument
from aster_expert.notes.formats import cell

ARTICLE = re.compile(r"(?<![\d.])(\d(?:_\d+){1,3})(?!\d)")
"""An article number written in a key (`as_min_9_2_1_1` -> 9.2.1.1)."""

# Articles of EN 1992-1-1 applied outside Code_Aster, as documented by the module that
# applies them (`ferraillage.poutre`: shear and torsion 6.2, 6.3).
SHEAR_TORSION_ARTICLES = "6.2 (effort tranchant), 6.3 (torsion)"


KEY_LABELS = {
    "thickness": "Épaisseur (m)",
    "cover": "Distance parement–axe (m)",
    "fck": "fck (Pa)",
    "fyk": "fyk (Pa)",
    "fctm": "fctm (Pa)",
    "eys": "Es, module de l'acier (Pa)",
    "alpha_cc": "αcc",
    "sigs_els": "σs limite à l'ELS caractéristique (Pa)",
    "sigc_els": "σc limite à l'ELS (Pa)",
    "sigc_els_qp": "σc limite à l'ELS quasi permanent (Pa)",
    "alpha_e": "αe",
    "kt": "kt",
    "wk": "wk (m)",
    "phi": "φ des barres (m)",
    "d_m": "Hauteur utile d (m)",
    "as_min_9_2_1_1_m2_per_m": "As,min de non-fragilité (m²/m)",
    "as_min_7_3_2_m2_per_m": "As,min de maîtrise de la fissuration (m²/m)",
    "as_min_m2_per_m": "As,min retenu (m²/m)",
    "repartition_min_ratio_9_3_1_1": (
        "Armatures de répartition, part minimale des armatures principales"
    ),
    "worst_relative_gap": "Écart relatif maximal",
    "AYS": "AYS (m²)",
    "AYI": "AYI (m²)",
    "AZS": "AZS (m²)",
    "AZI": "AZI (m²)",
    "AST": "AST (m²/m)",
}
"""French labels of the keys written by the common core's JSON files."""


def label_of(key: str) -> str:
    return KEY_LABELS.get(key, key)


def article_of(key: str) -> str:
    """`EN 1992-1-1, art. 9.2.1.1` for a key that carries an article number."""
    found = ARTICLE.search(key)
    return f"EN 1992-1-1, art. {found.group(1).replace('_', '.')}" if found else ""


def is_beam(data: dict[str, Any]) -> bool:
    return {"sections", "instants", "minima"} <= set(data)


def is_plate(data: dict[str, Any]) -> bool:
    return {"plaque", "valeurs", "minima_en_1992"} <= set(data)


def _key_values(
    note: NoteDocument, title: str, mapping: dict[str, Any], *, article: bool = False
) -> None:
    rows = []
    for key, value in mapping.items():
        row = [label_of(key), cell(value)]
        if article:
            row.append(article_of(key))
        rows.append(row)
    headers = ["Grandeur", "Valeur"] + (["Article"] if article else [])
    widths = [7.0, 4.0] + ([6.0] if article else [])
    note.table(headers, rows, widths_cm=widths, caption=title)


def render_beam(
    note: NoteDocument, data: dict[str, Any], control: dict[str, Any] | None
) -> None:
    """1D member: areas by face (Code_Aster), minima and shear/torsion (outside)."""
    note.paragraph(
        f"{data['sections']} sections, {data['instants']} instants (combinaisons) ; "
        f"aires négatives non résolues : {data['aires_negatives_non_resolues']}",
        label="Calcul",
    )
    note.heading("Part calculée par CALC_FERRAILLAGE", 2)
    _key_values(
        note,
        "Aire maximale par face, toutes familles (m²) — champ FERR_ELEM",
        data["max_par_face_toutes_familles"],
    )
    note.heading("Part calculée hors de Code_Aster", 2)
    rows = []
    for face, values in data["minima"].items():
        rows.append(
            [
                face,
                f"{face}S et {face}I",
                cell(values["b_m"]),
                cell(values["h_m"]),
                cell(values["d_m"]),
                cell(values["as_min_9_2_1_1"]),
                cell(values["phi_star_mm"]),
                cell(values["sigma_s_MPa"]),
                "oui" if values["sigma_s_borne_tableau"] else "non",
                cell(values["act_m2"]),
                cell(values["as_min_7_3_2"]),
            ]
        )
    note.table(
        [
            "Face",
            "Faces concernées",
            "b (m)",
            "h (m)",
            "d (m)",
            "As,min 9.2.1.1 (m²)",
            "φ*s (mm)",
            "σs (MPa)",
            "σs bornée",
            "Act (m²)",
            "As,min 7.3.2 (m²)",
        ],
        rows,
        widths_cm=[1.0, 2.6, 1.0, 1.0, 1.0, 1.9, 1.3, 1.3, 1.2, 1.3, 1.9],
        caption=(
            "Aires minimales : non-fragilité (EN 1992-1-1, 9.2.1.1) et maîtrise de la "
            "fissuration (EN 1992-1-1, 7.3.2, tableau 7.2N, expression 7.6N)"
        ),
    )
    note.key_values(
        [
            ("Effort tranchant et torsion", f"EN 1992-1-1, {SHEAR_TORSION_ARTICLES}"),
            ("Critère de bielle maximal", cell(data["max_bielle"])),
            (
                "Armature longitudinale de torsion maximale (m²)",
                cell(data["max_asl_torsion"]),
            ),
        ],
        headers=("Rubrique", "Valeur"),
    )
    if control is not None:
        note.heading("Contrôle indépendant des aires ELU", 2)
        note.key_values(
            [
                ("Critère", str(control["critere"])),
                ("Comparaisons", cell(control["nombre_de_comparaisons"])),
                ("Dans le critère", cell(control["dans_le_critere"])),
                ("Échecs", cell(control["echecs"])),
                (
                    "Écart relatif maximal dans le critère",
                    cell(control["ecart_relatif_max_dans_le_critere"]),
                ),
            ],
            headers=("Rubrique", "Valeur"),
        )
        failures = [c for c in control["comparaisons"] if not c.get("reussite")]
        if failures:
            note.table(
                ["Section", "Combinaison", "Face", "Code_Aster (m²)", "Module (m²)"],
                [
                    [
                        c["section"],
                        c["combinaison"],
                        face,
                        cell(c["code_aster"][face]),
                        cell(c["module"][face]),
                    ]
                    for c in failures
                    for face in c["code_aster"]
                    if abs(c["code_aster"][face] - c["module"][face]) > 1e-12
                ],
                widths_cm=[3.5, 5.5, 1.5, 3.2, 3.2],
                caption="Comparaisons en échec (rapportées telles quelles)",
            )


def render_plate(note: NoteDocument, data: dict[str, Any]) -> None:
    """2D plate: densities (Code_Aster), minima, hand check (outside)."""
    note.paragraph(f"{data['libelle']} (groupe {data['plaque']})", label="Plaque")
    _key_values(note, "Valeurs de calcul (unités SI du .comm)", data["valeurs"])
    note.heading("Part calculée par CALC_FERRAILLAGE", 2)
    _key_values(
        note,
        "Enveloppe des besoins ELU, ELS caractéristique, ELS quasi permanent (m²/m)",
        data["enveloppe_besoins_elu_els_qp_m2_par_m"],
    )
    rows = []
    for combo in data["combinaisons"]:
        for component, found in combo["max"].items():
            rows.append(
                [
                    combo["combinaison"],
                    combo["famille"],
                    component,
                    found["maille"],
                    cell(found["m2_par_m"]),
                ]
            )
    note.table(
        ["Combinaison", "Famille", "Densité", "Maille du maximum", "Valeur (m²/m)"],
        rows,
        widths_cm=[5, 3.5, 2, 3, 3.5],
        caption="Maximum de chaque densité, par combinaison (champ FERR_ELEM)",
    )
    note.heading("Part calculée hors de Code_Aster", 2)
    _key_values(
        note,
        "Minima (EN 1992-1-1) — module aster_expert.rebar",
        data["minima_en_1992"],
        article=True,
    )
    _key_values(
        note,
        "Enveloppe retenue : maximum des besoins et du minimum (m²/m)",
        data["enveloppe_avec_minimum_m2_par_m"],
    )
    control = data.get("controle_independant")
    if control:
        note.heading("Contrôle indépendant au centre", 2)
        note.paragraph(
            f"nœud {control['noeud']} ; tolérance relative "
            f"{cell(control['tolerance_relative'])}",
            label="Contrôle",
        )
        note.table(
            [
                "Combinaison",
                "Maille",
                "Écart relatif (moyenne des nœuds)",
                "Réussite de la moyenne",
            ],
            [
                [
                    m["combinaison"],
                    m["maille"],
                    cell(m["ecart_moyenne"]),
                    "oui" if m["reussite_moyenne"] else "non",
                ]
                for m in control["mailles"]
            ],
            widths_cm=[5, 2, 6, 4],
            caption="Écart entre CALC_FERRAILLAGE et le module indépendant (centre)",
        )


def render_generic_json(
    note: NoteDocument, data: Any, *, title: str, depth: int = 0
) -> None:
    """A JSON object of the package as key/value tables, one level of detail per
    nested dict (capped): for the files whose shape is the project's own."""
    if not isinstance(data, dict):
        note.paragraph(cell(data), label=title)
        return
    scalars = {k: v for k, v in data.items() if not isinstance(v, dict | list)}
    if scalars:
        _key_values(note, title, scalars)
    for key, value in data.items():
        if isinstance(value, dict) and depth < 2:
            render_generic_json(note, value, title=f"{title} — {key}", depth=depth + 1)
        elif (
            isinstance(value, list)
            and value
            and all(not isinstance(x, dict | list) for x in value)
        ):
            note.paragraph(", ".join(cell(x) for x in value), label=f"{title} — {key}")
        elif isinstance(value, dict | list) and depth >= 2:
            note.paragraph(
                "(détail dans le paquet de résultats)", label=f"{title} — {key}"
            )
        elif isinstance(value, list) and value:
            note.paragraph(
                f"{len(value)} éléments (détail dans le paquet de résultats)",
                label=f"{title} — {key}",
            )


__all__ = [
    "SHEAR_TORSION_ARTICLES",
    "article_of",
    "is_beam",
    "is_plate",
    "render_beam",
    "render_generic_json",
    "render_plate",
]
