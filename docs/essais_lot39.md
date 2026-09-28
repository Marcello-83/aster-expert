# Essais lot 39 — ferraillage de la poutre de couronnement et limites de `CALC_FERRAILLAGE`

Rapport rédigé au fil du lot, selon `docs/modele_rapport_essai.md`. Chaque
section « Critère » est écrite **avant** l'exécution qu'elle juge et n'est pas
modifiée ensuite ; l'heure d'écriture est indiquée. Version cible : Code_Aster
17.4.0 (digest `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).

Aucun verdict de conformité de l'ouvrage n'est porté ici : ce sont des aires
calculées, sous les hypothèses de la fiche.

## Étape 1 — Correction du module `aster_expert.rebar` (points intérieurs)

### Objet

Le lot 38 a laissé deux cas « infeasible » dans le module indépendant, là où
`CALC_FERRAILLAGE` donne une aire nulle : flexion composée comprimée
(N = −5 MN de compression, M = 2,183517 MN·m) et ELS quasi permanente
(N = 1 MN de compression, M = 0,5 MN·m), section 2,50 × 1,40 m, enrobage à l'axe
0,065 m (valeur du lot 38). Le contre-calcul de MM (énoncé du lot) établit que
ce sont des points intérieurs du domaine résistant du béton seul.

Ce que dit la documentation (niveau A, `R7.04.05`,
`Calcul_du_ferraillage_des_poutres_et_poteaux.rst`, lignes 69-420 et 906-1100,
commit documentaire `9c8c179f57ef7ca1d2891cac275ee4823a57967c`) :

- ELU : quand la résolution directe échoue (`COND_ITER = VRAI`), l'algorithme
  balaie α de −∞ à +∞ (pivots A, B, C) et « retiendra au final la configuration
  aboutissant à une minimisation de la somme As,s + As,i, tout en veillant à ce que
  les deux sections soient positives ».
- ELS caractéristique : section homogénéisée, **béton sans résistance en
  traction** (« le béton n'a aucune résistance », cas entièrement tendu), même
  balayage de ξ et même règle de minimisation.

Déduction (non énoncée par la documentation) : un couple (N, M) intérieur au
domaine du béton seul n'est l'équilibre d'aucun plan de déformation **ultime** à
aciers positifs ou nuls ; la minimisation « à sections positives » ne peut
alors aboutir qu'à zéro. Le module, qui ne retenait que des plans ultimes
réalisant exactement l'équilibre, n'avait aucune solution.

Correction apportée (écrite avant son exécution) :

- ELU : si l'effort normal est de compression et si |M| ≤ M_c(N), où M_c(N) est
  le moment que le béton seul reprend sous l'effort N sur la frontière de son
  propre domaine (même diagramme béton que le calcul avec aciers), l'aire est
  nulle sur les deux faces.
- ELS (caractéristique et quasi permanente) : si la section de béton seul,
  élastique et sans traction, équilibre (N, M) avec une contrainte maximale au
  plus égale à la limite (σc,lim à l'ELS caractéristique, σc,lim,FL à l'ELS
  quasi permanente), l'aire est nulle. C'est le modèle de `R7.04.05` (béton
  fissuré, sans traction). La vérification « section non fissurée »
  (contraintes de la section brute non fissurée, traction maximale comparée à
  fct,eff, EN 1992-1-1 7.1(2)) est ajoutée comme grandeur d'information ; elle
  n'est pas le critère de `CALC_FERRAILLAGE`.

### Critère de réussite (écrit avant l'exécution, 2026-09-28T05:43-04:00)

Section 2,50 × 1,40 m (h = 2,50 m dans le plan de flexion, b = 1,40 m),
C35/45, B500B, γc = 1,5, γs = 1,15, αcc = 1,0, enrobage à l'axe 0,065 m.

| Grandeur | Attendu | Origine | Nature | Seuil |
| --- | --- | --- | --- | --- |
| As, cas 1 (N = 0, M = 2,183517) | 2,074218e-03 (AYS) | `CALC_FERRAILLAGE`, lot 38, et calcul de MM | exacte | 1e-6 relatif |
| As, cas 3 (N = +5 traction) | 7,869025e-03 et 3,630975e-03 | idem | exacte | 1e-6 relatif |
| As, cas 2 (N = −5 compression) | 0 et 0, `feasible` | idem | exacte | aire nulle, `feasible = True` |
| M_c(N = 5 MN), béton seul | 5 × (2,50 − a)/2 avec a = 5/(23,333 × 1,40) = 0,15306 m, soit 5,867347 MN·m | calcul de MM | exacte | 1e-6 relatif |
| As, cas 4 (ELS_QP, N = −1, M = 0,5) | 0 et 0, `feasible` | idem | exacte | aire nulle, `feasible = True` |
| Contraintes de la section brute, cas 4 | −0,2857 ± 0,3429 MPa (traction max. 0,0571 MPa) | calcul de MM | exacte | 1e-6 relatif |
| Continuité : cas 2 avec M juste au-delà de M_c | aire strictement positive, petite | déduction | qualitative | As > 0 et As < 1e-4 m² pour M = 1,001 M_c |
| Cas de `ssll13b`/`ssll13d` déjà testés | inchangés | lot 38 | exacte | tests existants verts |

Toute autre issue est un échec.

### Résultats de l'étape 1 (exécution des tests, 2026-09-28)

`pytest tests/unit/test_rebar_interior_points.py` : 11 tests, tous verts
(sortie jointe au compte rendu final). Toutes les lignes du critère sont
tenues : cas 1 et 3 à 1e-6 relatif de Code_Aster, cas 2 et 4 nuls et
`feasible`, M_c(5 MN) = 5,867347 MN·m, contraintes de la section brute
−0,2857 ± 0,3429 MPa, aire strictement positive et inférieure à 1e-4 m² pour
M = 1,001 M_c, tests `ssll13b`/`ssll13d` existants verts.

**Défaut supplémentaire trouvé en préparant l'étape 2 (non prévu par le
critère ci-dessus, rapporté tel quel).** Dans
`serviceability._concrete_force_moment`, la profondeur de l'axe neutre était
calculée comme une fraction de h (`-eps_top / gradient`) puis utilisée comme une
longueur. Pour h < 1 m, l'intervalle d'intégration était trop long et
n'intégrait que des contraintes écrêtées à zéro (erreur de quadrature seulement :
6,0575e-4 → 6,0447e-4 m² sur `ssll13b` CHEFF4, soit 0,2 %) ; pour h > 1 m
(poutre de couronnement, 2,50 m), la zone comprimée était tronquée (2,1458e-3 →
2,1777e-3 m² pour M = 2 MN·m, soit 1,5 %). Corrigé. **Ce n'est pas la cause de
l'écart de 2,7 % sur `ssll13b` CHEFF4** : le calcul à la main selon la formule
de pivot acier de `R7.04.05` (ξ = 0,3027, x = 0,1392 m, σc = 11,58 MPa,
As = Fc/σs) redonne 6,0447e-4 m², la valeur du module corrigé, et non les
5,8876e-4 m² de la référence du cas test (`D_ref`, `REFERENCE="ANALYTIQUE"`).
Aucun des paramètres essayés (σs, αe, bras de levier pris à h) ne reproduit la
référence avec une valeur ronde : cause non établie.

## Étape 1 bis — Les quatre essais du lot 38 avec D19 (0,10 m)

### Critère (écrit avant l'exécution, 2026-09-28T05:54-04:00)

`data/examples/lot39_essais/d19/d19.comm`, mêmes cas que le lot 38, distance
parement-axe 0,10 m sur les quatre faces, `PHI_*` = 40 mm (D19). Valeurs
attendues : module corrigé, calculées avant l'exécution.

| Cas | Attendu (module) | Nature | Seuil |
| --- | --- | --- | --- |
| flexion simple (N = 0, MFZ = 2,183517 MN·m) | AYS = 2,104822e-03, AYI = 0 (pivot A) | exacte | 1e-6 relatif |
| composée comprimée (N = −5 MN) | 0 sur les quatre faces | exacte | aire nulle |
| composée tendue (N = +5 MN) | AYS = 7,933517e-03, AYI = 3,566483e-03 (somme N/fyd = 1,15e-02) | exacte | 1e-6 relatif |
| ELS QP (N = −1 MN, MFZ = 0,5 MN·m) | 0 sur les quatre faces | exacte | aire nulle |

## Étape 2 — Ce que `CALC_FERRAILLAGE` fait en 1D

Trois fichiers (`limites/`, `fermin/`, `fiss/`), un par sujet, pour qu'une
erreur fatale de l'un n'empêche pas les autres. Distance parement-axe 0,10 m
(D19). Ces essais **établissent un comportement** : pour chaque question, le
critère énumère les hypothèses concurrentes et leurs valeurs prédites, calculées
avant l'exécution ; le verdict dit laquelle est reproduite à 1e-6 relatif, ou
qu'aucune ne l'est.

### Critère 2.0 — faces et signes (écrit avant l'exécution, 2026-09-28T05:54-04:00)

Fait documentaire (`U4.81.42`, `Composition_du_champ_produit.rst`) : AYS/AYI =
faces +y/−y « suivant la hauteur h », AZS/AZI = faces +z/−z « suivant la largeur
b ». Constat du lot 38 : MFZ > 0 donne AYS.

| Instant | Efforts | Attendu | Seuil |
| --- | --- | --- | --- |
| `mfz_1` | MFZ = +1 MN·m | AYS = 9,608935e-04 (h = 2,50, b = 1,40), autres nuls | 1e-6 relatif |
| `mfz_m1` | MFZ = −1 MN·m | AYI = 9,608935e-04, autres nuls | 1e-6 relatif |
| `mfy_1`, `mfy_m1` | MFY = ±1 MN·m | 1,778296e-03 (h = 1,40, b = 2,50) sur AZS ou AZI ; **quelle face pour quel signe : à établir** | 1e-6 relatif |

### Critère 2.2 — flexion déviée (écrit avant l'exécution)

Hypothèse H-dir (direction par direction, sans interaction) : `devie_1` =
(AY de `mfz_1`, AZ de `mfy_1`), `devie_3` = (AY de `mfz_3` = 2,898292e-03, AZ de
`mfy_3` = 5,391007e-03). Hypothèse H-Bresler (`R7.04.05`, § flexion déviée :
calcul direction par direction puis augmentation proportionnelle des quatre aires
par pas de 10 % de l'aire totale jusqu'à vérifier l'inéquation de Bresler, a = 1
pour N/NR < 0,1) : aires strictement supérieures à H-dir, dans le même rapport
AY/AZ que H-dir (à 1e-6 relatif), la dernière itération vérifiant
MFY/MRy + MFZ/MRz ≤ 1. Verdict : l'hypothèse reproduite.

### Critère 2.3 — effort tranchant et torsion (écrit avant l'exécution)

`AST` (m²/m) en 1D, cadres droits. Valeurs prédites :

| Instant | H-EN (module, EN 1992-1-1 6.2/6.3, v_min = 0,035 k^1,5 fck^0,5) | H-R7 (`R7.04.05` lu à la lettre) |
| --- | --- | --- |
| `vy_2` (VY = 2 MN) | V_Rd,c = 1,018 MN < 2 → Asw/s = 8,518519e-04 (z = 0,9 d = 2,16 m, cot θ = 2,5) | v_min = 0,053 γc k^1,5 fck^0,5 → V_Rd,c = 2,31 MN > 2 → AST = 0 |
| `vy_4` (VY = 4 MN) | 1,703704e-03 | 1,703704e-03 |
| `vz_4` (VZ = 4 MN) | 3,145299e-03 (bw = 2,50, d = 1,30, z = 1,17) | même valeur si VZ est pris en compte dans son plan ; 0 si seul VY l'est |
| `mt_2` (MT = 2 MN·m) | T_Rd,c = 2,623 MN·m > 2 → 0 | 0 |
| `mt_4` (MT = 4 MN·m) | armatures de torsion : A_t/s = 9,429380e-04 par brin, soit 1,885876e-03 pour deux brins | V_Rd,s = T/A_k (h − t_k) = 4,2049 MN → AST = 1,790744e-03 |
| `vy_4_mt_4` | 1,703704e-03 + 1,885876e-03 = 3,589580e-03 | (4 + 4,2049)/(2,16 × 434,78 × 2,5) = 3,494447e-03 |
| `vy_4_vz_4` | à établir : max, somme, ou résultante √(VY² + VZ²) | idem |

Verdict : pour chaque instant, l'hypothèse reproduite à 1e-6 relatif, ou
« aucune ».

### Critère 2.4 — ELS caractéristique (écrit avant l'exécution)

σc,lim = 0,6 fck = 21 MPa (XS3, EN 1992-1-1 7.2(2)), σs,lim = 0,8 fyk = 400 MPa
(7.2(5)), αe = 15.

| Instant | Attendu (module corrigé) | Seuil |
| --- | --- | --- |
| `els_mfz_2` | AYS = 2,177745e-03 | 1e-6 relatif (l'écart de 2,7 % de `ssll13b` CHEFF4 peut se reproduire : il est alors rapporté) |
| `els_mfy_1` | 2,008225e-03 sur la face tendue de MFY | idem |
| `els_n_m3_mfz_4` | AYS = 9,331700e-04, AYI = 0 | idem |

Et `qp_mfz_1` (ELS QP, MFZ = 1 MN·m, wk = 0,2 mm, φ = 40 mm, kt = 0,4) : module
8,572637e-04, comparé sans seuil (le module QP n'a pas été calibré sur un cas
test).

### Critère 2.1 — ferraillage minimal (écrit avant l'exécution)

Catalogue 17.4.0 (`get_command_schema`) : `AFFE/FERR_MIN` ∈ {`VALE_MIN`, `EC2`}
et `AFFE/FERR_MIN_FISS` ∈ {`EC2`, `RCC-CW`} pour `CODIFICATION='EC2'`.
Documentation `U4.81.42` (Op_randes, lignes 876-927) : dans la section EC2, les
valeurs annoncées sont `VALE_MIN`/`BAEL91` (désaccord documentation/catalogue :
le catalogue fait foi) ; ρl,min = 0,26 fctm/fyk ≥ 0,0013 et ρt,min =
0,08 √fck/fyk en 1D. `FERR_MIN_FISS='EC2'` : minimum de maîtrise de la
fissuration à l'ELS QP selon 7.3.2, équation 7.1 ; les composantes `ASMIN*` ne
sont documentées qu'en 2D.

`fermin/` (ELU) :

| Instant | Hypothèses | Valeurs prédites |
| --- | --- | --- |
| `mfz_1_sans_min` | témoin | AYS = 9,608935e-04 |
| `mfz_1_min` | H1 : AYS = max(flexion, 0,26 fctm/fyk b d) avec b = 1,40, d = 2,40 ; H2 : même chose avec b h ; H3 : minimum sur les quatre faces (AZ : b = 2,50, d = 1,30) | H1 : 5,608446e-03 ; H2 : 5,842132e-03 ; H3 : AY = 5,608446e-03 et AZ = 5,424837e-03 |
| `nul_min` | minimum appliqué sans effort, ou non | 0 ou les valeurs ci-dessus |
| `vy_4_min` | AST = max(1,703704e-03, ρw,min bw) avec bw = 1,40 → 1,325202e-03 | 1,703704e-03 |

`fiss/` (ELS QP) : `qp_mfz_1_fiss` comparé au témoin `qp_mfz_1_sans` ; valeur
prédite par 7.3.2 si le minimum est appliqué sur la face tendue avec kc = 0,4,
k = 0,65, Act = b h/2 = 1,75 m², σs = fyk : 2,921066e-03 m². `qp_nul_fiss` :
minimum sans effort, ou non. Une erreur fatale est un résultat : elle est
rapportée.

### Critère 2.1 bis — `FERR_MIN='EC2'` en MPa et mm (écrit avant l'exécution, 2026-09-28T05:57-04:00)

Ajouté après lecture des résultats de `fermin/` (en Pa), qui donnent
0,0013·b·d sur les quatre faces et un minimum transversal de 2,366e-6 m²/m :
valeurs compatibles avec une formule en MPa appliquée à des données en Pa (fctm
calculé à partir de fck en Pa, 100 fois trop faible, donc 0,0013 l'emporte ;
√fck en Pa divisé par fyk en Pa, 1 000 fois trop faible). `fermin_mpa/` rejoue
`fermin/` avec `UNITE_CONTRAINTE='MPa'`, longueurs en mm, moments en N·mm.

| Instant | H-unités (la formule est écrite pour des MPa) | H-constante (0,0013 quelle que soit l'unité) | Seuil |
| --- | --- | --- | --- |
| `mfz_1_min` AY | 0,26 × 3,20996/500 × 1400 × 2400 = 5 608,446 mm² | 0,0013 × 1400 × 2400 = 4 368 mm² | 1e-6 relatif |
| `mfz_1_min` AZ | 0,26 × 3,20996/500 × 2500 × 1300 = 5 424,837 mm² | 4 225 mm² | 1e-6 relatif |
| `nul_min` AST | 9,465728e-04 × b_w, soit 2,366432 mm²/mm (b_w = 2500) ou 1,325202 (b_w = 1400) | 2,366432e-03 (même formule, ×1000 en Pa) | 1e-6 relatif |
| `mfz_1_sans_min` AYS | 960,8935 mm² (témoin, 9,608935e-04 m²) | idem | 1e-6 relatif |

## Étape 3 — Ferraillage de la poutre sous les combinaisons de D17

### Modèle

`data/examples/lot39_poutre/poutre.comm` (`scripts/build_lot39_poutre.py`) :
une maille `SEG2` par extrémité d'élément de `POUTRE_COUR` (64 éléments, 128
sections, `sections.csv`), efforts combinés (`efforts.csv`) imposés par
`CART_SIEF_R` dans le schéma des cas tests `ssll13*`. Efforts élémentaires :
tables `EFPOUT_<cas>` de l'exécution du modèle complet réutilisée au lot 38 ;
combinaisons : `aster_expert.report.combinations` (D17), **par extrémité
d'élément**, non moyennées par nœud (l'effort tranchant saute au droit des
tubes). Quatre appels de `CALC_FERRAILLAGE` : ELU fondamentale (8 combinaisons,
γc = 1,5, γs = 1,15), ELU accidentelle (1, γc = 1,2, γs = 1,0 : valeurs
recommandées de l'EN 1992-1-1, tableau 2.1N, **non décidées par MM**), ELS
caractéristique (4, σc ≤ 21 MPa, σs ≤ 400 MPa), ELS quasi permanente (1,
wk = 0,2 mm, φ = 40 mm, kt = 0,4). αcc = 1,0. `FERR_MIN` non activé (faux en Pa,
étape 2.1) : minima hors de Code_Aster (étape 4). ELS fréquente : aucun critère
de ferraillage dans D18, non calculée. Niveau B : 26/26 commandes confrontées
(`validate_comm`).

### Critère (écrit avant l'exécution, 2026-09-28T06:02-04:00)

Contre-vérification de trois sections par le module corrigé
(`aster_expert.rebar.ultimate` direction par direction, puis
`aster_expert.rebar.biaxial` pour la procédure de Bresler de `R7.04.05`,
reproduite à 1e-13 sur `devie_1`/`devie_3`) :

- au bollard (X = 0, nœud 2259) ;
- à mi-travée entre tubes (X = ±1,30 m, milieu de l'entraxe de 2,60 m entre
  `TUBE_05` et ses voisins) ;
- au plan de symétrie `SYM_G` (X = −10,40 m).

Pour chaque section (les deux extrémités d'élément qui s'y rencontrent quand
elles existent), et pour **chaque** combinaison ELU fondamentale et
accidentelle : AYS, AYI, AZS, AZI de `CALC_FERRAILLAGE` et du module doivent
coïncider à **1e-6 relatif** lorsque le pivot de chaque direction est A ou B
(écart absolu ≤ 1e-12 m² pour une aire nulle). Un cas en pivot C, ou résolu par
le béton seul, est rapporté à part sans seuil. Toute autre issue est un échec,
rapporté tel quel.

## Étape 6 — `CALC_FERRAILLAGE` en 2D, plaque DKT d'un élément

### Critère (écrit avant l'exécution, 2026-09-28T06:09-04:00)

`data/examples/lot39_essais/plaque/plaque.comm` (`scripts/build_lot39_plaque.py`) :
un `QUAD4` DKT de 1 m × 1 m dans le plan XY, épaisseur 0,50 m, distance
parement-axe 0,05 m, C35/45, B500B, ELU fondamental (γc = 1,5, γs = 1,15,
αcc = 1,0), méthode par défaut (`METHODE_2D='CAPRA-MAURY'`, catalogue). Niveau B :
16/16 commandes. Valeurs prédites par le module (bande de 1 m, h = 0,50 m,
d = 0,45 m), m²/m :

| Instant | Efforts (par m) | Prédiction | Seuil |
| --- | --- | --- | --- |
| `mxx_p` | MXX = +0,2 MN·m/m | 1,044824e-03 sur une face X (DNSXI ou DNSXS : **face à établir**), 0 ailleurs | 1e-6 relatif (bloc rectangulaire) ; si écart, comparer au parabole-rectangle 1,046055e-03 |
| `mxx_m` | MXX = −0,2 | même valeur sur l'autre face X | idem |
| `nxx_t_mxx` | NXX = +1 MN/m, MXX = +0,2 | 2,3e-03 sur la face tendue, 0 sur l'autre (e = h/2 − c exactement) | 1e-6 relatif |
| `nxx_c_mxx` | NXX = −2 MN/m, MXX = +0,2 | 0 (point intérieur, M_c = 0,4143) | aire nulle |
| `nxx_t` | NXX = +1 MN/m | 1,15e-03 sur chaque face X | 1e-6 relatif |
| `mxx_mxy` | MXX = +0,2, MXY = +0,1 | pas de prédiction exacte (Capra-Maury par facettes, pas de 5°) ; comparaison indicative à Wood-Armer : face tendue X pour MXX + abs(MXY) = 0,3 → 1,585371e-03 ; Y : abs(MXY) = 0,1 → 5,166373e-04 | sans seuil, écart rapporté |
| `mxy` | MXY = +0,1 | indicatif Wood-Armer : 5,166373e-04 sur chacune des quatre nappes | sans seuil, écart rapporté |

## Exécutions (toutes réelles, Code_Aster 17.4.0)

| Essai | `.comm` | Diagnostic | Durée |
| --- | --- | --- | --- |
| d19 | `data/examples/lot39_essais/d19/d19.comm` | OK | 13,7 s |
| limites | `data/examples/lot39_essais/limites/limites.comm` | OK | 10,0 s |
| fermin | `data/examples/lot39_essais/fermin/fermin.comm` | OK | 9,6 s |
| fiss | `data/examples/lot39_essais/fiss/fiss.comm` | `<F>_ERROR` (`CALCULEL7_40`) | 8,0 s |
| fermin_mpa | `data/examples/lot39_essais/fermin_mpa/fermin_mpa.comm` | OK | 10,1 s |
| poutre | `data/examples/lot39_poutre/poutre.comm` | OK, aucune alarme | 11,5 s |
| plaque | `data/examples/lot39_essais/plaque/plaque.comm` | OK | 8,4 s |

Journal : `data/examples/lot39_essais/rapports/executions.json`,
`data/examples/lot39_poutre/rapports/executions.json` (sha256 des `.comm`
exécutés contrôlés identiques aux versionnés, `scripts/collect_lot39_essais.py`) ;
extraits de listings `mess_*_extrait.txt` à côté. Sept exécutions, 71,3 s
cumulées.

## Résultats et verdicts

### Étape 1 bis (d19)

| Cas | Code_Aster | Module | Écart | Verdict |
| --- | --- | --- | --- | --- |
| flexion simple AYS | 2,104821602536e-03 | 2,104821602536e-03 | 1,1e-13 | réussite |
| composée comprimée | 0 (4 faces) | 0 | — | réussite |
| composée tendue AYS / AYI | 7,933517e-03 / 3,566483e-03 | idem | < 1e-13 | réussite |
| ELS QP | 0 (4 faces) | 0 | — | réussite |

Avec 0,10 m au lieu de 0,065 m, l'aire de flexion simple passe de 2,074218e-03
à 2,104822e-03 m² (+1,5 %, bras de levier plus court, comme le prévoyait la
justification de D19).

### Étape 2 (limites, fermin, fermin_mpa, fiss)

- **2.0, faces et signes : réussite.** MFZ = ±1 → AYS / AYI = 9,608935e-04 ;
  MFY = ±1 → AZS / AZI = 1,778296e-03 ; écarts ≤ 1e-13.
- **2.2, flexion déviée : H-Bresler reproduite, H-dir rejetée.** `devie_1` :
  AYS = 2,059761e-03, AZS = 3,811936e-03, soit 2,1436 = 1,1⁸ fois les aires
  direction par direction ; `devie_3` : même facteur. Le module
  `aster_expert.rebar.biaxial` (procédure de `R7.04.05`) reproduit à 1e-13,
  8 itérations, Bresler final 0,937 et 0,946.
- **2.3, effort tranchant et torsion : ni H-EN ni H-R7 exactement ; loi
  établie après coup et reproduite à 1e-13.** AST = [V + T/A_k (h − t_k)] /
  (0,9 d fyd cot θ) avec **θ = 21,8°** (cot θ = 2,50018 au lieu de 2,5 : d'où
  l'écart de 7,1e-5 de H-EN sur `vy_2`, `vy_4`, `vz_4`) ; `vy_2` donne des cadres
  (H-R7 lue à la lettre, V_Rd,c = 2,31 MN, est rejetée) ; `mt_2` : 0 (les deux
  hypothèses) ; `mt_4` : 1,790828e-03, formule de H-R7 avec θ = 21,8° (H-EN par
  paroi, 1,885876e-03, rejetée) ; `vy_4_vz_4` : 3,145075e-03 = VZ seul, **AST est
  le maximum des deux directions**.
- **2.4, ELS caractéristique : échec du critère à 1e-6.** `els_mfz_2`
  2,081470e-03 contre 2,177745e-03 (−4,4 %) ; `els_mfy_1` 2,013326e-03 contre
  2,008225e-03 (+0,25 %) ; `els_n_m3_mfz_4` 7,843649e-04 contre 9,331700e-04
  (−16 %). Même famille d'écart que `ssll13b` CHEFF4 (étape 1). Cause non établie.
  ELS QP `qp_mfz_1` : 3,859047e-03 contre 8,572637e-04 pour le module (non
  calibré) : écart rapporté.
- **2.1, minimum : H-constante rejetée, H-unités reproduite à 1e-14.** En MPa,
  `FERR_MIN='EC2'` donne AY = 5 608,446 mm², AZ = 5 424,837 mm² sur **les quatre
  faces**, même sans effort (`nul_min`), et AST = 2,366432 mm²/mm = ρw,min × 2 500
  (b_w = HY quelle que soit la direction). En Pa (`fermin`) : 4,368e-03 =
  0,0013 b d et AST = 2,366e-06 (1 000 fois trop faible). **`FERR_MIN_FISS='EC2'`
  en 1D : `<F> <CALCULEL7_40>`**, « Le calcul de ferraillage minimal pour la
  maîtrise de la fissuration n'est pas encore possible pour les éléments
  POUTRE ».

### Étape 3 (poutre)

128 sections × 14 combinaisons, aucune aire −1 (non résolue). Enveloppes :
`data/examples/lot39_poutre/enveloppes.csv`, figure `figures/as_x.png`.
Maxima (cm²) : AYS 45,13 (bollard, ELU fondamentale), AYI 23,25 (bollard, ELU
accidentelle ; 23,24 au plan de symétrie, ELU fondamentale), AZS 29,91 (bollard),
AZI 8,54 ; AST nul partout ; ELS QP nul partout (efforts de la poutre quasi nuls
sous G + EAU_P + 0,3 Q1, constat du lot 37).

Contre-vérification (critère ci-dessus) : 63 comparaisons (bollard, X = ±1,30,
SYM_G ; 7 combinaisons × sections), toutes dans le domaine du critère (pivots A
ou B). **61 réussites (écart maximal 6,5e-13), 2 échecs** : au bollard sous
`ELU_FOND_Q1_DOM_G_defav` et `..._G_favo`, où les moments valent quelques
1e-5 N·m (bruit numérique : le bollard est dans l'axe de symétrie de Q1),
Code_Aster imprime AZI = 4,8e-12 et 1,2e-11 m² contre 8e-14 et 7e-14 pour le
module : écart absolu supérieur au seuil écrit de 1e-12 m². Rapporté tel quel ;
le critère n'est pas modifié. Détail : `controle_main.json`. Les sections
contrôlées demandent 5 à 9 itérations de Bresler.

### Étape 4 (synthèse)

`data/examples/lot39_poutre/synthese.md` et `synthese.csv`. Sur toute la
longueur, l'aire retenue par face est un **minimum** : As,min 7.3.2 = 67,79 cm²
(faces AY) et 91,28 cm² (faces AZ, σs borné à 160 MPa car φ*s = 25,8 mm dépasse
le tableau 7.2N), au-dessus de 9.2.1.1 (56,08 et 54,25 cm²) et de l'enveloppe de
`CALC_FERRAILLAGE` (45,13 cm² au plus). Effort tranchant et torsion : béton seul
suffisant (6.31) dans toutes les sections sous les 9 combinaisons ELU, cadres
minimaux 13,25 cm²/m (b_w = 1,40) et 23,66 cm²/m (b_w = 2,50) ; critère de bielle
(6.29) au plus 0,100. Aucun verdict de conformité : premier jet sous les
hypothèses de la fiche.

### Étape 5

`data/examples/lot38_essais/ligne_comparaison_mm.csv` : 10 lignes (4 essais du
lot 38 avec D19, 3 sections × 2 plans de flexion), une ligne par plan de
flexion, h, b, ds, di, état limite, face tendue et face comprimée en toutes
lettres ; colonnes de MM vides.

### Étape 6 (plaque)

| Instant | Code_Aster (m²/m) | Prédiction | Verdict |
| --- | --- | --- | --- |
| `mxx_p` | DNSXS = 1,044823812257e-03 | 1,044824e-03 (bloc rectangulaire) | réussite (4e-13) ; **MXX > 0 tend la face supérieure** |
| `mxx_m` | DNSXI = 1,044824e-03 | idem | réussite |
| `nxx_t_mxx` | DNSXS = 2,3e-03 ; DNSXI = DNSYI = 5,687521e-05 | 2,3e-03 et 0 | **échec** sur la face opposée et en Y (cas dégénéré e = h/2 − c) ; face tendue exacte |
| `nxx_c_mxx` | 0 | 0 | réussite |
| `nxx_t` | DNSXI = DNSXS = 1,15e-03 | 1,15e-03 | réussite |
| `mxx_mxy` | X : 0 / 1,533205e-03 ; Y : 2,555054e-04 / 5,564423e-04 | Wood-Armer X 1,585371e-03, Y 5,166373e-04 | sans seuil : −3,3 % en X |
| `mxy` | X 4,709510e-04, Y 5,623236e-04 par nappe | Wood-Armer 5,166373e-04 | sans seuil : −8,8 % / +8,8 % |

## Lecture

- Fait : `CALC_FERRAILLAGE` en 1D reproduit à 1e-13 le module indépendant à
  l'ELU (flexion simple et composée, points intérieurs, flexion déviée par la
  procédure de Bresler de `R7.04.05`) et une formule d'effort tranchant/torsion
  entièrement identifiée (θ = 21,8°).
- Fait : les minima de `FERR_MIN='EC2'` ne sont justes qu'en MPa ;
  `FERR_MIN_FISS` est refusé pour les poutres.
- Fait : l'ELS caractéristique 1D s'écarte de 0,25 % à 16 % du calcul par pivot
  acier de `R7.04.05` refait à la main ; cause non établie.
- Déduction : la procédure de Bresler par pas de 10 % double presque l'aire
  (×2,14) sous deux moments égaux et se déclenche pour un moment secondaire
  infime ; les aires de la poutre en portent la trace (5 à 9 itérations).
- Déduction : sur cette poutre massive, le minimum de maîtrise de la fissuration
  (7.3.2) gouverne sur toute la longueur ; la valeur des faces AZ dépend d'une
  lecture bornée du tableau 7.2N (φ*s hors tableau) et de Act = b h/2 : ces deux
  choix sont de la session, à examiner par MM.
- Recommandation : conduire tout calcul `FERR_MIN` en MPa et mm ; ne pas lire
  les aires ELS 1D de `CALC_FERRAILLAGE` comme une référence sans contre-calcul.

## Limites

- Tableau 7.2N transcrit par la session depuis la norme, non confronté à un
  exemplaire : à vérifier par MM.
- 7.3.2 appliqué à toutes les faces (majorant), avec Act = b h/2 et kc = 0,4 de
  la flexion simple ; ni la répartition des zones tendues le long de la poutre ni
  l'effet de l'effort normal sur kc ne sont traités.
- Cause des écarts ELS (caractéristique et QP) non établie ; module ELS QP non
  calibré.
- γc = 1,2 et γs = 1,0 de l'ELU accidentelle : valeurs recommandées de
  l'EN 1992-1-1 (tableau 2.1N), pas des décisions de MM.
- Plaque : un seul élément, efforts constants ; Capra-Maury non recalculé à la
  main (seule l'approximation de Wood-Armer est comparée, sans seuil).
- Aucune vérification des contraintes d'un ferraillage retenu (VERI_FERRAILLAGE
  n'accepte pas le 1D).
