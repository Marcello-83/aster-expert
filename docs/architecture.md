# Architecture

## 1. Contexte

AsterExpert s'exécute dans la même machine virtuelle que Code_Aster. Cette
contrainte n'est pas accessoire : elle conditionne l'accès au catalogue, à
`run_aster` et aux cas tests installés. Une exécution depuis l'hôte ou depuis un
environnement distant sans Code_Aster ne permet que les fonctions documentaires,
niveau A au mieux.

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

    Python d'Aster ──► scripts/introspect_catalogue.py ──► JSON
                                   │
                                   ▼
                     data/processed/catalogue/<version>/*.json
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

### ADR-002 — Séparation des deux interpréteurs Python

**Décision.** Le paquet `aster_expert` n'importe jamais `code_aster`.
L'introspection du catalogue et l'exécution passent par des sous-processus
lancés avec le Python de l'installation Aster.

**Motif.** L'installation Code_Aster embarque fréquemment son propre
interpréteur et ses propres bibliothèques natives. Lier le projet à cet
interpréteur rendrait impossible l'installation des dépendances du projet, et
lierait le projet à une seule installation.

**Conséquence.** Les scripts destinés au Python d'Aster vivent dans `scripts/`,
n'ont aucune dépendance en dehors de la bibliothèque standard, et communiquent
exclusivement par JSON sur la sortie standard. Ils sont testables séparément.

### ADR-003 — Encapsulation de `run_aster`, pas de réimplémentation

**Décision.** L'exécution et le dépouillement s'appuient sur les modules
`run_aster.command_files`, `run_aster.status`, `run_aster.error_messages`,
`run_aster.export` et `run_aster.config`.

**Motif.** Ces modules sont livrés avec l'installation, suivent la version, et
couvrent déjà la préparation du fichier de commandes, l'état d'exécution et
l'extraction des messages d'erreur.

**Conséquence.** Un analyseur `.mess` propre au projet n'est écrit que pour ce
que ces modules ne couvrent pas — typiquement le relevé structuré des alarmes,
des durées par commande et des indicateurs de convergence. La lacune est
documentée avant d'être comblée.

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

### ADR-006 — Pas de conteneurisation initiale de l'exécution

**Décision.** L'exécution de Code_Aster se fait par sous-processus dans un
répertoire de travail dédié, avec limites de temps et de mémoire, sans Docker.

**Motif.** Le dépôt tourne déjà dans une machine virtuelle dédiée, qui fournit
l'isolation vis-à-vis du poste de travail. Empiler un conteneur dans la VM
imposerait la construction d'une image Code_Aster, pour un gain d'isolation
marginal.

**Conséquence.** `docker-compose.yml` n'est pas créé. L'isolation repose sur :
répertoire de travail éphémère, `timeout`, limites `resource` du sous-processus,
et refus d'exécuter un fichier situé hors des répertoires autorisés.

**Révision.** À reconsidérer si le projet doit tourner sur une machine
partagée ou exécuter des fichiers d'origine non contrôlée.

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
| `agent/` | Schémas de réponse, niveaux de validation, formats de citation |
| `mcp/` | Exposition des fonctions ci-dessus comme outils MCP |

`agent/` ne contient pas de logique d'appel à un modèle. Le projet produit des
outils et des données ; l'orchestration conversationnelle reste en dehors tant
que le périmètre n'est pas étendu.

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
