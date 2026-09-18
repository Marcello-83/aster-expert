# Plan de développement

Un lot par session et par branche Git. Un lot n'est pas terminé sans ses
critères de sortie. Aucun lot n'anticipe le suivant.

Périmètre de la version 1 : recherche documentaire, schémas de commandes,
validation statique, exécution encadrée et dépouillement `.mess`. La
comparaison aux références V et le banc de non-régression complet sont hors
périmètre v1 mais le jeu d'évaluation de la recherche, lui, est requis tôt.

---

## Lot 1 — Initialisation du dépôt

Squelette, `CLAUDE.md`, documentation d'architecture, configuration, packaging,
outillage qualité.

Critères de sortie : `pip install -e ".[dev]"` fonctionne, `ruff` et `mypy`
passent sur un squelette vide, `pytest` s'exécute sans test en échec, `aster-expert --help` répond.

## Lot 2 — Détection de l'environnement Aster

`aster-expert env detect`. Localisation de `run_aster`, du Python d'Aster et du
package `code_aster`. Écriture de la section `detected` de
`config/versions.yaml`.

Ne suppose aucun chemin. Échoue explicitement si l'environnement n'est pas
trouvé.

Critères de sortie : détection réussie sur l'installation réelle, sortie
consignée dans le compte rendu de lot ; tests unitaires sur environnement
simulé, sans dépendance à une installation.

## Lot 3 — Synchronisation Git versionnée

`aster-expert sources sync`. Clonage ou mise à jour des dépôts déclarés dans
`config/sources.yaml`, refus d'écraser des modifications locales, production du
manifeste.

Critères de sortie : idempotence vérifiée par test, manifeste conforme,
tests unitaires sur dépôts Git temporaires locaux sans réseau.

**Note (réconciliation, interprétation retenue pour `update_policy`).**
`fetch_and_checkout`/`pinned` ne `checkout`/`reset` jamais une copie de
travail déjà présente : soit elle correspond exactement à ce que `ref`
résout sur le dépôt distant après `fetch` (adoptée telle quelle,
`status: "adopted"`), soit elle en diverge et la synchronisation s'arrête
pour cette source (`status: "blocked_diverged"`), signalée dans le
manifeste, jamais corrigée d'autorité. Seul un premier clonage (source
absente) checkout réellement `ref` — une action de création d'état unique,
pas une correction d'une copie de travail existante. `fetch_only` fetch sans
jamais comparer ni bloquer. Conséquence pour l'idempotence testée
(`tests/unit/test_sources_sync.py::test_sync_idempotent_across_two_consecutive_runs`) :
elle porte sur deux exécutions consécutives sur une source déjà présente et
à jour (`"adopted"`), jamais sur la comparaison d'un premier clonage à une
absence de dépôt, qui n'a pas de sens (`docs/corpus.md` §5, amendement lot 3).

**Note (réconciliation de `codeaster-src`, constat concret).** La copie de
travail clonée à la main au lot 2 était en réalité déjà exactement conforme
à la déclaration : le seul écart était que `config/sources.yaml` déclarait
le sha de l'**objet tag annoté** `17.4.0` lui-même
(`961aacdfe6d316a88708143c02523dc3dd443432`, `git cat-file -t` confirme
`"tag"`), pas le commit vers lequel ce tag pointe une fois « peelé »
(`50ebc13c70ee9df62faf93ddcb746a3757b3042a`, `git rev-parse 17.4.0^{commit}`) —
qui est exactement le commit réellement extrait par la copie de travail.
`aster_expert.ingestion.git_client` compare donc toujours des commits
peelés (`peel_to_commit`, `current_commit`, `resolve_local_ref_commit`),
jamais un sha brut. `config/sources.yaml` corrigé en conséquence (commit
peelé, commentaire explicatif) ; aucune copie de travail n'a jamais divergé.

**Note (correspondance de version documentaire, `config/versions.yaml`).**
Établie par `git ls-remote --tags https://gitlab.com/codeaster/doc/docaster.git`
(aucun clone, aucun objet transféré) : le dépôt tague ses sorties
17.0, 17.2.0, 17.3.0, 17.4.0, 18.1.0, smeca2024.0 — un tag nommé
exactement `17.4.0` existe, dans le même dépôt GitLab `codeaster` que
`codeaster-src`, qui tague lui aussi ses sorties à l'identique. Ce n'est
jamais présenté comme une similitude de numérotation déduite : c'est le
même nom de tag, dans deux dépôts de la même organisation, pour ce qui est
de part et d'autre une sortie de version. `codeaster-doc` est donc
synchronisé sur `ref: "17.4.0"` (plus `main`, qui n'a jamais servi de
corpus, même raison que `codeaster-src` au lot 2) ; correspondance
consignée dans `config/versions.yaml`, section `versions`, avec sa preuve.
Aucun changelog croisé consulté pour confirmer au-delà de la convention de
nommage commune : à réviser sur preuve contraire.

**Observation de clôture — structure du corpus `codeaster-doc` (17.4.0),
sans parsing ni découpage (périmètre du lot 6).**

- Racine : `README.md`, `CONTRIBUTING.md`, `LICENSE.txt`, `questions.md`,
  `doc_build.sh`, `makefile`, `pyproject.toml`, `.readthedocs.yaml`,
  `.gitlabci/`, `data/` (gabarits, hooks git, `Dockerfile`), et `source/`
  (le contenu documentaire). Deuxième niveau de `source/` :
  `source/manuals/` (les familles), `source/_static/`, `source/_templates/`.
- Familles constatées sous `source/manuals/` : `man_u`, `man_r`, `man_v`,
  `man_d` (les quatre attendues par `docs/corpus.md` §3) **et `man_s`**, non
  anticipée par la classification attendue — à qualifier au lot 6, pas
  deviné ici. Chaque famille se subdivise en sous-répertoires numérotés
  (`man_u/u4`, `man_r/r5`, `man_v/v3`, ...), plus un `other_pages` par
  famille.
- Extensions et décompte (fichiers, hors `.git/`) : 13128 `.rst`, 5955
  `.svg`, 4199 `.png`, 772 `.gif`, 497 `.jpg`, 15 `.tif`, 12 `.tpl`, 5 `.py`,
  3 `.md`, 3 `.html`, 2 `.txt`, 2 `.eps`, 1 `.yaml`, 1 `.toml`, 1 `.json`,
  1 `.css`, 1 `.def`, quelques fichiers sans extension (`makefile`, hooks
  git sous `data/`, `Dockerfile`). Le contenu documentaire est donc du texte
  structuré (reStructuredText) accompagné d'images vectorielles et
  matricielles, jamais un traitement de texte ni un document composé — la
  question ouverte au §2 de `docs/corpus.md` (point 3) est tranchée dans ce
  sens par ce seul constat, sans qu'aucun parseur n'ait été écrit.
- Trois documents examinés individuellement :
  - `source/manuals/man_u/u4/u4.84.01/` (opérateur `COMB_SISM_MODAL`) :
    répertoire par document, `index.rst` (label reST `.. _u4.84.01:`,
    titre, `toctree`) plus une section par fichier (`But.rst`,
    `Syntaxe.rst`, `Op_randes.rst`, `Concept_en_sortie.rst`,
    `Bibliographie.rst`).
  - `source/manuals/man_v/v3/v3.03.100/` (cas de validation SSLS100,
    plaque circulaire encastrée) : même schéma, label `.. _V3.03.100:`,
    sections par modélisation (`Mod_lisation_A.rst` … `Mod_lisation_N.rst`),
    `Synth_se_des_r_sultats.rst`.
  - `source/manuals/man_r/r7/r7.01.03/` (loi de comportement
    `BETON_DOUBLE_DP`) : même schéma, label `.. _R7.01.03:`, sections
    théoriques (`Notations.rst`, `Ecoulement_plastique.rst`,
    `Int_gration_num_rique_de_la_loi_de_comportement.rst`, ...).
  - Dans les trois cas : un identifiant documentaire (U4.84.01, V3.03.100,
    R7.01.03) apparaît à la fois dans le nom du répertoire et comme label
    reST en tête de `index.rst` — jamais seulement l'un des deux.
- Procédure de construction d'un rendu : présente et documentée
  (`README.md`, `doc_build.sh`, `makefile`) — Sphinx, trois builders au
  choix (conteneur Singularity par défaut, environnement Pixi, ou venv
  Python), invocation `./doc_build.sh html`. Le `README.md` chiffre
  lui-même le coût : « ~2500 documents », « ~1.5 GB de pages html »,
  « ~5 min (x2) avec 16 tâches en parallèle ».
- Rendu déjà construit : **absent**. Aucun répertoire `_build` (ni tout
  autre répertoire de sortie) dans la copie de travail synchronisée : le
  rendu HTML n'existe que s'il est explicitement construit, jamais livré
  avec le dépôt.
- Identifiants documentaires U/R/V/D : **présents**, de façon systématique
  et cohérente, à la fois dans les noms de répertoires (`u4.84.01`,
  `r7.01.03`, `v3.03.100`, et la famille `d0`…`d9` vérifiée par simple
  listage) et dans le contenu (label reST `.. _<ID>:` en tête de chaque
  `index.rst`). Casse du label non uniforme entre les trois échantillons :
  minuscule pour `u4.84.01` (`.. _u4.84.01:`), majuscule pour `v3.03.100`
  et `r7.01.03` (`.. _V3.03.100:`, `.. _R7.01.03:`) — le nom de répertoire,
  lui, est systématiquement en minuscule dans les trois cas. À confirmer
  plus largement au lot 6, jamais supposé uniforme sur ce seul échantillon
  de trois documents.
- Taille de la copie de travail synchronisée : 779 Mio au total (259 Mio
  pour `.git`, clone partiel `--filter=blob:none` sur un seul tag), 24604
  fichiers de contenu (`find -type f`, hors `.git/`) — cohérent avec le
  chiffre annoncé par `README.md`.

Aucun parseur écrit, aucun découpage tenté, aucune conclusion sur la
stratégie du lot 6 : ce relevé est un constat, l'arbitrage revient à
l'utilisateur.

## Lot 4 — Introspection du catalogue

`scripts/introspect_catalogue.py`, exécuté par le Python d'Aster, sans
dépendance hors bibliothèque standard. Production de
`data/processed/catalogue/<version>/*.json` conforme à `docs/metadata.md`.

Commence par une exploration : lister ce que le catalogue expose réellement
dans la version installée avant d'écrire l'extracteur. Tout élément non reconnu
provoque un échec.

Critères de sortie : nombre de commandes extraites cohérent avec le nombre de
commandes exposées, extraction complète pour un échantillon fixe de commandes
vérifiées à la main contre leur documentation U4, tests sur un catalogue réduit
construit pour les tests.

