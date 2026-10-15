# Lot 51 — Pontons aluminium : palée complète, appuis néoprène, actions maritimes révisées, comparaison de solutions

**Tout en français. Profil `vm`. Branche `lot-51`, depuis `main` après fusion
de `lot-50quinquies`.** Consigne copiée dans `docs/lots/lot51_consigne.md`.
Elle remplace les versions 1 et 2.

## Objet

À la suite d'échanges internes du 15/10/2026, MM change la conception :

- **Piles** : articulées en tête, pour limiter les moments dans les poteaux.
- **Appuis du tablier** : néoprènes.
- **Liaison entre travées** : travées boulonnées entre elles.
- **Palée** : complète, avec 4 piles et un anneau BA.

Ce lot construit le nouveau modèle et calcule une **matrice de variantes**
pour comparer les solutions techniques avant la prochaine réunion. Il applique
aussi les actions d'accostage et d'amarrage révisées.

**Calcul linéaire uniquement.** Les vérifications EC9, béton armé et
appareils d'appui sont faites par le superviseur à partir des exports : **ne
pas les faire dans le lot**.

Règles d'économie :

- un seul `.comm` paramétré ;
- un seul script de maillage paramétré ;
- les variantes déclarées dans un fichier ;
- tests ciblés ;
- aucune modification du tronc commun sauf correction indispensable,
  justifiée dans le compte rendu.

## Décisions à enregistrer

Format habituel : source et variantes écartées, nature « pratique », tranchées
par MM.

**Actions maritimes.** Source : note `Carro_note_accostage_amarrage.docx`,
indice C. Les valeurs sont en annexe A ; la note n'a pas à être lue.

- **P29** : navire de projet enveloppe (L 9,0 m, B 3,0 m, tirant d'eau
  0,9 m, 5,0 t). Il remplace le navire AVP.
- **P30** : accostage selon PIANC WG 211, par l'arrière, perpendiculaire à la
  panne :
  - Ce = 1,0, Cm = 1,1 ;
  - γE = 1,81 ;
  - défense D100, longueur de contact Lc = 1 m.
- **P31** : accostage normal à γ = 1,5, avec ψ0 = 1,0, ψ1 = 0,5, ψ2 = 0. ACA
  est traité à l'ELU accidentel, γ = 1,0.
- **P32** : effort tangentiel de 0,7 × l'effort normal. Il est concomitant de
  l'effort normal, soit horizontal le long de la panne, soit vertical, jamais
  les deux.
- **P33** : cas d'amarrage AM local, AM1 et AM2, γ = 1,5. Ce γ remplace le
  1,3 de l'AVP. La note ne donne pas de ψ pour l'amarrage : conserver ceux du
  projet et les citer dans le compte rendu.
- **P34** : taquets de 5 t. La structure locale est vérifiée sous 49 kN à
  l'ELU accidentel (AMF).

**Structure.** Décisions de MM du 15/10/2026.

- **P35** : travée de 6,25 m confirmée.
  - Largeur chargée du platelage : 2,00 m.
  - Appuis côté quai inchangés : une rotule fixe, une rotule guidée en Y.
  - Jeu B′ seul retenu, plus l'ELU accidentel. Les jeux A et B ne sont plus
    calculés.
- **P36** : poutres principales en **tube carré** soudé (solution soudée
  conservée), alliage 6082-T6, angles vifs.
  - Section de référence : 200 × 200 × 8.
  - Balayage : 180 × 180 × 8 et 200 × 200 × 10.
  - Pannes, montants et diagonales inchangés.
- **P37** : critères de flèche, appliqués par le superviseur :
  - L/200 à l'ELS fréquent ;
  - L/150 à l'ELS caractéristique.
- **P38** : **appareils d'appui en élastomère fretté**, type B, NF EN 1337-3,
  tableau 3 : 200 × 300 mm, 3 feuillets de 8 mm (Te = 24 mm), G = 0,9 MPa.
  Raideurs selon NF EN 1337-3 §5.3.3.7, reprises par le guide Sétra
  « Appareils d'appui en élastomère fretté », annexe 1, tableau A.2 :
  - **Kx = Ky = G·A/Te** = 0,9 × 60 000 / 24 = **2,25 kN/mm** ;
  - **Kz** = [Σ tᵢ/A′ · (1/(5·G·S²) + 1/Eb)]⁻¹, avec :
    - A′ = 190 × 290 mm² ;
    - S = A′/(2·(a′+b′)·tᵢ) = 7,17 ;
    - Eb = 2 000 MPa ;
    - d'où **Kz ≈ 476 kN/mm** ;
  - **Kθ = 0** : rotule, formule simplifiée du guide.

  Les ressorts travaillent **aussi en traction**. Toute traction est rapportée
  comme un **effort de retenue** à reprendre par un dispositif
  anti-soulèvement. Sensibilité sur Kx et Ky : × 0,5 et × 2. Le facteur 2
  correspond à Gdyn = 1,8 MPa (guide Sétra §3.2.2).
