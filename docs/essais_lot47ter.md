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
