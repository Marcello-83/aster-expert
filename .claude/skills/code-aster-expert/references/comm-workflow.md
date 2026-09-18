# Vérifier un fichier `.comm`

Jamais de lecture à l'œil tenant lieu d'analyse ou de validation : un
`.comm` fourni par l'utilisateur passe toujours par les outils, dans cet
ordre.

## 1. `analyze_comm(comm_path)` — toujours en premier

Analyse structurelle statique (module `ast`, le fichier n'est jamais
exécuté). Donne, par instruction : commande, concepts produits/consommés,
mots-clés, groupes littéraux, modélisations/comportements repérés. Lire
`analysis.statements` avant toute chose :

- Un statement `dynamic=true` ou avec des `unresolved` non vides est
  déclaré comme tel dans la réponse — jamais reformulé comme si sa
  structure était connue.
- C'est le seul moyen légitime de décrire la structure d'un `.comm` sans
  l'exécuter (docs/architecture.md §5).

## 2. `validate_comm(comm_path, version=...)` — seulement si une confrontation au catalogue est utile

Confronte la syntaxe reconstruite au catalogue de la version cible via
`checkCommandSyntax`, dans le conteneur Code_Aster. Nécessite
`ASTER_CONTAINER_WORKROOT`/`ASTER_DOCKER_BIN` déjà configurés (sinon
`McpToolError` explicite — le rapporter à l'utilisateur tel quel, ne
jamais improviser un contournement). Peut prendre plusieurs dizaines de
secondes (exécution réelle dans un conteneur) : normal, ne pas le
présenter comme une anomalie.

En lisant `ValidationReport` :

- `valid=true` signifie seulement que les commandes *effectivement
  confrontées* (`commands_checked`) sont syntaxiquement correctes — jamais
  que le fichier s'exécute, ni qu'il est physiquement correct.
- Toujours rapporter `commands_not_checked` et ses `reasons` : un taux de
  couverture partiel n'est jamais dissimulé derrière un `valid=true`
  global.
- Une entrée d'`errors` porte son `code`, sa `command`, sa `line`, son
  `message` réel : le rapporter tel quel, jamais résumé en "il y a une
  erreur de syntaxe".

## Ce que ce flux ne couvre pas

Ni `analyze_comm` ni `validate_comm` n'exécutent le fichier (niveau C), ne
contrôlent un résultat physique (niveau D), ni ne le comparent à une
référence (niveau E). Un fichier `valid=true` en niveau B n'est jamais
annoncé comme « correct » sans cette qualification.
