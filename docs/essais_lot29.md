# Lot 29 : diagnostic du pivot nul par reproducteur minimal

Version Code_Aster : 17.4.0 (catalogue `b59726e0e698b1b477dc138028defff9c92168ad29b5bdccea4ea859c24c27ca`,
image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).

Le lot 28 avait établi, par sept exécutions du modèle complet du quai, qu'un
pivot de Lagrange exactement nul frappe systématiquement l'une des neuf
occurrences de `LIAISON_SOLIDE` (anneau de tête de tube + nœud de poutre)
dès que les ~10 400 ressorts `DIS_T` sont présents, sans lien géométrique
avec l'anneau touché, et « en chaise musicale » : exclure le nœud incriminé
d'un tube déplace l'échec vers un autre tube. La règle de ce lot est de ne
plus relancer le modèle complet pour chercher la cause, mais de construire
un reproducteur minimal, rapide, versionné, et de faire varier un facteur à
la fois.

## Étape 0 : `mcp-check`

```
$ aster-expert mcp-check
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs {"query": "STAT_NON_LINE", "k": 1} -> U4.53.01#But
  OK get_document_section {"fragment_id": "U4.53.01#But"} -> level A
  OK get_command_schema {"command": "STAT_NON_LINE"} -> level A
  OK analyze_comm {"comm_path": "/tmp/aster-expert-mcp-check-of2kqpu0/minimal.comm"} -> level A
  OK validate_comm {"comm_path": "/tmp/aster-expert-mcp-check-of2kqpu0/minimal.comm"} -> level B, valid=True
  OK search_test_cases {"command": "AFFE_MODELE", "limit": 1} -> adls102a.comm
  OK read_test_case {"path": "adls102a.comm"} -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.
```

Les sept outils MCP attachés à la session ont ensuite été appelés directement
(recherches et lectures de cas tests ci-dessous) : tous répondaient, aucune
reconnexion n'a été nécessaire.

## Étape 1 : reproducteur minimal

`scripts/build_lot29_repro.py` (`data/examples/lot29_repro/`) construit,
entièrement en dehors de tout projet, un tube facetté (rayon 0,71 m, 40
facettes -- valeurs du quai, `data/examples/combiwall_model_data.yaml`),
dont l'anneau de tête est lié par `LIAISON_SOLIDE` à un nœud de poutre
(`POU_D_E`), avec N ressorts `DIS_T` (`K_T_D_N`) plantés sur les propres
nœuds de coque du tube sous l'anneau -- jamais des points isolés : les
ressorts partagent leurs nœuds avec la coque, comme dans le modèle réel.
Maillage en format ASTER natif (`LIRE_MAILLAGE`, `FORMAT="ASTER"`), sans
Salomé ni MED (convention du lot 21, `build_fcoque_essai.py`). Le tube ne
grandit que si N l'exige (une couche supplémentaire de 0,25 m par tranche de
`facettes` ressorts) ; par défaut, sans ressort, il fait 2,00 m -- l'exemple
même des instructions de ce lot.

Quatre facteurs, un à la fois :

- `n_springs` : nombre de ressorts (0 par défaut) ;
- `stiffness_n_per_m` : raideur nodale d'un ressort ;
- `symmetry` : coupe le tube en demi-cercle (-90°..+90°) par un plan X=0,
  la configuration des tubes 1 et 9 du quai (21 nœuds d'anneau au lieu de
  40) ;
- `redundant_bc` : seulement avec `symmetry=True` -- reproduit le
  comportement déjà connu et déjà corrigé en production
  (`aster_expert.generation.comm.symmetry_and_support_block`) en imposant
  DRY=DRZ=0 une seconde fois sur la part d'anneau du plan de symétrie, en
  plus de la rotation que `LIAISON_SOLIDE` y dérive déjà.

