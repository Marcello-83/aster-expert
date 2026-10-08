# Essais du lot 49 — livrables de résultats (MED, charges appliquées, ParaView, Excel, interrogation)

Consigne : `docs/lots/lot49_consigne.md`. Profil **vm**. Code_Aster 17.4.0, image
`simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
Ce rapport suit `docs/modele_rapport_essai.md` : les sections 1 à 3 (objet, méthode,
critères) sont écrites et commitées **avant** les exécutions de post-traitement du quai et
de l'estacade et avant l'essai de mutation ; elles ne sont pas modifiées ensuite (une
erreur s'y corrige dans une section datée « Correction du critère »).

Deux exécutions ont précédé ce commit et sont déclarées comme telles : la campagne de
mesures des fils (étape 0, en cours au moment du commit, critère de choix écrit au § 3.1
avant toute lecture de ses résultats agrégés) et l'exécution de **développement** du
post-traitement de la dalle (`20261008T080443-426fc374`, 45 s), qui a servi à mettre au
point la chaîne ; elle sera rejouée après ce commit et c'est le rejeu qui compte.

## 1. Objet

1. Ressources (étape 0) : mesurer de nouveau l'effet du nombre de fils OpenMP (1, 4, 8,
   12, 14), trois répétitions par point, sur deux tailles (dalle de 0,25 m de l'estacade,
   cas N3 ; maillage de production de l'estacade), avec la part de la factorisation
   numérique ; en tirer la règle par défaut ; refuser `PARALLELISME_TEMPS='OUI'`
   (DIAG-027).
2. Livrables (étapes 1 à 7) : pour chaque projet, un MED des résultats (cas élémentaires,
   combinaisons, enveloppes), un MED des charges appliquées, leur conversion VTU, deux
   scripts ParaView générés et leurs images, un classeur Excel tiré du paquet, et
   l'interrogation des résultats (`aster-expert resultats lire`, outil MCP
   `query_results`).
3. Niveaux visés : aucun niveau nouveau. Les niveaux B à E des trois projets doivent être
   **conservés** (règle du lot 45) : le `.comm` de production n'est pas modifié.

## 2. Méthode (écrite avant les exécutions des livrables du quai et de l'estacade)

### 2.1 Exécution de post-traitement

**Établi dans la documentation 17.4 (niveau A).**

- Relecture d'un résultat archivé : la base des exécutions de production n'est pas
  archivée (pas de `glob.*` dans les répertoires d'exécution) ; `POURSUITE` est donc
  impossible. Le MED de production (`fort.80`, quai et estacade) ne porte ni les forces
  des ressorts ni les charges ; la dalle n'en écrit aucun. Les réactions d'un résultat
  `mult_elas` relu exigeraient les charges de chaque cas (`EXCIT`), qu'un MED ne porte pas.
- Méthode retenue : **une copie du `.comm` de production**, texte inchangé, dans laquelle
  des blocs de sorties sont **insérés** (`aster_expert.livrables.postcomm`) : avant le
  `DETRUIRE` de chaque résultat (ou avant `FIN`), les champs déclarés que la production
  n'a pas calculés (`CALC_CHAMP(reuse=…)`), un `IMPR_RESU` vers un MED de travail
  (`NOM_RESU_MED`, 8 caractères au plus : U7.05.21 « Opérande NOM_RESU_MED »), un
  `IMPR_RESU` des cas élémentaires vers le MED livrable avec un nom de champ explicite
  `CAS_<cas>__<champ>` (`NOM_CHAM_MED`, « chaîne de 64 caractères », U7.05.21
  « Opérande NOM_CHAM_MED » ; mots-clés confirmés au catalogue 17.4 sous
  `FORMAT='MED'` : `NOM_CHAM_MED`, `NOM_RESU_MED`, `NUME_ORDRE`, `GROUP_MA`, `GROUP_NO`,
  `CARA_ELEM`, `TYPE_NOM`), et les charges (§ 2.2). La copie n'est acceptée que si
  **toutes** ses tables `IMPR_TABLE(FORMAT_R='E20.12')` égalent celles de l'exécution de
  production archivée, valeur par valeur (`aster_expert.livrables.chaine.compare_tables`).
- Le `.comm` de post-traitement doit obtenir le verdict B `valide`.
- Combinaisons et enveloppes : calculées dans le conteneur Code_Aster (numpy et
  `medcoupling` 9.14), sur les tableaux bruts des champs écrits par Code_Aster
  (`getUndergroundDataArray`), et ajoutées au MED livrable par copie d'un champ de cas
  élémentaire (mêmes supports, profils et ordre des valeurs). Une combinaison qui porte
  une charge mobile est l'enveloppe (max, min) sur ses positions, avec la position qui
  gouverne ; l'enveloppe des combinaisons garde la combinaison et la position qui
  gouvernent (`aster_expert.livrables.calcul`).

### 2.2 Charges appliquées

**Établi dans la documentation 17.4 (niveau A).** `CALC_VECT_ELEM` (U4.61.02) :
`OPTION='CHAR_MECA'`, `CHARGE` = les charges du cas qui portent un chargement (les
charges cinématiques sont écartées), `CHAM_MATER` « nécessaire en mécanique pour les
chargements de pesanteur », `CARA_ELEM` pour les éléments de structure ; `MODELE` n'est
pas donné avec `CHAR_MECA` (le catalogue 17.4 exige alors `SOUS_STRUC`). Assemblage par
`ASSE_VECTEUR` (U4.61.23, catalogue : `VECT_ELEM`, `NUME_DDL`) sur `NUME_DDL(MODELE=…)`.
Écriture `FN_<cas>`. Un cas dont le champ de matériau porte une variable de commande
(température) reçoit ses forces nodales équivalentes (`OPTION='FORC_VARC'`, `FV_<cas>`)
et ses champs de température (`VARC_<cas>_TEMP_<k>`) : une charge thermique se représente
par son champ propre.

### 2.3 Interrogation

`aster-expert resultats lire` et l'outil MCP `query_results` lisent les tableaux des
livrables (`resultats/livrables/donnees/`), écrits par le conteneur à partir des MED.

## 3. Critères de réussite (écrits avant l'exécution)

### 3.1 Étape 0 — règle des fils

Critère de choix (écrit pendant la campagne, avant la lecture de ses résultats agrégés) :

| Grandeur | Règle |
| --- | --- |
| Temps d'un point | médiane des trois répétitions (durée du compte rendu, conteneur compris) |
| Fils utiles (`execution.useful_threads_max`) | plus petit nombre de fils dont la médiane est à moins de 10 % de la meilleure médiane, **sur les deux tailles** (le plus grand des deux) ; à défaut de gain de plus de 10 % sur une taille, 1 |
| Résultats | une configuration n'est retenue que si toutes ses tables sont identiques à celles de la première exécution à un fil de sa taille ; sinon elle est écartée et l'écart rapporté |
| Règle par défaut | fils = min(fils utiles, processeurs ÷ exécutions simultanées), au moins 1 ; MPI à 1 |

### 3.2 Post-traitement (par projet)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Verdict B du `.comm` de post-traitement | `valide` | exacte | toutes les commandes confrontées, 0 erreur |
| Tables `E20.12` du post-traitement | égales à celles de la production | exacte | toutes identiques (égalité des nombres lus) |
| `.comm` de production | inchangé | exacte | même SHA-256 avant et après le lot |
| Niveaux du paquet | ceux d'avant le lot (quai D, dalle E, estacade D) | exacte | identiques |

### 3.3 Charges (CTL-013 sur le MED des charges)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Σ des forces nodales de `FN_<cas>` (FX, FY, FZ) | résultante déclarée du cas (`controls.cases`, telle qu'évaluée) | exacte | écart rapporté à la plus grande composante ≤ seuil du projet (10⁻⁶) ; un cas `informative` est rapporté sans verdict |
| Σ des forces `FV_<cas>` d'un cas thermique | 0 | exacte | rapporté (autoéquilibre), sans verdict |

### 3.4 Essai de mutation (dalle)

Copie du `.comm` de post-traitement de la dalle où `CH_Q` (−10 kN/m² sur `DALLE`) est
appliquée sur `CENTRE_V` au lieu de `DALLE`.

| Grandeur | Attendu | Seuil |
| --- | --- | --- |
| CTL-013 sur `FN_Q` non muté | RÉUSSI | ≤ 10⁻⁶ |
| CTL-013 sur `FN_Q` muté | ÉCHEC | écart > 10⁻⁶ |
| Point d'application de ΣFZ de `FN_Q` muté | au centre de `CENTRE_V`, distinct de la répartition d'origine | rapporté |
| Image des charges mutées | flèches sur `CENTRE_V` seulement | constat visuel rapporté |

### 3.5 VTU et classeur

| Grandeur | Attendu | Seuil |
| --- | --- | --- |
| Chaque tableau relu d'un `.vtu` | égal à sa source | bit pour bit (NaN = NaN) |
| Valeur d'une cellule du classeur | valeur source × facteur d'affichage | égalité exacte (test de relecture) |
| Police, couleur, en-têtes | Arial 10, noir, en-têtes sur fond gris D9D9D9 | aucune exception |

### 3.6 Rejeu de l'export du lot 47

Les cinq CSV de `/media/sf_partage/echanges/lot47` relus ligne par ligne par
`aster_expert.livrables.lecture.query` : chaque valeur d'une colonne de résultat égale la
valeur de l'export à son nombre de décimales (« à l'identique aux arrondis près ») ; les
colonnes dérivées (modules, intégrales de dalle, sommes affichées) sont listées et non
comparées ; le `.comm` est comparé par son SHA-256 ; les deux documents Markdown ne sont
pas des exports de valeurs.

## 4. Résultats

(Rédigés après les exécutions.)
