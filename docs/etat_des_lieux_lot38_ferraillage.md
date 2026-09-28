# État des lieux des commandes de ferraillage de Code_Aster 17.4 (lot 38)

Niveau A (documentaire) et catalogue, complété par des cas tests officiels cités.
Aucun verdict de dimensionnement de l'ouvrage n'est porté ici (CLAUDE.md, interdits
du lot 38).

## 1. Commandes et règlement

| Commande | Nature | Règlement |
| --- | --- | --- |
| `CALC_FERRAILLAGE` (U4.81.42) | opérateur, calcule un champ `FERRAILLAGE`/`FERR_ELEM` à partir des efforts généralisés (`EFGE_ELNO`) d'un `RESULTAT` réentrant | `CODIFICATION = 'EC2'` (Eurocode 2 partie 1-1, défaut) ou `'BAEL91'` |
| `COMBINAISON_FERRAILLAGE` (U4.81.44) | macro-commande, appelle `CALC_FERRAILLAGE` pour chaque cas d'un `RESULTAT` de type `mult_elas`, classés par `COMBINAISON/TYPE` (`ELU_FONDAMENTAL`, `ELU_ACCIDENTEL`, `ELS_CARACTERISTIQUE`, `ELS_QUASIPERMANENT`), et retient par nœud/maille et par type d'armature la combinaison dimensionnante | EC2 ou BAEL91 |
| `POST_COMBINAISON` (U4.81.45) | macro-commande, combine linéairement des résultats (`mult_elas`, `evol_elas`, `mode_meca`) ou des tables selon une table de coefficients, pour produire le `RESULTAT` `mult_elas` que consomment les deux commandes ci-dessus | sans objet (combinaison linéaire, pas de règlement) |
| `VERI_FERRAILLAGE` (U4.81.46) | opérateur, vérifie un ferraillage **existant** (fourni, pas calculé) sous une charge donnée : marge mécanique et taux d'utilisation | EC2 ou BAEL91 ; `TYPE_COMB` limité à `'ELU'`/`'ELS'` (pas d'ELS quasi permanent) |
| `POST_VERI_FERRAILLAGE` (U4.81.47) | macro-commande, diagramme d'interaction de la facette critique après `VERI_FERRAILLAGE` | suit `VERI_FERRAILLAGE` |

Source : `U2.03.07` (« Panorama des outils… ») : « il est possible de calculer le
ferraillage d'une structure pour un cas de charge à l'aide de l'opérateur
CALC_FERRAILLAGE. La méthode utilisée est celle de Capra et Maury et elle est
applicable pour les éléments plaques, coques mais aussi pour les poutres. »

## 2. Types d'éléments acceptés

| Commande | 1D (poutres/poteaux) | 2D (plaques/coques) | volumiques (3D) |
| --- | --- | --- | --- |
| `CALC_FERRAILLAGE` | oui (`TYPE_STRUCTURE='1D'`) | oui (`TYPE_STRUCTURE='2D'`) | **non documenté** |
| `COMBINAISON_FERRAILLAGE` | oui | oui | non |
| `VERI_FERRAILLAGE` | **non** (`AFFE/TYPE_STRUCTURE` catalogue : seule valeur admise `'2D'`, tant en EC2 qu'en BAEL91) | oui | non |

Constat catalogue (`get_command_schema`, VERI_FERRAILLAGE) : le mot-clé
`AFFE/TYPE_STRUCTURE` n'admet que la valeur `'2D'` (`allowed_values: ["2D"]`,
`default: "2D"`), à la différence de `CALC_FERRAILLAGE` et `COMBINAISON_FERRAILLAGE`
où il admet `'1D'` et `'2D'`. Un ferraillage de poutre calculé par
`CALC_FERRAILLAGE` ne peut donc pas être re-vérifié par `VERI_FERRAILLAGE`.

Aucune des trois commandes de calcul de ferraillage ne mentionne, dans son
catalogue ni dans sa documentation (`U4.81.42`, `U4.81.44`, `R7.04.05`), un
mode `TYPE_STRUCTURE='3D'` ou un ferraillage d'éléments volumiques. `R7.04.05`
(résumé, `index.rst`) : « On présentera pour ce fait, en un premier temps,
l'algorithme de calcul des éléments linéiques 1D, pour ensuite examiner celui des
éléments surfaciques 2D de type plaque » — aucune troisième famille n'est
annoncée. Le ferraillage d'un massif 3D n'est pas couvert par ces commandes ;
`U2.03.10` (jonctions de génie civil) et `U2.03.07` orientent, pour des éléments
volumiques, vers une reconstruction de contraintes suivie d'un calcul séparé
(hors périmètre de ce lot).

