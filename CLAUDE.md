TOUTE PRODUCTION DE CE DÉPÔT EST EN FRANÇAIS : RÉPONSES DANS LE TERMINAL, Y
COMPRIS LE RÉSUMÉ FINAL, COMPTES RENDUS, MESSAGES DE COMMIT, RAPPORTS,
COMMENTAIRES DE CODE. CETTE RÈGLE A DÉJÀ DÛ ÊTRE RAPPELÉE EN TÊTE DE FICHIER
DEUX FOIS (LOTS 30 ET 32) PARCE QUE DES RAPPELS PLUS BAS DANS LE DOCUMENT
N'AVAIENT PAS SUFFI À LA FAIRE RESPECTER (COMPTES RENDUS DES LOTS 29 ET 31
RÉDIGÉS EN ANGLAIS) : NE PAS LA REDÉPLACER PLUS BAS.

# AsterExpert

## Langue de travail (lire en premier)
**Toute production de ce dépôt est en français** : comptes rendus au fil de la session, messages de commit, rapports d'essai (`docs/essais_lotXX.md`),
commentaires techniques, noms de sections. Le code Python (identifiants, docstrings) reste en anglais — voir la section « Langue » ci-dessous, qui ne
fait que détailler cette règle. Cette règle a déjà dû être rappelée en tête de fichier une fois (lot 30) parce qu'un rappel plus bas dans le document
n'avait pas suffi à la faire respecter : ne pas la redéplacer plus bas.

## Organisation du dépôt (lot 41) — lire en second
**Tout code propre à un ouvrage va dans `projets/<nom>/`, jamais dans `src/`.**

- `src/aster_expert/` est le **tronc commun** : ce qui vaut pour tout ouvrage (catalogue et validation B, recherche documentaire et cas tests,
  exécution et compte rendu, schéma de fiche et arbitrage, données structurées, exécution Salomé et vérificateur de maillage, contrôles D paramétrés,
  lecture MED, combinaisons, ferraillage 1D et module EN 1992, base de constats, déclaration et enchaînement des projets). Un test
  (`tests/unit/test_tronc_commun_sans_ouvrage.py`) échoue si `src/` nomme un groupe, un cas, une donnée ou le nom d'un ouvrage.
- Un ouvrage est un **projet** : `projets/<nom>/`, paquet Python importé depuis `projets/` (fiche, données et sources, script Salomé et invariants,
  générateur ou `.comm`, extensions, scripts de lot, tests, résultats de référence) et sa **déclaration** `projet.yaml` (schéma
  `aster_expert.projet.declaration`), seule interface avec le tronc commun. Le code propre à un projet peut être écrit par une session d'agent pour ce
  projet ; le tronc commun garantit la vérification (validation B, invariants de maillage, contrôles D, niveau atteint).
- Un fait établi sur Code_Aster va dans la **base de constats** `connaissances/constats_code_aster/CA-nnn.json` (un fichier par constat), jamais
  recopié dans une fiche : la fiche le référence (`{"nature": "constat", "constat_id": "CA-nnn", "point_label": ...}`).
- Enchaînement : `aster-expert projet <nom> <étape>` (verifier, maillage, generer, valider, executer, controles, synthese, combinaisons, ferraillage,
  tout). Les sorties vont dans `projets/<nom>/resultats/` (non versionné, `etat.json`), sauf `resultats/paquet/` (lot 45), **versionné** :
  `aster-expert projet exporter-resultats <nom>` y copie ce que déclare `results_package` dans `projet.yaml` (CSV, JSON, PNG, TXT ; jamais de MED ; 20
  Mo au plus) et écrit `paquet.json` (empreintes, cohérences, régénération du `.comm`, commits des critères, niveau atteint niveau par niveau). C'est
  la seule source de résultats d'une session Cloud.
- Premier projet : `projets/quai_cw_test_01/` (quai combi-wall). Les répertoires `data/examples/lotNN_*` restent les archives des essais des lots.

## Environnement : Python du projet (lot 41 bis) — lire en troisième
**Ne jamais dépendre du Python du système ; tout passe par le `.venv` du projet.** Le passage d'Ubuntu 24.04 à 26.04 a retiré `python3.12` et cassé le
`.venv` (`docs/environnement.md`, § 4). Depuis le lot 41 bis :
- la version de Python est fixée par `.python-version` (3.12) et installée par `uv` dans l'espace utilisateur (`~/.local/share/uv/python/`), jamais
  par `apt` ni `sudo` ; `[tool.uv] python-preference = "only-managed"` interdit à `uv` de choisir un Python du système ;
- les dépendances sont verrouillées dans `uv.lock` (versionné) : reconstruire par `uv sync --locked --all-extras`, jamais par `pip install` ; mettre à
  jour une dépendance est un changement délibéré, commité avec sa justification ;
