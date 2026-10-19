# Lot 52 — Pontons aluminium : géométrie PRO (B12, treillis constructible, appui v4) et recalcul complet

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-52`, depuis `main` après la
fusion de `lot-51quater`. Consigne : `docs/lots/lot52_consigne.md`. Essais : `docs/essais_lot52.md`,
critère commité au point d'arrêt `dc46aa5`, avant toute exécution Code_Aster, et non modifié depuis.
Niveau des résultats : **D** ; aucun niveau E. Calcul linéaire ; ni EC9, ni béton armé, ni appareil
d'appui ; aucun ancrage modélisé ; aucun autre projet modifié.

## Décisions P62 à P66

Enregistrées depuis `donnees/sources/enregistrement_P62_P66_lot52.md` (textes extraits de la consigne,
vérifiés à l'identique) ; P53 et P54 ré-arbitrées ; fiche régénérée : 76 entrées.

- **P62** : HU, HD et HU_IMP restent dans l'ELS caractéristique du critère de flèche (P37, P51 inchangés).
- **P63** : poutres 200 × 200 × 12 ; pannes 50 × 50 × 5 (sensibilité × 4) ; montants et diagonales
  120 × 120 × 6, 6082-T6 (zone adoucie 120 + 2 × 30 = 180 mm < 200 mm).
- **P64** : montants et diagonales sous les pannes, axe +1,29 ; montant relié au nœud de la poutre
  (+1,30) par une liaison rigide de 0,01 m ; pannes (+1,375) posées sur les montants et les
  diagonales par une liaison de 0,085 m ; nœud diagonale–montant à e = 0,25 m (|Y| = 0,68), dessin en
  N conservé, tronçon de montant entre la poutre et ce nœud exporté (groupe MONTANTS_TRONCONS).
- **P65** : axe des appuis à +1,175 ; liaisons inchangées (oreilles en translation et DRX, Z bloqué, Y
  bloqué côté YP, X libre).
- **P66** : défenses Delta continues, μ = 0,7 inchangé.

Coefficients P60 des pannes de 50 : HU = 4,92 HU_TUBES + 1,91 HU_PANNES + 0,90 HU_PLATELAGE ;
HD = 1,01 HD_TABLIER ; HU_IMP_Mk = 5,9 × (somme des trois cas du module).

## Géométrie des nœuds (`geometrie_noeuds.csv`, identique pour les trois variantes)

| Croisement | Nombre | Liaison | Jeu (mm) | Zone de soudure |
|---|---|---|---|---|
| panne / montant | 160 | 0,085 m | 0,0 (pose directe) | — |
| panne / diagonale | 120 | 0,085 m | 0,0 (pose directe) | — |
| montant / poutre | 80 | 0,01 m | marge de 30,0 en haut et en bas dans le flanc | 180 mm |
| panne / panne de rive (porte-à-faux) | 4 | 0,075 m | 25,0 | — |

**Aucun recouvrement ; zone de soudure maximale 180 mm ≤ 200 mm.**

## Harnais et contrôles

- `mesh check` 4 011/4 011 (géométries A et B) ; niveau B `valide` 1 616/1 616 ; trois exécutions
  `completed_ok`, 0 alarme (376 à 404 s).
- Harnais D : **221/221** par variante (écart ≤ 7,4·10⁻¹¹ ; TP, TM ≤ 3,9·10⁻⁷ N).
- Résultantes de HU, HD et HU_IMP_Mk : écart 0 à la formule, réactions ≤ 3,8·10⁻¹².
- Somme des modules contre le cas total : ≤ 1,5·10⁻¹¹ × max |u|.
- AM1 : ΣRX des palées ≤ 7,6·10⁻⁸ N (≤ 2,8·10⁻¹³ relatif).
- TP : DX de l'axe de P5 = 41,094 mm contre α·ΔT·38,85 = 41,103 mm (0,023 %).
- Énumération de contrôle (B52, 36 extrêmes, graine 52) : ≤ 5,1·10⁻¹⁶ contre `recombiner.py` et contre
  l'énumération explicite ; 2 364 008 combinaisons, aucune violation.
- `.npz` : lecteur indépendant 20/20.

## Comparaison B52 contre B12 du lot 51 quater

| Grandeur | B52 | B12 | Écart |
|---|---|---|---|
| Flèche ELS fréquent T2 (mm ; L/f) | −21,5 (L/290) | −20,7 (L/302) | +3,9 % |
| Flèche ELS caractéristique T2 (mm ; L/f) | 38,8 (L/161) | 38,2 (L/164) | +1,5 % |
| Flèche ELS caractéristique T5 (mm) | 29,1 | 27,8 | +4,8 % |
| PP My (kN·m) | −71,8 | −69,3 | +3,6 % |
| PP Mz (kN·m) | 17,6 | 17,1 | +3,4 % |
| Glissement des axes ELU (mm) | 110,3 | 114,3 | −3,5 % |
| Culée ΣRX ELU (kN) | 435,7 | 435,7 | 0 |
| Culée RX d'un axe (kN) | −301,7 | +312,6 | changement de signe |
| Ancrage ELU, P1 / P2 / P3 (kN) | 23,2 / 11,1 / 5,7 | 22,7 / 10,0 / 4,6 | +0,4 à +1,1 kN |
| Chevêtres T (kN·m) | 4,14 | 3,96 | +4,6 % |
| Montants Mz / V (kN·m, kN) | 11,5 / 56,0 | — | nouveau |

- **Flèches** : +3,9 à +5,4 % à l'ELS fréquent et +1,5 à +4,8 % à l'ELS caractéristique. C'est
  attendu : le treillis descend sous l'axe des poutres et ses sections sont plus petites (120 × 6 au
  lieu de 150 × 7).
- **Poutres** : My et Mz augmentent de 3 à 4 %, vraisemblablement pour la même raison (déduction, non
  isolée par un calcul).
- **Glissement des axes** : il diminue de 3,5 %. Explication probable, non isolée par un calcul :
  l'axe remonte à +1,175 et le tablier est plus léger.
- **Culée** : ΣRX est inchangé, car il est fixé par l'amarrage AM1. L'extrême signé de RX sur un axe
  change de signe, avec un module voisin : la combinaison qui gouverne passe d'une composante à l'autre.
- **Ancrage** : quasi inchangé, +0,4 à +1,1 kN par palée. L'écart, identique de P2 à P4 sous HU_S5,
  est compatible avec la baisse du poids propre (pannes de 50, montants plus légers). Les +11 et +24 %
  de P2 et P3 portent sur de petites valeurs.
- **Montants** : leur flexion est nouvelle. Tous leurs extrêmes tombent dans les tronçons entre la
  poutre et le nœud de diagonale, comme le prévoit P64.
- **Porte-à-faux** : l'extrême signé de la flèche caractéristique change de signe (−1,1 mm contre
  +1,0 mm). L'écart est sans portée (L/2 248).

## Ancrage par palée (kN, ELU / ELS caractéristique ; HU_S5 entre parenthèses)

| Palée | B52 | A52 | B52P4 |
|---|---|---|---|
| P1 | 23,2 / 0 (56,2 / 6,0) | 21,2 / 0 (54,3 / 3,6) | 23,3 / 0 (56,4 / 6,1) |
| P2 | 11,1 / 0 (44,2 / 0) | 10,6 / 0 (43,7 / 0) | 11,2 / 0 (44,3 / 0) |
| P3 | 5,7 / 0 (38,8 / 0) | 5,7 / 0 (38,8 / 0) | 5,8 / 0 (38,9 / 0) |
| P4 | 0 / 0 (28,9 / 0) | 0 / 0 (30,9 / 0) | 0 / 0 (29,1 / 0) |
| P5 | 0 / 0 (3,6 / 0) | 0 / 0 (1,2 / 0) | 0 / 0 (3,7 / 0) |

## Temps de recombinaison

Par variante, avec deux processus : 597 s (A52), 611 s (B52) et 679 s (B52P4). La comparaison en
représente 588 à 666 s, la lecture des tables 13 à 15 s et les exports 9 à 16 s. L'énumération de
contrôle de B52 prend 50 s. Le lot 51 quater donnait 280 à 290 s avec quatre processus.

## PNG vérifiés à l'œil

Les 12 PNG de B52 (vues 1 à 6, 7.1 à 7.4, 8, 9) font 1 920 × 1 080 et ne sont pas vides. J'ai regardé
les vues 4, 6, 8 et 9 :
- **Vue 9** : les pannes posent sur le montant et sur la diagonale, sans pénétration ; le montant
  aboute le flanc de la poutre.
- **Vue 8** : dessin en N, nœuds à |Y| = 0,68. Les étiquettes de PT1, d'abord sous la légende, ont été
  déplacées puis les vues ont été régénérées.
- **Vue 6** : axe Ø 24 dessiné comme une barre selon Y à +1,175, étrier en T du schéma v4.

## MED (B52)

`structure.med`, `charges.med` et `resultats.med` sont écrits en MED 3.3. Le contrôle de relecture est
réussi :
- 221 cas unitaires relus contre les tables E25.16 : écart 0 ;
- combinaisons relues contre les tables : écart 0 ;
- relecture des fichiers écrits : écart nul.

**Défaut du lot 51 quater corrigé.** `resultats.med` porte un second maillage, `PONTON_B52_ELNO`
(4 552 nœuds, 2 276 SEG2, 25 groupes), où chaque barre a ses deux nœuds propres. Le DEPL et les efforts
N, VY, VZ, MT, MFY et MFZ y sont deux champs aux nœuds du même support, ce qui permet de colorer la
déformée par composante d'effort. Les champs du maillage d'origine sont conservés. Le script ParaVis
adapté est `afficher_pontons_salome_52.py`.

## Dépôt

`/media/sf_partage/echanges/lot52/pontons_alu_01/` contient 75 fichiers (85 Mo) et
`empreintes.sha256`. Les CSV de plus de 100 Mo ne sont pas déposés : les déplacements élémentaires des
trois variantes et les efforts élémentaires de B52.

## Interruption

Le 19/10/2026 à 04:25, la VM s'est arrêtée sur un blocage du noyau, processeur saturé. Trois processus
de recombinaison tournaient alors en même temps que le post-traitement Code_Aster des livrables de B52.

Ce qui a été perdu :
- le post-traitement, classé « écarté » dans `rex` ;
- les exports en cours.

La reprise a eu lieu en série, sans changer les `.comm`. Les exécutions de calcul et le harnais D,
terminés avant l'arrêt, sont conservés.

## `rex` et interventions

```
Retour d'expérience du projet pontons_alu_01
Exécutions attribuées au projet : 49 ; échecs : 2 ; depuis le dernier retour d'expérience (2026-10-16) : 1.
Développement : 43 exécution(s), 2 échec(s), taux 4,7 % ; vérification : 6 exécution(s), 0 échec(s) (hors taux).
Classement : nouveau 1, écarté 1.
Diagnostic retrouvé automatiquement par la base (seul et égal au classement) : 0/1 échecs rattachés.
Répartition par cause : DIAG-030 1, écarté 1.
Constats de la fiche à verser dans la base : 0.
Candidats patrons dans le code du projet : 0 (similarité ≥ 0,40 ; 23 fonction(s) sous le seuil, non listées).
Connaissances créées par le projet : 3 ; promues : 0.
Consultations journalisées (tous projets) : search_connaissances 72, search_constats 3.
Tous les échecs sont classés : clôture possible.
```

- **Interventions de MM** : une relance après l'arrêt de la VM. Aucune question technique.
- **Connaissance qui a évité une erreur** : CA-036. Le REAC_NODA des extrémités des nouvelles liaisons
  LM_ est replié sur les nœuds de la culée et des oreilles.

## Limites

- Les liaisons rigides ne représentent pas la souplesse des parois soudées ; le moment des tronçons de
  montant en dépend.
- La panne de rive du porte-à-faux est inchangée (hors P64).
- La comparaison avec B12 mélange trois changements, qui ne sont pas séparés.
- Niveau D au mieux.
