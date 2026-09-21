# Étude lot 20 — coque orthotrope (option 2) et géométrie réelle (option 3)

Aide à la décision de MM sur la représentation de la palplanche intercalaire
(point 1, décision 2). **Cette étude ne décide rien** et n'enregistre aucune
décision pratique. Version Code_Aster : 17.4.0 ; sources documentaires au
commit `9c8c179f57ef7ca1d2891cac275ee4823a57967c` ; catalogue
`b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca`.
Niveau de validation : A (documentaire) et confrontation de mots-clés au
catalogue ; rien n'a été exécuté. Chaque extrait ci-dessous est
vérifié mot pour mot contre le dépôt de documentation par
`tests/unit/test_build_combiwall_reference.py` (identifiant entre crochets =
entrée de `data/examples/combiwall_inputs/lot20_extraits.json`, qui donne
document, section, plage de lignes).

## 1. Coque orthotrope (option 2)

### Q1 — Modélisations acceptant un comportement élastique orthotrope

Tableau des matériaux de U2.02.01 (section M_canique, lignes 551-556) :

*U2.02.01, section M_canique, lignes 551-556, v17.4.0* :

>     "**DEFI_MATERIAU**", "**COQUE_3D**", "**DKT, DST, Q4G**", "**DKTG,**
>     **Q4GG**", "**COQUE_AXIS**", "**GRILLE_EXCENTRE, GRILLE_MEMBRANE**", "**MEMBRANE**"
>     "ELASTICITE . LINEAIRE", "", "", "", "", "", ""
>     "ELAS", "•", "•", "•", "•", "•", "•"
>     "ELAS_ORTH ELAS_ISTR", "•", "•", "", "", "", ""
>     "ELAS_COQUE", "", "•", "", "", "", ""

Lecture : `ELAS_ORTH` / `ELAS_ISTR` sont cochés pour `COQUE_3D` et pour la
colonne `DKT, DST, Q4G` ; `ELAS_COQUE` seulement pour `DKT, DST, Q4G`. Le
tableau de la Conclusion de U2.02.01 (lignes 9-17) coche « Matériau
orthotrope, composite » pour `DKT` et `DST, Q4G` mais **pas** pour
`COQUE_3D` : **les deux tableaux de U2.02.01 divergent** sur `COQUE_3D`, la
documentation ne concilie pas.

*U2.02.01, section Conclusion_et_conseils_d_utilisation, lignes 9-17, v17.4.0* :

>     "**Modélisation**", "**DKT**", "**DST, Q4G**", "**DKTG,Q4GG**", "**COQUE_3D**", "**COQUE_AXIS**", "**GRILLE_***"
>     "Domaine d'application", "", "", "", "", "", ""
>     "Statique linéaire:
>     Matériau isotrope", "**X**", "**X**", "**X**", "**X**", "**X**", "**X**"
>     "Matériau orthotrope, composite", "**X**", "**X**", "", "", "", ""
>     "Statique non-linéaire matériau", "**X**", "", "**X**", "**X**", "**X**", "**X**"
>     "Statique non-linéaire géométrique", "", "", "", "**X**", "", ""
>     "Analyse dynamique", "**X**", "**X**", "**X**", "**X**", "**X**", "**X**"
>     "Flambement d'Euler", "**X**", "", "", "**X**", "", "**X**"

Le document de validation SSLS502 dit lui-même [v3502_synthese] :

*V3.03.502, section Synth_se_des_r_sultats, lignes 19-19, v17.4.0* :

> On constate donc que les résultats se dégradent quand le rapport de la longueur sur le diamètre diminue, en effet les effets géométriques deviennent importants avec ce type de modélisation. Il serait souhaitable de pouvoir effectuer un calcul en éléments finis de coques en milieu orthotrope, afin de mieux prendre en compte la courbure, les plaques constituant un cas limite.

Modélisations au catalogue (`AFFE_MODELE`, `AFFE/MODELISATION`) : `DKT`,
`DST`, `Q4G`, `COQUE_3D` présentes (`DKQ` absent).

### Q2 — Commandes, mots-clés, orientation des axes

