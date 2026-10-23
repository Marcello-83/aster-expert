# Enregistrement des décisions P67 à P76 de MM — projet `pontons_alu_01` (lot 54)

Décisions de la consigne du lot 54 (MM, 20 au 22/10/2026), enregistrées par `aster-expert fiche
enregistrer`. P67 révise P64 (point 3), P68 révise P43 et P48, P69 révise P56, P60 et P62 et annule
P61 : ces entrées sont ré-arbitrées (l'ancienne décision va dans l'historique). Les textes sont
extraits de la source par script (jamais retapés) ; la vérification exige qu'ils y figurent à
l'identique.

Source du texte : donnees/sources/consigne_lot54.md
Enregistré le : 2026-10-23T03:50:00-04:00
Domaine de validité par défaut : Calcul linéaire du ponton intégral de PONTONS-ALU-01, géométrie PRO définitive (lot 54), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P43 — Section des poutres BA de l'anneau

> **P68 — Chevêtres 0,60 × 0,40 prolongés, P43 et P48 révisées.**
>
> - Section des chevêtres : **b = 0,60 m** (selon X) **× h = 0,40 m**.
>   - Coulés en place, à section constante sur toute leur longueur.
>   - La largeur de 0,60 m couvre la tête des piles Ø 0,50 sans surlargeur locale
>     de coffrage.
> - Longrines inchangées : 0,40 × 0,40.
> - Chevêtres prolongés de **Y = ±1,05 à Y = ±1,20**, pour placer la fixation de
>   l'appui à 0,15 m de l'about.
> - Axes inchangés :
>   - chevêtres en X = 6,25 + 7,77 k et en X + 1,52 ;
>   - arase +0,69, dessus +1,09.
> - Liaisons longrine–chevêtre, pieu–anneau et appuis : inchangées en principe.
>   Les longueurs des liaisons rigides suivent la nouvelle géométrie.
> - Écartées :
>   - anneau 0,40 × 0,40 de P43 et chevêtres de Y = −1,05 à +1,05 de P48 ;
>   - anneau 0,50 × 0,50 (proposition du superviseur), refusé par MM ;
>   - nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur),
>     abandonnés pour la constructibilité.

- Écartée : Anneau 0,40 × 0,40 pour les chevêtres (P43) — chevêtres 0,60 × 0,40 coulés en place, longrines 0,40 × 0,40 inchangées (P68)
- Écartée : Anneau 0,50 × 0,50 (proposition du superviseur) — refusé par MM (P68)
- Écartée : Nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur) — abandonnés pour la constructibilité (P68)
- Note : Ré-arbitrage : la section des longrines reste 0,40 × 0,40 ; seuls les chevêtres passent à 0,60 (selon X) × 0,40 (P68). L'ancienne décision reste dans l'historique de la fiche.

### P48 — Géométrie des palées

> **P68 — Chevêtres 0,60 × 0,40 prolongés, P43 et P48 révisées.**
>
> - Section des chevêtres : **b = 0,60 m** (selon X) **× h = 0,40 m**.
>   - Coulés en place, à section constante sur toute leur longueur.
>   - La largeur de 0,60 m couvre la tête des piles Ø 0,50 sans surlargeur locale
>     de coffrage.
> - Longrines inchangées : 0,40 × 0,40.
> - Chevêtres prolongés de **Y = ±1,05 à Y = ±1,20**, pour placer la fixation de
>   l'appui à 0,15 m de l'about.
> - Axes inchangés :
>   - chevêtres en X = 6,25 + 7,77 k et en X + 1,52 ;
>   - arase +0,69, dessus +1,09.
> - Liaisons longrine–chevêtre, pieu–anneau et appuis : inchangées en principe.
>   Les longueurs des liaisons rigides suivent la nouvelle géométrie.
> - Écartées :
>   - anneau 0,40 × 0,40 de P43 et chevêtres de Y = −1,05 à +1,05 de P48 ;
>   - anneau 0,50 × 0,50 (proposition du superviseur), refusé par MM ;
>   - nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur),
>     abandonnés pour la constructibilité.

