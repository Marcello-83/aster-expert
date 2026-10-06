# Essais du lot 47 ter — estacade : attribuer chaque écart à sa cause

**Contre-calcul d'un modèle non validé** (lots 47 et 47 bis) : aucune ligne n'est un
niveau E, un écart ne désigne pas d'avance le logiciel fautif. Consigne :
`docs/lots/lot47ter_consigne.md`. Le lot ne recale pas le modèle : il **attribue** chaque
écart à une cause. La référence (E1 à E19) n'est pas modifiée ; les configurations
ajoutées sont des **variantes déclarées**.

Ce rapport suit `docs/modele_rapport_essai.md`. Les sections 1 à 5 sont écrites et
commitées **avant** toute exécution de calcul du lot ; elles ne sont pas modifiées
ensuite (une erreur s'y corrige dans une section datée « Correction du critère »).
Version de Code_Aster : 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

**Statut des critères.** Les règles de lecture sont celles du lot 47 bis (E17,
`docs/essais_lot47bis.md` § 1), inchangées. Elles ont été écrites après la première
exécution du lot 47 : elles ne sont pas aveugles. Les critères de conclusion ci-dessous
(§ 2.4, § 3.4, § 4) sont écrits **après** la lecture des trois configurations qui existent
déjà (référence, DST, E19 ; chiffres cités par la consigne) et **avant** l'exécution des
configurations nouvelles.

## 1. Étape 0 — `search_connaissances` (outil)

Rédigé après la reproduction, avant toute exécution de calcul.

- `env-check` : profil **vm**, 8 vérifications OK ; `mcp-check` : 9 outils OK.
- **Reproduction.** Le code du lot 47 (avant le lot 47 bis), chargé dans un processus,
  lit la base actuelle : `KnowledgeBaseError`, « CTL-005.yaml : version : Extra inputs are
  not permitted; version_history : Extra inputs are not permitted », même chose pour
  CTL-013, puis toutes les entrées qui citent CTL-005 (promotions, patrons). Le serveur
  relit la base à chaque appel (`load_knowledge`, aucun cache) mais garde le **schéma**
  importé à son démarrage (`aster_expert.connaissances.modeles`, `extra="forbid"`). Au
  lot 47 bis, la session a ajouté `version` et `version_history` au modèle `Control` et
  aux deux contrôles : pour le serveur lancé avant, la base entière devenait incohérente,
  jusqu'au redémarrage ; un serveur neuf (`mcp-check`) importait le nouveau schéma.
- **Classement** : diagnostic nouveau **ENV-002** (`connaissances/diagnostics/ENV-002.yaml`) ;
  aucun diagnostic existant ne le couvre (`search_connaissances`, couche diagnostics).
- **Correctif** : `aster_expert.connaissances.fraicheur` (empreinte SHA-256 des sources
  du chemin de lecture, prise à l'import ; rechargement de ces modules, dans l'ordre des
  dépendances, si elle a changé), appelé en tête de `search_connaissances` et de
  `search_constats`. Test : `tests/unit/test_connaissances_fraicheur.py` rejoue la panne
  dans un sous-processus, sur une copie des sources et de la base (champ ajouté au modèle
  et à une entrée après une première recherche) : sans rechargement, `KnowledgeBaseError`
  « Extra inputs are not permitted » ; avec, la recherche répond comme avant.
- **Limite** : un changement d'un module hors de ce chemin (par exemple
  `aster_expert.agent.hypotheses`, importé par les modèles des constats) n'est pas
  détecté ; la consigne « redémarrer la session » reste valable. Les outils MCP ne
  changent pas de nom ni de paramètres, mais leur code change : **redémarrer la session
  avant le lot suivant**.

## 2. Étape 1 — Plan factoriel {DKT, DST} × {chevêtre 0,90, 0,80}

### 2.1 Configurations

