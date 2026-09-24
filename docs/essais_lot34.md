# Lot 34 — Écart d'équilibre : charge appliquée ou lecture des réactions ?

Ce document fixe les critères **avant** toute exécution du lot. Le texte des
critères n'est jamais modifié après coup ; seules les sections « Résultats »
sont complétées.

## Étape 0

`aster-expert mcp-check` : 7 outils appelés sur un serveur neuf, identiques aux
outils du code (`mcp-check OK`, ~3 min : premier appel de `search_test_cases`
sur serveur froid, index construit à la volée). Les sept outils sont visibles
dans la session.

## Critère de l'étape 1 (charge assemblée contre charge intégrée)

Banc d'essai : quai réduit (maillage vérifié `20260923T135537-6993814e`).
Sonde : tous les degrés de liberté de tous les nœuds bloqués, sans
`LIAISON_SOLIDE` (redondante avec un blocage total), un cas de charge à la
fois ; `REAC_NODA` sommé sur `GEN_TOUS_NOEUDS`, composantes DX, DY, DZ. Avec
déplacements nuls, `REAC_NODA` = −(charge assemblée par Code_Aster).

Pour chaque cas (G, Q1, EAU_P, EAU_A) et chaque composante c ∈ {X, Y, Z} :

```
assemblée_c   = −Σ REAC_NODA_c            (Code_Aster)
intégrée_c    = écran_c + poutre_c [+ poids_c pour G]     (indépendante)
écart_c       = assemblée_c − intégrée_c
écart_rel_c   = écart_c / max(|intégrée_X|, |intégrée_Y|, |intégrée_Z|) du cas
```

- écran : intégrale de Gauss 2×2 par QUAD4 de `-p(z) n dA` sur les mailles de
  `ECRAN_POUSSEE` (`aster_expert.meshing.equilibrium`), maillage du quai réduit ;
- poutre : somme des `FORCE_NODALE` lue du `.comm` généré ;
- poids (G) : `expected_masses` × épaisseur/section × masse volumique × g
  (tubes, palplanches, tirants), avec `PESANTEUR` exclusivement sur ces trois
  groupes.

**Seuil : |écart_rel_c| ≤ 1e-6 sur les trois composantes → écart absent
(type b).** Une seule composante au-delà du seuil → écart présent (type a),
rapporté tel quel. Q3 et A sont lus à titre informatif (charges ponctuelles
écrites dans le `.comm`, comparées à la somme assemblée), sans verdict.

Si l'écart est présent : localisation en trois essais séparés (pression sur les
tubes seuls, pression sur les palplanches seules, charge de poutre seule), même
seuil.

## Critère de l'étape 2 (seulement si type b)

1. `REAC_NODA` selon DY sur les nœuds de `SYM_G`, `SYM_D`, `PIED_TUBES` (DY non
   bloqué) : |Σ| ≤ 1e-6 × |charge appliquée Y| du cas ; sinon, cause à établir.
2. Chaque nœud à ressort compté une fois ; Σk lue = Σk écrite (écart relatif ≤ 1e-9).
3. Décomposition terme à terme : ressorts d'argile, de marne, ancrages, réactions
   de blocage retenues, à côté de la charge appliquée ; le solde doit s'annuler à
   1e-6 près, sinon l'écart reste inexpliqué.

## Critère de l'étape 3 (pesanteur, cas G, verticale)

Résultante verticale attendue = poids calculé du maillage (tubes + palplanches +
tirants, `PESANTEUR`) + composante verticale de la poutre (`FORCE_NODALE`, FZ) +
composante verticale de la pression sur l'écran. Somme lue : `REAC_NODA` DZ sur
les groupes d'appui (`PIED_TUBES`) + ancrages (DZ bloqué) + `SYM_G`/`SYM_D`
(DZ non bloqué, attendu nul). Les tirants reprennent leur composante verticale
par les ancrages : force interne au système, vérifiée par la somme, pas
retranchée. **Seuil : écart relatif ≤ 1e-6.**