- Écartée : Chevêtres de Y = −1,05 à +1,05 (P48) — chevêtres prolongés à Y = ±1,20, fixation de l'appui à 0,15 m de l'about (P68)
- Note : Ré-arbitrage : piles, entraxes, semelles, raideurs de sol et absence d'ancrage de P48 inchangés (confirmés par P71 et P72) ; seuls la largeur et l'emprise en Y des chevêtres changent (P68). Paramètres B_CHEVETRE et Y_CHEVETRE du script de maillage (variantes_lot54.yaml).

### P56 — Houle par surfaces et par état limite

> **P69 — Houle de projet : forfait de 5 kPa, justifié par les études GEOMER, P56 et P60 révisées, P61 annulée.**
>
> - Les cas unitaires de 1 kPa par surface et par module de P56 sont conservés.
>   Seuls les événements changent :
>   - HU = 5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) ;
>   - HD = 5,0 × HD_TABLIER ;
>   - HU_F = 2,728 × HU_TUBES + 2,516 × HU_PANNES + 2,425 × HU_PLATELAGE, à
>     l'ELS fréquent. Valeurs majorantes : la houle fréquente n'atteint pas le
>     tablier.
> - **Aucun impact** : P61 est annulée. Les événements HU_IMP_Mk et leurs options
>   sont retirés des combinaisons.
> - **P62 révisée** : la houle reste dans le critère de flèche. HU et HD entrent
>   dans l'ELS caractéristique ; HU_IMP n'existe plus.
> - Justification :
>   - donnée d'entrée principale : houle mesurée à Cap Couronne (GEOMER, 1996),
>     transmise en zone 2 avec Kt = 0,10. Kt est commun au modèle physique GEOMER
>     de 1995 et à l'étude MS414803 ;
>   - les pannes A et B sont en **zone 2** GEOMER ;
>   - le calcul McConnell sur cette houle donne 4,0 à 5,0 kPa en sous-pression et
>     au plus 2,9 kPa en surpression.
> - Écartées :
>   - coefficients « tablier noyé » de P60 ;
>   - estimation à 11 kPa (houle au large ANEMOC + McConnell), qui n'apparaît que
>     pour mémoire dans la note d'hypothèses ;
>   - impacts de P61.
> - Toutes les autres règles de combinaison sont inchangées : P49, P57 et P59.
> - Nouveau groupe `houle_lot54` dans le fichier de données, avec les valeurs
>   ci-dessus.

- Écartée : Coefficients « tablier noyé » de P60 — forfait de 5 kPa sur les trois cas de sous-face et sur HD_TABLIER, HU_F majorant (P69)
- Note : Ré-arbitrage : les cas unitaires de 1 kPa par surface et par module de P56 sont conservés ; seuls les événements changent (groupe houle_lot54 du fichier de données). Règles P49, P57 et P59 inchangées.

### P60 — Houle « tablier noyé »

> **P69 — Houle de projet : forfait de 5 kPa, justifié par les études GEOMER, P56 et P60 révisées, P61 annulée.**
>
> - Les cas unitaires de 1 kPa par surface et par module de P56 sont conservés.
>   Seuls les événements changent :
>   - HU = 5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) ;
>   - HD = 5,0 × HD_TABLIER ;
>   - HU_F = 2,728 × HU_TUBES + 2,516 × HU_PANNES + 2,425 × HU_PLATELAGE, à
>     l'ELS fréquent. Valeurs majorantes : la houle fréquente n'atteint pas le
>     tablier.
> - **Aucun impact** : P61 est annulée. Les événements HU_IMP_Mk et leurs options
>   sont retirés des combinaisons.
> - **P62 révisée** : la houle reste dans le critère de flèche. HU et HD entrent
>   dans l'ELS caractéristique ; HU_IMP n'existe plus.
> - Justification :
>   - donnée d'entrée principale : houle mesurée à Cap Couronne (GEOMER, 1996),
>     transmise en zone 2 avec Kt = 0,10. Kt est commun au modèle physique GEOMER
>     de 1995 et à l'étude MS414803 ;
>   - les pannes A et B sont en **zone 2** GEOMER ;
>   - le calcul McConnell sur cette houle donne 4,0 à 5,0 kPa en sous-pression et
>     au plus 2,9 kPa en surpression.
> - Écartées :
>   - coefficients « tablier noyé » de P60 ;
>   - estimation à 11 kPa (houle au large ANEMOC + McConnell), qui n'apparaît que
>     pour mémoire dans la note d'hypothèses ;
>   - impacts de P61.
> - Toutes les autres règles de combinaison sont inchangées : P49, P57 et P59.
> - Nouveau groupe `houle_lot54` dans le fichier de données, avec les valeurs
>   ci-dessus.

