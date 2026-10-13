# Lot 50 quater — Pontons aluminium : visualisation des charges dans ParaView

**Tout en français. Profil `vm`. Branche `lot-50quater`, depuis `main` après
fusion de `lot-50ter`.** Consigne copiée dans `docs/lots/lot50quater_consigne.md`.

## Pourquoi

Le lot 49 a rendu natifs dans le tronc commun un MED de vérification des
charges et le script ParaView associé : `Calculator`, `Glyph`, échelle
calculée, génération depuis le manifeste.

Le lot 50 a pourtant déposé `med/charges.med` (509 ko) **sans aucun script
ni image ParaView**, alors que sa consigne les demandait. Le compte rendu ne
l'a pas signalé, et le lot 50 bis n'a déposé aucun MED.

MM veut contrôler lui-même, dans ParaView, l'application des charges du
modèle de référence.

**Référence** : exécution `20261012T144404-2cf50a46` (lot 50 bis : P24, P25,
MP1200, k = 1), la même que pour le lot 50 ter. Le `charges.med` du lot 50
porte l'ancienne géométrie (tablier 2,27 m, poutres déplacées au lot 50 bis) :
**il ne doit pas servir**.

Règles d'économie du lot 50 : tests ciblés, batterie complète à la fin, rien
sur les autres projets.

## Étape 0 — Diagnostic, court

1. **Chaîne du lot 49.** Pourquoi n'a-t-elle rien produit ou rien déposé pour
   `pontons_alu_01` ? Est-ce un générateur limité aux modèles de coques ou de
   massifs, une étape non branchée sur le dépôt, ou un échec silencieux ?
   Une phrase de cause dans le compte rendu, avec le fichier et la ligne.
2. **MED de charges de l'exécution de référence.** Existe-t-il dans le dépôt ?
   Si oui, inventaire du fichier :
   - maillage(s) ;
   - champs : nom, support (nœuds, éléments, points de Gauss), composantes ;
   - pas ou numéros d'ordre, et correspondance avec les 16 cas de
     `charges.csv` (G1, G2, Q, QD, HU, HD, TP, TM, TAP, TAM, AMM, AMP, ACM,
     ACP, AAM, AAP).
3. **S'il manque, ou s'il ne couvre pas les 16 cas**, il est régénéré à partir
   du `.comm` de référence et du même maillage :
   - de préférence par une exécution limitée à la construction des champs de
     charge, sans résolution, si le catalogue 17.4 le permet ;
   - sinon par réexécution du `.comm` de référence à l'identique.

   Les mots-clés retenus sont justifiés par le catalogue ou la documentation
   U4, jamais de mémoire. Les résultats du lot 50 bis ne sont pas modifiés.

## Étape 1 — Contenu attendu du MED de charges

Un pas par cas élémentaire, nommé par son identifiant (`G1`, `Q`, …).

Pour chaque cas :

- **Forces nodales équivalentes** (FX, FY, FZ, et MX, MY, MZ si non nuls).
  C'est ce que voit le solveur.
- **Intensité de la charge répartie par élément**, en N/m, avec ses
  composantes globales. Elle vaut zéro pour les éléments non chargés.
  C'est ce qui se compare aux hypothèses et aux figures de l'AVP.

Cas particuliers :

- **Température** (TP, TM, TAP, TAM) : champ par élément de l'écart ΔT en K.
- **Pesanteur** (G1) : forces nodales seulement.
- **Ponctuelles** (AMM, AMP) : forces nodales aux deux nœuds chargés.

Les noms de champs sont lisibles par MM sans documentation, par exemple
`CHARGE_NODALE`, `CHARGE_REPARTIE`, `ECART_TEMPERATURE`.

## Étape 2 — Script ParaView

Fichier `charges_paraview.py`, **généré par le tronc commun** depuis le
manifeste du MED, puis déposé. Il doit être lisible et modifiable à la main
par MM :

- un en-tête de paramètres commentés en français :
  - chemin du MED ;
  - cas affiché à l'ouverture ;
  - facteur d'échelle manuel (`None` pour le facteur calculé) ;
  - pas de sous-échantillonnage ;
- une fonction par représentation, sans code mort ;
- il tourne à la fois dans l'interface (Python Shell → Run Script) et en
  `pvpython`.

**Représentations, par cas :**

- **Forces nodales** :
  - flèches orientées selon le vecteur, colorées selon la norme ;
  - légende en kN ;
  - échelle commune à tous les cas de même nature (réparties, ponctuelles,
    pesanteur), pour comparer les intensités d'un cas à l'autre.
- **Charge répartie** : éléments colorés selon l'intensité, légende en kN/m.
  Les éléments non chargés sont en gris neutre, pas dans la teinte du zéro.
- **Température** : éléments colorés selon ΔT, légende en K.
- **Toujours visibles** :
  - le modèle filaire complet en fond, gris clair ;
  - les appuis (rotules côté quai, ressorts de la semelle) en symboles
    distincts ;
  - un titre donnant le cas, la nature et la résultante (ΣFX, ΣFY, ΣFZ
    en kN).

À l'ouverture, seul le premier cas est visible. Les autres sont dans le
navigateur de pipeline, nommés par cas.

Livrer aussi l'état `charges.pvsm` équivalent, si sa génération est fiable.

**Ouverture sous Windows** : appliquer la conclusion du lot 49, étape 4.4.
Si un ParaView standard ne lit pas le MED, livrer en plus la conversion
`.vtu` ou `.pvd`, que le script lit alors à la place du MED (paramètre
d'en-tête).

## Étape 3 — Contrôles, sans excès

1. **Résultantes.** Pour chaque cas mécanique, comparer la somme des forces
   nodales du MED à l'intégrale des charges de `charges.csv` (lot 50 ter).
   Tolérance de 10⁻⁶ en relatif. Le tableau des 12 cas va dans le compte
   rendu. Pour mémoire, Q = −62,5 kN en Z.
2. **Images de contrôle.** Un PNG iso par cas, rendu hors écran avec le script
   livré lui-même, sans copie ni variante. Puis une vue en plan pour Q et pour
   HU.
3. **Tronc commun.** Un test vérifie que tout projet filaire produit et dépose
   automatiquement le MED de charges, le script et les PNG. C'est la règle
   déjà actée par MM : chaque projet livre un MED de vérification des cas de
   charge avec son script ParaView.

## Dépôt

`/media/sf_partage/echanges/lot50quater/pontons_alu_01/` :

- `charges.med`, et la conversion `.vtu` ou `.pvd` si nécessaire ;
- `charges_paraview.py`, et `charges.pvsm` si livré ;
- `png/` : 16 vues iso, plus les vues en plan de Q et de HU ;
- `resultantes.csv` ;
- `LISEZMOI.txt` : 10 lignes maximum, pour ouvrir le tout sous Windows et
  changer de cas ;
- `empreintes.sha256`.

## Compte rendu attendu — EN FRANÇAIS, court

- Cause de l'absence de livrables ParaView au lot 50 (étape 0.1), et
  correctif apporté au tronc commun.
- Inventaire du MED (étape 0.2) et mode d'obtention (existant, régénéré sans
  résolution, ou réexécuté).
- Tableau des résultantes.
- Liste des fichiers déposés, avec leurs empreintes.
- `rex` et interventions.

## Interdits

- Aucune modification des résultats ni du `.comm` du lot 50 bis.
- Aucune modification des autres projets, en dehors du correctif du tronc
  commun et de son test.
- Aucun mot-clé Code_Aster sans source dans le catalogue ou la documentation
  17.4.
