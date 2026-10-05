# Essais du lot 47 — contre-calcul d'une estacade sur pieux (`estacade_pieux_01`)

**Contre-calcul d'un modèle non validé.** Le modèle source (Robot, avant-projet)
n'est pas validé : sa comparaison n'est jamais un niveau E. Un écart ne désigne
pas d'avance le logiciel fautif.

Ce rapport suit `docs/modele_rapport_essai.md`. Chaque section « Critère » est
écrite et commitée **avant** l'exécution qu'elle juge ; elle n'est pas modifiée
ensuite (une erreur s'y corrige dans une section datée « Correction du critère »).
Version de Code_Aster : 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

## 1. Sonde S1 — commandes que la base ne couvre pas

### 1.1 Objet

La base de connaissances ne dit rien de la température sur des coques ni de
`MACRO_ELAS_MULT` (consultation du 2026-10-05 : `search_connaissances` « température
dilatation AFFE_VARC » et `command=MACRO_ELAS_MULT`, aucun résultat). La sonde
`projets/estacade_pieux_01/references/cas/sonde_lot47.comm` (générée par
`projets/estacade_pieux_01/scripts/sonde_lot47.py`, maillage ASTER natif sans
Salomé) établit, avant d'écrire le générateur de l'estacade :

- T1 : une température uniforme portée par une plaque DKT (`CREA_RESU/PREP_VARC`
  d'un champ `TEMP_MIL`/`TEMP_INF`/`TEMP_SUP`, syntaxe du cas test `hsls01a`) et par
  une poutre POU_D_T qui partage ses nœuds (`CHAM_GD` de composante `TEMP`, syntaxe
  du cas test `ssll12a`), deux occurrences d'`AFFE_VARC`, donne la dilatation libre ;
- T2 : `MACRO_ELAS_MULT` (une factorisation, quatre `CAS_CHARGE`) avec `PESANTEUR` sur
  un modèle qui porte un ressort `DIS_T` de masse nulle (DIAG-004), `FORCE_COQUE` FZ
  et FX, `FORCE_ARETE` FZ sur une arête SEG2 de DKT : chaque résultante égale la
  charge déclarée ;
- la section `CERCLE` du tube équivalent (R, EP calculés pour que A et I égalent
  ceux du tableau B2) reproduit l'aire de B2 (poids du pieu).

Niveau visé : C, et D pour les grandeurs ci-dessous.

### 1.2 Critère de réussite (écrit avant l'exécution)

Valeurs attendues calculées par le script, avant l'exécution :
`projets/estacade_pieux_01/references/sonde_lot47_attendus.json`.

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| T1 : DX du nœud Q (x = 1,0) | α ΔT × 1,0 = 2,75e-4 m | exacte (dilatation libre, isostatique) | 1e-6 relatif |
| T1 : DY(y = 0,6) − DY(y = 0) à x = 0 | α ΔT × 0,6 = 1,65e-4 m | exacte | 1e-6 relatif |
| T1 : NXX, NYY de la plaque (`EFGE_ELNO`) | 0 | exacte | ≤ 1e-6 × E·α·ΔT·e (= 3,74 N/m) en valeur absolue |
| T1 : N du chevêtre (`EFGE_ELNO`) | 0 | exacte | ≤ 1e-6 × E·α·ΔT·A (= 10,1 N) en valeur absolue |
| T1 : résultante des réactions | 0 | exacte | ≤ 1e-6 × 10,1 N |
| T2 : PP, résultante DZ des réactions | +24 596,605 N (plaque 6 000, chevêtre 16 200, pieu 2 396,605) | exacte | 1e-6 relatif |
| T2 : G2, résultante DZ | +4 848 N | exacte | 1e-6 relatif |
| T2 : FR, résultante DX | −2 442 N | exacte | 1e-6 relatif |
| T2 : GC (`FORCE_ARETE`), résultante DZ | +500 N | exacte | 1e-6 relatif |

Les réactions s'opposent à la charge (signe inverse de la charge). Toute autre
issue est un échec, rapporté tel quel ; une erreur `<F>` est un échec de la sonde,
classé au registre `rex` du projet.

### 1.3 Exécution

Exécution `data/processed/runs/20261005T094059-46dee2b7` (6,7 s, `aster-expert run`),
diagnostic `<A>_ALARM` : six alarmes `<A> <UTILITAI_4>` (champ `EFGE_NOEU` demandé sur
tout le modèle, où plaque et poutres partagent des nœuds de repères locaux différents).
Diagnostic de la base consulté avant toute hypothèse : **DIAG-011** (même signature) ;
cause expliquée, aucun verdict n'en dépend (les critères lisent `EFGE_ELNO`), et le
générateur de l'estacade restreint `EFGE_NOEU` à la dalle. Tables recopiées dans
`projets/estacade_pieux_01/references/cas/sonde_lot47_listing_extrait.txt`.

### 1.4 Résultats et verdict

| Grandeur | Attendu | Obtenu | Écart | Verdict |
| --- | --- | --- | --- | --- |
| T1 : DX de Q | 2,75e-4 m | 2,750000000000e-4 m | < 1e-12 | réussite |
| T1 : DY(0,6) − DY(0) | 1,65e-4 m | 8,25e-5 − (−8,25e-5) = 1,65e-4 m | < 1e-12 | réussite |
| T1 : NXX, NYY plaque | 0 (seuil 3,74 N/m) | ≤ 3,7e-9 N/m | — | réussite |
| T1 : N chevêtre | 0 (seuil 10,1 N) | ≤ 1,9e-9 N | — | réussite |
| T1 : résultante des réactions | 0 (seuil 1,01e-5 N) | ≤ 1,7e-9 N | — | réussite |
| T2 : PP, DZ | 24 596,605 N | 24 596,605 N | < 1e-12 | réussite |
| T2 : G2, DZ | 4 848 N | 4 848,000 N | < 1e-12 | réussite |
| T2 : FR, DX | −2 442 N | −2 442,000 N | < 1e-12 | réussite |
| T2 : GC (`FORCE_ARETE`), DZ | 500 N | 500,000 N | < 1e-12 | réussite |

Lecture. Faits : la dilatation libre est exacte avec deux occurrences d'`AFFE_VARC`
(`EVOL` préparé par `PREP_VARC` sur la plaque DKT, `CHAM_GD` de composante `TEMP` sur
la poutre POU_D_T qui partage ses nœuds) ; `MACRO_ELAS_MULT` accepte `PESANTEUR` avec un
ressort `DIS_T` de masse nulle ; `FORCE_ARETE` agit sur une arête SEG2 affectée en DKT ;
la section `CERCLE` du tube équivalent redonne l'aire de B2 (poids du pieu exact) ; le
MED d'un résultat `mult_elas` range les cas en pas (k, k) dans l'ordre de `CAS_CHARGE`
(même numéro que `NUME_ORDRE` des tables). Déduction : sous les cas verticaux, les
réactions horizontales non nulles des appuis (−3,13 N en DX sous PP) équilibrent la
force du ressort du pieu (le cisaillement VY du tronçon supérieur du pieu vaut
3,128 N, nul sous le ressort) : la plaque tourne en P0 et le pieu suit. Lacune de
l'outil relevée : le validateur de niveau B ne résout pas un tuple de concepts
(`CHAR_MECA_GLOBAL=(CL,)`) et laisse alors `MACRO_ELAS_MULT` et toute la suite non
confrontés ; une référence simple (`CHAR_MECA_GLOBAL=CL`) est confrontée.

## 2. Contre-calcul de l'estacade — critères (écrits avant toute exécution du modèle)

### 2.1 Objet

Contre-calculer avec Code_Aster 17.4.0 le modèle source d'avant-projet (tablier-dalle
sur chevêtres, 14 pieux métalliques, ressorts de sol) selon E1 à E16
(`projets/estacade_pieux_01/donnees/sources/arbitrage_estacade_pieux_01_lot47.md`) et
l'annexe B (`.../annexe_B_lot47.md`), puis comparer aux valeurs publiées (B6). Niveau
visé : C avec contrôles D. **La comparaison est un contre-calcul d'un modèle non
validé, jamais un niveau E.**

### 2.2 Modèle (rappel de la fiche, pour lire les critères)

- Repère (U1) : X le long du tablier depuis l'about, Y transversal depuis l'axe, Z vers
  le haut égal à la cote NGF ; dalle au plan moyen Z = +1,30 ; m, N, Pa.
- Dalle DKT (E13), QUAD4 de 0,05 m (U2), normales orientées +Z, `ANGL_REP = (0, 0)` :
  x_l = X. Chevêtres POU_D_T (E13), rectangle 1,20 (selon X) × 0,90 (selon Z), au plan
  moyen, nœuds partagés avec la dalle (E2). Pieux POU_D_T, section `CERCLE` du tube
  équivalent à A et I de B2 (CA-057), tête au nœud du plan moyen (E3), DZ = 0 en pointe
  (E4), ressorts `DIS_T` kx = ky aux nœuds tous les 0,50 m (B3, E6), linéaires (E5).
- Charges : PP (pesanteur, E7), G2, UDL, TR, FR, TE+, TE− (B4, E9, E10) ; TS et LM2 en
  positions mobiles (E8, E15, E16) : TS, centre du tandem en X = 15,60 + 0,50 k,
  k = −29 … 29 (59 positions, toutes les empreintes sur la dalle, pas de 0,50 m,
  symétriques par rapport au milieu X = 15,60) ; LM2, X = 15,575 − 0,50 k et
  15,625 + 0,50 k, k = 0 … 30 (62 positions, empreintes alignées sur les mailles de
  0,05 m) ; positions transversales « axé » (TS : roues à Y = ±1,00 ; LM2 : ±1,00) et
  « bord de voie » côté Y > 0 (TS : roues à Y = 1,30 et −0,70 ; LM2 : 1,20 et −0,80).
  Le côté Y < 0 est l'image miroir (structure et autres charges symétriques en Y,
  contrôlé par CTL-006 sur les cas symétriques) : les extrema sur l'ouvrage sont les
  mêmes (déduction).

