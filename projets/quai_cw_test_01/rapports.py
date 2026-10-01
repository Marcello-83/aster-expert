"""Prose des rapports propres au quai (lot 41) : ce que le tronc commun
(`aster_expert.combinaisons`, `aster_expert.ferraillage`) calcule, mis en forme
avec le vocabulaire et les décisions de ce projet (repère du point 9, section de
la poutre de couronnement, D17 à D19). Textes repris tels quels des scripts des
lots 38 et 39 (`build_lot38_export.py`, `analyze_lot39_poutre.py`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, cast

from aster_expert.combinaisons.efforts import CombinedForces
from aster_expert.ferraillage.poutre import FACES, RebarResult
from aster_expert.projet.context import ProjectContext
from aster_expert.projet.errors import ProjectError


def _same_bytes(a: Path, b: Path) -> bool:
    return (
        hashlib.sha256(a.read_bytes()).digest()
        == hashlib.sha256(b.read_bytes()).digest()
    )


def combinations_report(
    ctx: ProjectContext,
    result: CombinedForces,
    *,
    comm_path: Path,
    run_comm_path: Path,
    **_: Path,
) -> dict[str, str]:
    """`poutre_couronnement.md` : combinaisons de D17 appliquées à la poutre de
    couronnement. Le `.comm` exécuté doit être celui du projet, octet pour octet :
    la phrase de provenance le dit, elle est donc vérifiée."""
    if not _same_bytes(comm_path, run_comm_path):
        message = (
            f"le .comm exécuté ({run_comm_path}) diffère du .comm du projet "
            f"({comm_path}) : provenance des efforts non établie"
        )
        raise ProjectError(message)
    root = ctx.repo_root
    check = result.manual_check
    assert check is not None
    components = result.forces.components
    lines = [
        "# Poutre de couronnement -- combinaisons de D17 (lot 38)",
        "",
        f"Source : `{result.mess_path.relative_to(root)}` -- {result.diagnostic}. "
        f"`.comm` exécuté identique (sha256) à `{comm_path.relative_to(root)}`, "
        "inchangé par le lot 38 : aucune nouvelle exécution.",
        "",
        "## Repère et conventions de signe",
        "",
        "Repère global (décision du point 9) : X le long du quai (SYM_G -> SYM_D), "
        "Y vers la terre, Z ascendant, origine dans l'axe de TUBE_05 à la cote "
        "0,00 CM. `N, VY, VZ, MT, MFY, MFZ` sont les composantes de `EFGE_ELNO` "
        "dans le repère « utilisateur » de la poutre (`POU_D_T`, axe porteur x_l "
        "= +X, U2.01.05 « Cas des poutres ») : N effort normal (traction "
        "positive), VY/VZ efforts tranchants, MT moment de torsion, MFY/MFZ "
        "moments de flexion. `EFGE_ELNO` n'étant pas moyenné par Code_Aster, les "
        "deux valeurs d'un nœud intérieur (une par élément adjacent) sont "
        "moyennées ici pour la lisibilité -- une simplification, jamais un "
        "contrôle d'équilibre.",
        "",
        "## Géométrie de section et données D18",
        "",
        "Section rectangulaire : HY = 2,50 m (largeur), HZ = 1,40 m (hauteur), "
        "axe à Y = 0,34 m, Z = 3,30 m. Béton C35/45, acier B500B, classe "
        "d'exposition XS3, durée d'utilisation 100 ans, enrobage nominal 65 mm, "
        "wk = 0,2 mm sous combinaison quasi permanente (décision D18, point 14).",
        "",
        f"## Combinaisons ({len(result.combinations)}, décision D17, point 13)",
        "",
        "| Nom | Famille | Coefficients |",
        "| --- | --- | --- |",
    ]
    for combination in result.combinations:
        coeffs = ", ".join(
            f"{case}={value:g}" for case, value in combination.coefficients.items()
        )
        lines.append(f"| `{combination.name}` | {combination.family} | {coeffs} |")
    lines += [
        "",
        "## Contrôle manuel",
        "",
        f"Combinaison `{check['combination']}` (ELU fondamentale, Q3 dominante, "
        f"sans Q1, γG défavorable), nœud {check['node']} (bollard, X ≈ 0) : "
        "1,35·(G+EAU_P) + 1,5·Q3, recalculé à la main à partir des tables "
        f"élémentaires du `.mess`, contre `combine()` -- écart absolu maximal "
        f"{check['max_absolute_gap']:.3e} (unités N, N.m).",
        "",
        "| Composante | À la main | `combine()` | Écart |",
        "| --- | --- | --- | --- |",
    ]
    for comp in components:
        lines.append(
            f"| {comp} | {check['hand'][comp]:.6e} | {check['code'][comp]:.6e} | "
            f"{abs(check['hand'][comp] - check['code'][comp]):.3e} |"
        )
    lines += [
        "",
        "## Extrema",
        "",
        "Voir `extrema.csv` : pour chaque combinaison, le nœud où chaque "
        "composante est maximale en valeur absolue, avec les composantes "
        "concomitantes.",
        "",
    ]
    return {"poutre_couronnement.md": "\n".join(lines) + "\n"}


COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
"""Categorical slots 1-4 of the dataviz reference palette, fixed order."""


def _write_markdown(
    out_dir: Path,
    xs: list[float],
    all_env: dict[float, dict[str, float]],
    governing: dict[float, dict[str, str]],
    mins: dict[str, dict[str, float | bool]],
    shear_x: dict[float, dict[str, float]],
    rho_w: float,
    hy: float,
    hz: float,
) -> None:
    """`synthese.md`: the final table per abscissa, in cm2 and cm2/m."""
    short = {
        "ELU fondamentale": "ELU F",
        "ELU accidentelle": "ELU A",
        "ELS caractéristique": "ELS C",
        "ELS quasi permanente": "ELS QP",
    }
    lines = [
        "# Poutre de couronnement — ferraillage par section (lot 39, premier jet)",
        "",
        "Aires **calculées** sous les hypothèses de la fiche (D17, D18, D19) : aucun "
        "verdict de conformité. cm² pour les aciers longitudinaux, cm²/m pour les "
        "cadres. « CF » : enveloppe de `CALC_FERRAILLAGE` sur les 14 combinaisons "
        "(famille dimensionnante entre parenthèses) ; « retenu » = max(CF, As,min "
        "9.2.1.1, As,min 7.3.2), appliqué à chaque face comme `FERR_MIN` de "
        "Code_Aster le fait (majorant : 9.2.1.1 et 7.3.2 visent les zones tendues).",
        "",
        "Minima (EN 1992-1-1, `aster_expert.rebar.minimum`) :",
        "",
        "| Faces | b (m) | h (m) | d (m) | As,min 9.2.1.1 (cm²) | φ*s (mm) | σs (MPa) "
        "| As,min 7.3.2 (cm²) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for faces in ("AY", "AZ"):
        m = mins[faces]
        bound = " (borné : hors du tableau 7.2N)" if m["sigma_s_borne_tableau"] else ""
        lines.append(
            f"| {faces}S / {faces}I | {float(m['b_m']):.2f} | {float(m['h_m']):.2f} "
            f"| {float(m['d_m']):.2f} | {float(m['as_min_9_2_1_1']) * 1e4:.2f} "
            f"| {float(m['phi_star_mm']):.2f} | {float(m['sigma_s_MPa']):.1f}{bound} "
            f"| {float(m['as_min_7_3_2']) * 1e4:.2f} |"
        )
    lines += [
        "",
        "7.3.2 : kc = 0,4 (flexion simple), k = 0,65 (h ≥ 0,80 m), fct,eff = fctm = "
        "3,21 MPa, Act = b h/2, σs lu dans le tableau 7.2N (wk = 0,2 mm) pour le "
        "diamètre de référence φ*s déduit de φ = 40 mm (D19) par l'expression "
        "(7.6N) avec hcr = h/2 et h − d = 0,10 m. Tableau 7.2N transcrit par la "
        "session : à vérifier sur l'exemplaire de la norme de MM.",
        "",
        f"Cadres minimaux (9.2.2(5)) : ρw,min = {rho_w:.4e}, soit "
        f"{rho_w * hz * 1e4:.2f} cm²/m pour bw = 1,40 m (effort VY) et "
        f"{rho_w * hy * 1e4:.2f} cm²/m pour bw = 2,50 m (effort VZ).",
        "",
        "| X (m) | AYS CF | AYI CF | AZS CF | AZI CF | AYS retenu | AYI retenu "
        "| AZS retenu | AZI retenu | AST CF | Asw/s VY (EN) | Asw/s VZ (EN) "
        "| At/s torsion par brin (EN) | Asl torsion (EN, cm²) | bielle (6.29) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- "
        "| --- | --- | --- |",
    ]
    for x in xs:
        env = all_env[x]
        cells = []
        for f in FACES:
            fam = f" ({short[governing[x][f]]})" if env[f] > 1e-9 else ""
            cells.append(f"{env[f] * 1e4:.2f}{fam}")
        retained = [
            max(
                env[f],
                float(mins[f[:2]]["as_min_9_2_1_1"]),
                float(mins[f[:2]]["as_min_7_3_2"]),
            )
            * 1e4
            for f in FACES
        ]
        s = shear_x[x]
        lines.append(
            f"| {x:+.3f} | "
            + " | ".join(cells)
            + " | "
            + " | ".join(f"{r:.2f}" for r in retained)
            + f" | {env['AST'] * 1e4:.2f} | {s['asw_s_y'] * 1e4:.2f} "
            f"| {s['asw_s_z'] * 1e4:.2f} | {s['at_s'] * 1e4:.2f} "
            f"| {s['asl_t'] * 1e4:.2f} | {s['bielle']:.3f} |"
        )
    lines += [
        "",
        "Effort tranchant et torsion (EN) : `aster_expert.rebar.shear`, enveloppe sur "
        "les 9 combinaisons ELU, cot θ = 2,5 si les bielles le permettent, "
        "z = 0,9 d ; « 0 » signifie que le béton seul suffit (6.31) — seules les "
        "armatures minimales s'appliquent alors. Critère de bielle : "
        "T/T_Rd,max + V/V_Rd,max (6.29), maximum des deux directions.",
        "",
    ]
    (out_dir / "synthese.md").write_text("\n".join(lines), encoding="utf-8")


def rebar_report(ctx: ProjectContext, result: RebarResult, out_dir: Path) -> None:  # noqa: ARG001
    """`synthese.md` (tableau final par abscisse) et `figures/as_x.png`
    (enveloppes As(X) par famille) de la poutre de couronnement (lot 39).

    La figure est tracée avec les réglages d'origine de matplotlib : celle du lot 39
    l'a été dans un processus neuf, alors que les vues de la synthèse du quai
    (`report/figures.py`) modifient `matplotlib.rcParams` à l'import et que
    `aster-expert projet <nom> tout` enchaîne les deux dans le même processus."""
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    original = {k: v for k, v in matplotlib.rcParamsOrig.items() if k != "backend"}
    with matplotlib.rc_context():
        matplotlib.rcParams.update(cast(Any, original))
        _rebar_report(result, out_dir)


def _rebar_report(result: RebarResult, out_dir: Path) -> None:
    import matplotlib.pyplot as plt  # noqa: PLC0415

    xs = result.xs
    envelope = result.envelope
    mins = result.minima
    families = result.families
    # Figure As(X): one panel per face, one line per family.
    (out_dir / "figures").mkdir(exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    titles = {
        "AYS": "AYS : face côté terre (+y), tendue par MFZ > 0",
        "AYI": "AYI : face côté bassin (−y), tendue par MFZ < 0",
        "AZS": "AZS : face supérieure (+z), tendue par MFY > 0",
        "AZI": "AZI : face inférieure (−z), tendue par MFY < 0",
    }
    for ax, face in zip(axes, FACES, strict=True):
        for color, family in zip(COLORS, families, strict=True):
            ys = [envelope[(x, family)][face] * 1e4 for x in xs]
            ax.plot(xs, ys, color=color, linewidth=2, label=family)
        m = mins[face[:2]]
        for key, style, text in (
            ("as_min_9_2_1_1", (0, (4, 3)), "As,min 9.2.1.1"),
            ("as_min_7_3_2", (0, (1, 2)), "As,min 7.3.2"),
        ):
            value = float(m[key]) * 1e4
            ax.axhline(value, color="#555555", linewidth=1, linestyle=style)
            ax.annotate(
                text,
                (xs[-1], value),
                xytext=(-4, 3),
                textcoords="offset points",
                ha="right",
                fontsize=8,
                color="#333333",
            )
        ax.set_title(titles[face], fontsize=10, loc="left")
        ax.set_ylabel("As (cm²)")
        ax.grid(axis="y", color="#dddddd", linewidth=0.6)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[-1].set_xlabel(
        "X (m) — le long du quai, de SYM_G vers SYM_D ; bollard en X = 0"
    )
    axes[0].legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    fig.suptitle(
        "Poutre de couronnement — enveloppes As(X) de CALC_FERRAILLAGE par famille (D17)\n"
        "section 2,50 × 1,40 m, axe des armatures à 0,10 m (D19) ; aires calculées, "
        "pas un verdict",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(out_dir / "figures" / "as_x.png", dpi=130)
    plt.close(fig)

    _write_markdown(
        out_dir,
        xs,
        result.all_env,
        result.governing,
        mins,
        result.shear_x,
        result.rho_w,
        result.values.hy,
        result.values.hz,
    )


__all__ = ["combinations_report", "rebar_report"]
