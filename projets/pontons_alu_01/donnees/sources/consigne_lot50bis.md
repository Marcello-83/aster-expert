# Lot 50 bis — Pontons aluminium : géométrie transversale, appuis côté quai, inertie nécessaire

**Tout en français. Profil `vm`. Branche `lot-50bis`, depuis `main` après
fusion de `lot-50`.** Consigne copiée dans `docs/lots/lot50bis_consigne.md`.

**Lot court.** Il reste sous les règles d'économie du lot 50 :

- pas de contrôles à outrance ;
- tests ciblés pendant le travail, batterie complète à la fin seulement ;
- **pas d'images ParaView ni de nouvelle feuille de classeur** : les livrables
  sont des CSV et un compte rendu court ;
- rien sur les autres projets.

## 1. Décisions de MM (à enregistrer : P24 à P28)

- **P24. Géométrie transversale corrigée par MM** (remplace la largeur de
  P2 ; tout le reste de P2 est conservé).
  - Le tablier fait **2,00 m** de large, poutres principales en rive.
  - Les **0,27 m** restants de la coupe PRO (2,27 m) correspondent aux
    défenses fixes, accrochées le long des poutres principales (environ
    0,135 m de chaque côté).
  - **Entraxe des poutres principales B = 1,86 m** : axes à Y = ±0,93, soit
    2,00/2 moins la demi-largeur du MP1200 (0,07 m). Les poteaux restent à
    Y = ±0,75 (entraxe de 1,50 m, Ø 0,50 m).
  - **Pannes secondaires** : Y = +0,56 ; +0,19 ; −0,18 ; −0,55, comme dans
    S2. L'espacement devient régulier, environ 0,37 m, entre les poutres et
    les pannes.
  - **Montants** de Y = −0,93 à +0,93. Diagonales recalculées avec les mêmes
    abscisses et le même sens.
  - **Profilés supports** à Y = −0,93 ; 0 ; +0,93.
  - **Chevêtre allongé** à Y ∈ [−1,05 ; +1,05] (proposition du superviseur,
    à confirmer par MM). Avec ±1,00, le support de rive serait à 7 cm du
    bout, ce qui est trop court pour une platine.
  - **Rotules côté quai** à Y = ±0,93.
  - **Largeur chargée** : 2,00 m (G2, Q, houle), répartie par largeurs
    d'influence sur les poutres et les pannes (P22). Le poids des défenses,
    non communiqué, est négligé et c'est écrit. L'accostage et l'amarrage
    restent appliqués sur la poutre de rive (P13).
  - C'est une modification des paramètres de `maillage_pontons.py`, sans code
    nouveau.
- **P25. Appuis côté quai.**
  - Rotule en Y = +0,93 : translations bloquées en X, Y et Z.
  - Rotule en Y = −0,93 : bloquée en X et Z, **libre en Y** (guidée
    transversalement).
  - La solution technologique réelle est à définir par MM.
  - Ce choix supprime le bridage du montant de rive sous la température
    (−301 kN au lot 50).
- **P26. Pannes secondaires soudées aux montants et aux diagonales** :
  confirmation de P7, sans changement.
- **P27. Variante de combinaison B′.** C'est le jeu B, avec **Q et la houle
  rendus non concomitants**. On ne compte pas une foule de 5 kPa pendant une
  houle qui submerge le tablier. Elle s'obtient en post-traitement seulement,
  et c'est une décision à proposer à MM, qui tranchera.
- **P28. Taux élastique simplifié** (§3). C'est un indicateur de
  dimensionnement, pas une vérification EC9.

## 2. Exécutions

- **Une exécution de référence** : P24 et P25, MP1200, avec un maillage
  régénéré par le script.
- **Balayage de l'inertie des poutres principales**, en deux exécutions de
  plus.
  - Iy est multiplié par k = 3 et k = 5.
  - A et Iz restent ceux du MP1200 : seule la raideur de flexion verticale
    varie.
  - Le tablier est presque isostatique : les moments varient peu avec k,
    seule la flèche suit 1/k. Le balayage le confirme ou le dément.
- Le `.comm` reste à plat, comme au lot 50. Entre les exécutions du
  balayage, seul le paramètre de section change.
- Harnais D par défaut. Contrôle à la main repris du lot 50 : M total à
  mi-portée sous Q, avec b = 2,00 m. Rien d'autre.

## 3. Taux élastique simplifié (P28), toutes familles d'aluminium

Pour chaque élément et chaque combinaison ELU des jeux B et B′, avec les
efforts aux deux extrémités (ELNO) :

- σ = |N|/A + |My|/Wel,y + |Mz|/Wel,z, comparé à f0/γM1 ;
- τ ≈ √(Vy² + Vz²)/Av, comparé à f0/(√3·γM1) ;
- aux extrémités soudées (P6), la même comparaison avec f0,haz à la place de
  f0. C'est une borne : la zone affectée thermiquement ne couvre qu'une
  longueur limitée.

Valeurs à utiliser (EC9, tableau 3.2b, et note d'hypothèses AVP), γM1 = 1,10 :

| Famille | Alliage | f0 (MPa) | f0,haz (MPa) |
|---|---|---|---|
| Poutres principales MP1200 | 6005A-T6, profil ouvert | 215 (5 < t ≤ 10 ; 225 si toutes les parois t ≤ 5) | 115 |
| Montants, diagonales, profilés supports, tube 150 × 150 × 7 | 6082-T6 | 260 (tube filé, 5 < t ≤ 15) | 125 |
| Pannes, tube 50 × 50 × 5 | 6082-T6 | 250 (t ≤ 5) | 125 |

**Avertissement à écrire en tête du CSV.** Ce taux ne vérifie ni la classe de
section, ni le flambement, ni le déversement, ni les assemblages.
L'EC9 viendra plus tard.

## 4. Livrables (CSV et compte rendu, dépôt dans `.../echanges/lot50bis/pontons_alu_01/`)

1. **Synthèse par famille**, à l'ELU des jeux B et B′ et à l'ELS
   caractéristique : N, My, Mz, V et le taux simplifié maximal, avec le lieu
   et la combinaison. Le compte rendu donne en clair :
   - les **profilés supports** : efforts, taux et réaction transmise au
     chevêtre ;
   - les **pannes** : effort normal maximal et taux ;
   - les **rotules côté quai** : réactions avec P25.
2. **Tableau d'inertie** pour k = 1, 3 et 5 :
   - flèche UZ à l'ELS caractéristique, au total et sous les actions
     variables seules ;
   - My maximal d'une poutre principale à l'ELU (jeux B et B′).
3. **Inertie et module nécessaires**, interpolés sur le tableau et rapportés
   à une seule poutre principale :
   - I nécessaire pour une flèche sous actions variables de L/200, L/250 et
     L/300 ;
   - Wel nécessaire pour un taux simplifié de 1,0, en partie courante (f0) et
     dans la zone affectée thermiquement (f0,haz).
4. **Chevêtre** : mise à jour des CSV de flexion composée pour P24 et P25.

## Compte rendu attendu — EN FRANÇAIS, court

Il comprend :

- les décisions P24 à P28 ;
- l'effet de P24 et de P25 sur les efforts, par rapport au lot 50 ;
- les points 1 à 4 des livrables ;
- les contrôles, `rex` et les interventions.

## Interdits

- Aucun mot-clé Code_Aster de mémoire.
- Le taux simplifié ne doit être présenté nulle part comme une vérification
  EC9.
- Aucune modification des autres projets.
