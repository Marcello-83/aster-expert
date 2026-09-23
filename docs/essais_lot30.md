# Lot 30 : quai réduit, LIAISON_SOLIDE isolée comme cause du pivot nul

Version Code_Aster : 17.4.0 (image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).
Niveau de validation : **C** pour le diagnostic (le quai réduit s'exécute
jusqu'au bout du calcul du cas G dès que `LIAISON_SOLIDE` est retiré — aucun
contrôle D n'a été fait sur ce résultat, hors sujet du lot). Le modèle
complet reste au niveau **B**, inchangé depuis le lot 28 : la cause touche une
décision de la fiche (point 3) et n'a pas été corrigée (voir « Cause établie »
et « Conclusion »).

## Étape 0 : `mcp-check`

```
Outils déclarés dans le code (7) : analyze_comm, get_command_schema, get_document_section, read_test_case, search_codeaster_docs, search_test_cases, validate_comm
  OK search_codeaster_docs {"query": "STAT_NON_LINE", "k": 1} -> U4.53.01#But
  OK get_document_section {"fragment_id": "U4.53.01#But"} -> level A
  OK get_command_schema {"command": "STAT_NON_LINE"} -> level A
  OK analyze_comm {"comm_path": "/tmp/aster-expert-mcp-check-30whfe5u/minimal.comm"} -> level A
  OK validate_comm {"comm_path": "/tmp/aster-expert-mcp-check-30whfe5u/minimal.comm"} -> level B, valid=True
  OK search_test_cases {"command": "AFFE_MODELE", "limit": 1} -> adls102a.comm
  OK read_test_case {"path": "adls102a.comm"} -> level A
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.
```

## Étape 1 : le message d'erreur du lot 28, relu avant toute nouvelle exécution

Le `.mess` complet de la dernière exécution déjà documentée du `.comm` de
production (`data/examples/lot28_quai/quai_combiwall.comm`,
`execution_report.json` et `mess_case_g_extrait.txt` versionnés au lot 28) a
été relu depuis le répertoire d'exécution encore présent sur le disque
(`data/processed/runs`, non versionné, jamais purgé depuis le lot 28) —
**aucune nouvelle exécution du modèle complet** dans cette étape. Le
diagnostic est identique à celui déjà versionné :

```
Le système linéaire à résoudre a 247999 degrés de liberté:
   - 240657 sont des degrés de liberté physiques
     (ils sont portés par 40114 noeuds du maillage)
   - 7342 sont les couples de paramètres de Lagrange associés
     aux 3671 relations linéaires dualisées.
Degré de liberté de Lagrange associé à une relation linéaire entre plusieurs degrés de liberté.
  La relation linéaire a été définie par la commande ayant produit le concept de nom 0000000a.
  La liste des noeuds impliqués dans cette relation linéaire est la suivante:

Noeud 2263
Noeud 2120

 ║ <F> <FACTOR_11>                                                                                ║
 ║ Problème : la matrice est singulière ou presque singulière :                                   ║
 ║   Lors de la factorisation de la matrice, on a rencontré un problème                           ║
 ║   (pivot nul ou presque nul) à la ligne 17118 qui correspond au degré de liberté donné          ║
 ║ ci-dessus.                                                                                      ║
```

1. **Identité du concept fautif** : recherche du concept `0000000a` dans le
   même listing → `# Résultat commande #0014 (AFFE_CHAR_MECA): CH_SOLIDE
   ('<0000000a>')`, la commande `LIAISON_SOLIDE` du point 3 (neuf occurrences
   dans un seul `AFFE_CHAR_MECA`).
