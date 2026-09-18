# Architecture

## 1. Contexte

AsterExpert s'exécute dans une machine virtuelle Ubuntu 24.04. Code_Aster n'y
est pas installé nativement : il est distribué sous forme d'images Docker
(`simvia/code_aster`), gérées par l'outil tiers `cave`, et exécuté dans des
conteneurs. Cette contrainte n'est pas accessoire : elle conditionne l'accès
au catalogue, à `run_aster` et aux cas tests, qui n'existent qu'à l'intérieur
de l'image — jamais sur le système de fichiers de la VM elle-même, où seul le
dépôt source amont peut être présent à titre de référence, jamais compilé ni
installé. Une exécution depuis l'hôte (hors VM), ou depuis tout environnement
sans Docker, ne permet que les fonctions documentaires, niveau A au mieux.
Voir ADR-002, ADR-003 et ADR-006 pour le détail du mécanisme retenu.

## 2. Vue d'ensemble

```
                 ┌──────────────────────────────────────────┐
                 │  Sources externes (external/, non gitées) │
                 │  codeaster/src        codeaster/doc       │
                 └───────────────┬──────────────────────────┘
                                 │ ingestion (clone versionné + manifeste)
                                 ▼
    ┌────────────────────────────────────────────────────────────┐
    │  data/raw          documents bruts + manifeste JSONL        │
    └───────────────┬────────────────────────────────────────────┘
                    │ parsing (doc, cas tests, .comm)
                    ▼
    ┌────────────────────────────────────────────────────────────┐
    │  data/processed    fragments + métadonnées normalisées      │
    └───────────────┬────────────────────────────────────────────┘
                    │ indexing
                    ▼
    ┌────────────────────────────────────────────────────────────┐
    │  data/indexes      index lexical (+ vectoriel si justifié)  │
    └───────────────┬────────────────────────────────────────────┘
                    │ retrieval (filtres de métadonnées, fusion)
                    ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐
    │  CLI          │   │  serveur MCP │   │  validation          │
    └──────────────┘   └──────────────┘   └──────────────────────┘

    Voie parallèle, indépendante du corpus documentaire :

    ┌─ conteneur Docker (simvia/code_aster, ADR-002/003/006) ──────────────┐
    │  Python d'Aster ──► scripts/introspect_catalogue.py ──► JSON         │
    └──────────────────────────────┬───────────────────────────────────────┘
                                   ▼
                     data/processed/catalogue/<digest>/*.json
                                   │
                                   ▼
                     validation statique (niveau B)
```

## 3. Décisions d'architecture

### ADR-001 — Le catalogue est la source de vérité syntaxique

**Décision.** Les schémas de commandes sont extraits par introspection du
catalogue Python de l'installation, jamais déduits des manuels U4.

**Motif.** Le catalogue est la définition formelle effectivement appliquée par
le superviseur lors de l'exécution. Le cycle de vérification est implémenté
dans `code_aster.Supervis.ExecuteCommand` (adaptation de compatibilité,
vérification vis-à-vis du catalogue, adaptation post-vérification). Une
grammaire reconstruite à partir des manuels serait une copie approximative,
désynchronisée à chaque montée de version, et impossible à rattacher à une
révision.

**Conséquence.** Les manuels U/R/V servent à la sémantique, aux hypothèses
théoriques et aux exemples, pas à la grammaire. Un désaccord entre manuel et
catalogue est tranché en faveur du catalogue et signalé comme anomalie.

### ADR-002 — Séparation des deux interpréteurs Python, exécution conteneurisée

**Décision.** Le paquet `aster_expert` n'importe jamais `code_aster`.
L'introspection du catalogue et l'exécution passent par des sous-processus
Python lancés **à l'intérieur du conteneur Docker** qui porte l'installation
Code_Aster, jamais par un interpréteur natif de l'hôte.

