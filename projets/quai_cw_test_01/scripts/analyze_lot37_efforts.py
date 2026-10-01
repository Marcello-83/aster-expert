"""Lot 37 : évaluation des critères C1, C4, C6, C8, C9 et C10 de `docs/essais_lot37.md`
et tableau avant/après des efforts des tirants et de la poutre (sous G et Q3).

Entrées : les `synthese.json` produits par `aster-expert report` pour le modèle
complet, le quai réduit et le quai réduit raffiné ×2, le `.comm` du modèle complet, la
synthèse du lot 36 (avant). Sortie : un JSON de résultats et un tableau Markdown.

Usage : python projets/quai_cw_test_01/scripts/analyze_lot37_efforts.py <complet.comm> <synthese complet> \\
    <synthese réduit> <synthese réduit fin> <synthese avant (lot 36)> <sortie.json> \\
    <tableau.md>
"""

from __future__ import annotations

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# Paquet du projet (`projets/`) : ce script vit dans projets/quai_cw_test_01/scripts.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import ast
import json
import math
import sys
from pathlib import Path
from typing import Any

UNIFORM_CASES = ("G", "EAU_P", "EAU_A", "Q1")
SECTION_THRESHOLD = 0.05
EXACT_THRESHOLD = 1.0e-6
COARSE_GAP_FLOOR = 1.0e-3
TIE_AREA = 0.00442


