# Lot 51 quater — Pontons aluminium : houle « tablier noyé » et impact quasi statique (recombinaison seule), vues 3D, MED complets

**Tout en français. Profil `vm`. Branche `lot-51quater`, depuis `main` après
fusion de `lot-51ter`.** Consigne copiée dans `docs/lots/lot51quater_consigne.md`.

## Objet

La houle P56 suppose que le dessus du tablier reste sec alors que la crête le
dépasse d'environ 1,2 m. Pour un tablier de 2 m, ajouré et à tubes drainés,
c'est une borne non physique. Elle pilote :

- l'ancrage ;
- les flèches de l'ELS caractéristique ;
- My des poutres principales, par HD ;
- une partie du glissement aux axes.

MM a retenu le **modèle du tablier noyé**, complété d'un **impact traité en
quasi statique**. Une étude dynamique pourra venir plus tard dans un lot
dédié.

**Aucune réexécution de Code_Aster pour les résultats.** Les 221 cas
unitaires du lot 51 ter suffisent. Les cas houle découpés par module (`_Mk`)
existent. Seuls les événements et les recombinaisons changent. Code_Aster
n'est relancé que pour écrire les MED de résultats (§ MED), et dans ce cas
avec le `.comm` du lot 51 ter, inchangé (empreinte à vérifier).

Ni EC9, ni béton armé, ni vérification d'appui dans le lot.

## Décisions à enregistrer (MM, 16/10/2026)

**P60 — Houle « tablier noyé », P56 révisée.** Les cas unitaires et les règles
de combinaison de P56 sont conservés. Seuls les coefficients changent.

Principe : quand la crête dépasse le dessus du platelage (+1,445), la pression
s'équilibre de part et d'autre des surfaces. La sous-pression quasi statique
nette est bornée par la hauteur immergée de chaque surface jusqu'au dessus du
platelage, soit ρg × (1,445 − z_sous-face), avec ρg = 10,05 kN/m³. Elle est
majorée d'un facteur 2 pour le retard de remplissage.

| Événement | HU_TUBES | HU_PANNES | HU_PLATELAGE | HD_TABLIER |
|---|---|---|---|---|
| HU (caractéristique), variantes 10 (pannes 50 × 50, sous-face +1,35) | 4,92 | 1,91 | 0,90 | — |
| HU (caractéristique), variantes 12 (pannes 60 × 60, sous-face +1,34) | 4,92 | 2,11 | 0,90 | — |
| HD (caractéristique) : retard de vidange, 0,10 m d'eau sur le platelage | — | — | — | 1,01 |
| HU_F (fréquent) : inchangé, la crête fréquente +1,435 reste sous le dessus | 2,36 | 0,85 | 0,35 | — |

HU et HD restent appliqués sur toute la longueur, en phase.

**P61 — Impact quasi statique.** Pression d'impact à l'entrée de l'eau sous
les surfaces :

p_imp = DAF × ½ ρ Cs w² = 1,5 × 0,5 × 1,025 × 2π × 1,1² ≈ **5,9 kPa**

Hypothèses du superviseur, à citer telles quelles :

- w = 1,1 m/s : vitesse verticale de la surface libre au niveau de la
  sous-face. C'est 2 × πHmax/T, avec Hmax = 2,03 m et T = 11,5 s, pour le
  front raide d'une houle en faible profondeur.
- Cs = 2π.
- DAF = 1,5 : durée d'impact de l'ordre de la période propre d'une travée.

L'impact est **local** : un module à la fois. Six événements exclusifs
HU_IMP_Mk, avec k = 0 à 5. Chacun est la somme, sur le seul module Mk, de :

5,9 × (HU_TUBES_Mk + HU_PANNES_Mk + HU_PLATELAGE_Mk)

Règles :

- HU_IMP_Mk et HU sont **alternatifs** dans l'emplacement de la houle :
  l'impact précède l'immersion.
- Mêmes facteurs que HU à l'ELU fondamental et à l'ELS caractéristique.
- Pas d'impact à l'ELU accidentel, à l'ELS fréquent ni à l'ELS quasi
  permanent.
- P57 s'applique : jamais avec AC ou ACA.

**Sensibilité, sans décision (forfait AVP de 5 kPa).** L'événement HU_S5 vaut
5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE), sur toute la longueur. Il est
évalué **uniquement** pour `ancrage.csv` et `palee_equilibre.csv`, dans une
colonne à part. Il n'entre dans aucune autre enveloppe.

## Variantes

A10, A12, B10, B12 : celles du lot 51 ter, sans changement de géométrie.

## Recombinaison : efficacité

- Enveloppe des grandeurs scalaires : décomposition par emplacement (méthode
  validée au lot 51 ter). Ne pas énumérer.
- Énumération complète une seule fois, pour contrôle, sur B10 et 36 extrêmes
  tirés au sort.
- Donner le temps de recombinaison par variante.

## Exports

**Mêmes fichiers qu'au lot 51 ter, recalculés.** Ajouter dans
`ancrage.csv` :

- la colonne de sensibilité HU_S5 ;
- l'identifiant de l'événement de houle gouvernant (HU, HU_IMP_Mk ou aucun).

**`efforts_elementaires.npz`** (numpy `savez_compressed`, float32), par
variante, en remplacement du CSV de 188 Mo pour la transmission :

- tableaux `cas`, `elements`, `noeuds` et `composantes` (N, VY, VZ, MT, MFY,
  MFZ) ;