**Motif.** Code_Aster n'est pas installé nativement sur cette machine. Il est
distribué sous forme d'images Docker (`simvia/code_aster`, gérées par l'outil
tiers `cave`) contenant leur propre interpréteur Python (empaqueté par Spack,
préfixe `/opt/spack/...`) et leurs propres bibliothèques natives. Ce préfixe
change à chaque image (hash Spack aléatoire) et est physiquement isolé de
l'hôte. Constaté en session de découverte : `run_aster` n'existe pas dans le
`PATH` de l'hôte ; le dépôt `/home/ubuntu/code-aster` présent sur la machine
n'est que le dépôt source amont (`gitlab.com/codeaster/src`, branche `main`),
jamais compilé ni installé — sa présence ne doit jamais laisser croire à une
installation native.

**Mécanisme d'invocation retenu.** Trois mécanismes ont été testés dans cet
ordre :

a. Invoquer `python3` directement dans le conteneur sans shell, en s'appuyant
   sur les variables déclarées dans `Config.Env` de l'image
   (`docker inspect`). Écarté : `Config.Env` ne porte qu'un `PATH` générique
   (`/usr/local/sbin:...`), sans `PYTHONPATH` ; `python3 -c "import
   code_aster"` échoue (`ModuleNotFoundError`) sans configuration
   supplémentaire.

b. `bash -lc "..."` (shell de connexion non interactif). Écarté :
   l'environnement Aster n'est configuré que dans `~/.bashrc`
   (`source /opt/activate.sh`, artefact propre à l'emballage Spack de cette
   image), fichier lu par un shell interactif, pas par un shell de connexion.
   Constaté : `bash -lc "run_aster --version"` échoue (`command not found`).

