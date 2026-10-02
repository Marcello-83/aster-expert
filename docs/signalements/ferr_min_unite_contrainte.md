# Signalement : `FERR_MIN='EC2'` de `CALC_FERRAILLAGE` dépend de `UNITE_CONTRAINTE`

**Statut.** Brouillon factuel rédigé au lot 45, à l'attention de MM, qui décide de le
publier ou non (forum Code_Aster, tracker). Rien n'est publié par la session. Version
documentaire et exécutée : Code_Aster 17.4.0, image `simvia/code_aster`, digest
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.

## Observation

En 1D (`TYPE_STRUCTURE='1D'`, `CODIFICATION='EC2'`), le ferraillage minimal demandé par
`FERR_MIN='EC2'` n'est pas le même selon `UNITE_CONTRAINTE`, pour un modèle physiquement
identique (mêmes grandeurs, exprimées en Pa et m, ou en MPa et mm). Le témoin sans
`FERR_MIN` donne le même résultat dans les deux unités ; seul le minimum diffère.

La documentation U4.81.42 (opérande `UNITE_CONTRAINTE`) dit que le mot-clé « définit à la
fois l'unité de contraintes utilisée et l'unité de longueur » (`'MPa'` : millimètre ;
`'Pa'` : mètre) et qu'il faut veiller à ce qu'elle soit celle du calcul. Les deux cas
ci-dessous respectent cette consigne. La section de la documentation relative à `FERR_MIN`
n'a pas été relue pour ce signalement.

## Cas reproductibles (versionnés)

Section rectangulaire de la poutre de couronnement de l'ouvrage d'essai : HY = 2,50 m,
HZ = 1,40 m, C35/45 (`FCK` = 35 MPa), B500B (`FYK` = 500 MPa), distance parement–axe
0,10 m sur les quatre faces, `GAMMA_C` = 1,5, `GAMMA_S` = 1,15, `ALPHA_CC` = 1,0,
`TYPE_COMB='ELU'`. Quatre instants : un moment MFZ de 1 MN·m avec et sans `FERR_MIN`,
un état nul avec `FERR_MIN`, un effort tranchant VY de 4 MN avec `FERR_MIN`.

- `data/examples/lot39_essais/fermin/fermin.comm` : `UNITE_CONTRAINTE='Pa'`, longueurs en
  m, efforts en N et N·m, `FYK=500000000.0`, `FCK=35000000.0`.
- `data/examples/lot39_essais/fermin_mpa/fermin_mpa.comm` : même cas en
  `UNITE_CONTRAINTE='MPa'`, longueurs en mm, efforts en N et N·mm, `FYK=500.0`,
  `FCK=35.0`.

Chaque dossier contient le `.mail` et le `.export` du cas. Exécution (VM ou Cloud, image
ci-dessus) :

```
aster-expert run data/examples/lot39_essais/fermin/fermin.comm
aster-expert run data/examples/lot39_essais/fermin_mpa/fermin_mpa.comm
```

Les listings extraits des exécutions du lot 39 (28 septembre 2026, `DIAGNOSTIC JOB : OK`,
9,6 s et 10,1 s) sont dans `data/examples/lot39_essais/rapports/mess_fermin_extrait.txt` et
`mess_fermin_mpa_extrait.txt`.

## Résultats (une ligne de `FERR_ELEM`, aires converties en mm²)

| Grandeur | `'Pa'` (m) | `'MPa'` (mm) | Formule EN 1992-1-1, 9.2.1.1 |
| --- | --- | --- | --- |
| Témoin sans `FERR_MIN` : AYS | 960,8935 mm² (9,608935e-04 m²) | 960,8935 mm² | sans objet (flexion) |
| Avec `FERR_MIN`, sans effort : AYS = AYI | 4 368,0 mm² (4,368000e-03 m²) | 5 608,446 mm² | 0,26 fctm/fyk b d = 5 608,446 mm² |
| Avec `FERR_MIN`, sans effort : AZS = AZI | 4 225,0 mm² (4,225000e-03 m²) | 5 424,837 mm² | 0,26 fctm/fyk b d = 5 424,837 mm² |
| Avec `FERR_MIN`, VY seul : AST | 2,366432e-06 m²/m | 2,366432 mm²/mm (soit 2,366432e-03 m²/m) | ρw,min b_w, ρw,min = 0,08 √fck/fyk |

Avec fctm = 0,30 fck^(2/3) = 3,20996 MPa, la formule 9.2.1.1 donne 5 608,446 mm² et
5 424,837 mm² : valeurs obtenues en `'MPa'` (à 1e-14 relatif, lot 39). En `'Pa'`,
4 368,0 mm² = 0,0013 · 1 400 · 2 400 mm² et 4 225,0 mm² = 0,0013 · 2 500 · 1 300 mm² :
c'est le plancher 0,0013 b d de la formule, et le minimum transversal est 1 000 fois plus
faible qu'en `'MPa'` (une fois ramené à la même unité). Aucune alarme n'est émise dans les
deux exécutions.

## Ce qui est établi, ce qui ne l'est pas

- **Établi** (exécution, 17.4.0, deux cas) : le résultat de `FERR_MIN='EC2'` n'est pas
  invariant par changement cohérent d'unités ; la valeur correcte (formule 9.2.1.1) est
  celle de `'MPa'` ; aucune alarme.
- **Hypothèse non vérifiée** : la formule du minimum serait écrite pour des contraintes en
  MPa, y compris pour fctm et √fck (fctm calculé à partir de `FCK` en Pa serait 100 fois
  trop faible, donc le plancher 0,0013 l'emporte ; √fck/fyk en Pa serait 1 000 fois trop
  faible). Les sources d'implémentation n'ont pas été lues.
- **Non testé** : `FERR_MIN='VALE_MIN'` ; le 2D (le minimum `FERR_MIN='EC2'` n'a pas été
  exécuté en 2D) ; `FERR_MIN_FISS` (refusé pour les poutres en 17.4.0 :
  `<F> <CALCULEL7_40>`, constat CA-041, sans lien avec les unités).
- La documentation du mot-clé écrit `'BAEL91'` là où le catalogue 17.4.0 propose `'EC2'`
  (constat CA-041).

## Conséquence pour l'outil

Le générateur ne demande jamais `FERR_MIN` (minima calculés hors Code_Aster) ; il refuse,
depuis le lot 45, tout `CALC_FERRAILLAGE` qui demanderait `FERR_MIN` avec une autre unité
que `'MPa'` (`aster_expert.ferraillage.unites`, test
`tests/unit/test_ferraillage_unites.py`, qui échoue sur `fermin.comm` et accepte
`fermin_mpa.comm`).
