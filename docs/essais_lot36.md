# Lot 36 — Diagnostic de la butée, accès aux fichiers MED, post-traitement graphique

Ce document fixe les critères **avant** les exécutions du modèle complet du lot. Le
texte des critères n'est jamais modifié après coup ; seules les sections « Résultats »,
« Verdict » et suivantes sont complétées (`docs/modele_rapport_essai.md`).

## Objet

1. Vérifier à la main le nœud à ressort le plus sollicité sous G (compression, traction)
   avant toute interprétation du dépassement de butée du lot 35 : 2 413 nœuds sur
   10 433 au-delà de la butée limite, jusqu'à 951 %, 1 605 nœuds en traction.
2. Chiffrer la part de trois causes prévues par le domaine de validité de la
   décision 5, par deux **variantes de diagnostic** du générateur qui ne servent jamais
   à produire le modèle de calcul : base (production) et V1 (pression initiale au repos
   côté bassin, cas G). Aucune révision de la décision 5 ni d'aucune décision pratique.
3. Donner accès aux fichiers MED (maillage, résultats) et les faire relire par la
   synthèse (`medcoupling`, conteneur).
4. Produire les vues qu'un ingénieur attend, en PNG, sans interface.

Code_Aster 17.4.0 (image du manifeste). Niveau visé : **C avec contrôles D**, jamais E.

## Étape 0

`aster-expert mcp-check` : 7 outils appelés sur un serveur neuf, identiques aux outils du
code (`mcp-check OK`). Les sept outils MCP sont visibles dans la session.

## Critères de réussite (écrits avant l'exécution du modèle complet)

Règle du dépôt : une grandeur que la théorie reproduit exactement l'est à 1e-6 près en
relatif ; toute autre issue est un échec, rapporté tel quel. Aucun seuil ci-dessous ne
sera relâché après lecture des résultats.

| Id | Grandeur | Attendu et origine | Nature | Seuil de réussite |
| --- | --- | --- | --- | --- |
| C1 | Exécution du modèle complet, base et V1 | `DIAGNOSTIC JOB : OK`, aucune alarme, aucune ligne `<F>`, `<E>`, `<S>` dans le `.mess` | binaire | tenu ou échec |
| C2 | Base : déplacements identiques à ceux du lot 35 | même modèle, mêmes charges : toutes les tables lues du lot 35 (`data/processed/runs/20260925T075049-b1de2c32`) égales à celles du MED de la base | exacte | écart relatif maximal <= 1e-9 sur toutes les tables de déplacement (`RESSORTS_*`, `DYT*`, `TETE_*`) des six cas |
| C3 | MED contre `.mess` (base et V1) | les tables reconstituées du MED égalent celles imprimées du `.mess` | exacte, limitée par l'impression (13 chiffres) | écart relatif maximal <= 1e-9 sur toutes les tables, six cas |
| C4 | Contenu du MED de résultats (base et V1) | par cas élémentaire : `DEPL`, `REAC_NODA`, `FORC_NODA` (ressorts), efforts généralisés des tubes, de la poutre et des tirants (`EFGE_ELNO`, `<cas>_ET`), des palplanches (`EFGE_NOEU`, `<cas>_EP`) : 30 champs | binaire | 30 champs présents, aucune valeur non finie |
| C5 | V1 : résultante de la pression initiale | Δ (réaction d'ancrage DY + force des ressorts) entre V1 et base, cas G = −Σ_bandes ∫ p(z)·L_proj dz (largeur projetée analytique, `band_projected_width`) | exacte | écart relatif <= 1e-6 |
| C6 | V1 ne modifie que le cas G | déplacements des cinq autres cas identiques entre V1 et base | exacte | écart relatif maximal <= 1e-9 |
| C7 | Base : équilibre du cas G, X, Y, Z | charge appliquée intégrée indépendamment + réactions des composantes bloquées + ressorts = 0 (`scripts/analyze_lot34_equilibre.py`) | exacte | écart relatif <= 1e-6 sur chaque composante, cas G, EAU_P, EAU_A, Q1 |
| C8 | Base : symétrie des déplacements | image miroir identique (x -> -x), six cas | exacte | écart relatif <= 1e-6 |
| C9 | Étape 1 : k/A d'un nœud à ressort | k écrit dans le `.comm` divisé par l'aire tributaire analytique = k_h de la couche | exacte | écart relatif <= 1e-9, aux deux nœuds relevés |
| C10 | Vues (par cas élémentaire) | chaque vue de la liste de l'étape 4 écrite en PNG non vide, lue depuis le MED, avec légende, unités, échelle ; le facteur d'amplification de la déformée est indiqué | binaire par vue | toutes les vues de la liste présentes ; toute vue non produite est déclarée avec sa cause |

Les résultats de l'étape 2 (taux maximal, nombre de nœuds au-delà de 100 %, nœuds en
traction au-delà de la butée côté terre, part de chaque cause) **n'ont pas de critère de
réussite** : ce sont des constats chiffrés sur le domaine de validité du modèle linéaire,
rapportés sans verdict de dimensionnement (CLAUDE.md, principe 6).

