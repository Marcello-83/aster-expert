# Enregistrement des décisions P1 à P23 de MM — projet `pontons_alu_01` (lot 50)

Décisions de l'annexe « Données » de la consigne du lot 50 (superviseur et MM, 12/10/2026),
enregistrées par `aster-expert fiche enregistrer`. Les textes sont recopiés tels quels de
la source par script (jamais retapés) ; la commande vérifie qu'ils y figurent à l'identique.
Les variantes écartées sont celles que la décision nomme elle-même (S2, note AVP, coupe PRO).

Source du texte : donnees/sources/annexe_donnees_lot50.md
Enregistré le : 2026-10-12T09:00:00-04:00
Domaine de validité par défaut : Calcul PRO d'une travée de la panne PONTONS-ALU-01 (lot 50), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P1 — Travée

> * **P1. Travée.** **L = 6,25 m** (S2 : têtes de poteaux à X = 6,25 ; la note
> arrondit à 6,20). Poteaux de **1,32 m** de haut, du dessus de la semelle au
> dessous du chevêtre (MM).

- Écartée : L = 6,20 m (note AVP, valeur arrondie) — S2 place les têtes de poteaux à X = 6,25 ; MM retient 6,25 m (P1)

### P2 — Géométrie en plan du tablier

> * **P2. Géométrie en plan du tablier : celle de S2** (§D2). L'entraxe des
> poutres principales vaut B = 1,50 m, à l'aplomb des axes des poteaux (2,00 m
> nu à nu). Le modèle reste paramétré.

- Écartée : Géométrie en plan propre au PRO — non fournie ; géométrie de S2 retenue, modèle paramétré (P2)

### P3 — Plate-forme : chevêtre neuf et profilés supports

> * **P3. Plate-forme, telle que dans la coupe PRO.**
> * Deux poteaux surmontés d'un **chevêtre transversal neuf**, et non le cadre
> de couronnement de S2.
> * Le tablier s'appuie sur le chevêtre par **trois profilés supports** (les
> « profilés alu support » de la coupe PRO) :
> * un sous chaque poutre principale ;
> * un au milieu, sous un **montant d'extrémité** ajouté à X = L. Dans S2, les
> poutres principales se raccordaient directement au couronnement.
> * Chevêtre : 0,25 m de large en X sur 0,40 m de haut, de +0,69 à +1,09 NGF,
> de Y = −1,00 à +1,00. Sa largeur est à affiner.

- Écartée : Cadre de couronnement de S2, poutres principales raccordées directement — remplacé par la coupe PRO : chevêtre neuf, trois profilés supports, montant d'extrémité (P3)

### P4 — Section des poutres principales

> * **P4.** Les poutres principales sont en **MP1200** (note de
> dimensionnement, §2.3, et fiche du fabricant). S2 utilise une section
> « I300 - T19 », environ 12 fois plus raide : c'est un écart de l'AVP à
> signaler, qui n'est pas repris.

- Écartée : Section « I300 - T19 » de S2 — environ 12 fois plus raide que le MP1200, écart de l'AVP non repris (P4)

### P5 — Appuis

> * **P5. Appuis.** Rotules fixes côté quai, aux deux extrémités des poutres
> principales : translations bloquées, rotations libres (`FIX PP` dans S2).
> Les profilés supports sont fixes, sans glissement, côté chevêtre.

- Écartée : Profilés supports glissants côté chevêtre — fixes, sans glissement (P5)

### P6 — Assemblages de la travée

> * **P6.** Tous les assemblages de la travée sont **soudés et encastrés**. Les
> assemblages entre travées sont boulonnés, sans objet ici.

- Écartée : Assemblages articulés dans la travée — tous soudés et encastrés (P6)

### P7 — Plans des barres et excentricité des pannes secondaires

