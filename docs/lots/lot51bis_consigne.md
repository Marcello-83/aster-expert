# Lot 51 bis — Pontons aluminium : appuis articulés à axe, tablier rehaussé de 0,50 m, palées réelles, équilibre des palées

**Tout en français. Profil `vm`. Branche `lot-51bis`, depuis `main` après
fusion de `lot-51`.** Consigne copiée dans `docs/lots/lot51bis_consigne.md`.

## Objet

Le lot 51 a montré trois choses :

- le néoprène ne convient pas à ce tablier léger (NF EN 1337-3 : non-glissement,
  soulèvement, stabilité en rotation) ;
- la palée se soulève sous la houle ;
- des têtes de piles mixtes, une encastrée et une articulée, n'apportent rien.

MM a tranché le 15/10/2026, et le diagnostic Sixense A25 13959 (CD13, mars
2026) donne la géométrie réelle de la semelle.

Le lot recalcule donc la solution retenue sur quatre palées types, et mesure
l'**équilibre de la palée** (lest manquant) avec le béton déjaugé.

**Calcul linéaire uniquement.** Ni vérification EC9, ni béton armé, ni appui
dans le lot : le superviseur les fait.

Règles d'économie :

- un seul `.comm` paramétré, un seul script de maillage paramétré ;
- les variantes déclarées dans `variantes_lot51bis.yaml` ;
- tests ciblés.

Le chargement, les événements et les combinaisons du lot 51 sont repris
**sauf** ce qui est modifié ci-dessous.

## Décisions à enregistrer

Nature « pratique », tranchées par MM. Source : échanges du 15/10/2026 et
diagnostic Sixense.

- **P44 — Appuis du tablier sur les chevêtres.** Le néoprène et le profilé
  support sont **supprimés**, remplacés par un **appui mécanique articulé à
  axe** (schéma `schema_appui_articule_v2.png`). Sur chaque chevêtre :
  - une chape inox ;
  - un axe parallèle à Y, commun aux oreilles des deux travées qui s'y
    rejoignent.

  Fonctionnement :

  | Degré de liberté | Appui YP | Appui YM |
  |---|---|---|
  | Z (compression et traction) | bloqué | bloqué |
  | X | **libre** (trou oblong dans les joues) | **libre** |
  | Y | **bloqué** | **libre** |
  | Rotations | libres | libres |

  Entre les deux travées liées par l'axe : translations liées, rotations
  autour de y et z locaux libérées (éclissage articulé).

  L'appui en X = 14,02 (palée suivante) suit le même schéma.
- **P45 — Point fixe longitudinal au quai.** La chaîne des travées est
  continue en X jusqu'à la rotule fixe du quai. **La culée est neuve et conçue
  par nous** : rotules inchangées (YP fixe en X, Y et Z ; YM fixe en X et Z).
  La culée n'est pas modélisée, ses réactions sont exportées.
- **P46 — Têtes de piles encastrées** (4 sur 4) dans le chevêtre.
  Liaison pile–semelle : encastrement, comme au lot 51.
- **P47 — Rehausse de 0,50 m du tablier.** Toutes les cotes aluminium du lot
  51 sont augmentées de 0,50 m. Cotes déduites :
  - axe d'appui : 0,17 m sous la sous-face des poutres principales ;
  - dessus du chevêtre : 0,10 m sous l'axe, soit **+1,488 NGF** avec la
    géométrie du lot 51.

  Le compte rendu donne les cotes exactes retenues.
- **P48 — Géométrie des palées.**
  - **Piles et entraxes** : **ceux du lot 51**, décision de MM. Piles Ø 0,50 m,
    en (6,25 ; ±0,75) et (7,77 ; ±0,75), donc petite travée de 1,52 m.
  - **Semelle**, d'après le diagnostic (annexe 2) : béton grossier **non
    armé**, carrée 2,60 × 2,60 m, épaisseur 0,20 m, centrée sur les piles
    (X = 7,01), sur RIGI_PARASOL (5 000 et 1 000 kN/m³). Aucun ancrage dans le
    sol. Par rapport au lot 51 (2,52 × 2,90 × 0,25 m), elle pèse environ 7 kN
    de moins une fois déjaugée : le signaler dans le compte rendu.
  - **Anneau BA** : chevêtres et longrines de 0,40 m de large, de hauteur h
    variable (§1). Chevêtres de Y = −1,05 à +1,05.
- **P49 — Déjaugeage.** Le béton est entièrement immergé pour les niveaux de
  calcul : niveau d'eau le plus haut +1,61 NGF, supérieur au dessus du
  chevêtre. Nouveau cas **DEJ** : poussée d'Archimède sur **tout le volume de
  béton** (palée et culée exclue), 10 kN/m³, vers le haut. Combinaison :
  - avec **G × 0,9**, et aux ELS et à l'ELU accidentel avec G × 1,0 : DEJ × 1,0
    (le poids est favorable) ;
  - avec **G × 1,2** : DEJ × 0 (le poids est défavorable).

  Les ELS et l'ELU accidentel comportent donc les deux options, avec et sans
  DEJ.
