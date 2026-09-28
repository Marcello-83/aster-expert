"""Lot 39, étapes 3.2, 3.3 et 4 : lecture de `CALC_FERRAILLAGE` sur la poutre de
couronnement, enveloppes As(X), contre-vérification de trois sections par le
module indépendant, tableau de synthèse avec les minima et l'effort tranchant /
torsion calculés hors de Code_Aster.

Entrée : l'exécution de `data/examples/lot39_poutre/poutre.comm` (répertoire de
travail passé en argument, `.comm` exécuté comparé par sha256 au versionné).
Sorties dans `data/examples/lot39_poutre/` :

- `rapports/mess_ferr_extrait.txt` : diagnostic et table `FERR_POUTRE` du `.mess` ;
- `ferraillage.csv` : aires par combinaison et par section ;
- `enveloppes.csv` : enveloppe par abscisse X, par famille et par face ;
- `figures/as_x.png` : As(X) par face, une courbe par famille ;
- `controle_main.json` : contre-vérification des trois sections (critère 1e-6) ;
- `synthese.csv`, `synthese.md` : tableau final par abscisse.

Aucun verdict de conformité : des aires calculées sous les hypothèses de la
fiche.

Usage : python scripts/analyze_lot39_poutre.py <répertoire d'exécution>
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from aster_expert.rebar.biaxial import design_biaxial  # noqa: E402
from aster_expert.rebar.minimum import (  # noqa: E402
    as_min_crack_control,
    as_min_flexure,
    reference_bar_diameter,
    rho_w_min,
    size_factor_k,
    steel_stress_table_7_2n,
)
from aster_expert.rebar.model import Concrete, Rectangle, Steel  # noqa: E402
from aster_expert.rebar.shear import design_shear_torsion  # noqa: E402
from aster_expert.rebar.ultimate import design_ultimate  # noqa: E402

DIR = ROOT / "data" / "examples" / "lot39_poutre"
FACES = ("AYS", "AYI", "AZS", "AZI")
AREAS = (*FACES, "AST", "ATOT")
FAMILIES = (
    "ELU fondamentale",
    "ELU accidentelle",
    "ELS caractéristique",
    "ELS quasi permanente",
)
GAMMAS = {"ELU fondamentale": (1.5, 1.15), "ELU accidentelle": (1.2, 1.0)}
HY, HZ, COVER, PHI_MM, WK_MM = 2.50, 1.40, 0.10, 40.0, 0.2
FCK, FYK = 35.0, 500.0
CHECK_SECTIONS = {
    "bollard (X = 0)": 0.0,
    "mi-travée entre tubes (X = -1,30)": -1.3,
    "mi-travée entre tubes (X = +1,30)": 1.3,
    "plan de symétrie SYM_G (X = -10,40)": -10.4,
}
COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
"""Categorical slots 1-4 of the dataviz reference palette, fixed order."""


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def parse_table(mess: Path) -> dict[tuple[int, str], dict[str, float]]:
    """`{(instant, section): {AYS, ..., ATOT}}` from the `FERR_POUTRE` table."""
    lines = mess.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("##FERR_POUTRE"))
    header = lines[start + 1].split()
    out: dict[tuple[int, str], dict[str, float]] = {}
    for line in lines[start + 2 :]:
        if not line.strip() or line.startswith("#"):
            break
        cells = line.split()
        row = dict(zip(header, cells, strict=True))
        # The table prints the mesh cell number (1..128, the order of
        # poutre.mail), not its name M001..M128.
        section = f"S{int(row['MAILLE']):03d}"
        out[(round(float(row["INST"])), section)] = {a: float(row[a]) for a in AREAS}
    return out


def extract(mess: Path) -> str:
    lines = mess.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("##FERR_POUTRE"))
    end = start + 2
    while end < len(lines) and lines[end].strip() and not lines[end].startswith("#"):
        end += 1
    diag = [ln for ln in lines if "DIAGNOSTIC JOB" in ln]
    return "\n".join([*lines[start:end], "", *diag, ""])


def _materials(family: str) -> tuple[Concrete, Steel]:
    gamma_c, gamma_s = GAMMAS[family]
    return Concrete(fck=FCK, gamma_c=gamma_c, alpha_cc=1.0), Steel(
        fyk=FYK, gamma_s=gamma_s
    )


def hand_check(
    efforts: list[dict[str, str]],
    sections: dict[str, dict[str, str]],
    results: dict[tuple[int, str], dict[str, float]],
) -> list[dict[str, object]]:
    """Module vs `CALC_FERRAILLAGE` on every ELU combination at the check
    sections (all element ends meeting at each abscissa)."""
    checks: list[dict[str, object]] = []
    for label, x in CHECK_SECTIONS.items():
        names = [s for s, row in sections.items() if abs(float(row["x_m"]) - x) < 1e-9]
        for row in efforts:
            if row["section"] not in names or row["famille"] not in GAMMAS:
                continue
            concrete, steel = _materials(row["famille"])
            n, mfy, mfz = (float(row[c]) / 1e6 for c in ("N", "MFY", "MFZ"))
            design = design_biaxial(HY, HZ, COVER, concrete, steel, n, mfy, mfz)
            pivots = (
                design_ultimate(
                    Rectangle(width=HZ, depth=HY, cover_pos=COVER, cover_neg=COVER),
                    concrete,
                    steel,
                    n,
                    mfz,
                ).pivot,
                design_ultimate(
                    Rectangle(width=HY, depth=HZ, cover_pos=COVER, cover_neg=COVER),
                    concrete,
                    steel,
                    n,
                    mfy,
                ).pivot,
            )
            ca = results[(int(row["instant"]), row["section"])]
            module = {
                "AYS": design.ays,
                "AYI": design.ayi,
                "AZS": design.azs,
                "AZI": design.azi,
            }
            deviations = {}
            for face in FACES:
                a, b = ca[face], module[face]
                if max(abs(a), abs(b)) <= 1e-12:
                    deviations[face] = 0.0
                else:
                    deviations[face] = abs(b - a) / max(abs(a), abs(b))
            in_scope = all(p in ("A", "B", "none") for p in pivots) and not any(
                p == "C" for p in pivots
            )
            checks.append(
                {
                    "section": label,
                    "section_code_aster": row["section"],
                    "maille_poutre": int(sections[row["section"]]["maille"]),
                    "noeud_poutre": int(sections[row["section"]]["noeud"]),
                    "combinaison": row["combinaison"],
                    "N_MN": n,
                    "MFY_MNm": mfy,
                    "MFZ_MNm": mfz,
                    "pivots_z_y": list(pivots),
                    "iterations_bresler": design.iterations,
                    "code_aster": {f: ca[f] for f in FACES},
                    "module": module,
                    "ecart_relatif_max": max(deviations.values()),
                    "dans_le_critere": in_scope,
                    "reussite": (max(deviations.values()) <= 1e-6)
                    if in_scope
                    else None,
                }
            )
    return checks


def minima() -> dict[str, dict[str, float | bool]]:
    """As,min per face: 9.2.1.1 (9.1N) and 7.3.2 (7.1) with sigma_s from Table 7.2N
    through (7.6N) (phi = 40 mm, wk = 0,2 mm, kc = 0,4 pure bending, h_cr = h/2)."""
    concrete = Concrete(fck=FCK, gamma_c=1.5)
    fctm = concrete.fctm
    out: dict[str, dict[str, float | bool]] = {}
    for faces, width, depth in (("AY", HZ, HY), ("AZ", HY, HZ)):
        d = depth - COVER
        phi_star = reference_bar_diameter(
            PHI_MM, fct_eff=fctm, kc=0.4, h_cr=depth / 2.0, h_minus_d=COVER
        )
        sigma_s, bounded = steel_stress_table_7_2n(phi_star, WK_MM)
        act = width * depth / 2.0
        crack = as_min_crack_control(
            kc=0.4,
            k=size_factor_k(min(width, depth)),
            fct_eff=fctm,
            act=act,
            sigma_s=sigma_s,
        )
        out[faces] = {
            "b_m": width,
            "h_m": depth,
            "d_m": d,
            "as_min_9_2_1_1": as_min_flexure(width, d, fctm, FYK),
            "phi_star_mm": phi_star,
            "sigma_s_MPa": sigma_s,
            "sigma_s_borne_tableau": bounded,
            "act_m2": act,
            "as_min_7_3_2": crack,
        }
    return out


def shear_torsion(
    efforts: list[dict[str, str]], results: dict[tuple[int, str], dict[str, float]]
) -> dict[str, dict[str, float]]:
    """Per section, envelope over the ELU combinations of the EN 1992-1-1 module:
    links for VY (+ MT), for VZ (+ MT), longitudinal torsion steel, crushing ratio."""
    out: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "asw_s_y": 0.0,
            "asw_s_z": 0.0,
            "at_s": 0.0,
            "asl_t": 0.0,
            "bielle": 0.0,
        }
    )
    for row in efforts:
        if row["famille"] not in GAMMAS:
            continue
        concrete, steel = _materials(row["famille"])
        n, vy, vz, mt = (float(row[c]) / 1e6 for c in ("N", "VY", "VZ", "MT"))
        ca = results[(int(row["instant"]), row["section"])]
        env = out[row["section"]]
        for key, width, depth, v, as_l in (
            ("y", HZ, HY, vy, max(ca["AYS"], ca["AYI"])),
            ("z", HY, HZ, vz, max(ca["AZS"], ca["AZI"])),
        ):
            section = Rectangle(
                width=width, depth=depth, cover_pos=COVER, cover_neg=COVER
            )
            result = design_shear_torsion(
                section, concrete, steel, v_ed=v, t_ed=mt, n_comp=-n, as_l=as_l
            )
            env[f"asw_s_{key}"] = max(env[f"asw_s_{key}"], result.asw_s)
            env["at_s"] = max(env["at_s"], result.at_s)
            env["asl_t"] = max(env["asl_t"], result.asl_torsion)
            env["bielle"] = max(env["bielle"], result.crushing_ratio)
    return out


def _write_markdown(
    xs: list[float],
    all_env: dict[float, dict[str, float]],
    governing: dict[float, dict[str, str]],
    mins: dict[str, dict[str, float | bool]],
    shear_x: dict[float, dict[str, float]],
    rho_w: float,
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
        f"{rho_w * HZ * 1e4:.2f} cm²/m pour bw = 1,40 m (effort VY) et "
        f"{rho_w * HY * 1e4:.2f} cm²/m pour bw = 2,50 m (effort VZ).",
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
    (DIR / "synthese.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    run = Path(argv[1]).resolve()
    executed = run / "poutre.comm"
    versioned = DIR / "poutre.comm"
    assert (
        hashlib.sha256(executed.read_bytes()).hexdigest()
        == hashlib.sha256(versioned.read_bytes()).hexdigest()
    ), "le .comm exécuté diffère du versionné"
    mess = run / "proc.0" / "fort.6"
    (DIR / "rapports").mkdir(exist_ok=True)
    (DIR / "rapports" / "mess_ferr_extrait.txt").write_text(extract(mess), "utf-8")
    results = parse_table(mess)
    sections = {r["section"]: r for r in _read_csv(DIR / "sections.csv")}
    efforts = _read_csv(DIR / "efforts.csv")
    by_instant = {int(r["instant"]): (r["combinaison"], r["famille"]) for r in efforts}
    assert len(results) == len(efforts) == 14 * 128

    with (DIR / "ferraillage.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["instant", "combinaison", "famille", "section", "x_m", *AREAS])
        for (inst, sec), values in sorted(results.items()):
            combination, family = by_instant[inst]
            writer.writerow(
                [inst, combination, family, sec, sections[sec]["x_m"]]
                + [f"{values[a]:.12e}" for a in AREAS]
            )

    # Envelope per abscissa (all element ends at that X), family and area.
    xs = sorted({round(float(r["x_m"]), 6) for r in sections.values()})
    envelope: dict[tuple[float, str], dict[str, float]] = {}
    unresolved: list[tuple[int, str]] = []
    for (inst, sec), values in results.items():
        family = by_instant[inst][1]
        if any(values[a] < 0.0 for a in AREAS):
            unresolved.append((inst, sec))
        key = (round(float(sections[sec]["x_m"]), 6), family)
        current = envelope.setdefault(key, dict.fromkeys(AREAS, 0.0))
        for a in AREAS:
            current[a] = max(current[a], values[a])
    with (DIR / "enveloppes.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["x_m", "famille", *AREAS])
        for x in xs:
            for family in FAMILIES:
                values = envelope[(x, family)]
                writer.writerow([x, family] + [f"{values[a]:.12e}" for a in AREAS])

    # Figure As(X): one panel per face, one line per family.
    (DIR / "figures").mkdir(exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(10, 11), sharex=True)
    titles = {
        "AYS": "AYS : face côté terre (+y), tendue par MFZ > 0",
        "AYI": "AYI : face côté bassin (−y), tendue par MFZ < 0",
        "AZS": "AZS : face supérieure (+z), tendue par MFY > 0",
        "AZI": "AZI : face inférieure (−z), tendue par MFY < 0",
    }
    mins = minima()
    for ax, face in zip(axes, FACES, strict=True):
        for color, family in zip(COLORS, FAMILIES, strict=True):
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
    fig.savefig(DIR / "figures" / "as_x.png", dpi=130)
    plt.close(fig)

    checks = hand_check(efforts, sections, results)
    in_scope = [c for c in checks if c["dans_le_critere"]]
    failures = [c for c in in_scope if not c["reussite"]]
    (DIR / "controle_main.json").write_text(
        json.dumps(
            {
                "critere": "1e-6 relatif (1e-12 m² absolu pour une aire nulle), "
                "pivots A et B, combinaisons ELU fondamentale et accidentelle",
                "nombre_de_comparaisons": len(checks),
                "dans_le_critere": len(in_scope),
                "echecs": len(failures),
                "ecart_relatif_max_dans_le_critere": max(
                    (float(c["ecart_relatif_max"]) for c in in_scope),
                    default=None,  # type: ignore[arg-type]
                ),
                "comparaisons": checks,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    # Final table per abscissa.
    shear = shear_torsion(efforts, results)
    all_env: dict[float, dict[str, float]] = {}
    for x in xs:
        all_env[x] = {a: max(envelope[(x, f)][a] for f in FAMILIES) for a in AREAS}
    governing: dict[float, dict[str, str]] = {}
    for x in xs:
        governing[x] = {
            a: max(FAMILIES, key=lambda f, a=a: envelope[(x, f)][a]) for a in FACES
        }
    shear_x: dict[float, dict[str, float]] = {}
    for sec, row in sections.items():
        x = round(float(row["x_m"]), 6)
        current = shear_x.setdefault(x, dict.fromkeys(shear[sec], 0.0))
        for k, v in shear[sec].items():
            current[k] = max(current[k], v)
    rho_w = rho_w_min(FCK, FYK)
    header = [
        "x_m",
        *(f"{f}_calc_ferraillage" for f in FACES),
        *(f"{f}_famille" for f in FACES),
        "As_min_AY_9_2_1_1",
        "As_min_AY_7_3_2",
        "As_min_AZ_9_2_1_1",
        "As_min_AZ_7_3_2",
        *(f"{f}_retenu" for f in FACES),
        "AST_calc_ferraillage_m2_par_m",
        "Asw_s_VY_EN_m2_par_m",
        "Asw_s_VZ_EN_m2_par_m",
        "At_s_torsion_par_brin_EN_m2_par_m",
        "Asw_s_min_9_2_2_bw_1_40",
        "Asl_torsion_EN_m2",
        "critere_bielle_EN",
    ]
    rows = []
    for x in xs:
        env = all_env[x]
        retained = {
            f: max(
                env[f],
                float(mins[f[:2]]["as_min_9_2_1_1"]),
                float(mins[f[:2]]["as_min_7_3_2"]),
            )
            for f in FACES
        }
        s = shear_x[x]
        rows.append(
            [
                x,
                *(env[f] for f in FACES),
                *(governing[x][f] for f in FACES),
                mins["AY"]["as_min_9_2_1_1"],
                mins["AY"]["as_min_7_3_2"],
                mins["AZ"]["as_min_9_2_1_1"],
                mins["AZ"]["as_min_7_3_2"],
                *(retained[f] for f in FACES),
                env["AST"],
                s["asw_s_y"],
                s["asw_s_z"],
                s["at_s"],
                rho_w * HZ,
                s["asl_t"],
                s["bielle"],
            ]
        )
    with (DIR / "synthese.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for r in rows:
            writer.writerow([f"{v:.6e}" if isinstance(v, float) else v for v in r])
    _write_markdown(xs, all_env, governing, mins, shear_x, rho_w)
    summary = {
        "sections": len(sections),
        "instants": 14,
        "aires_negatives_non_resolues": len(unresolved),
        "minima": mins,
        "controle_main": {
            "comparaisons": len(checks),
            "dans_le_critere": len(in_scope),
            "echecs": len(failures),
        },
        "max_par_face_toutes_familles": {
            f: max(all_env[x][f] for x in xs) for f in (*FACES, "AST")
        },
        "max_bielle": max(shear_x[x]["bielle"] for x in xs),
        "max_asl_torsion": max(shear_x[x]["asl_t"] for x in xs),
    }
    (DIR / "resume.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