### 2.3 Conventions de signe et de repère

- **Dalle.** Code_Aster : `EFGE_NOEU` de DKT, repère local x_l = X, normale +Z ;
  `MXX` > 0 tend la face du côté de la normale, ici la face **supérieure** (CA-045).
  Modèle source : convention lue de C13 (« Mxx inf. » positif, « Mxx sup. » négatif),
  soit Mxx > 0 tendant la face **inférieure** ; la « direction automatique » des
  plaques du modèle source est prise comme x local = X global (non vérifiable sans le
  modèle source : hypothèse). Comparaison : M_source ≙ −MXX ; Qxx ≙ `QX` ; Nxx ≙ `NXX`
  (traction positive dans les deux). Les valeurs C9 et C10 sont publiées sans signe :
  C9 (chapeau) se compare à max(MXX) (traction en face supérieure), C10 (travée) à
  max(−MXX).
- **Pieux.** Code_Aster : `EFGE_ELNO` des POU_D_T, N > 0 en traction (établi par la
  sonde S1 : pieu suspendu sous son poids, N = +γAL en tête). Modèle source : « N max »
  positif lu comme une compression ; N_source ≙ −N. Moments et efforts tranchants :
  axes locaux du modèle source inconnus ; **comparaison des modules** : M = √(MFY² +
  MFZ²), V = √(VY² + VZ²), à chaque extrémité d'élément ; les composantes sont
  rapportées à titre d'information.
