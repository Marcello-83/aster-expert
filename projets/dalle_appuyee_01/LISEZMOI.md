# Projet DALLE-APPUYEE-01 — dalle appuyée sur quatre côtés

Second projet du dépôt (lot 43, mesure d'autonomie de l'outil). Dalle en béton armé
C30/37 de 6,00 m (X) × 4,00 m (Y) × 0,30 m, appui bilatéral sur les quatre bords, DKT,
élasticité linéaire non fissurée ; poids propre (25 kN/m³) et exploitation de 10 kPa
(catégorie E) ; ferraillage ELU et ELS (XC1). Décisions : arbitrage de MM
(`donnees/sources/arbitrage_dalle_appuyee_01_v1.md`) et complément ELS.

**Niveau atteint : E** pour la flèche et les moments au centre (série de Navier,
`docs/essais_lot43.md`) ; D pour l'équilibre, la symétrie et les combinaisons. Les
flèches sont **instantanées et non fissurées** (long terme hors périmètre).

| Fichier | Contenu |
| --- | --- |
| `projet.yaml` | déclaration : fiche arbitrée, données, maillage, générateur, contrôles D, combinaisons, plaque à ferrailler (2D) |
| `fiche/hypotheses_dalle_projet.json`, `fiche_a_arbitrer.md` | fiche proposée de la phase 1 et document d'arbitrage (`scripts/build_fiche_lot43.py`) |
| `fiche/hypotheses_dalle_arbitree.json`, `fiche_arbitree.md` | fiche arbitrée courante : celle du lot 43 plus la décision de MM sur Es = 200 GPa (`scripts/decisions_lot44.py`) |
| `fiche/historique/` | fiche arbitrée du lot 43, telle quelle (`scripts/arbitrer_fiche_lot43.py`) |
| `fiche/hypotheses_dalle_rejeu_lot44.json`, `fiche_a_arbitrer_rejeu_lot44.md` | rejeu de la catégorie `choix_agent` sur la fiche de la phase 1 (`scripts/rejeu_choix_agent_lot44.py`) |
| `donnees/` | données (`dalle_model_data.yaml`), sources recopiées à l'identique, données de la phase 1 figées |
| `discretisation.py`, `maillage/` | comptages analytiques, script Salomé, invariants des trois maillages (générés, ne pas éditer) |
| `generation.py`, `extensions.py` | générateur du `.comm` et extensions déclarées |
| `navier.py`, `references/navier_lot43.json` | solution de Kirchhoff (Navier, contrôle par Lévy) calculée avant exécution |
| `references/niveau_e_lot43.json`, `references/cas/` | valeurs lues et verdicts de la suite de convergence ; cas versionnés (rejouables) |
| `scripts/` | fiche, arbitrage, invariants, référence, niveau E, versement des connaissances |
| `tests/` | tests propres à la dalle |
| `resultats/` | sorties de `aster-expert projet dalle_appuyee_01 <étape>` (non versionné) |

Chaîne : `aster-expert projet dalle_appuyee_01 tout` (maillage 48×32), puis
`scripts/niveau_e_lot43.py` pour la suite de convergence et le niveau E.
