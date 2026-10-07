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

## 5. Résultats

(Rédigés après les exécutions ; les sections 1 à 4 ne sont pas modifiées, hormis l'ajout
au § 1.4 du correctif du statut MPI, fait avant le commit des critères `27efdbc` et avant
toute exécution de Q1 à Q4.)

### 5.1 Étape 0 — Mesures d'accélération (N3, dalle 0,25 m)

Résultats : `projets/estacade_pieux_01/resultats/lot47quater/perf/mesures.json`
(`scripts/performances_lot47quater.py analyser`). Durée = durée du compte rendu (conteneur
compris) ; « tables » = écart aux 62 271 valeurs `E20.12` de N3 (écart absolu maximal
rapporté à la plus grande valeur, 4,7 × 10⁶ N).

| Mesure | ncpus × MPI | Exécution | Durée | / t01 | Statut | Tables |
| --- | --- | --- | --- | --- | --- | --- |
| t01 | 1 × 1 | `20261006T152556-49f4d7bd` | 118,6 s | 1,00 | OK | identiques |
| t04 | 4 × 1 | `20261006T152755-e739395d` | 115,3 s | 1,03 | OK | identiques |
| t08 | 8 × 1 | `20261006T152951-a035f140` | 138,8 s | 0,85 | OK | identiques |
| t12 | 12 × 1 | `20261006T153211-3bf172dd` | 288,0 s | 0,41 | OK | identiques |
| m02 (1ʳᵉ) | 1 × 2 | `20261006T153700-fcf5f2ca` | 127,0 s (`TOTAL_JOB`) | — | OK sur les 2 rangs, rapporté `unknown` (ENV-004) | — |
| m04 | 1 × 4 | `20261006T153913-0a246b46` | 156,5 s | 0,76 | OK sur les 4 rangs, rapporté `unknown` (ENV-004) | 2,9 × 10⁻¹⁴ |
| m04t3 | 3 × 4 | `20261006T154150-780297c0` | — | — | **bloqué** dans `CALC_CHAMP` (DIAG-026), arrêté par la session | — |
| *second jour (session graphique de la VM à ≈ 1,25 cœur)* | | | | | | |
| t01b | 1 × 1 | `20261007T074225-d8e14cf1` | 135,3 s | 0,88 | OK | identiques |
| m02 | 1 × 2 | `20261007T073342-02692da3` | 159,0 s | 0,75 | OK (statut lu sur 2 rangs) | 5,8 × 10⁻¹⁴ |
| m04pt | 1 × 4, `PARALLELISME_TEMPS` | `20261007T073622-91853194` | 173,4 s | 0,68 | OK avec alarmes `PREPOST_15` (4) | **2,9 × 10⁻³** (DIAG-027) |
| c1 ∥ c2 | 1 × 1, lancées ensemble | `20261007T073917-012e365e`, `…-c403fc7b` | 151,2 et 157,5 s | 1,12 et 1,16 × t01b | OK | identiques |
| m04t3b | 3 × 4, time_limit 300 s | `20261007T074441-b096aca0` | 230,5 s | 0,51 | OK | 2,9 × 10⁻¹⁴ |

Profil de t01 (112,1 s de `TOTAL_JOB`) : `MACRO_ELAS_MULT` 37,3 s, `CALC_CHAMP` 51,2 s,
`IMPR_RESU` 3,8 s, reste 19,1 s ; de t12 : `MACRO_ELAS_MULT` 205,8 s (×5,5),
`CALC_CHAMP` 52,6 s. Pic mémoire par rang : 907 Mo (m02), 934 Mo (N3).

Faits :

- **Fils OpenMP** : aucun gain (4 fils : 1,03) puis une dégradation (8 fils : 0,85 ;
  12 fils : 0,41), portée par `MACRO_ELAS_MULT` (factorisation) ; résultats identiques à
  l'octet. *Déduction* : avec l'OpenBLAS monofil de l'image, seuls les fils de MUMPS et
  de `libgomp` travaillent, et leur coût de synchronisation l'emporte sur ce problème
  (3 573 nœuds de dalle).