- Écartée : Coefficients « tablier noyé » (P60) — forfait de 5 kPa justifié par les études GEOMER (P69)
- Écartée : Estimation à 11 kPa (houle au large ANEMOC + McConnell) — pour mémoire seulement dans la note d'hypothèses (P69)
- Note : Ré-arbitrage : P60 remplacée par P69 ; l'ancienne décision reste dans l'historique de la fiche.

### P61 — Impact quasi statique

> - **Aucun impact** : P61 est annulée. Les événements HU_IMP_Mk et leurs options
>   sont retirés des combinaisons.

- Écartée : Impacts quasi statiques HU_IMP_Mk (P61) — aucun impact, P61 annulée (P69)
- Note : Annulation : les six événements HU_IMP_Mk et leurs options sont retirés des combinaisons (P69). L'ancienne décision reste dans l'historique de la fiche.

### P62 — Houle dans le critère de flèche

> - **P62 révisée** : la houle reste dans le critère de flèche. HU et HD entrent
>   dans l'ELS caractéristique ; HU_IMP n'existe plus.

- Écartée : HU_IMP dans l'ELS caractéristique du critère de flèche (P62, lot 52) — HU_IMP n'existe plus (P69)
- Note : Ré-arbitrage : HU et HD restent dans l'enveloppe de flèche de l'ELS caractéristique ; critères P37 et P51 inchangés.

### P64 — Treillis horizontal constructible

> **P67 — Treillis horizontal régulier, P64 révisée.**
>
> - Le point 3 de P64 (« Positions en X des montants inchangées ») est remplacé.
> - Dans chaque grande travée (de Xd à Xf = Xd + 6,25), 6 montants à
>   **Xd + k × 1,25, pour k = 0 à 5**, soit 5 panneaux égaux de 1,25 m.
>   - Avant : Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25.
> - Les diagonales restent en N, dans le même sens qu'au lot 52. Toutes les
>   diagonales des grandes travées deviennent identiques et parallèles : une
>   seule longueur et un seul angle de coupe, pour une fabrication en série en
>   usine.
> - Reste de P64 inchangé :
>   - nœud diagonale–montant à e = 0,25 m de l'axe des poutres, soit |Y| = 0,68 ;
>   - axe des montants et des diagonales à +1,29 ;
>   - liaisons rigides de 0,01 m et de 0,085 m.
> - Petites travées PT1 à PT5 et porte-à-faux : inchangés.
> - Le découpage des pannes suit les nouvelles positions. La portée maximale des
>   pannes passe de 1,50 m à 1,25 m.
> - Taquets inchangés : Xd + 1,6 et Xd + 4,6, sur les poutres principales.

- Écartée : Positions en X des montants inchangées (P64, point 3 : Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25) — 6 montants à Xd + k × 1,25, cinq panneaux égaux (P67)
- Note : Ré-arbitrage : seul le point 3 de P64 est remplacé (P67) ; nœud diagonale–montant à e = 0,25 m, axe +1,29, liaisons de 0,01 m et 0,085 m inchangés. Paramètre X_MONTANTS du script de maillage (variantes_lot54.yaml).

