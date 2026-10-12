# Lot 50 bis — PONTONS-ALU-01 : compte rendu

Profil `vm`, branche `lot-50bis` (depuis `main` après la fusion de `lot-50`). Essais :
`docs/essais_lot50bis.md` (critère et méthode commités avant les exécutions, e769f50).
Niveau atteint : **D** (harnais par défaut et un contrôle à la main), jamais plus.

## 1. Décisions P24 à P28 (fiche, 32 entrées)

Enregistrées depuis `donnees/sources/enregistrement_P24_P28_lot50bis.md`, texte cité vérifié à
l'identique dans la consigne.

- **P24** : tablier de 2,00 m, poutres principales en rive à Y = ±0,93 (B = 1,86 m), profilés
  supports à −0,93 ; 0 ; +0,93, chevêtre de −1,05 à +1,05 (**à confirmer par MM**), largeur
  chargée 2,00 m, poids des défenses négligé. Cette décision ne change que des paramètres du
  script, plus un paramètre `LARGEUR_TABLIER` : les bandes de rive vont jusqu'à ±1,00 et leur
  charge est appliquée sur l'axe de la poutre, ce qui néglige une excentricité de 0,07 m.
- **P25** : rotule Y = +0,93 fixe (DX, DY, DZ), rotule Y = −0,93 guidée (DY libre) : groupes
  `APP_QUAI_YP`, `APP_QUAI_YM`. La solution technologique reste à définir par MM.
- **P26** : pannes soudées aux montants et aux diagonales (P7 confirmé, sans changement).
- **P27** : jeu B′ = jeu B sans Q (ni Q½) en même temps que la houle, en post-traitement (1 602
  combinaisons sur 3 402). **Le choix entre B et B′ revient à MM** : les deux jeux sont livrés.
- **P28** : taux élastique simplifié. **C'est un indicateur de dimensionnement, pas une
  vérification EC9.** f0, f0,haz et γM1 = 1,10 sont dans le fichier de données (source P28).

## 2. Effet de P24 et P25 (jeu B, ELU fondamental)

| Grandeur | Lot 50 | Lot 50 bis |
| --- | --- | --- |
| Poutres principales, \|My\| max (kN·m) | 38,7 | 53,2 |
| Montants, N min / max (kN) | −456 / +277 | −66 / +52 |
| Montants, N sous T+ seul (kN) | −301 | −39 |
| Diagonales, N min / max (kN) | −101 / +74 | −70 / +66 |
| Pannes, N min / max (kN) | −75 / +35 | −86 / +41 |
| Rotule Y > 0, RY (kN) | −523 / +331 | −51 / +52 |
| Rotule Y < 0, RY sous T+ seul (kN) | +312 | 0 (guidée) |
| UZ min du tablier, ELS caractéristique (mm) | −59 | −82 |

P25 supprime le bridage du montant de rive et de la triangulation sous la température. P24
charge un tiers de largeur en plus (2,00 m au lieu de 1,50 m) et place les poutres en rive :
le moment et la flèche des poutres principales augmentent, de même que l'effort normal des
pannes.

## 3. Livrables

Dépôt : `/media/sf_partage/echanges/lot50bis/pontons_alu_01/` (CSV, avec SHA-256 dans
`empreintes.sha256`). Les CSV du lot sont aussi dans le paquet versionné
(`resultats/paquet/visualisation/lot50bis/`). L'avertissement P28 figure en tête des CSV de taux.

### 3.1 Synthèse par famille (`synthese_familles.csv`)

