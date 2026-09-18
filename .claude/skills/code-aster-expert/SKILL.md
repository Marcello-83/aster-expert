---
name: code-aster-expert
description: >-
  Use when answering a question about Code_Aster syntax, keywords,
  modelisations, comportements, or command usage, or when checking a
  `.comm` file — whenever the answer would rely on the `aster-expert` MCP
  server (search_codeaster_docs, get_document_section, get_command_schema,
  analyze_comm, validate_comm). Not a source of Code_Aster knowledge
  itself: describes the procedure for using those five tools correctly.
---

# Expert Code_Aster — procédure d'usage des outils

Ce skill ne contient aucune connaissance Code_Aster de première main. Il
décrit comment utiliser les cinq outils du serveur MCP `aster-expert` —
`search_codeaster_docs`, `get_document_section`, `get_command_schema`,
`analyze_comm`, `validate_comm` — de façon à ne jamais confondre pertinence
documentaire, validité syntaxique et exécution (CLAUDE.md). Toute
connaissance Code_Aster affirmée dans une réponse doit venir de la sortie
d'un de ces outils, jamais de la mémoire du modèle.

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

## 5. Un extrait de tête ne fonde jamais une affirmation sur le corps d'une section

`search_codeaster_docs` renvoie un `excerpt` coupé à 280 caractères — utile
pour repérer *quel* document et *quelle* section sont pertinents, jamais
suffisant pour affirmer ce qu'une section dit réellement. Dès qu'une
réponse s'appuie sur le contenu d'une section — un tableau comparatif
(ex. domaines d'application de plusieurs modélisations), un domaine de
validité, une liste de conditions ou de modèles disponibles — lire cette
section en entier avec `get_document_section` avant de conclure.
`search_codeaster_docs` a identifié la bonne section trois fois de suite
sur ce projet (tableau DKT/DST/Q4G de U2.02.01, panorama des modèles de
sol de U2.03.09, méthodes de U2.04.06) sans jamais pouvoir en citer le
contenu, faute d'un outil de lecture intégrale — c'est précisément ce que
`get_document_section` corrige, pas une amélioration du classement.

Chaque résultat de `search_codeaster_docs` porte déjà tout ce qu'il faut
pour l'appel suivant, sans rien reconstruire à la main : passer soit son
`fragment_id` seul, soit `document_id` + `section_path` + `granularity`
ensemble. Voir `references/citation.md`.

**Vérifier `content` avant de lire, lire par plages au-delà du seuil (lot
14, L1).** `get_document_section` ne tronque jamais en silence : au-delà
d'un seuil de taille, `content` revient à `null` plutôt que coupé --
`content_length` (toujours renseigné) dit la taille totale de la section,
`outline` liste les sous-titres détectés avec leurs bornes de lignes
absolues, et `guidance` explique quelle plage plus étroite demander.
Vérifier systématiquement `content is None` avant d'exploiter une réponse :
si c'est le cas, ne jamais conclure sur l'absence de contenu, mais
enchaîner un ou plusieurs appels avec `line_start`/`line_end` (une entrée
de `outline` si elle existe, sinon une plage de lignes choisie dans les
bornes indiquées) jusqu'à couvrir ce qui fonde la réponse. Une lecture par
plages successives reste une lecture intégrale de ce qui est cité, jamais
une lecture partielle passée sous silence.

## 6. Fichier `.comm` : `analyze_comm` puis `validate_comm`, jamais l'œil seul

Un `.comm` fourni par l'utilisateur passe par `analyze_comm` (structure)
puis, si une confrontation au catalogue est utile, `validate_comm` (niveau
B) — jamais une simple lecture visuelle du fichier tenant lieu de l'un ou
l'autre. Voir `references/comm-workflow.md`.

## 7. Annoncer le niveau de validation atteint, jamais un niveau supérieur

`search_codeaster_docs`, `get_document_section`, `get_command_schema`,
`analyze_comm` sont niveau A (documentaire, non exécuté, non confronté à
un fichier réel — y compris `get_command_schema`, qui lit le catalogue
mais ne confronte rien, et `get_document_section`, qui renvoie un texte
intégral mais toujours non exécuté). `validate_comm` est niveau B (syntaxe
confrontée au catalogue). Les niveaux C/D/E (exécution, validité physique,
comparaison à une référence) sont hors du périmètre de ce serveur : ne
jamais les annoncer à partir de ces cinq outils. Les mots « validé »,
« correct », « sans erreur » sont toujours qualifiés par leur niveau.

## 8. Distinguer faits, déductions, recommandations

Toute réponse sépare explicitement ce qui est lu dans une sortie d'outil
(fait documenté), ce qui en est inféré (déduction, à marquer comme telle),
et ce qui est suggéré à l'utilisateur (recommandation). Voir
`references/answer-format.md`.

## Quand la documentation ne tranche pas

Si `search_codeaster_docs` (sous plusieurs profils si le premier ne suffit
pas) ne renvoie rien qui réponde à la question, le dire explicitement.
Ne jamais forcer une réponse à partir d'un résultat hors sujet, ni
compléter par déduction ce qu'aucun document ne dit.