- **P39** : profilé support 150 × 150 × 7, haut de 0,15 m, **encastré** sur le
  chevêtre (platine boulonnée sur tiges scellées). Le néoprène est posé sur le
  profilé, sous le nœud de la poutre principale.
- **P40** : palée complète, avec :
  - 4 piles Ø 0,50 encastrées dans la semelle ;
  - 4 poutres BA en anneau ;
  - une petite travée aluminium entre les deux chevêtres.

  La liaison en tête de pile (goujon) est soit une rotule, soit un
  encastrement selon la variante.
- **P41** : hauteur des piles variable le long du ponton. Une palée a 4 piles
  de même hauteur. Hauteurs étudiées : 1,32 m et 4,0 m.
- **P42** : éclissages boulonnés entre travées, au droit des appuis, en deux
  variantes :
  - **articulé** : rotations libérées autour de y et de z locaux de la
    poutre ;
  - **continu**.
- **P43** : section des poutres BA de l'anneau (chevêtres et longrines) portée
  à **0,40 × 0,40**. La section 0,25 × 0,40 est écartée sans calcul,
  décision de MM. Motifs, établis par le superviseur à la main :
  - assise de la platine et des tiges d'ancrage du profilé support, avec des
    distances aux bords compatibles avec la NF EN 1992-4 ;
  - reprise de la traction des ancrages anti-soulèvement ;
  - torsion des chevêtres sous effort longitudinal des néoprènes, alors que la
    tête de pile est articulée ;
  - enrobage du goujon de tête de pile ;
  - poids propre favorable à la traction des piles.

## 1. Géométrie (script de maillage paramétré)

Repère inchangé : X le long du ponton depuis le quai, Y transversal, Z vers le
haut. Les cotes de Z du tablier, de la semelle, de l'axe du chevêtre et des
pannes sont celles du lot 50 bis.

**Grande travée 1** (X = 0 à 6,25) : géométrie du lot 50 bis, à une
différence près : les poutres principales sont en tube carré (P36). Rotules du
quai inchangées.

**Palée** (P40) :

- **Piles** : centres en (6,25 ; ±0,75) et (7,77 ; ±0,75). Hauteur H de 1,32
  ou 4,0 m. Pied relié à la semelle par liaison rigide, comme au lot 50 bis.
- **Semelle complète** : X de 5,75 à 8,27, Y de −1,45 à +1,45, épaisseur
  0,25, DKT, sur RIGI_PARASOL avec les modules du lot 50 bis. Pour H = 4,0 m,
  la semelle est inchangée ; le signaler.
- **Chevêtres** C1 (X = 6,25) et C2 (X = 7,77) : 0,40 × 0,40 (P43), Y de
  −1,05 à +1,05.
- **Longrines** L+ et L− (Y = ±0,75) : 0,40 × 0,40, X de 6,25 à 7,77.
- **Axe des poutres BA** : abaissé de sorte que leur face supérieure reste à
  la cote du lot 50 bis. Les cotes du profilé support et du tablier sont
  inchangées.
- **Anneau**, deux variantes :
  - **monolithique** : chevêtres et longrines continus aux angles ;
  - **4 poutres indépendantes** : aucune continuité entre poutres aux angles.
    Chaque extrémité est reliée séparément à la tête de pile.

**Appuis du tablier** : à chaque point (6,25 ; ±0,93) et (7,77 ; ±0,93), un
profilé support (P39) puis un ressort néoprène (P38). Les deux extrémités de
poutre qui se rejoignent au-dessus de l'appui sont reliées par l'éclissage
(P42), au nœud du néoprène.

**Petite travée** (X = 6,25 à 7,77) :

- poutres principales et pannes identiques à celles des grandes travées ;
- un montant à chaque extrémité ;
- une diagonale.

C'est une hypothèse de géométrie : le signaler.

**Grande travée 2** (X = 7,77 à 14,02) : identique à la travée 1. Ses appuis
d'extrémité en X = 14,02 (Y = ±0,93) sont un profilé support et un néoprène,
sur un support supposé fixe (palée suivante non modélisée).

## 2. Liaisons par variante

Toutes les variantes ont des chevêtres et des longrines en 0,40 × 0,40.

