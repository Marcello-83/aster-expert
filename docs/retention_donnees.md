# Politique de rétention de `data/processed/` (lot 47 quater, ENV-003)

`data/processed/` n'est pas versionné. Au lot 47 ter, des copies de travail jamais
effacées y ont rempli le disque de la VM pendant deux exécutions (ENV-003). Cette page
dit, dossier par dossier, **ce qu'on garde**, **ce qu'on peut régénérer** et **qui peut
supprimer**. Règle générale : **aucune suppression sans l'accord de MM**, et jamais dans
`runs/` (consigne du lot 47 quater). Une copie n'est supprimée que vérifiée contre son
original (SHA-256), comme au lot 47 ter.

## Prévention

- `aster-expert env-check` vérifie l'espace libre en début de lot (vérification `disque` :
  10 Go en profil vm, 2 Go en cloud et ci) et affiche les ressources de la machine
  (vérification `ressources`).
- `aster-expert run` **refuse de démarrer** une exécution sous le seuil
  `execution.min_free_disk_gb` (10 Go, `config/validation.yaml`, surchargeable dans
  `config/machine.local.yaml`), avant tout conteneur : une exécution ne s'arrête plus en
  cours de route sur `No space left on device` en laissant un compte rendu vide.
- Les lectures de MED (`run_med_script`, `mesh check`) effacent leur copie de travail et
  leur extraction dès la lecture faite (lot 47 ter).

Ordre de grandeur (lot 47 ter et 47 quater) : une exécution complète de l'estacade écrit
1,5 à 2,4 Go dans `runs/` (MED de résultats `fort.80`), une exécution du quai 0,2 à
0,8 Go ; le seuil de 10 Go couvre au moins quatre exécutions lancées ensemble.

## Dossier par dossier

| Dossier | Contenu | Garder | Régénérer | Supprimer |
| --- | --- | --- | --- | --- |
| `runs/` | archive des exécutions (`aster-expert run`) : entrées, listings, MED de résultats, `compte_rendu.json` | **toujours**, en entier : sources d'exécution des constats, épreuves, manifeste de `rex` (lot 46), paquets de résultats | jamais à l'identique (date, identifiant) ; un `.comm` se rejoue, mais le rejeu est une autre exécution | **jamais** par une session ; si la place manque, MM décide (déplacement vers `/media/sf_partage` ou un disque d'archive) |
| `mesh_runs/` | sorties de Salomé (MED de maillage, journaux, `.meta.json`) | oui : cache des maillages vérifiés (`find_verified_mesh`) | oui, par `aster-expert mesh run` (même script, mêmes paramètres, même empreinte) ; le maillage de l'estacade à 0,05 m prend environ 10 s (lot 47 quater) | avec l'accord de MM, pour un maillage qu'aucun projet ne cite |
| `mesh_checks/` | rapports de `mesh check` et de lecture de MED (`rapport_mesh_check.txt`, `out.json`, `dump.json`) ; les copies `input.med` et `out.npz` sont effacées automatiquement depuis le lot 47 ter | les rapports | oui, en relançant `mesh check` | les 10 copies `input.med` antérieures au lot 47 ter sans original connu (36 Mo, `projets/estacade_pieux_01/resultats/lot47ter/plan_suppression.json`) : conservées tant que MM n'a pas statué |
| `catalogue/` | catalogue introspecté de la version installée | oui (niveau B) | oui, `aster-expert catalogue …` dans le conteneur | non |
| `fragments_by_*.jsonl`, `xref_graph.json`, `command_document_map.json` | index documentaire | oui (outils MCP) | oui, `aster-expert fragments …` puis `aster-expert index …` | non |
| `query_log.jsonl` | journal des requêtes (statistiques d'usage, candidats du banc) | **toujours** (journal, ajout seul) | non | jamais |
| `rejeu_constats/`, `rejeu_references/` | rapports de rejeu | le dernier | oui, `aster-expert constats rejouer`, rejeu des références | les anciens, avec l'accord de MM |
| `lot37_rapports/` | rapports d'archive du lot 37 | oui | non | non |
| `mcp_check/`, `workroot/` | répertoires temporaires des contrôles | non | oui | oui, à tout moment (vides en régime normal) |

## Ce qui n'est pas dans `data/processed/`

- `projets/<nom>/resultats/` (non versionné, sauf `resultats/paquet/`) : `.comm` générés,
  `.export`, copies de maillage et lectures ; régénérables par le générateur et les
  scripts de lot, mais les lectures (`lectures.json`, `controles.json`) se gardent jusqu'à
  la clôture du lot qui les cite.
- `resultats/paquet/` est versionné (lot 45) : c'est la seule source de résultats d'une
  session Cloud.