Écarts par rapport au modèle réel, assumés et documentés dans le script :
matériau du tube en `ELAS` (pas `ELAS_COQUE`, sans objet ici), une poutre
courte (1,00 m) au lieu de la poutre de couronnement continue à neuf appuis,
une seule classe de raideur au lieu d'un regroupement par bande, et une
charge `FORCE_NODALE` quelconque en bout de poutre plutôt que `PESANTEUR`
(voir « Erreur rencontrée : `DISCRETS_26` » ci-dessous -- ce choix n'est pas
anodin, il évite un piège sans rapport avec le pivot).

Mise au point du reproducteur (trois erreurs de construction, corrigées
avant toute mesure, aucune n'étant le pivot recherché) :

1. **`<F> <MODELISA7_77>`, « le GROUP_MA RESSORTS ne fait pas partie du
   maillage »** : un premier essai plaçait les ressorts sur un `GROUP_NO`
   directement passé à `AFFE_MODELE`, qui exige un `GROUP_MA` (une maille).
   **Corrigé** : `CREA_MAILLAGE`/`CREA_POI1` depuis le `GROUP_NO`, exactement
   le mécanisme du générateur de production
   (`aster_expert.generation.comm.mesh_prep_block`), jamais réimplémenté à
   la main.
2. **`<F> <MODELISA8_14>`, « la maille POI1 ... est incluse dans une
   autre »** : une maille POI1 écrite directement dans le maillage natif, au
   même nœud qu'un QUAD4, est refusée à l'exécution. **Corrigé** : retour au
   mécanisme réel (`CREA_POI1`), point 1 ci-dessus.
3. **`<F> <DISCRETS_26>`/`<DISCRETS_30>`/`<DISCRETS_31>`, « vous utilisez la
   matrice de MASSE pour un discret MECA_DIS_T_N alors que vous n'avez pas
   affecté les caractéristiques de masses »** : `PESANTEUR` calcule sa force
   volumétrique via la matrice de masse, et un `DIS_T` qui ne porte que
   `K_T_D_N` (comme les ressorts du quai, réel et reproducteur) a une masse
   nulle -- une alarme, aggravée en erreur fatale par
   `DEBUT(ERREUR=_F(ALARME="EXCEPTION"))` (identique dans le `.comm` réel).
   Le modèle réel du quai porte pourtant la même configuration
   (`DISCRET=(_F(... CARA="K_T_D_N", ...),)`, sans masse) et une `PESANTEUR`
   identique (cas G) sans jamais atteindre cette alarme d'après
   `docs/essais_lot28.md` : la cause exacte de cette différence n'a pas été
   recherchée, hors sujet de ce lot (le pivot, pas la pesanteur). **Corrigé
   en évitant la question** : le reproducteur charge la poutre par
   `FORCE_NODALE` plutôt que par `PESANTEUR` -- une charge quelconque, comme
   demandé, qui ne touche pas à la matrice de masse.

Validation de niveau B systématique avant toute exécution
(`validate_comm`, `valid: true`, tous les cas de ce lot). Après les
exécutions, `ruff format`/`ruff check` ont demandé un retour à la ligne
purement cosmétique sur quelques lignes générées trop longues (`AFFE_CARA_ELEM`,
`DEFI_MATERIAU`) : les fichiers versionnés sous `data/examples/lot29_repro/`
sont régénérés avec le générateur final et revalidés (niveau B, échantillon
A0/A3/D0/E0), mais ne diffèrent des fichiers réellement exécutés que par ce
formatage (même précédent qu'au lot 27).

## Étape 2 : matrice et résultats

Chaque ligne est une exécution réelle (`aster-expert run`, niveau C),
jamais une prévision. Table complète : `data/examples/lot29_repro/
results.json`.

| Cas | N ressorts | Raideur (N/m) | Symétrie | CL redondante | Résultat | Message |
| --- | --- | --- | --- | --- | --- | --- |
| A0_n0 | 0 | 1e6 | non | non | `completed_ok` | -- |
| A1_n10 | 10 | 1e6 | non | non | `completed_ok` | -- |
| A2_n1000 | 1 000 | 1e6 | non | non | `completed_ok` | -- |
| A3_n10000 | 10 000 | 1e6 | non | non | `completed_ok` | -- |
| B1_klow | 10 000 | 1e2 (÷1e4) | non | non | `completed_ok` | -- |
| B2_khigh | 10 000 | 1e10 (×1e4) | non | non | `completed_ok` | -- |
| C0_sym_n0 | 0 | 1e6 | oui | non | `completed_ok` | -- |
| C1_sym_n | 10 000 | 1e6 | oui | non | `completed_ok` | -- |
| D0_sym_redundant | 0 | 1e6 | oui | **oui** | **`failed`** | `<F> <FACTOR_11>`, pivot nul, Nœuds 189/169 |
| E0_two_units¹ | 10 000 (5 000+5 000) | 1e6 | non | non | `completed_ok` | -- |

¹ Hors des quatre facteurs prescrits : deux unités tube+anneau+poutre
totalement indépendantes (aucun nœud partagé), chacune sa propre occurrence
de `LIAISON_SOLIDE`, un seul pool de ressorts partageant la numérotation
globale -- `scripts/build_lot29_repro_two_units.py`. Motivation : les
hypothèses H1-H3 sur une seule unité ne montrant rien (voir ci-dessous),
teste si la simple coexistence de plusieurs occurrences indépendantes de
`LIAISON_SOLIDE`, comme les neuf du quai, suffit.

## Hypothèse retenue, et preuve qui l'établit

**H1 (redondance liaison/CL), variante déjà connue et déjà corrigée en
production, est confirmée comme un mécanisme réel et exact** -- pas comme la
cause du problème actuellement ouvert. `D0_sym_redundant` (aucun ressort)
reproduit, en isolation complète, le diagnostic exact du lot 28 :

```
Le système linéaire à résoudre a 1620 degrés de liberté: ...
Degré de liberté de Lagrange associé à une relation linéaire entre plusieurs degrés de liberté.
  La liste des noeuds impliqués dans cette relation linéaire est la suivante:

Noeud 189
Noeud 169

 ║ <F> <FACTOR_11>                                                          ║
 ║ Problème : la matrice est singulière ou presque singulière :             ║
```

(extrait complet : `data/examples/lot29_repro/rapports/mess_D0_extrait.txt`,
même signature -- `<F> <FACTOR_11>`, deux nœuds listés juste avant -- que
`data/examples/lot28_quai/rapports/mess_case_g_extrait.txt`). La cause est
exactement celle documentée par `symmetry_and_support_block` : imposer
DRY=DRZ=0 une seconde fois sur un nœud d'anneau dont la rotation est déjà
dérivée par `LIAISON_SOLIDE` produit une relation de Lagrange linéairement
dépendante, donc un pivot exactement nul -- avec zéro ressort, ce qui exclut
toute confusion avec un effet d'échelle ou de nombre.

**Ce mécanisme n'est pas la cause du problème resté ouvert au lot 28.** La
même géométrie, avec la logique de production actuelle (`C0_sym_n0`,
`C1_sym_n` -- la part d'anneau du plan de symétrie exclue de la CL de
rotation, exactement `symmetry_and_support_block` tel qu'il est aujourd'hui
dans `aster_expert.generation.comm`), réussit systématiquement, avec ou sans
10 000 ressorts. Le lot 28 avait lui-même observé la même chose sur le
modèle complet : une fois cette redondance précise corrigée (son point 3),
l'échec a persisté, déplacé sur une paire de nœuds hors du plan de symétrie
(son point 4). Ce lot le confirme maintenant en isolation totale.

## Hypothèses écartées, et ce qui les écarte

- **H3 (nombre de ressorts)** : `A0_n0` → `A3_n10000`, raideur réelle
  (1e6 N/m), aucune symétrie -- tous `completed_ok`. Une seule
  `LIAISON_SOLIDE` reste insensible à 0, 10, 1 000 ou 10 000 ressorts
  supplémentaires partageant ses nœuds de coque.
- **H2 (écart d'échelle de raideur)** : `B1_klow` (÷1e4) et `B2_khigh`
  (×1e4), à N=10 000 constant -- tous deux `completed_ok`. Huit ordres de
  grandeur de raideur sans le moindre effet, cohérent avec la conclusion du
  lot 28 sur `COEF_RIGI_DRZ` (point 3, item 6) : une insensibilité totale à
  un facteur d'échelle indique une dépendance linéaire exacte quand elle se
  produit, jamais un problème de conditionnement -- ici, elle n'indique même
  aucun problème du tout.
- **H1, cas 3 (symétrie seule, logique de production actuelle)** :
  `C0_sym_n0` et `C1_sym_n` -- `completed_ok`. La coupe du tube en
  demi-cercle (21 nœuds d'anneau au lieu de 40), avec ou sans les 10 000
  ressorts, ne suffit pas seule.
- **Extension : multiplicité des `LIAISON_SOLIDE`** : `E0_two_units` --
  `completed_ok`. Deux occurrences indépendantes de `LIAISON_SOLIDE`
  partageant la même numérotation globale et un pool de 10 000 ressorts ne
  suffisent pas non plus, à elles seules, à produire un pivot nul.

## H4 : recherche documentaire et solveur

`search_test_cases` (`AFFE_CHAR_MECA`/`LIAISON_SOLIDE` croisé avec
`AFFE_CARA_ELEM`/`DISCRET`) trouve des cas tests officiels combinant les
deux (`sdlx102a`, `sdlx103a`, `sdlx105b`, `sdlx106a/b`, `sdnx100c/f/h`,
`sdnx101a/b/c/e`, `sdnx102a/b/c/d`, `zzzz140b`, `zzzz144a/b/c`,
`zzzz200a/b/c/e/f`, `zzzz337a/b`, `fdlv112b/d/e/h/k`, `mac3c14a/b`,
`sdnd111a`, `sdnl113a`, `sdls118c/d`, `ssnl504c` -- au moins 25 cas). **Ce
n'est donc pas l'absence documentée par le lot 28 (point 4, item 5)** :
l'association liaison de corps solide + éléments discrets a des précédents
officiels. Aucun de ces cas, cependant, ne combine une coque DKT facettée,
une poutre, et plusieurs milliers d'éléments discrets sans rapport
géométrique avec la liaison -- l'échelle et la topologie précises du quai
restent sans précédent identifié dans le corpus.

`get_command_schema("MECA_STATIQUE", keyword="SOLVEUR.NPREC")` confirme que
`SOLVEUR/NPREC` existe pour `METHODE="MUMPS"` (entier, défaut 8, sans
domaine de valeurs déclaré dans le catalogue) -- le paramètre que le message
`<F> <FACTOR_11>` lui-même suggère de relâcher. **Non testé sur le
reproducteur** : celui-ci ne présente jamais le pivot quasi-nul ambigu que
`NPREC` est censé traiter (D0 mis à part, qui est une dépendance linéaire
exacte, pas un cas limite) -- il n'y avait donc rien à mesurer. Le constat
du lot 28 sur `COEF_RIGI_DRZ` (une insensibilité totale à deux ordres de
grandeur, incompatible avec un simple mauvais conditionnement) rend d'autant
moins probable qu'un relâchement de `NPREC` change quoi que ce soit à
l'échec résiduel du modèle complet -- **déduction, non vérifiée par
exécution**.

## Correction apportée

**Aucune.** Étape 3 des instructions de ce lot conditionne toute correction
à une cause établie ; ce lot écarte H2 et H3, reconfirme H1 comme un
mécanisme réel mais insuffisant pour expliquer l'échec resté ouvert, et ne
peut conclure sur H4 sans l'essai interdit (relance du modèle complet). Le
générateur de production (`aster_expert.generation.comm`) porte déjà, depuis
le lot 28, la correction propre au mécanisme H1 confirmé ici
(`symmetry_and_support_block`) ; ce lot n'y change rien, n'ayant rien
démontré qui justifierait un changement supplémentaire.

## Modèle complet

**Non relancé, conformément aux instructions de ce lot** (« une seule
relance, après correction démontrée » -- aucune ne l'a été). Niveau de
validation inchangé depuis le lot 28 : **B** (générateur déterministe,
`.comm` conforme au catalogue, 80/80 commandes), **C non atteint**. Le
constat du lot 28 reste entier : `LIAISON_SOLIDE` (neuf occurrences) combiné
aux ~10 400 `DIS_T` produit un pivot nul systémique, cause profonde non
confirmée -- ce lot exclut deux candidats (nombre de ressorts, échelle de
raideur) et reconfirme sans l'étendre un troisième (redondance liaison/CL,
déjà corrigé, insuffisant seul).

## Coût

21 exécutions réelles au total (niveau C, `aster-expert run`), dont 10 de la
matrice retenue (table ci-dessus) et 11 de mise au point du reproducteur
(trois erreurs de construction, section « Étape 1 »). Fenêtre complète :
2026-09-23T13:05:03Z -- 13:19:56Z, soit environ 15 minutes. Chaque
exécution individuelle dure de 8 à 20 s (modèle synthétique, quelques
centaines à dizaines de milliers de degrés de liberté, sans commune mesure
avec les ~44 s du modèle complet du quai qui échoue, lui, après assemblage
de 247 999 degrés de liberté).

## Contrôle ajouté au générateur

Aucun (voir « Correction apportée »). Le reproducteur lui-même
(`scripts/build_lot29_repro.py`, `scripts/build_lot29_repro_two_units.py`)
est couvert par `tests/unit/test_build_lot29_repro.py` et
`tests/unit/test_build_lot29_repro_two_units.py` (déterminisme, comptages de
nœuds/mailles, absence de `CREA_POI1`/`DIS_T` quand `n_springs=0`, split
CL redondante/non redondante, deux `LIAISON_SOLIDE` sans nœud partagé).

## Limites et piste pour un prochain lot

- La cause du pivot résiduel (post-correction H1, sur le modèle complet)
  reste inconnue. Ce lot élimine le nombre de ressorts, l'échelle de leur
  raideur, la symétrie seule et la simple multiplicité de `LIAISON_SOLIDE`
  -- sans springs ni symétrie combinées à plus de deux occurrences
  simultanées. La configuration exacte du quai (neuf occurrences,
  toutes liées à une même poutre de couronnement **continue**, contrairement
  au reproducteur de ce lot où chaque poutre est un tronçon isolé) n'a pas
  été reproduite : une poutre continue reliant plusieurs `LIAISON_SOLIDE`
  successives est une piste concrète et non testée pour un prochain lot.
- `search_test_cases` montre que la combinaison liaison de corps solide +
  discrets a des précédents officiels, mais aucun à l'échelle ni à la
  topologie du quai : l'absence de précédent exact n'est pas elle-même une
  preuve, juste l'absence d'un raccourci disponible.
- `SOLVEUR/NPREC` n'a pas été testé (aucun pivot ambigu à traiter sur le
  reproducteur) ; l'argument du lot 28 contre un problème de conditionnement
  (insensibilité totale de `COEF_RIGI_DRZ`) rend cette piste peu probable
  mais ne l'exclut pas formellement.
- La recommandation du lot 28 reste d'actualité et hors de portée de ce lot :
  `LIAISON_ELEM`/raccord coque-poutre dédié (R3.03.03, R3.03.06) à la place
  de `LIAISON_SOLIDE`, avec sa propre étude de faisabilité, nécessiterait une
  nouvelle décision de MM (la décision 4 du point 3 retient explicitement
  `LIAISON_SOLIDE`).

## Compte rendu des sept commandes de contrôle

```
$ aster-expert mcp-check          -> OK, 7/7 outils identiques au code
$ ruff format --check .           -> 203 files already formatted
$ ruff check .                    -> All checks passed!
$ pytest tests/unit -q            -> 787 passed in 59.31s
$ pytest -q                       -> 814 passed in 54.74s
$ mypy src                        -> Success: no issues found in 77 source files
$ mypy                            -> Success: no issues found in 136 source files
```