- **Chevêtres.** Module de V (`VZ`, effort tranchant vertical). Moments : MFY (flexion
  dans le plan vertical) ; le signe « travée » (fibre inférieure tendue) est calé sur la
  physique : sous le cas G seul, le moment au milieu du chevêtre (Y = 0) est en travée
  (portée 4,00 m entre pieux, consoles de 1,00 m) ; s = signe de MFY(G, Y = 0) par
  chevêtre et M_travée = s · MFY. C6 se compare au maximum de M_travée sur |Y| < 2,00,
  C7 au minimum de M_travée aux nœuds Y = ±2,00 (les deux extrémités d'élément).

### 2.4 Combinaisons et enveloppes (E11)

Combinaisons 100 à 115 de B5, recopiées dans `projets/estacade_pieux_01/combinaisons.py`
(test contre le texte de B5) : ELS f, ELS c, ELU+ (γG = 1,35) et ELU− (γG = 1,00 sur
G = PP + G2). LM1 = UDL + TR + TS ; dans une combinaison, la valeur en un point est
l'enveloppe sur les positions de TS (« axé » pour 102 à 108, « bord de voie » pour 109
à 115) : max (ou min) sur k de Σ γ·cas fixes + γ_LM1 (UDL + TR + TS_k). La valeur
« ELU » d'un point est l'enveloppe d'ELU+ et d'ELU− de la combinaison citée. Quand B6
cite deux combinaisons (« 105 / 112 »), les colonnes ELS lisent la première et la
colonne ELU la seconde ; pour C8 (ELU seul), max et min sont pris sur l'enveloppe des
deux. FR est appliqué selon +X seulement (E9, une direction).

### 2.5 Points de comparaison et tolérances (E12)

| N° | Lecture Code_Aster | Zone | Tolérance |
| --- | --- | --- | --- |
| C1 | max sur les nœuds de √(DX²+DY²+DZ²), comb. 107 ELS c, enveloppe sur TS | tout l'ouvrage | source arrondie au demi-centimètre : « compatible » si 0,25 ≤ u < 0,75 cm |
| C2 | max de −N (compression) à l'extrémité haute de l'élément de tête de chaque pieu (Z = +1,30), comb. 112 | 14 pieux | 3 % (efforts globaux) ; valeurs alternatives 554 / 767 / 1 102 kN rapportées, non arbitrées |
| C3 | max de √(MFY²+MFZ²), comb. 111, comparé à max(|max|, |min|) publié ; second extremum publié en information | bouchon : −0,80 ≤ Z ≤ +0,70 (E14) | 5 % |
| C4 | max de √(VY²+VZ²), comb. 114 ELU | bouchon | 5 % |
| C5 | max de √(MFY²+MFZ²), comb. 111 ELU, comparé à 463 | pieu : Z < −0,80 | 5 % |
| C6 | max de M_travée, comb. 105 (ELS f, ELS c), 112 (ELU) | chevêtres, |Y| < 2,00 | 5 % |
| C7 | min de M_travée, enveloppe des ELU 100 à 115, comparé en module à 177 | chevêtres, nœuds Y = ±2,00 | 5 % |
| C8 | max et min de VZ, enveloppe de 105 et 112 ELU, comparés en module (653 gouverne) | chevêtres | 5 % |
| C9 | max de MXX (chapeau, face supérieure tendue), comb. 111 | |X − X_i| ≤ 0,60 (largeur du chevêtre) | 10 % |
| C10 | max de −MXX (travée), comb. 112 | |X − X_i| > 0,60 pour toute file | 10 % |
| C11 | max de |NXX| : FR seul ; TE− seul | toute la dalle | 10 % |
| C12 | max de |QX|, ELU : courant comb. 111 ; rive comb. 100 | courant : |Y| ≤ 1,50 (voie) ; rive : |Y| > 1,50 (trottoirs, files de pieux) | 10 % |
| C13 | enveloppes non pondérées (cas élémentaires) : max(−MXX), min(−MXX), max |QX| ; LM1 = UDL + TR + TS (toutes positions axé et bord) ; LM2 (toutes positions) | toute la dalle | 10 % |