### P67 — Treillis horizontal régulier

> **P67 — Treillis horizontal régulier, P64 révisée.**
>
> - Le point 3 de P64 (« Positions en X des montants inchangées ») est remplacé.
> - Dans chaque grande travée (de Xd à Xf = Xd + 6,25), 6 montants à
>   **Xd + k × 1,25, pour k = 0 à 5**, soit 5 panneaux égaux de 1,25 m.
>   - Avant : Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25.
> - Les diagonales restent en N, dans le même sens qu'au lot 52. Toutes les
>   diagonales des grandes travées deviennent identiques et parallèles : une
>   seule longueur et un seul angle de coupe, pour une fabrication en série en
>   usine.
> - Reste de P64 inchangé :
>   - nœud diagonale–montant à e = 0,25 m de l'axe des poutres, soit |Y| = 0,68 ;
>   - axe des montants et des diagonales à +1,29 ;
>   - liaisons rigides de 0,01 m et de 0,085 m.
> - Petites travées PT1 à PT5 et porte-à-faux : inchangés.
> - Le découpage des pannes suit les nouvelles positions. La portée maximale des
>   pannes passe de 1,50 m à 1,25 m.
> - Taquets inchangés : Xd + 1,6 et Xd + 4,6, sur les poutres principales.

- Écartée : Montants à Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25 (lot 52) — cinq panneaux égaux de 1,25 m, diagonales identiques et parallèles (P67)
- Note : Révise P64 (point 3). Portée maximale des pannes 1,25 m ; taquets à Xd + 1,6 et Xd + 4,6 inchangés.

### P68 — Chevêtres 0,60 × 0,40 prolongés

> **P68 — Chevêtres 0,60 × 0,40 prolongés, P43 et P48 révisées.**
>
> - Section des chevêtres : **b = 0,60 m** (selon X) **× h = 0,40 m**.
>   - Coulés en place, à section constante sur toute leur longueur.
>   - La largeur de 0,60 m couvre la tête des piles Ø 0,50 sans surlargeur locale
>     de coffrage.
> - Longrines inchangées : 0,40 × 0,40.
> - Chevêtres prolongés de **Y = ±1,05 à Y = ±1,20**, pour placer la fixation de
>   l'appui à 0,15 m de l'about.
> - Axes inchangés :
>   - chevêtres en X = 6,25 + 7,77 k et en X + 1,52 ;
>   - arase +0,69, dessus +1,09.
> - Liaisons longrine–chevêtre, pieu–anneau et appuis : inchangées en principe.
>   Les longueurs des liaisons rigides suivent la nouvelle géométrie.
> - Écartées :
>   - anneau 0,40 × 0,40 de P43 et chevêtres de Y = −1,05 à +1,05 de P48 ;
>   - anneau 0,50 × 0,50 (proposition du superviseur), refusé par MM ;
>   - nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur),
>     abandonnés pour la constructibilité.

- Écartée : Anneau 0,40 × 0,40 de P43 et chevêtres de Y = −1,05 à +1,05 de P48 — chevêtres 0,60 × 0,40 prolongés à Y = ±1,20 (P68)
- Écartée : Anneau 0,50 × 0,50 (proposition du superviseur) — refusé par MM (P68)
- Écartée : Nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur) — abandonnés pour la constructibilité (P68)
- Note : Révise P43 et P48. Les longueurs des liaisons rigides (longrine–chevêtre, pieu–anneau, appuis) suivent la nouvelle géométrie.

### P69 — Houle de projet : forfait de 5 kPa

