# Lot 46 — Socle : sécurité MCP, intégration continue, état versionné, trace des connaissances

Profil `cloud`. Branche `claude/lot-46-securite-mcp-wakze8` (imposée par la session ; la consigne
nomme `lot-46`). Aucun envoi sur `main`, aucun résultat d'ouvrage changé, aucune attribution
rétroactive d'épreuve. Consigne : `docs/lots/lot46_consigne.md`.

## 1. Décisions appliquées

- **PRE-032 (Es = 200 GPa)** : texte de MM recopié à l'identique (`arbitrage_combiwall_MM_lot46_Es.md`,
  décision 22 du fichier) ; la fiche du quai est régénérée par `build_combiwall_reference.py` (jamais
  éditée à la main), le texte du lot 45 passe dans `decision_history`, PRE-032 est reconstruit depuis
  la fiche. L'entrée reste « en révision » (bloqueur de génération visible) : le quai n'est pas
  recalculé et porte encore 210 GPa dans ses résultats. La note d'hypothèses du quai est régénérée.
- **Interventions du lot 45 = 1** : déclarée au registre de la dalle (le seul où le lot 45 figurait,
  « non renseigné »), sans recalcul des métriques (`declared_interventions_since_baseline` 2 → 3,
  `measured` inchangé). Le registre du quai n'a pas d'entrée pour le lot 45 : je n'y ai rien ajouté,
  pour ne pas compter deux fois une seule intervention. À corriger si MM la voulait aussi au quai.
- **Marqueurs `[À CONFIRMER MM]`** : `check_markers` distingue le texte en vigueur (tout marqueur,
  brut ou cité entre guillemets, fait échouer) de l'historique (annexe des révisions : accepté
  seulement cité entre guillemets ; brut, il échoue) ; `check_sheet_markers` refuse un marqueur dans
  une décision en vigueur de la fiche. 9 tests (`tests/unit/test_notes_marqueurs.py`).

## 2. Politique de lecture

