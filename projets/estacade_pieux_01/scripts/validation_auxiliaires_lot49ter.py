"""Lot 49 ter -- analytical validation of the auxiliary models A1 and A2 (E27).

docs/essais_lot49ter.md, § 2.4 (method) and § 3 (criteria, written before the runs).

The `.comm` of a derived model (`resultats/livrables_derives/<A>/post/*_modele.comm`,
written by `aster_expert.livrables.derives`) is kept up to its first solve; a group
block is inserted before `AFFE_MODELE`, then one load case, one `MECA_STATIQUE` with
the reference load `CL`, the derived load `DRV_<A>` and the analytical load, the
generalised forces and the extractions (`POST_RELEVE_T`, `IMPR_TABLE` in `E20.12`).

- A1: `FORCE_POUTRE` FZ = −q, q = 100 kN/m, on the cells of the cap beam of line 4
  (X = 15.60) between the piles (|Y| ≤ 2.00). Expected: the T section (E25: bar +
  ∫MYY dX over |X − 15.60| ≤ 0.60) at the pile axis, inner element, q·L²/12
  (L = 4.00 m); also reported: the full cut (every cap beam and the whole slab) and
  the statics of the span, M_support − M_mid = q·L²/8 over the full width.
- A2: `FORCE_COQUE` FZ = −q, q = 10 kPa, on the whole slab. Expected: MXX at the axis
  of lines 2 to 6 at Y = 0, q·L²/12 (L = 5.00 m).

Keywords: catalogue 17.4 (`DEFI_GROUP/CREA_GROUP_MA` OPTION BANDE, INTERSEC ;
`AFFE_CHAR_MECA/FORCE_POUTRE`, `FORCE_COQUE` ; `MECA_STATIQUE/EXCIT` ;
`POST_RELEVE_T/ACTION` EXTRACTION, GROUP_MA, MOYE_NOEUD) -- read with
`get_command_schema`, never from memory.

Run: `.venv/bin/python projets/estacade_pieux_01/scripts/validation_auxiliaires_lot49ter.py`
(after `aster-expert projet estacade_pieux_01 livrables --modele A1 --sous-etape
preparer`, idem A2). Writes `references/validation_auxiliaires_lot49ter.json`.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "projets"))

from aster_expert.controles.tables import TableIndex
from aster_expert.livrables.chaine import _export_text, production
from aster_expert.livrables.derives import derived_root
from aster_expert.projet.context import load_project
from aster_expert.projet.pipeline import Runtime, execute

PROJECT = ROOT / "projets" / "estacade_pieux_01"
OUT = PROJECT / "references" / "validation_auxiliaires_lot49ter.json"
Q_LINE = 100_000.0  # N/m (A1)
Q_SURF = 10_000.0  # Pa (A2)
L_CAP = 4.0
L_SLAB = 5.0
X_LOADED = 15.6
HALF = 0.60
TOL = 0.02
_SOLVE = re.compile(r"^\w+\s*=\s*(MACRO_ELAS_MULT|MECA_STATIQUE)\(", re.MULTILINE)
_MODEL = re.compile(r"^\w+\s*=\s*AFFE_MODELE\(", re.MULTILINE)


def _band(name: str, y: float) -> str:
    return (
        f'_F(NOM="{name}", OPTION="BANDE", POINT=(0.0, {y}, 0.0), '
        'VECT_NORMALE=(0.0, 1.0, 0.0), DIST=0.001, CRIT_NOEUD="AU_MOINS_UN")'
    )


def build(model: str, text: str) -> str:
    """The validation `.comm` of `model` (A1 or A2) from its derived `.comm`."""
    head = text[: _SOLVE.search(text).start()]  # type: ignore[union-attr]
    at = _MODEL.search(head)
    assert at is not None
    groups = [
        _band("VAL_LM", -2.0),
        _band("VAL_L0", 0.0),
        _band("VAL_LP", 2.0),
        '_F(NOM="VAL_LY", UNION=("VAL_LM", "VAL_L0", "VAL_LP"))',
        '_F(NOM="VAL_DL", INTERSEC=("VAL_LY", "DALLE"))',
    ]
    if model == "A1":
        groups += [
            '_F(NOM="VAL_BY", OPTION="BANDE", POINT=(0.0, 0.0, 0.0), '
            'VECT_NORMALE=(0.0, 1.0, 0.0), DIST=2.0001, CRIT_NOEUD="TOUS")',
            '_F(NOM="VAL_CH", INTERSEC=("VAL_BY", "CHEV_4"))',
        ]
        load = f'FORCE_POUTRE=_F(GROUP_MA="VAL_CH", FZ={-Q_LINE!r})'
    else:
        load = f'FORCE_COQUE=_F(GROUP_MA="DALLE", FZ={-Q_SURF!r})'
    mesh = re.search(r"MAILLAGE=(\w+)", head[at.end() :])
    assert mesh is not None
    m = mesh.group(1)
    block_groups = "\n".join(
        [
            f"# Validation analytique {model} (lot 49 ter, docs/essais_lot49ter.md § 2.4).",
            f"{m} = DEFI_GROUP(",
            f"    reuse={m},",
            f"    MAILLAGE={m},",
            "    CREA_GROUP_MA=(",
            *[f"        {g}," for g in groups],
            "    ),",
            "    CREA_GROUP_NO=(",
            '        _F(GROUP_MA="VAL_DL", NOM="VAL_NDL"),',
            '        _F(GROUP_MA="CHEVETRES", NOM="VAL_NCH"),',
            "    ),",
            ")",
            "",
        ]
    )
    supports = "TETES" if model == "A1" else "DRV_B01"
    tail = f"""
