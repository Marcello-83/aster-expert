# Enregistrement des décisions E24 à E27 de MM — projet `estacade_pieux_01` (lot 49 ter)

Décisions de MM de la consigne du lot 49 ter, enregistrées par `aster-expert fiche
enregistrer`. Les textes sont ceux de MM, cités tels quels ; la commande vérifie qu'ils
figurent à l'identique dans le fichier source. Ils servent la synthèse ingénieur (section
de calcul du bouchon, section en T des chevêtres, bande d'exclusion, moment de
dimensionnement sur appui) ; le modèle de référence et les décisions E1 à E23 ne changent pas.

Source du texte : donnees/sources/arbitrage_estacade_pieux_01_lot49ter.md
Enregistré le : 2026-10-09T09:08:05-04:00
Domaine de validité par défaut : Synthèse ingénieur du contre-calcul du modèle source d'avant-projet (lot 49 ter), telle que MM l'a décidée ; hors de cette synthèse, la décision n'est pas établie.

### E24 — Section de calcul du bouchon

> **E24, section de calcul du bouchon.**
> Le dimensionnement en béton armé du bouchon se fait au nu inférieur du
> chevêtre, à +0,60 : le chevêtre réel va de +0,60 à +1,50, et +0,60 est
> aussi la cote du recépage (E21).
> La valeur au nœud +1,30, situé à l'intérieur du chevêtre, est conservée
> pour mémoire et pour la comparaison avec la source. La source a
> dimensionné le bouchon avec M = 450 kN·m lu à ce nœud.

- Écartée : Lecture de dimensionnement au nœud de tête +1,30 (lot 49 bis, note d'E23) — conservée pour mémoire et pour la comparaison avec la source (E24)

### E25 — Chevêtres : torseur de la section en T

> **E25, chevêtres.**
> Le torseur de dimensionnement est le total de la section en T (règle
> E17.2 du lot 47 bis : barre plus bande de dalle), pour M comme pour V, à
> tous les états limites.
> La barre seule passe dans les colonnes de traçabilité. Sa part dépend de la
> formulation de plaque (DKT ou DST : C8, CA-058). C'est un artefact numérique,
> pas une grandeur physique.

- Écartée : Barre seule comme torseur de dimensionnement (lots 49, 49 bis) — artefact numérique dépendant de la formulation de plaque, gardé en traçabilité (E25)

### E26 — Bande d'exclusion le long des lignes de nœuds partagés poutre–plaque

> **E26, bande d'exclusion le long des lignes de nœuds partagés poutre–plaque.**
> La bande vaut ±b/2 de part et d'autre de la ligne, b étant la largeur de la
> poutre : ±0,60 m pour les chevêtres.
> Elle est déclarée par famille de poutres dans `engineering_summary` et
> s'applique à toutes les familles de coque, MYY compris. La lecture se fait
> ainsi au nu, conformément à l'EN 1992-1-1 §5.3.2.2(3) pour un appui
> monolithique. La clause est citée d'après MM et le superviseur (voir E27).
> Les valeurs situées dans la bande restent visibles dans une colonne
> « axe (comparaison) », jamais comme valeur de dimensionnement.
> Elle s'ajoute aux disques d'exclusion de PAT-013 autour des têtes ; elle ne
> les remplace pas.

- Écartée : Exclusion des seuls nœuds partagés poutre–plaque (lot 49 bis, CA-058) — remplacée par la bande ±b/2, qui s'ajoute aux disques PAT-013 (E26)

### E27 — Moment de dimensionnement sur appui

> **E27, moment de dimensionnement sur appui (règle de MM, EN 1992-1-1
> §5.3.2.2(3) et sa note).**
> M_dim = max(M_nu ; 0,65 × M_encastrement). La règle s'applique au chapeau de
> la dalle, au chevêtre sur appui et, par extension décidée par MM, au bouchon
> encastré dans le chevêtre.
> La clause est citée d'après MM et le superviseur. Le corpus du dépôt ne
> contient pas l'Eurocode : ne prétends pas l'avoir relue.
> M_encastrement est le vrai moment d'encastrement parfait (décision de
> MM). Ce n'est pas le moment élastique du modèle à l'axe. On l'obtient par
> des modèles auxiliaires, dérivés du modèle de référence. Chacun est
> calculé sous les mêmes cas, les mêmes combinaisons et les mêmes positions
> mobiles que la référence.
> A1, chevêtres. Tablier (dalle et chevêtres) sans les pieux, avec
> les nœuds de tête encastrés : translations et rotations bloquées.
> M_encastrement du chevêtre est le moment de la section en T (E25) à
> l'axe de la file de pieux.
> A2, dalle. Tablier dont les lignes d'axe des chevêtres sont des
> encastrements parfaits : déplacement vertical et rotation autour de
> la ligne bloqués. Chaque travée de 5 m est ainsi bi-encastrée.
> M_encastrement du chapeau est le MXX à l'axe, hors des disques PAT-013,
> au maximum sur la ligne.
> A3, bouchon (extension de la règle décidée par MM). Modèle complet,
> tronçon +0,60 → +1,30 rendu indéformable comme en V1, et rotations des
> têtes bloquées, translations libres. M_encastrement est le moment à
> +0,60.
> Actions des modèles auxiliaires. Charges verticales seulement : G,
> G2, LM1 (TS et UDL), TR, essieu de trottoir, avec les coefficients de la
> combinaison. Le freinage et la température en sont exclus : dans un
> modèle bi-encastré, un gradient thermique produit un moment artificiel
> sans rapport avec l'objet de la règle. Écris ce choix dans la synthèse ;
> MM peut le renverser.
> Formation de M_dim. Pour chaque combinaison et chaque position mobile :
> M_dim = max(M_nu de la référence ; 0,65 × M_encastrement de l'auxiliaire
> correspondant). On prend ensuite l'enveloppe. Le torseur exporté porte
> M_dim, avec N et V lus au nu, dans la référence, au même instant. Écris la
> convention.

- Écartée : Moment au nu seul (M_nu) — complété par 0,65 × M_encastrement (E27)
- Écartée : Moment élastique du modèle à l'axe pris comme M_encastrement — écarté par MM : M_encastrement est le moment d'encastrement parfait des modèles auxiliaires (E27)
- Note : Clause de l'EN 1992-1-1 citée d'après MM et le superviseur ; le corpus du dépôt ne contient pas l'Eurocode, elle n'a pas été relue par la session.
