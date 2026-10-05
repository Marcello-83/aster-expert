# Lot 46 — Socle : sécurité MCP, intégration continue, état versionné, trace des connaissances appliquées

Consigne de MM, copiée telle quelle au lancement du lot (profil `cloud`, branche
`lot-46` créée depuis `main` après fusion de `lot-45`, aucun envoi sur `main`).

## Contexte

Un audit externe, statique, a été fait sur le dépôt. MM et Claude en retiennent les
points ci-dessous et écartent les autres. Ce lot les traite, avec les lacunes relevées
aux lots 44 et 45, avant les lots d'ouvrages nouveaux. Il ne produit aucun résultat
d'ouvrage nouveau.

## Décisions de MM, validées par le lancement du lot

1. Texte de PRE-032 (Es = 200 GPa). Remplace le texte rédigé par la session au lot 45 :
   - option_retained : module d'élasticité des armatures de béton armé, Es = 200 GPa,
     pour tous les projets.
   - justification : valeur de calcul de l'EN 1992-1-1, 3.2.7(4). La valeur de 210 GPa
     est celle des aciers de construction (EN 1993-1-1, 3.2.6) et ne s'applique pas aux
     armatures.
   - validity_domain : armatures passives de béton armé. Hors domaine : acier de
     construction (tubes, palplanches, profilés), qui garde 210 GPa.
   - discarded_variants : Es = 210 GPa pour les armatures. Motif : valeur de l'EN 1993,
     non conforme à l'EN 1992-1-1.
   Le quai n'est pas recalculé dans ce lot.
2. Interventions du superviseur au lot 45 : 1. C'est l'arbitrage des trois points de la
   partie A sur la conservation des niveaux. C'était une information qui manquait, pas
   une correction. Déclarer cette valeur dans les registres concernés, sans recalculer
   les métriques (voir étape 4).
3. Marqueur `[À CONFIRMER MM]` dans l'historique du quai. Il est accepté tel que la
   note l'affiche, entre guillemets. C'est l'historique d'une révision levée, pas un
   texte en vigueur. Le contrôle des notes doit faire la différence explicitement : un
   marqueur dans un texte en vigueur fait échouer le contrôle, un marqueur dans un
   historique est autorisé s'il est cité. Ajouter un test.

## Étapes

- Étape 0 : `aster-expert env-check`, puis `aster-expert mcp-check`.
- Étape 1 : politique de lecture des outils MCP (fonction commune de résolution des
  chemins d'entrée ; politiques de lecture et d'exécution configurées dans `config/` ;
  application à tous les outils MCP et toutes les commandes recevant un chemin ; refus
  lisible ; tests : `../../x.comm`, chemin absolu hors racine, lien symbolique hors
  racine, racine externe déclarée, extension autre que `.comm`).
- Étape 2 : intégration continue GitHub Actions (workflow `pull_request` et `push` sur
  `lot-*` ; second workflow `workflow_dispatch` pour `pytest -m lent_aster` ; durée et
  coût ; règle dans `CLAUDE.md` : MM ne fusionne que si l'intégration continue est verte).
- Étape 3 : `docs/etat.yaml` lisible par la machine, section d'état du README générée,
  journal de `development-plan.md` remplacé par un renvoi, `requires-python =
  ">=3.12,<3.13"`, règle dans `CLAUDE.md` : tout lot met à jour `docs/etat.yaml`.
- Étape 4 : manifeste de l'archive d'exécution ; `rex` refuse d'écrire les métriques si
  l'archive est absente, partielle ou non conforme ; tests ignorés avec motif ; retrait
  du contournement manuel du lot 45 dans `CLAUDE.md`.
- Étape 5 : trace des connaissances appliquées par exécution (déclaration, règles
  d'épreuve par type d'entrée, obligation dans le skill, signalement par `rex`, aucune
  attribution rétroactive, test sur la dalle dans le Cloud).
- Étape 6 : harnais de niveau D par défaut (CTL-005, CTL-006, CTL-012 + quatre contrôles
  génériques ; désactivation motivée dans `projet.yaml`, affichée par la note ; mêmes
  verdicts D que ceux de la dalle ; quai par relecture du paquet, sans exécution).

## Contrôles

`aster-expert env-check`, `aster-expert mcp-check`, `ruff format --check`, `ruff check`,
`pytest tests/unit`, `pytest`, `pytest -m lent_aster`, `mypy src`, `mypy`,
`aster-expert connaissances verifier`. `rex` n'écrit pas de métriques dans le Cloud :
montrer seulement qu'il refuse proprement.

## Compte rendu attendu (en français)

1. Décisions appliquées. 2. Politique de lecture. 3. Intégration continue. 4. `docs/etat.yaml`,
README généré, `requires-python`. 5. Manifeste d'archive et `rex` dans le Cloud. 6. Trace
des connaissances. 7. Harnais D par défaut. 8. Commandes de contrôle, interventions.

## Interdits

Aucun changement de résultat d'ouvrage ; aucune attribution rétroactive d'épreuve ; aucun
envoi sur `main` ; aucun changement de visibilité du dépôt ; aucun identifiant Code_Aster
énoncé de mémoire.
