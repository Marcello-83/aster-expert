# Lot 41 bis — Mise en conformité avec Ubuntu 26 et Python géré par le projet

## Objet

La VM est passée d'Ubuntu 24.04 à Ubuntu 26.04 (2026-09-30) : `python3.12` a été
retiré, le `.venv` du projet a basculé sur Python 3.14 et ne trouvait plus ses
paquets, le serveur MCP ne démarrait plus. Ce lot :

1. établit le diagnostic de l'environnement (`docs/environnement.md`, § 1) ;
2. rend le projet indépendant du Python du système (Python 3.12 géré par `uv` dans
   l'espace utilisateur, dépendances verrouillées par `uv.lock`) ;
3. ajoute `aster-expert env-check`, première commande de chaque lot ;
4. rejoue les vérifications du lot 41 sous le nouvel environnement (chaîne du
   quai avec une exécution du modèle complet, contrôles, rejeu des constats).

Code_Aster 17.4.0 (`simvia/code_aster`, digest `sha256:d8d19ea9…`), Salomé-Méca
V2024.1.0. Niveau visé sur le modèle complet : **C avec contrôles D**, jamais E.
Aucune modification du comportement du quai, de la fiche ou des outils MCP.

## Critère de non-régression (écrit avant l'exécution, 2026-10-01T03:12-04:00)

### Références

- Les **26 références du lot 41** (`projets/quai_cw_test_01/references/`,
  `empreintes.json`), inchangées.
- **Nouvelles références** pour les 2 fichiers en échec formel au lot 41
  (`projets/quai_cw_test_01/references/lot41bis/`, `empreintes.json`) :
  - `maillage/combiwall_mesh_invariants.yaml` (SHA-256 `abf80326…`) ;
  - `ferraillage/poutre.comm` (SHA-256 `c0596fed…`).

  Ce sont les sorties du lot 41 telles qu'elles existaient avant ce lot (le premier
  versionné au commit `1d38cc9`, le second produit par l'étape `ferraillage` du
  2026-09-29T07:42-04:00 sous Python 3.12 du système), copiées sans modification.
  **Justification** : au lot 41, ces deux fichiers ne différaient de leur référence
  que par une ligne de commentaire nommant le producteur (chemin du script après
  déplacement dans `projets/`), que le critère du lot 41 n'énumérait pas ; aucune
  valeur ne différait. Une référence qui porte l'ancien chemin du producteur ne
  peut plus jamais être reproduite par le code actuel : la référence pertinente
  pour juger un changement d'environnement est la sortie du code actuel sous
  l'ancien environnement. Le critère du lot 41 et son verdict (échec formel sur
  2 fichiers) **ne sont pas réécrits**.

### Critère

La chaîne du quai est rejouée par `aster-expert projet quai_cw_test_01 <étape>`
avec **une nouvelle exécution du modèle complet**, sous le `.venv` reconstruit
(Python 3.12.14 géré par `uv`). Puis :

1. **Comparaison du lot 41, inchangée** (`comparer_references_lot41.py`, même
   classement) : les **18 fichiers identiques à l'octet** au lot 41 doivent le
   rester ; les **6 fichiers « admis »** ne doivent différer de leur référence que
   par les chemins et empreintes énumérés par le critère du lot 41 ; les 2 fichiers
   en échec formel doivent présenter **exactement les mêmes lignes non énumérées**
   qu'au lot 41 (en-tête du producteur), rien d'autre.
2. **Nouvelles références** : les 2 fichiers ci-dessus doivent être **identiques à
   l'octet** à `references/lot41bis/`.
3. Toute valeur numérique différente, même au dernier chiffre imprimé, et toute
   autre différence est un **échec**, rapporté tel quel.

Les 54 vues PNG restent hors critère (information seulement).

## Étape 0 — Diagnostic

`docs/environnement.md`, § 1 (relevé avant toute correction). Seul le Python du
projet était cassé (`.venv` passé à 3.14, paquets sous `lib/python3.12`) ; Docker
(`docker.io` 29.1.3, sans `sudo`), `cave` 0.1.4, l'image `simvia/code_aster:17.4.0`
(digest conforme), Singularity 4.3.7 et l'image Salomé (maillage d'un cube sans
interface), le partage `/media/sf_partage` fonctionnaient. Aucune intervention
système n'a été nécessaire.

## Étape 1 — Python géré par le projet

