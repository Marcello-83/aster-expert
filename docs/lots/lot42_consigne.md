# Lot 42 — Capitalisation : faire que chaque projet enrichisse l'outil

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français : terminal,
résumé final, compte rendu, commit, rapports, commentaires.

**Profil : `vm` obligatoire.** Les archives d'exécution du quai
(`data/processed/runs/`) ne sont pas versionnées : elles n'existent que dans la VM.
Branche `lot-42`, consigne copiée dans `docs/lots/lot42_consigne.md`, aucun envoi
direct sur `main`.

## Contexte et principe

Le lot 41 a séparé le tronc commun des projets. MM fixe une exigence
supplémentaire : **chaque projet doit rendre l'outil meilleur**, par ses
erreurs, par ses découvertes sur Code_Aster et par ses résultats.
L'analogie est celle d'un réseau qui apprend : l'expérience acquise sur un
projet remonte dans l'outil, et le projet suivant va plus vite et se trompe
moins.

Un agent ne modifie pas ses propres poids. Ce qu'il apprend doit donc être
**écrit dans le dépôt, sous une forme qu'il consulte avant d'agir** : une base
de connaissances structurée, interrogeable par les outils MCP, citée par le
skill, et protégée par des tests. Ce lot construit ce mécanisme et l'alimente
avec l'expérience du quai.

## Étape 0

`aster-expert env-check`, puis `aster-expert mcp-check`. Vérifie aussi que les
outils sont visibles dans la session, y compris `search_constats`, ajouté au
lot 41.

## Étape 1 — Les six couches de connaissance

Sous `connaissances/`, un répertoire par couche. Chaque entrée est un fichier
YAML validé par un schéma Pydantic, et porte :

- un identifiant stable ;
- le projet d'origine ;
- la date ;
- le niveau de validation ;
- ses sources, dont les empreintes des exécutions pour ce qui est établi par
  exécution ;
- les mots-clés et commandes Code_Aster concernés ;
- son statut (voir étape 2).

| Couche | Contenu | Exemple tiré du quai |
|---|---|---|
| `constats_code_aster/` (lot 41) | Comportement établi de Code_Aster, avec cas d'essai rejouable | `FORCE_COQUE` rapporte l'intensité à la surface développée |
| `diagnostics/` | Signature d'erreur ou d'alarme (identifiant `<F>`/`<A>`, motif du message), cause établie, correction, projet | `FACTOR_11`, pivot nul : condition aux limites et relation cinématique sur le même degré de liberté |
| `patrons/` | Recette de modélisation réutilisable : problème, solution, fragment de `.comm` ou de script Salomé, conditions d'emploi, contrôles qui la vérifient, constats liés | Ressorts de sol nodaux regroupés par classe de raideur, avec somme des raideurs aux nœuds communs |
| `controles/` | Contrôle de vérification réutilisable : ce qu'il détecte, comment il est paramétré, erreur réelle qu'il a attrapée | Demi-section obligatoire dans un plan de symétrie |
| `references_validation/` | Cas à solution connue (analytique ou référence externe), exécutable, avec critère et résultat | Console `ELAS_COQUE` (essai A du lot 22), demi-cylindre `FORCE_COQUE` |
| `precedents/` | Décisions pratiques de MM, avec justification et domaine de validité, réutilisables comme **précédents** | D5, ressorts côté bassin avec domaine de validité ; D21, Act = zone tendue complète |

**Règle sur les précédents.** Un précédent n'est jamais appliqué
automatiquement à un nouveau projet. Il peut être **proposé** dans une fiche,
avec l'origine `precedent_projet`, qui existe déjà dans le schéma. Il reste
soumis à l'arbitrage de MM. C'est le jugement d'ingénieur qui se capitalise, pas
une règle qui se substitue à lui.

## Étape 2 — Promotion : du projet vers le tronc commun

Pour éviter de polluer le tronc commun, chaque entrée a un statut :

1. **`observé`** : vu dans un projet, avec sa preuve.
2. **`établi`** : preuve rejouable, soit un cas d'essai exécuté, soit un test.
3. **`promu`** : réutilisé avec succès dans au moins **deux projets**, ou validé
   au niveau E. Un patron promu peut alors devenir une fonction du tronc commun,
   avec ses tests. Un contrôle promu entre dans le harnais par défaut.

La promotion est une commande explicite (`aster-expert connaissances promouvoir
<id>`). Elle vérifie les conditions et échoue sinon. Aucune promotion n'est
automatique.

## Étape 3 — Consultation obligatoire

1. Nouvel outil MCP `search_connaissances`, qui interroge les six couches par
   texte, commande ou mot-clé, et renvoie les entrées avec leur statut et leur
   niveau. Il remplace `search_constats`, ou l'englobe. Il est journalisé.
2. Le skill `code-aster-expert` rend la consultation **obligatoire** dans
   quatre situations :
   - avant d'écrire une commande Code_Aster : constats et patrons ;
   - dès qu'une erreur ou une alarme apparaît dans un `.mess` : diagnostics,
     avant toute autre hypothèse ;
   - avant de proposer une décision pratique : précédents ;
   - avant d'écrire un contrôle : contrôles existants.
3. `aster-expert run` : quand une exécution échoue, le compte rendu d'exécution
   (lot 41) cherche automatiquement la signature `<F>` dans `diagnostics/` et
   affiche les entrées correspondantes.

## Étape 4 — Retour d'expérience obligatoire en fin de projet ou de lot

Commande `aster-expert rex <projet>`, qui prépare le retour d'expérience :

