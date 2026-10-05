# Essais du lot 47 bis — estacade : relecture des écarts, critères v2, variantes ciblées

**Contre-calcul d'un modèle non validé** (comme au lot 47) : aucune ligne n'est un
niveau E, un écart ne désigne pas d'avance le logiciel fautif. Consigne :
`docs/lots/lot47bis_consigne.md`. Décisions de MM : E17 (règles de lecture v2), E18
(cas TR de la combinaison 100), E19 (variante de chevêtre de 0,80 m), recopiées dans
`projets/estacade_pieux_01/donnees/sources/arbitrage_estacade_pieux_01_lot47bis.md` et
dans la fiche (points E17 à E19). La référence (E1 à E16) n'est pas modifiée.

Ce rapport suit `docs/modele_rapport_essai.md`. Les sections 1 à 5 sont écrites et
commitées **avant** toute nouvelle exécution et avant la relecture chiffrée du résultat
du lot 47 ; elles ne sont pas modifiées ensuite (une erreur s'y corrige dans une
section datée « Correction du critère »). Version de Code_Aster : 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

**Statut des critères v2.** Ils sont **écrits après la première exécution** (celle
du lot 47, `data/processed/runs/20261005T101455-e0d5c870`) et après la lecture de ses
résultats par la session et par le superviseur : ils ne sont pas aveugles. Les
critères v1 (`docs/essais_lot47.md` § 2.3 à 2.7) et leurs verdicts
(`projets/estacade_pieux_01/references/comparaison_lot47.json`) restent tels quels ;
le tableau final les met côte à côte.

## 1. Critères de lecture v2 (E17) — points C1 à C13

### 1.1 Conventions (inchangées depuis le lot 47, § 2.3)

- Repère : X le long du tablier depuis l'about, Y transversal depuis l'axe, Z = cote
  NGF ; dalle au plan moyen Z = +1,30 ; files X_i = 0,60 + 5,00 (i − 1), i = 1 … 7 ;
  têtes de pieux aux 14 points (X_i, ±2,00, +1,30).
- Dalle : `EFGE_NOEU` (DKT, x_l = X, normale +Z ; `MXX`, `MYY` > 0 tendent la face
  supérieure, CA-045). M_source ≙ −MXX ; Qxx ≙ `QX` ; Nxx ≙ `NXX`.
- Pieux et chevêtres : `EFGE_ELNO` aux deux extrémités de chaque élément (sans
  moyenne). Pieux : modules √(MFY² + MFZ²), √(VY² + VZ²) ; N_source ≙ −N.
- Chevêtres : repère local x_l = +Y, z_l = +Z ; s = signe tel que s·MFY > 0 en
  travée sous G = PP + G2 au milieu du chevêtre (lot 47, § 2.3).
- Combinaisons de B5 (`projets/estacade_pieux_01/combinaisons.py`), enveloppe sur les
  positions de TS (« axé » pour 102 à 108, « bord de voie » pour 109 à 115). La
  colonne « ELU » est l'enveloppe d'ELU+ (γG = 1,35) et d'ELU− (γG = 1,00) ; **la
  famille qui gouverne (ELU+ ou ELU−) et la position de la charge mobile sont
  rapportées pour chaque valeur** (E17.1, étendu à tous les points ELU).
- **Combinaison 100 (E18)** : TR = 5 kPa sur les deux trottoirs **+** essieu de
  trottoir de E18 (§ 2), enveloppe sur ses 57 positions ; partout où la
  combinaison 100 intervient en v2 (C7, C12 « rive »). Dans LM1 (102 à 115), TR reste
  5 kPa.
- Écart relatif = (Code_Aster − source) / |source| ; tolérances d'E12 inchangées.

### 1.2 Disques d'exclusion des têtes de pieux (E17.3)

Un nœud de la dalle est **exclu** s'il est à une distance horizontale
√((X − X_i)² + (Y ∓ 2,00)²) ≤ 0,60 m (+1e-9) d'une des 14 têtes. Au maillage de
production (0,05 m), c'est le disque fermé : le nœud à 0,60 m exactement est exclu.

### 1.3 Bande de dalle des chevêtres (E17.2)

Pour une ligne de résultat du chevêtre de la file i (extrémité d'élément au nœud
(X_i, Y, +1,30)), la bande est l'ensemble des nœuds de la dalle de même Y et de
|X − X_i| ≤ 0,60 (25 nœuds au maillage de 0,05 m). Intégrales par la règle des
trapèzes sur ces nœuds (`EFGE_NOEU`, valeur nodale) :

- moment total (positif en travée) : M_T = s·MFY − ∫ MYY dX ;
- effort tranchant total : V_T = VZ + ∫ QY dX.

La barre seule (s·MFY, VZ) est rapportée pour information, sans verdict.

### 1.4 Tableau des lectures v2 (lieu, composante, famille)