## Précisions consignées avant l'exécution du modèle complet

Le texte des critères ci-dessus est inchangé. Ce qui suit dit comment ils sont appliqués :

1. **Budget.** Au plus trois exécutions du modèle complet : base, V1, et une réserve pour un
   échec expliqué. Le quai réduit (maillage vérifié du lot 30) sert au développement
   sans plafond ; ses exécutions sont comptées à part.
2. **La base n'est plus le `.comm` du lot 35 octet pour octet** : le générateur écrit
   désormais les efforts généralisés et la force des ressorts dans le MED de résultats,
   et retire `SIEF_ELGA` du MED (faux sous `ELAS_COQUE`, illisible par `medcoupling`,
   l'essentiel des 315 Mo du MED du lot 35). Le modèle de calcul est inchangé : le
   critère C2 le vérifie sur les déplacements. Sans option de diagnostic, le `.comm`
   de production reste celui qu'écrit le générateur (test de régression).
3. **V1 (données fictives de diagnostic, établies par Claude, énoncé du lot)** : pression
   initiale K0·σ'v côté bassin, dirigée vers la terre, sur les faces bassin des bandes de
   ressorts (`RESS_AV_ARGI`, `RESS_AV_MARNE` moins `ECRAN_POUSSEE` pour les tubes ;
   palplanches de la bande d'argile seulement, la pression sous −18,00 ne portant que
   sur les tubes). Sens : établi par lecture du maillage orienté (faces de tube côté
   bassin toutes radialement sortantes, cosinus 1 sur 8 960 mailles), donc `PRES` positif
   côté tube, négatif côté palplanche (normale +Y de `ORIE_NORM_COQUE`). Contrôlé sur le
   quai réduit avant le modèle complet : la variation de bilan vaut −1 806 080,0001 N pour
   1 806 080 N attendus (écart 5e-11).
4. **Lecture des taux.** Taux base et V1 : force de réaction du ressort / force de butée du
   nœud (Σ_bandes aire × σ'p de la couche), σ'p bassin (Rankine, données du lot 35).
   Nœuds en traction : pression k·DY/A comparée à la butée limite **côté terre**
   Kp·σ'v + 2c'·√Kp, σ'v côté terre calculée depuis la stratigraphie du cas de test (§5),
   nappe côté terre à +2,00 (§6, situation permanente du cas G), terre-plein à +4,00,
   γ au-dessus de la nappe, γ' au-dessous. Ce calcul est confronté au profil de poussée
   active du cas de test (annexe A.4 : mêmes σ'v) et au profil de butée bassin du lot 35,
   qu'il retrouve (tests unitaires).
5. **V2** (aucune exécution) : lecture littérale de l'énoncé : le taux est recalculé sur
   les nœuds en compression de la **base** en retranchant de la pression de réaction
   k·|DY|/A la pression initiale de V1 (0 si négative), rapporté à σ'p bassin. La lecture
   voisine (pression initiale ajoutée à la réaction de V1) est rapportée à part et
   nommée comme telle : l'énoncé ne dit pas laquelle des deux « part de K0·σ'v » ; le
   rapport ne tranche pas.
6. **Cote de pivot** : cote où DY change de signe le long de la génératrice côté bassin de
   `TUBE_05`, interpolée linéairement entre les deux nœuds voisins.

## Modèle et exécution

- Générateur : `aster_expert.generation.generate` (options de diagnostic
  `InitialPressureDiagnostic`, jamais actives par défaut), maillage vérifié du lot 27
  (`combiwall_mesh.med`, SHA-256 `1bd724bd…`, 40 114 nœuds), données
  `combiwall_model_data.yaml`, image `sha256:d8d19ea9…`, Code_Aster 17.4.0.
- `.comm` (produits par `scripts/generate_lot36_variantes.py`, niveau B par `validate_comm`,
  `valid = true`, **aucune commande non vérifiée**) :
  - base : `data/examples/lot36_butee/complet_base.comm`, SHA-256 `5a2b9be4…`, 3 715 lignes,
    265 commandes confrontées sur 265 ;
  - V1 : `complet_v1.comm`, SHA-256 `09873ea7…`, 3 764 lignes, 270 sur 270.
- Exécutions du modèle complet : **2 sur les 3 autorisées** (la réserve n'a pas servi).
  Base : `data/processed/runs/20260925T090253-1f383214`, **627,7 s** ; V1 :
  `20260925T091324-defef551`, **819,4 s** (exécutée en même temps que des lectures de MED :
  durée non comparable à la base). Cumul modèle complet : 1 447,1 s.
- Quai réduit (développement, sans plafond) : 4 exécutions, 546,2 s cumulées (144,7 + 125,1
  avant l'ajout des champs au MED, 140,0 + 136,4 après). Cumul de toutes les exécutions
  Code_Aster du lot : 6, 1 993,3 s.
- Autres commandes : `aster-expert report` (base : 2 min 40, V1 sans vues : 1 min 26),
  `scripts/analyze_lot34_equilibre.py` (4 min 28), `analyze_lot36_controles.py` (1 min 59),
  `analyze_lot36_butee.py` (46 s).
- Base : le `.mess` ne contient aucune ligne `<F>`, `<E>`, `<S>`, `<A>` (compte 0/0/0/0),
  `DIAGNOSTIC JOB : OK` ; V1 de même.

## Résultats

### Critères C1 à C10

| Id | Résultat obtenu | Seuil |
| --- | --- | --- |
| C1 | base et V1 : `DIAGNOSTIC JOB : OK`, 0 alarme, 0 `<F>`/`<E>`/`<S>` | tenu |
| C2 | écart maximal entre les tables du MED de la base et celles du `.mess` du lot 35 : 4,8e-13 (déplacements), 4,9e-13 (autres tables, 72 tables) | <= 1e-9 |
| C3 | MED contre `.mess` : 4,88e-13 pour la base et pour V1 (72 tables chacune) | <= 1e-9 |
| C4 | 30 champs attendus présents et finis dans le MED de la base, et dans celui de V1 | 30 / 30 |
| C5 | variation −7 224 319,999931 N pour −7 224 320 N attendus : écart relatif 9,6e-12 | <= 1e-6 |
| C6 | cinq autres cas : écart 0,0 sur 60 tables ; cas G : écart 1,87 (l'effet de V1) | <= 1e-9 |
| C7 | équilibre X, Y, Z, base : au plus 8,8e-11 (G : 3,9e-13, −5,0e-11, −1,1e-12 ; Q1 4,5e-12, −8,8e-11, −7,4e-13 ; EAU_P, EAU_A du même ordre) | <= 1e-6 |
| C8 | symétrie, 20 057 paires, six cas : au plus 5,7e-11 | <= 1e-6 |
| C9 | k/A = 35,000000 MN/m³ = k_h de la couche, aux deux nœuds (écart 1e-14) | <= 1e-9 |
| C10 | 48 PNG (6 cas × 8 vues), lus du MED, avec titre, unités, légende de couleur ; facteur d'amplification indiqué sur la déformée | 48 / 48 |

Remarque sur C7 : la sonde de charge assemblée (`analyze_lot34_charge_assemblee.py`, qui
exige un modèle entièrement bloqué, donc une exécution de plus) n'a **pas** été relancée :
la charge appliquée « telle qu'évaluée par Code_Aster » est celle du lot 35
(`data/examples/lot35_synthese/modele_complet/integrale_modele_complet.json`). Elle ne
dépend que du maillage (identique, même SHA-256) et des définitions de charge, dont les
sections du `.comm` de base sont celles du lot 35 ; la réutilisation est déclarée, non
cachée.

### Étape 1 — vérification à la main (cas G, base)

Aire tributaire A : lue de l'analytique (`spring_node_areas`), jamais déduite de la raideur ; raideur k : lue du `.comm` (`VALE` de la classe du nœud) ; DY : MED/`.mess`.

| | Nœud le plus sollicité en compression | Nœud en traction le plus sollicité |
|---|---|---|
| Nœud, porteur | N983, TUBE_04 | N20947, TUBE_05 |
| Cote z (m CM) | -12,00 | -16,75 |
| Groupe de raideur du `.comm` | GEN_RESS_ARGI_01 | GEN_RESS_ARGI_22 |
| Aire tributaire A (m²) | 0,002172 | 0,027767 |
| Raideur k (N/m) | 76015,35 | 971849,11 |
| k / A (MN/m³) | 35,000000 | 35,000000 |
| k_h de la couche (MN/m³) | 35,000 | 35,000 |
| DY (mm) | -12,8025 | 0,6644 |
| Pression k·DY/A (kPa) | -448,09 | 23,25 |
| σ'p bassin en z (kPa) | 47,10 | 169,97 |
| Taux vs butée bassin | 951,4 % | — |
| Butée côté terre en z (kPa) | 497,99 | 620,87 |
| Taux vs butée terre | — | 3,75 % |

Vérification à la main du nœud en compression : k/A vaut le k_h de la couche (35,000000 MN/m³) ; A = ¼ × (largeur projetée des deux facettes voisines) × hauteur de maille, soit ¼ × (R(1−cos 9°) + R(cos 9° − cos 18°)) × 0,25 m avec R = 0,71 m, ce qui donne 0,0348 × 0,25 / 4 = 0,002172 m² : aucune erreur d'aire tributaire ni d'unité (MN/m³ × 1e6 = N/m³).

### Étape 2 — part de chaque cause (cas G, modèle complet, 10 433 nœuds à ressort)

| Grandeur | Base | V1 (pression initiale côté bassin) |
|---|---:|---:|
| Nœuds en compression | 8 828 | 5 867 |
| Taux maximal de butée bassin | 951,4 % | 912,8 % |
| Nœud du taux maximal | N983, z = -12,00 | N983, z = -12,00 |
| Nœuds au-delà de 100 % | 2 413 | 2 141 |
| Force de compression totale des ressorts (MN) | 19,68 | 13,37 |
| Dont force en excès de la butée (MN) | 6,85 | 6,03 |
| Nœuds en traction | 1 605 | 4 566 |
| Pression de traction maximale (kPa) | 32,2 | 87,3 |
| Force de traction totale (MN) | 0,44 | 1,40 |
| Taux maximal vs butée limite **côté terre** | 3,75 % | 7,64 % |
| Nœuds en traction **au-delà** de la butée côté terre | 0 | 0 |
| Cote de pivot, génératrice bassin de TUBE_05 (m CM) | -14,97 | -15,04 |

### Contrôle corrigé du signe : nœuds en traction contre la butée limite côté terre (Kp·σ'v + 2c'·√Kp)

| Couche | Modèle | Nœuds en traction | Pression max (kPa) | Butée terre au nœud du taux max (kPa) | Taux max | Au-delà |
|---|---|---:|---:|---:|---:|---:|
| argile marneuse (−12,00 à −18,00) | base | 453 | 27,1 | 620,9 | 3,75 % | 0 |
| marne compacte (−18,00 à −26,00) | base | 1 193 | 32,2 | 885,2 | 3,64 % | 0 |
| argile marneuse (−12,00 à −18,00) | V1 | 524 | 22,0 | 620,9 | 3,11 % | 0 |
| marne compacte (−18,00 à −26,00) | V1 | 4 099 | 87,3 | 1135,3 | 7,64 % | 0 |

σ'v côté terre : stratigraphie du cas de test (§5), nappe à +2,00 (§6), terre-plein à +4,00 ; γ au-dessus de la nappe, γ' au-dessous. Ce calcul retrouve à 0,1 kPa près le profil de poussée active de l'annexe A.4 (test unitaire).

### V2 — sans exécution supplémentaire

| Lecture | Taux maximal | Nœuds au-delà de 100 % |
|---|---:|---:|
| Base (référence) | 951,4 % | 2 413 |
| V2, lecture littérale : (réaction de la base − pression initiale de V1)⁺ / σ'p bassin | 951,4 % | 2 205 |
| Lecture voisine : pression initiale de V1 **ajoutée** à la réaction de V1, / σ'p bassin | 912,8 % | 2 326 |

L'énoncé ne dit pas laquelle des deux lectures est celle de la figure F.1.1 : les deux sont rapportées, aucune n'est retenue. Le taux maximal est identique dans les trois cas parce que le nœud du maximum est à z = −12,00, où la pression initiale est nulle.

### Où se trouvent les dépassements (nœuds au-delà de 100 % / nœuds en compression)

| Tranche de cote (m CM) | Base | V1 |
|---|---:|---:|
| -12 à -13 | 1005 / 1005 | 1005 / 1005 |
| -13 à -14 | 841 / 1005 | 825 / 1005 |
| -14 à -15 | 560 / 996 | 496 / 1005 |
| -15 à -16 | 384 / 880 | 224 / 889 |
| -16 à -17 | 112 / 800 | 0 / 784 |

### Ce que chaque cause attribue (chiffres seulement, aucune conclusion de conception)

1. **Ressorts linéaires non plafonnés** : 6,85 MN sur 19,68 MN de compression (34,8 %) dépassent la force de butée de leur nœud, dans le modèle de base ; les dépassements sont sur les tranches −12 à −17 m.
2. **Pression initiale au repos côté bassin (V1)** : les nœuds au-delà de 100 % passent de 2 413 à 2 141 (-272), le taux maximal de 951,4 % à 912,8 % ; la force de compression baisse de 6,30 MN.
3. **Absence de ressorts côté terre** : 1 605 nœuds en traction (15,4 % des nœuds à ressort), pression maximale 32,2 kPa, soit 3,75 % de la butée limite côté terre ; 0 nœud au-delà. Sous V1 : 4 566 nœuds, 7,64 %, 0 au-delà.


## Étape 3 — accès aux fichiers MED

- **Maillage** : `combiwall_maillage.med` (copie du MED de `mesh run`, SHA-256 `1bd724bd…`,
  4,9 Mo), dans `résultats_MED_Paravis/` avec son empreinte. Sur instruction de MM, le
  dossier est dans le dépôt, sur la VM (ParaVis est dans la VM, pas sur l'hôte) ; le
  dossier partagé ne reçoit que les images, la synthèse et les `LISEZMOI.md`.
- **MED de résultats** : 142,8 Mo (> 100 Mo : signalé à MM avant toute copie ; réponse : dépôt
  brut dans la VM, jamais dans le dossier partagé). Il ne contenait avant ce lot que `DEPL`,
  `REAC_NODA` et `SIEF_ELGA` par cas : ni efforts généralisés, ni efforts des tirants, ni
  forces des ressorts. Le générateur écrit maintenant, par cas : `DEPL`, `REAC_NODA`,
  `FORC_NODA` (mailles `POI1` des ressorts), `EFGE_ELNO` (tubes, poutre, tirants),
  `EFGE_NOEU` (palplanches) : 30 champs, nommés `<cas>` + grandeur (`G_______DEPL`,
  `G_ET____EFGE_ELNO`, `G_EP____EFGE_NOEU`…). `SIEF_ELGA` en est retiré (faux sous
  `ELAS_COQUE`, et sa localisation `SECT_SHELL` fait échouer `MEDFileFields.New` de
  `medcoupling`) : le MED du lot 35 faisait 315 Mo.
- **Lecture par l'outil** : `aster-expert report` lit le MED par `medcoupling` dans le
  conteneur (`aster_expert.report.med_read`, `med_source`, `scripts/med_results_dump.py`)
  et reconstitue les mêmes lignes que les tables du `.mess`, qui ne sont plus qu'une
  contre-vérification (écart 4,88e-13). Les vues viennent du MED seulement.
- **ParaVis** : `LISEZMOI.md` (dossier VM et dossier partagé). Constat sur le lecteur
  MEDReader : un seul « support » (`ComSup`) peut être activé par lecteur ; par défaut seul
  `ComSup0` (efforts `EFGE_ELNO`) l'est, les déplacements sont sous `ComSup2`.

## Étape 4 — post-traitement graphique

- **Moteur des vues 3D : impossible ici.** `pvbatch` existe dans l'image Salomé-Méca 2024.1.0
  et lit le MED, mais son rendu échoue (`vtkXOpenGLRenderWindow`, `SIGABRT`) : ni `Xvfb` ni
  `xvfb-run` dans la VM ou l'image, le ParaView de Salomé-Méca n'a qu'un rendu X (pas
  d'EGL/OSMesa), et l'affichage `:0` du bureau refuse la connexion (autorisation).
- **Moteur retenu : `matplotlib` 3.11.2** (installé avec l'accord de MM, extra `figures` de
  `pyproject.toml`, backend Agg), vues 2D : `aster_expert.report.figures`, appelées par
  `aster-expert report` (`vues/`, insérées dans `synthese.md`), rejouables sur tout résultat.
- **Vues, par cas élémentaire** (8 × 6 = 48) : `deformee` (plans de tête et de dragage,
  coupe Y-Z du tube central, facteur indiqué), `dy_ecran` (développée X-Z, faces terre et
  bassin), `efforts_tubes` (`MXX`, `NXX`), `efforts_palplanches` (`MXX`, `NXX`, `EFGE_NOEU`),
  `fleches` (poussée, réactions des ressorts, tirant, charge de poutre, amarrage, accostage),
  `poutre` (moments et tranchants), `profils` (DY, M, N le long de `TUBE_05` et `TUBE_01`),
  `butee` (pression de réaction contre butée limite, avec cote de pivot).

## Verdict

C1 à C10 : **tenus**. Étape 2 : constats chiffrés, sans critère.

## Lecture

Faits : les chiffres des tableaux ci-dessus. En particulier, k/A vaut k_h de la couche aux
deux nœuds relevés (le taux de 951 % n'est pas un défaut d'aire ni d'unité) ; le nœud du
taux maximal est un nœud de coin de très faible aire (0,00217 m², force 973 N) situé à
z = −12,00, où la butée limite ne vaut que 2c'√Kp = 47,1 kPa ; les dépassements sont
concentrés entre −12 et −17 m ; aucun des nœuds en traction ne dépasse la butée limite côté
terre (3,75 % au plus en base, 7,64 % sous V1).

Déductions (marquées comme telles) : la pression initiale K0·σ'v seule ne fait pas
disparaître les dépassements (2 413 → 2 141 nœuds) ; les nœuds en traction sont, au regard
de la butée côté terre, sans commune mesure avec la limite (contre-butée représentée par les
ressorts côté bassin, ce que le modèle linéaire autorise sans plafond). Les dépassements ne
sont pas attribuables à eux seuls à l'une des trois causes : la part du plafonnement
(ressorts non plafonnés) n'est pas mesurée par une variante (aucune exécution ne plafonne
les ressorts) ; elle est seulement quantifiée par la force en excès (6,85 MN sur 19,68 MN).

Aucune recommandation de conception : la révision éventuelle de la décision 5 appartient à
MM.

## Limites

- Données de V1 fictives (établies par Claude) ; V1 n'est pas le modèle de calcul.
- V2 : deux lectures possibles de « retrancher la pression initiale », rapportées toutes
  deux sans en retenir une.
- Aucune vue 3D ; ParaVis en interface non lancé (aucun affichage pour l'agent) : seules la
  lecture du MED, le cochage des champs et le *Calculator* ont été essayés (`pvbatch`, sur le
  MED du quai réduit) ; le filtre *Extract Group* et le rendu graphique ne le sont pas.
- Les efforts des tubes sont par élément et par nœud, sans moyenne ; les vues les moyennent
  par maille (cartographies) ou par nœud (profils) : lecture graphique, non un extremum
  (les extrêmes sont dans `synthese.md`). L'échelle des cartographies d'efforts est limitée au
  99,5e centile de |valeur| (indiqué sur chaque légende).
- L'accrochage du tirant crée un pic local de contraintes (décision 11) : les pics de tête
  des profils de `MXX` et `NXX` sont hors échelle et signalés sur les vues.
- Efforts dimensionnants, combinaisons et vérifications normatives : hors périmètre.
