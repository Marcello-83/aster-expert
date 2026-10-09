# Essais du lot 49 ter — livrables de l'estacade : section en T, lecture au nu, moment sur appui (E24 à E27)

Consigne : `docs/lots/lot49ter_consigne.md`. Profil **vm**. Code_Aster 17.4.0, image
`simvia/code_aster:17.4.0` (digest `sha256:d8d19ea9…`). Ce rapport suit
`docs/modele_rapport_essai.md` : les sections 1 à 3 (objet, méthode, critères) sont
écrites et commitées **avant** toute exécution de ce lot (modèles dérivés A1 à A3,
variante V1, cas analytiques) et avant la première lecture des nouvelles sections ;
elles ne sont pas modifiées ensuite (une erreur s'y corrige dans une section datée
« Correction du critère »).

## 1. Objet

1. Enregistrer les décisions E24 à E27 de MM (`aster-expert fiche enregistrer`) et
   mettre à jour l'attribution de C6 (constat sur E19).
2. Calculer les **moments d'encastrement parfait** d'E27 par trois modèles auxiliaires
   dérivés de la référence (A1 chevêtres, A2 dalle, A3 bouchon), générés par une option
   générique du tronc commun (`engineering_summary.derived_models`), contrôlés par un
   harnais D et validés sur deux cas analytiques (A1, A2).
3. Corriger les six défauts D1 à D6 des livrables de l'estacade : section en T des
   chevêtres (E25), effort tranchant de la dalle, zones disjointes et signe de
   section, convention de la synthèse, arrondis du classeur, section du bouchon au nu
   (E24) avec la variante déclarée V1.
4. Compléter la comparaison à la source (feuille « Comparaison externe », profil du
   chapeau) ; empreintes des fichiers livrés et commande de vérification ; patrons et
   contrôle de livrable.

Niveau visé : **aucun niveau nouveau pour la référence** (contre-calcul au niveau D,
conservé par la règle du paquet : le `.comm` de production n'est pas modifié). Les
modèles dérivés et la variante atteignent au plus le niveau D (harnais D) ; les cas
analytiques sont des essais de niveau D sur un modèle dérivé, jamais un niveau E de
l'estacade.

## 2. Méthode (écrite avant toute exécution du lot)

### 2.1 Décisions et constat

E24 à E27 : texte de MM recopié de la consigne dans
`projets/estacade_pieux_01/donnees/sources/arbitrage_estacade_pieux_01_lot49ter.md`,
enregistré par `aster-expert fiche enregistrer` depuis
`enregistrement_E24_E27_lot49ter.md` (rejoué par `scripts/fiche_lot47.py`). Les
clauses de l'EN 1992-1-1 (§5.3.2.2(3) et sa note) sont citées **d'après MM et le
superviseur** : le corpus du dépôt ne contient pas l'Eurocode, la session ne l'a pas
relu. E1 à E23 ne changent pas. Constat sur E19 (§20.5.1 de la source : « h = 0.80 m
(augmenté à 0.90m) ») : l'attribution de C6 passe de « hypothèse non établie » à
« probable, appuyée par le texte de la source », sans changer la référence.

### 2.2 Modèles dérivés (tronc commun : `aster_expert.livrables.derives`)

**Faits établis dans la documentation 17.4 (niveau A)** :

- U4.44.01, « Mot-clé DDL_IMPO » : impose des valeurs de degrés de liberté sur des
  nœuds désignés par `GROUP_NO` ou `GROUP_MA` (catalogue 17.4 : `DX` … `DRZ`).
- U4.44.01, « Mot-clé LIAISON_SOLIDE » : « permet de modéliser une partie indéformable
  d'une structure » ; « si un élément a tous ses nœuds dans une zone solidifiée […] sa
  déformation est nulle […] ainsi que les efforts généralisés s'il s'agit d'un élément
  de structure ». La lecture d'un moment au bas d'un tronçon solidifié se fait donc
  dans l'élément situé **sous** ce tronçon.
- Catalogue 17.4 : `MACRO_ELAS_MULT/CHAR_MECA_GLOBAL` admet plusieurs chargements ;
  `DEFI_GROUP/CREA_GROUP_MA` (`NOM`, `INTERSEC`), `CREA_GROUP_NO` (`GROUP_MA`, `NOM`).

**Construction (générique).** Le `.comm` de production est repris mot pour mot, plus :
un `DEFI_GROUP` avant `AFFE_MODELE` (un groupe par partie rigide, intersection du
groupe déclaré et du groupe de chaque pieu ; groupes de nœuds des réactions), un
`AFFE_CHAR_MECA` `DRV_<nom>` (DDL_IMPO, LIAISON_SOLIDE) avant la première résolution,
ajouté à chacune des 12 résolutions (`CHAR_MECA_GLOBAL=(CL, DRV_<nom>)` des 10
`MACRO_ELAS_MULT`, `EXCIT` des 2 `MECA_STATIQUE`). Toute autre forme de résolution est
refusée. Le `.comm` de post-traitement du lot 49 y insère ensuite les sorties (champs
déclarés par le modèle, réactions sur les appuis et sur les groupes bloqués ou rigides).
Validation de niveau B exigée (verdict `valide`).

| Modèle | Rôle | Conditions ajoutées |
| --- | --- | --- |
| A1 | auxiliaire, chevêtres | DDL_IMPO DX, DY, DZ, DRX, DRY, DRZ = 0 sur `TETES` |
| A2 | auxiliaire, dalle | DDL_IMPO DZ, DRY = 0 sur les nœuds de `CHEVETRES` (lignes selon Y : DRY est la rotation autour de la ligne) |
| A3 | auxiliaire, bouchon | LIAISON_SOLIDE sur `PIEU_T1` ∩ chaque pieu, DDL_IMPO DRX, DRY, DRZ = 0 sur `TETES` |
| V1 | variante déclarée (D6) | LIAISON_SOLIDE sur `PIEU_T1` ∩ chaque pieu |

*Déductions (à vérifier par l'exécution)* :

- A1 : les six ddl des têtes étant imposés, les pieux n'agissent plus sur le tablier ;
  le tablier de A1 est celui d'un modèle « sans les pieux » à têtes encastrées (les
  efforts des pieux, sous leur seul poids, vont aux têtes et aux pointes).
- Tronçon indéformable : le maillage des pieux n'a **aucun nœud à +0,60** (nœuds à
  +0,50, +0,70, +1,00, +1,30) et ce lot ne crée pas de maillage. Le tronçon rendu
  indéformable va donc de **+0,70** (nœud le plus proche au-dessus de +0,60, début de
  `PIEU_T1`) à +1,30 ; 0,10 m de l'élément +0,50 → +0,70 reste déformable. Écart
  déclaré, chiffré par la longueur seulement (pas de calcul de sensibilité).
