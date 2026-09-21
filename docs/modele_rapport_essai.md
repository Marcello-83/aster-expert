# Modèle de rapport d'essai

Règle applicable à partir du lot 25. Un rapport d'essai reprend ce plan ; la
section « Critère de réussite » est **écrite avant l'exécution** et n'est pas
modifiée après elle (une erreur du critère se corrige dans une section datée
« Correction du critère », jamais en réécrivant l'original).

## Objet

Ce que l'essai établit, la version de Code_Aster, le niveau de validation visé
(C ou D, jamais plus).

## Critère de réussite (écrit avant l'exécution)

Pour chaque grandeur contrôlée, une ligne : grandeur, valeur attendue et son
origine (formule, théorie de l'élément), nature, seuil.

| Grandeur | Attendu | Nature | Seuil de réussite |
| --- | --- | --- | --- |
| … | … | exacte / sensible à la discrétisation | … |

Règle :

- une grandeur que la théorie de l'élément reproduit **exactement** doit l'être
  à 10⁻⁶ près en relatif ;
- une grandeur **sensible à la discrétisation** doit présenter une erreur qui
  décroît quand le maillage est raffiné d'un facteur 2 (au moins deux maillages) ;
- toute autre issue est un **échec**, rapporté tel quel : pas de seuil relâché
  après coup, pas d'exception invoquée après lecture des résultats.

## Modèle et exécution

Fichiers versionnés, version, digest d'image, commit, commande lancée.

## Résultats

Valeurs obtenues, écart relatif à l'attendu, décroissance de l'erreur par
raffinement. Chaque valeur est imprimée dans un listing versionné.

## Verdict

Une ligne par grandeur : réussite ou échec au regard du seul critère ci-dessus.

## Lecture

Faits (grandeurs mesurées), déductions (marquées comme telles),
recommandations.

## Limites

Ce que l'essai ne couvre pas.