| N° | Lieu exact | Composante | Combinaison et famille | Source comparée | Tol. | Changement par rapport à v1 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | tous les nœuds du modèle | max √(DX² + DY² + DZ²) | 107 ELS c, enveloppe TS bord | 0,5 cm (arrondi : compatible si 0,25 ≤ u < 0,75 cm) | arrondi | aucun |
| C2 | extrémité haute de l'élément de tête de chaque pieu (Z = +1,30), 14 pieux | max(−N) | 112 : ELS f, ELS c, ELU (ELU+ ∪ ELU−, famille rapportée) | 514 / 727 / 1 048 kN | 3 % | famille rapportée |
| C3 | pieux, extrémités des éléments dont les deux nœuds sont dans −0,80 ≤ Z ≤ +1,30 (élément de tête +1,30 → +1,00 compris), 14 pieux | max √(MFY² + MFZ²) | 111 : ELS f, ELS c, ELU (ELU+ ∪ ELU−, famille rapportée) | 209 / 312 / 449 kN·m (max(|max|, |min|) publié) | 5 % | **zone** : de la tête à −0,80 (v1 : −0,80 à +0,70) |
| C4 | pieux, éléments dont le milieu est dans −0,80 ≤ Z ≤ +0,70 (bouchon, E14) | max √(VY² + VZ²) | 114 ELU (famille rapportée) ; ELS f et ELS c en information | 253 kN | 5 % | aucun (E17 ne le vise pas) ; ELS en information |
| C5 | pieux, toutes les extrémités d'élément de +1,30 à −13,00 | max √(MFY² + MFZ²) | 111 ELU (famille rapportée) ; ELS f et ELS c en information | 463 kN·m | 5 % | **zone** : tout le pieu (v1 : Z < −0,80) |
| C6 | chevêtres, extrémités d'élément de |Y| < 2,00 | max M_T (§ 1.3) | 105 ELS f, 105 ELS c, 112 ELU (famille rapportée) | 180 / 276 / 408 kN·m | 5 % | **total** barre + bande de dalle ; barre seule en information |
| C7 | chevêtres, extrémités d'élément aux nœuds Y = ±2,00 (des deux côtés) | min M_T, comparé en module | enveloppe des ELU 100 à 115 (100 avec E18 ; combinaison et famille rapportées) ; ELS f et ELS c (même enveloppe) en information | 177 kN·m | 5 % | **total** ; barre seule en information |
| C8 | chevêtres, toutes les extrémités d'élément | max |V_T| | enveloppe de 105 et 112 ELU (famille rapportée) ; ELS f et ELS c en information | 653 kN (publié 620 / −653) | 5 % | **total** ; barre seule en information ; lecture complémentaire sans verdict hors des lignes Y = ±2,00 |
| C9 | dalle, |X − X_i| ≤ 0,60 pour une file i, **hors disques** (§ 1.2) | max MXX (face supérieure tendue) | 111 ELS f, ELS c, ELU (famille rapportée) | 79 / 118 / 174 kN·m/m | 10 % | **disques exclus** |
| C10 | dalle, |X − X_i| > 0,60 pour toute file | max(−MXX) | 112 ELS f, ELS c, ELU (famille rapportée) | 82 / 134 / 198 kN·m/m | 10 % | aucun (zone déjà hors disques) |
| C11 | dalle, chaque ligne de nœuds X = constante (les 625 abscisses du maillage) : N̄(X) = (1 / 6,00) ∫ NXX dY de Y = −3,00 à +3,00, trapèzes | max sur X de |N̄(X)| ; X rapporté | FR seul ; TE− seul | 18,9 / 64,1 kN/m | 10 % | **moyenne de section** (v1 : maximum nodal) |
| C12 courant | dalle, |Y| ≤ 1,50, **hors disques** | max |QX| | 111 ELU (famille rapportée) | 320 kN/m | 10 % | disques exclus |
| C12 rive | dalle, |Y| > 1,50, **hors disques** | max |QX| ; position de l'essieu rapportée | 100 ELU, TR d'E18 (enveloppe sur les 57 positions ; famille rapportée) | 568 kN/m | 10 % | disques exclus **et** cas TR d'E18 ; en information : TR = 5 kPa seul, et lecture dans les disques |
| C13 | dalle entière, **hors disques** | max(−MXX) « inf. », min(−MXX) « sup. », max |QX| « V » | non pondéré : LM1 = UDL + TR (5 kPa) + TS (toutes positions axé et bord) ; LM2 (toutes positions) | LM1 85 / −47 / 154 ; LM2 64 / −30 / 138 | 10 % | disques exclus |

Lecture de C12 « rive » : la source a appliqué l'essieu en charges ponctuelles (E18) ;
sa valeur dépend de son maillage, l'écart s'interprète en conséquence (aucun ajustement).

### 1.5 Contrôle de la lecture du total (avant toute conclusion sur C6 à C8)

La somme barre + dalle n'a de sens que si les signes de `VZ` et `QY`, de `MFY` et
`MYY` sont cohérents. Contrôle par un corps libre dont la charge est connue : sous PP
seul, la partie du tablier Y < Y0 (Y0 = −2,50 et −2,25 : consoles, aucun pieu) ne
porte que son poids W(Y0) = (γ_b e L + 7 γ_b b h)(Y0 + 3,00) = (25 × 0,40 × 31,20 +
7 × 25 × 1,20 × 0,90)(Y0 + 3,00) kN (chevêtre compté en entier, E2). Sur la coupe
Y = Y0 (sept chevêtres, moyenne des deux extrémités d'élément au nœud ; dalle de
X = 0 à 31,20, trapèzes) :

