"""Mise en forme Markdown de la synthèse (lot 35) et figures optionnelles.

Chaque grandeur porte son unité, le champ et la composante dont elle est lue, et le
repère (global ou local de l'élément). Les repères locaux viennent de la
documentation, pas d'une supposition : sources citées dans `FRAMES`.

Lot 41 : les textes écrits dans la synthèse gardent le nom des modules au lot 37
(`aster_expert.report.*`, déplacés depuis dans ce projet), pour que la synthèse
reste identique octet pour octet (restructuration neutre).
"""

from __future__ import annotations

import importlib.util
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from quai_cw_test_01.report import quantities as q
from quai_cw_test_01.report.build import (
    BAND_LAYER,
    CaseSummary,
    Synthesis,
    TubeSectionProfile,
)

if TYPE_CHECKING:
    from quai_cw_test_01.report.figures import FigureFile

KN = 1.0e3
MM = 1.0e3

#: (grandeur, champ, composantes, repère, unité, source du repère)
FRAMES: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "Déplacement horizontal (tête, profils)",
        "DEPL",
        "DY",
        "global : X le long du quai de SYM_G vers SYM_D, Y vers la terre, Z ascendant "
        "(décision du point 9) ; DY < 0 : vers le bassin",
        "mm",
        "fiche, point 9",
    ),
    (
        "Effort axial d'un tirant",
        "EFGE_ELNO",
        "N",
        "local de la barre (axe du tirant) ; N > 0 en traction",
        "kN",
        "U2.01.05 (efforts de poutre en repère « utilisateur »)",
    ),
    (
        "Efforts généralisés d'un tube (DKT)",
        "EFGE_ELNO (par élément et par nœud, sans moyenne)",
        "NXX, NYY, MXX, MYY",
        "local « utilisateur » de la facette : x_l = projection de "
        "VECTEUR = (0, 0, 1) sur le plan de la facette, donc **verticale** ; "
        "z_l = normale ; y_l = z_l ^ x_l (tangente horizontale). NXX et MXX : "
        "effort normal et moment de flexion "
        "**verticaux** ; NYY et MYY : circonférentiels",
        "kN/m ; kN·m/m (par mètre de largeur)",
        "U4.42.01, mot clé COQUE, opérande ANGL_REP / VECTEUR ; U2.01.05",
    ),
    (
        "Efforts généralisés d'une palplanche (ELAS_COQUE)",
        "EFGE_NOEU uniquement (décision 2)",
        "NXX, NYY, NXY, MXX, MYY, MXY, QX, QY",
        "local « utilisateur » : x_l = projection de VECTEUR = L (voir ci-dessous) "
        "sur le plan de la palplanche (plan Y = 0) ; moyenne arithmétique aux nœuds "
        "des valeurs par élément, restreinte aux mailles PALPS",
        "kN/m ; kN·m/m",
        "U4.42.01 COQUE ; U2.01.05 ; fiche, point 1 (décision 2)",
    ),
    (
        "Efforts d'une poutre de couronnement (POU_D_T)",
        "EFGE_ELNO (par élément et par nœud, sans moyenne)",
        "N, VY, VZ, MT, MFY, MFZ",
        "local de la poutre : x_l le long de l'élément (du premier au second nœud), "
        "y_l parallèle à Y global et z_l = x_l ^ y_l = Z global (repère par "
        "défaut, ANGL_VRIL = 0). MFY : moment de flexion dans le plan vertical "
        "(autour de y_l) ; MFZ : dans le plan horizontal",
        "kN ; kN·m",
        "U4.42.01, mot clé ORIENTATION (remarques) ; U2.01.05",
    ),
    (
        "Réactions d'appui",
        "REAC_NODA (RESULTANTE)",
        "DX, DY, DZ",
        "global ; seules les composantes bloquées comptent (ANCRAGES : DX, DY, DZ ; "
        "PIED_TUBES : DZ ; SYM_G, SYM_D : DX)",
        "kN",
        "lots 23 et 34 (constat de la fiche, points 1 et 8)",
    ),
    (
        "Force des ressorts sur l'écran",
        "DEPL/DY des nœuds à ressort × raideur",
        "−k·DY",
        "global, direction Y (positive vers la terre)",
        "kN",
        "fiche, point 4 ; K_T_D_N = (0, k, 0)",
    ),
)


