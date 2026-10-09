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
