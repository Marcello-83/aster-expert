# Lot 54 — Pontons aluminium : géométrie PRO définitive (treillis régulier, chevêtres 0,60), houle 5 kPa, recalcul complet

**Tout en français. Profil `vm`. Branche `lot-54`, depuis `main` après fusion
de `lot-53`.**

- Consigne copiée dans `docs/lots/lot54_consigne.md`.
- Consigne également copiée dans
  `projets/pontons_alu_01/donnees/sources/consigne_lot54.md`, source des textes
  cités.

## Objet

Acter les arbitrages de MM pris depuis le lot 53 (20 au 22/10/2026) et relancer
le calcul complet. La géométrie et la houle changent : il faut relancer
Code_Aster et recombiner. Le modèle obtenu est le **modèle final du PRO**. Il
alimente :

- la note d'hypothèses MM5083_ING_PRO_NOT_OA_0001 ;
- la note de calcul MM5083_ING_PRO_NOT_OA_0002 ;
- les classeurs de vérification du superviseur.

Tout le lot 52 est repris (modèle, cas unitaires, événements, combinaisons,
exports), ainsi que les exports de déplacements du lot 53, **sauf** ce qui est
modifié ci-dessous.

Calcul linéaire uniquement. Ni EC9, ni béton armé, ni vérification d'appui dans
le lot. Règles d'économie habituelles :

- un `.comm` paramétré ;
- un script de maillage paramétré ;
- les variantes dans `variantes_lot54.yaml` ;
- les barres générées par boucle ;
- aucun bloc recopié à la main par travée ou par palée.

## Décisions à enregistrer (MM, 20 au 22/10/2026)

État de la fiche au départ : décisions P1 à P66 (P52 non attribuée), dernier
enregistrement `enregistrement_P62_P66_lot52.md`. Le lot 53 n'a enregistré
aucune décision. Les décisions ci-dessous prennent donc les numéros **P67 à
P76**.

Enregistrement :

```
aster-expert fiche enregistrer pontons_alu_01 <arbitrage>
```

Sortie dans `donnees/sources/enregistrement_P67_P76_lot54.md`, selon la règle
habituelle :

- textes extraits de `consigne_lot54.md`, jamais retapés ;
- les révisions passent par `record_practice_decision`, l'ancienne décision
  allant dans `decision_history`.

Révisions et compléments à enregistrer :