`docs/environnement.md`, § 2 : `uv` 0.12.21 dans `~/.local/bin` ; `.python-version`
= `3.12` ; `[tool.uv] python-preference = "only-managed"` ; Python 3.12.14 géré par
`uv` ; `.venv` recréé par `uv sync --locked` (tous les extras) ; `uv.lock` versionné,
aux versions exactes de l'ancien `.venv` (62 paquets, aucun écart). Évaluation de
3.14 (environnement temporaire, mêmes versions) : `pytest tests/unit` → **789 passed
in 23.78s** ; environnement supprimé, 3.14 non adopté.

## Étape 2 — `env-check`

`aster_expert.environnement.verification`, commande `aster-expert env-check`,
31 tests (`tests/unit/test_env_check.py`), section `environnement.partage` de
`config/validation.yaml`. Sortie réelle (2026-10-01) :

```
  OK python : 3.12.14, .venv sur /home/ubuntu/.local/share/uv/python/cpython-3.12.14-linux-x86_64-gnu
  OK dependances : 61 distributions conformes à uv.lock, 14 dépendances directes, 17 modules importés
  OK docker : démon 29.1.3, sans sudo
  OK cave : cave 0.1.4, version 17.4.0 (global)
  OK image : simvia/code_aster:17.4.0 sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5
  OK salome : singularity-ce version 4.3.7-noble, image salome_meca.sif V2024.1.0_scibian_univ
  OK partage : /media/sf_partage/echanges, écriture possible
  OK mcp : /home/ubuntu/projets/aster-expert/.venv/bin/aster-expert-mcp, module serveur importable
env-check OK : 8 vérifications.
```

Écart provoqué (`ASTER_IMAGE_REF=16.8.0`) : quatre `OK`, puis
`env-check ÉCHEC : image : image simvia/code_aster:16.8.0 de digest sha256:480eff5a…,
config/versions.yaml attend sha256:d8d19ea9…`, `Non évalués : salome, partage, mcp`,
code 1, sans trace Python.

## Étape 3 — Reprise du lot 41

### Chaîne du quai (2026-10-01, 03:14 à 03:19)

`aster-expert projet quai_cw_test_01 <étape>`, une étape par commande :

