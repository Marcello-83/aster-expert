# Lot 43 — Second ouvrage : dalle appuyée (mesure d'autonomie)

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français.

**Profil : `vm`** (maillage Salomé). Branche `lot-43`.

## Nature de ce lot

Ce prompt est **volontairement court**. Il ne dit pas comment faire : c'est à
toi de mener la chaîne avec ce que l'outil fournit, c'est-à-dire `CLAUDE.md`, le
skill, les outils MCP, la base `connaissances/` et l'interface projet. Le lot
mesure ce que l'outil permet de faire seul. Chaque fois que tu es bloqué et que
tu dois demander de l'aide, ou qu'une consigne manque, **note-le**. C'est la
donnée la plus importante du lot.

## L'ouvrage, décrit par MM

> Dalle en béton armé C30/37 de 6,00 m × 4,00 m et 0,30 m d'épaisseur,
> simplement appuyée sur ses quatre côtés. Charges : poids propre, et
> exploitation uniforme de 10 kPa. Je veux les déplacements, les moments et le
> ferraillage (ELU, et ELS en XC1 avec un enrobage de 30 mm), avec une
> comparaison à la solution analytique.

## Ce qui est attendu

1. **Projet** `projets/dalle_appuyee_01/`, conforme à l'interface du lot 41.
2. **Fiche d'hypothèses proposée** par toi. Moitié `code_aster` fondée sur la
   documentation, les constats et les cas tests ; moitié `pratique` *proposée*,
   avec des précédents si la base en contient d'applicables. **Arrête-toi**
   quand la fiche est prête à arbitrer, et remets-la à MM. Les décisions
   pratiques sont les siennes. Le lot reprend après son arbitrage, dans la même
   branche.
3. Après arbitrage : maillage Salomé vérifié, `.comm`, exécution, contrôles de
   niveau D.
4. **Niveau E** : comparaison à la solution exacte d'une plaque de Kirchhoff
   rectangulaire simplement appuyée sous charge uniforme (série de Navier),
   calculée par l'outil avec un nombre de termes justifié, pour la flèche au
   centre et les moments au centre. Écris le critère avant l'exécution,
   convergence du maillage comprise.
5. Combinaisons et ferraillage 2D, avec contre-vérification indépendante d'au
   moins un point.
6. `aster-expert rex dalle_appuyee_01` et entrées de connaissances nouvelles. En
   particulier, dis quels patrons, constats ou précédents du quai ont servi, et
   lesquels pourraient être promus grâce à ce second projet.

## Compte rendu attendu — EN FRANÇAIS

1. Ce qui a été produit, et le niveau atteint (E visé).
2. **Journal d'autonomie** : chaque blocage, chaque information manquante,
   chaque consultation de la base qui a évité une erreur, chaque connaissance
   qui manquait.
3. Écarts entre l'outil et ce qu'il faudrait pour traiter seul ce type
   d'ouvrage.
4. Sortie de `rex`, et commandes de contrôle.

## Interdits

- Aucune décision pratique prise à la place de MM.
- Aucun code propre à la dalle dans `src/`.
- Aucun identifiant Code_Aster énoncé de mémoire.
- Aucun critère modifié après exécution.