Lecture de C12 (« courant / rive ») et de la zone « chapeau » : définitions de la
session, la source ne les précise pas ; une lecture complémentaire, sans verdict, est
rapportée : Qxx sur les consoles d'about (X ≤ 1,20 ou X ≥ 30,00). Écart relatif =
(Code_Aster − source) / |source| ; verdict « dans la tolérance » si |écart| ≤ tolérance,
sinon « hors tolérance », chaque écart hors tolérance expliqué (hypothèse, erreur d'un
côté, formulation) ou déclaré « inexpliqué » avec les pistes examinées. Aucune valeur
n'est ajustée pour se rapprocher de la source ; les variantes de sensibilité d'E13
((a) DST pour la dalle ; (b) POU_D_E pour les chevêtres si C6 à C8 sortent de
tolérance) sont déclarées comme telles et ne remplacent pas le calcul de référence.

### 2.6 Harnais D (seuil 1e-6 en relatif)

- CTL-005, équilibre de chaque cas déclaré (PP, G2, UDL, TR, FR, TE+, TE− et quatre
  positions mobiles : TS axé et bord au centre X = 15,60, LM2 axé et bord en
  X = 15,575) : charge appliquée + réactions DZ des pointes (`PIEDS`) + forces des
  ressorts (Σ k·u selon DX et DY, k des données, u lu dans Code_Aster) = 0, par
  composante ;
- CTL-013, résultante de chaque cas comparée à la charge déclarée, calculée à partir des
  données : PP = γ_béton (dalle 31,20 × 6,00 × 0,40 + 7 chevêtres 6,00 × 1,20 × 0,90) +
  γ_acier Σ A·L des pieux ; G2, UDL, TR, FR selon les surfaces de B1 ; TE± nulle ;
  chaque position mobile : 4 × 135 kN (TS) ou 2 × 160 kN (LM2) ;
- contrôle propre au projet sur **toutes** les positions mobiles (242 cas) : Σ DZ des
  réactions des pointes = charge des roues, à 1e-6 ;
- CTL-006, symétrie des déplacements par rapport aux plans X = 15,60 et Y = 0 pour PP,
  G2, UDL, TR, TE+ et TE− ;
- double compte d'E2 chiffré (rapporté, non corrigé) : 1,20 × 0,40 × 6,00 × 25 =
  72,0 kN par chevêtre, 504 kN pour les sept ; il est inclus dans la résultante PP.

### 2.7 Convergence de maillage de la dalle sous charge de roue

