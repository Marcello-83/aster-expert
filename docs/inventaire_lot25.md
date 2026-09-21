# Lot 25 — Données chiffrées du modèle et inventaire Salomé

## 1. Inventaire des valeurs numériques (étape 4)

Fichier : `data/examples/combiwall_model_data.yaml` (schéma Pydantic
`aster_expert.agent.model_data`). Sources : cas de test v2
(`combiwall_inputs/cas_test_quai_combiwall_v2.md`, recopié du dossier d'échange),
delta v3 (`cas_test_quai_combiwall_v3_delta.md` — le cas de test v3 est v2 modifié
par ce delta, il n'existe pas de fichier v3 complet), décisions et constats de la
fiche arbitrée (`point_label`). Les valeurs gardent l'unité de leur source (MN, kN,
cm, mm, degrés) : la conversion en unités du modèle (m, N, Pa, kg) est à la charge du
générateur (décision du point 9) ; aucune valeur n'est calculée, convertie ni
déduite dans le fichier. Une valeur approchée dans sa source (« ≈ », « environ »)
est recopiée telle quelle et le dit dans son commentaire.

Valeurs présentes des sources et **non reprises**, parce que hors du modèle en
tranche : longueur de quai (120,00 m), nombre de tubes sur 120 m (47), hauteur libre
(16,00 m, dérivée), stratigraphie complète (γ, γ', φ', c', cu, E_M et k_h des trois
couches au-dessus du dragage : entrées du calcul amont des profils), marnage
(+3,50 / −0,50), surcharges Q1 (40 et 60 kPa : entrent par le profil calculé en
amont, décision du point 5), composante hors plan de 15° de l'effort d'amarrage
(supprimée, décision du point 7), ancienne ligne « profil en Z, module 1800 cm³/m »
(remplacée par le delta v3).

Total : 108 valeurs, dont 86 fournies et 22 à fournir.

### repere (3 fournies, 0 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `repere.x_face_coupe_gauche` | -10.4 | m | décision, point 9 |
| `repere.x_face_coupe_droite` | 10.4 | m | décision, point 9 |
| `repere.x_serrure_par_rapport_axe_tube` | 0.71 | m | décision, point 9 |

### geometrie (10 fournies, 2 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `geometrie.longueur_tranche` | 20.8 | m | cas de test delta v3 §1 |
| `geometrie.entraxe_tubes` | 2.6 | m | cas de test v2 §2 |
| `geometrie.nombre_entraxes_tranche` | 8 | - | décision, point 7 |
| `geometrie.nombre_tubes_entiers` | 7 | - | décision, point 7 |
| `geometrie.nombre_demi_tubes` | 2 | - | décision, point 7 |
| `geometrie.nombre_palplanches_intercalaires` | 8 | - | décision, point 7 |
| `geometrie.cote_arase_terre_plein` | 4.0 | m CM | cas de test v2 §1 |
| `geometrie.cote_dragage` | -12.0 | m CM | cas de test v2 §1 |
| `geometrie.cote_pied_tubes` | -26.0 | m CM | cas de test v2 §1 |
| `geometrie.cote_pied_palplanches` | -18.0 | m CM | cas de test v2 §1 |

### tube (5 fournies, 4 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `tube.diametre_exterieur` | 1420 | mm | cas de test v2 §2 |
| `tube.rayon` | 0.71 | m | cas de test delta v3 §7 |
| `tube.epaisseur_nominale` | 16 | mm | cas de test v2 §2 |
| `tube.surepaisseur_corrosion` | 2.0 | mm | cas de test v2 §2 |
| `tube.nuance_acier` | S355 | - | cas de test v2 §2 |

### palplanche (28 fournies, 0 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `palplanche.periode` | 1.18 | m | cas de test delta v3 §2 |
| `palplanche.hauteur_profil` | 0.45 | m | cas de test delta v3 §2 |
| `palplanche.largeur_semelles` | 0.35 | m | cas de test delta v3 §2 |
| `palplanche.epaisseur` | 9.5 | mm | cas de test delta v3 §2 |
| `palplanche.inclinaison_ames` | 62 | deg | cas de test delta v3 §2 |
| `palplanche.longueur_developpee_par_periode` | 1.72 | m | cas de test delta v3 §2 |
| `palplanche.inertie_par_metre` | 42400 | cm4/m | cas de test delta v3 §2 |
| `palplanche.module_flexion_par_metre` | 1845 | cm3/m | cas de test delta v3 §2 |
| `palplanche.masse_surfacique_plan_ecran` | 109 | kg/m2 | cas de test delta v3 §2 |
| `palplanche.nuance_acier` | S355 | - | cas de test v2 §2 |
| `palplanche.module_young` | 210000 | MPa | décision, point 1 |
| `palplanche.coefficient_poisson` | 0.3 | - | décision, point 1 |
| `palplanche.module_cisaillement` | 80770 | MPa | décision, point 1 |
| `palplanche.masse_volumique` | 7850 | kg/m3 | décision, point 1 |
| `palplanche.rapport_developpee_sur_periode` | 1.458 | - | décision, point 1 |
| `palplanche.epaisseur_coque_EPAIS` | 13.85 | mm | décision, point 1 |
| `palplanche.masse_surfacique_rho_epais` | 108.7 | kg/m2 | décision, point 1 |
| `palplanche.MEMB_L` | 2908 | MN/m | décision, point 1 |
| `palplanche.MEMB_T` | 0.081 | MN/m | décision, point 1 |
| `palplanche.MEMB_G_LT` | 526 | MN/m | décision, point 1 |
| `palplanche.MEMB_LT` | 0 | MN/m | décision, point 1 |
| `palplanche.FLEX_L` | 89.0 | MN.m2/m | décision, point 1 |
| `palplanche.FLEX_T` | 0.0113 | MN.m2/m | décision, point 1 |
| `palplanche.FLEX_G_LT` | 0.0084 | MN.m2/m | décision, point 1 |
| `palplanche.FLEX_LT` | 0 | MN.m2/m | décision, point 1 |
| `palplanche.CISA_L` | 526 | MN/m | décision, point 1 |
| `palplanche.CISA_T` | 526 | MN/m | décision, point 1 |
| `palplanche.vecteur_axe_L` | (0.0, 0.0, 1.0) | - | constat, point 1 |

### poutre_couronnement (7 fournies, 4 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `poutre_couronnement.largeur` | 2.5 | m | cas de test v2 §3 |
| `poutre_couronnement.hauteur` | 1.4 | m | cas de test v2 §3 |
| `poutre_couronnement.cote_sous_face` | 2.6 | m CM | cas de test v2 §3 |
| `poutre_couronnement.cote_arase` | 4.0 | m CM | cas de test v2 §3 |
| `poutre_couronnement.cote_centre_gravite` | 3.3 | m CM | décision, point 8 |
| `poutre_couronnement.encastrement_tubes` | 0.8 | m | cas de test v2 §3 |
| `poutre_couronnement.beton` | C35/45 | - | cas de test v2 §3 |

### tirants (12 fournies, 2 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `tirants.diametre` | 75 | mm | cas de test v2 §4 |
| `tirants.nuance` | 500/700 | - | cas de test v2 §4 |
| `tirants.module_young` | 210000 | MPa | cas de test v2 §4 |
| `tirants.entraxe` | 2.6 | m | cas de test v2 §4 |
| `tirants.inclinaison` | 20 | deg | cas de test v2 §4 |
| `tirants.cote_tete` | 2.5 | m CM | cas de test v2 §4 |
| `tirants.longueur_libre` | 22.0 | m | cas de test v2 §4 |
| `tirants.longueur_scellement` | 8.0 | m | cas de test v2 §4 |
| `tirants.diametre_scellement` | 200 | mm | cas de test v2 §4 |
| `tirants.longueur_modelisee` | 26.0 | m | décision, point 2 |
| `tirants.section_brute` | 44.2 | cm2 | décision, point 2 |
| `tirants.raideur_axiale` | 35.7 | MN/m | décision, point 2 |

### sol (4 fournies, 0 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `sol.k_h_argile_marneuse_raide` | 35 | MN/m3 | décision, point 4 |
| `sol.k_h_marne_compacte` | 80 | MN/m3 | décision, point 4 |
| `sol.cote_haut_ressorts` | -12.0 | m CM | décision, point 4 |
| `sol.cote_interface_argile_marne` | -18.0 | m CM | décision, point 4 |

### eau_terres (4 fournies, 4 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `eau_terres.differentiel_permanent` | 1.5 | m | décision, point 5 |
| `eau_terres.differentiel_accidentel` | 3.5 | m | décision, point 5 |
| `eau_terres.niveau_nappe_terre_normal` | 2.0 | m CM | cas de test v2 §6 |
| `eau_terres.niveau_nappe_terre_haut` | 3.0 | m CM | cas de test v2 §6 |

### charges (13 fournies, 1 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|
| `charges.amarrage_effort` | 1000 | kN | décision, point 8 |
| `charges.amarrage_inclinaison` | 30 | deg | décision, point 8 |
| `charges.amarrage_composante_horizontale` | 866 | kN | décision, point 8 |
| `charges.amarrage_cote_application` | 3.3 | m CM | décision, point 8 |
| `charges.amarrage_decalage_vertical` | 0.7 | m | décision, point 8 |
| `charges.amarrage_moment_transport` | 606 | kN.m | décision, point 8 |
| `charges.accostage_effort` | 800 | kN | décision, point 8 |
| `charges.accostage_cote_bas_empreinte` | 1.0 | m CM | cas de test delta v3 §7 |
| `charges.accostage_cote_haut_empreinte` | 2.0 | m CM | cas de test delta v3 §7 |
| `charges.accostage_demi_angle_empreinte` | 45 | deg | décision, point 8 |
| `charges.accostage_largeur_platine` | 1.0 | m | décision, point 8 |
| `charges.accostage_surface_empreinte_ideale` | 1.115 | m2 | décision, point 8 |
| `charges.accostage_intensite_indicative` | 717 | kN/m2 | décision, point 8 |

### maillage (0 fournies, 5 à fournir)

| Valeur | Donnée | Unité | Source |
|---|---|---|---|

## Valeurs à fournir

| Valeur | Unité | Point | Ce que les sources disent |
|---|---|---|---|
| `geometrie.cote_tete_tubes` | m CM | 3 | Le cas de test donne le pied des tubes, la sous-face (+2,60) et l'arase (+4,00) de la poutre et un encastrement de 0,80 m dans la poutre ; aucune source n'énonce la cote de tête du tube, dont la décision du point 3 exige l'anneau de nœuds supérieur. |
| `geometrie.cote_tete_palplanches` | m CM | 1 | Le cas de test donne le pied des palplanches intercalaires (-18,00), aucune source n'en donne la tête. |
| `tube.epaisseur_coque_retenue` | mm | 1 | Le cas de test donne l'épaisseur nominale et une surépaisseur de corrosion déduite sur la face bassin seulement ; aucune source ne dit quelle épaisseur de coque DKT (uniforme) en résulte. |
| `tube.module_young` | MPa | 1 | Les sources donnent E pour l'acier du profil de palplanche (décision du point 1) et pour les tirants (v2 §4), pas pour le tube ; la nuance est la même (S355) mais l'identité des propriétés n'est pas une décision enregistrée. |
| `tube.coefficient_poisson` | - | 1 | Idem module_young : donné pour le profil de palplanche (décision du point 1), non pour le tube. |
| `tube.masse_volumique` | kg/m3 | 1 | Idem module_young : 7 850 kg/m3 est donnée pour le profil de palplanche (décision du point 1), non pour le tube. |
| `poutre_couronnement.module_young` | MPa | 3 | Le cas de test nomme la classe de béton (C35/45) ; aucune source ne donne le module d'élasticité à retenir. |
| `poutre_couronnement.coefficient_poisson` | - | 3 | Aucune source ne donne le coefficient de Poisson du béton. |
| `poutre_couronnement.masse_volumique` | kg/m3 | 3 | Le poids propre de la poutre est une charge G (v2 §7) ; aucune source ne donne la masse volumique du béton. |
| `poutre_couronnement.position_axe_y` | m | 3 | L'effort d'amarrage est appliqué « sur l'axe de la poutre en plan » (décision du point 8) ; aucune source ne place cet axe par rapport au plan des axes des tubes (Y = 0, décision du point 9). |
| `tirants.masse_volumique` | kg/m3 | 2 | Le poids propre des tirants est une charge G (v2 §7) ; les sources donnent 7 850 kg/m3 pour le profil de palplanche seulement. |
| `tirants.position_tete_sur_tube` | deg | 2 | Le cas de test donne la cote de la tête (+2,50) « sur le tube » ; aucune source ne dit sur quelle génératrice de la section du tube (position angulaire) la barre est accrochée. |
| `eau_terres.profil_poussee_terres_permanent` | Pa en fonction de Z | 5 | La décision du point 5 dit le profil calculé hors Code_Aster (incrément de Q1 inclus) ; aucune source ne le chiffre. |
| `eau_terres.profil_pression_eau_permanent` | Pa en fonction de Z | 5 | Calculé hors Code_Aster (décision du point 5) pour un différentiel de 1,50 m ; aucune source ne le chiffre. |
| `eau_terres.profil_poussee_terres_accidentel` | Pa en fonction de Z | 5 | Aucune source ne dit si le profil des terres diffère en situation accidentelle ni ne le chiffre. |
| `eau_terres.profil_pression_eau_accidentel` | Pa en fonction de Z | 5 | Calculé hors Code_Aster (décision du point 5) pour un différentiel de 3,50 m ; aucune source ne le chiffre. |
| `charges.acceleration_pesanteur` | m/s2 | 0 | Le poids propre est une charge G (v2 §7) portée par les masses volumiques (décision du point 1) ; aucune source ne donne l'accélération de la pesanteur. La direction découle du repère du point 9 (Z ascendant). |
| `maillage.nombre_facettes_par_tube` | - | 1 | La décision du point 1 fixe la discrétisation angulaire dans la branche maillage ; aucune source ne la chiffre (aucun critère chiffré de facettisation dans la documentation, lot 20). Des nœuds sont requis sur les génératrices Y = 0 (serrures, point 9) et à ±45° de la génératrice tournée vers le bassin (empreinte DEFENSE, point 8) : déduction, à confirmer. |
| `maillage.nombre_divisions_verticales` | - | 1 | Aucune source ne chiffre le pas vertical des tubes et des palplanches (nœuds communs sur les lignes de serrure). Des nœuds sont requis aux cotes +1,00 et +2,00 (empreinte), -12,00 et -18,00 (ressorts) : déduction, à confirmer. |
| `maillage.nombre_elements_largeur_palplanche` | - | 1 | Aucune source ne chiffre la division de la palplanche intercalaire entre deux tubes (période de 1,18 m). |
| `maillage.nombre_elements_par_entraxe_poutre` | - | 3 | Aucune source ne chiffre la division de la poutre de couronnement. |
| `maillage.nombre_elements_par_tirant` | - | 2 | Aucune source ne chiffre la division des barres de 26,00 m. |

### Les profils de poussée et de pression d'eau (point 5) : confirmé absents

Hypothèse de MM confirmée. Les quatre profils
(`eau_terres.profil_poussee_terres_permanent`, `…_pression_eau_permanent`,
`…_poussee_terres_accidentel`, `…_pression_eau_accidentel`) sont absents de toutes
les sources : la décision du point 5 dit seulement qu'ils sont « calculés hors
Code_Aster » et donne les différentiels de nappe (1,50 m et 3,50 m) ; le cas de test
donne les niveaux d'eau et les paramètres de sol, pas les pressions. Ils n'ont pas
été calculés. Le nombre de profils (quatre) est lui-même une lecture : aucune source
ne dit si le profil des terres diffère entre situations permanente et accidentelle.

### Absences que l'inventaire a révélées au-delà des profils

Les sources ne donnent pas : la cote de tête des tubes et celle des palplanches
(seul le pied) ; l'épaisseur de coque retenue du tube (surépaisseur de corrosion
déduite sur la face bassin seulement) ; E, ν, ρ de l'acier du tube, du béton de la
poutre et de la barre du tirant (donnés pour l'acier du profil de palplanche
seulement) ; la position de l'axe de la poutre par rapport au plan des axes des
tubes ; la génératrice d'accrochage des tirants sur le tube ; l'accélération de la
pesanteur ; la discrétisation (facettes, divisions). Les cinq valeurs de
discrétisation portent, en commentaire, les nœuds que d'autres décisions imposent
(génératrices Y = 0 des serrures, ±45° de l'empreinte, cotes +1,00, +2,00, −12,00 et
−18,00) : ce sont des déductions, non des choix.

