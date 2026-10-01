# Publication sur GitHub (lot 41 ter)

Critère bloquant fixé par MM avant toute publication : aucun secret, aucun fichier
de MM, aucun texte de norme AFNOR, aucun fichier de plus de 50 Mo, **dans l'arbre
comme dans tout l'historique**. Un élément des deux premières catégories dans
l'historique, ou de la troisième dans l'historique, arrête la publication
(réécrire l'historique est une décision de MM).

Inventaire fait le 2026-10-01 sur le dépôt local au commit `3f52c07` (lot 41 bis),
arbre propre.

## 1. Périmètre examiné

- **Historique** : `git rev-list --all` → 65 révisions : les 63 commits de `main`
  (qui contiennent ceux des 12 branches locales `lot-2-env-detect` …
  `lot-7-retrieval`, toutes ancêtres de `main`) et les 2 commits de la remise
  `stash@{0}` du lot 25 ; 1 263 chemins distincts, 1 560 blobs distincts. Seules
  `main` et la branche du lot sont poussées ; la remise ne l'est pas, mais elle a
  été examinée aussi.
- **Arbre de travail** : fichiers versionnés, et fichiers ignorés pour vérifier
  qu'ils le restent.

## 2. Secrets — aucun

1. Recherche par motifs (`git grep` sur les 65 révisions) : jetons GitHub
   (`ghp_`, `github_pat_`, `gho_`), GitLab (`glpat-`), Anthropic (`sk-ant-`),
   OpenAI (`sk-`), AWS (`AKIA…`), Google (`AIza…`), Slack (`xox?-`), clés privées
   (`-----BEGIN … PRIVATE KEY`), `Bearer …`, affectations `password|secret|token|
   api_key = …`, identifiants dans une URL. **Un seul résultat, faux positif** :
   `src/aster_expert/ingestion/inventory.py:142`, variable Python
   `token = document_id.split(".", 1)[0]`.
2. Outil dédié : `detect-secrets` 1.5.0 (`uv tool run --from detect-secrets==1.5.0
   detect-secrets scan --all-files`) sur les 1 560 blobs de l'historique exportés
   dans un répertoire temporaire : 897 signalements, **tous des faux positifs** :
   - 873 « Hex High Entropy String » : empreintes SHA-256 (695) et SHA-1 (174) —
     clés `case_sha256`, `repo_commit`, `source_commit`, `sha256_reference`,
     `catalogue_hash`, `comm_sha256`, `image_sha256`, … — et 4 empreintes tronquées
     à 16 caractères dans `versionner_maillages_lot41bis.py` ;
   - 24 « Base64 High Entropy String » : chemins de travail horodatés
     (`data/processed/runs/20260929T114036-62fb0a58`, …).
   (`gitleaks` et `trufflehog` ne sont pas sur PyPI : non lancés.)
3. Fichiers sensibles : aucun `.env`, aucune clé (`id_rsa`, `*.pem`, `*.key`,
   `*.p12`) dans l'historique. `.claude/settings.local.json` (permissions locales)
   n'a jamais été versionné ; il n'était ignoré que par le fichier d'exclusion
   global de la VM (`~/.config/git/ignore`) : ajouté au `.gitignore` du dépôt.

Données personnelles (non bloquant, pour information) : l'adresse électronique
professionnelle de MM figure comme auteur des commits ; des chemins
`/home/ubuntu/...` figurent dans des comptes rendus d'exécution versionnés.

## 3. Fichiers interdits par les règles du projet — aucun

- **Fichiers de MM** (`calcul_3d_v3`, `calcul_3d_v5`, `calcul_3d_v5_sismique`,
  données PANG) : aucun chemin de l'historique ne correspond. Le **contenu** ne
  mentionne `calcul_3d` que dans `docs/development-plan.md` (lots 7 à 10) : noms de
  fichiers et taux de couverture (« `calcul_3d_v3.comm` | 80,8 % | 82,8 % (82/99) »),
  jamais leur texte. « PANG » n'apparaît nulle part (chemins et contenus).
- **NF P 94-282** : aucun fichier de la norme. Le contenu la **cite par article**
  (arbitrages v2 et v3 de MM, fiche d'hypothèses, données chiffrées) : F.1 et
  figure F.1.1, F.2, F.3.1 et tableau F.3.1, F.4.2 et NOTE 4 ; la seule formule
  recopiée est celle de la raideur d'ancrage, `KMA = Et·A / (lf + lb/2)`, avec son
  article. L'arbitrage v3 le dit lui-même : « La NF P 94-282 est citée par
  article ; son texte n'est pas versé au dépôt (document sous licence AFNOR) ».
- **Autres normes diffusées par l'AFNOR (NF EN 1990, NF EN 1992-1-1)** : citées par
  article dans les décisions D17 à D19, les constats CA-039 à CA-044 et le module
  `aster_expert.rebar`. **Point soumis à MM** : `src/aster_expert/rebar/minimum.py`
  transcrit les valeurs numériques du **tableau 7.2N** de l'EN 1992-1-1 (diamètre
  maximal des barres selon σs et wk, lot 39, « à vérifier par MM ») et plusieurs
  expressions (7.1), (7.6N), 9.2.1.1(1), 9.2.2(5) ; les coefficients γ du tableau
  2.1N sont cités. Ce sont des formules et des valeurs, pas du texte rédigé de la
  norme : la session les classe comme **citations**, non bloquantes. Les extraits
  textuels versionnés (`lot38_extraits.json`, `lot39_extraits.json`, …) sont tirés
  de la **documentation Code_Aster** (R7.04.05, U4.81.42…), pas d'une norme.

## 4. Fichiers volumineux — aucun au-delà de 50 Mo

- **Historique** : plus gros blob, 12,5 Mo
  (`data/examples/lot27_maillage/mess/mess_lecture.txt`) ; aucun autre au-delà de
  5 Mo. Objets Git : 33,9 Mo au total. Les MED versionnés (lots 26 et 27) font
  moins de 12,5 Mo.
- **Arbre** : tous les fichiers de plus de 50 Mo sont ignorés par `.gitignore`
  (0 non ignoré) : sorties d'exécution `data/processed/runs/*/proc.0/fort.6`,
  `fort.80`, `glob.1` (jusqu'à 332 Mo), `data/processed/mesh_checks/*/input.med`,
  `résultats_MED_Paravis/*.med` (143 Mo), paquets Git des clones
  `external/codeaster-src` (804 Mo) et `external/codeaster-doc` (261 Mo).

## 5. Corpus et sources externes — non publiés

`external/codeaster-src` (1,4 Go) et `external/codeaster-doc` (779 Mo) sont ignorés
(`/external/*`) et ne l'ont jamais été autrement (aucun chemin `external/` autre que
`.gitkeep` dans l'historique). Ils se reconstruisent par clonage au commit figé de
`config/sources.yaml` (`aster-expert sources sync`, ou `scripts/cloud_setup.sh`
dans le Cloud). Les index et le catalogue (`data/indexes`, `data/processed`) sont
ignorés et se reconstruisent de même (`docs/cloud.md`, § 6 : index identiques à
l'octet).

## 6. Verdict

**Rien ne bloque la publication** : ni secret, ni fichier de MM, ni texte de norme,
ni fichier de plus de 50 Mo, dans l'arbre comme dans l'historique. Un seul point
de jugement a été soumis à MM : la transcription des valeurs du tableau 7.2N de
l'EN 1992-1-1 dans `rebar/minimum.py` (§ 3). **Décision de MM (2026-10-01, en
session) : « Citation, publier »** — non bloquant.

## 7. Garde-fou permanent

`config/publication.yaml` fixe les règles (50 Mo ; chemins interdits : fichiers de
MM, NF P 94-282 et AFNOR, images `.sif`, `.env`, clés, `settings.local.json` ;
contenus interdits : jetons et clés). Elles sont appliquées par :

- le crochet Git `scripts/git-hooks/pre-commit` aux fichiers **indexés** (contenu
  indexé, pas celui de l'arbre), installé par `git config core.hooksPath
  scripts/git-hooks` (fait dans la VM ; fait par `scripts/cloud_setup.sh` dans le
  Cloud) ;
- `tests/unit/test_publication.py`, qui vérifie tout l'arbre versionné à chaque
  `pytest` et éprouve le crochet dans un dépôt temporaire.

La règle porte sur les fichiers, pas sur leur mention : nommer un fichier interdit
dans un texte reste permis (`docs/development-plan.md`).

## 8. Dépôt créé

- Authentification : par MM, dans un terminal de la VM (`gh auth login
  --hostname github.com --git-protocol https --web`) ; la session n'a lu que
  `gh auth status` (jeton masqué) : compte `Marcello-83`, portées `repo`,
  `workflow`, `read:org`, `gist`. `gh` 2.102.0 installé dans `~/.local/bin`
  (archive officielle, empreinte SHA-256 vérifiée contre `gh_2.102.0_checksums.txt`).
- Syntaxe relevée dans `gh repo create --help` (« supply the repository name and
  one of `--public`, `--private`, or `--internal` » ; `--source`, `--remote`) :

  ```bash
  gh repo create aster-expert --private --source=. --remote=origin \
    --description "AsterExpert : agent expert Code_Aster (dépôt privé)"
  git push -u origin main
  ```

  `--push` n'a pas été employé, pour ne pousser que `main`, explicitement.
- Visibilité **relue** après création et après l'envoi :
  `gh repo view Marcello-83/aster-expert --json visibility,isPrivate` →
  `"visibility":"PRIVATE"`, `"isPrivate":true`.
- `main` poussée au commit `3f52c07c33446e8c2452340ee9fe8eec8e034c76` (lot 41 bis),
  celui qui a été inventorié ; `git ls-remote origin` ne montre que `main`. La
  branche `lot-41ter` (ce lot) est poussée ensuite, pour relecture et fusion par
  MM. Les 12 branches locales anciennes et la remise ne sont pas poussées.
- Adresse : https://github.com/Marcello-83/aster-expert

## 9. Application GitHub Claude, sur ce seul dépôt (à faire par MM)

Les sessions Cloud clonent le dépôt privé par l'application GitHub Claude :

1. Ouvrir https://github.com/apps/claude, bouton **Install** (ou **Configure** si
   elle est déjà installée), puis choisir le compte `Marcello-83`.
2. Dans **Repository access**, choisir **Only select repositories** (jamais
   « All repositories »), sélectionner `Marcello-83/aster-expert`, puis
   **Install** (ou **Save**).
3. Contrôle : GitHub → Settings → Applications → Installed GitHub Apps → Claude →
   Configure : la liste des dépôts ne contient que `aster-expert`.
4. Sur claude.ai/code, connecter GitHub si ce n'est pas fait ; le dépôt
   `aster-expert` apparaît dans le sélecteur.

`/web-setup` (envoi du jeton de `gh` à claude.ai) donnerait accès à **tous** les
dépôts que le jeton atteint : ne pas l'employer pour ce besoin.