- **P50 — Tubes aluminium étanches.** Avec la rehausse, la sous-face des
  poutres (environ +1,76 NGF) reste au-dessus du niveau le plus haut (+1,61) :
  pas de cas de flottabilité permanent. L'immersion transitoire sous la crête
  de houle est couverte par le forfait de 5 kPa, inchangé.
- **P51 — Règle de flèche.** La composante tangentielle d'accostage (ACZ,
  ACX) **n'entre pas** dans la flèche à l'ELS caractéristique : il n'y a pas
  d'effet irréversible. Elle reste dans la flèche à l'ELS fréquent, avec
  ψ1 = 0,5, et dans tous les états limites ultimes. Critères, appliqués par le
  superviseur : L/150 à l'ELS caractéristique, L/200 à l'ELS fréquent.

## 1. Variantes

Elles portent sur la hauteur h de l'anneau et sur la hauteur des piles de deux
palées types. Le diagnostic mesure des hauteurs de 1,30 m (P1) à 3,90 m (P5)
sous l'ancienne sous-face de poutre, à environ +0,69 NGF.

- Avec h = 0,80, la sous-face de l'anneau est à environ +0,69 : les piles
  gardent leur hauteur existante.
- Avec h = 0,40, la sous-face est à environ +1,09 : les piles sont rehaussées
  de 0,40 m.

| Code | h anneau | Hauteur libre des piles (dessus semelle → sous-face anneau) | Poutre principale |
|---|---|---|---|
| H40C | 0,40 | 1,70 m | 200 × 200 × 8 |
| H40P | 0,40 | 4,30 m | idem |
| H80C | 0,80 | 1,30 m | idem |
| H80P | 0,80 | 3,90 m | idem |
| H80C-S3 | 0,80 | 1,30 m | **200 × 200 × 10** |

Le reste est identique au modèle R du lot 51, hors décisions ci-dessus :

- quai, grande travée de 6,25 m, palée, grande travée de 6,25 m, appuis en
  X = 14,02 sur support fixe, comme au lot 51 ;
- pannes, montants, diagonales et petite travée (hypothèse du lot 51) ;
- accostage : zones QU, MI1, CH1, PT et PA2 du lot 51, inchangées ;
- taquets aux positions AVP.

## 2. Exports

Formats du lot 51, pour chaque variante : exports du §6 du lot 51, sans
`appuis_neoprene.csv`. À la place, **`appuis_axes.csv`** : par appui (A1, A2 et
A3, YM et YP) et par cas élémentaire, les efforts transmis par l'axe au
chevêtre (Fx, Fy, Fz ; Fz > 0 en compression) et la rotation relative autour
de Y.

Ajouter **`palee_equilibre.csv`**, par variante, avec :

- la somme des réactions du sol sous la semelle, minimale par état limite, et
  sa combinaison ;
- le nombre et la position des ressorts de sol en traction dans cette
  combinaison ;
- l'effort normal maximal de **traction** de chaque pile, en tête et en pied,
  par état limite ;
- le **lest manquant** = max(0 ; −ΣRz min ELU) / 0,9, en kN.

## 3. Comparaison

`comparaison_variantes.csv`, mêmes colonnes que le lot 51, avec en plus :

- ΣRz min de la semelle (ELU, ELS caractéristique) ;
- lest manquant ;
- traction maximale des piles ;
- M en tête et en pied des piles ;
- Fz min et max, et Fy max, des appuis à axe ;
- réactions de la culée (RX, RY, RZ).

Flèches de la travée 1 selon P51. Une phrase par variante.

## 4. Contrôles

- Exécution jusqu'à FIN pour les 5 variantes (niveau C).
- Harnais D, y compris DEJ : la résultante doit valoir 10 kN/m³ × volume de
  béton, à 10⁻⁶ près.
- MED de charges et `charges_salome.py` pour H80C seulement.

## Points ouverts, signalés et non tranchés

- Effort de houle sur tablier rehaussé : forfait de 5 kPa conservé.
- Liaison réelle pile–semelle et ferraillage des pieux existants : inconnus.
  Diagnostic : armatures « très peu denses » en partie immergée, ronds lisses
  de 12 mm.
- Épaisseur réelle de la semelle : 0,10 à 0,25 m. Le superviseur fera varier
  le lest à la main.
- Porte-à-faux d'extrémité de panne : 0,85 à 1,05 m, non modélisé.

## Dépôt

`/media/sf_partage/echanges/lot51bis/pontons_alu_01/` :

- `<variante>/` : exports ;
- `comparaison_variantes.csv` ;
- `H80C/charges.med` et `H80C/charges_salome.py` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P44 à P51.
- Cotes retenues.
- Variantes calculées.
- Harnais.
- Tableau de comparaison, avec une phrase par variante.
- Points ouverts.
- `rex` et interventions.

## Interdits

- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucune modification des autres projets.
- Aucun ancrage de semelle ni stabilisation artificielle. Un soulèvement se
  constate et se rapporte.
