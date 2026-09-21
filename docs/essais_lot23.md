# Lot 23 — Post-traitement sous `ELAS_COQUE`

Essais d'exécution synthétiques (`aster-expert run`), aucun fichier de MM lu.
Code_Aster 17.4.0, image
`sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
HEAD au moment des exécutions : `16c91ff` (arbre modifié : les cas n'étaient pas
commités ; l'empreinte `case_sha256` de chaque source fixe leurs octets).
Cas produits par `scripts/build_lot23_essais.py`, résultats extraits des `.mess`
versionnés (`data/examples/lot23_essais/mess/`) par
`scripts/analyze_lot23_essais.py` → `analyse.json`.

Chaîne : validation B (`aster-expert validate`, 100 % des commandes vérifiées, 0
erreur pour les 7 cas) → exécution → `.mess`. **Aucune alarme** dans les 7 `.mess`
(« aucune alarme », aucune balise `<A>`). Niveaux : C = exécuté jusqu'à `FIN`,
D = comparé à une solution analytique ou à l'équilibre. Aucun essai n'atteint E.

## Étape 0 — outils MCP

Le serveur attaché à la session (PID 14939, démarré à 04:36) précédait le code qui
enregistre `search_test_cases` et `read_test_case` (`server.py`, 06:06) : ils
n'étaient pas visibles dans la session. Le client de la session ne peut pas être
rebranché depuis l'agent ; les deux outils ont été vérifiés par un client MCP
stdio sur un serveur neuf (`tools/list` : les sept outils ; appels journalisés
dans `data/processed/query_log.jsonl`, commit `50ebc13c…` de `codeaster-src`). Une
reconnexion manuelle du serveur (`/mcp`) reste à faire pour les sessions suivantes.

## Étape 1 — documentation et cas tests (niveau A)

- **U4.43.01** (l. 680) : « une masse par unité de surface rho ».
- **R3.07.03** (l. 77) : « L'épaisseur donnée dans AFFE_CARA_ELEM est seulement utilisée avec
  la masse volumique définie par RHO ». Les deux documents se contredisent ; b3 (lot 22)
  et D4 donnent raison au second pour RHO. Le « seulement » est en revanche contredit
  par D2 pour le post-traitement (EPAIS intervient aussi dans FORC_NODA/REAC_NODA).
- **U4.81.04** (l. 73) : « Dans le cas de comportements homogénéisés de coque type
  ELAS_COQUE, il est préférable de regarder EFGE_NOEU. » Aucune restriction chiffrée.
- R3.07.03 décrit `SIEF_ELGA` comme des efforts généralisés ; la sortie 17.4.0 est un
  champ de contraintes `SIXX…` à trois sous-points (D1).
- U2.01.05 : aucune section ne traite d'`ELAS_COQUE` (recherche `ELAS_COQUE` dans
  ce document : aucun résultat).
- **Cas tests** (`search_test_cases DEFI_MATERIAU / ELAS_COQUE`, 12 fichiers, 0
  illisible, non tronqué) : hpla100i, hpla100j, ssls113a, ssls27a/c/d/e, ssls502a-d,
  zzzz503h, tous lus par `read_test_case`. Aucun ne contient `FORC_NODA` ni
  `REAC_NODA`. `EFGE_ELNO` : hpla100i/j (DKT, EPAIS = 1,0, PESANTEUR, référence
  analytique, tolérance jusqu'à 6 %), ssls113a. `SIEF_ELGA`/`SIGM_ELNO` : ssls502a/b,
  référence externe, tolérance jusqu'à 50 %. ssls502 a `FLEX_L = MEMB_L × EPAIS²/12`
  exactement (57,96338 = 18 692 840 × 0,0061²/12) : il n'exerce pas l'anomalie.

## D1 — efforts généralisés, FORC_NODA, REAC_NODA

Console DKT de l'essai A (L = 2 m, b = 0,5 m, FLEX_L = 1000, MEMB_L × EPAIS²/12 =
83,33), P = 5 N. Références par unité de largeur : M(0) = 20, M(1) = 10, |Q| = 10.

| Grandeur | Obtenu | Référence | Écart relatif |
|---|---|---|---|
| flèche en bout | 0,02666666666626 | 0,02666666666667 | −1,5×10⁻¹¹ |
| MXX EFGE_ELNO, x = 0 (moyenne) | 19,99999999983 | 20 | −8×10⁻¹² |
| MXX EFGE_ELNO, x = 1 | 9,999999999768 | 10 | −2×10⁻¹¹ |
| \|QX\| EFGE_ELNO, x = 1 | 9,999999999887 | 10 | −1×10⁻¹¹ |
| MXX EFGE_NOEU, x = 0 | 19,99999999983 | 20 | −8×10⁻¹² |
| écart max sur MXX, tous les points | 2,5×10⁻¹⁰ | 0 | — |
| SIEF_ELGA → moment équivalent / M analytique | 0,08333333333333 | 1 | −91,67 % |
| REAC_NODA, RZ à l'encastrement | 0,416666666672 | 5 | −91,67 % |
| FORC_NODA, RZ aux nœuds de l'encastrement | 0,416666666672 | 5 | −91,67 % |
| REAC_NODA, moment MY | −0,8333 | ±10 | facteur 1/12 |
| Σ FORC_NODA, tous les nœuds | −1×10⁻¹⁵ | 0 | (ne détecte rien) |

**Exacts** : déplacements, EFGE_ELNO, EFGE_NOEU (aux nœuds), y compris QX. **Faux** :
SIEF_ELGA (contraintes), FORC_NODA, REAC_NODA. Le moment équivalent tiré de SIEF_ELGA
(SIXX de la peau supérieure × EPAIS²/6) vaut MEMB_L × EPAIS²/(12 × FLEX_L) × M(x) sur
les 100 mailles, à 10⁻¹⁴ près. Non exploré : SIEF_ELGA aux points de Gauss en efforts
généralisés (le champ n'en contient pas), SIGM_ELNO.

## D2 — rôle d'EPAIS (coefficients inchangés)

| EPAIS | flèche en bout | EFGE M(0) | SIXX (1ᵉʳ point de Gauss) | REAC_NODA RZ | rapport SIEF/M |
|---|---|---|---|---|---|
| 0,005 | 0,02666666666626 | 19,99999999983 | 98 943,37567 | 0,104166666668 | 1/48 |
| 0,01 | idem | idem | idem | 0,416666666672 | 1/12 |
| 0,02 | idem | idem | idem | 1,666666666688 | 1/3 |

Déplacements, efforts généralisés et contraintes SIEF_ELGA **ne changent pas** ;
FORC_NODA/REAC_NODA et le moment équivalent varient **comme EPAIS²** (×4, ÷4). Cela
confirme l'hypothèse du lot 22 (rigidité de flexion reconstruite comme MEMB ×
EPAIS²/12) ; le mécanisme interne reste une déduction.

## D3 — CISA_L et CISA_T × 1000 (DKT)

Tous les résultats de D1 sont identiques (déplacements, EFGE, FORC_NODA, REAC_NODA,
SIEF_ELGA), à l'octet près des valeurs imprimées. Confirme U4.43.01 : pas de
cisaillement transverse en DKT.

## D4 — RHO nul

Exécution `completed_ok`, aucune alarme. Plaque ELAS (RHO = 7850, EPAIS = 0,01) :
770,085 N (référence 770,085, écart nul). Plaque ELAS_COQUE avec RHO = 0 (EPAIS =
0,02) : **0,0 N**. Le poids propre des éléments ELAS_COQUE est donc nul **sans
alarme** : `RHO = 0` n'est pas un moyen sûr d'exclure le poids, c'est une omission
silencieuse. (Référence nulle : non exprimable en écart relatif, rapportée en
notes, non en source.)

## D5 — contrôle d'équilibre hors ELAS_COQUE

Bande DKT, x < 1 en ELAS_COQUE (essai A), x > 1 en ELAS (E = 1,2×10¹⁰, ν = 0 :
D = 1000, même rigidité de flexion), charge 5 N en x = 0. Moments autour du point
d'application de la charge (attendus : |MX| = 1,25, MY = 0).

| Source | RZ | MX | MY | Écart à 5 N |
|---|---|---|---|---|
| D5a : forces des ressorts DIS_TR en x = 2 (FORC_NODA restreint aux POI1) | −5,000000000557 | −1,250000000181 | 3×10⁻¹⁰ | 1,1×10⁻¹⁰ |
| D5b : REAC_NODA aux nœuds d'appui x = 2 (aucun ELAS_COQUE) | 5,000000000551 | 1,250000000167 | −3×10⁻¹⁰ | 1,1×10⁻¹⁰ |
| D5b : REAC_NODA sur l'extrémité chargée (ELAS_COQUE seuls), 0 attendu | 4,5833 | 1,1458 | — | faux |
| D5b : REAC_NODA sur tous les nœuds | 5,000000000000 | 1,25 | — | 0 (ne discrimine pas) |

Flèche D5b : 0,02666666666841 (référence 0,02666666666667, +6×10⁻¹¹). Flèche D5a :
0,026703513 (aucune référence analytique : souplesse des ressorts).
La somme globale de REAC_NODA est juste alors que ses valeurs locales sont fausses : les
erreurs s'annulent (la somme des forces internes d'un ensemble d'éléments est nulle
quelle que soit la contrainte). Un contrôle d'équilibre porte donc soit sur les
ressorts, soit sur des nœuds d'appui hors ELAS_COQUE.

## Conclusion : (i), avec une précision

- **(i) retenue.** Les efforts généralisés d'`ELAS_COQUE` (EFGE_ELNO, EFGE_NOEU) sont
  exacts ; l'option 2 reste exploitable pour la répartition des efforts, avec le
  contrôle d'équilibre de D5.
- **Précision** : ne sont pas faux que FORC_NODA/REAC_NODA : SIEF_ELGA (contraintes)
  l'est aussi, et SIGM_ELNO n'est pas testé. Ce sont les champs construits à partir
  des contraintes qui sont faux ; ceux construits à partir des déformations
  généralisées sont exacts.
- **(ii) écartée** : les efforts généralisés sont exacts à 10⁻¹¹.
- **(iii) non retenue** : l'exactitude des EFGE ne dépend d'aucune condition sur
  EPAIS (D2). Les champs faux, eux, deviennent exacts si EPAIS² = 12 × FLEX/MEMB dans
  la direction sollicitée ; ce n'est pas une voie recommandée (EPAIS entre aussi dans
  le poids RHO × EPAIS × g et ne peut satisfaire à la fois L et T que si FLEX_L/MEMB_L
  = FLEX_T/MEMB_T).

## Limites

Flexion uniaxiale, une modélisation (DKT, QUAD4), un maillage, un repère ; membrane,
MYY, MXY, QY non sollicités (exactitude non testée) ; COQUE_3D, DST, TRIA3 non testés ;
ressorts sur des nœuds portés par ELAS_COQUE non testés (déduction : la force d'un
discret est k × déplacement) ; arbre Git modifié à l'exécution.