## 2. Contrôle de cohérence avec les décisions (étape 4.3)

`check_consistency` confronte chaque valeur fournie au texte de sa source : pour une
décision, l'`option_retained` des entrées pratique tranchées du `point_label` ; pour
un constat, l'`option_retained` du constat du sujet donné ; pour le cas de test, le
texte de la section citée. Notation française acceptée : virgule décimale, espace
(insécable ou fine) comme séparateur de milliers, signes `+`, `-`, `−`, `±`, petits
entiers écrits en lettres (« sept », « nuls »), tolérance = demi-unité du dernier
chiffre affiché.

**Résultat sur le fichier versionné : 0 écart** pour les 86 valeurs fournies. Le
contrôle est éprouvé (`tests/unit/test_model_data.py`) : une valeur altérée
(`tube.rayon` 0,72 ; `charges.amarrage_effort` 1200) est détectée. Limite : un nombre
présent ailleurs dans le texte de la source passe (le contrôle établit la présence
du nombre dans la source citée, non son rôle) ; un petit entier écrit en lettres est
reconnu par le mot, non par sa place dans la phrase.

## 3. Inventaire Salomé (étape 5, sans installation ni téléchargement)

Aucune installation, aucun téléchargement. Commandes lancées dans des conteneurs
isolés (`--network none` / `--net --network none`, `$HOME` non monté pour
Singularity), sans le lanceur `salome_meca` (dont le premier démarrage écrit un
fichier de configuration).