Suite h = 0,10 / 0,05 / 0,025 m (même script Salomé, `maillage/params_h0p*.json`),
deux cas : TS axé centré en X = 8,10 (travée entre les files 2 et 3) et en X = 5,60
(sur la file 2). Grandeurs : max(−MXX) (travée), max(MXX) (sur la file 2), max |QX|,
max |DZ| de la dalle. Critère (CTL-012 n'est pas applicable : aucune solution de
référence, niveau E non visé) : pour chaque grandeur, |Q(0,10) − Q(0,05)| >
|Q(0,05) − Q(0,025)| (l'écart décroît au raffinement ×2), et l'écart du maillage de
production |Q(0,05) − Q(0,025)| / |Q(0,025)| ≤ 2 %. Toute autre issue est un échec de
la grandeur concernée, rapporté tel quel avec sa conséquence sur la comparaison.

## 3. Résultats (rédigés après les exécutions ; les critères du § 2 ne sont pas modifiés)

### 3.1 Convergence de maillage (critère § 2.7)

Exécutions : h = 0,10 `20261005T100812-bdc02930` (16,2 s), h = 0,05
`20261005T100829-3782599a` (40,4 s), h = 0,025 `20261005T100910-b21d2121` (227,3 s),
toutes `OK`, aucune alarme ; Σ DZ des pointes = 540 kN par position (h = 0,10 : écart
2,6e-11). Une première exécution de h = 0,025 (`20261005T100413-8334652d`) s'est arrêtée
sur `<F> <FACTOR_57>` (MUMPS, erreur 2,08e-6 pour RESI_RELA = 1e-6). DIAG-003 a été lu
avant toute hypothèse : aucune redondance (seul DZ des pointes est bloqué, une fois) ni
mécanisme (h = 0,10 et 0,05 résolus) ; correction : raffinement itératif forcé
(`POSTTRAITEMENTS="FORCE"`), `RESI_RELA` inchangé, appliqué à toutes les exécutions du lot
(convergence relancée sur les trois maillages, production). Valeurs :
`projets/estacade_pieux_01/references/convergence_lot47.json`.

| Grandeur | h = 0,10 | h = 0,05 | h = 0,025 | Écart décroissant | Écart de production | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| travée, max(−MXX) (kN·m/m) | 66,871 | 66,884 | 66,983 | non (0,013 puis 0,099) | 0,15 % | échec |
| travée, max |QX| (kN/m) | 179,2 | 368,3 | 766,2 | non (×2 à chaque pas) | 52 % | échec |
| travée, max |DZ| (mm) | 0,98551 | 0,98479 | 0,98413 | oui | 0,07 % | réussite |
| file 2, max(MXX) (kN·m/m) | 25,12 | 30,73 | 34,78 | oui (5,61 puis 4,05) | 11,7 % | échec |
| file 2, max |QX| (kN/m) | 197,1 | 452,1 | 993,4 | non (×2 à chaque pas) | 54 % | échec |
| file 2, max |DZ| (mm) | 0,57650 | 0,57494 | 0,57362 | oui | 0,23 % | réussite |

Lecture. Faits : les maxima de |QX| et de MXX (sur appui) sont aux nœuds de tête de
pieux et à leurs voisins immédiats (X = 5,55 à 5,65 et 10,55 à 10,65, Y = ±2,00, au
maillage 0,05) ; |QX| y double à chaque division de la maille par 2. Déduction : la tête
de pieu est reliée à la dalle en un seul nœud (E2, E3 : chevêtre et pieu au plan moyen,
nœud partagé) ; la réaction concentrée et le moment transmis par le pieu sont, pour la
plaque, une force et un couple ponctuels, dont l'effort tranchant (en 1/r) et le moment
(en log r) sont singuliers : ces maxima n'ont pas de limite au raffinement. Le moment de
travée sous la roue converge (0,15 % entre 0,05 et 0,025) mais l'écart ne décroît pas au
sens du critère (0,013 puis 0,099 kN·m/m) : échec rapporté tel quel, d'amplitude faible
devant la tolérance de 10 %. Conséquence sur la comparaison : C9 (chapeau), C12 et la
colonne V de C13 lisent des maxima sur toute la dalle, donc atteints aux têtes de pieux :
leurs valeurs dépendent du maillage, dans Code_Aster comme dans le modèle source ; leurs
écarts ne peuvent être jugés qu'avec cette réserve (§ 3.4).

### 3.2 Exécution de production

Une première exécution (`20261005T101311-0097f394`) s'est arrêtée à la 5ᵉ commande sur
`<F> <JEVEUX_10>` (`&&SSCGNO.LITMP2`) : un `CREA_GROUP_NO` portant quatre `GROUP_MA` dans
une seule occurrence. Le diagnostic **DIAG-010** de la base le décrivait déjà, mais
n'avait pas été consulté avant d'écrire la commande (consultation faite par concept, pas
par commande `DEFI_GROUP`) : erreur **non évitée** alors que la connaissance existait.
Correction de DIAG-010 appliquée (un groupe par `GROUP_MA`, puis `UNION`), test ajouté.
Exécution de référence : `20261005T101455-e0d5c870`, 1 753 s, `OK`, aucune alarme ; 247
cas en 10 lots de `MACRO_ELAS_MULT`, TE+ et TE− par `MECA_STATIQUE` ; `.comm` versionné
(`projets/estacade_pieux_01/references/cas/estacade_pieux_01.comm`, niveau B 420/420).

### 3.3 Harnais D et double compte d'E2 (critère § 2.6)

| Contrôle | Résultat | Verdict |
| --- | --- | --- |
| CTL-005, équilibre de PP, G2, UDL, TR, FR et des quatre positions mobiles | écart relatif ≤ 1,7e-10 | réussite |
| CTL-005, équilibre de TEP et TEM | charge appliquée nulle : écart relatif **indéfini (NaN)** ; bilan absolu ≤ 2,4e-5 N pour Σ |k·u| = 1,01e6 N | **échec formel** |
| CTL-005, pesanteur (PP, DZ) | 3 553 297,604 N appliqués, 3,1e-11 | réussite |
| CTL-013, résultantes | identiques par construction (aucune charge évaluée par fonction) ; NaN pour TEP, TEM | échec formel (même cause) |
| Σ DZ des pointes, 242 positions mobiles | écart maximal 2,8e-10 | réussite |
| CTL-006, symétrie X = 15,60 et Y = 0 (PP, G2, UDL, TR, TEP, TEM ; 1 265 paires) | ≤ 5,7e-10 | réussite |

Le verdict d'ensemble des contrôles D est donc **ÉCHEC**, uniquement par l'écart relatif
indéfini des cas thermiques auto-équilibrés : le critère écrit « 1e-6 en relatif » ne
définit pas l'échelle d'un cas de charge nulle, et le tronc commun rend NaN. Ce verdict
n'est pas modifié ; le paquet de résultats déclare en conséquence le **niveau C** (D non
atteint). Lacune signalée pour un prochain lot : rapporter l'écart d'un cas
auto-équilibré à la plus grande force interne (ici Σ |k·u| des ressorts : 2,4e-5 / 1,0e6
= 2,4e-11).

