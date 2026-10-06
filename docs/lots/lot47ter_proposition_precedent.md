# Lot 47 ter — précédent proposé à l'arbitrage de MM (non tranché)

**Statut : proposition de la session, à arbitrer par MM.** Ce n'est ni une règle ni une
décision. Le schéma de la couche `precedents` exige la décision de MM qui fonde un
précédent (`DecisionEvidence`). Ce texte n'y est donc pas versé. Si MM le tranche, il
deviendra PRE-039 avec sa décision, sa date et son domaine de validité. Il ne s'applique à
aucune fiche avant.

## Question

Pour une dalle modélisée en coque mince, couplée à des poutres POU_D_T qui partagent ses
nœuds (section en T dalle + chevêtre, appuis ponctuels sur les nœuds de la poutre) : faut-il
une plaque **DKT** (Kirchhoff, sans déformation d'effort tranchant) ou **DST** (déformable
à l'effort tranchant) ?

## Faits du plan factoriel (lot 47 ter, `docs/essais_lot47ter.md` § 6)

Estacade sur pieux, maillage de dalle de 0,05 m, quatre configurations {DKT, DST} ×
{chevêtre 0,90, 0,80 m}. Valeurs Code_Aster, contre-calcul d'un modèle non validé :

- **Partage de l'effort tranchant près du pieu.** La formulation de la dalle en décide.
  Maximum de |VZ| de la barre seule en 105 et 112 ELU : 198,1 kN en DKT, 660,8 kN en DST.
  Maximum du total |VZ + ∫QY dX| : 722,5 et 733,3 kN. L'effet principal de DST sur la barre
  seule vaut +234 %, contre +1,8 % sur le total.
- **Moments.** Ils dépendent à peine de la formulation : C6 barre seule vaut 443,1 kN·m
  dans les deux cas (ELU, chevêtre de 0,90 m), et l'effet de DST reste sous 0,5 % sur
  C2 à C6.
- **Globales et dalle loin des pieux.** C1, C2, C4, C10, C11, C12 « courant », C13 « inf. »
  varient de moins de 2 % entre DKT et DST.
- **Source.** Le modèle source publie l'effort de la barre. Sa valeur (653 kN) est
  retrouvée par la barre seule en DST (+1,2 % avec 0,90 m, −2,7 % avec 0,80 m), pas en DKT
  (−69,7 %) ni par le total (+10,6 à +12,3 %).

## Proposition

1. **Pour un calcul de dimensionnement** : l'une ou l'autre formulation, à condition de
   lire l'**effort de la section en T** (total barre + bande de dalle, CA-058). Ce total
   dépend peu de la formulation (+1,8 % sur C8). Un ferraillage de chevêtre établi sur la
   barre seule d'un modèle DKT sous-estime l'effort tranchant d'un facteur 3 à 4 près des
   appuis.
2. **Pour comparer à un calcul externe qui publie l'effort des barres** : DST, plus proche
   d'un modèle de plaque épaisse à cisaillement. C'est la convention probable des
   logiciels de bureau d'études ; c'est une déduction, la formulation de la source n'étant
   pas connue. Déclarer la variante comme telle, et rapporter aussi le total.
3. **Domaine** : dalle de 0,40 m sur chevêtre de 1,20 × 0,90 m (ou 0,80 m), appuis
   ponctuels, maillage de 0,05 m. La part de la barre en DKT dépend du maillage (CA-058,
   lot 47 : 88,9 → 36,9 kN de h = 0,10 à 0,025 m). Hors de ce domaine, non établi.

## Variantes écartées par la session

- « DKT toujours, la barre seule » : sous-estime l'effort tranchant du chevêtre près des
  pieux (27 % du total).
- « DST toujours, sans lire le total » : ne vaut que si la dalle porte peu d'effort
  tranchant ; ici, 10 % du total près du pieu.