Les valeurs ci-dessous sont les maxima de l'ELU fondamental et de l'ELU accidentel, au format
jeu B / jeu B′. Elles sont données en partie courante (f0), puis en zone soudée (f0,haz, entre
parenthèses ; c'est une borne).

| Famille | Taux σ max | Lieu (jeu B) |
| --- | --- | --- |
| Poutres principales MP1200 | 1,53 / 1,01 (2,86 / 1,88) | PP_YP, X = 2,25, nœud du montant 3 |
| Pannes 50 × 5 | 0,87 / 0,58 (1,73 / 1,15) | PANNE_3 à X = 6,25 |
| Montants | 0,55 / 0,48 (1,14 / 1,00) | MONT_6, Y = +0,93 |
| Diagonales | 0,37 / 0,32 (0,78 / 0,66) | DIAG_2 |
| Profilés supports | 0,30 / 0,28 (0,63 / 0,59) | SUP_1, tête |

Le cisaillement ne gouverne nulle part (taux τ ≤ 0,57 en zone soudée).

- **Profilés supports** : ces efforts sont pris au pied, Z = +1,09. L'articulation (P18) les
  transmet tels quels au chevêtre. Valeurs à l'ELU B, en kN (N > 0 en traction ; VY selon X,
  VZ selon Y) :

  | Profilé | N | VY | VZ |
  | --- | --- | --- | --- |
  | SUP_1 (−0,93) | −58,0 / +26,8 | ±6,3 | −70,8 / +41,4 |
  | SUP_2 (0) | −37,0 / +43,9 | −11,5 / +24,1 | −6,3 / +11,1 |
  | SUP_3 (+0,93) | −47,2 / +22,2 | ±6,3 | −35,7 / +60,0 |

  Jeu B′ : N min −42,7, −31,7 et −36,2 kN. Détail : `profiles_supports_pieds.csv`.
- **Pannes** : l'effort normal minimal vaut −85,6 kN (B) et −55,6 kN (B′), sur PANNE_4 à
  X = 3,21. C'est la membrure comprimée du tablier (P7, P26). Le taux est de 0,87 / 0,58 en
  partie courante et de 1,73 / 1,15 en zone soudée. Le flambement n'est pas vérifié.
- **Rotules côté quai (P25)**, ELU B, en kN :

  | Rotule | RX | RY | RZ |
  | --- | --- | --- | --- |
  | Y = −0,93 (guidée) | −74,0 / +81,7 | 0 | −16,8 / +37,7 |
  | Y = +0,93 (fixe) | −69,7 / +76,4 | −51,4 / +51,6 | −22,8 / +50,7 |

  À l'ELU accidentel (accostage de 77 kN/m), RX atteint ±197 kN et RY ±154 kN (rotule fixe).
  Détail : `rotules_quai.csv`.

### 3.2 Inertie (`balayage_inertie.csv`)

La flèche relative est mesurée par rapport à la corde des appuis de la poutre, ce qui retire
le tassement de la semelle. Valeurs à l'ELS caractéristique, en mm :

| k (IY = k × IY du MP1200) | Flèche relative B, total / variables | Flèche relative B′, variables | My max ELU B / B′ (kN·m) |
| --- | --- | --- | --- |
| 1 | −78,6 / −68,5 | −38,8 | 53,2 / 34,4 |
| 3 | −33,3 / −29,1 | +16,5 (houle montante) | 61,2 / 39,5 |
| 5 | −21,4 / −18,7 | +10,6 (houle montante) | 63,2 / 40,8 |

Le balayage confirme que la flèche suit 1/k, à une part fixe près : a = 7,4 mm (B) et 4,3 mm
(B′). Il ne confirme qu'en partie la constance des moments : My croît de 19 % entre k = 1 et
k = 5, car des poutres plus raides attirent la charge des pannes et de la triangulation.

### 3.3 Inertie et module nécessaires, pour une poutre principale (`inertie_necessaire.csv`)

**Inertie nécessaire (cm⁴)**. Valeurs ajustées par a + b/k sur k = 1, 3, 5 ; résidu de 1,2 mm
pour B et de 0,7 mm pour B′. Pour comparaison, IY du MP1200 = 2 564 cm⁴.

| Flèche sous actions variables | Jeu B | Jeu B′ |
| --- | --- | --- |
| L/200 = 31,3 mm | 6 597 (k = 2,57) | 3 294 (k = 1,28) |
| L/250 = 25,0 mm | 8 944 (k = 3,49) | 4 287 (k = 1,67) |
| L/300 = 20,8 mm | 11 724 (k = 4,57) | 5 364 (k = 2,09) |