- Σ VZ + ∫ QY dX = ±W(Y0) (le signe est relevé, non imposé) ;
- Σ s·MFY − ∫ MYY dX = −W(Y0)·(Y0 + 3,00)/2 (moment de console, négatif en travée).

Critère : écart relatif ≤ 2 % pour chaque grandeur et chaque Y0 (champs nodaux
extrapolés, bords libres X = 0 et 31,20). Le terme de bord [MXY] aux deux abouts est
rapporté à part, sans entrer dans le critère. Un échec interdit de conclure sur le
total de C6 à C8 ; il est rapporté tel quel.

## 2. Exécution E18 — essieu de trottoir de la combinaison 100

### 2.1 Modèle

Même maillage vérifié, même modèle, même solveur que la production du lot 47
(`POSTTRAITEMENTS="FORCE"`) ; seules les charges changent. Cas « TRE_k » : deux
empreintes de 0,40 × 0,40 m en pression uniforme au plan moyen (80 kN chacune,
500 kPa), centrées en Y = +2,25 et en X = x_k ± 1,00, x_k = 15,60 + 0,50 k,
k = −28 … 28 (57 positions ; toutes les empreintes sur la dalle ; bords alignés sur
les mailles de 0,05 m). Groupes d'empreinte : bandes `CREA_GROUP_MA/BANDE`
(`CRIT_NOEUD="TOUS"`, PAT-003) intersectées avec le groupe `TROTT`. Le cas TR d'E18
de la position k est TR (5 kPa, résultat de production) + TRE_k (superposition
linéaire, E5). Le côté Y < 0 est l'image miroir (structure et charges permanentes
symétriques en Y) : non calculé.

### 2.2 Critère (contrôles D de l'exécution)

- Σ DZ des réactions des pointes = 160 000 N pour chacune des 57 positions, à 1e-6
  en relatif (table `RPIEDS_<lot>`) ;
- exécution `OK` sans alarme non expliquée.

Grandeur rapportée : C12 « rive » (§ 1.4) et la position gouvernante, comparée à celle
de la figure 100 (première charge juste avant le chevêtre 4, X_4 = 15,60 : l'essieu
gouvernant devrait avoir une roue à X légèrement inférieur à 15,60 et l'autre ≈ 2 m
plus loin). Aucune autre lecture n'est jugée sur cette exécution.

## 3. Exécution E19 — variante de chevêtre de 0,80 m

### 3.1 Modèle

Tout le modèle de production (E1 à E16, plus les cas TRE_k d'E18) sauf la hauteur du
chevêtre : `HZ = 0,80` au lieu de 0,90 (E19 : « le reste inchangé »). Le poids propre
du chevêtre suit la section (PESANTEUR) : c'est une conséquence de E19, rapportée.
Une seule exécution.

### 3.2 Critère

Contrôles D de l'exécution, à 1e-6 en relatif :

- Σ DZ des pointes = charge des roues pour les 242 positions de TS et LM2 et les 57
  positions TRE ;
- PP : Σ DZ des pointes = 3 553 297,604 − 7 × 6,00 × 1,20 × 0,10 × 25 000 =
  **3 427 297,604 N**.

Grandeurs rapportées, **sans verdict** (variante de sensibilité, la référence reste à
0,90 m) : C6, C7, C8 lus selon § 1.4 (total et barre seule), écart à la source et
écart à la référence. La piste (c) est **confirmée** si la variante ramène C6 (total
et barre) dans la tolérance de 5 % sans faire sortir C7 et C8 de la leur ; **réfutée**
si C6 ne s'en rapproche pas ; **partielle** sinon. Ce classement est écrit ici, avant
l'exécution.

## 4. Harnais D v2 — cas autoéquilibrés (TE+, TE−)

### 4.1 Lacune de v1

CTL-005 et CTL-013 rapportent l'écart à la plus grande composante de la charge
appliquée : pour TE+ et TE− elle est nulle, l'écart relatif vaut NaN et le verdict est
un échec formel (lot 47, § 3.3), qui a privé le paquet du niveau D. Ce verdict v1 est
conservé tel quel (`projets/estacade_pieux_01/references/controles_d_v1_lot47.json`).

### 4.2 Version 2 des contrôles

Un cas déclaré **autoéquilibré** dans `projet.yaml` (charge appliquée nulle par
construction) porte une **échelle déclarée** S, fournie par une extension du projet,
qui remplace l'échelle nulle ; un cas autoéquilibré dont la charge appliquée n'est pas
nulle est refusé. Pour l'estacade :

S = max sur c ∈ {DX, DY} de Σ |k·u_c| sur tous les nœuds de ressort (k des données,
u_c lu dans la table `DR_<cas>` du listing),

c'est-à-dire la somme des modules des forces que la sommation d'équilibre additionne :
l'échelle naturelle de l'erreur d'arrondi de cette somme. Critères v2 :

- CTL-005 : |bilan_c| / S ≤ 1e-6 pour c ∈ {DX, DY, DZ} ;
- CTL-013 : |charge évaluée − charge déclarée| / S ≤ 1e-6.

Les autres cas gardent l'échelle de v1 (aucun changement de verdict possible pour eux).
Niveau D réévalué sur l'exécution de production du lot 47, **sans nouvelle exécution**
(`aster-expert projet estacade_pieux_01 controles`).

## 5. Relecture sans calcul (production du lot 47)

Toutes les lectures du § 1 sur l'exécution `20261005T101455-e0d5c870` (MED de
résultats), à l'exception de la combinaison 100 avec E18 qui demande l'exécution du
§ 2. Les diagnostics (a), (b), (c) et (e) du superviseur sont vérifiés chiffres à
l'appui, chacun confirmé ou réfuté :

