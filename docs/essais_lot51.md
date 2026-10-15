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

## 3. Modèle et exécution (après le commit du critère, e169107)

- Maillages : `maillage/maillage_palee.py`, un pour H = 1,32 m (901 nœuds, 830 SEG2, 132 QUAD4)
  et un pour H = 4,0 m (941, 870, 132) ; `mesh check` 1 232/1 232 invariants tenus pour chacun.
- `.comm` : `generation_lot51.build_comm`, un par variante, régénérés octet pour octet par un
  test (`references/execution_lot51/<variante>/pontons_alu_01.comm`) ; niveau B **valide**,
  751/751 commandes confrontées pour chacune des douze variantes.
- Exécutions : `scripts/lot51.py executer` (six en parallèle, `ncpus` 1), image
  `simvia/code_aster:17.4.0` par digest. Répertoires : R `20261015T110339-767eaf49`, E
  `…110330-bc8444b9`, T1 `…110338-c669a5d5`, T2 `…110329-f03e0a12`, A `…110339-7254d74a`, P4
  `…110339-f66ff405`, P4E `…110413-4fc20c07`, N− `…110622-d01bcf9e`, N+ `…110630-c37ee584`, M
  `…110642-b94295ee`, S1 `…110650-91303668`, S3 `…110650-0cb89313`.

## 4. Résultats

| # | Résultat |
| --- | --- |
| 1 | 11 variantes `completed_ok`, 0 alarme. **A** : `<F> <FACTOR_11>`, « Degré de liberté physique associé au noeud 305 et à la composante DRX » ; nœud 305 = bout de la longrine L− (6,251 ; −0,75 ; 0,89). Classé DIAG-030 (mécanisme de torsion des longrines liées seulement en translation aux têtes de pile). |
| 2 | Harnais D `RÉUSSI` pour les 11 variantes calculées, 68 cas chacune ; résidu relatif maximal 1,14·10⁻¹¹ (P4E, ACN_PA2_YP), cas unitaires compris. |
| 3 | R : écart relatif maximal 6,1·10⁻¹³ (Q) entre le cas total et la somme de ses trois travées. |
| 4 | R : écart relatif maximal 3,0·10⁻¹² entre −K·Δu et l'effort lu en tête du profilé support. |
| 5 | R : 12 extrêmes (MFY des poutres principales, N des piles, Fz des néoprènes ; ELU fondamental et accidentel ; max et min) : écart relatif maximal 2,2·10⁻¹⁶ entre la décomposition et l'énumération de `recombiner.py`. Rejoué aussi depuis le partage par `python3 -I -S` : −53 782,930045686306 N·m dans les deux cas. |
| 6 | Effectifs : 276 235 combinaisons par variante (ELU fondamental 121 556, ELU accidentel 75 008, ELS caractéristique 60 778, ELS fréquent 18 458, ELS quasi permanent 435), 5 416 185 pour E (4 678 720 ; 357 824 ; 292 420 ; 85 220 ; 2 001) ; énumération de R : 276 235 jeux de coefficients, tous distincts. |

## 5. Verdict

| # | Verdict |
| --- | --- |
| 1 | RÉUSSI pour 11 variantes ; A non calculée, instabilité signalée comme la consigne le demande. |
| 2 | RÉUSSI (11 variantes). |
| 3 | RÉUSSI. |
| 4 | RÉUSSI. |
| 5 | RÉUSSI. |
| 6 | RÉUSSI (dénombrement par la formule égal à l'énumération pour R ; pour E, formule seule, l'énumération de 5,4 millions de jeux n'est pas faite). |

Niveau atteint : **D** pour les 11 variantes calculées ; aucun niveau E (aucune référence
extérieure).

## 6. Limites

- Les enveloppes des résultantes (V, Fxy, M des piles, déplacement horizontal relatif) sont
  le maximum sur 2 048 directions du plan : valeur par défaut, à 1,2·10⁻⁶ près au plus.
- Le critère 5 porte sur R ; les autres variantes emploient le même code.
- Les livrables locaux du lot 50 bis (`resultats/livrables`, non versionnés) ont été remplacés
  par ceux de R pour produire `charges.med` ; le test d'export du lot 50 ter les exige et est
  désormais ignoré avec son motif.