> * **P7. Plans.**
> * Les poutres principales, les montants et les diagonales ont le même plan
> moyen.
> * Les pannes secondaires reposent sur les montants et les diagonales, et y
> sont soudées à chaque croisement : S2 coupe toutes les lignes à leurs
> intersections.
> * L'axe des pannes est à **0,10 m** au-dessus du plan moyen, soit
> (150 + 50)/2 mm. S2 prend 0,09 m.

- Écartée : Excentricité des pannes de 0,09 m (S2) — 0,10 m = (150 + 50)/2 mm (P7)

### P8 — Charge permanente G2

> * **P8. G2 = 1,0 kN/m²** sur tout le tablier : platelage bois et équipements,
> valeur du modèle AVP (S2).

- Écartée : G2 réévalué pour le PRO — valeur du modèle AVP (S2) retenue (P8)

### P9 — Houle

> * **P9. Houle.**
> * Jeu PRO : on garde **5 kPa vers le haut et 5 kPa vers le bas**, comme dans
> la note d'hypothèses et selon la décision de MM. Pas de poussée
> d'Archimède ni de cas immergé pour l'instant.
> * Le modèle AVP (S2) appliquait en réalité **20 kPa vers le haut et 10 kPa
> vers le bas**. C'est un écart signalé à MM, et ces valeurs ne sont
> reprises que dans le jeu A.
> * Réserve : le niveau d'eau le plus élevé (+1,61 NGF) dépasse le dessus du
> tablier.

- Écartée : 20 kPa vers le haut et 10 kPa vers le bas dans le jeu PRO (S2) — repris seulement dans le jeu A (P9)

### P10 — Température

> * **P10. Température.** T0 = 10 °C (NF EN 1991-1-5/AN). Tmax = +40 °C,
> Tmin = −15 °C. Tablier de type 1 :
> * Te,max = Tmax + 16 = +56 °C ;
> * Te,min = Tmin − 3 = −18 °C ;
> * **ΔTN,exp = +46 °C** ;
> * **ΔTN,con = 28 °C**, soit une variation de −28 °C ;
> * composante uniforme, appliquée à **tout l'aluminium**.
> S2 appliquait +56 °C et −23 °C (−15 − 8), sans T0, aux poutres
> principales, aux montants et aux diagonales seulement. Ces valeurs ne sont
> reprises que dans le jeu A.

- Écartée : +56 °C et −23 °C sans T0, sur les poutres principales, montants et diagonales seulement (S2) — repris seulement dans le jeu A (P10)

### P11 — Coefficients partiels et de combinaison

> * **P11. Coefficients**, d'après le tableau complet de la note d'hypothèses
> (§D5).
> * Jeu PRO : γ = 1,5 pour la houle (MM) et pour la température (EN 1990,
> annexe A2). L'AVP prenait 1 pour les deux.

- Écartée : γ = 1 pour la houle et la température (AVP) — γ = 1,5 au jeu PRO (P11)

### P12 — Combinaisons

> * **P12. Combinaisons.** Le jeu A reproduit S2 (§D5). Le jeu B est généré
> par les formules de l'EN 1990.

- Écartée : Combinaisons du jeu PRO recopiées de S2 — générées par les formules de l'EN 1990 (P12)

### P13 — Amarrage et accostage

> * **P13. Amarrage et accostage**, comme dans S2.
> * **Amarrage** : 2 × 8,0 kN horizontaux transversaux, à X = 1,60 et
> X = 4,60, sur une poutre principale, tirant vers l'extérieur.
> * **Accostage** caractéristique (16 kN/m) et accidentel (77 kN/m) : de
> X = 1,63 à X = 3,63, sur une poutre principale, poussant vers
> l'intérieur.
> * S2 charge seulement la poutre en Y = −0,75. Le jeu B traite aussi le côté
> Y = +0,75, en symétrique, dans des cas exclusifs.
> * Défaut relevé dans S2 : l'amarrage y est appliqué sur la ligne `SLN 11`,
> qui est le couronnement, avec des abscisses hors de sa longueur. Il est
> remis ici sur la poutre principale.