- A3 : la liaison laisse libres les six mouvements de corps rigide du tronçon ; bloquer
  les trois rotations du seul nœud de tête n'est pas redondant (DIAG-001 : un pivot nul
  `FACTOR_11` signalerait le contraire ; il serait rapporté tel quel).

**Actions des modèles auxiliaires (E27).** Les combinaisons et positions mobiles de la
référence, les cas FR, TEP, TEM mis à zéro (charges verticales seulement : G, G2, LM1
TS et UDL, TR ; LM2 est vertical et reste, ses positions étant celles de la référence).
Choix écrit dans la synthèse ; MM peut le renverser. Dans la livraison de référence,
l'essieu de trottoir d'E18 n'est pas un cas des combinaisons (calculé à part au lot
47 bis) : il n'entre ni dans la référence ni dans les auxiliaires.

### 2.3 Harnais D des modèles dérivés (CTL-005 étendu)

Pour chaque cas élémentaire du modèle dérivé : Σ forces nodales du cas (MED des
charges) + Σ réactions (chaque nœud une fois : appuis, groupes bloqués, nœuds des
parties rigides, dont les composantes non bloquées s'annulent sur l'ensemble lié,
CA-036) + Σ forces des ressorts = 0 ; écart rapporté à la plus grande composante de la
charge (somme des modules pour un cas thermique autoéquilibré). Pour chaque position
mobile (aucun MED de charge) : réaction verticale totale égale à celle de la référence
(même charge appliquée).

### 2.4 Validation analytique de A1 et A2

Exécutions dédiées (`projets/estacade_pieux_01/scripts/validation_auxiliaires_lot49ter.py`) :
le `.comm` du modèle dérivé jusqu'à sa première résolution, puis une résolution
`MECA_STATIQUE` d'un seul cas et les lectures, imprimées en `E20.12`.

- **A1** : `FORCE_POUTRE` FZ = −q, q = 100 kN/m, sur les seules mailles du chevêtre de
  la file 4 (X = 15,60) entre les pieux (|Y| ≤ 2,00) ; consoles et dalle non chargées.
  Lecture : moment de la section en T (§ 2.5) à l'axe des pieux (Y = ±2,00), sur
  chacune des deux extrémités d'élément qui y aboutissent ; attendu q·L²/12 =
  133,33 kN·m (L = 4,00 m, poutre bi-encastrée).
