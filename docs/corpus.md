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

## 8. Jeu d'évaluation

`data/evaluations/questions.jsonl` contient les questions de référence (lot 5).
Schéma effectivement produit — un amendement du schéma esquissé initialement
ici, jamais un `expected_documents` deviné pour le remplir a posteriori :

```json
{
  "id": "eval-001",
  "question": "Quels types d'éléments finis de poutre sont disponibles pour modéliser un pieu, et en quoi diffèrent-ils",
  "domain": "modelisation_poutre",
  "origin": "travail reel",
  "source_question": "Comment modéliser les pieux dans code_aster",
  "version": null,
  "expected_documents": ["U3.11.01"],
  "expected_commands": ["AFFE_MODELE"],
  "verified_by": "U3.11.01 « Notice d'utilisation des éléments de poutre », section ... — titre et chemin vérifiés dans external/codeaster-doc",
  "note": "...",
  "answer_outside_corpus": false
}
```

- `id`/`question`/`domain`/`origin` : la question bornée elle-même.
- `source_question` : la question large d'origine dont elle est issue
  (`data/evaluations/cas_usage.md`, catalogue de couverture fonctionnelle,
  jamais lui-même une question d'évaluation).
- `version` : la version documentaire ciblée si la question en dépend
  explicitement, `null` sinon (le corpus synchronisé ne couvre que 17.4.0).
- `expected_documents` : identifiants de documents établis par lecture du
  corpus réel, jamais devinés ; vide et `note` renseignée si la question
  reste non résolue (résultat normal, pas un échec masqué). Plusieurs
  documents légitimes sont tous listés — la métrique est « au moins un
  document attendu retrouvé », pas « le bon document unique ».
- `expected_commands` : uniquement des noms présents dans le catalogue
  extrait au lot 4b (`data/processed/catalogue/<digest>/*.json`) ; une
  commande réelle mais hors catalogue (`DEFI_CONT`, `CALC_SPEC`,
  `CALC_FORC_AJOU`, `POURSUITE`, lot 6b X3) n'y figure jamais, seulement
  dans `note` si pertinent.
- `verified_by` : ce qui fonde chaque document retenu — titre exact,
  section, chemin du fichier source (`CLAUDE.md`, « Toute donnée indexée
  conserve sa source, son chemin »). Une correspondance de mots-clés seule
  n'est jamais suffisante.
- `note` : motif de non-résolution, mise en garde sur une fausse piste de
  la table commande → document (lot 6, I5), ou tout autre fait utile à la
  relecture.
- `answer_outside_corpus` : `true` quand la réponse relève des cas tests ou
  du catalogue plutôt que de la documentation elle-même — `expected_documents`
  reste alors vide, ce n'est jamais confondu avec une question non résolue.

`data/evaluations/questions_raw.jsonl` conserve le jeu de questions tel que
reçu de l'utilisateur, avant toute complétion (traçabilité, `CLAUDE.md`
principe 4). `data/evaluations/cas_usage.md` conserve les 21 questions larges
d'origine.

Les questions proviennent de problèmes réellement rencontrés, pas de
reformulations de la documentation. Elles ne sont jamais reformulées pour
les rendre plus faciles à satisfaire : c'est le corpus qu'on mesure, pas les
questions.

L'outil de mesure (`aster_expert.retrieval.evaluation`, `aster-expert eval
score`/`aster-expert eval summary`) calcule rappel@k, précision@k, hit@k et
MRR à partir d'une liste de résultats classés fournie en entrée — utilisable
avant qu'aucun index n'existe (lot 5). Une question non résolue
(`expected_documents` vide) est exclue de la métrique, jamais scorée comme un
échec.