| Nouvelle décision | Effet sur la fiche |
|---|---|
| P67 | P64 ré-arbitrée (point 3 : positions en X des montants) |
| P68 | P43 et P48 ré-arbitrées (section et emprise de l'anneau) |
| P69 | P56 et P60 ré-arbitrées (coefficients de houle) ; P61 annulée (impacts) ; P62 ré-arbitrée (plus de HU_IMP) |
| P71 | confirme P48 (aucun ancrage) et P19/P48 (raideurs de sol) |
| P72 | confirme P48 et P58 (piles Ø 0,50) |
| P74 | complète P46 (têtes encastrées, inchangé) |
| P75 | complète P45 (culée) |
| P76 | complète P23 (fissuration à l'ELS quasi permanent) |

**P67 — Treillis horizontal régulier, P64 révisée.**

- Le point 3 de P64 (« Positions en X des montants inchangées ») est remplacé.
- Dans chaque grande travée (de Xd à Xf = Xd + 6,25), 6 montants à
  **Xd + k × 1,25, pour k = 0 à 5**, soit 5 panneaux égaux de 1,25 m.
  - Avant : Xd + 0 / 0,75 / 2,25 / 3,75 / 5,25 / 6,25.
- Les diagonales restent en N, dans le même sens qu'au lot 52. Toutes les
  diagonales des grandes travées deviennent identiques et parallèles : une
  seule longueur et un seul angle de coupe, pour une fabrication en série en
  usine.
- Reste de P64 inchangé :
  - nœud diagonale–montant à e = 0,25 m de l'axe des poutres, soit |Y| = 0,68 ;
  - axe des montants et des diagonales à +1,29 ;
  - liaisons rigides de 0,01 m et de 0,085 m.
- Petites travées PT1 à PT5 et porte-à-faux : inchangés.
- Le découpage des pannes suit les nouvelles positions. La portée maximale des
  pannes passe de 1,50 m à 1,25 m.
- Taquets inchangés : Xd + 1,6 et Xd + 4,6, sur les poutres principales.

**P68 — Chevêtres 0,60 × 0,40 prolongés, P43 et P48 révisées.**

- Section des chevêtres : **b = 0,60 m** (selon X) **× h = 0,40 m**.
  - Coulés en place, à section constante sur toute leur longueur.
  - La largeur de 0,60 m couvre la tête des piles Ø 0,50 sans surlargeur locale
    de coffrage.
- Longrines inchangées : 0,40 × 0,40.
- Chevêtres prolongés de **Y = ±1,05 à Y = ±1,20**, pour placer la fixation de
  l'appui à 0,15 m de l'about.
- Axes inchangés :
  - chevêtres en X = 6,25 + 7,77 k et en X + 1,52 ;
  - arase +0,69, dessus +1,09.
- Liaisons longrine–chevêtre, pieu–anneau et appuis : inchangées en principe.
  Les longueurs des liaisons rigides suivent la nouvelle géométrie.
- Écartées :
  - anneau 0,40 × 0,40 de P43 et chevêtres de Y = −1,05 à +1,05 de P48 ;
  - anneau 0,50 × 0,50 (proposition du superviseur), refusé par MM ;
  - nœuds élargis 0,60 × 0,60 au droit des piles (proposition du superviseur),
    abandonnés pour la constructibilité.

**P69 — Houle de projet : forfait de 5 kPa, justifié par les études GEOMER, P56 et P60 révisées, P61 annulée.**

- Les cas unitaires de 1 kPa par surface et par module de P56 sont conservés.
  Seuls les événements changent :
  - HU = 5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) ;
  - HD = 5,0 × HD_TABLIER ;
  - HU_F = 2,728 × HU_TUBES + 2,516 × HU_PANNES + 2,425 × HU_PLATELAGE, à
    l'ELS fréquent. Valeurs majorantes : la houle fréquente n'atteint pas le
    tablier.
- **Aucun impact** : P61 est annulée. Les événements HU_IMP_Mk et leurs options
  sont retirés des combinaisons.
- **P62 révisée** : la houle reste dans le critère de flèche. HU et HD entrent
  dans l'ELS caractéristique ; HU_IMP n'existe plus.
- Justification :
  - donnée d'entrée principale : houle mesurée à Cap Couronne (GEOMER, 1996),
    transmise en zone 2 avec Kt = 0,10. Kt est commun au modèle physique GEOMER
    de 1995 et à l'étude MS414803 ;
  - les pannes A et B sont en **zone 2** GEOMER ;
  - le calcul McConnell sur cette houle donne 4,0 à 5,0 kPa en sous-pression et
    au plus 2,9 kPa en surpression.
- Écartées :
  - coefficients « tablier noyé » de P60 ;
  - estimation à 11 kPa (houle au large ANEMOC + McConnell), qui n'apparaît que
    pour mémoire dans la note d'hypothèses ;
  - impacts de P61.
- Toutes les autres règles de combinaison sont inchangées : P49, P57 et P59.
- Nouveau groupe `houle_lot54` dans le fichier de données, avec les valeurs
  ci-dessus.

**P70 — Accostage et amarrage local jamais au même poste.**

Un bateau qui accoste n'est pas amarré à son poste. Dans une même combinaison,
les deux événements suivants sont **interdits ensemble** :

- un amarrage local (AML_TQk_…) ou une rupture d'amarre (AMF_TQk_…) ;
- un accostage (AC_… ou ACA_…).

L'interdiction vaut lorsque les deux sont **sur la même rive** et que la
distance en X entre le centre de la zone d'accostage et le taquet est
**< 1,60 m** (demi-largeur de poste de 3,20 m).

Centres des zones d'accostage :

- début : Xd + 0,5 ;
- milieu : (Xd + Xf)/2 ;
- fin : Xf − 0,5 ;
- PTk : milieu ;
- PF : 38,85 + Lpf − 0,5.

AM1 et AM2 (cas globaux) restent combinables avec AC et ACA : c'est
sécuritaire.

Mise en œuvre :

- maximisation **conjointe** de l'emplacement AM et de l'emplacement AC (ou
  ACA) dans chaque branche qui contient les deux, en excluant les paires
  interdites ;
- les autres emplacements restent indépendants ;
- `recombiner.py` applique la même règle ;
- énumération de contrôle sur 36 extrêmes tirés au sort, dont au moins 12 dans
  des branches qui contiennent AM et AC.

**P71 — Stabilité des palées existantes : responsabilité du maître d'ouvrage.**

- Le maître d'ouvrage conserve les fondations sans intervention et prend à sa
  charge la stabilité des palées : soulèvement, renversement, portance,
  excentrement.
- On retient la voie du « comportement constaté » de l'existant (1975, jamais
  décollé).