`aster_expert.chemins.resolve_input_path` : liens symboliques et `..` résolus, puis racines, puis
extension, puis existence (un refus hors racine ne révèle pas l'existence du fichier). Politique de
lecture : `config/chemins.yaml` (config, connaissances, data, docs, projets, scripts, src, tests,
external ; ni `.git`, ni `.venv`, ni `.env`). Politique d'exécution : `execution.allowed_roots`,
inchangée, mais passée par la même fonction (`check_allowed`).
Appliquée à : `analyze_comm`, `validate_comm` (`.comm`) ; `read_test_case` (déjà confiné au corpus,
liens suivis) ; commandes `comm parse`, `validate`, `run`, `mesh run`/`check`, `report`, `generate`,
`fiche obligatoires`, `eval` (entrées), `connaissances eprouver`. Les sorties (écriture) ne sont pas couvertes.
**Déclarer une racine externe** (lecture seule, sans copie) : dans `config/chemins.local.yaml`
(non versionné, refusé par le contrôle de publication), `lecture: {racines_externes: [/chemin]}` ;
le refus affiche la racine manquante et cet exemple. Tests : `../../x.comm`, absolu hors racine,
lien hors racine, racine externe (local et versionné), extension, existence, politique d'exécution,
outils MCP, commande CLI (18 tests, `tests/unit/test_chemins.py`). `mcp-check` : sa sonde écrit
désormais sous `data/processed/mcp_check/` (un `/tmp` serait refusé). **Les outils MCP ont changé :
redémarrer la session avant le lot suivant.** Piège rencontré : après toute modification de
`pyproject.toml`, `mcp-check` exige un `uv sync --locked --all-extras` préalable (sinon `uv run`
reconstruit le projet sans accès réseau et la connexion se ferme).

## 3. Intégration continue

`.github/workflows/ci.yml` (pull request ; envois sur `lot-*` et `claude/lot-*`, la branche de travail
d'une session Cloud) : `uv sync --locked --all-extras`, `ruff format --check`, `ruff check`,
`mypy src`, `mypy`, `pytest` hors tests lents, contrôle de publication (`--arbre`), `pip-audit` non
bloquant (résumé de l'exécution). `ci-lent.yml` : `workflow_dispatch`, image tirée par digest lu de
`config/versions.yaml`, `catalogue extract`, `pytest -m lent_aster`. **Non déclenché** : aucune
exécution n'a été lancée (non essayé, la branche n'est pas la branche par défaut) ; à lancer par MM
(Actions > ci-lent > Run workflow). Premier workflow : **déclenché par chaque envoi** et lu par l'API
GitHub. Passages : n°1 échec (un test dépendant du catalogue, absent d'un runner neuf, corrigé), n°4
échec (test de `projet creer` que je n'avais pas lancé avant l'envoi, corrigé), n°3, 5 et 6 verts
(n°2 annulé par concurrence). **Durée : 2 min 12 s à 2 min 28 s** par passage (un seul job). **Coût
dépôt privé** : facturé à la minute entamée, soit 3 min par passage ; une offre à 2 000 min/mois en
autorise environ 650 (à rapprocher de l'offre réelle de MM, non connue de la session) ; les envois
sur une branche qui a aussi une pull request s'annulent (concurrence). `pip-audit` : une faille connue,
`pyjwt 2.14.0` (PYSEC-2026-4141, correctif 2.15.0), dépendance transitive de `mcp` ; non traitée
(signalement seulement). Avertissement GitHub : Node.js 20 déprécié pour `checkout@v4` et `setup-uv@v6`.
Les versions des actions (`@v4`, `@v6`) n'ont pas été comparées aux dernières publiées.
Règle ajoutée à `CLAUDE.md` : MM ne fusionne que si l'intégration continue est verte.

## 4. État versionné

`docs/etat.yaml` (50 lots relevés dans `git log` et les consignes ; 13 capacités avec niveau et preuve ;
2 projets ; liens vers les métriques) ; `aster_expert.etat`, `aster-expert etat readme|verifier` ;
section « État du projet » du README générée, test de divergence (`tests/unit/test_etat.py`).
Constats : l'historique publié commence au lot 8 (les lots 1 à 7 et 9 à 10c n'ont pas de commit
consultable, `commit: null`) ; le journal d'origine disait « à faire » les lots 5 et 6, qui ont une
clôture dans `development-plan.md` ; le lot 13 (hook `PostToolUse`) n'existe pas dans
`.claude/settings.json`, le lot 12 est partiel. Aucun commit de fusion (fusion en avance rapide) :
`commit` est celui qui porte le compte rendu. Journal de `development-plan.md` remplacé par un renvoi.
`requires-python = ">=3.12,<3.13"` ; `uv lock` : seuls les marqueurs de résolution disparaissent,
aucune version modifiée. Règle `CLAUDE.md` : tout lot met à jour `docs/etat.yaml`.

## 5. Archive d'exécution et `rex`

Le registre de chaque projet porte un manifeste (`archive` : nombre d'exécutions du projet, empreinte
de la liste triée), miroir dans `data/processed/runs/manifeste.json`. Une archive est conforme si les
`n` plus anciennes exécutions du projet ont l'empreinte (les nouvelles s'ajoutent à la fin). Absente,
partielle ou non conforme : `rex` le dit, n'écrit pas les métriques mesurées, ne met à jour que les
champs déclarés (interventions, erreurs évitées, baseline), `connaissances verifier` classe les sources
d'exécution en « non vérifiables », les tests dépendants s'ignorent avec le motif. Sortie réelle dans
le Cloud (une exécution fraîche présente dans `runs/`) :

    Archive d'exécution refusée : aucun manifeste versionné dans le registre du projet (archive non
    vérifiable ; dans la VM : `aster-expert rex <projet> --manifeste`). Aucun échec examiné, métriques
    mesurées ni recalculées ni écrites ; seuls les champs déclarés (interventions, erreurs évitées,
    notes) sont mis à jour.
    Champs déclarés seuls mis à jour : connaissances/metriques/dalle_appuyee_01.yaml

Vérifié : `measured` et `knowledge` du fichier de métriques inchangés. **Action pour MM, dans la VM,
avant le prochain lot** : `aster-expert rex quai_cw_test_01 --manifeste` et `... dalle_appuyee_01
--manifeste` (archive complète) ; jusqu'à là, la VM ignore aussi les tests dépendants de l'archive.
Contournement du lot 45 retiré de `CLAUDE.md`. Aucun manifeste n'a été écrit : l'archive complète
n'est pas dans le Cloud et je ne l'invente pas.

## 6. Trace des connaissances appliquées

**Forme** : fichier compagnon `<nom>.connaissances.yaml` à côté du `.comm`, recopié dans
`compte_rendu.json` (`knowledge`). Pas d'en-tête du `.comm` : le `.comm` de projet est généré, comparé
à l'octet, et la règle de conservation lit ses commentaires ; une déclaration qui n'est pas du calcul
n'a rien à y faire, et le compagnon est validé et refusé *avant* le conteneur. Une exécution de projet
(`.comm` sous `projets/<nom>/`) sans déclaration est refusée ; les autres peuvent déclarer. Pour la
chaîne : `knowledge_applied` dans `projet.yaml`, copié à chaque `executer`. Skill § 6 quinquies :
déclaration obligatoire ; `rex` signale toute exécution de projet sans déclaration depuis le lot 46
(`declaration_required_since`, aucune exécution passée touchée).
**Règles d'épreuve** (`connaissances.epreuve`, `aster-expert connaissances eprouver`) : constat jamais
par déclaration (rejeu de son cas) ; patron : exécution réussie dont les contrôles D du projet, liés à
ses résultats par empreintes, passent ; contrôle : présent et RÉUSSI dans `harness.controls` de cette
exécution (un échec sur défaut corrigé est seulement *proposé* à MM) ; référence : rejeu réussi d'un de
ses cas (`.comm` identique par empreinte), niveau C ; précédent jamais ; diagnostic aucune règle.
Un patron ou un contrôle éprouvé reçoit une réutilisation, jamais une promotion.
**Test dans le Cloud** (`pytest -m lent_aster`, `test_a_declared_replay_of_the_slab_proves_its_reference_only`) :
rejeu de `dalle_h0p125.comm` avec sa déclaration (23,9 s, `completed_ok`) :

    REF-014 : ÉPROUVÉ (niveau C) -- rejeu réussi du cas versionné ...dalle_h0p125.comm (empreinte identique)
    PAT-009, PAT-011 : non éprouvé -- aucun résultat de contrôle D
    CTL-010 : non éprouvé -- aucun résultat de contrôle D

Rien n'a été inscrit dans la base (REF-014 est déjà promue, de son projet d'origine).
Limites : le cas d'un contrôle en échec sur défaut corrigé n'est pas vérifiable par la machine ;
les contrôles D d'une exécution du Cloud ne sont pas disponibles (la chaîne complète exige Salomé).
Les déclarations de chaîne (dalle : 9 entrées, quai : 7) sont de la session, d'après les réutilisations
déjà consignées : elles ne prouvent rien.

