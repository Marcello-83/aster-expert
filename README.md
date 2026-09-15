# AsterExpert

Agent expert Code_Aster : recherche traçable dans le corpus officiel,
extraction des schémas exacts des commandes depuis le catalogue installé,
analyse et validation de fichiers `.comm`, exécution encadrée et dépouillement
des fichiers `.mess`.

Ce dépôt n'est pas un assistant généraliste. Il ne produit que des réponses
rattachées à une version de Code_Aster identifiée et à une source citable.

## Prérequis

- Machine virtuelle Ubuntu 24.04 avec une installation Code_Aster fonctionnelle.
- `run_aster` accessible dans le `PATH` de l'environnement Aster.
- Python 3.12 ou supérieur pour le projet (distinct du Python d'Aster).
- Git, et un accès réseau à `gitlab.com` pour la synchronisation du corpus.

## Installation

```bash
git clone <url-du-depot> aster-expert
cd aster-expert
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Renseigner ensuite `.env`, en particulier le chemin de l'environnement
Code_Aster.

## Première étape : identifier l'installation

Aucune commande de génération ou de validation ne fonctionne tant que la
version cible n'est pas résolue.

```bash
aster-expert env detect
```

Cette commande exécute un script d'introspection avec le Python d'Aster et
écrit le résultat dans `config/versions.yaml`, section `detected`. Elle relève :

- la version rapportée par `run_aster` ;
- le chemin du package `code_aster` ;
- le chemin du catalogue ;
- la révision de l'installation lorsqu'elle est disponible.

En cas d'échec, corriger `.env` avant de poursuivre. Ne jamais compléter
`config/versions.yaml` à la main avec une version supposée.

## Utilisation

```bash
# Synchroniser les dépôts officiels sous external/
aster-expert sources sync

# Extraire les schémas de commandes du catalogue installé
aster-expert catalogue extract

# Interroger le corpus
aster-expert search "ressort non linéaire unilatéral" --version 18

# Schéma exact d'une commande
aster-expert catalogue show STAT_NON_LINE --keyword COMPORTEMENT

# Validation statique d'un fichier de commandes
aster-expert validate model.comm

# Exécution encadrée puis dépouillement
aster-expert run model.comm --timeout 1800
aster-expert mess analyze resultats/model.mess
```

Les commandes non encore implémentées sont listées dans
`docs/development-plan.md` avec leur lot d'appartenance.

## Structure

```
config/      paramètres de sources, versions, recherche et validation
data/        corpus brut, corpus transformé, index, jeux d'évaluation
external/    clones des dépôts Code_Aster (non versionnés)
docs/        architecture, corpus, métadonnées, plan de développement
src/         code du projet
scripts/     scripts autonomes, dont ceux exécutés par le Python d'Aster
tests/       tests unitaires, d'intégration et d'évaluation
```

## Niveaux de validation

Toute réponse produite par le système porte un niveau :

| Niveau | Signification |
|--------|---------------|
| A | Réponse documentaire, non exécutée |
| B | Syntaxe confrontée au catalogue |
| C | Fichier exécuté jusqu'à `FIN` |
| D | Résultats soumis à des contrôles physiques |
| E | Résultats comparés à une référence validée |

## Contribution

Les règles permanentes du dépôt sont dans `CLAUDE.md`. Elles s'appliquent aux
contributions humaines comme aux contributions assistées.

## Licences

La licence du code de ce dépôt reste à choisir : ajouter un fichier `LICENSE`
et décommenter le champ correspondant dans `pyproject.toml` avant toute
diffusion. Les dépôts Code_Aster clonés sous `external/` conservent leurs licences propres
(GPL v3 pour les sources, GFDL v1.3 pour la documentation) et ne sont pas
redistribués par ce projet.
