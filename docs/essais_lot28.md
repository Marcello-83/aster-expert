# Lot 28 : décision 12, cinq faits Code_Aster, générateur de `.comm`, exécution niveau C

Version Code_Aster : 17.4.0 (catalogue `b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca`,
image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).
Niveau de validation visé : C (exécution) et D (contrôles physiques). **Niveau
réellement atteint : B** (générateur déterministe, `.comm` confronté au
catalogue sans écart). L'exécution (niveau C) est bloquée par un problème
numérique Code_Aster non résolu dans ce lot ; voir « Étape 4 » et « Limites »
ci-dessous. Aucun contrôle D n'a donc pu être fait.

## Étape 0 : `mcp-check`

```
$ aster-expert mcp-check
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs {"query": "STAT_NON_LINE", "k": 1} -> U4.53.01#But
  OK get_document_section {"fragment_id": "U4.53.01#But"} -> level A
  OK get_command_schema {"command": "STAT_NON_LINE"} -> level A
  OK analyze_comm {"comm_path": "/tmp/aster-expert-mcp-check-xzzjvbrf/minimal.comm"} -> level A
  OK validate_comm {"comm_path": "/tmp/aster-expert-mcp-check-xzzjvbrf/minimal.comm"} -> level B, valid=True
  OK search_test_cases {"command": "AFFE_MODELE", "limit": 1} -> adls102a.comm
  OK read_test_case {"path": "adls102a.comm"} -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.
```

## Étape 1 : décision 12, `PIED_TUBES`, maillage régénéré

