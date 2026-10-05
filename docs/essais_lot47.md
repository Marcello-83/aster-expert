# Essais du lot 47 — contre-calcul d'une estacade sur pieux (`estacade_pieux_01`)

**Contre-calcul d'un modèle non validé.** Le modèle source (Robot, avant-projet)
n'est pas validé : sa comparaison n'est jamais un niveau E. Un écart ne désigne
pas d'avance le logiciel fautif.

Ce rapport suit `docs/modele_rapport_essai.md`. Chaque section « Critère » est
écrite et commitée **avant** l'exécution qu'elle juge ; elle n'est pas modifiée
ensuite (une erreur s'y corrige dans une section datée « Correction du critère »).
Version de Code_Aster : 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

## 1. Sonde S1 — commandes que la base ne couvre pas

### 1.1 Objet

La base de connaissances ne dit rien de la température sur des coques ni de
`MACRO_ELAS_MULT` (consultation du 2026-10-05 : `search_connaissances` « température
dilatation AFFE_VARC » et `command=MACRO_ELAS_MULT`, aucun résultat). La sonde
`projets/estacade_pieux_01/references/cas/sonde_lot47.comm` (générée par
`projets/estacade_pieux_01/scripts/sonde_lot47.py`, maillage ASTER natif sans
Salomé) établit, avant d'écrire le générateur de l'estacade :

- T1 : une température uniforme portée par une plaque DKT (`CREA_RESU/PREP_VARC`
  d'un champ `TEMP_MIL`/`TEMP_INF`/`TEMP_SUP`, syntaxe du cas test `hsls01a`) et par
  une poutre POU_D_T qui partage ses nœuds (`CHAM_GD` de composante `TEMP`, syntaxe
  du cas test `ssll12a`), deux occurrences d'`AFFE_VARC`, donne la dilatation libre ;
- T2 : `MACRO_ELAS_MULT` (une factorisation, quatre `CAS_CHARGE`) avec `PESANTEUR` sur
  un modèle qui porte un ressort `DIS_T` de masse nulle (DIAG-004), `FORCE_COQUE` FZ
  et FX, `FORCE_ARETE` FZ sur une arête SEG2 de DKT : chaque résultante égale la
  charge déclarée ;
- la section `CERCLE` du tube équivalent (R, EP calculés pour que A et I égalent
  ceux du tableau B2) reproduit l'aire de B2 (poids du pieu).

Niveau visé : C, et D pour les grandeurs ci-dessous.

### 1.2 Critère de réussite (écrit avant l'exécution)

Valeurs attendues calculées par le script, avant l'exécution :
`projets/estacade_pieux_01/references/sonde_lot47_attendus.json`.

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| T1 : DX du nœud Q (x = 1,0) | α ΔT × 1,0 = 2,75e-4 m | exacte (dilatation libre, isostatique) | 1e-6 relatif |
| T1 : DY(y = 0,6) − DY(y = 0) à x = 0 | α ΔT × 0,6 = 1,65e-4 m | exacte | 1e-6 relatif |
| T1 : NXX, NYY de la plaque (`EFGE_ELNO`) | 0 | exacte | ≤ 1e-6 × E·α·ΔT·e (= 3,74 N/m) en valeur absolue |
| T1 : N du chevêtre (`EFGE_ELNO`) | 0 | exacte | ≤ 1e-6 × E·α·ΔT·A (= 10,1 N) en valeur absolue |
| T1 : résultante des réactions | 0 | exacte | ≤ 1e-6 × 10,1 N |
| T2 : PP, résultante DZ des réactions | +24 596,605 N (plaque 6 000, chevêtre 16 200, pieu 2 396,605) | exacte | 1e-6 relatif |
| T2 : G2, résultante DZ | +4 848 N | exacte | 1e-6 relatif |
| T2 : FR, résultante DX | −2 442 N | exacte | 1e-6 relatif |
| T2 : GC (`FORCE_ARETE`), résultante DZ | +500 N | exacte | 1e-6 relatif |

Les réactions s'opposent à la charge (signe inverse de la charge). Toute autre
issue est un échec, rapporté tel quel ; une erreur `<F>` est un échec de la sonde,
classé au registre `rex` du projet.
