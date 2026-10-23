# Lot 54 — Pontons aluminium : géométrie PRO définitive (treillis régulier, chevêtres 0,60), houle 5 kPa, recalcul complet

Profil `vm` (`env-check` OK). Branche `lot-54`, depuis `main` après la fusion de `lot-53`. Consigne :
`docs/lots/lot54_consigne.md` (v3). Essais : `docs/essais_lot54.md`, critère commité au point d'arrêt
`425101f`, avant toute exécution Code_Aster, et non modifié depuis. Niveau des résultats : **D** ;
aucun niveau E. Calcul linéaire ; ni EC9, ni béton armé, ni appareil d'appui ; aucun ancrage
modélisé ; aucun autre projet modifié.

**Clone neuf.** Le dépôt de la VM a été recloné le 23/10 à 03:32 : corpus, index, catalogue extrait,
`.env` et résultats non versionnés des lots précédents avaient disparu. Remise en état par les
commandes du dépôt (`docs/cloud.md` § 6). `mcp-check` : 9 outils sur 10 ; `query_results` échoue
faute de livrables locaux d'un projet (voir « Pour MM »).

## Décisions P67 à P76 et révisions de la fiche

Enregistrées par `aster-expert fiche enregistrer` depuis `donnees/sources/enregistrement_P67_P76_lot54.md`
(textes extraits par script de `consigne_lot54.md`) ; fiche régénérée : 86 entrées, identique à la
reconstruction par `scripts/fiche_lot50.py` ; groupe `houle_lot54` ajouté aux données.

| Nouvelle décision | Effet sur la fiche |
|---|---|
| P67 | P64 ré-arbitrée (montants à Xd + k × 1,25) ; ancienne version dans `decision_history` |
| P68 | P43 et P48 ré-arbitrées (chevêtres 0,60 × 0,40, Y = ±1,20) |
| P69 | P56, P60 et P62 ré-arbitrées ; P61 annulée (ancienne décision dans l'historique) |
| P70 | nouvelle entrée (règle de combinaison) |
| P71, P72 | confirment P48, P19, P58 (entrées nouvelles, modèle inchangé) |
| P73 à P76 | complètent P46, P45, P23 (entrées nouvelles, sans effet sur le calcul) |

`projet verifier` : déclaration cohérente, aucun bloqueur.

## Géométrie des nœuds (`geometrie_noeuds.csv`, B54 et A54)

| Croisement | Nombre | Liaison | Jeu (mm) | Zone de soudure |
|---|---|---|---|---|
| panne / montant | 160 | 0,085 m | 0,0 | — |
| panne / diagonale | 120 | 0,085 m | 0,0 | — |
| montant / poutre | 80 | 0,01 m | marge 30,0 | 180 mm |
| panne / panne de rive | 4 | 0,075 m | 25,0 | — |

Aucun recouvrement ; zone ≤ 200 mm. Les 25 diagonales des grandes travées mesurent toutes
1,847 m (écart 2·10⁻¹⁵ m sur les nœuds du maillage).

## Harnais et contrôles

- `mesh check` 4 011/4 011 ; niveau B `valide` 1 616/1 616 ; B54, A54 et B52 réexécuté `completed_ok`,
  0 alarme (257 à 283 s).
- Harnais D 221/221 par variante (≤ 1,5·10⁻¹⁰ ; TP, TM ≤ 5,5·10⁻⁷ N).
- Résultantes HU, HD, HU_F : exactes (≤ 1,5·10⁻¹⁶ à la formule, ≤ 1,4·10⁻¹² aux réactions).
- Chevêtre : 14,4 kN, écart 0. AM1 : ΣRX des palées ≤ 3,5·10⁻¹³. TP : 41,094 mm contre 41,103 mm
  (0,023 %). Linéarité ≤ 1,3·10⁻¹¹. `.npz` : 20/20.
- **B52 réexécuté** : `.comm` identique ; MED d'empreinte différente mais même contenu (nœuds,
  éléments, 6 035 952 efforts et 4 641 réactions égaux au dépôt du lot 52).

## Règle P70

- 1 920 paires d'événements interdites (AML ou AMF × AC ou ACA, même rive, centre de zone à moins
  de 1,60 m du taquet) : 40 couples taquet–zone, deux zones par taquet. Écrites dans
  `incompatibilites.csv`.
- Mise en œuvre : dans 14 branches, les emplacements AM et AC (ou ACA) sont maximisés
  conjointement sur les paires permises ; les autres restent indépendants. `recombiner.py` saute
  les mêmes paires.
- Effectifs : 2 247 920 combinaisons au lieu de 2 351 600, soit **103 680 exclues** ; égalité
  formule, `recombiner.py`, énumération ; 0 paire interdite énumérée.
- Énumération de contrôle : 36 extrêmes (graine 54), dont 27 dans des branches AM + AC, écart
  ≤ 5,8·10⁻¹⁶.
- Effet : 1 539 extrêmes sur 82 296 changés. Trois tirés au sort : panne T1 MFY 259,7 → 258,2 N·m ;
  panne T3 MFZ 49,0 → 48,5 N·m ; diagonale T4 MFZ (ELU accidentel) 941,8 → 873,2 N·m (−7,3 %).
  Aucune paire interdite avec la règle.

## B52 / B54 (`comparaison_B52_B54.csv`, B52 recombiné avec P69 et P70)

