# Exemples de référence

Contrairement à `data/raw`/`data/processed`/`data/indexes` (produits par le
pipeline, non versionnés), ce répertoire est versionné : il joue pour le
schéma de `aster_expert.agent.hypotheses` le même rôle que
`data/evaluations/` joue pour le banc de recherche — des données sources du
projet, écrites une fois à la main, pas régénérées.

## `hypotheses_combiwall_reference.json`

Transcription intégrale, lot 14 (M5), du spécimen de fiche d'hypothèses
produit lors d'un essai d'usage réel des outils MCP (recherche documentaire
et schéma de catalogue) sur un quai en combi-wall ancré — le cas qui a
motivé le lot 8c (`get_document_section`) et la conception du schéma
`HypothesesSheet` de ce lot.

**Statut.** C'est un exemple de référence pour valider le schéma contre un
cas réel, pas une fiche produite pour un projet en cours ni un livrable
d'ingénierie (CLAUDE.md, principe 11 : rien ici ne doit être présenté comme
un résultat réel de projet). `project_name` le rappelle explicitement dans
son propre texte. La date `created_at` (2026-09-18) est celle de la
transcription, pas nécessairement celle de l'essai original, inconnue.

**Fidélité de la transcription.** Chaque `document_id`, `section_path`,
`source_path` et extrait (`excerpt`) provient mot pour mot du texte du
spécimen ; rien n'a été inventé pour combler un champ absent — cinq
citations du spécimen (R7.01.25, R7.01.28, R7.01.14, R7.01.18, R7.01.23)
n'y donnaient pas de chemin source, et R7.01.23 n'y donnait même pas de
section : `source_path=null`/`section_path=[]` le reflètent tel quel
(`aster_expert.agent.hypotheses`, docstring du module, M5 correction 3).
Les cinq points que le spécimen rapportait comme non fondés par le corpus
(« Bilan 2 » du spécimen) sont ici des `PracticeHypothesisEntry` à
`status="non_tranche"` — huit au total, le point 1 s'étant décomposé en
deux questions distinctes (famille d'éléments, homogénéisation) à la
transcription.

**Ce qu'il ne couvre pas.** M4 (section `group_naming`) est vide : le
spécimen prédate cette exigence du schéma et ne discute jamais de noms de
groupes de mailles/nœuds — M4 n'est validé que par test unitaire
(`tests/unit/test_agent_hypotheses.py`), pas par ce cas réel.

Vérifié par `tests/unit/test_hypotheses_combiwall_reference.py` : le
fichier se recharge sans erreur contre `HypothesesSheet`
(`model_validate_json`), et son compte d'entrées non tranchées/tranchées
correspond aux bilans du spécimen.