2. **Identité des nœuds** (sonde `medcoupling` autonome, hors Salomé et hors
   Code_Aster, exécutée dans le même conteneur restreint que `mesh check` —
   script non versionné, jetable, relevé sur `data/examples/lot28_quai/quai_combiwall.mmed`) :
   - Nœud 2263 = (10.4, 0.34, 3.3), groupe `SYM_D`, cellule `POUTRE_COUR`
     (`GEN_POUTRE_09`, le nœud de poutre du tube 9, demi-tube de bord).
   - Nœud 2120 = (10.288931529821, 0.701258721823, 2.6), anneau `TETE_TUBE_09`
     ordinaire — ni sur le plan de symétrie, ni un nœud remarquable.
   - Les deux sont liés par la même occurrence (tube 9) de `LIAISON_SOLIDE`.
3. Ce nœud d'anneau (2120) n'est *pas* sur le plan de symétrie : ce n'est pas
   la redondance déjà corrigée au lot 28 (`GEN_SYMD_RING`/`GEN_SYMD_ROT`,
   docs/essais_lot28.md, « quatrième échec ») — c'est exactement le résidu
   que ce fait-là avait déjà établi comme non expliqué.
4. **Option documentée pour une lecture plus fine** : `MECA_STATIQUE/INFO`
   (`get_command_schema`) accepte `1` ou `2` ; le catalogue ne documente pas
   directement ce que `INFO=2` ajoute pour `LIAISON_SOLIDE`, mais
   `search_codeaster_docs` confirme le principe général (« Avec INFO=2, de
   nombreuses informations sur l'enchaînement des étapes de calcul sont
   affichées », U7.03.12) : à retenir pour un prochain diagnostic si
   l'identité des nœuds ne suffisait pas — ici elle a suffi, `INFO=2` n'a pas
   été activé.

Cette lecture désigne un nœud précis mais **ne clôt pas le diagnostic** :
c'est exactement le résidu déjà établi et non expliqué au lot 28 (point 4 de
sa propre démarche). Passage à l'étape 2.

## Étape 2 : quai réduit (deux entraxes)

`data/examples/lot30_quai_reduit/model_data_reduit.yaml` : copie de
`data/examples/combiwall_model_data.yaml` où seuls six champs de tranche
changent (`geometrie.nombre_entraxes_tranche` 8→2, `nombre_tubes_entiers`
7→1, `nombre_demi_tubes` inchangé à 2, `nombre_palplanches_intercalaires`
8→2, `repere.x_face_coupe_gauche/droite` ±10,40→±2,60 m) : trois tubes (deux
demi-tubes aux plans de symétrie, un tube central plein — `TUBE_02`), deux
palplanches, un tronçon de poutre continue sur deux entraxes, trois tirants,
les ressorts. Aucune décision n'est prise ni modifiée (`case_reference` du
fichier le dit explicitement).

- `scripts/build_lot30_quai_reduit.py` produit `params.json` et
  `invariants.yaml` analytiquement, avant toute exécution de Salomé (même
  mécanisme que le lot 27).
- `aster-expert mesh run scripts/salome/combiwall_mesh.py --params
  data/examples/lot30_quai_reduit/params.json` : maillage produit en
  **112,6 s** (contre ~17 min pour le modèle complet), 10 204 nœuds, 10 030
  QUAD4, 10 069 SEG2 — conforme aux comptages analytiques.
- `aster-expert mesh check` : **232/232 invariants tenus**, aucun écart
  (`data/examples/lot30_quai_reduit/invariants.yaml`).
- `.comm` produit par le générateur de production
  (`scripts/generate_lot30_quai_reduit.py`, qui appelle directement
  `aster_expert.generation.generate.generate_comm` — jamais la CLI
  `aster-expert generate`, qui écrit toujours dans
  `data/examples/lot28_quai/` et aurait écrasé le `.comm` de production).
  Validation niveau B : **80/80 commandes conformes**.
- Exécution : **échec identique** au modèle complet, `<F> <FACTOR_11>`, en
  13,7 s, sur le tube de bord opposé (tube 1 au lieu de 9) : nœud 575
  (`GEN_POUTRE_01`, `SYM_G`) et nœud 13 (anneau ordinaire `TETE_TUBE_01`) —
  même mécanisme, même signature (ligne de pivot 230, relation dualisée du
  concept `CH_SOLIDE`).

