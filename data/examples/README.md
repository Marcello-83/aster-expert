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

**Correction lot 14b (N1).** La citation R7.01.25 (point 4, alternatives au
contact surfacique) restait sans `excerpt` ni `source_path` : une entrée
`tranche` fondée sur une référence jamais lue, exactement la lacune que le
lot 14 avait notée sans la corriger ("Limites connues"). Corrigée en
relisant réellement R7.01.25 via `get_document_section` (lot 14b) plutôt
qu'en inventant un passage — le contenu réel confirme que ce document
documente des lois de joint pour les barrages, sans jamais dire s'il
s'applique à une interface sol-écran. Les quatre autres citations sans
chemin (R7.01.28, R7.01.14, R7.01.18, R7.01.23) restent inchangées : chacune
partage son entrée avec au moins une autre citation qui, elle, porte un
excerpt réel (§ N1, `_require_a_verbatim_excerpt_when_documentary` — au
moins un excerpt par entrée, pas un par citation), donc aucune ne violait la
nouvelle règle structurelle.
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

**Lot 15, canal d'arbitrage.** Les huit entrées `pratique`/`non_tranche`
de ce fichier restaient, avant ce lot, bloquées par construction : aucune
fonction du projet ne pouvait faire passer une entrée `pratique` à
`status="tranche"`, pas même une décision humaine. `aster_expert.agent.
arbitration.record_practice_decision` ouvre ce chemin (voir
`docs/development-plan.md`, clôture lot 15). Ce fichier reste inchangé et
`is_ready_for_generation=False` : ce lot n'y a fait passer aucune décision
-- la fiche de décision qu'il produit à partir de ce spécimen
(`/media/sf_partage/echanges/fiche_decision_combiwall_arbitrage_pratique.md`,
non versionnée) présente les huit points à un ingénieur, sans y répondre.