VAL_Q = AFFE_CHAR_MECA(MODELE=MODELE, {load})
VAL = MECA_STATIQUE(
    MODELE=MODELE,
    CHAM_MATER=CHMAT,
    CARA_ELEM=CARA,
    EXCIT=(_F(CHARGE=CL), _F(CHARGE=DRV_{model}), _F(CHARGE=VAL_Q)),
)
VAL = CALC_CHAMP(reuse=VAL, RESULTAT=VAL, GROUP_MA="DALLE", CONTRAINTE=("EFGE_NOEU",))
VAL = CALC_CHAMP(reuse=VAL, RESULTAT=VAL, GROUP_MA=("CHEVETRES",), CONTRAINTE=("EFGE_ELNO",))
VAL = CALC_CHAMP(reuse=VAL, RESULTAT=VAL, FORCE=("REAC_NODA",))
T_VCH = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="VAL_CHEV", RESULTAT=VAL, NOM_CHAM="EFGE_ELNO", GROUP_NO=("VAL_NCH",), GROUP_MA=("CHEVETRES",), NOM_CMP=("N", "VZ", "MFY"), MOYE_NOEUD="NON")
)
IMPR_TABLE(TABLE=T_VCH, UNITE=6, FORMAT_R="E20.12")
T_VDL = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="VAL_DALLE", RESULTAT=VAL, NOM_CHAM="EFGE_NOEU", GROUP_NO=("VAL_NDL",), NOM_CMP=("NYY", "MXX", "MYY", "QY"))
)
IMPR_TABLE(TABLE=T_VDL, UNITE=6, FORMAT_R="E20.12")
T_VRE = POST_RELEVE_T(
    ACTION=_F(OPERATION="EXTRACTION", INTITULE="VAL_REAC", RESULTAT=VAL, NOM_CHAM="REAC_NODA", GROUP_NO=("PIEDS", "{supports}"), RESULTANTE=("DX", "DY", "DZ"))
)
IMPR_TABLE(TABLE=T_VRE, UNITE=6, FORMAT_R="E20.12")
FIN()
"""
    return head[: at.start()] + block_groups + head[at.start() :] + tail


def _elements(records: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Rows of an ELNO extraction (MOYE_NOEUD='NON') grouped by element: the text
    cells are INTITULE, NOEUD, RESU, NOM_CHAM, NUME_ORDRE, INST, MAILLE (header of
    the table), the cell is the last one."""
    out: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        words = str(r["_head"]).split()
        out.setdefault(words[-1], []).append(r)
    return list(out.values())


