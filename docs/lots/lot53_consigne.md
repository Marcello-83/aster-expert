# Lot 53 — Pontons aluminium : déplacements sous accostage et amarrage (post-traitement B52)

**Tout en français. Profil `vm`. Branche `lot-53`, depuis `main` après fusion
de `lot-52`.** Consigne copiée dans `docs/lots/lot53_consigne.md`.

## Objet

Donner les déplacements du ponton en X, Y et Z sous les actions d'accostage et
d'amarrage, et les mettre dans le `.med` des résultats. Lot court de
post-traitement de la variante **B52** du lot 52.

- Ni modèle modifié, ni cas ajouté, ni nouvelles combinaisons.
- Si les déplacements des 221 cas unitaires sont déjà dans `resultats.med` du
  lot 52 : les relire.
- Sinon : relancer B52 tel quel (même `.comm`, même maillage, empreintes
  identiques à vérifier) en ajoutant seulement l'archivage des déplacements.
- Ni EC9, ni béton armé, ni appareil d'appui.

## Actions concernées

Événements du lot 52 (`evenements.csv`, valeurs caractéristiques) :

- AC (accostage caractéristique, composantes ACN, ACX, ACZ) ;
- ACA (accostage accidentel) ;
- AM (AM1, AM2, AML) ;
- AMF.

T (TP, TM) seulement en référence.

## Points de sortie

Pour chaque point : DX, DY, DZ en mm, et rotations pour les semelles.

1. Axes d'appui : point de l'axe et chevêtre au droit de l'axe, côtés YM et
   YP, toutes palées. Ajouter le déplacement relatif tablier/chevêtre (jeu en
   Y côté guidé, glissement en X).
2. Poutres principales : mi-travée T1 à T5, côtés YM et YP.
3. Porte-à-faux : bout, côtés YM et YP.
4. Têtes de piles (+0,69) et centre des semelles : DX, DY, DZ, DRX, DRY.
5. Culée : appuis.

## Exports (B52)

**`deplacements_unitaires.csv`** : point, cas unitaire, DX, DY, DZ (et
rotations si utiles), pour les cas unitaires AC*, ACA*, AM*, AMF*, TP et TM.

**`deplacements_evenements.csv`** : pour chaque point et chaque direction,
l'extrême positif et l'extrême négatif sur l'ensemble des événements AC, ACA,
AM et AMF, à la valeur caractéristique (coefficients d'`evenements.csv`), avec
le nom de l'événement.

**`deplacements_combinaisons.csv`** : pour chaque point et chaque direction,
les extrêmes avec le libellé de la combinaison gouvernante, selon les règles
du lot 52 (`combinaisons.csv`, branches et modules) :

- ELS caractéristique ;
- ELS fréquent ;
- ELU accidentel.

Deux colonnes :

- **totaux** ;
- **actions variables seules**, sans G ni DEJ. C'est la même convention que
  pour les flèches : préciser si T est inclus, et donner les deux variantes,
  avec T et sans T.

**`deplacements_synthese.csv`** : une ligne par palée. Colonnes :

- DY max de la tête de palée, ELS caractéristique et ELU accidentel ;
- DY max du tablier au droit de la palée ;
- jeu relatif en Y tablier/chevêtre ;
- DX max de l'axe hors thermique ;
- DZ min et max de l'axe.

## MED et vues

**`resultats.med`** : ajouter des champs de déplacement nodaux, sur le même
support que les efforts.

- Un champ par événement caractéristique représentatif :
  - AC normal le plus défavorable en DY ;
  - ACA idem ;
  - AM1_+X ;
  - AM2_YP ;
  - AML et AMF gouvernants en DY.
- Les 4 combinaisons gouvernantes :
  - max |DY| ELS caractéristique ;
  - max |DX| ELS caractéristique, hors thermique ;
  - max |DY| ELS fréquent ;
  - max |DY| ELU accidentel.
- Noms de champs explicites (une table de correspondance dans le compte rendu
  si les noms MED doivent être courts).
- Script ParaVis adapté (déformée amplifiée, coloration par composante).

**PNG** :

- **vue A** : vue en plan de la déformée, max |DY| ELS caractéristique,
  amplification indiquée, valeurs en mm aux palées et au bout du porte-à-faux ;
- **vue B** : idem pour l'ELU accidentel ;
- **vue C** : élévation de la déformée, max |DX| ELS caractéristique, hors
  thermique.

## Contrôles

- Relecture ou recalcul : réactions et efforts identiques au lot 52 à 10⁻⁶ près
  sur 5 cas tirés au sort.
- DX de l'axe de P5 sous TP égal à `deplacements_axes.csv` du lot 52.
- Linéarité : déplacement d'un événement égal à la somme pondérée de ses cas
  unitaires, sur 3 événements.
- Ordre de grandeur de DY de la tête de P5 sous un ACN unitaire, comparé à une
  estimation à la main (4 piles encastrées en tête, semelle sur ressorts) :
  écart commenté en une phrase.
- PNG : fichiers non vides, vues A et C vérifiées à l'œil.

## Dépôt

`/media/sf_partage/echanges/lot53/pontons_alu_01/` :

- `B52/` : CSV ;
- `B52/MED/` ;
- `vues/` ;
- `scripts/` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Relecture ou recalcul, et pourquoi.
- Tableau `deplacements_synthese.csv`.
- Les 3 plus grands DY et DX, avec l'événement ou la combinaison.
- Contrôles.
- Correspondance des champs MED.
- PNG vérifiés à l'œil.
- `rex` et interventions.

## Interdits

- Aucune modification du modèle, des cas, des événements ou des combinaisons.
- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucun ancrage modélisé.
- Aucune modification des autres projets.
- Aucun bloc recopié à la main par palée ou par travée.