- toute commande passe par `.venv/bin/…` (`aster-expert`, `pytest`, `ruff`, `mypy`), jamais par `python3` du système ;
- **`aster-expert env-check` est la première commande de chaque lot**, avant `mcp-check` : Python du `.venv` contre `.python-version`, dépendances
  contre `uv.lock`, Docker, `cave`, digest de l'image, Singularity et image Salomé, dossier partagé, exécutable du serveur MCP ; arrêt au premier
  écart. Si `aster-expert` lui-même ne démarre pas (`.venv` cassé), lancer `uv sync --locked --all-extras` puis `env-check` ;
- un écart de Docker, de Singularity ou du montage du partage ne se corrige jamais par la session (`sudo` exclu) : la session s'arrête et décrit à MM
  ce qu'il faut faire ;
- le passage à une autre version de Python (3.14 évaluée au lot 41 bis) est un lot à part, délibéré et testé.

## GitHub, branches et Cloud (lot 41 ter) — lire en quatrième
Le dépôt est hébergé sur un dépôt GitHub **privé** (`aster-expert`, `docs/publication_github.md`) ; une session peut tourner dans la VM ou dans le
Cloud de Claude Code (`docs/cloud.md`).

- **Un lot, une branche** `lot-NN` (`lot-41ter`, `lot-42`…), poussée sur GitHub avec le commit du lot. **MM fusionne dans `main`** après relecture du
  compte rendu ; une session ne fusionne pas et ne pousse jamais directement sur `main` (dans le Cloud, le proxy GitHub n'autorise de toute façon que
  la branche de travail de la session).
- **En tête de lot, la session annonce son profil** (`vm` ou `cloud`), lu sur la première ligne de `aster-expert env-check`. Un lot qui exige Salomé
  (maillage, `pytest -m lent_salome`) ou le dossier partagé ne se lance que dans la VM ; dans le Cloud, leur absence est attendue et `env-check` la
  signale comme telle.
- **Rien de ce qu'interdit `docs/publication_github.md` n'est jamais ajouté** : secrets, fichiers de MM (`calcul_3d_*`, données PANG), texte d'une
  norme AFNOR (citer l'article, ne pas verser le texte), fichiers de plus de 50 Mo. Garde-fous : `config/publication.yaml`, crochet
  `scripts/git-hooks/pre-commit` (à activer une fois par clone : `git config core.hooksPath scripts/git-hooks` ; le script Cloud le fait) et
  `tests/unit/test_publication.py`. Ne jamais contourner le crochet (`--no-verify`).
- **Intégration continue (lot 46)** : `.github/workflows/ci.yml` (pull request, envoi sur `main`, `lot-*` et `claude/**` : `uv sync --locked`, `ruff`,
  `mypy src` et `mypy`, `pytest` hors tests lents, contrôle de publication, `pip-audit` non bloquant) ; `.github/workflows/ci-lent.yml` (à la demande et sur tout envoi touchant `execution/`, `validation/`, `connaissances/` : `pytest -m lent_aster` puis le rejeu des références, image tirée par digest). **MM ne fusionne une branche dans `main` que si l'intégration continue est verte** ; une session
  ne déclare pas un lot terminé tant que le passage de sa branche n'est pas vert (ou qu'elle n'a pas dit à MM comment le vérifier).
- `/media/sf_partage` reste la zone d'échange avec MM pour les livrables lourds (VM seulement). Les consignes et comptes rendus de lot peuvent vivre
  dans `docs/lots/`.
- `.mcp.json` lance le serveur par `uv run --project ${CLAUDE_PROJECT_DIR:-.} --locked --all-extras` : aucun chemin propre à une machine.

## Base de connaissances et retour d'expérience (lot 42) — lire en cinquième
**Chaque projet rend l'outil meilleur** : ce qu'il apprend est écrit dans `connaissances/` (six couches, `connaissances/LISEZMOI.md`), consulté avant
d'agir et protégé par des tests.

- Couches : `constats_code_aster/` (CA-nnn), `diagnostics/` (DIAG-nnn, ENV-nnn : signature d'erreur, cause, correction), `patrons/` (PAT-nnn),
  `controles/` (CTL-nnn), `references_validation/` (REF-nnn), `precedents/` (PRE-nnn). Schémas : `aster_expert.connaissances.modeles` ; aucune entrée
  sans preuve ; contrôle par `aster-expert connaissances verifier`.
- Statuts : `observé`, `établi` (preuve rejouable : cas versionné ou test), `promu` (deux projets ou niveau E), seulement par `aster-expert
  connaissances promouvoir <id>`, qui vérifie les conditions. Aucune promotion automatique.
- **Consultation obligatoire** (`search_connaissances`, skill `code-aster-expert` § 6 quater) : avant d'écrire une commande (constats, patrons) ; dès
  qu'une erreur ou une alarme apparaît dans un `.mess` (diagnostics, avant toute autre hypothèse ; `aster-expert run` les affiche pour un échec) ;
  avant de proposer une décision pratique (précédents) ; avant d'écrire un contrôle (contrôles).
- **Un précédent n'est jamais appliqué** : il se propose (`aster-expert connaissances proposer-precedent`, entrée non tranchée, origine
  `precedent_projet`) et MM arbitre.
- **Tout lot se termine par `aster-expert rex <projet>`, et le compte rendu inclut sa sortie.** Un échec d'exécution non classé (registre
  `connaissances/rex/<projet>.yaml` : rattaché à un diagnostic, nouveau diagnostic, ou écarté avec un motif) bloque la clôture du lot. Le compte rendu
  déclare les interventions de MM et les connaissances qui ont évité une erreur (champ `lots` du registre), à partir du lot 43.

