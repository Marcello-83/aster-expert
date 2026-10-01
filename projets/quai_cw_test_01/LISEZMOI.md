# Projet QUAI-CW-TEST-01 — quai combi-wall

Premier projet du dépôt (lot 41) : le quai combi-wall des lots 19 à 39, séparé du
tronc commun `aster_expert`. Sa déclaration `projet.yaml` est la seule interface
avec le tronc commun (schéma `aster_expert.projet.declaration`).

| Répertoire | Contenu |
| --- | --- |
| `projet.yaml` | déclaration : fiche, données, maillage, générateur, contrôles D, combinaisons, ferraillage, synthèse |
| `fiche/` | fiche d'hypothèses arbitrée (constats `code_aster` cités par référence à `connaissances/constats_code_aster/`) et fiche initiale du lot 14 |
| `donnees/` | données chiffrées (`combiwall_model_data.yaml`) et leurs sources (`combiwall_inputs/`, arbitrages de MM recopiés à l'identique) |
| `maillage/` | script Salomé (octets figés : son empreinte fonde le cache de maillage vérifié) et invariants générés |
| `generation/`, `meshing/`, `report/` | générateur du `.comm`, comptages analytiques, synthèse et vues (déplacés de `src/` au lot 41) |
| `extensions.py`, `controles.py`, `rapports.py` | extensions nommées par `projet.yaml` : paramètres du maillage, génération, charge intégrée, forces des ressorts, prose des rapports |
| `scripts/` | scripts des lots 27 à 39 propres au quai, extraction des constats et comparaison du lot 41 |
| `tests/` | tests propres au quai |
| `references/` | sorties de référence figées avant la restructuration (lot 41, étape 1) et comparaison de la chaîne rejouée |
| `resultats/` | sorties de `aster-expert projet quai_cw_test_01 <étape>` (non versionné) |

Chaîne : `aster-expert projet quai_cw_test_01 tout` (ou étape par étape, voir le
`README.md` du dépôt). Niveau atteint sur le modèle complet : C avec contrôles D,
jamais E.
