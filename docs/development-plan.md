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
| 4 | | à faire | | |
| 5 | | à faire | | |
| 6 | | à faire | | |
| 7 | | à faire | | |
| 8 | | à faire | | |
| 9 | | à faire | | |
| 10 | | à faire | | |
| 11 | | à faire | | |
| 12 | | à faire | | |
| 13 | | à faire | | |
