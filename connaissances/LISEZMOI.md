# Base de connaissances de l'outil (lot 42)

Un agent ne modifie pas ses poids : ce qu'il apprend d'un projet est **écrit ici**,
sous une forme qu'il consulte avant d'agir (outil MCP `search_connaissances`,
skill `code-aster-expert`, § 6 quater) et que des tests protègent. Chaque projet
doit rendre l'outil meilleur : par ses erreurs (diagnostics), ses découvertes sur
Code_Aster (constats), ses recettes (patrons), ses contrôles, ses cas validés
(références) et les décisions de MM (précédents).

## Les six couches

| Répertoire | Identifiant | Contenu | Schéma |
| --- | --- | --- | --- |
| `constats_code_aster/` | `CA-nnn` (JSON) | comportement établi de Code_Aster, avec cas d'essai rejouable (lot 41) | `aster_expert.constats.models.Constat` |
| `diagnostics/` | `DIAG-nnn`, `ENV-nnn` | signature d'erreur ou d'alarme (genre, identifiants, motif), cause, correction, prévention | `aster_expert.connaissances.modeles.Diagnostic` |
| `patrons/` | `PAT-nnn` | recette de modélisation : problème, solution, fragment de `.comm` ou de script Salomé, conditions d'emploi, contrôles qui la vérifient, constats liés, code | `Pattern` |
| `controles/` | `CTL-nnn` | contrôle de vérification : ce qu'il détecte, paramètres, code, erreur réelle attrapée (`attrapée`, `a posteriori`, `aucune consignée`) | `Control` |
| `references_validation/` | `REF-nnn` | cas à solution connue, exécutable : grandeurs, valeur obtenue, référence, critère (`exact` à une tolérance, ou `raffinement`), résultat recalculé | `ValidationReference` |
| `precedents/` | `PRE-nnn` | décision pratique de MM avec justification, variantes écartées et domaine de validité | `Precedent` |