Double compte d'E2 (rapporté, non corrigé) : 1,20 × 0,40 × 6,00 × 25 = **72,0 kN par
chevêtre**, 504 kN pour les sept, compris dans PP (dalle 1 872,0 kN, chevêtres
1 134,0 kN, pieux 547,3 kN).

### 3.4 Comparaison C1 à C13 (critères § 2.3 à 2.5)

Tableau complet, avec le lieu de chaque extremum :
`projets/estacade_pieux_01/references/comparaison_lot47.json` ; lectures postérieures à
l'exécution, **sans verdict**, qui éprouvent des explications :
`projets/estacade_pieux_01/references/explications_lot47.json`. Conventions : § 2.3
(dalle : M_source ≙ −MXX, x_l = X ; barres : modules √(MFY² + MFZ²), √(VY² + VZ²) ;
N_source ≙ −N). Unités : kN, kN·m, kN·m/m, kN/m, cm.

| Point | Colonne | Code_Aster | Source | Écart | Tolérance | Verdict | Explication |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C13 | LM1 Mxx inf. | 83,61 | 85 | −1,6 % | 10 % | dans la tolérance | — |
| C13 | LM1 Mxx sup. | −80,03 | −47 | −70,3 % | 10 % | hors tolérance | singularité de tête de pieu (A) ; hors voisinage −54,6 ; DST −58,3 |
| C13 | LM1 V | 738,6 | 154 | +380 % | 10 % | hors tolérance | singularité (A) et formulation de plaque (B) ; DST 193,0 |
| C13 | LM2 Mxx inf. | 64,38 | 64 | +0,6 % | 10 % | dans la tolérance | — |
| C13 | LM2 Mxx sup. | −33,74 | −30 | −12,5 % | 10 % | hors tolérance | (A) ; hors voisinage −26,2 ; DST −26,6 |
| C13 | LM2 V | 335,6 | 138 | +143 % | 10 % | hors tolérance | (A), (B) ; DST 131,7 (−4,6 %) |
| C1 | ELS c (107) | 0,4375 cm | 0,5 cm | −12,5 % | arrondi | compatible avec l'arrondi | source arrondie au demi-centimètre |
| C2 | ELS f (112) | 526,9 | 514 | +2,5 % | 3 % | dans la tolérance | valeur alternative 554 : −4,9 % |
| C2 | ELS c (112) | 714,0 | 727 | −1,8 % | 3 % | dans la tolérance | alternative 767 : −6,9 % |
| C2 | ELU (112) | 1 023 | 1 048 | −2,4 % | 3 % | dans la tolérance | alternative 1 102 : −7,2 % |
| C3 | ELS f (111) | 131,0 | 209 | −37,3 % | 5 % | hors tolérance | inexpliqué (C) |
| C3 | ELS c (111) | 192,0 | 312 | −38,4 % | 5 % | hors tolérance | inexpliqué (C) |
| C3 | ELU (111) | 283,4 | 449 | −36,9 % | 5 % | hors tolérance | inexpliqué (C) |
| C4 | ELU (114) | 259,4 | 253 | +2,5 % | 5 % | dans la tolérance | — |
| C5 | ELU (111) | 105,2 | 463 | −77,3 % | 5 % | hors tolérance | inexpliqué (C), piste E6 |
| C6 | ELS f (105) | 202,8 | 180 | +12,7 % | 5 % | hors tolérance | partage chevêtre-dalle (B) ; § 3.5 |
| C6 | ELS c (105) | 303,2 | 276 | +9,9 % | 5 % | hors tolérance | idem |
| C6 | ELU (112) | 443,1 | 408 | +8,6 % | 5 % | hors tolérance | idem |
| C7 | ELU (enveloppe, 111) | 141,9 | 177 | −19,8 % | 5 % | hors tolérance | (A), (B) ; DST 154,8 |
| C8 | ELU (105, 112) | 198,1 | 653 | −69,7 % | 5 % | hors tolérance | (A), (B) ; DST 660,8 (+1,2 %) |
| C9 | ELS f (111) | 111,4 | 79 | +41,0 % | 10 % | hors tolérance | (A) ; hors voisinage 70,7 (−10,6 %) ; DST 93,7 |
| C9 | ELS c (111) | 150,4 | 118 | +27,5 % | 10 % | hors tolérance | (A) ; hors voisinage 105,4 (−10,7 %) |
| C9 | ELU (111) | 214,1 | 174 | +23,0 % | 10 % | hors tolérance | (A) ; hors voisinage 156,2 (−10,3 %) |
| C10 | ELS f (112) | 81,92 | 82 | −0,1 % | 10 % | dans la tolérance | — |
| C10 | ELS c (112) | 130,8 | 134 | −2,4 % | 10 % | dans la tolérance | — |
| C10 | ELU (112) | 192,9 | 198 | −2,6 % | 10 % | dans la tolérance | — |
| C11 | FR seul | 58,76 | 18,9 | +211 % | 10 % | hors tolérance | lecture (D) : moyenne de section 19,7 (+4,2 %) |
| C11 | TE− seul | 149,2 | 64,1 | +133 % | 10 % | hors tolérance | lecture (D) : moyenne de section 62,9 (−1,9 %) |
| C12 | ELU courant (111) | 351,4 | 320 | +9,8 % | 10 % | dans la tolérance | — |
| C12 | ELU rive (100) | 990,3 | 568 | +74,4 % | 10 % | hors tolérance | (A), (B) ; hors voisinage 100,4 ; DST 185,5 ; zone « rive » non définie par la source |