| Code | Têtes de piles | Anneau | Éclissage | H (m) | Appuis de palée | Poutre principale |
|---|---|---|---|---|---|---|
| R | 4 rotules | monolithique | articulé | 1,32 | néoprène nominal | 200 × 200 × 8 |
| E | idem R | idem | **continu** | idem | idem | idem |
| T1 | **sous chaque chevêtre : pile Y− encastrée, pile Y+ rotule** | idem | articulé | 1,32 | idem | idem |
| T2 | **4 encastrements** | idem | articulé | 1,32 | idem | idem |
| A | 4 rotules | **4 poutres indépendantes** | articulé | 1,32 | idem | idem |
| P4 | 4 rotules | monolithique | articulé | **4,0** | idem | idem |
| P4E | **4 encastrements** | monolithique | articulé | **4,0** | idem | idem |
| N− | idem R | | | | **Kx = Ky × 0,5** | idem |
| N+ | idem R | | | | **Kx = Ky × 2** | idem |
| M | idem R | | | | **appui mécanique articulé** : Y et Z bloqués, X libre, rotations libres | idem |
| S1 | idem R | | | | | **180 × 180 × 8** |
| S3 | idem R | | | | | **200 × 200 × 10** |

Une rotule en tête de pile transmet les trois translations et libère les
trois rotations. Un encastrement transmet tout. La variante M représente une
alternative au néoprène : appui à axe sur trou oblong, qui reprend le
soulèvement et l'effort transversal.

Si une variante est mécaniquement instable, ne pas la stabiliser
artificiellement. La signaler avec le message Code_Aster et passer à la
suivante.

## 3. Cas élémentaires (unitaires, linéaires)

Cas G1, G2, Q, QD, HU, HD, TP, TM, TAP et TAM : mêmes définitions qu'au lot 50
bis, sur les trois travées.

Pour permettre les dispositions défavorables dans la variante continue E, G2,
Q, HU et HD sont **découpés par travée** : `_T1`, `_PT` (petite travée) et
`_T2`. Le cas total est la somme.

**Accostage**, cas répartis de 1 kN/m sur une zone de 1 m de la poutre de
rive, pour chaque côté s ∈ {YM, YP} :

- `ACN` : perpendiculaire au bord, **vers l'intérieur** ;
- `ACX` : selon +X ;
- `ACZ` : selon +Z.

| Zone | X début | X fin |
|---|---|---|
| QU | 0,00 | 1,00 |
| MI1 | 2,625 | 3,625 |
| CH1 | 5,25 | 6,25 |
| PT | 6,51 | 7,51 |
| PA2 | 7,77 | 8,77 |

Cela fait 30 cas.

**Taquets** : positions AVP X = 1,6 et 4,6 sur chaque poutre de rive de la
travée 1, et X = 9,37 et 12,37 sur la travée 2, soit 8 taquets. Pour chaque
taquet, deux cas ponctuels de 1 kN :

- `AMY` : perpendiculaire au bord, **vers l'extérieur** ;
- `AMX` : selon +X.

Cela fait 16 cas. Aucun plan d'amarrage n'est fourni : le signaler.

## 4. Événements et combinaisons (jeu B′ et ELU accidentel)

Les événements sont **exclusifs** : un seul événement AC ou ACA, et un seul
événement AM, par combinaison. Les autres règles de concomitance du jeu B′
sont inchangées.

**Accostage.** Un événement = une zone, un côté, et une variante tangentielle
parmi +X, −X, +Z et −Z. Facteurs caractéristiques :

| Cas | Normal | Tangentiel |
|---|---|---|
| AC | 23,5 | ± 16,45 |
| ACA | 45,0 | ± 31,5 |

**Amarrage.**

- **AM local** : un taquet, 27,5 kN, ⊥ vers l'extérieur ou ± ∥.
- **AM1** : les 8 taquets ensemble.
  - 23,8 kN ⊥ vers l'extérieur de leur côté : les deux côtés sont opposés.
  - ± 13,7 kN ∥, avec le même signe pour tous.
  - 2 événements.
- **AM2** : les 4 taquets d'un même côté, 10,6 kN ⊥ chacun vers l'extérieur.
  2 événements (YM ou YP).
- **AMF** (ELU accidentel) : un taquet, 49 kN, ⊥ vers l'extérieur ou ± ∥.

**Coefficients.**

- AC et AM : γ = 1,5.
- AC : ψ0 = 1,0, ψ1 = 0,5, ψ2 = 0.
- ELU accidentel, selon la règle d'accompagnement en vigueur dans le projet
  (la citer) :
  - G + ACA ;
  - G + AMF.
