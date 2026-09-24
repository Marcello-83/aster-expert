"""Lot 33, étape 3 : contrôle d'équilibre, indépendant de Code_Aster pour la
part appliquée (intégration sur le MED réel, `aster_expert.meshing
.equilibrium`), et lu (jamais recalculé) pour la part interne (ressorts,
réactions) à partir du `.mess` d'une exécution réelle.

- Résultante appliquée : intégrale de p(z) sur les mailles réelles de
  `ECRAN_POUSSEE` (quadrature de Gauss, `group_pressure_resultant`) + somme
  des forces nodales de la décision 13 sur la poutre (déjà écrites dans le
  `.comm`, jamais recalculées ici : lues du texte généré).
- Ressorts : lit `TAB_RESS_<cas>` (`DEPL`/`DY` par nœud, `COOR_X/Y/Z`) du
  `.mess`, associe chaque nœud à sa classe (mêmes fonctions que le
  générateur, `aster_expert.generation.springs.build_spring_classes`), et
  somme `k_i * DY_i` -- jamais `FORC_NODA`.
- Réactions : lit `TAB_REAC_<cas>` (`REAC_NODA`, `RESULTANTE`) du `.mess`,
  déjà restreint à `_SUPPORT_GROUPS` par le générateur (lot 23).
- Pesanteur : résultante verticale attendue = poids de tous les matériaux
  (aires/longueurs analytiques x épaisseur/section x masse volumique x g).

Usage : python scripts/analyze_lot33_equilibre.py <mess> <comm> <données> \
    <maillage MED> <invariants MED> [--output PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_NUM = re.compile(r"^[-+]?\d+\.\d+E[-+]\d+$")


def parse_tables(text: str) -> list[dict[str, Any]]:
    """Every `IMPR_TABLE` table: header names and numeric rows aligned on
    the last columns (same parser as `scripts/analyze_lot23_essais.py`,
    never re-implemented differently -- CLAUDE.md, "ne pas réimplémenter")."""
    lines = text.splitlines()
    tables = []
    for i, line in enumerate(lines):
        if not line.startswith("##ASTER") or i + 1 >= len(lines):
            continue
        header = lines[i + 1].split()
        rows: list[list[str]] = []
        for row in lines[i + 2 :]:
            if not row.strip() or row.startswith("#"):
                break
            rows.append(row.split())
        tables.append({"header": header, "rows": rows})
    return tables


def table_records(table: dict[str, Any]) -> list[dict[str, float | str]]:
    header = table["header"]
    records = []
    for cells in table["rows"]:
        numeric = []
        for cell in reversed(cells):
            if _NUM.match(cell):
                numeric.append(float(cell))
            else:
                break
        numeric.reverse()
        names = header[len(header) - len(numeric) :]
        records.append(
            {
                **dict(zip(names, numeric, strict=True)),
                "_head": " ".join(cells[: len(cells) - len(numeric)]),
            }
        )
    return records


def find_table(text: str, needle: str) -> list[dict[str, float | str]]:
    for table in parse_tables(text):
        if table["rows"] and needle in table["rows"][0][:4]:
            return table_records(table)
    message = f"table introuvable : {needle}"
    raise KeyError(message)


def spring_resultant_n(mess_text: str, case: str, classes: list[Any]) -> float:
    """Somme k_i * DY_i pour le cas donné (même convention de signe que
    `EFGE_ELNO`'s own `VY`, vérifiée exactement sur le cas isolé
    `data/examples/lot33_equilibre/ressort_seul.comm` : un nœud libre avec
    `FY` appliqué = +1000 N et k = 500 N/m se déplace à DY = +2,00 m, et
    porte VY = +1000 N = k*DY -- même signe que la force EXTERNE appliquée,
    PAS la force que le ressort exerce sur la structure. Pour l'équilibre
    global, c'est `-(k*DY)` qu'il faut sommer aux réactions (voir `main`) :
    cette fonction retourne la quantité brute, jamais déjà retournée.

    Correspondance de chaque ligne de `TAB_RESS_<case>` (COOR_X/Y/Z, DY) aux
    classes de ressort par plus proche voisin, **sommées** : un nœud à la
    limite exacte de deux bandes (ARGI/MARNE) appartient légitimement à une
    classe de chaque bande (`spring_node_areas`'s own docstring, "Each quad
    contributes exactly 1/4 of its projected area to each of its 4 corner
    nodes" -- une limite de bande est un nœud partagé entre deux rangées de
    quadrangles de bandes différentes, chacune avec son propre k_h) : deux
    ressorts `DIS_T` en parallèle au même nœud s'additionnent, jamais un
    seul des deux (constaté ici : 2694 couples classe/nœud pour 2651 nœuds
    géométriquement distincts sur le quai réduit -- 43 nœuds de bordure de
    bande, chacun portant deux ressorts). Correspondance à 1 mm près
    (`IMPR_TABLE`'s own `FORMAT_R='E12.5'`, 6 chiffres significatifs : une
    correspondance exacte par arrondi décimal échoue pour des coordonnées
    > 10 m)."""
    records = find_table(mess_text, f"RESSORTS_{case}")
    by_point: dict[tuple[float, float, float], float] = {}
    for c in classes:
        for x, y, z in c.nodes:
            key = (round(x, 6), round(y, 6), round(z, 6))
            by_point[key] = by_point.get(key, 0.0) + c.stiffness_n_per_m
    points = list(by_point)
    tol = 1.0e-3
    # Appariement par grille de hachage (même motif que
    # `aster_expert.meshing.invariants.find_coincident_pairs`, jamais un
    # O(n*m) point par point -- devenu nécessaire sur le modèle complet, ~3x
    # plus de nœuds que le quai réduit).
    grid: dict[tuple[int, int, int], list[int]] = {}
    for i, p in enumerate(points):
        key = (int(p[0] // tol), int(p[1] // tol), int(p[2] // tol))
        grid.setdefault(key, []).append(i)
    total = 0.0
    unmatched = 0
    for r in records:
        rx, ry, rz = r["COOR_X"], r["COOR_Y"], r["COOR_Z"]
        cx, cy, cz = int(rx // tol), int(ry // tol), int(rz // tol)
        best_point, best_d = None, math.inf
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for i in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        d = math.dist((rx, ry, rz), points[i])
                        if d < best_d:
                            best_point, best_d = points[i], d
        if best_point is None or best_d > tol:
            unmatched += 1
            continue
        total += by_point[best_point] * r["DY"]
    if unmatched:
        message = (
            f"{unmatched} nœud(s) de TAB_RESS_{case} non retrouvés parmi les classes "
            f"(tolérance {tol:g} m)"
        )
        raise ValueError(message)
    return total


def reaction_resultant_n(
    mess_text: str, case: str, components: tuple[str, ...] = ("DY",)
) -> dict[str, float]:
    records = find_table(mess_text, f"REACTIONS_{case}")
    assert len(records) == 1, records
    return {c: float(records[0][c]) for c in components}


def symmetry_check(
    mess_text: str, case: str, tolerance: float = 1e-6
) -> dict[str, Any]:
    """Lot 33, étape 4 : apparie chaque nœud de `TAB_SYM_<case>` (tout le
    maillage, `TOUT="OUI"`) à son image miroir par coordonnées (x, y, z) ->
    (-x, y, z), et compare DY/DZ (égaux) et DX (opposés) -- jamais deux
    paires choisies à la main. L'écart relatif est rapporté au déplacement
    maximal du cas (le critère de l'étape 4, en valeur absolue, n'a de sens
    que rapporté à une échelle de déplacement réelle)."""
    records = find_table(mess_text, f"SYMETRIE_{case}")
    by_key: dict[tuple[int, int, int], dict[str, float]] = {}
    for r in records:
        key = (
            round(r["COOR_X"] / tolerance),
            round(r["COOR_Y"] / tolerance),
            round(r["COOR_Z"] / tolerance),
        )
        by_key[key] = r
    max_abs_depl = max(
        (abs(r[c]) for r in records for c in ("DX", "DY", "DZ")), default=0.0
    )
    worst = 0.0
    worst_detail: dict[str, Any] | None = None
    unmatched = 0
    checked = 0
    for r in records:
        mirror_key = (
            round(-r["COOR_X"] / tolerance),
            round(r["COOR_Y"] / tolerance),
            round(r["COOR_Z"] / tolerance),
        )
        m = by_key.get(mirror_key)
        if m is None:
            unmatched += 1
            continue
        checked += 1
        dy_gap = abs(r["DY"] - m["DY"])
        dz_gap = abs(r["DZ"] - m["DZ"])
        dx_gap = abs(r["DX"] + m["DX"])
        gap = max(dy_gap, dz_gap, dx_gap)
        if gap > worst:
            worst = gap
            worst_detail = {
                "point": (r["COOR_X"], r["COOR_Y"], r["COOR_Z"]),
                "dy_gap": dy_gap,
                "dz_gap": dz_gap,
                "dx_gap": dx_gap,
            }
    return {
        "n_nodes": len(records),
        "n_pairs_checked": checked // 2,
        "n_unmatched": unmatched,
        "max_abs_depl_m": max_abs_depl,
        "worst_gap_m": worst,
        "worst_relative_gap": (worst / max_abs_depl) if max_abs_depl else math.nan,
        "worst_detail": worst_detail,
    }


def beam_nodal_totals(comm_text: str, concept: str) -> tuple[float, float, float]:
    """Somme des FY/MX/FZ des occurrences FORCE_NODALE du concept donné,
    lue directement du texte généré (jamais recalculée -- la décision 13 et
    la répartition tributaire sont déjà un fait du `.comm`)."""
    block_match = re.search(
        rf"{concept} = AFFE_CHAR_MECA\(.*?FORCE_NODALE=\((.*?)\),\n\)",
        comm_text,
        flags=re.S,
    )
    if block_match is None:
        return (0.0, 0.0, 0.0)
    body = block_match[1]
    fy = sum(float(v) for v in re.findall(r"FY=([-\d.eE+]+)", body))
    mx = sum(float(v) for v in re.findall(r"MX=([-\d.eE+]+)", body))
    fz = sum(float(v) for v in re.findall(r"FZ=([-\d.eE+]+)", body))
    return (fy, mx, fz)


def gravity_check(mess_text: str, params: dict[str, Any], mv: Any) -> dict[str, float]:
    """Étape 3, point 4 : résultante verticale (Z) attendue du cas G = poids
    de tous les matériaux (aires/longueurs analytiques, `expected_masses`,
    x épaisseur/section x masse volumique x g -- `PESANTEUR` exclut
    `POUTRE_COUR`, lot 33 étape 3, dont le poids propre est porté par
    `CH_G_POUTRE`, déjà compté ailleurs), comparée à `REAC_NODA`/`DZ` du cas
    G (les ressorts n'ont aucune raideur en Z, `K_T_D_N=(0, k, 0)` : leur
    contribution est nulle par construction, jamais lue)."""
    from aster_expert.meshing.combiwall import expected_masses  # noqa: PLC0415

    masses = expected_masses(params)
    g = mv.si("charges.acceleration_pesanteur")
    epais_tube = mv.si("tube.epaisseur_coque_retenue")
    rho_tube = mv.si("tube.masse_volumique")
    epais_palp = mv.si("palplanche.epaisseur_coque_EPAIS")
    rho_palp = mv.si("palplanche.masse_volumique")
    section_tirant = mv.si("tirants.section_brute")
    rho_tirant = mv.si("tirants.masse_volumique")
    poids_tubes = masses["TUBES"]["mass"] * epais_tube * rho_tube * g
    poids_palps = masses["PALPS"]["mass"] * epais_palp * rho_palp * g
    poids_tirants = masses["TIRANTS"]["mass"] * section_tirant * rho_tirant * g
    expected_z = -(poids_tubes + poids_palps + poids_tirants)
    try:
        reactions_z = reaction_resultant_n(mess_text, "G", ("DZ",))["DZ"]
    except KeyError:
        # Le cas G n'a demandé RESULTANTE que sur DY (reaction_components
        # par défaut, aster_expert.generation.comm.controls_block) : DZ
        # n'a pas été extrait par ce `.comm` -- non un bug de cette analyse,
        # une limite non anticipée avant l'exécution unique du lot 33,
        # rapportée telle quelle plutôt que masquée.
        return {
            "expected_weight_z_n": expected_z,
            "reaction_z_n": None,
            "gap_z_n": None,
            "relative_gap_z": None,
            "note": "DZ non extrait par TAB_REAC_G (reaction_components par défaut "
            "= (DY,)) -- non vérifié par ce lot, limite connue.",
        }
    gap = reactions_z - expected_z
    return {
        "expected_weight_z_n": expected_z,
        "reaction_z_n": reactions_z,
        "gap_z_n": gap,
        "relative_gap_z": (gap / expected_z) if expected_z else math.nan,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("comm", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("maillage", type=Path)
    parser.add_argument("invariants", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    import sys  # noqa: PLC0415

    sys.path.insert(0, str(ROOT / "src"))
    from aster_expert.agent.model_data import load_model_data  # noqa: PLC0415
    from aster_expert.execution.docker_client import find_docker_binary  # noqa: PLC0415
    from aster_expert.generation.springs import (  # noqa: PLC0415
        COMBINED_BAND,
        build_spring_classes,
    )
    from aster_expert.meshing.check import check_med  # noqa: PLC0415
    from aster_expert.meshing.combiwall import build_params  # noqa: PLC0415
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415
    from aster_expert.meshing.equilibrium import (
        group_pressure_resultant,  # noqa: PLC0415
    )
    from aster_expert.meshing.invariants import MedDump  # noqa: PLC0415
    from aster_expert.validation.validate import (
        resolve_digest_for_version,  # noqa: PLC0415
    )

    mess_text = args.mess.read_text(encoding="utf-8")
    comm_text = args.comm.read_text(encoding="utf-8")
    data = load_model_data(args.donnees)
    params = build_params(data)

    k_h = {
        "RESS_AV_ARGI": float(data.items()["sol.k_h_argile_marneuse_raide"].value),
        "RESS_AV_MARNE": float(data.items()["sol.k_h_marne_compacte"].value),
    }
    classes = [c for c in build_spring_classes(params, k_h) if c.band != COMBINED_BAND]

    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        ROOT / "data" / "processed" / "catalogue",
        None,
        ROOT / "config" / "versions.yaml",
    )
    docker_bin = find_docker_binary(None)
    report = check_med(
        args.maillage,
        args.invariants,
        project_root=ROOT,
        config=config,
        docker_bin=docker_bin,
        image_ref=f"simvia/code_aster@{digest}",
    )
    dump = MedDump.model_validate_json(
        (Path(report.work_dir) / "dump.json").read_text(encoding="utf-8")
    )

    from aster_expert.generation.profiles import layered_profile  # noqa: PLC0415
    from aster_expert.generation.values import ModelValues  # noqa: PLC0415

    mv = ModelValues(data)

    def profile_si(
        name: str, component: str | None = None
    ) -> list[tuple[float, float]]:
        points = mv.profile_si(name)
        if component is not None:
            # Par couche (lot 34) : trier des paires (z, p) permute les deux
            # points d'une interface et crée des rampes fictives entre couches.
            return layered_profile(points, component)
        return sorted((z, p) for z, p, _, _ in points)

    profiles = {
        "G": profile_si("eau_terres.profil_poussee_terres_permanent", "G"),
        "Q1": profile_si("eau_terres.profil_poussee_terres_permanent", "Q1"),
        "EAU_P": profile_si("eau_terres.profil_pression_eau_permanent"),
        "EAU_A": profile_si("eau_terres.profil_pression_eau_accidentel"),
    }

    result: dict[str, Any] = {"cases": {}}
    for case, profile in profiles.items():
        screen_fx, screen_fy, screen_fz = group_pressure_resultant(
            dump, "ECRAN_POUSSEE", profile
        )
        beam_fy, beam_mx, beam_fz = beam_nodal_totals(comm_text, f"CH_{case}_POUTRE")
        applied_fy = screen_fy + beam_fy
        applied_fz = screen_fz + beam_fz

        spring_vy = spring_resultant_n(mess_text, case, classes)
        spring_force_on_structure_fy = -spring_vy
        reactions = reaction_resultant_n(mess_text, case)
        internal_fy = spring_force_on_structure_fy + reactions["DY"]

        # Équilibre : F_applied + F_reactions_sur_la_structure +
        # F_ressorts_sur_la_structure = 0, donc internal_fy = -applied_fy ;
        # l'écart est leur somme, jamais leur différence.
        gap_fy = internal_fy + applied_fy
        rel_fy = gap_fy / applied_fy if applied_fy else math.nan

        result["cases"][case] = {
            "screen_resultant_n": {"fx": screen_fx, "fy": screen_fy, "fz": screen_fz},
            "beam_nodal_totals_n": {"fy": beam_fy, "mx": beam_mx, "fz": beam_fz},
            "applied_fy_n": applied_fy,
            "applied_fz_n": applied_fz,
            "spring_vy_n": spring_vy,
            "spring_force_on_structure_fy_n": spring_force_on_structure_fy,
            "reaction_fy_n": reactions["DY"],
            "internal_fy_n": internal_fy,
            "gap_fy_n": gap_fy,
            "relative_gap_fy": rel_fy,
        }

    result["symmetry"] = {}
    for case in ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A"):
        try:
            result["symmetry"][case] = symmetry_check(mess_text, case)
        except KeyError:
            continue

    result["gravity"] = gravity_check(mess_text, params, mv)

    output = args.output or (args.mess.parent / "equilibre_analyse.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