| Étape | Résultat |
| --- | --- |
| `verifier` | déclaration cohérente, fiche 63 entrées, aucun bloqueur |
| `maillage` | MED vérifié du cache (`20260922T071600-8d931d77`), Salomé non relancé ; `mesh check` 599/599 |
| `generer` | `resultats/complet.comm`, SHA-256 `683ebc23…` (le même qu'au lot 41) |
| `valider` | niveau B, `valid=True`, 265/265 commandes, 0 erreur |
| `executer` | **une exécution du modèle complet** : `completed_ok` (`OK`), 169,6 s, 0 alarme, 0 erreur (`data/processed/runs/20261001T071428-babb7e8c/compte_rendu.md`) |
| `controles` | équilibre, pesanteur, symétrie : RÉUSSI (`equilibre.json` et `integrale.json` identiques à l'octet à ceux du lot 41) |
| `synthese` | source MED, écart MED/`.mess` 4,81e-13, 54 vues |
| `combinaisons` | 18 combinaisons |
| `ferraillage` | 128 sections × 14 combinaisons ; contrôle du module : 63 comparaisons, 2 échecs dans le critère (les mêmes qu'aux lots 39 et 41, au bollard) |

### Comparaison (`projets/quai_cw_test_01/scripts/comparer_references_lot41bis.py`)

Sorties : `projets/quai_cw_test_01/references/lot41bis/comparaison.json` et
`comparaison_critere_lot41.json` (script du lot 41, inchangé).

- Critère du lot 41 rejoué tel quel : **18 identiques, 6 différents par des chemins
  et empreintes énumérés, 2 échecs formels** (`maillage/combiwall_mesh_invariants.yaml`,
  `ferraillage/poutre.comm`) — exactement le bilan du lot 41 ; vues 54/54.
- Les 2 échecs formels portent **les mêmes lignes non énumérées** qu'au lot 41
  (en-tête du producteur), rien d'autre.
- Nouvelles références : les 2 fichiers sont **identiques à l'octet** à
  `references/lot41bis/` (`abf80326…`, `c0596fed…`).
- Bilan du critère du lot 41 bis : **28/28 lignes réussies**.

Information hors critère : les 86 fichiers de `resultats/` comparés à la copie des
sorties du lot 41 faite avant l'exécution : **79 identiques à l'octet**, 7
différents uniquement par le répertoire d'exécution, les empreintes du `.mess` et du
MED, les dates (`etat.json`, `validation.json` : `checked_at`,
`poutre_couronnement.md`, `synthese.json`, `synthese.md`, `rapports/executions.json`,
`rapports/mess_ferr_extrait.txt`). Aucune valeur numérique ne diffère.

## Étape 4 — Rejeu des constats

Les six cas du lot 35 des constats CA-029, CA-034, CA-035, CA-036 lisaient tous le
maillage du quai réduit du lot 30 (`quai_reduit.mmed`, SHA-256 `507a0942…`, relevé
sur les six répertoires d'exécution d'origine du 2026-09-24). Script
`projets/quai_cw_test_01/scripts/versionner_maillages_lot41bis.py` : à côté de chaque
cas, `<cas>.mmed` (copie à l'octet, un seul objet Git) et `<cas>.export` (paramètres
des `.export` d'origine) ; cas inchangés (empreintes des constats vérifiées).
`data/examples/lot35_constats` ajouté à `execution.allowed_roots`.

`aster-expert constats rejouer --sortie connaissances/constats_code_aster/rejeu`
(2026-10-01, 5 min 42 s) : **18/18 constats établis par exécution tiennent**, 47 cas
rejoués sur 47 (339,9 s d'exécution cumulée), 0 non rejouable, à réexaminer : aucun.

### Test adapté

`tests/unit/test_constats.py::test_cases_without_their_mesh_are_reported_not_replayable`
vérifiait la règle « `LIRE_MAILLAGE` sans `.export` voisin → non rejouable » sur
CA-034 **dans le dépôt** : il a échoué au premier passage des contrôles après le
versionnement des maillages (`assert {'rejoué'} == {'non rejouable'}`). La règle
est inchangée ; le test la vérifie désormais sur une copie temporaire contenant les
cas sans `.export`, et un nouveau test
(`test_lot41bis_cases_are_replayed_with_their_versioned_mesh`) vérifie que les six
cas de CA-029/034/035/036 sont rejoués avec leurs `.export` et `.mmed`.

## Contrôles (passage final, 2026-10-01)

| Commande | Sortie |
| --- | --- |
| `aster-expert env-check` | « env-check OK : 8 vérifications. » |
| `aster-expert mcp-check` | « mcp-check OK : 8 outils appelés sur un serveur neuf, identiques aux outils du code. » |
| `ruff format --check` | « 375 files already formatted » |
| `ruff check` | « All checks passed! » |
| `pytest tests/unit` | « 821 passed in 12.12s » |
| `pytest` | « 1196 passed, 3 deselected in 68.88s » |
| `pytest -m lent` | « 3 passed, 1196 deselected in 25.11s » (Code_Aster et Salomé réellement lancés) |
| `mypy src` | « Success: no issues found in 99 source files » |
| `mypy` | « Success: no issues found in 266 source files » |

## Verdict

- Non-régression du quai : **réussite** au regard du critère écrit avant
  l'exécution (28/28). Le verdict du lot 41 (échec formel sur 2 fichiers au regard
  de son propre critère) n'est pas réécrit.
- Niveau atteint sur le modèle complet sous le nouvel environnement : **C avec
  contrôles D**, jamais E.
- Constats : 18/18 tiennent sous Code_Aster 17.4.0.

## Lecture

**Faits.** Le changement d'OS n'a touché que le Python du projet ; avec le même
`.comm` (`683ebc23…`), la même image et les mêmes versions de dépendances, la
chaîne redonne les mêmes valeurs à l'octet. Python 3.14 passe les 789 tests
unitaires avec les versions verrouillées.

**Déductions.** La reproductibilité tient à trois empreintes désormais toutes
vérifiées par `env-check` : interpréteur (`.python-version`), dépendances
(`uv.lock`), image (digest). Salomé n'a été relancé que par `pytest -m lent` (la
chaîne du quai lit le MED vérifié du cache) : le maillage complet du quai (~17 min)
n'a pas été refait sous Ubuntu 26.

**Recommandations.** Lot 42 : reprendre la trace ENV-001 (`docs/environnement.md`,
§ 4) comme diagnostic. Passage à 3.14 : lot à part (`pytest` complet, `mypy`,
`pytest -m lent`, serveur MCP non évalués sous 3.14).

## Limites

- `env-check` ne peut rien dire si `aster-expert` lui-même ne démarre pas.
- Docker (`docker.io`) et `singularity-ce` (paquet tiers `-noble`) restent des
  paquets système exposés à une mise à niveau.
- Maillage complet du quai non refait sous Ubuntu 26 (cache utilisé, comme au
  lot 41) ; Salomé éprouvé par la géométrie minimale de `pytest -m lent` et par la
  sonde du diagnostic.