- Matériau : `DEFI_MATERIAU`, mot-clé facteur `ELAS_COQUE` (catalogue :
  `MEMB_L`, `MEMB_LT`, `MEMB_T`, `MEMB_G_LT`, `FLEX_L`, `FLEX_LT`, `FLEX_T`,
  `FLEX_G_LT`, `CISA_L`, `CISA_T`, et les variantes `M_LLLL`… `F_LLLL`…),
  ou `ELAS_ORTH` (`E_L`, `E_T`, `NU_LT`, `G_LT` requis) associé à
  `DEFI_COMPOSITE` (`COUCHE`: `EPAIS`, `MATER`, `ORIENTATION`).
- Orientation : `AFFE_CARA_ELEM`, mot-clé facteur `COQUE`, `ANGL_REP` (2
  réels) ou `VECTEUR` (3 réels), exclusifs (catalogue confirmé).

*U4.42.01, section Mot_cle_COQUE, lignes 124-124, v17.4.0* :

> Les mots clés ANGL_REP ou VECTEUR permettent de renseigner le repère «utilisateur» en chaque élément de coque. C’est dans ce repère que sont exprimées par exemple les contraintes dans la coque ou les efforts généralisés [:ref:`U2.01.05 <U2.01.05>`].

*U4.43.01, section Caract_ristiques__lastiques_g_n_rales, lignes 704-704, v17.4.0* :

> Ces coefficients sont à fournir dans le repère local de l’élément. Celui-ci est défini sous le mot-clé COQUE de AFFE_CARA_ELEM [:external:ref:`U4.42.01 <U4.42.01>`].

Pour `ELAS_ORTH` en composite :

*U4.42.03, section Op_randes, lignes 45-45, v17.4.0* :

> Angle de la 1ère direction d'orthotropie (sens longitudinal ou sens des fibres) dans le plan tangent à l'élément par rapport à la 1ère direction du repère de référence défini dans l'opérateur AFFE_CARA_ELEM par le mot clé facteur COQUE et le mot clé ANGL_REP [:ref:`U4.42.01 <U4.42.01>`].

### Q3 — Modules et épaisseur, ou rigidités découplées ?

`ELAS_COQUE` fournit **directement** les rigidités de membrane, de flexion et
de cisaillement, donc une raideur de flexion par direction (`FLEX_L`,
`FLEX_T`) indépendante de l'autre :

*U4.43.01, section Caract_ristiques__lastiques_g_n_rales, lignes 677-677, v17.4.0* :

> ELAS_COQUE permet à l’utilisateur de fournir directement les coefficients de la matrice d’élasticité (décomposée en membrane et flexion) des coques minces orthotropes en élasticité linéaire [:ref:`R3.07.03 <R3.07.03>`].

*U4.43.01, section Caract_ristiques__lastiques_g_n_rales, lignes 693-695, v17.4.0* :

> Pour les coques orthotropes dont les modules d’élasticité sont obtenus par une méthode d’homogénéisation, il n’est pas possible dans le cas général de trouver un module de Young équivalent :math:`\mathit{Eeq}` , et une épaisseur équivalente :math:`\mathit{heq}` pour retrouver les expressions précédentes.
>
> Les matrices de rigidité élastique en absence de couplage reliant les efforts généralisés aux déformations généralisées sont donc données directement sous la forme:

`ELAS_ORTH` passe par des modules et une épaisseur (`EPAIS` de `COQUE` ou de
`DEFI_COMPOSITE`) : les rigidités de membrane et de flexion en découlent
toutes deux de la même épaisseur, elles ne s'imposent pas séparément.
Cisaillement transverse avec `ELAS_COQUE` (U4.43.01, ligne 708) :
uniquement avec `DST` ; avec `DKT`, il n'est pas pris en compte.

### Q4 — Cas test officiel de coque orthotrope

**SSLS502** (V3.03.502), « Cylindre orthotrope soumis à une ligne de
charge ». Fichiers `ssls502a` à `ssls502d` : `MODELISATION="DKT"`,
`DEFI_MATERIAU(ELAS_COQUE=...)` avec `FLEX_L=57.96338137`,
`FLEX_T=351.7638047` (flexions indépendantes), `AFFE_CARA_ELEM`
`COQUE=_F(..., ANGL_REP=(0.0, 0.0))`, chargement `FORCE_ARETE`. Ce que le
test vérifie [v3502_resume] :

*V3.03.502, section index, lignes 9-9, v17.4.0* :