- **Échecs.** Liste les exécutions échouées du projet depuis le dernier retour
  d'expérience, avec leur signature. Chaque échec doit être **classé** : soit
  rattaché à un diagnostic existant, soit ouvert comme nouveau diagnostic, soit
  écarté comme faute de frappe ou d'environnement, avec une phrase de motif.
  **Un échec non classé bloque la clôture du lot.**
- **Nouveaux faits Code_Aster.** Les constats du projet pas encore dans la base
  sont proposés à l'ajout.
- **Code du projet.** Les fonctions et fragments candidats à devenir des
  patrons sont signalés, par exemple par similarité avec les patrons existants.
- **Métriques du projet**, écrites dans `connaissances/metriques/` :
  - nombre de lots ;
  - nombre d'exécutions et taux d'échec ;
  - temps de calcul ;
  - nombre d'interventions du superviseur, que je renseigne dans le compte
    rendu ;
  - nombre de connaissances consultées, et combien ont évité une erreur ;
  - nombre de connaissances créées et promues.

**Les métriques sont la « fonction de perte » de l'outil.** D'un projet à
l'autre, le taux d'échec, les interventions et le nombre de lots par ouvrage
doivent baisser. Un tableau de bord Markdown les compare entre projets.

Règle à ajouter dans `CLAUDE.md` : **tout lot se termine par
`aster-expert rex`, et le compte rendu inclut sa sortie.**

## Étape 5 — Amorçage avec le quai

1. **Diagnostics.** Classe les 73 exécutions échouées du quai, archivées et
   relevées par l'audit : signature, cause, correction, à partir des rapports
   d'essais des lots 21 à 39. Les échecs de même cause sont regroupés. Ceux
   dont la cause n'est pas retrouvable sont écartés avec un motif.
2. **Constats** : déjà faits au lot 41, à vérifier seulement.
3. **Patrons** : au moins huit patrons tirés du quai, par exemple :
   - ressorts nodaux par classe ;
   - liaison tête de pieu-poutre sans redondance ;
   - pression par couche et normales ;
   - demi-section en plan de symétrie ;
   - charge d'empreinte sur surface développée ;
   - poids d'une poutre liée par forces nodales ;
   - plaque orthotrope `ELAS_COQUE` avec lecture des efforts généralisés ;
   - script Salomé en partition unique.

   Statut : `établi` au mieux. Aucun ne peut être `promu`, puisqu'un seul projet
   existe.
4. **Contrôles** : ceux du harnais, avec l'erreur réelle que chacun a attrapée.
5. **Références de validation** : les essais A à D7 des lots 22 à 25, l'essai
   `FORCE_COQUE` et les essais de ferraillage, rendus rejouables par une
   commande unique.
6. **Précédents** : les décisions de la fiche du quai, avec leur domaine de
   validité.
7. **Métriques de base du quai** :
   - 40 lots ;
   - 190 exécutions, dont 38 % en échec ;
   - 1,54 h de calcul.

   **Interventions du superviseur**, estimées par Claude : sur les lots 19 à
   41, environ 25 lots ont exigé une intervention de fond. Ce sont des
   corrections de diagnostic, de critère ou de décision : lots 21, 23, 28 à 34,
   36, 37, 39, entre autres. Le chiffre est déclaré comme une estimation, pas
   comme une mesure. À partir du lot 43, ces interventions seront comptées dans
   chaque compte rendu.
8. **Diagnostic ENV-001** (lot 41 bis, `docs/environnement.md`, § 4) : c'est le
   premier diagnostic d'environnement de la base.

## Étape 6 — Recherche documentaire

Les requêtes journalisées depuis le lot 8 qui n'ont pas trouvé de réponse utile,
parce qu'elles ont été suivies d'une lecture directe ou d'une autre requête,
alimentent le banc d'évaluation comme nouvelles questions candidates. Elles
sont marquées à valider par MM. C'est la boucle qui fera progresser les profils
théorie (66,7 %) et méthode (55,6 %).

## Étape 7 — Tâche d'essai Cloud

Écris dans `docs/cloud.md` le texte d'une courte tâche, que MM lancera sur la
branche `lot-42`. Elle doit :

1. appeler **directement** l'outil `search_connaissances` depuis la session, ce
   que le premier essai Cloud n'a pas fait ;
2. vérifier que `aster-expert rex` fonctionne aussi en profil `cloud`. Les
   archives d'exécution y étant absentes, la commande doit le signaler sans
   échouer ;
3. rapporter, sans rien modifier, et en français.

## Contrôles

```bash
aster-expert mcp-check
ruff format --check
ruff check
pytest tests/unit
pytest
pytest -m lent
mypy src
mypy
aster-expert rex quai_cw_test_01
```

## Compte rendu attendu — EN FRANÇAIS

1. Schémas des six couches et règles de promotion.
2. Outil MCP et règles de consultation du skill.
3. Commande `rex` et tableau de bord.
4. Amorçage : nombre d'entrées par couche et par statut, classement des 73
   échecs (répartition par cause).
5. Nouvelles questions candidates pour le banc.
6. Résultats des neuf commandes de contrôle.
7. Texte de la tâche d'essai Cloud de l'étape 7.

Consigne à MM : le lot modifie un outil MCP, il faut donc redémarrer la session
avant le lot suivant.

## Interdits

- Aucune promotion au statut `promu` à partir du seul quai.
- Aucun précédent appliqué automatiquement.
- Aucune entrée de connaissance sans preuve.
- Aucune modification du comportement du quai.
