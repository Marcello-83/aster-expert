# Compte rendu d'exécution — pontons_alu_01.comm

Exécution Code_Aster encadrée (`aster-expert run`). Niveau atteint au mieux : C (exécution jusqu'à `FIN`) si le statut est `completed_ok` ou `completed_with_alarms` ; aucun contrôle physique n'est fait ici.

| Élément | Valeur |
| --- | --- |
| Fichier de commandes | `/home/ubuntu/projets/aster-expert/projets/pontons_alu_01/resultats/lot51/A/pontons_alu_01.comm` |
| Code_Aster | 17.4.0 |
| Image | `simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5` |
| Commande | `python3 /work/_aster_expert_run_comm.py --file /work/pontons_alu_01.export --wrkdir /work --status-file /work/__status__ --time-limit 3600 --memory-limit 6144` |
| Ressources | ncpus 1 (.export), mpi_nbcpu 1 (.export), time_limit 3600 s (.export), memory_limit 6144 Mio (.export) ; docker --cpus=1 --memory=8944m ; délai extérieur 4520 s |
| Statut | failed |
| Diagnostic (`run_aster.status`) | <F>_ERROR |
| Lecture du statut | run_aster.status.Status.load |
| Code de retour | 6 |
| Durée | 25.1 s |
| Date | 2026-10-15T11:04:04.735873+00:00 |
| Répertoire | `/home/ubuntu/projets/aster-expert/data/processed/runs/20261015T110339-7254d74a` |
| Listing | `/home/ubuntu/projets/aster-expert/data/processed/runs/20261015T110339-7254d74a/proc.0/fort.6` |

## Fichiers donnés à Code_Aster

| Fichier | SHA-256 |
| --- | --- |
| `pontons_alu_01.comm` | `abc44e6a40738b4169130f726fdb312e513f9d8c250522bf9c93d76435599f80` |
| `pontons_alu_01.connaissances.yaml` | `fb2fccb771020f9c0a929e33eb1d17ddbef41051549675b73d6f45b0e9f98a38` |
| `pontons_alu_01.export` | `adb8c657d1913637c76e14eb971553a4373c973fff6da9c303fdcbee6e5ef1ba` |
| `pontons_alu_01.mmed` | `1241c45a4a897c6c9370a94a153c01db872673115215961ae8b859709c836a71` |

## Messages (`run_aster.error_messages`)

0 alarme(s), 1 erreur(s).

| Genre | Identifiant | Ligne | Message |
| --- | --- | --- | --- |
| <F> | FACTOR_11 | 2294 | <F> <FACTOR_11> Problème : la matrice est singulière ou presque singulière : Lors de la factorisation de la matrice, on a rencontré un problème (pivot nul ou presque nul) à la ligne 3199 qui correspond au degré de liberté donné ci-dessus. Risques et conseils : * Si la ligne correspond a un degré de liberté physique, il s'agit probablement d'un mouvement de corps rigide mal bloqué. Vérifiez les con |

## Diagnostics de la base de connaissances

Lire ces diagnostics avant toute autre hypothèse.

| Diagnostic | Statut | Signature | Correction |
| --- | --- | --- | --- |
| `DIAG-001` Pivot nul à la factorisation : relation cinématique et blocage sur le même ddl | établi | <F> <FACTOR_11> | Ne bloquer par DDL_IMPO que les ddl que la relation ne détermine pas : au plan de symétrie, DX/DRY/DRZ sur le groupe du plan privé des nœuds de l'anneau (DEFI_GROUP/DIFFE), l'anneau tenant ses ddl de LIAISON_SOLIDE (symmetry_and_support_block, contrôle check_symmetry_ddl_impo_no_ring_redundancy). |

## Connaissances appliquées (déclaration, lot 46)

Déclaration `projets/pontons_alu_01/resultats/lot51/A/pontons_alu_01.connaissances.yaml` (SHA-256 `fb2fccb771020f9c…`).

| Entrée | Ce qui en est appliqué |
| --- | --- |
| `CA-037` | poutres de Timoshenko POU_D_T pour toutes les barres, aluminium et béton |
| `CA-033` | actions de surface en FORCE_POUTRE FZ, accostage en FORCE_POUTRE FY, repère global |
| `CA-019` | amarrage en FORCE_NODALE FY sur les nœuds des poutres principales |
| `CA-054` | températures uniformes : CHAM_GD NOEU_TEMP_R de composante TEMP et AFFE_VARC, VALE_REF = 0, un champ de matériau par cas |
| `CA-048` | poids propre par PESANTEUR et RHO = γ / g |
| `CA-020` | ressorts nodaux de sol : CREA_POI1, DIS_T, K_T_D_N en repère global (réparti par RIGI_PARASOL) |
| `CA-036` | équilibre : seules les composantes bloquées des rotules côté quai sont sommées |
| `DIAG-004` | masse M_T_D_N nulle des ressorts DIS_T de la semelle, le modèle portant PESANTEUR |
| `DIAG-024` | MECA_STATIQUE et MACRO_ELAS_MULT avec un champ de matériau |

## Fichiers produits

| Fichier | Taille (octets) |
| --- | --- |
| `proc.0/1.export` | 229 |
| `proc.0/__timer__` | 348 |
| `proc.0/fort.15` | 62993 |
| `proc.0/fort.20` | 335739 |
| `proc.0/fort.6` | 140294 |
| `proc.0/fort.8` | 0 |
| `proc.0/fort.9` | 0 |
| `proc.0/glob.1` | 128614408 |
| `proc.0/pontons_alu_01.comm.changed.py` | 94899 |
| `proc.0/vola.1` | 87654408 |
