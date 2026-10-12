"""Contrôle à la main du lot 50 bis (docs/essais_lot50bis.md § 2, critère écrit avant) :
moment de la section du tablier à mi-portée sous Q, b = 2,00 m (P24).

    PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/controles_lot50bis.py

Lit `resultats/controles/equilibre.json` et les livrables ; écrit
`references/controles_lot50bis/controles_analytiques.json`.
"""

import json
from pathlib import Path

from aster_expert.projet.context import load_project
from pontons_alu_01.controles_analytiques import run_lot50bis

ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    ctx = load_project("pontons_alu_01", ROOT)
    target = ctx.path("references/controles_lot50bis/controles_analytiques.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    result = run_lot50bis(ctx)
    target.write_text(
        json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    q = result["Q_mi_portee"]
    print(
        "Q_mi_portee",
        q["verdict"],
        f"M = {q['moment_section_nm']:.1f} N·m",
        f"q·b·L²/8 = {q['qbL2_sur_8_nm']:.1f} N·m",
        f"écart {q['ecart_relatif']:.3e}",
    )


if __name__ == "__main__":
    main()
