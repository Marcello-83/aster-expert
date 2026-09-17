# Cas d'usage AsterExpert — questions larges de l'utilisateur

Ces questions sont reprises telles que formulées par Marcello, sans reformulation.
Elles ne sont **pas** des questions d'évaluation : leur réponse n'est pas un
document unique et vérifiable. Elles décrivent ce que l'assistant devra savoir
traiter, et servent de catalogue de couverture fonctionnelle.

Chaque question d'évaluation de `lot5_questions.jsonl` porte, dans son champ
`source_question`, celle de cette liste dont elle est issue.

1. Comment modéliser les pieux dans Code_Aster
2. Comment affecter des ressorts de sol le long des pieux
3. Comment modéliser un autre type d'écran
4. Quelle loi de comportement pour le contact entre un radier et le sol
5. Comment faire une analyse modale spectrale
6. Comment construire un modèle mixte poutre coque
7. Comment construire des objets non « droits » (ex. radier voûte) et appliquer les forces
8. Comment mailler un tel objet
9. Comment imposer un choc unilatéral entre deux nœuds sans élément de contact
10. Quelle relation de comportement pour du béton fissuré en traction
11. Pourquoi STAT_NON_LINE diverge à l'instant du premier chargement hydraulique
12. Comment récupérer les efforts généralisés sur une coque en COQUE_3D
13. Comment déterminer le ferraillage
14. Comment être sûr de l'application des forces selon les normales des éléments sans affichage graphique
15. Comment sortir les résultats pour bien dimensionner les éléments béton ou métal
16. Comment modéliser de manière générale les interactions sol-structure, par exemple pour un ouvrage traversant plusieurs zones géotechniques (radier long reposant sur des sols différents)
17. Comment s'assurer de la cohérence des résultats
18. Comment appliquer des charges avec une répartition spécifique (attinage, valeurs différentes sur différentes zones d'un radier)
19. Comment appliquer les conditions limites
20. Comment affecter les matériaux
21. Comment faire des analyses dynamiques, et quelle utilité

## Note de périmètre

Le point 15 — sortir les résultats pour dimensionner les éléments béton ou métal —
est identifié par l'utilisateur lui-même comme un sujet suffisamment vaste pour
justifier un lot dédié ultérieur. Il n'est décomposé ici que sur ses aspects
directement documentés dans les manuels Code_Aster : extraction de champs,
lignes de coupe, tables, écriture de fichiers de résultats. La partie
dimensionnement normatif proprement dite sort du périmètre de la documentation
Code_Aster et relève d'un développement séparé.
