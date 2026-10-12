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
