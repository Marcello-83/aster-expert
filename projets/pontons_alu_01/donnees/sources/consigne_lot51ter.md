# Lot 51 ter — Pontons aluminium : ponton intégral, cotes AVP corrigées, houle par surfaces, ancrage des palées

**Tout en français. Profil `vm`. Branche `lot-51ter`, depuis `main` après
fusion de `lot-51bis`.** Consigne copiée dans `docs/lots/lot51ter_consigne.md`.
Cette version 3 remplace intégralement les versions 1 et 2 de la consigne.

## Objet

1. **Corriger les cotes.** Le lot 51 bis a été calé 0,50 m trop haut, par
   erreur de consigne du superviseur (P47). L'AVP (p. 15/96) fixe l'arase
   supérieure du tablier projeté à **+1,40 NGF**, soit le quai actuel (+0,90)
   rehaussé de 0,50 m. Tout doit tenir entre l'arase inférieure du chevêtre
   (+0,69) et +1,40.
2. **Modéliser la panne entière.** Il faut remplacer le modèle partiel (quai,
   travée, palée, travée, support fixe en X = 14,02) par le ponton complet :
   culée, 5 palées, 5 grandes travées et le porte-à-faux d'extrémité. La
   chaîne longitudinale jusqu'à la culée est alors calculée directement.
3. **Mesurer l'ancrage.** À ces cotes, le tablier est atteint par la houle.
   La sous-pression est recalculée par surfaces et par état limite. Le lot
   mesure, palée par palée, l'effort d'ancrage que demanderait chaque palée.

Le modèle, les cas, les événements et les combinaisons du lot 51 bis sont
repris, **sauf** ce qui est modifié ci-dessous.

**Calcul linéaire uniquement.** Ni EC9, ni béton armé, ni vérification
d'appui dans le lot. Règles d'économie habituelles :

- un `.comm` paramétré ;
- un script de maillage paramétré par la liste des stations ;
- les variantes dans `variantes_lot51ter.yaml`.

Les palées, les travées et les zones de chargement sont générées **par
boucle**, jamais recopiées à la main.

## Décisions à enregistrer (MM, 15 et 16/10/2026)

**P53 — Cotes AVP, P47 annulée.**

| Élément | Cote (m NGF) |
|---|---|
| Dessus des poutres principales et des pannes (pose du platelage) | +1,40 |
| Poutres principales 200 × 200 : axe | +1,30 |
| Poutres principales 200 × 200 : sous-face | +1,20 |
| Pannes 50 × 50 : axe (dessus affleurant) | +1,375 |
| Pannes 60 × 60 : axe (dessus affleurant) | +1,37 |
| Anneau BA 0,40 × 0,40 (chevêtres et longrines) : dessus | +1,09 |
| Anneau BA : arase inférieure | +0,69 |
| Anneau BA : axe | +0,89 |

Les montants et les diagonales gardent leur position relative aux poutres du
lot 51 bis : même plan que les poutres principales.

**P54 — Appui articulé compact** (principe P44 inchangé). Il est logé dans
les 0,11 m entre le dessus du chevêtre et la sous-face du tube :

- calage et platine : +1,09 à +1,125 ;
- **axe à +1,16** ;
- joues jusqu'à +1,195 ;
- oreilles sous le tube de +1,135 à +1,20.

La modélisation est inchangée par rapport au lot 51 bis, au point de l'axe
recalé :

- oreilles des deux travées liées en translation et en rotation autour de x
  (DRX) ;
- Z bloqué ;
- Y bloqué côté YP ;
- X libre.

Ce schéma s'applique aux **deux lignes d'appui de chacune des 5 palées**.

**P55 — Tubes percés (drainés).** Aucune flottabilité de l'aluminium. P50
annulée.

**P56 — Houle par surfaces et par état limite.**

- Référentiel unique : `pontons_niveaux_eau_houle_v2.xlsx`, à copier dans
  `donnees/sources/`.
