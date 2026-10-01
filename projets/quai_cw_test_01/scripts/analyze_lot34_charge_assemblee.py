"""Lot 34, étape 1 : compare, cas par cas et composante par composante, la
charge assemblée par Code_Aster (sonde de blocage total : -Σ REAC_NODA sur tous
les nœuds, table `CHARGE_<cas>` du `.mess`) à la charge intégrée
indépendamment (Gauss 2x2 sur les mailles réelles de `ECRAN_POUSSEE`, forces
nodales de la poutre lues du `.comm`, poids par les masses analytiques).

Critère (docs/essais_lot34.md, écrit avant l'exécution) : écart relatif
|assemblée_c - intégrée_c| / max_c'(|intégrée_c'|) <= 1e-6 sur X, Y et Z.

Usage : python projets/quai_cw_test_01/scripts/analyze_lot34_charge_assemblee.py <mess|-> <comm> <données> \\
    <maillage MED> <invariants MED> [--pression ...] [--output PATH]

`-` à la place du `.mess` : charges intégrées seules (modèle complet, sans sonde).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "projets"))

from quai_cw_test_01.controles import integrated_loads  # noqa: E402


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

    # Lot 41 : le calcul vit dans le paquet du projet (`quai_cw_test_01.controles`),
    # appelé aussi par les contrôles D du tronc commun ; ce script n'en est plus que
    # l'interface en ligne de commande.
    result = integrated_loads(
        mess_text=None if str(args.mess) == "-" else args.mess.read_text("utf-8"),
        comm_text=args.comm.read_text(encoding="utf-8"),
        data_path=args.donnees,
        mesh_path=args.maillage,
        invariants_path=args.invariants,
        repo_root=ROOT,
        pression=args.pression,
    )

    output = args.output or (args.mess.parent / "charge_assemblee_analyse.json")
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
