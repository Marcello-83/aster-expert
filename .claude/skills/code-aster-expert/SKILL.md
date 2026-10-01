---
name: code-aster-expert
description: >-
  Use when answering a question about Code_Aster syntax, keywords,
  modelisations, comportements, or command usage, or when checking a
  `.comm` file, or before generating a Code_Aster command — whenever the answer
  would rely on the `aster-expert` MCP server (search_codeaster_docs,
  get_document_section, get_command_schema, analyze_comm, validate_comm,
  search_test_cases, read_test_case, search_constats, search_connaissances),
  or when a Code_Aster run fails, before proposing a practice decision or
  writing a verification control. Not a source of Code_Aster knowledge itself:
  describes the procedure for using those nine tools correctly, including the
  mandatory consultations of the knowledge base.
---

# Expert Code_Aster — procédure d'usage des outils

Ce skill ne contient aucune connaissance Code_Aster de première main. Il
décrit comment utiliser les neuf outils du serveur MCP `aster-expert` —
`search_codeaster_docs`, `get_document_section`, `get_command_schema`,
`analyze_comm`, `validate_comm`, `search_test_cases`, `read_test_case`,
`search_constats`, `search_connaissances` — de façon à ne jamais confondre pertinence
documentaire, validité syntaxique et exécution (CLAUDE.md). Toute
connaissance Code_Aster affirmée dans une réponse doit venir de la sortie
d'un de ces outils, jamais de la mémoire du modèle.

## 1. Identifier la version cible avant toute affirmation de syntaxe

Chaque sortie d'outil porte sa propre version (`aster_version` sur un
`SearchHit` ou un `CommandSchema`, `aster_version`/`image_digest` sur un
`ValidationReport`). Lire ce champ et l'annoncer plutôt que de supposer
une version. Si l'utilisateur n'en a demandé aucune en particulier,
dire explicitement que c'est la dernière installation détectée qui a
répondu (comportement par défaut de `get_command_schema`/`validate_comm`
sans `version`). Un désaccord entre deux outils sur la version en jeu est
signalé, jamais lissé.

## 2. Choisir le profil de recherche, et le dire

Avant tout appel de `search_codeaster_docs`, choisir `profile` parmi
`syntaxe` (nom exact d'une commande/d'un mot-clé), `theorie` (fondement
physique ou mathématique) ou `methode` (choix de modélisation, comparaison
d'éléments) — jamais deviné à l'aveugle, jamais laissé au défaut sans
y avoir pensé. La description de l'outil donne le critère de choix. La
réponse à l'utilisateur nomme le profil retenu et pourquoi.

## 3. Aucune affirmation de syntaxe sans outil

Un nom de commande, de mot-clé, de modélisation ou de loi de comportement
n'est jamais énoncé sans provenir soit de `get_command_schema` (schéma
exact du catalogue), soit d'un extrait renvoyé par `search_codeaster_docs`.
Si l'outil ne le confirme pas, le dire plutôt que de compléter depuis la
mémoire du modèle.

## 4. Citer systématiquement la source

Toute affirmation documentaire porte : identifiant de document, section,
version, chemin source. Voir `references/citation.md` pour le mapping
exact champ de sortie → outil.

## 5. Un extrait de tête ne fonde jamais une affirmation sur le corps d'une section

