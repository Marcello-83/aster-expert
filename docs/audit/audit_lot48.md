# Audit de l'outil AsterExpert — lot 48 (lecture seule, profil Cloud)

Date : 2026-10-07. Dépôt audité : `main` au commit `3dc21f1` (lot 47 quater), arbre propre
au départ, branche de travail `claude/friendly-archimedes-fu7o0l` partie de ce commit.
Auditeur : session neuve, sans participation à aucun lot. Profil `cloud` (première ligne
d'`env-check`).

Seuls ce rapport et `docs/audit/annexes_lot48/` sont écrits. Aucune ligne de code, de test,
de fiche, de donnée ni de connaissance n'est modifiée. Les sondes et les calculs lancés pour
l'audit écrivent dans `data/processed/` (non versionné) ou dans le répertoire temporaire de
la session.

Les preuves viennent du dépôt, de l'historique Git, des tests et des exécutions lancées
pendant l'audit. `CLAUDE.md`, `docs/etat.yaml` et les comptes rendus de lot ont servi à
savoir **où** chercher. Ils ne servent jamais de preuve, et ils sont confrontés au dépôt
lorsqu'ils affirment quelque chose.

**Limite du profil Cloud, valable pour tout le rapport.** Les archives d'exécution
(`data/processed/runs/` de la VM), Salomé et le dossier partagé sont absents. Ce qui en
dépend est jugé sur les fichiers versionnés : paquets de résultats, registres `rex`,
métriques. La mention « non vérifiable dans le Cloud » le signale à chaque fois.

---

## 1. Synthèse pour MM (une page)

**Ce qui a changé depuis l'audit du lot 40.** À l'époque, l'outil ne savait traiter que le
quai. L'essai sur une dalle s'arrêtait dès la recherche documentaire. Aujourd'hui, trois
ouvrages passent par la même chaîne : le quai, la dalle et l'estacade. Le code commun à tous
les ouvrages est séparé du code propre à chaque ouvrage, et un test en vérifie la frontière
pour le quai. Ont aussi été ajoutés une base de connaissances (169 entrées), des notes Word
produites sans texte écrit à la main, des paquets de résultats versionnés et une intégration
continue. Neuf des dix recommandations du lot 40 sont faites ou en partie faites ; une seule
n'est pas faite (R9, le ferraillage).

**Niveau réellement atteint.**

- Dalle : **niveau E**, contre la solution de Navier, avec des critères écrits avant le calcul.
- Quai : **niveau D**. Les critères D ont été versés dans le même commit que les résultats :
  on ne peut donc pas démontrer qu'ils ont été écrits avant. Le quai **ne peut plus être
  régénéré aujourd'hui**, parce que la décision Es = 200 GPa est en attente d'application
  depuis le lot 45.
- Estacade : **niveau D**, mais le critère D en vigueur a été écrit après le calcul. C'est
  un contre-calcul d'un modèle non validé : 13 écarts sont attribués à une cause, 2 restent
  inexpliqués.

**Ce que l'audit a vérifié lui-même dans le Cloud.**

- Tests : 1 622 tests réussis, couverture mesurée à 85 %.
- Constats : 5 constats tirés au sort, établis par calcul, ont été rejoués ; ils tiennent.
- Maillages : les maillages versionnés de la dalle et de l'estacade respectent tous leurs
  invariants.
- Estacade : le `.comm` se régénère à l'identique (hors commentaires). Le calcul complet,
  rejoué dans le Cloud, aboutit sans alarme (38 min). En revanche, aucune des 30 valeurs de
  sa référence de comparaison ne peut être revérifiée automatiquement : ce sont des grandeurs
  calculées après coup, que le mécanisme de rejeu ne sait pas retrouver.
- Recherche documentaire : sur les 63 questions du lot 40, elle donne exactement le même
  score qu'au lot 40 (82,5 %). Elle n'a pas progressé.

**Cinq défauts relevés pendant l'audit.**

1. La seule référence de niveau E promue (REF-014, la dalle contre Navier) **ne se rejoue
   plus qu'à un maillage sur trois**. Une règle ajoutée au lot 46 bloque les deux autres.
2. Le validateur de niveau B répond « valide », avec un code de sortie 0, sur un fichier dont
   il n'a pas pu vérifier une partie. L'audit l'a reproduit sur une erreur réelle, qui est
   passée inaperçue.
3. Dans le Cloud et en intégration continue, la liste des termes confidentiels est absente.
   Le contrôle de publication passe alors **sans rien vérifier**.
4. La détection des paramètres obligatoires (lot 44) n'a jamais servi : aucune des trois
   fiches ne déclare les commandes qu'elle prévoit.
5. La référence de comparaison de l'estacade (REF-015) est classée « établie », c'est-à-dire
   rejouable ; en réalité, l'outil ne sait pas la rejouer (0 valeur sur 30 retrouvée après
   un calcul pourtant réussi).

**La courbe d'apprentissage.** Elle est réelle mais étroite.

- Ce qui progresse : le taux d'échec des calculs baisse (41 % pour le quai, 25 % pour
  l'estacade), le nombre d'interventions déclarées de MM baisse aussi, et la base reconnaît
  automatiquement la moitié des échecs de l'estacade.
- Ce qui ne baisse pas : le gros du coût. Chaque ouvrage demande encore 5 000 à 9 000 lignes
  de code Python écrites par une session pour cet ouvrage, et les quatre lots de l'estacade
  ont été orientés à chaque reprise par une hypothèse ou une relecture du superviseur.
- Les interventions déclarées sous-estiment l'apport de MM. Les décisions et les diagnostics
  écrits dans les consignes n'y sont pas comptés.

**Avant les deux prochains ouvrages.**

- Rien dans l'outil n'a jamais été exécuté en volumique 3D, en non-linéaire, en contact, en
  dynamique, en thermique transitoire, en phasage ou avec une loi de sol. Ni la base de
  connaissances ni le banc de recherche ne couvrent ces domaines.
- Pour la poutre de couronnement en 3D, il faut d'abord une référence volumique de niveau E,
  le raccord avec le sous-modèle et une méthode de passage des contraintes au ferraillage.
- Pour la forme de radoub, il faut d'abord des cas tests officiels non linéaires rejoués
  jusqu'au niveau E, des contrôles propres à un calcul incrémental et une procédure de
  phasage.

Le § 8 donne dix recommandations.

---

## 2. Étape 0 — environnement et outils MCP

| Commande | Résultat | Annexe |
|---|---|---|
| `aster-expert env-check` | `env-check OK (profil cloud) : 10 vérifications, dont 3 absences attendues` (cave, Salomé, partage) ; image `simvia/code_aster:17.4.0` par digest ; 4 processeurs, 15,7 Go ; 6,5 s | `journaux/env-check.txt` |
| `aster-expert mcp-check` | `mcp-check OK : 9 outils appelés sur un serveur neuf, identiques aux outils du code` ; 86,6 s | `journaux/mcp-check.txt` |

Chaque outil MCP a aussi été appelé directement, depuis la session, au moins une fois :

| Outil | Appel de l'audit | Résultat |
|---|---|---|
| `search_codeaster_docs` | « contact frottement DEFI_CONTACT », profil `methode` | R5.03.50, R5.03.52 ; niveau A |
| `get_document_section` | `R5.03.50#Conclusion` | section intégrale (1 469 caractères) |
| `get_command_schema` | `DEFI_MATERIAU`, mot-clé `MOHR_COULOMB` ; `AFFE_CHAR_MECA`, `LIAISON_SOLIDE.GROUP_NO` | sous-arbre seul (`keywords_omitted` 268 et 51) |
| `search_test_cases` | `DEFI_CONTACT` (251 cas) ; `AFFE_CHAR_MECA`/`LIAISON_SOLIDE` (69 cas) | 4 480 fichiers analysés, 0 illisible |
| `read_test_case` | `erreu08a.comm`, `sdlx03b.comm`, `ssls127a.comm` (plages) | niveau A |
| `search_constats` | mot-clé `LIAISON_SOLIDE` | 3 résultats, **tous de score 0** : CA-029 (pression aux nœuds) sort en tête, avant CA-035 et CA-036, plus pertinents |
| `search_connaissances` | couche `diagnostics`, mot-clé `FACTOR_11` | DIAG-001 |
| `analyze_comm` | `.comm` de l'estacade (1 695 lignes) | **892 461 caractères** de réponse : au-delà de la limite d'une réponse d'outil, inexploitable sans post-traitement |
| `validate_comm` | même fichier | niveau B, `valid=true`, 420/420 commandes ; réponse de ≈ 50 000 caractères |

Constat d'ergonomie : sur un `.comm` d'ouvrage réel, les deux outils de lecture de `.comm`
renvoient des réponses trop volumineuses pour être lues par un agent. Ni l'un ni l'autre
n'offre de mode résumé.

---

## 3. Étape 1 — suivi des recommandations du lot 40

