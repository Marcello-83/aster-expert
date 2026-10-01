# Essais lot 41 — restructuration : un tronc commun, des projets

Rapport rédigé au fil du lot, selon `docs/modele_rapport_essai.md`. La section
« Critère de non-régression » est écrite **avant** toute modification du code et
n'est pas modifiée ensuite ; l'heure d'écriture est indiquée. Version cible :
Code_Aster 17.4.0 (digest
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).

## Objet

Séparer le tronc commun (`src/aster_expert/`, valable pour tout ouvrage) du code,
des données et des scripts propres au quai combi-wall, déplacés dans
`projets/quai_cw_test_01/`, **sans changer le comportement du quai**. La
restructuration est neutre : c'est ce que le critère ci-dessous vérifie.

## Étape 0 — Contrôle MCP (2026-09-29T06:05-04:00)

`aster-expert mcp-check` : « mcp-check OK : 7 outils appelés sur un serveur neuf,
identiques aux outils du code. » (`validate_comm` → niveau B, `valid=True`). Les
sept outils (`analyze_comm`, `get_command_schema`, `get_document_section`,
`read_test_case`, `search_codeaster_docs`, `search_test_cases`, `validate_comm`)
sont visibles dans la session.

## Étape 1 — Critère de non-régression (écrit avant toute modification, 2026-09-29T06:23-04:00)

### Références figées

Commit de référence : `a88472c` (lot 40, audit en lecture seule ; code identique à
celui du lot 39, `8382425`). Les sorties ont été **reproduites à cet état** avant
toute modification, à partir des mêmes entrées que les lots 37 à 39, et copiées
dans `data/examples/lot41_restructuration/references/` ; leurs empreintes SHA-256
sont dans `references/empreintes.json` (26 fichiers).

| Sortie | Produite à l'état de référence par | Reproduction à l'état de référence |
| --- | --- | --- |
| `.comm` du modèle complet (`comm/complet.comm`, SHA-256 `cd41d4c8…`, 3 720 lignes) | `generate_comm` (fiche arbitrée, `combiwall_model_data.yaml`, maillage `20260922T071600-8d931d77`) | diffère du `lot37_efforts/complet.comm` versionné par les lignes 6-7 (empreintes de la fiche et des données, modifiées aux lots 38-39) et par l'indentation de deux `_F(` (l. 1906, 1909) : c'est la sortie du générateur au lot 39, prise comme référence |
| Rapport `mesh check` (`maillage/rapport_mesh_check.txt`, 599/599) et invariants (`maillage/combiwall_mesh_invariants.yaml`) | `aster-expert mesh check` sur le MED complet | 599 invariants tenus |
| Contrôles D : charge intégrée (`controles_d/integrale.json`), équilibre et symétrie (`controles_d/equilibre.json`) | `scripts/analyze_lot34_charge_assemblee.py -` puis `analyze_lot34_equilibre.py` sur l'exécution `20260925T125131-c67e28a1` | **identiques à l'octet** aux `lot37_efforts/rapports/integrale_modele_complet.json` et `equilibre_complet.json` versionnés |
| Synthèse (`synthese/synthese.json`, `synthese.md`, `controles.md`) | `aster-expert report` sur la même exécution | **identiques à l'octet** à `lot37_efforts/rapports/complet/` |
| Combinaisons (`combinaisons/` : `combinaisons.csv`, `extrema.csv`, `controle_manuel.json`, `poutre_couronnement.md`) | `scripts/build_lot38_export.py` | identiques à `data/examples/lot38_combinaisons/` (arbre Git propre après relance) |
| Ferraillage (`ferraillage/` : `poutre.comm`, `.mail`, `.export`, `efforts.csv`, `sections.csv`, `ferraillage.csv`, `enveloppes.csv`, `synthese.csv`, `synthese.md`, `controle_main.json`, `resume.json`, `figures/as_x.png`, `rapports/`) | `scripts/build_lot39_poutre.py` puis `analyze_lot39_poutre.py` sur l'exécution `20260928T100157-30609502` | identiques à `data/examples/lot39_poutre/` (arbre Git propre après relance) |

Hors critère, à titre d'information : les 54 vues PNG de la synthèse reproduites à
l'état de référence **diffèrent déjà** des PNG versionnés au lot 37 (empreintes dans
`empreintes.json`, `vues_informatives_hors_critere`) ; elles ne font pas partie des
cinq sorties exigées.

### Critère (écrit avant toute modification)