## 7. Harnais D par défaut

`aster_expert.controles.harnais`. Les quatre contrôles génériques demandés : équilibre global =
CTL-005 et symétrie = CTL-006 (déjà dans la base, non réécrits) ; convergence de maillage = CTL-012
(déjà dans la base, rendu générique : le projet fournit la série `controls.convergence`, le tronc
commun juge ; implémentation déplacée dans `src/`) ; **CTL-013 nouveau** : résultante de chaque cas
comparée à la charge déclarée. Drapeau `default_harness` posé sur CTL-005, CTL-006, CTL-012 ; CTL-013
est appliqué d'office mais non promu. Désactivation : `controls.disabled` de `projet.yaml`, motif écrit
obligatoire ; la note de résultats l'affiche, et son contrôle échoue s'il manque. Un contrôle qui ne
s'applique pas le dit (`NON APPLICABLE`) ; niveau E visé sans série déclarée : ÉCHEC, jamais un silence.
**Vérification sans exécution, relecture des paquets** : `summarize` appliqué à `equilibre.json` de
chaque paquet redonne exactement les champs équilibre, pesanteur, symétrie, informatif et verdict du
`controles_d.json` du paquet (dalle et quai) ; CTL-013 RÉUSSI aux deux (écarts 0 et 2,1e-12) ;
CTL-012 RÉUSSI à la dalle (erreur maximale au maillage fin 5,2e-4, seuil 1e-2) et non applicable au
quai. Les paquets versionnés n'ont pas été réexportés (pas de résultats dans le Cloud) : ils ne portent
donc pas encore la clé `harness`. Limite : la série de la dalle vient du rejeu du lot 45, non d'une
exécution du lot.

## 8. Contrôles (profil cloud)

    aster-expert env-check          OK (profil cloud : 8 vérifications, 3 absences attendues)
    aster-expert mcp-check          OK (9 outils appelés sur un serveur neuf)
    ruff format --check             489 fichiers déjà formatés
    ruff check                      All checks passed
    mypy src                        Success, 130 fichiers
    mypy                            Success, 349 fichiers
    pytest tests/unit               1107 réussis
    pytest                          1529 réussis, 6 ignorés (motifs lisibles), 4 écartés, 2 min 45 s
    pytest -m lent_aster            3 réussis (30 s)
    aster-expert connaissances verifier   OK, 252 preuves confrontées, 39 sources d'exécution non vérifiables
    aster-expert etat verifier      cohérent
    rex (écriture de métriques)     non lancé comme tel : refus montré en 5

Intégration continue sur la branche : verte au dernier passage (n°6, 2 min 28 s).
**Interventions de MM pendant le lot : 0** (les trois décisions étaient dans la consigne).
`aster-expert rex <projet>` : sorties en 5 ; le lot ne crée aucun échec d'exécution à classer
(trois exécutions Code_Aster du Cloud, toutes `completed_ok`, hors archive complète).
**Connaissances ayant évité une erreur** : aucune déclarée (le lot n'écrit aucune commande d'ouvrage).
Limites générales : politique de lecture et sorties ; `ci-lent.yml` non essayé ; manifestes à enregistrer
dans la VM ; quai non recalculé (Es), décision en révision.
