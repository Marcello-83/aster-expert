---
name: code-aster-expert
description: >-
  Use when answering a question about Code_Aster syntax, keywords,
  modelisations, comportements, or command usage, or when checking a
  `.comm` file — whenever the answer would rely on the `aster-expert` MCP
  server (search_codeaster_docs, get_command_schema, analyze_comm,
  validate_comm). Not a source of Code_Aster knowledge itself: describes
  the procedure for using those four tools correctly.
---

# Expert Code_Aster — procédure d'usage des outils

Ce skill ne contient aucune connaissance Code_Aster de première main. Il
décrit comment utiliser les quatre outils du serveur MCP `aster-expert` —
`search_codeaster_docs`, `get_command_schema`, `analyze_comm`,
`validate_comm` — de façon à ne jamais confondre pertinence documentaire,
validité syntaxique et exécution (CLAUDE.md). Toute connaissance
Code_Aster affirmée dans une réponse doit venir de la sortie d'un de ces
outils, jamais de la mémoire du modèle.

## 1. Identifier la version cible avant toute affirmation de syntaxe

Chaque sortie d'outil porte sa propre version (`aster_version` sur un
`SearchHit` ou un `CommandSchema`, `aster_version`/`image_digest` sur un
`ValidationReport`). Lire ce champ et l'annoncer plutôt que de supposer
une version. Si l'utilisateur n'en a demandé aucune en particulier,
dire explicitement que c'est la dernière installation détectée qui a
répondu (comportement par défaut de `get_command_schema`/`validate_comm`
sans `version`). Un désaccord entre deux outils sur la version en jeu est
signalé, jamais lissé.

## 2. Choisir le profil de recherche, et le dire

Avant tout appel de `search_codeaster_docs`, choisir `profile` parmi
`syntaxe` (nom exact d'une commande/d'un mot-clé), `theorie` (fondement
physique ou mathématique) ou `methode` (choix de modélisation, comparaison
d'éléments) — jamais deviné à l'aveugle, jamais laissé au défaut sans
y avoir pensé. La description de l'outil donne le critère de choix. La
réponse à l'utilisateur nomme le profil retenu et pourquoi.

## 3. Aucune affirmation de syntaxe sans outil

Un nom de commande, de mot-clé, de modélisation ou de loi de comportement
n'est jamais énoncé sans provenir soit de `get_command_schema` (schéma
exact du catalogue), soit d'un extrait renvoyé par `search_codeaster_docs`.
Si l'outil ne le confirme pas, le dire plutôt que de compléter depuis la
mémoire du modèle.

## 4. Citer systématiquement la source

Toute affirmation documentaire porte : identifiant de document, section,
version, chemin source. Voir `references/citation.md` pour le mapping
exact champ de sortie → outil.

## 5. Fichier `.comm` : `analyze_comm` puis `validate_comm`, jamais l'œil seul

Un `.comm` fourni par l'utilisateur passe par `analyze_comm` (structure)
puis, si une confrontation au catalogue est utile, `validate_comm` (niveau
B) — jamais une simple lecture visuelle du fichier tenant lieu de l'un ou
l'autre. Voir `references/comm-workflow.md`.

## 6. Annoncer le niveau de validation atteint, jamais un niveau supérieur

`search_codeaster_docs`, `get_command_schema`, `analyze_comm` sont niveau
A (documentaire, non exécuté, non confronté à un fichier réel — y compris
`get_command_schema`, qui lit le catalogue mais ne confronte rien).
`validate_comm` est niveau B (syntaxe confrontée au catalogue). Les
niveaux C/D/E (exécution, validité physique, comparaison à une référence)
sont hors du périmètre de ce serveur : ne jamais les annoncer à partir de
ces quatre outils. Les mots « validé », « correct », « sans erreur » sont
toujours qualifiés par leur niveau.

## 7. Distinguer faits, déductions, recommandations

Toute réponse sépare explicitement ce qui est lu dans une sortie d'outil
(fait documenté), ce qui en est inféré (déduction, à marquer comme telle),
et ce qui est suggéré à l'utilisateur (recommandation). Voir
`references/answer-format.md`.

## Quand la documentation ne tranche pas

Si `search_codeaster_docs` (sous plusieurs profils si le premier ne suffit
pas) ne renvoie rien qui réponde à la question, le dire explicitement.
Ne jamais forcer une réponse à partir d'un résultat hors sujet, ni
compléter par déduction ce qu'aucun document ne dit.
