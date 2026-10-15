# Enregistrement des décisions P44 à P51 de MM — projet `pontons_alu_01` (lot 51 bis)

Décisions de la consigne du lot 51 bis (MM, échanges du 15/10/2026 et diagnostic Sixense A25 13959,
CD13, mars 2026), enregistrées par la même fonction que `aster-expert fiche enregistrer`. Les textes
sont recopiés tels quels de la source par script (jamais retapés) ; la vérification exige qu'ils y
figurent à l'identique.

Source du texte : donnees/sources/consigne_lot51bis.md
Enregistré le : 2026-10-15T13:00:00-04:00
Domaine de validité par défaut : Calcul linéaire des palées types et des trois travées de PONTONS-ALU-01 (lot 51 bis), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P44 — Appuis du tablier : appui mécanique articulé à axe

> - **P44 — Appuis du tablier sur les chevêtres.** Le néoprène et le profilé
>   support sont **supprimés**, remplacés par un **appui mécanique articulé à
>   axe** (schéma `schema_appui_articule_v2.png`). Sur chaque chevêtre :
>   - une chape inox ;
>   - un axe parallèle à Y, commun aux oreilles des deux travées qui s'y
>     rejoignent.
> 
>   Fonctionnement :
> 
>   | Degré de liberté | Appui YP | Appui YM |
>   |---|---|---|
>   | Z (compression et traction) | bloqué | bloqué |
>   | X | **libre** (trou oblong dans les joues) | **libre** |
>   | Y | **bloqué** | **libre** |
>   | Rotations | libres | libres |
> 
>   Entre les deux travées liées par l'axe : translations liées, rotations
>   autour de y et z locaux libérées (éclissage articulé).
> 
>   L'appui en X = 14,02 (palée suivante) suit le même schéma.

- Écartée : Appuis néoprène sur profilé support 150 × 150 × 7 (P38, P39, lot 51) — supprimés, néoprène inadapté au tablier léger (NF EN 1337-3 : non-glissement, soulèvement, stabilité en rotation) ; remplacés par l'appui articulé à axe (P44)
- Écartée : Appui mécanique de la variante M du lot 51 (Y et Z liés aux six appuis, X libre) — remplacé par l'appui à axe : Y bloqué en YP seulement, éclissage articulé par l'axe commun (P44)
- Note : Schéma de principe : schema_appui_articule_v2.png (partage, non versionné, fichier de MM). Modélisation : relations linéaires (LIAISON_DDL) entre les nœuds d'extrémité des poutres principales, le point de l'axe et le nœud du chevêtre ; voir docs/essais_lot51bis.md.

### P45 — Point fixe longitudinal au quai, culée neuve

> - **P45 — Point fixe longitudinal au quai.** La chaîne des travées est
>   continue en X jusqu'à la rotule fixe du quai. **La culée est neuve et conçue
>   par nous** : rotules inchangées (YP fixe en X, Y et Z ; YM fixe en X et Z).
>   La culée n'est pas modélisée, ses réactions sont exportées.

- Écartée : Appuis de la palée bloqués en X (néoprènes, raideur horizontale) — chaîne continue en X jusqu'à la rotule fixe du quai (P45)

### P46 — Têtes de piles encastrées

> - **P46 — Têtes de piles encastrées** (4 sur 4) dans le chevêtre.
>   Liaison pile–semelle : encastrement, comme au lot 51.

- Écartée : Têtes de piles en rotule (variante R du lot 51) ou mixtes (T1) — 4 têtes encastrées (P46)

### P47 — Rehausse de 0,50 m du tablier

> - **P47 — Rehausse de 0,50 m du tablier.** Toutes les cotes aluminium du lot
>   51 sont augmentées de 0,50 m. Cotes déduites :
>   - axe d'appui : 0,17 m sous la sous-face des poutres principales ;
>   - dessus du chevêtre : 0,10 m sous l'axe, soit **+1,488 NGF** avec la
>     géométrie du lot 51.
> 
>   Le compte rendu donne les cotes exactes retenues.

