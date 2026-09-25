"""Lot 34, étape 1 : compare, cas par cas et composante par composante, la
charge assemblée par Code_Aster (sonde de blocage total : -Σ REAC_NODA sur tous
les nœuds, table `CHARGE_<cas>` du `.mess`) à la charge intégrée
indépendamment (Gauss 2x2 sur les mailles réelles de `ECRAN_POUSSEE`, forces
nodales de la poutre lues du `.comm`, poids par les masses analytiques).

Critère (docs/essais_lot34.md, écrit avant l'exécution) : écart relatif
|assemblée_c - intégrée_c| / max_c'(|intégrée_c'|) <= 1e-6 sur X, Y et Z.

Usage : python scripts/analyze_lot34_charge_assemblee.py <mess|-> <comm> <données> \\
    <maillage MED> <invariants MED> [--pression ...] [--output PATH]

`-` à la place du `.mess` : charges intégrées seules (modèle complet, sans sonde).
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import analyze_lot33_equilibre as l33  # noqa: E402

THRESHOLD = 1.0e-6
PRESSURE_CASES = ("G", "Q1", "EAU_P", "EAU_A")


def assembled_load(mess_text: str, case: str) -> dict[str, float]:
    """Charge assemblée (N) = -Σ REAC_NODA (déplacements nuls)."""
    records = l33.find_table(mess_text, f"CHARGE_{case}")
    assert len(records) == 1, records
    r = records[0]
    return {c: -float(r[c]) for c in ("DX", "DY", "DZ")}


def relative_gaps(
    assembled: dict[str, float], integrated: dict[str, float]
) -> dict[str, float]:
    """Écart rapporté à la plus grande composante intégrée du cas. Cas de charge
    intégrée nulle (aucun chargement dans la sonde) : l'échelle est nulle, les
    écarts sont rapportés en valeur absolue (N) -- cas non couvert par le
    critère écrit, signalé par `zero_load` dans le rapport."""
    scale = max(abs(v) for v in integrated.values()) or 1.0
    return {c: (assembled[c] - integrated[c]) / scale for c in assembled}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mess", type=Path)
    parser.add_argument("comm", type=Path)
    parser.add_argument("donnees", type=Path)
    parser.add_argument("maillage", type=Path)
    parser.add_argument("invariants", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--pression",
        choices=("ecran", "tubes", "palplanches", "aucune"),
        default="ecran",
        help="groupe portant la pression dans la sonde analysée",
    )
    args = parser.parse_args(argv)

    from aster_expert.agent.model_data import load_model_data  # noqa: PLC0415
    from aster_expert.execution.docker_client import find_docker_binary  # noqa: PLC0415
    from aster_expert.generation.profiles import (  # noqa: PLC0415
        layer_profiles,
        layered_profile,
    )
    from aster_expert.generation.values import ModelValues  # noqa: PLC0415
    from aster_expert.meshing.check import check_med  # noqa: PLC0415
    from aster_expert.meshing.combiwall import (  # noqa: PLC0415
        build_params,
        expected_masses,
    )
    from aster_expert.meshing.config import load_mesh_config  # noqa: PLC0415
    from aster_expert.meshing.equilibrium import (  # noqa: PLC0415
        _cross,
        _dshape,
        quad_pressure_force,
    )
    from aster_expert.meshing.equilibrium import (
        _weighted_sum as _wsum,
    )
    from aster_expert.meshing.invariants import MedDump  # noqa: PLC0415
    from aster_expert.validation.validate import (  # noqa: PLC0415
        resolve_digest_for_version,
    )

    independent_only = str(args.mess) == "-"
    mess_text = "" if independent_only else args.mess.read_text(encoding="utf-8")
    comm_text = args.comm.read_text(encoding="utf-8")
    data = load_model_data(args.donnees)
    params = build_params(data)
    mv = ModelValues(data)

    config = load_mesh_config(ROOT / "config" / "validation.yaml")
    digest, _ = resolve_digest_for_version(
        ROOT / "data" / "processed" / "catalogue",
        None,
        ROOT / "config" / "versions.yaml",
    )
    report = check_med(
        args.maillage,
        args.invariants,
        project_root=ROOT,
        config=config,
        docker_bin=find_docker_binary(None),
        image_ref=f"simvia/code_aster@{digest}",
    )
    dump = MedDump.model_validate_json(
        (Path(report.work_dir) / "dump.json").read_text(encoding="utf-8")
    )

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

    earth_points = mv.profile_si("eau_terres.profil_poussee_terres_permanent")
    applied_layers = {
        "G": layer_profiles(earth_points, "G"),
        "Q1": layer_profiles(earth_points, "Q1"),
    }
    # Fonction écrite dans le `.comm` : G et Q1 par couche (une occurrence de
    # FORCE_COQUE par couche, sur les mailles dont tous les nœuds sont dans la
    # bande de la couche), l'eau d'une seule fonction continue.
    written = {
        "EAU_P": sorted(
            (z, p)
            for z, p, _, _ in mv.profile_si("eau_terres.profil_pression_eau_permanent")
        ),
        "EAU_A": sorted(
            (z, p)
            for z, p, _, _ in mv.profile_si("eau_terres.profil_pression_eau_accidentel")
        ),
    }

    g = mv.si("charges.acceleration_pesanteur")
    masses = expected_masses(params)
    n_tubes = len(params["tube"]["axes_x"])

    def tie_share(k: int) -> float:
        """Lot 37 : les tirants des tubes de bord, dans les plans de symétrie, ont une
        demi-section (décision 8, point 7) : leur poids est la moitié de celui d'une
        section entière."""
        return 0.5 if k in (1, n_tubes) else 1.0

    weight_analytic = (
        masses["TUBES"]["mass"]
        * mv.si("tube.epaisseur_coque_retenue")
        * mv.si("tube.masse_volumique")
        + masses["PALPS"]["mass"]
        * mv.si("palplanche.epaisseur_coque_EPAIS")
        * mv.si("palplanche.masse_volumique")
        + sum(
            masses[f"TIRANT_{k:02d}"]["mass"] * tie_share(k)
            for k in range(1, n_tubes + 1)
        )
        * mv.si("tirants.section_brute")
        * mv.si("tirants.masse_volumique")
    ) * g

    def mesh_size(group: str, *, length: bool) -> float:
        """Aire (QUAD4, Gauss 2x2) ou longueur (SEG2) d'un groupe de mailles du
        MED : la quantité de matière que Code_Aster pèse, lue du maillage."""
        total = 0.0
        for grp in dump.groups:
            if grp.name != group or grp.level == 1:
                continue
            level = dump.levels[str(grp.level)]
            for cell in grp.ids:
                nodes = level.connectivity[cell]
                pts = [dump.coords[n] for n in nodes]
                if length:
                    total += math.dist(pts[0], pts[1])
                    continue
                c4 = (pts[0], pts[1], pts[2], pts[3])
                for xi, wx in ((-0.5773502691896257, 1.0), (0.5773502691896257, 1.0)):
                    for et, we in (
                        (-0.5773502691896257, 1.0),
                        (0.5773502691896257, 1.0),
                    ):
                        dxi, deta = _dshape(xi, et)
                        n = _cross(_wsum(dxi, c4), _wsum(deta, c4))
                        total += wx * we * math.sqrt(sum(v * v for v in n))
        return total

    weight = (
        mesh_size("TUBES", length=False)
        * mv.si("tube.epaisseur_coque_retenue")
        * mv.si("tube.masse_volumique")
        + mesh_size("PALPS", length=False)
        * mv.si("palplanche.epaisseur_coque_EPAIS")
        * mv.si("palplanche.masse_volumique")
        + sum(
            mesh_size(f"TIRANT_{k:02d}", length=True) * tie_share(k)
            for k in range(1, n_tubes + 1)
        )
        * mv.si("tirants.section_brute")
        * mv.si("tirants.masse_volumique")
    ) * g

    def group_cells(name: str) -> set[int]:
        found: set[int] = set()
        for grp in dump.groups:
            if grp.name == name and grp.level != 1:
                found |= set(grp.ids)
        return found

    level2 = next(
        dump.levels[str(grp.level)]
        for grp in dump.groups
        if grp.name == "ECRAN_POUSSEE" and grp.level != 1
    )
    ecran_cells = group_cells("ECRAN_POUSSEE")
    palps_cells = group_cells("PALPS")
    loaded_cells = {
        "ecran": ecran_cells,
        "tubes": ecran_cells - palps_cells,
        "palplanches": palps_cells,
        "aucune": set(),
    }[args.pression]

    def group_pressure_resultant(
        _dump: Any,
        _group: str,
        profile: list[tuple[float, float]],
        evaluation: str = "gauss",
    ) -> tuple[float, float, float]:
        total = (0.0, 0.0, 0.0)
        for cell in sorted(loaded_cells):
            nodes = level2.connectivity[cell]
            corners = (
                dump.coords[nodes[0]],
                dump.coords[nodes[1]],
                dump.coords[nodes[2]],
                dump.coords[nodes[3]],
            )
            f = quad_pressure_force(corners, profile, evaluation)  # type: ignore[arg-type]
            total = (total[0] + f[0], total[1] + f[1], total[2] + f[2])
        return total

    band_tolerance = 1.0e-6

    def layered_applied_resultant(layers: list[Any]) -> tuple[float, float, float]:
        """Ce que le `.comm` applique : pour chaque maille chargée, la fonction de
        la couche dont la bande contient tous ses nœuds, évaluée aux nœuds ; une
        maille dans aucune bande ne reçoit rien."""
        total = (0.0, 0.0, 0.0)
        for cell in sorted(loaded_cells):
            nodes = level2.connectivity[cell]
            corners = (
                dump.coords[nodes[0]],
                dump.coords[nodes[1]],
                dump.coords[nodes[2]],
                dump.coords[nodes[3]],
            )
            zs = [c[2] for c in corners]
            for layer in layers:
                if all(
                    layer.z_low - band_tolerance <= z <= layer.z_high + band_tolerance
                    for z in zs
                ):
                    f = quad_pressure_force(corners, list(layer.points), "nodes")
                    total = (total[0] + f[0], total[1] + f[1], total[2] + f[2])
                    break
        return total

    result: dict[str, Any] = {
        "threshold": THRESHOLD,
        "pression_sur": args.pression,
        "n_loaded_cells": len(loaded_cells),
        "weight_mesh_n": weight,
        "weight_analytic_n": weight_analytic,
        "weight_relative_gap": (weight - weight_analytic) / weight_analytic,
        "cases": {},
    }
    for case, profile in profiles.items():
        sx, sy, sz = group_pressure_resultant(dump, "ECRAN_POUSSEE", profile)
        by, _, bz = l33.beam_nodal_totals(comm_text, f"CH_{case}_POUTRE")
        integrated = {
            "DX": sx,
            "DY": sy + by,
            "DZ": sz + bz + (-weight if case == "G" else 0.0),
        }
        ex, ey, ez = (
            layered_applied_resultant(applied_layers[case])
            if case in applied_layers
            else group_pressure_resultant(dump, "ECRAN_POUSSEE", written[case], "nodes")
        )
        as_evaluated = {
            "DX": ex,
            "DY": ey + by,
            "DZ": ez + bz + (-weight if case == "G" else 0.0),
        }
        assembled = None if independent_only else assembled_load(mess_text, case)
        gaps = None if assembled is None else relative_gaps(assembled, integrated)
        gaps_evaluated = (
            None if assembled is None else relative_gaps(assembled, as_evaluated)
        )
        result["cases"][case] = {
            "integrated_n": integrated,
            "screen_n": {"DX": sx, "DY": sy, "DZ": sz},
            "beam_n": {"DY": by, "DZ": bz},
            "weight_n": weight if case == "G" else 0.0,
            "assembled_n": assembled,
            "relative_gap": gaps,
            "zero_load": all(v == 0.0 for v in integrated.values()),
            "verdict": None
            if gaps is None
            else "ABSENT"
            if all(abs(v) <= THRESHOLD for v in gaps.values())
            else "PRESENT",
            "as_evaluated": {
                "integrated_n": as_evaluated,
                "screen_n": {"DX": ex, "DY": ey, "DZ": ez},
                "relative_gap": gaps_evaluated,
                "verdict": None
                if gaps_evaluated is None
                else "ABSENT"
                if all(abs(v) <= THRESHOLD for v in gaps_evaluated.values())
                else "PRESENT",
            },
        }

    # Informatif : Q3 et A (charges ponctuelles écrites dans le .comm).
    bollard = re.search(
        r"GROUP_NO=\(\"BOLLARD\",\), FY=([-\d.eE+]+), FZ=([-\d.eE+]+)", comm_text
    )
    defense = re.search(r"GROUP_MA=\(\"DEFENSE\",\), FY=([-\d.eE+]+)\)", comm_text)
    info: dict[str, Any] = {}
    if bollard and not independent_only:
        info["Q3"] = {
            "written_n": {
                "DX": 0.0,
                "DY": float(bollard[1]),
                "DZ": float(bollard[2]),
            },
            "assembled_n": assembled_load(mess_text, "Q3"),
        }
    if defense and not independent_only:
        area = masses["DEFENSE"]["mass"]
        info["A"] = {
            "written_n": {"DX": 0.0, "DY": float(defense[1]) * area, "DZ": 0.0},
            "assembled_n": assembled_load(mess_text, "A"),
        }
    result["informative"] = info

    output = args.output or (args.mess.parent / "charge_assemblee_analyse.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