- **MPI** : aucun gain (2 et 4 processus : 0,75 et 0,76 de t01 ; m02 rejouée, 159 s
  contre 135 s pour t01b) ; tables égales au bruit numérique près (6 × 10⁻¹⁴ de la plus
  grande valeur, sur des composantes quasi nulles), donc **écartées par la règle du
  § 1.6** (10⁻⁶ en relatif) prise à la lettre — sans effet sur le choix, MPI étant plus
  lent. U2.08.06 conseille 30 000 à 50 000 ddl par processus : N3 en a environ 25 000 au
  total.
- **`PARALLELISME_TEMPS='OUI'`** : plus lent (173 s) et **faux** sur trois réactions
  (DIAG-027).
- **Deux exécutions simultanées** : 1,12 et 1,16 fois la durée d'une exécution seule.

**Valeurs par défaut retenues (règle du § 1.6)** : `execution.ncpus: 1`,
`execution.mpi_processes: 1` (t04 est à 3 % de t01 et prend quatre cœurs) — inchangées.
**Exécutions simultanées permises** (1,16 < 1,5 ; pics mémoire de 0,9 à 4,3 Go par
exécution) : c'est le seul gain mesuré sur cette machine, et il est appliqué à Q1 à Q4,
lancées ensemble (§ 5.2). Limites : un seul cas de taille moyenne ; la production (0,05 m,
76 000 nœuds, ≈ 460 000 ddl) n'a pas été mesurée en MPI ; la dispersion d'un jour à
l'autre (t01 118,6 s, t01b 135,3 s) vient de la charge de la VM et atteint 14 %.

### 5.2 Étape 1 — Exécutions Q1 à Q4

Lancées **ensemble** (règle du § 1.6), toutes au niveau B intégral avant exécution
(`aster-expert validate` : 504, 501, 504, 504 commandes), `ncpus` 1, `mpi_nbcpu` 1,
`memory_limit` 6 144 Mio (`docker run --cpus=1 --memory=8944m`, délai extérieur 9 020 s).

| Exécution | Répertoire | Durée | Statut | Contrôle (§ 2.4) | PP obtenu |
| --- | --- | --- | --- | --- | --- |
| Q1 | `data/processed/runs/20261007T075647-fcd8e999` | 4 230,2 s | OK, aucune alarme | 299 positions, écart max 5,6e-12 | à 2,1e-12 de 3 776 633,222 N |
| Q2 | `…/20261007T075647-743a7a50` | 4 350,4 s | OK, aucune alarme | 6,6e-12 | à 2,2e-12 de 3 560 008,098 N |
| Q3 | `…/20261007T075647-2b4ff984` | 4 393,1 s | OK, aucune alarme | 5,4e-12 | à 2,2e-12 de 3 804 613,774 N |
| Q4 | `…/20261007T075647-3a69da8e` | 4 322,0 s | OK, aucune alarme | 5,3e-12 | à 1,2e-12 de 3 678 613,774 N |

Pic mémoire : 4 322 à 4 344 Mo par exécution. Les quatre exécutions ont pris **73 min
ensemble**, contre ≈ 4 × 52 min en série (N1 seule : 3 127 s) : facteur ≈ 2,9.
Contrôles : `projets/estacade_pieux_01/references/controles_lot47quater.json` ; lectures :
`references/lectures_lot47quater.json` ; verdict : `references/verdict_lot47quater.json`
(`scripts/variantes_lot47quater.py controler`, `comparer`). Maillage H2 :
`references/maillage_lot47quater/rapport_h0p050_plan1p50.txt` (367/367, 76 073 nœuds),
Salomé 10,5 s.

### 5.3 Verdict (critère du § 2.5)

Écart à la source ; entre parenthèses, celui de la base (S pour Q1 à Q3, SH pour Q4).

