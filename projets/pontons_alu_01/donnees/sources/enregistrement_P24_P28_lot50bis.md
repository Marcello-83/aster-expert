# Enregistrement des décisions P24 à P28 de MM — projet `pontons_alu_01` (lot 50 bis)

Décisions de la consigne du lot 50 bis (MM, 12/10/2026), enregistrées par la même fonction que
`aster-expert fiche enregistrer`. Les textes sont recopiés tels quels de la source par script
(jamais retapés) ; la vérification exige qu'ils y figurent à l'identique.

Source du texte : donnees/sources/consigne_lot50bis.md
Enregistré le : 2026-10-12T15:00:00-04:00
Domaine de validité par défaut : Calcul PRO d'une travée de la panne PONTONS-ALU-01 (lot 50 bis), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P24 — Géométrie transversale corrigée

> - **P24. Géométrie transversale corrigée par MM** (remplace la largeur de
> P2 ; tout le reste de P2 est conservé).
> - Le tablier fait **2,00 m** de large, poutres principales en rive.
> - Les **0,27 m** restants de la coupe PRO (2,27 m) correspondent aux
> défenses fixes, accrochées le long des poutres principales (environ
> 0,135 m de chaque côté).
> - **Entraxe des poutres principales B = 1,86 m** : axes à Y = ±0,93, soit
> 2,00/2 moins la demi-largeur du MP1200 (0,07 m). Les poteaux restent à
> Y = ±0,75 (entraxe de 1,50 m, Ø 0,50 m).
> - **Pannes secondaires** : Y = +0,56 ; +0,19 ; −0,18 ; −0,55, comme dans
> S2. L'espacement devient régulier, environ 0,37 m, entre les poutres et
> les pannes.
> - **Montants** de Y = −0,93 à +0,93. Diagonales recalculées avec les mêmes
> abscisses et le même sens.
> - **Profilés supports** à Y = −0,93 ; 0 ; +0,93.
> - **Chevêtre allongé** à Y ∈ [−1,05 ; +1,05] (proposition du superviseur,
> à confirmer par MM). Avec ±1,00, le support de rive serait à 7 cm du
> bout, ce qui est trop court pour une platine.
> - **Rotules côté quai** à Y = ±0,93.
> - **Largeur chargée** : 2,00 m (G2, Q, houle), répartie par largeurs
> d'influence sur les poutres et les pannes (P22). Le poids des défenses,
> non communiqué, est négligé et c'est écrit. L'accostage et l'amarrage
> restent appliqués sur la poutre de rive (P13).
> - C'est une modification des paramètres de `maillage_pontons.py`, sans code
> nouveau.

- Écartée : Largeur de P2 (B = 1,50 m entre axes, à l'aplomb des poteaux) — corrigée par MM : tablier de 2,00 m, poutres de rive, B = 1,86 m (P24)
- Écartée : Chevêtre de Y = −1,00 à +1,00 (P3) — support de rive à 7 cm du bout, trop court pour une platine ; ±1,05 proposé par le superviseur (P24)
- Écartée : Largeur chargée limitée aux axes des poutres principales (lot 50, 1,50 m) — remplacée par 2,00 m (P24)
- Note : Remplace la largeur de P2 et, pour la largeur chargée, l'hypothèse « tablier limité aux axes des poutres principales » du lot 50 ; le reste de P2 et P3 (hors étendue du chevêtre) est conservé. Chevêtre à ±1,05 : proposition du superviseur, à confirmer par MM.

### P25 — Appuis côté quai

> - **P25. Appuis côté quai.**
> - Rotule en Y = +0,93 : translations bloquées en X, Y et Z.
> - Rotule en Y = −0,93 : bloquée en X et Z, **libre en Y** (guidée
> transversalement).
> - La solution technologique réelle est à définir par MM.
> - Ce choix supprime le bridage du montant de rive sous la température
> (−301 kN au lot 50).

- Écartée : Rotules fixes aux deux extrémités des poutres principales, translations bloquées (P5) — bride le montant de rive sous la température (−301 kN au lot 50) ; rotule Y = −0,93 guidée, libre en Y (P25)
- Note : Modifie P5 pour les seules rotules côté quai ; les profilés supports restent fixes côté chevêtre (P5). Solution technologique de l'appui guidé à définir par MM.

### P26 — Pannes secondaires soudées aux montants et aux diagonales

> - **P26. Pannes secondaires soudées aux montants et aux diagonales** :
> confirmation de P7, sans changement.

- Écartée : Pannes articulées ou posées sur les montants et diagonales — P7 confirmé : soudées à chaque croisement (P26)

### P27 — Variante de combinaison B′

> - **P27. Variante de combinaison B′.** C'est le jeu B, avec **Q et la houle
> rendus non concomitants**. On ne compte pas une foule de 5 kPa pendant une
> houle qui submerge le tablier. Elle s'obtient en post-traitement seulement,
> et c'est une décision à proposer à MM, qui tranchera.

- Écartée : Jeu B seul (Q et houle concomitants) — B′ calculé en plus, en post-traitement ; le choix entre B et B′ reste à MM (P27)
- Note : Le choix du jeu de dimensionnement (B ou B′) est proposé à MM, qui tranchera ; les deux sont rapportés.

### P28 — Taux élastique simplifié

> - **P28. Taux élastique simplifié** (§3). C'est un indicateur de
> dimensionnement, pas une vérification EC9.

- Écartée : Vérification EC9 complète (classe de section, flambement, déversement, assemblages) — hors lot ; le taux simplifié est un indicateur de dimensionnement (P28)
- Note : Valeurs f0, f0,haz et γM1 = 1,10 du § 3 de la consigne du lot 50 bis, reportées dans le fichier de données (groupe resistances_aluminium, source P28).
