# Lot 50 quinquies — Charges : un MED et un script pour Salomé-Méca

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-50quinquies`, depuis `main`
(après fusion de `lot-50quater`). Consigne : `docs/lots/lot50quinquies_consigne.md` (version 3 ; elle
remplace les versions 1 et 2). Aucune exécution Code_Aster, aucune modification du `.comm` ni des
résultats, aucun autre projet touché.

## Contenu du MED (`charges.med`)

Le fichier livré est celui que Code_Aster a écrit au post-traitement du lot 50 bis
(exécution `20261012T144424-430251f1`), copié **octet pour octet** (sha256 `969dbd82…`, 521 423
octets, empreinte relue identique à `resultats/livrables/med/charges.med`). 20 champs, un pas
chacun, sur un maillage de 416 nœuds :

- `FN_<cas>` (12 cas mécaniques) : forces nodales équivalentes aux charges du cas, six composantes
  `DX…DRZ` = `FX…MZ` en N et N·m ; commande : `CALC_VECT_ELEM(OPTION='CHAR_MECA')` puis
  `ASSE_VECTEUR`, écrit par `IMPR_RESU(FORMAT='MED', CHAM_GD=…, NOM_CHAM_MED=…)` (catalogue 17.4,
  U4.61.02 et U4.61.23, U7.05.21 « NOM_CHAM_MED ») ;
- `FV_<cas>` (4 cas thermiques) : forces nodales équivalentes aux variables de commande du cas
  (dilatation), autoéquilibrées ; commande : `CALC_VECT_ELEM(OPTION='FORC_VARC')` (U4.61.02, catalogue
  17.4 : `FORC_VARC` exige `MODELE` et `CHAM_MATER`). **Deux préfixes** parce que ce sont deux options
  de `CALC_VECT_ELEM` : un cas thermique n'a pas de charge propre, ses forces viennent du champ de
  matériau ;
- `VARC_<cas>_TEMP_1` (4 cas thermiques) : le champ de température lui-même, `IMPR_RESU/RESU/CHAM_GD`.

Source : `src/aster_expert/livrables/postcomm.py` (insertions dans une copie du `.comm`, jamais dans
la production). Le reconditionnement du lot 50 quater (16 pas, `CHARGE_REPARTIE`,
`ECART_TEMPERATURE`), la lecture statique du `.comm` et les `.vtu` sont **désactivés par défaut,
non supprimés** : sous-étape `charges_avance`, lancée par son nom
(`projet <nom> livrables --sous-etape charges_avance`), hors de la chaîne complète
(`chaine.OPTIONAL_SUBSTEPS`, testé).

## Le script `charges_salome.py`

Généré par le tronc commun (`livrables/charges_salome.py`, gabarit `charges_salome_modele.py`),
222 lignes, aucun fichier voisin ni manifeste. En-tête : `FICHIER_MED` (chemin absolu, rempli à la
génération, puis ramené au chemin du dépôt sur le partage au dépôt : c'est la seule ligne qui change),
`CAS_AFFICHE`, `FACTEUR_ECHELLE` (`None` : échelle automatique par cas), `SOUS_ECHANTILLONNAGE`, plus
`FLECHES_THERMIQUES` (faux). Il lit le MED par `MEDReader`, dessine le modèle en filaire gris, un objet
`Cas <nom>` par cas (flèches colorées selon la norme, légende en kN, **plus grande flèche = 15 % de la
taille du modèle, propre à chaque cas** ; cas thermiques : éléments colorés selon `TEMP`, plage
symétrique, sans flèches) et `afficher_cas("Q")`, qui cache les autres cas et affiche la légende du cas
(chaque cas a sa propre échelle de couleurs : défaut de légende partagée du lot 50 quater corrigé). Titre : cas, nature, ΣFX ΣFY ΣFZ en kN (Q : ΣFZ = −62,5 kN, comme au lot 50 quater).
Fichier introuvable : `FileNotFoundError("renseigner FICHIER_MED en tête du script …")` avant tout
objet de pipeline (test : aucun appel à `paraview.simple`).

## Les deux essais obligatoires (image Salomé-Méca V2024.1.0, ParaView 5.11)

1. **`pvbatch` sous `xvfb`, sur le script déposé** : 16 images iso rendues, puis **la même chose par
   `exec(open(…).read())` depuis un autre dossier, sans `__file__`** (pilote `lancement.py`) : 16
   images, identiques octet pour octet à celles de l'exécution directe.
2. **Interface réelle de Salomé-Méca (module ParaViS, `import pvsimple`)**, lancée sous `xvfb` : même
   `exec()` sans `__file__`, depuis `/tmp`. Résultat : 16 cas construits, 16 objets `Cas <nom>` dans le
   pipeline, `afficher_cas("TP")` puis `afficher_cas("Q")` sans erreur, capture de la vue avec la
   légende de Q (0 à 0,4478 kN). MEDReader est celui que charge ParaViS lui-même.

Constat utile : `MEDReader` sous `pvbatch` + `xvfb` se bloque dans `MPI_Init` (connexion X de
`hwloc_gl`) ; `HWLOC_COMPONENTS=-gl` le débloque. Réglé dans `run_in_salome`, sans effet pour MM dans
l'interface. Le menu ParaViS a été **relevé dans l'interface** : `Tools > Python Shell` (2ᵉ menu
`Tools`, celui de ParaView ; le premier est celui de Salomé), `View > Windows > Python Console`,
`File > Load Script…` (Salomé) et `Macros`. Le bouton `Run Script` du Python Shell n'a pas été cliqué
(l'essai a reproduit son effet par `exec`) ; sa présence est établie par la chaîne `Run Script` de
`libpqPython-pv5.11`.

## Correctif `images`

`paraview.py` n'embarque plus le manifeste en une ligne (`MANIFESTE = json.loads({manifeste!r})`,
l. 200) : il écrit `paraview_charges.json` et `paraview_resultats.json` à côté des scripts, lus par
`json.load` depuis `DOSSIER` (dossier du script, ou dossier courant sous `exec`). Test : manifeste
synthétique de 12 Mo, aucune ligne de script de plus de 1 000 caractères, relu à l'identique.
**Limite : la sous-étape `images` n'a pas été relancée** (consigne : correctif minimal, rien d'autre ;
son exécution réelle reste à faire et peut encore échouer ailleurs).

## Fichiers déposés (`/media/sf_partage/echanges/lot50quinquies/pontons_alu_01/`, 2,3 Mo)

`charges.med`, `charges_salome.py`, `LISEZMOI.txt` (5 lignes), `png/` (16 vues iso rendues par le script
lui-même), `empreintes.sha256` (19 lignes, `sha256sum -c` : 0 écart).

## Fichiers du dépôt

Créés : `src/aster_expert/livrables/charges_salome.py`, `charges_salome_modele.py`,
`tests/unit/test_livrables_charges_salome.py` (8 tests), `projets/pontons_alu_01/scripts/livrables_lot50quinquies.py`,
`docs/lots/lot50quinquies_*.md`. Modifiés : `livrables/chaine.py` (`charges_avance`,
`OPTIONAL_SUBSTEPS`), `charges_verif.py` (`step_charges` : MED tel quel ; ancienne version :
`step_charges_avance`), `paraview.py` (manifeste voisin), `cli.py` (aide), `tests/unit/test_livrables.py`,
`connaissances/rex/`, `docs/etat.yaml`, README.

## Tests

`ruff format`, `ruff check` : propres ; `mypy src` (168 fichiers) et `mypy` (474) : sans erreur ;
`pytest` hors tests lents : **1 801 réussis**, 4 désélectionnés (5 min 7 s). Nouveaux : cas et titre
(résultante), cas sans forces refusé, script court sans `__file__` ni manifeste, arrêt avant tout objet
si le MED manque, `set_med_path` ne change qu'une ligne, dépôt (MED identique, 5 lignes, empreintes),
`charges_avance` hors chaîne, refus sans traitement préalable ; correctif `images` (12 Mo). Essais réels :
sous-étape `charges` (≈ 1 min), script de dépôt, essai dans l'interface ; **non versionnés** (il n'y a
pas de test `lent_salome` : le dépôt ne contient aucun MED de charges, et celui de PONTONS-ALU-01 est
produit par un calcul non versionné).

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 11 exécutions attribuées, 0 échec, aucune exécution lancée dans ce
lot ; développement : 10, 0 échec, taux 0,0 % ; vérification : 1. « Tous les échecs sont classés :
clôture possible ». Revue inscrite (`--enregistrer --lot 50quinquies`). Interventions de MM : aucune
(la désignation `prompt_lot50quinquies.md` « v3 » est la troisième version de la consigne).
Connaissances ayant évité une erreur : aucune déclarée.

## Limites et points non couverts

- MM n'a pas encore ouvert le script ; l'essai dans l'interface est automatisé (`exec` sous `xvfb`).
- Le bouton `Run Script` du Python Shell n'a pas été actionné à la main.
- Les images sont des vues iso : sur Q (≤ 0,45 kN par nœud), la légende de chaque cas est propre, mais
  des flèches très voisines se recouvrent ; `SOUS_ECHANTILLONNAGE` et `FACTEUR_ECHELLE` y répondent.
- Les moments nodaux (`DRX…DRZ`) sont dans le MED, non dessinés.
- La température est tracée telle que le MED la porte (`TEMP`), sans retrancher `VALE_REF` ni unité
  déclarée : la légende dit « champ TEMP ».
- La sous-étape `images` corrigée n'a pas été relancée. CI de la branche à vérifier avant fusion.

Consigne à MM : le serveur MCP n'a pas changé dans ce lot ; aucun redémarrage de session requis.
