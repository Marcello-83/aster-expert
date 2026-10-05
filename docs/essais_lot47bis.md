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
