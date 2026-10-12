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

## 4. Livrables (étape 4)

Chaîne générique des lots 49 à 49 ter, jeu B (PRO) : post-traitement accepté (tables
identiques), MED des résultats (246 Mo) et des charges, VTU, CTL-013 sur les charges
réussi, synthèse ingénieur (9 familles, 12 sections, 480 torseurs), équilibre par état
limite réussi (ELU 4,1·10⁻¹¹ sur 1 620 combinaisons…), contrôle croisé par
`resultats lire` réussi (2 900 valeurs), diagrammes N, M, V des 7 familles de barres,
6 fichiers de flexion composée du chevêtre, classeur de 15 feuilles.

Ce que la chaîne générique n'a pas produit sans développement nouveau :

- images ParaView : le script `paraview_resultats.py` porte le manifeste des 3 402
  combinaisons sur une seule ligne de 10 Mo ; le Python de `pvbatch` (image Salomé)
  refuse le fichier (« SyntaxError: Non-UTF-8 code starting with '\xc2' … line 22 »),
  alors que le Python 3.12 du projet le compile ; non livrées ;
- classeur : il lit `torseurs_combinaisons.json` (31 Mo) dans le paquet, au-delà du
  plafond de 20 Mo ; le classeur a été produit en copiant ce fichier dans le paquet le
  temps de la sous-étape, puis il en a été retiré (le paquet versionné ne le porte pas) ;
- jeu A dans la synthèse générique : les états limites du tronc commun regroupent les
  familles de combinaisons, les deux jeux y seraient mêlés ; le jeu A est livré par les
  CSV du projet (ci-dessous), calculés à partir des mêmes cas élémentaires.

Livrables propres au projet (`pontons_alu_01.syntheses`, `paquet/comparaison/`) :
`torseurs_<famille>.csv` (jeux A et B, cinq états limites, min et max de N, VY, VZ, MT,
MFY, MFZ avec le torseur concomitant complet, le lieu, la combinaison et ses cas ;
convention de l'AVP, N > 0 en traction), réactions des rotules côté quai, déplacements
sous l'ELS caractéristique, comparaison à l'AVP, image du modèle filaire.

Nombre de combinaisons : jeu A 136 (ELU 80, ELU acc. 16, ELS car. 40) ; jeu B 3 402
(ELU 1 620, ELU acc. 594, ELS car. 810, ELS fréq. 297, ELS QP 81).

### 4.1 Comparaison à l'AVP (ordres de grandeur, pas une référence)

ELU fondamental, kN et kN·m, min / max :

| Famille | Grandeur | AVP | Jeu A | Jeu B |
| --- | --- | --- | --- | --- |
| Poutres principales | N | −139 / +78 | −206 / +178 | −77 / +127 |
| Poutres principales | My (MFY) | −32 / +20 | −53 / +53 | −39 / +18 |
| Poutres principales | Vz | −28 / +20 | −38 / +39 | −29 / +29 |
| Montants | N | −33 / +38 | −223 / +95 | −456 / +277 |
| Diagonales | N | −53 / +32 | −82 / +51 | −101 / +74 |
| Pannes secondaires | N | −51 / +64 | −105 / +124 | −75 / +35 |
| Poteaux | N | −72 / +14 | −60 / +49 | −52 / +18 |

Les montants du modèle PRO sont gouvernés par le montant 1 (X = 0), bridé entre les deux
rotules côté quai fixes en X, Y et Z (P5) : sous T+ seul, N = −301 kN, soit
E·A·α·ΔT = 297 kN. Ce résultat dépend entièrement de P5 (aucun jeu dans les rotules).

### 4.2 Déplacements, ELS caractéristique

Jeu B : UZ −59,1 / +20,1 mm (pannes, X ≈ 3,1 m), |UY| ≤ 4,1 mm, UX du tablier
−5,4 / +8,3 mm ; tête des profilés supports UX −6,4 / +14,2 mm. Jeu A : UZ −101,8 /
+106,9 mm, gouverné par la houle de S2 (20 kPa vers le haut, 10 kPa vers le bas).
AVP : −29,6 / +7,5 mm, UY 2,7 mm, avec une section des poutres principales environ 12
fois plus raide (P4).

### 4.3 Chevêtre (jeu B)

ELU : N −41 / +69 kN, MFY −9,1 / +12,2 kN·m, MFZ −2,3 / +4,8 kN·m, MT −2,0 / +1,7 kN·m,
VZ −27 / +25 kN ; torseurs concomitants dans `torseurs_chevetre.csv` et, par section
(supports, nus des poteaux, mi-portée), dans les fichiers de flexion composée.

### 4.4 Réactions côté quai (jeu B)

ELU fondamental, par rotule : DX −83 / +91 kN, DY −523 / +488 kN, DZ −17 / +39 kN ;
ELU accidentel : DX −229 / +233 kN, DY −324 / +244 kN. DY est gouverné par la
température bridée entre les deux rotules (P5).

## 5. Données manquantes et points à trancher par MM

Données absentes de l'annexe « Données », signalées, avec l'hypothèse provisoire retenue :

1. **Largeur chargée b** : non donnée. Retenu : tablier limité aux axes des poutres
   principales (b = 1,50 m), largeurs d'influence de P22 (0,100 / 0,285 / 0,370 / 0,370 /
   0,280 / 0,095 m). Toutes les actions de surface (G2, Q, houle) en sont
   proportionnelles.
2. **Aire de cisaillement Avy du MP1200** : non donnée (seul Avz = 17,41 cm²). Retenu :
   AY = AZ = A/Avz = 2,55 (souplesse d'effort tranchant horizontal des poutres
   principales, effet attendu faible).
3. **Nuance d'acier du chevêtre** : non donnée ; l'en-tête des fichiers de flexion
   composée porte « non donné par l'annexe « Données » (à fournir par MM) ».
4. **Gauchissement du MP1200** : JG non donné ; POU_D_T (sans gauchissement) retenu. Les
   assemblages sont soudés à chaque nœud et aucune charge n'est excentrée par rapport au
   centre de torsion ; MT des poutres principales reste inférieur à 0,1 kN·m sous Q
   (coupe § 3.3). Une formulation avec gauchissement (POU_D_TG) n'est pas utile au calcul
   des efforts ; le déversement relève de l'EC9.

Points qui dépendent fortement d'une hypothèse non confirmée :

- **P5, rotules côté quai fixes en X, Y et Z** : sous T+, le montant 1 (X = 0) est bridé
  entre les deux rotules (N = −301 kN, E·A·α·ΔT = 297 kN) et les rotules reçoivent
  ±312 kN selon Y ; aux ELU, N des montants −456 / +277 kN et DY des rotules ±520 kN en
  découlent. Un jeu ou un appui glissant transversal sur l'une des rotules ferait
  disparaître ces efforts.
- **P7, pannes soudées à chaque croisement avec 0,10 m d'excentricité** : les pannes
  secondaires (50 × 5) travaillent en membrure comprimée du tablier (−17 à −26 kN sous Q
  seul, −75 kN à l'ELU B).
- **P17 et P18, profilés supports** : section supposée ; leur encastrement sous le tablier
  donne un moment d'extrémité (R_quai = 23,27 kN contre 23,44 kN isostatique).
- **Jeu A, température de S2 sans les pannes** : −77 kN dans les poutres principales sous
  TA+, artefact du modèle AVP.
- **P23, ELS quasi permanent pour la fissuration**, et ds = di = 0,07 m : par défaut de
  l'outil, à confirmer.
- **P21** : plan moyen +1,3575 recalé à +1,358 (grille de 1 mm, choix A2 de l'agent).