def _load(path: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def bar_sections(comm_text: str) -> dict[str, float]:
    """Section de `BARRE` de chaque groupe de tirant, lue du `.comm` par `ast`."""
    out: dict[str, float] = {}
    for node in ast.walk(ast.parse(comm_text)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "AFFE_CARA_ELEM"
        ):
            continue
        for kw in node.keywords:
            if kw.arg != "BARRE":
                continue
            items = kw.value.elts if isinstance(kw.value, ast.Tuple) else [kw.value]
            for occ in items:
                assert isinstance(occ, ast.Call)
                fields = {k.arg: ast.literal_eval(k.value) for k in occ.keywords}
                for group in fields["GROUP_MA"]:
                    out[group] = float(fields["VALE"])
    return out


def criterion_c1_c4(comm_text: str) -> dict[str, Any]:
    sections = bar_sections(comm_text)
    tirants = [f"TIRANT_{k:02d}" for k in range(1, 10)]
    expected = {
        t: TIE_AREA / 2.0 if t in ("TIRANT_01", "TIRANT_09") else TIE_AREA
        for t in tirants
    }
    gaps = {
        t: abs(sections[t] - expected[t]) / expected[t] if t in sections else math.inf
        for t in tirants
    }
    return {
        "C1": {
            "sections": {t: sections.get(t) for t in tirants},
            "max_relative_gap": max(gaps.values()),
            "verdict": "RÉUSSI" if max(gaps.values()) <= 1.0e-12 else "ÉCHEC",
        },
        "C4": {
            "pou_d_t": 'MODELISATION="POU_D_T"' in comm_text,
            "pou_d_e": 'MODELISATION="POU_D_E"' in comm_text,
            "verdict": "RÉUSSI"
            if 'MODELISATION="POU_D_T"' in comm_text
            and 'MODELISATION="POU_D_E"' not in comm_text
            else "ÉCHEC",
        },
    }


def tie_forces(synthesis: dict[str, Any], case: str) -> list[float]:
    block = next(c for c in synthesis["cases"] if c["case"] == case)
    return [float(t["n"]) for t in sorted(block["ties"], key=lambda t: t["tie"])]


def criterion_c6(synthesis: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    ok = True
    for case in UNIFORM_CASES:
        n = tie_forces(synthesis, case)
        inner = n[1:-1]
        ratio_edge = n[0] / n[len(n) // 2]
        ratio_far = n[-1] / n[len(n) // 2]
        dispersion = (max(inner) - min(inner)) / max(abs(v) for v in inner)
        gap_a = max(abs(ratio_edge - 0.5), abs(ratio_far - 0.5)) / 0.5
        out[case] = {
            "N_kN": [v / 1e3 for v in n],
            "ratio_edge_over_central": ratio_edge,
            "ratio_other_edge_over_central": ratio_far,
            "gap_a_relative": gap_a,
            "dispersion_inner_relative": dispersion,
            "tenu": gap_a <= EXACT_THRESHOLD and dispersion <= EXACT_THRESHOLD,
        }
        ok = ok and bool(out[case]["tenu"])
    out["verdict"] = "RÉUSSI" if ok else "ÉCHEC"
    return out


def _statics(
    synthesis: dict[str, Any],
) -> dict[tuple[str, str], dict[str, float | None]]:
    return {
        (s["case"], s["scope"]): {
            "T": s["t_y"]["relative_gap"],
            "M": s["m_x"]["relative_gap"],
            "N": s["n_z"]["relative_gap"],
        }
        for s in synthesis["section_statics"]
    }


def criterion_c8_c9(synthesis: dict[str, Any]) -> dict[str, Any]:
    gaps = _statics(synthesis)
    result: dict[str, Any] = {"C8": {}, "C9": {}}
    for (case, scope), g in gaps.items():
        target = "C8" if scope == "ensemble" else "C9"
        tenu = all(
            g[k] is not None and abs(float(g[k] or 0.0)) <= SECTION_THRESHOLD
            for k in ("T", "M")
        )
        result[target][f"{case} / {scope}"] = {**g, "tenu": tenu}
    for key in ("C8", "C9"):
        result[key]["verdict"] = (
            "RÉUSSI"
            if all(v["tenu"] for k, v in result[key].items() if k != "verdict")
            else "ÉCHEC"
        )
    return result


def criterion_c10(coarse: dict[str, Any], fine: dict[str, Any]) -> dict[str, Any]:
    a, b = _statics(coarse), _statics(fine)
    rows: dict[str, Any] = {}
    ok = True
    for key in sorted(a):
        for quantity in ("T", "M"):
            g_coarse, g_fine = a[key][quantity], b[key][quantity]
            if g_coarse is None or g_fine is None:
                continue
            exempt = abs(g_coarse) < COARSE_GAP_FLOOR
            decreases = abs(g_fine) < abs(g_coarse)
            tenu = exempt or decreases
            rows[f"{key[0]} / {key[1]} / {quantity}"] = {
                "coarse": g_coarse,
                "fine": g_fine,
                "ratio_fine_over_coarse": abs(g_fine) / abs(g_coarse)
                if g_coarse
                else None,
                "exempt": exempt,
                "tenu": tenu,
            }
            ok = ok and tenu
    return {"rows": rows, "verdict": "RÉUSSI" if ok else "ÉCHEC"}


def _beam_extrema(
    synthesis: dict[str, Any], case: str
) -> dict[str, tuple[float, float]]:
    block = next(c for c in synthesis["cases"] if c["case"] == case)
    return {
        b["component"]: (float(b["minimum"]["value"]), float(b["maximum"]["value"]))
        for b in block["beam"]
    }


def before_after(before: dict[str, Any], after: dict[str, Any]) -> str:
    lines = [
        "# Avant / après — efforts des tirants et de la poutre (cas G et Q3)",
        "",
        "Avant : lot 36, base "
        "(`data/examples/lot36_butee/rapports_base/synthese.json` : tirants en section "
        "entière, poutre en `POU_D_E`). Après : lot 37 (tirants de bord `TIRANT_01` et "
        "`TIRANT_09` en demi-section, poutre en `POU_D_T`). **Deux changements "
        "simultanés** : l'écart de chaque ligne ne se laisse pas attribuer à l'un ou à "
        "l'autre par ce seul tableau. Cas élémentaires, aucun verdict.",
        "",
        "## Effort normal des tirants (kN)",
        "",
        "| Tirant | G avant | G après | Q3 avant | Q3 après |",
        "|---:|---:|---:|---:|---:|",
    ]
    nb = {c: tie_forces(before, c) for c in ("G", "Q3")}
    na = {c: tie_forces(after, c) for c in ("G", "Q3")}
    for i in range(len(nb["G"])):
        lines.append(
            f"| {i + 1} | {nb['G'][i] / 1e3:.1f} | {na['G'][i] / 1e3:.1f} "
            f"| {nb['Q3'][i] / 1e3:.1f} | {na['Q3'][i] / 1e3:.1f} |"
        )
    lines += [
        "",
        "## Efforts extrêmes de la poutre de couronnement",
        "",
        "N, VY, VZ en kN ; MT, MFY, MFZ en kN·m.",
        "",
        "| Effort | Cas | Min avant | Min après | Max avant | Max après |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for case in ("G", "Q3"):
        b, a = _beam_extrema(before, case), _beam_extrema(after, case)
        for comp in ("N", "VY", "VZ", "MT", "MFY", "MFZ"):
            lines.append(
                f"| {comp} | {case} | {b[comp][0] / 1e3:.1f} | {a[comp][0] / 1e3:.1f} "
                f"| {b[comp][1] / 1e3:.1f} | {a[comp][1] / 1e3:.1f} |"
            )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    comm_path, full_path, reduced_path, fine_path, before_path, out_json, out_md = argv
    full = _load(full_path)
    result: dict[str, Any] = {}
    result.update(criterion_c1_c4(Path(comm_path).read_text(encoding="utf-8")))
    result["C6"] = criterion_c6(full)
    result.update(criterion_c8_c9(full))
    result["C10"] = criterion_c10(_load(reduced_path), _load(fine_path))
    result["C10_reduced_statics"] = {
        "coarse": {
            f"{k[0]} / {k[1]}": v for k, v in _statics(_load(reduced_path)).items()
        },
        "fine": {f"{k[0]} / {k[1]}": v for k, v in _statics(_load(fine_path)).items()},
    }
    Path(out_json).write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    Path(out_md).write_text(before_after(_load(before_path), full), encoding="utf-8")
    for key in ("C1", "C4", "C6", "C8", "C9", "C10"):
        print(key, result[key]["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
