# Projet ESTACADE-PIEUX-01

Estacade sur pieux, **contre-calcul d'un modèle d'avant-projet non validé** (lot 47) :
dalle DKT de 31,20 × 6,00 × 0,40 m sur 7 chevêtres POU_D_T de 1,20 × 0,90 m au plan
moyen, 14 pieux tubulaires corrodés (POU_D_T, tube équivalent par tronçon), ressorts
horizontaux kx = ky tous les 0,50 m, DZ = 0 en pointe ; charges PP, G2, UDL, TR, FR,
TE± et 242 positions mobiles de TS et LM2 ; combinaisons 100 à 115 du modèle source.
Aucune comparaison n'y est un niveau E. Les données viennent d'un projet réel : aucun nom
de site, de client ou de bureau d'études n'est versé (test
`tests/unit/test_confidentialite.py`, liste locale non versionnée).

| Répertoire / fichier | Contenu |
| --- | --- |
| `donnees/sources/` | annexe B de la consigne (valeurs numériques seules), arbitrage E1 à E16 de MM |
| `donnees/` | données structurées (source : « référence externe, tableau Bn ») |
| `fiche/` | fiche : E1 à E16 (`arbitrage_mm`), U1 à U6 (`choix_agent`), K1 à K6 (constats) |
| `maillage/` | script Salomé, paramètres et invariants des trois tailles (0,10 / 0,05 / 0,025 m) |
| `donnees.py`, `discretisation.py`, `charges_mobiles.py`, `combinaisons.py` | modèle, maillage, positions mobiles, combinaisons de B5 |
| `generation.py`, `extensions.py` | générateur du `.comm` et extensions déclarées dans `projet.yaml` |
| `lecture.py`, `comparaison.py` | lecture du MED (tous les pas) et comparaison C1 à C13 |
| `scripts/` | scripts du lot 47 (sonde, constats, fiche, invariants, convergence, comparaison, variantes, explications, connaissances) |
| `references/` | cas versionnés (sonde S1, production), convergence, comparaison, explications |
| `livrables/notes/` | notes Word d'hypothèses et de résultats |
| `resultats/paquet/` | paquet de résultats versionné (niveau C) |

Rapport : `docs/essais_lot47.md` ; journal d'autonomie : `docs/lots/lot47_journal_autonomie.md`.
