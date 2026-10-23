# Compte rendu d'exécution — pontons_alu_01.comm

Exécution Code_Aster encadrée (`aster-expert run`). Niveau atteint au mieux : C (exécution jusqu'à `FIN`) si le statut est `completed_ok` ou `completed_with_alarms` ; aucun contrôle physique n'est fait ici.

| Élément | Valeur |
| --- | --- |
| Fichier de commandes | `/home/ubuntu/aster-expert/projets/pontons_alu_01/resultats/lot54/A54/pontons_alu_01.comm` |
| Code_Aster | 17.4.0 |
| Image | `simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5` |
| Commande | `python3 /work/_aster_expert_run_comm.py --file /work/pontons_alu_01.export --wrkdir /work --status-file /work/__status__ --time-limit 3600 --memory-limit 6144` |
| Ressources | ncpus 1 (.export), mpi_nbcpu 1 (.export), time_limit 3600 s (.export), memory_limit 6144 Mio (.export) ; docker --cpus=1 --memory=8944m ; délai extérieur 4520 s |
| Statut | completed_ok |
| Diagnostic (`run_aster.status`) | OK |
| Lecture du statut | run_aster.status.Status.load |
| Code de retour | 0 |
| Durée | 283.2 s |
| Date | 2026-10-23T08:17:12.761371+00:00 |
| Répertoire | `/home/ubuntu/aster-expert/data/processed/runs/20261023T081229-c87839be` |
| Listing | `/home/ubuntu/aster-expert/data/processed/runs/20261023T081229-c87839be/proc.0/fort.6` |

## Fichiers donnés à Code_Aster

| Fichier | SHA-256 |
| --- | --- |
| `pontons_alu_01.comm` | `c2afe581482d98b054a43a388c2d765fdc4233b0f17cecd9744fe001bb617f2c` |
| `pontons_alu_01.connaissances.yaml` | `df1e6a633753aa24ddcd1170f07724c55810ef1021b77ffc3bd077ea6babfb8c` |
| `pontons_alu_01.export` | `adb8c657d1913637c76e14eb971553a4373c973fff6da9c303fdcbee6e5ef1ba` |
| `pontons_alu_01.mmed` | `383bd5c3076c1ce666b77abe3eaed5ef2f554c72869e39489590f5149b58d8ba` |

## Messages (`run_aster.error_messages`)

0 alarme(s), 0 erreur(s).

## Connaissances appliquées (déclaration, lot 46)

Déclaration `projets/pontons_alu_01/resultats/lot54/A54/pontons_alu_01.connaissances.yaml` (SHA-256 `df1e6a633753aa24…`).

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
| `PAT-005` | déjaugeage de la semelle (DEJ) en FORCE_COQUE FZ, repère global, intensité par unité de surface développée (semelle plane) |
| `DIAG-030` | appuis à axe sous l'axe des poutres : DRX des deux oreilles liées et cadre de la travée, pour éviter le mécanisme de torsion d'une poutre liée seulement en translation |

## Fichiers produits

| Fichier | Taille (octets) |
| --- | --- |
| `proc.0/1.export` | 229 |
| `proc.0/__timer__` | 348 |
| `proc.0/fort.15` | 1610777 |
| `proc.0/fort.20` | 1154014 |
| `proc.0/fort.31` | 341997378 |
| `proc.0/fort.32` | 221658894 |
| `proc.0/fort.33` | 6709159 |
| `proc.0/fort.6` | 49558771 |
| `proc.0/fort.8` | 0 |
| `proc.0/fort.9` | 0 |
| `proc.0/pontons_alu_01.comm.changed.py` | 247417 |
