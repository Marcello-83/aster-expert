# Lot 41 ter — Dépôt GitHub privé et sessions Cloud

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français : terminal,
résumé final, compte rendu, commit, rapports, commentaires.

## Contexte

MM veut héberger le dépôt sur son GitHub pour pouvoir lancer des sessions
Claude Code dans le Cloud (navigateur, téléphone, `claude --cloud`), en plus de
la VM.

Faits établis par Claude dans la documentation Claude Code (pages « Use Claude
Code in the cloud » et « Configure cloud environments ») :

- **Accès au dépôt.** Une session Cloud clone le dépôt depuis GitHub. Il faut
  pour cela l'application GitHub Claude installée sur le dépôt, ou une connexion
  par `/web-setup` depuis le terminal.
- **Machine.** 4 vCPU, 16 Go de RAM, 30 Go de disque. **Docker est
  disponible.** Le réseau par défaut, dit « Trusted », autorise PyPI, Docker Hub
  et gitlab.com.
- **Script d'installation.** Un script s'exécute avant chaque session. Il n'est
  mis en cache que s'il dure moins de cinq minutes environ. Le cache conserve
  les fichiers, dont les images Docker tirées, mais pas les processus.

**Conséquences pour AsterExpert, à vérifier dans ce lot :**

- Code_Aster devrait pouvoir tourner dans le Cloud, en tirant l'image
  `simvia/code_aster` par son digest.
- **Salomé, non** : l'image `salome_meca.sif` est un fichier local de plusieurs
  Go, sur aucun registre. Le maillage reste donc réservé à la VM.
- Le corpus documentaire se clone depuis gitlab.com, au commit figé.

## Étape 0

`aster-expert env-check`, puis `aster-expert mcp-check`.

## Étape 1 — Ce qui ne doit pas quitter la machine (critère bloquant)

Avant toute publication, inventorie **le répertoire de travail et tout
l'historique Git** :

1. **Secrets** : jetons, mots de passe, clés, variables d'environnement
   sensibles. Recherche par motifs ; un outil dédié peut être lancé avec
   `uv tool run` s'il est disponible.
2. **Fichiers interdits par les règles du projet** :
   - fichiers de MM (`calcul_3d_v3/v5/v5_sismique` et toute donnée PANG) ;
   - texte de la NF P 94-282 ou de toute norme AFNOR. Les articles peuvent être
     cités, le texte ne doit pas être reproduit.
3. **Fichiers volumineux** : tout fichier de plus de 50 Mo, dans l'arbre comme
   dans l'historique. GitHub refuse les fichiers de plus de 100 Mo. Sont
   concernés notamment les MED de résultats, les archives d'exécution, le corpus
   documentaire, les sources Code_Aster et les images.
4. **Corpus et sources externes** (`codeaster-doc`, `codeaster-src`) : ils ne
   sont pas publiés et se reconstruisent par clonage au commit figé.

**Si l'historique contient un élément des catégories 1 ou 2, arrête-toi sans
rien publier** et rapporte-le. Réécrire l'historique est une décision de MM. Les
éléments de la catégorie 3 présents seulement dans l'arbre sont exclus par
`.gitignore`. S'ils sont dans l'historique, arrête-toi aussi.

Écris le résultat dans `docs/publication_github.md`.

## Étape 2 — Création du dépôt privé (avec MM)

1. Vérifie la présence de `gh`. S'il est absent, installe-le dans l'espace
   utilisateur. Sinon, décris à MM l'installation par paquet, sans la faire.
2. **MM** exécute `gh auth login` lui-même, dans le terminal de la VM : la
   session ne manipule aucun identifiant.
3. Ensuite, la session crée le dépôt **privé** `aster-expert` et pousse `main`.
   Vérifie dans la documentation de `gh` la syntaxe exacte, ne la suppose pas.
   Vérifie aussi que le dépôt est bien privé, en relisant sa visibilité
   effective.
4. Décris à MM comment installer l'application GitHub Claude sur ce seul dépôt,
   et non sur tout son compte.

## Étape 3 — Profils d'environnement : VM et Cloud

1. `env-check` détecte le profil (`vm` ou `cloud`). Dans le Cloud, l'absence de
   Salomé et du dossier partagé est **attendue** et signalée comme telle, pas
   comme une erreur.