### 3.1 Salomé dans la VM (natif)

Aucune installation native : ni `salome`, ni `salome_meca` dans le `PATH`, aucun
paquet `dpkg` Salomé/SMESH/MEDCoupling/libmed, aucun module Python
`medcoupling`/`MEDLoader`/`med`/`h5py`/`meshio` ni dans `.venv` (Python 3.12.3) ni
dans `/usr/bin/python3`.

Salomé-Méca est présent sous forme de **conteneur Singularity** :

- image `/home/ubuntu/Desktop/salome_meca.sif` (5,3 Gio, datée du 2026-03-02), lanceur
  Python `/home/ubuntu/Desktop/salome_meca` (`NAME = salome_meca-lgpl-2024`) ;
- `singularity-ce 4.3.7-noble` installé (`/usr/bin/singularity`) ;
- version (`README` de l'image) : **salome_meca V2024.1.0_scibian_univ**, plate-forme
  Scibian 11.1, recette « Salome: Meca LGPL » de l'équipe code_aster, construite le
  2025-01-02 ; plate-forme SALOME `Cea_archive-9120` ; Python 3.9.2 dans l'image ;
  modules `ASTERSTUDY_202410` et `EUROPLEXUS_202410`.

Mode d'exécution sans interface : le lanceur documente le mode texte (`-t`) et
`shell`. **Vérifié par exécution** (`singularity exec --containall --cleanenv
--no-home --net --network none`, environnement de `salome_prerequisites.sh` et
`salome_modules.sh` chargé) : `salome -t --shutdown-servers=1 script.py` exécute un
script GEOM + SMESH sans interface ; un script d'essai (boîte 1 × 1 × 1, 2 segments,
quadrangles) a imprimé `PROBE_MESH_OK True 24 26` (Compute vrai, 24 faces, 26 nœuds).
Le script d'essai est resté hors dépôt (répertoire de travail de la session).