c. **Retenu.** Reproduire la résolution de préfixe du script `run_aster`
   lui-même (déjà observée sur le gabarit `data/run_aster` du dépôt source
   amont) : localiser le binaire `run_aster` par recherche bornée sur le
   système de fichiers du conteneur (son chemin contient un hash Spack
   imprévisible, jamais codé en dur), résoudre son chemin réel (`readlink
   -f`), remonter de deux niveaux pour obtenir le préfixe d'installation, puis
   `source <préfixe>/share/aster/profile.sh`. Ce fichier est généré par le
   build Code_Aster lui-même (`data/wscript` / `profile.sh.tmpl` du dépôt
   source), donc présent dans toute installation correctement construite —
   contrairement à `/opt/activate.sh`, propre à cet emballage Spack
   particulier.
   Complément constaté en session : `profile.sh` seul règle `PYTHONPATH` sur
   le répertoire `lib64/aster` du préfixe (où réside effectivement
   `code_aster`), mais ne suffit pas pour les dépendances tierces du paquet
   `Cata` (`numpy`, utilisé par `code_aster.Cata.Language.SyntaxChecker`), qui
   vivent dans la vue Spack agrégée de l'environnement
   (`.../.spack-env/view/lib/python3.*/site-packages`).

   **Écart assumé au mécanisme officiel (lot 4).** Localiser cette vue est
   un ajout propre à ce projet, pas une étape du mécanisme officiel
   `run_aster`/`profile.sh` : sa seule raison d'être est que `numpy` n'est
   pas embarqué par `code_aster` lui-même mais fourni par l'emballage Spack
   de l'image. Sa racine (`.../var/spack/environments/<nom>/.spack-env/view`)
   n'est jamais codée en dur : elle est dérivée du préfixe déjà résolu, en
   remontant ses répertoires parents jusqu'à trouver un `var/spack/
   environments`, plutôt que supposée à un chemin ou une profondeur fixes
   (le nom de l'environnement Spack, `simvia_env` sur l'image testée, est
   propre à cet emballage et n'est jamais lu ni supposé). Absence de vue
   trouvée : non fatale ici, l'échec se déplace sur l'import Python lui-même
   (`ModuleNotFoundError`), qui reste explicite. Le mécanisme retenu ajoute
   donc cette entrée dérivée à `PYTHONPATH` avant de sourcer `profile.sh`
   (`set -u` désactivé le temps de ce `source`, ce fichier généré par le
   build n'étant pas nounset-safe — constaté en session : `${ASTER_
   PROFILE_LOADED}` et `${LD_LIBRARY_PATH}` y sont référencées sans valeur
   par défaut). Vérifié empiriquement : `import code_aster.Cata.Commands` et
   `numpy` réussissent alors, sans shell interactif ni avertissement de
   terminal.

   **Complément `LD_LIBRARY_PATH` (lot 11, exécution encadrée).** Les lots
   2/4/10 n'importent jamais `libaster` (l'introspection du catalogue et
   `checkCommandSyntax` sont du Python pur plus `numpy`) : l'écart ci-dessus
   ne portait donc que sur `PYTHONPATH`. Une exécution réelle importe
   `libaster` (`code_aster.Utilities.ExecutionParameter`), et ce chemin a
   échoué en session avec `ImportError: libmed.so.11: cannot open shared
   object file` — `profile.sh` seul règle `LD_LIBRARY_PATH` pour les
   bibliothèques embarquées par l'installation Aster elle-même, jamais pour
   les dépendances tierces que l'emballage Spack de cette image fournit à
   part (même famille d'écart que `numpy` ci-dessus). Confirmé par
   localisation directe : `libmed.so.11` ne vit nulle part sous le préfixe
   Aster, uniquement sous la vue Spack déjà résolue (`$VIEW/lib`). Le
   mécanisme retenu exporte donc aussi `LD_LIBRARY_PATH` depuis cette même
   vue avant de sourcer `profile.sh` (qui l'étend plutôt que l'écrase,
   d'après la même lecture nounset-unsafe déjà notée ci-dessus) —
   `aster_expert.execution.container_env.build_environment_setup_script`,
   partagé par tous les appelants, jamais dupliqué par lot.

**Résolution de version.** La version cible n'est jamais le tag `stable` : il
est mobile côté registre et peut diverger de l'image locale du même nom
(constaté en session : `docker images` renvoie `simvia/code_aster:stable`
identique à `16.8.0`, alors que `cave available` annonce `17.4.0` comme
version `stable` sur Docker Hub le même jour). La version cible est le digest
de l'image (`RepoDigests`, ex. `simvia/code_aster@sha256:...`), jamais le tag
seul. `config/versions.yaml`, section `detected`, enregistre le tag observé,
le digest, la sortie brute de `run_aster --version` et une empreinte du
catalogue introspecté — quatre données indépendantes, jamais déduites l'une de
l'autre.

**Conséquence.** Les scripts destinés au Python d'Aster vivent dans
`scripts/`, n'ont aucune dépendance en dehors de la bibliothèque standard (les
modules du catalogue qu'ils importent dépendent de `numpy` — dépendance de
`code_aster.Cata`, pas du script lui-même), et communiquent exclusivement par
JSON sur la sortie standard. Le mécanisme de résolution d'environnement ne
code en dur ni le hash de build, ni la racine Spack elle-même (dérivée du
préfixe résolu, voir ci-dessus) ; il dépend en revanche de la présence d'un
répertoire nommé `view` sous un `.spack-env` quelque part au-dessus du
préfixe, ce qui est spécifique à un emballage Spack — une image construite
autrement (paquet système, Conda) demanderait un mécanisme de repli distinct,
à traiter sur preuve si une telle image se présente.

### ADR-003 — Encapsulation de `run_aster` à l'intérieur du conteneur, pas de réimplémentation

**Décision.** L'exécution et le dépouillement s'appuient sur les modules
`run_aster.command_files`, `run_aster.status`, `run_aster.error_messages`,
`run_aster.export` et `run_aster.config`, invoqués **à l'intérieur du
conteneur** qui porte l'installation — jamais recopiés ni réimplémentés côté
hôte.

**Motif.** Inchangé sur le fond : ces modules sont livrés avec l'installation,
suivent la version, et couvrent déjà la préparation du fichier de commandes,
l'état d'exécution et l'extraction des messages d'erreur. Le fait que
l'installation soit conteneurisée ne change pas cette analyse : `run_aster`
reste le point d'entrée officiel. Confirmé en session par traçage
(`strace -f -e trace=execve`) de `cave run -- <fichier.export>` :

```
docker run --rm -it -v <répertoire_courant>:/home/user/data -w /home/user/data \
    <image> /bin/bash -i -c "run_aster <args>"