| Rôle | Ligne | Source | Q1 (H1) | Q2 (H2) | Q3 (H1 + H2) | Q4 (H1 + H2, 0,80) | Tol. |
| --- | --- | --- | --- | --- | --- | --- | --- |
| objectif | C3 ELS f (111) | 209 | 237,7 ; +13,7 % ✗ (−3,3 %) | 201,4 ; −3,6 % (−3,3 %) | 237,9 ; +13,8 % ✗ | 237,3 ; +13,6 % ✗ (−3,5 %) | 5 % |
| objectif | C3 ELS c (111) | 312 | 343,5 ; +10,1 % ✗ (−5,8 %) | 294,6 ; −5,6 % ✗ | 345,6 ; +10,8 % ✗ | 344,9 ; +10,5 % ✗ (−5,9 %) | 5 % |
| objectif | C3 ELU (111) | 449 | 508,1 ; +13,2 % ✗ (−3,1 %) | 435,9 ; −2,9 % | 511,1 ; +13,8 % ✗ | 510,1 ; +13,6 % ✗ (−3,3 %) | 5 % |
| objectif | C5 ELU (111) | 463 | 508,1 ; +9,7 % ✗ (−6,1 %) | 435,9 ; −5,9 % ✗ | 511,1 ; +10,4 % ✗ | 510,1 ; +10,2 % ✗ (−6,2 %) | 5 % |
| garde | C2 ELS f (112) | 514 | +2,8 % (+2,4 %) | +2,4 % | +2,7 % | +0,9 % (+0,6 %) | 3 % |
| garde | C2 ELS c (112) | 727 | −1,5 % (−1,9 %) | −1,9 % | −1,5 % | −2,9 % (−3,2 % ✗) | 3 % |
| garde | C2 ELU (112) | 1 048 | −2,1 % (−2,5 %) | −2,5 % | −2,1 % | −3,4 % ✗ (−3,8 % ✗) | 3 % |
| garde | C4 ELU (114) | 253 | 273,3 ; **+8,0 % ✗** (+2,4 %) | −3,3 % | +2,3 % | +2,1 % (+2,4 %) | 5 % |
| garde | C6 ELS f (105), barre seule | 180 | +12,6 % ✗ (+12,9 % ✗) | +12,8 % ✗ | +12,4 % ✗ | −1,9 % (−1,1 %) | 5 % |
| garde | C6 ELS c (105), barre seule | 276 | +9,6 % ✗ (+10,2 % ✗) | +10,2 % ✗ | +9,5 % ✗ | −4,3 % (−3,4 %) | 5 % |
| garde | C6 ELU (112), barre seule | 408 | +8,0 % ✗ (+8,6 % ✗) | +8,6 % ✗ | +8,0 % ✗ | 385,7 ; **−5,5 % ✗** (−4,6 %) | 5 % |
| garde | C7 ELU (100-115), barre seule | 177 | 171,6 ; −3,0 % (−12,5 % ✗) | −12,9 % ✗ | −3,1 % | +1,8 % (−9,5 % ✗) | 5 % |
| garde | C8 ELU (105, 112), barre seule | 653 | +1,7 % (+1,2 %) | +1,2 % | +1,7 % | −2,1 % (−2,7 %) | 5 % |

**Verdict, selon le critère écrit avant l'exécution : ni H1, ni H2, ni leur combinaison
n'expliquent C3 et C5.** Aucune des quatre variantes n'a ses quatre lignes « objectif »
dans 5 % ; gardes sorties par rapport à la base : C4 ELU (Q1), C6 ELU barre seule (Q4) ;
lecture stricte : aucune variante ne tient toutes les gardes.

Lecture (faits, puis déductions marquées) :

- **H2 (plan à +1,50) : effet négligeable** sur les pieux (C3, C5 : ≤ 0,3 point ; C4
  −5,7 points). Les écarts de C3 ELS c (−5,6 %) et C5 (−5,9 %) restent ceux de S.
