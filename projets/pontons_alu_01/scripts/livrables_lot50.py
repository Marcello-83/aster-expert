"""Livrables propres au projet (lot 50) : torseurs des jeux A et B, réactions,
déplacements, comparaison à l'AVP, à partir des cas élémentaires des livrables.

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/livrables_lot50.py
"""

from pathlib import Path

from aster_expert.projet.context import load_project
from pontons_alu_01.syntheses import write_all

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    ctx = load_project("pontons_alu_01", ROOT)
    out = ctx.results_dir / "livrables" / "paquet" / "comparaison"
    summary = write_all(ctx, out)
    print(out, len(summary["fichiers"]), "fichiers")


if __name__ == "__main__":
    main()