Modules Python de l'image Salomé (Python 3.9, environnement chargé) : `GEOM`, `SMESH`,
`salome`, `salome.geom`, `salome.smesh`, `medcoupling`, `MEDLoader`, `MEDCoupling`,
`med` (medfile), `h5py` ; absent : `meshio`.
Chemins : `…/BINARIES-DB11/GEOM`, `SMESH`, `KERNEL`, `MEDCOUPLING`, `medfile`,
`Cea_h5py-280` sous `/opt/salome_meca/V2024.1.0_scibian_univ/prerequisites/Cea_archive-9120/`.

Des scripts Salomé de MM existent dans la VM (`~/salome_create_radier.py`,
`~/Downloads/salome_*.py`, fichiers `.med` sur `~/Desktop`) ; ils n'ont pas été lus,
seule leur présence est relevée.

### 3.2 L'image Docker de `cave` (`simvia/code_aster@sha256:d8d19ea9…`, 17.4.0)

**Ne contient pas Salomé** : aucun module `GEOM`, `SMESH`, `salome` (Python d'Aster ni
Python système), aucun exécutable `salome`/`salome_meca`, aucun fichier au nom
`*salome*`/`*smesh*` dans le système de fichiers (seuls existent les paquets Spack de
`medcoupling`).

**Contient MEDCoupling/MEDLoader** : `medcoupling.py` et `MEDLoader.py` dans
`/opt/spack/var/spack/environments/simvia_env/.spack-env/view/lib/python3.11/site-packages`,
importables par le Python d'Aster (3.11.14, avec le `PYTHONPATH` de la vue Spack) et
par le Python système du conteneur (3.11.2) ; bibliothèques `libmed.so.11`,
`libmedC.so.11`, `libmedloader.so`, `libmedimport.so` sous `…/.spack-env/view/lib`.
Absents : `med` (medfile Python), `h5py`, `meshio`. (`code_aster` n'est pas importable
sans `profile.sh`, ce qui est normal : le mécanisme du projet le source.)

### 3.3 Modules de lecture MED : synthèse

| Où | Modules |
| --- | --- |
| VM, `.venv` et Python système (3.12.3) | aucun |
| Image Docker `simvia/code_aster:17.4.0` | `medcoupling`, `MEDLoader` (Python 3.11 d'Aster et système) |
| Image Singularity `salome_meca.sif` (Python 3.9) | `medcoupling`, `MEDLoader`, `MEDCoupling`, `med`, `h5py` |

### 3.4 Autres images

- Docker : `simvia/code_aster:16.8.0` (id `e0d78ea06146`, aussi étiquetée `stable`),
  `simvia/code_aster:17.4.0` (id `6a66bdaf0942`), `hello-world`. **Aucune autre image
  Salomé-Méca dans Docker.**
- Singularity : `~/Desktop/salome_meca.sif` (ci-dessus). Les autres `.sif` de la VM
  (`~/singularity/test/…`, `~/singularity/e2e/…`) sont les images de test du dépôt
  source de Singularity, sans rapport avec Salomé.

L'image `simvia/code_aster:16.8.0` n'a pas été interrogée (hors périmètre : le projet
cible 17.4.0, principe 1 de CLAUDE.md).