- Écartée : Cotes aluminium du lot 51 (plan moyen +1,358 NGF) — rehaussées de 0,50 m (P47)
- Note : Cotes retenues : voir le compte rendu du lot 51 bis (plan moyen +1,858, axe d'appui +1,588, dessus des chevêtres +1,488 NGF, grille de 1 mm).

### P48 — Géométrie des palées

> - **P48 — Géométrie des palées.**
>   - **Piles et entraxes** : **ceux du lot 51**, décision de MM. Piles Ø 0,50 m,
>     en (6,25 ; ±0,75) et (7,77 ; ±0,75), donc petite travée de 1,52 m.
>   - **Semelle**, d'après le diagnostic (annexe 2) : béton grossier **non
>     armé**, carrée 2,60 × 2,60 m, épaisseur 0,20 m, centrée sur les piles
>     (X = 7,01), sur RIGI_PARASOL (5 000 et 1 000 kN/m³). Aucun ancrage dans le
>     sol. Par rapport au lot 51 (2,52 × 2,90 × 0,25 m), elle pèse environ 7 kN
>     de moins une fois déjaugée : le signaler dans le compte rendu.
>   - **Anneau BA** : chevêtres et longrines de 0,40 m de large, de hauteur h
>     variable (§1). Chevêtres de Y = −1,05 à +1,05.

- Écartée : Semelle du lot 51 (2,52 × 2,90 × 0,25 m) — semelle du diagnostic Sixense A25 13959, 2,60 × 2,60 × 0,20 m, non armée (P48)
- Écartée : Anneau de hauteur unique 0,40 m (P43) — hauteur h de 0,40 ou 0,80 m selon la variante (P48, consigne § 1)
- Note : Variantes de la consigne § 1 (H40C, H40P, H80C, H80P, H80C-S3) : variantes_lot51bis.yaml.

### P49 — Déjaugeage du béton

> - **P49 — Déjaugeage.** Le béton est entièrement immergé pour les niveaux de
>   calcul : niveau d'eau le plus haut +1,61 NGF, supérieur au dessus du
>   chevêtre. Nouveau cas **DEJ** : poussée d'Archimède sur **tout le volume de
>   béton** (palée et culée exclue), 10 kN/m³, vers le haut. Combinaison :
>   - avec **G × 0,9**, et aux ELS et à l'ELU accidentel avec G × 1,0 : DEJ × 1,0
>     (le poids est favorable) ;
>   - avec **G × 1,2** : DEJ × 0 (le poids est défavorable).
> 
>   Les ELS et l'ELU accidentel comportent donc les deux options, avec et sans
>   DEJ.

- Écartée : Béton non déjaugé (lot 51) — poussée d'Archimède DEJ sur tout le volume de béton de la palée (P49)

### P50 — Tubes aluminium étanches, pas de flottabilité permanente

> - **P50 — Tubes aluminium étanches.** Avec la rehausse, la sous-face des
>   poutres (environ +1,76 NGF) reste au-dessus du niveau le plus haut (+1,61) :
>   pas de cas de flottabilité permanent. L'immersion transitoire sous la crête
>   de houle est couverte par le forfait de 5 kPa, inchangé.

- Écartée : Cas de flottabilité permanent des tubes — sans objet, sous-face au-dessus du niveau le plus haut (P50)

### P51 — Règle de flèche

> - **P51 — Règle de flèche.** La composante tangentielle d'accostage (ACZ,
>   ACX) **n'entre pas** dans la flèche à l'ELS caractéristique : il n'y a pas
>   d'effet irréversible. Elle reste dans la flèche à l'ELS fréquent, avec
>   ψ1 = 0,5, et dans tous les états limites ultimes. Critères, appliqués par le
>   superviseur : L/150 à l'ELS caractéristique, L/200 à l'ELS fréquent.

- Écartée : Composante tangentielle d'accostage dans la flèche à l'ELS caractéristique (lot 51) — exclue de cette flèche (P51)