2. Scinde les tests réels en deux marqueurs, `lent_aster` (Docker et image
   Code_Aster) et `lent_salome` (image Salomé). Chacun est ignoré avec un motif
   lisible quand sa ressource manque.
3. `.mcp.json` doit fonctionner dans les deux profils. Le chemin par défaut
   actuel, `/home/ubuntu/projets/aster-expert`, n'existe pas dans le Cloud.
   Établis une commande de lancement portable, par exemple via `uv run` dans le
   répertoire du projet, en vérifiant dans la documentation MCP de Claude Code
   comment le répertoire de travail et les variables sont résolus. Puis teste-la
   dans la VM.
4. **Script d'installation Cloud** (`scripts/cloud_setup.sh`) :
   - installation de `uv` ;
   - `uv sync --locked --all-extras` ;
   - clonage du corpus documentaire au commit figé ;
   - construction de l'index ;
   - tirage de l'image Code_Aster **par digest**.

   Mesure sa durée dans la VM. Si elle dépasse cinq minutes, sépare la partie
   longue (image, index) en une étape lancée à la demande par la session, et
   documente-la.
5. `docs/cloud.md` : ce qu'on peut faire dans le Cloud (développement, tests,
   recherche documentaire, fiche, exécutions Code_Aster) et ce qui reste réservé
   à la VM (maillage Salomé, dossier partagé, MED volumineux). Avec le texte du
   script d'installation à coller par MM dans la configuration de
   l'environnement Cloud.

## Étape 4 — Règles de travail

À ajouter dans `CLAUDE.md` :

- **Un lot, une branche** (`lot-NN`), poussée sur GitHub. MM fusionne dans
  `main` après relecture du compte rendu. Une session Cloud ne pousse jamais
  directement sur `main`.
- En tête de lot, la session annonce son profil (`vm` ou `cloud`). Un lot qui
  exige Salomé ne se lance que dans la VM.
- Rien de ce qu'interdit l'étape 1 ne doit jamais être ajouté. Ajoute un test ou
  un crochet `pre-commit` qui refuse les fichiers de plus de 50 Mo et les motifs
  interdits.
- Le dossier `/media/sf_partage` reste la zone d'échange avec MM pour les
  livrables lourds. Les prompts et les comptes rendus peuvent désormais vivre
  dans `docs/lots/`.

## Étape 5 — Premier essai Cloud (lancé par MM après le lot)

Prépare dans `docs/cloud.md` le texte exact d'une première tâche Cloud, que MM
lancera depuis claude.ai/code sur la branche `lot-41ter`. Elle doit :

1. lancer `aster-expert env-check` en profil `cloud` ;
2. lancer `pytest tests/unit` ;
3. lancer `pytest -m lent_aster` (Code_Aster réellement exécuté) ;
4. lancer `aster-expert mcp-check` ;
5. rapporter, sans rien modifier, et en français.

Le compte rendu de cet essai me sera transmis : il dira si Code_Aster tourne
vraiment dans le Cloud, et en combien de temps l'environnement se prépare.

## Contrôles (dans la VM)

```bash
aster-expert env-check
aster-expert mcp-check
ruff format --check
ruff check
pytest tests/unit
pytest
pytest -m lent_aster
pytest -m lent_salome
mypy src
mypy
```

## Compte rendu attendu — EN FRANÇAIS

1. Inventaire de publication : secrets, fichiers interdits, fichiers
   volumineux, dans l'arbre et dans l'historique. Publié ou bloqué.
2. Dépôt : nom, visibilité vérifiée, branche.
3. Profils, marqueurs de tests, `.mcp.json` portable, script Cloud et sa durée.
4. Règles ajoutées et crochet de refus.
5. Texte de la tâche d'essai Cloud.
6. Résultats des dix commandes de contrôle.

## Interdits

- Aucune publication si l'étape 1 trouve un secret ou un fichier interdit,
  y compris dans l'historique.
- Aucun dépôt public.
- Aucune manipulation d'identifiant GitHub par la session : c'est MM qui
  s'authentifie.
- Aucune installation par `sudo` sans accord de MM.
