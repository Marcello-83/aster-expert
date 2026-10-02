TOUTE PRODUCTION DE CE DÉPÔT EST EN FRANÇAIS : RÉPONSES DANS LE TERMINAL, Y
COMPRIS LE RÉSUMÉ FINAL, COMPTES RENDUS, MESSAGES DE COMMIT, RAPPORTS,
COMMENTAIRES DE CODE. CETTE RÈGLE A DÉJÀ DÛ ÊTRE RAPPELÉE EN TÊTE DE FICHIER
DEUX FOIS (LOTS 30 ET 32) PARCE QUE DES RAPPELS PLUS BAS DANS LE DOCUMENT
N'AVAIENT PAS SUFFI À LA FAIRE RESPECTER (COMPTES RENDUS DES LOTS 29 ET 31
RÉDIGÉS EN ANGLAIS) : NE PAS LA REDÉPLACER PLUS BAS.

# AsterExpert

## Langue de travail (lire en premier)

**Toute production de ce dépôt est en français** : comptes rendus au fil de la
session, messages de commit, rapports d'essai (`docs/essais_lotXX.md`),
commentaires techniques, noms de sections. Le code Python (identifiants,
docstrings) reste en anglais — voir la section « Langue » ci-dessous, qui ne
fait que détailler cette règle. Cette règle a déjà dû être rappelée en tête de
fichier une fois (lot 30) parce qu'un rappel plus bas dans le document n'avait
pas suffi à la faire respecter : ne pas la redéplacer plus bas.

## Organisation du dépôt (lot 41) — lire en second

**Tout code propre à un ouvrage va dans `projets/<nom>/`, jamais dans `src/`.**

- `src/aster_expert/` est le **tronc commun** : ce qui vaut pour tout ouvrage
  (catalogue et validation B, recherche documentaire et cas tests, exécution et
  compte rendu, schéma de fiche et arbitrage, données structurées, exécution
  Salomé et vérificateur de maillage, contrôles D paramétrés, lecture MED,
  combinaisons, ferraillage 1D et module EN 1992, base de constats, déclaration
  et enchaînement des projets). Un test (`tests/unit/test_tronc_commun_sans_ouvrage.py`)
  échoue si `src/` nomme un groupe, un cas, une donnée ou le nom d'un ouvrage.
- Un ouvrage est un **projet** : `projets/<nom>/`, paquet Python importé depuis
  `projets/` (fiche, données et sources, script Salomé et invariants, générateur ou
  `.comm`, extensions, scripts de lot, tests, résultats de référence) et sa
  **déclaration** `projet.yaml` (schéma `aster_expert.projet.declaration`), seule
  interface avec le tronc commun. Le code propre à un projet peut être écrit par
  une session d'agent pour ce projet ; le tronc commun garantit la vérification
  (validation B, invariants de maillage, contrôles D, niveau atteint).
- Un fait établi sur Code_Aster va dans la **base de constats**
  `connaissances/constats_code_aster/CA-nnn.json` (un fichier par constat), jamais
  recopié dans une fiche : la fiche le référence
  (`{"nature": "constat", "constat_id": "CA-nnn", "point_label": ...}`).
- Enchaînement : `aster-expert projet <nom> <étape>` (verifier, maillage, generer,
  valider, executer, controles, synthese, combinaisons, ferraillage, tout). Les
  sorties vont dans `projets/<nom>/resultats/` (non versionné, `etat.json`), sauf
  `resultats/paquet/` (lot 45), **versionné** : `aster-expert projet
  exporter-resultats <nom>` y copie ce que déclare `results_package` dans
  `projet.yaml` (CSV, JSON, PNG, TXT ; jamais de MED ; 20 Mo au plus) et écrit
  `paquet.json` (empreintes, cohérences, régénération du `.comm`, commits des
  critères, niveau atteint niveau par niveau). C'est la seule source de résultats
  d'une session Cloud.
- Premier projet : `projets/quai_cw_test_01/` (quai combi-wall). Les répertoires
  `data/examples/lotNN_*` restent les archives des essais des lots.

## Environnement : Python du projet (lot 41 bis) — lire en troisième

**Ne jamais dépendre du Python du système ; tout passe par le `.venv` du projet.**
Le passage d'Ubuntu 24.04 à 26.04 a retiré `python3.12` et cassé le `.venv`
(`docs/environnement.md`, § 4). Depuis le lot 41 bis :

- la version de Python est fixée par `.python-version` (3.12) et installée par
  `uv` dans l'espace utilisateur (`~/.local/share/uv/python/`), jamais par `apt`
  ni `sudo` ; `[tool.uv] python-preference = "only-managed"` interdit à `uv` de
  choisir un Python du système ;
- les dépendances sont verrouillées dans `uv.lock` (versionné) : reconstruire
  par `uv sync --locked --all-extras`, jamais par `pip install` ; mettre à jour
  une dépendance est un changement délibéré, commité avec sa justification ;
- toute commande passe par `.venv/bin/…` (`aster-expert`, `pytest`, `ruff`,
  `mypy`), jamais par `python3` du système ;
- **`aster-expert env-check` est la première commande de chaque lot**, avant
  `mcp-check` : Python du `.venv` contre `.python-version`, dépendances contre
  `uv.lock`, Docker, `cave`, digest de l'image, Singularity et image Salomé,
  dossier partagé, exécutable du serveur MCP ; arrêt au premier écart. Si
  `aster-expert` lui-même ne démarre pas (`.venv` cassé), lancer
  `uv sync --locked --all-extras` puis `env-check` ;
- un écart de Docker, de Singularity ou du montage du partage ne se corrige
  jamais par la session (`sudo` exclu) : la session s'arrête et décrit à MM ce
  qu'il faut faire ;
- le passage à une autre version de Python (3.14 évaluée au lot 41 bis) est un
  lot à part, délibéré et testé.

## GitHub, branches et Cloud (lot 41 ter) — lire en quatrième

Le dépôt est hébergé sur un dépôt GitHub **privé** (`aster-expert`,
`docs/publication_github.md`) ; une session peut tourner dans la VM ou dans le
Cloud de Claude Code (`docs/cloud.md`).

- **Un lot, une branche** `lot-NN` (`lot-41ter`, `lot-42`…), poussée sur GitHub
  avec le commit du lot. **MM fusionne dans `main`** après relecture du compte
  rendu ; une session ne fusionne pas et ne pousse jamais directement sur `main`
  (dans le Cloud, le proxy GitHub n'autorise de toute façon que la branche de
  travail de la session).
- **En tête de lot, la session annonce son profil** (`vm` ou `cloud`), lu sur la
  première ligne de `aster-expert env-check`. Un lot qui exige Salomé (maillage,
  `pytest -m lent_salome`) ou le dossier partagé ne se lance que dans la VM ; dans
  le Cloud, leur absence est attendue et `env-check` la signale comme telle.