## Fiche : les choix de l'agent, la promotion, la naissance d'un projet (lot 44) — lire en sixième
**Règle de partage.** Une fiche a trois catégories d'entrées : les faits Code_Aster (`code_aster`, sourcés), les décisions de MM (`pratique`, origine
`arbitrage_mm`, `decision_ingenieur`…) et, depuis le lot 44, les **choix de l'agent** (origine `choix_agent`,
`aster_expert.agent.arbitration.record_agent_choice`).

- **Relève de `choix_agent`** (et seulement cela, `AgentChoiceDomain`) : noms de groupes ; repère, origine et unités ; type et taille des mailles ;
  suite de convergence ; lecture des champs (`NOEU`/`ELNO`) ; blocage isostatique des mouvements de corps rigide ; étendue du modèle quand la symétrie
  est contrôlée.
- **Reste à MM** ce qui engage l'ouvrage : matériaux, actions, combinaisons, durabilité, conditions d'appui physiques, paramètres de ferraillage,
  choix d'une modélisation qui change la physique représentée.
- Un `choix_agent` nomme ses vérificateurs (`verified_by` : `CTL-nnn`, `REF-nnn` ou `projet:<nom>`) ; sans eux, ou hors des domaines ci-dessus, le
  schéma le refuse. Il est tranché (ne bloque pas la génération) et figure dans une section séparée du document d'arbitrage, où MM peut le remplacer
  (`record_practice_decision`, le choix de l'agent passe dans `decision_history`). Une question qui mêle les deux catégories se scinde. Détail : skill
  `hypotheses-drafting`, § 2 bis.
- **Paramètres obligatoires** : la fiche déclare les commandes qu'elle prévoit (`planned_commands`) ; `aster-expert fiche obligatoires` lit les
  mots-clés obligatoires de la combinaison d'options (catalogue **et** `data/config/obligations_execution.yaml` : le catalogue 17.4 déclare `optional`
  des mots-clés que `CALC_FERRAILLAGE` exige à l'exécution, CA-053) et ajoute une question par mot-clé non couvert.
- **Promotion** : une réutilisation ne compte que si le projet a **éprouvé** l'entrée (exécution réussie ou test versionné,
  `connaissances.modeles.is_proof`) ; une citation dans une fiche, une décision, un document ou du code n'est pas une épreuve. Épreuves d'un constat :
  `connaissances/epreuves_constats.yaml`. Rejeu : `aster-expert connaissances eligibilite`.