- **H1 (bouchon mixte de la tête à −0,80) : effet fort et de sens opposé à l'écart.**
  EI de la tête 325,6 → 575,4 MN·m² ; C3 passe de −3 / −6 % à +10 / +14 %, C5 de −6 % à
  +10 %. *Déduction* : la source se situe entre les deux modèles ; une raideur de tête
  intermédiaire (bouchon sur l'étendue d'E14, +0,70 à −0,80, sans le tronçon de tête ; ou
  béton fissuré, Ecm réduit) pourrait encadrer C3 et C5 ; **non testé** (hors des
  variantes déclarées).
- **H1 ramène C7 barre seule dans la tolérance** (−12,5 → −3,0 % ; −9,5 → +1,8 % avec
  0,80 m) et, en information, **C9** (moment de dalle près des têtes) de −10,5 % à
  +3,4 % (ELU) ; il éloigne C4 (+8,0 % en Q1, sans H2) et C13 « inf. » LM1 (−1,5 →
  −5,4 %). *Déduction* : la raideur de la tête de pieu gouverne aussi le moment
  d'encastrement transmis au chevêtre et à la dalle.
- La combinaison Q4 (0,80 m) tient C6, C7, C8 barre seule et C2 ELS ; elle perd C2 ELU
  (−3,4 %, poids des chevêtres de 0,80 m, comme SH) et C6 ELU (−5,5 %).

### 5.4 C6, C7, C8 barre seule sur les maillages de 0,25 et 0,50 m (lot 47 ter, sans calcul)

`references/maillages_barre_seule_lot47quater.json` (`variantes_lot47quater.py grossiers`),
configuration SH.

| Ligne | Source | 0,05 m | 0,25 m | 0,50 m | Variation max | Comparabilité (≤ 10 %) |
| --- | --- | --- | --- | --- | --- | --- |
| C6 ELS f (105) | 180 | 178,0 (−1,1 %) | 178,0 (−1,1 %) | 177,8 (−1,2 %) | 0,1 % | comparable |
| C6 ELS c (105) | 276 | 266,7 (−3,4 %) | 266,7 (−3,4 %) | 266,2 (−3,5 %) | 0,2 % | comparable |
| C6 ELU (112) | 408 | 389,4 (−4,6 %) | 388,5 (−4,8 %) | 388,2 (−4,9 %) | 0,3 % | comparable |
| C7 ELU (100-115) | 177 | 160,1 (−9,5 %) | 156,7 (−11,5 %) | 150,5 (−15,0 %) | 6,0 % | comparable |
| C8 ELU (105, 112), toutes lignes | 653 | 635,2 (−2,7 %) | 569,8 (−12,7 %) | 511,7 (−21,6 %) | **19,4 %** | **non comparable sans le maillage source** |

La part de la barre dans l'effort tranchant près du pieu (C8) dépend du maillage de la
dalle même en DST : la concordance de C8 barre seule à 0,05 m (−2,7 %) est un fait, sa
robustesse au maillage ne l'est pas. Les moments de la barre (C6) n'en dépendent pas.

## 6. Clôture du lot 47

### 6.1 Tableau final d'attribution (A à G)

Celui du lot 47 ter (§ 6.6), mis à jour par le § 5 ; lignes de la référence R (DKT,
0,90 m), verdicts v2.

