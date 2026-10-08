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

(Rédigés après les exécutions ; les sections 1 à 3 ne sont pas modifiées.)

### 4.1 Étape 0 — fils d'exécution (3 répétitions par point)

Script : `projets/estacade_pieux_01/scripts/performances_lot49.py` ; résultats :
`projets/estacade_pieux_01/resultats/lot49/perf/mesures.json` (non versionné). Durée =
durée du compte rendu (conteneur compris). `DEBUT(MESURE_TEMPS=_F(NIVE_DETAIL=2))`
(U4.11.01) sépare la factorisation numérique (#1.3) de la résolution (#1.4). « prod » est
le `.comm` de production de l'estacade (E13, maillage de 0,05 m) **coupé après son premier
lot** de `MACRO_ELAS_MULT` (25 cas, une factorisation) : même maillage, même matrice,
1/13 des factorisations (déclaré, § 1 du script). Les 30 exécutions ont abouti et toutes
leurs tables sont identiques à la première exécution à un fil de leur taille.

| Taille | Fils | Durées (s) | Médiane (s) | t01/tN | Factorisation num. (s, médiane) | Part |
| --- | --- | --- | --- | --- | --- | --- |
| N3 (0,25 m) | 1 | 194,0 ; 180,3 ; 171,0 | 180,3 | 1,00 | 1,5 | 0,9 % |
| N3 | 4 | 192,0 ; 164,0 ; 128,6 | 164,0 | 1,10 | 1,1 | 0,8 % |
| N3 | 8 | 269,5 ; 248,2 ; 163,3 | 248,2 | 0,73 | 6,2 | 2,6 % |
| N3 | 12 | 516,5 ; 301,5 ; 281,2 | 301,5 | 0,60 | 10,9 | 3,7 % |
| N3 | 14 | 657,9 ; 272,7 ; 327,7 | 327,7 | 0,55 | 26,1 | 9,8 % |
| prod (0,05 m) | 1 | 363,2 ; 413,8 ; 366,2 | 366,2 | 1,00 | 9,4 | 2,7 % |
| prod | 4 | 338,0 ; 206,4 ; 273,1 | 273,1 | 1,34 | 3,5 | 1,3 % |
| prod | 8 | 452,4 ; 304,6 ; 300,6 | 304,6 | 1,20 | 6,2 | 2,1 % |
| prod | 12 | 845,7 ; 410,4 ; 389,2 | 410,4 | 0,89 | 11,3 | 2,8 % |
| prod | 14 | 1192,8 ; 514,2 ; 487,1 | 514,2 | 0,71 | 18,4 | 3,3 % |

Faits :

- La dispersion est forte (jusqu'à un facteur 2,3 sur un même point) ; la première
  répétition (07:10 à 08:35 UTC) a été la plus lente aux grands nombres de fils : la
  session travaillait alors en parallèle (validations B, une exécution de développement de
  la dalle à 08:04 UTC). Les deuxième et troisième répétitions ont été faites sans autre
  calcul. La médiane retient la valeur centrale.
- **La factorisation numérique ne pèse que 1 à 10 % du temps** : les « 52 % » du lot 47
  quater étaient le temps total de `MACRO_ELAS_MULT`. Ce qui varie avec le nombre de fils
  est la **résolution** (#1.4, descente-remontée de chaque cas : prod 117,8 à 135,0 s à un
  fil, 81,6 à 148,5 s à 4 fils, 315,6 à 1 012,7 s à 14 fils) ; les calculs élémentaires
  (#2) ne bougent presque pas (31 à 60 s).
- Gain réel seulement sur le grand problème et à 4 fils (1,34) ; au-delà, la synchronisation
  l'emporte (0,71 à 14 fils). Déduction : OpenBLAS monofil de l'image (lot 47 quater), seule
  la partie parallèle de MUMPS travaille.

Règle (§ 3.1) : N3 → 1 fil (t01 à 9,9 % de la meilleure médiane, t04) ; prod → 4 fils
(t04 est la meilleure, t08 à 11,5 %) ; **fils utiles = 4** (`execution.useful_threads_max:
4`, `config/validation.yaml` et `config/machine.local.yaml`). Règle par défaut :
fils = min(4, 14 ÷ exécutions simultanées) — une exécution seule ou jusqu'à trois en
parallèle reçoivent 4 fils, sept en reçoivent 2 (`aster_expert.execution.regle_fils`,
option `--simultanees`). MPI reste à 1. `PARALLELISME_TEMPS='OUI'` est refusé avant
toute exécution, avec DIAG-027 dans le message (`execution.forbidden_keywords`, test
`tests/unit/test_execution_interdits.py`).

### 4.2 Étape 0 bis — reprises du lot 48 bis

- `env-check` (profil vm) et `mcp-check` (serveur neuf, 9 outils puis 10 avec
  `query_results`) réussis en début de lot ; la session a démarré sur la branche `main`
  après la fusion du lot 48 bis.
- **Paquets réexportés avec le harnais D**, dépôt complet (non tronqué), sans exécution
  nouvelle : `projet <nom> controles` relit le `.mess` archivé, puis `exporter-resultats`.
  Antériorité des critères : identique à celle des paquets précédents (dalle : aucun
  critère changé ; quai : `essais_lot34`, `lot37`, `lot39` déjà « antériorité non
  démontrable », inchangés) ; aucun écart à rapporter.
- **Quai** : `fiche prevoir --ecrire` (22 commandes prévues), exemption levée,
  `build_combiwall_reference.py` reprend les commandes prévues (test octet pour octet
  vert). `maillage` : MED du cache, vérifié par `mesh check` (599/599 invariants), Salomé
  non relancé (comportement normal de l'étape, lot 28) ; `generer` puis `valider` : niveau
  B `valide`, 265/265. Le `.comm` régénéré est **identique au `.comm` de référence hors
  commentaires** ; la seule ligne différente est l'en-tête « Fiche : sha256 », que
  `planned_commands` change. Écart déclaré : le niveau C du paquet exigeait jusqu'ici
  l'égalité octet pour octet et retombait (quai : D → B) ; la règle de conservation du
  lot 45 (« identique hors commentaires et en-tête ») est désormais appliquée aussi au
  niveau C, et le motif le dit (`aster_expert.projet.paquet`, test
  `tests/unit/test_lot49_regles.py`). Le quai reste au niveau D.
- `fiche obligatoires` : code 0 sur la dalle et l'estacade. Les cinq mots-clés de lecture
  et de codage de champ sont classés « sans question » dans `obligations_execution.yaml`
  avec leurs sources (U4.81.21, U4.72.04, U4.44.12) ; `DEFI_CONSTANTE/VALE`, qui porte un
  nombre (coefficients des combinaisons de la dalle), n'y entre pas : il est couvert par
  le point 13 de la fiche (`fiche prevoir --couvrir`). Sur le quai, il reste
  `DEFI_FONCTION/NOM_PARA` (variable des fonctions de pression, code 1) : non couvert par la
  session, signalé à MM.
- Aucun maillage modifié.

### 4.3 Livrables des trois projets

| Projet | `.comm` de post-traitement (B) | Exécution | Durée | Tables identiques | MED résultats / charges | VTU | Images |
| --- | --- | --- | --- | --- | --- | --- | --- |
| dalle | `valide`, 120/120 | `20261008T115345-0ec1336b` | 18 s | 82 134 / 82 134 | 2,5 / 0,3 Mo | 3,2 Mo (10) | 22 |
| quai | `valide`, 314/314 | `20261008T122524-241fe6cd` | 222 s | 9 931 632 / 9 931 632 | 364,3 / 18,7 Mo | 400,2 Mo (22) | 110 |
| estacade | `valide`, 478/478 | `20261008T115348-9d3191e5` | 1 719 s | 135 668 / 135 668 | 1 163,8 / 40,7 Mo | 1 224,4 Mo (16) | 88 |

Exécutions lancées en parallèle, 4 fils chacune (règle du § 4.1). Échecs de mise au point,
tous classés (`rex`) : quai `20261008T120445-3c2f0250` (`UTILITAI_4`, `EFGE_NOEU` sur les
facettes des tubes, DIAG-011 : contrat corrigé, `EFGE_ELNO` sur `TUBES`) et
`20261008T121847-521dfdf5` (`MED2_13` aggravée en erreur par le quai : nouveau DIAG-028,
`CARA_ELEM` retiré pour les ressorts). L'exécution de l'estacade, générée avant cette
correction, porte 59 alarmes `MED2_13` (CARA_ELEM ignoré, sans effet sur les valeurs) et
11 `CATAMESS_41` (affichage plafonné) ; elle n'est pas rejouée.

Contrôles :

- **CTL-013 sur le MED des charges** : réussi sur tous les cas déclarés (dalle G, Q : écart
  0 ; quai G, Q1, EAU_P, EAU_A : ≤ 7·10⁻¹⁴, Q3 et A informatifs ; estacade PP, G2, UDL, TR,
  FR : ≤ 1,3·10⁻¹²) ; forces des cas thermiques TE± : somme nulle à 3·10⁻¹⁶ de Σ|F|.
- **Bilan lu dans les livrables** (charges + réactions livrées + forces des ressorts) : nul
  à mieux que 10⁻⁵ N dans les trois projets ; le signe des ressorts est confirmé (estacade
  FR : charge +381 000 N, ressorts −381 000 N).
- **Combinaisons** : sur la dalle, les combinaisons calculées dans le conteneur égalent
  celles que Code_Aster calcule lui-même (RC01, RC02, tables `EFN_C_RC0x`) à 12 chiffres
  significatifs (MXX = −17 112,961 937 N·m/m, MYY = −31 516,398 429 N·m/m).
- **VTU** : chaque fichier relu est identique à sa source, tableau par tableau (NaN = NaN).
- **Classeurs** : 8 feuilles par projet, construits depuis le paquet ; test de relecture
  vert. **Notes Word** régénérées avec les unités de colonnes : contrôle sans problème sur
  les trois projets, après prise en compte de la précision absolue d'un affichage en
  décimales fixes (`aster_expert.notes.controle._tolerates`, test).

Ouverture sous Windows : le greffon `MEDReader` est livré avec les binaires officiels de
ParaView à partir de 5.12 (source secondaire : forum ParaView et dépôt Kitware, non vérifié
sur le poste de MM) ; les VTU sont donc fournis en plus et les scripts les lisent.
Rendu sans écran établi dans la VM : ParaView 5.11 de l'image Salomé-Méca ; `pvbatch` bloque
à l'initialisation MPI sans `--no-mpi` ; `--force-offscreen-rendering` s'arrête (SIGABRT,
pas d'EGL ni d'OSMesa) ; `xvfb-run -a pvbatch --no-mpi` fonctionne.

Dépôt : `/media/sf_partage/echanges/lot49/<projet>/` (classeur, manifeste, MED, VTU, deux
scripts, images ; aucun fichier ne dépasse 2 Go), notice `LISEZMOI.txt`.

### 4.4 Essai de mutation (dalle)

Script : `projets/dalle_appuyee_01/scripts/mutation_charges_lot49.py`. Première tentative
(`20261008T120432-98b0df80`) : `<F> MODELISA6_96`, `CENTRE_V` contenant aussi des
segments hors du modèle ; diagnostic DIAG-017 retrouvé par `aster-expert run` ; la
mutation porte alors sur `CENTRE_V ∩ DALLE` (`DEFI_GROUP/CREA_GROUP_MA/INTERSEC`,
catalogue 17.4, déjà employé par PAT-012) ; `.comm` muté au niveau B `valide`, exécution
`20261008T120540-22c17443` réussie.

| Grandeur | Obtenu | Verdict |
| --- | --- | --- |
| ΣFZ de `FN_Q` non muté | −240 000,0 N (attendu −240 000 N) | RÉUSSI (écart 0) |
| ΣFZ de `FN_Q` muté | −625,0 N | **ÉCHEC** (écart 0,997) |
| Point d'application | (3,0 ; 2,0) dans les deux cas | rapporté : `CENTRE_V` est centré sur le centre de la dalle ; c'est la répartition qui change, pas le point |
| Image | flèches sur les quatre mailles du centre seulement (`livrables_mutation/png/charges_FN_Q.png`), contre toute la dalle à l'origine | constat visuel conforme |

Verdict : le contrôle échoue sur la charge déplacée et réussit sur l'originale ; le MED et
l'image montrent le déplacement. Limite : un déplacement qui conserverait l'aire chargée
ne changerait pas la résultante ; seul le moment (point d'application, rapporté) et l'image
le montreraient.

### 4.5 Rejeu de l'export du lot 47

Script : `projets/estacade_pieux_01/scripts/rejeu_export_lot47.py`, résultat
`resultats/livrables/rejeu_export_lot47.json` (non versionné). Chaque ligne est redemandée
à `aster_expert.livrables.lecture.query` (le code de `aster-expert resultats lire`).

| Fichier | Lignes rejouées | Valeurs comparées | Différences |
| --- | --- | --- | --- |
| `tetes_de_pieux.csv` | 196 | 1 176 | 0 |
| `profils_pieux.csv` | 1 920 | 12 540 | 0 |
| `chevetres.csv` | 3 600 | 21 600 | 0 |
| `dalle_coupes.csv` | 5 000 | 20 000 | 0 |
| `resultantes_cas_elementaires.csv` | 84 | 252 | 0 |
| `comm_production.comm` | — | empreinte | identique |

Colonnes non comparées, parce que dérivées : modules √(MFY² + MFZ²) et √(VY² + VZ²),
intégrales de la dalle sur la bande de 1,20 m et moment de travée signé (`chevetres.csv`),
lignes « total » et « bilan » des résultantes, charge appliquée des positions mobiles
(aucun MED de charges n'est écrit pour les positions). `ecarts_C1_C13.md` et
`modele_resume.md` sont des documents de relecture, pas des exports de valeurs. Verdict
(§ 3.6) : **réussi** sur toutes les colonnes de résultat.

### 4.6 Conservation des niveaux

| Projet | Niveau avant | Niveau après | `.comm` de production |
| --- | --- | --- | --- |
| dalle | E | E | inchangé (`70ae851c…`) |
| quai | D | D | identique hors commentaires (en-tête) ; règle de conservation appliquée au niveau C |
| estacade | D | D | inchangé (`fe73819a…`) |

Aucun cas de référence (`projets/*/references/cas`) modifié.

## 5. Verdicts

| Critère | Verdict |
| --- | --- |
| § 3.1 règle des fils | appliquée : fils utiles = 4 |
| § 3.2 post-traitement (B valide, tables identiques, `.comm` inchangé, niveaux) | réussi sur les trois projets (quai : `.comm` égal hors en-tête, déclaré) |
| § 3.3 CTL-013 sur le MED des charges | réussi |
| § 3.4 mutation | réussi (échec du contrôle muté) ; point d'application inchangé, rapporté |
| § 3.5 VTU et classeur | réussi |
| § 3.6 rejeu de l'export du lot 47 | réussi (0 différence sur 55 568 valeurs) |

## 6. Limites

- Mesures des fils sur une seule machine, avec une dispersion forte ; la taille
  « production » est le `.comm` de production coupé après son premier lot.
- Un déplacement de charge qui conserve l'aire chargée ne change pas la résultante :
  CTL-013 ne le voit pas ; le point d'application (rapporté) et les images le montrent.
- Lecture directe du MED sous Windows non vérifiée ; scripts ParaView écrits pour ParaView
  ≥ 5.10 (noms de tableaux entre guillemets dans les `Calculator`), exécutés en 5.11.
- Taille des VTU de l'estacade (1,2 Go, dont les combinaisons : 1,03 Go).
- `DEFI_FONCTION/NOM_PARA` reste sans question ni couverture sur le quai (à MM).
- L'exécution de post-traitement de l'estacade porte les alarmes `MED2_13` (DIAG-028),
  corrigées dans le générateur après coup, sans rejeu.
