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
