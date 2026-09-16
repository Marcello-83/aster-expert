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

## Lot 5 — Jeu d'évaluation

Constitution de 30 à 50 questions réelles avec document attendu. Outil de
mesure du rappel et de la précision, utilisable avant qu'un index n'existe.

Critères de sortie : jeu versionné, chaque réponse attendue vérifiée dans la
documentation, outil de mesure testé sur un index factice.

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

## Lot 7 — Index lexical et recherche

Découpage documentaire selon `docs/corpus.md`, index BM25, filtres de
métadonnées, `aster-expert search`.

Critères de sortie : mesure sur le jeu d'évaluation du lot 5, affichage des
scores et des sources, contrôles de non-perte de contenu.

## Lot 8 — Serveur MCP minimal

Deux outils : `search_codeaster_docs` et `get_command_schema`. Wrapper mince
sur les fonctions existantes, sans logique propre.

Critères de sortie : serveur interrogeable, contrats d'entrée et de sortie
validés par modèle, tests d'intégration sur corpus réduit.

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
| 7 | | à faire | | |
| 8 | | à faire | | |
| 9 | lot-9-comm-parser | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10 | lot-10-validation-b | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10b | lot-10b-coverage | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10c | lot-10c-placeholders | fait | (ce lot, voir `git log`) | 2026-09-16 |
| 11 | | à faire | | |
| 12 | | à faire | | |
| 13 | | à faire | | |
