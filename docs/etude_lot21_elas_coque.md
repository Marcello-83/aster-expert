# Lot 21 — `ELAS_COQUE` : opérandes et conventions (Code_Aster 17.4.0)

Étude documentaire, niveau A (ni exécutée, ni confrontée à un fichier). Version :
17.4.0, image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`,
catalogue `b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca`.
Les documents ont été lus par `search_codeaster_docs` (profils `syntaxe` et
`methode`) puis `get_document_section`. Deux lectures directes, hors outils MCP,
sont déclarées : `external/codeaster-src/astest/ssls502a.comm` (question 6, les
fichiers `.comm` des cas tests ne sont pas indexés : trois requêtes sans résultat)
et, à l'étape 3, quelques `.comm` de cas tests. Les faits (F), déductions (D) et
« non établi » (NE) sont distingués.

## 1. Liste des opérandes (catalogue `DEFI_MATERIAU/ELAS_COQUE`)

45 opérandes, tous de type réel, **tous `optional` au catalogue** (un opérande
caché, `ORDRE_PARAM`, n'est pas listé). Le schéma exposé par l'outil ne porte
aucune règle d'exclusion ni de regroupement (`condition` vide) ; la syntaxe U4.43.01
(Syntaxe.rst, lignes 160-206) les note ainsi : `◇ / MEMB_L / M_LLLL` (exclusifs),
puis deux groupes `&` (`MEMB_LT` … `CISA_T`, puis `M_LLTT` … `C_TZTZ`) dont les
membres sont notés `◆`. Les règles exactes de combinaison ne sont donc **pas
établies par le schéma** (NE) ; la notation U4 est rapportée telle quelle. Une
variante `ELAS_COQUE_FO` (fonction / formule / nappe) existe avec les mêmes noms.

| Groupe | Opérandes | Signification (matrice de U4.43.01) | Statut |
|---|---|---|---|
| Membrane sans couplage | `MEMB_L`, `MEMB_LT`, `MEMB_T`, `MEMB_G_LT` | C1111, C1122, C2222, C1212 (D, voir Q2) | optionnels au catalogue |
| Flexion sans couplage | `FLEX_L`, `FLEX_LT`, `FLEX_T`, `FLEX_G_LT` | D1111, D1122, D2222, D1212 (D) | optionnels |
| Cisaillement transverse | `CISA_L`, `CISA_T` | G11, G22 | optionnels ; DST seulement |
| Couplage : membrane | `M_LLLL`, `M_LLTT`, `M_LLLT`, `M_TTTT`, `M_TTLT`, `M_LTLT` | HM (H1111 … H1212), 6 termes (D : L=1, T=2) | optionnels |
| Couplage : flexion | `F_LLLL`, `F_LLTT`, `F_LLLT`, `F_TTTT`, `F_TTLT`, `F_LTLT` | HF (A…), 6 termes (D) | optionnels |
| Couplage : membrane-flexion | `MF_LLLL`, `MF_LLTT`, `MF_LLLT`, `MF_TTTT`, `MF_TTLT`, `MF_LTLT` | HMF (B…), 6 termes (D) | optionnels |
| Couplage : membrane-cisaillement | `MC_LLLZ`, `MC_LLTZ`, `MC_TTLZ`, `MC_TTTZ`, `MC_LTLZ`, `MC_LTTZ` | HMC (E1113 … E1223), 6 termes (D : Z=3) | optionnels |
| Couplage : flexion-cisaillement | `FC_LLLZ`, `FC_LLTZ`, `FC_TTLZ`, `FC_TTTZ`, `FC_LTLZ`, `FC_LTTZ` | HFC (F1113 … F1223), 6 termes (D) | optionnels |
| Couplage : cisaillement | `C_LZLZ`, `C_LZTZ`, `C_TZTZ` | HC (G1313, G1323, G2323), 3 termes (D) | optionnels |
| Autres | `RHO`, `ALPHA` | masse par unité de surface ; dilatation thermique isotrope (F) | optionnels |

Compte : 4 + 4 + 2 + 6×5 + 3 + 2 = 45.

*Fait (U4.43.01 §ELAS_COQUE, lignes 674-740)* : « ELAS_COQUE permet à l'utilisateur de
fournir directement les coefficients de la matrice d'élasticité (décomposée en
membrane et flexion) des coques minces orthotropes en élasticité linéaire
[R3.07.03]. L'utilisateur peut également indiquer un coefficient de dilatation
thermique isotrope alpha et une masse par unité de surfacerho. »

*Fait (même section)* : « Si on souhaite utiliser ELAS_COQUE avec du cisaillement
transverse il faut nécessairement employer la modélisation DST. Si on utilise la
modélisation DKT, le cisaillement transverse ne sera pas pris en compte, quelque
soient les valeurs de G11 et G22. »

*Fait (U2.02.01, tableau « DEFI_MATERIAU », lignes 543-615)* : `ELAS_COQUE` n'est coché
que dans la colonne « DKT, DST, Q4G », pas sous `COQUE_3D`.

*Correspondance des noms aux termes des matrices* : la documentation ne l'écrit
pas (NE, hors table CALC_MATE_HOMO, qui ne définit pas ELAS_COQUE). C'est une
**déduction**, vérifiée numériquement sur SSLS502 (Q6) pour les huit opérandes
`MEMB_*`/`FLEX_*` ; pour les termes de couplage, elle repose sur la seule
correspondance des lettres (L=1, T=2, Z=3) avec les 6/6/6/6/6/3 termes des matrices
de U4.43.01, sans vérification numérique.

## 2. Unités et définition des coefficients

- *Fait* : U4.43.01 donne d'abord la forme isotrope, `C = Eh/(1-ν²)·[[1,ν,0],[ν,1,0],[0,0,(1-ν)/2]]`
  (membrane), `D = Eh³/(12(1-ν²))·[…]` (flexion), `G = 5Eh/(12(1+ν))·I` (cisaillement),
  puis : « Les matrices de rigidité élastique en absence de couplage reliant les
  efforts généralisés aux déformations généralisées sont donc données directement
  sous la forme : C = (C1111 C1122 0 ; C1122 C2222 0 ; 0 0 C1212), D = (…), G = (G11 0 ; 0 G22) ».
- *Déduction* : ce sont des rigidités **par unité de largeur de coque** (efforts
  généralisés par unité de longueur), donc, en unités cohérentes avec le maillage
  (SI : mètres, newtons) : membrane et cisaillement en N/m, flexion en N·m
  (les formules isotropes ci-dessus donnent ces dimensions). La documentation ne
  donne pas l'unité en toutes lettres (NE, en tant qu'énoncé).
- *Fait, cas test SSLS502 (V3.03.502, Problème de référence)* : « [H_membrane] = h[H] ;
  [H_membrane-flexion] = [0] ; [H_flexion] = h³[H]/12 », avec H11 = 3,0644×10⁹ N/m²,
  H12 = 1,1048×10⁹, H22 = 18,597×10⁹, H33 = 1,250×10⁹, et h = 0,0061 m
  (`AFFE_CARA_ELEM`, lu dans `ssls502a.comm`).
- *Sens des indices L et T* : L = direction 1 et T = direction 2 du repère
  utilisateur de la maille (Q5). Non écrit tel quel dans U4.43.01 (NE en tant
  qu'énoncé) ; déduit de SSLS502 : `MEMB_L` = h·H11 = 18 692 840, `MEMB_LT` = h·H12
  = 6 739 280, `MEMB_T` = h·H22 = 113 441 700, `MEMB_G_LT` = h·H33 = 7 625 000 ;
  `FLEX_L` = h³H11/12 = 57,96338, `FLEX_LT` = 20,89738, `FLEX_T` = 351,7638,
  `FLEX_G_LT` = 23,64385 : les huit valeurs du fichier de commandes coïncident avec
  ces produits (recalcul du 2026-09-21).
- **Signalé** : le résumé de V3.03.502 annonce la modélisation DST ; les fichiers
  de commandes `ssls502a-d` portent DKT (écart déjà relevé au lot 20).

## 3. Rôle de l'épaisseur déclarée dans `AFFE_CARA_ELEM`

*Fait (U4.42.01, mot clé COQUE, « Remarque sur l'utilisation de ELAS_COQUE »)* :
« Lorsqu'on utilise ELAS_COQUE les raideurs de flexion et de membrane sont rentrées
à la main par l'utilisateur dans DEFI_MATERIAU. Dans ce cas, l'épaisseur renseigné
dans AFFE_CARA_ELEM ne sert qu'à calculer la masse en dynamique et ne contribue pas
à la raideur. » Elle ne sert donc pas à la raideur ; sa contribution à la masse
n'est documentée que pour la dynamique. `EPAIS` reste obligatoire dans la syntaxe
`COQUE` (`♦ / EPAIS = ep`, U4.42.01) : elle doit rester déclarée.

## 4. Poids propre

- *Fait* : `RHO` est admis sous `ELAS_COQUE` (catalogue) et défini comme « une masse
  par unité de surface » (U4.43.01, citation en Q1).
- **Non établi** : comment `PESANTEUR` utilise cette valeur en statique (masse
  surfacique prise telle quelle, ou multipliée par l'épaisseur de `AFFE_CARA_ELEM`),
  et sur quelle épaisseur. U4.42.01 ne dit que « masse en dynamique ». Une recherche
  (profil `methode`, « PESANTEUR coque masse volumique épaisseur poids propre … »)
  ne renvoie aucune section qui tranche. Le point est à trancher par exécution.
  Avant cela, le poids propre de la palplanche ne doit pas être supposé pris en
  compte par `RHO`.

## 5. Orientation des axes L et T, repère des efforts généralisés

- *Fait (U4.43.01)* : « Ces coefficients sont à fournir dans le repère local de
  l'élément. Celui-ci est défini sous le mot-clé COQUE de AFFE_CARA_ELEM. »
  *(U2.02.01)* : « Ces coefficients sont donnés dans le repère utilisateur de
  l'élément défini par ANGL_REP. »
- *Fait (U4.42.01, opérande ANGL_REP / VECTEUR)* : « Les mots clés ANGL_REP ou
  VECTEUR permettent de renseigner le repère « utilisateur » en chaque élément de
  coque. C'est dans ce repère que sont exprimées par exemple les contraintes dans
  la coque ou les efforts généralisés. » Construction : « la projection de V sur le
  plan tangent fournit l'axe x_l ; le vecteur z_l est colinéaire à la normale n au
  plan de la coque […] ; le vecteur y_l est construit de manière à avoir un repère
  orthonormé » (z_l = n, y_l = z_l ∧ x_l). `ANGL_REP = (α, β)` définit V dans le
  repère global par deux angles nautiques ; `VECTEUR = (vx, vy, vz)` le définit par
  ses coordonnées globales ; les deux sont exclusifs. « Si aucun des mots clés
  ci-dessus n'est renseigné, c'est donc l'axe global X qui détermine, par
  projection sur le plan tangent de la coque, le repère « utilisateur » de chaque
  maille. »
- *Déduction* : sur des mailles DKT planes (facettes), V est projeté sur chaque
  facette : L = x_l est la direction de V projetée, T = y_l = n ∧ x_l. Le sens de
  z_l dépend de l'orientation de la normale (`MODI_MAILLAGE/ORIE_NORM_COQUE`).
  Le comportement lorsque V est normal à une facette (projection nulle) n'est pas
  documenté (NE) : le choix de V est à faire en fonction de la géométrie.
- Repère des efforts généralisés : repère utilisateur (citation ci-dessus), et non
  le repère global.

## 6. Ce que renseigne SSLS502 (`ssls502a.comm`, DKT, TRIA3 ; lecture directe)

`DEFI_MATERIAU(ELAS_COQUE=_F(MEMB_L=18692840.0, MEMB_LT=6739280.0, MEMB_T=113441700.0,
MEMB_G_LT=7625000.0, FLEX_L=57.96338137, FLEX_LT=20.89738407, FLEX_T=351.7638047,
FLEX_G_LT=23.64385417, CISA_L=10000000000.0, CISA_T=10000000000.0))` ;
`AFFE_CARA_ELEM(COQUE=_F(GROUP_MA="TOUT_ELT", EPAIS=0.0061, ANGL_REP=(0.0, 0.0)))` ;
aucun `RHO`, aucun `ALPHA` ; chargement `FORCE_ARETE`. Le fichier de commandes ne
porte pas de commentaire sur ces valeurs. Le commentaire est dans V3.03.502
(Modélisation A, Remarques) : « Les valeurs des coefficients CISA_L et de CISA_T ne
sont pas disponibles. Comme la structure est mince (h/R = 0.045), on suppose que les
effets du cisaillement transverse sont négligeables, nous avons donc imposé
CISA_L = CISA_T = 10¹⁰ » (sans effet en DKT, d'après la remarque de U4.43.01).
L'écart des valeurs MEMB/FLEX avec h·H et h³·H/12 est nul (Q2).