> Ce test représente le calcul quasi-statique, d’un cylindre court orthotrope et d’un cylindre long orthotrope soumis à une ligne de charge. À leurs extrémités, les cylindres reposent sur des diaphragmes rigides. Ce cas-test permet de valider la modélisation éléments finis DST avec les mailles TRIA3 et QUAD4, avec un matériau homogène orthotrope.

Écart relevé : le résumé du document V annonce la modélisation `DST`, les
quatre fichiers de commandes portent `DKT`. Aucune modélisation `COQUE_3D`
orthotrope n'est couverte (voir la synthèse citée en Q1).

Autres cas tests : **SSLS113** (V3.03.113, `ssls113a`, `DKT`, `ELAS_COQUE`) ;
`ssls27a`, `ssls27c` (`DKT`), `ssls27d` (`DST`), `ssls27e` (`Q4G`) avec
`ELAS_COQUE`. SSLS113 [v3113_resume] :

*V3.03.113, section index, lignes 9-11, v17.4.0* :

> Ce test permet de valider l’excentrement des plaques ayant un comportement ‘ELAS_COQUE’.
>
> La référence est donnée par une première résolution où l’on modélise un bi-couche orthotrope ayant une non-symétrie matérielle par rapport au plan moyen.

### Classement C1, C2, C3

| Critère | Réponse | Appui |
|---|---|---|
| C1 — documentée en U4 pour une modélisation de coque disponible | **oui** (`ELAS_COQUE` : `DKT`, `DST`, `Q4G`) | U4.43.01 lignes 677-704, U4.42.01 `COQUE` `ANGL_REP`, table de U2.02.01 M_canique 551-556. Pour `COQUE_3D` : **non établi**, les deux tableaux de U2.02.01 divergent (Q1). |
| C2 — couverte par au moins un cas test officiel | **oui** (`DKT`, `ELAS_COQUE`) : SSLS502 (cylindre, surface courbe), SSLS113, SSLS27 | `ssls502a-d.comm`. Pour `COQUE_3D` orthotrope : **non établi** (aucun cas test trouvé ; la synthèse de V3.03.502 souhaite ce calcul). |
| C3 — impose séparément raideur verticale et horizontale de flexion, sans homogénéisation propre à l'utilisateur | **oui pour `ELAS_COQUE`** (`FLEX_L`, `FLEX_T` indépendants, aucun `Eeq`/`heq` requis) ; **non** pour `ELAS_ORTH` (modules et épaisseur communs) | U4.43.01 lignes 693-695. Restriction : les valeurs de `FLEX_L`, `FLEX_T`, `MEMB_*` restent à calculer par l'utilisateur à partir du profil, la documentation ne fournit pas ce calcul. |

Faits ou déductions : les lignes du tableau sont des faits documentés ; la
lecture « `COQUE_3D` non établi » est une déduction de la divergence
documentaire.

## 2. Géométrie réelle (option 3)

### Critère d'élancement appliqué à 9,5 mm

U2.02.01, Conclusion [u2_structures_minces] :

*U2.02.01, section Conclusion_et_conseils_d_utilisation, lignes 35-35, v17.4.0* :

> * *Structures minces* **:** pour ces structures, dont le rapport h/L est inférieur à 1/20, les effets de cisaillement transverse peuvent être négligés et la théorie de Kirchhoff s’applique. On conseille d’utiliser pour ce type de structure des éléments plaques DKT-DKQ ou des éléments de coque courbe (COQUE_3D, _AXIS). **Il est conseillé d’utiliser de préférence les éléments** **DKT et DKQ**  qui donnent de très bons résultats sur les déplacements et plus approximatifs sur les contraintes (à recommander pour les analyses vibratoires). Même si on doit utiliser un grand nombre de ces éléments, les temps d’exécution restent raisonnables comparés à ceux des éléments courbes. On conseille de ne pas dépasser un rapport h/L=1/500 afin d'éviter des problèmes liés au verrouillages numériques.

Déduction arithmétique (non extraite) : pour des largeurs de 0,3 à 0,5 m,
h/L = 9,5/500 à 9,5/300, soit environ 1/53 à 1/32 : inférieur à 1/20 (structure
mince, Kirchhoff) et supérieur à 1/500 (limite de verrouillage citée).
Modélisations recevables : `DKT` (plaque, et son quadrangle DKQ) et
`COQUE_3D`, selon ce texte. Les modélisations `DST` et `Q4G` sont indiquées
pour les structures épaisses ; elles ne sont pas exclues par le texte pour une
structure mince, mais il ne les conseille pas non plus.

