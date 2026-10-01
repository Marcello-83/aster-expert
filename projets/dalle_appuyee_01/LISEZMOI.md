# Projet DALLE-APPUYEE-01 — dalle appuyée sur quatre côtés

Second projet du dépôt (lot 43, mesure d'autonomie de l'outil). Ouvrage décrit par
MM : dalle en béton armé C30/37 de 6,00 m × 4,00 m × 0,30 m, simplement appuyée sur
ses quatre côtés, poids propre et exploitation uniforme de 10 kPa ; déplacements,
moments, ferraillage ELU et ELS (XC1, enrobage 30 mm), comparaison à la solution
analytique (`donnees/sources/description_MM_lot43.md`).

**État : fiche proposée, en attente de l'arbitrage de MM.** Aucune décision
pratique n'est prise ; `projet.yaml` (déclaration du lot 41) sera écrit après
l'arbitrage, l'interface exigeant déjà le maillage et le générateur.

| Fichier | Contenu |
| --- | --- |
| `fiche/hypotheses_dalle_projet.json` | fiche proposée (`HypothesesSheet`), produite par `scripts/build_fiche_lot43.py` : ne jamais l'éditer à la main |
| `fiche/fiche_a_arbitrer.md` | document d'arbitrage pour MM (même script) |
| `donnees/dalle_model_data.yaml` | données chiffrées (`aster_expert.agent.model_data`) : valeurs de la description, le reste « à fournir » |
| `donnees/sources/` | description de MM recopiée à l'identique |
| `navier.py` | solution exacte de Kirchhoff (série de Navier, nombre de termes par doublement jusqu'à convergence ; contrôle par la série de Lévy) |
| `tests/` | tests propres à la dalle |

Reconstruire la fiche : `.venv/bin/python projets/dalle_appuyee_01/scripts/build_fiche_lot43.py`.