def _trapz(rows: list[dict[str, Any]], comp: str) -> float:
    rows = sorted(rows, key=lambda r: float(r["COOR_X"]))
    xs = np.array([float(r["COOR_X"]) for r in rows])
    return float(np.trapezoid([float(r[comp]) for r in rows], xs))


def _slab_line(slab: list[dict[str, Any]], y: float) -> list[dict[str, Any]]:
    return [r for r in slab if abs(float(r["COOR_Y"]) - y) < 1.0e-6]


def analyse_a1(index: TableIndex) -> dict[str, Any]:
    beams = _elements(index.find("VAL_CHEV"))
    slab = index.find("VAL_DALLE")
    reac = index.find("VAL_REAC")[0]
    expected = Q_LINE * L_CAP**2 / 12.0
    out: dict[str, Any] = {"attendu_Nm": expected, "q_N_m": Q_LINE, "L_m": L_CAP}

    def inner(y0: float, x0: float | None) -> tuple[float, float]:
        """Σ MFY of the cap ends at (x0, y0) whose element lies towards Y = 0."""
        total, count = 0.0, 0
        for element in beams:
            ys = [float(r["COOR_Y"]) for r in element]
            for r in element:
                y, x = float(r["COOR_Y"]), float(r["COOR_X"])
                if abs(y - y0) > 1e-6 or (x0 is not None and abs(x - x0) > 1e-6):
                    continue
                other = next(v for v in ys if abs(v - y0) > 1e-6)
                if y0 == 0.0:
                    # Mi-portée : moyenne des deux extrémités d'élément au nœud (saut =
                    # interaction nodale barre–dalle, CA-058), comme la preuve de D1.
                    total += 0.5 * float(r["MFY"])
                    count += 1
                elif abs(other) < abs(y0):
                    total += float(r["MFY"])
                    count += 1
        return total, count

    sections: dict[str, Any] = {}
    for y0 in (-2.0, 2.0):
        bar, count = inner(y0, X_LOADED)
        band = [
            r
            for r in _slab_line(slab, y0)
            if abs(float(r["COOR_X"]) - X_LOADED) <= HALF + 1e-9
        ]
        myy = _trapz(band, "MYY")
        total = bar + myy
        sections[f"Y={y0:+.2f}"] = {
            "barre_MFY_Nm": bar,
            "extremites": count,
            "bande_noeuds": len(band),
            "integrale_MYY_Nm": myy,
            "section_en_T_Nm": total,
            "ecart_relatif": (abs(total) - expected) / expected,
        }
    out["section_en_T"] = sections
    cuts: dict[str, Any] = {}
    for y0 in (-2.0, 0.0, 2.0):
        bar, count = inner(y0, None)
        cuts[f"Y={y0:+.2f}"] = {
            "somme_MFY_chevetres_Nm": bar,
            "extremites": count,
            "integrale_MYY_toute_largeur_Nm": _trapz(_slab_line(slab, y0), "MYY"),
        }
        cuts[f"Y={y0:+.2f}"]["total_Nm"] = (
            bar + cuts[f"Y={y0:+.2f}"]["integrale_MYY_toute_largeur_Nm"]
        )
    support = 0.5 * (cuts["Y=-2.00"]["total_Nm"] + cuts["Y=+2.00"]["total_Nm"])
    statics = support - cuts["Y=+0.00"]["total_Nm"]
    out["coupe_complete"] = {
        **cuts,
        "statique_M_appui_moins_M_mi_portee_Nm": statics,
        "statique_attendue_qL2_8_Nm": Q_LINE * L_CAP**2 / 8.0,
        "ecart_relatif_statique": (statics - Q_LINE * L_CAP**2 / 8.0)
        / (Q_LINE * L_CAP**2 / 8.0),
        "part_de_la_section_en_T_a_l_appui": 0.5
        * (
            sections["Y=-2.00"]["section_en_T_Nm"]
            + sections["Y=+2.00"]["section_en_T_Nm"]
        )
        / support,
    }
    out["reactions_N"] = {k: float(reac[k]) for k in ("DX", "DY", "DZ") if k in reac}
    out["charge_appliquee_N"] = -Q_LINE * L_CAP
    out["alarme"] = (
        "<A> <POSTRELE_70> : EFGE_NOEU extrait dans le repère local des éléments, "
        "confondu ici avec le repère global (ANGL_REP = (0, 0), normale +Z ; CA-058, "
        "DIAG-012)"
    )
    worst = max(abs(s["ecart_relatif"]) for s in sections.values())
    out["ecart_relatif_max"] = worst
    out["verdict"] = "RÉUSSI" if worst <= TOL else "ÉCART > 2 %"
    return out


