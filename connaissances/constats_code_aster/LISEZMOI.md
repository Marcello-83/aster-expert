# Base partagée des constats Code_Aster (lot 41)

Un fichier par constat, `CA-nnn.json` (modèle `aster_expert.constats.models.Constat`) :
identifiant, résumé du piège en une phrase, version de Code_Aster, niveau atteint
(A documentaire, B catalogue introspecté, C ou D exécution d'un cas d'essai
versionné), commandes et mots-clés du catalogue concernés, cas d'essai, origine
(fiche et point d'où le constat a été extrait) et l'entrée complète avec ses sources.
Chaque champ dérivé est recontrôlé à la lecture.

- Les 45 premiers (`CA-001` à `CA-045`) viennent de la fiche du quai
  (`projets/quai_cw_test_01/scripts/extraire_constats_lot41.py`) ; la fiche les cite
  désormais par référence.
- Recherche : outil MCP `search_constats`, `aster-expert constats chercher`.
- Rejeu à chaque changement de version : `aster-expert constats rejouer` (dernier
  rejeu : `rejeu/`).
- Un constat nouveau s'ajoute ici, jamais dans une fiche ; une correction se fait
  ici, et `externalize_sheet` refuse une fiche dont un constat diffère de la base.