| Point | Ligne | R (v2) | Catégorie finale | Preuve |
| --- | --- | --- | --- | --- |
| C1 | ELS c (107) | 0,4375 cm | aucun écart (D : arrondi de la source) | inchangé |
| C2 | ELS f, ELS c, ELU | +2,5 / −1,8 / −2,4 % | aucun écart (D : la source donne aussi 554, 767, 1 102 kN) | H1, H2 : ≤ 0,4 point |
| C3 | ELS f, ELU | −3,2 / −3,0 % | aucun écart (v1 : A, lieu de lecture) | — |
| C3 | ELS c | −5,7 % | **G, inexpliqué** | pistes examinées : DKT/DST, chevêtre, maillage, lieu, famille (lot 47 ter) ; **H2** sans effet (−5,6 %) ; **H1** l'inverse (+10,1 %) ; non testé : raideur de tête intermédiaire |
| C4 | ELU | +2,5 % | aucun écart | H1 seul : +8,0 % |
| C5 | ELU | −5,9 % | **G, inexpliqué** | idem C3 ELS c (H2 −5,9 %, H1 +9,7 %) |
| C6 | ELS f, ELS c, ELU, total | +19,5 / +17,1 / +16,0 % | **C (chevêtre, E2 ; D : I2 de la source) et A (grandeur : la source publie la barre)** | barre seule avec 0,80 m : −1,1 à −4,6 % ; indépendante du maillage (≤ 0,3 %) |
| C7 | ELU, total | +0,4 % | aucun écart ; barre seule : **B, section mixte de tête perdue (H1)** | barre seule −12,5 % (S) → −3,0 % (Q1) ; −9,5 % (SH) → +1,8 % (Q4) |
| C8 | ELU, total | +10,6 % | **C (E13, dalle DKT) et A (E17.2)** ; barre seule **E** (maillage) | barre seule DST −2,7 % à 0,05 m, −21,6 % à 0,50 m |
| C9 | ELS f, ELS c, ELU | −10,6 / −10,7 / −10,3 % | **E, maillage** (inchangé) ; information : H1 donne +3,0 à +4,5 % | variation 30 à 39 % entre maillages (lot 47 ter) |
| C10, C11, C12 courant, C13 inf. LM1/LM2, C13 V LM2 | — | dans la tolérance | aucun écart | — |
| C12 | ELU rive | −60,9 % | **E, maillage** (v1 : B, E18) | inchangé |
| C13 | LM1 sup., LM1 V, LM2 sup. | −16,2 / +33,1 / +12,7 % | **E, maillage** | inchangé |

Bilan des 13 lignes hors tolérance de R : **4 en C et A**, **7 en E**, **2 en G** (C3 ELS c,
C5), **0 en F**. L'étape 1 n'a déplacé aucune ligne jugée de G vers B : les deux
écarts de transcription sont **réels** (H1, H2 sont dans la source), mais ils
n'expliquent pas C3 et C5 au sens du critère. H1 explique la lecture « barre seule » de C7
(B). **Statut final de l'estacade : contre-calcul au niveau D, chaque écart attribué** ;
deux lignes restent inexpliquées, encadrées entre le modèle sans bouchon (−3 à −6 %) et
le modèle à bouchon mixte de la tête à −0,80 (+10 à +14 %).

### 6.2 Précédent PRE-039

