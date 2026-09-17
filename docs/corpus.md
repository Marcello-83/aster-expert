# Corpus

## 1. Sources

| Source | Dépôt | Contenu attendu | Licence |
|--------|-------|-----------------|---------|
| `codeaster-src` | `https://gitlab.com/codeaster/src.git` | sources, catalogues, cas tests de vérification, guide développeur | GPL v3 |
| `codeaster-doc` | `https://gitlab.com/codeaster/doc/docaster.git` | manuels U, R, V, D | GFDL v1.3 |

Les deux dépôts sont clonés sous `external/`, jamais commités, et déclarés dans
`config/sources.yaml`.

Une troisième source, l'installation Code_Aster locale elle-même, fournit le
catalogue effectivement appliqué. Elle n'est pas clonée : elle est introspectée.
C'est la seule source faisant autorité en matière de syntaxe.

## 2. État d'inspection

Au moment de la rédaction, la structure interne des deux dépôts n'a pas été
vérifiée. Les chemins internes ne doivent pas être écrits en dur avant
inspection. Le premier lot de corpus a pour objet cette inspection.

Points à établir avant toute écriture de parseur :

1. Emplacement et format des catalogues de commandes dans `codeaster/src`.
2. Emplacement des cas tests, et fichiers associés à chaque cas
   (`.comm`, `.mmed`, `.export`, `.mail`, fichiers de référence).
3. Format des sources documentaires dans `docaster` : texte structuré,
   traitement de texte, ou document composé. Cette réponse détermine à elle
   seule la faisabilité et le coût du lot de parsing documentaire.
4. Existence d'un rendu construit exploitable (HTML) et de sa procédure de
   construction.
5. Convention de nommage des tags de version des deux dépôts, et correspondance
   entre version de code et version documentaire.

Tant que le point 3 n'est pas tranché, deux stratégies restent ouvertes :
parsing des sources, ou consommation d'un rendu construit. Ne pas en choisir
une par défaut.

## 3. Familles documentaires

| Famille | Objet | Usage dans le système |
|---------|-------|-----------------------|
| U0 | guide de lecture de la documentation d'utilisation | contexte |
| U1 | présentation générale, supervision | contexte |
| U2 | guides méthodologiques | démarche de modélisation |
| U3 | formats et fichiers | entrées/sorties |
| U4, U7 | documentation des commandes | sémantique des mots-clés |
| R | références théoriques | hypothèses, formulations, lois |
| V | documents de validation | cas de référence et valeurs attendues |
| D | documents divers | selon contenu |
| SU | guides d'utilisation de la plate-forme Salome-Meca | contexte, hors périmètre Code_Aster |
| SV | fiches de validation d'outils de la plate-forme Salome-Meca | contexte, hors périmètre Code_Aster |
| cas tests | fichiers exécutables | exemples de mise en œuvre |
| catalogue | définition formelle | grammaire, seule autorité syntaxique |

Cette classification a été confirmée par l'inventaire réel du lot 6
(`docs/development-plan.md`, lot 6, I1/I2 ; `data/raw/inventory.jsonl`,
2047 documents), avec deux amendements par rapport à la classification
initialement attendue :

