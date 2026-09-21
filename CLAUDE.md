# AsterExpert

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

Le dépôt vit dans une machine virtuelle Ubuntu 24.04 (Oracle VirtualBox).
Code_Aster n'y est pas installé nativement : il s'exécute dans un conteneur
Docker (image `simvia/code_aster`), géré par l'outil tiers `cave`. Le
développement et l'indexation ont lieu dans la VM ; l'introspection du
catalogue et l'exécution de calculs ont lieu à l'intérieur du conteneur,
jamais par sous-processus natif de la VM. L'hôte (hors VM) ne sert qu'à
l'édition (VSCode en Remote-SSH) et ne dispose ni de Docker ni de Code_Aster.

Deux interpréteurs Python coexistent et ne doivent jamais être confondus :

- le Python du projet (`.venv`), dans la VM, qui exécute `aster_expert` ;
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

- Python 3.12 minimum pour le projet (version déclarée dans `pyproject.toml`).
- `pathlib` pour tous les chemins, jamais de concaténation de chaînes.
- Annotations de types sur toute fonction publique.
- Modèles de données validés (`pydantic`) pour tout objet sérialisé.
- Journalisation de chaque téléchargement, transformation et indexation.
- Chaque traitement est reproductible et idempotent.
- Éviter les dépendances inutiles ; toute dépendance nouvelle est justifiée
  dans le commit qui l'introduit.
- Aucun accès réseau dans les tests unitaires. Les dépôts Git de test sont
  créés localement dans des répertoires temporaires.

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

1. Formatage (`ruff format`).
2. Analyse statique (`ruff check`, `mypy`).
3. Tests unitaires concernés (`pytest`).
4. Tests d'intégration concernés, si applicable.
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

Les branches par lot sont facultatives et ne sont jamais un livrable en
elles-mêmes : la règle réelle du dépôt est un commit distinct par lot sur la
branche où l'on travaille, jamais une bulle de fusion cosmétique. Ni une
branche par lot ni un commit de fusion ne sont exigés — plusieurs lots
antérieurs sont des commits directs, et c'est le commit lui-même, avec son
message complet, qui a permis de retrouver le travail après un arrêt brutal
de la machine.

## Accès MCP (lot 24)

- Le serveur MCP est déclaré en portée projet dans `.mcp.json` (versionné) : il
  lance `.venv/bin/aster-expert-mcp` (installation éditable, code source du
  dépôt). Une entrée du même nom en portée `local` ou `user` primerait sur elle,
  sans fusion : ne pas en recréer. Voir `README.md` pour la commande exacte.
- Une session garde le processus serveur lancé à son démarrage : du code ajouté
  ensuite n'y est pas visible.
- Chaque lot commence par `aster-expert mcp-check` (serveur neuf, outils comparés
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
