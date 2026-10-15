# PONTONS-ALU-01 — une travée de panne en aluminium soudé (lots 50 et 50 bis)

Passerelle d'accès sur pieux (« panne ») reprise d'un AVP Sofistik pour un calcul PRO.
Consigne : `docs/lots/lot50_consigne.md` ; données : `donnees/sources/annexe_donnees_lot50.md`
(décisions P1 à P23 dans la fiche) ; essais : `docs/essais_lot50.md`. Lot 50 bis : consigne
`docs/lots/lot50bis_consigne.md`, décisions P24 à P28, essais `docs/essais_lot50bis.md`, compte
rendu `docs/lots/lot50bis_compte_rendu.md`.

| Fichier | Rôle |
| --- | --- |
| `maillage/maillage_pontons.py` | script Salomé autonome, paramètres en tête (§ D2) ; produit `pontons.med` |
| `geometrie.py`, `invariants.py` | lecture du bloc de paramètres, comptages et invariants calculés à part |
| `generation.py`, `extensions.py` | `.comm` à plat (repli), résultantes et ressorts du harnais D |
| `combinaisons.py` | jeux A (S2) et B (PRO, EN 1990) |
| `controles_analytiques.py`, `syntheses.py` | contrôles § 2 et livrables des jeux A et B |
| `lot50bis.py` | taux élastique simplifié (P28, indicateur, pas l'EC9), jeu B′ (P27), balayage de l'inertie |
| `scripts/` | fiche, invariants, contrôles, livrables, image du modèle |

Enchaînement : `aster-expert projet pontons_alu_01 tout`, puis
`PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/controles_lot50.py` et
`.../scripts/livrables_lot50.py`. Changer la géométrie : modifier le bloc de paramètres du
script de maillage, puis `scripts/ecrire_invariants.py` et `scripts/fiche_lot50.py`.

Lot 50 bis, balayage de l'inertie : pour k = 3 puis 5, `PONTONS_K_IY=k` et les étapes
`generer`, `valider`, `executer`, `controles`, `livrables --sous-etape` preparer, executer,
verifier, traiter ; déplacer `resultats/livrables` vers `resultats/balayage/k<k>/` ; puis la
référence (sans la variable) jusqu'à `ingenieur`, `scripts/controles_lot50bis.py` et
`scripts/livrables_lot50bis.py --lot50 <livrables du lot 50>`.

## Lot 51 — palée complète, appuis néoprène, matrice de variantes

Consigne `docs/lots/lot51_consigne.md` ; décisions P29 à P43 dans la fiche ; essais
`docs/essais_lot51.md` ; compte rendu `docs/lots/lot51_compte_rendu.md`. Le projet est passé au
modèle du lot 51 (`projet.yaml` : maillage, générateur, harnais) ; les modules des lots 50 à 50
quinquies restent pour leurs références.

| Fichier | Rôle |
| --- | --- |
| `maillage/maillage_palee.py` | script Salomé autonome de la palée et des trois travées ; seul `H_PILES` change par fichier de paramètres |
| `geometrie_lot51.py`, `invariants_lot51.py` | géométrie lue dans le bloc de paramètres, invariants calculés à part (`maillage/invariants_palee.yaml` : R) |
| `variantes_lot51.yaml`, `variantes_lot51.py` | les douze variantes (base et écarts) ; `PONTONS_VARIANTE` choisit celle de la chaîne |
| `generation_lot51.py`, `extensions_lot51.py` | `.comm` unique paramétré par la variante ; extensions du harnais D |
| `combinaisons_lot51.py` | jeu B′ révisé et ELU accidentel en règles (branches × emplacements), dénombrement, enveloppes par décomposition |
| `exports_lot51.py`, `scripts/lot51.py` | exécution des variantes, harnais, exports du § 6, comparaison du § 7, dépôt |
| `scripts/recombiner_lot51.py` | `recombiner.py` livré (bibliothèque standard) : énumère les combinaisons depuis les CSV |

Enchaînement : `PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot51.py tout`
(ou `executer`, `controles`, `exports`, `depot`, avec `--variantes R,E,...`). Sorties sous
`resultats/lot51/` ; références versionnées sous `references/execution_lot51/`.

## Lot 51 bis — appuis articulés à axe, tablier rehaussé, palées types, équilibre des palées

Consigne `docs/lots/lot51bis_consigne.md` ; décisions P44 à P51 dans la fiche (choix de l'agent A8,
A9) ; essais `docs/essais_lot51bis.md` ; compte rendu `docs/lots/lot51bis_compte_rendu.md`. Le
projet est passé au modèle du lot 51 bis (`projet.yaml` : maillage, générateur, harnais) ; les
modules des lots 50 à 51 restent pour leurs références.

| Fichier | Rôle |
| --- | --- |
| `maillage/maillage_palee_51bis.py` | script Salomé autonome de la palée type et des trois travées ; `H_ANNEAU` et `H_PILES` changent par fichier de paramètres |
| `geometrie_lot51bis.py`, `invariants_lot51bis.py` | géométrie et cotes lues dans le bloc de paramètres, appuis à axe, invariants calculés à part (`maillage/invariants_palee_51bis.yaml` : H80C) |
| `variantes_lot51bis.yaml`, `variantes_lot51bis.py` | les cinq variantes (H40C, H40P, H80C, H80P, H80C-S3) ; `PONTONS_VARIANTE` choisit celle de la chaîne |
| `generation_lot51bis.py`, `extensions_lot51bis.py` | `.comm` unique paramétré (axes en LIAISON_DDL, cas DEJ) ; extensions du harnais D |
| `combinaisons_lot51bis.py` | règles du lot 51 avec DEJ lié au facteur de G (P49) |
| `exports_lot51bis.py`, `scripts/lot51bis.py` | exécution des variantes, harnais, exports (dont `appuis_axes.csv`, `palee_equilibre.csv`), comparaison, critères, dépôt |
| `scripts/recombiner_lot51bis.py` | `recombiner.py` livré (bibliothèque standard) |

Enchaînement : `PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot51bis.py tout`
(ou `executer`, `controles`, `exports`, `depot`, avec `--variantes H40C,...`) ; `charges.med` de
H80C : `PONTONS_VARIANTE=H80C aster-expert projet pontons_alu_01` maillage, generer, valider,
executer, puis `livrables --sous-etape` preparer, executer, verifier, traiter, charges. Sorties
sous `resultats/lot51bis/` ; références versionnées sous `references/execution_lot51bis/`.