- (a) lieu et famille des lectures v1 de C3 et C5 ; valeur au nœud de tête +1,30 de
  F7_YP en 111 ELU+ (annoncée 435,5 kN·m) ; variation du moment sur l'élément
  +1,30 → +1,00 → +0,70 et effort tranchant correspondant ;
- (b) à Y = ±1,90 en 112 ELU+ : VZ du chevêtre (annoncé ≈ 190 kN), ∫QY de la bande
  (≈ 476 kN), total (≈ 666 kN) ; sur appui : MFY (≈ −125 à −133 kN·m), part de la
  dalle (≈ −42 kN·m), total (≈ −170 kN·m) ;
- (c) par l'exécution E19 (§ 3) ;
- (e) par l'exécution E18 (§ 2).

## 6. Sonde S2 — partage de l'effort entre dalle DKT et poutre POU_D_T coplanaires

Ajoutée pendant le lot, **avant son exécution**, pour donner au constat demandé par la
consigne (§ 3.6) une preuve rejouable : les valeurs de la production ne sont pas
imprimées dans un listing versionné. Script :
`projets/estacade_pieux_01/scripts/sonde_lot47bis.py` ; valeurs attendues calculées
avant l'exécution : `projets/estacade_pieux_01/references/sonde_lot47bis_attendus.json`.

### 6.1 Modèle

Bande de dalle de chevêtre isolée : dalle DKT X ∈ [−0,60 ; 0,60] × Y ∈ [−3,00 ; 3,00],
e = 0,40 m, QUAD4 de 0,05 m ; poutre POU_D_T 1,20 × 0,90 m le long de X = 0, nœuds
partagés, mêmes matériau (E = 34 GPa, ν = 0,2), section et orientation que
l'estacade ; deux appuis ponctuels sur les nœuds de la poutre en Y = ±2,00 (têtes de
pieux), isostatiques (P1 : DX, DY, DZ, DRY ; P2 : DX, DZ) ; pression uniforme
q = 10 kPa sur la dalle. La section en T est isostatique : W = 72 000 N, 36 000 N par
appui, effort tranchant total |V| = 22 800 N à Y = −1,90, moment total −6 000 N·m à
Y = −2,00 et +18 000 N·m (travée) à Y = 0.

### 6.2 Critère

