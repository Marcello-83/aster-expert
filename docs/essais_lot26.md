# Lot 26 — Chaîne Salomé, vérificateur de maillage, lecture par Code_Aster

Rapport d'essai selon `docs/modele_rapport_essai.md`. Niveau visé : C pour la
lecture par Code_Aster (exécution jusqu'à `FIN`), D pour le contrôle des aires et
longueurs de groupes (grandeurs exactes de la géométrie).

## Objet

Qualifier, sur trois géométries simples, la chaîne : script Salomé paramétré →
`aster-expert mesh run` → MED → `aster-expert mesh check` (lecture par
`medcoupling` dans l'image Docker de `cave`, sans Salomé) → lecture par Code_Aster
17.4.0 (`aster-expert run`). Le maillage du quai est l'objet du lot 27.

## Critère de réussite (écrit avant l'exécution)

### Vérificateur de maillage (`mesh check`)

Les valeurs attendues sont calculées **analytiquement** par
`scripts/build_lot26_essais.py` à partir des paramètres (maillages structurés de
quadrangles plans), écrites dans `invariants.yaml` **avant** tout lancement de
Salomé pour G2 et G3, et jamais relues d'un MED produit.

| Grandeur | Attendu | Nature | Seuil de réussite |
| --- | --- | --- | --- |
| G1 nœuds / QUAD4 / SEG2 | 25 / 16 / 20 | exacte (entiers) | égalité |
| G2 nœuds / QUAD4 / SEG2 | 836 / 792 / 976 | exacte (entiers) | égalité |
| G3 nœuds / QUAD4 / SEG2 | 19 / 8 / 16 | exacte (entiers) | égalité |
| Cardinalité, type et boîte englobante de chaque groupe | voir `invariants.yaml` | exacte | égalité ; boîtes à 1e-9 m |
| Nœuds partagés aux interfaces (G1 : 5 ; G2 : 19 par serrure ; G3 : 1 et 1) | voir `invariants.yaml` | exacte | égalité, aux points indiqués à 1e-9 m |
| Nœuds orphelins ; paires de nœuds distants de moins de 1e-9 m | 0 | exacte | égalité |

Pour chaque géométrie, la variante altérée doit être **rejetée** (code de sortie 1)
et le rapport doit désigner au moins un invariant en écart :

- G1 : partition remplacée par un composé (`MakeCompound`) ;
- G2 : 36 facettes au lieu de 40 ; cote +1,00 retirée de la liste des cotes ;
- G3 : barre hors de la partition (composé).

Les MED nominaux doivent tenir tous leurs invariants. Un MED nominal en écart est
un échec de la chaîne, rapporté tel quel.

### Lecture par Code_Aster

Pour chaque MED nominal versionné : `LIRE_MAILLAGE(FORMAT='MED', INFO=2)`,
`AFFE_MODELE` sur chaque groupe (DKT pour les coques, BARRE pour les segments,
POU_D_E pour la poutre), `AFFE_CARA_ELEM` unitaire (`EPAIS = 1`, `A = 1`),
`DEFI_MATERIAU` avec `RHO = 1`, puis `POST_ELEM(MASS_INER)` par groupe : la
masse d'un groupe est alors son aire (coque) ou sa longueur (barre, poutre),
grandeur **exacte** (`data/examples/lot26_essais/aster_expected.json`).

| Grandeur | Attendu | Nature | Seuil de réussite |
| --- | --- | --- | --- |
| Statut de l'exécution | `completed_ok` ou `completed_with_alarms` (toute alarme est listée et expliquée, jamais neutralisée) | — | jusqu'à `FIN` |
| Masse de chaque groupe (9 + 3 + 3 groupes) | aire ou longueur du groupe | exacte | 1e-6 en relatif |

Le niveau B de chaque `.comm` est établi (`validate_comm`) avant l'exécution.
Toute autre issue est un échec, rapporté tel quel.

## Modèle et exécution

- Salomé-Méca `V2024.1.0_scibian_univ` (lue dans l'image), image
  `~/Desktop/salome_meca.sif`, SHA-256
  `48beffc5062a2701be2a5af9a52124b1ff1a0b674445408dcdbb61d056094326`.
- Scripts : `scripts/salome/lot26_*.py` ; paramètres et invariants :
  `data/examples/lot26_essais/<géométrie>/` (produits par
  `scripts/build_lot26_essais.py`) ; rapports d'exécution et de contrôle :
  `data/examples/lot26_essais/rapports/` ; MED : `<géométrie>/med/`.
- Noms et signatures GEOM/SMESH relevés par introspection :
  `data/examples/lot26_essais/signatures_geom_smesh.txt` (sonde
  `scripts/salome/lot26_sonde_signatures.py`, sortie `LOT26_PROBE_OK`).
- Lecture par Code_Aster 17.4.0 (image `simvia/code_aster`, digest
  `sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`) :
  `aster-expert run` sur `<géométrie>/aster/lot26_gN.comm` ; listings dans `mess/`,
  analyse dans `analyse.json` (`scripts/analyze_lot26_essais.py`).

## Résultats

### Premier lancement de G3 : échec de la chaîne, rapporté tel quel

Le premier `mesh check` du G3 nominal a échoué : 9 invariants en écart (15 nœuds au
lieu de 19, groupes `POUTRE` et `BARRE` absents). Cause établie : l'appel de
`MakePartition` passait `1` en 6ᵉ position, qui est `RemoveWebs`, et non
`KeepNonlimitShapes` (8ᵉ) — la sonde de signatures l'a montré. Les arêtes isolées
avaient donc disparu de la partition. Le vérificateur a détecté le défaut du script ;
l'appel a été corrigé (`FACE, 0, [], 1`), et les sept exécutions ont été relancées
avec les scripts corrigés (les résultats ci-dessous sont ceux de ces exécutions).

### `mesh check`

| Cas | Invariants | Tenus | En écart | Premier invariant non tenu |
| --- | --- | --- | --- | --- |
| G1 nominal | 23 | 23 | 0 | — |
| G1 sans partition (composé) | 23 | 15 | 8 | nombre de nœuds (30 au lieu de 25) |
| G2 nominal | 45 | 45 | 0 | — |
| G2, 36 facettes | 45 | 40 | 5 | nombre de nœuds (760 au lieu de 836) |
| G2, cote +1,00 retirée | 45 | 44 | 1 | mailles par type (SEG2 932 au lieu de 976) |
| G3 nominal | 24 | 24 | 0 | — |
| G3, barre hors partition | 24 | 20 | 4 | nombre de nœuds (20 au lieu de 19) |

Rapports complets : `rapports/<cas>_check.txt`. Faits notables :

- G1 sans partition : 0 nœud partagé au lieu de 5 sur l'arête, 5 paires de nœuds
  confondus non fusionnés.
- G3, barre hors partition : 0 nœud partagé entre `BARRE` et `COQUE` (attendu 1) et
  1 paire de nœuds confondus non fusionnés, exactement le défaut décrit dans la
  consigne (nœud superposé sans être relié).
- G2, cote +1,00 retirée : seul le nombre de SEG2 change (932 contre 976). Les nœuds
  sont identiques, car toutes les longueurs sont multiples de la taille 0,25 : un nœud
  existe à +1,00 sans la coupe. La détection repose donc sur le comptage des segments ;
  **le contrôle « nœud à la cote imposée » ne suffit pas seul** dans ce cas.
- G2, 36 facettes (variante écartée de la décision 11) : le groupe `EMPREINTE` tombe à
  144 mailles et sa boîte englobante à ±0,4564 m en X (attendu ±0,5020 m).

### Lecture par Code_Aster (`aster-expert run`)

Niveau B de chaque `.comm` établi avant exécution (`validate_comm` : `valid=true`, 0
commande non confrontée). Exécution : `completed_ok`, diagnostic `OK`, pour G1, G2 et
G3, sans alarme.

| Cas | Nœuds lus | Mailles lues | Groupes (cardinalités) | Erreur relative max sur les masses |
| --- | --- | --- | --- | --- |
| G1 | 25 | 36 (SEG2 20, QUAD4 16) | 8 / 8 / 4 | 0 |
| G2 | 836 | 1768 (SEG2 976, QUAD4 792) | 720 / 36 / 36 / 180 / 18 / 18 | 1,4e-13 |
| G3 | 19 | 24 (SEG2 16, QUAD4 8) | 8 / 2 / 2 | 0 |

## Verdict

Au regard du seul critère ci-dessus :

- invariants des trois MED nominaux : **réussite** (23, 45 et 24 sur 24) ;
- rejet des quatre variantes altérées : **réussite** ;
- exécution jusqu'à `FIN` des trois lectures : **réussite** (niveau C) ;
- masses de groupes à 1e-6 : **réussite** (niveau D pour cette grandeur exacte).

## Lecture

Faits : les comptages analytiques, écrits avant l'exécution, sont ceux des MED
produits ; Code_Aster retrouve les groupes, leurs cardinalités et leurs contenus
géométriques (aires et longueurs) à la précision machine. Le premier essai de G3 a
révélé un défaut du script que seul le vérificateur a signalé (Salomé sortait sans
erreur avec un MED privé de la poutre et de la barre).

Déduction : un script Salomé qui sort sans erreur ne dit rien de son résultat ;
`mesh check` est le contrôle qui compte.

Recommandations : pour le lot 27, écrire les invariants du quai avant le script ; y
inclure un comptage des SEG2 et des groupes d'arêtes aux cotes imposées.

## Limites

- Aucun cas de longueur non multiple de la taille visée : la règle d'arrondi de
  `LocalLength` n'est pas qualifiée (les cotes réelles +2,50 / +2,60 en donnent un).
- La connexion barre/coque est établie sur le MED (nœud partagé), non par un calcul
  de rigidité dans Code_Aster.
- Coques planes uniquement (pas de coque courbe, pas de TRIA3, pas de maillage 3D).
- L'empreinte de l'image Salomé est mise en cache (chemin, taille, date de
  modification) : le rapport indique `computed` ou `cache`.
- Le fichier de données complémentaires de MM porte encore `[À CONFIRMER MM]` :
  l'étape 1 (décision 11, 22 valeurs) n'est pas faite.