| # | Recommandation (lot 40) | État | Preuve |
|---|---|---|---|
| R1 | Interface « famille d'ouvrage », quai déplacé sans changer sa sortie | **faite**, sous la forme « projet » | `src/aster_expert/projet/declaration.py` (`ProjectDeclaration`) ; `projets/*/projet.yaml` ; commit `1d38cc9` (lot 41) ; `aster-expert projet <nom> verifier` passe pour la dalle et l'estacade (`journaux/projet_verifier.txt`). Réserve : chaque projet écrit son propre générateur. Il n'existe aucune « famille » réutilisable d'un ouvrage à l'autre (§ 6.2) |
| R2 | Dalle comme deuxième famille, premier niveau E | **faite** | `projets/dalle_appuyee_01/resultats/paquet/paquet.json` : niveau E, critères commités avant l'exécution (`4093f12`, `anteriorite_demontrable: true`) ; REF-014. Réserve : REF-014 n'est plus rejouable qu'à un maillage sur trois (§ 4.3) |
| R3 | Données de projet hors du code, test qui interdit les nombres d'ouvrage dans `src/` | **faite** pour `src/` | `tests/unit/test_tronc_commun_sans_ouvrage.py` (identifiants du quai seulement). Recherche de l'audit dans `src/` : aucun nom d'ouvrage (§ 6.1). Réserve : le test ignore les noms de la dalle et de l'estacade ; l'estacade code ses coefficients de combinaison en Python (`projets/estacade_pieux_01/combinaisons.py:17-60`, choix assumé par la décision E11 et vérifié par un test contre le texte de l'annexe) |
| R4 | Contrôle d'adéquation de `generate` et `report` | **faite** | Essai de l'audit : `aster-expert generate estacade_pieux_01 --donnees <données de la dalle>` donne un refus lisible (« les données … sont celles de l'ouvrage 'DALLE-APPUYEE-01' », 13 données manquantes nommées), sans trace Python |
| R5 | Base de constats hors des fiches | **faite** | `connaissances/constats_code_aster/` : 58 constats ; fiches à références ; `aster-expert constats rejouer` (5/5 tiennent, § 4.3) |
| R6 | Contrôles, combinaisons, ferraillage et arbitrage dans `src/` et la CLI ; scripts sous `mypy` | **partielle** | Étapes `projet <nom> controles\|combinaisons\|ferraillage` ; `src/aster_expert/{controles,combinaisons,ferraillage}`. Restent **75 scripts de lot dans `projets/*/scripts/`** (sur 76) et 27 dans `scripts/` (sur 28). L'enregistrement des arbitrages passe toujours par un script de projet (`fiche_lot47.py`, `build_combiwall_reference.py`). Le `mypy` des scripts de projet existe, mais `scripts/` n'est pas typé |
| R7 | Compte rendu JSON par `run` et encapsulation de `run_aster.error_messages` | **faite** | `src/aster_expert/execution/compte_rendu.py:8`, `models.py:150-188` ; `tests/unit/test_execution_compte_rendu.py` |
| R8 | Petite suite d'intégration réelle, lancée avant chaque lot | **partielle** | `pytest -m lent_aster` : **3 tests**, réussis en 20,7 s dans le Cloud. `ci-lent.yml` est **manuel** : sur 3 passages, 1 seul vert (2026-10-05, branche du lot 46 bis). Il n'a pas été relancé après les changements de l'exécuteur aux lots 47 ter et 47 quater. `lent_salome` ne tourne que dans la VM |
| R9 | Clore les écarts de ferraillage avant toute note (7.2N, γ accidentels, ligne MM, ELS, 2D) | **non faite** (le 2D excepté) | Tableau 7.2N « à vérifier par MM » (`docs/etat.yaml:125`, PRE-020). `data/examples/lot38_essais/ligne_comparaison_mm.csv` : colonnes de MM toujours vides, inchangé depuis `a88472c`. Écart ELS ouvert (ANO-001). Fait : ferraillage 2D au tronc commun (`ferraillage/plaque.py`, dalle). Les notes de résultats existent pourtant (lot 45) |
| R10 | Enrichir le banc, le faire annoter par MM, viser `methode` et `theorie` | **partielle** | 87 questions (contre 65) ; les 22 nouvelles viennent du journal des requêtes, avec un tri validé par MM mais des **documents attendus choisis par la session** (`origin` de `eval-066` à `eval-087`). Aucune question en « description d'ouvrage ». Moteur inchangé : 52/63 sur les anciennes questions, comme au lot 40 (§ 5) |

Bilan : 5 faites, 4 partielles, 1 non faite.

---

## 4. Étape 2 — inventaire factuel

### 4.1 Commandes CLI (44) et outils MCP (9)

Au lot 40, il y avait 25 commandes et 7 outils. La dernière utilisation réelle n'est pas
vérifiable dans le Cloud : `query_log.jsonl` et les archives d'exécution ne sont pas
versionnés. La colonne s'appuie donc sur les registres `rex` et sur les comptes rendus
versionnés.

| Famille | Commandes | Ce qu'elles font | Tests (exemples) | Dernière utilisation attestée |
|---|---|---|---|---|
| Corpus | `sources sync\|inventory\|probe\|xref\|command-map`, `fragments build`, `index build` | dépôts Code_Aster, fragments, index BM25 | `test_sources_sync.py`, `test_xref.py`, `test_bm25_index.py` | chaque ouverture de session Cloud (`scripts/cloud_setup.sh`) ; manifeste du 2026-10-07 |
| Catalogue, `.comm` | `catalogue extract\|show`, `comm parse`, `validate` | introspection, analyse, niveau B | `test_catalogue_*.py`, `test_comm_parser.py`, `test_validate.py` | `validate` : lot 47 quater (Q1 à Q4) ; cet audit |
| Recherche, banc | `search`, `section`, `eval bench\|profile-bench\|score\|summary\|decompose\|candidats` | BM25, mesure hit@k | `test_bench.py`, `test_evaluation.py`, `test_banc_lot44.py` | banc : lot 44 ; cet audit |
| Exécution | `run`, `env detect`, `env-check`, `mcp-check` | calcul en conteneur, environnement | `test_execution_*.py`, `test_env_check.py`, `test_mcp_check.py` | `run` : 2026-10-07T07:56 (dernière exécution de l'estacade, registre) |
| Maillage | `mesh run\|check` | Salomé (VM), vérificateur MED | `test_meshing_run.py`, `test_meshing_invariants.py` | `mesh run` : lot 47 ter (VM) ; `mesh check` : cet audit |
| Projet | `projet <nom> <étape>`, `projet creer\|exporter-resultats`, `generate`, `report` | enchaînement, paquet | `test_projet_*.py`, `projets/*/tests/` | paquet de l'estacade : 2026-10-07T09:34 |
| Connaissances | `constats chercher\|rejouer`, `connaissances chercher\|verifier\|promouvoir\|eligibilite\|eprouver\|proposer-precedent\|rejouer-references`, `rex` | base à six couches, retour d'expérience | `test_connaissances*.py`, `test_rex_*.py`, `test_constats.py` | `rex` : lot 47 quater ; `promouvoir` : lot 44 (dernière promotion) ; `proposer-precedent` : jamais par la CLI (le précédent du lot 47 ter est un fichier `.md`) |
| Fiche, notes, état | `fiche obligatoires`, `note hypotheses\|resultats\|controler`, `etat readme\|verifier` | paramètres obligatoires, Word, état | `test_agent_obligatoires.py`, `test_notes*.py`, `test_etat.py` | notes : lot 47 quater ; `fiche obligatoires` : **sans effet sur les trois fiches** (0 commande prévue, § 5) |

Les 9 outils MCP sont listés au § 2. Les comptes d'appels des métriques
(`consultations.calls`) viennent d'un journal local non versionné. Les mêmes chiffres
apparaissent pour le quai et la dalle (12 et 1), et des chiffres différents pour l'estacade
(43 et 3), selon la machine et le moment du calcul. Ce compteur n'est **pas reproductible** :
dans le Cloud, `rex` affiche aujourd'hui 1 et 1.

### 4.2 `src/` : taille, couverture, dépendances, code mort

Mesure de l'audit :
`pytest --cov=aster_expert --cov=quai_cw_test_01 --cov=dalle_appuyee_01 --cov=estacade_pieux_01`.
Résultat : **1 622 réussis, 8 ignorés, 4 désélectionnés (tests lents), 320,8 s**. Couverture
globale **85 %** (21 260 instructions). Le détail est dans `couverture_lot48.tsv`.

| Module | Fichiers | Lignes | Couverture | Dépendances externes | Dépend de (tronc commun) |
|---|---|---|---|---|---|
| `connaissances` | 13 | 4 331 | 88,5 % | pydantic, yaml | agent, constats, execution, mcp, retrieval |
| `projet` | 8 | 3 093 | 87,5 % | pydantic, yaml | agent, connaissances, meshing |
| `notes` | 8 | 3 068 | 85,0 % | python-docx | agent, combinaisons, connaissances, projet |
| `cli.py` | 1 | 2 817 | 81,5 % (32,0 % au lot 40) | typer | tous |
| `agent` | 6 | 2 709 | 97,1 % | pydantic, yaml | catalogue, retrieval |
| `ingestion` | 9 | 2 347 | 95,2 % | docutils | — |
| `mcp` | 9 | 2 332 | 86,8 % | mcp 2.x | 8 modules |
| `execution` | 11 | 2 098 | 94,8 % | pydantic, yaml | chemins, **connaissances** |
| `rebar` | 7 | 1 527 | 96,0 % | numpy | — |
| `retrieval` | 8 | 1 520 | 98,6 % | bm25s | indexing, mcp |
| `parsing` | 6 | 1 461 | 93,4 % | — | ingestion |
| `ferraillage` | 3 | 1 412 | **52,3 %** | — | combinaisons, projet, rebar |
| `validation` | 7 | 1 395 | 83,8 % | — | catalogue, execution, parsing |
| `meshing` | 6 | 1 383 | 92,0 % | — | execution |
| `environnement` | 3 | 864 | 87,5 % | tomllib, yaml | execution |
| `constats` | 5 | 823 | 89,5 % | pydantic | agent, execution |
| `controles` | 4 | 803 | 93,1 % | — | projet |
| `indexing` | 5 | 763 | 97,8 % | bm25s, numpy | catalogue, parsing |
| `combinaisons` | 2 | 483 | 99,0 % | — | projet |
| `catalogue` | 5 | 460 | 87,9 % | — | execution |
| `report` | 3 | 236 | 93,0 % | — | execution, meshing, validation |
| `publication`, `etat`, `chemins` | 3 | 692 | 86,7 à 97,6 % | — | — |
| **Total `src/`** | | **36 627** (26 612 au lot 40) | | | |

- Fichiers les moins couverts, plus de 40 instructions :
  - `projets/estacade_pieux_01/comparaison_v2.py` : 18 % ;
  - `comparaison.py` : 20 % ;
  - `src/aster_expert/ferraillage/poutre.py` : 23 % ;
  - `projets/quai_cw_test_01/controles.py` : 29 % ;
  - `projets/estacade_pieux_01/lecture.py` : 31 % ;
  - `src/aster_expert/validation/checker_client.py` : 32 % (31,8 % au lot 40).

  La lecture des écarts du contre-calcul (C1 à C13), qui fonde le verdict de l'estacade, est
  donc presque sans test.
- Dépendance circulaire : `execution` importe `connaissances` (déclaration des connaissances
  appliquées), et `connaissances` importe `execution`.
- Code mort : `vulture` (60 %), après élimination des faux positifs (décorateurs pydantic et
  typer), trouve 3 fonctions de `src/` jamais appelées : `notes/controle.py:680`
  `sheet_points`, `notes/hypotheses.py:691` `hypotheses_sources`, `retrieval/config.py:107`
  `default_retrieval_config_path`. Par ailleurs, `config/retrieval.yaml` n'est lu que par
  les tests, jamais par la recherche. Le code mort est négligeable.
- Hors `src/` :
  - tests : 140 fichiers, 32 632 lignes ;
  - scripts : 104 fichiers, 22 998 lignes, dont 102 portent un numéro de lot ;
  - code propre aux projets, hors scripts et tests : 12 722 lignes pour le quai, 1 010 pour
    la dalle, 4 112 pour l'estacade.
- Qualité : `ruff format --check` (550 fichiers), `ruff check`, `mypy src` (133 fichiers) et
  `mypy` (392 fichiers) ne relèvent rien.

### 4.3 Base de connaissances

`aster-expert connaissances verifier` répond OK, avec 300 preuves confrontées au dépôt et
**55 exécutions archivées non vérifiables** (archives absentes dans le Cloud).

| Couche | Entrées | Observé | Établi | Promu |
|---|---|---|---|---|
| Constats Code_Aster (CA) | 58 | 34 | 24 | 0 |
| Diagnostics (DIAG, ENV) | 31 | 11 | 20 | 0 |
| Patrons (PAT) | 13 | 1 | 11 | 1 |
| Contrôles (CTL) | 14 | 1 | 10 | 3 |
| Références de validation (REF) | 15 | 0 | 14 | 1 |
| Précédents (PRE) | 38 | 38 | 0 | 0 |
| **Total** | **169** | 85 | 79 | **5** |

Remarques sur la promotion :

- Les 5 promotions datent toutes du lot 44 et passent toutes par la dalle (CTL-005, CTL-006,
  CTL-012, PAT-011, REF-014, `connaissances/promotions.yaml`).
- Trois d'entre elles reposent sur le seul niveau E de la dalle (un seul projet).
- Les deux promotions « deux projets » (CTL-005, CTL-006) comptent, côté quai, un **test
  unitaire** et non un calcul d'ouvrage.
- Aucune entrée de l'estacade n'est promue.

Origine des entrées :

- quai : 125 ;
- dalle : 22 ;
- estacade : 22 ;
- précédents : 38, tous au statut « observé », par construction.

**Échantillon de 20 entrées tirées au hasard** (`random.Random(48).sample` sur les 169
fichiers triés). Chaque preuve a été relue ; ce qui pouvait être rejoué dans le Cloud l'a été.

| Entrée | Niveau, statut | Vérification de l'audit | Verdict |
|---|---|---|---|
| CA-008 | B | catalogue : `LIAISON_SOLIDE.GROUP_NO` sans `max_values` (liste admise) ; `sdlx03b.comm` l. 62-72 : `GROUP_NO=("N241", "N44")` | **tient**. Deux des sources citées (R3.03.03, R3.03.06) traitent de `LIAISON_ELEM`, pas du fait affirmé |
| CA-028 | B | U4.23.04, `Op_randes.rst` l. 179-199 : « grno doit être une GROUP_NO ne contenant qu'un seul nœud », normale à angle aigu avec `VECT_NORM` | **tient** |
| CA-034 | D | `constats rejouer` : `f2_avant`, `f2_apres` rejoués, 1/1 et 1/1 valeurs retrouvées | **tient** (rejoué) |
| CA-040 | C | `d19.comm` 2/2, `limites.comm` 2/2 | **tient** (rejoué) |
| CA-043 | C | `limites.comm` 5/5 | **tient** (rejoué) |
| CA-050 | B | `ssls127a.comm` l. 128-135 (lu par `read_test_case`) : `DZ` sur les bords, `DY`/`DRX` et `DX`/`DRY` en symétrie | **tient** (le sens des noms `LSYMX`/`LSYMY` est une déduction) |
| CA-056 | D | `sonde_lot47.comm` 1/1 | **tient** (rejoué) |
| CA-057 | D | `sonde_lot47.comm` 1/1 | **tient** (rejoué) ; source catalogue sans empreinte (`catalogue_hash: null`) |
| CTL-010 | B, établi | tests cités présents (`test_generation_comm.py:86`, `:100`), réussis dans la suite ; `dalle_appuyee_01/generation.py:103` `_title` présent | **tient** ; c'est un contrôle propre au projet (`scope: projet`), réécrit dans la dalle |
| DIAG-020 | A, observé | exécution `20260923T130739-57ea01cb` absente ; `docs/essais_lot29.md:81` cite bien `MODELISA8_14` | **non vérifiable dans le Cloud**, cohérent avec le compte rendu |
| DIAG-023 | A, observé | exécution absente ; la signature `FileNotFoundError … lot27_maillage.mmed` figure au registre du quai | **non vérifiable dans le Cloud**, cohérent |
| PRE-006 | A, observé | texte identique à l'entrée du point 5 de la fiche du quai ; `decided_at` identique | **tient** (heure conventionnelle 18:00) |
| PRE-010 | A, observé | texte identique (point 8) ; arithmétique relue : 1 000 cos 30° × 0,70 = 606 kN·m ; 800 / 1,115 = 717 kN/m² | **tient** |
| PRE-012 | A, observé | texte identique (point 9) | **tient** |
| PRE-037 | A, observé | texte identique dans la fiche et dans `arbitrage_estacade_pieux_01_lot47.md` | **tient** ; le texte de MM garde le libellé « (Recommandé) » de l'option proposée par la session |
| PRE-039 | A, observé | texte identique dans la fiche et dans `…_lot47quater.md` | **tient** |
| REF-005 | D, établi | `d5a.comm` 1/1, `d5b.comm` 2/2 | **tient** (rejoué) |
| REF-011 | C, établi | `plaque.comm` 2/2 | **tient** (rejoué) |
| REF-014 | E, **promu** | `rejouer-references` : `dalle_h0p125` 6/6 ; **`dalle_h0p500` et `dalle_h0p250` non rejouables** (« exécution du projet dalle_appuyee_01 sans déclaration des connaissances appliquées », règle du lot 46) ; code de sortie 0 | **partiel** : la seule référence E promue ne peut plus démontrer sa convergence (critère E1, trois maillages) |
| REF-015 | C, établi | calcul complet rejoué dans le Cloud (§ 4.4 bis) : `DIAGNOSTIC JOB : OK` en 2 268 s ; **0/30 valeurs retrouvées** (grandeurs dérivées, non imprimées) ; code 1 | **calcul reproduit, référence non rejouable par l'outil** |

Résultat :

- 15 entrées tiennent, dont 7 rejouées par calcul ;
- 1 est partielle (REF-014) ;
- 2 ne sont pas vérifiables dans le Cloud ;
- 1 a un calcul reproduit mais des valeurs que l'outil ne sait pas rejouer (REF-015).

Aucune preuve fausse n'a été trouvée. Deux faiblesses de forme ont été relevées : des
sources hors sujet (CA-008) et une source catalogue sans empreinte (CA-057).

### 4.4 Projets : niveau atteint et preuve

| Projet | Niveau du paquet | Preuve (`resultats/paquet/paquet.json`) | Ce que l'audit a vérifié | Réserves |
|---|---|---|---|---|
| `quai_cw_test_01` | **D** | B 265/265 ; C `completed_ok` ; D réussi à 1e-6 ; E : aucune référence | `paquet.json` relu ; `note controler` OK | Les trois critères D (lots 34, 37, 39) ont été commités **avec des résultats** (`anteriorite_demontrable: false`). Paquet exporté le 2026-10-02 sur un arbre modifié (`arbre_modifie: true`). **`projet quai_cw_test_01 verifier` échoue aujourd'hui** : entrée du point 14 (Es) en révision depuis le lot 45. Le quai ne peut plus être régénéré, alors que Es ne sert qu'au ferraillage. Pas de clé `harness` (harnais du lot 46 non appliqué) |
| `dalle_appuyee_01` | **E** | E0, E1, E2 réussis (`references/rejeu_niveau_e_lot45.json`) ; critères commités avant l'exécution (`4093f12`, antériorité démontrable) | `projet verifier` OK ; `mesh check` du maillage h0p125 : 48/48 invariants | Rejeu de REF-014 partiel (§ 4.3). F4 « échec (limite active) » dans les verdicts ELS. Paquet sur arbre modifié |
| `estacade_pieux_01` | **D** (contre-calcul, jamais E) | B 420/420 ; C ; D réussi par le harnais v2 | `projet verifier` OK ; `mesh check` h0p050 : **367/367** invariants ; `.comm` régénéré dans le Cloud depuis le maillage versionné : **identique hors commentaires** ; calcul complet rejoué dans le Cloud : `OK` en 2 268 s, mais 0/30 valeurs de REF-015 retrouvables (§ 4.4 bis) | Le critère D v2 (`docs/essais_lot47bis.md`) a été commité **après** l'exécution (`posterieur_a_l_execution: true`). 2 lignes de comparaison inexpliquées (C3 ELS c, C5). Lecture C1 à C13 couverte à 18-20 % par les tests |

**Rejeu du calcul complet de l'estacade dans le Cloud (REF-015), § 4.4 bis.**

Commande : `connaissances rejouer-references --reference REF-015`. Le `.comm` versionné est
exécuté avec ses ressources par défaut : `ncpus 1`, `mpi_nbcpu 1`, `docker --cpus=1`,
`--memory=13040m`.

- **Calcul : `DIAGNOSTIC JOB : OK`, `completed_ok`, aucune alarme, aucune erreur.** Le niveau
  C de l'estacade est donc reproduit dans le Cloud. Durée : 2 268 s de temps mur (dont
  `TOTAL_JOB` 2 264 s), contre 1 753 s pour l'exécution de production dans la VM (REF-015,
  source). Pic mémoire : 4 267 Mo (VmPeak). Pendant tout le calcul, un seul des 4
  processeurs est occupé (`docker stats` : ≈ 100 % d'un cœur, 1,6 à 2,0 Go).
- **Valeurs de la référence : 0/30 retrouvées, verdict « échec : à réexaminer », code 1.**
  Les 30 grandeurs de REF-015 (C1 à C13) sont des valeurs **dérivées** : enveloppes sur les
  positions mobiles, combinaisons calculées en Python, moyennes de section. Elles ne sont pas
  imprimées dans le listing, alors que le mécanisme de rejeu cherche chaque valeur dans le
  listing. Ce n'est donc pas un écart de résultat. C'est une référence que l'outil
  **ne sait pas rejouer** : son statut « établi » (« preuve rejouable ») n'est pas justifié
  par le rejeu de la base.
- L'audit n'a pas recalculé lui-même les grandeurs dérivées : la chaîne
  `projet … controles` et la lecture C1 à C13 demandent l'état d'exécution du projet. Les
  sommes d'équilibre du paquet (`controles/equilibre.json`) sont, elles aussi, calculées par
  l'outil et ne figurent pas telles quelles dans le listing.
- Fin du listing : `annexes_lot48/journaux/rejeu_ref015_fin_listing.txt`. Rapport :
  `journaux/rejeu_ref015.md`.

### 4.5 Métriques : exécutions, échecs, interventions

Sources : `connaissances/rex/*.yaml`, `connaissances/metriques/*.yaml`. Ces chiffres ne sont
pas recalculables dans le Cloud : `rex` y refuse l'archive partielle, comme prévu. Le
volume de code vient de `git diff --numstat` (lignes Python ajoutées).

| Projet | Lot | Exécutions (cumul, registre) | Échecs (cumul) | Interventions de MM déclarées | Python ajouté, projet / tronc commun |
|---|---|---|---|---|---|
| quai | 1 à 40 | 190 (base, audit du lot 40) | 73 | ≈ 25 (estimation, non mesurée) | — |
| quai | 42 | — | — | 0 | 2 586 / 3 651 |
| dalle | 43 | 5 | 0 | 2 | 3 916 / 653 |
| dalle et quai | 44 | 6 | 0 | 0 | 1 056 / 1 521 |
| dalle | 45 | 6 (+ 3 dans le Cloud, hors archive) | 0 | 1 | 642 / 4 326 |
| estacade | 47 | 17 | 4 | 1 | 5 249 / 268 |
| estacade | 47 bis | 20 | 4 | 0 | 1 888 / 81 |
| estacade | 47 ter | 27 | 7 | 1 | 825 / 218 |
| estacade | 47 quater | 44 | 10 (dont 3 en vérification) | 0 | 1 201 / 684 |

Taux d'échec en développement (registres) : quai 41,2 % (73/177), dalle 0 % (0/5),
estacade 25,0 % (7/28). Temps de calcul : estacade 35 399 s (9,8 h, temps mur), dalle 66 s,
quai 5 545 s de temps Aster avant le lot 41 et 1 315 s de temps mur après.

**La courbe d'apprentissage est-elle réelle ?** En partie, et moins que ne le disent les
comptes rendus.

- **Ce qui baisse vraiment.**
  - Le taux d'échec en développement : 41 % pour le quai, 25 % pour l'estacade.
  - La durée calendaire : le quai a pris une vingtaine de lots pour atteindre le niveau D ;
    l'estacade, 4 lots en trois jours.
  - La part des échecs reconnus automatiquement **hors de l'échantillon qui a servi à
    construire la base** : 5 sur 10 pour l'estacade.
  - Le chiffre de 69/69 pour le quai est **circulaire** : les diagnostics ont été écrits au
    lot 42 à partir de ces mêmes 69 échecs.
- **Ce qui ne baisse pas.**
  - Le code propre à l'ouvrage. Dalle : 3 916 lignes au premier lot, 4 673 en tout (code et
    scripts). Estacade : 5 249 lignes au premier lot, 8 483 en tout. Le rapport « code du
    projet / tronc commun ajouté » passe de 6 pour la dalle (lot 43) à 20 pour l'estacade
    (lot 47).
  - La part de tronc commun réellement importée par chaque projet diminue. Lignes
    `import aster_expert…` : 132 pour le quai, 86 pour la dalle, **43 pour l'estacade**.
    L'estacade a écrit ses combinaisons, sa lecture et sa comparaison à part.