`search_codeaster_docs` renvoie un `excerpt` coupé à 280 caractères — utile
pour repérer *quel* document et *quelle* section sont pertinents, jamais
suffisant pour affirmer ce qu'une section dit réellement. Dès qu'une
réponse s'appuie sur le contenu d'une section — un tableau comparatif
(ex. domaines d'application de plusieurs modélisations), un domaine de
validité, une liste de conditions ou de modèles disponibles — lire cette
section en entier avec `get_document_section` avant de conclure.
`search_codeaster_docs` a identifié la bonne section trois fois de suite
sur ce projet (tableau DKT/DST/Q4G de U2.02.01, panorama des modèles de
sol de U2.03.09, méthodes de U2.04.06) sans jamais pouvoir en citer le
contenu, faute d'un outil de lecture intégrale — c'est précisément ce que
`get_document_section` corrige, pas une amélioration du classement.

Chaque résultat de `search_codeaster_docs` porte déjà tout ce qu'il faut
pour l'appel suivant, sans rien reconstruire à la main : passer soit son
`fragment_id` seul, soit `document_id` + `section_path` + `granularity`
ensemble. Voir `references/citation.md`.

**Vérifier `content` avant de lire, lire par plages au-delà du seuil (lot
14, L1).** `get_document_section` ne tronque jamais en silence : au-delà
d'un seuil de taille, `content` revient à `null` plutôt que coupé --
`content_length` (toujours renseigné) dit la taille totale de la section,
`outline` liste les sous-titres détectés avec leurs bornes de lignes
absolues, et `guidance` explique quelle plage plus étroite demander.
Vérifier systématiquement `content is None` avant d'exploiter une réponse :
si c'est le cas, ne jamais conclure sur l'absence de contenu, mais
enchaîner un ou plusieurs appels avec `line_start`/`line_end` (une entrée
de `outline` si elle existe, sinon une plage de lignes choisie dans les
bornes indiquées) jusqu'à couvrir ce qui fonde la réponse. Une lecture par
plages successives reste une lecture intégrale de ce qui est cité, jamais
une lecture partielle passée sous silence.

## 6. Fichier `.comm` : `analyze_comm` puis `validate_comm`, jamais l'œil seul

Un `.comm` fourni par l'utilisateur passe par `analyze_comm` (structure)
puis, si une confrontation au catalogue est utile, `validate_comm` (niveau
B) — jamais une simple lecture visuelle du fichier tenant lieu de l'un ou
l'autre. Voir `references/comm-workflow.md`.

## 6 bis. Cas tests : `search_test_cases` puis `read_test_case`, jamais une lecture directe (lot 22)

Les fichiers de commandes des cas tests officiels (`.comm`, `.com1`, ...)
ne sont pas dans l'index documentaire. Deux outils en lecture seule y
donnent accès, au commit de `codeaster-src` enregistré par la dernière
synchronisation (`source.source_commit` de chaque réponse ; l'outil refuse
de répondre si la copie de travail a quitté ce commit ou porte des
modifications locales) :

- `search_test_cases(command, keyword=None, limit=50)` : les fichiers qui
  utilisent une commande et, facultativement, un mot-clé (nom seul, ou
  chemin pointé dont la queue est comparée, ex. `ELAS_COQUE.FLEX_L`). La
  correspondance est structurelle (parseur du projet) : un commentaire ou une
  chaîne ne compte pas. Lire `files_unparsable` (fichiers que le parseur n'a
  pas pu lire, jamais omis en silence) et `truncated` (résultats coupés par
  `limit`) avant de conclure « aucun cas test n'utilise ... ».
- `read_test_case(path, line_start=None, line_end=None)` : `path` est le nom
  relatif renvoyé par la recherche. Comme `get_document_section`, `content`
  revient à `null` au-delà de 20000 caractères ; `guidance` dit alors quelle
  plage demander (`line_start` et `line_end` ensemble, lignes 1..`total_lines`).
  Un chemin hors du corpus, ou qui n'est pas un fichier de commandes, est
  refusé.

Toute lecture d'un cas test passe par ces deux outils, jamais par `cat`, un
outil de lecture de fichier ou `grep` sur `external/codeaster-src/astest` :
la lecture directe échappe au journal (`data/processed/query_log.jsonl`) et
au contrôle de commit. Un cas test est une référence exécutable, jamais un
modèle transposable (CLAUDE.md, principe 5) : le citer par son `path` et
`source_commit`, et comparer modélisation, éléments, loi, chargements,
conditions aux limites, type d'analyse et version avant toute réutilisation.
Niveau A : lire un cas test ne prouve rien sur un autre fichier.

## 6 ter. Avant de générer une commande : consulter les constats qui la concernent (lot 41)

La base partagée `connaissances/constats_code_aster/` garde, un fichier par
constat, les faits établis sur Code_Aster au fil des projets — souvent des
pièges trouvés par exécution d'un cas d'essai versionné (une charge de pression
évaluée aux nœuds, `CREA_POI1` qui ne crée qu'une maille par nœud, `FERR_MIN`
faux en `Pa`...). Avant d'écrire ou de générer une commande dans un `.comm`,
appeler `search_constats(command=<commande>)` (et, si un mot-clé est en jeu,
`keyword=<mot-clé>`, ou `text=` pour une recherche libre) et lire chaque constat
renvoyé avant d'écrire la commande :

- le `summary` dit le piège en une phrase ; le fichier (`file`) donne l'entrée
  complète et ses sources — le lire avant de s'appuyer dessus ;
- `constat_validation_level` est le niveau atteint par le constat lui-même
  (A documentaire, B catalogue, C/D exécution d'un cas d'essai versionné) :
  un constat A ou B n'a pas été éprouvé par exécution ;
- `aster_version` : un constat vaut pour cette version ; sur une autre, le dire
  (et le rejeu `aster-expert constats rejouer` dit s'il tient encore).

Une fiche de projet ne recopie jamais un constat : elle le référence
(`{"nature": "constat", "constat_id": "CA-nnn", "point_label": ...}`). Un
constat nouveau s'ajoute à la base, pas à une fiche. La réponse de
`search_constats` est de niveau A (lecture de la base, rien n'est exécuté).

## 6 quater. Consultation obligatoire de la base de connaissances (lot 42)

Ce que l'outil a appris sur les projets précédents est écrit dans
`connaissances/` (six couches : `constats_code_aster`, `diagnostics`,
`patrons`, `controles`, `references_validation`, `precedents`) et se consulte
par `search_connaissances(text=, command=, keyword=, layers=[...], status=)`.
Chaque résultat porte son `status` (`observé` : vu dans un projet ; `établi` :
preuve rejouable ; `promu` : réutilisé dans deux projets ou niveau E), le
niveau atteint par l'entrée (`entry_validation_level`) et le fichier qui porte
ses preuves (`file`), à lire avant de s'appuyer dessus. La consultation est
**obligatoire** dans quatre situations, et la réponse cite les entrées lues (ou
dit qu'aucune ne correspond) :

1. **Avant d'écrire une commande Code_Aster** : constats et patrons —
   `search_connaissances(command=<commande>, layers=["constats_code_aster",
   "patrons"])` (et `keyword=` pour un mot-clé en jeu). Un patron est une recette
   d'un projet antérieur, avec ses conditions d'emploi : vérifier qu'elles
   tiennent pour l'ouvrage présent avant de la reprendre.
2. **Dès qu'une erreur ou une alarme apparaît dans un `.mess`** : diagnostics,
   **avant toute autre hypothèse** — `search_connaissances(keyword=<identifiant>,
   layers=["diagnostics"])` avec l'identifiant du message (`FACTOR_11`,
   `MED2_4`…), ou `text=` pour un arrêt anormal (« Segmentation fault »).
   `aster-expert run` le fait déjà pour un échec et affiche les diagnostics
   trouvés ; les lire. Un diagnostic dont `cause_established` est faux donne une
   correction connue, pas une cause.
3. **Avant de proposer une décision pratique** : précédents —
   `search_connaissances(text=..., layers=["precedents"])`. Un précédent n'est
   **jamais appliqué** : il se propose (`aster-expert connaissances
   proposer-precedent <PRE-nnn> --point <p>`, entrée non tranchée et source
   d'origine `precedent_projet`) avec son domaine de validité, et MM arbitre.
4. **Avant d'écrire un contrôle** : contrôles existants —
   `search_connaissances(text=..., layers=["controles"])` ; reprendre un contrôle
   du tronc commun plutôt qu'en écrire un second.

En fin de lot, `aster-expert rex <projet>` prépare le retour d'expérience :
chaque échec d'exécution est classé (rattaché à un diagnostic, nouveau
diagnostic, ou écarté avec un motif) ; un échec non classé bloque la clôture du
lot. Une entrée nouvelle s'écrit dans sa couche avec sa preuve ; aucune n'est
promue sans `aster-expert connaissances promouvoir`, qui vérifie les conditions.

## 7. Annoncer le niveau de validation atteint, jamais un niveau supérieur

`search_codeaster_docs`, `get_document_section`, `get_command_schema`,
`analyze_comm`, `search_test_cases`, `read_test_case`, `search_constats`,
`search_connaissances` sont niveau A (documentaire, non exécuté, non confronté à
un fichier réel — y compris `get_command_schema`, qui lit le catalogue
mais ne confronte rien, et `get_document_section`, qui renvoie un texte
intégral mais toujours non exécuté). `validate_comm` est niveau B (syntaxe
confrontée au catalogue). Les niveaux C/D/E (exécution, validité physique,
comparaison à une référence) sont hors du périmètre de ce serveur : ne
jamais les annoncer à partir de ces neuf outils (le niveau C ou D d'un constat
ou d'une entrée de la base est celui de son cas d'essai, pas celui de la
réponse). Les mots « validé »,
« correct », « sans erreur » sont toujours qualifiés par leur niveau.

## 8. Distinguer faits, déductions, recommandations

Toute réponse sépare explicitement ce qui est lu dans une sortie d'outil
(fait documenté), ce qui en est inféré (déduction, à marquer comme telle),
et ce qui est suggéré à l'utilisateur (recommandation). Voir
`references/answer-format.md`.

## Quand la documentation ne tranche pas

Si `search_codeaster_docs` (sous plusieurs profils si le premier ne suffit
pas) ne renvoie rien qui réponde à la question, le dire explicitement.
Ne jamais forcer une réponse à partir d'un résultat hors sujet, ni
compléter par déduction ce qu'aucun document ne dit.
