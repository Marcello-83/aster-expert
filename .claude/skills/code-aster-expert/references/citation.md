# Citer une sortie d'outil

Chaque outil renvoie ses propres champs de citation ; ne jamais en
inventer, ne jamais réutiliser ceux d'un autre outil.

## `search_codeaster_docs` → `SearchDocsResult.results[i]` (`SearchHit`)

- Document : `document_id` (+ `document_title` s'il est présent)
- Section : `section_path` (chemin des sections, du document vers le
  fragment)
- Version : `aster_version`
- Chemin : `source_path`
- Révision : `source_commit`
- Score et famille (`score`, `family`) sont des éléments de classement,
  pas des éléments de citation ; les citer n'est jamais un substitut aux
  quatre champs ci-dessus.

Format minimal d'une citation : `<document_id> § <section_path> (v.
<aster_version>, <source_path>)`.

## `get_command_schema` → `CommandSchemaResult.command_schema` (`CommandSchema`)

- Commande : `command`
- Version : `aster_version`
- Origine : `catalogue_source` (chemin du catalogue Python introspecté),
  `catalogue_hash`
- Si `keyword` a été fourni : `keyword_variants` liste *toutes* les
  variantes trouvées (`KeywordSchema.path`, `.variant_id`, `.condition`) —
  n'en citer une seule silencieusement quand plusieurs existent, cf.
  `docs/metadata.md` §2.

Un schéma de commande n'a pas de "section" au sens documentaire : le
mot-clé pointé (`path`) en tient lieu.

## `analyze_comm` → `CommAnalysisResult.analysis` (`CommFileAnalysis`)

- `file_path`, `file_hash` identifient le fichier analysé, pas une
  affirmation Code_Aster : cette analyse ne cite jamais le catalogue, elle
  décrit seulement ce que le fichier contient.
- Un statement `dynamic`/`unresolved` est rapporté comme tel, jamais
  reformulé comme s'il était résolu.

## `validate_comm` → `ValidationReport`

- Version confrontée : `aster_version`, `image_digest`, `catalogue_hash`.
- Résultat : `valid`, `errors` (`ValidationFinding`, avec `code`,
  `command`, `line`, `message`, `source`), `warnings`.
- Couverture : `commands_checked` (avec `ok`) et `commands_not_checked`
  (avec `reasons`) — toujours mentionner le taux de couverture
  (`len(commands_checked)` vs `len(commands_not_checked)`), jamais
  seulement `valid=true/false` isolé de ce contexte.
