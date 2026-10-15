# Compte rendu d'exécution — pontons_alu_01.comm

Exécution Code_Aster encadrée (`aster-expert run`). Niveau atteint au mieux : C (exécution jusqu'à `FIN`) si le statut est `completed_ok` ou `completed_with_alarms` ; aucun contrôle physique n'est fait ici.

| Élément | Valeur |
| --- | --- |
| Fichier de commandes | `/home/ubuntu/projets/aster-expert/projets/pontons_alu_01/resultats/lot51/P4/pontons_alu_01.comm` |
| Code_Aster | 17.4.0 |
| Image | `simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5` |
| Commande | `python3 /work/_aster_expert_run_comm.py --file /work/pontons_alu_01.export --wrkdir /work --status-file /work/__status__ --time-limit 3600 --memory-limit 6144` |
| Ressources | ncpus 1 (.export), mpi_nbcpu 1 (.export), time_limit 3600 s (.export), memory_limit 6144 Mio (.export) ; docker --cpus=1 --memory=8944m ; délai extérieur 4520 s |
| Statut | completed_ok |
| Diagnostic (`run_aster.status`) | OK |
| Lecture du statut | run_aster.status.Status.load |
| Code de retour | 0 |
| Durée | 160.6 s |
| Date | 2026-10-15T11:06:20.369270+00:00 |
| Répertoire | `/home/ubuntu/projets/aster-expert/data/processed/runs/20261015T110339-f66ff405` |
| Listing | `/home/ubuntu/projets/aster-expert/data/processed/runs/20261015T110339-f66ff405/proc.0/fort.6` |

## Fichiers donnés à Code_Aster

| Fichier | SHA-256 |
| --- | --- |
| `pontons_alu_01.comm` | `fcb189cb66b6aebdb630249882d5faad3c0b44199d8eb2cf27a50b8e7b7ba939` |
| `pontons_alu_01.connaissances.yaml` | `fb2fccb771020f9c0a929e33eb1d17ddbef41051549675b73d6f45b0e9f98a38` |
| `pontons_alu_01.export` | `adb8c657d1913637c76e14eb971553a4373c973fff6da9c303fdcbee6e5ef1ba` |
| `pontons_alu_01.mmed` | `dec6cc9b919f0aaf943f8e76d0d26d881f94c7d0bb12da89388ad5b620173b04` |

## Messages (`run_aster.error_messages`)

0 alarme(s), 0 erreur(s).

## Connaissances appliquées (déclaration, lot 46)

Déclaration `projets/pontons_alu_01/resultats/lot51/P4/pontons_alu_01.connaissances.yaml` (SHA-256 `fb2fccb771020f9c…`).

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
| `proc.0/fort.15` | 493243 |
| `proc.0/fort.20` | 338619 |
| `proc.0/fort.31` | 35650506 |
| `proc.0/fort.32` | 19488687 |
| `proc.0/fort.33` | 85291 |
| `proc.0/fort.6` | 3369761 |
| `proc.0/fort.8` | 0 |
| `proc.0/fort.9` | 0 |
| `proc.0/pontons_alu_01.comm.changed.py` | 92950 |
