# Lot 47 — Journal d'autonomie (estacade sur pieux, contre-calcul)

Tenu au fil de la session. Classes, comme au lot 43 :

- **BLOCAGE** : impossible d'avancer sans MM ;
- **MANQUE** : information ou consigne absente, contournée ;
- **ÉVITÉ** : consultation de la base (`connaissances/`) ou de la documentation qui a évité une erreur ;
- **NON ÉVITÉ** : erreur commise alors qu'une connaissance de la base la décrivait ;
- **LACUNE** : connaissance ou capacité de l'outil qui manquait ;
- **OUTIL** : défaut d'un outil (MCP, CLI, tronc commun), corrigé ou signalé.

| # | Classe | Constat | Conséquence |
|---|---|---|---|
| 1 | BLOCAGE | Quatre points pratiques couverts ni par E1 à E12 ni par l'annexe B : étendue du bouchon (C3/C4 contre C5), surface d'application des roues, positions de LM2, formulations d'éléments (changement de la physique représentée). | Une seule question à MM (quatre réponses) : E13 à E16. Seule intervention de MM du lot. |
| 2 | MANQUE | La description de l'option LM2 proposée par la session portait une cote erronée (Y = ±1,325 au lieu de 1,20 / −0,80). | Erreur de la session, signalée dans l'arbitrage versé et dans la fiche ; la règle choisie (tangente au bord de voie) est appliquée. |
| 3 | ÉVITÉ | PAT-001, CA-020, CA-034 : ressorts nodaux, une classe de raideur par nœud (une seule maille POI1 par nœud). kx = ky écrits dans une seule `DISCRET` (k, k, 0) : aucune raideur perdue à un nœud commun. | 52 groupes de niveau, 10 classes, test qui le vérifie. |
| 4 | ÉVITÉ | DIAG-004 : `DIS_T` sans masse sous `PESANTEUR` arrête le calcul. | `M_T_D_N = 0` dès la sonde, aucune erreur. |
| 5 | ÉVITÉ | CA-029, PAT-003 : une pression définie par fonction est évaluée aux nœuds et déborde d'une demi-maille. | Empreintes de roue en réunions de mailles entières (bandes `CRIT_NOEUD="TOUS"`, maillage aligné à 0,05 m) ; aucune charge par fonction. |
| 6 | ÉVITÉ | CA-032, DIAG-001 : `LIAISON_SOLIDE` entre coque et poutre peut produire un pivot nul (DRZ fictif des coques, redondance avec un blocage). | Liaison barre-coque par nœuds partagés, aucune relation dualisée, DZ des pointes bloqué une seule fois : aucun pivot nul. |
| 7 | ÉVITÉ | CA-048, CA-028, CA-045 : poids par `PESANTEUR` et RHO ; `FORCE_COQUE` en FZ global ; normales orientées, `MXX > 0` tend la face du côté de la normale. | Convention de signe de la dalle fixée avant la comparaison (§ 2.3). |
| 8 | ÉVITÉ | DIAG-011 (révélé par la sonde S1, alarme `UTILITAI_4`) : `EFGE_NOEU` sur des éléments de repères différents. | `EFGE_NOEU` restreint à la dalle dans le générateur ; production sans alarme. |
| 9 | LACUNE | Rien dans la base sur la température des coques ni sur `MACRO_ELAS_MULT`. | Sonde S1 (critères écrits avant), constats CA-054 et CA-055, avec épreuve rejouée. |
| 10 | OUTIL | Le validateur de niveau B ne résout pas un tuple de concepts (`CHAR_MECA_GLOBAL=(CL,)`) et laisse toute la suite non confrontée. | Référence simple employée ; noté dans CA-055 ; test du générateur. Correction du validateur non faite (signalée). |
| 11 | NON ÉVITÉ | DIAG-010 (`JEVEUX_10`, `CREA_GROUP_NO` à plusieurs `GROUP_MA`) décrivait l'erreur, mais la base n'avait pas été consultée **par commande** (`DEFI_GROUP`) avant d'écrire le bloc. | Première exécution de production arrêtée ; correction du diagnostic appliquée, test ajouté. Leçon : consulter la base par commande pour chaque commande écrite, pas seulement par thème. |
| 12 | ÉVITÉ | DIAG-003 lu avant toute hypothèse sur `FACTOR_57` (maillage fin, 1,8 million de ddl) : redondance et mécanisme écartés d'abord. | Raffinement itératif `POSTTRAITEMENTS="FORCE"`, `RESI_RELA` inchangé pour la référence ; relâché à 1e-5, avec motif écrit, pour la seule variante POU_D_E. |
| 13 | ÉVITÉ | DIAG-007 (`FORCE_COQUE` sur un groupe non connexe) relu avant l'exécution : il porte sur `PRES` ; les empreintes et trottoirs non connexes en FZ/FX ne sont pas concernés (vérifié par les trois exécutions de convergence). | Aucun `VERI_NORM` nécessaire. |
| 14 | OUTIL | `controls.extra` déclaré au schéma mais appelé par aucune étape du pipeline. | Appelé par l'étape `controles`, test ajouté. |
| 15 | OUTIL | Le contrôle d'équilibre n'admettait les ressorts que dans une direction. | `SpringsSection.direction` accepte plusieurs composantes ; comportement à une direction inchangé (tests du quai). |
| 16 | OUTIL | L'écart relatif d'équilibre d'un cas de charge nulle (TE±) vaut NaN : ÉCHEC formel de CTL-005 et CTL-013, verdict D d'ensemble en échec, épreuves des patrons refusées. | Verdict non modifié après exécution ; lacune signalée (rapporter l'écart à la plus grande force interne). |
| 17 | OUTIL | Le contrôle des notes Word triait des NaN avec les valeurs du paquet et manquait des valeurs présentes ; il refusait « nan » affiché pour une source NaN. | Corrigé dans le tronc commun, deux tests. |
| 18 | OUTIL | Le paquet de résultats n'avait pas de section pour un contre-calcul. | Section `contre_calcul` et sa mention « Contre-calcul d'un modèle non validé » dans la note de résultats. |
| 19 | LACUNE | Le type « calcul externe non validé » n'existait pas dans `references_validation/`. | `reference_kind = calcul_externe_non_valide`, critère `contre_calcul`, jamais E ni promu, refusé à la promotion ; REF-015. |
| 20 | LACUNE | Aucune connaissance sur la singularité d'une plaque reliée à un pieu en un seul nœud. | Révélée par la suite de convergence ; CTL-014 (observé). |
| 21 | MANQUE | Moments des pieux (C3, C5) : écart inexpliqué, pistes listées ; le modèle source n'est pas disponible. | Rapporté « inexpliqué » (§ 3.4). |

## Bilan

- Interventions de MM : **1** (question unique sur E13 à E16, au début du lot).
- Erreurs évitées par la base : n° 3 à 8, 12, 13 (huit lignes ÉVITÉ).
- Erreur non évitée alors que la base la décrivait : n° 11 (DIAG-010).
- Exécutions en échec : 4 (FACTOR_57 au maillage fin de la convergence, JEVEUX_10 en production, FACTOR_57 deux fois sur la variante POU_D_E : avec `POSTTRAITEMENTS="FORCE"` seul, puis sur les cas thermiques) — classées au registre `rex`.
