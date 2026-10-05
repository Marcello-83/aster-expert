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