Bilan : 11 lignes dans la tolérance (ou compatibles avec l'arrondi) sur 30 lignes jugées ; 19 hors tolérance (les deux lectures « consoles d'about » de C12 sont des informations sans verdict).

**Explications examinées** (faits mesurés, puis déductions marquées comme telles) :

- **(A) Singularité d'appui ponctuel aux têtes de pieux.** Fait : la suite de convergence
  (§ 3.1) montre |QX| doublé et MXX sur appui croissant à chaque raffinement aux nœuds de
  tête ; tous les extrema hors tolérance de C9, C12 « rive », C13 « sup. » et « V » sont
  lus à moins d'une maille d'une tête de pieu (lieux du tableau JSON). Lus hors d'un rayon
  de 0,60 m autour des têtes, C9 passe à −10,3 % / −10,7 % / −10,6 % et C13 LM2 « sup. »
  à −12,7 %. Déduction : la valeur source dépend aussi de son maillage (inconnu) ; ces
  écarts sont des écarts de discrétisation d'une grandeur sans limite, pas d'un modèle.
- **(B) Formulation de la plaque et partage de la charge entre dalle et chevêtre.** Fait :
  sous TS sur la file 2, l'effort tranchant du chevêtre près du pieu décroît au raffinement
  (88,9 → 60,4 → 36,9 kN, h = 0,10 → 0,025) alors que son moment est stable (156 → 157 kN·m)
  et que la charge de la tête l'est aussi (468 kN) : la dalle DKT, sans déformation
  d'effort tranchant, porte d'autant plus directement la charge au nœud du pieu que la
  maille est fine. Fait (variante (a) d'E13, DST) : C8 passe de 198 à 660,8 kN (+1,2 % de
  la source), C13 LM2 « V » de 336 à 131,7 kN/m (−4,6 %), C7 de 141,9 à 154,8 kN·m.
  Déduction : les éléments de plaque du modèle source prennent vraisemblablement en compte
  la déformation d'effort tranchant (type Mindlin) ; c'est une **différence de formulation**,
  qu'E13 a tranchée (DKT) ; la référence n'est pas changée.
- **(C) Moments des pieux (C3, C5) : inexpliqué.** Faits : en tête, TE+ domine (107,5 kN·m
  sur 283,4 au point de C3, file 7) ; les têtes des files de rive se déplacent de
  4,06 mm sous TE+ (dilatation quasi libre de la dalle : α ΔT × 15,0 m = 4,13 mm) ; C3 est
  plus faible que la source d'un rapport constant (0,63) sur ELS f, ELS c et ELU ; C5
  (Z < −0,80) est lu à −2,50 m, file 7, et vaut 23 % de la source. Pistes examinées sans
  conclure : formulation des pieux (POU_D_T, sections B2 exactes : I/R = I/v publié) ;
  ressorts (k de B3 en N/m, kx = ky, aucune somme à un nœud commun, CA-034) ; DST (sans
  effet : C3 −0,2 %, C5 +0,1 %). Pistes non examinables sans le modèle source : valeurs de
  ressorts réellement saisies dans le modèle source aux nœuds −8,00 à −10,50 de la file 1
  (E6 corrige une erreur de recopie et complète deux nœuds manquants : si le modèle source
  les portait ainsi, les moments en profondeur y seraient plus grands — piste pour C5) ;
  liaison réelle des pieux au tablier dans le modèle source ; axes et composantes des
  moments publiés.
- **(D) Lecture de C11.** Fait : la moyenne de NXX sur une section transversale vaut
  19,7 kN/m sous FR (source 18,9) et 62,9 kN/m sous TE− (source 64,1), alors que le maximum
  nodal est atteint près des têtes de pieux (efforts concentrés du pieu dans le plan de la
  dalle). Déduction : la source publie vraisemblablement une valeur courante ou moyenne ;
  le critère écrit lit le maximum : écart de **lecture**, non de modèle.
