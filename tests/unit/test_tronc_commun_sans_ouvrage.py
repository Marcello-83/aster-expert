"""Le tronc commun ne contient aucune référence au quai (lot 41, étape 2.2).

Règle du dépôt : tout code propre à un ouvrage va dans `projets/<nom>/`, jamais
dans `src/`. La liste ci-dessous est tirée de l'annexe « éléments propres au
combi-wall dans `src/` » de l'audit du lot 40 (`docs/audit/audit_lot40.md`, § 5.1) :
noms de groupes, cas de charge, clés de données, couches de sol, nom du projet et
de son paquet. Le test lit tous les fichiers texte de `src/` (code, docstrings,
commentaires) : une seule occurrence le fait échouer, avec le fichier et la ligne.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"

# Annexe § 5.1 de l'audit du lot 40, colonne « élément codé en dur ».
_IDENTIFIERS = (
    # groupes du maillage et du `.comm` du quai
    "TUBE_0",
    "POUTRE_COUR",
    "ECRAN_POUSSEE",
    "SYM_G",
    "SYM_D",
    "PIED_TUBES",
    "ENV_CYLINDRE",
    "PALPS",
    "PALP_0",
    "RESS_AV_ARGI",
    "RESS_AV_MARNE",
    "ANCRAGES",
    "BOLLARD",
    "DEFENSE",
    "TIRANT_",
    "TETE_TUBE",
    "GEN_SYMG_ROT",
    "GEN_SYMG_RING",
    "GEN_SYMD_ROT",
    "GEN_SYMD_RING",
    "GEN_POUTRE_",
    # cas élémentaires propres au quai
    "EAU_P",
    "EAU_A",
    # données et couches de sol (terre.py, combinations.py, cli.py)
    "tube.rayon",
    "k_h_argile",
    "k_h_marne",
    "argile marneuse",
    "marne compacte",
    "combiwall_model_data",
    "combiwall_inputs",
    # projet, fiche et paquet du projet
    "combiwall",
    "combi-wall",
    "QUAI-CW",
    "quai_cw_test_01",
    # dalle appuyée et estacade sur pieux (lot 48 bis, audit R5 : même frontière)
    "dalle_appuyee",
    "DALLE-APPUYEE",
    "estacade_pieux",
    "ESTACADE-PIEUX",
    "chevêtre",
    "chevetre",
)
_WORDS = re.compile(r"\b(quais?|estacades?)\b", re.IGNORECASE)
_TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".toml"}


def _occurrences() -> list[str]:
    found = []
    for path in sorted(_SRC.rglob("*")):
        if not path.is_file() or path.suffix not in _TEXT_SUFFIXES:
            continue
        if "__pycache__" in path.parts:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            hits = [i for i in _IDENTIFIERS if i in line]
            if _WORDS.search(line):
                hits.append(_WORDS.search(line).group(1).lower())  # type: ignore[union-attr]
            found += [f"{path.relative_to(_SRC)}:{number}: {h}" for h in hits]
    return found


def test_the_common_trunk_names_no_structure() -> None:
    assert _occurrences() == []


def test_the_check_would_see_an_occurrence(tmp_path: Path) -> None:
    """Le motif n'est pas vide : une ligne du quai écrite dans un fichier de `src`
    serait trouvée (contrôle du contrôle)."""
    line = 'GROUP_MA=("POUTRE_COUR",)  # poutre du quai'
    assert any(i in line for i in _IDENTIFIERS)
    assert _WORDS.search(line)