| Famille | Grandeur | B52 | B54 | Écart |
|---|---|---|---|---|
| Pannes | Mz (kN·m) | −0,54 | −0,42 | −22 % en module |
| Pannes | V (kN) | 8,06 | 6,11 | −24 % |
| Montants | My (kN·m) | 5,67 | 4,88 | −14 % |
| Diagonales | My (kN·m) | −4,92 | −4,25 | −14 % en module |
| Diagonales | V (kN) | 11,20 | 13,22 | +18 % |
| Longrines | N (kN) | ±0,62 | −0,53 / +0,67 | sans portée |
| Ancrage ELU | P1 à P4 (kN) | 56,2 à 29,0 | 51,1 à 23,7 | −5,2 kN par palée |

- **Pannes** : moins sollicitées, comme attendu (portée réduite à 1,25 m).
- **Montants** : N, Mz et V à ±3 % ; seul My baisse de 14 %.
- **Diagonales** : N et Mz du même ordre ; V augmente de 18 % près de la culée (DIAG_T1_1).
  Explication probable, non isolée par un calcul : diagonales plus courtes et plus raides.
  C'est un écart à l'attente « du même ordre », rapporté tel quel.
- **Ancrage** : baisse de 5,2 kN à chaque palée. Elle égale le poids déjaugé supplémentaire de
  l'anneau à l'ELU (calcul à la main : 0,9 × 25 × 0,416 − 10 × 0,416 = 5,2 kN).
- **Poutres, chevêtres, piles** : écarts inférieurs à 5 % (chevêtres My et V +4,9 %).

## Ancrage par palée et culée (kN ; ELU / ELS caractéristique)

| Palée | B54 | A54 |
|---|---|---|
| P1 | 51,1 / 0 | 49,1 / 0 |
| P2 | 39,0 / 0 | 38,5 / 0 |
| P3 | 33,6 / 0 | 33,6 / 0 |
| P4 | 23,7 / 0 | 25,7 / 0 |
| P5 | 0 / 0 | 0 / 0 |

Les valeurs ne sont données que pour mémoire (P71). Gouvernant : G_DEJ_090 + 1,5 HU.

Culée de B54 à l'ELU fondamental :
- ΣRX = 435,7 kN, inchangé ;
- RX d'un axe −300,8 kN ;
- RY ±75,6 kN ;
- RZ de −22,7 à +52,9 kN.

## Déplacements (B54)

À 0,2 mm près ceux de B52 au lot 53 :

| Grandeur | Valeur |
|---|---|
| DY du bout du porte-à-faux, ELU accidentel | 78,9 mm |
| DY du bout du porte-à-faux, ELS caractéristique | 55,9 mm |
| DY tête de P5, ELS caractéristique / ELU accidentel | 43,6 / 60,0 mm |
| DX de l'axe de P5 hors thermique, ELS caractéristique | 31,9 mm |

Flèches : T2 à l'ELS caractéristique −36,3 mm (L/172) ; soulèvement de T2 sous la houle +34,9 mm
(L/179).

## PNG vérifiés à l'œil

Treize vues (`vues/panneB_vue01` à `vue11C`) : fond blanc, 200 dpi, 16 cm de large au plus. Toutes
ont été regardées. Celles que la consigne désigne :
- **vue 4** : chevêtres 0,60 prolongés au-delà des appuis ; longrines entre les nus ;
- **vue 6** : chevêtre 0,60 × 0,40 de −1,20 à +1,20, appui, tube, pannes, platelage ;
- **vue 7** : cotes 0 / 1,25 / 2,50 / 3,75 / 5,00 / 6,25, nœuds à e = 0,25 ;
- **vue 11** : valeurs aux palées en tableau sous le dessin.

Corrections faites en cours de route :
- polices trop petites à 16 cm (canevas trop large) ;
- étiquettes qui se chevauchaient ;
- vues 3D trop petites.

## Dépôt

`/media/sf_partage/echanges/lot54/pontons_alu_01/` : 59 fichiers (31 Mo) et `empreintes.sha256`
(vérifiées). Contenu :
- `B54/`, `A54/` ;
- `comparaison_B52_B54.csv`, `comparaison_variantes.csv` ;
- `vues/` (13 PNG) ;
- `scripts/`.

Les CSV de plus de 100 Mo (déplacements et efforts élémentaires) ne sont pas déposés.

## `rex` et interventions

```
Retour d'expérience du projet pontons_alu_01
Archive d'exécution refusée : archive partielle : 3 exécution(s) du projet pour 49 au manifeste. Aucun échec examiné, métriques mesurées ni recalculées ni écrites ; seuls les champs déclarés (interventions, erreurs évitées, notes) sont mis à jour.
Constats de la fiche à verser dans la base : 0.
Candidats patrons dans le code du projet : 0 (similarité ≥ 0,40 ; 24 fonction(s) sous le seuil, non listées).
Connaissances créées par le projet : 3 ; promues : 0.
Consultations journalisées (tous projets) : search_connaissances 2, search_constats 0.
Champs déclarés seuls mis à jour : connaissances/metriques/pontons_alu_01.yaml
Revue non inscrite : archive d'exécution refusée.
```

- Le refus vient du clone neuf. Les trois exécutions du lot ont réussi : aucun échec à classer.
- **Interventions de MM** : aucune.
- **Connaissances** : CA-035 et DIAG-009 consultés avant la modification du déjaugeage ; aucune
  erreur évitée à attribuer. CA-036 reste appliqué.

## Pour MM

- **`mcp-check`** : pour qu'il passe en entier, il faut les livrables locaux d'au moins un projet
  (`aster-expert projet <nom> livrables`), absents du clone neuf.
- **`.env`** : le fichier local n'existe plus. J'ai utilisé
  `ASTER_CONTAINER_WORKROOT=data/processed/workroot`.

## Limites

- Les MED ne sont pas produits : la liste des exports ne les demande pas.
- Les liaisons rigides ne représentent pas la souplesse des parois soudées.
- La hausse de V des diagonales n'est pas isolée.
- Niveau D au mieux.