- Écartée : Amarrage appliqué sur la ligne SLN 11 (couronnement) comme dans S2 — remis sur la poutre principale (P13)

### P14 — Flèches

> * **P14.** Les flèches sont rapportées, sans critère.

- Écartée : Critère de flèche dans ce lot — flèches rapportées sans critère (P14)

### P15 — Étendue du lot

> * **P15.** On en fait le maximum ; l'EC9 viendra après.

- Écartée : Vérifications EC9 dans ce lot — après ce lot (P15)

### P16 — Chevêtre et poteaux

> * **P16.** Le chevêtre est dimensionné. Les poteaux ne sont pas vérifiés.

- Écartée : Vérification des poteaux existants — non vérifiés (P16)

### P17 — Section des profilés supports

> * **P17. Section des profilés supports.** Ils figurent sur la coupe PRO, mais
> leur section n'est donnée nulle part. Hypothèse : tube carré 150 × 150 × 7
> en 6082-T6, comme les montants, de +1,09 à +1,24 NGF.

- Écartée : Section des profilés supports laissée inconnue — hypothèse tube carré 150 × 150 × 7 en 6082-T6 (P17)

### P18 — Liaison des profilés supports

> * **P18. Liaison des profilés supports.** Soudés et encastrés sous le
> tablier. Articulés sur le chevêtre (platine boulonnée), translations
> transmises.

- Écartée : Profilés supports encastrés sur le chevêtre — articulés (platine boulonnée), translations transmises (P18)

### P19 — Semelle et sol

> * **P19. Semelle et sol.**
> * On modélise la demi-semelle sous la file de poteaux : X ∈ \[L − 0,50 ;
> L + 0,76], Y ∈ \[−1,45 ; 1,45]. Le débord de 0,50 et 0,70 m vient de S2.
> * Épaisseur **0,25 m** (note de dimensionnement ; S2 prend 0,17 m). Dessus
> à −0,63 NGF.
> * Raideur normale du sol 5 000 kN/m³, raideur tangentielle 1 000 kN/m³ (S2
> et note).

- Écartée : Semelle de 0,17 m d'épaisseur (S2) — 0,25 m (note de dimensionnement, P19)

### P20 — Béton

> * **P20. Béton.** C35/45, Ecm = 34 GPa, ν = 0,2, pour les poteaux existants
> (Ø 0,50 m), le chevêtre neuf et la semelle.

- Écartée : Propriétés distinctes pour les poteaux existants et le chevêtre neuf — C35/45, Ecm = 34 GPa pour tous (P20)

### P21 — Cotes verticales

> * **P21. Cotes verticales.**
> * Dessous des poutres principales : +1,24 NGF. Plan moyen : +1,3575.
> * Axe des pannes secondaires : +1,4575.
> * Réserve : le dessus du platelage arrive vers +1,51, contre +1,40 sur la
> coupe PRO. L'écart est signalé à MM ; il est sans effet notable sur les
> efforts.

- Écartée : Dessus du platelage à +1,40 NGF (coupe PRO) — cotes de P21, écart signalé à MM (P21)

### P22 — Répartition des actions de surface

> * **P22.** Les actions de surface (G2, Q, houle) sont réparties sur les barres
> longitudinales (poutres principales et pannes secondaires) par largeurs
> d'influence. Le platelage n'a pas de raideur.

- Écartée : Platelage modélisé avec sa raideur — sans raideur, actions réparties par largeurs d'influence (P22)

### P23 — Fissuration du chevêtre

> * **P23.** La fissuration du chevêtre est vérifiée à l'ELS quasi permanent
> (défaut de l'outil), avec ds = di = 0,07 m.

- Écartée : Fissuration vérifiée à l'ELS fréquent — ELS quasi permanent, défaut de l'outil (P23)
