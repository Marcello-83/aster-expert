# Essais du lot 47 quater — estacade : clôture (performances de calcul, fidélité au modèle source)

**Contre-calcul d'un modèle non validé** (lots 47 à 47 ter) : aucune ligne n'est un
niveau E. La référence (E1 à E19) n'est pas modifiée ; Q1 à Q4 sont des **variantes
déclarées**. Consigne : `docs/lots/lot47quater_consigne.md`. Version de Code_Aster :
17.4.0, image `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

Ce rapport suit `docs/modele_rapport_essai.md`. Les sections 1 à 4 sont écrites et
commitées **avant** toute exécution de Q1 à Q4 ; elles ne sont pas modifiées ensuite
(une erreur s'y corrige dans une section datée « Correction du critère »). La règle de
choix des valeurs par défaut (§ 1.6) est écrite pendant la série de mesures, après
lecture des durées de `t01`, `t04` et `t08` seulement (dit tel quel).

## 1. Étape 0 — Performances de calcul

### 1.1 État des lieux (relevé en début de lot)

- `env-check` : profil **vm** ; `nproc` = **14** ; `free -g` : **20 Go** de mémoire
  (15 libres, 19 disponibles), 3 Go d'échange ; 273 Go libres sur 390 Go de disque.
  Processeur vu dans le conteneur : Intel Core Ultra 7 265HX.
- **Limites passées à `docker run` avant ce lot** : `--cpus=1` (`config/validation.yaml`,
  `execution.cpus_limit: "1"`, lot 11), `--memory=8192m` et délai de 1 800 s
  (`execution.memory_mb`, `execution.timeout_seconds`), sauf `--timeout` et `--memory-mb`
  en ligne de commande. **Les paramètres de l'`.export` n'étaient pas lus** (DIAG-025).
- **`.export` réellement transmis** (N1, `data/processed/runs/20261006T134632-58937400`) :
  `P time_limit 7200`, `P memory_limit 10240`, `P ncpus 1`, `P mpi_nbcpu 1`,
  `P mpi_nbnoeud 1` ; commande `run_comm.py … --time-limit 7200 --memory-limit 10240`
  (donnée en ligne de commande à cette exécution) ; `run_aster_main` place ces deux
  valeurs dans l'`.export` (`export.set_time_limit`, `export.set_memory_limit`).
- **Image : construction parallèle MPI, vérifiée dans le conteneur** (sondes de ce lot,
  sans réseau) :
  - `share/aster/config.json` de l'installation : `"parallel": 1`,
    `"mpiexec": "mpiexec -n {mpi_nbcpu} --tag-output {program}"`, `"require_mpiexec": 0`,
    `"only-proc0": 0`, `"addmem": "2800"`, compilateur `openmpi-5.0.8/bin/mpif90` ;
  - bibliothèques liées à `libaster.so`, `aster.so`, `libbibfor_ext.so` : `libmpi.so.40`
    (OpenMPI 5.0.8, `MPI_THREAD_MULTIPLE: yes`), `libptscotch`, `libparmetis`,
    `libscalapack`, `libpetsc.so.3.24`, MUMPS (`libsmumps`, `libzmumps`,
    `libmumps_common`), `libgomp.so.1` (OpenMP) ; **`libopenblas.so.0` construite
    `SINGLE_THREADED`** (chaîne `OpenBLAS 0.3.30 DYNAMIC_ARCH NO_AFFINITY USE_LOC
    SINGLE_THREADED`) ;
  - `mpiexec` existe (`/opt/spack/var/spack/environments/simvia_env/.spack-env/view/bin/
    mpiexec`, lien vers OpenMPI 5.0.8) mais **n'était pas dans le `PATH`** préparé par
    `aster_expert.execution.container_env` : `run_aster`, qui se relance sous `mpiexec`
    dès que `mpi_nbcpu` > 1, aurait échoué (« mpiexec: command not found ») ;
  - le listing de N1 se termine par « Code_Aster MPI exits normally », et `run_aster`
    écrit le listing sous `proc.0/` même pour un seul processus (lot 11) ;
  - **cas test parallèle de la version** : `petsc02f.comm` (`search_test_cases`, commande
    `LIRE_MAILLAGE`, mot-clé `PARTITIONNEUR` : 18 fichiers ; corpus au commit
    `50ebc13c70ee9df62faf93ddcb746a3757b3042a`) lit son maillage avec
    `PARTITIONNEUR="PTSCOTCH"` et résout par PETSc avec `MATR_DISTRIBUEE="OUI"`.

### 1.2 Profil d'une exécution de production

Lecture du tableau `COMMAND : USER : SYSTEM : USER+SYS : ELAPSED` du listing
(`aster_expert.execution.profil`, lacune de `run_aster.status` documentée dans le module,
qui ne lit que `TOTAL_JOB`). N1 (DST, chevêtre 0,80, 299 positions, maillage 0,05 m,
un processus, un fil) : `TOTAL_JOB` 3 114,3 s écoulées, 2 771,0 s CPU ; somme des lignes
3 113,4 s.

| Groupe | Commandes (occurrences) | Temps écoulé | Part |
| --- | --- | --- | --- |
| lecture du maillage | `LIRE_MAILLAGE` (1) | 0,4 s | 0,0 % |
| assemblage et factorisation | `MACRO_ELAS_MULT` (13 lots) | 1 614,0 s | 51,8 % |
| `CALC_CHAMP` | 45 (`EFGE_NOEU` dalle, `EFGE_ELNO` barres, `REAC_NODA`) | 1 305,9 s | 41,9 % |
| `IMPR_RESU` | 15 | 44,7 s | 1,4 % |
| reste | dont `DEFI_GROUP` 83,5 s, `MECA_STATIQUE` 31,6 s, `AFFE_CHAR_MECA` (305) 18,5 s | 149,0 s | 4,8 % |

Pic mémoire (VmPeak) : 4 325 Mo pour N1 ; 934 Mo pour N3 (dalle 0,25 m).

### 1.3 Documentation du parallélisme (17.4.0, niveau A)

Recherches : `search_codeaster_docs`, profil `methode` (choix d'un mode d'exécution) puis
`syntaxe` (paramètres de l'`.export`), sections lues en entier par
`get_document_section` ; mots-clés confirmés par `get_command_schema`.

- **U2.08.06** (« Notice d'utilisation du parallélisme »), § « Le parallélisme en
  quelques clics ! / Comment ? » et « En pratique via Astk » : le calcul est séquentiel
  par défaut ; pour un calcul dominé par des résolutions linéaires, METHODE 'MUMPS' ou
  'PETSC', puis distribution sur les processus MPI des étapes de construction et de
  résolution ; « on peut rajouter un deuxième niveau de parallélisme en utilisant, pour
  chaque processus MPI, plusieurs threads OpenMP […] Ce second niveau n'accélère […]
  qu'une partie de la résolution des systèmes linéaires et il ne permet pas de baisser
  le pic en mémoire RAM ». `ncpus` = fils OpenMP **par processus MPI** ; `mpi_nbcpu` =
  processus MPI au total ; `mpi_nbnoeud` = nœuds ; ne pas dépasser les cœurs physiques
  (`mpi_nbcpu` × `ncpus`) ; « la granularité de 1 processus MPI pour 30 ou 50 000 ddls
  est largement suffisante » ; « ne pas allouer tous les cœurs d'un nœud en MPI seul ».
  La mémoire d'Astk est donnée « pour chaque processus MPI » (figure 1.6).
- **U2.08.06**, « Distribution des calculs d'algèbre linéaire basiques / Mise en œuvre » :
  le parallélisme OpenMP (`ncpus` ≥ 2) « dépend du contexte informatique […] et des
  librairies d'algèbre linéaire utilisées. Sur la machine centralisée Aster, on utilise
  les BLAS threadées MKL ». *Déduction* : avec l'OpenBLAS monofil de l'image, le gain
  de `ncpus` est limité à ce que MUMPS et `libgomp` parallélisent eux-mêmes.
- **U2.08.06**, « Calculs élémentaires et assemblages / Mise en œuvre » : dès que
  plusieurs processus MPI sont actifs, `AFFE_MODELE` distribue les mailles
  (`DISTRIBUTION/METHODE`, défaut `SOUS_DOMAINE`, partitionneur `METIS` par défaut) ;
  `MATR_DISTRIBUEE` réduit le pic mémoire avec MUMPS ou PETSc ; `SOLVEUR/REDUCTION_MPI`
  réduit le nombre de processus de MUMPS.
- **U2.08.06**, « Package MUMPS / Mise en œuvre » : MUMPS est « le package HPC conseillé »,
  activé dès `mpi_nbcpu` ≥ 2, idéalement en mode distribué (défaut d'`AFFE_MODELE`).
- **U4.81.04** (`CALC_CHAMP`), § « Performance des calculs » : sous MPI, les options
  `REAC_NODA`, `FORC_NODA` et `xxx_NOEU` gagnent au **parallélisme en temps**,
  `PARALLELISME_TEMPS='OUI'` (accélérations « de X5 à X50 ») ; sans effet en séquentiel.
- **U4.21.01** (`LIRE_MAILLAGE`), « Opérandes pour le format 'MED' » : `PARTITIONNEUR`
  = `'SANS'` (défaut : « séquentiel et ancien parallélisme ») ou `'PTSCOTCH'` (maillage
  découpé en autant de sous-domaines que de processus MPI) ; « Attention, pour le
  moment, certaines mailles POI1 ne sont pas recopiées ».
- **U1.04.00** § « Fichier EXPORT » et **D1.02.05** : `ncpus`, `mpi_nbcpu`, `mpi_nbnoeud`,
  `memory_limit` (Mo), `time_limit` (s), un paramètre par ligne.
- **Catalogue 17.4.0** (`get_command_schema`) : `LIRE_MAILLAGE/PARTITIONNEUR` ∈ {`SANS`,
  `PTSCOTCH`} ; `AFFE_MODELE/DISTRIBUTION/METHODE` ∈ {`MAIL_CONTIGU`, `MAIL_DISPERSE`,
  `CENTRALISE`, `GROUP_ELEM`, `SOUS_DOMAINE`} (défaut `SOUS_DOMAINE`) ;
  `CALC_CHAMP/PARALLELISME_TEMPS` ∈ {`OUI`, `NON`} ; **le `SOLVEUR` de
  `MACRO_ELAS_MULT` ne porte ni `MATR_DISTRIBUEE` ni `REDUCTION_MPI`** (ses mots-clés :
  `METHODE`, `RENUM`, `STOP_SINGULIER`, `NPREC`, `TYPE_RESOL`, `PRETRAITEMENTS`,
  `PCENT_PIVOT`, `ELIM_LAGR`, `GESTION_MEMOIRE`, `ACCELERATION`, `LOW_RANK_SEUIL`,
  `RESI_RELA`, `POSTTRAITEMENTS`).
- **`run_aster` 17.4.0** (dépôt externe, tag 17.4.0) : `ncpus` fixe `OMP_NUM_THREADS`
  (`run.py`, `set_num_threads`) et `--numthreads` ; `mpi_nbcpu` > 1 fait relancer
  `run_aster` sous `mpiexec` (`run_aster_main.py`) ; délai du sous-processus
  `time_limit × 1,25 × ncpus` (`run.py`, `execute_study`) ; `run_sbatch` ajoute `addmem`
  à la mémoire réservée.

**Remarque de MM (« `mpi_nbcpu` dans l'`.export`, et des réglages dans `SOLVEUR` et
`LIRE_MAILLAGE` ») : confirmée pour `mpi_nbcpu` (U2.08.06, U1.04.00) et pour
`LIRE_MAILLAGE/PARTITIONNEUR='PTSCOTCH'` (U4.21.01, avec la réserve sur les POI1, que
l'estacade utilise pour ses ressorts) ; corrigée pour `SOLVEUR` : `MATR_DISTRIBUEE` et
`REDUCTION_MPI` n'existent pas dans le `SOLVEUR` de `MACRO_ELAS_MULT` (catalogue) ; la
distribution du modèle est le défaut d'`AFFE_MODELE` (`SOUS_DOMAINE`), sans mot-clé à
écrire ; le réglage propre aux post-traitements est `CALC_CHAMP/PARALLELISME_TEMPS`
(U4.81.04).** Aucun paramètre n'est énoncé de mémoire : chacun est cité ci-dessus.

### 1.4 Correctifs génériques (tronc commun)

- `aster_expert.execution.ressources` (nouveau) : lecture des quatre paramètres `P` de
  ressource de l'`.export` (`time_limit`, `memory_limit`, `ncpus`, `mpi_nbcpu`, rien
  d'autre ; lacune documentée : `run_aster.export` n'est importable que dans le
  conteneur), ressources de la machine (`os.sched_getaffinity`, `/proc/meminfo`),
  ordre de priorité ligne de commande > `.export` > `config/machine.local.yaml` (non
  versionné) > `config/validation.yaml` > valeurs calculées ou défauts de `run_aster`
  (86 400 s, 1 fil, 1 processus). `docker run` reçoit `--cpus = ncpus × mpi_nbcpu`
  (refus au-delà des processeurs de la machine) et `--memory = mpi_nbcpu ×
  (memory_limit + 2 800 Mio)` (`addmem` de l'image ; refus au-delà de la mémoire de la
  machine) ; délai extérieur `time_limit × 1,25 × ncpus + 20 s`. **Plus aucun 1 800 s
  codé** : `timeout_seconds: auto`, `memory_mb: auto`.
- `ncpus` et `mpi_nbcpu` ne sont jamais imposés par la configuration à l'exécution :
  `run_aster` les lit dans l'`.export`, et le conteneur reçoit exactement ce qu'il
  utilisera. La configuration (`ncpus`, `mpi_processes`) fixe les valeurs que la chaîne
  des projets **écrit** dans l'`.export` qu'elle génère (`projet.yaml` peut les fixer,
  `comm.export.ncpus`, `comm.export.mpi_nbcpu`).
- `container_env` : la vue Spack (`$VIEW/bin`) est ajoutée **en dernier** au `PATH`, pour
  que `run_aster` trouve `mpiexec`.
- Seuil disque avant exécution (ENV-003) : `execution.min_free_disk_gb` (10 Go) ;
  `aster-expert run` refuse en dessous, avant de démarrer un conteneur.
- `env-check` : 10ᵉ vérification `ressources` (processeurs, mémoire totale et disponible,
  défauts des `.export` de projet, seuil disque, présence de `config/machine.local.yaml`).
- `aster-expert run` affiche les ressources résolues avant le départ ; `compte_rendu.json`
  et `compte_rendu.md` les portent (champ `resources`).
- **Statut des exécutions MPI** (défaut trouvé par les mesures `m02` et `m04`, ENV-004) :
  avec `mpi_nbcpu` > 1, `run_aster_main` se relance sous `mpiexec` en ajoutant **son
  propre** `--status-file`, dans un répertoire temporaire qu'il efface (`run_aster_main.py`,
  17.4.0) ; le nôtre n'était jamais écrit et `aster-expert run` rapportait `unknown` pour
  un calcul `DIAGNOSTIC JOB : OK` sur tous les rangs. `scripts/run_comm.py` calcule alors
  le statut par `run_aster.status.get_status` (fonction de `run_aster`, jamais réécrite)
  sur le listing de chaque rang, et retient le premier rang dont le diagnostic diffère de
  celui du rang 0 ; la façon dont le statut a été lu est écrite dans le compte rendu
  (`status_source`). Test : `tests/unit/test_run_comm_mpi.py`.
- `aster_expert.execution.profil` : profil des temps par commande.
- Tests : `tests/unit/test_execution_ressources.py` (dont `test_the_export_is_passed_on_to_
  docker_run`, qui lit la ligne `docker run` réellement construite), `tests/unit/
  test_execution_profil.py`, `tests/unit/test_env_check.py` mis à jour.

### 1.5 Mesures (cas de taille moyenne : N3, dalle de 0,25 m)

Le `.comm` de N3 (lot 47 ter) est relancé **inchangé**, seul l'`.export` change
(`projets/estacade_pieux_01/scripts/performances_lot47quater.py`) : `t01`, `t04`, `t08`,
`t12` (1, 4, 8, 12 fils, un processus) ; `m02`, `m04` (2, 4 processus MPI, un fil) ;
`m04t3` (4 × 3) ; `m04pt` (4 processus, `PARALLELISME_TEMPS='OUI'` sur les `CALC_CHAMP`
d'`EFGE_NOEU` et de `REAC_NODA`, seule variante dont le `.comm` change : niveau B
500/500) ; `c1` et `c2`, deux exécutions indépendantes lancées en même temps.
`memory_limit` 2 048 Mio par processus. **Contrôle d'identité** : toutes les valeurs des
`IMPR_TABLE` (format `E20.12`) comparées à celles de N3, écart relatif maximal.

### 1.6 Règle de choix des valeurs par défaut (écrite après `t01`, `t04`, `t08`)

- Une configuration n'est retenue que si ses tables égalent celles de N3 à 10⁻⁶ près en
  relatif (sinon : écart rapporté, configuration écartée).
- Valeurs par défaut des `.export` de projet (`execution.ncpus`, `execution.mpi_processes`) :
  la configuration la plus rapide ; à 10 % près de la plus rapide, celle qui prend le
  moins de cœurs.
- Exécutions simultanées : permises si `c1` et `c2` finissent chacune en moins de 1,5 fois
  la durée de `t01`, et si la somme des pics mémoire tient dans la mémoire de la machine.

## 2. Étape 1 — Deux écarts de transcription (H1, H2)

### 2.1 Variantes déclarées

Toutes sur base DST (E13, variante (a)), modèle de production avec les positions d'E18,
maillage de dalle de 0,05 m, mêmes réglages du solveur que la production
(`POSTTRAITEMENTS="FORCE"`). Générateur : `projets/estacade_pieux_01/generation.py`
(options `mixed_plug`, `deck_level`) et `projets/estacade_pieux_01/transcription.py` ;
script : `projets/estacade_pieux_01/scripts/variantes_lot47quater.py`.

| Exécution | Chevêtre | H1 bouchon mixte | H2 plan à +1,50 | Base de comparaison (lot 47 ter) |
| --- | --- | --- | --- | --- |
| Q1 | 0,90 | oui | non | S (DST, 0,90) |
| Q2 | 0,90 | non | oui | S |
| Q3 | 0,90 | oui | oui | S |
| Q4 | 0,80 | oui | oui | SH (DST, 0,80) |

### 2.2 H1 — section mixte du bouchon (calcul des caractéristiques)

Données (consigne du lot, qui cite la source) : béton C35/45, Ø 0,622 m (§ 20.4.1 de la
source), Ecm = 34 GPa (non fissuré), γ = 25 kN/m³ ; acier Es = 210 GPa (E7). Étendue :
**de la tête à −0,80**, selon la consigne du lot. *Écart signalé* : E14 (« Le bouchon va
de +0.70 à -0.80 ») fixe la zone de lecture de C3/C4 ; elle n'est pas modifiée (aucun
changement de la référence) ; la légende de la figure 66 citée par la consigne
(« att. élevée-béton », « im-béton ») place du béton dans les deux familles du haut, ce
qui est cohérent avec « de la tête ».

- Ac = π × 0,622² / 4 = **0,303858 m²** ; Ic = π × 0,622⁴ / 64 = **7,34736 × 10⁻³ m⁴** ;
  Ecm × Ic = 249,8 MN·m².
- n = Es / Ecm = 210 / 34 = **6,17647**.
- Section homogénéisée en acier : A = As + Ac / n ; I = Is + Ic / n.
- Masse : matériau acier propre à chaque tronçon mixte, RHO = (γs·As + γc·Ac) / (g·A), pour
  que le poids propre soit exactement celui de l'acier et du béton.
- Section de calcul : tube équivalent de même A et I (CA-057), comme la référence.

| Tronçon | Cotes (B1 ; H2) | As (m²) | Is (m⁴) | A (m²) | I (m⁴) | Es·Is → Es·I (MN·m²) | RHO (kg/m³) | Tube équivalent R ; EP (m) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1 | +1,30 (+1,50) à +0,70 | 0,03053 | 1,55063 × 10⁻³ | 0,0797261 | 2,74020 × 10⁻³ | 325,6 → 575,4 | 12 777,0 | 0,285358 ; 0,048606 |
| T2 | +0,70 à 0,00 | 0,03053 | 1,55063 × 10⁻³ | 0,0797261 | 2,74020 × 10⁻³ | 325,6 → 575,4 | 12 777,0 | 0,285358 ; 0,048606 |
| T3 | 0,00 à −0,80 | 0,034643 | 1,77083 × 10⁻³ | 0,0838391 | 2,96040 × 10⁻³ | 371,9 → 621,7 | 12 542,8 | 0,289766 ; 0,050439 |

Le tube équivalent fixe A et I ; les coefficients de cisaillement de `POU_D_T` (section
`CERCLE`) sont ceux de ce tube fictif, pas ceux de la section mixte (limite).

### 2.3 H2 — plan du tablier à +1,50

Tablier, chevêtres et têtes de pieux à +1,50 ; ressorts à leurs cotes (B3, le premier à
+1,00 pour les files 1 et 7) ; tronçon T1 de B2 prolongé jusqu'au nœud du tablier (E3) ;
pointes à −13,00. Nouveau maillage Salomé, même script (`maillage/estacade_mesh.py`),
paramètres et invariants calculés avant Salomé (`maillage/params_h0p050_plan1p50.json`,
`maillage/invariants_h0p050_plan1p50.yaml`) : ils ne diffèrent de ceux de la production
que par la cote 1,3 → 1,5 (`z_dalle`, première cote des pieux, haut de `PIEU_T1`, boîtes
englobantes). Critère du maillage : `mesh check` sans écart. Q1 utilise le maillage de
production (0,05 m) déjà vérifié.

Règles de lecture inchangées (E17, v2), appliquées avec la cote de tête de la variante :
C3 de la tête (+1,50 en H2) à −0,80, élément de tête compris ; C4 dans le bouchon d'E14
(+0,70 à −0,80) ; C5 sur tout le pieu.

### 2.4 Contrôles des exécutions (à 10⁻⁶ en relatif)

- Σ DZ des réactions des pointes = charge des roues, pour chacune des 299 positions (TS,
  LM2, essieu de trottoir d'E18) ;
- PP : Σ DZ des pointes = poids de la variante (dalle + chevêtres + acier des pieux du
  nœud du tablier à la pointe + béton du bouchon) :

| Exécution | Dalle | Chevêtres | Acier des pieux | Béton du bouchon | PP attendu (N) |
| --- | --- | --- | --- | --- | --- |
| Q1 | 1 872 000 | 1 134 000 | 547 297,604 | 223 335,618 | 3 776 633,222 |
| Q2 | 1 872 000 | 1 134 000 | 554 008,098 | — | 3 560 008,098 |
| Q3 | 1 872 000 | 1 134 000 | 554 008,098 | 244 605,676 | 3 804 613,774 |
| Q4 | 1 872 000 | 1 008 000 | 554 008,098 | 244 605,676 | 3 678 613,774 |

- exécution `OK` ; toute alarme lue dans les diagnostics (DIAG/ENV) avant hypothèse.

### 2.5 Critère de conclusion (consigne, précisé ici avant toute exécution)

Tolérances d'E12. Lignes, toutes lues selon E17 v2 :

| Rôle | Point | Lignes | Tolérance |
| --- | --- | --- | --- |
| objectif | C3 | ELS f, ELS c, ELU (111) | 5 % |
| objectif | C5 | ELU (111) | 5 % |
| garde | C2 | ELS f, ELS c, ELU (112) | 3 % |
| garde | C4 | ELU (114) | 5 % |
| garde | C6 | **barre seule** ELS f, ELS c (105), ELU (112) | 5 % |
| garde | C7 | **barre seule** ELU (enveloppe 100-115), en module | 5 % |
| garde | C8 | **barre seule** ELU (105, 112), toutes lignes | 5 % |

- **H1, H2 ou leur combinaison expliquent C3 et C5** pour une variante Qi si les quatre
  lignes « objectif » sont dans 5 %, **et** si aucune ligne « garde » **n'en sort**.
- « En sortir » (précision écrite avant exécution) : une ligne de garde qui est dans sa
  tolérance pour la base de même chevêtre et même dalle (S pour Q1 à Q3, SH pour Q4,
  lot 47 ter) et ne l'est plus pour Qi. Raison : avec le chevêtre de 0,90, C6 et C7
  « barre seule » sont déjà hors tolérance en S (+8,6 à +12,9 % ; −12,5 %) ; H1 et H2
  ne peuvent pas les « faire sortir ». La **lecture stricte** (toutes les lignes de
  garde dans leur tolérance) est rapportée aussi, sans être le verdict.
- Verdict par variante : « explique » / « n'explique pas » ; puis, pour H1 et H2 : H1 seul
  (Q1), H2 seul (Q2), combinaison (Q3, Q4). Les effets (Q1 − S, Q2 − S, Q3 − S, Q4 − SH)
  sont rapportés ligne par ligne, sans verdict.
- **C6, C7, C8 barre seule sur les maillages de 0,25 et 0,50 m** (SH, lot 47 ter, sans
  nouveau calcul) : rapportées avec leur variation entre maillages ; même critère de
  comparabilité que le § 3.4 du lot 47 ter (variation ≤ 10 % : la valeur ne dépend pas
  de la taille de maille au-delà de la tolérance).

## 3. Étape 2 — Clôture (méthode)

- Tableau final d'attribution (A à G) : celui du lot 47 ter (§ 6.6), mis à jour ligne par
  ligne par le verdict du § 2.5 : une ligne G (C3 ELS c, C5) passe en **B** (donnée de la
  source perdue à la transcription) si la variante qui la ramène dans sa tolérance est
  celle d'une hypothèse de transcription (H1 ou H2) et que le critère est satisfait ;
  sinon elle reste G avec les pistes examinées.
- PRE-039 : décision de MM, versée dans la couche `precedents` (texte de MM, domaine de
  validité, justification CA-058 et plan factoriel du lot 47 ter).
- Leçons : chacune avec la règle ou la connaissance créée.
- Métriques : `rex estacade_pieux_01`, registre ; comparaison au quai et à la dalle.

## 4. Capitalisation prévue

- DIAG-025 : cause corrigée (`aster-expert run` lit l'`.export`) ; ENV-003 : prévention
  (seuil avant exécution) et politique de rétention de `data/processed/`
  (`docs/retention_donnees.md`) ;
- constat(s) sur le parallélisme de l'image 17.4.0 si les mesures en établissent ;
- PRE-039 ; leçons de transcription (skill `hypotheses-drafting`) ;
- `rex`, paquet de résultats, notes, `docs/etat.yaml`.