- **Naissance d'un projet** : `aster-expert projet creer <nom>` (arborescence, `projet.yaml` minimal, racines d'exécution, registre `rex`).
- **Métriques** : `rex` sépare les exécutions de **développement** et de **vérification** (lancée par une commande de rejeu --
  `ASTER_EXPERT_RUN_ORIGIN` dans le compte rendu -- ou rejeu d'un `.comm` déjà réussi, même empreinte) ; le taux d'échec porte sur le développement
  seul.
- **Anomalies ouvertes** : `connaissances/anomalies_ouvertes.yaml` (ANO-nnn) relie des entrées qui portent peut-être une même cause, sans rien
  conclure.

## Mission
Construire un agent expert Code_Aster versionné, traçable, capable de valider les fichiers qu'il produit.

Le système ne doit jamais confondre :
- pertinence documentaire ;
- validité syntaxique vis-à-vis du catalogue ;
- réussite d'exécution ;
- validité physique ;
- validation par comparaison à une référence.

## Environnement d'exécution
Le dépôt vit dans une machine virtuelle Ubuntu 26.04 (Oracle VirtualBox ; 24.04 jusqu'au 2026-09-30, voir `docs/environnement.md`). Code_Aster n'y est
pas installé nativement : il s'exécute dans un conteneur Docker (image `simvia/code_aster`), géré par l'outil tiers `cave`. Le développement et
l'indexation ont lieu dans la VM ; l'introspection du catalogue et l'exécution de calculs ont lieu à l'intérieur du conteneur, jamais par
sous-processus natif de la VM. L'hôte (hors VM) ne sert qu'à l'édition (VSCode en Remote-SSH) et ne dispose ni de Docker ni de Code_Aster.

Deux interpréteurs Python coexistent et ne doivent jamais être confondus :
- le Python du projet (`.venv`, Python 3.12 géré par `uv`, jamais celui du système), dans la VM, qui exécute `aster_expert` ;
- le Python de l'installation Code_Aster, à l'intérieur du conteneur, seul capable d'importer `code_aster` et son catalogue.

Le Python du projet n'importe jamais `code_aster`. Toute introspection du catalogue passe par un script autonome, copié dans un répertoire de travail
dédié puis exécuté par le Python d'Aster à l'intérieur d'un conteneur restreint (réseau désactivé, utilisateur non root, limites de ressources), qui
produit du JSON sur la sortie standard. Voir `docs/architecture.md`, décisions ADR-002, ADR-003 et ADR-006.

## Principes fondamentaux
1. Ne jamais mélanger silencieusement plusieurs versions de Code_Aster.
2. La version cible est résolue à partir de l'installation réelle, jamais supposée. Si elle est inconnue, l'exécution s'arrête avec un message
   explicite.
3. La syntaxe officielle provient du catalogue de la version installée, pas des manuels. Les manuels U/R/V documentent la sémantique, la théorie et
   les cas d'emploi.
4. Toute donnée indexée conserve sa source, son chemin, sa révision Git et sa version documentaire.
5. Les cas tests sont des références exécutables, pas des modèles transposables. Toute réutilisation exige la comparaison de la modélisation, des
   éléments, de la loi de comportement, des chargements, des conditions aux limites, du type d'analyse et de la version.
6. Toute réponse distingue faits documentés, déductions et recommandations.
7. Un calcul terminé sans erreur n'est pas nécessairement physiquement valide.
8. Ne jamais neutraliser une alarme sans en expliquer la cause.
9. Ne jamais modifier ni tronquer une partie d'un fichier utilisateur sans nécessité. Aucun `...` ni « reste inchangé » dans un fichier produit.
10. Tout développement a des tests. Une fonctionnalité sans test n'est pas terminée.
11. Aucun document, résultat ou extrait synthétique ne doit être présenté comme réel.

## Ne pas réimplémenter ce que Code_Aster fournit
Le package `run_aster` livré avec l'installation expose déjà :
- `run_aster.command_files` : préparation des fichiers de commandes ;
- `run_aster.status` : état d'une exécution ;
- `run_aster.error_messages` : extraction des messages d'erreur d'une sortie ;
- `run_aster.export` : lecture des fichiers `.export` ;
- `run_aster.config` : paramètres de l'installation.

Ces modules sont encapsulés, jamais réécrits. Un parseur `.mess` maison ne se justifie que pour ce que ces modules ne couvrent pas, et la lacune doit
être documentée avant d'être comblée.

Il n'existe pas d'option de `run_aster` réalisant une vérification syntaxique sans exécution (`--env` prépare seulement le répertoire de travail). La
validation statique de niveau B est donc réalisée par confrontation au catalogue introspecté.

## Niveaux de validation
- A : réponse documentaire, non exécutée.
- B : syntaxe confrontée au catalogue de la version cible.
- C : fichier exécuté jusqu'à `FIN`.
- D : résultats soumis à des contrôles physiques.
- E : résultats comparés à une référence validée.

Ne jamais annoncer un niveau supérieur à celui réellement atteint. Les expressions « entièrement validé », « sans erreur » et « correct » sont
interdites sans mention du niveau atteint.

## Langue
- Documentation du projet et messages utilisateur : français.
- Code Python : identifiants et docstrings en anglais.
- Commentaires techniques : homogènes par fichier.
- Identifiants Code_Aster : casse officielle conservée exactement (`STAT_NON_LINE`, `AFFE_CHAR_MECA`, `COQUE_3D`, `DIS_CHOC`).

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

Le forum et les sources communautaires sont des sources secondaires et doivent être signalés comme telles.

## Règles de développement
- Python du projet : 3.12, fixé par `.python-version`, installé par `uv` (`requires-python = ">=3.12,<3.13"` dans `pyproject.toml`, dépendances dans
  `uv.lock`).
- `pathlib` pour tous les chemins, jamais de concaténation de chaînes.
- Annotations de types sur toute fonction publique.
- Modèles de données validés (`pydantic`) pour tout objet sérialisé.
- Journalisation de chaque téléchargement, transformation et indexation.
- Chaque traitement est reproductible et idempotent.
- Éviter les dépendances inutiles ; toute dépendance nouvelle est justifiée dans le commit qui l'introduit.
- Aucun accès réseau dans les tests unitaires. Les dépôts Git de test sont créés localement dans des répertoires temporaires.
- Tout code propre à un ouvrage va dans `projets/<nom>/`, jamais dans `src/` (lot 41). Ses tests vont dans `projets/<nom>/tests/`.

## Gestion des dépôts externes
Les dépôts Code_Aster sont clonés sous `external/` et ne sont jamais commités. Chaque synchronisation enregistre dans un manifeste :
- URL du dépôt ;
- branche ou tag ;
- hash du commit ;
- date de synchronisation ;
- version documentaire associée ;
- présence de modifications locales.

Une synchronisation n'écrase jamais des modifications locales : elle échoue et le signale.

## Validation obligatoire après modification
0. `aster-expert env-check` (lot 41 bis ; profil annoncé, lot 41 ter), puis `aster-expert mcp-check`.
1. Formatage (`ruff format`).
2. Analyse statique (`ruff check`, `mypy` : `src`, `tests` et `projets`, scripts de projet compris, en mode strict ; les scripts Salomé d'un projet en
   sont exclus).
3. Tests unitaires concernés (`pytest` : `tests/` et `projets/*/tests/`, sans Docker ni Salomé).
4. Tests d'intégration concernés, si applicable. **Tests réels** (lot 41) : `pytest -m lent` lance réellement Code_Aster (cas versionné du lot 22,
   arrêt `<F> <CALCULEL7_40>` du lot 39, avec leur compte rendu) et Salomé (géométrie 1 du lot 26) puis `mesh check` ; environ deux minutes, hors de
   la série par défaut. Depuis le lot 41 ter : `pytest -m lent_aster` (Code_Aster, VM et Cloud) et `pytest -m lent_salome` (Salomé, VM seule) ; une
   ressource absente fait ignorer le test avec son motif, jamais échouer.
5. Compte rendu précis : commandes lancées, sorties réelles, échecs éventuels.

Ne jamais annoncer qu'un test a réussi sans l'avoir exécuté et sans en donner la sortie.

## Critère de réussite des essais (à partir du lot 25)
Modèle : `docs/modele_rapport_essai.md`.

- Le critère est écrit dans le rapport **avant** l'exécution et n'est pas modifié après elle.
- Une grandeur que la théorie de l'élément reproduit exactement doit l'être à 10⁻⁶ près en relatif.
- Une grandeur sensible à la discrétisation doit présenter une erreur qui décroît quand le maillage est raffiné d'un facteur 2.
- Toute autre issue est un échec, rapporté tel quel.

## Fin de lot
Un lot n'est terminé qu'avec un commit Git distinct, dont le message porte le compte rendu complet :
1. l'inventaire des fichiers créés ou modifiés ;
2. la justification des choix techniques ;
3. la liste des tests exécutés et leurs résultats exacts ;
4. les limites connues et les points non couverts.

Depuis le lot 46, **tout lot met à jour `docs/etat.yaml`** (état du lot, commit qui porte le compte rendu, capacités et projets touchés) puis
`aster-expert etat readme` : la section « État du projet » du README en est générée, et `tests/unit/test_etat.py` échoue si les deux divergent ou si
un fichier ou un commit cité n'existe pas (`aster-expert etat verifier`). Le journal de `docs/development-plan.md` n'existe plus.

Depuis le lot 42, avant ce commit : `aster-expert rex <projet>` (et, une fois les échecs classés, `aster-expert rex <projet> --enregistrer --lot NN`)
; sa sortie est reproduite dans le compte rendu, et un échec non classé interdit la clôture.

Depuis le lot 41 ter, ce commit est fait sur la branche `lot-NN` du lot, poussée sur GitHub ; MM la fusionne dans `main` après relecture (section «
GitHub, branches et Cloud »). C'est toujours le commit lui-même, avec son message complet, qui fait foi (il a permis de retrouver le travail après un
arrêt brutal de la machine) ; jamais de commit de fusion cosmétique fait par la session.

