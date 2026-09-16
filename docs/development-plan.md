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
| 3 | | à faire | | |
| 4 | lot-4-catalogue | fait | d1041e1 | 2026-09-15 |
| 4b | lot-4b-catalogue-fix | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 5 | | à faire | | |
| 6 | | à faire | | |
| 7 | | à faire | | |
| 8 | | à faire | | |
| 9 | lot-9-comm-parser | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10 | lot-10-validation-b | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 10b | lot-10b-coverage | fait | (ce lot, voir `git log`) | 2026-09-15 |
| 11 | | à faire | | |
| 12 | | à faire | | |
| 13 | | à faire | | |
