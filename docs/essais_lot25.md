# Lot 25 — Essai D7 : axes d'orthotropie d'une coque `ELAS_COQUE` verticale

Modèle : `docs/modele_rapport_essai.md`. Niveau visé : D (exécution jusqu'à `FIN`,
comparaison à une solution analytique). Code_Aster 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

## Objet

Établir la donnée `VECTEUR` (ou `ANGL_REP`) qui place l'axe L d'`ELAS_COQUE` selon
Z pour une plaque DKT située dans le plan vertical XZ du repère global de la
décision du point 9 (X le long du quai, Y vers la terre, Z vertical ascendant).

## Fondement documentaire (niveau A, lu avant l'essai)

U4.42.01, opérande `ANGL_REP / VECTEUR` (`get_document_section`) : la projection du
vecteur `V` sur le plan tangent de la coque fournit l'axe `x_l` du repère
« utilisateur » ; `z_l` est la normale ; `y_l = z_l ∧ x_l`. `VECTEUR` donne `V` par
ses coordonnées globales ; `ANGL_REP = (α, β)` le donne par deux angles nautiques
(rotation α autour de OZ, puis β autour de OY₁, X₂ étant l'image de X₁) ; sans l'un
ni l'autre, l'axe global X détermine `x_l` par projection. Le constat du lot 22
(fiche, point 1) établit par exécution que L d'`ELAS_COQUE` est l'axe `x_l`.

**Déduction (non lue telle quelle, à vérifier par l'essai)** : la plaque étant dans
le plan XZ, la projection de `V = (0, 0, 1)` sur son plan tangent est Z ; donc
`VECTEUR = (0, 0, 1)` place L selon Z et T selon X. Pour `ANGL_REP`, si la rotation
β est prise positive de Z vers X, `X₂ = (cos β, 0, −sin β)` : `β = −90°` (avec
`α = 0`) donne `V = Z`. Ce signe est une déduction, non une lecture des figures.

## Critère de réussite (écrit avant l'exécution)

Cas : console verticale dans le plan XZ (X ∈ [0 ; 1] m, Z ∈ [0 ; H], H = 1 m),
encastrée en Z = 0 (six degrés de liberté bloqués), `DRY = 0` bloqué partout (rotation
propre autour de la normale Y, sans raideur en DKT), effort linéique `q = 100 N/m`
selon +Y (perpendiculaire à la plaque) sur l'arête Z = H. Coefficients `ELAS_COQUE`
de la décision 2 v5 en SI (lot 24), dont `FLEX_L = 89,0e6` et `FLEX_T = 11 300`
N·m²/m, soit un rapport 7 876. Deux maillages réguliers de quadrangles, 8 × 8 puis
16 × 16 (raffinement d'un facteur 2).

| Cas | Donnée | Axe L attendu | Référence de la flèche en tête |
| --- | --- | --- | --- |
| D7a | `VECTEUR = (0, 0, 1)` | Z | `w_L = q·H³ / (3·FLEX_L)` |
| D7b (contre-épreuve) | `VECTEUR = (1, 0, 0)` | X | `w_T = q·H³ / (3·FLEX_T)` |
| D7c | `ANGL_REP = (0, −90)` | Z | identique à D7a |

Grandeurs et seuils :

1. **Exacte** (théorie de l'élément : équilibre statique de la console) — moment
   fléchissant nodal `EFGE_NOEU` : `|M(z)| = q·(H − z)` en tous les nœuds, composante
   `MXX` en D7a (flexion selon `x_l` = Z) et `MYY` en D7b (flexion selon `y_l` = Z).
   Seuil : écart maximal ≤ 10⁻⁶·q·H. L'autre composante de flexion, ainsi que `MXY`,
   doivent être ≤ 10⁻⁶·q·H.
2. **Sensible à la discrétisation** — flèche `|DY|` en tête (moyenne des nœuds de
   l'arête) en D7a et en D7b : l'écart relatif à la référence de la ligne du tableau
   doit décroître du maillage 8 × 8 au maillage 16 × 16.
3. **Identification de l'axe** — en D7a et D7b, au maillage 16 × 16, l'écart relatif
   de la flèche à la référence annoncée doit être inférieur au centième de son écart
   relatif à l'autre référence (elles diffèrent d'un facteur 7 876) : une orientation
   inversée est ainsi rejetée sans ambiguïté.
4. **Exacte** (deux écritures d'une même orientation) — D7c égale D7a au maillage
   8 × 8 : écart relatif des flèches en tête ≤ 10⁻⁶.

Toute autre issue est un échec, rapporté tel quel. Le critère n'est pas modifié après
l'exécution.

## Modèle et exécution

Cas produits par `scripts/build_lot25_essais.py` (maillage au format ASTER natif),
résultats extraits des `.mess` versionnés (`data/examples/lot25_essais/mess/`) par
`scripts/analyze_lot25_essais.py` → `analyse.json`. HEAD au moment des exécutions :
`5718698` (arbre modifié : les cas n'étaient pas commités ; `case_sha256` de chaque
source fixe leurs octets). Racine `data/examples/lot25_essais` ajoutée à
`execution.allowed_roots` (`config/validation.yaml`).

Chaîne : validation B (`aster-expert validate`, 14/14 commandes, 0 erreur, pour les
cinq cas) → exécution (`aster-expert run`, statut `completed_ok`, diagnostic `OK`)
→ `.mess`. **Aucune alarme** dans les cinq `.mess`. Niveau atteint : C (exécuté
jusqu'à `FIN`) et D (comparé à une solution analytique) ; aucun essai n'atteint E.

## Résultats

Flèche `|DY|` en tête (moyenne des nœuds de l'arête Z = H ; la flèche est vers +Y,
sens de la charge) :

| Cas | Maillage | Obtenu (m) | Référence (m) | Écart relatif |
| --- | --- | --- | --- | --- |
| D7a `VECTEUR = (0, 0, 1)` | 8 × 8 | 3,745318352061e-7 | `q·H³/(3·FLEX_L)` = 3,745318352060e-7 | 3,2e-13 |
| D7a | 16 × 16 | 3,745318352065e-7 | idem | 1,3e-12 |
| D7b `VECTEUR = (1, 0, 0)` | 8 × 8 | 2,949852508846e-3 | `q·H³/(3·FLEX_T)` = 2,949852507375e-3 | 5,0e-10 |
| D7b | 16 × 16 | 2,949852638258e-3 | idem | 4,4e-8 |
| D7c `ANGL_REP = (0, −90)` | 8 × 8 | 3,745318352061e-7 | `q·H³/(3·FLEX_L)` | 3,2e-13 (égal à D7a) |

Moments fléchissants `EFGE_NOEU` (écart maximal à `q·(H − z)`, rapporté à `q·H`) :
D7a 1,0e-12 (8 × 8), 1,1e-11 (16 × 16), composante `MXX` ; D7b 1,5e-9 puis 4,8e-8,
composante `MYY`. Autre composante de flexion : ≤ 7e-14 (D7a), ≤ 1,9e-8 (D7b) ;
`MXY` ≤ 6e-15 (D7a), ≤ 6,4e-10 (D7b). `QX` = −100 N/m. Signes de `MXX` des deux
sens dans le champ nodal, non exploités.

## Verdict (au regard du seul critère écrit avant l'exécution)

| Critère | Verdict |
| --- | --- |
| 1. Moment exact, ≤ 10⁻⁶·q·H | **Satisfait** (maximum 4,8e-8 en D7b 16 × 16) |
| 2. Erreur de flèche décroissante avec le raffinement | **ÉCHEC**, D7a (3,2e-13 → 1,3e-12) et D7b (5,0e-10 → 4,4e-8) : l'erreur croît |
| 3. Identification de l'axe (écart à la bonne référence < 1/100 de l'écart à l'autre) | **Satisfait** : D7a 1,3e-12 pour 0,9999 ; D7b 4,4e-8 pour 7 875 |
| 4. D7c = D7a à 10⁻⁶ | **Satisfait** (écart nul) |

L'échec du critère 2 est rapporté tel quel et n'est pas absorbé après coup. Le
critère n'est pas modifié.

## Lecture

- **Faits** : `VECTEUR = (0, 0, 1)` place L selon Z pour une plaque du plan XZ ;
  `VECTEUR = (1, 0, 0)` place L selon X (T selon Z) ; `ANGL_REP = (0, −90)` donne le
  même résultat que `VECTEUR = (0, 0, 1)`. La flexion selon `x_l` apparaît en
  `MXX` de `EFGE_NOEU`, celle selon `y_l` en `MYY`. Le rapport des deux flèches
  D7b/D7a vaut 7 876,1066 en 16 × 16 (7 876,1062 en 8 × 8), celui des flexions
  FLEX_L/FLEX_T (7 876,1062) à 4,4e-8 puis 5,0e-10 près.
- **Déduction** (non démontrée) : la flèche de la console est reproduite à la
  précision du solveur ; le critère la classait à tort comme sensible à la
  discrétisation (l'erreur relative ne décroît pas quand elle est de l'ordre de
  l'arrondi). La croissance de l'écart en D7b (5e-10 → 4e-8) relève probablement du
  conditionnement (MEMB_L de 2,9e9 N/m pour FLEX_T de 1,13e4 N·m²/m).
- **Recommandation** : le générateur emploie `VECTEUR = (0, 0, 1)` pour la
  palplanche du plan Y = 0. Une règle de critère pour la prochaine fois : ne classer
  « sensible à la discrétisation » qu'une grandeur dont la théorie prévoit un écart.
- Défaut relevé (lot 24) : `scripts/build_lot24_essais.py`, `plate_mesh`, mélange `n`
  et `N` pour `BORD_XA` et `BORD_YA` ; ces groupes ne portent aucune charge de D6b
  16 × 16, ses résultats ne sont pas touchés. Non corrigé (hors lot).

## Limites

Plans autres que XZ non testés (par exemple YZ) ; normale opposée
(`MODI_MAILLAGE/ORIE_NORM_COQUE`), TRIA3, DST, COQUE_3D, superposition avec la
membrane, maillage irrégulier non testés ; deux maillages par orientation ; une
version (17.4.0) ; aucune référence externe (niveau E). Le signe de `β` d'`ANGL_REP`
est établi pour −90° seulement (+90° donnerait −Z, même axe L, non exécuté).