**Le quai réduit reproduit fidèlement l'échec.** Reproducteur validé,
passage à l'étape 3 (pas d'extension à quatre/six entraxes, non nécessaire
puisque deux entraxes suffisent déjà).

## Étape 3 : retrait d'un ingrédient à la fois

Quatre options de retrait ajoutées au générateur de production
(`aster_expert.generation.generate.DiagnosticOmissions` : `sans_ressorts`,
`sans_tirants`, `sans_palplanches`, `sans_poutre`), **clairement documentées
comme outils de diagnostic** (docstring de la classe) et jamais actives par
défaut — `test_default_diagnostic_matches_production` vérifie que le `.comm`
par défaut reste identique à celui produit sans cet argument.

| # | Retrait | Exécution | Issue |
| --- | --- | --- | --- |
| 1 | sans les ressorts (`sans_ressorts`) | 21,2 s (après correction d'une erreur de préparation, voir ci-dessous) | **Échec identique** (`FACTOR_11`, nœuds 575/13) |
| 2 | sans les tirants (`sans_tirants`) | 18,2 s | **Échec identique** |
| 3 | sans les palplanches (`sans_palplanches`) | 17,9 s (après correction) | **Échec identique** |
| 4 | sans la poutre, donc sans `LIAISON_SOLIDE` (`sans_poutre`) | 19,0 s (après correction) | **Aucun `FACTOR_11`** — pivot disparu |

Trois erreurs de préparation, sans rapport avec le pivot, ont dû être
corrigées avant d'obtenir un résultat exploitable pour les retraits 1, 3 et 4
(comptées dans le coût, étape 7 ; voir
`data/examples/lot30_quai_reduit/rapports/executions.json` pour le détail
complet des huit exécutions) :

1. **Retrait 1, première tentative** : `<F> <FACTOR_11>` (le pivot!) sur le
   `.export` du 30 septembre... non : `<F> <_ABNORMAL_ABORT>` (ségmentation
   fault) — le `.export` copié portait le nom `quai_reduit.export` alors que
   le `.comm` s'appelait `quai_reduit_sans_ressorts.comm` : `run_aster`
   cherche un `.export` du même nom que le `.comm`
   (`aster_expert/execution/execute.py` : `export_sibling =
   comm_path.with_name(f"{stem}.export")`) ; sans le trouver, `LIRE_MAILLAGE`
   ne trouve pas son fichier MED (`fort.20`). Corrigé en nommant chaque
   `.export`/`.mmed` diagnostique du même nom que son `.comm`.
2. **Retrait 3, première tentative** : `<F> <MESH3_99>` — sans les
   palplanches, `ECRAN_POUSSEE` (tubes + palplanches) n'est plus un ensemble
   connexe de mailles de bord ; `FORCE_COQUE`'s propre vérification
   d'orientation (`VERI_NORM`, valeur catalogue par défaut `'OUI'`) refuse.
   Corrigé : un groupe dédié `GEN_ECRAN_POUSSEE_TUBES` (`ECRAN_POUSSEE`
   moins `PALPS`, `DEFI_GROUP`/`DIFFE`) porte la charge, avec
   `VERI_NORM="NON"` — le message d'erreur suggère lui-même ce contournement.
3. **Retrait 4, première tentative** : `<F> <CHARGES2_46>` — `CH_Q3`
   (amarrage sur `BOLLARD`) est construit *avant* le cas G lui-même (tous
   les concepts de charge sont assemblés en tête du `.comm`) ; sans la
   poutre, `BOLLARD` est hors modèle (aucun degré de liberté) et
   `AFFE_CHAR_MECA` refuse d'y imposer `FY`. Corrigé : le cas Q3 (amarrage)
   et sa charge n'ont plus de sens sans la poutre et sont omis entièrement
   dans cette variante.

Après ces trois corrections (des erreurs de préparation du diagnostic, pas
du mécanisme étudié), le retrait 4 est le **premier retrait qui débloque le
calcul** : le pivot nul disparaît dès que `LIAISON_SOLIDE` n'existe plus.
L'exécution corrigée du retrait 4 atteint l'assemblage du cas G
(commande #0025, `RESU_G = MECA_STATIQUE(...)`, 64 063 degrés de liberté)
puis échoue sur un défaut **différent et sans rapport** :
`<F> <DISCRETS_26>`/`<F> <DISCRETS_30>`/`<F> <DISCRETS_31>` (masse non
affectée sur les éléments discrets `DIS_T` des ressorts sous `PESANTEUR`,
alarme aggravée en erreur) — un défaut préexistant du générateur de
production, jamais rencontré avant ce lot parce que le pivot `FACTOR_11`
arrêtait systématiquement l'exécution avant d'atteindre ce point de calcul.
**Hors sujet de ce lot** (non lié à `LIAISON_SOLIDE`, non corrigé ici) ;
signalé pour un prochain lot.

**Retrait 5 (poutre présente, `LIAISON_SOLIDE` remplacée par un partage de
nœud) : non testé.** La sonde de l'étape 1 le montre : le nœud de poutre
(`GEN_POUTRE_09`, Y = 0,34, Z = 3,3) et les nœuds d'anneau (Y ≈ ±0,71,
Z = 2,6) ne sont géométriquement coïncidents pour aucun tube — un partage de
nœud simple n'est exprimable qu'en modifiant le maillage (rapprocher la
poutre de l'anneau ou vice-versa), interdit par ce lot (« aucune
modification manuelle du maillage »). Non testé, faute d'être exprimable
sans cette modification.

**Retrait 6 (sans les conditions de symétrie) : non testé.** Le premier
retrait informatif (4) ayant déjà désigné la cause avec certitude — et
touchant une décision de la fiche (point 3, voir ci-dessous) —, ce lot
s'arrête à l'instruction qui le prévoit explicitement plutôt que de
poursuivre la table au-delà du premier succès.

## Cause établie (niveau C, cinq exécutions réelles supplémentaires sur le quai réduit)

`LIAISON_SOLIDE`, en présence de plusieurs occurrences simultanées (au moins
trois, sur trois tubes) liées à une poutre de couronnement **continue**,
produit un pivot nul systémique à la factorisation MUMPS — **indépendamment
des ressorts, des tirants et des palplanches**, qu'aucun des trois premiers
retraits n'a pu éviter. Ce fait est établi sur un modèle onze fois plus
petit (10 204 nœuds contre 40 114) et bien plus rapide à exécuter (13 à 21 s
par tentative contre 44 s pour le modèle complet, sans compter le temps de
maillage : 113 s contre ~17 min).

**Ceci précise le fait établi du lot 28, sans le contredire sur
`LIAISON_SOLIDE`, mais le contredit sur le rôle des ressorts** : le lot 28
concluait, sur un reproducteur distinct et non générateur de production
(« tube 9 + panneau de palplanche voisin + `LIAISON_SOLIDE`, sans les
~10 400 éléments `DIS_T` de ressort », étendu ensuite aux neuf tubes et à
`TIRANTS`/`ANCRAGES`), que le retrait des ressorts seul suffisait à éviter
l'échec sur le modèle complet réel. Sur le quai réduit, produit par la
chaîne de production elle-même, **ce n'est pas le cas** : le retrait des
ressorts seul ne suffit pas ici. Les deux constats ne portent pas sur le
même modèle (le reproducteur du lot 28 n'était pas généré par
`aster_expert.generation`, sa géométrie et ses réglages exacts ne sont pas
reproductibles depuis ce dépôt) ; celui de ce lot repose sur le générateur
de production lui-même et est donc le plus directement transposable au
modèle complet.

**Déduction, non confirmée (comme au lot 28)** : le mécanisme précis reste
le choix interne par Code_Aster du nœud de référence de chaque corps rigide
(R3.03.02) parmi plusieurs `LIAISON_SOLIDE` simultanées, sensible à un
facteur que ce lot élimine partiellement (ce n'est ni le nombre de
ressorts, ni les tirants, ni les palplanches) sans l'identifier
positivement. Hors de portée des sept outils MCP de ce projet (aucun
n'inspecte l'algorithme interne d'élimination de Code_Aster), exactement
comme au lot 28.

## Cause touchant une décision de la fiche (point 3) : non modifiée

Conformément aux instructions de ce lot, `LIAISON_SOLIDE` (décision du
point 3, `arbitrage_combiwall_MM_lot21.md`, cas test officiel
`sdlx03b.comm`) n'est ni remplacée ni modifiée. Ce qu'il faudrait, pour un
prochain lot (déjà recommandé au lot 28, reconfirmé ici avec un
reproducteur nettement plus rapide et sans confusion possible avec les
ressorts) :

- Étudier `R3.03.03`/`R3.03.06` (« Liaison coque-poutre »), un mécanisme
  distinct de la relation de corps rigide générique de `LIAISON_SOLIDE`,
  potentiellement insensible à la multiplicité d'occurrences simultanées —
  avec sa propre étude de faisabilité avant toute exécution, comme le lot 28
  le recommandait déjà.
- Le quai réduit (`data/examples/lot30_quai_reduit/`, ~130 s de calcul
  Code_Aster cumulés pour cinq tentatives contre 44 s pour une seule
  exécution du modèle complet, mais avec un gain net en nombre d'itérations
  possibles par unité de temps) reste disponible pour instruire cette piste
  sans repasser par le modèle complet à chaque essai.

## Corrections apportées (généralisation du générateur, sans rapport avec la cause)

Deux limites de généralité du générateur de **production**, révélées par
l'usage sur une géométrie différente de huit entraxes (jamais exercée
auparavant), corrigées et couvertes par un test :

1. **`check_spring_sum`** (`aster_expert/generation/generate.py`) : les
   largeurs/hauteurs de bande (20,80/11,36 m, 6,00/8,00 m) étaient tapées en
   dur, propres au modèle à huit entraxes. Remplacées par un calcul
   analytique générique (`aster_expert.meshing.combiwall
   .band_projected_width`, nouveau), testé
   (`test_band_projected_width_matches_the_generator_own_former_constants`,
   `tests/unit/test_meshing_combiwall.py`) : reproduit exactement les deux
   anciennes constantes sur le modèle complet.
2. **`controls_block`** (`aster_expert/generation/comm.py`) : la paire de
   symétrie du contrôle D (`ANC_01`/`ANC_09`, `TETE_TUBE_02`/`TETE_TUBE_08`)
   était elle aussi tapée en dur — fausse pour tout autre nombre de tubes.
   Remplacée par un calcul depuis les tubes de bord et leurs voisins
   immédiats (`edge_tube_low`/`edge_tube_high`,
   `inner_tube_low`/`inner_tube_high`, `generate_comm`) ; à trois tubes, le
   voisin immédiat de chaque bord est le même tube central
   (`inner_tube_low == inner_tube_high`) — dédoublonné, `checkCommandSyntax`
   refusant toute valeur répétée dans un `GROUP_NO` (constaté par
   `validate_comm`, jamais visible dans la documentation).

Ces deux corrections sont dans le code de **production**, pas seulement le
diagnostic : ce sont de vraies limites de généralité, sans aucun rapport
avec le pivot nul. Vérifiées sans exécution réelle : la régénération du
`.comm` de production (`data/examples/hypotheses_combiwall_reference_arbitree.json`
+ `data/examples/combiwall_model_data.yaml` + le maillage vérifié du lot 27)
reste **octet pour octet identique** à `data/examples/lot28_quai/quai_combiwall.comm`
à l'exception de deux commentaires reformulés en toute généralité (mêmes
valeurs numériques, mêmes groupes) — vérifié deux fois, avant et après le
refactor final de mise en forme (`ruff format`).

