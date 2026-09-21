# Lot 27 — Maillage du quai QUAI-CW-TEST-01 par la chaîne Salomé

Rapport d'essai selon `docs/modele_rapport_essai.md`. Niveau visé : C pour la
lecture par Code_Aster (exécution jusqu'à `FIN`), D pour les grandeurs exactes de
la géométrie (aires, longueurs, comptages).

## Critère de réussite (écrit avant toute exécution de Salomé)

Les valeurs attendues sont calculées **analytiquement** par
`aster_expert.meshing.combiwall` (module distinct du script Salomé), à partir de
`data/examples/combiwall_model_data.yaml`, par `scripts/build_lot27_maillage.py`. Elles
sont écrites dans `data/examples/combiwall_mesh_invariants.yaml` et
`data/examples/lot27_maillage/` avant l'exécution, et jamais relues d'un MED.

### Maillage (`aster-expert mesh check`)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Nœuds | 40 114 | exacte (entier) | égalité |
| Mailles QUAD4 / SEG2 | 40 120 / 39 583 | exacte (entiers) | égalité |
| Cardinalité, type de mailles, boîte englobante des 57 groupes | voir `combiwall_mesh_invariants.yaml` | exacte | égalité ; boîtes à 1e-9 m |
| Boîte englobante du modèle | X ±10,40 ; Y −0,71 à +25,14 ; Z −26,00 à +3,30 | exacte | 1e-9 m |
| Nœuds à chaque cote imposée, sur chaque tube (génératrices bassin et terre) et chaque palplanche | présents | exacte | 1e-9 m |
| Axes des tubes | X = −10,40 + 2,60·k, k = 0…8 | exacte | 1e-9 m |
| Nœuds partagés palplanche / chacun de ses deux tubes | 84 (toute la hauteur −18,00 à +2,60), aux six cotes | exacte | égalité |
| Nœud de départ de chaque tirant commun avec un nœud de son tube | 1 | exacte | égalité |
| Nœud de chaque `ANC_xx` commun avec un nœud de l'écran | 0 | exacte | égalité |
| `DEFENSE` | ⊂ `TUBE_05`, cotes +1,00 à +2,00, ±45° du côté bassin | exacte | inclusion, boîte 1e-9 m |
| `SYM_G`, `SYM_D` | exactement les nœuds du plan X = ∓10,40 (234 chacun) | exacte | égalité d'ensembles |
| Nœuds orphelins ; paires de nœuds distants de moins de 1e-9 m | 0 | exacte | égalité |
| Symétrie : pour chaque nœud en X, un nœud en −X | 0 nœud sans symétrique | exacte | 1e-9 m |
| Largeur projetée de `ECRAN_POUSSEE` sur Y = 0, bande −18,00 à +2,60 | 20,80 m | exacte (aires des mailles) | 1e-9 m |
| Idem, bande sous −18,00 (tubes seuls) | 7 × 1,42 + 2 × 0,71 = 11,36 m | exacte (aires des mailles) | 1e-9 m |
| Aire développée de `DEFENSE` | 10 × (2 R sin(π/40)) × 1,00 = 1,114119 m² | exacte | 1e-9 m² |
| Écart de `DEFENSE` à 2 × (π/4) × 0,71 × 1,00 = 1,115265 m² | −0,001146 m² (effet de facettisation : −0,10 %) | exacte | 1e-9 m² |

Un invariant en écart est un échec, rapporté tel quel ; on corrige le script, jamais
les invariants, sauf si l'invariant est démontré faux (et alors on le rapporte).

### Lecture par Code_Aster

`LIRE_MAILLAGE(FORMAT='MED', INFO=2)`, `AFFE_MODELE` (DKT sur `TUBES` et `PALPS`, BARRE
sur `TIRANTS`, POU_D_E sur `POUTRE_COUR`), `AFFE_CARA_ELEM` unitaire (`EPAIS = 1`,
`A = 1`), `DEFI_MATERIAU` avec `RHO = 1`, puis `POST_ELEM(MASS_INER)` sur chacun des
35 groupes de mailles. La masse d'un groupe est son aire développée (coque) ou sa
longueur ; l'effet de facettisation est inclus dans la valeur de référence
(`data/examples/lot27_maillage/aster_expected.json`).

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Statut de l'exécution | `completed_ok` ou `completed_with_alarms` (toute alarme est listée et expliquée, jamais neutralisée) | — | jusqu'à `FIN` |
| Masse de chacun des 35 groupes | aire ou longueur du groupe | exacte | 1e-6 en relatif |

Le niveau B du `.comm` est établi (`validate_comm`) avant l'exécution.
Toute autre issue est un échec, rapporté tel quel.

## Modèle et exécution

- Salomé-Méca `V2024.1.0_scibian_univ`, image `~/Desktop/salome_meca.sif`, SHA-256
  `48beffc5062a2701be2a5af9a52124b1ff1a0b674445408dcdbb61d056094326`.
- Script `scripts/salome/combiwall_mesh.py`, paramètres `data/examples/lot27_maillage/params.json`
  (SHA-256 `c67d5f39715f76df623e3bc371a56f47fa8a99723f69e6fc89dabb5dc41b9ddc`, inscrite par le
  script et retrouvée par `mesh run`). MED : `med/combiwall_mesh.med`, 4,9 Mo, SHA-256
  `04cf52c988f6b7342be9807a93aee416d6300deebc67e58b7f4f8d94bbf0f434`.
- Le script exécuté a pour SHA-256 `abc3c0df…23fe` ; le fichier versionné n'en diffère que par
  le formatage `ruff format` appliqué ensuite (arbres syntaxiques identiques vérifiés).
- Signatures GEOM/SMESH relevées par la sonde `scripts/salome/lot27_sonde_signatures.py`
  (`signatures_geom_smesh.txt`, sortie `LOT27_PROBE_OK`).
- Rapports : `rapports/mesh_run.json`, `mesh_check.txt`, `mesh_check_variante_36_facettes.txt`,
  `aster_run.json`, `meta.json` (segments imposés) ; listing Code_Aster `mess/mess_lecture.txt` ;
  analyse `analyse.json` (`scripts/analyze_lot27_maillage.py`).

## Résultats

### Premières exécutions : échecs rapportés tels quels

- Lecture Code_Aster, premier lancement : `aborted` (`_ABNORMAL_ABORT`, 10 s) : le MED n'avait pas
  été copié, faute de porter le nom du `.comm` (`lot27_lecture.mmed`). Corrigé (nom), relancé.
- `mesh run`, premier lancement : délai de 900 s dépassé, journal perdu (processus tué). Le délai
  a été porté à 3 000 s dans `config/validation.yaml` et le script écrit sa progression dans
  `combiwall_mesh.progress.txt`. Durée mesurée : géométrie et partition 6,5 s, classement des
  4 237 arêtes (`GetInPlace`) 229 s, calcul du maillage 0,4 s, création des 57 groupes 805 s
  (total 1 040 s).

### Segments imposés par type d'arête (rapport de maillage)

| Type d'arête | Longueur (m) | Segments | Arêtes |
| --- | --- | --- | --- |
| Verticale −26,00 → −18,00 | 8,00 | 32 | 322 |
| Verticale −18,00 → −12,00 | 6,00 | 24 | 322 |
| Verticale −12,00 → +1,00 | 13,00 | 52 | 322 |
| Verticale +1,00 → +2,00 | 1,00 | 4 | 322 |
| Verticale +2,00 → +2,50 | 0,50 | 2 | 322 |
| Verticale +2,50 → +2,60 | 0,10 | 1 (règle : plancher à 1) | 322 |
| Horizontale d'une facette de tube | 0,11141 | 1 | 2 240 |
| Horizontale de palplanche (décision 11) | 1,18 | 5 | 48 |
| Travée de poutre (décision 11) | 2,60 | 8 | 8 |
| Tirant (décision 11) | 25,99725 | 1 | 9 |

Total 4 237 arêtes, égal au nombre d'arêtes de la partition (contrôle interne du script).
Ces nombres sont identiques à `segments_attendus.json` (module analytique).

### `mesh check`

588 invariants, 588 tenus, 0 en écart, au premier passage. Contrôles demandés :
boîte du modèle (−10,4 ; 10,4 ; −0,71 ; 25,14 ; −26 ; 3,3) ; symétrie X (0 nœud sans
symétrique) ; largeur projetée de `ECRAN_POUSSEE` : 20,8 m à z = 1,625 et 11,36 m à
z = −21,875 ; aire développée de `DEFENSE` 1,114119 m², écart à l'idéal 1,115265 m² :
−0,001146 m² (−0,10 %), égal à l'effet de facettisation calculé. Contrôle de sensibilité :
les invariants calculés pour 36 facettes rejettent le même MED (29 écarts, premier :
nombre de nœuds). Rapport complet : `rapports/mesh_check.txt`.

### Lecture par Code_Aster (`aster-expert run`, niveau C)

Niveau B du `.comm` établi avant exécution (`validate_comm` : `valid=true`, 9 commandes
confrontées, 0 non confrontée). Exécution `completed_ok`, diagnostic `OK`, sans alarme, 33,8 s.
Nœuds lus 40 114, mailles QUAD4 40 120 et SEG2 39 583 ; cardinalité des 35 groupes de mailles
conforme ; masses des 35 groupes : erreur relative maximale 5,4e-13 (seuil 1e-6).

### Taille du maillage

40 114 nœuds ; 79 703 mailles : 40 120 QUAD4 et 39 583 SEG2 (les SEG2 incluent les bords des
coques, constat du lot 26).

## Verdict

Au regard du seul critère ci-dessus : invariants du MED **réussite** (588/588) ; contrôles de
largeur projetée et d'aire de `DEFENSE` **réussite** ; lecture par Code_Aster jusqu'à `FIN`
**réussite** (niveau C) ; masses de groupes à 1e-6 **réussite** (niveau D pour cette grandeur
exacte).

## Lecture et limites

- Faits : longueur des tirants issue des coordonnées d'ancrage (données au centimètre) :
  25,99725 m et 19,9987°, contre 26,00 m et 20° annoncés (−0,01 %) ; les coordonnées sont
  employées telles quelles, l'écart est borné par `build_params`.
- `RESS_AV_ARGI` et `RESS_AV_MARNE` suivent la convention à la lettre (mailles de l'écran entre
  les cotes, les deux faces des tubes) ; la restriction « côté bassin » des ressorts relève du
  générateur du lot 28.
- Les groupes de nœuds ne sont vérifiés que par `mesh check` (cardinalité, boîtes, plans) ;
  Code_Aster ne les lit pas dans ce calcul. La poutre n'est pas reliée à l'écran (liaison de
  corps solide au lot 28, contrôle `poutre non reliée` en invariant).
- Aucune étude de convergence (0,25 m, 40 facettes), conformément à la décision 11.
- La création des groupes prend 805 s (compound de plusieurs centaines de faces par
  `GetInPlace`) : non optimisée.
- Le contrôle de cohérence des données pour la valeur 1 (« un élément de barre ») est faible :
  l'article « un » est accepté pour la valeur 1 exacte.