Tout fichier YAML porte : `id`, `title`, `summary` (une phrase), `origin_project`,
`date`, `validation_level` (A à E), `status`, `sources` (au moins une),
`commands` et `keywords` Code_Aster (casse officielle), `reuses`,
`status_history`. Les sources sont typées : `execution` (exécution archivée
`run`, et/ou cas versionné `case_path` + `case_sha256`, issue `échec` ou
`réussite` avec son niveau), `test` (fichier et fonction), `code` (fichier et
symbole), `document`, `constat`, `decision` (point d'une fiche).

Règles vérifiées au chargement (`aster-expert connaissances verifier`) :

- aucune entrée sans preuve ; le nom du fichier est l'identifiant ;
- le niveau déclaré ne dépasse pas celui des preuves (document, décision ou
  échec : A ; code ou test : B ; exécution réussie : son niveau C, D ou E ; constat :
  son niveau) ;
- toute référence (constat, contrôle) existe ;
- chaque preuve est confrontée au dépôt : cas présent avec son empreinte, test et
  symbole définis, document présent, exécution archivée présente (archives
  absentes dans le Cloud : signalé, pas vérifié).

## Statuts et promotion

1. **`observé`** : vu dans un projet, avec sa preuve.
2. **`établi`** : preuve rejouable — cas d'essai versionné (chemin et empreinte)
   ou test versionné. Pour un constat, dérivé : établi par exécution d'un cas
   versionné (niveau C ou D).
3. **`promu`** : **éprouvé** dans au moins **deux projets**, ou validé au niveau E.
   Depuis le lot 44, une réutilisation (`reuses`) ne compte que si sa preuve est une
   épreuve : une exécution réussie dont le résultat vérifie l'entrée, ou un test
   versionné qui l'applique et passe. Une citation dans une fiche, une décision, un
   document ou du code ne compte pas (au lot 43, CA-025 et CA-041 étaient éligibles
   par simple citation). Les épreuves d'un constat sont dans
   `epreuves_constats.yaml` ; `aster-expert connaissances eligibilite` rejoue la règle
   sur toute la base. Un patron promu peut devenir une fonction du tronc
   commun, avec ses tests ; un contrôle promu entre dans le harnais par défaut
   (`default_harness`, refusé à un contrôle non promu).

La promotion est explicite : `aster-expert connaissances promouvoir <id> --motif
"…"`. Elle vérifie les conditions, échoue sinon, réécrit le statut avec son
événement et l'inscrit dans `promotions.yaml`. Aucune promotion n'est
automatique ; un statut `promu` écrit à la main est refusé au chargement.

**Précédents.** Un précédent n'est jamais appliqué à un autre projet. Il se
propose (`aster-expert connaissances proposer-precedent <PRE-nnn> --point <p>`) :
une entrée pratique **non tranchée** (donc bloqueur de génération) et la source
d'origine `precedent_projet` que MM peut citer s'il le retient
(`record_practice_decision`). C'est le jugement d'ingénieur qui se capitalise, pas
une règle qui s'y substitue.

## Consultation

- `search_connaissances` (MCP) et `aster-expert connaissances chercher` : texte,
  commande, mot-clé, couche, statut ; niveau A.
- `aster-expert run` : en cas d'échec, le compte rendu d'exécution cherche la
  signature dans `diagnostics/` et affiche les entrées correspondantes.
- `aster-expert connaissances rejouer-references` : rejoue dans le conteneur les
  cas des références de validation et vérifie que chaque valeur est encore
  imprimée.

## Anomalies ouvertes (lot 44)

`anomalies_ouvertes.yaml` relie, sous un identifiant ANO-nnn, plusieurs entrées qui
portent peut-être une même cause inexpliquée, avec la signature de chacune, sans
rien conclure (ANO-001 : CA-052 et REF-012, `CALC_FERRAILLAGE` à l'ELS contre le
pivot acier de R7.04.05). Chaque entrée citée doit exister (contrôlé au chargement) ;
`search_connaissances` signale l'anomalie sur les entrées concernées.

## Retour d'expérience et métriques

`aster-expert rex <projet>` (registre `rex/<projet>.yaml`) liste les exécutions
échouées du projet avec leur signature et les diagnostics qui leur
correspondent, refuse la clôture tant qu'un échec n'est pas classé (rattaché,
nouveau diagnostic, ou écarté avec un motif), propose les constats d'une fiche
encore copiés, signale les fonctions du projet proches d'un patron, et écrit
`metriques/<projet>.yaml` et `metriques/tableau_de_bord.md` (la « fonction de
perte » de l'outil : taux d'échec, interventions du superviseur, lots par
ouvrage). Les chiffres déclarés portent leur nature (`mesure`, `estimation`,
`non renseigné`). **Tout lot se termine par `aster-expert rex`** (CLAUDE.md).

Depuis le lot 44, les exécutions se séparent en **développement** et
**vérification** (commande de rejeu, marquée par `ASTER_EXPERT_RUN_ORIGIN` dans le
compte rendu, ou rejeu d'un `.comm` déjà réussi, même empreinte) : le taux d'échec
porte sur le développement seul, les deux nombres sont affichés. Les candidats
patrons ne sont listés qu'à partir d'une similarité de 0,40
(`PATTERN_SIMILARITY_THRESHOLD`, calibrée sur les implémentations citées par la
base).

## Amorçage (lot 42)

Le quai (`projets/quai_cw_test_01`) a versé 76 entrées (25 diagnostics dont
ENV-001, 9 patrons, 11 contrôles, 13 références, 18 précédents), construites par
`quai_cw_test_01.capitalisation` et écrites par
`projets/quai_cw_test_01/scripts/amorcer_connaissances_lot42.py` ; un test les
reconstruit octet pour octet. Aucune n'est promue : un seul projet existe.