Décision de MM (consigne, étape 2), recopiée à l'identique et enregistrée comme **E20**
dans la fiche (`donnees/sources/arbitrage_estacade_pieux_01_lot47quater.md`,
`scripts/fiche_lot47.py`, heure d'enregistrement `enregistrement_lot47quater.json`), sans
changer la référence (E13 garde la dalle DKT). `connaissances/precedents/PRE-039.yaml`
(`scripts/connaissances_lot47quater.py`) : décision E20, CA-058, plan factoriel du lot
47 ter ; domaine de validité de MM (h/L ≤ 1/10, poutres au plan moyen) ; « proposition
seulement ». À ajouter au domaine, par ce lot (fait, § 5.4) : la part de l'effort
tranchant portée par la barre, en DST, dépend encore du maillage de la dalle.

### 6.3 Leçons pour l'outil

| Leçon | Règle ou connaissance |
| --- | --- |
| Transcription d'une source : relever **toutes** les légendes, les niveaux et les sections du modèle source, pas seulement le texte (H1, H2 perdus au lot 47) | skill `hypotheses-drafting`, § 2 quater (ce lot) |
| Points de comparaison : lieu, composante et famille déclarés avant exécution | skill `code-aster-expert`, § 6 sexies (lot 47 bis) ; E17 |
| Lecture hors singularité | PAT-013 et CTL-014 (lots 47, 47 bis) ; disques d'E17.3 |
| Partage de l'effort tranchant entre plaque et poutre | CA-058 (lot 47 bis, domaine précisé au lot 47 ter) ; PRE-039 (ce lot) ; dépendance au maillage en DST (§ 5.4) |
| Ressources : l'`.export` ne pilotait pas `docker run` ; le parallélisme n'est pas un gain par défaut | `aster_expert.execution.ressources`, DIAG-025 corrigé ; mesures du § 5.1 ; DIAG-026, DIAG-027 |
| Statut des exécutions MPI | ENV-004, `scripts/run_comm.py` |
| Disque plein | ENV-003 : seuil avant exécution, `docs/retention_donnees.md` |

### 6.4 Métriques du projet, comparées au quai et à la dalle

| | Quai (`quai_cw_test_01`) | Dalle (`dalle_appuyee_01`) | Estacade (`estacade_pieux_01`) |
| --- | --- | --- | --- |
| Lots | 40 (base, lots 1 à 40) puis 42, 44 | 3 (43, 44, 45) | **4** (47, 47 bis, 47 ter, 47 quater) |
| Exécutions mesurées (dév. + vérif.) | 177 + 196 | 5 + 1 | **28 + 16** |
| Taux d'échec en développement | 41,2 % (base 38,4 %) | 0,0 % | **25,0 %** (7 / 28) |
| Échecs en vérification | 0 | 0 | 3 (mesures MPI : ENV-004 ×2, DIAG-026) |
| Interventions de MM déclarées | 25 (estimation, lots 19 à 41) | 3 | **2** (47 : 1 ; 47 bis : 0 ; 47 ter : 1 ; 47 quater : 0) |
| Apports de fond du superviseur dans les consignes | — | — | 3 (diagnostic (b) au 47 bis, hypothèse DST + 0,80 au 47 ter, relecture H1/H2 au 47 quater) |
| Erreurs évitées par la base (déclarées) | — | 11 | **13** (8 + 2 + 1 + 2) |
| Connaissances créées / promues | 125 / 2 | 22 / 3 | 22 / 0 (dont 3 diagnostics et PRE-039 à ce lot) |
| Niveau atteint | D | E | **D** (contre-calcul d'un modèle non validé) |

Lecture : l'estacade, premier ouvrage réel, a demandé 4 lots contre 3 pour la dalle et une
quarantaine pour le quai ; son taux d'échec (25 %) est inférieur à celui du quai (41 %),
et 5 de ses 10 échecs ont été retrouvés automatiquement par la base. Les échecs restants
sont d'environnement ou d'outil (disque, délai, statut MPI, blocage hybride), aucun de
modélisation non diagnostiqué. Le superviseur a apporté à chaque lot de reprise
l'hypothèse ou la relecture qui orientait le lot : c'est la part de l'expertise qui
n'est pas encore dans l'outil (relecture de la source, § 6.3).

### 6.5 Retour d'expérience (`aster-expert rex estacade_pieux_01`)

Sortie après classement des trois échecs du lot, `--enregistrer --lot 47quater` et
`--manifeste` (archive de 44 exécutions enregistrée) :

```text
Retour d'expérience du projet estacade_pieux_01
Exécutions attribuées au projet : 44 ; échecs : 10 ; depuis le dernier retour d'expérience (2026-10-07) : 0.
Développement : 28 exécution(s), 7 échec(s), taux 25,0 % ; vérification : 16 exécution(s), 3 échec(s) (hors taux).
Classement : nouveau 6, rattaché 4.
Diagnostic retrouvé automatiquement par la base (seul et égal au classement) : 5/10 échecs rattachés.
Répartition par cause : DIAG-003 3, DIAG-010 1, DIAG-025 1, DIAG-026 1, ENV-003 2, ENV-004 2.
Constats de la fiche à verser dans la base : 0.
Candidats patrons dans le code du projet : 2 (similarité ≥ 0,40 ; 10 fonction(s) sous le seuil, non listées).
  projets/estacade_pieux_01/generation.py:fractional_loads_block — proche d'un patron (PAT-005, similarité 0.5)
  projets/estacade_pieux_01/generation.py:moving_loads_block — proche d'un patron (PAT-005, similarité 0.5)
Connaissances créées par le projet : 22 ; promues : 0.
Consultations journalisées (tous projets) : search_connaissances 43, search_constats 3.
Tous les échecs sont classés : clôture possible.
Métriques : connaissances/metriques/estacade_pieux_01.yaml
```

Correctif du tronc commun trouvé par ce retour d'expérience : une exécution **arrêtée sans
compte rendu** (`m04t3`) n'était attribuée à aucun projet et disparaissait des métriques ;
elle l'est maintenant par l'empreinte de son `.comm`, comme un compte rendu vide
(`aster_expert.connaissances.archive.attributed_runs`, test
`test_a_run_stopped_without_report_is_attributed_by_its_comm`).

Interventions de MM pendant le lot : **0** question posée. Deux relances (« Continue »)
après des attentes, sans effet sur le contenu. Décision prise par la session et signalée :
l'étendue du bouchon de H1 suit la consigne (« de la tête à −0,80 ») et non le texte
d'E14 (« de +0.70 à −0.80 »), E14 restant inchangée (§ 2.2).

### 6.6 Contrôles de fin de lot

| Commande | Résultat |
| --- | --- |
| `aster-expert env-check` | OK, profil vm, 10 vérifications (dont `ressources` : 14 processeurs, 21,0 Go) |
| `aster-expert mcp-check` | OK, 9 outils sur un serveur neuf |
| `ruff format --check .` ; `ruff check .` | 550 fichiers formatés ; aucune erreur |
| `mypy src` ; `mypy` | aucune erreur (133 et 392 fichiers) |
| `pytest` (série par défaut) | 1 629 réussis, 4 désélectionnés |
| `pytest -m lent` | 4 réussis (Code_Aster et Salomé réels, nouveau chemin d'exécution) |
| `aster-expert connaissances verifier` | OK (300 preuves confrontées) |
| `aster-expert etat verifier` | cohérent |
| `aster-expert projet exporter-resultats estacade_pieux_01` | niveau D ; `.comm` régénéré identique ; critère D du lot 47 bis signalé « antériorité non démontrable » (inchangé) |
| `aster-expert note controler estacade_pieux_01` | OK pour les deux notes |
| `aster-expert validate` (Q1 à Q4) | niveau B, 504, 501, 504, 504 commandes, 0 erreur |
| `aster-expert mesh check` (maillage H2) | 367/367 invariants |

Outils MCP : aucun outil n'a changé de nom, de paramètres ni de code ; la base de
connaissances a de nouvelles entrées, relues à chaque appel. Pas de redémarrage requis
par ce lot.

### 6.7 Limites

- **Contre-calcul d'un modèle non validé**, jamais un niveau E ; Q1 à Q4 sont des
  variantes déclarées, la référence reste R (E1 à E19 ; E20 n'est pas appliquée à
  l'estacade).
- H1 est testée sur la seule étendue de la consigne (tête à −0,80), béton non fissuré ;
  l'étendue d'E14 (+0,70 à −0,80) et un béton fissuré ne sont pas testés. Le tube
  équivalent fixe A et I de la section mixte, pas ses coefficients de cisaillement.
- Mesures de performance sur un seul cas de taille moyenne (N3) ; le modèle de production
  (≈ 460 000 ddl) n'a pas été mesuré en MPI ; dispersion de 14 % d'un jour à l'autre
  (charge de la VM) ; le blocage hybride (DIAG-026) n'est pas reproduit et sa cause n'est
  pas établie ; DIAG-027 repose sur une exécution.
- `config/machine.local.yaml` n'existe pas encore : MM peut y fixer les ressources de la
  VM (clés de la section `execution:`).
- Le critère « tables égales à 10⁻⁶ en relatif » (§ 1.6) écarte formellement les
  configurations MPI pour du bruit sur des valeurs quasi nulles (6 × 10⁻¹⁴ de la plus
  grande valeur) : critère trop strict pour MPI, rapporté tel quel, sans effet sur le
  choix.