- `data/examples/combiwall_inputs/decision12_appui_vertical.md` (copié à
  l'identique depuis `/media/sf_partage/echanges/`) tranche le point 11 (appui
  vertical de l'écran) : DZ bloqué au pied des tubes, aucune autre composante.
  Enregistrée par `_record_decision_12`
  (`data/examples/combiwall_inputs/lot28_enregistrement.json`), recopiée dans
  `data/examples/hypotheses_combiwall_reference_arbitree.json`.
- `PIED_TUBES` (groupe de nœuds, pied des tubes à Z = -26,00) ajouté à la
  convention de nommage (`aster_expert.meshing.combiwall.group_names`) et au
  script Salomé (`scripts/salome/combiwall_mesh.py`), invariant 7×40 + 2×21 =
  322 nœuds (7 tubes pleins à 40 facettes + 2 demi-tubes à 21 nœuds),
  calculé analytiquement par `expected_invariants` avant exécution.
- Le script ayant changé, l'empreinte de script ne correspondait plus à aucun
  MED déjà vérifié (`aster_expert.meshing.run` : « mesh run ne relance pas
  Salomé si l'empreinte du script et celle des paramètres sont identiques à
  celles d'un MED déjà vérifié ») : le maillage a été régénéré
  (`data/processed/mesh_runs/20260922T071600-8d931d77/combiwall_mesh.med`,
  sha256 `1bd724bd5e00…4e33ad0b8`) puis revérifié :

```
$ aster-expert mesh check data/processed/mesh_runs/20260922T071600-8d931d77/combiwall_mesh.med data/examples/combiwall_mesh_invariants.yaml
Rapport mesh check : combiwall_mesh.med
Invariants : 592, tenus : 592, en écart : 0
[OK    ] groupe | groupe PIED_TUBES : présence | attendu : présent | obtenu : présent
[OK    ] groupe | groupe PIED_TUBES : cardinalité | attendu : 322 | obtenu : 322
[OK    ] groupe | groupe PIED_TUBES : boîte englobante (tol. 1e-09) | attendu : (-10.4, 10.4, -0.71, 0.71, -26, -26) | obtenu : identique
[OK    ] plan | groupe PIED_TUBES = nœuds en Z = -26 (tol. 1e-09) | attendu : 322 nœuds du plan | obtenu : 322 nœuds du groupe, 322 dans le plan
Tous les invariants sont tenus.
```

Niveau C (lecture MED par `medcoupling`, sans Salomé, sans Code_Aster) : les
592 invariants, PIED_TUBES compris, sont tenus.

## Étape 2 : cinq faits Code_Aster (six constats enregistrés)

Chaque constat est établi par confrontation au catalogue
(`get_command_schema`) et/ou à la documentation (`search_codeaster_docs` +
`get_document_section`), avec au moins un cas test officiel lu par
`read_test_case`, jamais depuis la mémoire du modèle. Deux constats
remplacent des placeholders minces du lot 14 (`replaces_topic`, sources
conservées) ; les autres sont nouveaux. Tous enregistrés au point indiqué de
la fiche par `scripts/build_combiwall_reference.py::_lot28_facts`.

| Point | Sujet | Constat retenu | Cas test officiel |
| --- | --- | --- | --- |
| 3 | Liaison de corps solide anneau ↔ nœud de poutre | `LIAISON_SOLIDE`, `GROUP_NO=(anneau, nœud de poutre)`, une occurrence par tube | `sdlx03b.comm` |
| 5 | Pression fonction de Z sur coque DKT | `AFFE_CHAR_MECA_F`/`FORCE_COQUE`/`PRES=FORMULE(NOM_PARA='Z',...)` (jamais `PRES_REP`, absent de la liste DKT) | `ssls118a.comm`, `ssls100b.comm` |
| 5 | Orientation cohérente des normales (positive côté bassin) | `MODI_MAILLAGE`/`ORIE_NORM_COQUE`, `VECT_NORM=(0,1,0)` depuis un nœud de référence au point où la normale géométrique vaut exactement (0,1,0) | `sdls118a.comm` |
| 5 | Profil discontinu : points doublés à Z ± 0,001 m | Calcul géométrique propre (aucune interface de couche à moins de 1 mm d'un point d'intégration FPG1/4/9 du QU4, R3.01.01) | — (propriété géométrique, pas un usage de commande) |
| 7 | Symétrie X = constante, DKT + POU_D_E | `DDL_IMPO(DX=0, DRY=0, DRZ=0)` sur le plan, sextuplet DX…DRZ identique pour DKT et POU_D_E (U3.12.01/U3.11.01) | `ssls100b.comm` (DKT ; POU_D_E par identité documentée, non testé) |
| 2 | Barre : section, matériau, pas de rotation | `AFFE_MODELE(MODELISATION="BARRE")`, `AFFE_CARA_ELEM/BARRE/SECTION="GENERALE"`, aucun DDL de rotation porté par la maille barre (U3.11.01) | `comp009a.comm` |

Aucun fait n'a manqué : les six constats ci-dessus sont tous enregistrés
« tranché » avant génération ; `HypothesesSheet.generation_blockers` était
vide (`_check_facts_present` dans `aster_expert.generation.generate`
confirme les sept sujets requis présents).

## Étape 3 : générateur (`aster_expert.generation`)

`aster-expert generate <fiche> <données> <maillage vérifié>` refuse de
s'exécuter si la fiche n'est pas prête, si un fait de l'étape 2 manque, ou si
le maillage donné ne correspond pas (empreinte script/paramètres) à un MED
confirmé vérifié par `mesh check` (`find_verified_mesh`) — les quatre tests
de `test_generation_generate.py` couvrent ces trois refus plus le cas
nominal.

### Structure du `.comm` (2410 lignes)

Un bloc par fonction de `aster_expert.generation.comm`, dans l'ordre où
`generate_comm` les assemble : en-tête (version + trois hachages sha256),
préparation du maillage (groupes `GEN_`, `CREA_POI1`, `ORIE_NORM_COQUE`),
`AFFE_MODELE`/`AFFE_CARA_ELEM` uniques, quatre `DEFI_MATERIAU`,
`LIAISON_SOLIDE`, symétrie et appuis, quatre `DEFI_FONCTION`, cinq charges de
pression/force, puis pour chacun des six cas élémentaires (G, EAU_P, EAU_A,
Q1, Q3, A) : `MECA_STATIQUE`, `CALC_CHAMP`, les contrôles D
(`POST_RELEVE_T` ressorts/réactions/symétrie), et pour G et Q3 l'ordre de
grandeur. Chaque commande porte, en commentaire immédiatement au-dessus ou à
côté, le point de la fiche et le constat ou cas test qui la fonde (voir le
fichier lui-même, jamais reproduit ici pour ne pas dupliquer une source
versionnée).

### Classes de ressorts et invariant

`aster_expert.meshing.combiwall.spring_node_areas` donne l'aire tributaire
projetée exacte de chaque nœud côté bassin (Y ≤ 0) ; `aster_expert.generation
.springs.build_spring_classes` regroupe les nœuds de raideur identique (48
classes, préfixe réservé `GEN_RESS_<ARGI|MARNE>_NN`) et
`check_spring_sum` vérifie, avant toute écriture, que la somme des raideurs
de chaque bande reproduit exactement k_h × largeur × hauteur :

```
RESS_AV_ARGI  : 35 × 20.80 × 6.00 = 4368.0            obtenu : 4367.999999999996
RESS_AV_MARNE : 80 × 11.36 × 8.00 = 7270.4            obtenu : 7270.3999999999905
```

(écart relatif ≤ 7×10⁻¹⁵, bruit de calcul flottant, tolérance du test
1×10⁻⁹).

### Groupes créés par le générateur : mécanisme et limite rencontrée

Le mécanisme initial (une occurrence `ENV_SPHERE` par nœud de ressort,
~10 600 occurrences) produisait un `.comm` de 1,37 Mo/11 000 lignes qui a fait
perdre la connexion au serveur MCP lors d'un `analyze_comm` (« Connection
closed »). Remplacé par un mécanisme par colonne (`ENV_CYLINDRE`, une
occurrence par colonne (X, Y) plutôt que par nœud) croisé avec la ligne haute
ou basse de la bande (`PLAN`) ou son complément
(`INTERSEC`/`UNION`/`DIFFE`), établi sur `zzzz106a.comm` (trouvé via
V1.01.106) : ~2 070 lignes/265 Ko pour le même résultat. Deux classes
« mixtes » (nœuds à la fois sur une ligne de bord et à l'intérieur de la
bande) retombent sur un `ENV_SPHERE` par nœud, chacun sous un nom distinct
(voir « Erreurs rencontrées » ci-dessous — la première version de ce
mécanisme réutilisait le même nom pour chaque nœud d'une classe mixte, ce qui
échoue).

Toute limite Code_Aster utilisée ici vient d'une exécution réelle, jamais de
la mémoire du modèle : voir « Erreurs rencontrées et corrigées ».

### Déterminisme

`test_generation_is_deterministic` régénère deux fois le même `.comm` à
partir des mêmes fiche/données/empreinte de maillage : textes et rapports de
génération strictement identiques (formatage des flottants par
`repr(float(x))`, ordre stable des occurrences).

## Étape 4 : validation niveau B, tentative d'exécution niveau C

### Validation niveau B

```
$ aster-expert validate_comm data/examples/lot28_quai/quai_combiwall.comm
valid: true, errors: [], warnings: []
commands_checked: 80/80, commands_not_checked: []
```

Les 80 instructions (DEBUT, LIRE_MAILLAGE, 2×DEFI_GROUP, CREA_MAILLAGE,
MODI_MAILLAGE, AFFE_MODELE, AFFE_CARA_ELEM, 4×DEFI_MATERIAU, AFFE_MATERIAU,
2×AFFE_CHAR_MECA, 4×DEFI_FONCTION, 5×AFFE_CHAR_MECA(_F), 6×MECA_STATIQUE +
CALC_CHAMP + 3×POST_RELEVE_T/IMPR_TABLE par cas, IMPR_RESU, FIN) sont toutes
syntaxiquement conformes au catalogue de la version cible. **Ceci est un
fait de niveau B : cela ne dit rien de l'exécution.**

### Tentative d'exécution (niveau C) : bloquée

```
$ aster-expert run data/examples/lot28_quai/quai_combiwall.comm
Statut : failed
Diagnostic : <F>_ERROR  (<F> <FACTOR_11> : pivot nul, degré de liberté de
  Lagrange associé à une relation linéaire entre plusieurs degrés de liberté)
```

Rapport complet et extrait pertinent du listing (fort.6, 157 641 lignes au
total, non versionné intégralement) déposés dans
`data/examples/lot28_quai/rapports/execution_report.json` et
`data/examples/lot28_quai/rapports/mess_case_g_extrait.txt`.

Le premier cas (G) échoue systématiquement à la factorisation MUMPS, avant
tout calcul, sur une relation linéaire impliquant le nœud de poutre d'un tube
et un nœud de l'anneau de tête de ce même tube (`LIAISON_SOLIDE`, point 3).

**Démarche de diagnostic (sept exécutions réelles, niveau C, jamais depuis la
mémoire du modèle) :**

1. Premier échec : `GEN_BNDPART_RESS_AV_ARGI_BAS`/`_HAUT` (28/29 caractères)
   tronqués silencieusement par Code_Aster à 24 caractères identiques
   (`GEN_BNDPART_RESS_AV_ARGI`), provoquant un doublon (`<F> <SOUSTRUC_37>`,
   « le groupe … existe déjà »). Cette limite (24 caractères, silencieuse,
   absente du schéma catalogue où `NOM` est un simple `TXM` sans longueur
   déclarée) n'est visible qu'à l'exécution. **Corrigé** : tous les noms de
   groupe du générateur raccourcis (suffixe de bande au lieu du nom complet),
   plus un garde-fou (`aster_expert.generation.comm._gn`) qui refuse à la
   génération tout nom dépassant 24 caractères.
2. Deuxième échec, même mécanisme : le repli par nœud des classes de
   ressorts « mixtes » réutilisait le même `NOM=` pour chaque nœud d'une
   classe — la deuxième occurrence d'un nom déjà créé échoue à l'identique.
   **Corrigé** : un nom temporaire distinct par nœud, réunis ensuite par
   `UNION` (comme pour les classes non mixtes).
3. Troisième échec : `<F> <FACTOR_11>`, pivot nul sur une relation de
   Lagrange entre l'anneau de tête et le nœud de poutre d'un tube de bord
   (celui dont deux nœuds d'anneau sont exactement sur le plan de symétrie
   X = constante) — le même nœud recevait à la fois la rotation du plan de
   symétrie (`DRY`/`DRZ` = 0, imposée directement) et celle du corps rigide
   (`LIAISON_SOLIDE` lie la rotation de chaque nœud d'anneau à celle du nœud
   de poutre, R3.03.02 « Traitement des cas 2DA et 3DA » : chaque nœud portant
   `DRX`/`DRY`/`DRZ` reçoit une relation `DRZ(nœud) = DRZ(référence)`, en plus
   des relations de translation) — la même information imposée deux fois de
   façon linéairement dépendante. **Corrigé** : la part du plan de symétrie
   qui coïncide avec l'anneau (`GEN_SYMG_RING`/`GEN_SYMD_RING`,
   `INTERSEC`/`DIFFE` avec `TETE_TUBE_01`/`09`) ne reçoit plus que la
   translation (DX) ; la rotation (DRY, DRZ) reste sur le reste du plan
   (`GEN_SYMG_ROT`/`GEN_SYMD_ROT`). Nombre de couples de Lagrange réduit de
   7358 à 7342, cohérent avec la suppression de relations redondantes.
