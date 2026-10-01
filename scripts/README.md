# scripts/

Scripts autonomes exécutés par l'interpréteur Python de l'installation
Code_Aster, jamais par le Python du projet (voir `docs/architecture.md`,
ADR-002).

Contraintes :

- bibliothèque standard uniquement, aucune dépendance du projet ;
- sortie exclusivement en JSON sur la sortie standard ;
- messages de diagnostic sur la sortie d'erreur ;
- code de retour non nul en cas d'échec, jamais de sortie partielle
  silencieuse.

Ce répertoire contient aussi les scripts d'essais génériques des lots (cas
d'essai sur plaques, barres, `CALC_FERRAILLAGE`, qualification Salomé du lot 26),
exécutés par le Python du projet. Depuis le lot 41, les scripts propres à un
ouvrage vivent dans son projet (`projets/<nom>/scripts/`, par exemple ceux du quai
dans `projets/quai_cw_test_01/scripts/`), jamais ici.