- 0 m CM = −0,329 m NGF.
- Caractéristique = période de retour 50 ans (EN 1990).

Les cas HU et HD du lot 51 bis sont **remplacés** par quatre cas unitaires de
1 kPa, appliqués sur **toute la longueur** du tablier (porte-à-faux compris) :

| Cas | Surface | Largeur chargée | Application | Sens |
|---|---|---|---|---|
| HU_TUBES | sous-face des 2 poutres principales | 0,20 m chacune | ligne sur chaque poutre | haut |
| HU_PANNES | sous-face des 4 pannes | 0,05 m chacune | ligne sur chaque panne | haut |
| HU_PLATELAGE | sous-face des planches, joints déduits | 1,327 m au total | réparti entre pannes et poutres par largeurs tributaires (comme G2) | haut |
| HD_TABLIER | dessus du platelage | 1,895 m | idem G2 | bas |

**Coefficients uniformes sur toute la longueur.** Les pressions ont été
recalculées par plate-forme, avec les fonds réels (voir P58) et la méthode du
classeur :

- de P2 à P5, sur les deux pannes, la houle n'est pas limitée par la
  profondeur : valeurs P5 (à 1 % près pour P2 de la panne B) ;
- les plates-formes P1 des pannes A et B sont limitées par la profondeur.
  Leur scénario gouvernant est niveau 50 ans + Hs 5 ans, soit 13,55 kPa au
  lieu de 14,49 kPa sur les tubes (−6,5 %).

On retient donc les valeurs P5 partout (enveloppe, sans découpage en zones).
Coefficients sans γ :

| Événement | HU_TUBES | HU_PANNES | HU_PLATELAGE | HD_TABLIER | Scénario |
|---|---|---|---|---|---|
| HU (caractéristique) | 14,49 | 12,99 | 12,48 | — | niveau 5 ans + Hs 50 ans |
| HD (caractéristique) | — | — | — | 12,03 | idem |
| HU_F (fréquent) | 2,36 | 0,85 | 0,35 | — | PHMA 2050 + Hs 1 an |

La houle est **en phase sur toute la longueur**. C'est une borne haute pour
les efforts globaux, retenue volontairement.

Règles de combinaison pour la houle (le reste du jeu B′ est inchangé) :

- **ELU fondamental** : HU ou HD × 1,5 en dominante, × 1,5 × 0,77 en
  accompagnement.
- **ELU accidentel** : HU ou HD × 0,77 en accompagnement, comme au lot 51 bis.
- **ELS caractéristique** : HU ou HD × 1,0 en dominante, × 0,77 en
  accompagnement.
- **ELS fréquent** : en dominante, l'événement HU_F × 1,0 remplace ψ1·HU ;
  en accompagnement, rien (ψ2 = 0).
- **ELS quasi permanent** : pas de houle. La houle courante n'atteint pas le
  tablier.

Les cas sont unitaires et le calcul est linéaire. Si les pressions changent
(méthode dédiée, autre scénario, découpage par zones), seuls les coefficients
des événements changent, sans réexécution. Pour cela, conserver aussi les
quatre cas unitaires **découpés par module** (suffixes `_Mk`, voir §
Chargements) : leur somme doit égaler le cas total.

**P57 — Houle et accostage non concomitants.** Aucune combinaison ne contient
à la fois un événement HU ou HD et un événement AC ou ACA. Ils restent
concomitants avec AM, comme au lot 51 bis.

**P58 — Ponton intégral.** La géométrie est celle du lot 51 bis, répétée sur
toute la longueur, conformément aux décisions MM :

- piles Ø 0,50 ;
- entraxes du lot 51 ;
- travée de 6,25 m (P35) ;
- semelles du diagnostic.

**Rappel.** Le frottement de défense reste μ = 0,7. Le frontal à faible
frottement (μ = 0,3) est proposé mais pas encore acté.

## Géométrie du ponton intégral

