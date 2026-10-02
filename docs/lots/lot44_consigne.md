# Lot 44 — Consolidation de l'outil après le second ouvrage

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français : terminal,
résumé final, compte rendu, commit, rapports, commentaires.

**Profil : `vm`** (les archives d'exécution servent au recalcul des métriques).
Branche `lot-44`, créée depuis `main` après fusion de `lot-43`. Consigne copiée
dans `docs/lots/lot44_consigne.md`.

## Contexte

La dalle (lot 43) a atteint le niveau E en un lot, avec 5 exécutions, 0 échec, 2
interventions et 11 erreurs évitées par la base. C'est un cas d'école : le
résultat est encourageant, mais il ne prouve rien sur un ouvrage réel. Ce lot
corrige les lacunes que la dalle a mises au jour, **avant** le troisième ouvrage.
Il ne produit aucun nouveau calcul d'ouvrage.

**Décisions de MM, validées par le lancement du lot :**

- **D20** — situation accidentelle : γc = 1,2 et γs = 1,0.
- **D21** — poutre de couronnement du quai, maîtrise de la fissuration :
  - Act est la zone tendue complète, b·h, l'élément étant tendu (EN 1992-1-1,
    7.3.2) ;
  - σs est tiré du tableau 7.2N, avec le diamètre modifié par 7.6N ;
  - φ40 ;
  - wk = 0,2 mm.

  **Domaine de validité** : éléments tendus ou en traction gênée. Il exclut la
  flexion simple, comme la dalle l'a montré au lot 43 (kc = 0,4 et Act = b·h/2).
- **Module de l'acier : Es = 200 GPa** (EN 1992-1-1, 3.2.7(4)), au lieu des
  210 GPa communiqués au lot 43.
  - La valeur de 210 GPa est celle des aciers de construction (EN 1993). La
    réglementation du béton armé retient 200 GPa pour les armatures.
  - αe = 15 est maintenu : c'est un coefficient d'équivalence de long terme,
    choisi délibérément, indépendant de Es.
  - Le précédent de la dalle qui porte Es est corrigé, avec la mention de la
    décision. Le ferraillage de la dalle est recalculé, et l'écart est
    rapporté. L'ELS ne gouvernant pas, aucun changement de résultat n'est
    attendu.

## Étape 0

`aster-expert env-check`, puis `aster-expert mcp-check`.

## Étape 1 — Troisième catégorie de la fiche : les choix de l'agent

Au lot 43, 15 bloqueurs sur 31 n'avaient pas à remonter à MM.

1. Ajoute au schéma de la fiche une origine `choix_agent` : un choix de
   modélisation proposé par l'agent, et **vérifié par un contrôle ou par une
   référence de validation désignés nommément**.
   - Un choix `choix_agent` sans contrôle désigné est refusé par le schéma.
   - Il ne bloque pas la génération.
   - Il apparaît dans le document d'arbitrage, dans une section séparée, où MM
     peut le remplacer.
2. Établis la règle de partage dans `CLAUDE.md` et dans le skill
   `hypotheses-drafting`.
   - **Relève de `choix_agent`** ce que les contrôles ou le niveau E
     vérifient : noms de groupes, repère, type et taille des mailles, suite de
     convergence, lecture des champs (`NOEU`/`ELNO`), blocage isostatique des
     mouvements de corps rigide, étendue du modèle quand la symétrie est
     contrôlée.
   - **Reste à MM** ce qui engage l'ouvrage : matériaux, actions, combinaisons,
     durabilité, conditions d'appui physiques, paramètres de ferraillage,
     choix d'une modélisation qui change la physique représentée.
3. **Rejeu** sur la fiche de la phase 1 du lot 43. Rapporte combien de
   bloqueurs deviennent des `choix_agent`. L'attendu est d'environ 15 sur 31.

## Étape 2 — Paramètres obligatoires détectés à la rédaction de la fiche

Au lot 43, U4.81.42 rendait obligatoires σc, αe, KT et Es pour l'ELS 2D, et la
fiche ne les demandait pas. Il a fallu une seconde intervention.

1. Quand la fiche prévoit une commande et ses options, l'outil lit dans le
   catalogue 17.4 les mots-clés **obligatoires** de cette combinaison d'options.
   Il ajoute chacun de ceux qui n'ont pas de valeur à la fiche, comme point à
   trancher, dans la bonne catégorie.
2. Test de non-régression : sur la fiche de la phase 1 du lot 43, l'outil doit
   retrouver les quatre paramètres ELS.

## Étape 3 — Création d'un projet en une commande

`aster-expert projet creer <nom>` crée en une fois :

- l'arborescence ;
- un `projet.yaml` minimal valide ;
- les racines d'exécution dans `config/validation.yaml` ;
- le registre `rex`.

Ajoute un test qui crée un projet temporaire et passe `rex` sans erreur.

## Étape 4 — `get_command_schema` filtré

Filtré par mot-clé, l'outil renvoyait au lot 43 tout le schéma (721 000
caractères pour `DEFI_MATERIAU`/`ELAS`). Avec un filtre, il ne doit renvoyer
que le sous-arbre demandé. Test : `DEFI_MATERIAU` filtré sur `ELAS` renvoie
moins de 50 000 caractères et ne contient aucun autre mot-clé facteur.

