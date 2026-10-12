# Essais du lot 50 bis — PONTONS-ALU-01 : géométrie transversale, appuis côté quai, inertie nécessaire

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot50bis_consigne.md`. Décisions P24 à P28 de
MM dans la fiche (`donnees/sources/enregistrement_P24_P28_lot50bis.md`). Lot court, sous les règles
d'économie du lot 50 : harnais D par défaut et un seul contrôle à la main.

## 1. Modèle (avant exécution)

- P24 : paramètres de `maillage_pontons.py` seulement — B = 1,86 m (poutres principales à
  Y = ±0,93), `LARGEUR_TABLIER` = 2,00 m (nouveau paramètre, lu par `geometrie.influence_widths`),
  profilés supports à Y = −0,93 ; 0 ; +0,93, chevêtre de Y = −1,05 à +1,05. Les montants vont de
  Y = −0,93 à +0,93 et les diagonales sont recalculées par le script (mêmes abscisses, même sens).
  Comptages calculés avant l'exécution par `pontons_alu_01.geometrie` : 416 nœuds, 384 SEG2,
  72 QUAD4 ; 97 groupes.
- Largeurs d'influence (P22, P24) : PP_YM 0,260 ; PANNE_4 0,375 ; PANNE_3 0,370 ; PANNE_2 0,370 ;
  PANNE_1 0,370 ; PP_YP 0,255 m, Σ b = 2,000 m (Q½ : 1,000 m). La charge de la bande de rive,
  de 0,07 m au-delà de l'axe de la poutre, est appliquée sur l'axe : son excentricité (torsion
  de la poutre) est négligée. Le poids des défenses, non communiqué, est négligé.
- P25 : deux groupes de nœuds `APP_QUAI_YP` (DX, DY, DZ bloqués) et `APP_QUAI_YM` (DX, DZ
  bloqués, DY libre) ; `APP_QUAI` reste le groupe des deux rotules pour le harnais et les
  livrables.
- Balayage (P24 et P25 identiques) : IY des poutres principales multiplié par k = 3 et k = 5
  (variable `PONTONS_K_IY` lue par le générateur ; A, IZ, AY, AZ, JX inchangés). Entre deux
  exécutions du balayage, seule la valeur de IY change dans le `.comm`, plus une ligne de
  commentaire qui la rappelle.

## 2. Critère du contrôle à la main (écrit avant l'exécution)

Repris du lot 50 (§ 2.2 de `docs/essais_lot50.md`), avec b = 2,00 m (P24) :

q·b·L²/8 = 5 000 × 2,00 × 6,25² / 8 = **48 828 N·m**.

Même lecture qu'au lot 50 : coupe X = L/2 = 3,125 m à travers toutes les barres longitudinales
et la diagonale coupée, torseur interpolé dans l'élément traversé (EFGE_ELNO du cas Q) et
ramené à l'axe Y global, bras de levier des efforts normaux par rapport au plan moyen des poutres
principales. Critère : |M − 48 828| ≤ 10 % de 48 828. Au-delà, l'écart est expliqué, et c'est un
échec.

Le harnais D par défaut (équilibre de chacun des 16 cas, CTL-013) s'applique sans changement.
Aucun autre contrôle n'est fait (consigne).

## 3. Balayage de l'inertie (rapporté, sans critère)

Hypothèse de la consigne : le tablier est presque isostatique, donc les moments varient peu
avec k et la flèche suit 1/k. Le balayage la confirme ou l'infirme ; ce n'est pas un critère.
Méthode d'interpolation, fixée avant les résultats : la flèche relative d'une poutre principale
(UZ moins la corde entre ses appuis X = 0 et X = L, ce qui retire le tassement de la semelle, qui
ne dépend pas de k) est ajustée par f(k) = a + b/k sur les trois points (moindres carrés) ;
l'inertie nécessaire est k·IY du MP1200, où k résout f(k) = L/200, L/250 et L/300. Le résidu de
l'ajustement est rapporté.

## 4. Taux élastique simplifié (P28)

Indicateur de dimensionnement, **pas une vérification EC9** : ni classe de section, ni
flambement, ni déversement, ni assemblages. Pour chaque extrémité d'élément (EFGE_ELNO) et
chaque combinaison ELU (fondamentale et accidentelle) des jeux B et B′ :
σ = |N|/A + |MFY|/Wel,y + |MFZ|/Wel,z rapporté à f0/γM1, τ = √(VY² + VZ²)/Av rapporté à
f0/(√3·γM1) ; aux extrémités soudées, les mêmes rapports avec f0,haz (borne : la zone affectée
thermiquement ne couvre qu'une longueur limitée). Hypothèses de l'outil, à confirmer par MM :

- MP1200 : Wel,y = 218 166 mm³, Wel,z = 145 794 mm³ (D3) ; Av = Avz = 17,41 cm² pour les deux
  directions (Avy non donné, même hypothèse que AY = AZ du `.comm`).
- Tubes carrés à angles vifs : Wel = I/(h/2) avec I = (h⁴ − (h − 2t)⁴)/12 ; Av = A/2 (les deux
  parois parallèles à l'effort tranchant).
- Extrémité soudée : nœud commun à deux barres d'aluminium ou plus, nœud d'une liaison rigide
  (pannes, tête des profilés supports) et pied des profilés supports (platine supposée soudée
  au tube).

## 5. Résultats

(Complété après les exécutions.)
