# Lot 47 ter — Estacade : attribuer chaque écart à sa cause

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-47ter` créée depuis `main` après fusion de `lot-47bis`).

---

**Tout en français. Profil `vm`. Branche `lot-47ter`, depuis `main` après
fusion de `lot-47bis`.** Termes interdits : ceux du lot 47. Consigne copiée dans
`docs/lots/lot47ter_consigne.md`.

## Question posée par MM

Les écarts restants viennent-ils de **notre modélisation**, c'est-à-dire des
choix et des erreurs de l'agent ou du superviseur, de **différences de modèle
connues** avec la source, de **la source elle-même**, ou de grandeurs **locales
non comparables** ?

Le lot ne cherche pas à « recaler » le modèle. Il **attribue** chaque écart à
une cause, chiffres à l'appui.

## Hypothèse du superviseur, à confirmer ou réfuter

Le modèle source est plus proche d'une **plaque déformable à l'effort tranchant
(type DST) avec un chevêtre de 0,80 m** que de notre référence (DKT et chevêtre
de 0,90 m).

- **(b) du lot 47 bis.** La variante DST ramène C8 de la barre seule à +1,2 %.
  Une dalle DKT, rigide au cisaillement, attire l'effort tranchant près des
  pieux. La source publie les efforts de la barre.
- **(c), variante E19.** Avec un chevêtre de 0,80 m, C6 de la barre seule
  rentre dans la tolérance (−1,6 à −4,8 %).
- **Les grandeurs globales concordent** : C2, C4, C7 total, C10, C11 en moyenne
  et C12 « courant ». Les charges, les raideurs, les ressorts et les
  combinaisons ne sont donc pas en cause.

## Étape 0 — Outil

1. `aster-expert env-check`, puis `aster-expert mcp-check`.
2. Au lot 47 bis, `search_connaissances` a renvoyé une erreur pendant toute la
   session, alors qu'un serveur neuf répondait normalement. Reproduis-la si
   possible, par exemple après une modification de la base en cours de session.
   Classe-la (diagnostic nouveau ou existant). Si la cause est un état gardé en
   mémoire par le serveur, propose un correctif, comme un rechargement quand
   les fichiers de la base changent, avec un test.

## Étape 1 — Plan factoriel (critères écrits et commités avant exécution)

Les quatre combinaisons {DKT, DST} × {chevêtre 0,90, chevêtre 0,80}. Trois
existent déjà (référence, variante (a), variante E19). Il en manque **une : DST
avec un chevêtre de 0,80 m**.

Pour les quatre, lis C1 à C13 selon les règles v2 (E17), **en rapportant aussi
la barre seule** pour C6, C7 et C8. La source publie des efforts de barre.

Critère de conclusion, écrit avant l'exécution : l'hypothèse est **confirmée**
si, avec DST et 0,80 m, C2, C3, C4, C5, C6, C7 et C8 (barre seule) sont tous
dans leur tolérance E12. Sinon, elle est réfutée ou partielle, avec la liste
des points qui résistent.

## Étape 2 — Dépendance au maillage des grandeurs locales

C9, C12 « rive » et C13 (Mxx sup., V) sont lus près de singularités (appuis
ponctuels, charges concentrées). Leur valeur dépend du maillage, le nôtre comme
celui de la source, que l'on ne connaît pas.

1. Sur la configuration la plus proche de la source, celle de l'étape 1,
   calcule deux maillages de dalle plus grossiers : **0,25 m et 0,50 m**.
   Les empreintes de roue doivent rester représentées à charge totale exacte :
   contrôle de résultante.
2. Rapporte C9, C12 « rive » et C13 sur les trois maillages (0,05, 0,25 et
   0,50 m), et la taille de maille pour laquelle chaque valeur rejoint la
   source, s'il y en a une.
3. Conclusion attendue : pour chaque point, « comparable » ou « non comparable
   sans le maillage source », avec le motif.

## Étape 3 — Attribution

Tableau final : une ligne par écart de C1 à C13 (v2). Pour chacune, la cause
retenue parmi les catégories suivantes, avec la preuve chiffrée :

| Catégorie | Exemples |
|---|---|
| **A. Erreur de lecture ou de définition** (agent ou superviseur) | lieu de C3/C5 au lot 47, maximum au lieu de la moyenne pour C11 |
| **B. Erreur de données** (superviseur) | essieu de trottoir omis dans B4 |
| **C. Choix de modélisation documenté, différent de la source** | E13 DKT, E2 chevêtre de 0,90 m |
| **D. Incohérence de la source** | I1 à I9, hauteur du chevêtre |
| **E. Grandeur locale dépendant du maillage** | singularités |
| **F. Erreur de modélisation de notre modèle** | aucune identifiée à ce jour ; à démontrer si elle existe |
| **G. Inexpliqué** | pistes examinées listées |

Ajoute **un bilan des erreurs de l'outil** (agent et superviseur) depuis le
lot 47, chacune avec la connaissance ou la règle qui l'empêche désormais.

## Étape 4 — Capitalisation

- **Un précédent proposé**, pas une règle, à arbitrer par MM : DKT ou DST
  pour une dalle couplée à des poutres POU_D_T qui partagent ses nœuds, selon
  le résultat du plan factoriel.
- La mise à jour de CA-058 si le plan factoriel en précise le domaine de
  validité.
- `rex`, paquet de résultats, notes et `docs/etat.yaml`.

## Compte rendu attendu — EN FRANÇAIS

1. `search_connaissances` : cause et correctif.
2. Plan factoriel : tableau 4 × (C1 à C13), et verdict de l'hypothèse.
3. Maillages : valeurs locales sur les trois tailles, et comparabilité.
4. Tableau d'attribution A à G, et bilan des erreurs de l'outil.
5. `rex`, contrôles, interventions.

## Interdits

- Aucun changement de la référence (E1 à E19). Les configurations
  supplémentaires sont des variantes déclarées.
- Aucun critère écrit après exécution sans le déclarer comme tel.
- Aucun terme interdit dans le dépôt.