**Module Wel,y nécessaire pour un taux simplifié de 1,0 (mm³)**, avec A et Wel,z du MP1200.
Pour comparaison, Wel,y du MP1200 = 218 166 mm³. Les valeurs sont données pour k = 1 / 3 / 5 ;
le module se lit au k retenu pour la flèche (par exemple environ 362 000 mm³ pour B à L/250).

| Résistance | Jeu B | Jeu B′ |
| --- | --- | --- |
| f0 | 385 800 / 362 300 / 360 700 | 219 700 / 231 100 / 251 400 |
| f0,haz, ELU fondamental | 1 196 400 / 830 200 / 787 300 | 545 700 / 478 500 / 483 500 |
| f0,haz, ELU accidentel | impossible | impossible |

Pour f0 et le jeu B, c'est l'ELU fondamental qui gouverne. Pour le jeu B′, c'est l'ELU
fondamental à k = 1, puis l'ELU accidentel à k = 3 et 5.

À l'ELU accidentel, en zone soudée, **aucun Wel,y ne suffit** : sur PP_YP à X = 2,25, sous
l'accostage AAP, |N|/A + |Mz|/Wel,z vaut déjà 1,09 × f0,haz/γM1. Il faut agir sur A, sur
Wel,z ou sur l'étendue de la zone affectée thermiquement, par une décision de MM.

### 3.4 Chevêtre

Les six CSV de flexion composée sont mis à jour. Au droit des supports, les stations passent à
Y = −0,93 ; 0 ; +0,93. À l'ELU B, le moment MFY minimal passe de −12,2 à −14,2 kN·m, au droit
du support de rive Y = −0,93, qui est en console au-delà du poteau. Le moment MFZ maximal passe
de 4,8 à 10,0 kN·m, à Y = 0. Au nu des poteaux, MFY vaut −6,2 / +3,8 kN·m.

## 4. Contrôles, `rex`, interventions

- `env-check` OK (profil vm, 10 vérifications) ; `mcp-check` OK (10 outils).
- `mesh check` : 356/356 invariants tenus. Niveau B : 116/116 commandes, verdict valide, pour
  les 3 exécutions.
- Niveau C : 3 exécutions `completed_ok`, 0 alarme. Tables de post-traitement identiques à
  celles de la production (10 608 valeurs).
- Niveau D : harnais par défaut RÉUSSI pour k = 1, 3 et 5 (G1 : écart 4,1·10⁻¹³). Moment à
  mi-portée sous Q : 48,07 kN·m contre 48,83 kN·m, soit 1,55 % d'écart, **RÉUSSI** (critère :
  10 %). CTL-013, équilibre par état limite et contrôle croisé : RÉUSSIS.
- Paquet : niveau D, antériorité des critères démontrable.
- `aster-expert rex pontons_alu_01` : 11 exécutions, 0 échec (développement 10, taux 0,0 % ;
  vérification 1) ; « Tous les échecs sont classés : clôture possible. »
- Interventions de MM : 1. MM a fusionné `lot-50` dans `main` en cours de session.
- Erreurs évitées par la base : 2. DIAG-001 : aucune `LIAISON_SOLIDE` sur les nœuds des
  rotules, donc pas de risque de pivot nul. CA-016 : `DDL_IMPO` est répétable.

## 5. Points ouverts pour MM

1. Le chevêtre à ±1,05 est à confirmer.
2. Le choix entre les jeux B et B′ reste à faire.
3. Hypothèses du taux simplifié à confirmer :
   - Av du MP1200 = Avz ;
   - Av des tubes = A/2 ;
   - définition des extrémités soudées, platine du pied des supports comprise.
4. Zone soudée à l'ELU accidentel : il faut agir sur A ou sur Wel,z, pas sur Wel,y.
5. Le flambement des pannes comprimées reste à vérifier dans l'EC9.
6. Toujours absents : la solution technologique de l'appui guidé, le poids des défenses et la
   nuance d'acier du chevêtre.