- **`U0`** : un seul document (`U0.00.01`, « Guide de lecture de la
  documentation d'Utilisation »), présent sous `source/manuals/man_u/u0/`
  aux côtés de `u1`..`u7` mais non listé à l'origine. Ajouté comme famille
  à part entière plutôt que rattaché à `U1` : c'est un document sur la
  documentation elle-même, pas une présentation de Code_Aster.
- **`U3`** (amendement lot 7c, diagnostic du routage par profil de requête).
  La ligne « formats et fichiers | entrées/sorties » de la table ci-dessus
  ne décrit qu'une petite partie du contenu réel : sur les 36 documents `U3`
  du corpus 17.4.0, seuls 4 (`U3.01.00`-`U3.04.01`) sont effectivement des
  formats de fichier de maillage (GMSH, IDEAS, GIBI...) ; les 32 autres
  (`U3.11.*`-`U3.33.*`) sont des notices de modélisation -- ex.
  `U3.11.01` « Modélisations POU_D_T, POU_D_E, BARRE », `U3.12.03`
  « Modélisation COQUE_3D » -- qui cataloguent les types d'éléments finis
  disponibles par phénomène et renvoient à leur formulation, un contenu de
  nature syntaxique/comparative (quel élément existe, en quoi diffère-t-il)
  bien plus que documentaire d'entrée/sortie. Constat confirmé par mesure
  au lot 7c (`config/retrieval.yaml`, `docs/development-plan.md`, clôture
  lot 7c, G2) : la famille `U3` est nécessaire aux profils
  `theorie`/`methode` mais dégrade le profil `syntaxe` si elle y est
  ajoutée sans distinction, précisément parce que les 4 documents de
  formats de fichier y remontent alors à poids plein sur des requêtes sans
  rapport avec la modélisation.
- **`man_s` (`SU`, `SV`)** : famille entièrement absente de la
  classification initiale, découverte lors de la synchronisation (lot 3,
  observation de clôture) et qualifiée au lot 6 (I2). Elle documente la
  plate-forme **Salome-Meca** (pré/post-traitement, outils métier,
  serveurs de calcul), pas Code_Aster lui-même : `SU1`/`SU4` sont des
  guides d'utilisation (ex. `SU1.04.01`, tuyauterie sous Salome-Meca ;
  `SU4.01.01`, serveur de calcul Cronos), `SV1`/`SV3`/`SV4` des fiches de
  validation d'outils de la plate-forme (ex. `SV1.01.02`, AsterStudy ;
  `SV3.01.01`, ASTK ; `SV4.02.01`, recette d'installation) — jamais des cas
  de validation Code_Aster au sens de la famille `V`. Sur le corpus
  17.4.0 : 10 documents (`SU1` : 2, `SU4` : 2, `SV1` : 4, `SV3` : 1,
  `SV4` : 1). Réel corpus indexable (structure identique aux autres
  familles : répertoire par document, label `.. _SUx.yy.zz:` ou
  `.. _SVx.yy.zz:` en tête d'`index.rst`), mais hors du périmètre de la
  priorité des sources syntaxiques/théoriques de `CLAUDE.md` (« Priorité
  des sources ») : ni catalogue, ni sémantique de mots-clés, ni théorie —
  à retrouver, sur requête, comme contexte d'usage de la plate-forme
  plutôt que comme source de syntaxe ou de validation physique.

## 4. Politique de version

Une version cible est un triplet :

- version de code (déterminée par l'installation) ;
- tag ou branche du dépôt `src` correspondant ;
- tag ou branche du dépôt `docaster` correspondant.

Règles :

1. Aucun fragment n'entre dans un index sans étiquette de version.
2. Une requête sans version explicite utilise la version cible déclarée dans
   `config/versions.yaml`, et l'indique dans la réponse.
3. Un fragment issu d'une version différente de la version interrogée n'est
   jamais renvoyé silencieusement. Il peut l'être avec un avertissement
   explicite, si aucun fragment de la bonne version ne répond.
4. Les correspondances entre versions sont déclarées, jamais déduites d'une
   similarité de numérotation.

## 5. Manifeste de synchronisation

Chaque exécution de `aster-expert sources sync` écrit
`data/raw/manifest.json` :

```json
{
  "generated_at": "2026-01-01T00:00:00+00:00",
  "sources": [
    {
      "name": "codeaster-src",
      "url": "https://gitlab.com/codeaster/src.git",
      "ref": "v18.0.0",
      "commit": "0000000000000000000000000000000000000000",
      "local_path": "external/codeaster-src",
      "synchronized_at": "2026-01-01T00:00:00+00:00",
      "dirty": false,
      "families": ["catalogue", "testcases"]
    }
  ]
}
```

Le champ `dirty` signale des modifications locales non commitées. Une source
`dirty` bloque la synchronisation de cette source et le fait est journalisé.

**Amendement lot 3.** Chaque entrée porte aussi `status` (`"cloned"`,
`"adopted"`, `"blocked_dirty"`, `"blocked_diverged"`, `"blocked_error"`) et
`detail` (texte explicatif, obligatoire pour tout `status` `blocked_*`) :
une simple liste de noms/commits ne permet pas de distinguer une source
réellement synchronisée d'une source dont la synchronisation a été refusée,
ce que `CLAUDE.md` interdit de faire silencieusement. `"cloned"` et
`"adopted"` signifient tous deux que la copie de travail correspond
exactement à la déclaration (`ref` résolu sur le dépôt distant) : le premier
la première fois qu'une source est clonée, le second à toute exécution
suivante où elle s'y trouvait déjà — l'idempotence porte sur ce second cas
(deux exécutions consécutives sur une source déjà présente et à jour
produisent le même `status`, le même `commit`, le même `detail`), jamais sur
la comparaison d'un premier clonage à une absence de dépôt, qui n'a pas de
sens. Une source existante dont le commit courant diverge de ce que `ref`
résout sur le dépôt distant n'est jamais réalignée d'autorité : `status`
vaut `"blocked_diverged"`, `detail` cite les deux commits, et la copie de
travail n'est ni `checkout`-ée ni `reset`-ée (`aster_expert.ingestion.sync`).

## 6. Inventaire

L'inventaire produit `data/raw/inventory.jsonl`, une entrée par document
identifié, avant tout découpage. Champs attendus : identifiant documentaire,
titre, famille, version, chemin relatif, format source, taille, empreinte,
liens internes repérés, fichiers associés.

L'inventaire produit également :

- des statistiques par famille et par version ;
- une liste d'anomalies : document sans identifiant, identifiant en double,
  document orphelin, lien interne non résolu, format inattendu.

Les anomalies ne sont pas corrigées silencieusement. Elles sont listées et
tranchées explicitement.

## 7. Découpage

Le découpage n'est pas fondé sur une taille fixe. Règles cibles, à valider par
le banc d'évaluation :

- U4 et U7 : un fragment par commande, puis par mot-clé facteur, puis par
  mot-clé simple, en conservant le rattachement hiérarchique ;
- R : section théorique complète, équations et définitions maintenues
  ensemble ;
- V : problème, modélisation, valeurs de référence, synthèse, séparés mais liés ;
- cas tests : blocs fonctionnels et commandes, avec numéros de lignes ;
- catalogue : un fragment par commande, issu de l'introspection, pas du texte.

Contrôles automatiques exigés :

1. aucun contenu significatif perdu entre le document source et l'ensemble de
   ses fragments ;
2. chaque fragment rattaché à une source, un chemin et une version ;
3. liens U/R/V/cas tests conservés lorsqu'ils existent dans la source ;
4. idempotence : deux exécutions sur la même révision produisent des fragments
   identiques.

**Clôture du lot 7 (découpage documentaire réel, `aster_expert.parsing.
doc_fragments`).** Réutilise la structure établie au lot 6
(`aster_expert.ingestion.inventory` : un document est un répertoire, une
section est un fichier `.rst`), jamais un nouveau parseur. Deux granularités
construites et mesurées côte à côte sur le corpus 17.4.0 synchronisé (2047
documents, 13116 fichiers de section) :

- `by_file` : un fragment par fichier — 13116 fragments, taille médiane
  1358 caractères.
- `by_subsection` : identique à `by_file` pour tout fichier de 150 lignes
  ou moins (seuil choisi juste sous le 90e centile réel de la distribution
  des tailles de fichiers de section — médiane 41 lignes, 90e centile 155
  lignes, mesuré par `wc -l` sur les 13116 fichiers), redécoupé par en-tête
  reStructuredText sinon — 26553 fragments, taille médiane 946 caractères.

Contrôle 1 (non-perte) vérifié par construction et par test, pas supposé :
`content` est toujours une tranche brute du texte source (jamais un rendu
docutils), et tout découpage en sous-sections est validé par
`verify_full_coverage` (reconstruction ligne à ligne comparée à la source),
qui aurait levé une erreur explicite sur le moindre écart — aucune levée sur
l'ensemble des 13116 fichiers de la passe réelle. Contrôle 2 trivialement
garanti par le modèle `pydantic` (`source_commit`/`source_path`/
`aster_version` non optionnels). Contrôle 3 : chaque fragment porte les liens
déjà établis au lot 6/6b, à la granularité du document entier (la table
commande -> document et le graphe de références n'ont pas de granularité
plus fine que le document) — 1538/13116 fragments `by_file` portent une
commande liée, 4478/13116 un document lié. Contrôle 4 (idempotence) vérifié
sur la passe réelle complète : deux exécutions consécutives de
`aster-expert fragments build --granularity by_file` produisent un
`fragments_by_file.jsonl` identique champ à champ, empreintes comprises,
hors le seul champ `extracted_at` (horodatage du lot, jamais un fait du
contenu).

**Mesure sur le banc (lot 5, 63 questions résolues sur 65) : les deux
granularités sont statistiquement indiscernables**, compte rendu complet du
lot 7. `by_file` reste la granularité par défaut, retenue pour sa simplicité
(deux fois moins de fragments à indexer) faute d'un gain mesuré de
`by_subsection` qui la justifierait — jamais un choix esthétique présenté
comme un arbitrage mesuré.

## 8. Jeu d'évaluation

`data/evaluations/questions.jsonl` contient les questions de référence (lot 5,
schéma amendé au lot 5b — normalisation, docs/development-plan.md). Schéma
effectivement produit — un amendement du schéma esquissé initialement ici,
jamais un `required_documents` deviné pour le remplir a posteriori :

```json
{
  "id": "eval-001",
  "question": "Quels types d'éléments finis de poutre sont disponibles pour modéliser un pieu, et en quoi diffèrent-ils",
  "domain": "modelisation_poutre",
  "origin": "travail reel",
  "source_question": "Comment modéliser les pieux dans code_aster",
  "version": {
    "solver": "17.4.0",
    "documentation_revision": "9c8c179f57ef7ca1d2891cac275ee4823a57967c",
    "compatibility_status": "correspondance solveur/documentation vérifiée par tag (git ls-remote --tags, config/versions.yaml) ; aucune confirmation croisée par changelog au-delà de cette convention de nommage commune"
  },
  "required_documents": ["U3.11.01"],
  "supporting_documents": [],
  "expected_commands": ["AFFE_MODELE"],
  "verified_by": "U3.11.01 « Notice d'utilisation des éléments de poutre », section ... — titre et chemin vérifiés dans external/codeaster-doc",
  "note": "...",
  "answerability": "explicit",
  "gold_confidence": "high",
  "answer_outside_corpus": false
}
```

- `id`/`question`/`domain`/`origin` : la question bornée elle-même.
- `source_question` : la question large d'origine dont elle est issue
  (`data/evaluations/cas_usage.md`, catalogue de couverture fonctionnelle,
  jamais lui-même une question d'évaluation).
- `version` : jamais `null` (amendement lot 5b) — le corpus synchronisé ne
  couvre qu'une seule révision documentaire, donc chaque question porte la
  version du solveur (`solver`), la révision du dépôt `codeaster-doc`
  effectivement lue (`documentation_revision`, le commit de
  `data/raw/manifest.json`/`config/versions.yaml`) et un
  `compatibility_status` explicite sur ce qui a été vérifié de cette
  correspondance solveur/documentation et ce qui ne l'a pas été
  (`config/versions.yaml` : correspondance de tag confirmée par
  `git ls-remote --tags`, aucun changelog croisé consulté) — jamais
  « vérifié » sans préciser jusqu'où (`CLAUDE.md`, principe 6).
- `required_documents` : identifiants de documents établis par lecture du
  corpus réel, jamais devinés, sans lesquels la réponse manquerait son
  noyau ; vide et `note` renseignée si la question reste non résolue
  (résultat normal, pas un échec masqué). Plusieurs documents légitimes
  sont tous listés — la métrique est « au moins un document attendu
  retrouvé », pas « le bon document unique ». C'est le seul champ lu par
  `aster_expert.retrieval.evaluation`.
- `supporting_documents` (amendement lot 5b) : documents utiles à une
  réponse complète (théorie sous-jacente, corroboration, panorama de
  contexte) mais dont l'absence ne rendrait pas la réponse fausse — jamais
  scorés par l'outil de mesure. Le classement se fonde sur ce que dit déjà
  `verified_by` au moment de la scission (jamais une nouvelle recherche) :
  quand `verified_by` ne permet pas de trancher entre les deux, le document
  reste en `required_documents`.
- `expected_commands` : uniquement des noms présents dans le catalogue
  extrait au lot 4b (`data/processed/catalogue/<digest>/*.json`) ; une
  commande réelle mais hors catalogue (`DEFI_CONT`, `CALC_SPEC`,
  `CALC_FORC_AJOU`, `POURSUITE`, lot 6b X3) n'y figure jamais, seulement
  dans `note` si pertinent.
- `verified_by` : ce qui fonde chaque document retenu — titre exact,
  section, chemin du fichier source (`CLAUDE.md`, « Toute donnée indexée
  conserve sa source, son chemin »). Une correspondance de mots-clés seule
  n'est jamais suffisante. Un document cité par un autre document sans que
  son propre contenu ait été lu n'est pas considéré comme individuellement
  vérifié (lot 5b, X1 : cas d'eval-039/U4.81.44/U4.81.46, corrigé par
  lecture directe).
- `note` : motif de non-résolution, mise en garde sur une fausse piste de
  la table commande → document (lot 6, I5), ou tout autre fait utile à la
  relecture.
- `answerability` (amendement lot 5b) : quatre valeurs — `explicit` (réponse
  présente telle quelle dans un document), `inferable` (déduite de faits
  documentés, sans être énoncée comme telle), `partial` (la preuve ne
  couvre qu'une partie de ce que demande la question) et `absent` (aucune
  réponse officielle établie — `required_documents` vide, cas normal
  d'eval-005/eval-007, pas un trou du jeu).
- `gold_confidence` (amendement lot 5b) : trois valeurs — `high`, `medium`,
  `provisional` — reflétant la seule solidité de `verified_by` (jamais une
  nouvelle vérification) : `high` pour une citation directe et spécifique
  de chaque document retenu ; `medium` quand la réponse repose sur un
  mécanisme générique documenté appliqué à un cas que le corpus ne nomme
  jamais, ou quand la vérification reste à un niveau de citation
  documentaire plutôt que de contenu ; `provisional` pour une question non
  résolue, un constat de recherche à un instant donné, pas un fait
  définitif.
- `answer_outside_corpus` : `true` quand la réponse relève des cas tests ou
  du catalogue plutôt que de la documentation elle-même — `required_documents`
  reste alors vide, ce n'est jamais confondu avec une question non résolue.

`data/evaluations/questions_raw.jsonl` conserve le jeu de questions tel que
reçu de l'utilisateur, avant toute complétion (traçabilité, `CLAUDE.md`
principe 4). `data/evaluations/cas_usage.md` conserve les 21 questions larges
d'origine.

`data/evaluations/query_profiles.jsonl` (lot 7c, G3) associe à chacune des
64 premières questions un profil de routage (`syntaxe`, `theorie`,
`methode` -- `aster_expert.retrieval.query_profiles`), établi une fois par
l'utilisateur à partir du seul libellé de la question, sans consulter les
documents attendus. C'est une donnée d'entrée, copiée verbatim et jamais
retouchée pour la faire coïncider avec un résultat mesuré
(`aster_expert.retrieval.bench.run_profile_routed_bench` lit ce fichier, ne
l'écrit jamais). `eval-065` (ajoutée au lot 5b après la production de cette
annotation) n'y figure pas : un appelant qui ne trouve pas de profil pour
une question retombe sur le profil par défaut (`syntaxe`), jamais un profil
deviné pour combler l'absence.

Les questions proviennent de problèmes réellement rencontrés, pas de
reformulations de la documentation. Elles ne sont jamais reformulées pour
les rendre plus faciles à satisfaire : c'est le corpus qu'on mesure, pas les
questions. Exception documentée : `eval-013`, scindée en deux questions
distinctes au lot 5b (`eval-013` et `eval-065`) parce qu'elle mélangeait deux
mécanismes documentés séparément (calculer un spectre d'oscillateur depuis un
accélérogramme, ou en déclarer un déjà connu) — une scission, jamais une
reformulation de contenu.

L'outil de mesure (`aster_expert.retrieval.evaluation`, `aster-expert eval
score`/`aster-expert eval summary`) calcule rappel@k, précision@k, hit@k et
MRR à partir d'une liste de résultats classés fournie en entrée — utilisable
avant qu'aucun index n'existe (lot 5). Une question non résolue
(`required_documents` vide) est exclue de la métrique, jamais scorée comme un
échec.

**Documents référencés mais absents du corpus synchronisé (lot 5b).**
Plusieurs documents `U4`/`U7`/`R` du corpus 17.4.0 renvoient vers `U2.06.05`
et `U2.06.07` (guides méthodologiques d'interaction sol-structure), qui
n'existent ni dans `external/codeaster-doc/source/manuals/man_u/u2/`
(répertoires `u2.06.05`/`u2.06.07` absents) ni dans
`data/raw/inventory.jsonl` — 9 arêtes non résolues dans
`data/processed/xref_graph.json` depuis 6 documents distincts
(`U2.03.07`, `U2.06.10`, `U2.06.13`, `U4.53.05`, `U4.63.02`, `U7.03.12`,
et une occurrence dans `V2.03.201`). Repéré à l'occasion de la vérification
d'`eval-048` (interaction sol-structure) : un manque réel du dépôt
documentaire public synchronisé, même famille de constat que les renvois
cassés déjà relevés au lot 6b (`D3.02.01`, `A2.01`, obsolètes ou hors
périmètre) — jamais deviné ni comblé, seulement consigné ici pour qu'une
future synchronisation ou lecture ne le redécouvre pas de zéro.
