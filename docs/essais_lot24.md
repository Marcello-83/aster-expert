# Lot 24 — Essai D6 : efforts généralisés complets sous `ELAS_COQUE`

Essais d'exécution synthétiques (`aster-expert run`), aucun fichier de MM lu.
Code_Aster 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
HEAD au moment des exécutions : `f5ede57` (arbre modifié : les cas n'étaient pas
commités ; `case_sha256` de chaque source fixe leurs octets). Cas produits par
`scripts/build_lot24_essais.py`, résultats extraits des `.mess` versionnés
(`data/examples/lot24_essais/mess/`) par `scripts/analyze_lot24_essais.py` →
`analyse.json`.

Chaîne : validation B (`aster-expert validate`, 22/22 commandes, 0 erreur, pour les
quatre cas) → exécution (statut `completed_ok`) → `.mess`. **Aucune alarme** dans
les quatre `.mess`. Niveaux : C = exécuté jusqu'à `FIN`, D = comparé à une solution
analytique. Aucun essai n'atteint E.

Plaque carrée de 1 m, quadrangles DKT 8 × 8, coefficients du tableau de la
décision 2 v5 en unités SI (1 MN = 1e6 N), `EPAIS` = 13,85 mm, `RHO` = 7 850 ;
L = axe Y du maillage, T = axe X (`ANGL_REP = (90, 0)`, orientation établie au lot
22). La plaque est dans le plan XY du maillage : le plan vertical de la palplanche
réelle n'est pas reproduit (voir limites).

## Résultats

| Cas | Grandeur | Obtenu | Référence | Écart relatif | Niveau |
|---|---|---|---|---|---|
| D6a traction T, q = 100 N/m | allongement du bord chargé (m) | 1,2345679012408e-3 | q·a/MEMB_T = 1,2345679012346e-3 | 5e-12 | D |
| | NYY, EFGE_NOEU (N/m) | 100,00000000049 | 100 | 5e-12 | D |
| | autres composantes | ≤ 1e-7 | 0 | — | D |
| | résultante REAC_NODA en X, bord x = 0 (N) | −100,0000000008 | −100 | 8e-12 | D |
| D6b flexion cyl. T, p = 100 Pa | flèche à mi-portée (m), 8 × 8 | 1,13788255953e-4 | 5pa⁴/(384 FLEX_T) = 1,15228613569e-4 | −1,25 % | D |
| | flèche à mi-portée (m), 16 × 16 | 1,14868524281e-4 | idem | −0,3125 % | D |
| | MYY à mi-portée (N·m/m) | 12,500000006 | pa²/8 = 12,5 | 5e-10 | D |
| | MYY, écart max sur tous les nœuds | 7,2e-9 | 0 | — | D |
| | QY en x = a/4 (N/m) | 25,00000001356 | 25 | 5e-10 | D |
| | QY aux nœuds d'appui (N/m), 8 × 8 | 43,75000002313 | pa/2 = 50 | −12,5 % | D |
| | QY aux nœuds d'appui (N/m), 16 × 16 | 46,87500006827 | 50 | −6,25 % | D |
| | REAC_NODA en Z, bord d'appui x = 0 (N), 8 × 8 | 6,255013060359 | 50 | −87,49 % | D |
| | REAC_NODA en Z, bord d'appui x = 0 (N), 16 × 16 | 3,130371136104 | 50 | −93,74 % | D |
| | Σ REAC_NODA en Z, tous nœuds (N) | 100,0 | pa² = 100 | 0 | D |
| D6c cisaillement pur, τ = 1e5 N/m | DX du bord supérieur (m) | 1,9011406844114e-4 | τa/MEMB_G_LT = 1,9011406844106e-4 | 4e-13 | D |
| | DX − γ·y, écart max ; DY max | 2e-16 ; 1,6e-17 | 0 | — | D |
| | \|NXY\|, EFGE_NOEU (N/m) | 100000,0 | 1e5 | 0 | D |
| | résultantes REAC_NODA (tous groupes) | ≤ 3e-10 | 0 (auto-équilibré) | — | D |

## Lecture

- **Membrane et cisaillement (D6a, D6c)** : déplacements, efforts généralisés
  et réactions exacts. La membrane selon T porte bien sur `MEMB_T`, le cisaillement
  de membrane sur `MEMB_G_LT` (`N_xy = MEMB_G_LT·γ`, γ distorsion d'ingénieur).
- **Flexion (D6b)** : `MYY` exact en tous les nœuds ; `QY` exact aux nœuds intérieurs ;
  la flèche s'écarte de −1,25 % et `QY` d'appui de −12,5 %. Ces deux écarts sont
  de discrétisation : le raffinement 8 → 16 divise l'écart de flèche par 4
  (−0,3125 %) et celui de `QY` par 2 (−6,25 %). `QY` d'appui est la valeur constante
  de l'élément adjacent (43,75 = p·(a/2 − h/2)), la moyenne de deux éléments donnant
  la valeur exacte aux nœuds intérieurs. Le refus de qualifier ces écarts d'erreur de
  coefficient repose sur ce raffinement, non sur une lecture de code.
- **Réactions** : exactes en membrane. En flexion, la résultante du bord d'appui
  (6,255 N ; 3,130 N en 16 × 16) n'est pas la réaction (50 N) : elle vaut, à 0,08 % et
  0,17 % près, la part nodale de la pression sur le bord (p·a·h/2 = 6,25 puis 3,125 N)
  — déduction : la réaction n'en contiendrait que le terme de charge. Le rapport
  FLEX_T/(MEMB_T·EPAIS²/12) vaut 8 727 ici. La somme sur tous les nœuds (100 N) est
  exacte et ne discrimine rien, comme au lot 23.
- **Signes** : NYY > 0 en traction ; MYY < 0 et DZ < 0 sous `PRES_REP` positive ; NXY < 0
  pour une force +X sur le bord y = a (déduction : repère local x_l = Y, y_l = −X).

## Limites

Non testés : `MEMB_L` seule et `QX` (la flexion selon L est celle du lot 23), la
torsion (`FLEX_G_LT`, `MXY` : la flexion cylindrique n'en produit pas — la décision
2 v5 range pourtant la torsion parmi les composantes de ce lot), les couplages
`MEMB_LT`/`FLEX_LT` (nuls), la superposition des sollicitations, un plan de plaque
autre que XY (convention `ANGL_REP` pour un plan vertical non établie), TRIA3, DST,
COQUE_3D, un maillage irrégulier. Les cas de membrane imposent DZ, DRX, DRY, DRZ nuls
sur tous les nœuds. Un seul maillage (8 × 8 ; 16 × 16 pour D6b). Aucune référence
externe (niveau E).
