# Lot 31 — Jonction tête de tube / poutre de couronnement : cause et candidats

Version Code_Aster : 17.4.0 (image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).
Niveau de validation : **B** pour les quatre candidats de jonction (validés
au catalogue, aucun n'atteint le niveau C) ; **C** pour l'étape 3 (le quai
réduit `sans_poutre` termine tous ses cas de charge sans le défaut
`DISCRETS_26/30/31`, mais échoue ensuite sur un défaut latent sans rapport,
voir plus bas). Le modèle complet n'a pas été relancé (interdit de ce lot).

## Étape 0 : `mcp-check`

```
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs {"query": "STAT_NON_LINE", "k": 1} -> U4.53.01#But
  OK get_document_section {"fragment_id": "U4.53.01#But"} -> level A
  OK get_command_schema {"command": "STAT_NON_LINE"} -> level A
  OK analyze_comm {"comm_path": "..."} -> level A
  OK validate_comm {"comm_path": "..."} -> level B, valid=True
  OK search_test_cases {"command": "AFFE_MODELE", "limit": 1} -> adls102a.comm
  OK read_test_case {"path": "adls102a.comm"} -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.
```

## Étape 1 : cause exacte

### Q1 — Quelles relations LIAISON_SOLIDE écrit-elle, sur quels degrés de liberté ?

Catalogue introspecté (`get_command_schema`, `AFFE_CHAR_MECA`, mot-clé
`LIAISON_SOLIDE`) : `GROUP_NO`, `GROUP_MA`, `SANS_GROUP_MA`, `SANS_GROUP_NO`,
`DIST_MIN`. **Aucun mot-clé ne restreint les degrés de liberté concernés** :
le candidat C1 ne peut donc pas s'écrire avec `LIAISON_SOLIDE` elle-même
(confirme l'énoncé de ce lot).

R3.03.02 (« Conditions de liaison de corps solide ») : la liste des nœuds à
rigidifier est classée en quatre cas selon les degrés de liberté portés
(`#Quels sont les cas de figure traités ?`). Pour un anneau de coque DKT (6
ddl par nœud, voir Q2) et un nœud de poutre POU_D_E (6 ddl), **tous** les
nœuds portent `DX, DY, DZ` et au moins l'un porte `DRX, DRY, DRZ` : c'est le
**cas 3DA**. Le code trouve un nœud A portant tous les degrés de liberté du
solide (ici, n'importe lequel des nœuds convient, anneau ou poutre) et écrit,
pour chaque autre nœud M (`#Traitement des cas 2DA et 3DA`) :

```
DX(M) - DX(A) - DRY(A).z + DRZ(A).y = 0
DY(M) - DY(A) - DRZ(A).x + DRX(A).z = 0
DZ(M) - DZ(A) - DRX(A).y + DRY(A).x = 0
+ si M porte DRX, DRY, DRZ : DRX(M)-DRX(A)=0, DRY(M)-DRY(A)=0, DRZ(M)-DRZ(A)=0
```

Fait établi : chaque nœud d'anneau porte, en plus de ses trois relations de
translation (avec bras de levier), trois relations de **rotation** exacte
avec le nœud de référence — y compris `DRZ(M)-DRZ(A)=0`.

### Q2 — Statut de la rotation propre de la coque (DRZ) en DKT

U3.12.01 (`#Discrétisation`) : les degrés de liberté de discrétisation DKT
sont, à chaque nœud sommet, les six composantes (trois translations, trois
rotations) : `DX, DY, DZ, DRX, DRY, DRZ`. **DRZ est un degré de liberté réel**
(V3.03.108, `#Modélisation I` : « le ddl DRZ a un sens physique de "drilling
rotation" ou rotation autour de la normale »).

R3.07.03 (`#Implantation des éléments de plaque dans Code_Aster`, ligne 42) :

> La valeur CTOR correspond au coefficient que l'utilisateur peut introduire
> pour le traitement des termes de rigidité et de masse suivant la rotation
> normale au plan de la plaque. Ce coefficient doit être suffisamment petit
> pour ne pas perturber le bilan énergétique de l'élément et pas trop petit
> pour que les matrices de rigidité et de masse soient inversibles. Une
> valeur de 10⁻⁵ est mise par défaut.

Fait établi : DRZ ne porte **aucune raideur physique** en flexion de plaque ;
`COEF_RIGI_DRZ` (`DRZ_STIFFNESS_COEF` du générateur, 1e-3, relevé au lot 28)
lui affecte une raideur **délibérément fictive et minimale**, uniquement pour
éviter une matrice singulière — le catalogue documente lui-même ce degré de
liberté comme « à la limite de la singularité » par construction.

### Q3 — Une relation dualisée sur un ddl sans raideur propre produit-elle un multiplicateur indéterminé ?

R3.03.01 (« Dualisation des conditions aux limites », `#Inconvénients de
cette dualisation`, exemple 1) :

> Soit une structure physique qui, par malchance, est « retenue par son
> dernier ddl physique » c'est-à-dire telle que si on ne bloque pas ce ddl,
> la matrice est singulière, et telle que si on le bloque la matrice est
> inversible. L'utilisation d'un degré de liberté de Lagrange λ pour ce
> blocage est impossible. En effet, si on numérote λ avant le dernier degré
> de liberté physique, il y aura un pivot nul au niveau de λ, et si on le
> numérote après (donc en tout dernier degré de liberté), la matrice K_{n-1}
> ne sera pas inversible puisque le blocage n'est pas encore pris en compte.

Fait établi : c'est exactement le cas d'un ddl à raideur fictive minimale
(DRZ) dualisé par une relation linéaire (`LIAISON_SOLIDE`, cas 3DA) — la
documentation décrit ce cas, en toute généralité, comme produisant un pivot
nul **indépendamment de la formulation de la relation**, par un effet de
numérotation globale sur lequel l'utilisateur n'a pas de prise directe.

### Q4 — Un cas test officiel combine-t-il LIAISON_SOLIDE, coques DKT et une poutre transversale ?

`search_test_cases("AFFE_CHAR_MECA", keyword="LIAISON_SOLIDE")` : 69
fichiers. Croisé avec `AFFE_CARA_ELEM/POUTRE` (444 fichiers) et
`AFFE_CARA_ELEM/COQUE` (602 fichiers) : intersection réduite à `sdlx102a.comm`,
`sdlx103a.comm`, `sdnv112a.comm`, `sdnx100c/f/h.comm`, `sslv114b.comm`,
`sslx300a/b/c/d.comm`, `zzzz200a/c.comm`. Lecture de `sdlx102a.comm` (SDLX102,
interaction sol-structure) : un nœud de poutre `POU_D_T` (point `PA0`) est lié
par `LIAISON_SOLIDE` à un groupe de nœuds de coque `DST` (`SBAS1`, une dalle
de fondation) — la même combinaison catalogue (coque à raideur DRZ fictive +
poutre) mais **sans poutre transversale traversant un anneau fermé**, et sans
occurrences multiples sur une poutre continue.

**Aucun cas test officiel ne combine LIAISON_SOLIDE, coques DKT/DST et une
poutre transversale en jonction T sur plusieurs occurrences simultanées.**
La combinaison élémentaire (coque à raideur fictive + poutre, une occurrence)
a un précédent ; sa multiplication sur une poutre continue n'en a pas.

### Constat enregistré (point 3)

Les trois faits ci-dessus, combinés, sont **cohérents avec** (mais non
prouvés seuls par un unique document pour ce cas précis) le pivot nul observé
depuis le lot 28 : `LIAISON_SOLIDE`, cas 3DA, dualise la rotation DRZ des
nœuds d'anneau ; DRZ ne porte, sous DKT, qu'une raideur fictive minimale ;
dualiser une relation sur un tel ddl est le cas pathologique documenté par
R3.03.01. Enregistré comme constat `code_aster` au point 3
(`aster_expert.agent.drafting.record_code_aster_finding`, sources
`DocumentarySource`/`CatalogueSource`, `data/examples/combiwall_inputs/
lot31_facts.json`/`lot31_extraits.json`).

**Ce constat a été précisé, pas invalidé, par l'étape 2 : voir plus bas.**

## Étape 2 : candidats, comparés sur le quai réduit

Quatre candidats définis par ce lot ; deux exécutables (C1, C4), un bloqué
par le catalogue (C2), un inapplicable à cette géométrie (C3). Chaque
candidat exécutable est une option du générateur
(`aster_expert.generation.generate.JunctionCandidate`, outil de diagnostic,
jamais actif par défaut — `method="liaison_solide"` reproduit la production
octet pour octet, vérifié par test) ; aucune édition manuelle du `.comm`.

### C1 — Liaison cinématique limitée aux translations

`LIAISON_SOLIDE` ne permet pas de restreindre les degrés de liberté (Q1) :
implémenté avec `LIAISON_DDL` (U4.44.01, `#Mot-clé LIAISON_DDL`), une
occurrence par relation, écrite nœud par nœud avec le bras de levier exact
(coordonnées analytiques, `aster_expert.meshing.combiwall
.tube_head_ring_points`, nouveau). Pour chaque nœud d'anneau M et le nœud de
poutre A du même tube :

```
_F(GROUP_NO=(M, A, A, A), DDL=("DX","DX","DRY","DRZ"),
   COEF_MULT=(1.0, -1.0, -(z_M-z_A), (y_M-y_A)), COEF_IMPO=0.0)
```
(et les deux relations analogues pour DY et DZ) — **aucune relation de
rotation propre du nœud M** : sa rotation reste libre. Validé niveau B
(80/80 commandes). Exécuté sur le quai réduit :

**Échec identique**, en 29,6 s : `<F> <FACTOR_11>`, pivot nul ligne 3073,
sur les nœuds 441 et 577 (répété trois fois, une occurrence de la relation
en cause). Identifiés par sonde medcoupling autonome (jetable, non
versionnée, mêmes conditions que le lot 28/30) sur le MED du quai réduit :

- Nœud 441 = (2,6 ; 0,71 ; 2,6) — nœud d'anneau, tube de bord côté `SYM_D`
  (X = 2,6), génératrice terre (Y = +0,71, angle 90°).
- Nœud 577 = (2,6 ; 0,34 ; 3,3) — **nœud de poutre**, exactement sur le plan
  `SYM_D` (X = 2,6).

Le nœud de poutre du plan de symétrie est déjà dualisé par `CH_BLOC` (point
7 : `DX = 0`, et sous ce lot `DRY = DRZ = 0` sur le plan entier — voir
« conséquence sur la symétrie » plus bas). Mes relations C1 référencent ce
même nœud (`DRY(A)`, `DRZ(A)`, `DRX(A)`) : la combinaison des deux
dualisations reproduit le mécanisme R3.03.01, cette fois sur le nœud de
**poutre**, pas sur l'anneau.

### C2 — Rayons rigides matériels

**Non réalisable sans modifier le maillage**, constaté avant toute
exécution. Une raideur matérielle réelle (aucune dualisation) exige une
maille `SEG2` support (`AFFE_CARA_ELEM/DISCRET`, `CARA="K_T_D_L"`, entité
« sEG2 », U4.42.01) ou un élément `POU_D_E`/`BARRE` — les deux exigent une
maille de liaison **déjà existante** entre les deux nœuds. `CREA_MAILLAGE`
(catalogue introspecté en entier, `get_command_schema`) ne propose que
`CREA_POI1` pour créer de nouvelles mailles à partir de nœuds existants
(des mailles ponctuelles, jamais des segments) ; aucun mot-clé ne crée une
maille `SEG2` entre deux nœuds existants non reliés. Créer les rayons
exigerait donc une géométrie ou un maillage Salomé modifiés, interdit par ce
lot (« aucune modification manuelle du maillage »). **Non exécuté.**

### C3 — Raccord coque-poutre documenté (LIAISON_ELEM, OPTION='COQ_POU')

**Inapplicable à cette géométrie**, établi par la documentation (R3.03.06,
« Liaison coque-poutre », `#Utilisation`) avant toute exécution : la commande
exige `S`, la trace de la section droite de la poutre sur la coque — « la
liste des mailles linéiques (affectées d'éléments 'bord' de modélisation
coque) qui représentent géométriquement cette section » — et un vecteur
d'axe `V` « orienté de la coque vers la poutre ». C'est la géométrie d'une
poutre **dans le prolongement** d'une coque (le cas test associé, SSLX101,
encastre une coque tubulaire mince sur un élément ponctuel à son extrémité).
La poutre de couronnement du quai est **transversale** : elle traverse un
anneau fermé (la tête de tube), sans bord libre qui en représenterait la
section, et ne se prolonge pas depuis la coque. **Non exécuté** — le
résultat est documentaire.

### C4 — Nœud unique partagé (réponse à la remarque de MM sur un maillage coïncident)

La poutre et l'anneau ne partagent aucun nœud existant du maillage (Y = 0,34
contre Y = ±0,71 ; Z = 3,3 contre Z = 2,6) : implémenté en réduisant
`LIAISON_SOLIDE` à **un seul nœud d'anneau** par tube — celui de plus grand Y
(génératrice terre, le point déjà utilisé comme référence de normale au
point 5) — plutôt que l'anneau entier. Validé niveau B (80/80). Exécuté :

**Échec identique**, en 24,3 s : `<F> <FACTOR_11>`, pivot nul ligne 999, sur
les nœuds 575 et 147 :

- Nœud 575 = (-2,6 ; 0,34 ; 3,3) — nœud de poutre, sur le plan `SYM_G`
  (X = -2,6).
- Nœud 147 = (-2,6 ; 0,71 ; 2,6) — le nœud d'anneau unique choisi pour ce
  tube (génératrice terre), tube de bord côté `SYM_G`.

Même schéma que C1, à l'inverse (plan `SYM_G` au lieu de `SYM_D`) : le nœud
de poutre du plan de symétrie, déjà dualisé par `CH_BLOC`, est de nouveau
dualisé par `LIAISON_SOLIDE` (cas 3DA, deux nœuds seulement — la réduction à
un seul nœud d'anneau **ne réduit pas la multiplicité des occurrences**, qui
reste une par tube).

### Conséquence sur la condition de symétrie (point 7)

Pour C1 et C4, la scission `GEN_SYMG_RING`/`GEN_SYMD_RING` du point 7 (lot
28 : elle retient la rotation de l'anneau de `LIAISON_SOLIDE` seule) n'a plus
de raison d'être — ni C1 ni C4 ne dualise la rotation propre d'un nœud
d'anneau. `aster_expert.generation.comm.symmetry_and_support_block` reçoit
un nouveau paramètre `split_ring_rotation` : `True` (défaut, méthode
`liaison_solide`, reproduit la production à l'identique, vérifié par test)
impose `DRY = DRZ = 0` sur la part hors anneau du plan de symétrie
seulement ; `False` (candidats C1/C4) l'impose sur le plan entier, y compris
le nœud de poutre qui s'y trouve — **c'est précisément ce nœud, ainsi
dualisé, que C1 et C4 redualisent chacun à leur tour**, révélant le même
mécanisme sur un ddl différent de celui du lot 28.

### Tableau de comparaison

| Candidat | Aboutit | Grandeurs relevées | Hypothèse mécanique | Coût (exécution) | Conséquence pour la fiche |
| --- | --- | --- | --- | --- | --- |
| Production (`LIAISON_SOLIDE`, masse corrigée) | Non | — (`<F> <FACTOR_11>`, ligne 230, nœuds 575/13) | Corps rigide, anneau entier ; dualise la rotation de chaque nœud d'anneau (R3.03.02 cas 3DA) | 26,5 s | Aucune (référence) |
| C1 (`LIAISON_DDL`, translations) | Non | — (`<F> <FACTOR_11>`, ligne 3073, nœuds 441/577) | Translations seules, bras de levier exact ; dualise quand même DRX/DRY/DRZ du nœud de **poutre** | 29,6 s | Ne lève pas la cause ; touche un ddl différent (poutre, pas anneau) |
| C2 (rayons rigides) | Non exécuté (bloqué) | — | Raideur matérielle, aucune dualisation | 0 s | Sans objet : exigerait un maillage modifié |
| C3 (`LIAISON_ELEM`/`COQ_POU`) | Non applicable | — | Raccord coque-poutre en prolongement | 0 s | Sans objet : géométrie en T incompatible |
| C4 (nœud unique) | Non | — (`<F> <FACTOR_11>`, ligne 999, nœuds 575/147) | Corps rigide réduit à un point de contact | 24,3 s | Ne lève pas la cause ; la multiplicité d'occurrences (une par tube), pas la taille de l'anneau, est en jeu |

**Aucun candidat n'atteint le niveau C.** Aucune grandeur physique
(déplacement, effort en tête de poutre, ovalisation de l'anneau) n'a donc pu
être relevée pour aucun candidat — la comparaison porte sur le mécanisme et
l'échec, non sur un résultat.

## Étape 3 : masse des ressorts sous pesanteur

U4.42.01 (`AFFE_CARA_ELEM`, mot-clé `DISCRET`) : pour un `DIS_T` (matrice de
masse diagonale, nœud ou `POI1`), `CARA="M_T_D_N"` prend **1 terme** (la
masse). Confirmé par l'exécution du lot 30 (`<F> <DISCRETS_26>`, « Vous
utilisez la matrice de MASSE pour un discret MECA_DIS_T_N alors que vous
n'avez pas affecté les caractéristiques de masses. Par défaut la masse est
nulle. »). Un ressort est un appui, pas de la matière (CLAUDE.md, ce lot) :
correction dans `aster_expert.generation.comm.model_and_cara_block`, une
occurrence `_F(GROUP_MA=(<classe>,), CARA="M_T_D_N", VALE=(0.0,))` par classe
de raideur, à côté de `K_T_D_N` — masse **explicitement** nulle, jamais
omise. Test ajouté (`test_springs_carry_an_explicit_zero_mass`).

Vérifié sur un essai minimal (quai réduit, variante diagnostic
`sans_poutre` — la seule à atteindre l'assemblage sous `PESANTEUR` avant ce
lot, `LIAISON_SOLIDE` arrêtant systématiquement l'exécution plus tôt) :
régénérée avec le générateur corrigé, validée niveau B (80/80), exécutée.
**Plus aucun `<F> <DISCRETS_26/30/31>`** : les cinq cas de charge (G, EAU_P,
EAU_A, Q1, A) atteignent chacun `MECA_STATIQUE`, `CALC_CHAMP` et
`POST_RELEVE_T` sans erreur — la correction fonctionne.

### Défaut latent découvert et corrigé (sans rapport avec la masse)

L'exécution a atteint, pour la première fois, `IMPR_RESU` (jamais atteint
avant ce lot, le pivot `FACTOR_11` arrêtant systématiquement l'exécution
avant) et échoué : `<F> <MED2_14>`, « On essaie d'imprimer le champ
SIEF_ELGA au format MED mais pour l'élément de type MEDKQU4 ce champ
contient des sous-points. On a besoin du CARA_ELEM ... ». Corrigé
(`aster_expert.generation.comm.footer`, `CARA_ELEM=CARA` sur chaque
occurrence de `RESU`, la solution que le message d'erreur suggère
lui-même, confirmée par le catalogue `IMPR_RESU/RESU/CARA_ELEM`, condition
`FORMAT='MED'`). Test ajouté
(`test_impr_resu_carries_cara_elem_for_every_result`). Ce défaut touchait le
générateur de **production** (`footer()` est partagé, sans condition liée à
`sans_poutre`) : sans cette correction, le modèle complet aurait échoué au
même endroit dès que `LIAISON_SOLIDE` serait un jour corrigée.

### Défaut latent découvert, non corrigé (hors périmètre de ce lot)

Ré-exécuté après la correction ci-dessus : nouvel échec, sans rapport avec
la masse des ressorts ni avec `LIAISON_SOLIDE`. `<F> <MED2_4>` : « Le champ
'RESU_EAUDEPL' est déjà présent dans le fichier MED pour l'instant 0. » —
une collision de nom entre les champs `DEPL` des résultats `RESU_EAU_P` et
`RESU_EAU_A` à l'écriture MED (`IMPR_RESU`). **Non corrigé** : sans rapport
avec la décision de jonction ou la masse des ressorts, hors du périmètre
explicite de ce lot. Comme la correction `CARA_ELEM` ci-dessus, ce défaut
touche `footer()` (production, tous les cas de charge) : **il bloquera le
niveau C du modèle complet même une fois la jonction corrigée**, jusqu'à
correction dans un prochain lot (par exemple, ne pas exporter `DEPL` en
double, ou nommer les champs autrement).

## Ce que chaque candidat impliquerait pour la fiche

- **Production (`LIAISON_SOLIDE`)** : décision 4 (point 3) désormais en
  révision (voir ci-dessous) ; aucun changement de contenu.
- **C1 (`LIAISON_DDL`)** : s'il aboutissait un jour (après correction de la
  cause touchant le nœud de poutre du plan de symétrie), remplacerait la
  décision 4 et ajouterait ~2 × (nombre de nœuds d'anneau × 3 tubes) lignes
  `LIAISON_DDL` par tranche du modèle complet (plus verbeux que
  `LIAISON_SOLIDE`, mais sans dualiser la rotation de l'anneau) ; nouveaux
  groupes `GEN_J1_<tube>_<nn>` (un par nœud d'anneau, jamais par le
  générateur de production actuel).
- **C2 (rayons rigides)** : impliquerait une refonte du maillage Salomé
  (nouvelles mailles `SEG2`), hors de portée d'une simple option du
  générateur — étude de faisabilité distincte nécessaire avant tout essai.
- **C3 (`LIAISON_ELEM`/`COQ_POU`)** : sans objet pour cette géométrie en T ;
  ne serait pertinent que si la poutre était reconstruite en prolongement
  d'un bord de coque ouvert, changement de conception majeur.
- **C4 (nœud unique)** : plus proche de la piste de MM (maillage
  coïncident), mais l'anneau n'est alors plus tenu — l'échec observé montre
  que la remarque de MM (coïncidence) ne suffit pas à elle seule à éviter la
  cause, qui touche la poutre, pas l'anneau.

**Aucun candidat n'est retenu.** La piste recommandée aux lots 28 et 30 reste
la plus prometteuse et n'a pas été essayée ce lot : `LIAISON_ELEM`
(`OPTION='3D_POU'`/`'2D_POU'`, R3.03.03, un mécanisme distinct de la relation
de corps rigide générique) mériterait sa propre étude de faisabilité — mais
la cause précisée ici (le nœud de poutre du plan de symétrie, pas seulement
l'anneau) devrait aussi être prise en compte dans cette étude.

## Coût

- 5 exécutions Code_Aster réelles (`aster-expert run`, quai réduit) :
  26,5 + 29,6 + 24,3 + 49,7 + 40,2 = **170,3 s cumulées**
  (`data/examples/lot31_jonction/rapports/executions.json`).
- 1 sonde `medcoupling` autonome, jetable, non versionnée (identité des
  nœuds des candidats C1 et C4, un seul MED lu, les deux lectures de nœuds
  faites sur le même dump).
- Aucune exécution Salomé (maillage réduit du lot 30 réutilisé tel quel,
  mêmes paramètres, cache de maillage encore valide).
- Aucune relance du modèle complet (interdit de ce lot, respecté).

## Résultats des sept commandes de contrôle

```
$ aster-expert mcp-check
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.

$ ruff format --check
208 files already formatted

$ ruff check
All checks passed!

$ pytest tests/unit
797 passed

$ pytest
824 passed

$ mypy src
Success: no issues found in 77 source files

$ mypy
Success: no issues found in 137 source files
```

## Limites connues

- La cause reste une **déduction documentaire**, cohérente avec toutes les
  observations (lots 28, 29, 30, 31) mais non énoncée telle quelle par un
  document unique pour ce cas précis ; le mécanisme précis de numérotation
  interne de Code_Aster (R3.03.01 le nomme, ne le détaille pas
  algorithmiquement) reste hors de portée des sept outils MCP de ce projet,
  exactement comme aux lots 28 et 30.
- C1 et C4 échouent tous deux sur le **nœud de poutre** du plan de symétrie,
  jamais sur l'anneau : la piste « exclure ce nœud de la dualisation de
  rotation de `CH_BLOC` » n'a pas été testée (hors périmètre explicite de ce
  lot, qui prescrivait quatre candidats précis, pas une correction).
- C2 n'a fait l'objet d'aucune tentative d'exécution (bloqué par le
  catalogue avant tout essai) ; l'hypothèse « aucune maille SEG2 créable
  entre deux nœuds existants » repose sur une lecture exhaustive du schéma
  `CREA_MAILLAGE`, jamais sur un essai réel qui l'aurait confirmée en
  pratique.
- C3 n'a fait l'objet d'aucune tentative d'exécution (jugé inapplicable par
  la documentation seule).
- Le défaut `MED2_4` (collision de nom de champ MED) est nouvellement
  découvert, non corrigé, et bloquera le niveau C du modèle complet même une
  fois la jonction et la masse des ressorts réglées.
- Aucun contrôle D n'a été fait (aucun candidat n'atteint un calcul complet).
