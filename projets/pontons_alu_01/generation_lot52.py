# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01, lot 52: the PRO geometry of the whole pontoon,
one parameterised file for every variant (`variantes_lot52.yaml`, PONTONS_VARIANTE).

The text is that of lot 51 ter (`generation_lot51ter.build_comm`: cases, loads, pins,
footings, outputs), on the geometry of `geometrie_lot52` (P64: posts and diagonals under
the purlins, rigid links LM_ and LR_; P65: pin axis at +1,175), with the section of the
posts and diagonals of the variant (P63: tube 120 × 120 × 6 instead of 150 × 150 × 7)
and the head of this lot. The unit cases are unchanged (221): the houle cases keep their
widths (HU_PANNES: 0,05 m per purlin, now the width of the purlins).
"""

from __future__ import annotations

import dataclasses
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation_lot51ter import Values51ter
from pontons_alu_01.generation_lot51ter import build_comm as build_51ter
from pontons_alu_01.generation_lot51ter import values as values_51ter
from pontons_alu_01.geometrie_lot51ter import Geometry51ter
from pontons_alu_01.geometrie_lot52 import geometry
from pontons_alu_01.variantes_lot52 import Variant52, current

SOLID_NOTE = (
    "# X, Z bloqués. LIAISON_SOLIDE (P64) : pannes posées sur les montants et les diagonales (LR_, 0,085 m),"
    " montants soudés sur le flanc des poutres principales (LM_, 0,01 m), pannes du porte-à-faux / panne de rive (LR_ de PF),"
)


def geometry_of(variant: Variant52) -> Geometry51ter:
    return geometry(variant.mesh_overrides)


def values(ctx: ProjectContext, variant: Variant52) -> Values51ter:
    """The values of lot 51 ter on the parameters of `maillage_ponton_52.py`, the posts
    and diagonals with the section of the variant (P63). The fields keep their names of
    lot 51 ter (t150, e150: side and thickness of the posts and diagonals)."""
    base = values_51ter(ctx, variant, geometry_of(variant).parameters)
    return dataclasses.replace(
        base,
        t150=variant.post_side_mm * 1e-3,
        e150=variant.post_thickness_mm * 1e-3,
    )


def linked_support_ends(g: Geometry51ter) -> dict[str, tuple[str, ...]]:
    """CA-036: the abutment nodes and the ears of the pins are the B ends of rigid links
    LM_ (post / main beam, P64); REAC_NODA of a linked node carries the force of the
    link, which cancels only over the linked nodes. Returns the groups of the post ends
    (LM_*_A) linked to the abutment (`APP_CULEE`) and to the ears (`AXES`)."""
    abutment = set(g.node_groups["APP_CULEE"])
    ears = {p for a in g.axes for p in a.ears}
    lm = [lk for lk in g.links if lk.name.startswith("LM_")]
    return {
        "APP_CULEE": tuple(f"{lk.name}_A" for lk in lm if lk.b in abutment),
        "AXES": tuple(f"{lk.name}_A" for lk in lm if lk.b in ears),
    }


def header(variant: Variant52, mesh_label: str, g: Geometry51ter) -> list[str]:
    lv = g.levels
    return [
        "# PONTONS-ALU-01, lot 52 : ponton intégral, géométrie PRO (culée, 5 palées, 5 grandes travées,",
        "# porte-à-faux d'extrémité), treillis horizontal constructible (P64), appuis articulés à axe (P65).",
        "# Calcul linéaire, cas élémentaires unitaires.",
        f"# Variante {variant.code} : {variant.description}.",
        f"# Code_Aster 17.4. Unités : m, N, Pa, °C. Maillage : {mesh_label} (maillage_ponton_52.py).",
        "# Généré par pontons_alu_01.generation_lot52 à partir de la fiche (P1 à P66), des données",
        "# et de variantes_lot52.yaml : régénérer plutôt qu'éditer. Combinaisons et exports :",
        "# post-traitement (scripts/lot52.py).",
        f"# P63, P64 : montants et diagonales tube {variant.post_label} mm (6082-T6), axe +{lv['montants']:g}"
        f" sous les pannes ; nœud diagonale–montant à e = {variant.e_diag:g} m de l'axe des poutres.",
        "# CA-036 : les nœuds d'appui de la culée et les oreilles des appuis à axe sont liés aux montants",
        "# (LM_) ; leur REAC_NODA porte l'effort de la liaison. Le relevé R<cas> du harnais porte donc sur",
        "# APP_CULEE et les bouts de montant qui y sont liés, et l'unité 33 sur les bouts liés aux oreilles.",
    ]


def build_comm(
    ctx: ProjectContext, *, mesh_label: str, variant: Variant52 | None = None
) -> tuple[str, dict[str, Any]]:
    variant = variant or current()
    g = geometry_of(variant)
    linked = linked_support_ends(g)
    text, report = build_51ter(
        ctx,
        mesh_label=mesh_label,
        variant=variant,
        g=g,
        v=values(ctx, variant),
        header=header(variant, mesh_label, g),
        solid_note=SOLID_NOTE,
        harness_groups={"R": ("APP_CULEE", *linked["APP_CULEE"])},
        extra_reaction_groups=(*linked["APP_CULEE"], *linked["AXES"]),
    )
    report["post_section"] = variant.post_label
    report["e_diag_m"] = variant.e_diag
    return text, report


def applied_loads(
    ctx: ProjectContext, variant: Variant52
) -> dict[str, dict[str, float]]:
    from pontons_alu_01.generation_lot51ter import (  # noqa: PLC0415
        applied_loads as loads_51ter,
    )

    return loads_51ter(values(ctx, variant), geometry_of(variant))


__all__ = [
    "SOLID_NOTE",
    "applied_loads",
    "build_comm",
    "geometry_of",
    "header",
    "values",
]