> **P69 — Houle de projet : forfait de 5 kPa, justifié par les études GEOMER, P56 et P60 révisées, P61 annulée.**
>
> - Les cas unitaires de 1 kPa par surface et par module de P56 sont conservés.
>   Seuls les événements changent :
>   - HU = 5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) ;
>   - HD = 5,0 × HD_TABLIER ;
>   - HU_F = 2,728 × HU_TUBES + 2,516 × HU_PANNES + 2,425 × HU_PLATELAGE, à
>     l'ELS fréquent. Valeurs majorantes : la houle fréquente n'atteint pas le
>     tablier.
> - **Aucun impact** : P61 est annulée. Les événements HU_IMP_Mk et leurs options
>   sont retirés des combinaisons.
> - **P62 révisée** : la houle reste dans le critère de flèche. HU et HD entrent
>   dans l'ELS caractéristique ; HU_IMP n'existe plus.
> - Justification :
>   - donnée d'entrée principale : houle mesurée à Cap Couronne (GEOMER, 1996),
>     transmise en zone 2 avec Kt = 0,10. Kt est commun au modèle physique GEOMER
>     de 1995 et à l'étude MS414803 ;
>   - les pannes A et B sont en **zone 2** GEOMER ;
>   - le calcul McConnell sur cette houle donne 4,0 à 5,0 kPa en sous-pression et
>     au plus 2,9 kPa en surpression.
> - Écartées :
>   - coefficients « tablier noyé » de P60 ;
>   - estimation à 11 kPa (houle au large ANEMOC + McConnell), qui n'apparaît que
>     pour mémoire dans la note d'hypothèses ;
>   - impacts de P61.
> - Toutes les autres règles de combinaison sont inchangées : P49, P57 et P59.
> - Nouveau groupe `houle_lot54` dans le fichier de données, avec les valeurs
>   ci-dessus.

- Écartée : Coefficients « tablier noyé » de P60 — forfait de 5 kPa (P69)
- Écartée : Estimation à 11 kPa (houle au large ANEMOC + McConnell) — pour mémoire seulement dans la note d'hypothèses (P69)
- Écartée : Impacts de P61 — aucun impact (P69)
- Note : Révise P56, P60 et P62 ; annule P61. Groupe houle_lot54 du fichier de données.

### P70 — Accostage et amarrage local jamais au même poste

> **P70 — Accostage et amarrage local jamais au même poste.**
>
> Un bateau qui accoste n'est pas amarré à son poste. Dans une même combinaison,
> les deux événements suivants sont **interdits ensemble** :
>
> - un amarrage local (AML_TQk_…) ou une rupture d'amarre (AMF_TQk_…) ;
> - un accostage (AC_… ou ACA_…).
>
> L'interdiction vaut lorsque les deux sont **sur la même rive** et que la
> distance en X entre le centre de la zone d'accostage et le taquet est
> **< 1,60 m** (demi-largeur de poste de 3,20 m).
>
> Centres des zones d'accostage :
>
> - début : Xd + 0,5 ;
> - milieu : (Xd + Xf)/2 ;
> - fin : Xf − 0,5 ;
> - PTk : milieu ;
> - PF : 38,85 + Lpf − 0,5.
>
> AM1 et AM2 (cas globaux) restent combinables avec AC et ACA : c'est
> sécuritaire.
>
> Mise en œuvre :
>
> - maximisation **conjointe** de l'emplacement AM et de l'emplacement AC (ou
>   ACA) dans chaque branche qui contient les deux, en excluant les paires
>   interdites ;
> - les autres emplacements restent indépendants ;
> - `recombiner.py` applique la même règle ;
> - énumération de contrôle sur 36 extrêmes tirés au sort, dont au moins 12 dans
>   des branches qui contiennent AM et AC.

- Écartée : Amarrage local (AML, AMF) et accostage (AC, ACA) combinables au même poste (lots 51 ter à 53) — interdits ensemble sur la même rive à moins de 1,60 m en X du centre de la zone d'accostage (P70)
- Note : AM1 et AM2 restent combinables avec AC et ACA. Maximisation conjointe des emplacements AM et AC (ou ACA) dans les branches qui contiennent les deux ; recombiner.py applique la même règle.

### P71 — Stabilité des palées existantes