- Σ DZ des réactions des deux appuis = 72 000 N, à 1e-6 en relatif ;
- total de la section (même lecture que § 1.3, bande = toute la largeur ; barre :
  moyenne des deux extrémités d'élément au nœud de la ligne) : |VZ + ∫QY dX| à
  Y = −1,90, s·MFY − ∫MYY dX à Y = −2,00 et à Y = 0, chacun à 2 % de la statique ; le
  terme de bord [MXY] est rapporté à part.

Grandeur établie (rapportée, sans seuil) : la part de la barre seule dans le total, à
Y = −1,90, −2,00 et 0. Un échec du critère est rapporté tel quel et interdit de
fonder le constat sur cette sonde.

## 7. Résultats (rédigés après les exécutions et la relecture ; les sections 1 à 6 ne sont pas modifiées)

Exécutions du lot (toutes `OK`, sans alarme sauf S2) :

| Exécution | Répertoire | Durée | Critère | Résultat |
| --- | --- | --- | --- | --- |
| E18, essieu de trottoir (57 positions), niveau B 95/95 | `data/processed/runs/20261005T150307-187df570` | 332,6 s | § 2.2 : Σ DZ des pointes = 160 kN | 57/57, écart maximal 5,9e-10 : **réussi** |
| E19, chevêtre de 0,80 m (+ positions d'E18), niveau B 501/501 | `data/processed/runs/20261005T150840-65219726` | 1 770,1 s | § 3.2 : Σ DZ des pointes, 299 positions ; PP | 299/299 à 6,2e-10 ; PP = 3 427 297,604 N à 2,0e-11 : **réussi** |
| Sonde S2, niveau B 24/24 | `data/processed/runs/20261005T150756-c0428813` | 7,8 s | § 6.2 | **réussi** (§ 7.4) |

Deux appels de `aster-expert run` sur le `.export` ont d'abord été refusés par la politique
des chemins (lot 46 : `.comm` attendu), avant toute exécution. S2 émet quatre
`<A> <POSTRELE_70>` : diagnostic **DIAG-012** consulté avant toute hypothèse ; l'alarme
signale que `EFGE_NOEU` est relu dans le repère local des éléments, qui est ici le repère
global (dalle seule, `ANGL_REP = (0, 0)`, normale +Z, aucune `UTILITAI_4`) : aucune lecture
n'en dépend.

Relecture : `projets/estacade_pieux_01/scripts/comparer_lot47bis.py` (module
`comparaison_v2.py`), production du lot 47 + E18 →
`projets/estacade_pieux_01/references/comparaison_v2_lot47bis.json` ; variante E19 →
`references/variante_chevetre_0p80_lot47bis.json`.

### 7.1 Contrôle de la lecture du total (§ 1.5) — réussi

| Coupe | W (kN) | Σ VZ (kN) | ∫ QY (kN) | Total (kN) | Écart | Moment total (kN·m) | Attendu | Écart |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Y0 = −2,50 | 250,5 | 77,4 | 173,3 | 250,7 | +0,07 % | −62,625 | −62,625 | 3,8e-10 |
| Y0 = −2,25 | 375,75 | 116,9 | 259,1 | 375,95 | +0,05 % | −140,906 | −140,906 | 2,9e-10 |

`VZ` et `∫QY` s'ajoutent avec le même signe ; le total redonne la statique. Terme de bord
[MXY] aux abouts : 0,38 et 0,42 kN (rapporté, hors critère). La lecture du total de C6 à
C8 est donc fondée.

### 7.2 Tableau C1 à C13 : verdicts v1 et v2 côte à côte

v1 : `docs/essais_lot47.md` § 3.4 (conservé). v2 : règles du § 1.4. Valeurs Code_Aster ;
écart ; verdict. Unités : kN, kN·m, kN·m/m, kN/m, cm.

| Point | Colonne | Source | v1 | v2 | Règle v2 appliquée ; lieu ; famille, position |
| --- | --- | --- | --- | --- | --- |
| C1 | ELS c (107) | 0,5 | 0,4375 ; −12,5 % ; compatible avec l'arrondi | 0,4375 ; −12,5 % ; **compatible avec l'arrondi** | max √(DX²+DY²+DZ²), tous les nœuds (inchangé) ; X = 31,20, Y = 3,00 ; ELS c, TSA_M26 |
| C2 | ELS f (112) | 514 | 526,9 ; +2,5 % ; dans la tolérance | 526,9 ; +2,5 % ; **dans la tolérance** | max(−N) en tête (inchangé) ; F2_YP ; ELS f, TSB_M20 |
| C2 | ELS c (112) | 727 | 714 ; −1,8 % ; dans la tolérance | 714 ; −1,8 % ; **dans la tolérance** | idem ; ELS c, TSB_M20 |
| C2 | ELU (112) | 1 048 | 1 023 ; −2,4 % ; dans la tolérance | 1 023 ; −2,4 % ; **dans la tolérance** | idem ; ELU+, TSB_M20 |
| C3 | ELS f (111) | 209 | 131 ; −37,3 % ; hors tolérance | 202,4 ; −3,2 % ; **dans la tolérance** | max √(MFY²+MFZ²), +1,30 à −0,80 (E17.1) ; F7_YP, Z = +1,30 ; ELS f, TSB_P25 |
| C3 | ELS c (111) | 312 | 192 ; −38,4 % ; hors tolérance | 294,3 ; −5,7 % ; **hors tolérance** | idem ; F7_YP, Z = +1,30 ; ELS c, TSB_P25 |
| C3 | ELU (111) | 449 | 283,4 ; −36,9 % ; hors tolérance | 435,5 ; −3,0 % ; **dans la tolérance** | idem ; F7_YP, Z = +1,30 ; ELU+, TSB_P25 |
| C4 | ELU (114) | 253 | 259,4 ; +2,5 % ; dans la tolérance | 259,4 ; +2,5 % ; **dans la tolérance** | bouchon (inchangé) ; F7_YP, Z = +0,70 ; ELU+, TSB_P25 |
| C5 | ELU (111) | 463 | 105,2 ; −77,3 % ; hors tolérance | 435,5 ; −5,9 % ; **hors tolérance** | tout le pieu (E17.1) ; F7_YP, Z = +1,30 ; ELU+, TSB_P25 |
| C6 | ELS f (105) | 180 | 202,8 ; +12,7 % ; hors tolérance | 215,0 ; +19,5 % ; **hors tolérance** | total M_T, |Y| < 2,00 (E17.2) ; file 2, Y = 0 ; ELS f, TSA_M20 |
| C6 | ELS c (105) | 276 | 303,2 ; +9,9 % ; hors tolérance | 323,1 ; +17,1 % ; **hors tolérance** | idem ; file 2, Y = 0 ; ELS c, TSA_M20 |
| C6 | ELU (112) | 408 | 443,1 ; +8,6 % ; hors tolérance | 473,2 ; +16,0 % ; **hors tolérance** | idem ; file 2, Y = −0,20 ; ELU+, TSB_M20 |
| C7 | ELU (enveloppe 100–115) | 177 | 141,9 ; −19,8 % ; hors tolérance | 177,7 ; +0,4 % ; **dans la tolérance** | min M_T aux nœuds Y = ±2,00 (E17.2) ; file 2, Y = −2,00 ; comb. 111, ELU+, TSB_M20 |
| C8 | ELU (105, 112) | 653 | 198,1 ; −69,7 % ; hors tolérance | 722,5 ; +10,6 % ; **hors tolérance** | max |VZ + ∫QY dX| (E17.2) ; file 2, Y = +1,95 ; comb. 112, ELU+, TSB_M20 |
| C9 | ELS f (111) | 79 | 111,4 ; +41,0 % ; hors tolérance | 70,66 ; −10,6 % ; **hors tolérance** | max MXX, chapeau hors disques (E17.3) ; X = 30,55, Y = 1,40 ; ELS f, TSB_P27 |
| C9 | ELS c (111) | 118 | 150,4 ; +27,5 % ; hors tolérance | 105,4 ; −10,7 % ; **hors tolérance** | idem ; ELS c, TSB_P27 |
| C9 | ELU (111) | 174 | 214,1 ; +23,0 % ; hors tolérance | 156,2 ; −10,3 % ; **hors tolérance** | idem ; ELU+, TSB_P27 |
| C10 | ELS f (112) | 82 | 81,92 ; −0,1 % ; dans la tolérance | 81,92 ; −0,1 % ; **dans la tolérance** | travée (inchangé) ; X = 2,55, Y = 1,30 ; ELS f, TSB_M25 |
| C10 | ELS c (112) | 134 | 130,8 ; −2,4 % ; dans la tolérance | 130,8 ; −2,4 % ; **dans la tolérance** | idem ; ELS c |
| C10 | ELU (112) | 198 | 192,9 ; −2,6 % ; dans la tolérance | 192,9 ; −2,6 % ; **dans la tolérance** | idem ; ELU+ |
| C11 | FR seul | 18,9 | 58,76 ; +210,9 % ; hors tolérance | 19,70 ; +4,2 % ; **dans la tolérance** | moyenne de section (E17.4) ; X = 30,55 |
| C11 | TE− seul | 64,1 | 149,2 ; +132,8 % ; hors tolérance | 62,88 ; −1,9 % ; **dans la tolérance** | idem ; X = 15,60 |
| C12 | ELU courant (111) | 320 | 351,4 ; +9,8 % ; dans la tolérance | 351,4 ; +9,8 % ; **dans la tolérance** | max |QX|, voie hors disques (E17.3) ; X = 30,50, Y = 1,30 ; ELU+, TSB_P28 |
| C12 | ELU rive (100) | 568 | 990,3 ; +74,4 % ; hors tolérance | 222,1 ; −60,9 % ; **hors tolérance** | max |QX|, trottoirs hors disques, TR d'E18 ; X = 5,55, Y = 2,90 ; ELU+, TRE_M24 |
| C13 | LM1 Mxx inf. | 85 | 83,61 ; −1,6 % ; dans la tolérance | 83,61 ; −1,6 % ; **dans la tolérance** | hors disques (E17.3) ; X = 3,05, Y = 1,30 ; TSB_M24 |
| C13 | LM1 Mxx sup. | −47 | −80,03 ; −70,3 % ; hors tolérance | −54,60 ; −16,2 % ; **hors tolérance** | idem ; X = 5,55, Y = 1,40 ; TSB_M24 |
| C13 | LM1 V | 154 | 738,6 ; +379,6 % ; hors tolérance | 205,0 ; +33,1 % ; **hors tolérance** | idem ; X = 25,70, Y = 1,30 ; TSB_P22 |
| C13 | LM2 Mxx inf. | 64 | 64,38 ; +0,6 % ; dans la tolérance | 64,38 ; +0,6 % ; **dans la tolérance** | idem ; X = 3,05, Y = 1,15 ; L2B_M25 |
| C13 | LM2 Mxx sup. | −30 | −33,74 ; −12,5 % ; hors tolérance | −26,20 ; +12,7 % ; **hors tolérance** | idem ; X = 5,55, Y = 1,00 ; L2B_M24 |
| C13 | LM2 V | 138 | 335,6 ; +143,2 % ; hors tolérance | 134,8 ; −2,3 % ; **dans la tolérance** | idem ; X = 0,70, Y = 1,20 ; L2B_M29 |

Bilan : **v2, 17 lignes sur 30** dans la tolérance (ou compatibles avec l'arrondi) ;
v1, 11 sur 30. Les lectures « information » (barre seule, ELS de C4, C5, C7, C8, C12 dans
les disques ou avec TR = 5 kPa seul) sont dans le JSON, sans verdict.

Lecture des 13 lignes hors tolérance v2 (faits, puis déductions marquées) :

- **C3 ELS c (−5,7 %) et C5 (−5,9 %)** : à la limite de 5 %. Le maximum de tout le pieu
  est en tête (Z = +1,30) : C5 v2 égale C3 v2 ELU. Déduction : la source, qui publie 463
  pour C5 et 449 pour C3 sous la même combinaison, ne lit pas les deux au même lieu ; le
  lieu de C5 dans la source reste inconnu.
- **C6 (+16 à +19,5 %)** : le total est plus éloigné de la source que la barre seule
  (+8,6 à +12,7 %). Testé par E19 (§ 9).
- **C8 (+10,6 %)** : le total dépasse la source ; à Y = ±1,90, +7,2 % (§ 8 (b)).
- **C9 (−10,3 à −10,7 %)** : juste au-delà de 10 %, lu à X = 30,55, Y = 1,40, au bord du
  disque de la tête F7_YP. Déduction : la valeur hors disque dépend encore du rayon choisi
  (gradient fort près de la tête).
- **C12 rive (−60,9 %)** : § 8 (e).
- **C13 LM1 sup. (−16,2 %), LM1 V (+33,1 %), LM2 sup. (+12,7 %)** : LM1 sup. est lu à
  X = 5,55, Y = 1,40, juste hors du disque de la tête F2_YP (même dépendance au rayon que
  C9) ; LM2 sup. à X = 5,55, Y = 1,00, à 1,00 m de la tête, sous la roue intérieure de LM2
  bord de voie : non expliqué ; LM1 V est lu à X = 25,70, Y = 1,30, à 0,10 m du bord d'une
  empreinte de roue de TS bord de voie (TSB_P22, empreinte X = 25,80 à 26,20), où QX varie
  vite : grandeur locale sensible au maillage (suite de convergence du lot 47 : max |QX|
  non convergé). Non expliqué au-delà.

### 7.3 Contributions par famille et ELS des barres

Pour chaque valeur ELU, la famille qui gouverne est ELU+ (γG = 1,35) ; aucune lecture v2
n'est gouvernée par ELU−. ELS en information (sans source) : C4 114 ELS f / ELS c = 121,3 /
174,2 kN ; C5 111 = 202,4 / 294,3 kN·m ; C7 total ELS f / ELS c = 99,7 / 125,8 kN·m ; C8
total = 349,4 / 500,5 kN.

### 7.4 Sonde S2 (§ 6) — réussie

`projets/estacade_pieux_01/references/sonde_lot47bis_resultats.json`, listing versionné
`references/cas/sonde_lot47bis_listing_extrait.txt`. Σ DZ = 71 999,99999946 N
(−7,5e-12).

| Ligne | Grandeur | Barre seule | Dalle | Total | Statique | Écart du total | Part de la barre |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Y = −1,90 | effort tranchant (N) | 6 452,5 | 16 323,0 | 22 775,5 | 22 800 | −0,11 % | **28 %** |
| Y = −2,00 | moment sur appui (N·m) | −4 733,8 | −1 266,2 | −6 000,0 | −6 000 | 2,5e-11 | 79 % |
| Y = 0 | moment en travée (N·m) | 16 594,9 | 1 405,1 | 18 000,0 | 18 000 | −3,2e-11 | 92 % |

Fait établi (CA-058) : la barre seule n'est pas l'effort de la section en T ; près de
l'appui ponctuel, la dalle DKT porte 72 % de l'effort tranchant.

## 8. Diagnostics du superviseur : vérification

**(a) C3, C5, lieu de lecture — confirmé, sauf la famille de C3.**
- Lieux v1 : C3 lu à Z = +0,70 (F7_YP, ELU 111), C5 à Z = −2,50 (F7_YP) : **confirmé**.
- Famille : C3 v1 est gouverné par **ELU+** (283,4 kN·m ; ELU− 272,4) et non ELU− ;
  C5 v1 par **ELU−** (105,2 ; ELU+ 104,2) : confirmé pour C5 seulement.
- Au nœud de tête F7_YP, 111 ELU+ (TSB_P25) : **435,49 kN·m**, −3,0 % de 449 et −5,9 % de
  463 : **confirmé** au chiffre près.
- Profil : M = 435,5 (Z = +1,30) → 356,8 (+1,00) → 283,4 (+0,70) kN·m sous V = 262,5 puis
  244,7 kN : 152,1 kN·m perdus sur 0,60 m : **confirmé** (« environ 150 kN·m sous environ
  260 kN »). Le nœud intermédiaire +1,00 (ressort) existe : l'élément de tête est
  +1,30 → +1,00.

**(b) C7, C8, partage dalle/chevêtre — confirmé pour le partage et pour C7 ; le total de
C8 ne rejoint pas la source.**
- Mécanisme : établi indépendamment par S2 (§ 7.4) ; sur l'estacade à Y = +1,90, 112
  ELU+ (TSB_M20, file 2) : VZ = 198,1 kN, ∫QY = 501,9 kN, total **699,9 kN**, part de la
  dalle **72 %** (annoncé ≈ 190 / 476 / 666 kN, ≈ 70 %). Le partage est confirmé ; le total
  est à **+7,2 %** de 653 (annoncé +2 %), et le maximum v2 de C8 (Y = +1,95) à +10,6 % :
  **hors tolérance**, le chiffre du superviseur n'est pas retrouvé.
- Sur appui (Y = −2,00, 112 ELU+, TSB_M20, file 2) : MFY = −132,7 kN·m, dalle −41,6, total
  **−174,3 kN·m** (annoncé −125 à −133, −42, −170) : **confirmé** ; C7 v2 = 177,7 (+0,4 %).

**(c) C6 et chevêtre de 0,80 m — partiellement confirmé** (classement du § 3.2), § 9.

**(e) Essieu de trottoir de la combinaison 100 — confirmé comme cause principale de
l'écart de v1 sur la charge, mais l'écart reste.**
- TR = 5 kPa seul, hors disques : 100,4 kN/m ; avec l'essieu d'E18 : **222,1 kN/m**
  (×2,2), −60,9 % de 568. Dans les disques : 1 431 kN/m (singulier, sans sens).
- Position gouvernante : TRE_M24, roues à X = 2,60 et 4,60, Y = 2,25 ; extremum à
  X = 5,55, Y = 2,90, au bord du chevêtre 2 (X = 5,60). Comme sur la figure 100, la
  première roue est **juste avant un chevêtre** ; mais le chevêtre est le **2** (et son
  symétrique 6), non le 4. Déduction : sous une empreinte de 0,40 m, l'effet de l'essieu
  sur QX hors des disques est loin des 568 kN/m d'une charge ponctuelle, dont l'effort
  tranchant est singulier (E18 l'annonçait) ; l'écart restant n'est pas expliqué par les
  données disponibles.

## 9. Variante E19 — chevêtre de 0,80 m (sans verdict)

| Point | Lecture | Référence 0,90 m | E19 0,80 m | Source | Écart E19 |
| --- | --- | --- | --- | --- | --- |
| C6 ELS f (105) | total | 215,0 | 194,1 | 180 | +7,8 % |
| C6 ELS c (105) | total | 323,1 | 292,2 | 276 | +5,9 % |
| C6 ELU (112) | total | 473,2 | 429,3 | 408 | +5,2 % |
| C6 ELS f / ELS c / ELU | barre seule | 202,8 / 303,2 / 443,1 | 177,1 / 265,1 / 388,6 | 180 / 276 / 408 | −1,6 / −3,9 / −4,8 % |
| C7 ELU (100–115) | total | 177,7 | 186,0 | 177 | +5,1 % |
| C7 ELU | barre seule | 141,9 | 146,7 | 177 | −17,1 % |
| C8 ELU (105, 112) | total | 722,5 | 700,9 | 653 | +7,3 % |
| C8 ELU | barre seule | 198,1 | 172,6 | 653 | −73,6 % |

Classement écrit avant (§ 3.2) : C6 total ne rentre pas dans 5 % (+5,2 à +7,8 %), C7 en
sort (+5,1 %) : **piste (c) partielle**. Faits : le chevêtre de 0,80 m rapproche C6 de la
source d'environ 10 points (total) et ramène la barre seule dans 5 % ; il réduit aussi
C8 (+7,3 %). Déduction : une hauteur de chevêtre de 0,80 m dans le modèle source est
compatible avec C6 « barre seule », non démontrée ; la grandeur publiée (barre ou section
en T) reste inconnue.

## 10. Harnais D v2 et niveau

`aster-expert projet estacade_pieux_01 controles` relancé sur l'exécution de production du
lot 47, sans nouvelle exécution. Échelle déclarée de TE± : S = max(Σ |k·u_X|, Σ |k·u_Y|)
= max(9,804316e5 ; 1,922542e5) = **9,804316e5 N**.

| Contrôle | v1 (lot 47) | v2 (lot 47 bis) |
| --- | --- | --- |
| CTL-005, TEP et TEM | NaN, échec formel | bilan max 2,37e-5 N (DZ) → 2,4e-11 : **réussi** |
| CTL-013, TEP et TEM | NaN, échec formel | 0 / S = 0 : **réussi** |
| CTL-005 autres cas, CTL-006, pesanteur | réussi | identiques (≤ 1,7e-10 ; symétrie ≤ 5,7e-10) |
| Verdict d'ensemble | ÉCHEC | **RÉUSSI** |

Verdict v1 conservé : `projets/estacade_pieux_01/references/controles_d_v1_lot47.json`,
`equilibre_v1_lot47.json`. Paquet de résultats (`aster-expert projet exporter-resultats`) :
**niveau D atteint** (B 420/420, C, D), E non atteint ; le paquet signale que le critère
v2 (`docs/essais_lot47bis.md`) est « commité après l'exécution : antériorité non
démontrable » — c'est exact : l'échelle a été définie après avoir vu l'échec v1.

## 11. Limites

- **Contre-calcul d'un modèle non validé**, jamais un niveau E ; les règles v2 sont écrites
  après la première exécution et après les lectures du superviseur : elles ne sont pas
  aveugles.
- C9 et C13 « sup. » sont lus au bord des disques de 0,60 m : leur valeur dépend du rayon,
  décision de lecture d'E17, non d'une convergence.
- C12 « rive » : l'effet de l'essieu est calculé sous une empreinte de 0,40 m, la source
  en charges ponctuelles ; aucune lecture ne peut les rapprocher. Le côté Y < 0 n'est pas
  calculé (symétrie).
- C8 : le total n'atteint pas le +2 % annoncé ; la grandeur publiée par la source reste
  inconnue.
- La sonde S2 établit le partage pour une bande isolée de 1,20 m, au maillage de 0,05 m ;
  les parts dépendent du maillage (lot 47), le total non.
- Incident d'outil : `search_connaissances` du serveur MCP attaché à la session échouait
  pendant tout le lot (un serveur neuf répond : `mcp-check` OK). Consultations faites par
  `search_constats` et par l'appel direct du même outil sur un serveur neuf (DIAG-012).
  **Redémarrer la session avant le lot suivant.**
