# Essais du lot 43 — dalle appuyée DALLE-APPUYEE-01

## Objet

Second ouvrage du dépôt (`projets/dalle_appuyee_01/`), mené avec les seuls moyens de
l'outil (mesure d'autonomie, consigne `docs/lots/lot43_consigne.md`). Dalle en béton
armé C30/37 de 6,00 m (X) × 4,00 m (Y) × 0,30 m, appui bilatéral sur les quatre
bords, DKT, élasticité linéaire non fissurée (fiche arbitrée
`fiche/hypotheses_dalle_arbitree.json`, arbitrage `arbitrage_dalle_appuyee_01_v1` et
son complément ELS). Cas G (poids propre, 25 kN/m³) et Q (10 kPa), combinaisons EN
1990 (catégorie E), ferraillage 2D par `CALC_FERRAILLAGE`. Code_Aster 17.4.0 (image
`simvia/code_aster:17.4.0`, digest
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`).

Niveau visé : **E** pour la flèche et les moments au centre (comparaison à la solution
exacte de Kirchhoff), **D** pour l'équilibre, la symétrie et le ferraillage.

## Référence (calculée avant exécution)

`projets/dalle_appuyee_01/scripts/reference_navier_lot43.py` →
`projets/dalle_appuyee_01/references/navier_lot43.json`. Série de Navier au centre
(x = 3, y = 2), D = E h³ / (12 (1 − ν²)) = 77 343 750 N·m, E = 33 000 MPa, ν = 0,2.
Nombre de termes : l'ordre de troncature (m, n impairs ≤ N) est doublé jusqu'à ce que
w, Mx et My varient de moins de 1e-10 en relatif ; atteint à N = 8191, soit
4096² = 16 777 216 termes (à chaque doublement, l'écart des moments est divisé par
environ 8). Contrôle indépendant : la série de Lévy redonne la flèche à 1,0e-14 (G) et
1,1e-14 (Q) près. Convention : w > 0 dans le sens de la charge, Mx et My > 0 quand ils
tendent la face inférieure.

| Cas | q (Pa) | w (m) | Mx (N·m/m) | My (N·m/m) |
| --- | --- | --- | --- | --- |
| G | 7 500 | 1,917429853e-04 | 5 108,061864 | 9 403,017545 |
| Q | 10 000 | 2,556573137e-04 | 6 810,749152 | 12 537,35673 |

## Critère de réussite (écrit avant l'exécution)

Maillages : la suite de la section B de l'arbitrage, tailles 0,50 / 0,25 / 0,125 m
(12×8, 24×16, 48×32 QUAD4), chacun vérifié par `mesh check` contre ses invariants
analytiques (`maillage/invariants_h0p500.yaml`, `h0p250`, `h0p125`). Correspondance
Code_Aster → référence : w = −DZ au nœud `CENTRE` ; Mx = −MXX et My = −MYY
(`EFGE_NOEU` au nœud `CENTRE`). Cette correspondance de signe est une **déduction**
de CA-045 (`MXX > 0` tend la face du côté de la normale ; normales orientées +Z par
`ORIE_NORM_COQUE`) : elle est contrôlée par le critère E0, pas supposée.

### Niveau E (flèche et moments au centre, cas G et Q séparément)

| N° | Grandeur | Attendu | Nature | Seuil de réussite |
| --- | --- | --- | --- | --- |
| E0 | signes au centre, 3 maillages, G et Q | DZ < 0, MXX < 0, MYY < 0 | exacte (signe) | les trois signes, partout |
| E1 | w, Mx, My au centre | Navier (tableau ci-dessus) | sensible à la discrétisation | \|erreur relative\| strictement décroissante de 0,50 à 0,25 puis à 0,125 m, pour chacune des 6 grandeurs |
| E2 | w, Mx, My au centre, maillage 0,125 m | Navier | sensible à la discrétisation | \|erreur relative\| ≤ 1 % pour chacune des 6 grandeurs |

E3 (informatif, sans verdict) : écart entre `EFGE_ELNO` des quatre mailles voisines du
centre et `EFGE_NOEU` au centre (écart de lissage, section B).

### Niveau D (contrôles sur le maillage 0,125 m, et sur les deux autres pour mémoire)

| N° | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| D1 | équilibre X, Y, Z de chaque cas (tronc commun, composantes bloquées seulement) | 0 | exacte | ≤ 1e-6 relatif à la charge |
| D2 | résultante appliquée de G | −180,0 kN (MM) | exacte | ≤ 1e-6 relatif |
| D3 | résultante appliquée de Q | −240,0 kN (MM) | exacte | ≤ 1e-6 relatif |
| D4 | symétrie des déplacements, plans X = 3 et Y = 2, G et Q | image miroir | exacte (maillage symétrique) | ≤ 1e-6 relatif au déplacement maximal |
| D5 | MXY au nœud `CENTRE` (EFGE_NOEU), G et Q | 0 | exacte (symétrie) | \|MXY\| ≤ 1e-6 × max(\|MXX\|, \|MYY\|) |
| D6 | linéarité : w(G)/w(Q) et M(G)/M(Q) au centre | 0,75 | exacte | ≤ 1e-6 relatif |

D7 (informatif, sans verdict, P4) : réactions nodales des coins (soulèvement empêché),
de signe opposé aux réactions des bords, relevées et commentées.

### Ferraillage 2D

| N° | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| F1 | densités ELU des 4 mailles voisines du centre contre le module `aster_expert.rebar` (bande de 1 m par direction, MXY ignoré) évalué à la moyenne des efforts aux nœuds de la maille | égalité | **exploratoire** : la réduction par maille de `CALC_FERRAILLAGE` n'est pas documentée et MXY n'y est pas nul | rapporté tel quel, sans verdict ; établit (ou non) un constat |
| F2 | densité ELU au centre (DNSXI, DNSYI) : moyenne des 4 mailles voisines contre le calcul manuel au nœud `CENTRE` (EFGE_NOEU, MXY = 0 par symétrie : deux flexions simples) | égalité à la limite | sensible à la discrétisation | \|écart relatif\| strictement décroissant de 0,50 à 0,25 puis à 0,125 m, pour DNSXI et DNSYI |
| F3 | calcul manuel au centre : module `aster_expert.rebar` contre la formule fermée du bloc rectangulaire (μ, α, z) | égalité | exacte | ≤ 1e-6 relatif |
| F4 | sensibilité (MM) : densités ELS caractéristiques avec SIGC_*_ELS = 18 MPa et = 1 000 MPa | identiques | exacte | toutes les densités égales à 1e-6 relatif (≤ 1e-12 m²/m en absolu près de zéro) ; sinon, la limite est active et c'est rapporté |

Toute autre issue est un échec, rapporté tel quel.

## Modèle et exécution

- Générateur : `projets/dalle_appuyee_01/generation.py` (fiche arbitrée et données) ;
  `.comm` du maillage fin validé au niveau B (107/107 commandes, 0 erreur).
- Chaîne projet (`aster-expert projet dalle_appuyee_01 maillage generer valider
  executer controles ferraillage`) : maillage 48×32, 48/48 invariants ; exécution
  `completed_ok`, 14,3 s, 0 alarme (`data/processed/runs/20261002T085726-378a7180`).
- Suite de convergence (`scripts/niveau_e_lot43.py`, commit de départ 4093f12, arbre
  modifié par les scripts d'analyse et `config/validation.yaml`) : trois maillages
  Salomé, chacun 48/48 invariants, trois exécutions `completed_ok`, 0 alarme
  (9,5 s, 9,8 s, 10,4 s). Cas versionnés : `projets/dalle_appuyee_01/references/cas/`
  (`.comm`, `.mmed`, `.export`, extrait de listing). Valeurs lues et verdicts :
  `projets/dalle_appuyee_01/references/niveau_e_lot43.json`.

## Résultats

### Niveau E — centre de la dalle

| Maillage | Cas | w (m) | Mx (N·m/m) | My (N·m/m) | err. w | err. Mx | err. My |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12×8 | G | 1,910985e-04 | 5 112,49 | 9 482,22 | −3,36e-03 | +8,68e-04 | +8,42e-03 |
| 24×16 | G | 1,915848e-04 | 5 109,20 | 9 422,54 | −8,25e-04 | +2,22e-04 | +2,08e-03 |
| 48×32 | G | 1,917036e-04 | 5 108,35 | 9 407,88 | −2,05e-04 | +5,58e-05 | +5,17e-04 |
| 12×8 | Q | 2,547981e-04 | 6 816,66 | 12 642,96 | −3,36e-03 | +8,68e-04 | +8,42e-03 |
| 24×16 | Q | 2,554463e-04 | 6 812,26 | 12 563,38 | −8,25e-04 | +2,22e-04 | +2,08e-03 |
| 48×32 | Q | 2,556048e-04 | 6 811,13 | 12 543,84 | −2,05e-04 | +5,58e-05 | +5,17e-04 |

L'erreur est divisée par 4,07 à 4,06 à chaque raffinement (convergence d'ordre 2).
Signes : DZ, MXX, MYY < 0 au centre dans les six calculs. E3 (informatif) : sur 48×32,
`EFGE_ELNO` des quatre mailles voisines au nœud central coïncide avec `EFGE_NOEU` à
la précision d'impression (MXX = −5 108,346847 pour G dans les quatre mailles) ; MXY y
vaut au plus 2,5e-9 N·m/m.

### Niveau D

- D1 : équilibre G et Q, écart 8,3e-12 en Z, 0 en X et Y (tronc commun,
  `resultats/controles/controles_d.md`).
- D2 et D3 : résultantes reprises par les appuis 180 000,0 N et 240 000,0 N (somme sur
  tous les nœuds) ; charges attendues 180,0 et 240,0 kN (MM), calculées identiquement.
- D4 : symétrie X = 3 et Y = 2, 808 paires par plan, écart relatif maximal 5,2e-13 (G)
  et 3,9e-13 (Q).
- D5 : |MXY| au centre / max(|MXX|, |MYY|) = 1,7e-13 (G), 1,6e-13 (Q).
- D6 : w(G)/w(Q) = 0,75 exactement (écart 0) ; MXX 3,9e-13 ; MYY 6,4e-13.
- D7 (informatif) : réaction de chaque coin −11 608,0 N (G) et −15 477,4 N (Q), dirigée
  vers le bas, alors que les autres nœuds des bords portent +226 432 N (G) au total (180 000 + 4 × 11 608) : c'est la force de
  coin de la plaque de Kirchhoff retenue contre le soulèvement (hypothèse de Navier,
  P4). Contrôle de lecture (déduction) : MXY au coin (0, 0) vaut 7 807,4 N·m/m sous Q
  (`EFGE_NOEU`), et 2·MXY = 15 614,8 N, à 0,9 % de la réaction de coin du maillage fin.
- Contrôle complémentaire (ajouté après exécution, hors critère) : la combinaison ELU
  au centre vaut 1,35 G + 1,5 Q à 4e-13 près (MXX et MYY, trois maillages).

### Ferraillage 2D (maillage 48×32, `resultats/ferraillage/ferraillage_DALLE.md`)

| Combinaison | DNSXI | DNSXS | DNSYI | DNSYS |
| --- | --- | --- | --- | --- |
| ELU fondamentale (1,35 G + 1,5 Q) | 1,774 | 1,627 | 2,906 | 1,942 |
| ELS caractéristique (G + Q) | 1,607 | 1,444 | 2,372 | 1,711 |
| ELS quasi permanente (G + 0,8 Q) | 1,457 | 1,221 | 2,056 | 1,544 |

(maxima sur les mailles, cm²/m ; « S » = dessus, CA-045.) Minimum EN 1992-1-1 (d =
0,252 m) : 9.2.1.1 → 3,80 cm²/m, 7.3.2 (kc = 0,4, k = 1, Act = b·h/2) → 3,48 cm²/m ;
**le minimum de 3,80 cm²/m gouverne dans les deux directions et sur les deux faces**.
Les maxima de la face supérieure (DNSXS, DNSYS) sont aux coins (MXY = 7 807 N·m/m sous
Q au coin (0, 0)) : armatures de coin (9.3.1.3) signalées, non calculées (P6).

- F1 (exploratoire) : 0/4 mailles reproduites à 1e-6 par le module évalué à la moyenne
  des nœuds (écart 3,2e-4), ni à un nœud (1,7e-3 au mieux) ; MXY aux nœuds non
  centraux de ces mailles vaut 43 N·m/m. La réduction par maille reste non établie.
- F2 : écart entre la moyenne des 4 mailles voisines et le calcul manuel au nœud
  `CENTRE` : DNSXI 1,86e-2 → 5,83e-3 → 1,93e-3 ; DNSYI 2,98e-2 → 7,69e-3 → 2,38e-3.
  Au maillage fin : 1,5695 contre 1,5726 cm²/m (X) et 2,9062 contre 2,9131 cm²/m (Y).
- F3 : module `aster_expert.rebar` contre formule fermée du bloc rectangulaire au
  centre : 3,7e-16.
- F4 : densités ELS caractéristiques avec SIGC_*_ELS = 18 MPa et 1 000 MPa : **elles
  diffèrent** (4 124 des 6 144 valeurs du maillage fin, y compris dans des mailles
  peu sollicitées ; écart relatif maximal 1,0, une densité nulle d'un côté). Au centre,
  DNSYI = 2,372e-4 (18 MPa) et 2,392e-4 m²/m (1 000 MPa) ; le pivot acier de R7.04.05,
  où σc,lim se simplifie, refait par `aster_expert.rebar.serviceability.design_els`,
  donne 2,294e-4 m²/m pour les deux valeurs (constat CA-052, rejoué).

## Verdict

| N° | Verdict |
| --- | --- |
| E0 | réussi |
| E1 | réussi (6/6 grandeurs, deux raffinements) |
| E2 | réussi (écart maximal 5,2e-4 ≤ 1e-2) |
| D1 à D6 | réussis |
| F2 | réussi |
| F3 | réussi |
| F4 | **échec** : les densités dépendent de SIGC_*_ELS. La lecture prévue par le critère (« la limite est active ») est contredite par les données : la limite de 18 MPa n'est pas atteinte dans les mailles peu sollicitées où les densités changent aussi ; c'est le paramètre lui-même qui intervient (CA-052). |

**Niveau atteint : E** pour la flèche et les moments au centre (cas G et Q, Navier) ;
**D** pour l'équilibre, la symétrie et les combinaisons ; ferraillage : C avec
contrôles D (F2, F3), et un échec F4 rapporté tel quel.

## Lecture

- Fait : DKT reproduit la plaque de Kirchhoff avec une erreur d'ordre 2 en h ; sur
  48×32, l'écart à Navier est de 0,02 % (flèche) et 0,05 % (moment de la petite portée).
- Fait : la correspondance de signes déduite de CA-045 (normales +Z) est confirmée.
- Fait : le ferraillage de la dalle est gouverné par le minimum de l'EN 1992-1-1
  (3,80 cm²/m), au-dessus de tous les besoins ELU et ELS.
- Déduction : la dépendance des densités ELS 2D à SIGC_*_ELS (F4) est de la même
  famille que les écarts ELS 1D inexpliqués de CA-044 ; elle ne change rien ici
  (l'ELS ne gouverne pas) mais interdit de traiter SIGC_*_ELS comme une limite neutre.
- Rappel (P2) : **les flèches sont instantanées et non fissurées** ; la flèche à long
  terme (fluage, fissuration, EC2 7.4.3) est hors périmètre.

## Limites

- Appui bilatéral (coins retenus) ; l'appui unilatéral n'est pas étudié.
- Sensibilité DST non faite (hors périmètre, P1).
- Réduction par maille de `CALC_FERRAILLAGE` en 2D non établie (F1) ; contre-vérification
  au centre seulement ; armatures de coin non calculées.
- Ferraillage ELS 2D : écart au pivot acier et dépendance à SIGC_*_ELS non expliqués.
- Aucun MED de résultats écrit (les tables du listing suffisent au contrôle) : pas de
  vue graphique.
- Les articles d'Eurocode sont ceux fournis par MM, non vérifiés par l'outil.
