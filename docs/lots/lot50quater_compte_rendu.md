# Lot 50 quater — Pontons aluminium : visualisation des charges dans ParaView

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-50quater`, depuis `main`
(après fusion de `lot-50ter`). Consigne : `docs/lots/lot50quater_consigne.md`. Exécution de
référence : `20261012T144404-2cf50a46` (lot 50 bis : P24, P25, MP1200, k = 1). Aucune exécution
Code_Aster n'a été relancée, aucun résultat ni le `.comm` du lot 50 bis n'ont été modifiés.

## Étape 0 — Diagnostic

**0.1 Cause.** Le script ParaView des charges n'était produit que par la sous-étape `images`
(`aster_expert/livrables/paraview.py`, `step_images` → `write_scripts`, l. 573), qui écrit et
rend **ensemble** les deux scripts. Le script des résultats incorpore tout le manifeste sur une
seule ligne (`MANIFESTE = json.loads({manifeste!r})`, l. 200, 3 402 combinaisons : 10 Mo) que le
Python de `pvbatch` refuse ; au lot 50 la sous-étape a donc été abandonnée en bloc, charges
comprises, et le compte rendu n'a mentionné que le script des résultats. Ce n'était pas un
générateur limité à un type de modèle : les charges d'un modèle filaire sont gérées. La chaîne
par défaut (`run_deliverables`) n'avait aucune sortie de charges indépendante de `images`.
**Correctif** : nouvelle sous-étape `charges` (`SUBSTEPS`, après `traiter`) du tronc commun,
`aster_expert/livrables/charges_verif.py`, qui ne dépend ni de `images` ni du manifeste des
combinaisons ; un test vérifie qu'elle fait partie de la chaîne par défaut. `images` n'est pas
modifiée (limite ci-dessous).

**0.2 MED de charges de l'exécution de référence.** Il existe : `resultats/livrables/med/charges.med`
(post-traitement `20261012T144424-430251f1`, tables identiques à la production). Inventaire :
un maillage (`00000002`, 416 nœuds, 72 QUAD4, SEG2, POI1) ; 20 champs, **un seul pas chacun** :
12 `FN_<cas>` et 4 `FV_<cas>` (forces nodales, FX…MZ en `DX…DRZ`, supports nœuds) et 4
`VARC_<cas>_TEMP_1` (température, 298 nœuds). Il couvre les 16 cas (G1, G2, Q, QD, HU, HD, TP, TM,
TAP, TAM, AMM, AMP, ACM, ACP, AAM, AAP) mais **par champ et non par pas**, sans intensité répartie
par élément ni ΔT par élément. ΣFZ(FN_Q) = −62 500 N : c'est bien la géométrie de référence
(le `charges.med` du lot 50, tablier de 2,27 m, n'a pas servi).

**0.3 Mode d'obtention : existant.** Les 16 cas étant couverts, rien n'a été régénéré ni
réexécuté. Les champs ajoutés viennent du `.comm` de production (lecture statique, jamais
exécuté). Mots-clés retenus, confrontés au catalogue 17.4 (`get_command_schema`) et à U4.44.01 :
`FORCE_POUTRE` (`GROUP_MA`, `TYPE_CHARGE='FORCE'` par défaut ; `FX FY FZ MX MY MZ` en repère
**global**, `N VY VZ MT MFY MFZ MGX MGY MGZ` en repère local) ; `FORCE_NODALE` ; `PESANTEUR` ;
`AFFE_MATERIAU/AFFE_VARC` (`NOM_VARC`, `CHAM_GD`, `VALE_REF`) et `CREA_CHAMP/AFFE/VALE`.

## Contenu du MED (`charges.med`, écrit par `scripts/livrables_charges.py`, relu)

- `CHARGE_NODALE` (nœuds, FX FY FZ MX MY MZ, N et N·m) : 16 pas ;
- `CHARGE_REPARTIE` (mailles SEG2, FX…MZ globaux, N/m et N·m/m, zéro hors charge) : 9 pas
  (les cas à `FORCE_POUTRE`) ;
- `ECART_TEMPERATURE` (mailles SEG2, ΔT en K) : 4 pas (TP +46, TM −28, TAP +56, TAM −23 K).

Numéro d'ordre = rang du cas (G1 = 1 … TAM = 16, table `pas_du_med` de `manifeste.json`).
**Limite** : un pas MED ne porte pas de nom ; l'identifiant du cas est dans le manifeste, dans
les noms de fichiers `.vtu` et dans le pipeline du script. Relecture du fichier écrit : 62 208
valeurs comparées, 0 pas en écart. Pesanteur : forces nodales seulement ; ponctuelles : forces
nodales aux deux nœuds chargés. Le catalogue lu n'a rien laissé « non traité » sur ce modèle.

## Script ParaView

`charges_paraview.py`, généré par le tronc commun (`charges_modele.py`), modifiable à la main :
paramètres en tête (`DOSSIER`, `CAS_AFFICHE`, `FACTEUR_ECHELLE`, `SOUS_ECHANTILLONNAGE`,
`CAS_EN_PLAN`), une fonction par représentation, tourne dans le Python Shell et en `pvbatch`.
Flèches nodales colorées par la norme (kN), échelle **commune par nature** (répartie, ponctuelle,
pesanteur, température) ; mailles colorées selon l'intensité (kN/m, plage commune des cas
répartis), non chargées en gris ; ΔT en K ; filaire gris, rotules (sphères rouges) et ressorts
(cubes bleus) toujours visibles ; titre : cas, nature, ΣFX ΣFY ΣFZ. Seul le premier cas (G1) est
visible à l'ouverture ; les autres sont cachés et nommés par cas.

**Écarts à la consigne, à connaître** : (1) le script lit les `.vtu` (un par cas) et non le MED :
la lecture du MED par un ParaView Windows standard n'est pas établie (conclusion du lot 49), donc
la conversion `.vtu` est livrée et lue par défaut ; le MED est livré avec les mêmes champs, pas
de paramètre de bascule (non testé, donc non livré). (2) `charges.pvsm` **non livré** : un état
ParaView enregistre des chemins absolus (ceux du conteneur), il ne serait pas fiable sous Windows.
(3) Échelle commune : les flèches de Q (≤ 0,45 kN par nœud) sont 40 fois plus courtes que celles de
AAM (17,7 kN) et à peine visibles sur l'image ; c'est la conséquence voulue d'une échelle commune
aux cas répartis (la lecture de Q se fait par la couleur) ; `FACTEUR_ECHELLE` agrandit les flèches.

## Résultantes (12 cas mécaniques, seuil 10⁻⁶ en relatif)

Somme des forces nodales du MED (non arrondie) contre l'intégrale des charges déclarées
(`resultantes.csv`, source `.comm` × longueurs des mailles) et contre `charges.csv` du lot 50 ter
(`controle_charges_csv.csv`) ; G1 contre le poids calculé à la main (CTL-013, `controls.cases`).

| Cas | ΣFX (kN) | ΣFY (kN) | ΣFZ (kN) | écart relatif | verdict |
|---|---|---|---|---|---|
| G1 | 0,0 | 0,0 | −45,6 | 8,0e-16 | RÉUSSI (poids à la main) |
| G2 | 0,0 | 0,0 | −12,5 | 2,9e-16 | RÉUSSI |
| Q | 0,0 | 0,0 | −62,5 | 1,2e-16 | RÉUSSI |
| QD | 0,0 | 0,0 | −31,25 | 1,2e-15 | RÉUSSI |
| HU | 0,0 | 0,0 | 12,5 | 2,9e-16 | RÉUSSI |
| HD | 0,0 | 0,0 | −12,5 | 2,9e-16 | RÉUSSI |
| AMM | 0,0 | −16,0 | 0,0 | 0 | RÉUSSI |
| AMP | 0,0 | 16,0 | 0,0 | 0 | RÉUSSI |
| ACM | 0,0 | 32,0 | 0,0 | 1,1e-16 | RÉUSSI |
| ACP | 0,0 | −32,0 | 0,0 | 1,1e-16 | RÉUSSI |
| AAM | 0,0 | 154,0 | 0,0 | 0 | RÉUSSI |
| AAP | 0,0 | −154,0 | 0,0 | 0 | RÉUSSI |

Les quatre cas de température sont autoéquilibrés (écart 8e-18 à 4e-17 sur Σ|F|), informatifs.
Niveau : ces contrôles sont de niveau D sur l'application des charges (pas un niveau E).

## Images

18 PNG rendus **par le script livré lui-même** (`pvbatch --png`, `xvfb-run`, ParaView 5.11 de
l'image Salomé-Méca) : 16 vues iso (une par cas) et les vues en plan de Q et de HU
(`load_plan_views` de `projet.yaml`, nouveau champ de la déclaration).

## Fichiers déposés (`/media/sf_partage/echanges/lot50quater/pontons_alu_01/`, 4,3 Mo, 43 fichiers)

`charges.med` (b8e91eb3…), `charges_paraview.py` (ebdf34d9…), 16 `charges_<cas>.vtu`, `modele.vtu`
(8e0b1d46…), `appuis_reactions.vtu` (4416f199…), `appuis_ressorts.vtu` (b6cadcd4…), `png/` (18),
`resultantes.csv` (9793be33…), `controle_charges_csv.csv` (5c3d1a90…), `manifeste.json`
(d951dae4…), `LISEZMOI.txt` (10 lignes, cc1800ef…), `empreintes.sha256` (43 lignes, relues :
`sha256sum -c`, 0 écart). Les empreintes complètes sont dans `empreintes.sha256`.

## Fichiers du dépôt

Créés : `src/aster_expert/livrables/charges_verif.py`, `charges_modele.py`,
`scripts/livrables_charges.py`, `tests/unit/test_livrables_charges.py` (10 tests),
`projets/pontons_alu_01/scripts/livrables_lot50quater.py`, `docs/lots/lot50quater_*.md`.
Modifiés : `livrables/chaine.py` (sous-étape `charges`), `livrables/conteneur.py` (paramètre
`script`), `livrables/inventaire.py` (`NEUTRAL_KEYWORDS` public), `projet/declaration.py`
(`load_plan_views`), `projets/pontons_alu_01/projet.yaml` (`load_plan_views: [Q, HU]`),
`connaissances/rex/` et `metriques/`, `docs/etat.yaml`, README.

## Tests exécutés

`ruff format`, `ruff check` : propres ; `mypy src` (166 fichiers) et `mypy` (470) : sans erreur ;
`pytest` hors tests lents : **1 792 réussis**, 4 désélectionnés, 4 min 35 s ; nouveaux tests :
lecture du `.comm` (dont composantes locales et `FORCE_COQUE` listées, jamais dessinées), intensité
par élément et résultante, ponctuelle et température, refus d'un cas sans champ nodal, verdicts de
résultante (un écart provoqué est rapporté en ÉCHEC), `.vtu` relus à l'identique, script compilé
et manifeste intégré relu, dépôt avec `LISEZMOI` et empreintes, sous-étape présente dans la chaîne
par défaut. Run réel : sous-étape `charges` (conteneur Code_Aster pour le MED, Salomé-Méca pour
les PNG), puis `livrables_lot50quater.py`.

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 11 exécutions attribuées, 0 échec, aucune exécution lancée
dans ce lot ; taux d'échec (développement) 0,0 % ; « Tous les échecs sont classés : clôture
possible ». Revue inscrite (`--enregistrer --lot 50quater`). Interventions de MM : aucune.
Connaissances ayant évité une erreur : aucune déclarée.

## Limites et points non couverts

- `images` (scripts des résultats) reste en échec sur le manifeste d'une ligne de 10 Mo : non
  corrigé ici (hors périmètre) ; seule la partie charges est désormais indépendante.
- Charges non dessinées par la sous-étape (listées dans `non_traite`, vides sur ce modèle) :
  `TOUT` de `FORCE_POUTRE`, composantes locales, `TYPE_CHARGE='VENT'`, `FORCE_COQUE`,
  `FORCE_ARETE`, `PRES_REP`… : les autres projets les verront listées ; ils n'ont pas été relancés.
- Dessin des flèches : forces seulement (les moments nodaux sont dans le MED, pas dessinés).
- Le MED n'a pas été ouvert dans un ParaView ; sa lecture par MEDReader reste à confirmer par MM.
- CI : à vérifier sur la branche après envoi avant fusion.

Consigne à MM : le serveur MCP n'a pas changé dans ce lot ; aucun redémarrage de session requis.