## Accès MCP (lot 24)
- Le serveur MCP est déclaré en portée projet dans `.mcp.json` (versionné) : il lance `aster-expert-mcp` par `uv run --project
  ${CLAUDE_PROJECT_DIR:-.} --locked --all-extras` (lot 41 ter ; installation éditable, code source du dépôt). Une entrée du même nom en portée `local`
  ou `user` primerait sur elle, sans fusion : ne pas en recréer. Voir `README.md` pour la commande exacte.
- Une session garde le processus serveur lancé à son démarrage : du code ajouté ensuite n'y est pas visible.
- Chaque lot commence par `aster-expert env-check` (lot 41 bis), puis `aster-expert mcp-check` (serveur neuf, outils comparés au code, chaque outil
  appelé sur une requête minimale, arrêt au premier écart). Depuis le lot 25, `mcp-check` lit `.mcp.json`, applique `${VAR}` et `${VAR:-défaut}` à
  partir de l'environnement du shell **seul** (Claude Code ne définit `CLAUDE_PROJECT_DIR` que dans l'environnement du serveur lancé : ne jamais
  l'injecter dans le contrôle), vérifie que la commande obtenue existe et est exécutable, puis démarre le serveur avec cette commande. Ses appels
  portent `origin: "mcp-check"` dans `query_log.jsonl` (variable `ASTER_EXPERT_CALL_ORIGIN`) ; `read_usage_entries` les exclut des statistiques
  d'usage (les lignes antérieures au lot 25 n'ont pas d'origine et comptent comme usage). Quiconque ajoute un outil à `server.py` lui ajoute sa
  requête minimale dans `aster_expert/mcp/check.py` : à défaut le contrôle échoue.
- Si un outil attendu n'est pas visible dans la session, la session s'arrête et demande à MM de relancer Claude Code ou de reconnecter le serveur
  (`/mcp`). Elle ne se replie jamais sur une lecture directe de la documentation ou des cas tests.