- **Aucun ancrage, aucun lest** n'est modélisé ni dimensionné (P48 confirmée).
- Les réactions des semelles sont exportées pour mémoire seulement.
- Raideurs de sol 5 000 / 1 000 kN/m³ conservées (P19, P48), sans étude de
  sensibilité.

**P72 — Piles Ø 0,50 confirmées.**

- P48 et P58 sont inchangées.
- Le diamètre réel est d'environ 0,42 m, buse comprise. Il sera relevé en EXE.

**P73 — Platelage bois non fusible ; caillebotis refusé.**

- Le maître d'ouvrage assume le risque d'arrachement du platelage par la houle.
- Le caillebotis est refusé : le client veut du bois.
- Les surfaces chargées de HU_PLATELAGE (1,327 m) et de HD_TABLIER (1,895 m)
  sont conservées.

**P74 — Liaison pieu–chevêtre.**

- Barres HA20 scellées chimiquement dans le pieu recépé et ancrées par crosse
  dans le chevêtre. Vérification par le superviseur.
- Modèle : têtes de pieux encastrées dans l'anneau (P46), inchangé.

**P75 — Culée : recépage du quai existant et bloc béton neuf.**

- La culée reste neuve et conçue par nous (P45).
- Son dimensionnement fera l'objet d'un lot ultérieur.
- Modèle inchangé :
  - deux appuis, X et Z bloqués, Y bloqué côté YP ;
  - culée non modélisée, réactions exportées comme au lot 52.

**P76 — Fissuration de l'anneau en XS3.**

- wmax = 0,2 mm sous combinaison quasi permanente, soit σs ≤ 200 MPa pour des
  HA16.
- Le superviseur vérifie l'anneau à l'ELS quasi permanent avec ce critère
  (complète P23).
- Sans effet sur le calcul du lot.

## Variantes

| Code | Géométrie | Poutres | Pannes | Montants et diagonales | Chevêtres |
|---|---|---|---|---|---|
| B54 | panne B (piles 1,30 à 3,90 m, Lpf 1,25 m) | 200 × 200 × 12 | 50 × 50 × 5 | 120 × 120 × 6, P64 et P67 | 0,60 × 0,40, P68 |
| A54 | panne A (piles 1,50 à 3,90 m, Lpf 1,05 m) | idem | idem | idem | idem |

La sensibilité B52P4 (pannes 50 × 50 × 4) n'est pas reprise.

## Exécution

- Code_Aster jusqu'à FIN pour B54 et A54.
- Harnais D sur tous les cas unitaires.
- Recombinaison par décomposition, avec la règle P70, et le temps de calcul.

## Exports

Pour chaque variante, les mêmes fichiers qu'au lot 52 :

- `efforts_elementaires.npz`, en float32 ;
- `ancrage.csv`, `palee_equilibre.csv`, `culee.csv`, `chaine_x.csv`,
  `deplacements_axes.csv`, `appuis_axes.csv`, `piles.csv` ;
- `membres.csv`, `elements.csv`, `sections.csv`, `noeuds.csv`,
  `geometrie_noeuds.csv`, `evenements.csv`, `combinaisons.csv`, `charges.csv`,
  `recombiner.py`.

Pour B54 seulement, les exports de déplacements du lot 53, avec P69 et P70 :

- `deplacements_unitaires.csv` ;
- `deplacements_evenements.csv` ;
- `deplacements_combinaisons.csv` ;
- `deplacements_synthese.csv`.

**`comparaison_B52_B54.csv`** :

- par famille : poutres, pannes, montants, diagonales, chevêtres, longrines,
  piles ;
- grandeurs : N min, N max, My, Mz et V extrêmes ;
- pour B52 recombiné avec P69 et P70, et pour B54.

## Vues pour les notes (client)

Ces vues sont destinées aux notes remises au client. Règles de présentation :

- **aucune mention** de « lot », de variante, de code projet interne ou de
  numéro de décision (P…) dans les titres et les légendes ;
- titre court en français, par exemple « Panne B – palée P1 » ;
- polices lisibles une fois la figure imprimée sur 16 cm de large : texte au
  moins 11 pt, légendes au moins 10 pt ;