4. Quatrième échec, nœuds différents (2263, 2120 seulement, au lieu de
   2263, 2120, 2120, 2120) : une relation de Lagrange **différente et
   toujours présente** entre le même type de paire (poutre, anneau), sur un
   nœud d'anneau qui n'est *pas* sur le plan de symétrie. `COEF_RIGI_DRZ`
   (rigidité fictive de la rotation de flambement d'une coque DKT, U4.42.01 :
   « nécessaire pour empêcher que la matrice de rigidité soit singulière »,
   valeur par défaut du catalogue 1×10⁻⁵) porté sur `TUBES` et `PALPS` ; sans
   effet sur ce point précis (voir point 6 ci-dessous).
5. Une reproduction isolée (tube 9 + panneau de palplanche voisin +
   `LIAISON_SOLIDE`, sans les ~10 400 éléments `DIS_T` de ressort) aboutit
   sans erreur (`completed_ok`) après relâchement de `SOLVEUR/RESI_RELA`
   (défaut MUMPS 1×10⁻⁶, relâché à 1×10⁻⁴ — un autre écart réel, `<F>
   <FACTOR_57>`, distinct de l'écart de pivot). Étendue aux neuf tubes et à
   leurs neuf `LIAISON_SOLIDE`, plus `TIRANTS`/`ANCRAGES` : toujours sans
   erreur. **Seule l'adjonction des ~10 400 éléments `DIS_T` (points 4)
   reproduit l'échec** sur le modèle complet.
6. `COEF_RIGI_DRZ` porté de 1×10⁻⁵ à 1×10⁻³ (deux ordres de grandeur, encore
   cinq à huit ordres de grandeur sous la rigidité réelle de l'acier ou des
   ressorts) : **échec strictement identique**, même diagnostic, mêmes deux
   nœuds. Un authentique problème de conditionnement (pivot relatif marginal)
   aurait dû réagir à un tel changement ; l'absence totale de réaction exclut
   `COEF_RIGI_DRZ` comme cause et indique une relation exactement dépendante,
   non un simple mauvais conditionnement.
7. Exclusion du nœud d'anneau incriminé du seul tube 9
   (`LIAISON_SOLIDE(..., SANS_GROUP_NO=(...))`, mécanisme documenté à cet
   effet, U4.44.01) : l'échec réapparaît **au même diagnostic, sur une autre
   paire de nœuds** (un autre tube). Ce comportement de « chaise musicale »
   confirme un problème **systémique** (présent, à l'identique, pour chacun
   des neuf `LIAISON_SOLIDE`), non local à un nœud ni à un tube particulier.

**Fait établi (niveau C, sept exécutions réelles)** : la combinaison
`LIAISON_SOLIDE` (neuf occurrences, anneau de coque DKT + nœud de poutre) et
un grand nombre d'éléments `DIS_T` par ailleurs sans rapport géométrique avec
les anneaux (les ressorts sont entre Z = -26 et Z = -12, les anneaux à
Z = 2,60) produit, sur ce modèle, un pivot exactement nul lors de la
factorisation MUMPS d'une relation de Lagrange de `LIAISON_SOLIDE`.

**Déduction, non confirmée** : l'origine la plus probable, au vu de
R3.03.02, est le choix interne par Code_Aster du nœud de référence « A » du
corps rigide (« un nœud arbitraire du solide ») parmi les vingt-deux nœuds du
groupe (l'anneau *et* le nœud de poutre portent tous, nominalement, les
mêmes six degrés de liberté DEPL_R) : rien dans la documentation consultée
(U4.44.01, R3.03.02) ne dit selon quel critère ce choix est fait, ni s'il est
sensible au reste de la numérotation du modèle (donc aux ~10 400 nœuds de
ressort ajoutés). Cette hypothèse n'a pas pu être vérifiée par les sept
outils MCP de ce projet (aucun n'inspecte l'algorithme interne d'élimination
de Code_Aster) ; elle est rapportée comme déduction, jamais comme fait.

**Recommandation, non mise en œuvre dans ce lot** : `R3.03.03`/`R3.03.06`
(« Liaison coque-poutre », `LIAISON_ELEM`/`OPTION` dédiée au raccord
coque-poutre) documentent un mécanisme différent, spécifiquement conçu pour
ce raccord plutôt que la relation de corps rigide générique de
`LIAISON_SOLIDE` — piste à examiner dans un prochain lot, avec sa propre
étude de faisabilité (niveau A) avant toute exécution.

**Conséquence** : aucun contrôle D (résultante appliquée, équilibre global,
symétrie, ordre de grandeur) n'a pu être exécuté. Le mécanisme d'analyse
(`aster_expert.meshing.combiwall.expected_pressure_resultant_y`, résultante
Y exacte d'une pression sur `ECRAN_POUSSEE`, en reproduisant ligne à ligne
l'intégration bilinéaire par ligne de maille que Code_Aster effectuerait,
plutôt que l'intégrale continue du profil) a été écrit et n'a pas pu être
exercé faute d'un résultat Code_Aster à comparer.

## Critère de réussite des contrôles D (écrit avant l'exécution, non exercé)

Ce critère était fixé avant toute tentative d'exécution ; il n'a pas été
modifié depuis, et n'a pas pu être appliqué faute d'exécution réussie.

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Résultante appliquée (G, EAU_P, EAU_A, Q1) | Intégrale exacte du profil de pression, discrétisée ligne de maille par ligne de maille (`expected_pressure_resultant_y`) | exacte | 10⁻⁶ relatif |
| Résultante appliquée (Q3, A) | Valeur du chargement ponctuel/surfacique, identité algébrique de construction | exacte | 10⁻⁶ relatif |
| Équilibre global | Somme des `FORC_NODA` (ressorts) + `REAC_NODA` (`ANCRAGES`, `PIED_TUBES`, `SYM_G`, `SYM_D`) = résultante appliquée | exacte | 10⁻⁶ relatif |
| Symétrie | DY, DZ égaux / DX opposés entre nœuds symétriques (`ANC_01`/`ANC_09`, `TETE_TUBE_02`/`08`), DX ≈ 0 sur `BOLLARD` | exacte | 10⁻⁶ relatif |
| Ordre de grandeur (G, Q3) | Déplacement horizontal maximal en tête d'écran | aucun critère (donnée pour MM, CLAUDE.md principe 6) | — |

## Compte rendu des sept commandes de contrôle

```
$ aster-expert mcp-check          -> OK, 7/7 outils identiques au code
$ ruff format --check .           -> 196 files already formatted
$ ruff check .                    -> All checks passed!
$ pytest tests/unit -q            -> 769 passed in 100.77s
$ pytest -q                       -> 796 passed in 42.60s
$ mypy src                        -> Success: no issues found in 77 source files
$ mypy                            -> Success: no issues found in 134 source files
```

## Niveau de validation atteint

**B**, pas C. Le `.comm` généré est déterministe, entièrement fondé sur les
six constats de l'étape 2 et les données du modèle, et intégralement
conforme au catalogue de la version 17.4.0. Il ne s'exécute pas jusqu'à
`FIN` : aucune affirmation de validité physique, d'équilibre ou de
comportement du modèle ne peut être faite sur cette base. Ce lot ne clôt donc
pas l'étape 4 de la fiche méthodologique.

## Limites

- L'exécution niveau C n'a pas abouti : cause immédiate identifiée
  (`LIAISON_SOLIDE` × ~10 400 `DIS_T`, pivot de Lagrange exactement nul,
  systémique sur les neuf tubes), mécanisme sous-jacent non confirmé
  (dépend d'un comportement interne de Code_Aster non documenté dans les
  sources consultées).
- Aucun contrôle D (résultante, équilibre, symétrie, ordre de grandeur) n'a
  été exercé ; le code qui les calcule analytiquement
  (`expected_pressure_resultant_y`) est écrit et testé unitairement sur son
  arithmétique propre, jamais confronté à un résultat Code_Aster réel.
- Le domaine de validité de `COEF_RIGI_DRZ` (point 3, valeur retenue 1×10⁻³)
  n'est pas établi pour ce modèle au-delà de « n'a aucun effet sur cet
  échec » : sa valeur reste dans le `.comm` par prudence physique (une coque
  DKT en a besoin dans l'absolu), mais ne doit pas être présentée comme la
  cause ni la solution du blocage rapporté ici.
- `LIAISON_ELEM`/raccord coque-poutre dédié (R3.03.03, R3.03.06), repéré en
  fin de diagnostic, n'a fait l'objet d'aucune étude de faisabilité : ni
  syntaxe exacte, ni compatibilité avec l'anneau facettisé du point 1, ni cas
  test officiel identifié.
- Les fichiers de diagnostic (reproductions isolées, patch d'exclusion de
  nœud) étaient dans `data/examples/lot28_quai/repro/` et
  `data/processed/runs`/`data/processed/mesh_checks` (ce dernier répertoire
  hors dépôt, `.gitignore`) ; le répertoire `repro/` a été supprimé avant ce
  commit, n'étant qu'un outil de diagnostic jetable, jamais un livrable.