- **À difficulté comparable ?** Non. La dalle est un cas d'école à solution analytique.
  L'estacade est un contre-calcul d'un modèle réel, dont trois des quatre lots ont été
  consacrés à attribuer des écarts. Les trois ouvrages ne permettent pas de conclure à une
  baisse du coût à difficulté égale.
- **Les interventions déclarées sont sous-estimées par construction.** Les décisions et les
  diagnostics que MM écrit dans la consigne ne comptent pas (« validées par le lancement du
  lot ») :
  - E1 à E12 au lot 47 ;
  - E17 à E19, et le diagnostic (b), au lot 47 bis ;
  - l'hypothèse « DST et chevêtre 0,80 » au lot 47 ter ;
  - H1, H2 et E20 au lot 47 quater.

  Le compte rendu du lot 47 quater compte lui-même « 3 apports de fond du superviseur » à
  côté de « 2 interventions » (`docs/essais_lot47quater.md`, § 6.4). Les « erreurs évitées
  par la base » (11 pour la dalle, 13 pour l'estacade) sont **déclarées par les sessions
  elles-mêmes** et ne sont pas vérifiables.

---

## 5. Étape 3 — évaluation par capacité

| Capacité | État | Niveau démontré | Preuve (audit) | Limites |
|---|---|---|---|---|
| Recherche documentaire | **opérationnelle, sans progrès depuis le lot 40** | A | banc relancé (`banc_recherche_lot48.json`), profil réaliste. **`by_file` : hit@10 82,9 % (68/82)** ; par profil : `syntaxe` 91,7 % (44/48), **`methode` 73,9 % (17/23)**, **`theorie` 63,6 % (7/11)** ; plancher (`syntaxe` pour toutes) 73,2 %. `by_subsection` : 76,8 % ; `syntaxe` 89,6 %, `methode` 65,2 %, `theorie` 45,5 %. Sur les 63 questions du lot 40 : **52/63 = 82,5 %, identique** | Moteur BM25 inchangé ; la hausse apparente de `methode` (55,6 % → 73,9 %) vient des questions ajoutées, pas du moteur. 5 questions exclues (documents attendus non résolus), `eval-065` sans profil. Parmi les 14 échecs à 10 (`by_file`) : `eval-006` (réaction latérale non linéaire d'un pieu) et `eval-072` (domaine de validité de Mohr-Coulomb) ; `eval-066` (choix d'une loi de sol) échoue en `by_subsection` |
| Validation de niveau B | **opérationnelle, limite non signalée par le verdict** | B | `validate_comm` sur l'estacade : 420/420. Sonde de l'audit (`sonde_validation_b/`) : `CHAR_MECA_GLOBAL=(CL,)` donne **`valid: true`, code de sortie 0**, couverture 6/8, avec `MACRO_ELAS_MULT` et le `CALC_CHAMP` suivant **non confrontés**, si bien que le mot-clé inexistant `MOT_INEXISTANT=1` passe. La même sonde avec `CHAR_MECA_GLOBAL=CL` : 1 erreur, code 1 | Un tuple de concepts empêche de résoudre le concept et toute sa suite (« concept 'R' has no resolved placeholder »). Le paquet exige 100 % de couverture, mais l'appel direct ne le fait pas. Rien sur la cohérence des groupes avec le maillage |
| Exécution, `.mess`, diagnostics automatiques | **opérationnelle** | C | `pytest -m lent_aster` : 3 réussis (20,7 s) ; 7 cas rejoués par l'audit, tous `OK` ; compte rendu JSON et `run_aster.error_messages` encapsulés | Proposition automatique de diagnostic : 5/10 sur l'estacade, seul échantillon hors construction. Statut MPI propre à l'outil (ENV-004) |
| Fiche : `choix_agent` | **opérationnelle, employée une fois** | — | estacade : 6 entrées `choix_agent` (U1 à U6) sur 40 ; dalle et quai : 0 (antérieurs au lot 44) | La règle de partage repose sur la discipline de la session |
| Fiche : paramètres obligatoires | **partielle : jamais employée sur un ouvrage** | — | `aster-expert fiche obligatoires` sur les fiches de la dalle et de l'estacade : « Commandes prévues : 0 ». Aucune fiche n'a de `planned_commands` | L'estacade, postérieure au lot 44, ne l'a pas utilisée ; rien ne l'impose |
| Maillage Salomé | **VM seulement** | invariants (structure) | 3 scripts Salomé (`projets/*/maillage/*_mesh.py`) ; `mesh check` dans le Cloud sur les maillages versionnés : 367/367 et 48/48 | **Aucun maillage possible dans le Cloud** (Salomé absent, image locale sur aucun registre). `mesh check` refuse l'extension `.mmed` des maillages versionnés : il faut en faire une copie en `.med`. Aucun maillage volumique jamais produit |
| Générateur de `.comm` | **propre à chaque projet** | B, C | `projet.yaml`, `comm.generator: <projet>.extensions:generate` ; générateurs de 858 lignes (estacade), 3 756 (quai) | Le tronc commun fournit la vérification (exigences, refus, nommage `_gn`), pas la production des blocs. Seuls les blocs de ferraillage (`ferraillage/poutre.py`, `plaque.py`) sont génériques |
| Harnais D par défaut | **opérationnel sur l'estacade seule** | D | `controles/harnais` (CTL-005, CTL-006, CTL-012, CTL-013) ; clé `harness` présente dans le paquet de l'estacade, absente de ceux du quai et de la dalle | Écart relatif indéfini sur charge nulle corrigé (v2), mais sur un critère écrit après l'exécution |
| Niveau E | **partielle** | E (dalle) | paquet de la dalle ; REF-014 | Une seule référence E, plus rejouable en entier (§ 4.3) |
| Comparaison à un calcul externe | **opérationnelle, propre à l'estacade** | C/D, jamais E | REF-015 (`reference_kind = calcul_externe_non_valide`) ; `comparaison.py` et `comparaison_v2.py` | Lecture C1 à C13 propre au projet, en deux versions, couverte à 18-20 % ; aucun module générique de comparaison |
| Combinaisons | **opérationnelle (EN 1990), contournée par l'estacade** | arithmétique | `src/aster_expert/combinaisons` (99 % couvert) ; quai et dalle | L'estacade recopie les combinaisons du modèle source en Python (`combinaisons.py`) |
| Ferraillage 1D | **partielle** | D (calibré `ssll13*`) | `rebar` 96 % ; `ferraillage/poutre.py` **23 %** | 7.2N non vérifié par MM ; écart ELS ouvert (ANO-001) |
| Ferraillage 2D | **opérationnelle sur la dalle** | D | `ferraillage/plaque.py` | Densités ELS dépendant de `SIGC_*_ELS` (CA-052, ANO-001) |
| Notes Word | **opérationnelle** | — (contrôle de transcription) | `note controler` OK sur les trois projets (estacade : 33 points, 573 valeurs retrouvées dans le paquet) | Le contrôle vérifie la note contre ses sources, pas la justesse des sources. L'estacade n'a pas de `controle_notes.json` versionné |
| Base de connaissances : consultation | **opérationnelle** | A | `search_connaissances`, `search_constats` appelés | Classement : 3 résultats à score 0 dans un ordre sans rapport avec la pertinence (§ 2). Panne de tout un lot au 47 bis (ENV-002, corrigée) |
| Base : épreuve, promotion | **partielle** | — | 5 promotions, toutes au lot 44 ; aucune depuis | Aucune entrée de l'estacade promue ; règle de déclaration du lot 46 qui casse un rejeu de référence |
| Base : `rex` | **opérationnelle dans la VM, déclarative dans le Cloud** | — | `rex` sur les 3 projets : « archive partielle », métriques non recalculées, code 0 | Les consultations sont comptées sur un journal local ; les interventions et les erreurs évitées sont déclarées |
| Sécurité : politique de lecture MCP | **opérationnelle** | — | refus lisible d'un `.comm` hors des racines (sonde de l'audit), avec la racine manquante et la marche à suivre | Écriture non couverte (`docs/etat.yaml`) |
| Sécurité : termes interdits | **inopérante hors de la VM** | — | `config/termes_interdits.local.txt` absent dans le Cloud ; `publication.py:58` prend alors une liste vide ; `python -m aster_expert.publication --arbre` : code 0 ; `test_confidentialite.py` : 2 tests ignorés | Une session Cloud, ou l'intégration continue, ne peut pas détecter un terme confidentiel de l'estacade |
| Sécurité : contrôle de publication | **opérationnelle** | — | crochet `pre-commit` actif (`core.hooksPath = scripts/git-hooks`) ; `--arbre` OK | — |
| Intégration continue | **opérationnelle, souvent rouge au premier envoi** | — | GitHub Actions : `ci`, 16 passages, dont **5 en échec et 1 annulé** (passages 1, 4, 8, 9, 15) ; `ci-lent`, 3 passages, dont 2 en échec, dernier vert le 2026-10-05 | Déclencheurs `lot-*` et `claude/lot-*` seulement : ni `main` ni une branche Cloud `claude/<autre>` (comme celle de cet audit) ne sont contrôlées à l'envoi. `ci-lent` n'a pas été relancé après les changements de l'exécuteur (lots 47 ter et 47 quater) |
| Performances (après le lot 47 quater) | **opérationnelle, un seul cœur** | — | défauts `ncpus 1`, `mpi_nbcpu 1` (`env-check`) ; rejeu de l'estacade dans le Cloud : 1 cœur sur 4 occupé (100 % d'un processeur, 1,6 Go), estacade en 2 268 s dans le Cloud contre 1 753 s dans la VM (§ 4.4 bis) | Gain du parallélisme non démontré (lot 47 quater, § 5.1). Réactions fausses sous `PARALLELISME_TEMPS` (DIAG-027) |
| Non-linéaire | **absente** | — | aucun `STAT_NON_LINE` dans `projets/` ni dans un générateur ; 0 exécution | — |
| Contact | **absente** | — | aucun `DEFI_CONTACT` dans `src/`, `projets/`, `connaissances/` | — |
| Thermique transitoire | **absente** | — | aucun `THER_*` ; seule une température de coque imposée en statique (estacade, CA-054) | — |
| Dynamique | **absente** | — | aucun `DYNA_*`, `CALC_MODES` | — |
| Phasage | **absente** | — | — | — |
| Géotechnique (lois de sol, sol maillé) | **absente** | — | `MOHR_COULOMB`, `HUJEUX`, `DRUCK_PRAGER` n'apparaissent que dans un constat de catalogue (niveau B) ; les sols sont des ressorts linéaires (quai, estacade) | — |
| Volumique 3D | **absente** | — | aucun `MODELISATION="3D"`, `HEXA`, `TETRA` dans `src/`, `projets/`, `connaissances/` | — |