Cinq tests unitaires ajoutés
(`tests/unit/test_generation_generate_diagnostics.py`) : le `.comm` par
défaut (`DiagnosticOmissions()`) reste identique à l'appel sans cet
argument, et chaque option de retrait omet exactement et seulement
l'ingrédient qu'elle nomme.

## Modèle complet : non relancé

Aucune correction du mécanisme `LIAISON_SOLIDE` lui-même n'a été apportée
(branche « touche une décision de la fiche » de ce lot). Conformément aux
interdits (« aucune relance exploratoire du modèle complet »), il n'a pas
été réexécuté : sa régénération produit un texte **octet pour octet
identique** à celui déjà exécuté au lot 28 (à l'exception des deux
commentaires reformulés ci-dessus), donc son comportement à l'exécution —
le même `<F> <FACTOR_11>` déjà documenté au lot 28 — est nécessairement
inchangé. Aucune exécution du modèle complet n'a eu lieu dans ce lot :
l'étape 1 s'est appuyée sur le répertoire d'exécution encore présent sur le
disque (`data/processed/runs`, non versionné) de la dernière exécution déjà
documentée au lot 28 (`execution_report.json`, `mess_case_g_extrait.txt`,
tous deux versionnés) pour en relire le listing complet — jamais relancée.

## Coût