> **P71 — Stabilité des palées existantes : responsabilité du maître d'ouvrage.**
>
> - Le maître d'ouvrage conserve les fondations sans intervention et prend à sa
>   charge la stabilité des palées : soulèvement, renversement, portance,
>   excentrement.
> - On retient la voie du « comportement constaté » de l'existant (1975, jamais
>   décollé).
> - **Aucun ancrage, aucun lest** n'est modélisé ni dimensionné (P48 confirmée).
> - Les réactions des semelles sont exportées pour mémoire seulement.
> - Raideurs de sol 5 000 / 1 000 kN/m³ conservées (P19, P48), sans étude de
>   sensibilité.

- Écartée : Ancrage ou lest des palées — aucun, la stabilité des palées est à la charge du maître d'ouvrage (P71)
- Note : Confirme P48 (aucun ancrage) et P19/P48 (raideurs de sol 5 000 / 1 000 kN/m³). Réactions des semelles exportées pour mémoire.

### P72 — Piles Ø 0,50 confirmées

> **P72 — Piles Ø 0,50 confirmées.**
>
> - P48 et P58 sont inchangées.
> - Le diamètre réel est d'environ 0,42 m, buse comprise. Il sera relevé en EXE.

- Écartée : Piles au diamètre réel d'environ 0,42 m, buse comprise — Ø 0,50 conservé, diamètre réel relevé en EXE (P72)
- Note : Confirme P48 et P58. Diamètre réel à relever en EXE.

### P73 — Platelage bois non fusible

> **P73 — Platelage bois non fusible ; caillebotis refusé.**
>
> - Le maître d'ouvrage assume le risque d'arrachement du platelage par la houle.
> - Le caillebotis est refusé : le client veut du bois.
> - Les surfaces chargées de HU_PLATELAGE (1,327 m) et de HD_TABLIER (1,895 m)
>   sont conservées.

- Écartée : Caillebotis — refusé, le client veut du bois (P73)
- Note : Surfaces chargées de HU_PLATELAGE (1,327 m) et de HD_TABLIER (1,895 m) inchangées.

### P74 — Liaison pieu–chevêtre

> **P74 — Liaison pieu–chevêtre.**
>
> - Barres HA20 scellées chimiquement dans le pieu recépé et ancrées par crosse
>   dans le chevêtre. Vérification par le superviseur.
> - Modèle : têtes de pieux encastrées dans l'anneau (P46), inchangé.

- Écartée : Liaison pieu–chevêtre non précisée (P46 : têtes encastrées) — barres HA20 scellées chimiquement dans le pieu recépé et ancrées par crosse dans le chevêtre (P74)
- Note : Complète P46 : modèle inchangé (têtes de pieux encastrées dans l'anneau).

### P75 — Culée : recépage du quai existant et bloc béton neuf

> **P75 — Culée : recépage du quai existant et bloc béton neuf.**
>
> - La culée reste neuve et conçue par nous (P45).
> - Son dimensionnement fera l'objet d'un lot ultérieur.
> - Modèle inchangé :
>   - deux appuis, X et Z bloqués, Y bloqué côté YP ;
>   - culée non modélisée, réactions exportées comme au lot 52.

- Écartée : Culée sans principe constructif (P45 : culée neuve) — recépage du quai existant et bloc béton neuf (P75)
- Note : Complète P45 : modèle inchangé ; dimensionnement de la culée dans un lot ultérieur.

### P76 — Fissuration de l'anneau en XS3

> **P76 — Fissuration de l'anneau en XS3.**
>
> - wmax = 0,2 mm sous combinaison quasi permanente, soit σs ≤ 200 MPa pour des
>   HA16.
> - Le superviseur vérifie l'anneau à l'ELS quasi permanent avec ce critère
>   (complète P23).
> - Sans effet sur le calcul du lot.

- Écartée : Critère d'ouverture de fissure non précisé (P23) — wmax = 0,2 mm sous combinaison quasi permanente, σs ≤ 200 MPa pour des HA16 (P76)
- Note : Complète P23. Sans effet sur le calcul du lot 54.