- Variante E : les cas G2, Q, HU et HD par travée sont combinés avec leurs
  dispositions défavorables (chaque travée chargée ou non). Les autres
  variantes utilisent les cas totaux.

Donner l'effectif des combinaisons.

## 5. Exécution et contrôles

1. Une exécution par variante, jusqu'à FIN (niveau C), en exploitant les
   ressources de la VM.
2. Harnais D : équilibre des cas unitaires. La résultante doit valoir 1 kN, ou
   1 kN/m × 1 m, à 10⁻⁶ près.
3. MED de charges et `charges_salome.py` générés pour la variante R
   seulement.

## 6. Exports (par variante, formats du lot 50 ter)

- `noeuds`, `elements`, `membres`, `efforts_elementaires`,
  `deplacements_elementaires`, `reactions_elementaires`, `combinaisons`,
  `charges`, `sections`, et `recombiner.py`.
- Nouveaux fichiers :
  - **`appuis_neoprene.csv`** : par appui et par cas élémentaire, les trois
    efforts du ressort (Fx, Fy, Fz ; Fz > 0 en compression) et le
    déplacement relatif (ux, uy, uz) entre ses deux nœuds ;
  - **`piles.csv`** : torseurs en tête et en pied de chaque pile, par cas
    élémentaire.

## 7. Comparaison des variantes (`comparaison_variantes.csv`, plus un tableau dans le compte rendu)

Une ligne par variante. Toutes les valeurs sont des enveloppes du jeu B′
(ELU, ELS caractéristique, ELS fréquent) et de l'ELU accidentel.

| Famille | Grandeurs |
|---|---|
| Poutres principales | My, Mz, N et V maximaux ; flèche maximale de la travée 1 en ELS fréquent et en ELS caractéristique (variables seules) |
| Appuis néoprène | Fz minimal (traction = soulèvement), Fz maximal, Fxy maximal, déplacement horizontal relatif maximal |
| Piles | N minimal et maximal ; M en tête et en pied ; V |
| Chevêtres et longrines | My, Mz, T et V maximaux ; efforts aux nœuds d'angle |
| Rotules du quai | réactions maximales |

Ajouter une phrase par variante sur ce qu'elle change par rapport à R.

## 8. `rex`

Faits nouveaux du lot. Précédent à proposer, statut « observé » : « navire
enveloppe de plaisance défini par le maître de port plutôt que par L·B·T·Cb ».

## Points ouverts, signalés et non tranchés

- Durée de moyennage du vent Météo-France.
- Coefficients Cv et Ct du fournisseur de défenses.
- Fiche fournisseur des taquets de 5 t.
- Plan d'amarrage absent.
- Géométrie de la petite travée.
- Semelle pour H = 4,0 m.
- Fixation de la défense sous 36,6 kN, vérification locale.

## Dépôt

`/media/sf_partage/echanges/lot51/pontons_alu_01/` :

- `<variante>/` : exports du §6 ;
- `comparaison_variantes.csv` ;
- `R/charges.med` et `R/charges_salome.py` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P29 à P43.
- Variantes calculées et instabilités éventuelles.
- Effectifs des combinaisons.
- Harnais.
- Tableau de comparaison, avec une phrase par variante.
- Points ouverts.
- `rex` et interventions.

## Interdits

- Aucune action maritime calculée par l'outil.
- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucune modification des autres projets.

## Annexe A — Actions maritimes (caractéristiques, note de MM, indice C)

| Action | Valeur | Application | γ |
|---|---|---|---|
| AC normal | 23,5 kN sur 1 m | ⊥ au bord, vers l'intérieur | 1,5 |
| AC tangentiel | 16,45 kN sur 1 m | ±X ou ±Z, concomitant | 1,5 |
| ACA normal | 45 kN sur 1 m | idem | 1,0 (accidentel) |
| ACA tangentiel | 31,5 kN sur 1 m | idem | 1,0 |
| AM local | 27,5 kN par taquet | horizontal, ⊥ ou ∥ | 1,5 |
| AM1 | 23,8 kN ⊥ et 13,7 kN ∥ par poste | un taquet par poste, tous les postes, deux côtés (⊥ opposés, ∥ de même sens) | 1,5 |
| AM2 | 10,6 kN ⊥ par poste | deux taquets par poste (2 × 5,3 kN), un côté | 1,5 |
| AMF | 49 kN | un taquet, horizontal quelconque | 1,0 (accidentel) |

Valeurs AVP remplacées : AC 16 kN/m sur 2 m (γ 1,0), ACA 77 kN/m sur 2 m, AM
8,0 kN sur deux points (γ 1,3).