**Stations en X** (m, origine sur la ligne d'appui de la culée). Elles sont
paramétrées dans le yaml, sous forme de liste, pour pouvoir être recalées sur
les implantations réelles sans toucher au code.

| Élément | X début | X fin |
|---|---|---|
| Culée (ligne d'appui) | 0,00 | — |
| Grande travée T1 | 0,00 | 6,25 |
| Palée P1 (petite travée PT1) | 6,25 | 7,77 |
| T2 | 7,77 | 14,02 |
| P2 (PT2) | 14,02 | 15,54 |
| T3 | 15,54 | 21,79 |
| P3 (PT3) | 21,79 | 23,31 |
| T4 | 23,31 | 29,56 |
| P4 (PT4) | 29,56 | 31,08 |
| T5 | 31,08 | 37,33 |
| P5 (PT5) | 37,33 | 38,85 |
| Porte-à-faux PF | 38,85 | 38,85 + Lpf |

**Contenu de chaque palée Pk.** Identique au lot 51 bis, translaté :

- 4 piles Ø 0,50 en (Xk ; ±0,75) et (Xk + 1,52 ; ±0,75) ;
- anneau BA 0,40 × 0,40 (chevêtres et longrines), arase inférieure +0,69 ;
- semelle 2,60 × 2,60 × 0,20 m centrée sur la palée, sur RIGI_PARASOL
  (mêmes raideurs qu'au lot 51 bis) ;
- 4 têtes de piles encastrées ;
- béton déjaugé (P49).

**Hauteur libre des piles** (de la sous-face de l'anneau +0,69 au dessus de
la semelle), selon le diagnostic A25-13959, annexe 2 :

| Panne | P1 | P2 | P3 | P4 | P5 | Lpf |
|---|---|---|---|---|---|---|
| A | 1,50 | 2,00 | 2,50 | 3,30 | 3,90 | 1,05 |
| B | 1,30 | 1,95 | 2,50 | 3,50 | 3,90 | 1,25 |

On en déduit, pour chaque palée :

- dessus de semelle = +0,69 − H ;
- sous-face de semelle (fond) = +0,49 − H.

Ces hauteurs sont celles mesurées par le diagnostic. La bathymétrie ARTEMIS
(notice MS414803-01, fig. 29, classes de 1 m en m NM) les recoupe : fonds de
−1 à −2 m NM près du quai, −3 à −5 m NM à 40 m. Ne pas la réinterpréter.

Lpf est le porte-à-faux du diagnostic (0,85 m pour A, 1,05 m pour B), compté
depuis la face de la plate-forme, augmenté de 0,20 m jusqu'à la ligne
d'appui. C'est une hypothèse : le signaler dans le compte rendu.

**Grandes travées et petites travées.** Section, pannes, montants et
diagonales, éclissages et liaisons comme au lot 51 bis. La variante
d'éclissage retenue au lot 51 bis s'applique à **toutes** les jonctions.

**Culée** (X = 0, conçue par nous) : point fixe longitudinal du ponton.

- Axe YP : X, Y et Z bloqués.
- Axe YM : X et Z bloqués.

Le support fixe en X = 14,02 du lot 51 bis est **supprimé**. Aucun autre
point fixe en X : la chaîne longitudinale passe entièrement par les poutres
jusqu'à la culée. L'hypothèse ΔN de post-traitement des lots précédents
devient sans objet.

**Porte-à-faux d'extrémité** : poutres principales et pannes prolongées
au-delà de P5, extrémité libre, avec une panne de rive transversale en bout.

## Chargements sur toute la longueur

**Cas G1, G2, Q, QD, TP, TM, TAP et TAM** : mêmes définitions qu'au lot 51
bis, étendues à toute la longueur.

**Découpage en modules.** G2, Q, QD, ainsi que les 4 cas houle, sont découpés
en modules :

- M0 = T1 ;
- Mk = PTk + T(k+1) pour k = 1 à 4 ;
- M5 = PT5 + PF.

Chaque module a son cas unitaire. Le cas total est la somme des modules.

Dispositions défavorables pour Q et QD : chaque module chargé ou non. Il ne
faut pas énumérer les 2⁶ combinaisons à l'aveugle. Pour chaque grandeur
exportée, sommer les contributions de même signe (méthode des lignes
d'influence, exacte en linéaire). Préciser la méthode dans le compte rendu.

**Accostage.** Cas répartis de 1 kN/m sur une zone de 1 m de la poutre de
rive, pour chaque côté s ∈ {YM, YP}, dans trois directions :

- `ACN` : perpendiculaire au bord, vers l'intérieur ;
- `ACX` : selon +X ;
- `ACZ` : selon +Z.

Zones générées par boucle :

- pour chaque grande travée Tk (de Xd à Xf) :
  - début [Xd ; Xd + 1] ;
  - milieu [(Xd + Xf)/2 − 0,5 ; (Xd + Xf)/2 + 0,5] ;
  - fin [Xf − 1 ; Xf] ;
- pour chaque petite travée PTk : le milieu, sur 1 m ;
- porte-à-faux : [38,85 + Lpf − 1 ; 38,85 + Lpf].

Cela fait 21 zones et 126 cas. Événements et facteurs : comme au lot 51 bis.

**Exclusivité de l'accostage (rappel explicite).** Un seul bateau accoste à
la fois. Chaque combinaison contient **au plus un** événement AC ou ACA,
c'est-à-dire une seule zone parmi 21, un seul côté et une seule variante
tangentielle. Les 126 cas unitaires ne sont jamais sommés entre eux. Cela
donne 21 × 2 × 4 = 168 événements AC, autant d'événements ACA, et autant de
combinaisons alternatives.

**Taquets.** Positions AVP reportées dans chaque grande travée, à Xd + 1,6 et
Xd + 4,6, sur chaque poutre de rive : 20 taquets au total. Pour chacun, deux
cas ponctuels de 1 kN :

- `AMY` : perpendiculaire au bord, vers l'extérieur ;
- `AMX` : selon +X.

Cela fait 40 cas. Les événements sont ceux du lot 51 bis, étendus :

- **AM local** : un taquet quelconque.
- **AM1** : les 20 taquets ensemble, ⊥ opposés, ∥ de même signe.
- **AM2** : les 10 taquets d'un même côté.
- **AMF** : un taquet quelconque.

Les intensités sont inchangées. AM1 est l'amarrage de tous les postes occupés
sous vent ou courant : il ne s'agit pas d'accostages simultanés.

**P59 — Facteurs ψ de l'amarrage** (note d'hypothèses AVP, tableau des
coefficients, conservés par P33) : ψ0 = 0,77, ψ1 = 0,77, ψ2 = 0,2, avec γ =
1,5 (P33). Pour AM local, AM1 et AM2 :

| État limite | AM en dominante | AM en accompagnement |
|---|---|---|
| ELU fondamental | × 1,5 | × 1,5 × 0,77 |
| ELS caractéristique | × 1,0 | × 0,77 |
| ELS fréquent | × 0,77 | × 0,2 |
| ELS quasi permanent | — | × 0,2 |

AMF reste réservé à l'ELU accidentel. Le compte rendu doit signaler que AM1 sur 20
taquets donne la poussée longitudinale maximale sur la culée.

Donner l'effectif des cas et des combinaisons.

## Variantes

| Code | Géométrie (hauteurs de piles, Lpf) | Poutres principales | Pannes |
|---|---|---|---|
| A10 | panne A | 200 × 200 × 10 | 50 × 50 × 5 |
| A12 | panne A | 200 × 200 × 12 | 60 × 60 × 5 |
| B10 | panne B | 200 × 200 × 10 | 50 × 50 × 5 |
| B12 | panne B | 200 × 200 × 12 | 60 × 60 × 5 |

## Corrections du tronc commun

1. **Harnais D** : accepter les cas élémentaires sans effort (TP et TM quand X
   est libre aux palées). Critère absolu, Σ|F| ≤ 1 N, quand l'échelle de
   référence est nulle.
2. **Volume de l'anneau** : les angles ne doivent plus être comptés deux fois
   dans DEJ et G1 (constat du lot 51 bis).

Un test pour chaque correction.

## Exports

**Formats du lot 51 bis**, étendus à toute la longueur :

- exports du §6, avec le repérage des barres par travée et par palée ;
- `appuis_axes.csv` : chaque appui, avec la palée et le côté ;
- `palee_equilibre.csv` : une ligne par palée.

**`ancrage.csv`**, par variante et par palée P1 à P5, à l'ELU fondamental et à
l'ELS caractéristique :

- ΣRz min du sol, et effort d'ancrage requis = max(0 ; −ΣRz min), avec la
  combinaison ;
- traction maximale de chaque pile, en tête et en pied, avec la combinaison ;
- part du soulèvement due à HU dans la combinaison gouvernante.

**`culee.csv`**, par variante. Pour chaque appui de culée et chaque
composante, aux ELU fondamental, ELU accidentel, ELS caractéristique et ELS
quasi permanent :

- RX, RY et RZ, max et min, avec la combinaison ;
- résultante horizontale max ;
- RZ min (soulèvement).

**`chaine_x.csv`**, par variante. Effort normal N max et min dans chaque
poutre principale, au droit de chaque ligne d'appui (culée, P1 à P5), à
l'ELU fondamental, avec la combinaison.

**`deplacements_axes.csv`**, par variante. Pour chaque axe d'appui de palée :

- DX sous TP et TM seuls ;
- DX max et min à l'ELS caractéristique.

Ces valeurs servent au dimensionnement des trous oblongs.

**`comparaison_variantes.csv`**, mêmes colonnes que le lot 51 bis, plus :

- effort d'ancrage requis maximal sur les palées, avec la palée concernée, à
  l'ELU et à l'ELS caractéristique ;
- RX max de culée à l'ELU ;
- |N| max dans les poutres principales ;
- DX max de l'axe de P5 ;
- flèches selon P51 pour chaque grande travée et pour le porte-à-faux
  (rapport L/flèche ; pour le porte-à-faux, L = 2 Lpf).

## Contrôles

- Exécution jusqu'à FIN pour les 4 variantes.
- Harnais D corrigé : toutes les résultantes de cas unitaires.
- Pour HU_PLATELAGE et HD_TABLIER, la résultante doit valoir largeur ×
  longueur totale du tablier × 1 kPa. Même contrôle pour chaque module.
- Somme des modules = cas total, pour G2, Q, QD et les 4 cas houle.
- Équilibre global sous AM1 : ΣRX culée + ΣRX palées = force appliquée, avec
  ΣRX palées = 0 attendu.
- Sous TP seul : réactions nulles, et DX de l'axe de P5 égal à α·ΔT·38,85, à
  1 % près.
- MED de charges et `charges_salome.py` pour B10.

## Dépôt

`/media/sf_partage/echanges/lot51ter/pontons_alu_01/` :

- `<variante>/` : exports ;
- `comparaison_variantes.csv` ;
- `B10/charges.med` et `B10/charges_salome.py` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P53 à P59.
- Géométrie générée : stations, hauteurs de piles, cotes des semelles, Lpf.
- Effectifs des cas et des combinaisons.
- Harnais et contrôles.
- Tableau de comparaison, avec une phrase par variante.
- Ancrage par palée : un tableau, P1 à P5 × 4 variantes, à l'ELU et à l'ELS
  caractéristique.
- Culée : réactions maximales.
- Chaîne longitudinale.
- DX des axes.
- Corrections du tronc commun.
- `rex` et interventions.

## Interdits

- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucune modification des autres projets.
- Aucun ancrage modélisé : le soulèvement se constate et se rapporte.
- Aucune duplication manuelle de blocs par palée ou par travée dans le `.comm`
  ou le script de maillage.
