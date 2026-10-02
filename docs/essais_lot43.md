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

(À compléter après exécution.)

## Résultats

(À compléter après exécution.)

## Verdict

(À compléter après exécution.)

## Limites

(À compléter après exécution.)