- Un lot qui ajoute ou modifie un outil MCP se termine par une consigne explicite à MM : redémarrer la session avant le lot suivant.
- Une session par lot.
- Dix outils : `search_connaissances` interroge les six couches de `connaissances/` et englobe `search_constats` (constats seuls) ; le skill
  `code-aster-expert` impose de les consulter avant d'écrire une commande. `query_results` (lot 49) répond à une question sur les résultats
  d'un projet en lisant ses livrables (`aster-expert resultats lire`), jamais de mémoire ; sa sonde de `mcp-check` exige qu'un projet ait des
  livrables.
- Lot 44 : `get_command_schema` filtré par `keyword` ne renvoie que le sous-arbre demandé (`keyword_variants`), `command_schema` réduit à ses
  métadonnées et `keywords_omitted` qui compte ce qui est laissé de côté.
- `search_codeaster_docs` n'indexe pas les cas tests (familles présentes : V, R, U4, D, U2, U3, U7, U1, SV, SU, U0) : les chercher par
  `search_test_cases`. Une `family` absente de l'index est refusée avec la liste des familles présentes.

## Scripts Salomé (lot 26)
Les maillages d'ouvrage sont produits par des scripts Python exécutés dans Salomé-Méca (`aster-expert mesh run`, configuration `mesh:` de
`config/validation.yaml`) et contrôlés par un vérificateur indépendant qui relit le MED sans Salomé (`aster-expert mesh check <fichier.med>
<invariants.yaml>`, `medcoupling` de l'image Docker de `cave`). Règles d'écriture d'un script :
- toute la géométrie est assemblée en **une seule partition** (`MakePartition`) avant le maillage, pour garantir le partage des nœuds aux interfaces ;
  le bloc est encadré par `# ASSEMBLY begin` / `# ASSEMBLY end` (les variantes altérées le remplacent) ;
- les groupes sont créés **sur la géométrie** (`CreateGroup`, `GetInPlace`, `UnionIDs`) puis transférés au maillage (`GroupOnGeom`), jamais
  sélectionnés à la main ;
- **aucune coordonnée en dur** : tout est lu du fichier de paramètres passé au script (`args:<params>,<sortie.med>`) ;
- le script écrit `<sortie>.meta.json` avec l'empreinte SHA-256 de ses paramètres ; `mesh run` échoue si elle manque ou diverge.

Règles complémentaires (lot 27, leçons du lot 26) :
- **Arguments nommés.** Tout appel GEOM ou SMESH à plus de trois paramètres passe ses arguments par nom, jamais par position (erreur de
  `MakePartition` au lot 26).
- **Discrétisation explicite.** Ne pas s'appuyer sur l'arrondi d'une longueur locale : pour chaque arête, le script calcule un nombre de segments
  entier à partir de la taille visée et de la longueur réelle (`segment_count`) ou prend celui qu'une décision fixe, et l'impose par une hypothèse de
  sous-maillage sur un groupe d'arêtes de la partition. Ces nombres sont écrits dans `<sortie>.meta.json` et reportés dans le rapport de maillage.
- **Comptages attendus.** Les nombres de nœuds et de mailles attendus sont calculés analytiquement à partir des mêmes paramètres, par un module
  distinct du script Salomé (`aster_expert.meshing.combiwall`), avant l'exécution.
- Un script long écrit sa progression dans `<sortie>.progress.txt` (le journal d'un processus tué par le délai est perdu).

Noms et signatures GEOM/SMESH : jamais de mémoire. Ils sont relevés par introspection dans l'image (`scripts/salome/lot26_sonde_signatures.py`, sortie
versionnée `data/examples/lot26_essais/signatures_geom_smesh.txt`). Piège constaté : dans `MakePartition`, `KeepNonlimitShapes` est le **8e** argument
(`RemoveWebs` est le 6e) ; le passer en 6e position supprime silencieusement les arêtes isolées (poutre, barre) du maillage.

Le vérificateur évalue **tous** les invariants (comptages de nœuds et de mailles par type, présence, cardinalité, type de mailles et boîte englobante
de chaque groupe, nœuds à des coordonnées imposées, nœuds partagés entre groupes, nœuds orphelins, nœuds confondus non fusionnés), les liste avec
valeur attendue et valeur obtenue, et sort en erreur (code 1) dès qu'un seul est en écart en désignant le premier. Les valeurs attendues d'un fichier
d'invariants sont calculées **analytiquement à partir des paramètres**, avant l'exécution, jamais relues d'un MED produit.

Constat (lot 26) : les MED exportés contiennent aussi les SEG2 du maillage 1D (bords compris) ; les comptages de mailles les incluent.

## Règles tirées des lots 19 à 49 (en vigueur)
L'historique de ces lots est dans `docs/historique/claude_md_avant_lot48bis.md`, `docs/etat.yaml` et `docs/essais_lotNN.md`. Ne restent ici que les
règles.

Fiche et données :
- Un JSON de fiche produit par script (fiche du quai : `build_combiwall_reference.py` ; dalle et estacade : scripts de décisions, `fiche enregistrer`,
  `fiche prevoir`) n'est jamais édité à la main ; un test rejoue le script et compare octet pour octet.
- Une révision de décision passe par `record_practice_decision` : l'ancienne décision va dans `decision_history`, jamais modifiée en place.
- Une source `norme` datée d'un mois seulement ne porte pas de `date` (`date=None`, le mois reste dans `reference`) : ne jamais inventer un jour.
- `HypothesesSheet.group_naming_gaps(catalogue_identifiers)` signale, ne corrige pas ; sans le vocabulaire du catalogue, des mots-clés sont lus à tort
  comme des groupes.
- Une entrée `code_aster` non tranchée ne porte pas d'option retenue ; un ensemble d'options recevables se consigne dans une entrée tranchée qui le
  dit, plus une entrée pratique ouverte du même `point_label`.
- `ExecutionSource` n'est admise que sur les constats `code_aster`, au niveau C ou D (jamais plus) ; chemin et empreinte sont confrontés au dépôt
  (`record_execution_finding`) ; sa valeur est imprimée dans son listing versionné (test) ; une exécution en échec est de niveau B et se rapporte dans
  les `notes`. Écriture par script d'entrées, jamais à la main.
- `declare_under_revision` / `lift_revision` : motif obligatoire, journal `revision_history` ; une entrée en révision est un bloqueur de génération,
  **limité depuis le lot 48 bis aux étapes que `blocker_scopes` de `projet.yaml` déclare** (sans déclaration : toutes les étapes) ; une nouvelle
  `record_practice_decision` la clôt.
- Une valeur « à fournir » du fichier de données bloque : ne jamais la compléter sans source, la demander à MM. Valeurs dans l'unité de leur source,
  jamais converties ni calculées dans le fichier.
- Décisions de MM : `aster-expert fiche enregistrer <projet> <arbitrage.md>` (texte cité vérifié à l'identique dans le fichier source, jamais retapé)
  ; plus de script de lot. `planned_commands` : `aster-expert fiche prevoir <projet> --ecrire`, exigées par `projet verifier` (ou exemption motivée
  `planned_commands_exemption`).
- Décisions en vigueur : Es = 200 GPa pour les armatures de tous les projets (PRE-032 ; quai en révision, ferraillage bloqué) ; D20, D21 (PRE-019,
  PRE-020) ; `FERR_MIN` n'est demandé qu'avec `UNITE_CONTRAINTE='MPa'` (CA-041).
- Un marqueur `[À CONFIRMER MM]` est refusé dans un texte en vigueur, accepté cité dans l'historique.

Code_Aster (faits dans `connaissances/constats_code_aster/`, à consulter avant d'écrire) :
- Sous `ELAS_COQUE`, ne jamais lire `REAC_NODA`, `FORC_NODA`, `SIEF_ELGA` quand `FLEX ≠ MEMB × EPAIS²/12` : lire `EFGE_NOEU` ; `RHO = 0` donne un
  poids nul sans alarme ; le contrôle d'équilibre se fait sur les forces des ressorts ou sur des nœuds sans `ELAS_COQUE`.
- Ressorts nodaux : un groupe `POI1` par classe de raideur, une occurrence de `CREA_POI1` et de `DISCRET` par classe, jamais par nœud ; `CREA_POI1` ne
  crée qu'une maille par nœud (classes communes de raideur sommées) ; `DIS_T` sous `PESANTEUR` exige une masse (`M_T_D_N`).
- Noms de groupe de 24 caractères au plus (Code_Aster tronque en silence). `IMPR_TABLE` tronque l'intitulé à 16 caractères ; contrôles imprimés en
  `E20.12`. `FORCE_COQUE/PRES` en fonction est évalué aux nœuds. `NOM_RESU_MED` (8 caractères au plus) par occurrence de `RESU`.
- Toute lecture de cas tests passe par `search_test_cases` / `read_test_case` ; jamais `cat` ni `grep` de `external/codeaster-src/astest`.
- Un cas avec maillage exige un `.export` (seul un `.export` fait copier les fichiers voisins) et sa racine dans `execution.allowed_roots`.
- Le serveur MCP attaché à une session peut précéder le code : se reconnecter (`/mcp`).
- Salomé : pas d'installation native ; Salomé-Méca en conteneur Singularity (`~/Desktop/salome_meca.sif`, Python 3.9, VM seulement) ; `salome -t
  --shutdown-servers=1 script.py` exécute GEOM + SMESH sans interface ; l'image Docker de `cave` n'a pas Salomé mais `medcoupling` ; le Python du
  projet n'a aucun module MED ; ne pas lancer le lanceur `salome_meca` sans nécessité (son premier démarrage écrit une configuration).

Projets, paquets et livrables :
- Règle de conservation d'un niveau (paquet) : un niveau reste acquis pour un `.comm` identique hors commentaires et en-tête (`normalize_comm`), sinon
  il est rejoué avec les critères d'origine ; critères commités après l'exécution ou avec des résultats : signalés (`anteriorite_demontrable`). Dans
  un dépôt Git tronqué (Cloud), `--reevaluer` ne dit pas la vérité sur l'antériorité : ne pas l'utiliser pour changer un paquet.
- Notes Word : contenu tiré de la fiche, des données et du paquet, jamais d'un texte écrit à la main ; tableaux et figures déclarés dans `projet.yaml`
  ; contrôle automatique relu dans le `.docx`.
- Une archive d'exécution absente, partielle (Cloud) ou non conforme est refusée par `rex` : seuls les champs déclarés sont écrits.
- Un cas de référence d'un projet (`projets/*/references/cas/*.comm`) porte sa déclaration `<stem>.connaissances.yaml` (sans elle son rejeu est
  refusé, REF-014 au lot 46).

Contrôles exécutables ajoutés au lot 48 bis (audit R3, R4, R6, R8) :
- `validate` / `validate_comm` : verdict `valide`, `partiel` (une commande non confrontée au catalogue : code de sortie 2, commandes listées) ou
  `invalide` (code 1) ; `valid` n'est vrai que si tout est confronté. Les tuples de concepts (`CHAR_MECA_GLOBAL=(CL,)`) sont résolus.
- `connaissances rejouer-references` et `constats rejouer` : code 2 pour un cas non rejouable, code 1 pour une référence à réexaminer. Une référence
  `établie` ou `promue` déclare son `replay_mode` (`listing` seul aujourd'hui, testé) ; sans mode elle reste `observé` et n'est pas rejouée.
- Termes confidentiels : variable `ASTER_EXPERT_TERMES_INTERDITS` (secret GitHub Actions et variable de l'environnement Cloud, jamais un fichier
  versionné, `docs/cloud.md` § 11) ; un projet `confidential_data: true` sans liste fait échouer le contrôle de publication.
- Nombres des maillages et des sorties texte (lot 48 bis) : un script de maillage construit ses sommets à partir de valeurs exactes et recale les coordonnées voulues sur la grille de `config/arrondis.yaml` (1 mm) avant l'écriture ; `mesh check` rapporte toute coordonnée « presque sur la grille sans y être » (non bloquant tant que les maillages versionnés en portent). Les sorties texte (tableaux de notes, CSV de lecture, commentaires de `.comm`) arrondissent selon la table unique `config/arrondis.yaml` (`aster_expert.arrondis`) ; les contrôles numériques travaillent sur les valeurs non arrondies, et une valeur dérivée d'un calcul exact garde sa précision dans le `.comm` avec sa valeur arrondie en commentaire.
- Crochet `pre-push` : `ruff format --check`, `ruff check`, `pytest` (hors tests lents) avant tout envoi ; ne jamais le contourner. `ci.yml` : `main`,
  `lot-*`, `claude/**` ; `ci-lent.yml` aussi sur tout envoi touchant `execution/`, `validation/` ou `connaissances/`.

Livrables et ressources (lot 49) :
- Tout projet déclare `deliverables` dans `projet.yaml` (`projet verifier` le refuse absent) : champs par famille, combinaisons, enveloppes,
  livrables non pertinents avec leur motif. `aster-expert projet <nom> livrables` (sous-étapes `preparer`, `executer`, `verifier`, `traiter`,
  `vues`, puis `classeur` après `exporter-resultats`) : le `.comm` de production n'est jamais modifié ; une copie, avec des blocs de sorties
  insérés, est exécutée et n'est acceptée que si toutes ses tables `E20.12` égalent celles de la production. MED et VTU jamais versionnés ; le
  paquet porte la section `visualisation` (manifeste avec empreintes, contrôle CTL-013 sur le MED des charges, synthèses, images).
- Questions sur des résultats : `aster-expert resultats lire <projet>` ou `query_results`, jamais un script jetable.
- `CALC_CHAMP/PARALLELISME_TEMPS='OUI'` est refusé avant toute exécution (DIAG-027, `execution.forbidden_keywords`) ; une règle se lève en la
  retirant de `config/validation.yaml` une fois son diagnostic résolu. Fils d'une exécution : processeurs ÷ exécutions simultanées, plafonnés par
  `execution.useful_threads_max` (mesures du lot 49, `aster_expert.execution.regle_fils`) ; MPI désactivé par défaut.
- Rendu ParaView sans écran (VM) : ParaView 5.11 de l'image Salomé-Méca, `xvfb-run -a pvbatch --no-mpi` (sans `--no-mpi`, blocage à
  l'initialisation MPI ; `--force-offscreen-rendering` s'arrête en SIGABRT). Les scripts ParaView sont générés du manifeste, jamais écrits
  à la main avec une liste de cas.

## Périmètre à ne pas dépasser sans instruction
Une session traite un lot et un seul. Ne pas anticiper les lots suivants, ne pas installer d'infrastructure non demandée, ne pas inventer la structure
d'un dépôt externe avant de l'avoir inspectée.