- **Rien de ce qu'interdit `docs/publication_github.md` n'est jamais ajouté** :
  secrets, fichiers de MM (`calcul_3d_*`, données PANG), texte d'une norme AFNOR
  (citer l'article, ne pas verser le texte), fichiers de plus de 50 Mo. Garde-fous :
  `config/publication.yaml`, crochet `scripts/git-hooks/pre-commit` (à activer une
  fois par clone : `git config core.hooksPath scripts/git-hooks` ; le script Cloud
  le fait) et `tests/unit/test_publication.py`. Ne jamais contourner le crochet
  (`--no-verify`).
- `/media/sf_partage` reste la zone d'échange avec MM pour les livrables lourds
  (VM seulement). Les consignes et comptes rendus de lot peuvent vivre dans
  `docs/lots/`.
- `.mcp.json` lance le serveur par `uv run --project ${CLAUDE_PROJECT_DIR:-.}
  --locked --all-extras` : aucun chemin propre à une machine.

## Base de connaissances et retour d'expérience (lot 42) — lire en cinquième

**Chaque projet rend l'outil meilleur** : ce qu'il apprend est écrit dans
`connaissances/` (six couches, `connaissances/LISEZMOI.md`), consulté avant d'agir
et protégé par des tests.

- Couches : `constats_code_aster/` (CA-nnn), `diagnostics/` (DIAG-nnn, ENV-nnn :
  signature d'erreur, cause, correction), `patrons/` (PAT-nnn), `controles/`
  (CTL-nnn), `references_validation/` (REF-nnn), `precedents/` (PRE-nnn). Schémas :
  `aster_expert.connaissances.modeles` ; aucune entrée sans preuve ; contrôle par
  `aster-expert connaissances verifier`.
- Statuts : `observé`, `établi` (preuve rejouable : cas versionné ou test),
  `promu` (deux projets ou niveau E), seulement par `aster-expert connaissances
  promouvoir <id>`, qui vérifie les conditions. Aucune promotion automatique.
- **Consultation obligatoire** (`search_connaissances`, skill `code-aster-expert`
  § 6 quater) : avant d'écrire une commande (constats, patrons) ; dès qu'une erreur
  ou une alarme apparaît dans un `.mess` (diagnostics, avant toute autre
  hypothèse ; `aster-expert run` les affiche pour un échec) ; avant de proposer une
  décision pratique (précédents) ; avant d'écrire un contrôle (contrôles).
- **Un précédent n'est jamais appliqué** : il se propose (`aster-expert
  connaissances proposer-precedent`, entrée non tranchée, origine
  `precedent_projet`) et MM arbitre.
- **Tout lot se termine par `aster-expert rex <projet>`, et le compte rendu inclut
  sa sortie.** Un échec d'exécution non classé (registre
  `connaissances/rex/<projet>.yaml` : rattaché à un diagnostic, nouveau
  diagnostic, ou écarté avec un motif) bloque la clôture du lot. Le compte rendu
  déclare les interventions de MM et les connaissances qui ont évité une erreur
  (champ `lots` du registre), à partir du lot 43.

## Fiche : les choix de l'agent, la promotion, la naissance d'un projet (lot 44) — lire en sixième

**Règle de partage.** Une fiche a trois catégories d'entrées : les faits Code_Aster
(`code_aster`, sourcés), les décisions de MM (`pratique`, origine `arbitrage_mm`,
`decision_ingenieur`…) et, depuis le lot 44, les **choix de l'agent** (origine
`choix_agent`, `aster_expert.agent.arbitration.record_agent_choice`).

- **Relève de `choix_agent`** (et seulement cela, `AgentChoiceDomain`) : noms de
  groupes ; repère, origine et unités ; type et taille des mailles ; suite de
  convergence ; lecture des champs (`NOEU`/`ELNO`) ; blocage isostatique des
  mouvements de corps rigide ; étendue du modèle quand la symétrie est contrôlée.
- **Reste à MM** ce qui engage l'ouvrage : matériaux, actions, combinaisons,
  durabilité, conditions d'appui physiques, paramètres de ferraillage, choix d'une
  modélisation qui change la physique représentée.
- Un `choix_agent` nomme ses vérificateurs (`verified_by` : `CTL-nnn`, `REF-nnn` ou
  `projet:<nom>`) ; sans eux, ou hors des domaines ci-dessus, le schéma le refuse. Il
  est tranché (ne bloque pas la génération) et figure dans une section séparée du
  document d'arbitrage, où MM peut le remplacer (`record_practice_decision`, le choix
  de l'agent passe dans `decision_history`). Une question qui mêle les deux catégories
  se scinde. Détail : skill `hypotheses-drafting`, § 2 bis.
- **Paramètres obligatoires** : la fiche déclare les commandes qu'elle prévoit
  (`planned_commands`) ; `aster-expert fiche obligatoires` lit les mots-clés
  obligatoires de la combinaison d'options (catalogue **et**
  `data/config/obligations_execution.yaml` : le catalogue 17.4 déclare `optional` des
  mots-clés que `CALC_FERRAILLAGE` exige à l'exécution, CA-053) et ajoute une question
  par mot-clé non couvert.
- **Promotion** : une réutilisation ne compte que si le projet a **éprouvé** l'entrée
  (exécution réussie ou test versionné, `connaissances.modeles.is_proof`) ; une citation
  dans une fiche, une décision, un document ou du code n'est pas une épreuve. Épreuves
  d'un constat : `connaissances/epreuves_constats.yaml`. Rejeu :
  `aster-expert connaissances eligibilite`.
- **Naissance d'un projet** : `aster-expert projet creer <nom>` (arborescence,
  `projet.yaml` minimal, racines d'exécution, registre `rex`).
- **Métriques** : `rex` sépare les exécutions de **développement** et de
  **vérification** (lancée par une commande de rejeu -- `ASTER_EXPERT_RUN_ORIGIN` dans
  le compte rendu -- ou rejeu d'un `.comm` déjà réussi, même empreinte) ; le taux
  d'échec porte sur le développement seul.
- **Anomalies ouvertes** : `connaissances/anomalies_ouvertes.yaml` (ANO-nnn) relie des
  entrées qui portent peut-être une même cause, sans rien conclure.

## Mission

Construire un agent expert Code_Aster versionné, traçable, capable de valider
les fichiers qu'il produit.

Le système ne doit jamais confondre :

- pertinence documentaire ;
- validité syntaxique vis-à-vis du catalogue ;
- réussite d'exécution ;
- validité physique ;
- validation par comparaison à une référence.

## Environnement d'exécution

Le dépôt vit dans une machine virtuelle Ubuntu 26.04 (Oracle VirtualBox ;
24.04 jusqu'au 2026-09-30, voir `docs/environnement.md`).
Code_Aster n'y est pas installé nativement : il s'exécute dans un conteneur
Docker (image `simvia/code_aster`), géré par l'outil tiers `cave`. Le
développement et l'indexation ont lieu dans la VM ; l'introspection du
catalogue et l'exécution de calculs ont lieu à l'intérieur du conteneur,
jamais par sous-processus natif de la VM. L'hôte (hors VM) ne sert qu'à
l'édition (VSCode en Remote-SSH) et ne dispose ni de Docker ni de Code_Aster.

Deux interpréteurs Python coexistent et ne doivent jamais être confondus :

- le Python du projet (`.venv`, Python 3.12 géré par `uv`, jamais celui du
  système), dans la VM, qui exécute `aster_expert` ;
- le Python de l'installation Code_Aster, à l'intérieur du conteneur, seul
  capable d'importer `code_aster` et son catalogue.

Le Python du projet n'importe jamais `code_aster`. Toute introspection du
catalogue passe par un script autonome, copié dans un répertoire de travail
dédié puis exécuté par le Python d'Aster à l'intérieur d'un conteneur
restreint (réseau désactivé, utilisateur non root, limites de ressources), qui
produit du JSON sur la sortie standard. Voir `docs/architecture.md`, décisions
ADR-002, ADR-003 et ADR-006.

## Principes fondamentaux

1. Ne jamais mélanger silencieusement plusieurs versions de Code_Aster.
2. La version cible est résolue à partir de l'installation réelle, jamais
   supposée. Si elle est inconnue, l'exécution s'arrête avec un message
   explicite.
3. La syntaxe officielle provient du catalogue de la version installée, pas
   des manuels. Les manuels U/R/V documentent la sémantique, la théorie et les
   cas d'emploi.
4. Toute donnée indexée conserve sa source, son chemin, sa révision Git et sa
   version documentaire.
5. Les cas tests sont des références exécutables, pas des modèles
   transposables. Toute réutilisation exige la comparaison de la modélisation,
   des éléments, de la loi de comportement, des chargements, des conditions aux
   limites, du type d'analyse et de la version.
6. Toute réponse distingue faits documentés, déductions et recommandations.
7. Un calcul terminé sans erreur n'est pas nécessairement physiquement valide.
8. Ne jamais neutraliser une alarme sans en expliquer la cause.
9. Ne jamais modifier ni tronquer une partie d'un fichier utilisateur sans
   nécessité. Aucun `...` ni « reste inchangé » dans un fichier produit.
10. Tout développement a des tests. Une fonctionnalité sans test n'est pas
    terminée.
11. Aucun document, résultat ou extrait synthétique ne doit être présenté comme
    réel.

## Ne pas réimplémenter ce que Code_Aster fournit

Le package `run_aster` livré avec l'installation expose déjà :

- `run_aster.command_files` : préparation des fichiers de commandes ;
- `run_aster.status` : état d'une exécution ;
- `run_aster.error_messages` : extraction des messages d'erreur d'une sortie ;
- `run_aster.export` : lecture des fichiers `.export` ;
- `run_aster.config` : paramètres de l'installation.

Ces modules sont encapsulés, jamais réécrits. Un parseur `.mess` maison ne se
justifie que pour ce que ces modules ne couvrent pas, et la lacune doit être
documentée avant d'être comblée.

Il n'existe pas d'option de `run_aster` réalisant une vérification syntaxique
sans exécution (`--env` prépare seulement le répertoire de travail). La
validation statique de niveau B est donc réalisée par confrontation au
catalogue introspecté.

## Niveaux de validation

- A : réponse documentaire, non exécutée.
- B : syntaxe confrontée au catalogue de la version cible.
- C : fichier exécuté jusqu'à `FIN`.
- D : résultats soumis à des contrôles physiques.
- E : résultats comparés à une référence validée.

Ne jamais annoncer un niveau supérieur à celui réellement atteint. Les
expressions « entièrement validé », « sans erreur » et « correct » sont
interdites sans mention du niveau atteint.

## Langue

- Documentation du projet et messages utilisateur : français.
- Code Python : identifiants et docstrings en anglais.
- Commentaires techniques : homogènes par fichier.
- Identifiants Code_Aster : casse officielle conservée exactement
  (`STAT_NON_LINE`, `AFFE_CHAR_MECA`, `COQUE_3D`, `DIS_CHOC`).

## Priorité des sources

### Syntaxe
1. Catalogue de la version installée.
2. Documentation U4 et U7 de la même version.
3. Cas tests de la même version.
4. Sources d'implémentation.

### Théorie
1. Documents R.
2. Guides méthodologiques U2.
3. Documentation U4.
4. Documents V.

### Exemples
1. Cas tests officiels.
2. Document V associé.
3. Documentation des commandes employées.

Le forum et les sources communautaires sont des sources secondaires et doivent
être signalés comme telles.

## Règles de développement

- Python du projet : 3.12, fixé par `.python-version`, installé par `uv`
  (`requires-python = ">=3.12"` dans `pyproject.toml`, dépendances dans `uv.lock`).
- `pathlib` pour tous les chemins, jamais de concaténation de chaînes.
- Annotations de types sur toute fonction publique.
- Modèles de données validés (`pydantic`) pour tout objet sérialisé.
- Journalisation de chaque téléchargement, transformation et indexation.
- Chaque traitement est reproductible et idempotent.
- Éviter les dépendances inutiles ; toute dépendance nouvelle est justifiée
  dans le commit qui l'introduit.
- Aucun accès réseau dans les tests unitaires. Les dépôts Git de test sont
  créés localement dans des répertoires temporaires.
- Tout code propre à un ouvrage va dans `projets/<nom>/`, jamais dans `src/`
  (lot 41). Ses tests vont dans `projets/<nom>/tests/`.

## Gestion des dépôts externes

Les dépôts Code_Aster sont clonés sous `external/` et ne sont jamais commités.
Chaque synchronisation enregistre dans un manifeste :

- URL du dépôt ;
- branche ou tag ;
- hash du commit ;
- date de synchronisation ;
- version documentaire associée ;
- présence de modifications locales.

Une synchronisation n'écrase jamais des modifications locales : elle échoue et
le signale.

## Validation obligatoire après modification

0. `aster-expert env-check` (lot 41 bis ; profil annoncé, lot 41 ter), puis
   `aster-expert mcp-check`.
1. Formatage (`ruff format`).
2. Analyse statique (`ruff check`, `mypy` : `src`, `tests` et `projets`, scripts de
   projet compris, en mode strict ; les scripts Salomé d'un projet en sont exclus).
3. Tests unitaires concernés (`pytest` : `tests/` et `projets/*/tests/`, sans
   Docker ni Salomé).
4. Tests d'intégration concernés, si applicable. **Tests réels** (lot 41) :
   `pytest -m lent` lance réellement Code_Aster (cas versionné du lot 22, arrêt
   `<F> <CALCULEL7_40>` du lot 39, avec leur compte rendu) et Salomé (géométrie 1
   du lot 26) puis `mesh check` ; environ deux minutes, hors de la série par défaut.
   Depuis le lot 41 ter : `pytest -m lent_aster` (Code_Aster, VM et Cloud) et
   `pytest -m lent_salome` (Salomé, VM seule) ; une ressource absente fait ignorer
   le test avec son motif, jamais échouer.
5. Compte rendu précis : commandes lancées, sorties réelles, échecs éventuels.

Ne jamais annoncer qu'un test a réussi sans l'avoir exécuté et sans en donner
la sortie.

## Critère de réussite des essais (à partir du lot 25)

Modèle : `docs/modele_rapport_essai.md`.

- Le critère est écrit dans le rapport **avant** l'exécution et n'est pas
  modifié après elle.
- Une grandeur que la théorie de l'élément reproduit exactement doit l'être à
  10⁻⁶ près en relatif.
- Une grandeur sensible à la discrétisation doit présenter une erreur qui
  décroît quand le maillage est raffiné d'un facteur 2.
- Toute autre issue est un échec, rapporté tel quel.

## Fin de lot

Un lot n'est terminé qu'avec un commit Git distinct, dont le message porte
le compte rendu complet :

1. l'inventaire des fichiers créés ou modifiés ;
2. la justification des choix techniques ;
3. la liste des tests exécutés et leurs résultats exacts ;
4. les limites connues et les points non couverts.

Depuis le lot 42, avant ce commit : `aster-expert rex <projet>` (et, une fois les
échecs classés, `aster-expert rex <projet> --enregistrer --lot NN`) ; sa sortie est
reproduite dans le compte rendu, et un échec non classé interdit la clôture.

Depuis le lot 41 ter, ce commit est fait sur la branche `lot-NN` du lot, poussée
sur GitHub ; MM la fusionne dans `main` après relecture (section « GitHub,
branches et Cloud »). C'est toujours le commit lui-même, avec son message
complet, qui fait foi (il a permis de retrouver le travail après un arrêt brutal
de la machine) ; jamais de commit de fusion cosmétique fait par la session.

## Accès MCP (lot 24)

- Le serveur MCP est déclaré en portée projet dans `.mcp.json` (versionné) : il
  lance `aster-expert-mcp` par `uv run --project ${CLAUDE_PROJECT_DIR:-.} --locked
  --all-extras` (lot 41 ter ; installation éditable, code source du dépôt). Une entrée du même nom en portée `local` ou `user` primerait sur elle,
  sans fusion : ne pas en recréer. Voir `README.md` pour la commande exacte.
- Une session garde le processus serveur lancé à son démarrage : du code ajouté
  ensuite n'y est pas visible.
- Chaque lot commence par `aster-expert env-check` (lot 41 bis), puis
  `aster-expert mcp-check` (serveur neuf, outils comparés
  au code, chaque outil appelé sur une requête minimale, arrêt au premier écart).
  Depuis le lot 25, `mcp-check` lit `.mcp.json`, applique `${VAR}` et `${VAR:-défaut}`
  à partir de l'environnement du shell **seul** (Claude Code ne définit
  `CLAUDE_PROJECT_DIR` que dans l'environnement du serveur lancé : ne jamais
  l'injecter dans le contrôle), vérifie que la commande obtenue existe et est
  exécutable, puis démarre le serveur avec cette commande. Ses appels portent
  `origin: "mcp-check"` dans `query_log.jsonl` (variable `ASTER_EXPERT_CALL_ORIGIN`) ;
  `read_usage_entries` les exclut des statistiques d'usage (les lignes antérieures
  au lot 25 n'ont pas d'origine et comptent comme usage).
  Quiconque ajoute un outil à `server.py` lui ajoute sa requête minimale dans
  `aster_expert/mcp/check.py` : à défaut le contrôle échoue.
- Si un outil attendu n'est pas visible dans la session, la session s'arrête et
  demande à MM de relancer Claude Code ou de reconnecter le serveur (`/mcp`). Elle
  ne se replie jamais sur une lecture directe de la documentation ou des cas tests.
- Un lot qui ajoute ou modifie un outil MCP se termine par une consigne explicite à
  MM : redémarrer la session avant le lot suivant.
- Une session par lot.
- Huit outils depuis le lot 41 : `search_constats` cherche dans la base partagée des
  constats (commande, mot-clé, texte) ; le skill `code-aster-expert` impose de la
  consulter avant d'écrire une commande.
- Neuf outils depuis le lot 42 : `search_connaissances` interroge les six couches de
  `connaissances/` (texte, commande, mot-clé, couche, statut) et englobe
  `search_constats`, conservé.
- Lot 44 : `get_command_schema` filtré par `keyword` ne renvoie que le sous-arbre
  demandé (`keyword_variants`), `command_schema` réduit à ses métadonnées et
  `keywords_omitted` qui compte ce qui est laissé de côté.
- `search_codeaster_docs` n'indexe pas les cas tests (familles présentes : V, R, U4,
  D, U2, U3, U7, U1, SV, SU, U0) : les chercher par `search_test_cases`. Une `family`
  absente de l'index est refusée avec la liste des familles présentes.

## Scripts Salomé (lot 26)

Les maillages d'ouvrage sont produits par des scripts Python exécutés dans
Salomé-Méca (`aster-expert mesh run`, configuration `mesh:` de
`config/validation.yaml`) et contrôlés par un vérificateur indépendant qui relit
le MED sans Salomé (`aster-expert mesh check <fichier.med> <invariants.yaml>`,
`medcoupling` de l'image Docker de `cave`). Règles d'écriture d'un script :

- toute la géométrie est assemblée en **une seule partition** (`MakePartition`)
  avant le maillage, pour garantir le partage des nœuds aux interfaces ; le bloc
  est encadré par `# ASSEMBLY begin` / `# ASSEMBLY end` (les variantes altérées
  le remplacent) ;
- les groupes sont créés **sur la géométrie** (`CreateGroup`, `GetInPlace`,
  `UnionIDs`) puis transférés au maillage (`GroupOnGeom`), jamais sélectionnés à
  la main ;
- **aucune coordonnée en dur** : tout est lu du fichier de paramètres passé au
  script (`args:<params>,<sortie.med>`) ;
- le script écrit `<sortie>.meta.json` avec l'empreinte SHA-256 de ses
  paramètres ; `mesh run` échoue si elle manque ou diverge.

Règles complémentaires (lot 27, leçons du lot 26) :

- **Arguments nommés.** Tout appel GEOM ou SMESH à plus de trois paramètres passe
  ses arguments par nom, jamais par position (erreur de `MakePartition` au lot 26).
- **Discrétisation explicite.** Ne pas s'appuyer sur l'arrondi d'une longueur
  locale : pour chaque arête, le script calcule un nombre de segments entier à
  partir de la taille visée et de la longueur réelle (`segment_count`) ou prend celui
  qu'une décision fixe, et l'impose par une hypothèse de sous-maillage sur un groupe
  d'arêtes de la partition. Ces nombres sont écrits dans `<sortie>.meta.json` et
  reportés dans le rapport de maillage.
- **Comptages attendus.** Les nombres de nœuds et de mailles attendus sont calculés
  analytiquement à partir des mêmes paramètres, par un module distinct du script
  Salomé (`aster_expert.meshing.combiwall`), avant l'exécution.
- Un script long écrit sa progression dans `<sortie>.progress.txt` (le journal d'un
  processus tué par le délai est perdu).

Noms et signatures GEOM/SMESH : jamais de mémoire. Ils sont relevés par
introspection dans l'image (`scripts/salome/lot26_sonde_signatures.py`, sortie
versionnée `data/examples/lot26_essais/signatures_geom_smesh.txt`). Piège
constaté : dans `MakePartition`, `KeepNonlimitShapes` est le **8e** argument
(`RemoveWebs` est le 6e) ; le passer en 6e position supprime silencieusement les
arêtes isolées (poutre, barre) du maillage.

Le vérificateur évalue **tous** les invariants (comptages de nœuds et de mailles
par type, présence, cardinalité, type de mailles et boîte englobante de chaque
groupe, nœuds à des coordonnées imposées, nœuds partagés entre groupes, nœuds
orphelins, nœuds confondus non fusionnés), les liste avec valeur attendue et
valeur obtenue, et sort en erreur (code 1) dès qu'un seul est en écart en
désignant le premier. Les valeurs attendues d'un fichier d'invariants sont
calculées **analytiquement à partir des paramètres**, avant l'exécution, jamais
relues d'un MED produit.

Constat (lot 26) : les MED exportés contiennent aussi les SEG2 du maillage 1D
(bords compris) ; les comptages de mailles les incluent.

- Lot 26 (`docs/essais_lot26.md`, `data/examples/lot26_essais/`,
  `scripts/salome/`, `scripts/build_lot26_essais.py`, `collect_lot26_essais.py`,
  `analyze_lot26_essais.py`) : trois géométries qualifiées (plaque avec raidisseur,
  tube facettisé à 40 facettes et deux plaques sur ses génératrices Y = 0, poutre et
  barre sur une coque), chacune avec une variante altérée rejetée par `mesh check`.
  Limites : la règle d'arrondi de `LocalLength` pour une longueur non multiple de la
  taille n'est pas qualifiée (toutes les longueurs des essais sont des multiples de
  0,25) ; la connexion réelle barre/coque n'est pas éprouvée par un calcul de
  rigidité ; la seule lecture par Code_Aster est celle des groupes (masses).
- Étape 1 du lot 26 faite au lot 27 : `donnees_complementaires_combiwall_v1.md` (copié à
  l'identique) ; décision 11 enregistrée au point 10 (`_record_decision_11`,
  `lot27_enregistrement.json`) ; `ECRAN_POUSSEE` rattaché au point 10 ; les 22 valeurs « à
  fournir » ont toutes une source (`generation_blockers(model_data)` vide). Deux
  correspondances de nature différente : `position_tete_sur_tube` est donnée en Y (0,71 m) et
  non en degrés ; `nombre_divisions_verticales` est remplacée par `taille_verticale_visee`
  (0,25 m) et `cotes_imposees`. Les profils de pression sont des tableaux de points
  (`ProfilePoint` : z, p, couche, composante G/Q1) ; G et Q1 ne sont pas sommés.
- Lot 27 (`docs/essais_lot27.md`, `data/examples/lot27_maillage/`,
  `scripts/salome/combiwall_mesh.py`, `scripts/build_lot27_maillage.py`,
  `analyze_lot27_maillage.py`, `aster_expert.meshing.combiwall`) : maillage du quai
  (40 114 nœuds, 40 120 QUAD4, 39 583 SEG2, 57 groupes), 588/588 invariants
  (`data/examples/combiwall_mesh_invariants.yaml`, généré, ne pas éditer), lecture Code_Aster
  niveau C, masses exactes à 5e-13. Le script exécuté ne diffère du versionné que par des
  commentaires et le formatage (AST identique). Le maillage dure ~17 min (groupes : 805 s) ;
  délai `mesh.salome.timeout_seconds` porté à 3 000 s. Limite : la poutre n'est pas reliée à
  l'écran (lot 28) ; les groupes de nœuds ne sont contrôlés que par `mesh check`.
- Lot 28 (`docs/essais_lot28.md`, `data/examples/lot28_quai/`,
  `src/aster_expert/generation/`) : décision 12 (appui vertical, DZ seul au pied des tubes) et
  groupe `PIED_TUBES` (322 nœuds = 7×40 + 2×21, `mesh check` 592/592) ; six constats
  `code_aster` (points 2, 3, 5×3, 7) sourcés catalogue + cas test officiel chacun
  (`sdlx03b.comm`, `ssls118a.comm`, `sdls118a.comm`, `ssls100b.comm`, `comp009a.comm`) ;
  générateur `aster_expert.generation` (`aster-expert generate <fiche> <données>
  <maillage vérifié>`) refusant si la fiche n'est pas prête, un fait manque, ou le maillage
  ne correspond pas au dernier `mesh check` réussi (`find_verified_mesh`, cache de maillage
  ajouté ce lot dans `aster_expert.meshing.run`). `.comm` déterministe, 2410 lignes, niveau B
  intégral (80/80). Ressorts : 48 classes (`aster_expert.generation.springs`), groupées par
  colonne (`ENV_CYLINDRE`) × ligne haute/basse (`PLAN`) plutôt que par nœud (~10 600 occurrences
  initiales avaient fait perdre la connexion MCP sur `analyze_comm`) ; Σk_i exact
  (35×20,80×6,00 et 80×11,36×8,00, écart ≤1e-9). Noms de groupe générateur limités à 24
  caractères (`aster_expert.generation.comm._gn`) : au-delà, Code_Aster tronque en silence et
  ne le signale qu'au premier doublon résultant (`<F> <SOUSTRUC_37>`, fait établi par
  exécution, absent du schéma catalogue où `NOM` est un `TXM` sans longueur). **Niveau C non
  atteint** : `LIAISON_SOLIDE` (neuf occurrences, anneau DKT + nœud de poutre, point 3) combiné
  aux ~10 400 éléments `DIS_T` des ressorts (point 4) produit un pivot de Lagrange exactement
  nul à la factorisation MUMPS (`<F> <FACTOR_11>`), systémique sur les neuf tubes (confirmé par
  sept exécutions réelles : `COEF_RIGI_DRZ` sans effet même ×100, une reproduction isolée sans
  les ressorts aboutit, l'exclusion d'un nœud déplace l'échec vers un autre tube). Cause
  probable non confirmée : choix interne par Code_Aster du nœud de référence du corps rigide
  parmi des nœuds nominalement équivalents (R3.03.02), sensible à la numérotation globale —
  hors de portée des sept outils MCP. Aucun contrôle D fait. Piste pour un prochain lot :
  `LIAISON_ELEM`/raccord coque-poutre dédié (R3.03.03, R3.03.06) à la place de `LIAISON_SOLIDE`,
  avec sa propre étude de faisabilité avant exécution.
- Lot 29 (`docs/essais_lot29.md`, `data/examples/lot29_repro/`,
  `scripts/build_lot29_repro.py`, `scripts/build_lot29_repro_two_units.py`) : diagnostic du pivot
  nul du lot 28 par reproducteur minimal (un tube facetté + `LIAISON_SOLIDE` + N ressorts `DIS_T`,
  hors de tout projet, maillage ASTER natif sans Salomé), 21 exécutions réelles en ~15 min (jamais
  le modèle complet, interdit par ce lot). Trois hypothèses **écartées** par la matrice
  (`data/examples/lot29_repro/results.json`) : nombre de ressorts (0 à 10 000, insensible),
  échelle de raideur (1e2 à 1e10 N/m, insensible, cohérent avec l'insensibilité de
  `COEF_RIGI_DRZ` du lot 28), symétrie seule avec la logique de production actuelle. La
  redondance liaison/CL (H1, déjà corrigée en production par `symmetry_and_support_block`) est
  **reconfirmée comme un mécanisme réel** en isolation totale (`D0_sym_redundant`, zéro ressort,
  même signature `<F> <FACTOR_11>` que `data/examples/lot28_quai/rapports/mess_case_g_extrait.txt`
  — noms de fichiers similaires, deux nœuds listés juste avant l'erreur) mais **insuffisante** :
  la géométrie corrigée réussit systématiquement, avec ou sans ressorts. Extension hors matrice
  (`E0_two_units`, deux `LIAISON_SOLIDE` indépendantes + 10 000 ressorts partagés) : réussit aussi,
  la simple multiplicité de liaisons ne suffit pas. `search_test_cases` : la combinaison
  `LIAISON_SOLIDE` + `DISCRET` a des précédents officiels (≥25 cas, ex. `sdlx106a.comm`,
  `zzzz200b.comm`) — ce n'était pas une combinaison inédite. **Aucune correction apportée** (aucune
  cause établie pour l'échec résiduel) ; modèle complet non relancé. Piste non testée : la poutre
  de couronnement du quai est **continue** entre les neuf `LIAISON_SOLIDE` (contrairement aux
  poutres-tronçons isolées de ce lot) — candidat pour un prochain lot.
- Lot 30 (`docs/essais_lot30.md`, `data/examples/lot30_quai_reduit/`,
  `scripts/build_lot30_quai_reduit.py`, `scripts/generate_lot30_quai_reduit.py`) : la piste laissée
  par le lot 29 (poutre continue) confirmée par un **quai réduit** produit par la chaîne de
  production elle-même (même script Salomé, même générateur, mêmes décisions ; deux entraxes, trois
  tubes, 10 204 nœuds contre 40 114) — reproduit le pivot `<F> <FACTOR_11>` du lot 28 en 13,7 s
  (contre 44 s pour le modèle complet, 112,6 s de maillage contre ~17 min). Quatre retraits
  d'ingrédient ajoutés au générateur, diagnostic seulement, jamais actifs par défaut
  (`aster_expert.generation.generate.DiagnosticOmissions` : `sans_ressorts`, `sans_tirants`,
  `sans_palplanches`, `sans_poutre`) : les trois premiers **n'évitent pas** l'échec (contredit le
  lot 28 sur le rôle nécessaire des ressorts, établi sur un reproducteur distinct du générateur de
  production) ; le quatrième (poutre, donc `LIAISON_SOLIDE`) fait disparaître le pivot. **Fait
  établi** : `LIAISON_SOLIDE`, avec plusieurs occurrences simultanées liées par une poutre
  **continue**, produit le pivot nul indépendamment des ressorts/tirants/palplanches — précise, sans
  le contredire, le rôle de `LIAISON_SOLIDE` déjà établi au lot 28. Cause touchant la décision du
  point 3 : **non modifiée**, modèle complet **non relancé** (recommandation reconduite du lot 28 :
  étudier `LIAISON_ELEM`/R3.03.03-06). Deux généralisations corrigées dans le générateur de
  *production*, sans rapport avec la cause (révélées par le premier usage sur une géométrie autre
  que huit entraxes) : `check_spring_sum` (largeurs/hauteurs de bande tapées en dur →
  `aster_expert.meshing.combiwall.band_projected_width`) et la paire de symétrie du contrôle D de
  `controls_block` (`ANC_01/09`, `TETE_TUBE_02/08` tapés en dur → calculés depuis les tubes de bord,
  dédoublonnés — `GROUP_NO` refuse toute valeur répétée, constaté par `validate_comm`) ; le `.comm`
  de production reste octet pour octet identique (vérifié deux fois). Défaut latent découvert sans
  rapport avec `LIAISON_SOLIDE`, non corrigé : ressorts `DIS_T` sans masse sous `PESANTEUR`
  (`<F> <DISCRETS_26/30/31>`), jamais atteint avant ce lot car `FACTOR_11` arrêtait toujours
  l'exécution plus tôt. 8 exécutions Code_Aster réelles (129,5 s cumulées, dont 3 refaites après une
  erreur de préparation sans rapport : nommage `.export`/`.mmed`, `VERI_NORM`, charge fantôme
  `CH_Q3`) ; 5 tests unitaires ajoutés. Non testé : retrait 5 (partage de nœud, non exprimable sans
  modifier le maillage) et retrait 6 (symétrie, le premier retrait informatif ayant déjà tranché).
- Lot 31 (`docs/essais_lot31.md`, `data/examples/lot31_jonction/`,
  `scripts/generate_lot31_candidat.py`) : cause documentaire du pivot nul établie (constat point 3,
  `data/examples/combiwall_inputs/lot31_facts.json`/`lot31_extraits.json`) en combinant trois faits
  catalogue jamais réunis avant ce lot : `LIAISON_SOLIDE` place un anneau DKT + un nœud de poutre
  POU_D_E dans le cas 3DA (R3.03.02), qui dualise la rotation DRZ de chaque nœud d'anneau ; DRZ, sous
  DKT, ne porte qu'une raideur fictive minimale (`COEF_RIGI_DRZ`, R3.07.03, 1e-5 par défaut) ; dualiser
  une relation sur un tel ddl est exactement le cas pathologique décrit par R3.03.01 (« structure
  retenue par son dernier ddl physique », pivot nul indépendant de la formulation). Aucun cas test
  officiel ne combine `LIAISON_SOLIDE` + coques DKT + poutre transversale en T sur plusieurs occurrences
  (`search_test_cases`, 69 fichiers `LIAISON_SOLIDE` croisés avec `POUTRE`/`COQUE` ; le plus proche,
  `sdlx102a.comm`, n'a ni poutre transversale ni occurrences multiples). Quatre candidats comparés sur
  le quai réduit du lot 30 (générateur, `aster_expert.generation.generate.JunctionCandidate`, diagnostic
  seulement, jamais actif par défaut) : C1 (`LIAISON_DDL`, translations seules, bras de levier exact,
  rotations d'anneau libres) et C4 (un seul nœud d'anneau lié, réponse à la coïncidence suggérée par MM)
  validés niveau B puis exécutés, **échouent tous deux avec le même `<F> <FACTOR_11>`** -- mais sur le
  **nœud de poutre du plan de symétrie** (déjà dualisé par `CH_BLOC`), jamais sur l'anneau : la cause
  touche plus largement toute relation dualisée combinée à une rotation déjà dualisée à la symétrie, pas
  seulement le mécanisme propre de `LIAISON_SOLIDE`. C2 (rayons rigides matériels) non exécuté, bloqué
  par le catalogue : `CREA_MAILLAGE` ne propose aucun moyen de créer une maille SEG2 entre deux nœuds
  existants non reliés (seul `CREA_POI1` crée de nouvelles mailles, ponctuelles). C3
  (`LIAISON_ELEM`/`COQ_POU`) non exécuté, inapplicable par la documentation seule (R3.03.06 exige une
  poutre dans le prolongement d'un bord libre de coque, jamais une jonction en T). **Aucun candidat
  retenu.** Le point 3 (décision 4, méthode de jonction) est déclaré **en révision**
  (`declare_under_revision`, motif = cause établie) sans être modifié : conséquence directe, la fiche
  n'est plus prête pour la génération (`HypothesesSheet.generation_blockers`, `aster-expert generate`
  refusera désormais tant que MM n'aura pas tranché) -- les tests de mécanique du générateur
  (`test_generation_generate*.py`) utilisent depuis ce lot une copie de la fiche avec la révision levée
  en mémoire seulement, jamais écrite. Étape 3 : `DIS_T` sous `PESANTEUR` exige une masse explicitement
  affectée (`AFFE_CARA_ELEM/DISCRET`, `CARA="M_T_D_N"`, sinon `<F> <DISCRETS_26>`) ; corrigé dans le
  générateur de production (`M_T_D_N=(0.0,)` par classe de ressort -- un ressort est un appui, pas de la
  matière) et vérifié par exécution (le quai réduit `sans_poutre` atteint désormais les cinq cas de
  charge sans ce défaut). Deux défauts latents découverts en vérifiant, jamais atteints avant ce lot
  (le pivot arrêtait toujours l'exécution plus tôt) : `IMPR_RESU` sans `CARA_ELEM` (`<F> <MED2_14>`,
  SIEF_ELGA à sous-points d'un élément COQUE) **corrigé** (`footer()`, `CARA_ELEM=CARA` sur chaque
  `RESU`, testé) ; collision de nom de champ MED entre `RESU_EAU_P` et `RESU_EAU_A`
  (`<F> <MED2_4>`, « RESU_EAUDEPL » présent deux fois) **non corrigé**, sans rapport avec ce lot, mais
  qui bloquera le niveau C du modèle complet même une fois la jonction réglée -- signalé pour un
  prochain lot. 5 exécutions Code_Aster réelles (170,3 s cumulées,
  `data/examples/lot31_jonction/rapports/executions.json`), 1 sonde `medcoupling` jetable (identité
  des nœuds 441/577 et 575/147). Modèle complet non relancé. Limites : le mécanisme précis de
  numérotation interne de Code_Aster reste hors de portée des sept outils MCP (comme aux lots 28/30) ;
  la piste « exclure le nœud de poutre du plan de symétrie de la dualisation de rotation de `CH_BLOC` »
  n'a pas été testée (hors périmètre de ce lot) ; `LIAISON_ELEM`/`OPTION='3D_POU'` (R3.03.03), recommandé
  depuis le lot 28, reste à étudier.
- Lot 32 (`docs/essais_lot32.md`, `data/examples/lot32_cl/`,
  `scripts/generate_lot32_regle_cl.py`) : **le pivot nul est levé, niveau C atteint sur le modèle
  complet pour la première fois.** La correction du lot 31 n'excluait que les rotations (DRY, DRZ) de
  la redondance CL/`LIAISON_SOLIDE` ; ce lot généralise à la translation (DX) -- le nœud de poutre et
  les deux nœuds d'anneau du plan de coupe partagent le même bras de levier nul en X, donc `DX` de
  l'anneau est déjà dérivé de celui de la poutre, l'imposer une seconde fois via `SYM_G`/`SYM_D` bruts
  produisait la même redondance que DRY/DRZ au lot 31. `symmetry_and_support_block` regroupe désormais
  DX/DRY/DRZ dans une seule occurrence portée par `GEN_SYMG_ROT`/`GEN_SYMD_ROT` (anneau exclu) ; contrôle
  ajouté (`check_symmetry_ddl_impo_no_ring_redundancy`, appelé avant écriture, testé) refusant toute
  ligne `DDL_IMPO` qui porterait encore DX/DRY/DRZ sur `SYM_G`/`SYM_D` bruts. Prouvé sur le quai réduit
  (`data/examples/lot32_cl/quai_reduit_regle_cl.comm`, niveau B 80/80, exécution 42,1 s) : plus aucun
  `<F> <FACTOR_11>`, arrêt seulement sur le défaut de collision MED du lot 31, sans rapport. Ce défaut
  (`NOM_RESU_MED` absent, nom Jeveux du concept `RESULTAT` tronqué en silence à 8 caractères --
  `RESU_EAU_P`/`RESU_EAU_A` coïncidant, U7.05.21) **corrigé** : `footer()` porte
  `NOM_RESU_MED="<nom du cas>"` (≤ 8 caractères, contrôlé) par occurrence de `RESU`. La révision du
  point 3 (décision 4, méthode de jonction), déclarée au lot 31, est **close** (`lift_revision`, motif =
  correction prouvée) sans que la décision change (maillage coïncident, `LIAISON_SOLIDE` inchangés) --
  la fiche de référence n'a plus de bloqueur. Modèle complet (9 tubes) généré, validé niveau B (80/80),
  **exécuté avec succès (`DIAGNOSTIC JOB : OK`, 147,9 s, aucune alarme, aucun `<F>` dans le `.mess`)** --
  première exécution réelle du modèle complet à aboutir depuis le lot 28. Contrôles D (résultantes
  ressorts/réactions par cas, symétrie de 37 paires de nœuds d'anneau + ancrages + BOLLARD, ordres de
  grandeur du déplacement en tête d'écran sous G et Q3) : `data/examples/lot28_quai/rapports/
  controles_niveau_d_lot32.json`, informatifs, jamais un verdict (CLAUDE.md, principe 6) -- aucun niveau E.
  `.comm` généré et tableau de résultats déposés dans `/media/sf_partage/echanges/`. 2 exécutions
  Code_Aster réelles (190,0 s cumulées : quai réduit 42,1 s, modèle complet 147,9 s) ; étape 2
  (exploration libre) non nécessaire, l'étape 1 a réussi du premier coup. Limites : le mécanisme précis
  de numérotation interne de Code_Aster reste hors de portée des sept outils MCP (comme aux lots
  28/30/31) ; aucune décision pratique prise ni complétée par ce lot.
- Lot 34 (`docs/essais_lot34.md`, `data/examples/lot34_equilibre/`, `scripts/analyze_lot34_*.py`,
  `generate_lot34_sonde.py`, `report_lot34.py`) : **l'écart d'équilibre du lot 33 est expliqué et fermé.**
  Quatre causes, chacune démontrée par exécution sur le quai réduit (15 exécutions sur 20) puis corrigée :
  (1) la référence indépendante du lot 33 triait les paires `(z, p)` (rampe fictive entre couches à
  une interface dont le dessus est moins chargé) -- `profiles.layered_profile` ; (2) **Code_Aster évalue
  `FORCE_COQUE/PRES` (fonction) aux nœuds** puis interpole (fait établi nœud par nœud, non documenté :
  U4.44.01 dit « réel ou fonction ») : une marche de pression écrite en rampe de 2 mm sur une arête de
  maille déborde d'une demi-maille (G 1,2e-3, Q1 2,3e-4) -- la poussée G/Q1 est maintenant appliquée
  **par couche** (`comm.layered_pressure_load_block`, groupes `CREA_GROUP_MA/BANDE` `CRIT_NOEUD="TOUS"`,
  `VERI_NORM="NON"` car la couche de marne n'a que les trois tubes non connexes) ; (3) **`CREA_POI1` ne
  crée qu'une maille par nœud** : sur un nœud partagé par deux bandes de ressorts la 2ᵉ occurrence de
  `DISCRET` écrasait la 1ʳᵉ (43 nœuds du quai réduit, 169 du modèle complet : raideur de l'argile perdue)
  -- classes communes de raideur sommée, écrites après (`springs._combined_classes`,
  `check_spring_coverage`) ; (4) lecture : seules les composantes **réellement bloquées** entrent dans la
  somme (`SYM_G`/`SYM_D` DX ; `PIED_TUBES` DZ ; ancrages DX, DY, DZ), les réactions des composantes libres
  de `SYM` sont des forces de liaison de `LIAISON_SOLIDE` qui s'annulent sur l'ensemble des nœuds, et
  `POST_RELEVE_T/RESULTANTE` sur plusieurs groupes de nœuds **n'est pas la somme** des résultantes par
  groupe (table `REACTIONS_<cas>` du lot 33 : ne plus la lire ; toujours écrite dans le `.comm` exécuté,
  à retirer au prochain lot). `IMPR_TABLE` tronque l'intitulé à **16 caractères** (deux tables au même
  début deviennent indiscernables) et son format par défaut `E12.5` (6 chiffres) limite tout critère à
  ~1e-6 : les tables de contrôle sont imprimées en `E20.12` (le 6,07e-7 de symétrie du lot 33 n'était
  que cet arrondi). Sonde de charge assemblée (`generation.generate.EquilibriumProbe`, diagnostic seul) :
  tous les ddl bloqués, `REAC_NODA` sommé sur tous les nœuds. **Résultat sur le modèle complet, une
  exécution (208 s, aucune alarme) : équilibre X, Y, Z ≤ 9e-11, symétrie ≤ 5,7e-11 sur 20 057 paires,
  pesanteur fermée à 1e-12 : niveau C avec contrôles D, jamais E.** Le modèle a changé (ressorts aux limites
  de bande, poussée par couche) : ne pas comparer aux résultats des lots 32/33. La fiche (point 5 :
  « doublement à 1 mm sûr, aucun point d'intégration à moins de 1 mm d'une arête ») est contredite par
  l'évaluation aux nœuds -- non modifiée, à enregistrer par MM. Limites : couches non alignées sur les
  rangées de mailles (maille sans pression, signalée par l'équilibre seulement) ; cause du comportement de
  `RESULTANTE` multi-groupes non établie.

- Lot 35 (`docs/essais_lot35.md`, `data/examples/lot35_constats/`, `data/examples/lot35_synthese/`,
  `src/aster_expert/report/`, `aster_expert.meshing.normals`) : consolidation et première synthèse.
  Les quatre constats `code_aster` du lot 34 sont enregistrés avec sources d'exécution (évaluation aux
  nœuds de `FORCE_COQUE/PRES`, qui **remplace** « doublement à 1 mm sûr » au point 5 ; `CREA_POI1` une
  maille par nœud ; poutre continue et `CALCULEL2_92` ; `REAC_NODA` aux nœuds liés). La table combinée
  `REACTIONS_<cas>` n'est plus écrite. `mesh check` porte l'invariant de couche (`LayerBandsInvariant`,
  599/599 sur le maillage complet) ; les normales de chaque couche sont vérifiées explicitement sur le
  maillage relu après `ORIE_NORM_COQUE` (`IMPR_RESU/MAILLAGE`, unité 81). `aster-expert report <exécution>`
  écrit `synthese.md`, `controles.md`, `synthese.json` (cas élémentaires, aucune combinaison, aucun
  verdict) à partir des tables du `.mess`, **sans relire le MED**. Faits d'exécution à retenir : sur un
  champ de structure, `POST_RELEVE_T` s'arrête (`<POSTRELE_70>` aggravée par `DEBUT/ERREUR`,
  `<POSTRELE_38>` avec `REPERE="LOCAL"`) et `CALC_CHAMP/EFGE_NOEU` sur les tubes aussi
  (`<UTILITAI_4>`, repères locaux à 92°) : les efforts sont lus par `CREA_TABLE` (valeurs stockées ;
  `EFGE_ELNO` sans moyenne pour tubes, poutre, tirants ; `EFGE_NOEU` pour les palplanches seulement) ;
  le `TITRE` d'une table imprimée se pose sur `IMPR_TABLE` (marqueur `##<titre>ASTER`), pas sur
  `CREA_TABLE` ; `IMPR_TABLE` tronque l'intitulé à 16 caractères (`ORDRE_GRANDEUR_Q3` devient
  `ORDRE_GRANDEUR_Q`). Les tubes reçoivent `VECTEUR = (0, 0, 1)` (`x_l` vertical) : déplacements
  identiques bit à bit, avec ou sans. Contrôles de validité de la décision 5 (signe, butée, donnée
  `donnees_butee_combiwall_v1.md`) : constats sur le modèle linéaire, sans verdict ; sous G, 27 % des
  ressorts comprimés dépassent la butée fictive. **Niveau C avec contrôles D sur le modèle complet, jamais
  E** ; déplacements identiques bit à bit à ceux du lot 34. Limites : MED de résultats non relu ; pas de
  figures (`matplotlib` absent) ; moments de poutre lus pour `x_l = +X` (déduit de l'ordre des lignes).

- Lot 36 (`docs/essais_lot36.md`, `data/examples/lot36_butee/`, `résultats_MED_Paravis/`,
  `aster_expert.report.{med_read,med_source,figures,loads}`, `aster_expert.generation.terre`) :
  **diagnostic de la butée sous G** (2 413 nœuds au-delà de 100 %, taux maximal 951 %) sans
  révision de la décision 5. Vérification à la main : k/A = k_h de la couche (aire tributaire
  analytique), le taux maximal est un nœud de coin de 0,00217 m² à −12,00 (butée 47,1 kPa).
  Variante de diagnostic V1 (`generation.generate.InitialPressureDiagnostic`, jamais active par
  défaut) : pression initiale K0·σ'v côté bassin, sens établi sur le maillage orienté (faces de
  tube bassin toutes radialement sortantes, palplanches en normale +Y donc pression négative),
  résultante vérifiée à 1e-11 ; sous V1 les nœuds au-delà de 100 % passent de 2 413 à 2 141 et
  aucun nœud en traction ne dépasse la butée côté terre (3,75 % au plus en base, 7,64 % sous V1).
  V2 : deux lectures possibles, rapportées sans être départagées. **Le MED de résultats est
  désormais la source de `aster-expert report`** (`medcoupling` en conteneur, `.mess` en
  contre-vérification, 4,9e-13) : 30 champs nommés (`<cas>` + grandeur), `SIEF_ELGA` retiré (faux
  sous `ELAS_COQUE`, illisible par `MEDFileFields`), efforts généralisés et `FORC_NODA` des
  ressorts ajoutés. MEDReader (ParaVis) n'active qu'un `ComSup` par lecteur. ParaVis hors
  interface impossible (pas de serveur X virtuel) : vues 2D `matplotlib` (48 PNG). MED de
  résultats (143 Mo) et maillage dans `résultats_MED_Paravis/` (VM, ignoré par Git) ; images,
  synthèse et `LISEZMOI.md` dans `/media/sf_partage/echanges/lot36/`. 2 exécutions du modèle
  complet (627,7 s et 819,4 s), niveau C avec contrôles D sur le modèle de base, jamais E.
  Limites : filtre *Extract Group* et rendu de l'interface ParaVis non essayés ; sonde de charge
  assemblée du lot 35 réutilisée (même maillage, mêmes charges).

- Lot 37 (`docs/essais_lot37.md`, `data/examples/lot37_efforts/`, `aster_expert.report.{sections,
  section_statics}`, `scripts/generate_lot37.py`, `analyze_lot37_efforts.py`) : **corrections issues
  de la relecture du lot 36.** (1) Défaut : les tirants de bord (`TIRANT_01`, `TIRANT_09`, dans les
  plans de symétrie) portaient la section entière au lieu de la demi-section de la décision 8 ;
  corrigé (`comm._barre_keyword`), contrôle générique `comm.check_symmetry_plane_sections` (tout
  groupe linéaire dans un plan de symétrie porte A/2, sinon un motif écrit le dispense ; la poutre de
  couronnement, perpendiculaire, est dispensée), test qui échoue sur le `.comm` du lot 36. Autres
  omissions du même type : aucune dans le générateur (charges nodales de poutre aux plans déjà à
  demi-longueur, ressorts par `band_projected_width`, poids des tirants suit la section) ; une dans
  l'*outil de contrôle* (`analyze_lot34_charge_assemblee.py` pesait les tirants de bord en section
  entière, corrigé). (2) Décisions D14 (révision de la décision 4, point 3 : poutre de Timoshenko),
  D15 (domaine de validité de la décision 7, point 6), D16 (domaine de validité de la décision 5,
  point 4) enregistrées à l'identique (`arbitrage_combiwall_MM_lot37.md`, `lot37_enregistrement.json`) ;
  identifiant de la poutre de Timoshenko : **`POU_D_T`** (U3.11.01, catalogue `AFFE_MODELE`), constat
  `code_aster` du point 3 ; appliqué au générateur. Le texte de la décision 4 révisée ne mentionne plus
  le maillage coïncident ni `LIAISON_SOLIDE` (dans `decision_history`). (3) `aster-expert report`
  donne `N(z)`, `M(z)`, `T(z)` des tubes (`∫NXX ds`, `∫NXX·y ds`, `∫(NXY·y_l + QX·n)·Y ds` ; convention
  U2.01.05 ; `T` porte la part `QX`, qui domine près de la tête) et un contrôle de statique du corps
  inférieur à **−11,75 m** (première rangée sans ressort au-dessus du dragage : à −12,00 m les forces
  nodales des ressorts rendent la coupure ambiguë) : T à 0,9 %, M à 1,2-1,6 %, erreur divisée par 2 à
  4 au raffinement vertical ×2 ; MED seulement. (4) Modèle complet (430,3 s, `DIAGNOSTIC JOB : OK`) :
  tirant de bord = moitié du courant à 1e-12 sous charge uniforme, tirants 2 à 8 égaux, efforts de
  poutre nuls sous G (ils venaient du défaut), équilibre ≤ 2,8e-12, symétrie ≤ 5,2e-11 : **niveau C
  avec contrôles D, jamais E**. Limites : le tableau avant/après mêle deux changements (demi-section,
  `POU_D_T`) ; raffinement vertical seulement ; conditions de symétrie sourcées pour `POU_D_E` ;
  sonde de charge assemblée non relancée sur le modèle complet.

- Lot 39 (`docs/essais_lot39.md`, `data/examples/lot39_essais/`, `data/examples/lot39_poutre/`,
  `aster_expert.rebar.{minimum,shear,biaxial}`, `scripts/build_lot39_*.py`, `analyze_lot39_poutre.py`,
  `collect_lot39_essais.py`) : **ferraillage de la poutre de couronnement et limites de
  `CALC_FERRAILLAGE`.** Module `rebar` corrigé : un couple intérieur au domaine du béton seul donne
  zéro (ELU : `concrete_alone_moment_capacity` ; ELS : béton sans traction sous σc,lim), plus un
  défaut de profondeur d'axe neutre ELS (fraction de h prise pour une longueur). D19 (point 14 :
  axe des armatures à 0,10 m sur toutes les faces, φ équivalent 40 mm) enregistrée telle quelle ;
  6 constats d'exécution au point 14 (`lot39_essais.json`, produit par `build_lot39_constats.py`).
  Faits établis par exécution : MFZ > 0 tend AYS (+y), MFY > 0 tend AZS (+z) ; en 2D, MXX > 0 tend
  la face supérieure (DNSXS) ; flexion déviée = direction par direction puis +10 % par itération de
  Bresler (×1,1⁸ sous deux moments égaux, reproduit par `rebar.biaxial` à 1e-13) ; `AST` 1D =
  [V + T/A_k (h − t_k)]/(0,9 d fyd cot θ), **θ = 21,8°**, maximum des deux directions, pas d'acier
  longitudinal de torsion ni de critère de bielle en sortie ; **`FERR_MIN='EC2'` n'est juste qu'en
  `UNITE_CONTRAINTE='MPa'`** (en Pa : 0,0013 b d et minimum transversal ×1/1000), posé sur les
  quatre faces même sans effort ; **`FERR_MIN_FISS` refusé pour les poutres** (`<F>
  <CALCULEL7_40>`) ; ELS caractéristique 1D : écarts de −16 % à +0,25 % au pivot acier de R7.04.05
  refait à la main, cause non établie (même famille que `ssll13b` CHEFF4, 2,7 %). Poutre : 128
  sections (extrémités d'élément, non moyennées) × 14 combinaisons, schéma `ssll13*` ; 61/63
  comparaisons ELU au module à ≤ 6,5e-13, 2 échecs au bollard (moments ~1e-5 N·m, seuil absolu
  1e-12 m² écrit avant) ; le minimum 7.3.2 gouverne partout (tableau 7.2N transcrit par la session,
  à vérifier par MM ; faces AZ bornées à σs = 160 MPa). `ligne_comparaison_mm.csv` (lot 38) : une
  ligne par plan de flexion, colonnes de MM vides. ELU accidentelle : γc = 1,2, γs = 1,0
  (EN 1992-1-1, tableau 2.1N, non décidés par MM). 7 exécutions réelles (71,3 s).

## Lots 33 à 44 (résumé)

Les chemins cités dans les entrées détaillées des lots 22 à 39 sont ceux de leur
époque : depuis le lot 41, le code, les données et les scripts du quai sont dans
`projets/quai_cw_test_01/` (`generation/`, `meshing/`, `report/`, `donnees/`,
`fiche/`, `maillage/`, `scripts/`), ses constats dans
`connaissances/constats_code_aster/`.

- **Lot 33** (`docs/essais_lot33.md`) : contrôle d'équilibre honnête sur le quai ;
  paramètres hérités (`RESI_RELA`, `COEF_RIGI_DRZ`) retirés après isolation ;
  décision 13 (poussée sur la poutre) en forces nodales tributaires ; symétrie tenue,
  équilibre en échec rapporté tel quel (expliqué au lot 34).
- **Lot 34** : l'écart d'équilibre expliqué et fermé (quatre causes : tri des
  profils, évaluation de `FORCE_COQUE/PRES` aux nœuds, `CREA_POI1` une maille par
  nœud, composantes libres des nœuds liés) ; modèle complet à 1e-10 (détail
  ci-dessus).
- **Lot 35** : consolidation, `aster-expert report`, contrôles de validité de la
  décision 5 (détail ci-dessus).
- **Lot 36** : diagnostic de la butée sous G, MED de résultats lu par l'outil, vues
  2D (détail ci-dessus).
- **Lot 37** : tirants de bord à demi-section, D14 à D16, efforts d'ensemble des
  tubes (détail ci-dessus).
- **Lot 38** (`docs/essais_lot38.md`, `docs/etat_des_lieux_lot38_ferraillage.md`) :
  D14 bis, D17 (18 combinaisons : 8 ELU fondamentale, 1 accidentelle, 4 ELS
  caractéristique, 4 fréquente, 1 quasi permanente) et D18 (durabilité) enregistrées ;
  combinaisons faites dans l'outil sur les tables `EFPOUT_<cas>` (contrôle manuel à
  8,5e-22) ; état des lieux des commandes de ferraillage ; module indépendant
  `aster_expert.rebar` (ELU, ELS) calibré sur `ssll13b`/`ssll13d`.
- **Lot 39** : ferraillage de la poutre de couronnement et limites de
  `CALC_FERRAILLAGE` (détail ci-dessus).
- **Lot 40** (`docs/audit/audit_lot40.md`, lecture seule) : audit de l'outil ; la
  chaîne ne sait traiter que le quai (≈ 8 700 lignes de `src/` propres au quai,
  tout l'aval), essai dalle arrêté à la recherche documentaire ; dix
  recommandations (R1 : séparer le quai du moteur).
- **Lot 41** (`docs/essais_lot41.md`) : restructuration en tronc commun + projets
  (R1, R3, R4, R5, R7, R8 de l'audit). Déplacés vers `projets/quai_cw_test_01/` :
  `generation/` (générateur), `meshing/combiwall|normals|equilibrium`, `report/`
  (synthèse, vues ; `combinations.py` supprimé : γ/ψ lus du fichier de données),
  données, fiche, script Salomé, invariants, 41 scripts de lot et 32 fichiers de
  tests. Nouveaux modules du tronc commun : `projet` (déclaration, contrôles de
  cohérence, enchaînement `aster-expert projet`), `controles` (équilibre,
  pesanteur, symétrie), `combinaisons` (règles EN 1990 lues de la déclaration),
  `ferraillage` (1D, schéma `ssll13*`), `constats` (base, références, recherche,
  rejeu), `execution.compte_rendu` (compte rendu JSON/Markdown de chaque exécution,
  messages de `run_aster.error_messages`). Refus lisibles de `generate`, `report`,
  `mesh check`, `projet` (dont les données de dalle de l'audit). 45 constats extraits
  (`CA-001` à `CA-045`), fiche à références ; outil MCP `search_constats` ; rejeu :
  14/18 constats établis par exécution tiennent, 4 non rejouables en l'état (cas du
  lot 34 sur le quai réduit, maillage non versionné à côté du cas). Chaîne du quai
  rejouée (une exécution du modèle complet, 160 s) : toutes les valeurs identiques ;
  18 fichiers identiques à l'octet, 6 différents par des chemins/empreintes
  énumérés, 2 par des chemins non énumérés par le critère (échec formel rapporté).
  Couverture de `cli.py` : 88 %.
- **Lot 41 bis** (`docs/essais_lot41bis.md`, `docs/environnement.md`) : mise en
  conformité avec Ubuntu 26.04, qui avait retiré `python3.12` et cassé le `.venv`
  (passé à 3.14 sans paquets) et le serveur MCP. Python 3.12.14 géré par `uv`
  (`.python-version`, `python-preference = "only-managed"`), `uv.lock` aux versions
  exactes de l'ancien `.venv` ; 3.14 évalué à part (789/789 tests unitaires), non
  adopté. `aster-expert env-check` (`aster_expert.environnement`, 8 vérifications,
  première commande de chaque lot). Chaîne du quai rejouée (modèle complet 169,6 s,
  même `.comm`) : 18 identiques, 6 admis, 2 échecs formels du lot 41 inchangés et
  identiques à l'octet à leurs nouvelles références (`references/lot41bis/`) : 28/28.
  Maillages des cas de CA-029/034/035/036 versionnés : rejeu 18/18 constats, 47/47 cas.
  Trace de panne ENV-001 (`docs/environnement.md`, § 4) pour le lot 42.
- **Lot 41 ter** (`docs/publication_github.md`, `docs/cloud.md`, `docs/lots/`) :
  inventaire de publication (arbre et 65 révisions : aucun secret, aucun fichier de
  MM, normes citées par article seulement, plus gros blob 12,5 Mo ; tableau 7.2N de
  l'EN 1992-1-1 classé citation par MM), dépôt GitHub privé, branche `lot-41ter`.
  Profils `vm`/`cloud` dans `env-check` (`CLAUDE_CODE_REMOTE`), marqueurs
  `lent_aster`/`lent_salome` (`aster_expert.environnement.ressources`), `.mcp.json`
  portable par `uv run`, `scripts/cloud_setup.sh` (installation Cloud : 242 s à froid
  dans la VM sans le tirage de l'image ; crochet `SessionStart --session`),
  `aster_expert.publication` + crochet `pre-commit`. Cloud : `releases.astral.sh` à
  autoriser (Python de `uv`).
- **Lot 42** (`connaissances/LISEZMOI.md`, `docs/lots/lot42_consigne.md`) :
  capitalisation. Paquet `aster_expert.connaissances` (schémas des cinq couches
  YAML, base et confrontation des preuves au dépôt, recherche, signatures d'erreur,
  promotion, précédents proposés, rejeu des références, `rex` et métriques) ; outil
  MCP `search_connaissances` ; diagnostics dans le compte rendu de `run` ; `aster-expert
  eval candidats` (39 questions candidates du journal, à valider par MM,
  `data/evaluations/questions_candidates_lot42.jsonl`). Amorçage par le quai
  (`quai_cw_test_01.capitalisation`) : 25 diagnostics (dont ENV-001), 9 patrons, 11
  contrôles, 13 références (3 en échec rapporté tel quel), 18 précédents ; aucune
  entrée promue. Les 73 échecs archivés : 69 rattachés à 24 diagnostics (le
  diagnostic proposé automatiquement est le bon pour les 69), 4 écartés (fautes de
  frappe sur un nom de groupe). Le journal `query_log.jsonl` contient une ligne
  abîmée (octets nuls) : lue en tolérance, jamais réparée.
- **Lot 43** (`docs/essais_lot43.md`, `docs/lots/lot43_journal_autonomie.md`,
  `projets/dalle_appuyee_01/`) : second projet, dalle C30/37 6 × 4 × 0,30 m appuyée sur
  quatre côtés, menée pour mesurer l'autonomie de l'outil. Phase 1 : fiche proposée,
  arrêt pour arbitrage. Phase 2 : arbitrage de MM (`arbitrage_dalle_appuyee_01_v1`,
  nouvelle origine `arbitrage_mm`) et complément ELS. DKT, appui bilatéral, dalle
  entière. Tronc commun : ferraillage 2D des plaques (`aster_expert.ferraillage.plaque`,
  `rebar.plates`), γG favorable facultatif, alias de projet par `structure`.
  **Niveau E** (Navier, 16,8 millions de termes, Lévy à 1e-14) : erreur au centre
  divisée par 4 à chaque raffinement, 0,05 % au plus sur 48×32 ; contrôles D à 1e-12.
  Le minimum EN 1992 (3,80 cm²/m) gouverne le ferraillage. Échec F4 rapporté :
  les densités ELS 2D de `CALC_FERRAILLAGE` dépendent de `SIGC_*_ELS` (CA-052).
  Connaissances : CA-046 à CA-052, REF-014, PAT-010, PAT-011, CTL-012, PRE-022 à
  PRE-031 (PRE-021 laissé libre, cité par MM) ; réutilisations de PAT-008, PAT-009,
  CTL-005, CTL-006, CTL-008, CTL-010, PRE-016, PRE-018 ; aucune promotion.
  Interventions de MM : 2.
- **Lot 44** (`docs/lots/lot44_consigne.md`) : consolidation après le second ouvrage,
  aucun nouveau calcul d'ouvrage. Catégorie `choix_agent` (rejeu sur la fiche de la
  phase 1 de la dalle : 31 bloqueurs → 19) ; détection des paramètres obligatoires
  (`aster_expert.agent.obligatoires`, les quatre paramètres ELS du lot 43 retrouvés ;
  CA-053) ; `projet creer` ; `get_command_schema` filtré (`DEFI_MATERIAU`/`ELAS` : 719 340
  → 3 686 caractères) ; règle de promotion corrigée (CTL-005, CTL-006, CTL-012, PAT-011,
  REF-014 promus ; CA-025, CA-041 et 7 autres deviennent inéligibles) ; métriques
  développement/vérification (quai : 41,2 % sur 177 exécutions de développement, contre
  38,4 % de référence ; seuil des candidats patrons 0,40) ; D20, D21 (PRE-019, PRE-020),
  Es = 200 GPa pour la dalle (ELS QP +6,6 % au plus, ferraillage retenu inchangé),
  ANO-001 (CA-052 + REF-012) ; banc : 22 questions versées (87 au total), aiguillage et
  reformulation dans le skill `code-aster-expert`.

- **Lot 45, partie A** (VM, `docs/lots/lot45_consigne.md`) : paquets de résultats
  (`aster_expert.projet.paquet`) du quai (74 fichiers, 10,6 Mo, niveau D) et de la
  dalle (9 fichiers, 60 ko, niveau D). `controles_d.json` porte désormais les
  empreintes du `.mess` et du `.comm` contrôlés (`provenance`) : sans elles, le
  niveau D n'est pas reconnu par le paquet. Dalle : le niveau E du lot 43 n'est pas
  reporté sur l'exécution du lot 44 (`.comm` différent : un commentaire et `EYS`
  des quatre `CALC_FERRAILLAGE`, listés dans `niveau_e.difference_comm`). Quai : le
  `.comm` régénéré ne diffère de l'exécuté que par l'empreinte de la fiche en
  en-tête (`regeneration_comm.difference`).

- **Lot 45, partie B** (Cloud, `docs/essais_lot45.md`, `docs/lots/lot45_consigne.md`) :
  notes Word génériques. `aster-expert note hypotheses|resultats|controler <projet>`
  (`aster_expert.notes`) : Arial 10, texte noir, en-têtes de tableaux sur fond gris
  `D9D9D9`, titres numérotés ; le contenu vient entièrement de la fiche, des données,
  de la convention de nommage et du paquet de résultats (jamais d'un texte écrit à
  la main ; un marqueur cité par la fiche, `[À CONFIRMER MM]`, est montré entre
  guillemets). Les tableaux et figures de la note de résultats sont **déclarés dans
  `projet.yaml`** (`results_package.note_tables`, `note_figures`) ; les sections
  affichées suivent le contenu du paquet. Contrôle automatique relu dans le `.docx`
  (points, valeurs, textes mot pour mot, marqueurs, police, taille, couleur, fond
  gris), éprouvé par altération du fichier. Livrables versionnés :
  `projets/<projet>/livrables/notes/` (`scripts/build_lot45_notes.py`). **Règle de
  conservation d'un niveau** (paquet) : un niveau reste acquis pour un `.comm`
  identique hors commentaires et en-tête (`normalize_comm`), sinon il est rejoué avec
  les critères d'origine ; critères commités après l'exécution ou avec des
  résultats : signalés (`anteriorite_demontrable`) ; `projet exporter-resultats
  --reevaluer` ré-applique tout cela à un paquet existant sans archive (Cloud).
  Dalle : E0, E1, E2 rejoués sur le `.comm` actuel (EYS = 200 GPa, maillages
  versionnés, critères du lot 43), niveau E acquis. Décisions : D20 et D21 au texte de
  MM (PRE-019, PRE-020), D21 s'applique à la dalle (P6 révisée, PRE-030), Es = 200 GPa
  pour tous les projets, **en attente d'application au quai** (PRE-032, déclarée « en
  révision » : bloqueur de génération visible, le quai garde 210 GPa). `FERR_MIN`
  n'est demandé qu'avec `UNITE_CONTRAINTE='MPa'` (`aster_expert.ferraillage.unites`,
  CA-041) ; signalement factuel : `docs/signalements/ferr_min_unite_contrainte.md`.
  Piège : dans le Cloud, une exécution crée `data/processed/runs/` ; les tests qui
  prennent ce répertoire pour l'archive complète du quai (`rex`, `connaissances
  verifier`, `test_capitalisation_lot42`) échouent ensuite : lancer `pytest -m
  lent_aster` en dernier, comme le veut l'ordre des contrôles.

## Périmètre à ne pas dépasser sans instruction

Une session traite un lot et un seul. Ne pas anticiper les lots suivants, ne
pas installer d'infrastructure non demandée, ne pas inventer la structure d'un
dépôt externe avant de l'avoir inspectée.

## État de la fiche combi-wall (lots 19-24)

- `data/examples/hypotheses_combiwall_reference_arbitree.json` est produit par
  `scripts/build_combiwall_reference.py` à partir des entrées versionnées de
  `data/examples/combiwall_inputs/` (arbitrages MM v2 et v3, extraits et
  recherches du lot 20). Ne jamais éditer ce JSON à la main : modifier les
  entrées puis relancer le script ; un test rejoue le script et compare
  octet pour octet.
- Une révision de décision passe par `record_practice_decision` (la décision
  précédente va dans `decision_history`, jamais modifiée).
- Une source `norme` datée d'un mois seulement ne peut porter de `date` (le
  schéma exige une date complète) : `date=None`, le mois reste dans
  `reference`. Ne jamais inventer un jour.
- `HypothesesSheet.group_naming_gaps()` : chaque groupe porte le
  `point_label` du point qui le fonde ; le contrôle signale un point absent
  ou portant une entrée pratique non tranchée. Il signale, il ne corrige pas.
- Point 1 (coque du tube) : la documentation U2.02.01 ne départage pas DKT et
  COQUE_3D, l'ensemble recevable est un constat `code_aster`, le choix est une
  entrée pratique ouverte. Aucun critère chiffré de facettisation n'existe
  dans la documentation. Étude de la palplanche : `docs/etude_lot20_coque_orthotrope.md`.
- Une entrée `code_aster` non tranchée ne peut pas porter d'option retenue ;
  un ensemble d'options recevables se consigne dans une entrée tranchée qui
  le dit, plus une entrée pratique ouverte du même `point_label`.
- Lot 21 : le point 1 (tube) est tranché par MM en DKT facettisé
  (`arbitrage_combiwall_MM_lot21.md`, recopié à l'identique) ; l'entrée porte
  `options_considered = (DKT, COQUE_3D)`, paramètre optionnel de
  `record_unfounded_point`. Le point non fondé de la raideur surfacique (point 4)
  est remplacé par un constat `code_aster` (chaîne CREA_POI1 → DIS_T → DISCRET
  K_T_D_N) ; la trace de recherche de l'ancien point reste dans les `notes` du
  constat. Il n'y avait alors plus d'entrée non tranchée : cela ne disait rien de
  ce que la fiche ne portait pas encore (option orthotrope de la palplanche, à
  enregistrer avec ses coefficients).
- `ELAS_COQUE` : `docs/etude_lot21_elas_coque.md` (niveau A, avec mise à jour du
  lot 22). Établi au lot 22 par exécution (`docs/essais_lot22.md`) : `FLEX_*` par
  unité de largeur, L = axe x_l du repère utilisateur ; sous `PESANTEUR` statique
  le poids vaut `RHO` × `EPAIS` × g (RHO agit en masse **volumique**, contre le
  libellé de U4.43.01) et `PESANTEUR` exige `RHO` sur tous les éléments
  `ELAS_COQUE` du modèle, même restreinte par `GROUP_MA` ; `REAC_NODA` est faux
  sous `ELAS_COQUE` quand FLEX ≠ MEMB × EPAIS²/12 (déduction : ne pas lire de
  réaction sans contrôle d'équilibre) ; le groupe `MEMB_LT` … `CISA_T` est
  indissociable (`checkCommandSyntax`, niveau B).
- Essai d'exécution `FORCE_COQUE` (`docs/essai_lot21_force_coque.md`, niveau C,
  D pour cet essai) : l'intensité se rapporte à la surface **développée** des
  mailles (résultante 2,22982 pour 2,229823 m² de facettes, contre 1,42 m²
  projetés). Le modèle est produit par `scripts/build_fcoque_essai.py` (maillage
  au format ASTER natif). Enregistré au lot 22 au point 8 avec sa source d'exécution.
- Lot 22, source d'exécution : `ExecutionSource` est le troisième membre de
  `CodeAsterSource`. Admise **uniquement** sur les constats `code_aster`
  (`PracticeHypothesisEntry.sources` est typé `PracticeSource`, elle y est
  refusée). Champs : version, digest d'image, commit du dépôt et arbre modifié
  ou non, chemin versionné du cas et son `case_sha256`, listing versionné,
  grandeur, valeur obtenue, référence, valeur de référence, écart relatif
  (recalculé par le modèle, refusé s'il diverge), niveau **C ou D** (jamais
  plus). Le chemin et l'empreinte sont confrontés au dépôt par
  `record_execution_finding`, jamais à la lecture du modèle ; un test le fait
  pour toute la fiche. Une exécution en échec est de niveau B : elle se rapporte
  dans les `notes`, elle n'est pas une source. Écriture : `lot22_essais.json` +
  `scripts/build_combiwall_reference.py` ; jamais à la main.
- Lot 22, « en révision » : `declare_under_revision` / `lift_revision` (journal
  `revision_history`, `RevisionEvent` : motif obligatoire, auteur, date, alternance
  `declared`/`lifted`). Une entrée pratique en révision est un bloqueur de
  génération ; une nouvelle `record_practice_decision` clôt la révision. Refusé
  sur une entrée non tranchée. Lot 23 : `arbitrage_combiwall_MM_v4.md` et
  `cas_test_quai_combiwall_v3_delta.md` sont recopiés à l'identique dans
  `combiwall_inputs/` ; ne restent que la phrase de statut de v4 qui cite le
  marqueur (le test la retire avant de chercher `À CONFIRMER`). Les décisions 8
  (point 7) et 9 (point 8) sont enregistrées (`_record_decisions(..., only=...)`) ;
  la décision 9 a clos la révision du point 8 (`declared` lot 22, `lifted` par MM).
  **La décision 2 (point 1, homogénéisation) n'est pas enregistrée** : elle reste
  la seule entrée en révision, son motif (`lot22_essais.json`, `revisions`) cite le
  poids propre (`RHO` exigé, compté dans `EPAIS`) et l'anomalie de post-traitement ;
  elle sera réécrite après le lot 23. `decided_at` de v4 (2026-09-22 18:00) est
  l'heure conventionnelle de MM, postérieure à la date de session.
- Lot 23 (`docs/essais_lot23.md`, niveau C/D, `data/examples/lot23_essais/`,
  `scripts/build_lot23_essais.py` et `analyze_lot23_essais.py`, entrées
  `lot23_essais.json`, `lot23_extraits.json`) : sous `ELAS_COQUE` (DKT) les efforts
  généralisés `EFGE_ELNO`/`EFGE_NOEU` sont **exacts** et indépendants de `EPAIS` et de
  `CISA_*` ; `SIEF_ELGA` (contraintes `SIXX…` à 3 sous-points en 17.4.0, non des
  efforts généralisés), `FORC_NODA` et `REAC_NODA` sont faux quand
  `FLEX ≠ MEMB × EPAIS²/12`, proportionnels à `EPAIS²` (hypothèse du lot 22
  confirmée). Ne jamais lire de réaction ni de contrainte sous `ELAS_COQUE` : lire
  `EFGE_NOEU`. Contrôle d'équilibre : forces des ressorts discrets (`FORC_NODA`
  restreint aux `POI1`) ou `REAC_NODA` sur des nœuds d'appui sans `ELAS_COQUE` ; la
  somme de `REAC_NODA` sur tout le modèle est juste et ne discrimine rien. `RHO = 0`
  sur `ELAS_COQUE` : poids nul **sans alarme**. U4.43.01 (« masse par unité de
  surface ») contredit R3.07.03 (masse volumique) ; l'exécution suit R3.07.03.
  Non testés : membrane, `MYY`, `MXY`, `QY`, `SIGM_ELNO`, COQUE_3D, DST, TRIA3.
- Une valeur d'`ExecutionSource` doit être imprimée dans son listing versionné
  (test) : pas de grandeur dérivée comme source, elle va dans `analyse.json` et les
  notes.
- Outils MCP : le serveur attaché à une session peut précéder le code
  (`search_test_cases`/`read_test_case` absents) ; se reconnecter (`/mcp`), à
  défaut passer par un client MCP stdio sur un serveur neuf.
- Ressorts nodaux (point 4, exécuté au lot 22, niveau D) : regrouper les nœuds de
  même raideur (mêmes `VALE`) dans un même groupe `POI1`, une occurrence de
  `CREA_POI1` et de `DISCRET` par classe de raideur, jamais par nœud. Tolérance de
  comparaison de deux raideurs (maillage irrégulier) non établie.
- Cas tests : toute lecture passe par les outils MCP `search_test_cases` et
  `read_test_case` (journalisés, au commit de `codeaster-src` du manifeste, refus
  hors corpus). Jamais `cat`/`grep`/lecture directe de `external/codeaster-src/astest`.
- Chaîne d'exécution : un cas avec maillage exige un `.export` (seul un `.export`
  fait copier les fichiers `<nom>.*` voisins) et sa racine dans
  `execution.allowed_roots`. Les listes de noms d'un maillage ASTER se répartissent
  sur plusieurs lignes.
- Lot 24 (`docs/essais_lot24.md`, niveau C/D, `data/examples/lot24_essais/`,
  `scripts/build_lot24_essais.py` et `analyze_lot24_essais.py`, entrées
  `lot24_essais.json`, `lot24_enregistrement.json`) : plaque carrée DKT en quadrangles
  avec les coefficients de la décision 2 v5 (L = axe Y du maillage, `ANGL_REP = (90, 0)`).
  Membrane selon T, flexion cylindrique selon T et cisaillement de membrane sont exacts
  en déplacements et en `EFGE_NOEU`, aux erreurs de discrétisation près (flèche −1,25 %
  en 8 × 8, −0,3125 % en 16 × 16 ; `QY` des nœuds d'appui = valeur constante de l'élément
  adjacent). `REAC_NODA` : exact en membrane, faux en flexion (bord d'appui 6,255 N pour
  50 N, valeur proche de la part nodale de la charge : déduction) ; la somme reste
  exacte. Non testés : torsion (`FLEX_G_LT`, `MXY`), `MEMB_L` seule, couplages,
  superposition, plan de plaque vertical (`ANGL_REP` hors plan XY non établi).
- Lot 24, décision 2 v5 (`arbitrage_combiwall_MM_v5_decision2.md`, recopié à
  l'identique) : enregistrée, révision du point 1 close (`lifted`), plus aucun
  bloqueur de génération. MM n'a écrit ni date ni heure : `decided_at` est l'heure de
  l'enregistrement (2026-09-21T08:27:13-04:00, `lot24_enregistrement.json`), antérieure à
  l'heure conventionnelle des décisions 8 et 9 de la v4. Le constat des efforts
  généralisés du point 1 remplace celui du lot 23 (sources conservées). L'absence de
  bloqueur ne dit pas que le domaine de validité est satisfait : l'étude de
  sensibilité de la membrane horizontale (×10 et ÷10) reste requise et non faite.
  `group_naming_gaps()` signalait `EPAIS` et `EFGE_NOEU` (faux positifs : mots-clés
  entre apostrophes inverses lus comme groupes) ; corrigé au lot 25 (ci-dessous).
- Lot 25 (`docs/essais_lot25.md`, `docs/inventaire_lot25.md`) : `HypothesesSheet.
  group_naming_gaps(catalogue_identifiers)` reçoit le vocabulaire du catalogue
  (`aster_expert.catalogue.query.catalogue_vocabulary` : commandes, mots-clés,
  valeurs permises) et ne lit plus un identifiant du catalogue comme un groupe ;
  sans vocabulaire, les deux faux positifs réapparaissent (l'appelant le fournit, le
  module ne dépend pas du catalogue). Décision de MM du point 9 (repère global :
  X le long du quai de `SYM_G` vers `SYM_D`, Y vers la terre, Z ascendant, origine
  dans l'axe de `TUBE_05` à la cote 0,00 CM, palplanche dans le plan Y = 0, unités
  m, N, Pa, kg) enregistrée par `insert_practice_entry`, telle que rédigée
  (`arbitrage_combiwall_MM_lot25_repere.md` ; `decided_at` = heure d'enregistrement,
  `lot25_enregistrement.json`). Ne pas confondre avec la « décision 9 » de la v4
  (point 8).
- Lot 25, essai D7 (niveau C/D, `data/examples/lot25_essais/`,
  `scripts/build_lot25_essais.py` et `analyze_lot25_essais.py`, entrées
  `lot25_essais.json`, `lot25_extraits.json`) : pour une plaque dans le plan XZ,
  `VECTEUR = (0, 0, 1)` place L (`x_l`) selon Z et T selon X ; `VECTEUR = (1, 0, 0)`
  place L selon X ; `ANGL_REP = (0, -90)` équivaut à `VECTEUR = (0, 0, 1)`. Flexion
  selon `x_l` en `MXX`, selon `y_l` en `MYY` (`EFGE_NOEU`). **Critère 2 du rapport en
  échec, rapporté tel quel** : l'erreur de flèche ne décroît pas avec le raffinement
  (elle est ≤ 5e-8 : grandeur reproduite à la précision du solveur, classée à tort
  sensible à la discrétisation) ; les critères 1, 3 et 4 sont satisfaits. Le
  constat est enregistré au point 1 (7 sources d'exécution) avec cet échec dans ses
  notes. Non testés : plans autres que XZ, normale opposée, TRIA3, DST, COQUE_3D.
- Lot 25, données chiffrées : `data/examples/combiwall_model_data.yaml`, schéma
  `aster_expert.agent.model_data` (valeur, unité, source, commentaire ; valeurs dans
  l'unité de leur source, jamais converties ni calculées). 108 valeurs, 86 fournies,
  22 « à fournir » (profils de poussée et de pression d'eau du point 5, cotes de tête,
  propriétés du tube, du béton et du tirant, position de l'axe de la poutre,
  accrochage des tirants, pesanteur, discrétisation). Une valeur « à fournir » bloque :
  `HypothesesSheet.generation_blockers(model_data)` la signale (sans argument,
  seule la fiche est examinée : elle est prête, le fichier de données ne l'est pas).
  `check_consistency` confronte chaque valeur fournie à son texte source
  (0 écart) ; il signale, il ne corrige pas. Ne jamais compléter une valeur « à
  fournir » sans source : la demander à MM. Le cas de test complet vit dans
  `combiwall_inputs/cas_test_quai_combiwall_v2.md` (v3 = v2 + delta).
- Salomé (état au lot 25, `docs/inventaire_lot25.md` §3) : pas d'installation native ;
  Salomé-Méca V2024.1.0 en conteneur Singularity (`~/Desktop/salome_meca.sif`,
  Python 3.9) ; `salome -t --shutdown-servers=1 script.py` exécute GEOM + SMESH sans
  interface (vérifié) ; l'image Docker de `cave` ne contient pas Salomé mais
  `medcoupling` et `MEDLoader` (Python 3.11). Le Python du projet n'a aucun module
  MED. Ne pas lancer le lanceur `salome_meca` sans nécessité : son premier démarrage
  écrit une configuration.