```

**Conséquence.** `cave` n'expose pas d'équivalent à `docker exec` pour une
commande arbitraire — sa seule sous-commande d'exécution est
`cave run -- <fichier.export>`. `aster_expert` n'invoque donc jamais `cave`
pour l'introspection ou la validation : il invoque `docker run` directement,
en reproduisant le motif de montage de `cave` mais restreint à un répertoire
dédié (voir ADR-006) — jamais la racine du dépôt ni `$HOME`.

`run_aster` demeure la voie d'exécution effective d'un fichier `.export` ou
`.comm` (lot 11). L'introspection du catalogue (lot 4) n'a pas besoin de
passer par `run_aster` lui-même : un `python3` correctement configuré
(ADR-002) suffit, et évite l'appareillage de job complet de `run_aster`
(répertoire `proc.N`, restauration de base, relance MPI) — constaté en
session lors d'un essai infructueux de `run_aster --no-comm script.py` sur un
script exécuté sans configuration additionnelle : l'échec (`No module named
mpi4py`) venait de l'interpréteur Spack brut, qui n'a pas la vue Spack
complète tant qu'elle n'est pas ajoutée explicitement au `PYTHONPATH` (ADR-002).
Le répertoire `proc.N` anticipé ici s'est confirmé au lot 11 : l'image
`simvia/code_aster:17.4.0` se déclare "parallel" (`run_aster.config.CFG`)
même pour une exécution à un seul processus, donc `RunAster.execute` imbrique
systématiquement la sortie sous `<répertoire de travail>/proc.0/` — jamais à
la racine du répertoire monté. `aster_expert.execution.execute` en tient
compte pour localiser le `.mess`, jamais en supposant un chemin fixe.

Un analyseur `.mess` propre au projet n'est écrit que pour ce que ces modules
ne couvrent pas — typiquement le relevé structuré des alarmes, des durées par
commande et des indicateurs de convergence. La lacune est documentée avant
d'être comblée.

### ADR-004 — Recherche lexicale d'abord, vectorielle sur preuve

**Décision.** L'index initial est lexical (BM25) avec filtres de métadonnées
stricts. L'index vectoriel n'est construit que si le banc d'évaluation montre
un déficit de rappel que le lexical ne comble pas.

**Motif.** Les requêtes Code_Aster sont lexicalement denses : noms de commandes,
mots-clés facteurs, identifiants documentaires, identifiants de messages. Le
coût d'un index vectoriel (modèle d'embedding, stockage, dérive de version,
dépendance API) n'est pas justifié tant qu'il n'est pas mesuré.

**Conséquence.** L'interface `Retriever` est définie dès le départ pour
accueillir plusieurs moteurs et une fusion, mais une seule implémentation
existe initialement.

### ADR-005 — Le banc d'évaluation précède l'optimisation

**Décision.** Un jeu de 30 à 50 questions réelles, chacune associée au document
ou au fragment attendu, est constitué avant tout travail sur le chunking, la
fusion ou le reranking.

**Motif.** Sans mesure, les choix de découpage et de pondération ne sont pas
décidables et toute amélioration est invérifiable.

**Conséquence.** `data/evaluations/` contient le jeu de questions versionné.
Chaque lot touchant la recherche rapporte les métriques avant et après.

### ADR-006 — L'isolation vient du conteneur ; limites par `--memory`, `--cpus` et `--network=none`

**Décision.** L'exécution de Code_Aster — introspection du catalogue comme
exécution encadrée d'un calcul — se fait exclusivement à l'intérieur du
conteneur Docker qui porte l'installation, jamais par sous-processus natif sur
l'hôte. L'isolation ne repose plus sur un répertoire de travail éphémère au
sens de la version précédente de cette décision (aucune installation native
n'existe sur l'hôte pour justifier cette hypothèse), mais sur le conteneur
lui-même, avec les paramètres suivants, tous vérifiés en session :

- `--network=none` : aucun accès réseau depuis l'introspection ni
  l'exécution. Vérifié : `urllib.request.urlopen` échoue avec
  `Temporary failure in name resolution`.
- `--memory=<limite>` et `--cpus=<limite>` : limites de ressources imposées
  par le moteur conteneur (cgroups), pas par le module `resource` de Python.
  Vérifié : `--memory=512m` se traduit en `536870912` octets dans
  `/sys/fs/cgroup/memory.max` à l'intérieur du conteneur.
- `--user $(id -u):$(id -g)` : le conteneur s'exécute avec l'UID/GID de
  l'utilisateur hôte, jamais root. Vérifié : les fichiers produits dans le
  répertoire monté appartiennent à l'utilisateur hôte, pas à `root`.
- Montage restreint à un répertoire de travail dédié (répertoire temporaire ou
  répertoire d'exécution explicite), jamais la racine du dépôt ni `$HOME`. Le
  script d'introspection est copié dans ce répertoire au moment de l'appel, il
  n'est jamais monté depuis son emplacement dans le dépôt.
- Un fichier n'est jamais exécuté hors de ce répertoire monté.
- Le délai maximal enveloppe l'appel `docker run` lui-même (au niveau
  `aster_expert`, pas seulement au niveau de `run_aster`), pour couvrir aussi
  un conteneur qui ne se terminerait pas.

**Motif.** La version précédente de cette décision supposait une installation
Code_Aster native dans la VM et une isolation déjà fournie par la VM
elle-même. Cette hypothèse était fausse : aucune installation native n'existe,
Code_Aster s'exécute exclusivement via des images Docker gérées par `cave`
(constaté en phase de découverte : `run_aster` absent du `PATH` hôte,
`/home/ubuntu/code-aster` n'est que le dépôt source jamais compilé). Le
conteneur est donc la seule frontière d'isolation disponible, et doit être
configuré explicitement plutôt que supposée acquise.

**Conséquence.** `docker-compose.yml` reste inutile : un appel `docker run`
unique et entièrement paramétré (image résolue par digest — voir ADR-002 —,
montage restreint, `--network=none`, `--user`, `--memory`, `--cpus`) couvre
aussi bien l'introspection que l'exécution encadrée. `cave` reste l'outil de
gestion des versions d'image (`cave list`, `cave available`, `cave pin`) mais
n'est pas invoqué par `aster_expert` pour l'exécution elle-même, faute
d'option d'exécution arbitraire (voir ADR-003).

**Révision.** À reconsidérer si `docker` devient indisponible pour
l'utilisateur (l'appartenance au groupe `docker` est nécessaire, vérifiée en
session) ou si plusieurs conteneurs doivent être orchestrés simultanément.

### ADR-007 — Le profil de requête est un paramètre explicite, jamais détecté

**Décision.** Le profil de priorité des sources (`syntaxe`, `theorie`,
`methode` -- `config/retrieval.yaml`, `defaults.source_priority`) est
toujours reçu en paramètre explicite par l'appelant (`aster-expert search
--profile`), jamais déduit automatiquement du texte de la requête. Aucun
classifieur, aucune heuristique de détection n'est écrite pour ce projet.

**Motif.** Un profil deviné à partir du texte de la requête introduirait une
seconde source d'erreur non mesurée (la détection elle-même) par-dessus la
recherche. Au lot 8 (serveur MCP), l'appelant sera une session Claude qui
sait déjà quelle sorte de réponse elle cherche -- le profil est une entrée
que l'appelant fournit, pas une devinette que le système doit produire à sa
place. `syntaxe` reste le profil par défaut quand l'appelant n'en fournit
aucun (jamais un défaut détecté non plus, un simple repli documenté).

**Conséquence.** `aster_expert.retrieval.query_profiles` ne contient qu'un
modèle et un chargeur pour une annotation *fournie en donnée d'entrée*
(`data/evaluations/query_profiles.jsonl`, lot 7c G3 : établie une fois, à la
main, à partir du seul libellé de chaque question du banc, sans consulter
les documents attendus) -- jamais un mécanisme de classification exécuté à
la volée. Mesurer l'effet du routage sur le banc exige donc de fournir un
profil par question (`aster_expert.retrieval.bench.
run_profile_routed_bench`) plutôt que de le déduire au moment de la mesure.

**Révision.** À reconsidérer si un lot futur démontre, sur mesure, qu'une
détection automatique améliore le résultat sans coût de fiabilité
inacceptable -- non entrepris ici, faute d'instruction et de mesure en ce
sens.

## 4. Modules

| Module | Rôle |
|--------|------|
| `ingestion/` | Clonage versionné des dépôts, manifeste, inventaire du corpus |
| `parsing/` | Transformation des documents et des cas tests en fragments |
| `catalogue/` | Pilotage de l'introspection, modèles de schémas de commandes |
| `indexing/` | Construction des index et des métadonnées de filtrage |
| `retrieval/` | Interrogation, filtres, fusion, priorité des sources |
| `validation/` | Contrôles statiques d'un `.comm` vis-à-vis du catalogue |
| `execution/` | Encapsulation de `run_aster`, dépouillement du `.mess` |
| `agent/` | Schémas de réponse, niveaux de validation, formats de citation, fiche d'hypothèses (lot 14) |
| `mcp/` | Exposition des fonctions ci-dessus comme outils MCP |

`agent/` ne contient pas de logique d'appel à un modèle. Le projet produit des
outils et des données ; l'orchestration conversationnelle reste en dehors tant
que le périmètre n'est pas étendu. `agent.hypotheses` (lot 14) fait de même
pour la structure d'une fiche d'hypothèses de modélisation : un schéma de
données validé (`pydantic`), jamais un générateur de fiche ni de `.comm`.

## 5. Flux de validation d'un fichier `.comm`

```
fichier .comm
  │
  ├─ parsing structurel (sans exécution du fichier)
  │     commandes, ordre, concepts produits et consommés,
  │     mots-clés facteurs et simples, groupes littéraux,
  │     modélisations, comportements, unités logiques
  │
  ├─ confrontation au catalogue de la version cible      -> niveau B
  │     commande inconnue, mot-clé inconnu, cardinalité,
  │     type de valeur, blocs conditionnels non satisfaits,
  │     concept utilisé avant définition
  │
  ├─ exécution encadrée                                  -> niveau C
  │     run_aster, répertoire dédié, limites de ressources
  │
  ├─ dépouillement du .mess                              -> niveau C
  │     état, erreurs, alarmes, convergence
  │
  └─ contrôles physiques et comparaison de référence      -> niveaux D, E
```

Un fichier `.comm` n'est jamais exécuté par le parseur, y compris pour en
déduire la structure. Sa syntaxe est proche de Python mais son exécution
déclenche des effets de bord et des calculs.

## 6. Limites connues de cette architecture

- L'extraction du catalogue dépend de la stabilité des noms internes du package
  `code_aster`. Ces noms ne sont pas une API publique et peuvent changer entre
  versions majeures. L'introspection doit échouer bruyamment, jamais deviner.
- Le format des sources documentaires de `codeaster/doc` n'a pas été inspecté au
  moment de la rédaction. Le lot de parsing documentaire ne peut pas être figé
  avant cette inspection.
- L'analyse structurelle d'un `.comm` qui construit ses arguments dynamiquement
  (boucles, dictionnaires assemblés, fonctions utilisateur) est partielle par
  construction. Les cas non résolus doivent être signalés, pas devinés.
