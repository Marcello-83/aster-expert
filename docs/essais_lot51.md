# Essais du lot 51 — PONTONS-ALU-01 : palée complète, appuis néoprène, matrice de variantes

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot51_consigne.md`. Code_Aster 17.4.0
(image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). Calcul linéaire seulement ; niveau
visé : **D** (harnais d'équilibre et contrôles de cohérence), jamais plus. Aucune vérification
EC9, béton armé ou appareil d'appui (consigne, « Interdits »).

## Objet

Établir, pour chacune des douze variantes de `variantes_lot51.yaml` (R, E, T1, T2, A, P4, P4E,
N−, N+, M, S1, S3), un calcul linéaire des 68 cas élémentaires (22 cas de G, Q, houle et
températures, dont G2, Q, HU, HD découpés par travée, 30 cas unitaires d'accostage, 16 cas
unitaires d'amarrage), puis les enveloppes du jeu B′ révisé et de l'ELU accidentel.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | Fin d'exécution de chaque variante | `FIN` atteint, statut `completed_ok` ou `completed_with_alarms` | niveau C | — ; une variante qui s'arrête est rapportée avec son message (consigne § 2 : variante mécaniquement instable, jamais stabilisée artificiellement) |
| 2 | Équilibre de chaque cas, chaque variante exécutée (harnais D du tronc commun, `level_d_controls`) : charge appliquée + réactions des rotules du quai + réactions des pieds fixes en X = 14,02 + forces des ressorts de sol | 0 ; la charge appliquée vaut, pour un cas unitaire, 1 kN (amarrage) ou 1 kN/m × 1 m (accostage) dans la direction du cas, et pour les autres cas la valeur calculée par `generation_lot51.applied_loads` à partir des données et des paramètres | exacte (équilibre discret) | résidu ≤ 10⁻⁶ × charge appliquée ; cas thermiques autoéquilibrés : résidu ≤ 10⁻⁶ × Σ\|k·u\| des ressorts de sol |
| 3 | Somme des cas par travée : `G2_T1 + G2_PT + G2_T2` contre `G2`, de même Q, HU, HD, sur les déplacements de tous les nœuds (variante R) | égalité (linéarité) | exacte | écart ≤ 10⁻⁶ × max \|u\| du cas total |
| 4 | Efforts des appuis néoprène (variante R, tous les cas) : F = −K·(u_haut − u_bas) contre l'effort intérieur en tête du profilé support (EFGE_ELNO, ramené au repère global) | égalité (le nœud bas du ressort ne porte que le profilé et le ressort) | exacte | écart ≤ 10⁻⁶ × max \|F\| du cas |
| 5 | Enveloppes par décomposition (`combinaisons_lot51`, somme des maxima par action) contre l'énumération combinaison par combinaison de `recombiner.py` (bibliothèque standard) : max et min de MFY des poutres principales, N des piles, Fz des néoprènes, variante R, jeu B′ ELU fondamental et ELU accidentel | égalité | exacte | écart ≤ 10⁻⁹ en relatif |
| 6 | Effectif des combinaisons : formule de dénombrement contre énumération avec suppression des doublons (même règle que le lot 50 : jeux de coefficients identiques gardés une fois) | égalité | exacte | égalité stricte |

Toute autre issue est un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- Deux nœuds liés sont toujours distincts (invariant `no_coincident_nodes`) : la petite travée et
  les longrines s'arrêtent à 1 mm du nœud auquel elles sont liées ; le ressort de l'appui
  néoprène est une SEG2 de 1 mm, reliée au nœud de la poutre principale par un bras rigide
  (U2.02.03 : un discret ne transmet pas le moment d'un couple). Effet : 2 mm de tablier non
  chargés sur 14,02 m (0,014 %).
- Rotule en tête de pile : les trois translations transmises par un bras rigide de 0,20 m (tête
  de pile → axe de l'anneau), rotations libres ; encastrement : `LIAISON_SOLIDE`.
- Variante E (éclissages continus) : G2 par travée avec γG,sup = 1,2 ou γG,inf = 0,9
  indépendamment (G1 en bloc) ; Q, HU, HD : chaque travée chargée ou non. Autres variantes :
  cas totaux.
- Variante M et sensibilités N−, N+ : appliquées aux six appuis (quatre de la palée et deux en
  X = 14,02, palée suivante supposée de même conception).
- ELU accidentel (règle du projet, lot 50, D5) : G + A_d + ψ1·Q_dominante + Σ ψ2·Q_autres, la
  dominante pouvant être absente ; G + ACA sans autre événement AC, G + AMF sans autre
  événement AM.