**Réponse au point demandé par MM** (étape 3.3) : **un élément de poutre `POU_D_T`
n'est pas pris en charge par `VERI_FERRAILLAGE`** (catalogue : `TYPE_STRUCTURE`
figé à `'2D'`). Il **est** pris en charge par `CALC_FERRAILLAGE` et
`COMBINAISON_FERRAILLAGE` via `TYPE_STRUCTURE='1D'` : ces deux commandes ne
distinguent aucune modélisation de poutre par son nom (`POU_D_E`, `POU_D_T`, …) --
elles consomment un champ `EFGE_ELNO` (N, VY, VZ, MT, MFY, MFZ) et les
caractéristiques `AFFE_CARA_ELEM/POUTRE` (section, enrobages), indépendamment de
la modélisation qui a produit ce champ. Le cas test officiel `ssll13d.comm`
confirme l'exécution réelle de `CALC_FERRAILLAGE` sur une poutre `POU_D_T`
(`AFFE_MODELE(..., MODELISATION="POU_D_T")`, `CALC_FERRAILLAGE` appelé sur le
`RESULTAT` produit) et compare ses résultats à des valeurs de référence
analytiques (`REFERENCE="ANALYTIQUE"`) : c'est un précédent officiel exécuté,
pas seulement une lecture de catalogue.

## 3. États limites traités

| Commande | ELU | ELS caractéristique | ELS quasi permanent (wk) |
| --- | --- | --- | --- |
| `CALC_FERRAILLAGE` | oui (`TYPE_COMB='ELU'`) | oui (`'ELS'`) | oui (`'ELS_QP'`) |
| `COMBINAISON_FERRAILLAGE` | oui (fondamental **et** accidentel, coefficients γ distincts) | oui | oui |
| `VERI_FERRAILLAGE` | oui | oui | **non** (`TYPE_COMB` catalogue : `['ELU', 'ELS']` seulement) |

`R7.04.05` distingue les trois critères par état limite (§ Notations et principes
d'équilibre) : « ELU : le critère est le non dépassement des déformations
ultimes du béton comprimé et de l'acier de renforcement. ELS Caractéristique :
le critère est le non dépassement de la contrainte de compression limite du
béton en compression et de la contrainte limite de l'acier de flexion. ELS
Quasi Permanent : le critère est le non dépassement de l'ouverture maximale des
fissures. »

## 4. Paramètres d'entrée

Communs aux trois états limites (`CALC_FERRAILLAGE`, `AFFE`, `CODIFICATION='EC2'`) :
`TYPE_STRUCTURE`, enrobages (`C_SUP`/`C_INF` en 2D, `C_SUP_Y`/`C_INF_Y`/`C_SUP_Z`/
`C_INF_Z` en 1D — un enrobage par face et par axe), `FCK`, `FYK`, `EYS`,
`TYPE_DIAGRAMME` (`'B1'` palier incliné limité, `'B2'` palier horizontal illimité,
défaut), `CLASSE_ACIER` (`'A'`/`'B'`/`'C'`, pivot A à 2,5/5,0/7,5 %), `ALPHA_CC`
(1,0 par défaut en EC2), `FERR_SYME`, `FERR_COMP`, `EPURE_CISA`, `FERR_MIN`.

Spécifiques à l'ELU : `GAMMA_S`/`GAMMA_C` (`CALC_FERRAILLAGE`) ou
`GAMMA_S_FOND`/`GAMMA_C_FOND`/`GAMMA_S_ACCI`/`GAMMA_C_ACCI`
(`COMBINAISON_FERRAILLAGE`, un couple par type de combinaison).

Spécifiques à l'ELS caractéristique : `ALPHA_E` (coefficient d'équivalence
acier/béton, 15 dans l'exemple documenté), `SIGS_ELS`, `SIGC_INF/SUP(_Y/_Z)_ELS`.

Spécifiques à l'ELS quasi permanent : `SIGC_ELS_QP` (limite de fluage non
linéaire du béton, 0,45·fck usuel), `KT` (durée de chargement, 0,6 court terme,
0,4 long terme), `WMAX_INF/SUP(_Y/_Z)` (ouverture limite), `PHI_INF/SUP_X/Y/Z`
(diamètre estimatif des armatures).

`UNITE_CONTRAINTE` (`'MPa'` ou `'Pa'`) fixe conjointement l'unité de longueur
(mm ou m) : à faire correspondre à celle du calcul éléments finis (remarque
explicite de la documentation).

## 5. Sorties