- fond blanc, 200 dpi, marges blanches rognées ;
- **une couleur par famille, identique sur toutes les vues**. Familles :
  - poutres principales ;
  - pannes ;
  - montants ;
  - diagonales ;
  - chevêtres ;
  - longrines ;
  - piles ;
  - semelles ;
  - appuis.

Pour B54 :

1. Vue d'ensemble isométrique depuis le porte-à-faux.
2. Vue d'ensemble isométrique depuis la culée.
3. Culée et travée T1, zoom.
4. Palée P1 isométrique : piles, semelle, anneau avec chevêtres 0,60 prolongés,
   appuis.
5. Palée P5, petite travée PT5 et porte-à-faux.
6. Coupe transversale sur la palée P1 : chevêtre 0,60 × 0,40 prolongé à ±1,20,
   appui, tube, pannes et platelage.
7. Vue en plan du treillis de T1 et PT1 (P67) : cotes des montants
   (0 / 1,25 / 2,50 / 3,75 / 5,00 / 6,25), nœuds à e = 0,25, pannes en
   transparence.
8. Zoom 3D sur un nœud poutre / montant / diagonale / panne.
9. Déformée (× 10) sous la combinaison ELU qui maximise ΣRX de la culée, avec
   la valeur de ΣRX.
10. Déformée sous la combinaison ELS caractéristique qui maximise la flèche
    vers le haut de T2 (houle), avec la flèche en mm.
11. Vues A, B et C du lot 53, avec les valeurs aux palées :
    - A : déformée DY à l'ELS caractéristique ;
    - B : déformée DY à l'ELU accidentel ;
    - C : déformée DX hors thermique à l'ELS caractéristique.

## Contrôles

- `geometrie_noeuds.csv` :
  - zéro recouvrement ;
  - zone de soudure ≤ 200 mm ;
  - toutes les diagonales des grandes travées ont la même longueur, à 1 mm près.
- Résultantes de HU, HD et HU_F exactes (coefficients × surfaces).
- Poids propre d'un chevêtre : 0,60 × 0,40 × 2,40 × 25 = 14,4 kN, à 1 % près.
- Sous AM1 : ΣRX des palées ≈ 0.
- Sous TP : DX de l'axe de P5 = α·ΔT·38,85.
- Règle P70 : pour 3 éléments tirés au sort, montrer qu'une paire interdite
  donnait l'extrême sans la règle, et donner la valeur avec la règle.
- `comparaison_B52_B54.csv` : une phrase par écart de plus de 5 %. On attend :
  - des pannes moins sollicitées (portée de 1,25 m) ;
  - des montants et des diagonales du même ordre ;
  - un ancrage des palées un peu réduit (chevêtres plus lourds).
- Fiche :
  - `projet verifier` vert ;
  - P64, P43, P48, P56, P60 et P62 avec leur ancienne version dans
    `decision_history` ;
  - P61 annulée.
- Chaque PNG : fichier non vide. Vérifier à l'œil les vues 4, 6, 7 et 11.

## Dépôt

`/media/sf_partage/echanges/lot54/pontons_alu_01/` :

- `B54/` et `A54/` : exports ;
- `comparaison_B52_B54.csv` ;
- `vues/` ;
- `scripts/` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P67 à P76 enregistrées et révisions de la fiche (tableau
  « nouvelle décision → effet »).
- Géométrie des nœuds : synthèse de `geometrie_noeuds.csv`.
- Harnais et contrôles.
- Règle P70 : mise en œuvre, contrôle par énumération, nombre de paires
  exclues.
- Tableau B52 / B54, avec une phrase par écart notable.
- Ancrage par palée et réactions de culée.
- Synthèse des déplacements.
- PNG vérifiés à l'œil.
- `rex` et interventions.

## Hors fiche (pour information, sans effet sur le lot)

Codification des livrables PRO :

- MM5083_ING_PRO_NOT_OA_0001 : note d'hypothèses ;
- MM5083_ING_PRO_NOT_OA_0002 : note de calcul ;
- MM5083_ING_PRO_CAL_OA_0001 : classeur aluminium et appuis ;
- MM5083_ING_PRO_CAL_OA_0002 : classeur béton armé et fixations.

## Interdits

- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucun ancrage modélisé.
- Aucune modification des autres projets.
- Aucun bloc recopié à la main.
- Aucune édition à la main du JSON de la fiche.
