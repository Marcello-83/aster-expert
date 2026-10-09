# Essais du lot 49 bis — synthèse ingénieur (familles d'éléments, torseurs concomitants, états limites, diagrammes)

Consigne : `docs/lots/lot49bis_consigne.md`. Profil **vm**. Code_Aster 17.4.0 (aucune
exécution nouvelle : les données lues sont celles des exécutions de post-traitement du
lot 49). Ce rapport suit `docs/modele_rapport_essai.md` : les sections 1 à 3 (objet,
méthode, critères) sont écrites et commitées **avant** la première lecture de la
synthèse sur les données réelles des trois projets ; elles ne sont pas modifiées ensuite
(une erreur s'y corrige dans une section datée « Correction du critère »).

## 1. Objet

1. Une couche de **synthèse ingénieur générique**, déclarée par projet dans
   `projet.yaml` (section `engineering_summary`) : familles d'éléments d'ouvrage,
   sections de dimensionnement avec leur règle de lecture, états limites tirés des
   familles de combinaisons, critères de service, en-tête des fichiers de flexion
   composée.
2. Pour chaque famille × section × état limite, les **torseurs concomitants** (N, V, M
   au même lieu, pour la même combinaison et la même position de charge mobile).
3. L'export pour le logiciel de flexion composée de MM, un fichier par section et par
   plan de flexion, conventions converties (N > 0 en compression, M > 0 comprime la
   fibre supérieure).
4. Un classeur restructuré (Synthèse ingénieur, Vérifications de service, Torseurs,
   détails en format large, feuilles du lot 49 conservées après) et des diagrammes 2D.
5. Des images ParaView en unités d'affichage, titrées, en trois vues, avec des flèches
   de charges regroupées.

Niveau visé : **aucun niveau nouveau**. La synthèse est une lecture des livrables du
lot 49 ; les niveaux des paquets (quai D, dalle E, estacade D) doivent être conservés,
aucun `.comm` de production n'est modifié, aucune exécution Code_Aster n'est lancée.

## 2. Méthode (écrite avant la lecture des données réelles)

### 2.1 Combinaisons et concomitance

**Fait établi dans la documentation 17.4 (niveau A)** : R3.08.01, § « Le tenseur des
contraintes » : N = ∫ σxx dS, MFY = ∫ z σxx dS, MFZ = −∫ y σxx dS (N > 0 en traction).
U4.42.01, § ORIENTATION : sans orientation donnée, le repère local d'une SEG2 suit la
maille (x_l le long du segment, rotation γ nulle). CA-045 : MXX > 0 tend la face
supérieure d'une coque DKT.

Une combinaison est la superposition des cas élémentaires et des positions mobiles
livrés (`cas/<cas>`, `pos/<position>` des tableaux du lot 49), avec les coefficients
déclarés : c'est l'arithmétique des combinaisons du lot 49 et de `aster-expert
resultats lire` (`<combinaison>@<position>`). Aucune grandeur ne manque dans les MED du
lot 49 : aucun recalcul n'est nécessaire.

Pour chaque état limite (familles de combinaisons déclarées) et chaque ligne d'une
famille (extrémité d'élément, nœud), le max et le min de chaque composante (et de
√(MFY² + MFZ²), √(VY² + VZ²) pour une section circulaire) sont gardés avec la
combinaison et la position qui les donnent. La valeur de dimensionnement d'une section
est l'extremum sur ses lignes ; son torseur est le vecteur complet en cette ligne, pour
cette combinaison et cette position.

### 2.2 Valeurs non significatives

Une coque exclut de sa valeur de dimensionnement les nœuds des disques d'exclusion
(PAT-013, `deliverables.exclusion_disks`) et les nœuds partagés avec une poutre
(CA-058, `shared_with` de la section). L'extremum lu dans ces zones, s'il dépasse la
valeur retenue, est rapporté à côté, marqué « non significative » avec son motif.

### 2.3 Conversion pour le logiciel de flexion composée

N(logiciel) = −N(Code_Aster). M(logiciel) = −MFY pour une fibre supérieure en +z_l,
+MFY en −z_l, +MFZ en +y_l, −MFZ en −y_l, −MXX (ou −MYY) pour la face de la normale
d'une coque. Section circulaire : √(MFY² + MFZ²) ≥ 0, avec un avertissement.

### 2.4 Critères de service (E21, E22, décisions de MM du lot 49 bis)

Déplacement horizontal en tête √(DX² + DY²) sous ELS caractéristique, limite
2,85 / 400 ; flèche relative aux appuis (corde des appuis retranchée ; console :
déplacement de l'appui retranché) sous ELS caractéristique hors PP, G2, TE+ et TE−.

## 3. Critères de réussite (écrits avant la lecture des données réelles)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Torseur de tête de pieu, ELU fondamental, estacade : M résultant max | 435,49 kN·m (lot 47 bis, § 8 a), au nœud de tête +1,30 de PIEU_F7_YP, combinaison 111 ELU+, position TSB_P25 | exacte (même superposition des mêmes tableaux) | écart relatif ≤ 10⁻⁶ sur la valeur imprimée au lot 47 bis à 0,01 kN·m près : |M − 435,49| ≤ 0,005 kN·m ; lieu, combinaison et position identiques |
| Fichier de flexion composée de la tête de pieu, ligne ELU « M max » | M = 435,5 kN·m ; N = −N(Code_Aster) du même torseur | exacte | égalité à 0,1 kN·m (arrondi du fichier) |
| Chaque valeur de chaque torseur de la synthèse, relue par `resultats lire` (`<combinaison>@<position>` ou combinaison du lot 49, au même nœud et à la même extrémité) | égale | exacte | écart rapporté à la plus grande composante du torseur ≤ 10⁻⁹ |
| Combinaisons recalculées par superposition, aux lignes de leur maximum | égales aux combinaisons du lot 49 (`comb/<i>/max`) | exacte | ≤ 10⁻⁹ (même contrôle croisé) |
| Équilibre par état limite : Σ charges + Σ réactions + Σ ressorts, chaque combinaison, chaque position mobile | 0 | exacte | ≤ seuil du projet (`controls.threshold`, 10⁻⁶) rapporté à la plus grande composante de la charge |
| Grille des flèches de charges : Σ des flèches d'un cas | Σ des forces nodales du cas | exacte | ≤ 10⁻⁹ relatif |
| `.comm` de production, niveaux des paquets | inchangés (dalle E, quai D, estacade D) | exacte | identiques |
| Classeur relu | valeurs égales à leur source du paquet ; Arial 10 ; en-têtes gris D9D9D9 ; en-têtes figés ; valeur non significative grisée avec son motif | exacte | aucune exception |

Toute autre issue est un échec, rapporté tel quel.

## 4. Résultats

(Rédigés après les lectures ; les sections 1 à 3 ne sont pas modifiées.)

### 4.1 Déroulement

- `env-check` (profil **vm**, 10 vérifications) et `mcp-check` (10 outils, serveur neuf)
  réussis en tête de lot ; branche `lot-49bis` créée depuis `main` (lot 49 fusionné).
- Trois questions posées à MM (h de h/400, portées de L/400, matériaux et sections des
  fichiers de flexion composée) ; réponses recopiées à l'identique
  (`projets/estacade_pieux_01/donnees/sources/arbitrage_estacade_pieux_01_lot49bis.md`)
  et enregistrées par `aster-expert fiche enregistrer` (E21, E22, E23).
- Critères (sections 1 à 3) commités avant la première lecture : `0c4a994`.
- Une interruption de la session Claude Code, alors que deux traitements lourds tournaient
  en parallèle (rendu ParaView de l'estacade, synthèse du quai) ; aucune trace d'arrêt pour
  manque de mémoire dans le journal du noyau lisible ; reprise sur consigne de MM, les
  traitements relancés l'un après l'autre (rendu de l'estacade : 2 min 34 s, mémoire
  résidente maximale 5,0 Go). Aucun fichier perdu.
- Aucune exécution Code_Aster, aucun `.comm` de production ni MED modifié.

### 4.2 Section `engineering_summary` (schéma `aster_expert.projet.declaration`)

Nom : `engineering_summary`, parce que `synthesis` est déjà l'étape `synthese` du quai
(lots 35 à 37) et que les clés de `projet.yaml` sont anglaises. Contenu, validé par le
schéma (refus lisible sinon) :

| Clé | Contenu | Règle du schéma |
| --- | --- | --- |
| `limit_states` | état limite → familles de combinaisons (`family` des combinaisons des livrables) | les cinq états (ELU fondamental, ELU accidentel, ELS caractéristique, fréquent, quasi permanent) sont déclarés ou dans `absent_limit_states` avec un motif écrit |
| `cracking` | état de la maîtrise de la fissuration (`ELSfiss`) et sa source | défaut : ELS quasi permanent (EC2, 7.3.1) ; doit être un état déclaré |
| `families` | nom métier, type (`poutre`, `coque`, `discret`, `appui`), champ livré, groupes, motif des membres, grandeurs, section circulaire, moments et tranchants de dimensionnement, axe des diagrammes, réserve | champ admis selon le type ; une poutre fléchie déclare ses moments ou `circular` |
| `sections` | nom (fichier d'export), libellé, famille, règle de lecture (`node_group`, `groups`, `box` avec axes en valeur absolue, `near` : à / dans / au-delà d'une distance des nœuds d'un groupe, `station` : coordonnée de maillage la plus proche), justification d'une ligne, `shared_with`, `exclude_singular`, réserve, `bending_export` ou `not_exported` (motif) | une section sans export porte son motif |
| `service_criteria` | déplacement ou flèche relative (portées entre appuis, consoles), état limite, cas exclus, L/ratio, portée du verdict, source | sinon `no_service_criteria` avec motif |
| `cuts` | coupes de coques pour les diagrammes | famille déclarée |

Sections de dimensionnement (justification d'une ligne dans `projet.yaml`) :

| Projet | Section | Règle de lecture | Export |
| --- | --- | --- | --- |
| estacade | tête de pieu | extrémités au nœud `TETES` (+1,30) | bouchon, carré équivalent 0,52 (E23) |
| estacade | bouchon | Z ∈ [−0,80 ; +0,70] (E14) | idem |
| estacade | pieu courant | Z ∈ [−13,00 ; −0,80] | non : tube acier (E23) |
| estacade | chevêtre en travée | \|Y\| ≤ 1,67 (axe des pieux ±2,00, tube Ø 660, annexe B1) | 1,20 × 0,90, MFY, fibre +z_l |
| estacade | chevêtre au nu de l'appui | station \|Y\| la plus proche de 1,67 (lue : 1,650) | idem |
| estacade | dalle en chapeau | \|X − X_file\| = 0,60 (nu du chevêtre de 1,20 m) | bande de 1,00 m × 0,40, MXX et MYY |
| estacade | dalle en travée | \|X − X_file\| > 0,60 | idem |
| estacade | dalle en rive | \|Y\| ≥ 1,50 (trottoirs) | idem |
| estacade | ressorts, pointes | tous les ressorts ; `PIEDS` | non |
| quai | poutre de couronnement : bollard, mi-travée, courante | station X = 0 ; \|X\| = 1,30 ; toute la poutre | 2,50 × 1,40 (données), MFY fibre +z_l ; MFZ fibre +y_l, section tournée |
| quai | tirants, palplanches, tubes, ressorts, appuis | tout le groupe | non : acier, ou sans section de béton armé |
| dalle | dalle, toute la travée ; centre | toute la dalle ; `CENTRE` | bande de 1,00 m × 0,30 (données), MXX et MYY |
| dalle | appuis | `APPUIS` | non |

États limites : estacade ELU (ELU+ et ELU−), ELS car. (ELS_c), ELS fréq. (ELS_f), ELU
accidentel et ELS QP absents (E11) ; fissuration ELS fréquent (E23, §13.7.2). Quai : les
cinq ; fissuration ELS QP (D21). Dalle : quatre, ELU accidentel absent ; fissuration ELS
QP (point 14).

### 4.3 Torseurs concomitants et critère F7_YP

Méthode : § 2.1. Exécutions : sous-étape `ingenieur` (estacade 31 s, quai 4 s, dalle
1 s). Résultats :

| Projet | Familles | Sections | Torseurs | Non significatifs | Fichiers de flexion composée | Contrôle croisé (valeurs, écart max) |
| --- | --- | --- | --- | --- | --- | --- |
| estacade | 5 | 10 | 183 | 9 | 10 | 1 314, 4,7·10⁻¹⁷ |
| quai | 6 | 8 | 220 | 10 | 6 | 1 250, 0 |
| dalle | 2 | 3 | 40 | 0 | 4 | 280, 0 |

Critère F7_YP : torseur de tête de pieu, ELU fondamental, M résultant max =
**435,494 kN·m** au nœud de tête (Z = +1,30) de **PIEU_F7_YP**, combinaison **111 ELU+**,
position **TSB_P25** ; concomitants N = −651,0 kN (compression, convention Code_Aster),
V résultant = 262,5 kN (VY = −260,5, VZ = 32,2), MFY = −59,2, MFZ = −431,5 kN·m. Ligne
ELU « M max » du fichier `tete_de_pieu.csv` : N = 651,0 kN (compression positive),
M = 435,5 kN·m. Test : `tests/unit/test_synthese_ingenieur.py::test_the_pile_head_of_f7_yp_finds_the_moment_of_lot_47bis`.

Exemple complet demandé, `flexion_composee/bouchon.csv` de l'estacade (colonnes de repère
abrégées ici) :

```
Section de dimensionnement;bouchon (+0,70 à −0,80);bouchon
Projet;estacade_pieux_01;
Plan de flexion;flexion déviée : moment résultant √(MFY² + MFZ²);√(MFY² + MFZ²)
Type de section;circulaire (bouchon béton Ø 0,622 m) saisie en carré équivalent;
h (m);0,52;E23 : carré équivalent 0,52 × 0,52 (§20.4.1)
b (m);0,52;E23 : carré équivalent 0,52 × 0,52 (§20.4.1)
ds (m);0,090;E23 : ds = 0,09 m (d = 0,43, §20.4.1)
di (m);0,090;E23 : di = 0,09 m (§20.4.1)
Classe de béton;C35/45;E23 (§13.7.3, §19.1)
Acier;Fe E500 classe B, diagramme à branche inclinée;E23 (§13.7.4)
Classe d'exposition;XS3;E23 (§13.7.1)
cnom (mm);55;E23 (§13.7.5)
Équivalence;section circulaire du bouchon Ø 0,622 m saisie en carré de 0,52 × 0,52 m de même module d'inertie (π·D³/32 = a³/6), §20.4.1 de la source (E23);
Convention N;N > 0 en compression : N = −N de Code_Aster (Code_Aster : N > 0 en traction, R3.08.01);
Convention M;M = √(MFY² + MFZ²) ≥ 0 (section circulaire : pas de fibre supérieure propre);
Avertissement;"section circulaire en flexion déviée : le moment résultant est exporté ; le logiciel traite une flexion plane ; « M min » sans objet";
État limite non exporté;ELU accidentel : absent (le modèle source ne déclare aucune combinaison accidentelle ni sismique (combinaisons 100 à 115, E11));
État limite non exporté;"ELS quasi permanent : absent (le modèle source ne déclare pas de combinaison quasi permanente (E11) ; la fissuration se vérifie sous ELS fréquent (E23))";

N°;Type;N (kN);M (kN.m);;Cas dimensionnant;Combinaison;Position mobile;Lieu;Cote (m);V concomitant (kN);MFY brut Code_Aster (kN.m);MFZ brut Code_Aster (kN.m);N brut Code_Aster (kN);Repère des valeurs brutes
1;ELU;653,0;283,4;;M max;111 ELU+;TSB_P25;PIEU_F7_YP, maille 5242, extrémité 2, nœud 472;Z = 0,700;244,7;-40,4;-280,5;-653,0;"POU_D_T, repère local de l'élément : pieux x_l = −Z, y_l = +X, z_l = −Y ; …"
2;ELU;1029,8;57,1;;N max;112 ELU+;TSB_M20;PIEU_F2_YP, maille 4927, extrémité 1, nœud 156;Z = -0,800;36,4;-10,4;-56,2;-1029,8;"…"
3;ELU;167,7;119,8;;N min;115 ELU-;TSB_M15;PIEU_F1_YM, maille 4826, extrémité 2, nœud 56;Z = 0,700;198,2;-18,7;-118,4;-167,7;"…"
4;ELS;456,8;192,0;;M max;111 ELS_c;TSB_P25;PIEU_F7_YP, maille 5242, extrémité 2, nœud 472;Z = 0,700;164,5;-27,3;-190,1;-456,8;"…"
5;ELS;719,3;38,3;;N max;112 ELS_c;TSB_M20;PIEU_F2_YP, maille 4927, extrémité 1, nœud 156;Z = -0,800;24,3;-7,3;-37,6;-719,3;"…"
6;ELS;183,4;69,4;;N min;115 ELS_c;TSB_M15;PIEU_F1_YM, maille 4826, extrémité 2, nœud 56;Z = 0,700;127,7;-11,1;-68,5;-183,4;"…"
7;ELSfiss;345,3;131,0;;M max;111 ELS_f;TSB_P25;PIEU_F7_YP, maille 5242, extrémité 2, nœud 472;Z = 0,700;114,8;-20,8;-129,3;-345,3;"…"
8;ELSfiss;532,2;25,8;;N max;112 ELS_f;TSB_M20;PIEU_F2_YP, maille 4927, extrémité 1, nœud 156;Z = -0,800;16,2;-4,2;-25,4;-532,2;"…"
9;ELSfiss;186,6;41,0;;N min;115 ELS_f;TSB_M15;PIEU_F1_YM, maille 4826, extrémité 2, nœud 56;Z = 0,700;86,2;-8,6;-40,1;-186,6;"…"

Empreinte du MED source (resultats.med, SHA-256);8e8b91ffa99a22aefb7582274008393795c031c693cf3e0852d6c4f6b5891315
```

Les lignes de même nœud, combinaison, position, N et M au dixième sont fusionnées (la
colonne « Cas dimensionnant » nomme les cas qu'elles couvrent) : au plus quatre lignes par
état limite.

### 4.4 Critères de service (estacade, E21 et E22)

| Critère | Valeur | Limite | Taux | Verdict | Lieu, combinaison, position |
| --- | --- | --- | --- | --- | --- |
| déplacement horizontal en tête, files 2 à 6 | 3,399 mm | 7,125 mm | 0,477 | RÉUSSI | PIEU_F2_YP (5,60 ; 2,00), 115 ELS_c, TSB_M26 |
| idem, files 1 et 7 (information, E21) | 4,205 mm | 7,125 mm | 0,590 | sans verdict | (0,60 ; 2,00), 115 ELS_c, TSB_M26 |
| flèche des chevêtres, Y −2 → +2 | 0,145 mm | 10,0 mm | 0,015 | RÉUSSI | file X = 30,60, 103 ELS_c, TSA_P29 |
| flèche de la dalle entre files | 0,896 mm | 12,5 mm | 0,072 | RÉUSSI | (2,95 ; 1,05), 110 ELS_c, TSB_M25 |
| consoles de chevêtre (information) | 0,133 mm | 5,0 mm | 0,027 | information | (30,60 ; −3,00), 110 ELS_c, TSB_P29 |
| débord d'about (information) | 0,339 mm | 3,0 mm | 0,113 | information | (0,00 ; 1,05), 110 ELS_c, TSB_M25 |

828 évaluations par critère (16 combinaisons ELS_c, 59 positions TS chacune pour 14
d'entre elles) ; flèches sous ELS caractéristique hors PP, G2, TE+ et TE− (E22). Quai et
dalle : aucun critère décidé (`no_service_criteria`, motif écrit).

### 4.5 Équilibre par état limite

| Projet | État limite | Évaluations | Écart relatif max | Composantes jugées | Verdict |
| --- | --- | --- | --- | --- | --- |
| estacade | ELU fondamental | 1 656 | 4,7·10⁻¹¹ | FX, FY, FZ | RÉUSSI |
| estacade | ELS caractéristique | 828 | 3,9·10⁻¹¹ | FX, FY, FZ | RÉUSSI |
| estacade | ELS fréquent | 828 | 3,0·10⁻¹¹ | FX, FY, FZ | RÉUSSI |
| quai | les cinq | 1 à 8 | ≤ 1,7·10⁻¹² | FY, FZ (SYM_G, SYM_D ne bloquent que DX et ne sont pas livrés, CA-026) | RÉUSSI |
| dalle | les quatre | 1 | 8,4·10⁻¹² | FX, FY, FZ | RÉUSSI |

La charge d'une position mobile est la résultante déclarée de sa position de référence
(`controls.cases` : TSA_P00, TSB_P00, évaluées par l'extension du projet).

### 4.6 Classeur

Plan des feuilles (estacade : 10) : « Synthèse ingénieur », « Vérifications de service »,
« Torseurs » (format large : 183 lignes dimensionnantes puis une ligne par section ×
combinaison), « Détail pieux », « Détail chevêtres » (un membre par ligne et par état
limite), puis les feuilles du lot 49 : « Réactions et équilibre » (complétée par
l'équilibre par état limite), « Contrôles D et E » (avec le contrôle croisé),
« Comparaison externe », « Conventions » (avec les états limites et les règles de lecture
des sections), « Provenance ». Les tables longues du lot 49 (valeurs aux points de
lecture, enveloppes le long des éléments, extrema par champ) sont des CSV annexes
(`livrables/annexes/`, `paquet/visualisation/synthese.csv`), hors du classeur. En-têtes
figés, largeurs adaptées, format d'affichage par unité (`config/arrondis.yaml`), Arial 10,
en-têtes gris D9D9D9, valeurs non significatives sur gris F2F2F2 avec leur motif.

Capture texte de la Synthèse ingénieur de l'estacade (valeurs de Code_Aster, kN, kN·m,
coques par mètre ; colonnes « Détail » et « Remarque » abrégées) :

```
Famille | Section | Grandeur | ELU : Valeur, N, M, V | ELS car. : Valeur, N, M, V | ELS fréq. : Valeur, N, M, V
pieux | tête de pieu | N max | -166.3, -166.3, 244.7, 218.3 | -181.9, -181.9, 150.0, 141.0 | -185.1, -185.1, 95.3, 95.5
pieux | tête de pieu | N min | -1022.6, -1022.6, 133.1, 36.4 | -714.0, -714.0, 89.0, 24.3 | -526.9, -526.9, 59.7, 16.2
pieux | tête de pieu | M max (résultante) | 435.5, -651.0, 435.5, 262.5 | 294.3, -455.3, 294.3, 176.3 | 202.4, -343.8, 202.4, 123.3
pieux | tête de pieu | V max (résultante) | 279.7, -573.9, 434.2, 279.7 | 187.8, -403.9, 293.4, 187.8 | 130.9, -309.6, 201.8, 130.9
pieux | bouchon (+0,70 à −0,80) | M max (résultante) | 283.4, -653.0, 283.4, 244.7 | 192.0, -456.8, 192.0, 164.5 | 131.0, -345.3, 131.0, 114.8
pieux | pieu courant (sous −0,80) | M max (résultante) | 140.9, -453.6, 140.9, 14.9 | 94.4, -324.6, 94.4, 10.4 | 64.9, -251.0, 64.9, 6.8
chevêtres | chevêtre en travée | MFY min | -443.1, -13.4, -443.1, 0.5 | -304.6, -8.9, -304.6, 0.0 | -203.3, -6.3, -203.3, -0.1  (barre seule, CA-058)
chevêtres | chevêtre au nu de l'appui | |VZ| max | 179.9, -11.2, -63.1, 179.9 | 124.2, -7.4, -41.0, 124.2 | 84.8, -5.2, -17.3, 84.8  (barre seule, CA-058)
tablier | dalle en chapeau au nu du chevêtre | MXX max | 90.2, -94.7, 90.2, 79.6 | 60.1, -63.6, 60.1, 56.1 | 41.3, -45.0, 41.3, 44.6
tablier | dalle en travée | MXX min | -192.9, 44.4, -192.9, 6.7 | -130.8, 29.2, -130.8, 4.0 | -81.9, 21.9, -81.9, 2.9
tablier | dalle en rive (trottoirs) | MXX max | 157.1, 40.4, 157.1, 160.2 | 108.6, 26.5, 108.6, 111.2 | 78.6, 21.1, 78.6, 81.4
tablier | dalle en rive (trottoirs) | MXX max | 245.9, 47.0, 245.9, 509.5 | …  non significative : dans un disque d'exclusion de rayon 0,6 m autour de TETES (PAT-013)
ressorts de sol | ressorts de sol | N max | 45.7 | 30.6 | 21.4
appuis | pointes des pieux | DZ max | 1075.4 | 753.1 | 566.0
```

(58 lignes en tout, extrait ; feuille complète dans le classeur déposé.) Le QY de
10 409 kN/m relevé au lot 49 sur la ligne du chevêtre n'apparaît plus : les nœuds partagés
avec les chevêtres sont hors des valeurs de dimensionnement de la dalle.

### 4.7 Diagrammes et images

| Défaut relevé (consigne) | Correction |
| --- | --- |
| Pas de diagramme N, M, V | une planche par famille de poutres (`diagramme_<famille>.png` : estacade pieux et chevêtres, quai poutre de couronnement et tirants), une case par membre et par grandeur, enveloppes ELU (bande) et ELS car. (lignes), extrema ELU annotés (valeur, cote), kN et kN·m ; coupes de dalle (`coupe_<nom>.png` : estacade 3, dalle 2) avec les zones exclues hachurées |
| Unités SI brutes dans les légendes | Calculator de conversion dans les scripts : kN, kN·m, kN/m, kN·m/m, mm |
| Pas de titre | titre par image : cas ou combinaison, valeur extrême (min et max des cartes, déplacement max, norme max des flèches, résultante des charges) |
| Pas de vue en plan ni en élévation | trois vues par objet : `_iso`, `_plan` (depuis +Z), `_elevation` (depuis −Y), projection parallèle pour les deux dernières |
| Flèches à chaque nœud de 0,05 m (blocs) | forces sommées sur une grille de pas multiple du pas des nœuds (origine à un demi-pas), 400 flèches au plus par cas, somme conservée (test) : estacade 7 grilles (2 510 flèches en tout), quai 6 (1 571), dalle 2 (374) ; une charge uniforme se lit en flèches égales |
| Défaut constaté pendant le lot | effort tranchant en dents de scie (extrémités d'éléments d'un même nœud triées au hasard) : tracé élément après élément ; « \| » et « Σ » non rendus par la police de ParaView : remplacés par « norme » et « résultante » |

Images : estacade 264, quai 330, dalle 66 (vues iso, plan, élévation) ; seules les vues
isométriques des charges et des enveloppes entrent dans le paquet versionné. Toutes sont
générées depuis le manifeste (`grilles_charges`, `extremes`), sans liste écrite à la main.
Limite : en vue en plan, une charge verticale se voit de dessus (disques colorés) ; c'est la
répartition qui s'y lit, l'intensité se lit en isométrique et en élévation.

### 4.8 Dépôt et paquets

Dépôt (estacade d'abord, cas pilote) : `/media/sf_partage/echanges/lot49bis/<projet>/`
(classeur, `flexion_composee/`, `diagrammes/`, `png/`, `vtu/` : scripts et grilles,
`annexes/`, JSON de la synthèse ; notice `LISEZMOI.txt`) : estacade 20 Mo, quai 24 Mo,
dalle 6,1 Mo. Paquets versionnés : estacade 8,7 Mo, quai 16 Mo, dalle 2,2 Mo (plafond
20 Mo).

| Projet | Niveau avant | Niveau après | `.comm` de production |
| --- | --- | --- | --- |
| dalle | E | E | inchangé |
| quai | D | D | inchangé |
| estacade | D | D | inchangé |

## 5. Verdicts

| Critère (§ 3) | Verdict |
| --- | --- |
| F7_YP, M résultant ELU = 435,49 ± 0,005 kN·m, lieu, combinaison, position | **réussi** (435,494 ; PIEU_F7_YP, +1,30 ; 111 ELU+ ; TSB_P25) |
| Ligne ELU « M max » du fichier de la tête de pieu | **réussi** (M = 435,5 ; N = 651,0 = −N de Code_Aster) |
| Contrôle croisé par `resultats lire` (≤ 10⁻⁹) | **réussi** (2 844 valeurs, écart max 4,7·10⁻¹⁷) |
| Combinaisons recalculées = combinaisons du lot 49 | **réussi** (même contrôle : combinaisons sans charge mobile relues dans `comb/<i>/max`) |
| Équilibre par état limite (≤ 10⁻⁶) | **réussi** (≤ 4,7·10⁻¹¹ ; quai jugé sur FY et FZ) |
| Grille des flèches : somme conservée | **réussi** (test, 10⁻¹²) |
| `.comm` et niveaux des paquets | **réussi** (E, D, D conservés) |
| Classeur relu | **réussi** (tests de relecture) |

## 6. Limites

- Chevêtres de l'estacade : la synthèse et l'export donnent la **barre seule** ; la dalle
  porte une part de l'effort (CA-058). Le total de la section en T (règle E17.2) n'est pas
  une grandeur générique de la synthèse : réserve écrite dans le classeur et les fichiers.
- Coques : seuls les nœuds partagés et les disques déclarés sont exclus. Leurs voisins ne
  le sont pas : sur la rive de l'estacade, le QY concomitant de MYY max vaut 577 kN/m à
  5 cm d'une ligne de chevêtre. Une bande d'exclusion autour des lignes partagées serait
  une décision de MM, non prise par la session.
- Quai : les efforts de la poutre de couronnement sont nuls aux arrondis près sous G,
  EAU_P et Q1 (|MFY| ≤ 2·10⁻⁵ N·m, lu par `resultats lire`) ; seul Q3 (amarrage) la
  charge. Cause probable (déduction) : tronçons solidaires des têtes de tubes par
  `LIAISON_SOLIDE` (`GEN_POUTRE_xx`). Réserve déclarée sur la famille, à confirmer par MM ;
  le ferraillage du quai reste bloqué par la révision d'Es (PRE-032).
- Équilibre des positions mobiles : la charge d'une position est la résultante déclarée de
  sa position de référence, pas celle de chaque position (aucun MED de charges n'est écrit
  pour les positions, lot 49).
- Section circulaire : la flexion déviée est exportée par son moment résultant ; le
  logiciel de MM traite une flexion plane (avertissement dans le fichier).
- Images en plan des charges verticales peu lisibles en intensité (§ 4.7).
- Les valeurs de la synthèse ont le niveau des livrables (C ; contrôles D des projets) :
  la synthèse ne crée aucun niveau.
