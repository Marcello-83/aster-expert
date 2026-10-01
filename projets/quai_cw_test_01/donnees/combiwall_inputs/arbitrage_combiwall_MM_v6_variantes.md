# Variantes écartées de D17 et D18 — arbitrage v6

Dictées par MM en séance le jour de l'enregistrement (25 septembre 2026), à la
demande de la session du lot 38 : le fichier `arbitrage_combiwall_MM_v6.md` ne
porte pas de `discarded_variants` pour D17 et D18, que la règle P1 de la fiche
exige. Recopiées à l'identique ; seule la mise en forme (`*description*` /
`*reason*`) est de la session. Source : `decision_ingenieur`, MM.

## D17

1. *description* : Amarrage (Q3) et accostage (A) simultanés.
   *reason* : Un navire n'est pas amarré au poste qu'il est en train d'accoster ; les deux actions ne sont pas concomitantes.
2. *description* : Pression d'eau permanente (EAU_P) traitée comme action variable.
   *reason* : Elle résulte du niveau de nappe permanent et suit les actions permanentes ; elle est affectée du même coefficient que G.
3. *description* : Accostage traité comme action variable en combinaison fondamentale (γQ = 1,5).
   *reason* : L'effort de 800 kN est défini par le cas de test comme une situation accidentelle, associée à la nappe haute (§7, cas A).
4. *description* : Coefficients γG distincts pour G et pour EAU_P.
   *reason* : Les deux actions varient ensemble ; les traiter comme un seul bloc limite le nombre de combinaisons sans perte de pertinence pour un cas de test.

## D18

1. *description* : Ouverture de fissure limite de 0,3 mm sous combinaison quasi permanente.
   *reason* : Valeur recommandée de l'EN 1992-1-1 (tableau 7.1N) pour la classe XS3 ; MM retient 0,2 mm, plus sévère, pour un ouvrage maritime de durée d'utilisation de 100 ans.
2. *description* : Enrobage déterminé par le calcul détaillé de cmin,dur selon l'EN 1992-1-1 (§4.4.1).
   *reason* : MM retient directement sa valeur usuelle de 65 mm pour ce type d'ouvrage ; le calcul détaillé n'apporte rien à un cas de test.
3. *description* : Maîtrise de la fissuration sous combinaison fréquente.
   *reason* : MM retient la combinaison quasi permanente, usuelle pour la maîtrise de l'ouverture des fissures en béton armé.