def analyse_a2(index: TableIndex) -> dict[str, Any]:
    slab = index.find("VAL_DALLE")
    reac = index.find("VAL_REAC")[0]
    expected = Q_SURF * L_SLAB**2 / 12.0
    lines = {}
    for x0 in (5.6, 10.6, 15.6, 20.6, 25.6):
        at = [r for r in _slab_line(slab, 0.0) if abs(float(r["COOR_X"]) - x0) < 1.0e-6]
        value = float(at[0]["MXX"])
        lines[f"X={x0:.2f}"] = {
            "MXX_Nm_m": value,
            "ecart_relatif": (abs(value) - expected) / expected,
        }
    worst = max(abs(v["ecart_relatif"]) for v in lines.values())
    return {
        "attendu_Nm_m": expected,
        "q_Pa": Q_SURF,
        "L_m": L_SLAB,
        "lignes_Y0": lines,
        "reactions_N": {k: float(reac[k]) for k in ("DX", "DY", "DZ") if k in reac},
        "ecart_relatif_max": worst,
        "verdict": "RÉUSSI" if worst <= TOL else "ÉCART > 2 %",
        "alarme": "<A> <POSTRELE_70> : EFGE_NOEU extrait dans le repère local des "
        "éléments, confondu ici avec le repère global (ANGL_REP = (0, 0), normale +Z ; "
        "CA-058, DIAG-012)",
    }


def run(model: str) -> dict[str, Any]:
    ctx = load_project("estacade_pieux_01", ROOT)
    rt = Runtime(ROOT)
    root = derived_root(ctx, model)
    source = next((root / "post").glob("*_modele.comm"))
    work = root / "validation"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    prod = production(ctx)
    stem = f"validation_{model.lower()}"
    comm = work / f"{stem}.comm"
    comm.write_text(build(model, source.read_text("utf-8")), "utf-8")
    mesh_name = f"{stem}{prod.mesh.suffix}"
    shutil.copyfile(prod.mesh, work / mesh_name)
    (work / f"{stem}.export").write_text(
        _export_text(prod, stem, mesh_name, 4), "utf-8"
    )
    report = execute(ctx, rt, comm)
    mess = next(Path(report.work_dir).rglob("fort.6"))
    index = TableIndex(mess.read_text("utf-8", errors="replace"))
    result = analyse_a1(index) if model == "A1" else analyse_a2(index)
    result["execution"] = {
        "run": Path(report.work_dir).name,
        "statut": report.status,
        "duree_s": report.duration_s,
        "comm": comm.relative_to(ROOT).as_posix(),
    }
    return result


def main() -> None:
    out = {
        "lot": "49 ter",
        "critere": "docs/essais_lot49ter.md § 3 (écrit avant l'exécution) : écart ≤ 2 %, "
        "sinon écrit et expliqué",
        "A1": run("A1"),
        "A2": run("A2"),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
