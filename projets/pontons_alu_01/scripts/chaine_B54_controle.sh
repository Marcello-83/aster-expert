#!/bin/bash
# Contrôle post-lot 54 : chaîne du tronc commun sur B54, .comm identique à celui du lot 54
# (sha256 56f07a29…), pour produire les MED unitaires (charges.med, resultats.med).
set -e
cd "$(git rev-parse --show-toplevel)"
export PONTONS_VARIANTE=B54
REF=${1:-projets/pontons_alu_01/resultats/lot54/B54/pontons_alu_01.comm}
for e in maillage generer valider; do
  echo "=== $e"; .venv/bin/aster-expert projet pontons_alu_01 $e
done
sha256sum projets/pontons_alu_01/resultats/pontons_alu_01.comm
if [ -f "$REF" ]; then sha256sum "$REF"; cmp projets/pontons_alu_01/resultats/pontons_alu_01.comm "$REF"; fi
echo "=== executer"; .venv/bin/aster-expert projet pontons_alu_01 executer
for s in preparer executer verifier traiter; do
  echo "=== livrables $s"; .venv/bin/aster-expert projet pontons_alu_01 livrables --sous-etape $s
done
echo FIN_CHAINE
