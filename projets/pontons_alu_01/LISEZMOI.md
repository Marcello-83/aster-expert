# Projet PONTONS-ALU-01

Panne (passerelle d'accès sur pieux) en aluminium soudé : une travée de 6,25 m, poutres principales MP1200, montants, diagonales et pannes secondaires tubulaires, profilés supports sur chevêtre béton neuf, deux poteaux et demi-semelle sur sol élastique ; reprise PRO d'un AVP Sofistik

Créé par `aster-expert projet creer pontons_alu_01` : arborescence, `projet.yaml` minimal,
racines d'exécution (`config/validation.yaml`) et registre `rex`
(`connaissances/rex/pontons_alu_01.yaml`). Tout le reste est à écrire.

| Répertoire | Contenu |
| --- | --- |
| `fiche/` | fiche d'hypothèses (skill `hypotheses-drafting`) et document d'arbitrage |
| `donnees/` | données du modèle et leurs sources recopiées à l'identique |
| `maillage/` | script Salomé et invariants (calculés analytiquement avant exécution) |
| `extensions.py` | générateur du `.comm` et extensions déclarées |
| `scripts/`, `tests/` | scripts de lot et tests propres au projet |
| `references/cas/` | cas versionnés rejouables (constats, références de validation) |
| `resultats/` | sorties de `aster-expert projet pontons_alu_01 <étape>` (non versionné) |
