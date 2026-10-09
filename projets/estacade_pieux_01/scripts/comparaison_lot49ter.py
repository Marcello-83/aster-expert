"""Lot 49 ter -- comparison with the source model and profile of the slab hogging zone.

docs/essais_lot49ter.md, § 2.12. Reads the engineering summary just produced
(`resultats/livrables/paquet/synthese_ingenieur.json`) and, for what it does not
hold, the deliverables through the trunk (`aster_expert.livrables`), never a value
typed by hand. Writes:

- `resultats/livrables/paquet/comparaison_externe.json`: the tables of the sheet
  « Comparaison externe » (point, place, component, family, limit state, source,
  Code_Aster, gap, attribution A to G -- rule of the comparison points of lot 47
  quater);
- `resultats/livrables/paquet/comparaison/profil_chapeau.csv` and `.png`: MXX across
  the cap beam of the governing line, at Y = 0 and ±1.00, from the axis to 1.00 m,
  combination 111 (ELU+, ELS c, ELS f), envelope of the moving positions;
- `references/comparaison_externe_lot49ter.json` (versioned copy).

Values of the source (C1 to C13): `references/comparaison_v2_lot47bis.json`; the
supervisor's table (consigne of lot 49 ter) is checked line by line against them.

Run after `aster-expert projet estacade_pieux_01 livrables --sous-etape ingenieur`:
`.venv/bin/python projets/estacade_pieux_01/scripts/comparaison_lot49ter.py`.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.livrables.appuis import subset
from aster_expert.livrables.donnees import Deliverables
from aster_expert.livrables.ingenieur import bands, family_rows
from aster_expert.livrables.sections import V_RES, section_rows
from aster_expert.livrables.torseurs import evaluate
from aster_expert.projet.context import load_project

PROJECT = ROOT / "projets" / "estacade_pieux_01"
PAQUET = PROJECT / "resultats" / "livrables" / "paquet"
STATES = {
    "ELS_frequent": "ELS f",
    "ELS_caracteristique": "ELS c",
    "ELU_fondamental": "ELU",
}
COMB_111 = {"ELU_fondamental": "111 ELU+", "ELS_caracteristique": "111 ELS_c",
            "ELS_frequent": "111 ELS_f"}  # fmt: skip
SOURCE_FAMILY = {"ELS_f": "ELS_frequent", "ELS_c": "ELS_caracteristique",
                 "ELU+": "ELU_fondamental"}  # fmt: skip


def _load(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def source_values() -> dict[tuple[str, str], float]:
    """(point, state) -> value of the source, C1 to C13 (lot 47 bis, v2 lines)."""
    data = _load(PROJECT / "references" / "comparaison_v2_lot47bis.json")
    out: dict[tuple[str, str], float] = {}
    for line in data["lignes"]:
        state = SOURCE_FAMILY.get((line.get("lieu") or {}).get("famille", ""))
        if state and line.get("source") is not None:
            out.setdefault((line["point"], state), float(line["source"]))
    return out


def torsor(
    syn: dict[str, Any], section: str, state: str, *, label: str | None = None,
    column: str | None = None, e27: bool = False, sense: str | None = None,
) -> dict[str, Any] | None:  # fmt: skip
    for t in syn["torseurs"]:
        if t["section"] != section or t["etat_limite"] != state:
            continue
        if e27 != ("e27" in t):
            continue
        if label is not None and t.get("libelle_ingenieur") != label:
            continue
        if column is not None and t["colonne"] != column:
            continue
        if sense is not None and t.get("sens") != sense:
            continue
        if not t.get("significative", True) and not t.get("comparaison_seulement"):
            continue
        found: dict[str, Any] = t
        return found
    return None


def k(value: float | None) -> float | None:
    return None if value is None else value * 1.0e-3


def gap(ours: float | None, source: float | None) -> float | None:
    if ours is None or not source:
        return None
    return (abs(ours) - abs(source)) / abs(source)


def where(t: dict[str, Any] | None) -> str:
    if t is None:
        return ""
    lieu = t["lieu"]
    x, y, z = lieu["coordonnees_m"]
    member = f"{lieu['groupe']}, " if lieu.get("groupe") else ""
    position = f" @ {t['position_mobile']}" if t.get("position_mobile") else ""
    return f"{member}({x:.2f} ; {y:.2f} ; {z:.2f}) ; {t['combinaison']}{position}"


def _support(entry: dict[str, Any], key: str) -> str:
    own = entry[key]
    position = f" @ {own['position_mobile']}" if own.get("position_mobile") else ""
    coords = " ; ".join(f"{c:.2f}" for c in entry["appui"])
    return f"appui ({coords}) ; {own['combinaison']}{position}"


def rive_shear_comb100(ctx: Any) -> dict[str, Any]:
    """V = √(QX² + QY²) max of the edge section under combination 100 ELU+ (the
    deliverables' combination 100: PP, G2, TR; the axle of E18 is not one of its
    cases, it was run apart at lot 47 bis)."""
    summary = ctx.declaration.engineering_summary
    d = Deliverables(PROJECT / "resultats" / "livrables", keep_fields=True)
    infos = d.field_infos(ctx.declaration.deliverables.fields)
    family = next(f for f in summary.families if f.name == "tablier")
    fr = family_rows(d, infos, summary, family)
    section = next(s for s in summary.sections if s.name == "dalle_rive")
    sec = section_rows(
        fr, d.mesh, section, ctx.declaration.deliverables, bands(d, summary)
    )
    rows = np.nonzero(sec.mask & ~sec.singular)[0]
    sub = subset(fr, rows)
    combos = [(i, c) for i, c in enumerate(d.combinations) if c.name == "100 ELU+"]
    _ci, _pi, values = next(evaluate(sub, combos))
    v = values[:, sub.column(V_RES)]
    j = int(np.argmax(v))
    x, y, _z = sub.xyz[j]
    return {"V_kN_m": float(v[j]) * 1e-3, "lieu": f"({x:.2f} ; {y:.2f})"}


def profile(ctx: Any, syn: dict[str, Any]) -> dict[str, Any]:
    """MXX of the reference across the governing line of the hogging zone."""
    summary = ctx.declaration.engineering_summary
    d = Deliverables(PROJECT / "resultats" / "livrables", keep_fields=True)
    infos = d.field_infos(ctx.declaration.deliverables.fields)
    family = next(f for f in summary.families if f.name == "tablier")
    fr = family_rows(d, infos, summary, family)
    governing = torsor(syn, "dalle_chapeau", "ELU_fondamental", e27=True)
    assert governing is not None
    x_file = float(governing["e27"]["appui"][0])
    x_face = float(governing["lieu"]["coordonnees_m"][0])
    side = 1.0 if x_face >= x_file else -1.0
    out: dict[str, Any] = {"X_file_m": x_file, "cote": "+" if side > 0 else "−",
                           "lignes": {}}  # fmt: skip
    combos_by_state = {
        state: [(i, c) for i, c in enumerate(d.combinations) if c.name == name]
        for state, name in COMB_111.items()
    }
    for y in (-1.0, 0.0, 1.0):
        on = np.nonzero(
            (np.abs(fr.xyz[:, 1] - y) < 1e-6)
            & ((fr.xyz[:, 0] - x_file) * side >= -1e-6)
            & ((fr.xyz[:, 0] - x_file) * side <= 1.0 + 1e-6)
        )[0]
        order = on[np.argsort(np.abs(fr.xyz[on, 0] - x_file))]
        sub = subset(fr, order)
        column = sub.column("MXX")
        line: dict[str, Any] = {
            "distance_m": [float(abs(v - x_file)) for v in sub.xyz[:, 0]]
        }
        for state, combos in combos_by_state.items():
            best = np.full(len(order), -np.inf)
            for _ci, _pi, values in evaluate(sub, combos):
                best = np.maximum(best, values[:, column])
            line[state] = [float(v) * 1e-3 for v in best]
        out["lignes"][f"Y={y:+.2f}"] = line
    return out


def draw(prof: dict[str, Any], sources: dict[str, float], path: Path) -> None:
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=False)
    for ax, (state, label) in zip(axes, STATES.items(), strict=True):
        for name, line in prof["lignes"].items():
            ax.plot(line["distance_m"], line[state], marker=".", label=name)
        if label in sources:
            ax.axhline(sources[label], color="black", linestyle="--",
                       label=f"source {sources[label]:.0f}")  # fmt: skip
        for x0 in (0.0, 0.30, 0.60):
            ax.axvline(x0, color="grey", linewidth=0.6)
        ax.set_title(f"MXX, combinaison 111, {label} (kN·m/m)")
        ax.set_xlabel(f"distance à l'axe de la file X = {prof['X_file_m']:.2f} (m)")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("Profil du moment de chapeau perpendiculaire au chevêtre "
                 "(axe, 0,30 m, nu à 0,60 m), enveloppe des positions de TS")  # fmt: skip
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main() -> None:
    ctx = load_project("estacade_pieux_01", ROOT)
    syn = _load(PAQUET / "synthese_ingenieur.json")
    src = source_values()
    rows: list[dict[str, Any]] = []

    def add(point: str, lieu: str, comp: str, famille: str, state: str,
            source: float | None, ours: float | None, attribution: str,
            note: str = "", grey: bool = False) -> None:  # fmt: skip
        rows.append(
            {
                "point": point,
                "lieu": lieu,
                "composante": comp,
                "famille": famille,
                "etat": STATES.get(state, state),
                "source": source,
                "code_aster": ours,
                "ecart": gap(ours, source),
                "attribution": attribution,
                "note": note,
                "_grise": grey,
            }
        )

    for state in STATES:
        # Pointes : réaction verticale de la pointe (la source donne aussi 554, 767,
        # 1 102 kN, D) ; tête : N au nœud +1,30 (C2).
        t = torsor(syn, "pointes", state, column="DZ", sense="max")
        pointe = {"ELS_frequent": 554.0, "ELS_caracteristique": 767.0,
                  "ELU_fondamental": 1102.0}[state]  # fmt: skip
        add("pointes", where(t), "réaction DZ", "appuis", state, pointe,
            k(t["valeur_si"]) if t else None, ATTRIBUTION["pointes"])  # fmt: skip
        t = torsor(syn, "tete_de_pieu", state, label="compression max")
        add("C2", where(t), "N (compression)", "pieux, tête +1,30", state,
            src.get(("C2", state)), k(-t["torseur_si"]["N"]) if t else None,
            ATTRIBUTION["C2"])  # fmt: skip
        t = torsor(syn, "tete_de_pieu", state, label="moment max (résultante)")
        add("C3", where(t), "M résultant", "pieux, tête +1,30 (comparaison, E24)",
            state, src.get(("C3", state)), k(t["valeur_si"]) if t else None,
            ATTRIBUTION[f"C3 {STATES[state]}"])  # fmt: skip
        t = torsor(syn, "bouchon_nu_chevetre", state, e27=True)
        add("bouchon (E24, E27)", where(t), "M_dim résultant", "pieux, nu +0,60",
            state, 450.0 if state == "ELU_fondamental" else None,
            k(t["e27"]["M_dim_si"]) if t else None, ATTRIBUTION["bouchon"])  # fmt: skip
        vs = [torsor(syn, s, state, label="effort tranchant max (résultante)")
              for s in ("bouchon_nu_chevetre", "bouchon")]  # fmt: skip
        v = max((x for x in vs if x), key=lambda x: x["valeur_si"], default=None)
        add("C4", where(v), "V résultant", "pieux, bouchon (+0,60 à −0,80)", state,
            src.get(("C4", state)), k(v["valeur_si"]) if v else None,
            ATTRIBUTION["C4"])  # fmt: skip
        t = torsor(syn, "chevetre_travee", state, label="moment de travée max")
        add("C6", where(t), "M de travée, section en T (E25)", "chevêtres", state,
            src.get(("C6", state)), k(-t["valeur_si"]) if t else None,
            ATTRIBUTION["C6"])  # fmt: skip
        t = torsor(syn, "chevetre_nu_appui", state, e27=True)
        if t is not None:
            e = t["e27"]
            per = e["par_appui"]
            nu = max(per, key=lambda a: a["M_nu_max"]["valeur"])
            axe = max(per, key=lambda a: a["M_axe_max"]["valeur"])
            source7 = 177.0 if state == "ELU_fondamental" else None
            add("C7", where(t), "M_dim sur appui (E27)", "chevêtres, section en T",
                state, source7, k(e["M_dim_si"]), ATTRIBUTION["C7 dim"],
                f"terme qui gouverne : {e['terme_gouvernant']} (M_enc de A1 "
                f"{k(e['M_enc_si']):.1f} kN·m)")  # fmt: skip
            add("C7", _support(nu, "M_nu_max"), "M au nu (M_nu), max sur les appuis",
                "chevêtres, section en T", state, source7, k(nu["M_nu_max"]["valeur"]),
                ATTRIBUTION["C7 nu"])  # fmt: skip
            add("C7", _support(axe, "M_axe_max"), "M à l'axe (M_axe, comparaison), max "
                "sur les appuis", "chevêtres, section en T", state, source7,
                k(axe["M_axe_max"]["valeur"]),
                ATTRIBUTION["C7 axe"])  # fmt: skip
        t = torsor(syn, "chevetre_nu_appui", state, label="effort tranchant max")
        add("C8", where(t), "V au nu, section en T", "chevêtres", state,
            653.0 if state == "ELU_fondamental" else None,
            k(abs(t["valeur_si"])) if t else None, ATTRIBUTION["C8"])  # fmt: skip
        t = torsor(syn, "dalle_travee", state, label="moment de travée max (MXX)")
        add("C10", where(t), "MXX de travée", "tablier, travée courante", state,
            src.get(("C10", state)), k(-t["valeur_si"]) if t else None,
            ATTRIBUTION["C10"])  # fmt: skip
        t = torsor(syn, "dalle_chapeau", state, e27=True)
        if t is not None:
            e = t["e27"]
            per = e["par_appui"]
            nu = max(per, key=lambda a: a["M_nu_max"]["valeur"])
            axe = max(per, key=lambda a: a["M_axe_max"]["valeur"])
            source9 = src.get(("C9", state))
            note9 = ("tableau du superviseur : 174 / 119 / 80 ; source versionnée "
                     "(lot 47 bis) : 174 / 118 / 79")  # fmt: skip
            add("C9", where(t), "M_dim sur appui (E27)", "tablier, chapeau", state,
                source9, k(e["M_dim_si"]), ATTRIBUTION["C9"],
                f"terme qui gouverne : {e['terme_gouvernant']} ; " + note9)  # fmt: skip
            add("C9", _support(nu, "M_nu_max"), "M au nu (M_nu), max sur les lignes",
                "tablier, chapeau", state, source9, k(nu["M_nu_max"]["valeur"]),
                ATTRIBUTION["C9"])  # fmt: skip
            add("C9", _support(axe, "M_axe_max"), "M à l'axe hors disques (M_axe), max "
                "sur les lignes", "tablier, chapeau", state, source9,
                k(axe["M_axe_max"]["valeur"]),
                ATTRIBUTION["C9"])  # fmt: skip
        vs = [torsor(syn, s, state, label="effort tranchant max (résultante)")
              for s in ("dalle_travee", "dalle_rive", "dalle_chapeau")]  # fmt: skip
        v = max((x for x in vs if x), key=lambda x: x["valeur_si"], default=None)
        add("C12", where(v), "V = √(QX² + QY²), hors bandes et disques",
            "tablier (courante, rive, chapeau)", state,
            src.get(("C12", state)), k(v["valeur_si"]) if v else None,
            ATTRIBUTION["C12"])  # fmt: skip
    rive = rive_shear_comb100(ctx)
    add("C12 rive (E18)", rive["lieu"] + " ; 100 ELU+", "V = √(QX² + QY²)",
        "tablier, rive", "ELU_fondamental", 321.0, rive["V_kN_m"],
        ATTRIBUTION["C12 rive"],
        "tableau du superviseur : 321 kN/m sous TR (combinaison 100) ; la source "
        "versionnée (lot 47 bis) donne 568 kN/m pour C12 rive et 320 pour C12 "
        "courant : 321 est très probablement la valeur courante. La combinaison 100 "
        "des livrables n'a pas l'essieu d'E18 (calculé à part au lot 47 bis : "
        "222,1 kN/m hors disques)")  # fmt: skip
    add("C11", "moyenne de section (E17.4)", "N de la dalle", "tablier",
        "ELU_fondamental", 65.0 + 0.7 * 19.0, None, ATTRIBUTION["C11"],
        "non comparable directement : la source compose 65 + 0,7 × 19 à la main, "
        "sans concomitance ; ses coefficients d'ELS fréquent ne sont pas cohérents "
        "avec sa combinaison 111 ; ordre de grandeur : C11 au lot 47 bis 19,7 et "
        "62,9 kN/m (sources 18,9 et 64,1)", grey=True)  # fmt: skip
    prof = profile(ctx, syn)
    sources_chapeau = {"ELS f": 80.0, "ELS c": 119.0, "ELU": 174.0}
    out_dir = PAQUET / "comparaison"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "profil_chapeau.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as h:
        w = csv.writer(h, delimiter=";")
        w.writerow(["Y (m)", "distance à l'axe (m)",
                    *[f"MXX {lab} (kN.m/m)" for lab in STATES.values()]])  # fmt: skip
        for name, line in prof["lignes"].items():
            for j, dist in enumerate(line["distance_m"]):
                w.writerow([name[2:], f"{dist:.2f}".replace(".", ","),
                            *[f"{line[s][j]:.1f}".replace(".", ",") for s in STATES]])  # fmt: skip
    draw(prof, sources_chapeau, out_dir / "profil_chapeau.png")
    key_points = []
    for name, line in prof["lignes"].items():
        for target in (0.0, 0.30, 0.60):
            j = int(np.argmin(np.abs(np.array(line["distance_m"]) - target)))
            key_points.append(
                {
                    "ligne": name,
                    "distance_m": line["distance_m"][j],
                    **{STATES[s]: line[s][j] for s in STATES},
                }
            )
    tables = {
        "tableaux": [
            {
                "titre": "Comparaison au modèle source (contre-calcul d'un modèle non "
                "validé, jamais un niveau E) : points du tableau du superviseur, "
                "vérifiés ligne par ligne (lot 49 ter)",
                "note": "Valeurs de la source : references/comparaison_v2_lot47bis.json "
                "(C1 à C13) ; écart = (|Code_Aster| − |source|) / |source| ; "
                "attribution A à G (règle des points de comparaison du lot 47 "
                "quater). Convention ingénieur (compression, moments de travée et "
                "sur appui en valeur positive).",
                "colonnes": [
                    {"cle": "point", "entete": "Point"},
                    {"cle": "composante", "entete": "Composante"},
                    {"cle": "famille", "entete": "Famille"},
                    {"cle": "etat", "entete": "État limite"},
                    {"cle": "source", "entete": "Source", "unite": "kN"},
                    {"cle": "code_aster", "entete": "Code_Aster", "unite": "kN"},
                    {"cle": "ecart", "entete": "Écart", "unite": "%"},
                    {"cle": "attribution", "entete": "Attribution"},
                    {"cle": "lieu", "entete": "Lieu"},
                    {"cle": "note", "entete": "Note"},
                ],
                "lignes": [
                    {**r, "ecart": None if r["ecart"] is None else 100 * r["ecart"]}
                    for r in rows
                ],
            },
            {
                "titre": "Profil du chapeau : MXX perpendiculaire au chevêtre, "
                f"file X = {prof['X_file_m']:.2f}, côté {prof['cote']}, combinaison "
                "111, enveloppe des positions de TS (comparaison seulement)",
                "note": "Source : 174 / 119 / 80 kN·m/m (ELU / ELS c / ELS f). "
                "Fichiers comparaison/profil_chapeau.csv et .png.",
                "colonnes": [
                    {"cle": "ligne", "entete": "Ligne"},
                    {"cle": "distance_m", "entete": "Distance à l'axe", "unite": "m"},
                    *[
                        {"cle": lab, "entete": f"MXX {lab}", "unite": "kN·m/m"}
                        for lab in STATES.values()
                    ],  # fmt: skip
                ],
                "lignes": key_points,
            },
        ],
        "profil": prof,
    }
    (PAQUET / "comparaison_externe.json").write_text(
        json.dumps(tables, indent=1, ensure_ascii=False) + "\n", "utf-8"
    )
    (PROJECT / "references" / "comparaison_externe_lot49ter.json").write_text(
        json.dumps({"lignes": rows, "profil_points": key_points, "profil": prof},
                   indent=1, ensure_ascii=False) + "\n", "utf-8")  # fmt: skip
    for r in rows:
        print(r["point"], r["composante"], r["etat"], r["source"],
              None if r["code_aster"] is None else round(r["code_aster"], 1),
              None if r["ecart"] is None else f"{100 * r['ecart']:+.1f} %")  # fmt: skip
    for p in key_points:
        print(p)


ATTRIBUTION: dict[str, str] = {
    "pointes": "aucun écart (≤ 3 %) ; D : la source donne aussi 554 / 767 / 1 102 kN "
    "en tête (lot 47 quater)",
    "C2": "aucun écart (≤ 3 %)",
    "C3 ELS f": "aucun écart (≤ 5 %) ; lieu de comparaison seulement (E24)",
    "C3 ELS c": "G, inexpliqué (lot 47 quater, § 6.1) ; lieu de comparaison seulement "
    "(E24)",
    "C3 ELU": "aucun écart (≤ 5 %) ; lieu de comparaison seulement (E24)",
    "bouchon": "A, lieu de lecture : la source dimensionne à +1,30 (dans le chevêtre), "
    "E24 au nu +0,60 ; enveloppe avec V1 (E27, critère de 5 %) ; non comparable "
    "directement",
    "C4": "aucun écart (≤ 5 %)",
    "C6": "C, chevêtre de 0,80 m probable dans le modèle source (§20.5.1 : « h = 0.80 m "
    "(augmenté à 0.90m) », constat sur E19) ; A, la source publie la barre et non la "
    "section en T (E25)",
    "C7 dim": "C, règle E27 de MM (0,65 × moment d'encastrement parfait de A1), que la "
    "source n'applique pas ; non comparable directement",
    "C7 nu": "A, lieu de lecture : la source lit à l'axe des pieux, la section de "
    "dimensionnement est au nu (E26)",
    "C7 axe": "aucun écart (+0,4 %) : même lecture que C7 au lot 47 bis (177,7 kN·m, "
    "section en T à l'axe des pieux) ; comparaison seulement",
    "C8": "aucun écart (≤ 5 %) au nu en section en T ; la barre seule en DKT donne le "
    "tiers (C8 du lot 47 bis, CA-058)",
    "C10": "aucun écart (≤ 5 %)",
    "C9": "A, lieu de lecture : le profil montre MXX maximal à 0,30 m de l'axe (dans "
    "la bande E26) et un maximum local près des têtes de pieux (lot 47 bis : 156,2 "
    "kN·m/m à 5 cm de l'axe de la file 7, juste hors du disque) ; la source lit dans "
    "cette zone ; E, maillage (lot 47 quater)",
    "C12": "E, maillage (lot 47 quater) et A : résultante hors bandes E26 et disques",
    "C12 rive": "B, non comparable directement : l'essieu d'E18 n'est pas un cas de la "
    "combinaison 100 des livrables",
    "C11": "non comparable directement",
}
"""Attribution of each point (A to G, rule of the comparison points of lot 47 quater),
written after reading (lot 49 ter)."""


if __name__ == "__main__":
    main()
