# Lot 48 bis — corriger ce que l'audit a trouvé de silencieux ou de bloquant

Profil `cloud` (première ligne d'`aster-expert env-check` : « Profil : cloud », 10 vérifications, 3 absences attendues).
Branche `claude/jolly-goodall-i1i5st`, qui contient la branche de l'audit du lot 48 (`main` ne la contient pas encore : le
commit `d7fbf87` de l'audit est dans l'historique de la branche, `main` est son ancêtre). Aucun envoi sur `main`.
Consigne : `docs/lots/lot48bis_consigne.md`. Aucun résultat d'ouvrage modifié : les `.comm`, les maillages, les paquets de
résultats et les valeurs sont inchangés ; seules les fiches de la dalle et de l'estacade gagnent `planned_commands`.

## 1. Défauts silencieux (R3, A15, A16)

**1.1 Validation B partielle.** Cause : `CHAR_MECA_GLOBAL=(CL,)` était lu comme une valeur dynamique
(`DynamicValue`), donc la commande et tout ce qui dépend de son concept `R` n'étaient pas confrontés, et `valid` valait
`len(errors) == 0`. Correctifs : nouvelle valeur `ConceptListValue` (`parsing/models.py`, liste ou tuple de littéraux et de
concepts connus, rien d'autre) reconstruite en liste de marqueurs de concept ; `ValidationReport.verdict` ∈ `valide`,
`partiel`, `invalide`, dérivé de `errors` et `commands_not_checked`, `valid` n'est vrai que pour `valide` ; `aster-expert
validate` code 2 pour `partiel`, code 1 pour `invalide`, liste des commandes non vérifiées ; `projet … valider` refuse un
rapport non valide. Preuve : la sonde de l'audit (`docs/audit/annexes_lot48/sonde_validation_b/tuple.comm`) rejouée :
`8/8 (100,0 %)`, `Erreurs remontées : 1`, verdict `invalide`, code 1, erreur `UNKNOWN_KEYWORD CALC_CHAMP ['MOT_INEXISTANT']`
(avant : `valid: true`, 6/8, code 0). Les trois `.comm` de production restent `valide` : quai 265/265, dalle 107/107,
estacade 420/420. Tests : `tests/unit/test_comm_parser.py::test_tuple_of_concepts_is_a_concept_list`,
`tests/unit/test_validate.py` (le test qui affirmait `valid is True` malgré une commande non confrontée affirme
désormais `False`/`partiel`, 3 autres idem ; `test_validate_comm_file_tuple_of_concepts_is_resolved`),
`tests/unit/test_cli_commandes.py::test_validate`.

**1.2 Rejeu.** `constats rejouer` et `connaissances rejouer-references` : code 2 dès qu'un cas est « non rejouable », code 1
pour « à réexaminer ». Preuve : avant la correction de 1.3, `connaissances rejouer-references --reference REF-014` répondait
`non rejouable` pour `dalle_h0p500` et `dalle_h0p250` avec le code 2 (avant : 0). Tests :
`test_cli_commandes.py::test_constats_rejouer`, `::test_rejouer_references_non_rejouable_code_non_nul`.

**1.3 REF-014.** Choix : **déclaration** des connaissances pour les deux cas manquants
(`dalle_h0p500.connaissances.yaml`, `dalle_h0p250.connaissances.yaml`, sur le modèle de `dalle_h0p125`), pas d'exemption.
Motif : ces cas sont des exécutions d'un projet comme les autres ; une exemption « cas de référence » ouvrirait une voie de
contournement de la règle du lot 46 (une exécution de projet déclare ce qu'elle applique) pour tout futur cas qu'on
appellerait « référence », et la déclaration coûte douze lignes. Preuve : `connaissances rejouer-references --reference
REF-014` → `REF-014 (réussi) : tient`, `dalle_h0p500` 6/6, `dalle_h0p250` 6/6 (deux lignes : maillage raffiné), `dalle_h0p125`
6/6, `1/1 référence(s) de validation tiennent sous Code_Aster 17.4.0`, code 0. Garde-fou :
`tests/unit/test_references_replay_mode.py::test_every_reference_case_of_a_project_declares_its_knowledge`.
Rejeu complet des 14 références : `14/14 tiennent`, 247 s, code 0.

**1.4 REF-015.** Voie retenue : **« observée »**. Le rejeu par la lecture du projet n'existe pas dans le tronc commun (la
lecture C1 à C13 est propre à l'estacade, `comparaison.py`/`comparaison_v2.py`, R5 de l'audit) et le rejeu du calcul complet
dure 2 268 s sans retrouver une valeur (0/30, grandeurs dérivées). REF-015 passe à `observé`, motif dans `status_history`
(`connaissances/references_validation/REF-015.yaml`). Règle de schéma : `ValidationReference.replay_mode` (`listing` seul,
registre `REPLAY_MODES`) ; une référence `établi` ou `promu` sans mode est refusée à la lecture ; REF-001 à REF-014
déclarent `listing` ; un rejeu complet saute (et dit) les références sans mode (`REF-015 : non rejouée`). Le mode est testé
(`test_references_replay_mode.py` : mode `listing` retrouve les valeurs imprimées et signale les absentes ; un mode ajouté au
registre doit y avoir son test). `connaissances verifier OK`.

## 2. Contrôles exécutables partout (R4)

**2.1 Termes confidentiels.** `ASTER_EXPERT_TERMES_INTERDITS` (variable d'environnement : secret GitHub Actions, variable de
l'environnement Cloud ; termes séparés par des retours à la ligne ou `;`) s'ajoute au fichier local de la VM
(`aster_expert.publication`). Un projet qui déclare `confidential_data: true` dans `projet.yaml` (aujourd'hui
`estacade_pieux_01`) rend la liste obligatoire : `--arbre` échoue sans elle, `--index` (crochet `pre-commit`) échoue quand un
fichier d'un tel projet est indexé. Preuve : sans la variable, `python -m aster_expert.publication --arbre` répond « projet à
données confidentielles sans liste de termes interdits » et code 1 ; avec elle, code 0. Cette session l'a rencontré
elle-même : le crochet a refusé un commit touchant l'estacade tant que MM n'avait pas fourni la liste (voir
« Interventions »). Procédure pour MM : `docs/cloud.md` § 11 (aucun terme écrit). Tests :
`tests/unit/test_publication.py` (variable, projet confidentiel sans liste, crochet d'index). Limite documentée : une variable
d'environnement Cloud est lisible par toute personne qui peut utiliser l'environnement (§ 5 de `docs/cloud.md`).

**2.2 Intégration continue.** `ci.yml` : `main`, `lot-*`, `claude/**`, secret passé à l'étape de publication. `ci-lent.yml` :
à la demande et sur envoi touchant `src/aster_expert/{execution,validation,connaissances}/` ou `connaissances/`, avec
`pytest -m lent_aster` puis `connaissances rejouer-references`. Tests : `tests/unit/test_ci_workflows.py`.
Durées et coût : voir le paragraphe « Durée et coût » en fin de section.

**2.3 `pre-push`.** `scripts/git-hooks/pre-push` : `ruff format --check`, `ruff check`, `pytest` (hors tests lents), refus au
premier échec. Preuve réelle : lors du premier envoi de ce lot, il a lancé `pytest` (266 s) et **refusé l'envoi** pour 3 tests
du faux projet (`tests/unit/test_projet_pipeline.py`) que l'exigence de `planned_commands` cassait : corrigés avant l'envoi
(`tests/conftest.py`). Tests : `tests/unit/test_hook_pre_push.py` (ordre, premier échec, absence de branche distante).

**Durée et coût** (mesures locales dans le conteneur Cloud, 4 vCPU ; les minutes facturées de la CI sont relevées après envoi,
voir plus bas) : `ruff format --check` 1 s, `ruff check` < 1 s, `mypy src` < 1 s (cache), `mypy` 3 s, `pytest` 245 s (1 677
réussis, 8 ignorés), `pytest -m lent_aster` 36 s (3 tests), rejeu des 14 références 247 s. Estimation du coût de `ci-lent` :
mise en place (tirage de l'image de 5 Go, `uv sync`, extraction du catalogue) + 36 s + 247 s.

## 3. Fiche : commandes prévues et arbitrages (R6)

**3.1 `planned_commands`.** `aster-expert fiche prevoir <projet> [--comm …] [--ecrire]` déduit du `.comm` une commande prévue par
commande et par combinaison d'options que le catalogue ou les règles d'exécution testent et que le `.comm` écrit en clair
(pas d'option déduite d'un nom de groupe), rattachée au point du constat qui nomme la commande (à défaut au premier point
pratique) ; aucune couverture n'est déduite. `projet <nom> verifier` exige `planned_commands` (ou
`planned_commands_exemption`, motif visible). Dalle : 20 commandes (dont 3 `CALC_FERRAILLAGE` ELU, ELS, ELS_QP) ; estacade :
23 commandes. Quai : exemption motivée dans `projet.yaml` (fiche produite par script avant le lot 44).
`fiche obligatoires` trouve alors :

- *dalle* (couverture des `CALC_FERRAILLAGE` posée à `point:14` et `point:9`, d'après la couverture du lot 44) : 3 manques
  restants, tous « mm:non classé » et sans portée d'ingénieur : `DEFI_CONSTANTE/VALE`, `POST_RELEVE_T/ACTION.OPERATION`,
  `POST_RELEVE_T/ACTION.INTITULE` (mots-clés de lecture de tables, que la table de catégories
  `data/config/obligations_execution.yaml` ne classe pas). Sans la couverture posée, les 29 paramètres de
  `CALC_FERRAILLAGE` ressortaient « manquants ».
- *estacade* : 5 manques sans couverture, tous « mm:non classé » : `CREA_CHAMP/TYPE_CHAM` et `AFFE.NOM_CMP`,
  `CREA_RESU/AFFE.NOM_CHAM` (OPERATION=AFFE, variante thermique), `POST_RELEVE_T/ACTION.OPERATION` et `INTITULE`. Aucun
  paramètre de ferraillage (le projet n'en a pas).
- Défaut trouvé : le lecteur de conditions du catalogue (`aster_expert.agent.obligatoires._holds`) **abandonnait toute la
  vérification** sur `CALC_CHAMP` (`is_type("RESULTAT") in (...)`). Corrigé : un mot-clé dont la condition n'est pas
  interprétable n'est ni compté obligatoire ni compté absent, il est **listé** (`NON INTERPRÉTÉE CALC_CHAMP/… (n
  condition(s))` : 14 mots-clés de `CALC_CHAMP`, `CREA_CHAMP/PROL_ZERO`, `IMPR_RESU/RESU.PARTIE`, `RESU.TYPE_NOM`).

Tests : `tests/unit/test_projet_portee_bloqueurs.py` (verifier exige les commandes, dérivation rejouée = fiches
versionnées), `tests/unit/test_agent_obligatoires.py`. Les scripts qui réécrivent ces fiches (`fiche_lot47.py`,
`decisions_lot45.py`) conservent désormais `planned_commands` (`carry_planned_commands`) ; leurs tests de reproduction
comparent le reste à l'octet.

**3.2 `fiche enregistrer`.** `aster-expert fiche enregistrer <projet> <arbitrage.md> [--simuler]` lit un fichier structuré
(`aster_expert.agent.enregistrement` : en-têtes `Source du texte`, `Enregistré le`, domaine de validité par défaut ; une
section `### <point> — <sujet>` par décision avec le texte cité, les variantes écartées, notes et domaine facultatifs). Le
texte cité de chaque décision doit figurer **à l'identique** dans le fichier source de MM (jamais retapé). Rejeu de E13 à E16 de
l'estacade (`donnees/sources/enregistrement_E13_E16_lot48bis.md`) : la fiche d'avant E13 à E16 (questions rouvertes) devient,
après l'enregistrement, **identique** à la fiche versionnée (`model_dump_json` égaux,
`tests/unit/test_fiche_enregistrer.py::test_replaying_e13_to_e16_gives_the_recorded_fiche`) ; ré-arbitrer une décision
déjà prise la conserve dans `decision_history` ; un point absent est inséré ; un texte retapé, une date sans fuseau, une
puce inconnue sont refusés.

## 4. Bloqueurs limités à leur étape (R8)

`projet.yaml` déclare `blocker_scopes` (point, sujet exact, étapes que la révision bloque, motif). Quai : la révision du point 14
(Es, PRE-032) ne bloque que `ferraillage` ; `HypothesesSheet.generation_blockers(waived_revisions=…)` n'écarte que des
**révisions** (jamais une question ouverte) et chaque étape dit ce qu'elle a écarté. Preuves :

- `aster-expert projet quai_cw_test_01 verifier` : passe, avec la ligne « Révision du point 14 (…Es) non bloquante pour
  `verifier` … (bloque : ferraillage) » ;
- `projet quai_cw_test_01 generer` : ne s'arrête plus sur le bloqueur mais sur « maillage vérifié inconnu » (le maillage est
  produit par Salomé, VM seulement) ; le générateur du quai reçoit les révisions écartées
  (`test_the_quai_generator_waives_the_declared_revision`) ;
- `validate` du `.comm` de production du quai (`references/comm/complet.comm`) : 265/265, verdict `valide` (l'étape `valider` ne
  lit pas les bloqueurs) ;
- `projet quai_cw_test_01 ferraillage` : « ferraillage refusé » avec le bloqueur Es (testé).
  Es n'est lu que par le ferraillage (`eys_pa` : `ferraillage/poutre.py`, `projet/check.py`, `projet.yaml`).

**Paquets de la dalle et du quai : non réexportés avec le harnais D — à faire au lot 49 (VM).** `exporter-resultats
--reevaluer` ne relit que les fichiers du paquet, pas le `.mess` d'où le harnais D tire ses contrôles (aucune archive
d'exécution dans le Cloud). Pire, le dépôt Cloud est un clone **tronqué** (`git rev-parse --is-shallow-repository` : `true`,
53 commits) : sur le quai, la réévaluation a conclu « antériorité démontrable » pour des critères que le paquet disait non
démontrables, faute d'historique ; ce résultat est faux, le fichier a été restauré (aucun paquet modifié). Dalle :
réévaluation identique à l'existant. Règle ajoutée à `CLAUDE.md` : ne pas utiliser `--reevaluer` dans un dépôt tronqué.

## 5. Allègements (R10 a, c, e)

**5.1 `CLAUDE.md`** : 1 141 → 391 lignes (`tests/unit/test_claude_md.py` : < 400 lignes, ancres des règles). Copie intégrale de
l'ancien fichier : `docs/historique/claude_md_avant_lot48bis.md` (rien n'est perdu). Règles avant et après :

- *Conservées à l'identique* (lignes 1 à 475 de l'ancien fichier, reformatées sans changer un mot, sauf les puces d'historique
  des outils MCP) : langue de travail ; organisation (tronc commun et projets) ; Python du projet (`.venv`, `uv`) ; GitHub,
  branches et Cloud (un lot, une branche ; profil annoncé ; interdits de publication ; crochet) ; base de connaissances et
  retour d'expérience ; fiche (choix de l'agent, promotion, `planned_commands`) ; mission ; environnement d'exécution ;
  principes fondamentaux 1 à 11 ; ne pas réimplémenter `run_aster` ; niveaux de validation A à E ; langue ; priorité des
  sources ; règles de développement ; dépôts externes ; validation obligatoire ; critère de réussite des essais ; fin de lot ;
  accès MCP ; règles d'écriture des scripts Salomé (partition unique, groupes sur la géométrie, aucune coordonnée en dur,
  `meta.json`, arguments nommés, discrétisation explicite, comptages attendus, progression, signatures par introspection).
- *Déplacées dans la section « Règles tirées des lots 19 à 46 »* (règles contenues dans l'ancien historique) : JSON de fiche
  jamais édité à la main ; révision par `record_practice_decision` ; `date=None` pour une norme datée d'un mois ; `group_naming_gaps`
  signale sans corriger ; entrée `code_aster` non tranchée sans option retenue ; règles d'`ExecutionSource` ; `declare_under_revision`
  / `lift_revision` ; valeur « à fournir » jamais complétée sans source ; `ELAS_COQUE` (jamais `REAC_NODA`, `FORC_NODA`,
  `SIEF_ELGA`, `RHO = 0` sans alarme) ; ressorts par classe, `CREA_POI1` une maille par nœud, `DIS_T` sous `PESANTEUR` ; noms de
  groupe ≤ 24 caractères ; `IMPR_TABLE` (16 caractères, `E20.12`) ; cas tests par les outils MCP seulement ; `.export` et
  `allowed_roots` ; serveur MCP en retard sur le code ; état de Salomé ; règle de conservation d'un niveau ; notes Word ;
  archives refusées ; décisions en vigueur (Es = 200 GPa, D20, D21, `FERR_MIN`, marqueurs `[À CONFIRMER MM]`).
- *Retirées de `CLAUDE.md`* (historique, copié verbatim dans `docs/historique/…` et résumé dans `docs/etat.yaml` et les
  `docs/essais_lotNN.md`) : le compte rendu de chaque lot 26 à 46 (valeurs, durées, chemins), les puces de comptage d'outils MCP
  (« huit outils depuis le lot 41 », « neuf depuis le lot 42 »), l'état de la fiche du combi-wall des lots 19 à 24.
- *Ajoutées au lot 48 bis* : validation partielle, codes de rejeu, `replay_mode`, termes confidentiels, `pre-push`,
  `blocker_scopes`, `fiche prevoir`/`enregistrer`, grille et table d'arrondi, `--reevaluer` en dépôt tronqué.

**5.2 Mode résumé** (`aster_expert.mcp.resume`) : au-delà de 150 commandes, `analyze_comm` et `validate_comm` répondent par
défaut un résumé ; `detail="complet"` force l'entière ; `command` ou `line_start`/`line_end` filtrent. Sur le `.comm` de
l'estacade (1 695 lignes) : `analyze_comm` **892 461 → < 20 000 caractères**, `validate_comm` ≈ 50 000 → < 20 000
(`tests/unit/test_mcp_resume.py`, y compris l'appel réel à Docker). Le verdict est toujours celui du fichier entier, même
filtré. `mcp-check` : `mcp-check OK : 9 outils appelés sur un serveur neuf, identiques aux outils du code`.

**5.3 Code mort.** Supprimés : `notes/controle.py:sheet_points`, `notes/hypotheses.py:hypotheses_sources`,
`retrieval/config.py:default_retrieval_config_path`. **Correction de l'audit** : `config/retrieval.yaml` n'est pas lu « par les
tests seulement » : `cli.py` le lit par `load_source_priority` (trois commandes) ; il est conservé. Seul
`retrieval.config.load_retrieval_config` n'est lu que par ses tests (conservé : lecture typée documentée, test sur le fichier
réel). Test de frontière du tronc commun étendu : `dalle_appuyee`, `DALLE-APPUYEE`, `estacade_pieux`, `ESTACADE-PIEUX`,
`chevêtre`, le mot `estacade` ; 0 occurrence dans `src/`. Le mot « dalle » seul n'est pas interdit (il désigne aussi les
plaques génériques du ferraillage 2D).

## 6. Nombres dans les maillages et les fichiers produits

**6.1 Fait établi** (`scripts/rapport_grille_lot48bis.py`, `scripts/sonde_arrondi_med.py`, medcoupling en conteneur,
`data/examples/lot48bis_grille/rapport_grille.json`) : arrondir les coordonnées à 1 mm ne réduit **ni la taille ni le nombre
de lignes** : quai (40 114 nœuds, 79 703 mailles) 4 908 789 → 4 908 612 octets (−0,004 %), dalle h0p125 152 295 → 152 202
(−0,06 %), dalle h0p500 28 527 → 29 479 (+3,3 %, aucune coordonnée modifiée : la réécriture ajoute des métadonnées) ; nœuds et
mailles identiques. Le gain est dans la lisibilité, la recherche de nœuds et la robustesse des groupes. Attention : arrondir
**toutes** les coordonnées déplacerait les nœuds de facettes (tubes du quai : jusqu'à 0,40 mm) ; la grille ne vaut que pour
les coordonnées voulues sur la grille, d'où un invariant « presque sur la grille sans y être ».

**6.2 Invariant de grille** (`aster_expert.meshing.grille`, `mesh check` ; règle dans `config/arrondis.yaml` : grille 1 mm,
ε = 1e-6 m, non bloquant). Justification de 1 mm : plus fine que toute cote des trois ouvrages (mailles de 0,05 à 0,50 m,
cotes au centimètre), plus grosse que le bruit de calcul (écarts relevés ≤ 7,5e-14 m). Rapporté séparément des invariants du
projet (leur compte ne change pas), bloquant seulement si la table le dit. Écarts sur les maillages versionnés (aucun modifié) :

| maillage | coordonnées « presque sur la grille » | écart max (m) |
|---|---|---|
| lot 26 : plaque, poutre-barre, tube-plaques | 0 sur 75, 57, 2 508 | 0 |
| quai complet (lot 27, lot 28) | 1 162 sur 120 342 (1 058 nœuds sur 40 114) | 1,8e-15 |
| quai réduit (lot 30) | 136 sur 30 612 | 1,8e-15 |
| quai réduit fin (lot 37) | 259 sur 60 624 | 1,8e-15 |
| dalle h0p500 / h0p250 / h0p125 | 0 / 18 / 110 | 0 / 4,4e-16 / 4,4e-16 |
| estacade | 135 215 sur 228 219 (75 091 nœuds sur 76 073) | 7,5e-14 |

Règle ajoutée pour les scripts de maillage (`CLAUDE.md`) ; les scripts eux-mêmes ne sont pas modifiés dans ce lot.

**6.3 Table d'arrondi** (`config/arrondis.yaml`, `aster_expert.arrondis`) : m 3, kN 1, kN·m 1, MPa 2, etc. ;
`format_value`, `round_value`, `comm_value` (valeur dérivée d'un calcul exact : `repr` complet dans le `.comm`, valeur arrondie en
commentaire) ; `NoteColumn.unit` (colonne de note arrondie selon la table, sans `format`). Tests :
`tests/unit/test_arrondis_grille.py`. **Non fait dans ce lot, et pourquoi** : aucun générateur de `.comm` ni déclaration de note
existant n'a été modifié, parce que (a) les `.comm` de référence sont comparés à l'octet par la règle de conservation des
niveaux et par `projet exporter-resultats` (un commentaire change l'empreinte), (b) `combinaisons.csv` et `extrema.csv`
alimentent le ferraillage : les arrondir violerait « les contrôles numériques travaillent sur les valeurs non arrondies ».
L'adoption par les projets (colonnes `unit` des notes, commentaires de `.comm`) est à faire avec leur régénération, dans la VM
(lot 49).

## Contrôles

Commandes lancées et sorties (profil Cloud) :

| commande | résultat |
|---|---|
| `aster-expert env-check` | `env-check OK (profil cloud) : 10 vérifications, dont 3 absences attendues` |
| `aster-expert mcp-check` | `mcp-check OK : 9 outils appelés sur un serveur neuf, identiques aux outils du code` (`analyze_comm` : level A ; `validate_comm` : level B, valid=True) |
| `ruff format --check` | tous les fichiers déjà formatés, code 0 |
| `ruff check` | `All checks passed!` (après correction de lignes trop longues dans deux scripts) |
| `mypy src` ; `mypy` | `Success: no issues found` (138 fichiers ; 401 fichiers) |
| `pytest` | 1 677 réussis, 8 ignorés, 4 désélectionnés en 245 s ; 1 échec attendu corrigé ensuite (`test_check_med_reads…`, assertion sur la dernière ligne du rapport de maillage), relancé : réussi |
| `pytest -m lent_aster` | 3 réussis, 36 s |
| `connaissances verifier` | `connaissances verifier OK` (300 preuves ; 55 exécutions archivées non vérifiables : archive absente) |
| `connaissances rejouer-references --reference REF-014` | `tient`, 3 maillages, code 0 |
| `rex <projet>` (dalle, quai, estacade) | archive refusée (non conforme, partielle, absente) : seuls les champs déclarés sont écrits, aucun écart ; aucune exécution de développement nouvelle |

## Interventions de MM

- Une : la liste des termes confidentiels, fournie dans le chat à la demande de la session (le crochet `pre-commit` refusait
  un commit touchant l'estacade) ; utilisée comme variable d'environnement de la seule commande, jamais écrite dans un fichier,
  un journal ou un message de commit.
- La remarque sur les nombres des maillages (point 6) est un apport de la consigne.

## Limites et points non couverts

- Paquets de la dalle et du quai non réexportés avec le harnais D (Cloud : pas d'archive, dépôt tronqué) : lot 49, VM.
- `generer` et `valider` du quai de bout en bout : le maillage vient de Salomé (VM) ; ici, blocage levé et `.comm` versionné
  validé, mais pas de régénération.
- `planned_commands` du quai : exemption motivée, à remplir dans la VM.
- Table d'arrondi non adoptée par les générateurs de `.comm` ni par les notes existantes (voir 6.3).
- `fiche obligatoires` reste en code 1 sur la dalle et l'estacade : les mots-clés de lecture de tables ne sont pas classés dans
  `obligations_execution.yaml`.
- Mode de rejeu `projet` (lecture du projet) non réalisé : REF-015 reste observée.

## Outils MCP

**Les outils MCP ont changé** (`analyze_comm` et `validate_comm` : paramètres `detail`, `command`, `line_start`, `line_end` ;
nouveaux champs `verdict`, `detail`, `summary` ; description révisée). **Redémarrer la session (ou reconnecter le serveur,
`/mcp`) avant le lot suivant.**
