---
name: hypotheses-drafting
description: >-
  Use when drafting a PROJECT fiche d'hypothèses (aster_expert.agent.hypotheses.HypothesesSheet)
  from a physical description of a structure — turning what was done by
  hand for the combi-wall trial into a reproducible procedure. Requires the
  code-aster-expert skill's tool discipline (search_codeaster_docs,
  get_document_section, get_command_schema) and the write-path barrier in
  aster_expert.agent.drafting. Never produces a validated fiche, only a
  draft submitted to the engineer.
---

# Rédiger une fiche d'hypothèses (projet, jamais validée)

Ce skill décrit comment instruire chaque point d'une fiche d'hypothèses à
partir de la trame par défaut (`data/config/hypotheses_trame_defaut.json`,
chargée par `aster_expert.agent.drafting.load_trame`/`default_trame_path`),
en s'appuyant sur les outils MCP `aster-expert` (voir le skill
`code-aster-expert` pour leur discipline d'usage : choix du profil, lecture
intégrale avant de conclure, citation systématique). Il ne contient aucune
connaissance Code_Aster de première main et ne décide jamais rien à la
place de l'ingénieur.

**Le livrable est un projet.** `HypothesesSheet.is_ready_for_generation`
peut être vrai sans que la fiche soit validée : aucun mécanisme de ce
projet ne fait tenir lieu de validation d'ingénieur à ce champ. Le dire
explicitement dans toute réponse qui présente une fiche produite par ce
skill.

## 1. Charger la trame et parcourir ses rubriques dans l'ordre

```python
from pathlib import Path
from aster_expert.agent.drafting import default_trame_path, load_trame

trame = load_trame(default_trame_path(Path.cwd()))
```

Chaque `TrameTopic` (`label`, `heading`, `prompt`, `profile_hint`) est un
point à instruire, pas un texte à recopier dans la fiche : un même point
peut se décomposer en plusieurs `HypothesisEntry` (un fait catalogue, une
question de pratique côte à côte — voir le spécimen combi-wall). Adapter
les rubriques au vocabulaire de l'ouvrage traité (« le composant 1 » du
combi-wall est un écran ; sur un radier, c'est le radier lui-même) sans
changer la trame elle-même.

## 2. Pour chaque point : chercher, lire, confronter, puis écrire

1. **Chercher** avec `search_codeaster_docs`, sous le `profile_hint` de la
   rubrique par défaut, ajusté si la question posée ne correspond pas à ce
   défaut (un `profile` mal choisi dégrade la pertinence sans jamais
   provoquer d'erreur — le choisir consciemment, pas à l'aveugle).
2. **Lire** la section entière avec `get_document_section` avant de
   conclure quoi que ce soit sur son contenu — un extrait de tête de
   `search_codeaster_docs` (280 caractères) ne fonde jamais une
   affirmation à lui seul (skill `code-aster-expert`, §5).
3. **Confronter au catalogue** avec `get_command_schema` dès qu'un
   identifiant Code_Aster (commande, mot-clé, valeur de mot-clé) est en
   jeu — jamais une syntaxe affirmée de mémoire.