def _kn(value: float) -> str:
    return f"{value / KN:.3f}"


def _mm(value: float) -> str:
    return f"{value * MM:.4f}"


def _place(e: q.Extremum) -> str:
    where = f"z = {e.z:.3f} m, x = {e.x:.3f} m, y = {e.y:.3f} m"
    parts = [where]
    if e.holder:
        parts.append(e.holder)
    if e.element:
        parts.append(f"maille {e.element}")
    if e.node:
        parts.append(f"nœud {e.node}")
    return " ; ".join(parts)


def _pair_table(pairs: list[q.ExtremaPair], unit: str, scale: float) -> list[str]:
    lines = [
        f"| Composante | Maximum ({unit}) | Lieu du maximum | Minimum ({unit}) "
        "| Lieu du minimum |",
        "|---|---:|---|---:|---|",
    ]
    for pair in pairs:
        lines.append(
            f"| {pair.component} | {pair.maximum.value / scale:.3f} "
            f"| {_place(pair.maximum)} | {pair.minimum.value / scale:.3f} "
            f"| {_place(pair.minimum)} |"
        )
    return lines


def _tie_anchor_line(check: q.TieAnchorCheck) -> str:
    vertical = (
        "sous pesanteur l'ancrage porte en plus une part du poids propre du tirant : "
        "l'écart vertical n'est pas un défaut de lecture"
        if check.gravity
        else "exacte hors pesanteur"
    )
    return (
        "Lecture croisée (statique du nœud d'ancrage) : Σ N × cos θ = "
        f"{_kn(check.ties_dy_n)} kN contre {_kn(check.anchor_dy_n)} kN de réaction "
        f"d'ancrage selon Y (écart relatif {check.gap_dy:.1e}) ; Σ N × sin θ = "
        f"{_kn(check.ties_dz_n)} kN contre {_kn(check.anchor_dz_n)} kN selon Z (écart "
        f"relatif {check.gap_dz:.1e}, {vertical})."
    )


def _case_section(case: CaseSummary) -> list[str]:
    head = case.head
    lines = [
        f"### Cas élémentaire {case.case}",
        "",
        "**Déplacement horizontal en tête d'écran** (`DEPL`, `DY`, repère global) : "
        f"maximum en valeur absolue {_mm(head.max_abs.value)} mm, "
        f"{_place(head.max_abs)}. Étendue sur les {head.n_nodes} nœuds des "
        f"anneaux de tête : de {_mm(head.minimum.value)} à "
        f"{_mm(head.maximum.value)} mm.",
        "",
        "**Effort axial dans chaque tirant** (`EFGE_ELNO`, `N`, repère local de "
        "la barre, kN ; > 0 en traction) :",
        "",
        "| Tirant (tube) | X (m) | N (kN) | N minimal | N maximal |",
        "|---:|---:|---:|---:|---:|",
    ]
    for tie in case.ties:
        lines.append(
            f"| {tie.tie} | {tie.x:.3f} | {_kn(tie.n)} | {_kn(tie.minimum)} "
            f"| {_kn(tie.maximum)} |"
        )
    lines += [
        "",
        "**Efforts généralisés extrêmes dans les tubes** (`EFGE_ELNO`, repère local "
        "« utilisateur » de la facette, x_l vertical ; kN/m et kN·m/m) :",
        "",
        *_pair_table(case.tubes[:], "kN/m ou kN·m/m", KN),
        "",
        "**Efforts généralisés extrêmes dans les palplanches** (`EFGE_NOEU`, repère "
        "local « utilisateur » ; kN/m et kN·m/m) :",
        "",
        *_pair_table(case.palps, "kN/m ou kN·m/m", KN),
        "",
    ]
    if case.beam is not None:
        lines += [
            "**Moments et efforts extrêmes dans la poutre de couronnement** "
            "(`EFGE_ELNO`, repère local de la poutre ; kN et kN·m) :",
            "",
            *_pair_table(case.beam, "kN ou kN·m", KN),
            "",
        ]
    lines += [
        "**Réactions** (`REAC_NODA`, résultante, repère global, kN ; composantes "
        "bloquées en gras) :",
        "",
        "| Groupe | DX | DY | DZ |",
        "|---|---:|---:|---:|",
    ]
    for r in case.reactions:
        cells = [
            f"**{_kn(v)}**" if name in r.blocked else _kn(v)
            for name, v in (("DX", r.dx), ("DY", r.dy), ("DZ", r.dz))
        ]
        lines.append(f"| {r.group} | {cells[0]} | {cells[1]} | {cells[2]} |")
    lines += [
        "",
        _tie_anchor_line(case.tie_anchor),
        "",
        "Somme des ressorts par couche (force exercée sur l'écran selon Y, "
        "−Σ k·DY, kN) : "
        + " ; ".join(
            f"{BAND_LAYER[b]} {_kn(v)}"
            for b, v in sorted(case.springs.layer_forces_n.items())
        )
        + f" ; total {_kn(case.springs.total_force_n)}.",
        "",
    ]
    return lines