- 1 exécution Salomé (maillage réduit, `mesh run`) : 112,6 s.
- 1 `mesh check` (medcoupling, quelques secondes).
- 2 sondes `medcoupling` autonomes, jetables (identité des nœuds, étapes 1
  et 2, dont une sur le répertoire d'exécution déjà existant du lot 28, sans
  le relancer).
- 8 exécutions Code_Aster réelles du quai réduit (`aster-expert run`, dont 3
  refaites après correction d'une erreur de préparation sans rapport avec
  le pivot) : 13,7 + 7,8 + 21,2 + 18,2 + 17,3 + 17,9 + 14,4 + 19,0 =
  **129,5 s cumulées** (détail complet :
  `data/examples/lot30_quai_reduit/rapports/executions.json`).
- Total calcul réel (Salomé + Code_Aster, 112,6 + 129,5 s) : **≈ 4 minutes**,
  pour isoler une cause qu'un unique test du modèle complet (44 s, mais
  ~17 min de maillage au préalable) n'aurait pas pu isoler par lui-même.

## Contrôles

```
$ aster-expert mcp-check
mcp-check OK : 7 outils appelés sur un serveur neuf, identiques aux outils du code.

$ ruff format --check
206 files already formatted

$ ruff check
All checks passed!

$ pytest tests/unit
793 passed

$ pytest
820 passed

$ mypy src
Success: no issues found in 77 source files

$ mypy
Success: no issues found in 137 source files
```

## Limites connues

- Le mécanisme précis du choix interne du nœud de référence de
  `LIAISON_SOLIDE` (R3.03.02) reste une déduction, non un fait établi.
- Le défaut `DISCRETS_26`/`DISCRETS_30`/`DISCRETS_31` (masse non affectée
  sur les ressorts `DIS_T` sous `PESANTEUR`) est désormais connu mais non
  corrigé : il bloquera de toute façon le niveau C du modèle complet même
  si `LIAISON_SOLIDE` était un jour remplacée par `LIAISON_ELEM`.
- Retrait 5 (partage de nœud) non testé, non exprimable sans modifier le
  maillage (interdit par ce lot).
- Retrait 6 (symétrie) non testé : le premier retrait informatif (4) a
  suffi à désigner la cause.
- Aucun contrôle D n'a été fait (le quai réduit n'atteint jamais un calcul
  complet sans erreur, même sans `LIAISON_SOLIDE`, à cause du défaut
  `DISCRETS_*` ci-dessus).
