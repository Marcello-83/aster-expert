# Enregistrement des décisions P53 à P59 de MM — projet `pontons_alu_01` (lot 51 ter)

Décisions de la consigne du lot 51 ter (MM, 15 et 16/10/2026), enregistrées par `aster-expert fiche
enregistrer`. P53 annule P47 et P55 annule P50 : P47 et P50 sont ré-arbitrées (l'ancienne décision va
dans l'historique). Les textes sont extraits de la source par script (jamais retapés) ; la
vérification exige qu'ils y figurent à l'identique.

Source du texte : donnees/sources/consigne_lot51ter.md
Enregistré le : 2026-10-16T09:00:00-04:00
Domaine de validité par défaut : Calcul linéaire du ponton intégral de PONTONS-ALU-01 (lot 51 ter), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P47 — Rehausse de 0,50 m du tablier

> 1. **Corriger les cotes.** Le lot 51 bis a été calé 0,50 m trop haut, par
>    erreur de consigne du superviseur (P47). L'AVP (p. 15/96) fixe l'arase
>    supérieure du tablier projeté à **+1,40 NGF**, soit le quai actuel (+0,90)
>    rehaussé de 0,50 m. Tout doit tenir entre l'arase inférieure du chevêtre
>    (+0,69) et +1,40.

- Écartée : Rehausse de 0,50 m de toutes les cotes aluminium du lot 51 (P47, lot 51 bis : plan moyen +1,858, axe d'appui +1,588, dessus des chevêtres +1,488 NGF) — erreur de consigne du superviseur ; annulée par P53 (cotes de l'AVP, p. 15/96, dessus du tablier +1,40 NGF)
- Note : Ré-arbitrage : P47 est annulée et remplacée par P53 ; l'ancienne décision reste dans l'historique de la fiche.

### P50 — Tubes aluminium étanches, pas de flottabilité permanente

> **P55 — Tubes percés (drainés).** Aucune flottabilité de l'aluminium. P50
> annulée.

- Écartée : Tubes aluminium étanches (P50, lot 51 bis) — tubes percés (drainés), aucune flottabilité de l'aluminium (P55)
- Note : Ré-arbitrage : P50 est annulée par P55.

### P53 — Cotes de l'AVP

> **P53 — Cotes AVP, P47 annulée.**
>
> | Élément | Cote (m NGF) |
> |---|---|
> | Dessus des poutres principales et des pannes (pose du platelage) | +1,40 |
> | Poutres principales 200 × 200 : axe | +1,30 |
> | Poutres principales 200 × 200 : sous-face | +1,20 |
> | Pannes 50 × 50 : axe (dessus affleurant) | +1,375 |
> | Pannes 60 × 60 : axe (dessus affleurant) | +1,37 |
> | Anneau BA 0,40 × 0,40 (chevêtres et longrines) : dessus | +1,09 |
> | Anneau BA : arase inférieure | +0,69 |
> | Anneau BA : axe | +0,89 |
>
> Les montants et les diagonales gardent leur position relative aux poutres du
> lot 51 bis : même plan que les poutres principales.

- Écartée : Tablier rehaussé de 0,50 m par rapport au lot 51 (P47, lot 51 bis) — calé 0,50 m trop haut ; cotes de l'AVP (P53)
- Écartée : Cotes du lot 51 (plan moyen +1,358 NGF) — quai actuel +0,90 rehaussé de 0,50 m : dessus du tablier +1,40 NGF (P53)
- Note : Grille de 1 mm : dessus +1,40, axe des poutres +1,30, pannes 50 × 50 : +1,375, pannes 60 × 60 : +1,37, anneau 0,40 × 0,40 de +0,69 à +1,09 (axe +0,89) ; voir docs/essais_lot51ter.md.

### P54 — Appui articulé compact

> **P54 — Appui articulé compact** (principe P44 inchangé). Il est logé dans
> les 0,11 m entre le dessus du chevêtre et la sous-face du tube :
>
> - calage et platine : +1,09 à +1,125 ;
> - **axe à +1,16** ;
> - joues jusqu'à +1,195 ;
> - oreilles sous le tube de +1,135 à +1,20.
>
> La modélisation est inchangée par rapport au lot 51 bis, au point de l'axe
> recalé :
>
> - oreilles des deux travées liées en translation et en rotation autour de x
>   (DRX) ;
> - Z bloqué ;
> - Y bloqué côté YP ;
> - X libre.
>
> Ce schéma s'applique aux **deux lignes d'appui de chacune des 5 palées**.

- Écartée : Axe d'appui à +1,588 NGF, 0,17 m sous la sous-face des poutres (lot 51 bis) — appui compact logé dans les 0,11 m entre le dessus du chevêtre et la sous-face du tube, axe à +1,16 NGF (P54)
- Note : Modélisation inchangée (LIAISON_DDL au point de l'axe recalé) ; sur le chevêtre C2 de P5, une seule oreille (petite travée continue avec le porte-à-faux).

### P55 — Tubes percés, pas de flottabilité de l'aluminium

> **P55 — Tubes percés (drainés).** Aucune flottabilité de l'aluminium. P50
> annulée.

- Écartée : Tubes aluminium étanches (P50) — tubes percés (drainés) : aucune flottabilité (P55)

### P56 — Houle par surfaces et par état limite

> **P56 — Houle par surfaces et par état limite.**
>
> - Référentiel unique : `pontons_niveaux_eau_houle_v2.xlsx`, à copier dans
>   `donnees/sources/`.
> - 0 m CM = −0,329 m NGF.
> - Caractéristique = période de retour 50 ans (EN 1990).
>
> Les cas HU et HD du lot 51 bis sont **remplacés** par quatre cas unitaires de
> 1 kPa, appliqués sur **toute la longueur** du tablier (porte-à-faux compris) :
>
> | Cas | Surface | Largeur chargée | Application | Sens |
> |---|---|---|---|---|
> | HU_TUBES | sous-face des 2 poutres principales | 0,20 m chacune | ligne sur chaque poutre | haut |
> | HU_PANNES | sous-face des 4 pannes | 0,05 m chacune | ligne sur chaque panne | haut |
> | HU_PLATELAGE | sous-face des planches, joints déduits | 1,327 m au total | réparti entre pannes et poutres par largeurs tributaires (comme G2) | haut |
> | HD_TABLIER | dessus du platelage | 1,895 m | idem G2 | bas |
>
> **Coefficients uniformes sur toute la longueur.** Les pressions ont été
> recalculées par plate-forme, avec les fonds réels (voir P58) et la méthode du
> classeur :
>
> - de P2 à P5, sur les deux pannes, la houle n'est pas limitée par la
>   profondeur : valeurs P5 (à 1 % près pour P2 de la panne B) ;
> - les plates-formes P1 des pannes A et B sont limitées par la profondeur.
>   Leur scénario gouvernant est niveau 50 ans + Hs 5 ans, soit 13,55 kPa au
>   lieu de 14,49 kPa sur les tubes (−6,5 %).
>
> On retient donc les valeurs P5 partout (enveloppe, sans découpage en zones).
> Coefficients sans γ :
>
> | Événement | HU_TUBES | HU_PANNES | HU_PLATELAGE | HD_TABLIER | Scénario |
> |---|---|---|---|---|---|
> | HU (caractéristique) | 14,49 | 12,99 | 12,48 | — | niveau 5 ans + Hs 50 ans |
> | HD (caractéristique) | — | — | — | 12,03 | idem |
> | HU_F (fréquent) | 2,36 | 0,85 | 0,35 | — | PHMA 2050 + Hs 1 an |
>
> La houle est **en phase sur toute la longueur**. C'est une borne haute pour
> les efforts globaux, retenue volontairement.
>
> Règles de combinaison pour la houle (le reste du jeu B′ est inchangé) :
>
> - **ELU fondamental** : HU ou HD × 1,5 en dominante, × 1,5 × 0,77 en
>   accompagnement.
> - **ELU accidentel** : HU ou HD × 0,77 en accompagnement, comme au lot 51 bis.
> - **ELS caractéristique** : HU ou HD × 1,0 en dominante, × 0,77 en
>   accompagnement.
> - **ELS fréquent** : en dominante, l'événement HU_F × 1,0 remplace ψ1·HU ;
>   en accompagnement, rien (ψ2 = 0).
> - **ELS quasi permanent** : pas de houle. La houle courante n'atteint pas le
>   tablier.
>
> Les cas sont unitaires et le calcul est linéaire. Si les pressions changent
> (méthode dédiée, autre scénario, découpage par zones), seuls les coefficients
> des événements changent, sans réexécution. Pour cela, conserver aussi les
> quatre cas unitaires **découpés par module** (suffixes `_Mk`, voir §
> Chargements) : leur somme doit égaler le cas total.

- Écartée : Forfait de houle de 5 kPa sur le tablier, cas HU et HD des lots 50 à 51 bis — remplacé par quatre cas unitaires de 1 kPa par surface et des coefficients par état limite (P56)
- Écartée : Découpage des pressions par zones (P1 des pannes A et B limitées par la profondeur : 13,55 kPa au lieu de 14,49 sur les tubes) — valeurs P5 retenues partout (enveloppe), sans découpage en zones (P56)
- Note : Classeur donnees/sources/pontons_niveaux_eau_houle_v2.xlsx (copie du partage « Claude outputs », 16/10/2026, sha256 43d4a4ca…) ; coefficients dans le groupe houle_lot51ter du fichier de données.

### P57 — Houle et accostage non concomitants

> **P57 — Houle et accostage non concomitants.** Aucune combinaison ne contient
> à la fois un événement HU ou HD et un événement AC ou ACA. Ils restent
> concomitants avec AM, comme au lot 51 bis.

- Écartée : Houle concomitante avec l'accostage (lots 51 et 51 bis, jeu B′) — aucune combinaison ne contient à la fois HU ou HD et AC ou ACA (P57)

### P58 — Ponton intégral

> **P58 — Ponton intégral.** La géométrie est celle du lot 51 bis, répétée sur
> toute la longueur, conformément aux décisions MM :
>
> - piles Ø 0,50 ;
> - entraxes du lot 51 ;
> - travée de 6,25 m (P35) ;
> - semelles du diagnostic.

- Écartée : Modèle partiel du lot 51 bis (quai, travée, palée, travée, support fixe en X = 14,02) — ponton complet : culée, 5 palées, 5 grandes travées, porte-à-faux (P58)
- Écartée : Point fixe longitudinal au quai et hypothèse ΔN de post-traitement (lots 50 à 51 bis) — culée neuve en X = 0, seul point fixe ; chaîne longitudinale calculée directement (P58)
- Note : Hauteurs libres des piles et porte-à-faux : diagnostic A25-13959, annexe 2 (variantes_lot51ter.yaml) ; Lpf = porte-à-faux du diagnostic + 0,20 m jusqu'à la ligne d'appui, hypothèse de la consigne.

### P59 — Facteurs ψ de l'amarrage

> **P59 — Facteurs ψ de l'amarrage** (note d'hypothèses AVP, tableau des
> coefficients, conservés par P33) : ψ0 = 0,77, ψ1 = 0,77, ψ2 = 0,2, avec γ =
> 1,5 (P33). Pour AM local, AM1 et AM2 :
>
> | État limite | AM en dominante | AM en accompagnement |
> |---|---|---|
> | ELU fondamental | × 1,5 | × 1,5 × 0,77 |
> | ELS caractéristique | × 1,0 | × 0,77 |
> | ELS fréquent | × 0,77 | × 0,2 |
> | ELS quasi permanent | — | × 0,2 |
>
> AMF reste réservé à l'ELU accidentel. Le compte rendu doit signaler que AM1 sur 20
> taquets donne la poussée longitudinale maximale sur la culée.

- Écartée : Facteurs ψ de l'amarrage non rappelés par état limite (lot 51, ψ du projet conservés) — tableau de la note d'hypothèses AVP par état limite (P59)
