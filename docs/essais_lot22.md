# Lot 22 — Essais ciblés : `ELAS_COQUE`, pesanteur, ressorts nodaux

Trois essais d'exécution minimaux (`aster-expert run`), modèles entièrement
synthétiques, aucun fichier de MM lu ni copié. Code_Aster 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
HEAD au moment des exécutions : `b7ce267408c2cfa7a2b1719e2aeff93d13fb05b6`,
arbre modifié (les cas n'étaient pas encore commités : l'empreinte
`case_sha256` de chaque source d'exécution fixe les octets exacts du cas).

Chaîne suivie pour chaque cas : maillage écrit par `scripts/build_lot22_essais.py`
au format ASTER natif (déterministe, rejoué octet pour octet par un test) →
`aster-expert validate` (**niveau B : 14/14 ou 15/15 commandes vérifiées, 0
erreur** pour les 12 cas) → `aster-expert run` → `.mess` (`fort.6`) analysé,
copie versionnée sous `data/examples/lot22_essais/mess/`. **Alarmes : aucune** dans
les 12 `.mess` (liste de fin de calcul « aucune alarme », aucune balise `<A>`).

Les niveaux annoncés sont ceux de CLAUDE.md : **C** = exécuté jusqu'à `FIN`,
**D** = résultats soumis à un contrôle physique ou à une solution analytique
(comme au lot 21). Aucun essai n'atteint **E**.

## Essai A — convention de `ELAS_COQUE`

Bande console DKT, L = 2,00 m, b = 0,50 m, maillage 20 × 5 QUAD4, épaisseur
déclarée 0,01 m, matériau défini par `ELAS_COQUE` seul. `FLEX_L = 1000`,
`FLEX_T = 4000`, `FLEX_LT = 0` (pas d'effet anticlastique : la bande se comporte
comme des poutres en parallèle), membrane `MEMB_L = MEMB_T = 10⁷`,
`MEMB_LT = 3×10⁶`, `MEMB_G_LT = 3,5×10⁶`. Encastrement en x = 0, `FORCE_ARETE`
`FZ = -10` N/m sur l'arête de bout : P = 10 × 0,5 = 5 N. Référence :
flèche = P·L³/(3·FLEX·b).

**Incident de validation (niveau B).** Un premier fichier sans `CISA_L` ni
`CISA_T` a été refusé par `checkCommandSyntax` : « (`MEMB_LT`, `MEMB_T`,
`MEMB_G_LT`, `FLEX_L`, `FLEX_LT`, `FLEX_T`, `FLEX_G_LT`, `CISA_L`, `CISA_T`) must
be all defined ». Le schéma exposé ne portait pas cette règle (non établi au
lot 21) : le groupe est indissociable dès qu'un de ses membres est donné.
`CISA_L = CISA_T = 10¹⁰` ont été ajoutés (sans effet en DKT selon U4.43.01, non
testé ici). Deuxième incident, de mon fait : les segments de l'arête portaient des
noms `MA1…` déjà pris par les QUAD4 (`LIRE_MAILLAGE` : « le nom MA1 existe déjà »,
`<EXCEPTION> MODELISA7_10`) ; segments renommés `SG1…`.

| Cas | Orientation | Flèche en bout obtenue (m) | Référence (m) | Écart relatif |
|---|---|---|---|---|
| a1 | `ANGL_REP = (0, 0)` : L le long de la console | 0,02666666666627 | 40/1500 = 0,026666666666667 | −1,5×10⁻¹¹ |
| a2 | `VECTEUR = (0, 1, 0)` : T le long de la console | 0,00666666666669 | 40/6000 = 0,006666666666667 | +3,5×10⁻¹² |
| a3 | `ANGL_REP = (90, 0)` : T le long de la console | 0,00666666666669 | 0,006666666666667 | +3,5×10⁻¹² |

Rapport a1/a2 = 3,99999999993, contre FLEX_T/FLEX_L = 4 (−1,8×10⁻¹¹). Les
flèches sont uniformes sur la largeur (six nœuds identiques à 10⁻¹² près).

**Constat (niveau D).** Une rigidité `FLEX` est une rigidité par unité de largeur
de coque (N·m, unités SI cohérentes avec le maillage) ; L est l'axe x_l du repère
utilisateur ; `VECTEUR = (0,1,0)` et `ANGL_REP = (90, 0)` sont équivalents et
mettent T le long de X. Une unité par mètre absente donnerait un facteur 0,5, un
repère inversé un facteur 4 : ni l'un ni l'autre n'est observé. Non testés : les
termes de membrane et de couplage, COQUE_3D (qui n'accepte pas `ELAS_COQUE`
selon U2.02.01), TRIA3.

### Anomalie découverte : les réactions nodales sous `ELAS_COQUE`

La résultante DZ des réactions `REAC_NODA` à l'encastrement devait valoir 5 N
(équilibre). Elle ne vaut pas 5 N :

| Cas | Matériau | Flèche | Résultante `REAC_NODA` (N) | Écart à 5 N |
|---|---|---|---|---|
| a1 | `ELAS_COQUE`, membrane 10⁷, FLEX_L = 1000 | exacte | 0,416666666672 | −91,7 % |
| a2 | idem, T le long de la console | exacte | 0,1041666666671 | −97,9 % |
| a6 | membrane de a1, flexion isotrope 1000/1000 | exacte | 0,4166666666576 | −91,7 % |
| a4 | témoin `ELAS` (E = 1,2×10¹⁰, ν = 0 ; D = 1000) | exacte | 4,999999999892 | −2,2×10⁻¹¹ |
| a5 | `ELAS_COQUE` isotrope (membrane 1,2×10⁸, FLEX 1000) | exacte | 4,999999999892 | −2,2×10⁻¹¹ |
| a7 | membrane isotrope 1,2×10⁸, FLEX_L = 1000, FLEX_T = 4000 | exacte | 5,000000000062 | +1,2×10⁻¹¹ |

Les déplacements sont justes dans tous les cas ; seule la résultante dérive. La
valeur D_eff = MEMB × EPAIS²/12 = 10⁷ × 10⁻⁴/12 = 83,33 N·m reproduit exactement
le coefficient 15,625 = 3·D_eff·b/L³ qui lie résultante et flèche dans a1, a2 et
a6 ; a5 et a7 (où FLEX porté par la charge = MEMB × EPAIS²/12) sont exacts. **C'est
une déduction** compatible avec les six essais, pas un mécanisme établi : le
calcul de `REAC_NODA` semble reconstruire la rigidité de flexion à partir de la
membrane et de l'épaisseur. Portée : DKT, QUAD4, une charge de bord ; `FORC_NODA`,
`EFGE_ELNO`, COQUE_3D non testés. Conséquence : ne pas exploiter `REAC_NODA` avec
`ELAS_COQUE` sans contrôle d'équilibre.

## Essai B — pesanteur sur un modèle mixte `ELAS` / `ELAS_COQUE`

Deux plaques DKT carrées de 1 m, maillées 4 × 4, dans le même modèle
(`P1` : `ELAS`, E = 2,1×10¹¹, ν = 0,3, `RHO` = 7850 kg/m³, épaisseur 0,01 —
**témoin** ; `P2` : `ELAS_COQUE` par les formules isotropes de U4.43.01,
épaisseur **0,02**, différente de P1 pour distinguer masse surfacique et
volumique), `PESANTEUR` (g = 9,81, direction −Z), appuis sur les quatre coins.

| Cas | Variante | Exécution | Plaque 1 (N) | Plaque 2 (N) |
|---|---|---|---|---|
| b1 | P2 sans `RHO`, `PESANTEUR` sur tout le modèle | **échec** `<S>_ERROR`, `MODELISA9_77` | — | — |
| b4 | P2 sans `RHO`, `PESANTEUR` limitée à `GROUP_MA="P1"` | **échec** `<S>_ERROR`, `MODELISA9_77` | — | — |
| b2 | P2 avec `RHO` = 100 | `completed_ok`, aucune alarme | 770,085 | 19,62 |

Message des deux échecs (rapporté tel quel) : « Le paramètre 'RHO' doit être
fourni pour la maille 17 », option `CHAR_MECA_PESA_R`, type d'élément `MEDKQU4`,
maille 17 du groupe `P2`, puis `MODELISA6_4`. Les deux échecs sont de niveau
**B** seulement (syntaxe validée, exécution non aboutie) : ils ne sont pas des
sources d'exécution.

Résultante de la plaque 2 avec `RHO` = 100 et épaisseur 0,02, pour 1 m² :

| Hypothèse | Valeur attendue | Obtenu 19,62 |
|---|---|---|
| `RHO` × g × aire (masse surfacique, sens de U4.43.01) | 981 N | −98,0 % |
| `RHO` × épaisseur × g × aire (masse volumique) | **19,62 N** | **0** |
| zéro | 0 | non |

Témoin ELAS : 7850 × 0,01 × 9,81 = 770,085 N, obtenu 770,085 (écart 0).

**Contrôle indépendant des réactions (b3)**, à cause de l'anomalie ci-dessus :
console de l'essai A en `ELAS_COQUE` avec `RHO` = 1, épaisseur 0,01, sous
`PESANTEUR`, mesurée par le **déplacement**. Référence p·L⁴/(8·FLEX_L) avec
p = `RHO` × épaisseur × g = 0,0981 N/m² : 1,962×10⁻⁴ m ; obtenu 1,963635×10⁻⁴ m
(+0,083 %, discrétisation DKT). Sous l'hypothèse « masse surfacique » (p = 9,81)
la flèche serait 1,962×10⁻² m (−99 %).

**Constat (niveau D).** Sous `PESANTEUR` en statique, `ELAS_COQUE` reçoit le poids
`RHO` × `EPAIS` × g par unité de surface : `RHO` agit comme une masse **volumique**,
non comme la « masse par unité de surface » de U4.43.01 — la documentation est
contredite sur ce point. Une `RHO` de masse surfacique sous-estimerait le poids
d'un facteur égal à l'épaisseur.

**Réponse à la question du double compte.**

- Le modèle mixte accepte `PESANTEUR` **si tous ses éléments `ELAS_COQUE` portent
  `RHO`**, même quand `PESANTEUR` est restreinte par `GROUP_MA` à un autre
  groupe (b4). Sans `RHO`, l'exécution s'arrête (b1, b4).
- Avec `RHO` renseigné, `PESANTEUR` prend le poids propre de l'élément
  `ELAS_COQUE` en compte (b2, b3) : **la force surfacique explicite de la
  décision 2, si elle représente ce même poids, serait comptée deux fois**
  (déduction directe de b2/b3).
- Sans `RHO`, la force explicite serait la seule voie pour charger ce groupe, mais
  `PESANTEUR` étant alors impossible dans ce modèle, l'ensemble du poids propre
  (tube compris) devrait être appliqué par forces : cette configuration n'est
  pas testée. `RHO` nul n'est pas testé non plus. Le choix reste à l'ingénieur.

## Essai C — ressorts nodaux

Plaque DKT carrée de 1 m, maillée 4 × 4 (25 nœuds), appuyée sur des ressorts
`DIS_T` / `K_T_D_N` normaux, créés par `CREA_MAILLAGE` / `CREA_POI1`. Raideur
nodale = raideur surfacique (10⁶ N/m³) × aire tributaire : intérieur (9 nœuds)
62 500 N/m, bord (12) 31 250 N/m, coin (4) 15 625 N/m ; **trois** occurrences de
`CREA_POI1` et trois de `DISCRET`, un groupe `POI1` par classe et non par nœud.
`VALE = (0, 0, k)` (kx = ky = 0 accepté sans alarme). Pression uniforme
1000 Pa. Blocages dans le plan : A (DX, DY), B (DY). Forces des ressorts par
`CALC_CHAMP(GROUP_MA = groupes POI1, FORCE = "FORC_NODA")`.

| Grandeur | Obtenu | Référence | Écart relatif |
|---|---|---|---|
| DZ des 25 nœuds (valeur absolue) | 1,000000000000×10⁻³ m, identique aux 25 nœuds | p/ks = 10³/10⁶ = 10⁻³ m | 0 (12 chiffres) |
| résultante des forces nodales des ressorts (valeur absolue) | 1000,0 N (signe −) | p × aire = 1000 N | 0 |

Aucune alarme ; 25 mailles `POI1`, 25 éléments `DIS_T` créés.

**Constat (niveau D).** La chaîne `CREA_POI1` → `DIS_T` → `DISCRET` / `K_T_D_N` est
confirmée par exécution. Le constat du point 4 (niveau A au lot 21) passe au
niveau D. **Règle de regroupement pour le générateur :** les nœuds de même
raideur (mêmes valeurs de `VALE`) se regroupent dans un même groupe `POI1`, avec
une occurrence de `CREA_POI1` et une de `DISCRET` par classe de raideur, jamais
par nœud. La déduction (a) du lot 21 (« un groupe d'une seule maille par nœud »)
est corrigée : un groupe par nœud n'est nécessaire que si toutes les raideurs
diffèrent ; l'ancien texte est conservé dans les `notes` de l'entrée. Non
testé : maillage irrégulier (tolérance de comparaison de deux raideurs, à
définir et non établie), raideurs tangentielles, autre direction que la normale.
Sens observé : `PRES > 0` sur une plaque de normale +Z donne DZ < 0.

## Essai `FORCE_COQUE` du lot 21

Repris tel quel de `docs/essai_lot21_force_coque.md` : résultante 2,22982 N contre
la surface développée des facettes 2,229823082115976 m² (écart −1,4×10⁻⁶ à la
précision d'impression de 5 chiffres), contre 1,42 m² projetés (la résultante
la dépasse de 57 %). Niveau C, D pour cette question seulement. Enregistré au
point 8 avec la source d'exécution (HEAD de l'époque `28b1fe8…`, arbre modifié).

## Ce qui ne change pas dans la documentation du lot 21

`docs/etude_lot21_elas_coque.md` (niveau A) reste l'état documentaire du lot 21.
Trois points y étaient « non établis » ou déduits : l'unité de `ELAS_COQUE`, `RHO`
sous `PESANTEUR`, la chaîne de ressorts. Ils sont ici établis par exécution ; le
sens de `RHO` **contredit** le libellé de U4.43.01 rapporté au § 1 de cette étude.

## Limites

- Un seul maillage par cas, une seule modélisation (DKT, QUAD4), une seule
  version (17.4.0). Aucun essai sur COQUE_3D ni TRIA3.
- Résultats lus avec 12 chiffres (`FORMAT_R = E20.12`) ; l'exactitude de a1–a7 à
  10⁻¹¹ est celle du solveur direct sur des cas où la solution discrète est
  exacte (poutres en flexion pure) : elle ne dit rien de la précision de la
  discrétisation sur un cas général (b3 : +0,08 %).
- La cause de l'anomalie `REAC_NODA` sous `ELAS_COQUE` n'est pas isolée.
- Les alarmes analysées sont celles du `.mess` ; aucune extension du parseur
  n'a été écrite (CLAUDE.md, « ne pas réimplémenter »).
- Les exécutions ont eu lieu sur un arbre modifié (fichiers non commités) ; le
  commit du lot les contient, et l'empreinte de chaque cas est dans la fiche.
