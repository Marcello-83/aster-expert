# Essais du lot 50 — PONTONS-ALU-01, une travée de panne en aluminium au niveau PRO

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot50_consigne.md`. Données : annexe
« Données » (`projets/pontons_alu_01/donnees/sources/annexe_donnees_lot50.md`), décisions P1 à
P23 de MM dans la fiche.

## 1. Modèle (avant exécution)

- Maillage : `projets/pontons_alu_01/maillage_pontons.py`, script Salomé autonome, paramètres
  en tête ; 405 nœuds, 373 SEG2, 72 QUAD4 ; 95 groupes ; 51 liaisons rigides (44 pannes, 3
  têtes de profilés supports, 2 têtes et 2 pieds de poteaux), 3 articulations des profilés
  supports sur le chevêtre. Comptages calculés avant l'exécution par
  `pontons_alu_01.geometrie` (module distinct du script) : 350 invariants tenus.
- Barres : POU_D_T ; semelle : DKT ; sol : DIS_T répartis par `RIGI_PARASOL` (cas test
  `ssls135a`, radier DKT sur `RIGI_PARASOL`).
- Cas élémentaires : G1, G2, Q, QD (Q½), HU, HD (1 kPa), AMM, AMP, ACM, ACP, AAM, AAP
  (`MACRO_ELAS_MULT`), TP, TM, TAP, TAM (`MECA_STATIQUE`, un champ de matériau par cas).

## 2. Critères des contrôles analytiques (écrits avant la lecture des résultats)

Écrits et commités avant toute lecture des efforts, des déplacements ou des réactions du
calcul. Seul le harnais D par défaut (équilibre de chaque cas) a été lu avant ce
commit, sous la forme de son verdict.

### 2.1 Poids propre G1

Poids calculé à la main à partir des seules données (§ D3, P3, P19, P20, géométrie § D2) :

| Famille | Calcul | Poids (N) |
| --- | --- | --- |
| Poutres principales | 2 × 6,25 m × 4 440 mm² × 27 kN/m³ | 1 498,5 |
| Montants | 6 × 1,50 m × 4 004 mm² × 27 kN/m³ | 972,97 |
| Diagonales | (1,6771 + 3 × 2,1213 + 1,8028) m × 4 004 mm² × 27 kN/m³ | 1 064,2 |
| Pannes secondaires | 4 × 6,25 m × 900 mm² × 27 kN/m³ | 607,5 |
| Profilés supports | 3 × 0,15 m × 4 004 mm² × 27 kN/m³ | 48,65 |
| Chevêtre | 2,00 × 0,25 × 0,40 m × 25 kN/m³ | 5 000,0 |
| Poteaux | 2 × 1,32 m × π × 0,25² m² × 25 kN/m³ | 12 959,1 |
| Semelle | 1,26 × 2,90 × 0,25 m × 25 kN/m³ | 22 837,5 |
| **Total** | | **44 988,4** |

Critère : la réaction verticale totale sous G1 (rotules côté quai + ressorts de sol)
égale 44 988,4 N à 0,5 % près. Les tronçons rigides (liaisons) n'ont pas de poids.

### 2.2 Exploitation Q = 5 kPa sur tout le tablier : moment à mi-portée

Largeur chargée b = 1,50 m (tablier limité aux axes des poutres principales, largeurs
d'influence de P22 ; b n'est pas donné par l'annexe, point à confirmer par MM), L = 6,25 m :
q·b·L²/8 = 5 000 × 1,50 × 6,25² / 8 = 36 621 N·m.

Lecture : coupe X = L/2 = 3,125 m, à travers les deux poutres principales, les quatre
pannes secondaires et la diagonale 3 (aucun montant n'est coupé : la part des montants est
nulle à cette abscisse). Pour chaque barre coupée, le torseur à la coupe est interpolé
linéairement entre les extrémités de l'élément qui la traverse (EFGE_ELNO du cas Q) et
ramené au repère global ; le moment total autour de l'axe Y global est
M = Σ (M · e_Y) + Σ N_X · (z − z_PP), z_PP = plan moyen des poutres principales (le bras
de levier des pannes, 0,10 m, entre ainsi par leur effort normal). Critère : |M − 36 621|
≤ 10 % de 36 621. Au-delà, l'écart est expliqué (encastrement partiel du tablier par les
profilés supports soudés, effet d'arc entre la rotule et les pieds des profilés).

### 2.3 Température

Rapportés sans critère : effort normal des poutres principales sous TP et TM (minimum,
maximum, valeur à mi-portée) et déplacement DX en tête des poteaux. Ils mesurent la
retenue entre la rotule côté quai et les profilés supports fixes. Ordre de grandeur pour
un tablier totalement bridé : N = E·A·α·ΔT = 70 000 × 4 440 × 23·10⁻⁶ × 46 = 329 kN par
poutre principale sous T+ ; pour un tablier libre : DX(L) = α·ΔT·L = 6,6 mm.

### 2.4 Plausibilité

Flèche UZ sous l'ELS caractéristique (jeu B, enveloppe) comparée, pour ordre de grandeur
seulement, aux valeurs de l'AVP (−29,6 / +7,5 mm, UY 2,7 mm) : la géométrie diffère, ce
n'est pas un critère.

## 3. Résultats des contrôles (niveau D)

Exécution de référence : `20261012T130752-dcba979a` (completed_ok, 0 alarme). Première
exécution de post-traitement des livrables (`20261012T130649-e18ee9e7`) : alarme
`<A> <CALCULEL2_89>` (« Le champ EFGE_NOEU n'a pas pu être calculé ») sur la semelle,
aucun diagnostic dans la base ; cause retenue (déduction, confirmée par l'exécution
suivante sans alarme) : `EFGE_NOEU` demandé après un `EFGE_ELNO` restreint aux barres ne
recalcule pas `EFGE_ELNO` sur la semelle. Correction : `EFGE_NOEU` de la semelle calculé
en production avant `EFGE_ELNO` des barres (ordre de l'estacade). Les tables de
post-traitement égalent celles de la production (10 608 valeurs E20.12 identiques).

### 3.1 Harnais D par défaut

Équilibre des 16 cas : écart relatif maximal 8,2·10⁻¹² (TP) ; pesanteur G1 : 1,2·10⁻¹²
(`references/execution_lot50/controles_d.md`). RÉUSSI.

### 3.2 Poids propre G1 (critère § 2.1)

Réaction verticale totale 44 988,38 N (rotules 2 041,6 N, ressorts 42 946,8 N) contre
44 988,4 N calculés à la main : écart 3,9·10⁻⁷. **RÉUSSI**.

### 3.3 Moment à mi-portée sous Q (critère § 2.2)

`references/controles_lot50/controles_analytiques.json`. Coupe X = 3,125 m :

| Barre | N (kN) | MFY (kN·m) | Contribution (kN·m) |
| --- | --- | --- | --- |
| PP_YM | +37,6 | −11,50 | −11,50 |
| PP_YP | +42,4 | −11,83 | −11,83 |
| PANNE_1 | −25,7 | −0,24 | −2,81 |
| PANNE_2 | −17,2 | −0,18 | −1,90 |
| PANNE_3 | −17,3 | −0,06 | −1,79 |
| PANNE_4 | −26,0 | −0,20 | −2,80 |
| DIAG_3 | +2,0 | −3,23 | −3,45 |
| **Total** | | | **−36,07** |

|M| = 36,07 kN·m contre q·b·L²/8 = 36,62 kN·m : écart 1,5 %. **RÉUSSI**. Vérification
statique indépendante : R_quai·L/2 − q·b·(L/2)²/2 = 36,10 kN·m (R_quai = 23,27 kN contre
q·b·L/2 = 23,44 kN : les profilés supports soudés reprennent un peu de moment
d'extrémité), écart de 0,03 kN·m à la somme des barres (interpolation linéaire dans
l'élément).

Constat : les pannes secondaires, soudées à chaque croisement avec 0,10 m
d'excentricité (P7), travaillent en membrure comprimée du tablier (−17 à −26 kN sous Q
seul) ; les poutres principales sont tendues (+38 à +42 kN). Ce fonctionnement dépend
directement de P7 (soudure à chaque croisement) : à signaler pour l'EC9 des pannes
(50 × 5).

### 3.4 Température (rapporté, sans critère)

| Cas | N poutres principales min / max (kN) | DX tête de poteau (mm) |
| --- | --- | --- |
| TP, +46 °C, tout l'aluminium | −2,7 / +7,6 | +5,2 |
| TM, −28 °C, tout l'aluminium | −4,6 / +1,6 | −3,2 |
| TAP, +56 °C, PP, montants, diagonales (S2) | −76,9 / −25,6 | +7,3 |
| TAM, −23 °C, PP, montants, diagonales (S2) | +10,5 / +31,6 | −3,0 |

La retenue entre la rotule côté quai et les profilés supports est faible : sous T+, la
tête des poteaux se déplace de 5,2 mm pour une dilatation libre du tablier de
α·ΔT·L = 6,6 mm ; l'effort normal des poutres principales reste inférieur à 8 kN
(329 kN si le tablier était bridé). En revanche, la température de S2, appliquée aux
seules poutres, montants et diagonales, est bridée par les pannes non chauffées : −77 kN
de compression dans les poutres principales sous TA+ (−46 kN à 0,6 dans le jeu A). C'est
un artefact du modèle AVP (pannes exclues de la température), qui pèse sur le jeu A.