---

## 6. Étape 4 — généricité

### 6.1 Ce qui reste propre à un ouvrage dans `src/`

Recherche de l'audit sur tous les `.py` de `src/` :

- noms d'ouvrage (`dalle`, `estacade`, `pieu`, `chevêtre`, `tablier`, `palplanche`,
  `tirant`, `bollard`, `LM1`, `LM2`, `UDL`, `radoub`) ;
- identifiants du quai (liste de `test_tronc_commun_sans_ouvrage.py`) ;
- noms de groupes et de cas codés en dur.

Résultat :

- **aucune occurrence propre à un ouvrage**. Les 10 lignes trouvées sont des faux positifs
  (« dépôts », « loudly »).
- `src/aster_expert/ferraillage/poutre.py:270-320` code en dur un groupe `POUTRE` et
  `POU_D_E`. Ce sont les lignes du modèle synthétique de ferraillage 1D (schéma `ssll13*`),
  que le module construit lui-même : ce n'est pas une donnée d'ouvrage.
- Hypothèse supposée dans le tronc commun : `controles` et `combinaisons` attendent des
  tables imprimées sous des noms déclarés dans `projet.yaml`. C'est générique, mais limité
  aux calculs linéaires à cas élémentaires (pas d'instants, pas de pas de charge).

Le test de frontière (`test_tronc_commun_sans_ouvrage.py`) ne contient que les identifiants
du quai : une fuite de la dalle ou de l'estacade dans `src/` ne serait pas détectée.

### 6.2 Code propre à chaque projet comparé au tronc commun utilisé

| Projet | Code du projet (hors scripts, tests) | Scripts de lot | Tests | Imports du tronc commun (lignes) | Étapes servies par le tronc commun |
|---|---|---|---|---|---|
| Quai | 12 722 | 8 853 (46 fichiers) | 7 177 | 132 | fiche, maillage (vérif.), validation, exécution, contrôles, combinaisons, ferraillage 1D, notes |
| Dalle | 1 010 | 3 663 (12) | 676 | 86 | idem, ferraillage 2D |
| Estacade | 4 112 | 4 371 (18) | 604 | 43 | fiche, maillage (vérif.), validation, exécution, contrôles, notes ; **pas** combinaisons, ferraillage, comparaison |

Le rapport ne baisse pas d'un projet à l'autre :

- dalle : 4 673 lignes de code et de scripts propres au projet ;
- estacade : 8 483 lignes.

La dalle est l'ouvrage le plus simple ; l'estacade a demandé du code que le tronc commun ne
porte pas (charges mobiles, lecture et comparaison à une source).

Ce qui ne s'est **pas** produit : la remontée de ce code générique dans le tronc commun.
`rex` signale lui-même deux fonctions candidates à devenir des patrons dans l'estacade
(`generation.py:fractional_loads_block`, `moving_loads_block`, proches de PAT-005) et deux
dans le quai. Aucune n'a été versée.

### 6.3 Essai de pensée : poutre de couronnement en modèle volumique 3D (sous-modèle)

Hypothèse : on reprend la poutre du quai (2,50 × 1,40 m), modélisée en volumique, avec les
déplacements ou les efforts aux limites issus du modèle global (POU_D_T).

Les estimations sont en lots de la taille des lots 47 et suivants. Ce sont des **déductions**
de l'audit, à prendre comme des ordres de grandeur.

| Étape | Réutilisation | Ce qu'il faut faire | Estimation |
|---|---|---|---|
| Fiche d'hypothèses, arbitrage | **se paramètre** | Nouveaux points : raccord au modèle global, type d'élément (HEXA20, TETRA10), loi du béton, lecture des contraintes. `choix_agent` couvre déjà le type et la taille des mailles | < 0,5 lot |
| Données (`model_data`) | **telle quelle** | — | — |
| Maillage Salomé | **se réécrit** | Script volumique (partition, groupes de faces d'appui et de coupure), comptages analytiques des HEXA ou TETRA. `mesh check` accepte tout type MED, mais aucun invariant n'a été éprouvé sur des mailles volumiques. **Dans la VM seulement** | 1 lot |
| Raccord global / sous-modèle | **absent** | Aucune connaissance ni aucun essai. `LIAISON_ELEM` en option `3D_POU` (R3.03.03) est recommandé depuis le lot 28 et n'a jamais été exécuté. Transfert de champ par `PROJ_CHAMP` : aucune entrée | 1 lot, avec une sonde de niveau E |
| Générateur `.comm` | **se réécrit** (projet) | Modèle `3D`, matériau, conditions de coupure, cas ; refus et nommage réutilisés | 0,5 à 1 lot |
| Validation B, exécution | **telles quelles** | Mémoire : volumique plus gros que l'estacade (4,3 Go au pic) ; un seul cœur par défaut | — |
| Contrôles D | **se paramètrent** | Équilibre (CTL-005) sur les réactions des faces de coupure : réutilisable si les tables sont déclarées. La symétrie sert peu. Il faut ajouter la continuité avec le modèle global | 0,5 lot |
| Post-traitement | **se réécrit** | Contraintes `SIGM_NOEU` et `SIEF_ELGA`, intégration des contraintes sur des coupes pour retrouver N, M, V (aucun module : les efforts de section du quai, `section_statics`, sont propres aux coques) | 1 lot |
| Ferraillage | **absent** | `CALC_FERRAILLAGE` ne traite que 1D et 2D. Passer des contraintes 3D aux aciers (efforts de section, puis module `rebar` ; ou bielles et tirants) est une décision de MM et une méthode à valider | 1 à 2 lots |
| Notes Word | **se paramètrent** | Tableaux et figures déclarés dans `projet.yaml` | < 0,5 lot |
| Base de connaissances | **à construire** | 0 constat volumique | inclus ci-dessus |

Ordre de grandeur : **5 à 7 lots**. C'est davantage que l'estacade, parce que trois maillons
(raccord, post-traitement volumique, ferraillage depuis le 3D) n'existent pas du tout.

---

## 7. Étape 5 — le processus

### 7.1 Erreurs depuis le lot 41

Le bilan du lot 47 ter (`docs/essais_lot47ter.md`, § 6.7, 16 lignes) couvre les lots 47 à
47 ter. Ses lignes 2, 8, 11, 13 et 14 ont été confrontées aux registres
(`connaissances/rex/estacade_pieux_01.yaml` : DIAG-010, ENV-002, ENV-003, DIAG-025) et au
journal d'autonomie du lot 47 (lignes 2, 11, 16). Elles concordent. Le tableau ci-dessous
**complète** ce bilan pour les lots 41 à 46 et 47 quater, et relève ce qui y manquait. Les
erreurs déjà décrites au lot 47 ter n'y sont pas répétées. Pour les lots 41 et 42, les sources
versionnées ne montrent pas d'erreur au sens de ce tableau, hormis deux écarts formels du
critère de rejeu de la chaîne au lot 41 (chemins non énumérés), rapportés par la session
elle-même.

| N° | Lot | Auteur | Catégorie | Erreur | Preuve | Ce qui l'empêche désormais |
|---|---|---|---|---|---|---|
| A1 | 43 | MM (arbitrage) | référence | L'arbitrage cite « PRE-021 (D21) », absent de la base et d'aucune fiche | `lot43_journal_autonomie.md`, ligne 19 | PRE-021 laissé libre ; D21 enregistrée au lot 45 ; rien n'empêche une nouvelle citation inexistante dans un arbitrage |
| A2 | 43 | données sources (MM) | données manquantes | Nuance d'acier, catégorie d'usage, E et ν, poids volumique, ouverture de fissure absents de la description | même journal, ligne 7 | `fiche obligatoires` le détecterait **si** la fiche déclarait ses commandes ; aucune ne le fait |
| A3 | 43 | outil | outil | `get_command_schema` renvoyait tout le schéma (721 000 caractères) ; origine `arbitrage_mm` absente ; attribution des constats par nom de projet fausse | même journal, lignes 2, 18 et 31 | corrigé au lot 44 (filtre par mot-clé) et au lot 43 |
| A4 | 44 | session | compte rendu | Explication non vérifiée et fausse de l'écart 41,2 % / 38,4 % | commit `aca7e68` | correction publiée ; aucune règle |
| A5 | 45 | session | transcription | Décision Es enregistrée sans reprendre le texte de MM | commit `fbcfb98` (« Es au texte de MM ») | `note controler` vérifie les textes de décision mot pour mot (`textes_de_decision_verifies`) |
| A6 | 45 | session | contournement | Contournement manuel inscrit dans `CLAUDE.md` | commit `fbcfb98` (« contournement manuel du lot 45 retiré ») | aucune règle écrite |
| A7 | 46 | session | intégration continue | Premier passage de `ci` en échec (test supposant un catalogue extrait) | `bb0d926` ; passage 1 | aucune règle ; même catégorie que A9, A10, A12 |
| A8 | 46 | session | intégration continue | Workflow `ci-lent` cassé (`cave` absent, image sans référence), découvert par le premier passage lancé par MM | `51baf31` ; passages 1 et 2 de `ci-lent` | profil `ci` dans `env-check` ; tests du workflow |
| A9 | 47 | session | intégration continue | Test d'`env-check` dépendant de `GITHUB_ACTIONS` | `b97f6a3` ; passage 8 | correctif ponctuel |
| A10 | 47 | session | intégration continue | Ligne de 89 caractères poussée sans `ruff check` | `1afb621` ; passage 9 | aucune ; la règle « Validation obligatoire » de `CLAUDE.md` existait déjà |
| A11 | 47 quater | superviseur (consigne) | consigne | La consigne situe le bouchon « de la tête à −0,80 (E14) » alors que E14 dit « de +0.70 à −0.80 » | `docs/lots/lot47quater_consigne.md:83-84` contre `projets/estacade_pieux_01/donnees/sources/arbitrage_estacade_pieux_01_lot47.md:45` | Signalé par la session (`connaissances/rex/estacade_pieux_01.yaml`, lot 47 quater). L'audit n'établit pas si la tête est à +0,70 ; l'écart de texte est réel |
| A12 | 47 quater | session | intégration continue | Seuil disque de 10 Go appliqué au runner (4,1 Go libres) | `3dc21f1` ; passage 15 | seuil par profil, test |
| A13 | 47 quater | session | exécution | Série de mesures lancée sans délai court : blocage d'un essai hybride, arrêté à la main | DIAG-026, registre | DIAG-026 |
| A14 | 47 quater | Code_Aster et outil | lecture | Réactions fausses sous `PARALLELISME_TEMPS` | DIAG-027 | contrôle d'équilibre CTL-005 |
| A15 | 46 | session | régression | La règle « déclaration des connaissances appliquées » rend 2 cas sur 3 de REF-014 non rejouables, et `rejouer-references` répond quand même par le code 0 | rejeu de l'audit (`journaux/rejeu_refs.txt`) | **aucune** : non détectée jusqu'à cet audit |
| A16 | 47 | session | validation | Lacune connue du validateur B (tuple de concepts) consignée, mais verdict `valid=true` laissé tel quel | `docs/essais_lot47.md:92` ; sonde de l'audit | **aucune** : notée dans CA-055, jamais corrigée |

Ce qui manquait au bilan du lot 47 ter :

- **Six erreurs d'intégration continue en quatre lots** (A7 à A10, A12, et le passage 4 du
  lot 46). Le critère « une session ne déclare pas un lot terminé tant que l'intégration
  continue n'est pas verte » de `CLAUDE.md` est respecté *a posteriori*, par un commit
  correctif. La vérification locale avant l'envoi ne l'est pas.
- **Deux défauts silencieux de l'outil** (A15, A16), que personne n'a vus.

Répartition sur les 16 lignes du lot 47 ter et les 16 de ce tableau :

| Auteur | Lot 47 ter (lots 47 à 47 ter) | Audit (lots 43 à 47 quater, complément) |
|---|---|---|
| session | 9 | 11 |
| superviseur | 2 | 1 |
| agent et superviseur | 2 | — |
| outil | 3 | 1 |
| MM ou données sources | 0 | 2 |
| Code_Aster et outil | — | 1 |

Erreurs commises alors qu'une règle existait déjà : DIAG-010 (lot 47), lignes 15 et 16 du
lot 47 ter, A10. Les règles écrites dans `CLAUDE.md` (1 141 lignes) ou dans les skills ne
suffisent pas à les empêcher. Seuls les contrôles automatiques (tests, refus de la CLI) ont
effectivement empêché une erreur de se reproduire.

### 7.2 Interventions de MM

| Lot | Déclarées | Nature | Évitables par l'outil ? |
|---|---|---|---|
| 42 | 0 | validation du tri des questions | — |
| 43 | 2 | choix de modélisation (section B), 4 paramètres ELS de `CALC_FERRAILLAGE` | **oui pour les 4 paramètres** : la détection des obligatoires existe depuis le lot 44, mais n'est pas utilisée |
| 44 | 0 | D20, D21, Es dans la consigne | — |
| 45 | 1 | règle de conservation des niveaux | non (décision de méthode) ; la règle est désormais codée |
| 46, 46 bis | non déclarées | décisions 1 à 3 dans la consigne ; passage de `ci-lent` lancé et constaté par MM | `ci-lent` : oui, s'il était déclenché automatiquement |
| 47 | 1 | E13 à E16 (4 points pratiques) | non : décisions d'ingénieur |
| 47 bis | 0 (+ 1 relance) | diagnostic (b) et E17 à E19 dans la consigne | en partie : relecture chiffrée de la source |
| 47 ter | 1 | accord pour effacer des copies MED (disque plein) | **oui** : politique de rétention automatique (ENV-003, prévention écrite après coup) |
| 47 quater | 0 (+ 2 relances « Continue ») | H1, H2, E20 dans la consigne | en partie : skill `hypotheses-drafting` § 2 quater, ajouté après coup |

Interventions déclarées du lot 42 au lot 47 quater : **5**. Apports de fond inscrits dans les
consignes, non comptés : au moins **8 blocs** (lots 44, 45, 46, 47, 47 bis, 47 ter,
47 quater).

### 7.3 Ergonomie pour MM : de la description à la note

Chemin réellement suivi pour l'estacade (registres, scripts du projet, consignes) :

| # | Étape | Qui | Outil |
|---|---|---|---|
| 1 | Description, sources, décisions E1 à E12 | MM | consigne |
| 2 | Projet de fiche | session | skill + script `fiche_lot47.py` (pas de commande) |
| 3 | Arbitrage des points ouverts | MM | chat ; `AskUserQuestion` |
| 4 | Enregistrement des arbitrages | session | script `fiche_lot47.py` |
| 5 | Données chiffrées | session | YAML + `donnees.py` du projet |
| 6 | Discrétisation, script Salomé, invariants | session | code du projet (`discretisation.py`, `estacade_mesh.py`, `invariants_lot47.py`) |
| 7 | `projet … maillage` | CLI | VM seulement |
| 8 | Générateur | session | `generation.py` (858 lignes) |
| 9 | `generate`, `valider` | CLI | — |
| 10 | `executer` | CLI | 25 % d'échecs en développement |
| 11 | `controles` | CLI (harnais) | — |
| 12 | Combinaisons, lecture, comparaison | session | `combinaisons.py`, `lecture.py`, `comparaison*.py`, scripts de lot |
| 13 | `exporter-resultats` | CLI | — |
| 14 | `note hypotheses\|resultats\|controler` | CLI | — |
| 15 | `rex` | CLI | VM pour les métriques |

Bilan : 8 étapes sur 15 sont des commandes ; 6 exigent du code écrit par une session pour
l'ouvrage (lot 40 : 6 sur 13). La note existe désormais. **MM ne peut toujours pas conduire
seul la chaîne** : entre sa description et le premier `generate`, il faut environ
5 000 lignes de Python d'ouvrage.

### 7.4 Consignes du superviseur

| Lot | Consigne | Erreur ou manque | Preuve |
|---|---|---|---|
| 47 | données B4 de la consigne | essieu de trottoir de la combinaison 100 omis | bilan du lot 47 ter, ligne 7 ; E18 |
| 47 | critères v1 | lieu de lecture de C3 et C5 non précisé (avec la session) | bilan du lot 47 ter, ligne 3 |
| 47 bis | diagnostic (b) | total C8 annoncé à +2 %, retrouvé à +7,2 % | bilan du lot 47 ter, ligne 9 |
| 47 bis | E17.2 | comparaison du total barre + dalle au lieu de la barre (avec la session) | bilan du lot 47 ter, ligne 10 |
| 47 quater | H1 | étendue du bouchon transcrite autrement que E14 | A11 |

Aucune consigne n'a fait écrire une erreur dans le code ou dans la base qui y serait restée :
chaque erreur de consigne relevée a été détectée par la session ou par le lot suivant. En
revanche, les **diagnostics clés** (b, DST + 0,80, H1/H2) sont venus des consignes : sur
l'estacade, la relecture de la source et la formulation d'hypothèses restent le fait du
superviseur.

---

## 8. Recommandations (dix au plus)

Classées par valeur pour l'objectif, puis par effort : F = faible, M = moyen, É = élevé.

| # | Recommandation | Valeur | Effort | Preuve |
|---|---|---|---|---|
| **R1** | **Avant la forme de radoub (géotechnique non linéaire).** Faire un lot de « sondes non linéaires » sur des cas tests officiels, rejoués jusqu'au niveau E : loi de sol (Mohr-Coulomb, puis Hujeux si MM le retient), état initial géostatique, phasage (excavation, activation et désactivation), contact sol-structure. Il faut ajouter au tronc commun : (a) l'exécution incrémentale (suivi de convergence par pas, `.mess` de `STAT_NON_LINE`, diagnostics de non-convergence) ; (b) des contrôles D propres au non-linéaire (équilibre à chaque instant, résidu, cohérence de l'état initial) ; (c) des questions de banc de ces domaines, annotées par MM. Ne pas partir de l'ouvrage. | très haute | É (3 à 4 lots) | § 5 : 0 exécution, 0 entrée exécutée, échecs du banc sur `eval-066` et `eval-072` ; § 7.1 : 25 % d'échecs même en linéaire |
| **R2** | **Avant la poutre en 3D volumique.** Faire une référence volumique de niveau E (console ou poutre HEXA20 et TETRA10, contre la théorie des poutres, avec raffinement), une sonde de raccord sous-modèle (`LIAISON_ELEM` en option `3D_POU`, ou transfert de champ), un module générique d'efforts de section depuis les contraintes, et faire trancher par MM la méthode de ferraillage depuis le 3D | très haute | É (≈ 3 lots avant l'ouvrage) | § 6.3 : trois maillons absents ; § 5 : 0 maille volumique |
| **R3** | **Réparer les deux défauts silencieux.** (a) `validate` et `validate_comm` : `valid` faux, ou « partiel » avec un code non nul, dès qu'une commande n'est pas confrontée ; résoudre les tuples de concepts. (b) `rejouer-references` et `constats rejouer` : code non nul pour un cas « non rejouable » ; rendre REF-014 rejouable (déclarations de connaissances pour h0p500 et h0p250, ou exemption des cas de référence). (c) Une référence dont les grandeurs sont dérivées (REF-015) imprime ces grandeurs dans le listing, ou se rejoue par la lecture du projet ; sinon elle reste « observée » | haute | F-M | § 5 (sonde B), § 4.3 (REF-014), § 4.4 bis (REF-015), A15, A16 |
| **R4** | **Rendre les contrôles exécutables partout.** Fournir la liste des termes confidentiels au Cloud et à l'intégration continue par un secret, et refuser la publication d'un projet réel sans elle. Étendre `ci.yml` à toutes les branches `claude/**` et à `main`. Lancer `ci-lent`, avec le rejeu des références, à chaque lot qui touche `execution/`, `validation/` ou `connaissances/` | haute | F | § 5 (termes interdits, intégration continue) ; A7 à A10, A12 |
| **R5** | **Faire remonter le code d'ouvrage dans le tronc commun avant le quatrième ouvrage.** Charges mobiles (`fractional_loads_block`, `moving_loads_block`, signalés par `rex`), lecture et comparaison à une source externe (`comparaison*.py`, en un seul module testé), combinaisons « recopiées d'une source ». Étendre le test de frontière aux noms de la dalle et de l'estacade | haute | M | § 6.2 : 8 483 lignes propres à l'estacade, 43 imports du tronc commun ; § 4.2 : couverture de 18 à 20 % |
| **R6** | **Imposer la déclaration des commandes prévues dans la fiche** (`planned_commands`) au `projet verifier`, pour que `fiche obligatoires` serve. Faire de même pour l'enregistrement des arbitrages, aujourd'hui dans des scripts de lot : une commande générique `fiche enregistrer <arbitrage.md>` | moyenne | F-M | § 5 (0 commande prévue) ; § 7.2 (lot 43, 4 paramètres ELS) ; § 7.3 (étapes 2 et 4) |
| **R7** | **Mesurer honnêtement.** Compter les apports de la consigne (décisions, diagnostics, hypothèses) comme des interventions. Ne publier le taux de diagnostic automatique que hors de l'échantillon de construction. Retirer le compteur de consultations (journal local, non reproductible) ou le versionner par projet. Marquer « déclaré » les erreurs évitées | moyenne | F | § 4.5, § 4.1 |
| **R8** | **Restreindre les bloqueurs de génération à l'étape qu'ils concernent.** Le quai est bloqué en entier depuis le lot 45 par Es, qui ne sert qu'au ferraillage. Réexporter les paquets du quai et de la dalle avec le harnais D, sur un arbre propre | moyenne | F | § 4.4 |
| **R9** | **Ferraillage : clore R9 du lot 40 avant toute note qui porte des aciers.** Vérification du tableau 7.2N et ligne de comparaison par MM, cause de l'ANO-001 | moyenne | M | § 3 (R9 non faite) |
| **R10** | **Alléger.** (a) Sortir l'historique des lots 19 à 47 de `CLAUDE.md` (1 141 lignes), qui ne porte plus que les règles ; l'historique vit déjà dans `docs/etat.yaml` et les comptes rendus. (b) Archiver ou supprimer les 102 scripts de lot qui ne servent plus qu'à reproduire un lot passé, en gardant ceux qu'un test appelle. (c) Donner à `analyze_comm` et `validate_comm` un mode résumé (892 461 et ≈ 50 000 caractères sur l'estacade). (d) Supprimer `comparaison.py` après la fusion de R5. (e) Retirer le chemin mort (`config/retrieval.yaml` lu par les tests seulement, 3 fonctions jamais appelées) | moyenne | F | § 2, § 4.2, § 7.1 (règles écrites sans effet préventif) |

**Réponse aux trois questions posées.**

- *Avant un ouvrage en 3D volumique* : R2, avec R3 (un validateur et un rejeu qui ne mentent
  pas) et R4 (`ci-lent` régulier).
- *Avant un ouvrage géotechnique non linéaire (forme de radoub)* : R1, qui est un préalable
  plus lourd que R2. Le tronc commun ne connaît que des calculs linéaires à cas élémentaires
  (contrôles, combinaisons, tables). La forme de radoub ajoute le phasage, la sous-pression
  et l'interaction sol-structure non linéaire, tous absents. R5 et R6 réduisent ensuite le
  coût propre à l'ouvrage.
- *Ce qui n'apporte rien et peut être allégé* :
  - R10 ;
  - le compteur de consultations (R7) ;
  - les règles écrites dans `CLAUDE.md` qui n'ont empêché aucune répétition (§ 7.1), à
    remplacer par des contrôles exécutables ;
  - la double version de la comparaison de l'estacade.

---

## 9. Commandes lancées et résultats

Toutes ont été lancées depuis la racine du dépôt, dans le Cloud, avec le `.venv` du projet.
Les sorties sont dans `docs/audit/annexes_lot48/`.

| Commande | Résultat |
|---|---|
| `.venv/bin/aster-expert env-check` | OK (profil cloud), 10 vérifications, 3 absences attendues, 6,5 s |
| `.venv/bin/aster-expert mcp-check` | OK, 9 outils, 86,6 s |
| 9 outils MCP appelés directement (§ 2) | tous répondent ; `analyze_comm` sur l'estacade : 892 461 caractères |
| `.venv/bin/pytest -q -p no:cacheprovider --cov=aster_expert --cov=quai_cw_test_01 --cov=dalle_appuyee_01 --cov=estacade_pieux_01 --cov-report=json:…` | 1 622 réussis, 8 ignorés, 4 désélectionnés, 320,8 s ; couverture 85 % |
| `.venv/bin/pytest -m lent_aster -p no:cacheprovider -ra -q` | 3 réussis, 20,7 s |
| `.venv/bin/ruff format --check` ; `.venv/bin/ruff check` | 550 fichiers conformes ; aucune erreur |
| `.venv/bin/mypy src` ; `.venv/bin/mypy` | aucune erreur (133 ; 392 fichiers) |
| `.venv/bin/python -m aster_expert.publication --arbre` | code 0, aucune sortie (liste de termes absente : non vérifiée) |
| `.venv/bin/aster-expert etat verifier` | « docs/etat.yaml cohérent » |
| `.venv/bin/aster-expert connaissances verifier` | OK ; 169 entrées ; 300 preuves confrontées ; 55 exécutions non vérifiables |
| `.venv/bin/aster-expert constats rejouer --constat CA-034 --constat CA-040 --constat CA-043 --constat CA-056 --constat CA-057 --sortie <temp>` | 5/5 tiennent, 88,6 s |
| `.venv/bin/aster-expert connaissances rejouer-references --reference REF-005 --reference REF-011 --reference REF-014 --sortie <temp>` | REF-005 et REF-011 tiennent ; REF-014 : 1 cas rejoué (6/6), 2 non rejouables ; code 0 |
| `.venv/bin/aster-expert connaissances rejouer-references --reference REF-015 --sortie <temp>` | calcul `OK` en 2 268 s (37 min 54 s pour la commande), 0/30 valeurs retrouvées, code 1 (§ 4.4 bis) |
| `.venv/bin/aster-expert eval profile-bench --granularity by_file\|by_subsection --output <temp>` | réaliste 82,9 % ou 76,8 % à 10 ; détail au § 5 |
| `.venv/bin/aster-expert eval bench --granularity by_file --output <temp>` | rapport produit (référence naïve comprise), 1,7 s |
| `.venv/bin/aster-expert projet <nom> verifier` (×3) | quai : **échec** (point 14 en révision) ; dalle et estacade : cohérentes, aucun bloqueur |
| `.venv/bin/aster-expert generate estacade_pieux_01 --donnees <données de la dalle> --sortie …` | refus lisible, 14 motifs |
| `.venv/bin/aster-expert generate estacade_pieux_01 --sortie …` | « maillage vérifié inconnu : lancer d'abord l'étape maillage » |
| `.venv/bin/aster-expert mesh check <estacade .mmed> …` | refus : « extension '.mmed' refusée, .med attendu » |
| `.venv/bin/aster-expert mesh check data/processed/audit_lot48/estacade_h0p050.med projets/estacade_pieux_01/maillage/invariants_h0p050.yaml` | 367/367 invariants, 3,8 s |
| `.venv/bin/aster-expert mesh check data/processed/audit_lot48/dalle_h0p125.med projets/dalle_appuyee_01/maillage/invariants_h0p125.yaml` | 48/48, 1,8 s |
| `.venv/bin/aster-expert generate estacade_pieux_01 --maillage data/processed/audit_lot48/estacade_h0p050.med --sortie data/processed/audit_lot48/estacade_regen.comm` | `.comm` écrit ; identique au `.comm` de référence hors lignes de commentaire (`diff` vide) |
| `.venv/bin/aster-expert validate <copie> <script>` (`tuple.comm`, `simple.comm`, copiés de la session vers `data/processed/audit_lot48/`) | tuple : `valid: true`, 6/8, code 0 ; simple : 8/8, 1 erreur, code 1 |
| `.venv/bin/aster-expert note controler <nom>` (×3) | OK pour les trois projets |
| `.venv/bin/aster-expert fiche obligatoires <fiche>` (dalle, estacade) | « Commandes prévues : 0 » |
| `.venv/bin/aster-expert rex <nom>` (×3) | archive partielle refusée, code 0 ; aucun fichier versionné modifié (`git status` vide) |
| `uv tool run vulture src projets scripts tests --min-confidence 60` | 106 signalements, dont 3 fonctions mortes réelles après tri |
| `mcp__github__actions_list` (`list_workflow_runs`) | `ci` : 16 passages, 5 échecs, 1 annulé ; `ci-lent` : 3 passages, 2 échecs |
| `git log`, `git diff --numstat` par intervalle de lots | § 4.5 |

Écart de méthode à signaler : une lecture de `ssls127a.comm` a d'abord été faite par `grep`
directement dans `external/codeaster-src/astest`, contrairement à la règle du dépôt. Elle a
été refaite par `read_test_case`, dont le résultat est seul cité.