**Note (constat du lot 10b, à consigner ici puisqu'elle concerne le périmètre
de l'extraction elle-même).** Le catalogue extrait par ce lot ne couvre pas
l'ensemble des commandes réellement exécutables d'une installation
Code_Aster : `_find_commands` (`scripts/introspect_catalogue.py`) parcourt
exclusivement `code_aster.Cata.Commands`, alors qu'un sous-ensemble de
commandes bien réelles — `DEFI_CONT`, `MACR_ROTA_GLOBALE` et consorts —
sont définies dans `code_aster.MacroCommands` (constaté par lecture directe
du dépôt source : `DEFI_CONT`, dans `code_aster/MacroCommands/defi_cont.py`,
lie ce nom à `UserMacro("DEFI_CONT", DEFI_CONT_CATA, defi_cont_ops)`, un
exécuteur, jamais l'objet catalogue `MACRO(...)` lui-même — nommé en interne
`DEFI_CONT_CATA`, une convention propre à ce fichier, non généralisable sans
deviner). Vérifié empiriquement dans le conteneur : `code_aster.Cata.Commands`
lui-même ne porte pas ces noms (`getattr(..., "DEFI_CONT", None)` renvoie
`None`) — ce n'est donc pas une lacune de l'extracteur du lot 4, mais une
limite de portée du module qu'il introspecte. Sur les 4183 cas tests
officiels, le lot 10b en a dénombré 59 occurrences de commandes dans ce cas
(hors catalogue mais explicitement importées — voir `docs/development-plan.md`,
lot 10, mécanisme M4, point D), réparties sur 11 commandes distinctes :
`DEFI_CONT` (26), `F_FONC` (13), `F_ACS2C11` (5), `CALC_SPEC` (4), `F_ACC_X`
(3), `MACR_ROTA_GLOBALE` (2), `CHAR_GRAD_INI` (2), `F_ACCEL`, `TEST_INIT`,
`F_FLBNS`, `MACRO_TEST` (1 chacune) — détail complet dans le compte rendu du
lot 10b. Traitées comme non vérifiées avec motif dédié, jamais comme une
erreur. Combler cette lacune (introspecter aussi `MacroCommands`) resterait
à faire sur preuve d'un besoin mesuré, hors périmètre de ce lot.

**Note (confirmation indépendante, lot 6b, X3 — extraction non modifiée
dans ce lot).** Le constat du lot 10b reposait sur la fréquence d'usage
dans les cas tests (une source indirecte : une commande peut être
utilisée sans être officiellement documentée, ou documentée sans
apparaître dans l'échantillon de cas tests dépouillé). La table
commande → document du lot 6 (I5, construite depuis le titre des
documents `U4`/`U7`, sans aucun rapport avec les cas tests) apporte une
**source indépendante** : sur les 15 documents `U4`/`U7` initialement
sans commande reconnue, deux nomment effectivement une commande réelle,
absente des 268 commandes introspectées, confirmée par lecture directe de
`external/codeaster-src` :

- `DEFI_CONT` (`U4.44.13`, « Opérateur DEFI_CONT ») et `CALC_SPEC`
  (`U4.32.21`, « Opérateur CALC_SPEC ») — déjà dans la liste du lot 10b ;
  la documentation officielle confirme donc, par une voie indépendante des
  cas tests, que ces deux commandes existent réellement et sont
  documentées, pas un artefact de l'échantillon de cas tests du lot 10b.
- `CALC_FORC_AJOU` (`U4.66.03`, « Opérateur CALC_FORC_AJOU ») — **révélée
  par cette table, absente de l'énumération du lot 10b** :
  `code_aster/MacroCommands/Utils/calc_forc_ajou.py` (`CALC_FORC_AJOU =
  CalcForcAjou.run`), catalogue `OPER(nom="CALC_FORC_AJOU", ...)` dans
  `calc_forc_ajou_cata.py` du même répertoire — un `MacroCommands` de
  plus, structurellement semblable à `DEFI_CONT`/`CALC_SPEC`.
- `POURSUITE` (`U4.11.03`, « Procédure POURSUITE ») — **révélée par cette
  table, d'une nature différente des précédentes** : jamais un
  `MacroCommands`. Définie dans `code_aster/CodeCommands/debut.py`
  (`POURSUITE = partial(Starter.run, caller="POURSUITE")`), un alias
  d'exécution de `DEBUT` sous un autre nom d'appelant.
  `code_aster.Cata.Commands` ne porte "POURSUITE" sous aucune forme —
  seulement comme valeur autorisée du mot-clé `MODE` de `DEBUT`
  (`into=("AUTO", "DEBUT", "POURSUITE")`), jamais une commande à part
  entière dans ce module. `DEBUT`/`FIN`, eux, sont bien dans les 268
  commandes introspectées : seul l'alias `POURSUITE` en est absent.

**Décompte total (lot 6b) : 4 commandes documentées confirmées absentes du
catalogue introspecté par une source indépendante des cas tests** (2
déjà connues du lot 10b, 2 nouvellement révélées par la table du lot 6).
Combiné aux 11 noms déjà établis au lot 10b (dont les 2 repris ci-dessus),
**13 commandes distinctes** sont maintenant connues comme réelles et
absentes du périmètre de `code_aster.Cata.Commands`, réparties sur deux
mécanismes distincts : `MacroCommands` (la majorité) et `CodeCommands`
(`POURSUITE`, un cas différent, jamais un `MacroCommands`). Aucune
modification de `scripts/introspect_catalogue.py` dans ce lot : le
périmètre de l'introspection reste celui du lot 4, cette note ne fait que
consigner une preuve supplémentaire de sa limite déjà actée.

## Lot 5 — Jeu d'évaluation

Constitution de 30 à 50 questions réelles avec document attendu. Outil de
mesure du rappel et de la précision, utilisable avant qu'un index n'existe.

Critères de sortie : jeu versionné, chaque réponse attendue vérifiée dans la
documentation, outil de mesure testé sur un index factice.

**Clôture du lot 5.**

**Entrées.** 64 questions bornées réelles (`data/evaluations/questions_raw.jsonl`,
copie verbatim de `/media/sf_partage/echanges/lot5_questions.jsonl`, jamais
modifiée), décomposées par l'utilisateur à partir de 21 questions larges
(`data/evaluations/cas_usage.md`) — dépasse le minimum de 30 demandé par ce
lot, sans reformulation d'aucune des deux listes.

**Établissement des réponses.** Chaque question a été confrontée au corpus
synchronisé (`external/codeaster-doc`), jamais devinée à partir d'une
correspondance de mots-clés seule : recherche de candidats via la table
commande → document du lot 6/6b (`data/processed/command_document_map.json`)
et les titres de `data/raw/inventory.jsonl`, puis lecture directe du contenu
réel du (des) document(s) candidat(s) pour confirmer qu'il répond
effectivement à la question posée. `expected_commands` vérifié un par un
contre les 268 noms du catalogue extrait au lot 4b — aucune commande hors
catalogue (`DEFI_CONT`, `CALC_SPEC`, `CALC_FORC_AJOU`, `POURSUITE`, lot 6b X3)
n'y figure, même quand elle répondait matériellement à la question.

**Résultat : 62/64 questions résolues, 2 non résolues.**

- `eval-005` (« raideur qui varie le long d'une ligne » pour un élément
  discret) : `AFFE_CARA_ELEM` permet de facto de juxtaposer plusieurs
  occurrences de `DISCRET` avec des `VALE` différentes sur des `GROUP_MA`
  distincts, mais aucun document ne traite explicitement ce mécanisme comme
  une réponse à la question (à la différence de `VARI_SECT` pour une poutre à
  section continûment variable) — conclure serait une déduction, pas un fait
  établi dans un document dédié.
- `eval-007` (choix plaque vs poutre pour une paroi moulée) : les familles
  poutre (`U3.11.*`) et plaque (`U3.12.*`) sont chacune documentées
  séparément ; aucun document ne compare les deux pour ce cas d'usage
  géotechnique précis. Les citer comme réponse aurait été une correspondance
  de mots-clés, pas une réponse établie.

Aucune question n'a dû être classée `answer_outside_corpus` : sur ce jeu, la
réponse établie vit chaque fois dans la documentation elle-même (parfois
complétée, jamais remplacée, par un cas test cité en confirmation
indépendante — `eval-010`, `V5.01.108`/`V6.08.116` pour `DIS_CONTACT`) —
signalé ici pour le découpage du lot 7, comme demandé, plutôt que déduit
silencieusement d'une absence de valeur `true`.

**Répartition des documents attendus par famille** (une question pouvant en
citer plusieurs) : U4 71, R 31, U2 11, U3 6, U7 3, V 0, D 0. Aucun document V
n'a été retenu en tant que réponse établie : plusieurs cas de validation ont
été repérés comme corroboration (`eval-006`, `eval-010`) mais jamais ajoutés
à `expected_documents` sans lecture dédiée confirmant qu'ils répondent
eux-mêmes à la question, pas seulement qu'ils exercent la même commande.

**Répartition par domaine** (résolu/non résolu) : `dynamique` 8/0,
`post_traitement` 7/0, `chargements` 5/0, `materiaux` 5/0, `convergence` 5/0,
`verification` 5/0, `interaction_sol_structure` 4/0, `maillage` 4/0,
`conditions_limites` 4/0, `lois_comportement` 4/0, `modelisation_poutre` 3/0,
`ferraillage` 2/0, `elements_discrets` 2/1, `modelisation_coque` 1/1,
`modelisation_generale` 1/0, `raccords` 1/0, `contact` 1/0.

**Fausses pistes de la table commande → document signalées** (jamais
suivies aveuglément) : `VERI_NORM` (mot-clé d'`AFFE_CHAR_MECA`, absent de la
table car ce n'est pas une commande — rapprochement fait par lecture
directe), `LIAISON_ELEM` (même motif), `RIGI_PARASOL` (mot-clé
d'`AFFE_CARA_ELEM`, jamais mis dans `expected_commands` pour cette raison) ;
`MACR_SPECTRE` écartée pour `eval-013` après lecture (calcule des spectres de
plancher en post-traitement, pas un spectre d'oscillateur depuis des valeurs
d'accélération brutes) ; `POST_VERI_FERRAILLAGE` écartée pour `eval-039`
(présente au catalogue mais non nommée par le document panorama lu).

**Outil de mesure.** `aster_expert.retrieval.evaluation` (recall@k,
precision@k, hit@k « au moins un document attendu retrouvé », MRR) prend en
entrée une liste de résultats classés (JSONL `{"id", "ranked_documents"}`)
et le jeu de référence — jamais le corpus lui-même, utilisable avant qu'un
index n'existe. Exposé par `aster-expert eval score`/`aster-expert eval
summary`. Testé sur un jeu et un classement fabriqués pour le test
(`tests/unit/test_evaluation.py`, 7 tests : hit au sein de `k`, question non
résolue exclue de la métrique, question résolue absente des résultats comptée
comme échec réel, `k` invalide rejeté, aller-retour JSONL, comptage du
résumé) — aucun corpus, aucun réseau.

**Limite connue (amendée au lot 5b, voir ci-dessous).** Le corpus synchronisé
ne couvre qu'une version documentaire (17.4.0) : `version` était laissé à
`null` sur les 64 questions, aucune n'en dépendant explicitement à ce stade.

**Clôture du lot 5b — normalisation du schéma d'évaluation.**

**N0 — contrôle préalable de la relecture externe.** Une relecture par un
autre modèle a proposé une refonte du schéma en citant 20 identifiants de
documents tirés de sa mémoire, sans vérification contre le corpus :
`R5.03.31`, `R5.03.17`, `U3.11.01`, `U3.12.01`, `R7.01.04`, `R7.01.08`,
`R7.01.09`, `R7.01.42`, `R7.01.47`, `R5.03.28`, `U4.81.44`, `U4.81.46`,
`U4.52.17`, `U4.52.12`, `U4.42.01`, `U4.32.11`, `U4.81.21`, `U4.23.04`,
`U4.52.13`, `R3.03.05`. Vérification directe dans `data/raw/inventory.jsonl` :
**les 20 identifiants existent**, tous dans une famille et avec un titre
cohérents avec l'usage qu'en faisait la relecture — aucun n'est inventé.
Ce résultat, contraire à l'attente qui motivait le contrôle, ne dispense pas
d'avoir vérifié : il fonde le crédit donné aux items N1-N5 de la relecture,
qui ont ensuite été traités individuellement plutôt qu'importés en bloc.

**N1 — version, jamais `null`.** `EvaluationQuestion.version`
(`src/aster_expert/retrieval/models.py`) devient un objet `VersionInfo`
obligatoire : `solver` ("17.4.0"), `documentation_revision` (le commit
`codeaster-doc` de `data/raw/manifest.json`/`config/versions.yaml`,
`9c8c179f57ef7ca1d2891cac275ee4823a57967c`) et `compatibility_status`, qui
énonce précisément ce qui a été vérifié de la correspondance
solveur/documentation (correspondance de tag confirmée par
`git ls-remote --tags`) et ce qui ne l'a pas été (aucun changelog croisé
consulté, note déjà présente dans `config/versions.yaml`) — jamais
« vérifié » sans cette nuance (`CLAUDE.md`, principe 6). Le même objet
s'applique aux 65 questions, le corpus synchronisé ne couvrant qu'une seule
révision.

**N2 — `required_documents`/`supporting_documents`.** `expected_documents`
est scindé sur la base de ce que `verified_by` établissait déjà (aucune
nouvelle recherche) : un document devient `supporting_documents` quand
`verified_by` le qualifie lui-même de théorie sous-jacente, de renvoi pour
détail algorithmique/mathématique, de confirmation/panorama de contexte —
sinon il reste `required_documents`, conformément à l'instruction (« quand
`verified_by` ne permet pas de trancher, garde le document en required »).
Documents déclassés en `supporting_documents` : `U2.02.03` (eval-004,
notice générale), `R3.03.03`/`R3.03.06` (eval-018, théorie des raccords),
`R5.03.01` (eval-030/032/034, détail algorithmique de STAT_NON_LINE),
`R5.03.80` (eval-033, détail des modes de pilotage), `U2.01.05` (eval-035,
détail des composantes), `U2.03.07` (eval-038, panorama), `R7.01.42`
(eval-029, justification du choix plutôt que formulation elle-même),
`U4.23.04` (eval-040, correction du défaut plutôt que la vérification
elle-même demandée par la question). `evaluate_retrieval` ne lit plus que
`required_documents` (`src/aster_expert/retrieval/evaluation.py`,
`QueryScore.required_documents`) ; `supporting_documents` n'est jamais
scoré.

**N3 — `answerability`.** Quatre valeurs (`explicit`, `inferable`,
`partial`, `absent`) ajoutées à chaque question. `eval-005`/`eval-007`
passent à `absent` (`required_documents` vide déjà, comportement inchangé,
juste explicité). `eval-006`/`eval-008` passent à `inferable` (mécanisme
documenté générique appliqué à un cas géotechnique/de vocabulaire que le
corpus ne nomme jamais). `eval-021`/`eval-048` passent à `partial` (voir
N5).

**N4 — `gold_confidence`.** Trois valeurs (`high`, `medium`, `provisional`)
d'après `verified_by` seul. `high` : 59/65. `medium` : `eval-006`,
`eval-008`, `eval-021`, `eval-048` (mécanisme générique ou citation
documentaire sans citation de contenu). `provisional` : `eval-005`,
`eval-007` (un « non résolu » est un constat de recherche, pas un fait
définitif).

**N5 — corrections ciblées, chacune sur preuve.**

- `eval-039` (X1) : `U4.81.44` et `U4.81.46` étaient cités par `U2.03.07`
  sans que leur propre contenu ait été lu. Lus directement
  (`external/codeaster-doc/source/manuals/man_u/u4/u4.81.44/But.rst` et
  `.../u4.81.46/But.rst`) : les deux confirment répondre à la question
  (`COMBINAISON_FERRAILLAGE` — plusieurs combinaisons de chargement ;
  `VERI_FERRAILLAGE` — vérification d'un ferraillage existant). Maintenus
  en `required_documents`, `verified_by` réécrit avec les citations
  individuelles, `gold_confidence` passé de `medium` à `high`.
- `eval-013` : question scindée en deux, l'identifiant `eval-013` gardé pour
  le calcul d'un spectre depuis un accélérogramme (`CALC_FONCTION`,
  inchangé), et `eval-065` ajoutée en fin de jeu pour la déclaration d'un
  spectre déjà connu (`LIRE_FONCTION`/`DEFI_NAPPE`, vérifiée par lecture de
  `U4.84.01/Op_randes.rst` ligne 282 et des `But.rst` de `U4.32.02` et
  `U4.31.03`) — jamais une reformulation du contenu établi, une séparation
  de deux mécanismes déjà documentés côte à côte.
- `eval-048` : lacune consignée dans `docs/corpus.md` §8 (guides ISS
  `U2.06.05`/`U2.06.07` référencés par 6 documents distincts mais absents du
  corpus synchronisé, confirmé par 9 arêtes non résolues dans
  `data/processed/xref_graph.json` — plus large que les deux renvois déjà
  relevés lors de l'établissement de la question). `answerability` passé à
  `partial`.
- `eval-021` : preuve relue — elle ne couvre que les forces nodales
  concentrées (`FORCE_NODALE`), pas les chargements répartis pour lesquels
  aucun mécanisme `REPERE='LOCAL'` équivalent n'existe dans le corpus.
  `answerability` passé à `partial`.

**Hors périmètre, conformément à l'instruction.** Aucun document attendu
supplémentaire recherché ; aucun ensemble de réponses alternatives, document
piège, commande conditionnelle ni nouvelle métrique introduits — reportés
après le lot 7.

**Garde-fou de parallélisme.** Travail réalisé sans sous-agent : `git status
--short` relevé avant modification (dépôt propre) et après (seuls les
fichiers listés dans l'inventaire de clôture modifiés).

**Tests.** `tests/unit/test_evaluation.py` mis à jour pour le renommage de
champ (`required_documents`) et l'ajout d'un test dédié
(`test_supporting_documents_never_scored`, garantit qu'un document
`supporting_documents` retrouvé n'est jamais compté comme un hit) ;
`tests/unit/test_retrieval_models.py` ajouté (5 tests : `version`
obligatoire et jamais `null`, `answerability`/`gold_confidence` rejettent
une valeur hors énumération, `required_documents`/`supporting_documents`
indépendants, question non résolue).

## Lot 6 — Inventaire du corpus

Inspection des dépôts synchronisés, inventaire JSONL, statistiques, anomalies.
Tranche la question du format des sources documentaires.

Critères de sortie : inventaire reproductible, anomalies listées et
qualifiées, décision écrite sur la stratégie de parsing documentaire.

**Note (à consigner sans l'implémenter, lot 4b, C4).** Le champ `docu` du
catalogue (référence manuel U4/U7) n'est pas une source fiable pour relier
une commande à sa documentation : sur la version 17.4.0, 262 commandes sur
268 n'ont pas de `docu` exploitable (260 nulles, 2 malformées — voir
`docs/metadata.md` §2 et `catalogue_summary.json` du lot 4b). Le lien
commande → manuel devra être construit depuis le corpus documentaire
lui-même (structure des documents U4/U7 synchronisés, lot 3, inventoriés
dans ce lot 6), pas déduit ou complété à partir du catalogue.

**Clôture du lot 6.**

**I1/I2 — Inventaire et familles.** `aster-expert sources inventory`
(`aster_expert.ingestion.inventory`) produit `data/raw/inventory.jsonl` :
2047 documents (un répertoire portant son propre `index.rst`, jamais
imbriqué sous un autre — vérifié, 0 occurrence). `docs/corpus.md` §3 est
amendé : `U0` (un document, guide de lecture) et `man_s` (`SU`/`SV`, 10
documents, plate-forme Salome-Meca — hors périmètre Code_Aster) rejoignent
la table des familles, confirmée sur le reste par l'inventaire réel.
Statistiques par famille et par type de fichier détaillées dans le compte
rendu de session ; identifiant normalisé et label brut conservés
séparément (1943 labels majuscules, 104 minuscules, 0 casse mixte sur le
corpus 17.4.0).

**I3 — Sonde docutils : l'arbitrage est confirmé, pas supposé.**
`aster-expert sources probe` (`aster_expert.ingestion.rst_probe`) sonde un
échantillon stratifié de 69 documents (≥ 60 exigés) couvrant U2, U4, U7, R,
V, D et man_s, avec `docutils` seul (aucune extension Sphinx, `conf.py`
jamais exécuté — seule son assignation `extensions = [...]` est lue par
`ast`). Mesure sur l'échantillon : 78,2 % des caractères de la source sont
récupérables tels quels (hors messages de diagnostic générés par
`docutils` lui-même) ; l'écart restant est très majoritairement du balisage
reST/Sphinx (`**`, `.. `, options de directive), jamais du contenu perdu —
vérifié directement sur la structure du document produit : une directive
ou un rôle inconnu de `docutils` seul (`toctree`, `ref`, `external:ref`,
`numref`, `eq` — tous fournis par Sphinx lui-même ou par les deux
extensions déclarées, `sphinx.ext.autosectionlabel` et
`sphinx.ext.intersphinx`, jamais un mystère) conserve son texte brut
intégralement dans le document produit (`literal_block`/`problematic`),
jamais supprimé silencieusement. `.. math::`/`:math:` sont nativement
reconnus par `docutils` seul : les formules restent en LaTeX exploitable,
confirmant le motif de l'arbitrage. Point à surveiller reproduit ici :
`language_code` doit être réglé sur `"fr"` (comme `source/conf.py`), sans
quoi une directive native de `docutils` sous son alias français
(`.. avertissement::`, alias de `warning`) est signalée à tort comme
inconnue.

Seule perte réelle, mesurée précisément : la directive `include` cible
`_cache/{math_styles,external_refs,home}.rst`, un répertoire **généré au
build** (`data/docaster_build.py` à partir de gabarits Jinja2 sous
`data/templates/`), absent de tout clone brut — jamais un défaut de
l'extracteur, un fait de fabrication du dépôt lui-même. 76 occurrences
(72 + 3 + 1) sur 34/2047 documents (1,7 %) ; contenu perdu = ces trois
fichiers eux-mêmes, jamais du contenu propre à un document : 18 648 octets
uniques (macros LaTeX de confort pour l'analyse tensorielle/mécanique des
milieux continus, et liens de navigation/dépôts) sur 48 253 722 octets de
texte `.rst` du corpus entier, soit **0,039 %** — 2,16 % dans l'hypothèse
maximaliste (fausse) où chacune des 76 occurrences comptait le contenu
comme non partagé. **Conclusion : la perte est négligeable et
intégralement caractérisée ; l'arbitrage du lot 6 (parser les sources
`.rst`, jamais un rendu Sphinx construit) est confirmé, pas révisé.**

**I4 — Graphe de références croisées, établi, pas exploité (chiffres
corrigés au lot 6b, voir la clôture du lot 6b ci-dessous : le premier
calcul confondait deux mécanismes distincts déclarés dans `conf.py` et
n'aurait jamais dû être cité seul).**
`aster-expert sources xref` (`aster_expert.ingestion.xref`) relève 15560
occurrences `:ref:`/`:external:ref:` sur le corpus entier :
**3779 résolues en interne (24,3 %)**, **3412 externes/intersphinx
(21,9 %)**, **0 ambiguë**, **8369 réellement non résolues (53,8 %)**,
2164 arêtes distinctes (`data/processed/xref_graph.json`). La majorité des
« réellement non résolues » ne vise pas un document : bibliographie locale
(`bib1`...), numérotation de figure/équation/section, ancres générées par
la conversion Word→reST (`RefHeading__...`, `RefNumPara__...`), labels
explicites de sous-document (`u4.43.01-visc_isot_plas_...`) — hors
périmètre de ce graphe document-à-document, jamais confondu avec une
référence cassée. Un sous-ensemble plus restreint ressemble à un
identifiant documentaire sans en être un valide dans cette version (ex.
`D3.02.01` : la famille `D3` n'existe pas sur le corpus 17.4.0,
`man_d` allant de `d0` à `d9` sans `d3` ; `A2.01` : la famille `A`
— `man_a` — n'est jamais synchronisée, intranet uniquement) — un renvoi
obsolète ou hors périmètre du dépôt public, pas un défaut d'extraction.
Un défaut réel de la source a aussi été trouvé et confirmé, jamais
corrigé : `man_v/v6/v6.08.120/Probl_mes_de_r_f_rence.rst:67` et son
homologue `v5.01.109` enveloppent un littéral Python (`NU.array([...])`)
dans un rôle `:ref:`, probablement un artefact de substitution
automatique ; classé non résolu comme n'importe quelle cible sans deviner
de correction.

**I5 — Table commande → document, le livrable attendu (chiffres corrigés
au lot 6b, X3 : 2 documents supplémentaires reclassés).**
`aster-expert sources command-map`
(`aster_expert.ingestion.command_map`) construit
`data/processed/command_document_map.json` depuis un fait observé — le nom
de commande, casse officielle, apparaît comme identifiant complet
(jamais comme sous-chaîne d'un nom plus long, ex. `AFFE_CHAR_MECA` ne
matche jamais le titre d'`AFFE_CHAR_MECA_C`) dans le titre d'un document
`U4`/`U7`. Chaque arête porte le titre exact et le chemin du fichier
source d'où provient le rapprochement (amendement lot 6b, X2). Couverture :
**266/268 commandes du catalogue (99,3 %)**. 2 commandes sans document
(`IMPR_CORR_HOMO`, `LIRE_CORR_HOMO`) ; **13** documents U4/U7 sans commande
(guides généraux, mots-clés transverses comme `SOLVEUR`, notes de
version) ; **4** documents nomment une commande réelle mais hors du
catalogue introspecté par construction (`DEFI_CONT`, `CALC_SPEC`,
`CALC_FORC_AJOU`, `POURSUITE` — voir la clôture du lot 6b et l'amendement
du lot 4). La relation est many-to-many, jamais forcée à un choix
arbitraire : un document peut nommer plusieurs commandes sœurs ensemble
(`U4.44.01`, « Opérateurs AFFE_CHAR_MECA, AFFE_CHAR_MECA_C et
AFFE_CHAR_MECA_F ») et une commande peut être documentée par plusieurs
documents (`IMPR_RESU`, quatre documents, un par format de sortie).

**I6 — Anomalies.** 35 anomalies sur 2047 documents, toutes qualifiées et
listées dans `data/raw/inventory.jsonl`/le compte rendu, aucune corrigée
silencieusement : `unresolved_toctree_entry` (14), `orphan_file` (14, dont
un fichier au nom mal recopié dans son propre toctree — même défaut que
l'entrée toctree cassée d'`U4.53.01`), `label_directory_mismatch` (3),
`empty_component_file` (3 : `1.rst` sous `r3.08.10` et `r7.02.15`, 3
octets chacun, uniquement des lignes blanches ; `1.rst` sous `v3.04.002`,
37 octets, même motif), `duplicate_document_id`
(1, `R3.07.10` — le label de `r3.07.11` recopie celui du document
voisin). `missing_label`/`missing_title`/`unknown_family_prefix`/
`empty_document` : 0 occurrence sur le corpus réel (types conservés dans
le modèle, vérifiés par test, jamais suppprimés faute d'exemple présent).

**Idempotence.** Deux exécutions consécutives de `aster-expert sources
inventory` sur la même révision produisent un `inventory.jsonl` identique
octet à octet (vérifié en session, `sha256sum` égal) — l'horodatage de
génération n'est jamais écrit dans les entrées elles-mêmes.

**Clôture du lot 6b (relecture externe du lot 6, trois points, aucun
développement au-delà).**

**X1 — le taux de résolution du graphe I4, décomposé, pas juste corrigé.**
La relecture pointait deux mécanismes de `source/conf.py` non pris en
compte au lot 6. Vérifiés par lecture directe des sources de Sphinx
9.1.0 (téléchargé pour inspection seule, jamais installé comme dépendance
du projet — l'arbitrage du lot 6 reste : parser les `.rst`, pas un rendu
Sphinx construit), jamais supposés :

- `sphinx.ext.autosectionlabel` (`autosectionlabel_maxdepth = 1`,
  `autosectionlabel_prefix_document` absent de `conf.py` donc `False` par
  défaut — vérifié dans `sphinx.ext.autosectionlabel.setup`) fait de la
  section de tête de **chaque fichier** `.rst` (pas seulement
  `index.rst` : chaque fichier est son propre document Sphinx dès que
  `doctitle_xform` vaut `False`, réglage par défaut de
  `sphinx.environment` — sans lui, `docutils` fusionnerait cette section
  dans `document['title']` et `register_sections_as_label` ne la
  verrait jamais) un label implicite, nommé
  `fully_normalize_name(title.rawsource)` — le texte **brut** de la
  ligne de titre, marqueurs `**id**` ou rôle imbriqué compris, jamais le
  texte rendu (`sphinx/ext/autosectionlabel.py`, lu ligne à ligne).
  `aster_expert.ingestion.xref.build_autosectionlabel_index` reproduit
  cet algorithme exactement et construit le registre complet : **13116
  fichiers, 6m39s, 4175 labels distincts, 0 erreur.**
  **Mesuré, pas supposé : ce registre n'intersecte AUCUNE des 3460
  cibles `:ref:` distinctes du corpus qui ne sont pas déjà un identifiant
  de document.** Une clé générée est illisible dès qu'un titre porte
  lui-même un rôle (ex. `"partie [:ref:`d0 <d0>`] : généralités"`) : ce
  n'est jamais un texte qu'un auteur retape manuellement comme cible.
  **Conclusion, contraire à l'hypothèse de la relecture : sur ce corpus,
  `autosectionlabel` n'explique aucune part de la non-résolution
  mesurée au lot 6.** Le mécanisme est néanmoins gardé, implémenté et
  testé (jamais deviné une fois pour toutes) : 268 des 4175 labels sont
  déjà dupliqués entre plusieurs documents (ambiguïté potentielle,
  jamais résolue arbitrairement si un jour un `:ref:` les cible), et rien
  n'empêche un usage futur.
- `sphinx.ext.intersphinx` : un `:external:ref:` est **toujours**
  distribué vers l'inventaire externe, jamais vers le domaine local,
  quelle que soit sa cible — confirmé même quand la cible existe
  localement (`U4.63.12`, référencé par `:external:ref:` dans
  `u4.84.01/Op_randes.rst` alors que le document existe dans notre
  synchronisation). Fait supplémentaire, non demandé par la relecture
  mais découvert en le vérifiant : `intersphinx_mapping` n'est défini
  dans `conf.py` **que si** `objects_global.inv` existe déjà
  (`if global_objects.exists(): intersphinx_mapping = {...}`), un
  fichier lui-même produit par un `_build` antérieur — absent de tout
  clone brut (`docs/development-plan.md`, observation de clôture du
  lot 3). Sur un premier `build` à partir de ce clone, `intersphinx`
  n'aurait donc **aucun** inventaire enregistré et tout `:external:ref:`
  échouerait au moment du build — un « externe » n'est jamais une
  garantie de résolution réussie ailleurs, seulement un fait de
  distribution structurelle qui l'exclut du domaine local.

**Chiffres corrigés (corpus entier, 15560 occurrences) :** 3779 résolues
en interne (24,3 %, dont 3779 par étiquette explicite, **0** par
`autosectionlabel`), 3412 externes/intersphinx (21,9 %), 0 ambiguë, 8369
réellement non résolues (53,8 %). Décomposition de ce dernier chiffre
(mesurée, `data/processed/xref_graph.json`) : 17,5 % ancres générées par
la conversion Word (`RefHeading__...`, `RefNumPara__...`), 17,4 %
bibliographie locale (`bib1`...), 12,5 % numéros de figure/table nus,
10,8 % équations (`éq X.X-X`), 6,3 % sections (`§X`), 4,9 % labels
explicites de sous-document (`u4.43.01-visc_isot_plas_...`, un mécanisme
réel du corpus, hors périmètre de ce graphe document-à-document), le
reste (~30 %) réparti entre légendes de figure, variantes de
bibliographie (`Boi01`...), identifiants partiels ou de familles absentes
du dépôt public (`D3.02.01`, `A2.01`) et un très petit nombre de défauts
réels de la source (le cas `NU.array([:ref:`...`])`, déjà relevé au
lot 6).

**X2 — traçabilité de la table I5.** Chaque arête
`CommandDocumentEdge` (et chaque `UncataloguedCommandMention`) porte
désormais `document_title` (le titre exact où le nom de commande a été
trouvé) et `source_path` (le chemin du fichier `index.rst` correspondant)
— jamais seulement `command`/`document_id`, qui ne permettaient pas de
revérifier le rapprochement sans rejouer l'extraction (`CLAUDE.md`,
« Toute donnée indexée conserve sa source, son chemin »). Table
régénérée et redéposée dans `/media/sf_partage/echanges/`.

**X3 — voir l'amendement du lot 4 ci-dessus.** La table I5 confirme, par
une source indépendante des cas tests, l'existence documentée de
`DEFI_CONT`/`CALC_SPEC` (déjà connues du lot 10b) et révèle deux
commandes documentées supplémentaires absentes du catalogue introspecté :
`CALC_FORC_AJOU` (`MacroCommands`, comme les précédentes) et `POURSUITE`
(`CodeCommands`, un alias d'exécution de `DEBUT` — un mécanisme distinct,
jamais un `MacroCommands`). Catalogue non modifié dans ce lot.

**Découpage/indexation/recherche** : non touchés, conformément à
l'instruction du lot 6b.

## Lot 7 — Index lexical et recherche

Découpage documentaire selon `docs/corpus.md`, index BM25, filtres de
métadonnées, `aster-expert search`.

Critères de sortie : mesure sur le jeu d'évaluation du lot 5, affichage des
scores et des sources, contrôles de non-perte de contenu.

**Clôture du lot 7.**

**D1/D2 — Découpage, deux granularités.** `aster_expert.parsing.
doc_fragments` réutilise la structure du lot 6
(`aster_expert.ingestion.inventory.DocumentEntry` : un document est un
répertoire, une section est un fichier `.rst`), jamais un nouveau parseur —
`find_section_headers`/`split_into_subsections` détectent les en-têtes reST
(titre + ligne d'ornementation, convention par soulignement uniquement,
jamais surlignement+soulignement, non observée sur l'échantillon inspecté)
par lecture directe du texte, sans docutils. `content` est toujours une
tranche brute (`str.splitlines()` rejointe), jamais un rendu : une formule
`.. math::`/`:math:` apparaît donc exactement comme dans la source.

Seuil de redécoupage (`DEFAULT_SUBSECTION_LINE_THRESHOLD = 150`) choisi par
mesure : `wc -l` sur les 13116 fichiers de section réels du corpus 17.4.0
synchronisé (hors `other_pages`) donne une médiane de 41 lignes et un 90e
centile à 155 lignes — 150 est retenu juste en dessous, pour ne redécouper
que la longue traîne (dictionnaires de mots-clés, syntaxes complètes,
chapitres théoriques), pas la majorité des fichiers déjà courts.

Sur le corpus réel (`aster-expert fragments build --granularity both`) :

| Granularité | Fragments | Taille médiane |
|---|---|---|
| `by_file` | 13116 | 1358 caractères |
| `by_subsection` | 26553 | 946 caractères |

**D3 — Contrôles de non-perte.** Vérifiés, pas supposés :

- non-perte : `verify_full_coverage` reconstruit chaque fichier redécoupé
  ligne à ligne à partir des bornes déclarées et compare à la source ;
  aucune levée sur l'ensemble des fichiers de la passe réelle (contrôle
  intégré au constructeur, pas un audit a posteriori) ;
- rattachement : garanti par construction (`DocumentFragment.source_commit`/
  `source_path`/`aster_version` non optionnels, `pydantic`) ;
- idempotence : deux exécutions consécutives de `aster-expert fragments
  build --granularity by_file` sur la même révision produisent un
  `fragments_by_file.jsonl` identique champ à champ (13116/13116), empreintes
  comprises, hors `extracted_at` seul (horodatage du lot, jamais un fait du
  contenu) — vérifié par comparaison directe des deux sorties, pas
  supposé de la seule déterminisme apparent du code.

Liens attachés (lot 6/6b, à la granularité du document — ni la table
commande -> document ni le graphe de références n'ont de granularité plus
fine) : 1538/13116 fragments `by_file` portent au moins une commande liée,
4478/13116 portent au moins un document lié.

**D4 — Index lexical et recherche.** `aster_expert.indexing.bm25_index`
encapsule `bm25s` (`stopwords="french"`, jamais la liste anglaise par
défaut) sans réimplémenter son calcul de score. Les filtres de métadonnées
(`--version`, `--family`, `--document`, `--command`, `--section`) sont
appliqués en deux temps : un `weight_mask` natif de `bm25s.BM25.retrieve`
met à zéro le score de tout fragment hors filtre *avant* la sélection du
top-k (le classement lui-même n'est jamais pollué par un candidat proche du
seuil), puis chaque résultat retenu est revérifié explicitement — un score
nul n'est jamais interprété à lui seul comme une preuve d'exclusion
(`CLAUDE.md`, « jamais renvoyé silencieusement »). Aucune fusion, aucun
reranking, aucun index vectoriel (ADR-004).

`aster-expert search "question" [--version X] [--family U4] [--document ID]
[--command NOM] [--section TEXTE] [--granularity by_file|by_subsection]
[--k N]` affiche pour chaque résultat : score, identifiant de document,
chemin de section, chemin source, révision (12 premiers caractères), et un
extrait. Index construits sur le corpus réel : `by_file` (13116 fragments,
vocabulaire 101427 formes, 68 Mio), `by_subsection` (26553 fragments, même
vocabulaire, 80 Mio).

**D5 — Mesure sur le banc (livrable qui décide de la suite).**
`aster_expert.retrieval.bench` réduit un classement de fragments à un
classement de **documents** (dédupliqué, premier fragment rencontré fixe le
rang du document) avant de le confier à `aster_expert.retrieval.evaluation`,
inchangé depuis le lot 5. Sur les 65 questions du lot 5/5b, 63 résolues
(`required_documents` non vide), version filtrée à `17.4.0` :

| Granularité | k | hit@k | recall@k | MRR |
|---|---|---|---|---|
| `by_file` | 5 | 46,0 % | 35,2 % | 0,330 |
| `by_file` | 10 | 61,9 % | 49,6 % | 0,330 |
| `by_file` | 20 | 76,2 % | 63,2 % | 0,330 |
| `by_subsection` | 5 | 52,4 % | 39,2 % | 0,344 |
| `by_subsection` | 10 | 60,3 % | 47,9 % | 0,344 |
| `by_subsection` | 20 | 77,8 % | 64,9 % | 0,344 |

**Verdict D2, tranché par le chiffre, pas par préférence : les deux
granularités sont statistiquement indiscernables.** Sur les échecs à k=10,
6 questions échouent seulement avec `by_file` et 7 seulement avec
`by_subsection` (18 échouent avec les deux) — un renversement d'une dizaine
de questions dans un sens ou l'autre sur un jeu de 63, sans dominance
claire d'une granularité. `by_file` est retenue par défaut pour
`aster-expert search` : à mesure égale, elle est deux fois moins volumineuse
à indexer et plus simple à citer (une section du dépôt = un fragment,
jamais un choix esthétique présenté comme un arbitrage mesuré) —
`--granularity by_subsection` reste disponible et indexé pour qui veut la
comparer.

Ventilation (`by_file`, k=10) par famille : U4 64,7 % (51 questions), R
63,6 % (11), U2 75,0 % (8), U3 66,7 % (3), U7 66,7 % (3). Par
`answerability` : `explicit` 66,1 % (59), `inferable` 0 % (2), `partial`
0 % (2) — les 4 questions non `explicit` échouent toutes, cohérent avec leur
nature (une réponse déduite ou partielle n'est, par construction, pas la
correspondance lexicale directe que BM25 cherche). Détail par domaine dans
le rapport JSON déposé.

**Liste nominative des 24 échecs à k=10 (`by_file`), avec ce qui a été
remonté à la place (3 premiers résultats)** — c'est cette liste, pas le
score global, qui pèse sur l'opportunité du lot C1 :

| Question | Domaine | Attendu | Obtenu (top 3) |
|---|---|---|---|
| eval-001 | modelisation_poutre | U3.11.01, U3.11.04, U3.11.05, U3.11.07 | U2.06.10, U2.06.03, U2.03.11 |
| eval-006 | interaction_sol_structure | R5.03.17 | V5.05.101, V7.31.133, U2.01.09 |
| eval-008 | modelisation_coque | U4.42.01, U4.43.01 | R3.08.02, V5.03.100, V5.01.104 |
| eval-009 | interaction_sol_structure | R5.03.17, R5.03.31 | U4.84.11, V5.05.101, V2.02.147 |
| eval-010 | lois_comportement | R5.03.17 | V5.05.101, V2.02.401, R5.03.09 |
| eval-012 | dynamique | U4.52.02 | U2.06.01, R5.01.02, U1.02.00 |
| eval-016 | dynamique | U2.06.04, U4.52.14 | V2.01.105, V2.02.023, V2.08.012 |
| eval-017 | modelisation_generale | U4.41.01 | U2.04.06, V1.01.266, U1.05.00 |
| eval-019 | chargements | U4.44.01 | V6.03.501, V6.03.502, V6.04.503 |
| eval-021 | chargements | U4.44.01 | D4.06.01, R5.04.01, V6.02.130 |
| eval-030 | convergence | U4.51.03 | U1.02.00, U2.08.01, D4.06.15 |
| eval-035 | post_traitement | U4.81.04 | U2.02.02, R3.07.04, R3.07.06 |
| eval-036 | post_traitement | U4.42.01, U4.81.04, U4.81.05 | R3.07.04, R3.07.03, V6.05.108 |
| eval-037 | post_traitement | U2.01.05 | R3.07.06, SV1.01.01, D5.02.04 |
| eval-038 | ferraillage | U4.81.42 | V3.01.111, R7.01.31, R3.07.06 |
| eval-041 | verification | U4.81.21, U4.81.04 | V2.03.504, V1.03.134, U2.01.11 |
| eval-045 | post_traitement | U4.81.21 | D5.02.03, V0.01.001, V1.01.415 |
| eval-046 | materiaux | U4.43.03 | U4.01.00, U1.05.00, U4.43.07 |
| eval-048 | interaction_sol_structure | U7.03.12, R4.05.04, R4.05.07 | U1.02.00, U7.04.33, U2.04.03 |
| eval-051 | verification | U4.81.22 | U4.66.11, U4.66.01, U2.06.10 |
| eval-054 | chargements | U4.44.01 | V1.01.137, U1.05.00, U1.03.00 |
| eval-058 | conditions_limites | U4.44.01, U4.44.03, U4.31.02 | V4.24.201, V3.02.326, U4.43.03 |
| eval-059 | materiaux | U4.43.01 | U2.04.03, V7.31.149, V2.04.126 |
| eval-065 | dynamique | U4.31.03, U4.32.02 | R4.05.03, V2.03.118, V1.01.102 |

**Observation, jamais une décision prise à la place de l'utilisateur** :
15/63 questions (23,8 %) échouent encore à k=20 (`eval-048`, notamment,
porte la lacune documentaire déjà consignée ci-dessus — `U2.06.05`/
`U2.06.07` absents du corpus synchronisé — un échec de corpus, pas de
recherche). `U4.44.01` (« Opérateurs AFFE_CHAR_MECA... ») manque à 4
reprises (`eval-019`, `eval-021`, `eval-054`, `eval-058`), toujours sur le
domaine `chargements` : les questions posées en langage naturel ne
reprennent jamais le vocabulaire du titre du document ni le nom de la
commande, ce que le lexical seul ne comble pas par construction — un motif
concret, nommé, que le lot C1 (index vectoriel) devrait trancher sur
preuve, pas la persistance d'un score global insuffisant.

**D6 — Comparaison à la recherche naïve, résultat sans appel.**
`aster_expert.indexing.naive_search` cherche un jeton en MAJUSCULES d'au
moins 3 caractères dans le texte brut de la question, puis consulte la
table commande -> document du lot 6/6b. Sur les 62 questions (`by_file`)
qui nomment une commande attendue (`expected_commands` non vide) : **hit@5 =
hit@10 = hit@20 = 0 %** pour la référence naïve, contre 46,8 % / 62,9 % /
75,8 % pour BM25 sur exactement le même sous-ensemble. Motif, vérifié sur
les questions elles-mêmes (`data/evaluations/questions.jsonl`) : les 65
questions sont des reformulations de problèmes réels
(`docs/development-plan.md`, lot 5), jamais des requêtes tapées avec un nom
de commande officiel — aucune question ne contient littéralement
`AFFE_CHAR_MECA` ou `STAT_NON_LINE`. La référence naïve n'est donc pas
"battue de justesse" : elle n'a **jamais** pu répondre à une seule question
de ce jeu, ce qui est le résultat honnête à rapporter, pas un artefact du
choix d'implémentation — `expected_commands` documente la bonne réponse,
pas ce que l'utilisateur a tapé.

**NE PAS FAIT (conforme à la consigne).** Aucun embedding, aucune base
vectorielle, aucun reranking, aucun serveur MCP, aucune génération. Le jeu
d'évaluation (`data/evaluations/questions.jsonl`) n'a pas été modifié.

**Garde-fou de parallélisme.** Aucun sous-agent utilisé dans ce lot :
`git status --short` relevé avant modification (dépôt propre, `HEAD` sur
`lot-7-retrieval`) et à la clôture (seuls les fichiers de l'inventaire de
clôture modifiés).

**Tests.** 26 tests nouveaux (`tests/unit/test_doc_fragments.py`,
`test_bm25_index.py`, `test_naive_search.py`, `test_bench.py`, plus 4 tests
ajoutés à `test_evaluation.py` pour les ventilations et
`list_failures`) — fixtures locales uniquement, aucun accès réseau, aucune
dépendance à `external/codeaster-doc`. Suite complète du projet : 317 tests,
0 échec. `ruff format`/`ruff check` propres sur tout le code touché ;
`mypy` (configuration du projet, `src` + `tests`) ne signale aucune
régression nouvelle — les erreurs résiduelles (`test_sources_sync.py`,
`test_detect.py`, `test_catalogue_extract.py`, trois lignes préexistantes
de `test_evaluation.py`) sont antérieures à ce lot, présentes à l'identique
sur `main` avant toute modification (vérifié par `git stash`), et hors
périmètre de ce lot.

**Limites connues.**

- La détection d'en-tête reST ne reconnaît que la convention par
  soulignement seul (jamais surlignement+soulignement) — non rencontrée sur
  l'échantillon inspecté pour ce lot, mais pas exclue ailleurs dans le
  corpus ; un tel en-tête resterait alors non détecté, le fichier qui le
  porte restant un fragment unique (`by_subsection`) au lieu d'être
  redécoupé — jamais une perte de contenu, seulement une granularité plus
  grossière que souhaitée sur ce cas précis.
- `related_commands`/`related_documents` sont attachés à la granularité du
  document entier, jamais à la section précise qui cite effectivement le
  lien (le lot 6/6b ne produit pas cette granularité).
- Le filtre `--section` est une sous-chaîne insensible à la casse sur le
  chemin de section joint, pas une recherche structurée.
- 15/63 questions résolues du banc échouent encore à k=20 — voir
  l'observation D5 ci-dessus, à charge du lot C1 s'il est engagé.

**Clôture du lot 7b — priorité des sources et enrichissement des fragments.**

Point de départ (relecture externe, diagnostic établi avant ce lot) : sur les
24 échecs à k=10 du lot 7, douze placent au premier rang un document d'une
famille absente de tout `expected_documents` du banc (V : 8, D : 2, U1 : 2).
Le goulot identifié était la **précision**, pas le rappel — confirmé par la
mesure de ce lot (E4 ci-dessous).

**E1 — Enrichissement du texte indexé.** `aster_expert.indexing.enrichment`
ajoute, uniquement au texte *soumis à la tokenisation* BM25 (jamais au
`content` du fragment, ni à ce qui est cité ou extrait — `bm25_index.
build_bm25_index(..., keyword_names_by_command=...)`, `IndexBuildSummary.
text_enrichment`) : le titre du document, le chemin de section, et — pour
chaque commande déjà liée au document (table du lot 6b) — le nom de la
commande et les noms de ses mots-clés de **premier niveau** (facteurs et
simples, jamais les enfants d'un mot-clé facteur). Choix de profondeur
assumé, pas deviné : `AFFE_CHAR_MECA` porte à lui seul 51 mots-clés de
premier niveau (jusqu'à 232 pour la commande la plus riche du corpus,
médiane 10, mesuré sur les 266/270 commandes liées effectivement
cataloguées — 4 `MacroCommands` hors catalogue, lot 6b, silencieusement
ignorées, jamais une erreur) ; recourir à ses enfants aurait ajouté des
centaines de jetons génériques (`DX`, `DY`, `H1X`, `K1`...) par fragment,
à l'opposé de l'objectif de précision de ce lot. Index construit :
`aster-expert index build --granularity by_file --enrich-text`, écrit dans
`data/indexes/bm25_by_file_e1` (jamais dans l'index de référence du lot 7,
`default_index_dir(..., variant=...)`) — 13116 fragments, vocabulaire
101437 formes (+10 par rapport aux 101427 du lot 7 : la quasi-totalité du
vocabulaire ajouté existait déjà ailleurs dans le corpus, l'enrichissement
joue surtout sur la fréquence des termes dans les fragments concernés, pas
sur la couverture lexicale).

**Gain de E1 seul, à classement inchangé, mesuré honnêtement — un résultat
négatif, pas maquillé en progrès partiel :**

| k | hit@k (lot 7 réf.) | hit@k (E1 seul) |
|---|---|---|
| 5 | 46,0 % | 42,9 % |
| 10 | 61,9 % | 60,3 % |
| 20 | 76,2 % | 76,2 % |

E1 seul **dégrade légèrement** hit@5/hit@10 (2 questions basculent :
`eval-040`, `eval-055`) et en corrige une (`eval-030`) — net négatif à
k=5/10, neutre à k=20. Cause identifiée par inspection directe (pas
supposée) : `related_commands` est attaché au **document entier** (seule
granularité que fournit la table du lot 6b, déjà signalé comme limite du
lot 7), donc les mots-clés de premier niveau d'une commande sont injectés
dans **chaque** fragment du document, y compris ceux qui ne parlent pas de
ce mot-clé précis. `U4.44.01` (« Opérateurs AFFE_CHAR_MECA, AFFE_CHAR_MECA_C
et AFFE_CHAR_MECA_F ») compte 10 fragments `by_file` ; un fragment de 487
caractères (`#But`) reçoit ainsi la totalité du vocabulaire des trois
commandes (jusqu'à ~150 jetons combinés), le rendant lexicalement plus
proche de documents V/D qui emploient ce même vocabulaire de mots-clés réels
dans leur prose (pression, force nodale, liaison...) sans être eux-mêmes la
bonne réponse. E1 seul ne referme donc pas le goulot de précision diagnostiqué
— il peut même l'aggraver ponctuellement. **E1 n'est retenu dans la suite que
parce qu'il est un prérequis technique d'E2 (le texte enrichi porte les noms
de commandes/mots-clés que le filtre de famille peut ensuite exploiter), pas
parce qu'il apporte un gain mesuré isolément.**

**E2 — Priorité des sources, enfin câblée.** `aster_expert.retrieval.config`
(lecture validée de `config/retrieval.yaml`) et `aster_expert.retrieval.
source_priority` implémentent les deux variantes demandées, toutes deux
appliquées **par-dessus l'index E1**, jamais un nouvel index :

- **(a) filtre dur** (`hard_filter_search`) : restreint les fragments
  candidats aux familles du profil actif (`family_in`, nouveau paramètre de
  `bm25_index.search`, indépendant du filtre `--family` à valeur unique déjà
  existant) ; un second passage non filtré ne comble que les rangs restants
  si le premier n'a pas atteint `k`.
- **(b) repondération douce** (`soft_reweight_search`) : score brut ×
  `1.0` si la famille du fragment figure dans le profil actif, ×
  `DEFAULT_OUT_OF_PRIORITY_FACTOR = 0.3` sinon, sur un bassin de 200
  candidats (le plancher déjà appliqué en interne par `bm25_index.search`) —
  personne n'est exclu, seul le classement change. `0.3` est une valeur
  choisie et justifiée dans le code, jamais ajustée par recherche d'optimum
  sur le banc (ce que la consigne E3 interdit).

Le profil de requête n'est jamais détecté automatiquement dans ce lot
(consigne E2) : `aster-expert eval decompose --profile` l'expose en option
explicite, `syntax` par défaut — le seul profil qui corresponde à la nature
du banc actuel (docs/corpus.md §8 : aucune question du lot 5/5b ne porte sur
la théorie ou un exemple de cas test). Pour ce profil,
`config/retrieval.yaml` donne `[catalogue, U4, U7, testcase, source]` ; seuls
`U4` et `U7` sont effectivement indexés à ce jour (`catalogue`/`testcase`/
`source` ne font pas partie du corpus documentaire fragmenté par le lot 7)
— un fait constaté, pas une lacune de ce lot : la priorité s'applique à ce
qui existe dans l'index, rien de plus.

**Gain d'E2, mesuré séparément pour chaque variante (hit@k, sur le même index
E1) :**

| k | E1 seul | E1+E2a (dur) | E1+E2b (doux) |
|---|---|---|---|
| 5 | 42,9 % | 71,4 % | 71,4 % |
| 10 | 60,3 % | 81,0 % | 82,5 % |
| 20 | 76,2 % | 84,1 % | 87,3 % |

**Ventilation par famille attendue (hit@10) — quelle famille E2 dégrade, tel
que demandé :**

| Famille | n | lot 7 réf. | E1 seul | E1+E2a | E1+E2b |
|---|---|---|---|---|---|
| U4 | 51 | 64,7 % | 62,7 % | 94,1 % | 94,1 % |
| U7 | 3 | 66,7 % | 66,7 % | 100,0 % | 100,0 % |
| U2 | 8 | 75,0 % | 75,0 % | 62,5 % | 62,5 % |
| R | 11 | 63,6 % | 63,6 % | 36,4 % | 45,5 % |
| U3 | 3 | 66,7 % | 66,7 % | 66,7 % | 66,7 % |

U4/U7 (dans le profil `syntax`) progressent nettement ; U2/R (absents du
profil `syntax`) reculent — un effet de bord assumé et chiffré, pas caché.
Nominativement, sur les 63 questions résolues, par rapport à E1 seul, à
k=10 : E2a et E2b **corrigent les mêmes 17 questions**
(`eval-008`, `eval-012`, `eval-016`, `eval-017`, `eval-019`, `eval-021`,
`eval-035`, `eval-036`, `eval-038`, `eval-040`, `eval-041`, `eval-046`,
`eval-048`, `eval-054`, `eval-055`, `eval-058`, `eval-059` — les échecs du
domaine `chargements` portés par `U4.44.01`, motif initial du lot, en font
tous partie : `eval-019`, `eval-021`, `eval-040`, `eval-054`, `eval-055`,
`eval-058`) et **dégradent** `eval-025` (`U2.02.03`/`R5.03.17`), `eval-029`
(`R5.04.01`/`R5.03.28`), `eval-057` (`R3.03.01`/`R3.03.05`/`U2.01.02`) —
toutes les trois hors du profil `syntax` sur chacun de leurs documents
requis. Seule différence nominative entre (a) et (b) : le filtre dur dégrade
en plus `eval-027` (sept documents `R7.01.*`/`R5.03.28`), que la
repondération douce récupère — un score brut suffisamment élevé pour
survivre à la pénalité ×0,3, ce qu'un filtre qui exclut ne peut jamais
permettre. **Verdict, tranché par le chiffre : la repondération douce (b)
domine strictement le filtre dur (a)** sur les trois profondeurs mesurées
(hit@10 82,5 % contre 81,0 %, hit@20 87,3 % contre 84,1 %, un échec nominatif
de moins) — jamais un filtre qui exclut, une pondération qui laisse une
chance à un candidat très fortement pertinent hors profil.

**E3 — Honnêteté de la mesure.** Impact d'E2 sur les 4 questions résolues
d'`answerability` non `explicite` (`eval-006` inferable, `eval-008`
inferable, `eval-021` partial, `eval-048` partial — `eval-005`/`eval-007`,
`absent`, restent hors métrique, non résolues) :

| id | answerability | familles requises | hit réf./E1 | hit E1+E2a | hit E1+E2b |
|---|---|---|---|---|---|
| eval-006 | inferable | R | non | non | non |
| eval-008 | inferable | U4 | non | **oui** | **oui** |
| eval-021 | partial | U4 | non | **oui** | **oui** |
| eval-048 | partial | U7, R, R | non | **oui** | **oui** |

3/4 progressent — parce que leurs documents requis sont `U4`/`U7`, dans le
profil `syntax`, pas parce que la mesure aurait été réglée sur elles.
`eval-006` (seul document requis : `R5.03.17`, hors profil `syntax`) reste
un échec sous toutes les variantes, y compris la référence — E2 ne l'a pas
cassé, il ne l'a jamais résolu.

**Lacune du banc, signalée ici, jamais comblée dans ce lot (instruction
E3).** Le jeu d'évaluation actuel (`data/evaluations/questions.jsonl`,
65 questions, lot 5/5b) n'attend **aucun** document `V` ni cas test comme
réponse (`docs/corpus.md` §8, `required_documents`) : chaque famille qu'E2
déprioritise (`V`, `D`, `U1`...) est absente aussi bien des réponses
attendues que des questions elles-mêmes. Optimiser la précision en écartant
ces familles revient donc, structurellement, à se régler en partie sur une
zone aveugle du banc : la mesure ne peut montrer aucune dégradation sur une
question dont la bonne réponse serait un document `V` ou un cas test,
puisqu'aucune n'existe dans le jeu actuel. Avant d'envisager le filtre dur
(E2a) ou la repondération (E2b) comme réglage par défaut de
`aster-expert search`, le banc doit être complété par des questions dont la
réponse **est** un document `V` ou un cas test (ex. « quel cas test valide
telle modélisation de coque » — `answer_outside_corpus` le couvrirait pour
un cas test), selon le même protocole que le lot 5 (avec l'utilisateur,
jamais des questions inventées ici) — sans quoi la mesure favorise
mécaniquement, par construction, un moteur qui ignore ces familles.

**E4 — Mesure finale, décomposition complète du gain.** hit@k / recall@k /
MRR, granularité `by_file` fixe (consigne : ne pas changer la granularité
par défaut du lot 7) :

| Variante | k=5 | k=10 | k=20 | MRR |
|---|---|---|---|---|
| lot 7 référence | hit 46,0 % / rappel 35,2 % | hit 61,9 % / rappel 49,6 % | hit 76,2 % / rappel 63,2 % | 0,330 |
| E1 seul | hit 42,9 % / rappel 34,3 % | hit 60,3 % / rappel 48,7 % | hit 76,2 % / rappel 63,2 % | 0,327 |
| E1+E2a (dur) | hit 71,4 % / rappel 55,0 % | hit 81,0 % / rappel 65,9 % | hit 84,1 % / rappel 71,7 % | 0,534 |
| E1+E2b (doux) | hit 71,4 % / rappel 55,0 % | hit 82,5 % / rappel 66,3 % | hit 87,3 % / rappel 74,7 % | 0,540 |

63/65 questions évaluées (2 non résolues exclues, identique au lot 7).

**Cible annoncée (85 % de hit@10 sur `answerability = explicit`, 59
questions) : non atteinte, par variante :**

| Variante | hit@10 explicit | écart à la cible |
|---|---|---|
| lot 7 référence | 66,1 % | -18,9 points |
| E1 seul | 64,4 % | -20,6 points |
| E1+E2a (dur) | 81,4 % | -3,6 points |
| E1+E2b (doux) | 83,1 % | **-1,9 point** |

La meilleure variante (E1+E2b) reste sous la cible de 1,9 point — un
progrès réel et important par rapport au lot 7 (+17,0 points), jamais
présenté comme la cible atteinte.

**Liste nominative des échecs à k=10, meilleure variante (E1+E2b) — 11
questions, dont 10 `explicit` :**

| Question | Domaine | Attendu | Obtenu (top 3) |
|---|---|---|---|
| eval-001 | modelisation_poutre | U3.11.01, U3.11.04, U3.11.05, U3.11.07 | U4.82.11, U4.61.02, U4.81.07 |
| eval-009 | interaction_sol_structure | R5.03.17, R5.03.31 | U4.84.11, U4.32.11, U4.52.13 |
| eval-010 | lois_comportement | R5.03.17 | U4.01.13, U4.43.01, U4.42.07 |
| eval-025 | elements_discrets | U2.02.03, R5.03.17 | U4.43.01, U4.44.21, U4.67.02 |
| eval-029 | lois_comportement | R5.04.01, R5.03.28 | U4.01.06, U4.01.13, U4.01.00 |
| eval-037 | post_traitement | U2.01.05 | U4.81.05, U7.04.51, U4.74.01 |
| eval-045 | post_traitement | U4.81.21 | U4.81.04, U7.03.01, U4.84.11 |
| eval-051 | verification | U4.81.22 | U4.66.11, U4.66.01, U4.42.01 |
| eval-057 | conditions_limites | R3.03.01, R3.03.05, U2.01.02 | U4.44.03, U4.61.22, U4.61.11 |
| eval-065 | dynamique | U4.31.03, U4.32.02 | U4.32.04, U4.32.13, U7.03.12 |

(`eval-006`, `inferable`, n'est pas dans cette liste `explicit` mais reste
également un échec — voir E3.) Motif des 10 échecs `explicit` restants,
vérifié par leurs `required_documents`, pas supposé :

- **5 sur 10 requièrent un document `R`** (`eval-009`, `eval-010`,
  `eval-025`, `eval-029`, `eval-057` — théorie, hors profil `syntax` par
  construction) : le filtre/la repondération de ce lot ne pouvait pas les
  corriger sans changer de profil, ce qui sortirait du périmètre E2 (pas de
  détection automatique de profil dans ce lot).
- **2 sur 10 requièrent une famille elle aussi hors du profil `syntax`** :
  `eval-001` (`U3`), `eval-037` (`U2`) — même explication.
- **3 sur 10 requièrent pourtant un document `U4`, dans le profil**
  (`eval-045`, `eval-051`, `eval-065`) et échouent malgré tout : des échecs
  de vocabulaire non résolus par l'enrichissement E1 tel qu'implémenté
  (requêtes en langage naturel sans recoupement lexical suffisant avec le
  document cible) — la limite déjà connue du lot 7 persiste pour ces trois
  questions, la priorité de source n'y change rien puisque le bon document
  n'est jamais écarté par elle.

**Reproduction.** `aster-expert index build --granularity by_file
--enrich-text` puis `aster-expert eval decompose --output <fichier>` — le
rapport JSON complet (décomposition, ventilations par famille/domaine/
answerability aux trois k, échecs nominatifs de chaque variante), ainsi
qu'un compte rendu de mesure au format Markdown, sont déposés dans
`/media/sf_partage/echanges/` (`lot7b_decomposition_report.json`,
`lot7b_rapport_mesure.md`), jamais commités dans le dépôt — même convention
que le lot 7 (`data/evaluations/` ne conserve que le jeu de questions et ses
dérivés normalisés, pas les rapports de mesure d'un lot).

**NE PAS FAIT (conforme à la consigne).** Aucun embedding, aucune base
vectorielle, aucun reranking par modèle, aucun serveur MCP. Le jeu
d'évaluation n'a pas été modifié. La granularité par défaut reste `by_file`
(consigne : ne pas la changer) ; `by_subsection` n'a pas été mesuré dans ce
lot (E4 le demande explicitement pour `by_file` seul). Aucune détection
automatique du profil de requête.

**Garde-fou de parallélisme.** Aucun sous-agent utilisé dans ce lot (même
pratique que le lot 7) : `git status --short` relevé avant modification
(dépôt propre, `HEAD` sur `lot-7b-ranking`) et à la clôture.

**Tests.** 24 tests nouveaux : 13 dans les nouveaux fichiers
(`tests/unit/test_enrichment.py`, `test_source_priority.py`,
`test_retrieval_config.py`), 5 cas ajoutés à `test_bm25_index.py`
(`family_in`, enrichissement, `default_index_dir` avec variante), 2 à
`test_bench.py` (`rank_documents_with_source_priority`,
`run_lot7b_decomposition`), et 4 à `test_catalogue_query.py` pour
`resolve_digest_for_aster_version` (fonction extraite de
`aster_expert.validation.validate.resolve_digest_for_version`, qui la
délègue désormais au lieu de dupliquer la même résolution de digest —
comportement et messages d'erreur inchangés, vérifié par la suite de tests
existante de ce module). Suite complète du projet : 341 tests, 0 échec.
`ruff format`/`ruff check` propres sur tout le code touché ; `mypy` ne
signale aucune régression nouvelle (les 7 erreurs résiduelles —
`test_sources_sync.py`, `test_detect.py`, `test_catalogue_extract.py`, trois
lignes de `test_evaluation.py` — sont antérieures à ce lot, présentes à
l'identique sur `main`, hors périmètre).

**Limites connues.**

- E1 est un prérequis technique d'E2, pas un gain mesuré isolément (voir
  ci-dessus) — sa cause (enrichissement au niveau du document entier,
  jamais du fragment précis) est la même limite déjà connue du lot 7 pour
  `related_commands`/`related_documents`, qui se propage ici.
- `soft_reweight_search` ré-ordonne un bassin de 200 fragments candidats
  déjà classés par score brut, jamais le corpus entier reclassé (limite
  assumée et documentée dans le code, `aster_expert.retrieval.
  source_priority`) — sans effet pratique constaté aux profondeurs mesurées
  ici (k <= 20 documents).
- `DEFAULT_OUT_OF_PRIORITY_FACTOR = 0.3` est un choix documenté, jamais
  ajusté par recherche d'optimum sur le banc (consigne E3) — une valeur
  différente n'a pas été mesurée dans ce lot.
- Le banc actuel ne peut pas mesurer l'effet d'E2 sur une question dont la
  réponse est un document `V` ou un cas test (voir la lacune signalée
  ci-dessus) : la cible de 85 % n'a été vérifiée que sur les questions de
  syntaxe/méthode déjà couvertes par le lot 5/5b.
- Le profil `theory`/`example` de `config/retrieval.yaml` n'a pas été
  mesuré (aucune question du banc actuel n'en relève) — câblé et
  disponible (`aster-expert eval decompose --profile theory`), non validé
  sur un jeu de questions théoriques ou d'exemples faute d'un tel jeu.

**Clôture du lot 7c — routage par profil de requête.**

Point de départ (relecture externe, diagnostic établi avant ce lot) : sur
les 11 échecs à k=10 d'E1+E2b (lot 7b), neuf sont des questions de théorie
ou de méthode servies par le seul profil disponible (`syntax`, faute de
routage) ; deux (`eval-045`, `eval-065`) sont des échecs de vocabulaire dans
le bon profil. Le levier de ce lot est le routage, pas l'indexation —
confirmé, pas supposé, par G6 ci-dessous.

**G1 — Profil en entrée, jamais inféré.** `aster-expert search "..."
--profile syntaxe|theorie|methode` (défaut `syntaxe`) est maintenant câblé
sur `aster_expert.retrieval.source_priority.soft_reweight_search`
(`--priority-mode hard` reste disponible, jamais recommandé par défaut —
voir G5). Aucun classifieur, aucune heuristique de détection de profil
n'a été écrite (ADR-007, `docs/architecture.md`) : le profil reste, comme
au lot 7b (consigne E2), un paramètre explicite de l'appelant. Les filtres
existants (`--family`, `--document`, `--command`, `--section`) restent
combinables avec `--profile` : `hard_filter_search`/`soft_reweight_search`
(`aster_expert.retrieval.source_priority`) relaient désormais ces quatre
filtres vers `search` en plus de `priority_families`, au lieu de n'accepter
que `version`.

**G2 — Profils révisés sur le corpus observé, mesurés, pas devinés à
l'aveugle.** `config/retrieval.yaml` datait du lot 1 : ses clés anglaises
(`syntax`/`theory`/`example`) sont renommées `syntaxe`/`theorie`/`methode`,
alignées sur l'annotation externe (G3). `methode` est un profil nouveau,
sans équivalent au lot 1 (l'ancien `example` visait les cas tests/`V`,
jamais mesuré et toujours vide sur le banc actuel — lot 7b, E3 — et n'est
donc conservé dans aucun des profils mesurés ici).

Diagnostic initial de la relecture externe : `syntax` ne contenait pas
`U3`, cité pour cause directe de l'échec d'`eval-001`. Vérifié sur
l'inventaire réel du lot 6 (`data/raw/inventory.jsonl`) : sur les 36
documents `U3` du corpus 17.4.0, 32 sont des notices de modélisation
(« Modélisations POU_D_T, POU_D_E, BARRE », « Modélisation COQUE_3D »...),
seuls 4 (`U3.01.00`-`U3.04.01`) sont des formats de fichier de maillage —
amendement consigné dans `docs/corpus.md` §3. **Trois jeux de profils
candidats mesurés côte à côte** (banc réaliste complet, G5, index de
référence lot 7 sans E1 — voir G4), pas seulement le jeu « à l'aveugle » que
la consigne demandait explicitement d'éviter :

| Candidat | `syntaxe` | `theorie` | `methode` | réaliste hit@10 | méthode hit@10 |
|---|---|---|---|---|---|
| A, ajout aveugle de `U3` | + `U3` | inchangé | copie de l'ancien `theory` | 76,2 % | 33,3 % |
| B, `U3` partout | + `U3` | + `U3` | `U2,U4,R,U3` (dédié) | 79,4 % | 55,6 % |
| **C, retenu** | **inchangé (sans `U3`)** | **+ `U3`** | **`U2,U4,R,U3` (dédié)** | **82,5 %** | **55,6 %** |

**Résultat, contraire à l'hypothèse de la relecture externe : ajouter `U3` à
`syntaxe` (candidats A et B) est net négatif par rapport à ne pas y toucher
(candidat C).** Cause identifiée par inspection nominative (pas supposée) :
`eval-001` est annotée `theorie` (G3), pas `syntaxe` — ajouter `U3` à
`syntaxe` ne le corrige donc jamais (`eval-001` échoue sous les trois
candidats, voir G6) — et les 4 documents de formats de fichier de `U3`
(non pertinents pour une question de mot-clé de commande) remontent à poids
plein sur des requêtes `syntaxe` sans rapport, évinçant la bonne réponse
`U4` (`eval-017`, `eval-054` corrigées par le seul retrait de `U3` de
`syntaxe`, candidat C contre B — comparaison nominative des échecs à k=10
entre les trois candidats, pas une inspection isolée). Le candidat A échoue
en outre à cause de `methode` : recopier l'ancien `theory` (qui inclut `V`)
pour ce nouveau profil laisse `V` à poids plein, désactivant la suppression
des faux positifs `V`/`D` qui fait tout l'intérêt d'E2 (`eval-003`,
`eval-009` corrigées par le seul retrait de `V`/ajout de `U3` dans
`methode`, candidat B contre A, sans dégrader aucune autre question).
`eval-008`, `eval-041`, `eval-051` restent en échec sous les trois
candidats A, B et C : leur cause n'est jamais la composition du profil
`methode` (déjà bon dans les trois cas pour leur famille attendue), mais un
défaut de recouvrement lexical propre à chacune (voir G6). **`config/
retrieval.yaml` retient le candidat C** :
`syntaxe: [catalogue, U4, U7, testcase, source]`,
`theorie: [R, U2, U4, U3, V]`, `methode: [U2, U4, R, U3]`.

**G3 — Annotation des requêtes, donnée d'entrée, jamais retouchée.**
`/media/sf_partage/echanges/lot7c_query_profiles.jsonl` copié verbatim dans
`data/evaluations/query_profiles.jsonl` (64 lignes, diff vide contre la
source) et versionné ; `aster_expert.retrieval.query_profiles` en est le
seul lecteur, jamais l'auteur. **Écart signalé, pas corrigé** (consigne
G3) : le fichier ne couvre que `eval-001`-`eval-064` — `eval-065` (ajoutée
au lot 5b, après la production de cette annotation) en est absente ; tout
appelant (CLI, banc de mesure) retombe alors sur le profil par défaut
(`syntaxe`), jamais un profil deviné pour la combler. **Une annotation
jugée discutable, signalée sans être changée** : `eval-001` (« quels types
d'éléments finis de poutre sont disponibles... et en quoi diffèrent-ils »)
est annotée `theorie`, alors que ses quatre documents attendus sont tous
`U3` (des notices de modélisation, pas des documents `R`) — un profil
`syntaxe` ou `methode` semblerait au moins aussi défendable pour une
question qui énumère des options disponibles plutôt qu'elle n'explique une
formulation théorique. Le même motif (« quels types... », « quelle est la
différence entre... ») est annoté `theorie` pour `eval-064` alors que son
seul document attendu (`U4.53.03`) est un `U4` pur — sans conséquence
mesurée ici puisque `theorie` inclut `U4`, mais le motif mérite d'être
noté : la formulation comparative de la question semble avoir pesé plus que
la famille documentaire réelle de sa réponse dans cette annotation.

**G4 — E1 réparé, mesuré, retiré du chemin par défaut.**
`aster_expert.indexing.enrichment.enrich_indexed_text` n'injecte plus le nom
d'un mot-clé de premier niveau que dans les fragments dont le chemin de
section le mentionne déjà (le nom de la commande, lui, reste attaché à
chaque fragment du document, seule granularité disponible pour ce lien) —
`data/indexes/bm25_by_file_e1` reconstruit avec la correction :
101433 formes (101437 avant correction, lot 7b).

**Mesuré, pas supposé : la correction ne change rien au chiffre du lot 7b,
et E1 corrigé ne contribue plus rien à E2, dans aucun mode.**

- Seuls **129/13116 fragments** `by_file` (0,98 %) reçoivent encore au
  moins un nom de mot-clé après correction — la granularité `by_file` ne
  découpe presque jamais un fichier à l'échelle d'un seul mot-clé (limite
  déjà connue, `docs/development-plan.md` lot 7). E1 seul, classement
  inchangé : hit@5 = 42,9 %, hit@10 = 60,3 %, hit@20 = 76,2 % — identiques,
  au chiffre, à la mesure buguée du lot 7b (le déficit mesuré au lot 7b ne
  venait donc pas principalement de la pollution par mots-clés, mais du nom
  de commande seul, injecté dans chaque fragment du document, inchangé par
  cette correction).
- **E1(corrigé)+E2a et E1(corrigé)+E2b sont bit pour bit identiques à E2a et
  E2b appliqués seuls sur l'index de référence (non enrichi)**, mêmes
  rappel/MRR à la décimale (`aster-expert eval decompose --profile
  syntax`, comparé à un appel direct de
  `rank_documents_with_source_priority` sur l'index de référence) :

  | Variante | hit@10 (lot 7b, E1 bugué) | hit@10 (lot 7c, E1 corrigé = E2 seul) |
  |---|---|---|
  | E1+E2a (dur) | 81,0 % | 79,4 % |
  | E1+E2b (doux) | 82,5 % | 81,0 % |

  Un sous-produit inattendu de cette mesure : **la part du gain E1+E2 du
  lot 7b qui dépasse ces chiffres corrigés (1,6 point pour E2a, 1,5 point
  pour E2b) provenait donc de la pollution de mots-clés que ce lot
  corrige**, pas d'un effet réel et durable d'E1 — un fait à consigner
  honnêtement, jamais maquillé en régression cachée.

**Conclusion, conforme à la consigne (« s'il reste négatif ou neutre,
retire-le ») : E1 est retiré du chemin par défaut.** `aster-expert search
--profile` interroge l'index de référence (sans enrichissement), jamais
`bm25_by_file_e1`. Le code et le drapeau `aster-expert index build
--enrich-text` ne sont pas supprimés, faute d'instruction de suppression et
parce qu'ils n'ont jamais été mesurés à la granularité `by_subsection` (où
le chemin de section nomme effectivement des mots-clés — `docs/
development-plan.md` lot 7, D2 : « Mot-clé DDL_IMPO » comme sous-section
propre) ; `run_lot7b_decomposition` reste disponible pour qui voudrait
reproduire cette mesure.

**G5 — Mesure : plancher, réaliste, ventilation.** `aster_expert.retrieval.
bench.run_profile_routed_bench` (nouveau, lot 7c) sert chaque question avec
son propre profil (`realistic`) ou un profil unique pour toutes
(`floor`) sur le même index. Sur le candidat C (retenu), granularité
`by_file`, 63 questions résolues :

| Mesure | k | hit@k | recall@k | MRR |
|---|---|---|---|---|
| plancher (`syntaxe` pour toutes) | 5 | 71,4 % | 56,9 % | 0,545 |
| plancher | 10 | **81,0 %** | 65,8 % | 0,545 |
| plancher | 20 | 87,3 % | 74,7 % | 0,545 |
| réaliste (profil annoté) | 5 | 73,0 % | 57,8 % | 0,538 |
| réaliste | 10 | **82,5 %** | 67,3 % | 0,538 |
| réaliste | 20 | 90,5 % | 77,9 % | 0,538 |

Le plancher (81,0 %) est la mesure E2 seule sans E1 (G4) ; le réaliste
(82,5 %) est la situation d'usage réelle visée par ce lot, puisque
l'appelant fournira toujours un profil (G1). Gain du routage seul : +1,5
point à k=10, +3,2 points à k=20 — plus modeste que le gain d'E2 lui-même
(lot 7b), cohérent avec le fait que le plancher applique déjà `syntaxe` à
`syntax`-majoritaire (45/63 questions).

**Cible (85 % de hit@10 sur `answerability = explicit`, 59 questions),
atteinte pour la première fois :**

| Mesure | hit@10 explicite | écart à la cible |
|---|---|---|
| plancher | 81,4 % (48/59) | -3,6 points |
| **réaliste** | **86,4 % (51/59)** | **+1,4 point — cible atteinte** |

Ventilation par profil (réaliste, hit@10) : `syntaxe` 91,1 % (41/45
questions), `theorie` 66,7 % (6/9), `methode` 55,6 % (5/9). `syntaxe`
domine le banc (71 % des questions) et porte l'essentiel du gain ; `theorie`
et `methode` restent nettement sous la cible — un fait à ne pas dissimuler
derrière le chiffre global.

**Liste nominative des 11 échecs à k=10 (réaliste), avec le profil
utilisé :**

| Question | Profil | Domaine | Attendu | Obtenu (top 3) |
|---|---|---|---|---|
| eval-001 | theorie | modelisation_poutre | U3.11.01, U3.11.04, U3.11.05, U3.11.07 | U2.06.10, U2.06.03, U2.03.11 |
| eval-006 | methode | interaction_sol_structure | R5.03.17 | U2.01.09, U2.03.09, R5.06.03 |
| eval-008 | methode | modelisation_coque | U4.42.01, U4.43.01 | R3.08.02, R7.02.04, U2.06.32 |
| eval-010 | theorie | lois_comportement | R5.03.17 | V5.05.101, V2.02.401, R5.03.09 |
| eval-035 | syntaxe | post_traitement | U4.81.04 | U4.81.05, U4.81.42, U4.44.01 |
| eval-041 | methode | verification | U4.81.21, U4.81.04 | U2.01.11, U4.54.02, U4.51.03 |
| eval-045 | syntaxe | post_traitement | U4.81.21 | U4.81.04, U7.03.01, U7.03.02 |
| eval-048 | theorie | interaction_sol_structure | U7.03.12, R4.05.04, R4.05.07 | U2.04.03, R4.02.05, U4.53.05 |
| eval-051 | methode | verification | U4.81.22 | U4.66.11, U4.66.01, U2.06.10 |
| eval-063 | syntaxe | dynamique | U2.06.03, U4.43.01, U4.53.05 | U4.65.01, U7.03.12, U4.32.11 |
| eval-065 | syntaxe (défaut, non annotée) | dynamique | U4.31.03, U4.32.02 | U4.32.04, U7.03.12, U4.32.13 |

**G6 — Conclusion sur l'index vectoriel, chiffrée, rien engagé.** À k=20
(même candidat C, même mesure réaliste), 6 des 11 échecs ci-dessus
persistent (`eval-001`, `eval-006`, `eval-010`, `eval-045`, `eval-051`,
`eval-065` — les 5 autres, dont `eval-035`/`eval-041`/`eval-063`/`eval-008`,
sont résolus dès qu'on élargit la profondeur) : le document attendu
**n'apparaît jamais** dans les 20 premiers résultats, sous aucun des trois
profils, ni au candidat A, B ou C. Sur ces 6, 5 sont `answerability =
explicit` (`eval-001`, `eval-010`, `eval-045`, `eval-051`, `eval-065` —
`eval-006` est `inferable`, hors du dénominateur des 59 questions
explicites) : **5/59 (8,5 %) des questions explicites du banc ne retrouvent
jamais leur document attendu, à aucune profondeur mesurée, sous aucun
profil ni aucune variante de routage essayée dans ce lot ou le lot 7b**
(enrichissement E1, filtre dur E2a, repondération douce E2b, profils
révisés G2). Ce n'est jamais un problème de précision (la bonne famille est
déjà priorisée pour chacune) : c'est un défaut de recouvrement lexical pur
— la question n'emploie aucun terme qui recoupe le vocabulaire propre du
document cible (`eval-010` : « ressort ne travaillant qu'en compression »
contre la dénomination technique de la loi `DIS_CONTACT` dans `R5.03.17` ;
`eval-051` : « vérifier la masse totale d'un modèle » contre le nom
d'opérande propre à `U4.81.22`).

**Conclusion, chiffrée, rien engagé dans ce lot :** 5 échecs sur 59 (8,5 %)
est un chiffre nettement supérieur au « deux échecs sur cinquante-neuf » que
l'instruction de ce lot qualifie explicitement d'insuffisant pour justifier
le lot C1 — et ces 5 échecs partagent un motif identique, jamais corrigé
par deux lots de réglage lexical successifs (enrichissement du texte
indexé, routage par famille, révision des profils). C'est une base
chiffrée et nommée, pas une impression : **le lot C1 (index vectoriel)
paraît justifié sur cette base**, précisément parce que le motif résiduel
(absence de recouvrement lexical, pas un problème de priorité de famille)
est exactement ce qu'un index vectoriel adresse et qu'un réglage lexical
supplémentaire n'adresserait pas. Rien n'est engagé vers ce lot ici,
conformément à l'instruction — ni embedding, ni base vectorielle, ni
prototype.

`eval-048` (`partial`, `interaction_sol_structure`) reste un échec distinct
de ce groupe : sa cause est la lacune de corpus déjà consignée
(`docs/corpus.md` §8, `U2.06.05`/`U2.06.07` absents du dépôt synchronisé),
jamais un défaut de recherche — aucun index, vectoriel ou lexical, ne peut
retrouver un document qui n'existe pas dans le corpus synchronisé.

**NE PAS FAIT (conforme à la consigne).** Aucun embedding, aucun
reranking par modèle, aucun serveur MCP. Le jeu d'évaluation
(`data/evaluations/questions.jsonl`) n'a pas été modifié ; l'annotation de
profils (`data/evaluations/query_profiles.jsonl`) copiée verbatim, jamais
retouchée (l'écart `eval-065` et l'annotation discutable d'`eval-001` sont
signalés ci-dessus, pas corrigés). Aucun classifieur ni heuristique de
détection automatique de profil (G1, ADR-007). Le lot C1 n'a reçu aucun
développement (G6).

**Garde-fou de parallélisme.** Aucun sous-agent utilisé dans ce lot :
`git status --short` relevé avant modification (dépôt propre, `HEAD` sur
`main`) et à la clôture (seuls les fichiers de l'inventaire ci-dessous
modifiés).

**Inventaire des fichiers créés ou modifiés.**

- Créés : `src/aster_expert/retrieval/query_profiles.py`,
  `tests/unit/test_query_profiles.py`, `data/evaluations/query_profiles.jsonl`.
- Modifiés : `config/retrieval.yaml` (profils renommés et révisés),
  `src/aster_expert/indexing/enrichment.py` (G4),
  `src/aster_expert/indexing/models.py` (renommage de
  `TextEnrichment`), `src/aster_expert/indexing/bm25_index.py` (même
  renommage), `src/aster_expert/retrieval/bench.py`
  (`rank_documents_with_query_profile`, `run_profile_routed_bench`,
  `ProfileFailureCase`, `ProfileBenchReport`),
  `src/aster_expert/retrieval/source_priority.py` (relais des filtres
  `family`/`document_id`/`command`/`section_contains`),
  `src/aster_expert/cli.py` (`search --profile`/`--priority-mode`, `eval
  profile-bench`, renommage du défaut d'`eval decompose`),
  `docs/architecture.md` (ADR-007), `docs/corpus.md` (§3 amendement `U3`,
  §8 `query_profiles.jsonl`), `docs/development-plan.md` (cette clôture) ;
  tests mis à jour en conséquence
  (`tests/unit/test_enrichment.py`, `test_bm25_index.py`,
  `test_retrieval_config.py`, `test_source_priority.py`, `test_bench.py`,
  `tests/test_cli.py`).

**Tests.** 12 tests nouveaux (4 dans `test_query_profiles.py`, 2 dans
`test_bench.py` (`rank_documents_with_query_profile`,
`run_profile_routed_bench`), 2 dans `test_source_priority.py` (relais de
filtres), 2 nets dans `test_enrichment.py` (1 renommé, 2 ajoutés pour la
portée du mot-clé G4, 1 retiré), 2 dans `tests/test_cli.py` (`search
--profile` inconnu, `eval profile-bench` sans annotation)), plus 1 test
réécrit dans `test_retrieval_config.py` (profils français) et une valeur
corrigée dans `test_bm25_index.py` — fixtures locales uniquement, aucun
accès réseau. Suite complète du projet : **353 tests (341 avant ce lot),
0 échec**. `ruff format`/`ruff check` propres sur tout le code touché ;
`mypy` (configuration du projet, `src` + `tests`) ne signale aucune
régression nouvelle — les 7 erreurs résiduelles
(`test_sources_sync.py`, `test_evaluation.py` ×3, `test_detect.py`,
`test_catalogue_extract.py`) sont identiques, fichier et ligne, à celles de
`main` avant toute modification (vérifié par `git stash`), hors périmètre
de ce lot.

**Limites connues.**

- `search --profile` n'utilise jamais l'index enrichi E1
  (`bm25_by_file_e1`), retiré du chemin par défaut (G4) — un appelant qui
  voudrait comparer continue de le faire via `aster-expert eval decompose`,
  jamais via `search` lui-même.
- Le profil `methode` et `theorie` n'ont été mesurés qu'à la granularité
  `by_file` (consigne : ne pas changer la granularité par défaut) — jamais
  à `by_subsection`, où le chemin de section nomme effectivement des
  mots-clés (voir G4) et où l'effet d'E1 pourrait différer.
- `run_profile_routed_bench` retombe sur `default_profile` pour toute
  question absente de l'annotation (`eval-065` seule aujourd'hui) — un
  choix documenté (G1 : le même repli que l'appelant CLI), jamais mesuré
  séparément d'un éventuel autre repli.
- La cible de 85 % n'est atteinte qu'en moyenne globale (réaliste,
  86,4 %) ; les profils `theorie` (66,7 %) et `methode` (55,6 %) restent
  chacun nettement sous la cible pris isolément — un fait que la moyenne
  globale ne doit pas masquer.
- `hard_filter_search`/`soft_reweight_search` acceptent maintenant
  `family`/`document_id`/`command`/`section_contains`, mais aucun test ne
  couvre leur combinaison avec `family_in` simultanément active sur les
  *deux* passages du filtre dur (primaire et repli) au-delà du cas simple
  déjà testé.

## Lot 8 — Serveur MCP minimal

Quatre outils (amendement à l'ouverture du lot, cf. clôture ci-dessous) :
`search_codeaster_docs`, `get_command_schema`, `analyze_comm`,
`validate_comm`. Wrapper mince sur les fonctions existantes, sans logique
propre.

Critères de sortie : serveur interrogeable, contrats d'entrée et de sortie
validés par modèle, tests d'intégration sur corpus réduit.

**Clôture du lot 8 — serveur MCP.**

Le lot a été ouvert avec quatre outils à exposer, pas les deux esquissés
plus haut au moment du plan initial (`search_codeaster_docs`,
`get_command_schema`, `analyze_comm`, `validate_comm`) : la consigne
d'ouverture du lot l'a explicitement élargi, et ce paragraphe de plan est mis
à jour en conséquence plutôt que laissé périmé.

- **H1, contrats jamais redéfinis à la main.** `aster_expert.mcp.models`
  n'ajoute que ce qui manquait pour porter `validation_level` : trois
  enveloppes (`SearchDocsResult`, `CommandSchemaResult`, `CommAnalysisResult`)
  qui composent `SearchHit`/`CommandSchema`/`KeywordSchema`/`CommFileAnalysis`
  comme champs, jamais en recopiant un de leurs attributs.
  `validate_comm` ne construit aucune enveloppe : `ValidationReport` porte
  déjà `validation_level` (toujours `"B"`), donc le rapport est renvoyé tel
  quel.
- **H2, le niveau et les sources voyagent avec la réponse.**
  `search_codeaster_docs`/`get_command_schema`/`analyze_comm` portent
  `validation_level: "A"` -- aucun des trois ne confronte un fichier réel au
  catalogue, n'exécute rien, ni ne contrôle un résultat physique ; c'est ce
  qui distingue "A" de "B", pas la nature de la source consultée (le
  catalogue lui-même, consulté par `get_command_schema`, est pourtant la
  source de vérité syntaxique -- ADR-001 -- mais présenter son contenu brut
  n'est toujours pas confronter un fichier utilisateur à ce contenu :
  `validate_comm` reste seul à porter "B"). Les sources (document, section,
  chemin, révision Git ; digest d'image et hash de catalogue pour
  `get_command_schema`/`validate_comm`) sont déjà portées par les modèles
  existants, jamais ajoutées à part.
- **H1, profil jamais deviné (ADR-007 étendu au serveur).**
  `search_codeaster_docs` prend `profile` en paramètre explicite, sans
  valeur par défaut cachée au-delà de celle déjà déclarée par
  `config/retrieval.yaml` (`syntaxe`) ; la description de l'outil (visible
  par l'appelant avant tout appel) explique quand choisir `syntaxe`,
  `theorie` ou `methode`, plutôt que de laisser le serveur deviner à partir
  du texte de la requête.
- **H3, journalisation.** `aster_expert.mcp.logging.append_query_log` ajoute
  une ligne JSON à `data/processed/query_log.jsonl` par appel (horodatage,
  outil, requête, profil, filtres, identifiants retournés avec leurs scores,
  durée) ; `analyze_comm`/`validate_comm` n'y passent jamais que le nom du
  fichier et son empreinte SHA-256 (jamais son contenu, jamais un résumé
  dérivé du contenu comme les noms de commandes rencontrées). Vérifié par
  test (`tests/unit/test_mcp_tools.py`, assertions `"MAIL" not in
  json.dumps(entry)` / `"LIRE_MAILLAGE" not in ...`) et par un appel réel
  (compte rendu de lot) dont le journal produit ne contient que
  `file_name`/`file_fingerprint`.
- **Choix du SDK, constaté en session.** `mcp>=1.2` (pyproject.toml avant ce
  lot) installe en pratique la 2.x (2.2.0 au moment du lot) : son API a
  renommé `FastMCP` en `MCPServer` entre la 1.x et la 2.x (incompatible --
  `from mcp.server.fastmcp import FastMCP` échoue avec un message de
  migration explicite sous 2.x). Ce projet écrit donc contre `MCPServer`,
  jamais `FastMCP`, et `pyproject.toml` épingle `mcp>=2.0,<3` pour ne plus
  laisser cette ambiguïté glisser silencieusement. `MCPServer.call_tool`
  (appel direct, sans transport) sert de harnais de test : il distingue
  explicitement une erreur anticipée (`ToolError`, message conservé) d'un
  crash (`UnexpectedToolError`, message générique, cause d'origine dans
  `__cause__`) -- `aster_expert.mcp.errors.McpToolError` hérite de
  `ToolError` précisément pour ça (CLAUDE.md, "ne jamais neutraliser une
  alarme sans en expliquer la cause").
- **H5, contrat de sortie invalide.** Vérifié directement contre le SDK,
  pas seulement contre une convention du projet
  (`tests/integration/test_mcp_server.py::
  test_invalid_output_contract_fails_loudly_never_partial`) : un outil
  jouet annoté `-> SearchDocsResult` qui renvoie un objet incomplet fait
  échouer `call_tool` avec `UnexpectedToolError`, jamais un résultat
  partiel accepté tel quel.
- **Limites connues, non traitées ici (hors périmètre du lot).** Aucun cache
  d'index/catalogue entre deux appels : chaque appel recharge l'index BM25
  et relit le fichier de schéma depuis le disque -- mesuré négligeable ici
  (le corpus tient largement en mémoire, lot 6/7) mais non chiffré sous
  charge répétée ; à traiter sur preuve si un usage réel le justifie, jamais
  anticipé. `query_log.jsonl` n'est ni relu, ni compacté, ni fait tourner
  par ce lot -- seule l'écriture existe, conformément à la consigne
  d'ouverture ("il faut qu'il soit exploitable dès le premier jour d'usage",
  pas qu'il soit déjà exploité). Aucun outil de génération ou de
  modification de fichier `.comm` n'est exposé : les quatre outils sont tous
  en lecture (recherche, catalogue, analyse, validation) au sens où aucun
  n'écrit dans le dépôt de l'utilisateur.

## Lot 8b — Discipline d'usage des outils, et latence

**J1 — latence mesurée avant toute optimisation.**
`data/processed/query_log.jsonl` (écrit par le lot 8) portait déjà six
appels réels des quatre outils, dans une seule session :

| Outil | Appels | Durée(s) réelle |
|---|---|---|
| `search_codeaster_docs` | 3 (même requête) | 5,226 / 1,199 / 1,035 |
| `get_command_schema` | 1 | 0,028 |
| `analyze_comm` | 1 | 0,006 |
| `validate_comm` | 1 | 54,372 |

Le premier appel de `search_codeaster_docs` dépasse le seuil de deux
secondes fixé par la consigne du lot ; les deux suivants, sur la même
requête dans le même processus, restent au-dessus d'une seconde alors
qu'aucun cache applicatif n'existait encore -- cause déjà nommée par la
clôture du lot 8 (« chaque appel recharge l'index BM25 et relit le
fichier de schéma depuis le disque ») et confirmée ici par lecture du
code : `aster_expert.mcp.tools.search_codeaster_docs` appelait
`load_bm25_index` (rechargement de `bm25s.BM25.load`, retriever + corpus)
sans aucune mise en cache, à chaque invocation. `get_command_schema`
(0,028 s) et `analyze_comm` (0,006 s) étaient déjà sous la seconde :
aucune optimisation n'y est apportée pour cette seule raison (CLAUDE.md,
« pas d'optimisation sans mesure »). `validate_comm` (54,372 s) est un
temps d'exécution Docker réel, pas un coût de rechargement : hors du
périmètre de ce cache.

**Cache posé (`aster_expert.mcp.cache`, nouveau module).** Deux
dictionnaires en mémoire, vivants pour la durée du processus serveur (un
redémarrage du serveur MCP les vide ; rien n'est persisté sur disque ni
partagé entre processus) :

- `cached_bm25_index(index_dir)` mémoïse `load_bm25_index` (clé : chemin
  résolu de l'index).
- `cached_command_schema(catalogue_root, digest, command)` mémoïse
  `load_command_schema` (clé : racine résolue + digest + commande).

`aster_expert.mcp.tools.search_codeaster_docs`/`get_command_schema` les
utilisent à la place des fonctions de chargement directes ; aucune autre
logique de classement, de chunking, d'extraction ou de validation n'est
modifiée. Le catalogue est mis en cache aux côtés de l'index, tel que
demandé par la consigne d'ouverture du lot (« un cache ... de l'index et
du catalogue »), même si `get_command_schema` seul n'avait pas franchi le
seuil de deux secondes.

Mesure après cache, même requête, même processus, trois appels
consécutifs (journal réel, `data/processed/query_log.jsonl`) :

| Outil | Appel 1 (froid) | Appel 2 | Appel 3 |
|---|---|---|---|
| `search_codeaster_docs` | 9,335 s | 0,033 s | 0,028 s |
| `get_command_schema` | 0,063 s | 0,023 s | 0,029 s |

Le premier appel reste coûteux (chargement disque incompressible, sur
lequel un cache ne peut agir qu'à partir du deuxième appel) -- plus élevé
même qu'avant (9,335 s contre 5,226 s), écart attribué à l'état du cache
disque du système au moment de la mesure, pas au cache applicatif qui
n'intervient qu'ensuite. Les appels suivants tombent de 1,0-1,2 s à
0,02-0,03 s pour `search_codeaster_docs` (gain ×35 à ×40), sans recharger
l'index ni le fichier de schéma. `get_command_schema`, déjà sous la
seconde avant ce lot, y reste ; son propre gain (0,028 s → 0,02-0,03 s
après un premier appel mesuré à 0,063 s) n'était pas requis par la mesure
mais découle du même mécanisme, posé une seule fois pour les deux outils.

Tests : `tests/unit/test_mcp_cache.py` (nouveau, trois cas : chargement
unique par processus pour l'index et pour le schéma, deux répertoires
d'index distincts jamais confondus) et deux tests ajoutés à
`tests/unit/test_mcp_tools.py`
(`test_search_codeaster_docs_reuses_cached_index_across_calls`,
`test_get_command_schema_reuses_cached_schema_across_calls`), qui
vérifient par comptage d'appels à la fonction de chargement réelle qu'un
second appel identique ne retouche jamais le disque.

**J2 — skill `code-aster-expert`.**
`.claude/skills/code-aster-expert/SKILL.md`, plus trois fichiers de
référence chargés à la demande (`references/citation.md`,
`references/comm-workflow.md`, `references/answer-format.md`), décrivent
la procédure d'usage des quatre outils du serveur MCP -- identification de
la version cible, choix explicite et annoncé du profil de recherche,
interdiction d'énoncer une syntaxe sans preuve outillée, citation
systématique (document, section, version, chemin), annonce du niveau de
validation atteint (jamais au-dessus de ce qui a été réellement obtenu),
`analyze_comm` puis `validate_comm` pour un `.comm` (jamais une lecture à
l'œil), distinction faits/déductions/recommandations. Aucune connaissance
Code_Aster de première main n'y est écrite : chaque affirmation de
syntaxe renvoie à l'outil qui la fournirait, jamais à une valeur citée en
dur dans le skill.

**J3 — vérification sur trois questions réelles, appels bruts rapportés.**
Trois questions ont été effectivement posées aux quatre outils MCP dans
cette session (jamais choisies après coup pour « marcher ») :

1. *« Comment définir une section circulaire pour une poutre avec
   AFFE_CARA_ELEM ? »* -- `search_codeaster_docs(profile="syntaxe", k=5)`
   (le meilleur résultat, `U4.42.01#Affectation_de_valeurs`, ne portait
   pas encore l'opérande cherché), puis
   `get_command_schema(command="AFFE_CARA_ELEM",
   keyword="POUTRE.SECTION")` : `allowed_values` contient `"CERCLE"`
   (variante `e7bec782a25c46a1`, v17.4.0) -- fait documenté, cité par
   l'outil qui l'a produit (le catalogue, pas la recherche documentaire).
   Niveau A.
2. *« Différence entre les lois de comportement DIS_CHOC et DIS_CONTACT
   pour un élément discret ? »* -- `search_codeaster_docs(profile
   ="theorie", k=5)` ne renvoyait pas `R5.03.17` ; relancé à `k=15`,
   `R5.03.17#Modelisation_des_chocs_et_du_frottement_DIS_CONTACT` (rang 11)
   et `#Modelisation_des_chocs_et_du_frottement_DIS_CHOC` (rang 16) sont
   sortis. Fait documenté cité : R5.03.17, v17.4.0,
   `source/manuals/man_r/r5/r5.03.17/...` -- DIS_CONTACT (schéma implicite,
   raideurs "physiques") est recommandé quand DIS_CHOC (schéma explicite,
   raideurs "pénalisantes") ne convient pas, les deux exprimant un contact
   unilatéral. Confirmé en niveau A par `get_command_schema` (`STAT_NON_LINE
   .COMPORTEMENT.RELATION` liste bien `DIS_CHOC`/`DIS_CONTACT` parmi les
   valeurs autorisées du catalogue, v17.4.0). Niveau A -- il a fallu
   élargir `k` pour que le document sorte, observation directement utile
   au J4 ci-dessous.
3. *« Comment vérifier la masse totale d'un modèle ? »* (= `eval-051`,
   profil annoté `methode`) -- `search_codeaster_docs(profile="methode",
   k=10)` puis `k=20` : le document attendu (`U4.81.22`, opérateur
   `POST_ELEM`, mot-clé `MASS_INER`) n'apparaît dans aucun des deux, sous
   ce profil (résultats obtenus : `U4.66.11`, `U4.66.01`, `U2.06.10`,
   ... -- tous relatifs à la « masse ajoutée » fluide-structure ou à une
   liste de vérifications préalables en sismique, jamais au calcul de la
   masse totale d'un modèle). Conclusion rapportée telle quelle à
   l'utilisateur : *la documentation indexée ne tranche pas cette question
   sous le profil `methode`*, plutôt que de forcer une réponse à partir
   d'un résultat hors sujet. Remarque annexe, marquée comme telle (pas une
   réponse) : sous le profil `syntaxe` (non celui annoté pour cette
   question), `U4.81.22#But` apparaît en rang 10 -- signalé comme piste,
   jamais présenté comme une réponse trouvée par le profil retenu.

Aucune des trois réponses n'a été donnée sans appel d'outil ; le skill
n'a pas été contourné.

**J4 — les cinq questions du lot 7c jamais retrouvées, examen du texte
attendu.** Rappel nominatif (`docs/development-plan.md`, clôture lot 7c,
G6) : `eval-001`, `eval-010`, `eval-045`, `eval-051`, `eval-065` --
5/59 (8,5 %) des questions `answerability=explicit` du banc, jamais
retrouvées à `k<=20`, sous aucun des trois profils, dans aucun des lots 7/7b/7c.

| id | libellé | `required_documents` | nature du texte attendu |
|---|---|---|---|
| `eval-001` | Quels types d'éléments finis de poutre sont disponibles pour modéliser un pieu, et en quoi diffèrent-ils | `U3.11.01`, `U3.11.04`, `U3.11.05`, `U3.11.07` (`index.rst` de chaque modélisation) | Prose réelle mais très courte (un résumé de quelques phrases par fichier, ex. U3.11.01 : « Les quatre modélisations POU_D_T, POU_D_E et BARRE correspondent aux formulations classiques d'éléments de poutres... ») -- jamais un tableau de mots-clés, mais un vocabulaire générique qui ne reprend aucun terme différenciateur de la question (« pieu », « en quoi diffèrent-ils ») : déficit lexical, pas un problème de découpage. |
| `eval-010` | Quelle relation de comportement décrit un ressort ne travaillant qu'en compression | `R5.03.17` (sections DIS_CHOC/DIS_CONTACT) | Prose réelle et développée (théorie, équations, figures) : « Le comportement DIS_CONTACT traduit le contact avec choc et frottement... la relation de contact unilatéral... ». Aucune occurrence de « ressort » ni « compression » : vocabulaire physique/théorique (« contact unilatéral », « non-interpénétrabilité ») contre vocabulaire de métier de la question -- déficit lexical pur, confirmé en J3.2 ci-dessus (le document ressort dès que la requête emploie les termes techniques `DIS_CHOC`/`DIS_CONTACT` eux-mêmes, à `k=15`). |
| `eval-045` | Comment obtenir les valeurs extrêmes d'un champ et leur localisation | `U4.81.21` | Le fichier cité par `verified_by` (`Exemples.rst`) est surtout du code et des tables de résultats, peu de prose. Mais le même document (`U4.81.21`, fichier `Principes_d_utilisation...ACTION.rst`) contient une vraie phrase descriptive : « de calcul de minimum et de maximum sur des groupes ou des entités : 'EXTREMA' » et « Le lieu du post-traitement désigne une figure géométrique... ». Prose réelle, présente dans le même document, mais avec un vocabulaire voisin sans être identique (« minimum et maximum » pour « valeurs extrêmes », « lieu » pour « localisation ») -- toujours un déficit lexical (synonymie), pas une absence de prose ni un défaut de découpage : le bon fragment existe et est indexé, il n'emploie simplement pas les mots de la question. |
| `eval-051` | Comment vérifier la masse totale d'un modèle | `U4.81.22` | `Op_randes.rst`, mot-clé `MASS_INER` : prose réelle (« Mot clé facteur permettant de calculer la masse, les inerties et le centre de gravité... ») mêlée à des formules. Le mot « masse » y figure, mais ni « vérifier » ni « totale » -- registre de documentation de référence (opérande par opérande) contre une question formulée en langage d'usage. Déficit lexical de registre, pas un tableau de mots-clés sans phrase, confirmé en J3.3 ci-dessus (toujours absent à `k=20` sous le profil annoté). |
| `eval-065` | Comment déclarer un spectre d'oscillateur déjà défini par des valeurs tabulées, sans le calculer depuis un accélérogramme | `U4.31.03`, `U4.32.02` | `But.rst` de chaque opérateur : prose réelle mais extrêmement courte et générique (« Définir une fonction réelle de deux variables réelles... », « Lire un fichier de données contenant des valeurs réelles... ») -- aucune mention de « spectre », « oscillateur », « réglementaire » ni « accélérogramme » : la description générique de l'opérateur ne recoupe jamais le vocabulaire du cas d'usage spécifique posé par la question. Déficit lexical, pas un problème de découpage (le fichier `But.rst` est déjà le plus petit grain indexé pour ce document). |

Dans les cinq cas, le texte attendu est une **prose réelle** (jamais un
simple tableau de mots-clés sans phrase) qui n'emploie tout simplement pas
le vocabulaire de la question -- synonymie (`eval-045`, `eval-010`),
registre documentaire contre langage d'usage (`eval-051`), ou généricité
d'un résumé qui ne nomme pas le cas d'usage précis (`eval-001`,
`eval-065`). C'est donc bien un **déficit lexical**, relevant d'un index
vectoriel (conclusion déjà posée, chiffrée, par la clôture du lot 7c),
jamais un problème de découpage : aucun de ces cinq documents ne
bénéficierait d'un correctif de chunking, puisque le fragment concerné
existe déjà tel quel, indexé, et contient déjà la bonne réponse en prose
-- il n'est simplement jamais choisi par un score lexical qui ne recoupe
aucun terme de la question.

**NE PAS FAIT (conforme à la consigne).** Aucun embedding, aucune
modification du découpage, du classement, du catalogue, du validateur ni
du jeu d'évaluation. Le skill décrit un usage des quatre outils
existants, il n'ajoute aucune capacité ni n'écrit de connaissance
Code_Aster en dur.

## Lot 9 — Parseur `.comm`

Analyse structurelle sans exécution, conforme à `docs/metadata.md`. Gestion
explicite des constructions dynamiques.

Critères de sortie : tests sur plusieurs formes syntaxiques réelles issues des
cas tests, dont au moins un fichier à construction dynamique, avec `unresolved`
correctement renseigné.

**Note (à consigner sans l'implémenter, lot 4).** Pour permettre au lot 10
d'appeler `checkCommandSyntax` par reconstruction des arguments (plutôt que de
réimplémenter sa logique — voir la note du lot 10), le parseur doit conserver,
pour chaque mot-clé :

- la valeur littérale et son type Python quand elle est statiquement
  déterminable (nombre, chaîne, liste, `_F(...)` imbriqué) — directement
  utilisable comme entrée de `checkCommandSyntax` ;
- un marqueur explicite sinon (référence à un concept produit par une
  commande précédente, expression non littérale, construction dynamique).

Une commande dont un argument est construit dynamiquement (boucle,
dictionnaire assemblé, fonction utilisateur) est déclarée non vérifiée
(`unresolved`), jamais devinée. `docs/metadata.md`, section 3 (schéma
d'analyse d'un `.comm`), est à amender en conséquence à l'ouverture de ce
lot : le champ `keywords` d'un `statement` doit pouvoir distinguer une valeur
littérale typée d'un marqueur de non-résolution, pas seulement lister des
noms de mots-clés.

## Lot 10 — Validation statique niveau B

Confrontation du résultat du lot 9 au catalogue du lot 4 : commande inconnue,
mot-clé inconnu, cardinalité, type de valeur, blocs conditionnels, concept
utilisé avant définition.

Critères de sortie : détection correcte sur un jeu de fichiers fautifs
construits pour les tests, absence de faux positif sur un échantillon de cas
tests officiels.

**Note (découverte anticipée, lot 2, à trancher formellement à l'ouverture du
lot 10).** `code_aster.Cata.SyntaxChecker` (ré-export de
`code_aster.Cata.Language.SyntaxChecker`) expose un vérificateur officiel,
utilisé par le superviseur lui-même (ADR-001) :

- `checkCommandSyntax(command, keywords, add_default=True, max_check=99999)` —
  fonction publique : `command` est un objet catalogue
  (`code_aster.Cata.Commands.<NOM>`), `keywords` un dict Python déjà typé
  (valeurs évaluées, pas du texte `.comm`). Lève `CheckerError` (attributs
  `.msg`, `.original`, pile de mots-clés) **ou**, pour certaines règles
  (`AU_MOINS_UN`, `EXCLUS`, etc., définies dans `Language/Rules.py`),
  directement `ValueError`/`TypeError`/`KeyError` non enveloppée — un wrapper
  doit capturer les deux catégories.
- `SyntaxCheckerVisitor(max_check=99999)` — classe visiteur sous-jacente
  (`visitCommand`, `visitFactorKeyword`, `visitSimpleKeyword`,
  `_visitComposite`), vérifie cardinalité, type, bornes, appartenance `into`,
  mots-clés obligatoires et règles.

Vérifié empiriquement en session (image `simvia/code_aster@sha256:d8d19ea9...`,
17.4.0) : `import code_aster.Cata.Commands` puis `checkCommandSyntax` (via
`code_aster.Cata.SyntaxChecker`) fonctionnent **sans** `CA.init()`, sans
extension compilée `libaster`, sans MPI — seule dépendance tierce : `numpy`.
Un mot-clé non autorisé et un type de valeur incorrect ont bien été détectés
et signalés avec un message exploitable.

Limite non résolue par cette découverte : `checkCommandSyntax` attend des
**valeurs Python déjà évaluées**, pas du texte source non exécuté. Une valeur
littérale (nombre, chaîne, liste, `_F(...)` imbriqué) reste vérifiable après
un simple `ast.literal_eval` sans exécuter le fichier ; un concept produit par
une commande précédente (ex. un maillage passé à une commande suivante) exige
un objet Python de type correct (`DataStructure`), pas seulement son nom — le
vérificateur accepte cependant `DS.not_checked`/`DS.PythonVariable` comme
échappatoires dont l'usage reste à étudier pour construire un objet de
substitution ne nécessitant pas d'exécution réelle.

**Conséquence attendue pour l'ouverture du lot 10** (à confirmer, pas encore
tranché) : ne pas réimplémenter la logique de vérification de cardinalité,
type ou règle — elle existe et doit être appelée via `checkCommandSyntax`. Le
travail propre au lot 10 se limiterait alors à la reconstruction, à partir du
résultat du parseur (lot 9), d'un dict de mots-clés en valeurs Python pour
chaque commande résolue statiquement, et à la gestion explicite des concepts
non résolus sans exécution (`unresolved`, déjà prévu par le lot 9).

**Note complémentaire (lot 4b, C2/C3, vérifiée empiriquement contre
`checkCommandSyntax` — sorties réelles dans le compte rendu de ce lot).**

- Une valeur vide (`[]`) pour un mot-clé simple obligatoire est traitée par
  le vérificateur officiel comme une **absence** (`is_undefined([])` vaut
  `True`), pas comme une violation de cardinalité : elle lève
  `KeyError: 'Keyword ... is mandatory'`, la même erreur qu'une absence pure
  et simple. Le lot 10 ne doit donc pas distinguer "valeur vide fournie" de
  "mot-clé absent" pour un mot-clé obligatoire : reconstruire `[]` ou omettre
  la clé du dict produit le même diagnostic chez `checkCommandSyntax`, et
  c'est le comportement correct à préserver, pas à contourner.
- `status: "hidden"` (`statut="c"`, voir `docs/metadata.md` §2) doit être
  traité comme fonctionnellement équivalent à `"optional"` pour la
  vérification (jamais requis, accepté explicitement) : `isHidden()` n'est
  utilisé nulle part dans `SyntaxChecker.py` ni ailleurs dans le dépôt
  source, ce n'est pas une notion de validation. À trancher formellement à
  l'ouverture de ce lot : si un outil de complétion/génération de `.comm`
  est un jour construit, il ne doit pas proposer un mot-clé caché comme une
  option normale (hors périmètre de ce lot, mais la distinction doit être
  préservée dans le schéma, pas aplatie avec `"optional"`).

## Lot 10b — Couverture de la validation et élimination des faux positifs

Traite les causes identifiées des 225 erreurs et du taux de vérification de
53,0 % du lot 10, par ordre de gain, en continuant à déléguer à Code_Aster
plutôt qu'en réimplémentant.

**A. Résolution dynamique du type de concept (le plus gros levier).**
`result_type_dynamic` signifie que le catalogue calcule le type par une
fonction `sd_prod`. Le lot 10 ne l'appelait jamais : la table concept → type
(M1, `concept_types.py`) était calculée hors conteneur, à partir du seul
`result_type` statique du catalogue, donc toujours inconnue pour un concept
produit par l'une des 94 commandes à `result_type_dynamic` vrai sur 268
(`LIRE_MAILLAGE`, `CALC_CHAMP`, `CREA_CHAMP`, `CREA_RESU`, `CALC_TABLE`, ...).
Vérifié expérimentalement dans le conteneur (sorties réelles dans le compte
rendu de ce lot) : `Command.get_type_sd_prod(**keywords)` — la méthode
officielle appelée par `Command.call_default` lui-même après
`checkCommandSyntax` — ajoute les mots-clés par défaut, complète les
arguments manquants de `sd_prod` par `None` (`add_none_sdprod`), et distingue
elle-même un `Operator` (`sd_prod(**ctxt)`) d'un `Macro` (`sd_prod(self,
**ctxt)`) : jamais besoin de reproduire cette distinction à la main. Appelée
seule, sans `checkCommandSyntax` préalable, elle peut renvoyer un type erroné
sans lever d'exception (`CALC_CHAMP` sans `RESULTAT` résout vers le `NoneType`
Python plutôt que de lever) — mais `SyntaxCheckerVisitor.visitCommand`
(`Cata/Language/SyntaxChecker.py`) appelle déjà `get_type_sd_prod` en interne
et transforme son échec en `CheckerError` : un `checkCommandSyntax` qui
réussit garantit donc que le second appel réussira aussi, sans jamais avoir
besoin d'un filet de sécurité séparé.

Le mécanisme M1 hors conteneur est supprimé (`concept_types.py`) et remplacé
par une résolution **en direct, dans l'ordre du fichier** :
`aster_expert.validation.reconstruct` (M2) ne reconstruit plus un type par
avance — une référence de concept (`reuse=` compris) devient un marqueur
`{"__concept_ref__": "<nom>"}`, jamais un type deviné. `scripts/
check_command_syntax.py` (M3), exécuté dans le conteneur, traite les
`statement` d'un fichier dans l'ordre du lot 9, maintient une table de
placeholders vivante, et, pour tout `statement` qui passe `checkCommandSyntax`
et porte un concept produit, appelle `get_type_sd_prod` pour l'enregistrer.
`reuse=` n'est pas un cas particulier séparé : pour une commande réentrante,
l'objet produit est l'objet réutilisé par construction, donc le même appel
uniforme donne déjà la bonne réponse (vérifié empiriquement sur `CALC_CHAMP`
et `MECA_STATIQUE`/`THER_LINEAIRE`/`THER_NON_LINE`). Un concept référencé
jamais résolu (producteur exclu, en échec, ou pas encore atteint) rend le
`statement` non vérifié avec motif dédié — jamais une supposition.

**B. Adaptation officielle de compatibilité.** Les six traductions
identifiées à la main lors du diagnostic (`ORIE_PEAU_3D`→`ORIE_PEAU` sur
`MODI_MAILLAGE`, l'injection de `RESULTAT` depuis `reuse=` sur
`MECA_STATIQUE`/`THER_LINEAIRE`/`THER_NON_LINE`/`SECH_NON_LINE`, la règle
`LIAISON="ENCASTRE"`→`BLOCAGE` sur `AFFE_CHAR_MECA`) sont, vérifié par lecture
directe du dépôt source, exactement ce que fait `command.get_compat_syntax()`
— une fonction `compat_syntax` attachée au catalogue de la commande
elle-même, rejouée par `ExecuteCommand.compat_syntax_` avant
`checkCommandSyntax` dans le cycle officiel
(`code_aster/Supervis/ExecuteCommand.py`). `scripts/check_command_syntax.py`
appelle désormais `command.get_compat_syntax()(keywords)` avant
`checkCommandSyntax`, pour toute commande, sans exception : aucune table de
correspondance écrite à la main ne subsiste. L'adaptation *après*
vérification (`ExecuteCommand.adapt_syntax`) est un mécanisme distinct,
défini par commande dans les modules exécuteurs (`code_aster.CodeCommands`/
`MacroCommands`, pas le catalogue `Cata`), qui importent `libaster`/
`aster_core` — indisponibles dans ce conteneur (`docs/architecture.md`,
ADR-002). Hors de portée pour la validation de niveau B, documenté comme
limite connue, jamais une omission silencieuse.

**C. Heuristique de nom de commande.** Le parseur du lot 9 reconnaissait
comme commande tout appel `NOM(...)` dont `NOM` correspondait au motif
`^[A-Z][A-Z0-9_]*$`, sans regarder si `NOM` était défini par le fichier
lui-même. `aster_expert.parsing.comm_parser._collect_shadowing_names`
collecte désormais, au niveau module (classes, fonctions, variables
Python ordinaires liées, y compris sous `if`/`for`/`while`/`try`/`with`,
jamais dans le corps d'une fonction ou d'une classe imbriquée — portée
différente), tout nom qui met à l'écart un appel de même nom, quelle que
soit sa casse. Un nom importé n'est jamais mis à l'écart par cette règle :
c'est au contraire la façon normale dont une vraie commande atteint le
fichier (`from code_aster.Commands import ...`).

**D. Commandes hors `Cata.Commands`.** `DEFI_CONT`, `MACR_ROTA_GLOBALE` et
consorts sont des commandes réelles, définies dans `code_aster.MacroCommands`
et non dans `code_aster.Cata.Commands` (constaté par lecture directe :
`DEFI_CONT`, dans `code_aster/MacroCommands/defi_cont.py`, lie ce nom à
`UserMacro("DEFI_CONT", DEFI_CONT_CATA, defi_cont_ops)`, un exécuteur, jamais
l'objet catalogue lui-même). Consigné au lot 4 ci-dessus. Le lot 9 collecte
désormais `imported_names` (tout nom explicitement lié par `import`/`from ...
import ...`, jamais les membres d'un import générique) ; `aster_expert.
validation.validate` route un `UNKNOWN_COMMAND` vers `commands_not_checked`,
motif dédié, quand le nom appartient à `imported_names` — une commande
absente du catalogue et non importée reste une vraie erreur, une faute de
frappe.

**E. Cas particuliers déclarés.**
- `FORMULE` accepte des mots-clés libres (constantes nommées de l'expression)
  au-delà de `VALE`/`VALE_C`/`NOM_PARA`. Le mécanisme officiel qui les retire
  (`FormulaDefinition.change_syntax`, `code_aster/CodeCommands/formule.py`)
  vit dans la couche exécuteur, indisponible ici ; `aster_expert.validation.
  reconstruct` reproduit cette seule substitution, étroite et documentée
  (jamais une grammaire).
- `VARIABLE` (`code_aster.Cata.Commands.variable.VariableSupport`) n'est pas
  une instance de `Command` — vérifié empiriquement (`isinstance` faux) —
  donc jamais soumise à `checkCommandSyntax` : motif dédié
  (`NonStandardCatalogueObject`), aucune autre exception de ce type
  rencontrée sur le catalogue 17.4.0.
- `entier` et `reel` (`code_aster/Cata/Commands/defi_fichier.py`,
  `extr_table.py`) sont les deux seules classes `DataStructure` qu'un
  `sd_prod` peut renvoyer qui représentent une *valeur* extraite (un numéro
  d'unité logique auto-alloué, un scalaire tiré d'une table), pas un objet
  structurel. Un placeholder nu échoue chez `checkCommandSyntax` dès qu'il
  est réinjecté dans un mot-clé de type `ValueCheckMixing` (ex. `UnitType()`
  sur `UNITE=`) — `ValueCheckMixing.checkValue` ne connaît que `None` et
  `PythonVariable`, jamais une instance `DataStructure` nue (vérifié
  empiriquement : `DEFI_FICHIER` puis `IMPR_RESU(UNITE=...)` échoue avec un
  placeholder `entier()`, réussit avec `PythonVariable()`).
  `scripts/check_command_syntax.py` enregistre désormais un
  `PythonVariable()` — l'échappatoire officielle du vérificateur pour « une
  valeur non encore résolue » — pour ces deux noms précisément, jamais une
  règle plus large.

**F. Les 14 erreurs non confirmées.** Vérifié empiriquement, jamais par
analogie : `CREA_CHAMP`/`POST_RELEVE_T` (`RESULTAT` attendant
`resultat_sdaster`) reçoivent, dans les cas rencontrés, un concept produit
par `EXTR_COUPE` — dont le `sd_prod` est statique, `sd_prod=cham_gd_sdaster`,
sans ambiguïté. C'est un désaccord réel entre le type que `EXTR_COUPE`
déclare produire et le type que `CREA_CHAMP`/`POST_RELEVE_T` déclarent
attendre pour ce mot-clé — un fait du catalogue, jamais un artefact de la
reconstruction du projet (confirmé en isolant la chaîne de types, sans
aucun mot-clé littéral ambigu). Traité comme une erreur réelle remontée par
`checkCommandSyntax`, pas comme un faux positif à masquer. Décompte réel sur
le corpus après A à E : 12 occurrences (`CREA_CHAMP` × 8, `POST_RELEVE_T` ×
4, sur `zzzz169a.comm`/`zzzz169b.comm`), et non 14 — l'écart avec
l'estimation initiale du lot 10 vient du décompte de statements différent
après le correctif du point C (certains appels auparavant comptés comme
commandes ne le sont plus) ; chaque occurrence a été vérifiée
individuellement, pas seulement rapprochée du total attendu.

**G. Mesures (corpus officiel, 4183 fichiers `astest/*.comm`, et les trois
fichiers réels de l'utilisateur, lecture seule, jamais copiés).** Détail
complet, motif principal par commande (jamais par occurrence), et analyse
individuelle de chaque erreur résiduelle : voir le compte rendu de ce lot.

## Lot 10c — Règle de placeholder en deux branches et classement des échecs

Relecture externe du lot 10b : le gain de couverture (53,0 % -> 57,25 %) était
en grande partie annulé par une règle trop stricte — un placeholder n'était
enregistré qu'après un `checkCommandSyntax` réussi sur le `statement`
producteur, y compris pour un `result_type` **statique**, où le type produit
est un fait du catalogue indépendant de la résolubilité des mots-clés du
producteur. Quatre points, traités dans l'ordre de gain.

**P1. Règle du placeholder en deux branches (le plus gros levier).** Prouvé par
lecture directe de `Command.get_type_sd_prod`
(`code_aster/Cata/Language/SyntaxObjects.py`) : la branche non-fonction
(`sd_prod` statique) retourne la classe **sans jamais regarder `ctxt`** — les
mots-clés reconstruits ou un dict vide donnent exactement la même réponse.
`scripts/check_command_syntax.py` distingue désormais deux branches, décidées
par le même fait de catalogue que `result_type_dynamic` (lot 4) :
`isinstance(command.definition.get("sd_prod"), type)`.

- Statique -> placeholder **enregistré immédiatement**, avant même de tenter
  `compat_syntax`/`checkCommandSyntax`, y compris pour un `statement`
  **exclu** par la RÈGLE ABSOLUE du lot 10 (mot-clé non résolu,
  `parse_warning`, `control_flow`) : un tel `statement` reste
  `commands_not_checked` (aucun verdict rendu sur lui-même), mais contribue
  désormais un placeholder via une requête `"type_probe"` (nom de commande et
  concept assigné seuls, jamais de mot-clé) envoyée au conteneur dans le même
  ordre de fichier.
- Dynamique -> inchangé du lot 10b, placeholder seulement après
  `checkCommandSyntax` réussi.
- Producteur en **erreur** (et non simplement non vérifié) : un placeholder
  statique reste disponible même si le `statement` producteur échoue son
  propre `checkCommandSyntax` (une vraie entrée `errors`). Le consommateur qui
  le référence directement est donc quand même vérifié, mais son entrée
  `commands_checked` porte désormais un `warnings` nommant le producteur en
  erreur — jamais pour un producteur simplement exclu (`commands_not_checked`),
  qui ne déclenche aucun avertissement. Cette distinction "non vérifié" /
  "en erreur" est reprise partout dans `aster_expert.validation` (code et
  rapports), jamais confondue.

**Deux régressions trouvées et corrigées en cours de route, sur des fichiers
réels, pas des cas construits.**

1. Une auto-référence (réutilisation du même nom de variable Python, ex.
   `line_1 = POST_RELEVE_T(ACTION=_F(..., RESULTAT=line_1, ...))`, cas réel
   `astest/zzzz169c.comm`) résolvait `RESULTAT` vers le placeholder que le
   `statement` était lui-même en train de produire, au lieu de rester
   honnêtement `UnresolvedConcept` (`line_1` n'ayant aucun autre producteur
   suivi). Cause : le placeholder était enregistré dans `concept_objects`
   avant même de résoudre les mots-clés propres du `statement`.
2. Le correctif naïf du point 1 (enregistrer seulement *après* la résolution
   réussie des mots-clés propres du `statement`) a provoqué une régression de
   couverture spectaculaire sur un fichier réel de l'utilisateur (82,8 % ->
   26,3 % sur `calcul_3d_v3.comm`) : dès qu'un `statement` référence, parmi
   ses propres mots-clés, **un autre** concept pas encore résolu (ex.
   `AFFE_CARA_ELEM` dont un `DISCRET[i].VALE` est une valeur Python
   dynamique), l'échec de résolution empêchait aussi l'enregistrement du
   placeholder de CE `statement`, alors que son propre type produit
   (`CARA`) est un fait de catalogue totalement indépendant de cet autre
   mot-clé.

Correctif définitif (`scripts/check_command_syntax.py`,
`_compute_static_placeholder`/`_commit_placeholder`) : le placeholder
statique est **calculé** dès le départ, à partir du seul nom de commande
(donc à l'épreuve de l'auto-référence), mais son **enregistrement** dans
`concept_objects` est différé jusqu'après la résolution des mots-clés propres
du `statement` — puis commis sur **toutes** les branches de sortie
(`UnresolvedConcept`, échec de `compat_syntax`, échec de
`checkCommandSyntax`, succès), jamais seulement en cas de succès. Deux tests
de non-régression dédiés couvrent chacun des deux bugs
(`tests/unit/test_check_command_syntax_script.py`).

**P2. Échecs systémiques du vérificateur -> `commands_not_checked`, jamais
`errors`.** Trois signatures vérifiées individuellement, chacune sur un cas
test officiel dont les mots-clés en cause sont purement littéraux (jamais une
reconstruction du projet) :

- `MACRO_ELAS_MULT` : `KeyError('NOM_CAS')`. Son propre `sd_prod`
  (`code_aster/Cata/Commands/macro_elas_mult.py`) lit
  `CAS_CHARGE[i]['NOM_CAS']` sans condition, alors que `NOM_CAS` est déclaré
  `optional` sans défaut (`addDefaultKeywords` ne l'insère jamais) —
  confirmé sur `astest/hslv304b.comm`, `MACRO_ELAS_MULT` ligne 57, un
  `CAS_CHARGE` entièrement littéral qui omet légitimement `NOM_CAS`.
- `AFFE_CARA_ELEM` : `KeyError('EPAIS')`, même famille. `affe_cara_elem_prod`
  lit `mclf['EPAIS']` sans condition pour une occurrence `COQUE`, sans jamais
  vérifier l'alternative légitime du catalogue, `EPAIS_FO` (une formule) —
  confirmé sur `astest/zzzz331a.comm`, lignes 50/58, `COQUE` fourni
  uniquement via `EPAIS_FO`.
- `DEFI_GROUP` : `CataError('type de concept resultat non prevu')`.
  `defi_group_prod` teste `AsType(MAILLAGE) == maillage_sdaster` — une
  égalité **stricte**, pas un test de sous-classe — donc un `MAILLAGE` de
  type `super_mesh` (sous-classe de `maillage_sdaster`,
  `code_aster/Cata/Language/DataStructure.py`, produit par
  `DEFI_MAILLAGE`/`ASSE_MAILLAGE`) ne correspond jamais et tombe dans le
  `raise` — confirmé sur `astest/sdlx102a.comm`, `DEFI_GROUP` lignes 58/63/66.

Une limite du vérificateur ne se présente jamais comme une erreur dans le
fichier de l'utilisateur : `aster_expert.validation.error_mapping.
match_tool_limitation` route ces trois signatures vers
`commands_not_checked`, motif dédié, avant que `validate.py` n'atteigne
`errors`/`error_indices` — un producteur ainsi routé ne déclenche donc jamais
non plus l'avertissement P1 "producteur en erreur" chez ses consommateurs
(il n'est jamais en erreur, seulement non vérifiable par cet outil).

**Découverte annexe, volontairement non ajoutée à cette table.**
`CALC_MECA_MULT` lève aussi `KeyError('Keyword NOM_CAS is mandatory')`
(`astest/zzzz168a.comm`, ligne 416) — mais NOM_CAS y est déclaré `required`
sous condition `is_type("EVOL_THER") == evol_ther`
(`aster-expert catalogue show CALC_MECA_MULT --keyword CAS_CHARGE.NOM_CAS`),
et le fichier fournit bien un `EVOL_THER` dont le type résolu est
`evol_ther` : la condition est remplie, `NOM_CAS` est réellement obligatoire
et absent. C'est une vraie erreur du fichier, pas une limite de l'outil —
volontairement exclue de la table `_TOOL_LIMITATIONS`.

**R2 (relecture externe du lot 10c lui-même).** Cette découverte a révélé un
bug préexistant, antérieur à ce lot : `error_mapping._MANDATORY_KEYWORD`
(`^Keyword (?P<kw>\S+) is mandatory$`) ne correspondait **jamais** au texte
réellement produit. `Composite.checkMandatory`
(`Cata/Language/SyntaxObjects.py`) lève un `KeyError` **brut**, jamais une
`CheckerError` ; `scripts/check_command_syntax.py` rapporte alors
`str(exc)`, et `KeyError.__str__` renvoie le `repr()` de son argument unique
— le message arrive donc toujours entre guillemets
(`"'Keyword X is mandatory'"`), jamais sous la forme nue que le motif
attendait. Toute occurrence corpus-wide de ce cas tombait donc, en silence,
dans le générique `CHECKER_ERROR` plutôt que `MISSING_MANDATORY_KEYWORD` —
faussant la classification des erreurs que ce lot s'apprêtait justement à
mesurer. Corrigé avant les mesures (`^'?Keyword (?P<kw>\S+) is
mandatory'?$`, les deux formes acceptées, seule la citée étant jamais
observée en pratique) ; test de non-régression sur le texte réel, cité
verbatim, dans `tests/unit/test_error_mapping.py`. `CALC_MECA_MULT`
ci-dessus est désormais correctement classé `MISSING_MANDATORY_KEYWORD`.

**P3. `EXTR_COUPE` tranché par exécution réelle.** `EXTR_COUPE` déclare un
`sd_prod` statique unique (`cham_gd_sdaster`,
`code_aster/Cata/Commands/extr_coupe.py`), mais `CREA_CHAMP`/`POST_RELEVE_T`
attendent `resultat_sdaster` pour le `RESULTAT` produit par un `EXTR_COUPE`
en amont — un désaccord réel de catalogue (lot 10b, point F), jamais un
artefact de reconstruction. Exécution réelle, ponctuelle, de diagnostic
(aucune infrastructure d'exécution développée, hors périmètre du lot 12) :
`run_aster astest/zzzz169a.export`, dans le conteneur (contournement du TTY
que `cave run` impose : `bash -ic` au lieu de `cave run --`, seul le
mécanisme d'invocation change, pas le binaire exécuté). Résultat :
`DIAGNOSTIC JOB : OK`, exécution jusqu'à `FIN`, tous les `TEST_RESU`/
`TEST_TABLE` réussis — y compris les `CREA_CHAMP(OPERATION="EXTR",
RESULTAT=<résultat EXTR_COUPE>)` et `POST_RELEVE_T(ACTION=_F(RESULTAT=
<résultat EXTR_COUPE>, ...))` que le contrôle statique de ce projet rejette.

Cause de l'écart, établie par lecture de l'exécuteur
(`code_aster/MacroCommands/extr_coupe_ops.py`, pas seulement du catalogue) :
le chemin de linéarisation appelle `LIRE_RESU(TYPE_RESU=resu.getType(),
...)`, qui retype le résultat extrait **comme le `RESULTAT` d'origine** (un
sous-type `evol_*` de `resultat_sdaster`) — jamais littéralement
`cham_gd_sdaster` comme le déclare statiquement le catalogue. Le contrôle
statique de ce projet est donc plus strict que le superviseur réel sur ce
motif précis, jamais l'inverse. Routé vers `commands_checked` avec `ok:
true` et un `warnings` documentant la preuve
(`error_mapping.match_execution_confirmed_override`), jamais vers `errors` —
et **uniquement** quand le producteur du concept `RESULTAT`/`ACTION.RESULTAT`
rejeté est vérifié, mot-clé par mot-clé, comme étant bien `EXTR_COUPE`
(`aster_expert.validation.validate._concept_at_path` +
`_most_recent_producer_index`) : jamais deviné du seul texte du message,
jamais une règle plus large que le fait établi.

**R3 (réconciliation du décompte, relecture externe).** Lot 10b : 12
occurrences (`CREA_CHAMP` x 8, `POST_RELEVE_T` x 4). Une première mesure de
ce lot en annonçait 14 — **faux**, un artefact de la régression P1 n°1
ci-dessus : sur `astest/zzzz169c.comm`, l'auto-référence de `line_1`/`line_2`
résolvait à tort vers le placeholder `table_sdaster` que `POST_RELEVE_T`
produit lui-même, provoquant 2 rejets `INVALID_TYPE` supplémentaires sur une
paire de types sans rapport (`table_sdaster`/`resultat_sdaster`, pas
`cham_gd_sdaster`/`resultat_sdaster`) — jamais liés à `EXTR_COUPE`. Corrigé
(régression n°1 ci-dessus), ces deux `statement` deviennent correctement
`UnresolvedConcept` (`commands_not_checked`), et le décompte final,
mesuré sur `astest/zzzz169a.comm` et `astest/zzzz169b.comm` uniquement,
revient exactement à **12** : `CREA_CHAMP` x 4 par fichier, `POST_RELEVE_T`
x 2 par fichier. **Le lot 10b avait raison ; le 14 initial de ce lot était
faux**, corrigé par le même correctif d'auto-référence que la régression n°1.

**P4. `POST_GOUJ` — conclu sur preuve, contredit les deux hypothèses
suggérées.** Ni "hors `Cata.Commands`" (recherche exhaustive,
`git grep -n "POST_GOUJ" -- .` dans `external/codeaster-src` : zéro
occurrence en dehors des deux cas tests eux-mêmes, aucune trace dans
`code_aster.MacroCommands` ni ailleurs), ni une conditionnalité de
compilation propre à cette image (`grep` récursif dans le paquet
`code_aster` réellement installé du conteneur 17.4.0 : zéro occurrence,
aucun code source à conditionner). L'historique Git de
`gitlab.com/codeaster/src` (consulté une seule fois, avant la consigne R1 de
ce lot restreignant cette investigation à `git grep` sur le contenu actuel)
montre la suppression d'un fichier catalogue legacy
(`catapy/commande/post_gouj2e.capy`, un format de catalogue pré-Python) il y
a une dizaine de versions majeures. Conclusion établie par les faits :
`POST_GOUJ` est une commande **disparue du produit**, pas une commande
jamais indexée par le lot 4 et pas une faute de frappe. Les deux seuls cas
tests officiels qui l'appellent encore, `astest/zzzz120a.comm` et
`astest/zzzz120b.comm`, référencent une commande absente du catalogue de la
version cible (17.4.0) : **un vrai défaut de ces deux fichiers du corpus
officiel, détecté correctement par l'outil, pas un faux positif.**

**R4 (message et consigne, relecture externe).** Le message de rapport pour
`POST_GOUJ` ne doit jamais suggérer une faute de frappe : `_suggest`
(distance d'édition) proposait `POST_COQUE` sur ce nom précis — une
suggestion trompeuse, puisque le fait établi ci-dessus est que ce n'en est
pas une. `aster_expert.validation.validate._CONFIRMED_ABSENT_COMMANDS` est
une table étroite, un seul nom vérifié à ce jour, qui remplace le message et
supprime `suggestion` (`null`) pour ce nom précis, jamais une règle
générale — `_suggest` reste actif pour toute autre `UNKNOWN_COMMAND`, où une
suggestion de faute de frappe reste la lecture la plus probable, faute de
preuve du contraire. Message désormais : *"command absent from the target
version's catalogue -- confirmed absent from the entire code_aster 17.4.0
source tree and from the running container's own installed package [...],
so not a typo"* (`docs/metadata.md` §4 amendé).

**Méthode de mesure (R5, changement de méthode, à appliquer à partir de ce
lot).** Une passe complète sur les 4183 fichiers, via un conteneur par
fichier, prend de l'ordre de 8 à 24 heures — un seul appel `docker run`
coûte ~25 s de démarrage d'environnement (recherche de `run_aster`, montage
de la vue Spack, import de `code_aster`), payés une fois par fichier. La
mesure de routine se fait désormais sur un **échantillon aléatoire fixe de
400 cas tests officiels**, tiré une fois pour toutes avec une graine
constante et versionnée
(`data/evaluations/validation_sample_400.json` : `seed: 20260916`,
`random.Random(seed).sample(sorted(glob("astest/*.comm")), 400)`,
déterministe). La liste des 400 fichiers est versionnée dans le dépôt pour
que les mesures restent comparables d'un lot à l'autre. Un seul conteneur,
séquentiel, `--memory=4g` : les 400 fichiers s'exécutent en 30 à 70 s au
total (un seul coût de démarrage d'environnement pour tout l'échantillon,
un script diagnostic hors dépôt boucle sur `check_command_syntax.
run_requests` par fichier, table de placeholders réinitialisée à chaque
fichier). La passe complète sur les 4183 fichiers devient un contrôle
exceptionnel, sur demande explicite — voir la calibration en fin de compte
rendu de ce lot.

**Mesures (échantillon 400, comparaison directe lot 10b vs lot 10c sur le
même échantillon).**

- Lot 10b (mécanisme d'un seul placeholder après succès, code
  `scripts/check_command_syntax.py` au commit `1e535bc`, même
  `reconstruct.py`, mêmes 400 fichiers) : 6716/12149 commandes vérifiées
  (55,28 %), 0 erreur.
- P1 seul (deux branches, sans le reclassement P2/P3) : 8791/12149
  (72,36 %), 1 erreur (`MACRO_ELAS_MULT`/`NOM_CAS`, `astest/sslv139c.comm`).
- **Gain imputable à P1 seul, sur cet échantillon : +17,08 points.**
- P1+P2+P3 : 8790/12149 (72,35 %, différence de coverage négligeable — P2
  déplace des `statement` de `checked`/`errors` vers `not_checked`, P3 ne
  change jamais `checked_total`), 0 erreur.

Détail des erreurs résiduelles et de l'avertissement P3, mesuré sur un lot
ciblé de 29 fichiers connus pour contenir les motifs P2/P3 (les fichiers cités
individuellement ci-dessus), *en complément* de l'échantillon aléatoire — pas
un remplacement, l'échantillon de 400 ne contient par hasard qu'un seul de ces
cas (`sslv139c.comm`) :

- 7 erreurs, toutes analysées individuellement ci-dessus : `UNKNOWN_COMMAND`
  x 4 (`POST_GOUJ`), `MISSING_MANDATORY_KEYWORD` x 1 (`CALC_MECA_MULT`,
  légitime), `INVALID_TYPE` x 2 (`EXTR_CONCEPT`, `astest/zzzz168a.comm`,
  non tranché — hors périmètre P3, voir ci-dessous).
- 12 `commands_checked` avec avertissement P3 (`EXTR_COUPE`), confirmant le
  décompte de R3.

**Limite découverte, non traitée (hors périmètre de ce lot).**
`EXTR_CONCEPT(NOM="CAS_1", DICT=calc_ther_mult)` (`astest/zzzz168a.comm`,
lignes 384/385) attend `ds_dict` mais reçoit `evol_ther` : `calc_ther_mult`
est produit par `CALC_THER_MULT`, dont le `sd_prod` statique déclaré est
`evol_ther` (fait du catalogue, vérifié) — mais ce nom est utilisé ici comme
un conteneur multi-cas (`EXTR_CONCEPT` y extrait un cas nommé). Possible
lien avec le mécanisme de "résultats additionnels" des macro-commandes
(`Command.get_all_types`, `Cata/Language/SyntaxObjects.py`), jamais exploré
par ce projet. Contrairement à `EXTR_COUPE`, aucune exécution réelle n'a
tranché ce cas : reste une vraie erreur non résolue, 2 occurrences,
documentée ici pour un lot futur.

**Trois fichiers réels de l'utilisateur (lecture seule, jamais copiés).**
Chiffre manquant du lot 10b, lot 10 pour référence : 80,8 / 88,9 / 90,4 %.

| Fichier | Lot 10 | Lot 10c |
|---|---|---|
| `calcul_3d_v3.comm` | 80,8 % | 82,8 % (82/99) |
| `calcul_3d_v5.comm` | 88,9 % | 90,0 % (162/180) |
| `calcul_3d_v5_sismique.comm` | 90,4 % | 92,0 % (346/376) |

0 erreur sur les trois fichiers, 0 avertissement P1/P3 (aucun des deux motifs
n'y est présent). Gain plus modeste que sur le corpus officiel : ces fichiers
d'ingénierie répètent surtout un petit nombre de commandes (peu de chaînes de
concepts profondes bloquées par un producteur exclu), à la différence des cas
tests officiels, plus variés et plus enchaînés. Identiques avant/après le
correctif d'auto-référence : aucun des deux ne contient de réutilisation de
nom de variable Python en auto-référence.

**`forma12e.comm` (déposé dans `/media/sf_partage/echanges/`, comparaison
directe avec le rapport du lot 10b déjà présent).** 17/22 commandes vérifiées
(77,3 %), contre 6/22 (27,3 %) au lot 10b — 0 erreur, 0 avertissement,
`valid: true`. Gain concentré sur `DEFI_LIST_INST`, `POST_ELEM`,
`CALC_CHAMP` (reuse), `IMPR_TABLE`, `RECU_FONCTION` x 3, `IMPR_RESU`,
`RECU_TABLE`, `TEST_FONCTION` : tous consomment, directement ou en cascade,
un concept produit par une commande à `result_type` statique
(`DEFI_LIST_REEL`, `AFFE_MATERIAU`, `DYNA_NON_LINE`) dont le `statement`
producteur reste lui-même exclu (valeurs Python scalaires non résolues,
propagation de constantes hors périmètre) — exactement le cas d'usage visé
par P1. Restent non vérifiés : `DEFI_MATERIAU`/`DEFI_LIST_REEL` eux-mêmes
(variables scalaires Python en amont, `tfin`, `pa`, `dse`, `E`, `nu`, `rho`),
`AFFE_MATERIAU` (`MATER=[MAT]`, une liste d'un seul concept que le lot 9 ne
reconnaît pas comme référence directe — limite distincte, non P1),
`FORMULE` (mot-clé libre `om=om`, variable scalaire) et, en cascade,
`DYNA_NON_LINE` (bloqué par `FONC_MULT=sinom`, produit par ce `FORMULE`
non résolu) : cinq `statement`, tous bloqués par des limites hors périmètre
de ce lot (constantes Python, un cas de reconnaissance de référence de
concept non couvert par le lot 9), jamais par le mécanisme de placeholder
lui-même.

**Gain de la propagation de constantes, chiffre actualisé après P1
(échantillon 400).** 2214 `statement` exclus par une valeur non résolue,
dont 949 **uniquement** par une référence à une variable scalaire Python
antérieure (`DynamicValue.reason == "reference_variable"`, aucune autre
raison dynamique concurrente sur le même `statement`) — extrapolé au corpus
complet (x 4183/400) : environ 9 920, contre 10 010 au lot 10b. **P1 ne
change quasiment pas ce chiffre** : la propagation de constantes et la
propagation de type de concept sont deux mécanismes disjoints — P1 résout des
chaînes de *concepts* (un mot-clé qui référence un autre `statement` via son
nom de variable assigné), jamais une expression Python scalaire
(`VALE=dse`, `tfin = 0.1` puis `JUSQU_A=tfin`), qui reste, par construction du
lot 9, une limite assumée et non contournée (`docs/metadata.md` §3, "Limite
de résolution assumée"). L'hypothèse initiale de ce lot ("la cascade que P1
supprime en change probablement beaucoup l'estimation") ne se vérifie pas :
les deux chiffres concordent à ~1 % près, un écart cohérent avec la variance
d'échantillonnage (400/4183 ≈ 9,6 %).

**NE PAS FAIT (hors périmètre, conforme à la consigne) :** aucune
propagation de constantes, aucun évaluateur de conditions de `Bloc`, aucune
règle de grammaire écrite à la main, aucune infrastructure d'exécution
(l'exécution de `astest/zzzz169a.comm` pour P3 est un appel `docker run`
manuel et ponctuel, jamais encapsulé dans `aster_expert`).

**Calibration de l'estimateur (R5, une seule fois, en fin de lot).** Passe
complète sur les 4183 fichiers, un seul conteneur, séquentiel, `--memory=4g`,
aucun autre conteneur ni processus Git en parallèle : 8 min 24 s, aucune
saturation mémoire (`free -h` stable à ~8 Gio disponibles avant/après).

| Mesure | Échantillon (400) | Corpus complet (4183) | Écart |
|---|---|---|---|
| P1 seul, couverture | 72,36 % (8791/12149) | 75,20 % (96856/128797) | +2,84 pt |
| P1+P2+P3, couverture | 72,35 % (8790/12149) | 75,17 % (96823/128797) | +2,82 pt |
| P1+P2+P3, erreurs résiduelles | 0 (aucun des 7 fichiers en cause n'est tiré) | 7 (4 `POST_GOUJ`, 2 `EXTR_CONCEPT`, 1 `CALC_MECA_MULT`) | -- |
| P1+P2+P3, avertissements P3 | 0 | 12 (`EXTR_COUPE`, confirme R3) | -- |
| P1-only, détail erreurs | 1 (`MACRO_ELAS_MULT`, `sslv139c.comm`) | 52 (33 `CHECKER_ERROR` = 22 `MACRO_ELAS_MULT` + 9 `DEFI_GROUP` + 2 `AFFE_CARA_ELEM`, 14 `INVALID_TYPE` = 12 `EXTR_COUPE` + 2 `EXTR_CONCEPT`, 4 `UNKNOWN_COMMAND`, 1 `MISSING_MANDATORY_KEYWORD`) | -- |

**Verdict : l'estimateur est valide pour le suivi de tendance, pas pour une
décision au point de pourcentage près.** L'écart de couverture est faible et
stable (~2,8 points, dans le même sens pour P1 seul et P1+P2+P3 — pas un
artefact du reclassement P2/P3) : un échantillon de 9,6 % du corpus,
regroupé par fichier (variance de grappe, pas un tirage indépendant par
`statement`), sous-estime légèrement mais régulièrement le taux réel.
Les erreurs résiduelles et les avertissements P3, en revanche, sont trop
rares (7 et 12 sur 128 797 `statement`) pour qu'un échantillon de 400
fichiers en capture un nombre représentatif — l'échantillon tiré pour ce lot
n'en contient d'ailleurs aucun sauf un (`sslv139c.comm`, 1 des 33
`CHECKER_ERROR`). Pour tout lot futur : la couverture globale peut se
suivre sur l'échantillon de 400 seul ; le dénombrement précis d'erreurs
résiduelles rares exige soit un fichier ciblé connu (comme la liste de 29
fichiers de ce lot), soit la passe complète.

## Lot 11 — Hook de validation

Hook `PostToolUse` déclenchant `aster-expert validate` après modification d'un
`.comm`, renvoyant les erreurs dans le contexte. Second contrôle refusant une
déclaration de fin de tâche si la version est inconnue, si le fichier contient
`...`, ou si des alarmes n'ont pas été signalées.

Critères de sortie : hook testé sur modification réelle, comportement en échec
vérifié.

## Lot 12 — Exécution encadrée

`aster-expert run`, encapsulation de `run_aster` : répertoire de travail dédié,
limites de temps et de mémoire, refus d'exécuter hors des répertoires
autorisés, collecte des fichiers produits.

Critères de sortie : exécution réussie d'un cas test officiel jusqu'à `FIN`,
comportement correct en dépassement de temps, aucun effet de bord hors du
répertoire de travail.

## Lot 13 — Dépouillement `.mess`

Encapsulation de `run_aster.status` et `run_aster.error_messages`. Complément
propre au projet uniquement pour ce qui n'est pas couvert : relevé structuré
des alarmes, durées, indicateurs de convergence. La lacune est documentée avant
d'être comblée.

Critères de sortie : rapport conforme à `docs/metadata.md` sur au moins trois
exécutions réelles de natures différentes, dont une en non-convergence.

---

## Lots conditionnels

Ces lots ne sont engagés que sur preuve mesurée.

### Lot C1 — Index vectoriel et fusion

Engagé seulement si le lot 7 montre un déficit de rappel que le lexical ne
comble pas, mesuré sur le jeu du lot 5. Le compte rendu du lot 7 doit nommer
les questions en échec.

### Lot C2 — Reranking

Engagé seulement après C1 et sur la même exigence de mesure.

### Lot C3 — Contrôles physiques et comparaison de référence

Niveaux D et E. Hors périmètre v1.

---

## Journal des lots

| Lot | Branche | État | Commit | Date |
|-----|---------|------|--------|------|
| 1 | main | fait | 934aca8 | 2026-09-15 |
| 2 | lot-2-env-detect | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 3 | lot-3-sources | fait | (ce lot, voir `git log`) | 2026-09-16 |
| 4 | lot-4-catalogue | fait | d1041e1 | 2026-09-15 |
| 4b | lot-4b-catalogue-fix | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 5 | | à faire | | |
| 6 | | à faire | | |
| 7 | lot-7-retrieval | fait | (ce lot, voir `git log`) | 2026-09-17 |
| 7b | lot-7b-ranking | fait | (ce lot, voir `git log`) | 2026-09-17 |
| 8 | | fait | (ce lot, voir `git log`) | 2026-09-18 |
| 8b | | fait | (ce lot, voir `git log`) | 2026-09-18 |
| 9 | lot-9-comm-parser | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10 | lot-10-validation-b | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10b | lot-10b-coverage | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10c | lot-10c-placeholders | fait | (ce lot, voir `git log`) | 2026-09-16 |
| 11 | | à faire | | |
| 12 | | à faire | | |
| 13 | | à faire | | |
