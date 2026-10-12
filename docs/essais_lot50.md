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