4. **Créer l'entrée** :
   - Si la lecture confirme réellement le point : construire les
     `CodeAsterSource` (un par citation retenue) et appeler
     `aster_expert.agent.drafting.record_code_aster_finding` avec l'option
     retenue et sa justification. Si aucune citation ne porte un `excerpt`
     réel (un fait purement catalogue en est dispensé, voir le module
     `aster_expert.agent.hypotheses`, N1), l'appel lève
     `pydantic.ValidationError` — c'est le signal d'aller relire la
     section pour de vrai, jamais de fabriquer un extrait pour faire
     passer l'appel.
   - Si rien trouvé ne fonde le point (aucun résultat pertinent, ou un
     résultat hors sujet malgré plusieurs profils essayés) : construire un
     `SearchAttempt` par recherche tentée (`profile`, `query`, `outcome`)
     et appeler `aster_expert.agent.drafting.record_unfounded_point`.
     Cette fonction ne prend ni `option_retained`, ni `justification`, ni
     `sources` — il est structurellement impossible d'en sortir autre
     chose qu'une entrée `pratique`/`non_tranche`. Une déduction
     d'ingénierie qui relie un fait catalogue à la situation du projet,
     sans qu'un document ne le formule, va dans `deduction` — jamais
     présentée comme une décision.
   - Point de pratique (lot 42) : avant d'en proposer une option, chercher
     les précédents d'autres projets (`search_connaissances(text=...,
     layers=["precedents"])`, consultation obligatoire du skill
     `code-aster-expert`, § 6 quater). Un précédent n'est jamais appliqué :
     il se cite dans la trace du point non fondé et se propose par
     `aster-expert connaissances proposer-precedent <PRE-nnn> --point <p>`
     (entrée non tranchée, source `precedent_projet` prête pour MM), avec
     son domaine de validité à confronter à l'ouvrage. MM arbitre.

   - Choix de modélisation vérifié par contrôle (lot 44) : voir § 2 bis ;
     chemin d'écriture `aster_expert.agent.arbitration.record_agent_choice`.

Aucune autre voie : pas d'entrée créée à la main en dehors de ces fonctions
pour ce skill, précisément pour que le chemin d'écriture reste couvert par la
même barrière que le schéma (`docs/development-plan.md`, lot 14b, N3).

## 2 bis. Règle de partage : ce que l'agent tranche, ce qui reste à MM (lot 44)

Au lot 43, 15 des 31 bloqueurs de la première fiche de la dalle étaient des
choix techniques qu'un contrôle ou le niveau E vérifie : MM n'avait pas à les
trancher. La fiche a une troisième catégorie, l'origine `choix_agent`.

**Relève de `choix_agent`** (et seulement cela, `AgentChoiceDomain`) : noms de
groupes ; repère, origine et unités ; type et taille des mailles ; suite de
convergence ; lecture des champs (`NOEU`/`ELNO`) ; blocage isostatique des
mouvements de corps rigide ; étendue du modèle quand la symétrie est contrôlée.

**Reste à MM** : ce qui engage l'ouvrage — matériaux, actions, combinaisons,
durabilité, conditions d'appui physiques, paramètres de ferraillage, et tout choix
de modélisation qui change la physique représentée (DKT ou DST, périmètre du
calcul, appui bilatéral ou unilatéral…).

Règles :

1. Un `choix_agent` **nomme ses vérificateurs** (`verified_by`) : un contrôle
   `CTL-nnn` ou une référence `REF-nnn` de `connaissances/`, ou un contrôle déclaré
   par le projet (`projet:<nom>`). Sans vérificateur, ou hors des domaines
   ci-dessus, le schéma le refuse. Chercher le contrôle existant
   (`search_connaissances(layers=["controles", "references_validation"])`) avant
   d'en inventer un.
2. Il s'écrit par `record_agent_choice(entry=<question>, domain=…, verified_by=…,
   option_retained=…, justification=…, validity_domain=…, discarded_variants=…,
   reference=…, decided_at=…)` : entrée `tranche`, `decided_by` « agent
   (choix_agent) ». Un point qui couvre plusieurs domaines (mailles, convergence,
   lecture) passe un tuple de domaines.
3. Une question qui mêle les deux catégories **se scinde** : la moitié qui engage
   l'ouvrage reste une question (`record_unfounded_point`), l'autre devient un
   `choix_agent` (rejeu du lot 44 : point 6 de la dalle, appui physique d'un côté,
   blocage isostatique et dalle entière de l'autre).
4. Il ne bloque pas la génération et figure dans une section séparée du document
   d'arbitrage (`render_decision_sheet`) : MM peut le remplacer par
   `record_practice_decision`, le choix de l'agent passe alors dans
   `decision_history`.
5. Une valeur de données qui découle d'un `choix_agent` (taille de maille) est
   `fourni` avec la source `decision` du point.

## 2 ter. Paramètres obligatoires des commandes prévues (lot 44)

Dès que la fiche prévoit une commande et ses options (`CALC_FERRAILLAGE` en 2D à
l'ELS, par exemple), la déclarer dans la fiche (`HypothesesSheet.planned_commands`,
`PlannedCommand(command, point_label, options, covered_by)` ; `covered_by` relie un
mot-clé à une donnée `data:<groupe.clé>`, même « à fournir », ou à une question
`point:<p>`), puis lancer `aster-expert fiche obligatoires <fiche.json> --donnees
<données.yaml> --sortie <fiche.json>` (`aster_expert.agent.obligatoires`). L'outil lit
les mots-clés **obligatoires** de la combinaison d'options dans le catalogue de la
version cible **et** dans la table des obligations d'exécution
(`data/config/obligations_execution.yaml`) : en 17.4, `ALPHA_E`, `SIGC_*_ELS`,
`SIGC_ELS_QP`, `KT`, `EYS` de `CALC_FERRAILLAGE` sont `optional` au catalogue mais
refusés à l'exécution s'ils manquent (constat CA-053). Chaque mot-clé non couvert
devient une question non tranchée, dans sa catégorie (paramètre de ferraillage : MM ;
unité : choix de l'agent possible). Au lot 43, l'oubli de σc, αe, KT et Es a coûté
une intervention de MM. Une nouvelle obligation d'exécution découverte (arrêt `<F>`
pour mot-clé absent) s'ajoute à la table, avec ses sources.

## 3. Nommage des groupes (rubrique 7)

Un `MeshGroupNaming` par groupe `GROUP_MA`/`GROUP_NO` nécessaire — jamais
sourcé (ni `CodeAsterSource` ni `PracticeSource`). Depuis le lot 44, un nom de
groupe est un `choix_agent` (`status="choix_agent"`, `verified_by` : au moins
`CTL-008` invariants de maillage et `CTL-009` longueur des noms) ;
`status="non_tranche"` seulement si le nom dépend d'une question encore ouverte.

## 4. Rendre compte

Le compte rendu qui accompagne une fiche produite par ce skill donne, sans
exception : le nombre d'entrées `code_aster`/`tranche` (avec extrait
réel), le nombre d'entrées `pratique`/`non_tranche` (avec la trace des
recherches menées), le nombre de `choix_agent` (entrées et noms de groupes,
avec leurs vérificateurs), et `sheet.is_ready_for_generation` — jamais un de
ces chiffres sans les autres, et jamais présenté comme une validation
d'ingénieur.