`CALC_FERRAILLAGE`/`COMBINAISON_FERRAILLAGE`, `TYPE_STRUCTURE='1D'` (champ
`FERR_ELEM`, densités en m², par élément) : `AYS`/`AYI` (lit supérieur/inférieur
suivant l'axe Y), `AZS`/`AZI` (suivant Z), `AST` (densité transversale, m²/m),
`ATOT` (longitudinal total), `DNSVOL` (densité volumique totale), `CONSTRUC`
(indicateur de complexité de mise en œuvre, actif seulement si `RHO_ACIER>0`).
Une densité de **−1** signale un cas non résolu (pivot B/C trop comprimé avec
`FERR_COMP='NON'`, flexion déviée sans convergence de l'inéquation de Bresler,
ELS_QP sans convergence de l'itération sur l'ouverture de fissure) : jamais une
valeur physique, toujours un repli documenté.

`TYPE_STRUCTURE='2D'` : `DNSXI`/`DNSXS` (suivant X, face inf/sup), `DNSYI`/`DNSYS`
(suivant Y), `DNSXT`/`DNSYT` (transversal), `DNSVOL`, `CONSTRUC`, et (depuis la
version disponible ici) `ASMINXI`/`ASMINXS`/`ASMINYI`/`ASMINYS` (ferraillage
minimal de maîtrise de fissuration).

`VERI_FERRAILLAGE` : marge mécanique et taux d'utilisation (composition non
approfondie ici, hors du périmètre 1D de ce lot).

`COMBINAISON_FERRAILLAGE` ajoute deux cas au `mult_elas` : `COMB_DIME_ACIER`
(armatures maximales par type, tous nœuds/mailles) et `COMB_DIME_ORDRE` (numéro
d'ordre du cas dimensionnant par nœud/maille et par type d'armature).

## 6. Limites documentées

- ELU en flexion déviée composée (deux moments simultanés) : méthode
  **itérative** (inéquation de Bresler, EC2 §5.8.9), pas un calcul direct ;
  convergence non garantie (`COND_ITER`, densité −1 en échec).
- ELS quasi permanent : itération sur `k_var` par dichotomie, avec un plafond de
  40 halvings documenté dans le module de ce lot (§8) ; la documentation ne
  donne pas elle-même de plafond d'itérations.
- `VERI_FERRAILLAGE` : pas de `TYPE_COMB='ELS_QP'`, pas de `TYPE_STRUCTURE='1D'`.
- Aucune des commandes ne couvre les éléments volumiques (3D) ni les coques
  `COQUE_3D`/`DST`/`Q4G` autrement qu'au même titre que `DKT` (le catalogue ne
  distingue pas la modélisation de coque, comme il ne distingue pas la
  modélisation de poutre) — non vérifié par un cas test dans ce lot.
- Le ferraillage transversal (cisaillement, `AST`) suppose des cadres droits
  (`alpha=90°`) et une section rectangulaire (`b_w = b`), hypothèses fixées par
  l'algorithme, non paramétrables.
- `CALC_FERRAILLAGE` exige que les combinaisons soient pondérées **avant**
  l'appel (remarque 1 de `U4.81.42`, Op_randes/TYPE_COMB) : la commande ne
  pondère jamais elle-même un jeu d'efforts bruts.

## 7. Sources

- `U4.81.42` (But, Syntaxe, Op_randes, Composition_du_champ_produit,
  Erreurs_et_alarmes), `U4.81.44` (But, Op_randes), `U4.81.45` (But, Syntaxe,
  Op_randes), `U4.81.46` (But, Op_randes), `U4.81.47` (But).
- `R7.04.05` (index, Calcul_du_ferraillage_des_poutres_et_poteaux,
  Calcul_du_ferraillage_des_plaques §Capra-Maury, Verification_du_ferraillage).
- `U2.03.07` (Calcul_de_ferraillage).
- Catalogue 17.4.0 (`get_command_schema`) : `CALC_FERRAILLAGE`,
  `COMBINAISON_FERRAILLAGE`, `VERI_FERRAILLAGE`, `POST_COMBINAISON`.
- Cas tests officiels (`search_test_cases`/`read_test_case`, commit
  `50ebc13c70ee9df62faf93ddcb746a3757b3042a`) : `ssll13a/b/c/d.comm` (poutre
  `POU_D_E`/`POU_D_T`, ELU/ELS/ELS_QP), `ssll18a/b.comm` (comparaison à
  `SECTION_ARMATURES`), `ssls134*.comm`, `ssls145a.comm`, `ssls146a/b.comm`
  (plaques/portique DKT + poteaux `POU_D_E`, `COMBINAISON_FERRAILLAGE`),
  `ssls126*.comm`, `ssls135a.comm`, `ssls142*.comm`, `ssls150*.comm`
  (`VERI_FERRAILLAGE`, 2D uniquement), `sslx100c.comm` (jonction coque/poutre,
  ferraillage non exercé dans ce cas).
