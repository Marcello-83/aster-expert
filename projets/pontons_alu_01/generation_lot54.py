# ruff: noqa: E501 -- gabarits du texte .comm, lignes de commande Code_Aster entières
"""`.comm` generator of PONTONS-ALU-01, lot 54: the final PRO geometry of the whole
pontoon, one parameterised file for every variant (`variantes_lot54.yaml`,
PONTONS_VARIANTE).

The text is that of lot 52 (`generation_lot51ter.build_comm` with the links LM_ and LR_
of P64 and the relevé of CA-036), on the geometry of `geometrie_lot54` (P67: regular
truss, posts at Xd + k × 1,25; P68: cap beams 0,60 × 0,40 from Y = −1,20 to +1,20),
with the cap beams' own section and buoyancy (`Values51ter.cap_b`). The unit cases are
unchanged (221); the houle (P69) and the rule P70 are post-processing.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from aster_expert.projet.context import ProjectContext
from pontons_alu_01.generation_lot51ter import Values51ter
from pontons_alu_01.generation_lot51ter import applied_loads as loads_51ter
from pontons_alu_01.generation_lot51ter import build_comm as build_51ter
from pontons_alu_01.generation_lot51ter import values as values_51ter
from pontons_alu_01.generation_lot52 import SOLID_NOTE, linked_support_ends
from pontons_alu_01.geometrie_lot51ter import Geometry51ter
from pontons_alu_01.geometrie_lot54 import geometry
from pontons_alu_01.variantes_lot54 import Variant54, current


def geometry_of(variant: Variant54) -> Geometry51ter:
    return geometry(variant.mesh_overrides)


def values(ctx: ProjectContext, variant: Variant54) -> Values51ter:
    """The values of lot 52 on the parameters of lot 54: posts and diagonals with the
    section of the variant (P63), cap beams of their own width (P68)."""
    base = values_51ter(ctx, variant, geometry_of(variant).parameters)
    return dataclasses.replace(
        base,
        t150=variant.post_side_mm * 1e-3,
        e150=variant.post_thickness_mm * 1e-3,
        cap_b=variant.cap_width,
    )


def header(variant: Variant54, mesh_label: str, g: Geometry51ter) -> list[str]:
    lv = g.levels

    def fr(x: float) -> str:
        return f"{x:g}".replace(".", ",").replace("-", "−")

    posts = " / ".join(fr(x) for x in (0.0, *variant.inner_posts))
    return [
        "# PONTONS-ALU-01, lot 54 : ponton intégral, géométrie PRO définitive (culée, 5 palées, 5 grandes",
        "# travées, porte-à-faux d'extrémité), treillis horizontal régulier (P64, P67), chevêtres 0,60 × 0,40",
        "# prolongés (P68), appuis articulés à axe (P65). Calcul linéaire, cas élémentaires unitaires.",
        f"# Variante {variant.code} : {variant.description}.",
        f"# Code_Aster 17.4. Unités : m, N, Pa, °C. Maillage : {mesh_label} (maillage_ponton_52.py).",
        "# Généré par pontons_alu_01.generation_lot54 à partir de la fiche (P1 à P76), des données",
        "# et de variantes_lot54.yaml : régénérer plutôt qu'éditer. Combinaisons et exports :",
        "# post-traitement (scripts/lot54.py ; houle P69, règle P70).",
        f"# P63, P64 : montants et diagonales tube {variant.post_label} mm (6082-T6), axe +{lv['montants']:g}"
        f" sous les pannes ; nœud diagonale–montant à e = {variant.e_diag:g} m de l'axe des poutres.",
        f"# P67 : montants d'une grande travée à Xd + {posts} / 6,25 m (panneaux égaux).",
        f"# P68 : chevêtres {fr(variant.cap_width)} (selon X) × 0,4 m, de Y = {fr(variant.cap_ends[0])} à {fr(variant.cap_ends[1])} ;"
        " longrines 0,4 × 0,4 coupées au nu des chevêtres.",
        "# CA-036 : les nœuds d'appui de la culée et les oreilles des appuis à axe sont liés aux montants",
        "# (LM_) ; leur REAC_NODA porte l'effort de la liaison. Le relevé R<cas> du harnais porte donc sur",
        "# APP_CULEE et les bouts de montant qui y sont liés, et l'unité 33 sur les bouts liés aux oreilles.",
    ]


def build_comm(
    ctx: ProjectContext, *, mesh_label: str, variant: Variant54 | None = None
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
    report["inner_posts_m"] = list(variant.inner_posts)
    report["cap_width_m"] = variant.cap_width
    report["cap_ends_m"] = list(variant.cap_ends)
    return text, report


def applied_loads(
    ctx: ProjectContext, variant: Variant54
) -> dict[str, dict[str, float]]:
    return loads_51ter(values(ctx, variant), geometry_of(variant))


__all__ = ["applied_loads", "build_comm", "geometry_of", "header", "values"]