- **A2** : `FORCE_COQUE` FZ = −q, q = 10 kPa, sur toute la dalle. Lecture : MXX
  (`EFGE_NOEU`) aux nœuds des lignes d'axe des files 2 à 6 (X = 5,60 … 25,60) à
  Y = 0 (à 3,00 m des bords libres, à 2,00 m des têtes) ; attendu q·L²/12 =
  20,833 kN·m/m (L = 5,00 m, flexion cylindrique d'une bande bi-encastrée).

*Déduction écrite avant* : en A1, la dalle relie la file chargée aux files voisines,
elles aussi portées par des têtes encastrées ; une part de la charge peut passer par la
dalle hors de la bande de ±0,60 m, si bien que la section en T peut ne pas retrouver
toute la valeur q·L²/12. La coupe complète (tous les chevêtres et toute la dalle à
Y = ±2,00) est aussi rapportée. Tout écart au-delà de 2 % est expliqué ou déclaré
inexpliqué, jamais absorbé par le seuil.

### 2.5 Section en T des chevêtres (E25, règle E17.2) — méthode d'intégration

- **Largeur** : bande |X − X_file| ≤ b/2 = 0,60 m (chevêtre de 1,20 m, E2), bords
  compris.
- **Nœuds** : à chaque ligne de la barre (extrémité d'élément au nœud (X_file, Y)), les
  nœuds de la dalle de même Y (à 10⁻⁶ m près) dans la bande, soit 25 nœuds au pas de
  0,05 m ; intégrale par trapèzes en X.
- **Champ** : `EFGE_NOEU` de la dalle (DKT) et `EFGE_ELNO` de la barre (POU_D_T).
- **Repère et signes** (R3.08.01 : MFY = ∫ z σxx dS ; CA-045 : MXX, MYY > 0 tendent la
  face supérieure ; chevêtre x_l = +Y, y_l = −X, z_l = +Z ; dalle repère global) :
  le moment exercé sur la partie Y < Y₀ par la barre est MFY·e_{y_l} = −MFY·e_X ; par la
  dalle, −MYY·e_X par unité de longueur. D'où N_T = N + ∫NYY dX, M_T = MFY + ∫MYY dX,
  V_T = VZ + ∫QY dX, en convention de la barre (M_T > 0 tend la fibre supérieure). C'est
  l'opposé de « s·MFY − ∫MYY dX » du lot 47 bis (s = −1) : mêmes valeurs, signe de la
  convention Code_Aster de la barre.
- La barre seule reste dans les colonnes `N_barre`, `MFY_barre`, `VZ_barre`
  (traçabilité, E25).
- **Contrôle croisé** : les colonnes de la barre sont relues par `resultats lire` ;
  l'intégrale de bande est contrôlée par la preuve du § 2.10.

### 2.6 Bande d'exclusion E26

Déclarée sur la famille des chevêtres (`exclusion_band`, demi-largeur 0,60 m). Pour
toute famille de coque, un nœud dont la distance dans le plan XY au nœud le plus
proche des chevêtres est **strictement** inférieure à 0,60 m (à 1 mm près) n'a pas de
valeur de dimensionnement ; le nu (distance 0,60) est lu. Les valeurs de la bande
restent dans la colonne « axe (comparaison) ». Les disques PAT-013 (rayon 0,60 m
autour des têtes) s'appliquent en plus.

### 2.7 Zones de lecture (D3) et conventions (D4)

- Zones d'une même famille disjointes ; contrôle générique à chaque synthèse : aucun
  nœud ni aucune extrémité d'élément dans deux sections d'une famille, sauf partage
  déclaré (`shared_rows`) ; deux lignes identiques (même lieu, même valeur) dans deux
  sections refusées sauf déclaration. Estacade :
  - pieux : tête +1,30 (**comparaison** seulement), bouchon au nu (+0,60, coupe
    interpolée), bouchon sous le nu (−0,80 ≤ z < +0,60), pieu courant (z < −0,80) ;
  - chevêtres : travée |Y| < 1,65 (station du nu intérieur) ; nu d'appui aux stations
    |Y| = 1,65 et 2,35 (nus du tube Ø 660 à ±2,00 : 1,67 et 2,33, stations du maillage
    les plus proches) ; consoles |Y| > 2,35 sans section ;
  - dalle : chapeau |X − X_file| = 0,60 ; travée courante |X − X_file| > 0,60 et
    |Y| < 1,50 ; rive |X − X_file| > 0,60 et |Y| ≥ 1,50.
- Signe : une section « travée » ne retient que le moment de travée (Code_Aster :
  MFY < 0 de la section en T, MXX < 0 de la dalle) ; « appui », « chapeau », « nu » le
  moment sur appui (> 0) ; un pieu circulaire, la résultante. Le signe opposé est
  rapporté (« non dimensionnant » s'il est inférieur à la valeur des sections qui
  retiennent ce signe, sinon retenu et déclaré).
- Feuille « Synthèse ingénieur » : convention ingénieur des CSV (N > 0 compression ;
  M > 0 = moment du signe déclaré de la section : travée ou appui ; |V|) ; intitulés
  physiques. Feuille « Torseurs » et colonnes brutes : convention Code_Aster, dite en
  tête de feuille.

### 2.8 Moment de dimensionnement sur appui (E27) — convention

Pour chaque combinaison et chaque position mobile, appui par appui (le pieu le plus
proche pour un chevêtre ou un bouchon ; la ligne de pieux la plus proche selon X pour
le chapeau) :

- M_nu = max des lignes de la section sur cet appui, signe d'appui, dans la
  référence ;
- M_enc = max des lignes d'axe (`axis_rule`) sur cet appui, même signe, dans le modèle
  auxiliaire, sous la même combinaison et la même position, FR, TEP, TEM exclus ;
- M_dim = max(M_nu ; 0,65 × M_enc), terme qui gouverne noté ;
- enveloppe sur appuis, combinaisons, positions, par état limite. Le torseur exporté
  porte M_dim, avec N et V **lus au nu dans la référence** à la ligne de M_nu, au même
  instant. M_axe (référence, mêmes lignes d'axe) : comparaison seulement.

Sections : chapeau (MXX, A2, axe X = X_file hors disques), chevêtre au nu (M_T, A1,
axe = extrémités d'élément au nœud de tête), bouchon au nu (M résultant, A3, coupe à
+0,60 de l'élément +0,50 → +0,70).

### 2.9 Bouchon au nu (E24, D6) et variante V1

- Lecture à +0,60 : aucun nœud ; interpolation linéaire entre les deux extrémités
  (`EFGE_ELNO`) de l'élément +0,50 → +0,70 de chaque pieu, cas par cas (exacte car les
  combinaisons sont linéaires), avant la résultante √(MFY² + MFZ²). Exacte pour M et V
  si l'élément ne porte ni charge transversale répartie ni ressort intermédiaire :
  vérifié par le MED des charges (aucune force transversale aux nœuds +0,50 et +0,70
  autre que celles des ressorts aux nœuds, qui sont aux extrémités) et par le maillage
  (aucun nœud entre +0,50 et +0,70).
- V1 : M_dim(V1) = max(M_nu de V1 ; 0,65 × M_enc de A3), comme pour la référence
  (A3 a déjà le tronçon indéformable). Effet rapporté sur la tête (C3 ; en V1 le
  moment au nœud +1,30 est nul par construction, U4.44.01 : le moment est lu au haut
  de la partie déformable, +0,70), sur le chevêtre (section en T) et sur le
  déplacement horizontal en tête (ELS caractéristique).

### 2.10 Preuve de D1 : équilibre d'une coupe (CTL-005 étendu)

Cas élémentaire PP. Corps libre Y < Y₀ (tablier et pieux de ce côté). Moment autour
de la ligne (Y = Y₀, Z = 1,30, plan moyen), composante X :
M_T,total(Y₀) = Σ [(y − Y₀)·F_z − (z − 1,30)·F_y] des forces extérieures du corps
libre (forces nodales du MED des charges, réactions de pointe, forces des ressorts sur
la structure), où M_T,total = Σ MFY des sept chevêtres + ∫ MYY dX sur toute la
largeur. Les nœuds de la coupe ont un bras nul en F_z. Coupes : Y₀ = 0 (mi-portée,
hyperstatique : les forces des pieux et des ressorts entrent) et Y₀ = −2,50 (console,
isostatique). Puis la part des sept sections en T (bande ±0,60) dans M_T,total.

### 2.11 Effort tranchant de la dalle (D2)

Noms de composantes : ceux du champ `EFGE_NOEU` livré (`QX`, `QY`, lus dans le MED par
le conteneur, liste du lot 49) ; vérifiés au catalogue 17.4 avant écriture. Grandeur
« V max » des familles de coque : V = √(QX² + QY²) par unité de largeur, avec N et M
concomitants, hors bandes E26 et hors disques. Une colonne V est ajoutée aux fichiers
de flexion composée de la dalle.

### 2.12 Comparaison externe et profil du chapeau

Feuille « Comparaison externe » : point, lieu, composante, famille, état limite, valeur
de la source, valeur Code_Aster, écart, attribution A à G (règle des points de
comparaison du lot 47 quater), tableau du superviseur vérifié ligne par ligne. N de la
dalle : « non comparable directement » (la source compose 65 + 0,7 × 19 à la main,
sans concomitance), ordre de grandeur seulement. Profil de MXX selon X, à Y = 0 et
±1,00, de l'axe d'une file à 1,00 m, combinaison 111 (ELU+, ELS c, ELS f), enveloppe
des positions mobiles, avec les valeurs à l'axe, à 0,30 m et au nu ; conclusion
« écart dû au lieu de lecture » ou « écart non expliqué ».

### 2.13 Intégrité des exports

Manifeste de livraison : empreinte SHA-256 de chaque fichier livré (CSV, classeur,
images, manifeste lui-même exclu) ; commande `aster-expert projet <nom> livraison
<dossier>` (dépôt) et `aster-expert projet <nom> livraison <dossier> --verifier`
(signale tout fichier modifié, absent ou ajouté depuis la livraison, code de sortie 1).

## 3. Critères de réussite (écrits avant toute exécution du lot)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Validation B des `.comm` dérivés A1, A2, A3, V1 | verdict `valide` | exacte | aucune erreur, toutes commandes confrontées |
| Exécution des modèles dérivés | jusqu'à `FIN` | exacte | statut `completed_ok` ou `completed_with_alarms` (alarmes expliquées) |
| Harnais D de A1, A2, A3, V1 : Σ charges + Σ réactions + Σ ressorts, chaque cas élémentaire | 0 | exacte | ≤ 10⁻⁶ (`controls.threshold`) rapporté à la charge |
| Harnais D : réaction verticale de chaque position mobile | égale à la référence | exacte | ≤ 10⁻⁶ relatif |
| A1 analytique : M_T à l'axe des pieux, file 4 | q·L²/12 = 133,33 kN·m | sensible à la modélisation (part de la dalle hors bande) | écart ≤ 2 % ; au-delà : écart écrit et expliqué, sinon déclaré inexpliqué |
| A2 analytique : MXX à l'axe, files 2 à 6, Y = 0 | q·L²/12 = 20,833 kN·m/m | sensible à la discrétisation | écart ≤ 2 % ; au-delà : écart écrit et expliqué |
| D1, coupe Y₀ = −2,50 sous PP : M_T,total contre l'équilibre du corps libre | égal | exacte (équilibre) | ≤ 10⁻⁶ relatif |
| D1, coupe Y₀ = 0 sous PP : M_T,total contre l'équilibre du corps libre | égal | exacte (équilibre) | ≤ 10⁻⁶ relatif |
| Section en T, valeur de la barre seule relue par `resultats lire` | égale | exacte | ≤ 10⁻⁹ rapporté au torseur |
| Interpolation à +0,60 | aucune force transversale aux nœuds +0,50 et +0,70 hors ressorts ; aucun nœud intérieur | exacte | sinon signalé (pas de maillage nouveau) |
| V1 : M_dim du bouchon (E27), ELU, référence contre V1 | — | décision | variation > 5 % : valeur de dimensionnement = enveloppe des deux, écart écrit dans la synthèse ; ≤ 5 % : la référence suffit |
| D3 : zones d'une famille | disjointes | exacte | aucun nœud ni extrémité d'élément commun non déclaré ; aucune ligne identique entre deux sections |
| D5 : format d'affichage de chaque cellule de valeur du classeur | celui de `config/arrondis.yaml` pour son unité | exacte | aucune cellule numérique de valeur au format « General » |
| Intégrité : un fichier livré modifié après dépôt | signalé | exacte | `--verifier` sort en code 1 et le nomme |
| `.comm` de production, niveaux des paquets (dalle E, estacade D, quai D) | inchangés | exacte | identiques |

Toute autre issue est un échec, rapporté tel quel.

## 4. Résultats

(Rédigés après les exécutions et les lectures ; les sections 1 à 3 ne sont pas modifiées.)

### 4.1 Déroulement

- `env-check` (profil **vm**, 10 vérifications) et `mcp-check` (10 outils, serveur neuf)
  réussis en tête de lot ; branche `lot-49ter` créée depuis `main` (lot 49 bis fusionné).
- Critères (sections 1 à 3) commités avant toute exécution : `58a3522`.
- Aucune question posée à MM : E24 à E27 étaient dans la consigne. Une interruption par
  la limite d'usage de claude.ai, reprise sans perte.
- Exécutions (toutes `completed_ok` ou `completed_with_alarms`, aucune en échec) :

| Exécution | Objet | Durée | Statut |
| --- | --- | --- | --- |
| `20261009T131936-931302c8` | A1 (post-traitement dérivé) | 2 274,9 s | completed_ok |
| `20261009T135809-6fafb336` | A2 | 2 450,3 s | completed_ok |
| `20261009T143950-e69a74f4` | A3 | 2 397,4 s | completed_ok |
| `20261009T152011-d04d9ab3` | V1 | 1 820,5 s | completed_ok |
| `20261009T152115-c0cf7cc8`, `20261009T152242-59583226` | cas analytiques A1, A2 (passe retenue ; deux passes antérieures de lecture : `133533`, `133740`, `134013`, `134140`) | 86 s, 90 s | completed_with_alarms (`<A> <POSTRELE_70>`) |

- Alarme `<A> <POSTRELE_70>` des cas analytiques : DIAG-012 consulté avant toute autre
  hypothèse ; `EFGE_NOEU` extrait dans le repère local des éléments, confondu ici avec le
  repère global (ANGL_REP = (0, 0), normale +Z ; CA-058). Expliquée, non neutralisée.
- Validation de niveau B : les `.comm` dérivés A1 (479/479), A2, A3, V1 (480/480) et de
  validation (277/277, 278/278) `valide`. Une première version des `.comm` de validation
  a été refusée au niveau B (`POST_RELEVE_T` : « At least one argument of ('GROUP_NO',
  'NOEUD') must be defined ») et corrigée avant toute exécution.
- Écart constaté au fil du lot dans le script du conteneur (`scripts/livrables_med.py`) :
  il n'extrayait que les cas cités par une combinaison ; un modèle dérivé n'en déclare
  aucune. Il extrait désormais tous les cas déclarés (sans effet sur la référence, dont
  toutes les positions extraites sont dans ses combinaisons).

### 4.2 Décisions E24 à E27 et constat sur E19

- `aster-expert fiche enregistrer estacade_pieux_01
  projets/estacade_pieux_01/donnees/sources/enregistrement_E24_E27_lot49ter.md` : E24,
  E25, E26, E27 insérées (origine `arbitrage_mm`, texte vérifié à l'identique dans
  `arbitrage_estacade_pieux_01_lot49ter.md`) ; rejeu `scripts/fiche_lot47.py` identique
  à l'octet ; la fiche compte 47 entrées, 27 décisions de MM.
- Constat sur E19 : `scripts/constat_e19_lot49ter.py` met à jour la note des trois lignes
  C6 de REF-015 (« C, chevêtre de 0,80 m dans le modèle source -- probable, appuyé par le
  texte de la source (§20.5.1) » ; « A, la source publie la barre ») ; statut, valeurs et
  verdicts inchangés ; même attribution dans la feuille « Comparaison externe ».
  Référence E1 à E23 inchangée.

### 4.3 Modèles auxiliaires A1 à A3 et variante V1

| Modèle | Conditions ajoutées (tronc commun, `derived_models`) | Harnais D : cas élémentaires | Positions (FZ contre la référence) | Verdict |
| --- | --- | --- | --- | --- |
| A1 | DDL_IMPO DX…DRZ = 0 sur TETES | 1,5·10⁻¹¹ | 2,3·10⁻¹⁰ (118) | RÉUSSI |
| A2 | DDL_IMPO DZ, DRY = 0 sur les nœuds de CHEVETRES | 9,3·10⁻¹¹ | 2,5·10⁻¹⁰ (118) | RÉUSSI |
| A3 | LIAISON_SOLIDE sur PIEU_T1 ∩ chaque pieu ; DDL_IMPO DRX, DRY, DRZ = 0 sur TETES | 3,7·10⁻¹¹ | 1,6·10⁻¹⁰ (118) | RÉUSSI |
| V1 | LIAISON_SOLIDE sur PIEU_T1 ∩ chaque pieu | 8,2·10⁻¹¹ | 1,2·10⁻¹⁰ (118) | RÉUSSI |

Les 124 positions de LM2 (L2A, L2B) n'entrent dans aucune combinaison de la référence :
elles n'y sont pas extraites, la comparaison des positions porte sur les 118 de TS.
Aucun pivot nul en A3 (DIAG-001 écarté) ; aucune alarme dans les quatre exécutions.

**Fait (lecture de A3)** : sous charges verticales seules (FR, TEP, TEM exclus par E27),
avec les rotations de tête bloquées, les pieux ne reçoivent aucune charge transversale :
leurs moments sont nuls (N seul non nul, −179 kN sous PP au pieu F7_YP). M_encastrement
du bouchon vaut donc 0 et M_dim = M_nu. *Déduction* : le moment du bouchon de la
référence vient de la rotation du tablier imposée à la tête (effet de portique) et des
actions horizontales, que A3 supprime par construction ; l'extension d'E27 au bouchon ne
change rien avec la définition décidée. **Point à MM** : inclure FR et TE dans A3
donnerait le moment de pieu à tête encastrée sous déplacement latéral.

### 4.4 Validation analytique (critère § 3 : 2 %)

`references/validation_auxiliaires_lot49ter.json`.

| Cas | Grandeur | Attendu | Obtenu | Écart | Verdict |
| --- | --- | --- | --- | --- | --- |
| A2 | MXX à l'axe, files 2 à 6, Y = 0 | 20,833 kN·m/m | 20,576 kN·m/m | −1,24 % | **RÉUSSI** |
| A1 | section en T à l'axe des pieux, file 4 (Y = ±2,00, élément côté travée) | 133,33 kN·m | 122,48 kN·m (barre 114,18 + bande 8,30) | −8,14 % | **ÉCART > 2 %** |
| A1 (information) | coupe complète à Y = ±2,00 (7 chevêtres + toute la dalle) | 133,33 | 127,34 | −4,5 % | — |
| A1 (information) | statique de la travée sur toute la largeur, M_appui − M_mi-portée | q·L²/8 = 200,0 | 197,83 | −1,08 % | — |

Lecture de l'écart d'A1 (*déductions*, établies par les deux lignes d'information) :
(1) la dalle hors de la bande de ±0,60 m porte 4,86 kN·m de la coupe d'appui (3,7 %) ;
(2) la ligne Y = ±2,00 n'est encastrée qu'aux sept têtes, pas sur sa longueur : la
dalle tourne entre les têtes, l'encastrement de la travée de 4 m est imparfait et le
moment se reporte en travée (coupe complète −4,5 %, mi-portée 70,5 kN·m au lieu de
66,7), alors que la statique de la travée tient à 1,1 % (lecture nodale moyennée de la
dalle). L'écart est donc expliqué et propre au modèle A1 tel que E27 le définit ; le
seuil n'est pas relâché : **critère de 2 % non tenu pour A1**.

### 4.5 D1 — Chevêtres en section en T (E25)

Avant (lot 49 bis, barre seule, ELU) : travée MFY min −443,1 kN·m ; nu MFY max 37,5 ;
|VZ| max 179,9 kN (les deux sections lisaient Y = 1,65). Après (section en T) :

| Section | Grandeur (ELU) | Valeur | Lieu, combinaison |
| --- | --- | --- | --- |
| travée | moment de travée max | 473,2 kN·m | CHEV_2, Y = −0,20 ; 112 ELU+ @ TSB_M20 |
| travée | effort tranchant max | 606,1 kN | CHEV_2, Y = 1,60 |
| nu | moment sur appui max (M_nu) | 73,2 kN·m | Y = −2,35 ; 112 ELU+ @ TSB_M20 |
| nu | effort tranchant max | 621,3 kN | Y = 1,65 |
| nu | M_dim (E27) = 0,65 × M_enc(A1) | 314,2 kN·m | appui (5,60 ; 2,00) ; 109 ELU+ @ TSB_M20 |

Méthode d'intégration (§ 2.5) : bande |X − X_file| ≤ 0,60 m, 25 nœuds de dalle de même
Y, trapèzes, `EFGE_NOEU` (NYY, MYY, QY) ajoutés à `EFGE_ELNO` (N, MFY, VZ), cas par cas ;
barre seule en colonnes `*_barre`.

**Preuve (CTL-005 étendu, `equilibre_coupes.json`)** : sous PP, moment total de la coupe
(sept barres + dalle sur toute la largeur) contre l'équilibre du corps libre Y < Y₀ :

| Coupe | Moment total | Équilibre | Écart | Part des sections en T |
| --- | --- | --- | --- | --- |
| Y₀ = 0 (mi-portée) | −712,330 kN·m | −712,330 kN·m | 3,1·10⁻¹⁰ | 81,8 % |
| Y₀ = −2,50 (console) | 62,625 kN·m | 62,625 kN·m | 3,8·10⁻¹⁰ | 112 % |

Deux précisions de lecture, apportées pendant la mise au point et conformes au contrôle
du total du lot 47 bis (§ 1.5) : la barre est lue au nœud de la coupe en moyenne des deux
extrémités d'élément (le saut entre elles est l'interaction nodale barre–dalle, CA-058 ;
sans cette moyenne l'écart en console était de 6,3 %) ; les moments nodaux du vecteur de
charge consistant (charge répartie des barres, 39,375 N·m = 7 × q·h²/12 en bout de
console) ne sont pas comptés. Le critère (10⁻⁶) n'a pas été changé. Comparaison à la
source : V ELU au nu −4,9 % (621,3 / 653) ; M sur appui : M_axe 177,7 (+0,4 %), M_nu
73,2, M_dim 314,2 ; M en travée +16,0 % (473,2 / 408) — § 4.11.

### 4.6 D2 — Effort tranchant de la dalle

Composantes : U2.01.05, § « SIEF_R » (efforts de coque NXX, NYY, NXY, MXX, MYY, MXY, QX,
QY), et liste lue dans le MED écrit par Code_Aster 17.4. Grandeur « effort tranchant max
(résultante) » V = √(QX² + QY²) des trois sections de dalle, hors bandes E26 et disques,
avec N et M concomitants ; colonne « V résultant concomitant » ajoutée aux six fichiers
de flexion composée de la dalle. ELU : courante 282,1 kN/m, chapeau 265,9, rive 269,1
(tous 112 ELU+ @ TSB_M23). Rive sous la combinaison 100 des livrables : 62,9 kN/m (la
combinaison 100 n'a pas l'essieu d'E18, calculé à part au lot 47 bis : 222,1 kN/m hors
disques). Le 321 kN/m du tableau du superviseur est très probablement C12 « courant »
de la source (320) ; C12 rive de la source vaut 568 kN/m.

### 4.7 D3 — Zones disjointes et signe de section

Zones (§ 2.7) écrites dans `engineering_summary` ; contrôle à chaque synthèse :
`disjoint_zones` (aucune ligne, aucun nœud commun) et `identical_lines`. Estacade :
0 ligne et 0 nœud communs sur les 6 paires des pieux, la paire des chevêtres et les
3 paires de la dalle. Avant : `dalle_travee_MXX.csv` portait un moment de chapeau
(86,3 kN·m/m à X = 29,95) ; après, ce signe est rapporté « moment de signe opposé (MXX) »,
80,9, non dimensionnant (inférieur au chapeau, 90,2). Signe opposé retenu seulement s'il
dimensionne (aucun cas à l'estacade). Dalle : le centre, point de contrôle pris dans la
travée, partage déclaré (`shared_rows`).

### 4.8 D4, D5 — Convention et arrondis du classeur

« Synthèse ingénieur » en convention ingénieur (compression > 0, moment dans le sens de
la section, |V|), intitulés physiques (« compression max », « traction max », « moment de
travée max », « moment sur appui max », « moment max, fibre … tendue » quand les deux
signes sont retenus) ; « Torseurs » en convention Code_Aster ; l'en-tête de chaque feuille
le dit. Toute cellule numérique a un format : unité de `config/arrondis.yaml`, ou
`0.00E+00` pour un écart relatif sans unité, `0` pour un entier. Relecture du classeur de
l'estacade : 0 cellule numérique au format « Standard » sur 11 feuilles ; test
`test_the_workbook_puts_the_engineering_sheets_first` (number_format, convention).

### 4.9 D6 — Bouchon au nu (E24, E27) et variante V1

Lecture à +0,60 : aucun nœud ; 14 lignes interpolées dans l'élément +0,50 → +0,70.
Contrôle : force transversale maximale aux 28 nœuds d'extrémité, tous cas élémentaires :
3,2·10⁻³⁰ N (≤ 10⁻⁶ N) ; aucun nœud intérieur : **interpolation exacte**.

| État | M_nu référence | 0,65 × M_enc (A3) | M_dim référence | M_nu V1 | Variation | M_dim retenu |
| --- | --- | --- | --- | --- | --- | --- |
| ELU | 258,9 kN·m | 0,0 | 258,9 | 338,5 | +30,8 % | **338,5 (enveloppe)** |
| ELS c | 175,6 | 0,0 | 175,6 | 229,5 | +30,7 % | **229,5** |
| ELS f | 119,5 | 0,0 | 119,5 | 157,9 | +32,1 % | **157,9** |

Critère (§ 3, écrit avant) : variation > 5 % → **valeur de dimensionnement = enveloppe des
deux** ; torseur lu dans V1 (F7_YP, 111 ELU+ @ TSB_P25 : N = 676,9 kN, V = 271,9 kN).
Effets de V1 (`references/variante_v1_lot49ter.json`) :

| Grandeur (ELU sauf mention) | Référence | V1 | Variation |
| --- | --- | --- | --- |
| tête, moment au haut de la partie déformable (+0,70) | 283,4 kN·m | 365,7 | +29,1 % |
| tête +1,30 (C3) | 435,5 | 0 par construction (partie rigide, U4.44.01) | — |
| chevêtre, moment de travée (section en T) | 473,2 | 471,4 | −0,4 % |
| chevêtre, M au nu | 73,2 | 72,9 | −0,3 % |
| chevêtre, V au nu | 621,3 | 624,7 | +0,6 % |
| déplacement horizontal en tête, ELS c, toutes têtes | 4,21 mm | 4,01 mm | −4,6 % |

Limite déclarée : la partie rigide va de +0,70 (nœud) à +1,30 ; 0,10 m de l'élément
+0,50 → +0,70 reste déformable.

### 4.10 E27 — chevêtre et chapeau

| Section | État | M_nu | M_enc | 0,65 × M_enc | M_dim | Terme qui gouverne | M_axe |
| --- | --- | --- | --- | --- | --- | --- | --- |
| chevêtre (A1) | ELU | 62,7 | 483,4 | 314,2 | **314,2** | 0,65·M_enc | 158,2 |
| | ELS c | 44,9 | 334,4 | 217,3 | **217,3** | 0,65·M_enc | 112,7 |
| | ELS f | 38,1 | 227,8 | 148,1 | **148,1** | 0,65·M_enc | 92,8 |
| chapeau (A2) | ELU | 90,2 | 38,7 | 25,1 | **90,2** | M_nu | 75,4 |
| | ELS c | 60,1 | 27,9 | 18,1 | **60,1** | M_nu | 51,5 |
| | ELS f | 41,3 | 24,1 | 15,7 | **41,3** | M_nu | 38,0 |

(kN·m, kN·m/m pour le chapeau ; M_nu et M_axe à l'instant et à l'appui qui gouvernent
M_dim ; leurs maxima propres, sur tous les appuis : chevêtre 73,2 et 177,7, chapeau 90,2
et 133,0 à l'ELU.)

### 4.11 Comparaison à la source

Feuille « Comparaison externe » (`comparaison_externe.json`, copie versionnée
`references/comparaison_externe_lot49ter.json`), attribution A à G (règle du lot 47
quater), tableau du superviseur vérifié ligne par ligne :

| Point | Grandeur | ELU source | ELU Code_Aster | Écart | Attribution |
| --- | --- | --- | --- | --- | --- |
| pointes | réaction DZ | 1 102 | 1 075,4 | −2,4 % | aucun écart |
| C2 | N tête (compression) | 1 048 | 1 022,6 | −2,4 % | aucun écart |
| C3 | M tête +1,30 | 449 | 435,5 | −3,0 % | aucun écart (ELS c −5,7 % : G) |
| bouchon | M_dim au nu +0,60 | 450 (lu à +1,30) | 338,5 | −24,8 % | A, lieu (E24), non comparable directement |
| C4 | V bouchon | 253 | 259,4 | +2,5 % | aucun écart |
| C6 | M travée, section en T | 408 | 473,2 | +16,0 % | C (0,80 m probable, §20.5.1) et A (la source publie la barre) |
| C7 | M_axe / M_nu / M_dim | 177 (superviseur : 178) | 177,7 / 73,2 / 314,2 | +0,4 / −58,7 / +77,5 % | axe : aucun écart ; nu : A ; M_dim : C (règle E27) |
| C8 | V au nu, section en T | 653 (superviseur : 654) | 621,3 | −4,9 % | aucun écart |
| C10 | MXX travée | 198 | 192,9 | −2,6 % | aucun écart |
| C9 | chapeau M_dim / M_nu / M_axe | 174 (superviseur 174/119/80, source 174/118/79) | 90,2 / 90,2 / 133,0 | −48 / −48 / −24 % | A, lieu de lecture (profil) ; E, maillage |
| C12 | V dalle hors bandes et disques | 320 | 282,1 | −11,8 % | E et A |
| C12 rive | V rive, combinaison 100 | 321 (superviseur) / 568 (source) | 62,9 | — | B, essieu d'E18 absent de la combinaison 100 livrée |
| C11 | N de la dalle | 65 + 0,7 × 19 = 78,3 | ordre de grandeur 19,7 / 62,9 kN/m (lot 47 bis) | — | non comparable directement |

ELS f et ELS c dans la feuille ; la tête (+1,30) n'est plus exportée, elle reste en
comparaison.

**Profil du chapeau** (`comparaison/profil_chapeau.csv` et `.png`, file X = 30,60, côté
travée, combinaison 111, enveloppe des positions de TS), ELU, kN·m/m :

| Ligne | Axe (nœud partagé) | 0,05 m | 0,30 m | Nu (0,60 m) |
| --- | --- | --- | --- | --- |
| Y = −1,00 | 74,2 | 130,5 | 97,8 | 69,0 |
| Y = 0 | 70,5 | 124,6 | 94,4 | 65,9 |
| Y = +1,00 | 79,3 | 140,9 | 105,3 | 72,3 |

MXX culmine au premier nœud à côté de l'axe ; la valeur au nœud d'axe, partagé avec le
chevêtre, est abaissée par l'interaction nodale (CA-058) ; le moment est divisé par 2
environ de 0,05 m au nu. La source (174) est voisine du maximum lu près de l'axe et des
têtes (156,2 au lot 47 bis, à 5 cm de l'axe de la file 7, sensible au maillage : E).
**Conclusion : écart dû au lieu de lecture.**

### 4.12 Intégrité des exports et connaissances

- `aster-expert projet estacade_pieux_01 livraison --dossier <d>` : 18 fichiers copiés
  (classeur, 10 CSV, 5 diagrammes, profil CSV et PNG), `manifeste_livraison.json`
  (SHA-256, octets, source, commit) ; `--verifier` : INTACT ; un fichier modifié, absent ou
  ajouté est nommé et la commande sort en code 1 (test
  `test_a_file_modified_after_delivery_is_reported`).
- PAT-014 « poutre partageant ses nœuds avec une plaque : section en T » (niveau D,
  preuve : équilibre des coupes, D1) ; PAT-015 « lecture au nu » (bande ±b/2 et disques,
  PAT-013, E26) ; CTL-015 « chaîne de livraison » (D3, D4, D5, tests du tronc commun).
  Statut `observé` (un seul projet).

## 5. Verdict

| Critère (§ 3) | Résultat | Verdict |
| --- | --- | --- |
| Validation B des `.comm` dérivés | 479/479, 480/480 ×3 | RÉUSSI |
| Exécution des modèles dérivés | 4 × completed_ok | RÉUSSI |
| Harnais D, cas élémentaires | ≤ 9,3·10⁻¹¹ | RÉUSSI |
| Harnais D, positions mobiles | ≤ 2,5·10⁻¹⁰ | RÉUSSI |
| A1 analytique | −8,14 % | **ÉCHEC au seuil de 2 % (écart expliqué)** |
| A2 analytique | −1,24 % | RÉUSSI |
| D1, coupe Y₀ = −2,50 | 3,8·10⁻¹⁰ | RÉUSSI |
| D1, coupe Y₀ = 0 | 3,1·10⁻¹⁰ | RÉUSSI |
| Barre seule relue par `resultats lire` | 1,5·10⁻¹⁶ (1 689 valeurs) | RÉUSSI |
| Interpolation à +0,60 | 3,2·10⁻³⁰ N, aucun nœud intérieur | exacte |
| V1 | +30,8 % > 5 % | enveloppe retenue (M_dim bouchon ELU 338,5 kN·m) |
| D3 zones | 0 recouvrement, 0 ligne identique | RÉUSSI |
| D5 formats | 0 cellule au format « Standard » | RÉUSSI |
| Intégrité | modification signalée, code 1 | RÉUSSI (test) |
| Niveaux des paquets, `.comm` de production | dalle E, estacade D conservés ; quai non régénéré | RÉUSSI |

## 6. Limites

- A1 ne retrouve pas q·L²/12 à 2 % (encastrement ponctuel aux têtes, part de la dalle hors
  bande) : M_enc du chevêtre est celui du modèle défini par E27, pas celui d'une poutre
  bi-encastrée idéale.
- A3 donne M_enc = 0 pour le bouchon (charges verticales seules, rotations de tête
  bloquées) : l'extension d'E27 au bouchon est sans effet tant que FR et TE sont exclus.
- Tronçon indéformable de V1 et A3 depuis +0,70 (aucun nœud à +0,60, pas de maillage
  nouveau).
- L'essieu de trottoir d'E18 n'est pas un cas des combinaisons livrées (C12 rive non
  comparable).
- Les diagrammes des chevêtres titrent MFY et VZ : ce sont les totaux de la section en T
  (dit dans la réserve de la famille).
- Le quai n'est pas régénéré ; ses sections ne déclarent ni zone ni signe.