| Code | Dalle | Chevêtre | Exécutions (maillage de production 0,05 m) | Statut |
| --- | --- | --- | --- | --- |
| R | DKT | 0,90 m | `20261005T101455-e0d5c870` (lot 47) + `20261005T150307-187df570` (positions d'E18, lot 47 bis) | référence (E1 à E18) |
| S | DST | 0,90 m | `20261005T104915-1d558927` (variante (a), lot 47) + **N2** (positions d'E18, ce lot) | variante E13 |
| H | DKT | 0,80 m | `20261005T150840-65219726` (E19, positions d'E18 comprises) | variante E19 |
| SH | DST | 0,80 m | **N1** (ce lot, positions d'E18 comprises) | variante déclarée, ce lot |

- **N1** : tout le modèle de production (E1 à E18) avec `MODELISATION="DST"` sur la dalle
  et ses arêtes de rive, et `HZ = 0,80` pour les chevêtres ; générateur
  `projets/estacade_pieux_01/generation.py`, variante `dst_chevetre_0p80`. Le poids du
  chevêtre suit la section (comme E19).
- **N2** : les 57 positions de l'essieu de trottoir d'E18 sur le modèle de la variante S
  (DST, 0,90 m), mode `tr_essieu` ; seul ajout à S, pour lire C12 « rive » selon E18 (la
  variante (a) du lot 47 précède E18).
- Même maillage vérifié (0,05 m), même solveur (`POSTTRAITEMENTS="FORCE"`) que la
  production. Le générateur rend la référence, E19 et la variante DST du lot 47
  **identiques à l'octet** aux `.comm` exécutés (vérifié avant ce rapport).

### 2.2 Lectures

Pour les quatre configurations : toutes les lignes de `ComparisonV2.all_points()`
(`projets/estacade_pieux_01/comparaison_v2.py`), C1 à C13, règles du § 1.4 de
`docs/essais_lot47bis.md`, **avec la barre seule** de C6, C7 et C8 (lignes « information »
du lot 47 bis). La combinaison 100 comprend l'essieu d'E18 (enveloppe sur ses 57
positions) dans les quatre configurations.

### 2.3 Contrôles des exécutions N1 et N2 (à 1e-6 en relatif)

- Σ DZ des réactions des pointes = charge des roues de chaque position (N1 : 242
  positions de TS et LM2 et 57 positions TRE ; N2 : 57 positions TRE) ;
- N1, PP : Σ DZ des pointes = **3 427 297,604 N** (même poids qu'E19 : la modélisation
  de la dalle ne change pas le poids) ;
- exécution `OK`, toute alarme consultée dans les diagnostics (DIAG/ENV) avant
  hypothèse.

### 2.4 Critère de conclusion (consigne, précisé ici avant l'exécution de N1)

Lignes examinées sur la configuration SH, avec les tolérances d'E12 :

| Point | Lignes | Tolérance |
| --- | --- | --- |
| C2 | ELS f, ELS c, ELU (112) | 3 % |
| C3 | ELS f, ELS c, ELU (111) | 5 % |
| C4 | ELU (114) | 5 % |
| C5 | ELU (111) | 5 % |
| C6 | **barre seule** ELS f, ELS c (105), ELU (112) | 5 % |
| C7 | **barre seule** ELU (enveloppe 100-115), en module | 5 % |
| C8 | **barre seule** ELU (105, 112), toutes lignes | 5 % |

- **Confirmée** : les 13 lignes sont dans leur tolérance.
- **Partielle** : au moins une ligne en sort, et SH en a strictement plus dans la tolérance
  que R lue de la même façon (mêmes 13 lignes, barre seule pour C6 à C8).
- **Réfutée** : au moins une ligne en sort, et SH n'en a pas plus dans la tolérance que R.

Dans les trois cas, les lignes qui résistent sont listées avec leur écart. Les effets
principaux (moyenne des deux niveaux de l'autre facteur) et l'interaction des deux
facteurs sont rapportés pour chaque ligne, sans verdict. Le total barre + dalle (règle
v2) reste rapporté pour C6 à C8.

## 3. Étape 2 — Dépendance au maillage des grandeurs locales

### 3.1 Configuration et maillages

Configuration **SH** (celle de l'étape 1), fixée ici quel que soit le résultat du § 2.4.
Trois maillages de dalle : 0,05 m (N1), **0,25 m (N3)** et **0,50 m (N4)**, même script
Salomé (`maillage/estacade_mesh.py`), paramètres et invariants calculés avant Salomé
(`maillage/params_h0p250.json`, `params_h0p500.json`, `invariants_h0p250.yaml`,
`invariants_h0p500.yaml`, `scripts/invariants_lot47.py`). Coupes inchangées (files de
pieux, lignes Y = ±2,00 et ±1,50) : les têtes de pieux et les chevêtres restent sur des
lignes de nœuds. L'about de 0,60 m n'est pas un multiple de 0,25 ni de 0,50 : il reçoit
le nombre entier de segments le plus proche, écrit dans les paramètres (2 × 0,30 m à
0,25 ; 1 × 0,60 m à 0,50) ; toutes les autres arêtes sont des multiples exacts. Pieux
inchangés. Critère du maillage : `mesh check` sans écart (comptages : 3 573 nœuds et
2 976 QUAD4 à 0,25 ; 1 267 nœuds et 744 QUAD4 à 0,50).

### 3.2 Représentation des empreintes à charge totale exacte

Positions identiques à celles du maillage de production (pas de 0,50 m, LM2 décalé d'une
demi-maille de 0,05 m). Une empreinte ne peut plus être une réunion de mailles entières :
chaque roue est appliquée sur **chaque maille qu'elle recouvre**, en pression uniforme
égale à la pression de la roue multipliée par la fraction recouverte de la maille
(`generation.fractional_prints`) ; deux empreintes sur une même maille s'additionnent (une
seule occurrence de `FORCE_COQUE` par maille et par cas). La force sur chaque maille, et
donc la charge totale, sont exactes ; la charge est étalée sur la maille (conséquence de
la taille de maille, voulue par l'étape). Le générateur refuse une position dont la charge
représentée s'écarte de la charge nominale de plus de 1e-9 en relatif. Mailles : un groupe
par maille (`CREA_GROUP_MA/BANDE`, `CRIT_NOEUD="TOUS"`, PAT-003, intersecté avec `DALLE`).

### 3.3 Contrôles des exécutions N3 et N4 (contrôle de résultante)

Les mêmes que N1 (§ 2.3), à 1e-6 : Σ DZ des pointes = charge des roues pour les 299
positions, PP = 3 427 297,604 N (aires exactes à toute taille de maille).

### 3.4 Lectures et critère de comparabilité

Lectures sur les trois maillages, règles v2 inchangées (disques de 0,60 m, combinaison
100 avec E18) : **C9** (ELS f, ELS c, ELU), **C12 « rive »** (ELU), **C13** (LM1 et LM2 :
Mxx inf., Mxx sup., V). Les autres points sont rapportés en information.

- « Rejoint la source » à la taille h : |écart| ≤ 10 % (E12) à cette taille.
- **Comparable** : la valeur varie de 10 % au plus entre les trois maillages,
  max sur h ∈ {0,25 ; 0,50} de |v(h) − v(0,05)| / |v(0,05)| ≤ 0,10 ; l'écart à la source ne
  s'explique alors pas par la taille de maille.
- **Non comparable sans le maillage source** : variation de plus de 10 % ; la valeur
  dépend de la taille de maille plus que la tolérance, et le maillage source est inconnu.
  Le motif (singularité d'appui, charge concentrée, gradient) est rapporté.

Un point où la valeur ne rejoint la source qu'à une taille de maille grossière n'en devient
pas « comparable » : la taille est rapportée, sans être tenue pour celle de la source.

## 4. Étape 3 — Méthode d'attribution (écrite avant les exécutions N1 à N4)

Une ligne par ligne jugée de la comparaison v2 (30 lignes). Pour chacune, la catégorie
retenue (A à G de la consigne) et sa preuve chiffrée :

- **A** (lecture ou définition) et **B** (données) : causes d'un écart v1 déjà levées au
  lot 47 bis, citées pour les lignes qu'elles ont ramenées dans la tolérance ;
- **C** (choix de modélisation documenté) : la variante S, H ou SH qui porte la différence
  ramène la ligne dans sa tolérance, lue selon la même règle ;
- **D** (incohérence de la source) : citée avec sa trace dans les données versées (annexe B,
  décisions de MM) ;
- **E** (maillage) : ligne classée « non comparable » au § 3.4 ;
- **F** (erreur de notre modèle) : seulement si une erreur est démontrée (contrôle en échec,
  donnée mal appliquée) ;
- **G** (inexpliqué) : sinon, avec les pistes examinées.

Une ligne dans la tolérance de la référence est classée « aucun écart », avec la cause de
son écart v1 s'il y en avait un.

## 5. Capitalisation prévue

- **Précédent proposé** (couche `precedents`, non tranché, à arbitrer par MM) : DKT ou DST
  pour une dalle couplée à des poutres POU_D_T qui partagent ses nœuds, selon le § 2 ;
- CA-058 : domaine de validité précisé si le plan factoriel le permet ;
- `rex estacade_pieux_01`, paquet de résultats, notes, `docs/etat.yaml`.

## 6. Résultats

(Rédigés après les exécutions ; les sections 1 à 5 ne sont pas modifiées.)

### 6.1 Incident d'environnement (ENV-003) et arrêt sur délai (DIAG-025)

Rédigé après les faits, sans modifier les critères des §§ 1 à 5.

**Disque plein (ENV-003).** Le 6 octobre, pendant N1 et N2, le disque de la VM (120 Go) s'est
rempli : N2 s'est arrêtée sur `OSError: [Errno 28] No space left on device`, N1 aussi, et
leurs `compte_rendu.json` sont restés vides (`rex` s'arrêtait alors sur `JSONDecodeError`).
Cause : `run_med_script` (lecture d'un MED de résultats) et `mesh check` copiaient le MED lu
dans `data/processed/mesh_checks/<id>/input.med` (1,9 Go pour l'estacade) et y laissaient
l'extraction `out.npz` (1,9 Go), sans jamais les effacer : 25 Go au total, dont 20 Go pour
les relectures du 5 octobre.

Correction, avec l'accord de MM (question posée dans la session, réponse : supprimer, à
condition de vérifier chaque copie contre son original) :

- 130 copies `input.med` examinées : **120** ont un original de même SHA-256 dans
  `data/processed/runs/` (13,9 Go), revérifié juste avant la suppression ; **10** n'en ont pas
  (36 Mo, contrôles des 21 septembre, 2 octobre et 5 octobre ; leur original n'a pas été
  cherché hors de `runs/`) : **conservées**, listées dans
  `projets/estacade_pieux_01/resultats/lot47ter/plan_suppression.json` ;
- 43 extractions `out.npz` supprimées ; rapports (`rapport_mesh_check.txt`, `out.json`,
  `dump.json`) conservés ; espace libéré : **25,44 Go** (journal :
  `resultats/lot47ter/suppression.log`).

Occupation du disque relevée après la suppression (`du`, `docker system df`), 90 Go utilisés
sur 120 :

| Dossier | Taille |
| --- | --- |
| `data/processed/runs` (archive des exécutions, 404 répertoires ; 1,5 à 2,4 Go pour chaque exécution complète de l'estacade) | 31 Go |
| autres dossiers de `~/projets` (hors `aster-expert`) | 6 Go |
| images Docker (`/var/lib/docker`, 3 images) | 9,4 Go |
| `~/Desktop` (dont l'image Salomé `salome_meca.sif`) | 5,3 Go |
| `~/.local` (dont Pythons de `uv` : 110 Mo) | 4,4 Go |
| `aster-expert/external` (dépôts Code_Aster) | 2,2 Go |
| `~/code-aster` | 1,9 Go |
| caches (`~/.cache`, dont `uv` : 541 Mo) | 0,85 Go |
| `aster-expert/.venv` | 0,3 Go |
| `data/processed/mesh_checks` (après suppression) | 0,4 Go |
| système : `/usr` 7,6 Go, `/var` 7,4 Go (part lisible sans droits d'administration) | ≈ 15 Go |

Correctifs de l'outil (tests : `tests/unit/test_med_read_copies.py`,
`tests/unit/test_rex_compte_rendu_illisible.py`, `tests/unit/test_env_check.py`) :

- la copie du MED est effacée dès que le conteneur rend la main, même en échec
  (`aster_expert.meshing.check.run_then_drop_copy`, utilisé par `run_med_script` et
  `mesh check`) ; `aster_expert.report.med_read.take_arrays` charge l'extraction puis
  l'efface (estacade et quai) ;
- `rex` lit un compte rendu vide ou illisible comme une exécution sans compte rendu (échec à
  classer) et l'attribue au projet par l'empreinte de son `.comm` ;
- `env-check` a une 9ᵉ vérification, `disque` : au moins 10 Go libres en profil vm (2 Go en
  cloud et ci).

Les deux exécutions sont classées sous ENV-003 (nouveau) dans
`connaissances/rex/estacade_pieux_01.yaml`.

**Arrêt par manque de temps CPU (DIAG-025).** N1, relancée après la libération du disque
sans `--timeout`, s'est arrêtée sur `<EXCEPTION> <SUPERVIS_63>` à 1 803,9 s : `aster-expert
run` impose son délai par défaut (1 800 s, 8 192 Mio) quelles que soient les valeurs de
l'`.export` (7 200 s, 10 240 Mio), que seul `run_aster.export` lit, dans le conteneur ; la
variante DST du lot 47 avait été lancée avec `--timeout 7200 --memory-mb 10240` (2 442 s).
Aucun diagnostic existant (`search_connaissances`, mot-clé `CPU_LIMIT`, texte « délai ») :
nouveau diagnostic DIAG-025 ; N1 relancée avec ces limites. La lecture de l'`.export` côté VM
n'est pas ajoutée (ce serait réécrire `run_aster.export`) ; le script du lot imprime la
commande d'exécution avec ses limites.


### 6.2 Exécutions du lot

Toutes au niveau B intégral avant exécution (`aster-expert validate`), aucune alarme dans
les `.mess` des quatre exécutions réussies.

| Exécution | Répertoire | Niveau B | Durée | Contrôle (§ 2.3, § 3.3) | Résultat |
| --- | --- | --- | --- | --- | --- |
| N1, SH (DST, 0,80 m), 0,05 m | `data/processed/runs/20261006T134632-58937400` | 501/501 | 3 127,2 s | 299 positions : écart max 5,9e-12 ; PP 3 427 297,604 N à 1,8e-12 | **réussi** |
| N2, positions d'E18 sur S (DST, 0,90 m) | `data/processed/runs/20261006T134742-072cb0d7` | 95/95 | 615,7 s | 57 positions : écart max 5,0e-12 | **réussi** |
| N3, SH, dalle 0,25 m | `data/processed/runs/20261006T125858-33203f20` | 500/500 | 246,5 s | 299 positions : 7,4e-13 ; PP à 2,9e-13 | **réussi** |
| N4, SH, dalle 0,50 m | `data/processed/runs/20261006T125800-511148ec` | 500/500 | 41,5 s | 299 positions : 3,1e-13 ; PP à 1,4e-16 | **réussi** |
| N1 (1ʳᵉ), N2 (1ʳᵉ) | `…/20261006T125858-7291dc7a`, `…/20261006T130308-683933a3` | — | — | disque plein | échec, ENV-003 (§ 6.1) |
| N1 (2ᵉ) | `…/20261006T131606-cda5e20e` | — | 1 803,9 s | `<S>_CPU_LIMIT` | échec, DIAG-025 (§ 6.1) |

Maillages 0,25 et 0,50 m : `mesh check` **367/367** invariants chacun
(`projets/estacade_pieux_01/references/maillage_lot47ter/`), 3 573 nœuds et 2 976 QUAD4,
1 267 nœuds et 744 QUAD4, comme calculé au § 3.1. Contrôles :
`projets/estacade_pieux_01/references/controles_lot47ter.json`.

Relecture (`scripts/executions_lot47ter.py comparer`, `analyser`) : R et H relus par le même
code redonnent **exactement** (écart 0) les 55 valeurs de
`references/comparaison_v2_lot47bis.json` et les 24 de
`references/variante_chevetre_0p80_lot47bis.json`. Résultats :
`references/plan_factoriel_lot47ter.json`, `references/maillages_lot47ter.json`.

### 6.3 Plan factoriel : verdict de l'hypothèse (critère du § 2.4)

| Point | Ligne | Source | R (DKT, 0,90) | S (DST, 0,90) | H (DKT, 0,80) | SH (DST, 0,80) | Tol. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C2 | ELS_f (112) | 514 | 526,9 ; +2,5 % | 526,4 ; +2,4 % | 517,5 ; +0,7 % | 517,0 ; +0,6 % | 3 % |
| C2 | ELS_c (112) | 727 | 714,0 ; -1,8 % | 713,4 ; -1,9 % | 704,4 ; -3,1 % ✗ | 703,7 ; -3,2 % ✗ | 3 % |
| C2 | ELU (112) | 1 048 | 1 022,6 ; -2,4 % | 1 021,8 ; -2,5 % | 1 009,6 ; -3,7 % ✗ | 1 008,6 ; -3,8 % ✗ | 3 % |
| C3 | ELS_f (111) | 209 | 202,4 ; -3,2 % | 202,1 ; -3,3 % | 202,1 ; -3,3 % | 201,8 ; -3,5 % | 5 % |
| C3 | ELS_c (111) | 312 | 294,3 ; -5,7 % ✗ | 293,9 ; -5,8 % ✗ | 293,9 ; -5,8 % ✗ | 293,5 ; -5,9 % ✗ | 5 % |
| C3 | ELU (111) | 449 | 435,5 ; -3,0 % | 434,9 ; -3,1 % | 434,9 ; -3,1 % | 434,2 ; -3,3 % | 5 % |
| C4 | ELU (114) | 253 | 259,4 ; +2,5 % | 259,2 ; +2,4 % | 259,2 ; +2,4 % | 259,0 ; +2,4 % | 5 % |
| C5 | ELU (111) | 463 | 435,5 ; -5,9 % ✗ | 434,9 ; -6,1 % ✗ | 434,9 ; -6,1 % ✗ | 434,2 ; -6,2 % ✗ | 5 % |
| C6 | ELS_f (105), barre seule | 180 | 202,8 ; +12,7 % ✗ | 203,3 ; +12,9 % ✗ | 177,1 ; -1,6 % | 178,0 ; -1,1 % | 5 % |
| C6 | ELS_c (105), barre seule | 276 | 303,2 ; +9,9 % ✗ | 304,2 ; +10,2 % ✗ | 265,1 ; -3,9 % | 266,7 ; -3,4 % | 5 % |
| C6 | ELU (112), barre seule | 408 | 443,1 ; +8,6 % ✗ | 443,1 ; +8,6 % ✗ | 388,6 ; -4,8 % | 389,4 ; -4,6 % | 5 % |
| C7 | ELU (enveloppe 100-115), barre seule | 177 | 141,9 ; -19,8 % ✗ | 154,8 ; -12,5 % ✗ | 146,7 ; -17,1 % ✗ | 160,1 ; -9,5 % ✗ | 5 % |
| C8 | ELU (105, 112), barre seule, toutes lignes | 653 | 198,1 ; -69,7 % ✗ | 660,8 ; +1,2 % | 172,6 ; -73,6 % ✗ | 635,2 ; -2,7 % | 5 % |
| | **lignes dans la tolérance** | | **6/13** | **7/13** | **7/13** | **8/13** | |

**Verdict, selon le critère écrit avant l'exécution : hypothèse partielle.** SH a 8 lignes sur
13 dans la tolérance, contre 6 pour R. Lignes qui résistent avec SH : C2 ELS c (−3,2 %),
C2 ELU (−3,8 %), C3 ELS c (−5,9 %), C5 ELU (−6,2 %), C7 barre seule (−9,5 %).

Lecture des effets (faits, puis déductions marquées) :

- **C8 (effort tranchant du chevêtre) : la formulation de la dalle décide.** Barre seule :
  198,1 kN en DKT, 660,8 kN en DST (+234 % d'effet principal) ; la source (653 kN) est
  retrouvée en DST (+1,2 % ; −2,7 % avec 0,80 m). Le total barre + dalle varie peu (+1,8 %)
  et s'éloigne de la source en DST (+12,3 %). *Déduction* : la source publie l'effort de la
  barre d'un modèle dont la dalle ne capte pas l'effort tranchant près des appuis, comme une
  plaque déformable à l'effort tranchant ; la partie « DST » de l'hypothèse est **confirmée
  pour C8**.
- **C6 (moment en travée) : la hauteur du chevêtre décide.** Effet de 0,80 m : −12,2 à
  −12,6 points sur la barre seule, effet de DST ≤ 0,4 point. Barre seule dans la tolérance
  avec 0,80 m (H et SH : −1,1 à −4,8 %), total hors tolérance (+5,2 à +8,0 %). La partie
  « 0,80 m » de l'hypothèse est **confirmée pour C6**, lue sur la barre.
- **C2 (effort normal en tête) : 0,80 m le dégrade.** Le chevêtre de 0,80 m allège la
  structure de 126 kN (7 × 6,00 × 1,20 × 0,10 × 25), soit −1,3 à −1,8 point sur C2 ; ELS c
  et ELU sortent de 3 % (−3,2 et −3,8 %). *Déduction* : les charges de la source
  correspondent mieux à un chevêtre pesant 0,90 m ; c'est cohérent avec l'incohérence I2
  (poids sismique à 0,80, « augmenté à 0,90 ») si la source a augmenté la charge sans
  augmenter la raideur, ce qui n'est pas démontrable ici.
- **C3 ELS c, C5 : insensibles aux deux facteurs** (effets ≤ 0,2 point ; −5,7 à −6,2 %
  partout). Ni la formulation ni le chevêtre ne les expliquent.
- **C7 barre seule** : effet DST +9,3 points, 0,80 m +3,5 points ; SH −9,5 % : se rapproche
  sans rentrer. Le total (règle v2) est à +0,4 % en R et sort avec 0,80 m (+5,0 %).
- **Dalle** : C9, C10, C11, C13 « inf. » varient de 1 point au plus ; C12 « courant » et
  C13 « V » baissent de 1,5 à 5,4 points en DST. En information, la lecture de C12 « rive »
  **dans** les disques passe de 1 431 kN/m (DKT) à 326 kN/m (DST) : la singularité de
  l'effort tranchant au nœud de tête est bien plus faible en DST.

### 6.4 Tableau 4 × (C1 à C13), toutes les lignes v2 et la barre seule

Valeurs Code_Aster (écart à la source). Effets principaux et interaction rapportés à |R|.
Unités : kN, kN·m, kN·m/m, kN/m, cm (C1 : 0,4375 cm dans les quatre configurations,
« compatible avec l'arrondi »).

| Point | Colonne | Source | R | S | H | SH | Effet DST | Effet 0,80 | Interaction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | ELS c (107) | 0,5 | 0,4 (-12,5 %) | 0,4 (-12,4 %) | 0,4 (-12,5 %) | 0,4 (-12,4 %) | +0,1 % | -0,0 % | +0,0 % |
| C2 | ELS_f (112) | 514 | 526,9 (+2,5 %) | 526,4 (+2,4 %) | 517,5 (+0,7 %) | 517,0 (+0,6 %) | -0,1 % | -1,8 % | -0,0 % |
| C2 | ELS_c (112) | 727 | 714,0 (-1,8 %) | 713,4 (-1,9 %) | 704,4 (-3,1 %) | 703,7 (-3,2 %) | -0,1 % | -1,3 % | -0,0 % |
| C2 | ELU (112) | 1 048 | 1 022,6 (-2,4 %) | 1 021,8 (-2,5 %) | 1 009,6 (-3,7 %) | 1 008,6 (-3,8 %) | -0,1 % | -1,3 % | -0,0 % |
| C3 | ELS_f (111) | 209 | 202,4 (-3,2 %) | 202,1 (-3,3 %) | 202,1 (-3,3 %) | 201,8 (-3,5 %) | -0,1 % | -0,2 % | -0,0 % |
| C3 | ELS_c (111) | 312 | 294,3 (-5,7 %) | 293,9 (-5,8 %) | 293,9 (-5,8 %) | 293,5 (-5,9 %) | -0,1 % | -0,1 % | -0,0 % |
| C3 | ELU (111) | 449 | 435,5 (-3,0 %) | 434,9 (-3,1 %) | 434,9 (-3,1 %) | 434,2 (-3,3 %) | -0,1 % | -0,1 % | -0,0 % |
| C4 | ELS_f (114) *(info.)* | — | 121,3 (—) | 121,2 (—) | 121,2 (—) | 121,1 (—) | -0,1 % | -0,1 % | -0,0 % |
| C4 | ELS_c (114) *(info.)* | — | 174,2 (—) | 174,1 (—) | 174,1 (—) | 174,0 (—) | -0,1 % | -0,1 % | -0,0 % |
| C4 | ELU (114) | 253 | 259,4 (+2,5 %) | 259,2 (+2,4 %) | 259,2 (+2,4 %) | 259,0 (+2,4 %) | -0,1 % | -0,1 % | -0,0 % |
| C5 | ELS_f (111) *(info.)* | — | 202,4 (—) | 202,1 (—) | 202,1 (—) | 201,8 (—) | -0,1 % | -0,2 % | -0,0 % |
| C5 | ELS_c (111) *(info.)* | — | 294,3 (—) | 293,9 (—) | 293,9 (—) | 293,5 (—) | -0,1 % | -0,1 % | -0,0 % |
| C5 | ELU (111) | 463 | 435,5 (-5,9 %) | 434,9 (-6,1 %) | 434,9 (-6,1 %) | 434,2 (-6,2 %) | -0,1 % | -0,1 % | -0,0 % |
| C6 | ELS_f (105), total barre + dalle | 180 | 215,0 (+19,5 %) | 215,1 (+19,5 %) | 194,1 (+7,8 %) | 194,5 (+8,0 %) | +0,1 % | -9,7 % | +0,1 % |
| C6 | ELS_c (105), total barre + dalle | 276 | 323,1 (+17,1 %) | 323,3 (+17,1 %) | 292,2 (+5,9 %) | 292,9 (+6,1 %) | +0,1 % | -9,5 % | +0,1 % |
| C6 | ELU (112), total barre + dalle | 408 | 473,2 (+16,0 %) | 472,8 (+15,9 %) | 429,3 (+5,2 %) | 429,6 (+5,3 %) | -0,0 % | -9,2 % | +0,1 % |
| C7 | ELU (enveloppe 100-115), total barre + dalle | 177 | 177,7 (+0,4 %) | 177,3 (+0,2 %) | 186,0 (+5,1 %) | 185,8 (+5,0 %) | -0,2 % | +4,7 % | +0,0 % |
| C7 | ELS_f (enveloppe 100-115), total barre + dalle *(info.)* | 177 | 99,7 (-43,7 %) | 99,7 (-43,7 %) | 102,0 (-42,4 %) | 102,2 (-42,3 %) | +0,1 % | +2,4 % | +0,1 % |
| C7 | ELS_c (enveloppe 100-115), total barre + dalle *(info.)* | 177 | 125,8 (-29,0 %) | 125,5 (-29,1 %) | 131,3 (-25,8 %) | 131,1 (-25,9 %) | -0,2 % | +4,4 % | +0,0 % |
| C8 | ELU (105, 112), total barre + dalle, toutes lignes | 653 | 722,5 (+10,6 %) | 733,3 (+12,3 %) | 700,9 (+7,3 %) | 715,8 (+9,6 %) | +1,8 % | -2,7 % | +0,3 % |
| C8 | ELU (105, 112), total barre + dalle, hors Y = ±2,00 *(info.)* | 653 | 722,5 (+10,6 %) | 733,3 (+12,3 %) | 700,9 (+7,3 %) | 715,8 (+9,6 %) | +1,8 % | -2,7 % | +0,3 % |
| C8 | ELS_f (105, 112), total barre + dalle, toutes lignes *(info.)* | 653 | 349,4 (-46,5 %) | 355,6 (-45,5 %) | 337,7 (-48,3 %) | 345,9 (-47,0 %) | +2,1 % | -3,1 % | +0,3 % |
| C8 | ELS_f (105, 112), total barre + dalle, hors Y = ±2,00 *(info.)* | 653 | 349,4 (-46,5 %) | 355,6 (-45,5 %) | 337,7 (-48,3 %) | 345,9 (-47,0 %) | +2,1 % | -3,1 % | +0,3 % |
| C8 | ELS_c (105, 112), total barre + dalle, toutes lignes *(info.)* | 653 | 500,5 (-23,3 %) | 508,2 (-22,2 %) | 485,3 (-25,7 %) | 495,8 (-24,1 %) | +1,8 % | -2,8 % | +0,3 % |
| C8 | ELS_c (105, 112), total barre + dalle, hors Y = ±2,00 *(info.)* | 653 | 500,5 (-23,3 %) | 508,2 (-22,2 %) | 485,3 (-25,7 %) | 495,8 (-24,1 %) | +1,8 % | -2,8 % | +0,3 % |
| C6 | ELS_f (105), barre seule *(info.)* | 180 | 202,8 (+12,7 %) | 203,3 (+12,9 %) | 177,1 (-1,6 %) | 178,0 (-1,1 %) | +0,3 % | -12,6 % | +0,1 % |
| C6 | ELS_c (105), barre seule *(info.)* | 276 | 303,2 (+9,9 %) | 304,2 (+10,2 %) | 265,1 (-3,9 %) | 266,7 (-3,4 %) | +0,4 % | -12,5 % | +0,1 % |
| C6 | ELU (112), barre seule *(info.)* | 408 | 443,1 (+8,6 %) | 443,1 (+8,6 %) | 388,6 (-4,8 %) | 389,4 (-4,6 %) | +0,1 % | -12,2 % | +0,1 % |
| C7 | ELU (enveloppe 100-115), barre seule *(info.)* | 177 | 141,9 (-19,8 %) | 154,8 (-12,5 %) | 146,7 (-17,1 %) | 160,1 (-9,5 %) | +9,3 % | +3,5 % | +0,2 % |
| C7 | ELS_f (enveloppe 100-115), barre seule *(info.)* | 177 | 79,3 (-55,2 %) | 86,5 (-51,2 %) | 79,8 (-54,9 %) | 87,2 (-50,7 %) | +9,1 % | +0,7 % | +0,2 % |
| C7 | ELS_c (enveloppe 100-115), barre seule *(info.)* | 177 | 100,3 (-43,3 %) | 109,4 (-38,2 %) | 103,3 (-41,7 %) | 112,8 (-36,3 %) | +9,3 % | +3,2 % | +0,2 % |
| C8 | ELU (105, 112), barre seule, toutes lignes *(info.)* | 653 | 198,1 (-69,7 %) | 660,8 (+1,2 %) | 172,6 (-73,6 %) | 635,2 (-2,7 %) | +233,6 % | -12,9 % | -0,1 % |
| C8 | ELU (105, 112), barre seule, hors Y = ±2,00 *(info.)* | 653 | 198,1 (-69,7 %) | 659,0 (+0,9 %) | 172,6 (-73,6 %) | 633,6 (-3,0 %) | +232,7 % | -12,8 % | -0,0 % |
| C8 | ELS_f (105, 112), barre seule, toutes lignes *(info.)* | 653 | 94,9 (-85,5 %) | 323,1 (-50,5 %) | 82,5 (-87,4 %) | 309,8 (-52,6 %) | +240,0 % | -13,6 % | -0,5 % |
| C8 | ELS_f (105, 112), barre seule, hors Y = ±2,00 *(info.)* | 653 | 94,9 (-85,5 %) | 321,8 (-50,7 %) | 82,5 (-87,4 %) | 308,6 (-52,7 %) | +238,7 % | -13,5 % | -0,4 % |
| C8 | ELS_c (105, 112), barre seule, toutes lignes *(info.)* | 653 | 137,1 (-79,0 %) | 458,5 (-29,8 %) | 119,5 (-81,7 %) | 440,6 (-32,5 %) | +234,3 % | -13,0 % | -0,1 % |
| C8 | ELS_c (105, 112), barre seule, hors Y = ±2,00 *(info.)* | 653 | 137,1 (-79,0 %) | 457,1 (-30,0 %) | 119,5 (-81,7 %) | 439,4 (-32,7 %) | +233,4 % | -12,9 % | -0,0 % |
| C9 | ELS_f (111) | 79 | 70,7 (-10,6 %) | 70,8 (-10,4 %) | 70,2 (-11,1 %) | 70,4 (-10,9 %) | +0,3 % | -0,6 % | +0,0 % |
| C9 | ELS_c (111) | 118 | 105,4 (-10,7 %) | 105,1 (-10,9 %) | 104,1 (-11,8 %) | 104,3 (-11,6 %) | +0,0 % | -1,0 % | +0,2 % |
| C9 | ELU (111) | 174 | 156,2 (-10,3 %) | 155,8 (-10,5 %) | 154,2 (-11,4 %) | 154,5 (-11,2 %) | -0,0 % | -1,0 % | +0,2 % |
| C10 | ELS_f (112) | 82 | 81,9 (-0,1 %) | 81,9 (-0,1 %) | 82,0 (+0,0 %) | 82,0 (+0,0 %) | -0,0 % | +0,1 % | -0,0 % |
| C10 | ELS_c (112) | 134 | 130,8 (-2,4 %) | 130,8 (-2,4 %) | 131,0 (-2,2 %) | 131,0 (-2,2 %) | +0,0 % | +0,2 % | +0,0 % |
| C10 | ELU (112) | 198 | 192,9 (-2,6 %) | 192,9 (-2,6 %) | 193,1 (-2,4 %) | 193,2 (-2,4 %) | +0,0 % | +0,1 % | +0,0 % |
| C11 | FR seul | 18,9 | 19,7 (+4,2 %) | 19,7 (+4,2 %) | 19,7 (+4,2 %) | 19,7 (+4,2 %) | +0,0 % | +0,0 % | +0,0 % |
| C11 | TE- seul | 64,1 | 62,9 (-1,9 %) | 62,8 (-2,1 %) | 62,7 (-2,1 %) | 62,6 (-2,3 %) | -0,2 % | -0,2 % | -0,0 % |
| C12 | ELU courant (111) | 320 | 351,4 (+9,8 %) | 342,9 (+7,1 %) | 341,2 (+6,6 %) | 338,9 (+5,9 %) | -1,5 % | -2,0 % | +0,9 % |
| C12 | ELU rive (100) | 568 | 222,1 (-60,9 %) | 245,4 (-56,8 %) | 213,3 (-62,5 %) | 243,8 (-57,1 %) | +12,1 % | -2,3 % | +1,6 % |
| C12 | ELU rive, dans les disques compris (100) *(info.)* | 568 | 1 430,9 (+151,9 %) | 325,8 (-42,6 %) | 1 465,0 (+157,9 %) | 344,5 (-39,4 %) | -77,8 % | +1,8 % | -0,5 % |
| C12 | ELU rive (100), TR = 5 kPa seul (charge de v1) *(info.)* | 568 | 100,4 (-82,3 %) | 107,1 (-81,2 %) | 97,3 (-82,9 %) | 105,7 (-81,4 %) | +7,5 % | -2,2 % | +0,8 % |
| C13 | LM1 Mxx inf. | 85 | 83,6 (-1,6 %) | 83,7 (-1,5 %) | 83,9 (-1,3 %) | 84,0 (-1,2 %) | +0,1 % | +0,3 % | +0,0 % |
| C13 | LM1 Mxx sup. | -47 | -54,6 (-16,2 %) | -54,1 (-15,0 %) | -53,7 (-14,3 %) | -53,3 (-13,4 %) | +0,9 % | +1,5 % | -0,1 % |
| C13 | LM1 V (|Qxx|) | 154 | 205,0 (+33,1 %) | 193,0 (+25,3 %) | 200,7 (+30,4 %) | 190,5 (+23,7 %) | -5,4 % | -1,7 % | +0,4 % |
| C13 | LM2 Mxx inf. | 64 | 64,4 (+0,6 %) | 64,5 (+0,7 %) | 64,5 (+0,8 %) | 64,6 (+0,9 %) | +0,1 % | +0,2 % | +0,0 % |
| C13 | LM2 Mxx sup. | -30 | -26,2 (+12,7 %) | -25,8 (+13,9 %) | -25,5 (+15,1 %) | -25,3 (+15,5 %) | +0,9 % | +2,3 % | -0,5 % |
| C13 | LM2 V (|Qxx|) | 138 | 134,8 (-2,3 %) | 131,7 (-4,6 %) | 131,7 (-4,5 %) | 130,0 (-5,8 %) | -1,8 % | -1,8 % | +0,5 % |

### 6.5 Dépendance au maillage des grandeurs locales (critère du § 3.4)

Configuration SH ; même lecture v2 (disques de 0,60 m, combinaison 100 avec E18).

| Point | Ligne | Source | h = 0,05 | h = 0,25 | h = 0,50 | Variation max | Rejoint la source à | Comparabilité |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C9 | ELS_f (111) | 79 | 70,4 (-10,9 %) | 57,1 (-27,8 %) | 49,5 (-37,3 %) | 29,7 % | aucune | non comparable sans le maillage source |
| C9 | ELS_c (111) | 118 | 104,3 (-11,6 %) | 80,0 (-32,2 %) | 65,4 (-44,6 %) | 37,3 % | aucune | non comparable sans le maillage source |
| C9 | ELU (111) | 174 | 154,5 (-11,2 %) | 118,1 (-32,1 %) | 95,0 (-45,4 %) | 38,5 % | aucune | non comparable sans le maillage source |
| C12 | ELU rive (100) | 568 | 243,8 (-57,1 %) | 211,3 (-62,8 %) | 165,4 (-70,9 %) | 32,1 % | aucune | non comparable sans le maillage source |
| C13 | LM1 Mxx inf. | 85 | 84,0 (-1,2 %) | 81,1 (-4,5 %) | 74,4 (-12,5 %) | 11,4 % | 0,05, 0,25 | non comparable sans le maillage source |
| C13 | LM1 Mxx sup. | -47 | -53,3 (-13,4 %) | -43,5 (+7,4 %) | -40,9 (+13,0 %) | 23,2 % | 0,25 | non comparable sans le maillage source |
| C13 | LM1 V (|Qxx|) | 154 | 190,5 (+23,7 %) | 133,7 (-13,2 %) | 95,1 (-38,2 %) | 50,1 % | aucune | non comparable sans le maillage source |
| C13 | LM2 Mxx inf. | 64 | 64,6 (+0,9 %) | 61,4 (-4,0 %) | 53,0 (-17,2 %) | 17,9 % | 0,05, 0,25 | non comparable sans le maillage source |
| C13 | LM2 Mxx sup. | -30 | -25,3 (+15,5 %) | -19,7 (+34,3 %) | -18,8 (+37,2 %) | 25,7 % | aucune | non comparable sans le maillage source |
| C13 | LM2 V (|Qxx|) | 138 | 130,0 (-5,8 %) | 99,8 (-27,7 %) | 58,0 (-58,0 %) | 55,4 % | 0,05 | non comparable sans le maillage source |

Lieux (X, Y ; cas) : C9 est lu à (30,55 ; 1,40) au bord du disque de la tête F7_YP à
0,05 m, puis au **bord libre Y = 3,00** à 0,25 et 0,50 m (déduction : l'extremum fin, proche de la
tête, n'est plus représenté hors du disque de 0,60 m sur un maillage grossier) ; C12 « rive » à (4,85 ; 3,00) ou
(5,10 ; 3,00), au bord libre, position TRE_M25 sur les trois maillages ; C13 « V » à
X = 5,1 à 5,45, au bord d'empreinte de TS bord de voie.

**Conclusion, selon le critère écrit avant :** les dix lignes locales sont **non comparables
sans le maillage source**. Leur valeur varie de 11 à 55 % entre 0,05 et 0,50 m, quand la
tolérance est de 10 %. Motifs : extremum au voisinage d'un appui ponctuel pour C9 et C13
« sup. », effort tranchant sous une charge de roue concentrée pour C12 « rive » et C13
« V », étalement de la charge sur une maille plus grande que l'empreinte à 0,25 et 0,50 m.
Seules C13 « sup. » LM1 (à 0,25 m) et les lignes déjà dans la tolérance à 0,05 m rejoignent
la source à une taille donnée. Cette taille n'est pas tenue pour celle de la source. Deux
lignes dans la tolérance à 0,05 m (C13 « inf. » LM1 et LM2) sont aussi classées non
comparables par ce critère : leur concordance est un fait, sa robustesse au maillage n'est
pas établie.

### 6.6 Attribution des écarts (méthode du § 4)

Une ligne par ligne jugée v2 (30), verdict v2 de la référence R. « Aucun écart » : dans la
tolérance ; la cause de l'écart v1 (lot 47) est rappelée quand il y en avait un.

| Point | Ligne | R (v2) | Catégorie retenue | Preuve chiffrée |
| --- | --- | --- | --- | --- |
| C1 | ELS c (107) | 0,4375 cm, compatible avec l'arrondi | aucun écart (D : valeur source arrondie au demi-centimètre, annexe B) | 0,4375 dans les quatre configurations |
| C2 | ELS f, ELS c, ELU (112) | +2,5 / −1,8 / −2,4 % | aucun écart (D : la source donne aussi 554, 767, 1 102 kN, annexe B) | avec 0,80 m, −3,2 et −3,8 % en ELS c et ELU (poids −126 kN) |
| C3 | ELS f, ELU (111) | −3,2 / −3,0 % | aucun écart (v1 : A, lieu de lecture à +0,70, lot 47 bis) | v1 −37 % → v2 −3 % |
| C3 | ELS c (111) | −5,7 % | **G, inexpliqué** | effets DST et 0,80 m ≤ 0,2 point ; grandeur de barre, sans singularité ; rapport ELS c / ELU : source 0,695, Code_Aster 0,676 |
| C4 | ELU (114) | +2,5 % | aucun écart | — |
| C5 | ELU (111) | −5,9 % | **G, inexpliqué** | effets ≤ 0,1 point ; le maximum de tout le pieu est en tête (C5 = C3 ELU = 435,5) quand la source publie 463 ≠ 449 sous la même combinaison : lieu de C5 dans la source inconnu |
| C6 | ELS f, ELS c, ELU (105, 112), total | +19,5 / +17,1 / +16,0 % | **C (E2, chevêtre de 0,90 m ; D : incohérence I2 de la source) et A (E17.2 compare le total, la source publie la barre)** | barre seule avec 0,80 m : −1,6 / −3,9 / −4,8 % (H), −1,1 / −3,4 / −4,6 % (SH) ; effet 0,80 m −12,2 à −12,6 points ; total avec 0,80 m encore +5,2 à +8,0 % |
| C7 | ELU (100-115), total | +0,4 % | aucun écart (v1 : A, barre seule d'un modèle DKT, lot 47 bis) | en lecture barre seule, SH −9,5 % : **G** pour cette lecture (effets DST +9,3, 0,80 m +3,5 points) |
| C8 | ELU (105, 112), total | +10,6 % | **C (E13, dalle DKT) et A (E17.2)** | barre seule en DST : +1,2 % (S), −2,7 % (SH) ; en DKT −69,7 % ; total en DST +12,3 % |
| C9 | ELS f, ELS c, ELU (111) | −10,6 / −10,7 / −10,3 % | **E, maillage** | variation 30 à 39 % entre 0,05 et 0,50 m (§ 6.5) ; effets des deux facteurs ≤ 1 point |
| C10 | ELS f, ELS c, ELU (112) | −0,1 / −2,4 / −2,6 % | aucun écart | — |
| C11 | FR, TE− | +4,2 / −1,9 % | aucun écart (v1 : A, maximum nodal au lieu de la moyenne de section, E17.4) | v1 +211 / +133 % |
| C12 | ELU courant (111) | +9,8 % | aucun écart | SH +5,9 % |
| C12 | ELU rive (100) | −60,9 % | **E, maillage** (v1 : B, essieu de trottoir omis, E18) | variation 32 % ; la source a appliqué l'essieu en charges ponctuelles (E18) ; 0,05 m le plus proche de la source, les maillages grossiers s'en éloignent |
| C13 | LM1 Mxx inf. | −1,6 % | aucun écart | variation 11 % entre maillages (non comparable au sens du § 3.4) |
| C13 | LM1 Mxx sup. | −16,2 % | **E, maillage** | variation 23 % ; rejoint la source à 0,25 m (+7,4 %) ; lu à 0,60 m de la tête F2_YP, au bord du disque |
| C13 | LM1 V | +33,1 % | **E, maillage** | variation 50 % ; lu au bord d'une empreinte de TS |
| C13 | LM2 Mxx inf. | +0,6 % | aucun écart | variation 18 % |
| C13 | LM2 Mxx sup. | +12,7 % | **E, maillage** | variation 26 % ; ne rejoint la source à aucune taille |
| C13 | LM2 V | −2,3 % | aucun écart | variation 55 % |

Bilan des 13 lignes hors tolérance de R : **4 en C et A** (C6 × 3, C8 : chevêtre, formulation de
la dalle et grandeur comparée), **7 en E** (C9 × 3, C12 « rive », C13 LM1 « sup. », LM1 « V »,
LM2 « sup. »), **2 en G** (C3 ELS c, C5). **Aucune en F** : aucune erreur de notre modèle n'est
démontrée. Les contrôles D de toutes les exécutions sont réussis (résultantes à 1e-11 et
mieux), la référence se régénère à l'octet et les globales concordent dans les quatre
configurations. Aucune en B après E18.

Pistes examinées pour les deux lignes G :
- formulation de la dalle et hauteur du chevêtre (effets ≤ 0,2 point) ;
- maillage : grandeurs de barre, sans singularité ;
- lieu de lecture : maximum en tête, comme le dit la source (§20.3.2 cité au lot 47 bis) ;
- famille : ELU+ gouverne.

Non examinées faute de données : coefficients de la combinaison 111 ELS c dans la source,
ressorts de la source en tête de pieu (la file 7 porte des ressorts dès +1,00 m), section
du tronçon de tête (E3).

### 6.7 Bilan des erreurs de l'outil (agent et superviseur) depuis le lot 47

| N° | Lot | Auteur | Erreur | Effet | Ce qui l'empêche désormais |
| --- | --- | --- | --- | --- | --- |
| 1 | 47 | agent | Cote erronée dans la description de l'option LM2 proposée à MM | signalée, règle appliquée juste | aucune règle nouvelle ; la fiche porte la décision de MM (E16) |
| 2 | 47 | agent | `CREA_GROUP_NO` à plusieurs `GROUP_MA` alors que DIAG-010 le décrivait (base non consultée par commande) | 1ʳᵉ exécution de production arrêtée | skill § 6 quater, point 1 (consultation par commande) ; test du générateur |
| 3 | 47 | agent et superviseur | C3 et C5 lus à +0,70 et −2,50 m au lieu de la tête ; lieu omis dans les critères | écarts de −37 et −77 % | skill § 6 sexies (lieu, composante, famille déclarés avant exécution) ; E17.1 |
| 4 | 47 | agent | C11 lu en maximum nodal au lieu de la moyenne de section | +211 % | E17.4 ; skill § 6 sexies |
| 5 | 47 | agent | C9, C12, C13 lus au nœud singulier de la tête de pieu | jusqu'à +380 % | PAT-013, CTL-014 ; disques d'E17.3 |
| 6 | 47 | agent | C7 et C8 lus sur la barre seule d'un modèle DKT | −20 et −70 % | CA-058 (lot 47 bis), domaine DKT/DST précisé ici |
| 7 | 47 | superviseur | Essieu de trottoir de la combinaison 100 omis dans B4 | C12 « rive » | E18 |
| 8 | 47 | outil | Écart relatif NaN des cas autoéquilibrés (CTL-005, CTL-013) | niveau D refusé | CTL-005 et CTL-013 version 2 (lot 47 bis) |
| 9 | 47 bis | superviseur | Diagnostic (b) : total C8 annoncé à +2 %, retrouvé à +7,2 % | conclusion retenue sur le total | relecture chiffrée de chaque diagnostic (§ 8 du lot 47 bis) ; la factorielle montre que la source publie la barre (§ 6.3) |
| 10 | 47 bis | agent et superviseur | E17.2 compare le total barre + dalle ; la grandeur publiée par la source est l'effort de barre d'un modèle à dalle de type DST | C6 et C8 v2 hors tolérance | CA-058 (domaine précisé) ; précédent proposé (`docs/lots/lot47ter_proposition_precedent.md`) |
| 11 | 47 bis | outil | `search_connaissances` en panne toute la session (schéma modifié en cours de session) | consultations par contournement | ENV-002 ; `connaissances.fraicheur` et son test |
| 12 | 47 bis, 47 ter | agent | `aster-expert run` appelé sur l'`.export` (refusé : `.comm` attendu) | aucun (refus avant exécution) | script du lot qui imprime la commande |
| 13 | 47 ter | outil | Copies de lecture MED jamais effacées : disque plein, deux exécutions perdues, comptes rendus vides, `rex` arrêté | 2 exécutions, ≈ 10 min | ENV-003 ; `run_then_drop_copy`, `take_arrays`, `rex` tolérant, `env-check` disque ; tests |
| 14 | 47 ter | agent | N1 relancée sans `--timeout` (délai par défaut 1 800 s) | 30 min perdues | DIAG-025 ; script qui imprime la commande avec ses limites |
| 15 | 47 ter | agent | Blocs `DEFI_GROUP` et `FORCE_COQUE` du maillage grossier écrits sans consulter la base par commande ; consultation faite après les exécutions N3, N4 | aucun (aucune entrée contredite : DIAG-002 respecté par `_gn`, DIAG-010 hors sujet) | skill § 6 quater, point 1 ; **non évitée** par la règle existante |
| 16 | 47 ter | agent | Une lecture JSON lancée avec le `python3` du système (CLAUDE.md : `.venv` seul) | aucun (échec de lecture d'un fichier vide) | CLAUDE.md ; **non évitée** par la règle existante |

### 6.8 Capitalisation

- **ENV-002** (étape 0), **ENV-003** (disque plein), **DIAG-025** (délai par défaut) : nouveaux
  diagnostics, rattachés aux trois échecs du lot dans `connaissances/rex/estacade_pieux_01.yaml`.
- **CA-058** : domaine de validité précisé dans ses notes (DKT : la dalle porte l'effort
  tranchant près de l'appui ; DST : la barre en porte 90 %), sans changer ses sources ni
  son niveau ; régénéré par `scripts/constats_lot47bis.py`.
- **Précédent proposé** (non tranché, non versé dans `precedents/` : le schéma exige la
  décision de MM) : `docs/lots/lot47ter_proposition_precedent.md`.
- Aucune promotion.

### 6.9 Limites

- **Contre-calcul d'un modèle non validé**, jamais un niveau E. Les variantes S, H, SH sont
  des variantes de sensibilité ; la référence reste R (E1 à E19).
- Le critère de conclusion du § 2.4 est écrit après lecture de R, S et H (chiffres connus,
  cités par la consigne), avant N1 seulement.
- L'étape 2 ne porte que sur des maillages **plus grossiers** que la production, avec une
  charge de roue étalée sur des mailles plus grandes que l'empreinte ; elle montre la
  sensibilité, pas la valeur convergée. Le maillage de la source reste inconnu.
- Les chiffres de l'estacade cités dans CA-058 et dans le précédent proposé ne sont pas
  imprimés dans un listing versionné : ils restent des observations (notes), pas des sources.
- `aster-expert run` ne lit pas les limites de l'`.export` (DIAG-025, choix assumé : lecture
  réservée à `run_aster.export`).

### 6.10 Retour d'expérience et contrôles de fin de lot

Sortie de `aster-expert rex estacade_pieux_01` (avant `--enregistrer --lot 47ter` et
`--manifeste`, archive de 27 exécutions enregistrée) :

```text
Retour d'expérience du projet estacade_pieux_01
Exécutions attribuées au projet : 27 ; échecs : 7 ; depuis le dernier retour d'expérience (2026-10-05) : 3.
Développement : 23 exécution(s), 7 échec(s), taux 30,4 % ; vérification : 4 exécution(s), 0 échec(s) (hors taux).
Classement : nouveau 3, rattaché 4.
Diagnostic retrouvé automatiquement par la base (seul et égal au classement) : 5/7 échecs rattachés.
Répartition par cause : DIAG-003 3, DIAG-010 1, DIAG-025 1, ENV-003 2.
Constats de la fiche à verser dans la base : 0.
Candidats patrons dans le code du projet : 2 (similarité ≥ 0,40 ; 9 fonction(s) sous le seuil, non listées).
  projets/estacade_pieux_01/generation.py:fractional_loads_block — proche d'un patron (PAT-005, similarité 0.5)
  projets/estacade_pieux_01/generation.py:moving_loads_block — proche d'un patron (PAT-005, similarité 0.5)
Connaissances créées par le projet : 18 ; promues : 0.
Consultations journalisées (tous projets) : search_connaissances 35, search_constats 3.
Tous les échecs sont classés : clôture possible.
Métriques : connaissances/metriques/estacade_pieux_01.yaml
Tableau de bord : connaissances/metriques/tableau_de_bord.md
```

Interventions de MM pendant le lot : **1** (accord pour supprimer les copies de travail des
lectures MED, avec ses conditions) ; une question sur l'avancement de N1, sans effet sur le
contenu.

| Commande | Résultat |
| --- | --- |
| `aster-expert env-check` | OK, profil vm, 9 vérifications (disque : 25,2 Go libres en cours de lot) |
| `aster-expert mcp-check` | OK, 9 outils sur un serveur neuf |
| `ruff format --check .` ; `ruff check .` | 536 fichiers formatés ; aucune erreur |
| `mypy src` ; `mypy` | aucune erreur (131 et 382 fichiers) |
| `pytest` (série par défaut) | 1 604 réussis, 4 désélectionnés |
| `pytest -m lent` | 4 réussis (Code_Aster et Salomé réels) |
| `aster-expert connaissances verifier` | OK |
| `aster-expert etat verifier` | cohérent |
| `aster-expert projet exporter-resultats estacade_pieux_01` | niveau D, 16 fichiers ; critère D du lot 47 bis signalé « antériorité non démontrable » (inchangé) |
| `aster-expert note controler estacade_pieux_01` | OK pour les deux notes |

**Outils MCP** : `search_connaissances` et `search_constats` ont changé de code (rechargement
du schéma, ENV-002). Leur interface est inchangée. **Redémarrer la session avant le lot
suivant.**