## Critère de l'étape 4

Après correction : écart d'équilibre ≤ 1e-6 dans X, Y, Z sur le quai réduit,
puis une exécution unique du modèle complet avec contrôles d'équilibre (X, Y,
Z), de symétrie (seuil 1e-6 du lot 33, inchangé) et de pesanteur. Aucun seuil
n'est modifié : un cas au-delà reste un ÉCHEC rapporté tel quel.

## Précisions consignées après les essais du quai réduit, avant l'exécution du modèle complet

Le texte des critères ci-dessus est inchangé : seuil 1e-6, trois directions,
même définition de l'écart relatif. Ce qui suit dit comment le critère est
appliqué au modèle complet, écrit avant son exécution :

1. **Charge appliquée de référence** (`applied`) : intégrale indépendante de la
   charge que le `.comm` applique -- profil spécifié par couche, aux points de
   Gauss (référence « spécifiée »), et règle d'évaluation aux nœuds que Code_Aster
   applique à `FORCE_COQUE/PRES` (référence « telle qu'évaluée »). Les deux sont
   rapportées. Une référence bâtie sur le tri de paires `(z, p)` (celle du lot 33)
   est un défaut, corrigé (`layered_profile`).
2. **Le modèle complet n'a pas de sonde** (une seule exécution) : sa charge
   appliquée est l'intégrale indépendante seule (`analyze_lot34_charge_assemblee.py
   -`), validée sur le quai réduit contre la charge assemblée par Code_Aster.
3. **Réactions** : seules les composantes réellement bloquées entrent dans la
   somme (`SYM_G`/`SYM_D` : DX ; `PIED_TUBES` : DZ ; `ANCRAGES` : DX, DY, DZ).
4. **Ressorts** : raideur effective par nœud ; un nœud partagé par deux bandes
   porte la somme des deux (classes communes).
5. **Pesanteur** : poids des tubes, palplanches et tirants calculé **sur le
   maillage** (aires QUAD4 et longueurs SEG2 du MED), comparé au poids analytique.
6. **Symétrie** : critère du lot 33, inchangé (1e-6, toutes les paires), avec les
   tables imprimées à 12 chiffres.
7. **Cas Q3 et A** : bilan calculé de la même façon, à titre informatif (sans
   verdict), comme au lot 33.

## Résultats

Tous les chiffres viennent des rapports JSON versionnés de
`data/examples/lot34_equilibre/rapports/` ; les tableaux complets sont générés par
`scripts/report_lot34.py` (`tableaux_lot34.md`). Exécutions : `rapports/executions.json`.

### Étape 1 -- charge assemblée par Code_Aster contre charge intégrée (quai réduit)

Sonde : tous les ddl de tous les nœuds bloqués, sans `LIAISON_SOLIDE`, `REAC_NODA`
sommé sur `GEN_TOUS_NOEUDS`. Écart relatif maximal des trois composantes, par cas :

| Cas | Référence du lot 33 (tri des paires), tables à 6 chiffres | Référence par couche, application d'origine | Après correction du générateur |
|---|---:|---:|---:|
| G | 2,00e-05 (ÉCART PRÉSENT) | 1,19e-03 (PRÉSENT) | 2,07e-12 (absent) |
| Q1 | 1,53e-02 (PRÉSENT) | 2,33e-04 (PRÉSENT) | 1,90e-15 (absent) |
| EAU_P | 2,41e-14 (absent) | 2,41e-14 (absent) | 2,41e-14 (absent) |
| EAU_A | 1,08e-15 (absent) | 1,08e-15 (absent) | 1,08e-15 (absent) |

**Verdict.** Selon la lettre du critère (seuil 1e-6), l'écart est **présent** sur G et Q1 :
type (a), rapporté tel quel. L'analyse montre qu'il a **deux origines distinctes**, dont
une seule est un écart de charge réellement appliquée :

1. *Défaut de la référence indépendante* (le mien, lot 33) : `profile_si` triait les
   paires `(z, p)` ; à une interface dont la couche supérieure est moins chargée, le tri
   permute les deux points et relie deux couches par une rampe fictive (Q1 : écart de 1,5 %
   à lui seul). Corrigé (`layered_profile`, testé). Ce n'est pas la charge de Code_Aster.
2. *Charge réellement appliquée* : Code_Aster évalue la fonction de `FORCE_COQUE/PRES`
   **aux nœuds** de chaque maille puis l'interpole. La marche de pression entre couches,
   écrite comme une rampe de 2 mm sur une arête de maille, est lue à mi-rampe aux nœuds de
   l'interface et déborde d'une demi-maille (G : 1,19e-3, Q1 : 2,33e-4 de la poussée). Fait
   établi par exécution, nœud par nœud (`REAC_NODA` reproduit à moins de 1 N à chaque nœud de
   palplanche), non documenté (U4.44.01 : « réel ou fonction »). L'hypothèse de la fiche
   (point 5 : « aucun point d'intégration à moins de 1 mm d'une arête ») ne s'applique pas à
   une évaluation aux nœuds.

Les cas d'eau (fonction continue) sont **sans écart de charge** : leur écart du lot 33
(−0,22 %) est donc de type (b).

Localisation en trois essais (écart en Y, N ; référence du lot 33 puis référence par couche) :

| Pression sur | Mailles | G | Q1 | EAU_P, EAU_A |
|---|---:|---:|---:|---|
| tubes seuls | 4 600 | −3 662 puis +29,9 | −15 333 puis +3,2 | nul (≤ 2 N, arrondi de la table) |
| palplanches seules | 830 | +3 552 puis +6 620 | −12 316 puis +428 | nul (≤ 2 N, arrondi de la table) |
| poutre et poids seuls | 0 | 0 | 0 | 0 |

La charge de poutre (décision 13) est exacte ; l'écart naît de la pression sur l'écran,
surtout sur les palplanches.

### Étapes 2 et 3 -- lecture de l'équilibre (quai réduit)

1. **Réactions sur composantes non bloquées.** `PIED_TUBES` : DY, DX nulles (≤ 1e-8 N).
   `SYM_G`/`SYM_D` : DY et DZ **non nulles** (cas EAU_A : +2,654e5 N chacun en DY, −2,619e5 N
   en DZ), alors que seul DX y est bloqué. Ce sont les forces de liaison de `LIAISON_SOLIDE`
   (multiplicateurs de la relation anneau/nœud de poutre, déduction) : la somme sur **tous**
   les nœuds égale la réaction des seuls ancrages (DY, EAU_A : +9,7917e5 N des deux côtés ;
   écart ≤ 4,4e-4 N sur les quatre cas, le résidu du solveur), elles s'annulent donc. Elles ne doivent pas entrer dans la somme : seules les
   composantes bloquées comptent (SYM : DX ; pied : DZ ; ancrages : DX, DY, DZ).
2. **Table combinée du lot 33.** `POST_RELEVE_T/RESULTANTE` sur les quatre groupes d'appui
   d'un seul coup (table `REACTIONS_<cas>`) ne vaut pas la somme des résultantes par groupe
   (quai réduit, G, DY : 7,578e5 N contre 1,262e6 N ; modèle complet : 3,231e6 N contre
   3,841e6 N, ancrages seuls 3,2096e6 N). Cause non établie ; cette table n'est plus lue.
3. **Ressorts.** Chaque nœud est compté une fois (2 651 nœuds, 2 694 couples classe/nœud) et
   Σk lu = Σk écrit (écart 0). Mais **43 nœuds** de la limite argile/marne (z = −18)
   portent, dans Code_Aster, **une seule** des deux raideurs écrites : `FORC_NODA` restreint
   aux `POI1` donne k effectif = k marne (rapports 0,70 et 0,08 du k écrit), soit −16,2 kN
   sur G (Σ FORC_NODA −4 794 309 N contre Σ k·DY −4 810 480 N). Cause : `CREA_POI1` ne crée
   **qu'une maille ponctuelle par nœud** (2 651 mailles `POI1`) et la seconde occurrence de
   `DISCRET` écrase la première (règle de surcharge, U4.42.01/U1.03.00).
4. **Décomposition terme à terme** du bilan Y du lot 33 sur le quai réduit
   (`decomposition_ecart_lot33_quai_reduit.json`, reproduit les 0,64 % (G) et 1,93 % (Q1)
   que le lot 33 avait rapportés) :

| Cas | Écart type lot 33 (N) | référence (tri) | règle nodale | table combinée | ressorts partagés |
|---|---:|---:|---:|---:|---:|
| G | −36 088 | +6 760 | −6 650 | **−52 370** | +16 172 |
| Q1 | +34 941 | +28 080 | −428 | +3 894 | +3 394 |
| EAU_P | −31 193 | 0 | 0 | **−34 529** | +3 335 |
| EAU_A | −71 112 | 0 | 0 | **−78 907** | +7 796 |

La lecture par la table combinée domine ; viennent ensuite les ressorts partagés, puis les
deux effets de charge. Aucun des termes n'est un défaut de Code_Aster.

5. **Pesanteur (étape 3).** Cas G, direction Z, quai réduit : voir le tableau du modèle
   complet ci-dessous (même contrôle, écart 1,65e-13 au quai réduit).

### Cause établie et essai qui la démontre

Quatre causes, chacune démontrée par une exécution et corrigée :

| Cause | Essai qui la démontre | Correction |
|---|---|---|
| Référence indépendante fausse (tri des paires) | sonde : Q1 écart 1,5 % ; profil par couche : 2,3e-4 | `layered_profile` |
| Évaluation aux nœuds de la fonction de pression | `REAC_NODA` nœud par nœud, palplanches : < 1 N par nœud | une occurrence de `FORCE_COQUE` par couche (`comm.layered_pressure_load_block`) ; sonde : 2e-12 |
| 43 nœuds à une seule raideur (`CREA_POI1` + surcharge) | `FORC_NODA` sur les `POI1` contre k·DY : 43 nœuds → 0 | classes communes (`springs._combined_classes`, `check_spring_coverage`) |
| Lecture : composantes libres et table combinée | Σ tous nœuds = ancrages ; bilan par composante bloquée | `scripts/analyze_lot34_equilibre.py` |

### Étape 4 -- quai réduit puis modèle complet

Quai réduit, modèle corrigé (`equilibre_quai_reduit_v3.json`) : écart relatif ≤ 1,03e-10
(Y), ≤ 3,8e-13 (X), ≤ 5,4e-13 (Z) sur G, Q1, EAU_P, EAU_A ; Q3 et A (informatifs) ≤ 1,4e-10.
Symétrie ≤ 2,0e-11 (5 102 paires).

**Modèle complet, exécution unique** (`data/processed/runs/20260924T160321-dca7bfa8/`,
`DIAGNOSTIC JOB : OK`, 208,3 s, « aucune alarme », aucune ligne `<F>`/`<E>`/`<S>`) :

| Cas | X | Y | Z | Verdict (seuil 1e-6) |
|---|---:|---:|---:|---|
| G | 3,87e-13 | −5,00e-11 | −1,07e-12 | **RÉUSSI** |
| Q1 | 4,53e-12 | −8,76e-11 | −7,35e-13 | **RÉUSSI** |
| EAU_P | −1,53e-12 | −5,13e-11 | −3,66e-13 | **RÉUSSI** |
| EAU_A | −8,37e-13 | −8,01e-11 | −7,56e-13 | **RÉUSSI** |
| Q3 (informatif) | 5,08e-12 | −2,28e-10 | 1,04e-12 | -- |
| A (informatif) | −1,90e-11 | 2,14e-10 | 0 | -- |

Symétrie (20 057 paires, 40 114 nœuds, seuil 1e-6) : pire écart relatif 5,70e-11 (Q1),
soit 4 ordres de grandeur sous le seuil ; le 6,07e-7 du lot 33 (Q1) était l'arrondi à
6 chiffres des tables. Pesanteur, cas G, Z : poids maillage −1 386 344,209 N (= analytique à
6,5e-13), poutre −1 785 420 N, pression sur l'écran ≈ 0 ; résultante −3 171 764,209 N ;
réactions bloquées +3 171 764,209 N (ancrages −1 128 152 N, pied des tubes +4 299 916 N) ;
bilan −2,4e-5 N (1,07e-12). La composante verticale des tirants est reprise par les
ancrages : force interne, vérifiée par la somme, non retranchée. Σk lu = Σk écrit, 10 433
nœuds de ressort, écart 0.

**Niveau atteint : C** (exécuté jusqu'à `FIN`) **avec contrôles D** : équilibre X, Y, Z,
symétrie et pesanteur tous sous 1e-6 ; **aucun niveau E** (aucune comparaison à une référence
validée).

### Coût

Quai réduit : **15 exécutions** sur les 20 autorisées, 1 144,9 s cumulées (dont 2 échecs
`<F> <MESH3_99>` de 19,9 s et 19,3 s, expliqués plus bas). Modèle complet : **1 exécution**,
208,3 s. Total 1 353,2 s.

### Limites et points non couverts

- **Modèle physique modifié, à connaître.** Deux corrections changent le modèle, dans le sens
  de la fiche : (i) 43 nœuds du quai réduit et 169 du modèle complet (12 classes communes
  dans chaque cas) portent maintenant la somme des raideurs des deux bandes au lieu de la seule marne ;
  (ii) la poussée G/Q1 est appliquée par couche, sans le débordement d'une demi-maille aux
  interfaces (G : 0,12 %, Q1 : 0,02 % de la poussée). Les déplacements et efforts du modèle
  complet du lot 32/33 ne sont pas ceux de ce lot : ne pas les comparer.
- **Le finding du point 5 de la fiche** (doublement à 1 mm « sûr » car aucun point
  d'intégration à moins de 1 mm d'une arête) est contredit par l'évaluation aux nœuds ; la
  fiche n'est pas modifiée par ce lot (aucune décision pratique prise ni complétée) --
  à enregistrer par MM.
- **Couches non alignées sur le maillage.** La charge par couche suppose que les rangées de
  mailles s'arrêtent aux cotes d'interface (vrai ici : cotes imposées, multiples de 0,25 m).
  Une maille à cheval sur deux couches ne serait dans aucune bande et ne recevrait aucune
  pression : l'équilibre (`analyze_lot34_equilibre.py`) le signalerait, le générateur non.
- **`VERI_NORM="NON"`** sur les occurrences par couche (`<F> <MESH3_99>` sinon : la couche de
  marne ne porte que les trois tubes, non connexes). L'orientation des normales reste
  contrôlée par les charges d'eau, qui portent sur l'écran entier.
- **Table `REACTIONS_<cas>`** (combinée) toujours écrite dans le `.comm` exécuté du modèle
  complet : sa valeur est fausse, à retirer du générateur au prochain lot (retirée ici, le
  `.comm` déposé n'aurait plus été celui qui a été exécuté).
- **Cause du comportement de `RESULTANTE` sur plusieurs groupes** : non établie.
- Le mécanisme exact des forces de liaison sur `SYM_G`/`SYM_D` (multiplicateurs de
  `LIAISON_SOLIDE`) est une déduction : la somme sur tous les nœuds les annule, sans que le
  détail nœud par nœud ait été relevé sur le modèle complet.
- Les anciens `.comm` de sonde (`sonde_pression_*.comm`, `sonde_blocage_total` d'origine) ne
  sont pas régénérables par le générateur actuel : ils sont conservés tels qu'exécutés, avec
  les rapports `initiale_*`/`corrigee_*`.
- Non testé : maillages dont les rangées ne sont pas alignées sur les interfaces ; le
  raffinement du maillage (critère de convergence) -- l'équilibre est exact à la précision du
  solveur à chaque maillage, il ne teste pas l'erreur de discrétisation.