Cet outil MCP est modifié : MM redémarrera la session après le lot.

## Étape 5 — Règle de promotion : distinguer la citation de l'épreuve

1. Une entrée compte comme réutilisée par un projet seulement si ce projet l'a
   **éprouvée** : par une exécution dont le résultat la vérifie, ou par un
   contrôle qui l'applique et passe. Une citation dans une fiche n'est pas une
   épreuve.
2. Rejoue l'éligibilité de toutes les entrées.
3. **Promotion autorisée dans ce lot**, par la commande `promouvoir`, pour les
   entrées qui satisfont la règle corrigée. Liste-les dans le compte rendu,
   avec, pour chacune, l'épreuve dans chacun des deux projets ou le niveau E.
   Au lot 43, CA-025 et CA-041 n'étaient éligibles que formellement : ils ne
   doivent plus l'être.

## Étape 6 — Métriques

1. **Exécutions de développement et de vérification.**
   - Une exécution de vérification est le rejeu d'un cas déjà réussi sans
     modification du `.comm` (même empreinte), ou une exécution lancée par une
     commande de rejeu : constats, `rejouer-references`, tests lents.
   - Le taux d'échec est calculé **sur les exécutions de développement
     seulement**. Les deux nombres sont affichés.
   - Recalcule le quai et la dalle. Le taux du quai doit retrouver un ordre de
     grandeur cohérent avec les 38 % de la référence. S'il s'en écarte, explique
     pourquoi.
2. **Interventions** : lot 43 = 2, déclarées par MM.
   - La section B de l'arbitrage compte pour une.
   - Les quatre paramètres ELS comptent pour une.
   - L'arrêt pour arbitrage était prévu et ne compte pas.
3. **Candidats patrons.** Le seuil de similarité actuel produit du bruit :
   15 candidats entre 0,20 et 0,43. Fixe un seuil justifié par les données du
   quai et de la dalle, et rapporte la liste obtenue.
4. Mets à jour le tableau de bord.

## Étape 7 — Précédents manquants et anomalies ouvertes

1. Verse D20 et D21 dans `precedents/`, avec leur domaine de validité.
   L'arbitrage de la dalle citait par erreur « PRE-021 » pour D21 : ajoute une
   note de correspondance dans l'entrée de D21, quel que soit son numéro.
2. **CA-052 et REF-012** :
   - CA-052 : à l'ELS 2D, `CALC_FERRAILLAGE` donne 3 à 4 % de plus que le
     calcul de R7.04.05, sensible à `SIGC_*_ELS` ;
   - REF-012 : à l'ELS 1D, l'écart est de −4,4 %.

   Elles portent peut-être sur une même cause. Relie-les dans la base comme
   **une seule anomalie ouverte**, avec les deux signatures. N'enquête pas dans
   ce lot.

## Étape 8 — Banc d'évaluation et aiguillage des requêtes

1. Le tri validé par MM est dans
   `/media/sf_partage/echanges/tri_questions_candidates_lot42.md` : 22
   questions retenues, 17 écartées.
   - Pour chaque question retenue, **établis le document attendu en lisant la
     documentation**. La colonne du tri n'est qu'une hypothèse.
   - Une question à laquelle aucun document ne répond entre comme « non
     documentée ».
   - Verse les 22 questions au banc et relance-le. Rapporte le score par
     profil, avant et après.
2. **Aiguillage dans le skill `code-aster-expert`** :
   - nom de cas test → `search_test_cases` ;
   - comportement établi par exécution → `search_connaissances` ;
   - principe ou syntaxe → documentation.
3. **Reformulation** : une requête faite d'une liste de mots-clés est
   reformulée en langage naturel avant la recherche. Mesure l'effet sur les
   questions cand-019 et cand-021, qui échouaient au lot 42.

## Contrôles

```bash
aster-expert env-check
aster-expert mcp-check
ruff format --check
ruff check
pytest tests/unit
pytest
pytest -m lent
mypy src
mypy
aster-expert connaissances verifier
aster-expert rex quai_cw_test_01
aster-expert rex dalle_appuyee_01
```

## Compte rendu attendu — EN FRANÇAIS

1. Catégorie `choix_agent` : règle de partage, et rejeu sur la fiche du lot 43
   (nombre de bloqueurs avant et après).
2. Détection des paramètres obligatoires : rejeu des quatre paramètres ELS.
3. `projet creer`, et `get_command_schema` filtré (taille avant et après).
4. Promotion : règle corrigée, entrées promues avec leur épreuve, entrées
   devenues inéligibles.
5. Métriques recalculées (développement et vérification, quai et dalle), seuil
   des patrons, tableau de bord.
6. D20, D21, correction de Es, anomalie ouverte CA-052/REF-012.
7. Banc : documents attendus établis, scores par profil avant et après, effet de
   l'aiguillage et de la reformulation.
8. Sortie des commandes de contrôle, dont `rex`, et interventions du lot.

## Interdits

- Aucun changement de résultat du quai ou de la dalle, sauf le recalcul dû à Es,
  rapporté.
- Aucune promotion hors de la règle corrigée.
- Aucune entrée `choix_agent` sans contrôle désigné.
- Aucune note Word : elles font l'objet du lot 45.