def _spring_control_section(cases: list[CaseSummary]) -> list[str]:
    """Contrôles de validité de la décision 5 (domaine de validité, items 1 et 2),
    par cas élémentaire. Constats sur le domaine du modèle linéaire, non des
    vérifications de l'ouvrage."""
    lines = [
        "## Contrôles de validité de la décision 5 (cas élémentaires)",
        "",
        "Ces contrôles portent sur des cas **élémentaires** : ils ne constituent "
        "pas une vérification de l'ouvrage (aucune combinaison n'est décidée dans "
        "la fiche) et ne portent aucun verdict de dimensionnement. Un dépassement "
        "est un constat sur les limites du modèle linéaire des ressorts.",
        "",
        "### Signe : le ressort est en compression lorsque l'écran va vers le bassin "
        "(DY < 0)",
        "",
        "| Cas | Nœuds | En compression | En traction | Cotes des nœuds en traction "
        "(m) | Réaction de traction maximale (kN) | Lieu |",
        "|---|---:|---:|---:|---|---:|---|",
    ]
    for c in cases:
        s = c.springs.sign
        if s.n_tension:
            zs = f"{s.z_min_tension:.3f} à {s.z_max_tension:.3f}"
            worst = _kn(s.max_tension_reaction_n or 0.0)
            at = _place(s.at_max_tension) if s.at_max_tension else ""
        else:
            zs, worst, at = "-", "-", "-"
        lines.append(
            f"| {c.case} | {s.n_nodes} | {s.n_compression} | {s.n_tension} | {zs} "
            f"| {worst} | {at} |"
        )
    lines += [
        "",
        "### Butée : pression de réaction k·abs(DY) / A comparée à σ'p(z)",
        "",
        "La force de butée d'un nœud est Σ (aire tributaire de chaque bande × σ'p de "
        "la couche de la bande à la cote du nœud), σ'p interpolée linéairement "
        "(`donnees_butee_combiwall_v1.md`) ; la pression initiale au repos n'est pas "
        "ajoutée (non modélisée, décision 5, item 3). Taux = force de réaction / force "
        "de butée.",
        "",
        "| Cas | Nœuds comprimés | Taux maximal | Cote (m) | Porteur "
        "| Pression k·abs(DY)/A (kPa) | σ'p (kPa) | Nœuds au-delà de 100 % "
        "| Porteurs concernés |",
        "|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for c in cases:
        b = c.springs.bearing
        if b.at_max is None:
            lines.append(f"| {c.case} | 0 | - | - | - | - | - | 0 | - |")
            continue
        lines.append(
            f"| {c.case} | {b.n_compressed} | {100 * b.max_ratio:.2f} % "
            f"| {b.at_max.z:.3f} | {b.at_max.holder or '-'} "
            f"| {b.max_pressure_kpa:.2f} | {b.limit_kpa:.2f} | {b.n_over_100} "
            f"| {', '.join(b.n_over_100_holders) or '-'} |"
        )
    lines.append("")
    return lines


def _profile_section(synthesis: Synthesis) -> list[str]:
    lines = [
        "## Profils du déplacement horizontal DY le long des tubes",
        "",
        "`DEPL`, `DY`, repère global, en mm (< 0 vers le bassin). Chaque valeur est la "
        "**moyenne de DY sur l'anneau de nœuds** du tube à la cote donnée ; l'étendue "
        "(minimum à maximum sur l'anneau) figure entre parenthèses.",
        "",
    ]
    cases = [c.case for c in synthesis.cases]
    for profile in synthesis.profiles:
        lines += [
            f"### {profile.label}",
            "",
            "| Cote (m) | " + " | ".join(cases) + " |",
            "|---:|" + "---:|" * len(cases),
        ]
        zs = [p.z for p in profile.by_case[cases[0]]]
        for i, z in enumerate(zs):
            cells = []
            for case in cases:
                p = profile.by_case[case][i]
                cells.append(f"{_mm(p.mean)} ({_mm(p.minimum)} ; {_mm(p.maximum)})")
            lines.append(f"| {z:.3f} | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


KEY_LEVEL_COUNT = 5


def _section_forces_section(synthesis: Synthesis) -> list[str]:
    """Lot 37 : `N`, `M`, `T` de chaque tube de profil, comme une poutre."""
    if not synthesis.tube_sections:
        return []
    lines = [
        "## Efforts d'ensemble des tubes (le tube vu comme une poutre)",
        "",
        "Intégrales, sur la circonférence, des efforts de coque `EFGE_ELNO` à chaque "
        "cote (`aster_expert.report.sections` ; convention de U2.01.05, lue le jour "
        "du lot 37) : `N = ∫ NXX ds` (traction positive), `M = ∫ NXX·y ds` (moment "
        "d'axe X du tube, `y` distance à l'axe ; > 0 : traction côté terre), "
        "`T = ∫ (NXY·y_l + QX·n)·Y ds` (effort tranchant selon Y, force exercée par "
        "la partie haute sur la partie basse ; la part de `NXY` et celle de `QX` sont "
        "données à part). Les efforts de flexion de paroi (`MXX`) ne sont pas dans "
        "`M`. Valeur d'une cote : moyenne des estimations par le haut et par le bas "
        "(les efforts par élément aux nœuds ne sont pas continus d'une rangée à "
        "l'autre). Le tube de bord (`TUBE_01`) est un **demi-tube** dans un plan de "
        "symétrie : ses efforts sont ceux du demi-tube. Cas élémentaires ; aucun "
        "verdict.",
        "",
    ]
    cases = [c.case for c in synthesis.cases]
    for profile in synthesis.tube_sections:
        half = " (demi-tube, plan de symétrie)" if profile.half_tube else ""
        lines += [f"### {profile.label}{half}", ""]
        for case in cases:
            levels = profile.by_case[case]
            top = max(levels, key=lambda lv: lv.z)
            extremes = {
                "N": max(levels, key=lambda lv: abs(lv.mean.n)),
                "M": max(levels, key=lambda lv: abs(lv.mean.mx)),
                "T": max(levels, key=lambda lv: abs(lv.mean.ty)),
            }
            lines += [
                f"**{case}** — extrêmes : "
                f"N (plus grande valeur absolue) = {_kn(extremes['N'].mean.n)} kN à "
                f"{extremes['N'].z:g} m ; M = {_kn(extremes['M'].mean.mx)} kN·m à "
                f"{extremes['M'].z:g} m ; T = {_kn(extremes['T'].mean.ty)} kN à "
                f"{extremes['T'].z:g} m "
                f"(tête du tube : {top.z:g} m).",
                "",
            ]
        wanted = _key_levels(profile, synthesis.dredge_z)
        lines += [
            "| Cote (m) | Cas | N (kN) | M (kN·m) | T (kN) | dont NXY | dont QX |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
        for z in wanted:
            for case in cases:
                lv = next(v for v in profile.by_case[case] if v.z == z)
                m = lv.mean
                lines.append(
                    f"| {z:.2f} | {case} | {_kn(m.n)} | {_kn(m.mx)} | {_kn(m.ty)} "
                    f"| {_kn(m.ty_nxy)} | {_kn(m.ty_qx)} |"
                )
        lines.append("")
    return lines


def _key_levels(profile: TubeSectionProfile, dredge_z: float | None) -> list[float]:
    """Cotes du tableau : tête, 0, la première rangée au-dessus du dragage, le
    dragage, la limite de la bande de tubes seuls, le pied."""
    zs = sorted({lv.z for lv in next(iter(profile.by_case.values()))})
    picks = [zs[-1], 0.0, zs[0]]
    if dredge_z is not None:
        above = [z for z in zs if z > dredge_z + 1.0e-6]
        picks += [min(above), dredge_z, -18.0]
    return sorted({z for z in picks if z in zs}, reverse=True)


def _section_statics_section(synthesis: Synthesis) -> list[str]:
    """Lot 37 : statique des efforts d'ensemble à la première rangée au-dessus du
    dragage."""
    if not synthesis.section_statics:
        return []
    z = synthesis.section_check_z
    lines = [
        "## Statique des efforts d'ensemble à la cote de dragage",
        "",
        f"Cote de la coupure : {z:g} m, première rangée au-dessus du dragage "
        f"({synthesis.dredge_z:g} m) : la rangée du dragage porte les forces nodales "
        "des premiers ressorts, ce qui rend la coupure ambiguë "
        "(`aster_expert.report.section_statics`). Le corps inférieur (sous la coupure) "
        "est en équilibre sous la poussée, les ressorts, les réactions du pied et le "
        "poids ; la force que la partie haute exerce sur lui est l'opposée de leur "
        "somme. *Mesuré* : intégrale des efforts de coque (tubes et palplanches). "
        "*Attendu* : statique du corps inférieur. Écart = |mesuré − attendu| / "
        "max(|mesuré|, |attendu|). Grandeur **sensible à la discrétisation** "
        "(extrapolation des efforts par élément aux nœuds), non exacte : voir "
        "`docs/essais_lot37.md` pour le critère.",
        "",
        "| Cas | Portée | T mesuré (kN) | T attendu (kN) | écart T | M mesuré (kN·m) "
        "| M attendu (kN·m) | écart M | N mesuré (kN) | N attendu (kN) | écart N |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for c in synthesis.section_statics:

        def pct(value: float | None) -> str:
            return "—" if value is None else f"{100.0 * value:.2f} %"

        lines.append(
            f"| {c.case} | {c.scope} | {_kn(c.t_y.measured)} | {_kn(c.t_y.expected)} "
            f"| {pct(c.t_y.relative_gap)} | {_kn(c.m_x.measured)} "
            f"| {_kn(c.m_x.expected)} | {pct(c.m_x.relative_gap)} "
            f"| {_kn(c.n_z.measured)} | {_kn(c.n_z.expected)} "
            f"| {pct(c.n_z.relative_gap)} |"
        )
    lines.append("")
    return lines


def matplotlib_available() -> bool:
    return importlib.util.find_spec("matplotlib") is not None


def plot_profiles(synthesis: Synthesis, out_dir: Path) -> list[Path]:
    """Une figure PNG par profil (tube) si `matplotlib` est disponible ; sinon aucune
    (liste vide) : la synthèse porte alors les tableaux seuls."""
    if not matplotlib_available():
        return []
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for profile in synthesis.profiles:
        fig, ax = plt.subplots(figsize=(6, 8))
        for case, points in profile.by_case.items():
            ax.plot([p.mean * MM for p in points], [p.z for p in points], label=case)
        ax.set_xlabel("DY moyen sur l'anneau (mm, < 0 vers le bassin)")
        ax.set_ylabel("cote Z (m CM)")
        ax.set_title(f"Profil de DY le long de {profile.label} (cas élémentaires)")
        ax.grid(True)
        ax.legend()
        path = out_dir / f"profil_dy_{profile.label.lower()}.png"
        fig.savefig(path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        paths.append(path)
    return paths


def _level_d_section(level_d: dict[str, Any] | None) -> list[str]:
    if level_d is None:
        return [
            "## Contrôles de niveau D",
            "",
            "Non fournis à cette synthèse (option `--controles-d`).",
            "",
        ]
    lines = [
        "## Contrôles de niveau D (équilibre et symétrie)",
        "",
        f"Seuil : {level_d.get('threshold', '?'):g} (relatif). Bilan "
        "appliquée + réactions bloquées + ressorts = 0, par composante ; jamais un "
        "niveau E (aucune comparaison à une référence validée).",
        "",
        "| Cas | X | Y | Z | Verdict |",
        "|---|---:|---:|---:|---|",
    ]
    rows = [
        (case, block, block["verdict"])
        for case, block in level_d.get("cases", {}).items()
    ] + [
        (case, block, "informatif (aucun critère)")
        for case, block in level_d.get("informative_cases", {}).items()
    ]
    for case, block, verdict in rows:
        comps = block["components"]
        gaps = [f"{comps[c]['relative_gap']:.2e}" for c in ("DX", "DY", "DZ")]
        lines.append(f"| {case} | {gaps[0]} | {gaps[1]} | {gaps[2]} | {verdict} |")
    sym = level_d.get("symmetry", {})
    if sym:
        lines += [
            "",
            "Symétrie des déplacements (paires de nœuds miroir), pire écart relatif :",
            "",
            "| Cas | Paires vérifiées | Sans image miroir | Pire écart relatif |",
            "|---|---:|---:|---:|",
        ]
        for case, block in sym.items():
            lines.append(
                f"| {case} | {block['n_pairs_checked']} | {block['n_unmatched']} "
                f"| {block['worst_relative_gap']:.2e} |"
            )
    lines.append("")
    return lines


def render_controls(synthesis: Synthesis) -> str:
    """Le tableau des contrôles (fichier distinct de la synthèse) : contrôles de
    validité de la décision 5 par cas, puis contrôles de niveau D. Mêmes tableaux que
    la synthèse, sans le reste."""
    lines = [
        f"# Contrôles — {synthesis.project}",
        "",
        *_spring_control_section(synthesis.cases),
        *_section_statics_section(synthesis),
        *_level_d_section(synthesis.level_d),
    ]
    return "\n".join(lines) + "\n"


def _provenance_lines(synthesis: Synthesis) -> list[str]:
    prov = synthesis.provenance
    if not prov.med_read:
        return [
            f"- Listing : `{prov.mess_path}` (SHA-256 `{prov.mess_sha256}`)",
            "- Le MED de résultats **n'est pas relu** : chaque grandeur vient d'une "
            "table imprimée du listing, traçable à une commande du `.comm`.",
        ]
    lines = [
        f"- **MED de résultats** : `{prov.med_path}` (SHA-256 `{prov.med_sha256}`), "
        "relu par `medcoupling` dans le conteneur : chaque grandeur de cette synthèse "
        "vient de ses champs."
    ]
    if prov.mess_path and prov.cross_check_max is not None:
        lines.append(
            f"- Contre-vérification : listing `{prov.mess_path}` (SHA-256 "
            f"`{prov.mess_sha256}`) ; écart relatif maximal entre le MED et les tables "
            f"imprimées, {len(prov.cross_check or {})} tables : "
            f"{prov.cross_check_max:.2e}."
        )
    else:
        lines.append(
            "- Aucun listing fourni : pas de contre-vérification par le `.mess`."
        )
    return lines


def _views_section(views: Sequence[FigureFile], base: Path | None) -> list[str]:
    """Les vues du lot 36, groupées par cas élémentaire, images insérées."""
    lines = ["## Vues (PNG, lues dans le MED de résultats)", ""]
    lines += [
        "Projections 2D produites par `aster_expert.report.figures` (matplotlib, sans "
        "interface : ParaVis hors interface est impossible ici, voir "
        "`docs/essais_lot36.md`). Repère : X le long du quai, Y vers la terre, Z "
        "ascendant. Aucune vue n'est un verdict : les limites de butée sont des "
        "constats sur le domaine du modèle linéaire.",
        "",
    ]
    cases = list(dict.fromkeys(v.case for v in views))
    for case in cases:
        lines += [f"### Cas {case}", ""]
        for view in (v for v in views if v.case == case):
            try:
                rel = view.path.relative_to(base) if base else view.path
            except ValueError:
                rel = Path(view.path.name)
            lines += [
                f"**{view.title}**",
                "",
                f"![{view.title} — cas {case}]({rel})",
                "",
            ]
    return lines


def render_synthesis(
    synthesis: Synthesis,
    figures: list[Path],
    views: Sequence[FigureFile] = (),
    views_base: Path | None = None,
) -> str:
    """Le document Markdown de la synthèse."""
    prov = synthesis.provenance
    comm_line = f"SHA-256 `{prov.comm_sha256}`" if prov.comm_sha256 else "non fourni"
    lines = [
        f"# Synthèse des résultats — {synthesis.project}",
        "",
        "## Ce que ce document est, et n'est pas",
        "",
        "- Des **résultats de cas élémentaires** (G, EAU_P, EAU_A, Q1, Q3, A), lus "
        + (
            "dans le MED de résultats de Code_Aster"
            if prov.med_read
            else "dans les tables imprimées par Code_Aster"
        )
        + ". Aucune combinaison n'est faite, "
        "aucun verdict de dimensionnement n'est porté : la fiche ne décide aucune "
        "combinaison.",
        "- Niveau de validation du calcul : C (exécuté jusqu'à `FIN`) avec contrôles D "
        "(voir plus bas) ; jamais E.",
        "- Les grandeurs sont **linéaires** (modèle élastique, ressorts sans "
        "plafond) : un dépassement de la butée est un constat sur les limites du "
        "modèle, non une rupture calculée.",
        "",
        "## Provenance",
        "",
        *_provenance_lines(synthesis),
        f"- `.comm` : {comm_line}",
        f"- Données : `{prov.data_path}`",
        "",
        "## Repères, champs et unités",
        "",
        "| Grandeur | Champ | Composantes | Repère | Unité | Source du repère |",
        "|---|---|---|---|---|---|",
    ]
    for row in FRAMES:
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "",
        "Axe L des palplanches (`VECTEUR`, repère global) : "
        f"{tuple(synthesis.palp_local_x)} (vertical). Tubes : `VECTEUR = (0, 0, 1)`.",
    ]
    if synthesis.beam_orientation_checked is not None:
        lines.append(
            "Orientation des éléments de poutre : "
            + (
                "chaque élément est listé du X le plus bas au plus haut, donc "
                "x_l = +X, y_l = +Y, z_l = +Z (déduit de l'ordre des lignes de la "
                "table, non de la documentation)."
                if synthesis.beam_orientation_checked
                else "au moins un élément est orienté vers -X : le signe de MFY, MT et "
                "VZ y est inversé par rapport au repère indiqué."
            )
        )
    lines += [
        "",
        f"Tubes : axes à X = {', '.join(f'{x:g}' for x in synthesis.axes_x)} m, rayon "
        f"{synthesis.radius:g} m ; « porteur » d'un point = tube (cercle de rayon R) "
        "ou palplanche (plan Y = 0) le portant.",
        "",
        "## Résultats par cas élémentaire",
        "",
    ]
    for case in synthesis.cases:
        lines += _case_section(case)
    lines += _spring_control_section(synthesis.cases)
    lines += _profile_section(synthesis)
    lines += _section_forces_section(synthesis)
    if views:
        lines += _views_section(views, views_base)
    if figures:
        lines += ["## Figures", ""]
        lines += [f"![{p.stem}]({p.name})" for p in figures]
        lines.append("")
    elif not views:
        lines += [
            "## Figures",
            "",
            "Aucune figure : la bibliothèque de tracé (`matplotlib`) n'est pas "
            "disponible dans l'environnement du projet ; les profils sont donnés en "
            "tableaux ci-dessus.",
            "",
        ]
    lines += _section_statics_section(synthesis)
    lines += _level_d_section(synthesis.level_d)
    return "\n".join(lines) + "\n"