Après restructuration, la chaîne du quai est rejouée par
`aster-expert projet quai_cw_test_01 <étape>` (étape 7), **avec une nouvelle
exécution du modèle complet**. Chaque sortie ci-dessus doit être :

1. **identique à l'octet près** à sa référence ; ou
2. différer **uniquement** par des chemins et des empreintes, chacun documenté
   ci-dessous avant l'exécution :
   - `.comm` : la ligne `# Fiche : sha256:…` (la fiche change par le seul
     remplacement des constats recopiés par des références, étape 4) ; la ligne
     `# Données : sha256:…` si et seulement si le fichier de données change
     d'octets (il ne doit pas changer : il est déplacé, pas modifié) ;
   - contrôles D, synthèse, combinaisons, ferraillage : les chemins du `.mess`, du
     MED de résultats, du `.comm` exécuté, du fichier de données et des
     répertoires d'exécution, et les empreintes SHA-256 du `.mess`, du MED de
     résultats et du `.comm` exécuté (un nouveau `.mess` porte d'autres dates) ;
   - ferraillage : `rapports/executions.json` (date, durée, répertoire et
     empreinte de l'exécution de `poutre.comm`) et `rapports/mess_ferr_extrait.txt`
     si seules des lignes de date ou de durée diffèrent.

   Toute valeur numérique (déplacement, effort, réaction, écart d'équilibre,
   aire d'acier, coefficient) différente, même au dernier chiffre imprimé, est un
   **échec**. Toute différence non listée ci-dessus est un **échec**, rapporté tel
   quel, sans critère relâché après coup.

La comparaison est faite fichier par fichier contre `references/empreintes.json`,
puis par `diff` pour tout fichier dont l'empreinte diffère.

### Correction de l'emplacement des références (2026-09-29T06:30-04:00, avant toute modification du code)

Les références ont été déplacées, telles quelles, de
`data/examples/lot41_restructuration/references/` vers
`projets/quai_cw_test_01/references/` (résultats de référence du projet), avant la
première modification du code. Les empreintes de `empreintes.json` sont celles des
mêmes fichiers ; le critère ci-dessus n'est pas modifié.

## Étape 2 — Séparation

### Ce qui a été déplacé (sans modification de comportement)

| De | Vers |
| --- | --- |
| `src/aster_expert/generation/` (générateur, 7 fichiers) | `projets/quai_cw_test_01/generation/` |
| `src/aster_expert/meshing/{combiwall,normals,equilibrium}.py` | `projets/quai_cw_test_01/meshing/` |
| `src/aster_expert/report/{build,figures,loads,med_source,quantities,render,section_statics,sections}.py` | `projets/quai_cw_test_01/report/` |
| `src/aster_expert/report/combinations.py` (coefficients de D17 codés en dur, en double avec les données) | **supprimé** : combinaisons du tronc commun, γ et ψ lus du fichier de données |
| `data/examples/hypotheses_combiwall_reference*.json` | `projets/quai_cw_test_01/fiche/` |
| `data/examples/combiwall_model_data.yaml`, `combiwall_inputs/` | `projets/quai_cw_test_01/donnees/` (fichier de données inchangé à l'octet) |
| `data/examples/combiwall_mesh_invariants.yaml`, `scripts/salome/combiwall_mesh.py` | `projets/quai_cw_test_01/maillage/` (script inchangé à l'octet : son empreinte `05213fec…` fonde le cache de maillage vérifié) |
| 41 scripts de lot propres au quai (`scripts/analyze_lot2[7]…39`, `build_lot27…39`, `generate_lot30…37`, `build_combiwall_reference.py`…) | `projets/quai_cw_test_01/scripts/` |
| 32 fichiers de tests propres au quai | `projets/quai_cw_test_01/tests/` |

Les couches de sol de `terre.py`, les noms de groupes et la synthèse propre au quai
partent avec `generation/` et `report/`. Les archives des essais des lots
(`data/examples/lotNN_*`) restent en place : elles sont citées par les rapports et
par les sources d'exécution des constats.

Lignes de `src/` (fichiers `.py`) : **26 612 avant, 22 455 après** ; **8 861 lignes
propres au quai sorties de `src/`** (8 713 déplacées dans le projet, 148 de
`combinations.py` supprimées) ; **4 284 lignes nouvelles** dans le tronc commun
(`projet`, `controles`, `combinaisons`, `ferraillage`, `constats`,
`execution/compte_rendu.py`).

Test d'absence : `tests/unit/test_tronc_commun_sans_ouvrage.py` échoue si un
fichier texte de `src/` contient un des 36 identifiants tirés de l'annexe « codé en
dur » de l'audit (§ 5.1 : `POUTRE_COUR`, `ECRAN_POUSSEE`, `SYM_G`, `PIED_TUBES`,
`EAU_P`, `tube.rayon`, `argile marneuse`, `combiwall`, `quai_cw_test_01`…) ou le mot
« quai ». Les docstrings historiques du tronc commun qui citaient le spécimen
combi-wall ont été réécrites (« fiche de référence du premier projet »).

Textes émis dans les sorties : trois phrases de la synthèse et un commentaire du
`.comm` nommaient des modules déplacés (`aster_expert.report.sections`,
`aster_expert.meshing.normals`…). Ils sont **conservés tels quels** (un commentaire
du code le dit) pour que les sorties restent identiques ; ils nomment donc des
modules qui vivent désormais dans le projet.

### Interface projet : la déclaration

`projets/<nom>/projet.yaml`, validé par `aster_expert.projet.declaration.
ProjectDeclaration` (pydantic, `extra="forbid"`) : `schema_version`, `name` (nom du
répertoire et du paquet), `structure` (identifiant des données) et `variants`,
`fiche`, `data`, `data_sources`, `mesh` (`invariants`, `script`, `parameters`,
`med`), `comm` (`generator` ou `file`, `output`, `required_data`, `export`),
`controls` (`threshold`, `vertical`, `supports` avec composantes bloquées et table
de réactions, `total_reactions`, `springs`, `cases` avec leur résultante attendue,
`symmetry_planes`), `combinations` (bloc permanent, γ, actions variables et ψ,
accidentelles écrites, tables d'efforts, contrôle manuel, rapport), `rebar`
(éléments à ferrailler : section, enrobage, matériaux, familles, sections de
contrôle), `synthesis`. Le code propre au projet est nommé « module:fonction » et
doit appartenir au paquet du projet. Exemple complet : `projets/quai_cw_test_01/projet.yaml`.

Tronc commun lisant seulement la déclaration et les résultats :
`aster_expert.controles` (équilibre, pesanteur, symétrie), `aster_expert.combinaisons`
(règles EN 1990 : fondamentale 6.10 avec bloc permanent défavorable et favorable,
accidentelles écrites, caractéristique, fréquente, quasi permanente),
`aster_expert.ferraillage` (1D, schéma `ssll13*`), `aster-expert report` (appelle
l'extension de synthèse déclarée). Extensions du quai :
`quai_cw_test_01.extensions` (paramètres du maillage, génération, charge intégrée,
forces des ressorts, synthèse), `quai_cw_test_01.controles` (charge intégrée et
ressorts, repris des scripts du lot 34, qui l'appellent désormais),
`quai_cw_test_01.rapports` (prose du rapport des combinaisons, tableau et figure du
ferraillage).

Commande : `aster-expert projet <nom> <étape>` (`verifier`, `maillage`, `generer`,
`valider`, `executer`, `controles`, `synthese`, `combinaisons`, `ferraillage`,
`tout`), état dans `projets/<nom>/resultats/etat.json`.

## Étape 3 — Refus lisibles

| Refus | Où | Test |
| --- | --- | --- |
| données d'un autre ouvrage (données de dalle de l'audit passées au quai) : « les données dalle_donnees.yaml sont celles de l'ouvrage 'DALLE-AUDIT-40', la déclaration admet 'QUAI-CW-TEST-01', … » | `generate`, `report`, `projet` | `test_the_audit_slab_data_is_refused_by_the_quay_project`, `test_generate_refuses_the_slab_data_readably`, `test_report_refuses_the_slab_data_readably` |
| donnée exigée par le générateur absente : « donnée manquante : tube.rayon (exigée par le générateur, absente de …) » — le cas de l'audit | `generate`, `projet` | idem, `test_a_missing_data_value_is_named` |
| groupe absent du maillage (invariants) | `generate`, `projet` | `test_a_group_absent_from_the_mesh_is_refused` |
| cas de charge sans résultante attendue | `projet`, contrôles D | `test_a_load_case_without_expected_resultant_is_refused` |
| champ manquant ou inconnu, extension mal formée, générateur et fichier à la fois, déclaration illisible ou vide, projet inconnu, nom ≠ répertoire, extension hors du paquet du projet, unité inattendue | toutes | `tests/unit/test_projet_declaration.py` (19 tests) |
| fichier d'invariants incohérent (champ manquant, champ inconnu) ou illisible | `mesh check` | `test_mesh_check_refuses_an_incoherent_invariants_file` |
| étape inconnue, étape lancée avant celle dont elle dépend, maillage en écart, exécution en échec (avec les erreurs `<F>` et leur identifiant) | `projet` | `tests/unit/test_projet_pipeline.py` |

Aucun de ces refus ne laisse passer une trace Python (`Traceback` vérifié absent).

## Étape 4 — Base de constats partagée

45 constats extraits (`connaissances/constats_code_aster/CA-001.json` à `CA-045.json`,
`projets/quai_cw_test_01/scripts/extraire_constats_lot41.py`, idempotent) : niveau
D 12, C 6 (les 18 établis par exécution, 47 cas d'essai versionnés), B 20
(catalogue), A 7 (documentation seule) — les chiffres de l'audit (§ 3.3). Chaque
fichier porte la version (17.4.0), le niveau (recalculé à partir des sources et
recontrôlé à la lecture), les sources complètes, les commandes et mots-clés (source
catalogue et identifiants du catalogue cités dans le texte), les cas d'essai, et un
résumé d'une phrase rédigé par cette session à partir du texte retenu du constat
(`lot41_resumes_constats.yaml`, à relire par MM).

La fiche référence les constats (`FindingReference`, nature `constat`) : seule
modification de la fiche. Résolue contre la base (`load_resolved_sheet`), elle est
identique, entrée par entrée, à la fiche complète d'avant la restructuration ;
`build_combiwall_reference.py` la reproduit octet pour octet et refuse un constat
qui diffèrerait de la base. Une référence non résolue est un bloqueur de génération.

Outil MCP `search_constats` (commande, mot-clé ou valeur, texte ; journalisé ;
réponse de niveau A, chaque constat avec son propre niveau), requête minimale dans
`mcp/check.py`, skill `code-aster-expert` (§ 6 ter : consulter les constats avant
d'écrire une commande). CLI : `aster-expert constats chercher`.

Rejeu (`aster-expert constats rejouer`, `aster_expert.constats.rejeu`) : chaque cas
d'essai des constats établis par exécution rejoué dans le conteneur ; la conclusion
tient si chaque valeur obtenue enregistrée est de nouveau imprimée (1e-9 relatif,
critère des listings versionnés). Résultat sous 17.4.0 : voir « Résultats ».

## Étape 5 — Fiabilité de l'exécution

- `aster-expert run` écrit `compte_rendu.json` et `compte_rendu.md` dans le
  répertoire de l'exécution : commande, image, empreintes des fichiers donnés à
  Code_Aster, durée, statut et diagnostic de `run_aster.status`, alarmes par
  identifiant, erreurs `<F>`/`<E>`/`<S>` avec identifiant, ligne et message,
  fichiers produits et leur taille. Les messages sont extraits dans le conteneur
  par `run_aster.error_messages.search_msg` sur tout le listing (5 s pour les
  1,4 million de lignes du modèle complet), jamais par un parseur du projet.
- Tests réels `pytest -m lent` (`tests/integration/test_reel_lent.py`) : un cas
  Code_Aster versionné (lot 22) avec son compte rendu, un arrêt `<F> <CALCULEL7_40>`
  (lot 39) retrouvé avec son identifiant, la géométrie 1 du lot 26 maillée par
  Salomé puis `mesh check`. Commande documentée dans `CLAUDE.md` et le `README.md`.
- Couverture de `cli.py` : 32 % (audit) → voir « Résultats ».
- `mypy` couvre `projets/` (scripts compris, mode strict) ; les scripts Salomé
  (Python 3.9 de Salomé-Méca) en sont exclus.

## Étape 7 — Vérification du critère

### Exécution

Chaîne rejouée par `aster-expert projet quai_cw_test_01 <étape>`, une étape par
commande (2026-09-29, 07:05 à 07:18), puis les étapes sans exécution du modèle
complet rejouées dans un seul processus (07:3x) pour vérifier qu'elles ne
s'influencent pas :

| Étape | Résultat |
| --- | --- |
| `verifier` | déclaration cohérente, fiche sans bloqueur (63 entrées) |
| `maillage` | MED vérifié du cache (`20260922T071600-8d931d77`), Salomé non relancé ; `mesh check` 599/599 |
| `generer` | `resultats/complet.comm`, SHA-256 `683ebc23…` |
| `valider` | niveau B, `valid = true`, 265/265 commandes confrontées |
| `executer` | **une exécution du modèle complet** : `completed_ok` (`OK`), 160,0 s, 0 alarme, 0 erreur (`data/processed/runs/20260929T111324-78b3ade0/compte_rendu.md`) |
| `controles` | équilibre G, Q1, EAU_P, EAU_A ≤ 2,8e-12 ; pesanteur (DZ de G) 8,1e-14 ; symétrie, 20 057 paires, six cas, ≤ 5,2e-11 : RÉUSSI (niveau D) |
| `synthese` | source MED, écart MED/`.mess` 4,81e-13, 54 vues |
| `combinaisons` | 18 combinaisons |
| `ferraillage` | 128 sections × 14 combinaisons, `poutre.comm` exécuté (6,4 s) ; contrôle du module : 63 comparaisons, 2 échecs dans le critère (les mêmes qu'au lot 39, au bollard) |

## Résultats

### Comparaison aux références (`projets/quai_cw_test_01/references/comparaison_lot41.json`)

Script `projets/quai_cw_test_01/scripts/comparer_references_lot41.py` : chaque sortie
comparée à sa référence ; pour un fichier différent, chaque paire de lignes classée
« admis » (chemin ou empreinte énuméré par le critère) ou « non énuméré ». Aucune
valeur numérique n'est normalisée.

| Sortie | Résultat |
| --- | --- |
| `.comm` du modèle complet | différent : **ligne 6 seule** (`# Fiche : sha256:…`, la fiche citant désormais la base de constats) — admis. Ligne 7 (données) identique : le fichier de données n'a pas changé d'octets |
| rapport `mesh check` (599/599) | **identique** |
| invariants du maillage | différent : **lignes 3-4 seules**, commentaire d'en-tête (`# Produit par projets/quai_cw_test_01/scripts/build_lot27_maillage.py, à partir de projets/quai_cw_test_01/donnees/combiwall_model_data.yaml`) — chemins du script producteur et du fichier de données, **non énumérés** par le critère pour ce fichier : échec formel |
| contrôles D : `equilibre.json`, `integrale.json` | **identiques** (produits désormais par le tronc commun et l'extension du quai) |
| synthèse : `controles.md` | **identique** |
| synthèse : `synthese.json`, `synthese.md` | différents : chemins et empreintes du `.mess`, du MED, du `.comm` exécuté et chemin du fichier de données seulement — admis |
| combinaisons : `combinaisons.csv`, `extrema.csv`, `controle_manuel.json` | **identiques** (γ/ψ lus des données, contrôle manuel par le tronc commun) |
| combinaisons : `poutre_couronnement.md` | différent : ligne 3, chemins du `.mess` et du `.comm` exécuté — admis |
| ferraillage : `ferraillage.csv`, `enveloppes.csv`, `synthese.csv`, `synthese.md`, `controle_main.json`, `resume.json`, `sections.csv`, `efforts.csv`, `poutre.mail`, `poutre.export`, `figures/as_x.png` | **identiques** |
| ferraillage : `rapports/executions.json`, `rapports/mess_ferr_extrait.txt` | différents : répertoire, empreinte, date et durée de l'exécution ; date de la table — admis |
| ferraillage : `poutre.comm` | différent : **ligne 5 seule**, `# Produit par src/aster_expert/ferraillage/poutre.py -- ne pas éditer.` au lieu de `scripts/build_lot39_poutre.py` — chemin du producteur, **non énuméré** par le critère : échec formel |
| vues PNG de la synthèse (hors critère) | 54/54 identiques aux empreintes relevées à l'étape 1 |

Bilan : **18 fichiers identiques à l'octet, 6 différents uniquement par des chemins
et empreintes énumérés, 2 différents par des chemins non énumérés** ; aucune valeur
numérique différente.

### Rejeu des constats (`connaissances/constats_code_aster/rejeu/`)

Code_Aster 17.4.0, 2026-09-29, 2 min 52 s : **14 des 18 constats établis par
exécution tiennent** (toutes leurs valeurs de nouveau imprimées ; 41 cas rejoués sur 47) ;
**4 ne sont pas rejouables en l'état** (CA-029, CA-034, CA-035, CA-036 : les cas du
lot 34 sur le quai réduit lisent un maillage qui n'est pas versionné à côté du cas,
sans `.export`) ; **aucun à réexaminer**.

### Contrôles (commandes de l'énoncé)

| Commande | Sortie |
| --- | --- |
| `aster-expert mcp-check` | « mcp-check OK : 8 outils appelés sur un serveur neuf, identiques aux outils du code. » (`search_constats` → CA-035, niveau A) |
| `ruff format --check` | « 368 files already formatted » |
| `ruff check` | « All checks passed! » |
| `pytest tests/unit` | « 789 passed in 13.52s » |
| `pytest` | « 1164 passed, 3 deselected in 117.45s » (couverture totale 92 %, `cli.py` 88 %) |
| `pytest -m lent` | « 3 passed, 1164 deselected in 19.90s » |
| `mypy src` | « Success: no issues found in 97 source files » |
| `mypy` | « Success: no issues found in 261 source files » |

## Verdict

Au regard du seul critère écrit à l'étape 1 : **échec formel sur 2 fichiers sur 26**
(l'en-tête des invariants du maillage et l'en-tête du `.comm` de ferraillage
diffèrent par des chemins que le critère n'énumérait pas pour eux) ; réussite pour
les 24 autres (18 identiques, 6 différents par des chemins et empreintes énumérés).
Aucune valeur numérique ne diffère : déplacements, efforts, réactions, écarts
d'équilibre et de symétrie, combinaisons, aires d'acier et contrôles du module sont
identiques à l'octet. Niveau atteint sur le modèle complet : **C avec contrôles D**,
jamais E.

## Lecture

**Faits.**
- Le modèle complet, régénéré par le générateur déplacé dans le projet, s'exécute
  (`completed_ok`, 160 s, aucune alarme) et redonne les mêmes tables à l'octet que
  l'exécution du lot 37 (`equilibre.json`, `controles.md`, tables de combinaisons
  identiques) : Code_Aster 17.4.0 est déterministe sur ce modèle, à `.comm` égal
  aux commentaires près.
- Les contrôles D, les combinaisons et le ferraillage, désormais écrits une fois dans
  le tronc commun et paramétrés par `projet.yaml`, reproduisent exactement les
  sorties des scripts des lots 34, 38 et 39.
- Défaut trouvé en rejouant la chaîne dans un seul processus : les vues de la
  synthèse du quai modifient `matplotlib.rcParams` à l'import et changeaient la
  figure du ferraillage (`as_x.png`) quand les deux étaient produites dans le même
  processus (`projet … tout`). Corrigé (figure tracée avec les réglages d'origine) ;
  rejouée dans un seul processus, la figure est identique.

**Déductions.**
- Les deux différences non énumérées ne portent que sur des lignes de commentaire
  nommant le producteur d'un fichier généré ; le critère aurait dû énumérer aussi les
  chemins des producteurs. Elles sont rapportées comme échec, sans relâcher le
  critère.

**Recommandations (pas de décision).** Versionner à côté des cas du lot 34 le
maillage du quai réduit et un `.export`, pour rendre rejouables CA-029, CA-034,
CA-035 et CA-036. Faire relire par MM les 45 résumés de constats.

## Limites

- Les archives des essais (`data/examples/lotNN_*`) restent hors du projet ; leurs
  chemins restent ceux de leur lot. Les scripts historiques du quai déplacés dans
  le projet gardent leurs entrées d'origine (exécutions archivées) ; certains
  (lots 33 à 37) conservent leur propre calcul d'équilibre à côté de celui du tronc
  commun (ceux du lot 34 appellent désormais `quai_cw_test_01.controles`).
- Les textes émis dans le `.comm` et la synthèse citent encore des modules sous leur
  nom du lot 35-37 (`aster_expert.meshing.normals`, `aster_expert.report.*`), gardés
  pour l'identité des sorties.
- Le ferraillage du tronc commun couvre le 1D (sections rectangulaires, schéma
  `ssll13*`) ; le 2D reste absent. Les combinaisons couvrent les familles de
  l'EN 1990 déclarées ; les combinaisons sismiques ne sont pas prévues.
- Un seul projet existe : l'interface n'est éprouvée que sur le quai et sur le projet
  factice des tests ; aucun second ouvrage n'a été traité (hors périmètre).
- Rejeu : 4 constats non rejouables en l'état ; le critère du rejeu vérifie que la
  valeur est imprimée, pas à quelle grandeur elle correspond.
- Les résumés des constats sont rédigés par la session à partir du texte des
  constats, non relus par MM.
- Le lot ajoute un outil MCP : **redémarrer la session avant le lot suivant**.
