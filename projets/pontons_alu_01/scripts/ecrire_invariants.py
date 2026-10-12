"""Écrit maillage/invariants.yaml à partir des paramètres du script de maillage (lot 50).

PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/ecrire_invariants.py
"""

from pathlib import Path

import yaml

from pontons_alu_01.geometrie import geometry
from pontons_alu_01.invariants import invariants

HEAD = (
    "# Invariants du maillage de PONTONS-ALU-01 (lot 50) : calculés par\n"
    "# pontons_alu_01.invariants à partir des seuls paramètres de maillage_pontons.py,\n"
    "# avant toute exécution (scripts/ecrire_invariants.py). Ne pas éditer.\n"
)


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "maillage" / "invariants.yaml"
    text = yaml.safe_dump(invariants(geometry()), sort_keys=False, allow_unicode=True)
    target.write_text(HEAD + text, encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
