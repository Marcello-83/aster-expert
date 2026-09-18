# Distinguer faits, déductions, recommandations

Toute réponse produite avec ces outils sépare explicitement trois choses
(CLAUDE.md, principe 6) :

- **Fait documenté** : lu tel quel dans une sortie d'outil (un champ de
  `SearchHit`, de `CommandSchema`, de `CommFileAnalysis`, de
  `ValidationReport`) — accompagné de sa citation
  (`references/citation.md`).
- **Déduction** : une conclusion tirée de plusieurs faits mais que
  qu'aucun document ni schéma n'énonce lui-même. À marquer comme telle
  (« ce qui suit est une déduction, pas une lecture directe de… »), jamais
  présentée avec la même autorité qu'un fait.
- **Recommandation** : une suggestion d'action pour l'utilisateur (choix
  de modélisation, prochaine commande à essayer). Toujours distincte des
  deux précédentes, jamais mêlée à l'énoncé d'un fait.

## Annoncer le niveau de validation

La réponse nomme toujours le niveau atteint (A/B/C/D/E, CLAUDE.md) et ne
l'omet jamais dans une phrase de conclusion :

- Résultat de `search_codeaster_docs`, `get_command_schema`,
  `analyze_comm` → niveau **A**, jamais présenté comme une preuve de
  syntaxe correcte ou d'exécution.
- Résultat de `validate_comm` → niveau **B**, jamais présenté comme une
  preuve d'exécution réussie (C), de validité physique (D) ou de
  comparaison à une référence (E) — ces trois niveaux sont hors du
  périmètre des quatre outils de ce serveur ; ne jamais les revendiquer à
  partir de leur seule sortie.
- Les mots « validé », « correct », « sans erreur » sont toujours suivis
  de leur niveau (« syntaxiquement correct, niveau B » — pas « correct »
  seul).

## Quand aucun outil ne tranche

Si `search_codeaster_docs` (sous plusieurs profils si le premier profil
choisi ne suffit pas) ne renvoie rien qui réponde à la question posée, ou
si les résultats sont hors sujet, le dire explicitement : « la
documentation indexée ne tranche pas cette question » (ou équivalent),
plutôt que de meubler avec une déduction non signalée comme telle ou une
information non outillée. C'est une réponse complète, pas un échec à
masquer.
