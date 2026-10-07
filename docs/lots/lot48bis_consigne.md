# Lot 48 bis — consigne (recopiée de la demande de MM)

Lot 48 bis — Corriger ce que l'audit a trouvé de silencieux ou de bloquant. Tout en français. Profil `cloud`. Branche de travail Cloud, depuis `main` après la fusion de la branche de l'audit du lot 48. Aucun envoi sur `main`. Consigne copiée dans `docs/lots/lot48bis_consigne.md`.

Lot court et ciblé. Il traite les recommandations de l'audit (`docs/audit/audit_lot48.md`) qui sont à faible effort et à forte valeur : R3, R4, R6, R8, et R10 (a, c, e). Il ne touche à aucun résultat d'ouvrage.

## 1. Défauts silencieux (R3, A15, A16)

1. Validation B. `validate` et `validate_comm` ne répondent plus « valide » quand une commande n'a pas été confrontée au catalogue. Le verdict devient « partiel », avec un code de sortie non nul, et la liste des commandes non vérifiées.
   * Résous les tuples de concepts (`CHAR_MECA_GLOBAL=(CL,)`) pour que la commande et toute la suite du fichier soient confrontées.
   * Rejoue la sonde de l'audit (`MOT_INEXISTANT=1` derrière un tuple) : elle doit maintenant échouer.
2. Rejeu. `rejouer-references` et `constats rejouer` répondent avec un code non nul dès qu'un cas est « non rejouable ».
3. REF-014 redevient rejouable sur ses trois maillages. Les cas de référence sont exemptés de la règle de déclaration des connaissances du lot 46, ou reçoivent leur déclaration : justifie le choix. Rejoue les trois cas.
4. REF-015. Une référence dont les grandeurs sont dérivées (enveloppes, combinaisons, moyennes) ne peut pas être « établie » si l'outil ne sait pas la rejouer. Choisis l'une de deux voies et justifie-la : le rejeu passe par la lecture du projet ; ou REF-015 redescend à « observée », avec un motif. Ajoute une règle de schéma : une référence « établie » doit déclarer son mode de rejeu, et ce mode doit être testé.

## 2. Contrôles exécutables partout (R4)

1. Termes confidentiels hors de la VM. La liste est fournie au Cloud et à l'intégration continue par un secret (GitHub Actions, et variable d'environnement de la session Cloud), jamais par un fichier versionné. Sans la liste, le contrôle de publication d'un projet réel échoue, au lieu de passer en silence. Documente dans `docs/cloud.md` comment MM crée le secret, sans écrire les termes.
2. Intégration continue. `ci.yml` se déclenche sur `main` et sur toutes les branches `claude/**`. `ci-lent`, rejeu des références compris, se déclenche automatiquement quand un envoi touche `src/aster_expert/execution/`, `validation/` ou `connaissances/`. Mesure la durée et le coût en minutes, et rapporte-les.
3. Vérification locale avant envoi. Six échecs d'intégration continue en quatre lots venaient d'un envoi sans contrôle local. Ajoute un crochet `pre-push` qui lance `ruff format --check`, `ruff check` et `pytest` (hors tests lents). Une règle écrite dans `CLAUDE.md` n'a pas suffi.

## 3. Fiche : commandes prévues et arbitrages (R6)

1. `projet <nom> verifier` exige `planned_commands` dans la fiche, pour que `fiche obligatoires` serve. Renseigne-les pour la dalle et l'estacade, d'après leur `.comm`. Le quai est traité au point 4. Rapporte ce que `fiche obligatoires` trouve alors sur chacun.
2. Commande générique `aster-expert fiche enregistrer <projet> <arbitrage.md>`, qui remplace les scripts de lot du type `fiche_lot47.py`. Teste-la en rejouant l'enregistrement d'E13 à E16 de l'estacade. Le résultat doit être identique.

## 4. Bloqueurs de génération limités à leur étape (R8)

Un point en révision ne bloque que les étapes qui en dépendent. Es ne sert qu'au ferraillage : `projet quai_cw_test_01 verifier`, `generate` et `valider` doivent de nouveau passer, et le ferraillage du quai reste bloqué tant que PRE-032 n'est pas appliqué. Réexporte les paquets de la dalle et du quai avec le harnais D, sur un arbre propre, sans exécution nouvelle si le paquet le permet. Sinon, signale-le pour le lot 49, qui tourne dans la VM.

## 5. Allègements (R10 a, c, e)

1. `CLAUDE.md` ne garde que les règles en vigueur. L'historique des lots part dans `docs/etat.yaml` et les comptes rendus. Vise moins de 400 lignes, sans perdre une seule règle : liste les règles avant et après.
2. `analyze_comm` et `validate_comm` reçoivent un mode résumé, activé par défaut au-delà d'une taille (commandes par type, concepts, erreurs, avertissements, couverture). Le détail reste disponible sur demande, filtré par commande ou par plage de lignes. Cible : moins de 20 000 caractères sur le `.comm` de l'estacade.
3. Supprime le code mort relevé par l'audit (3 fonctions, `config/retrieval.yaml` s'il n'est lu que par les tests), et le test de frontière du tronc commun couvre aussi les noms de la dalle et de l'estacade.

## 6. Nombres dans les maillages et les fichiers produits (remarque de MM)

Des coordonnées du type `2.4999999999` ou `0.30000000004` n'apportent rien et gênent la lecture et la recherche de nœuds.

1. Fait à établir : dans un MED, les coordonnées sont des réels binaires de taille fixe ; les arrondir ne réduit ni la taille ni le nombre de lignes. Le vérifier sur un maillage versionné.
2. Règle pour les scripts de maillage : sommets construits à partir de valeurs exactes, coordonnées recalées sur une grille (1 mm, à justifier) avant l'écriture. Invariant générique de `mesh check` : « aucune coordonnée à moins de ε d'un multiple de la grille sans y être », appliqué aux maillages versionnés, écarts rapportés sans modifier les maillages.
3. Sorties texte (CSV, Excel, notes, `.comm` générés) arrondies selon l'unité, table unique dans `config/` (m à 3 décimales, kN à 1, kN·m à 1, MPa à 2). Les valeurs dérivées d'un calcul exact gardent leur précision dans le `.comm`, avec un commentaire donnant la valeur arrondie. Les contrôles numériques travaillent sur les valeurs non arrondies.

## Contrôles

`aster-expert env-check`, `aster-expert mcp-check`, `ruff format --check`, `ruff check`, `pytest`, `pytest -m lent_aster`, `mypy src`, `mypy`, `aster-expert connaissances verifier`, `aster-expert connaissances rejouer-references --reference REF-014`, `aster-expert etat verifier`.

## Interdits

Aucun résultat d'ouvrage modifié. Aucun terme confidentiel dans un fichier versionné, un journal ou un message de commit. Aucune règle de `CLAUDE.md` supprimée sans être conservée ailleurs ou remplacée par un contrôle exécutable.