### Coques assemblées en arêtes vives

Rien trouvé de spécifique aux facettes planes jointes sous un angle sans
congé. Requêtes : `search_codeaster_docs` (profil `methode`) « jonction de
plaques planes sous un angle arête vive facettes DKT rotation normale DRZ »
(famille U2) et « raccord de deux plaques non coplanaires intersection coques
angle » ; recherche lexicale (`facett`, `arête vive`, `arêtes vives`,
`jonction`, `angle dièdre`, `courbure importante`) dans U2, U3.12.*, R3.07.03,
R3.07.04, U4.42.*, U4.44.*. Éléments voisins trouvés, non spécifiques :

*U2.02.01, section Introduction, lignes 11-11, v17.4.0* :

> *   Les éléments de **plaques** , qui sont plans. La courbure de la structure à représenter n’est pas prise en compte et il est donc nécessaire d’utiliser un grand nombre d’éléments de façon à approcher correctement la géométrie de la structure (aspect facettes).

*U3.12.01, section index, lignes 26-26, v17.4.0* :

> Elles sont utilisables pour des problèmes de plaque en tridimensionnel [:external:ref:`R3.07.03 <R3.07.03>`] en analyse mécanique linéaire pour toutes les modélisations et en non linéaire matériau pour les modélisations DKT, DKTGet Q4GG uniquement. Leur utilisation pour des problèmes de coque est couramment admise en considérant que le plan de l'élément est assimilable à une facette tangente au feuillet moyen de la coque (attention, seules les facettes planes sont permises).

`COEF_RIGI_DRZ` (U4.42.01, `COQUE`, ligne 112) : rigidité fictive sur la
rotation autour de la normale, nécessaire pour éviter une matrice singulière
sur les éléments plans ; U2.02.01 (M_canique, ligne 967) signale qu'une
mauvaise valeur pénalise la convergence des calculs DKT non linéaires.

## 3. Tube : facettisation, DKQ et DKT

- **Critère de facettisation** (discrétisation angulaire, rapport rayon /
  taille de maille) : **aucun critère chiffré trouvé**. Seules mentions
  qualitatives : [u2_intro_plaques_facettes] (« aspect facettes »),
  [u2_plans_sans_courbure].

*U2.02.01, section Conclusion_et_conseils_d_utilisation, lignes 42-42, v17.4.0* :

> Les éléments DKT, DKQ, DST, DSQ et Q4G sont des éléments plans, ils ne prennent pas en compte la courbure des structures, il est donc nécessaire de raffiner le maillage dans le cas où la courbure est importante si on veut éviter les flexions parasites.

- **Cas test de cylindre mince** V3.03.020 (`ssls20`, DKT et COQUE_3D)
  [v3020_dkt], [v3020_coque3d_quad] :

*V3.03.020, section Synth_se_des_r_sultats, lignes 10-10, v17.4.0* :

> *   Solution convenable pour un maillage fin.

*V3.03.020, section Synth_se_des_r_sultats, lignes 25-25, v17.4.0* :

> *   COQUE_3D sur des quadrangles: très bonne solution obtenue avec un maillage relativement grossier.

- **Relation DKQ / DKT** : DKQ n'est pas une modélisation distincte.

*U2.02.01, section Introduction, lignes 19-19, v17.4.0* :

> *   DKT: maille TRIA3élément DKT, maille QUAD4éléments DKQ(linéaire géométrique);

*R3.07.03, section Implantation_des__l_ments_de_plaque_dans_Code_Aster, lignes 18-18, v17.4.0* :

>

  Catalogue : `DKQ` absent des valeurs de `AFFE_MODELE/AFFE/MODELISATION`.
  Les noms « DKQ », « DSQ » ne subsistent que comme titres de variantes de cas
  tests (`ssls100e` : `MODELISATION="DKT"`).
- **Conclusion** : la documentation ne départage pas `DKT` et `COQUE_3D` pour
  le tube. Ensemble recevable enregistré dans la fiche (entrée `code_aster`
  du point 1) ; choix renvoyé à une entrée pratique non tranchée du même
  point.

## 4. Points non fondés

Voir les entrées de la fiche : `FORCE_COQUE` (point 2 : fondé),
`FORCE_NODALE` (point 3 : fondé), raideur surfacique projetée (point 1 : non
fondé, trace de recherche dans `notes`).