- **C6 (chevêtre en travée, +8,6 à +12,7 %)** : la variante (b) d'E13 (POU_D_E) teste
  l'hypothèse de MM « le modèle source ne prend pas en compte la déformation d'effort
  tranchant des barres » (§ 3.5).

### 3.5 Variantes de sensibilité d'E13 (déclarées comme telles, sans verdict)

Elles ne remplacent pas la référence (DKT, POU_D_T) ; même lecture que § 2.5. Tableaux :
`projets/estacade_pieux_01/references/variante_dst_lot47.json`,
`.../variante_pou_d_e_lot47.json`.

- **(a) DST pour la dalle** : exécution `20261005T104915-1d558927` (2 442 s, `OK`).
- **(b) POU_D_E pour les chevêtres** (hypothèse de MM : « le modèle source ne prend pas en
  compte la déformation d'effort tranchant des barres », demandée si C6 à C8 sortent de
  tolérance, ce qui est le cas) : deux exécutions arrêtées sur `<F> <FACTOR_57>`
  (`20261005T104726-677b0c0a`, erreur 2,81e-6 malgré `POSTTRAITEMENTS="FORCE"` ;
  `20261005T130207-09fd42f0`, 1,41e-6 sur les cas thermiques) ; `RESI_RELA` relâché à 1e-5
  pour cette seule variante (DIAG-003 : motif écrit, pas de redondance — mêmes conditions
  aux limites que la référence, qui se résout —, équilibre contrôlé : Σ DZ des pointes à
  6,7e-9 sur les 242 positions) ; exécution `20261005T132953-7c17bdcb` (1 736 s, `OK`).

| Point | Référence | (a) DST | (b) POU_D_E | Source |
| --- | --- | --- | --- | --- |
| C6 ELS f / ELS c / ELU | 202,8 / 303,2 / 443,1 | 203,3 / 304,2 / 443,1 | 204,8 / 306,0 / 447,6 | 180 / 276 / 408 |
| C7 ELU | 141,9 | 154,8 | 165,5 | 177 |
| C8 ELU | 198,1 | 660,8 | 697,6 | 653 |
| C9 ELS f / ELS c / ELU | 111,4 / 150,4 / 214,1 | 93,7 / 134,5 / 198,2 | 94,0 / 135,5 / 200,0 | 79 / 118 / 174 |
| C13 LM2 V | 335,6 | 131,7 | — | 138 |
| C3 ELU, C5 ELU | 283,4 ; 105,2 | 282,8 ; 105,3 | 283,4 ; 105,2 | 449 ; 463 |

Lecture. Faits : les deux variantes changent surtout l'effort tranchant du chevêtre au
voisinage du pieu (C8 ×3,3 à ×3,5) et le moment sur appui (C7), très peu le moment en travée
(C6) et pas du tout les pieux (C3, C5) ni la dalle en travée (C10). Déduction : le partage de
la charge entre la dalle et le chevêtre au nœud du pieu est gouverné par la rigidité locale
la plus faible ; une dalle sans déformation d'effort tranchant (DKT) court-circuite le
chevêtre, ce qui explique C8 et en partie C7 ; l'hypothèse (b) de MM rapproche C7 et C8 de
la source, mais éloigne C6 (+9,7 % à +13,8 %) : **C6 reste inexpliqué** ; C3 et C5 n'en
dépendent pas (**inexpliqués**, § 3.4 (C)).

## 4. Limites

- **Contre-calcul d'un modèle non validé** : aucune ligne n'est un niveau E ; REF-015
  (`calcul_externe_non_valide`) ne peut servir à aucune promotion.
- Niveau atteint par le paquet : **C**. Le niveau D n'est pas reconnu, à cause de l'échec
  formel de CTL-005 et CTL-013 sur TEP et TEM (écart relatif indéfini) ; tous les autres
  contrôles D sont tenus.
- Les maxima de dalle aux têtes de pieux n'ont pas de limite au raffinement (§ 3.1). Les
  comparaisons qui les lisent (C9, C12 « rive », C13 « sup. » et « V ») dépendent du
  maillage. Les lectures hors voisinage du § 3.4 sont postérieures à l'exécution.
- Moments des pieux (C3, C5) et moment en travée du chevêtre (C6) : écarts **inexpliqués**,
  pistes listées. Le modèle source (saisie réelle des ressorts, liaisons, axes des
  résultats) n'est pas disponible.
- FR n'est appliqué que selon +X (E9). Le côté « bord de voie » Y < 0 est déduit par
  symétrie ; il n'est pas calculé.
- La variante POU_D_E est calculée avec `RESI_RELA = 1e-5` (DIAG-003, motif écrit).
- Lacunes de l'outil signalées pour un prochain lot : le validateur de niveau B ne résout
  pas un tuple de concepts ; il faut une échelle d'équilibre pour un cas de charge nulle.