- tableau `efforts` [cas, élément-nœud, composante], en N et N·m ;
- toutes les barres : aluminium, piles et anneau.

Garder aussi le CSV, mais ne le déposer qu'une seule fois, pour B10. Objectif :
moins de 60 Mo par fichier `.npz`. Donner la taille obtenue.

**`comparaison_variantes.csv`** : colonnes du lot 51 ter, plus :

- ancrage par palée selon P60, P61 et HU_S5 ;
- événement de houle gouvernant pour PP My, pour la flèche de l'ELS c et pour
  l'ancrage.

## Vues 3D en PNG (aucune depuis longtemps)

Variantes B10 et B12. Profilés **en volume**, pas en filaire :

- tubes en caissons creux ;
- pannes ;
- montants et diagonales à leur section ;
- piles en cylindres Ø 0,50 ;
- anneau, semelles 2,60 × 2,60 × 0,20 et axes d'appui.

Outil : ParaView de salome_meca en mode hors écran, ou pyvista, à préciser.
Couleur par famille, avec légende. Format PNG d'au moins 1 920 × 1 080, avec
le titre, la variante et l'échelle.

Vues :

1. Ponton entier, vue iso côté mer.
2. Ponton entier, vue iso côté port.
3. Culée et T1, zoom.
4. Palée P1 et ses deux lignes d'appui, zoom : chevêtre, longrines, piles,
   axes.
5. P5, PT5 et porte-à-faux, zoom.
6. Coupe transversale sur palée, avec les cotes NGF des éléments (P53).
7. Déformées de 4 combinaisons, avec le facteur d'amplification et le
   déplacement maximal en mm indiqués :
   - PP My extrême ;
   - flèche de l'ELS fréquent ;
   - ΣRX de la culée ;
   - impact HU_IMP_M0.

Script : `scripts/vues_3d_pontons.py`, paramétré par la variante, et déposé.

## MED et scripts Salome (structure entière)

Pour B10 et B12, dans `MED/` :

- **`structure.med`** : maillage complet, avec les groupes de la consigne
  (familles, travées, palées, axes).
- **`charges.med`** : les cas unitaires et les événements de houle P60 et
  P61, en champs nodaux de forces. Même principe qu'au lot 50 quinquies.
- **`resultats.med`** : pour les 4 combinaisons de la vue 7 et pour les
  enveloppes ELU de N, My et Mz par élément :
  - champs DEPL (pour la déformée) ;
  - champs EFGE_ELNO.

  Pour ces champs uniquement, relancer le `.comm` du lot 51 ter, inchangé,
  et combiner les résultats unitaires avec les coefficients de ces
  combinaisons. Commande de combinaison choisie dans le catalogue de la
  version installée et citée ; aucun mot-clé de mémoire. Si l'écriture
  directe en Python (medcoupling) est plus sûre, la préférer et le dire.
- **`afficher_pontons_salome.py`** : un script qui charge les trois MED dans
  le module ParaVis, avec :
  - charges en flèches, mises à l'échelle cas par cas (retour du lot 50
    quater) ;
  - déformée par `warp_by_vector`, facteur réglable ;
  - colorisation par famille ou par composante d'effort.

  En tête du script, un mode d'emploi de 10 lignes au plus.

Contrôle : ouvrir chaque MED par relecture (`LIRE_RESU` ou medcoupling) et
vérifier le nombre de nœuds, de mailles et de groupes.

## Contrôles

- Résultantes des événements :
  - HU sur la longueur totale = (4,92 × 0,40 + 1,91 × 0,20 + 0,90 × 1,327) ×
    L, à 10⁻⁶ près (variantes 10) ;
  - pour chaque HU_IMP_Mk = 5,9 × 1,927 × longueur du module, à la largeur
    réelle des surfaces près.
- Identité avec le lot 51 ter :
  - les combinaisons sans houle donnent des valeurs identiques ;
  - avec les coefficients P56, la recombinaison retrouve exactement
    `comparaison_variantes.csv` du lot 51 ter.
- Lecture des `.npz` par un script indépendant : un effort tiré au sort,
  comparé au CSV.
- Pour chaque PNG : fichier non vide, aux dimensions attendues. En vérifier
  au moins deux à l'œil (dire lesquels).

## Dépôt

`/media/sf_partage/echanges/lot51quater/pontons_alu_01/` :

- `<variante>/` : exports et `efforts_elementaires.npz` ;
- `B10/efforts_elementaires.csv` ;
- `comparaison_variantes.csv` ;
- `vues/` : PNG, avec le nom de la variante et de la vue dans le nom de
  fichier ;
- `B10/MED/`, `B12/MED/` ;
- `scripts/` : `vues_3d_pontons.py` et `afficher_pontons_salome.py` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P60 et P61.
- Contrôle d'identité avec le lot 51 ter.
- Tableau de comparaison, avec une phrase par variante.
- Ancrage par palée : P60/P61, et sensibilité HU_S5.
- Événement de houle gouvernant pour chaque grandeur.
- Temps de recombinaison.
- Taille des `.npz`.
- Liste des PNG et des MED.
- `rex` et interventions.

## Interdits

- Aucun nouveau cas unitaire, aucune modification du `.comm` ni du maillage.
- Aucune vérification EC9, béton armé ou appareil d'appui.
- Aucun ancrage modélisé.
- Aucune modification des autres projets.
