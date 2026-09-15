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

## Fin de lot

Un lot n'est terminé qu'avec :

1. l'inventaire des fichiers créés ou modifiés ;
2. la justification des choix techniques ;
3. la liste des tests exécutés et leurs résultats exacts ;
4. les limites connues et les points non couverts ;
5. un commit Git distinct.

## Périmètre à ne pas dépasser sans instruction

Une session traite un lot et un seul. Ne pas anticiper les lots suivants, ne
pas installer d'infrastructure non demandée, ne pas inventer la structure d'un
dépôt externe avant de l'avoir inspectée.
