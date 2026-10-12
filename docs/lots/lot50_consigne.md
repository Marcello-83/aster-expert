# Lot 50 — Pontons aluminium : une travée au niveau PRO, de la fiche aux torseurs

**Tout en français. Profil `vm`. Branche `lot-50`, depuis `main` après fusion
de `lot-49ter`.** Consigne copiée dans `docs/lots/lot50\_consigne.md`.

## Contexte et règles de ce lot

* **Projet nouveau, réel.** Il s'agit d'une passerelle d'accès sur pieux (une
« panne », au sens portuaire), en aluminium soudé.

  * Elle est reprise d'une étude d'avant-projet (AVP) faite sous Sofistik, pour
un calcul de niveau PRO.
  * Nom du projet : `pontons\_alu\_01`. Aucun terme interdit pour l'instant
(décision de MM).
* **Vocabulaire.**

  * « Panne » désigne l'ouvrage entier.
  * Les « pannes secondaires » sont les tubes longitudinaux qui portent le
platelage bois.
  * Ne les confonds pas.
* **Source unique des données : l'annexe « Données » de cette consigne.** Elle a été
extraite des notes AVP par le superviseur, puis arbitrée par MM (décisions
P1 à P23). Il n'y a pas d'autre annexe.

  * Les notes AVP ne sont pas dans le dépôt et n'y entrent pas.
  * Toute donnée absente de l'annexe « Données » est signalée. Elle n'est jamais
inventée.
* **Délai court.** MM a une échéance vendredi. Le lot vise le maximum de
résultats exploitables, avec des **points d'arrêt utilisables** : chaque
étape terminée est commitée et déposée avant de passer à la suivante.
* **Économie.**

  * Aucune refactorisation du tronc commun.
  * Aucune régénération des autres projets.
  * Aucun audit.
  * Pendant le développement, seuls les tests ciblés tournent. La batterie
complète et ci-lent ne tournent qu'à la fin.
  * Le code propre au projet est admis s'il est court. Le générateur
déclaratif viendra plus tard ; ce projet en sera le troisième exemple.
  * **Pas de contrôles à outrance** (demande expresse de MM). On fait le
harnais D par défaut et les deux contrôles analytiques de l'étape 3, rien
de plus. Pas de variante d'exécution, pas d'étude de maillage.
  * Les diagrammes, les images et les MED ne sont livrés que si la chaîne
générique des lots 49 à 49 ter les produit **sans développement
nouveau**.
* **Hors périmètre** :

  * vérifications EC9 (lot ultérieur) ;
  * vérification des poteaux existants ;
  * poussée d'Archimède et tablier immergé (P9) ;
  * critère de flèche (P14).

## Forme des fichiers (demande de MM)

MM doit pouvoir **lire et modifier lui-même** le maillage et le `.comm`.

* **Maillage : un script Python autonome**, `maillage\_pontons.py`, dans le
dossier du projet.

  * Il utilise le mailleur déjà employé pour l'estacade.
  * Les paramètres de l'annexe « Données » (§D2) sont en tête du script, un
par ligne, avec leur unité et leur décision P.
  * Il est construit par blocs commentés : tablier, supports, chevêtre,
poteaux, semelle, groupes.
  * Il produit `pontons.med`, sans aucune dépendance au code d'AsterExpert.
  * La commande pour le relancer est écrite en tête du script.
* **`.comm` lisible**, lu directement avec ce MED par `LIRE\_MAILLAGE`.

  * **En-tête** : projet, version de Code\_Aster, unités, renvoi aux décisions
P.
  * **Paramètres** : un bloc de paramètres en Python (charges, températures,
pressions).
  * **Ordre des sections, chacune titrée** : maillage, modèle, matériaux,
caractéristiques, liaisons et appuis, cas de charge, résolution, sorties.
  * **Pas de listes dépliées** : ce qui se répète (cas de charge, positions)
s'écrit avec des boucles ou des dictionnaires Python. Aucune liste de
nœuds ni de valeurs de plus de 20 lignes.
  * **Contenu** : le `.comm` calcule les cas élémentaires. Les combinaisons et
les livrables restent dans le post-traitement de l'outil.
  * **Taille** : cible de moins de 400 lignes.
  * **Commentaires** : techniques et courts, sans commentaire conversationnel.
* L'outil s'en sert comme d'habitude : validation B, exécution, `.mess`,
harnais, livrables. Si le générateur de projet existant est utilisé, il doit
produire exactement cette forme.
* **Repli.** Si cette forme demande un développement notable dans la chaîne
existante, garde le flux habituel pour ce lot, et dis dans le compte rendu
ce qui l'a empêché. MM accepte ce repli.

## Étape 0 — Fiche

* `aster-expert projet creer pontons\_alu\_01`.
* Enregistre les décisions P1 à P23 par `aster-expert fiche enregistrer`.
* Renseigne `planned\_commands` et `engineering\_summary` :

  * familles : poutres principales, montants, diagonales, pannes secondaires,
profilés supports, chevêtre, poteaux, semelle ;
  * sections de dimensionnement ;
  * états limites ;
  * en-tête de flexion composée du chevêtre.
* `fiche obligatoires` : rapporte ce qu'il trouve.

**Point d'arrêt 0** : la fiche est commitée.

## Étape 1 — Maillage filaire et semelle

* Le modèle est **paramétré** (annexe « Données », §D2) :

  * portée L ;
  * entraxe des poutres principales B ;
  * ordonnées des pannes ;
  * abscisses des montants ;
  * sens des diagonales ;
  * cotes NGF.

  La géométrie du PRO peut changer (P2) : un changement de paramètre ne doit
demander aucun code.

* **Nœuds partagés.** Partout où deux éléments sont soudés (P6), ils partagent
un nœud. Les pannes secondaires sont reliées aux montants **et** aux
diagonales qu'elles croisent (P7).

  * Leur excentricité verticale est représentée par une liaison rigide entre
le nœud de la panne et le nœud du montant ou de la diagonale situé
au-dessous.
  * Choisis le moyen dans la documentation 17.4 et cite la référence.
* **Repère des coordonnées.** Les coordonnées sont en mètres, recalées sur
une grille de 1 mm. L'axe X suit le tablier, avec X = 0 à l'appui côté quai.
Y est transversal. Z est la cote NGF.
* **Groupes.**

|Groupe|Éléments|
|-|-|
|`POUTRES\_PRINC`|poutres principales|
|`MONTANTS`|montants|
|`DIAGONALES`|diagonales|
|`PANNES\_SEC`|pannes secondaires|
|`SUPPORTS`|profilés supports|
|`CHEVETRE`|chevêtre|
|`POTEAUX`|poteaux|
|`SEMELLE`|semelle|
|`APP\_QUAI`|nœuds d'appui côté quai|
|`PIEDS\_SUPPORTS`|pieds des profilés supports|
|`TETES\_POTEAUX`|têtes des poteaux|

  Ajoute aussi un groupe par élément pour les extrêmes.

* **Discrétisation.** Au plus 0,25 m sur les barres, et au moins 4 éléments
par barre. La semelle a des mailles d'au plus 0,25 m.
* `mesh check`, invariant de grille compris.

## Étape 2 — `.comm`, exécution jusqu'au niveau C

* **Éléments.** Tous les choix viennent du catalogue et de la documentation
17.4, avec leurs références. Aucun mot-clé de mémoire. Recherche au moins un
cas test proche (poutres 3D avec excentricité, coque sur appui élastique).

  * **Aluminium** : poutres de Timoshenko 3D. Pour la section ouverte MP1200,
dis si une formulation avec gauchissement est utile pour le calcul des
efforts. La vérification au déversement relève de l'EC9, hors lot.
  * **Béton** : poutres pour le chevêtre et les poteaux.
  * **Semelle** : coque.
  * **Sol** : appui élastique réparti sous la semelle (P19).
* **Liaisons et conditions aux limites** (P5, P6, P18) :

  * **côté quai** : rotules fixes aux deux extrémités des poutres
principales, translations bloquées et rotations libres ;
  * **profilés supports** : soudés au tablier (encastrés) et articulés sur le
chevêtre (platine boulonnée), translations transmises ;
  * **poteaux** : encastrés dans le chevêtre et dans la semelle. Le
décalage entre le plan moyen de la semelle et le pied du poteau, et celui
entre l'axe du chevêtre et la tête du poteau, sont représentés.
* **Repère local des barres.** Fixe et documente l'orientation, l'axe fort
des poutres principales étant horizontal. Dans le tableau des efforts AVP,
l'axe y est l'axe fort ; le repère Code\_Aster peut différer, alors écris la
correspondance.
* **Cas de charge** : annexe « Données », §D4. Un cas élémentaire par action et par
variante de position. Températures : seulement sur les éléments en
aluminium.
* **Combinaisons** : annexe « Données », §D5. Il y a **deux jeux** :

  * **A, « modèle AVP »** : les combinaisons du fichier Sofistik de l'AVP,
reproduites telles quelles. Leurs défauts sont relevés en §D5, et ce jeu
sert seulement à la comparaison ;
  * **B, « PRO »** : combinaisons générées par l'outil à partir des formules de
l'EN 1990 et du tableau des coefficients de la note d'hypothèses.

  Les cas de houle sont calculés sous une pression unitaire de 1 kPa, mise à
l'échelle dans les combinaisons (20 / 10 kPa en A, 5 / 5 kPa en B). Les deux
jeux viennent d'**une seule exécution**.

* Exécution, analyse du `.mess`, niveau C.

**Point d'arrêt 2** : le `.comm` et le `.mess` sont commités ; le niveau C est
atteint.

## Étape 3 — Contrôles (niveau D)

* Harnais D : équilibre par cas, résultantes des charges, convergence si
applicable.
* **Contrôles analytiques**, écrits et commités avant la lecture des
résultats :

  * sous G1 seul, la réaction totale est égale au poids calculé à la main à
0,5 % près ;
  * sous Q = 5 kPa sur tout le tablier, la somme des moments des deux poutres
principales et des pannes secondaires à mi-portée, ajoutée à la part
transmise par les montants, est comparée à q·b·L²/8 ;

    * b est la largeur chargée ;
    * le tablier est pratiquement isostatique entre la rotule et les
supports ;
    * tolérance de 10 %. Au-delà, explique l'écart ;
  * **température** : rapporte l'effort normal des poutres principales
sous T+ et T−, et le déplacement en tête des poteaux. Ce sont eux qui
mesurent la retenue entre la rotule côté quai et les profilés supports
fixes.
* Plausibilité : flèche UZ sous l'ELS caractéristique. Pour mémoire, l'AVP
donne −29,6 / +7,5 mm et UY = 2,7 mm. La géométrie diffère : c'est un ordre
de grandeur, pas un critère.

## Étape 4 — Livrables

* **Classeur, feuille « Synthèse ingénieur »**, par famille d'aluminium
(poutres principales, montants, diagonales, pannes secondaires, profilés
supports) :

  * ELU fondamental, ELU accidentel et ELS caractéristique ;
  * jeux A et B ;
  * pour N, Vy, Vz, Mx, My et Mz min et max, le torseur concomitant complet,
avec le lieu, la combinaison et le cas ;
  * présentation et signes alignés sur les tableaux de l'AVP : N > 0 en
traction, repère local déclaré.

  Ces torseurs alimentent les feuilles EC9 de MM. Ajoute un CSV par famille,
au format de flexion composée du lot 49 bis, sans en-tête béton.

* **Chevêtre** (béton armé neuf, P16) :

  * sections de dimensionnement : au droit des profilés supports, sur appui
(nu des poteaux) et à mi-portée entre les poteaux ;
  * CSV de flexion composée : 0,25 × 0,40 m, C35/45, XS3, cnom = 55 mm,
ds = di = 0,07 m à confirmer par MM ;
  * états limites ELU, ELUA, ELS et ELSfiss ; ELSfiss = ELS quasi permanent,
par défaut de l'outil, à confirmer par MM ;
  * efforts de flexion biaxiale et de torsion, rapportés tous les deux, avec
leur torseur concomitant.
* **Réactions** côté quai et aux pieds des poteaux, par combinaison
enveloppe, plus les efforts en tête des poteaux. On ne vérifie pas les
poteaux, mais MM en aura besoin plus tard.
* **Déplacements** : UZ min et max, UY max, UX aux appuis, sous l'ELS
caractéristique.
* **Comparaison avec l'AVP** (annexe « Données », §D6) : ordres de grandeur famille par
famille. **Ce n'est pas une référence de validation** : la géométrie du PRO
diffère.
* Diagrammes N, M, V par famille, images ParaView, MED de résultats et
manifeste d'empreintes (lots 49 à 49 ter).

**Point d'arrêt 4** : dépôt dans
`/media/sf\_partage/echanges/lot50/pontons\_alu\_01/`.

## Compte rendu attendu — EN FRANÇAIS

1. **Fiche** : P1 à P23, sortie de `fiche obligatoires`, et données
manquantes signalées.
2. **Modèle** : nombre de nœuds et d'éléments, groupes, liaisons, références
documentaires, cas test proche, et une image du maillage.
3. **Niveau C** : alarmes du `.mess` et leur traitement.
4. **Niveau D** : contrôles analytiques, harnais, effet de la température.
5. **Synthèse ingénieur** des deux jeux, comparaison avec l'AVP, efforts du
chevêtre, écarts de l'AVP relevés dans S2.
6. **Points à trancher par MM**, en particulier ce qui dans les résultats
dépend fortement d'une hypothèse non confirmée.
7. Contrôles, `rex`, interventions, et la consigne de redémarrage si un outil
MCP a changé.

## Interdits

* Aucune donnée hors annexe « Données » sans le signaler.
* Aucun mot-clé Code\_Aster énoncé de mémoire.
* Aucune modification des projets existants.
* Aucune suppression dans `data/processed/runs/`.

\---

# Annexe « Données » — données et décisions (superviseur et MM, 12/10/2026)

**Sources.**

* Note d'hypothèses et note de dimensionnement de l'AVP.
* Fichier Sofistik de la travée de l'AVP, dit « S2 » ci-dessous.
* Coupe type du projet, dite « coupe PRO ».
* Réponses de MM.

S2 décrit le modèle de l'AVP ; il n'est pas une référence pour le PRO. En cas
de conflit, les décisions ci-dessous priment.

## D1. Décisions

* **P1. Travée.** **L = 6,25 m** (S2 : têtes de poteaux à X = 6,25 ; la note
arrondit à 6,20). Poteaux de **1,32 m** de haut, du dessus de la semelle au
dessous du chevêtre (MM).
* **P2. Géométrie en plan du tablier : celle de S2** (§D2). L'entraxe des
poutres principales vaut B = 1,50 m, à l'aplomb des axes des poteaux (2,00 m
nu à nu). Le modèle reste paramétré.
* **P3. Plate-forme, telle que dans la coupe PRO.**

  * Deux poteaux surmontés d'un **chevêtre transversal neuf**, et non le cadre
de couronnement de S2.
  * Le tablier s'appuie sur le chevêtre par **trois profilés supports** (les
« profilés alu support » de la coupe PRO) :

    * un sous chaque poutre principale ;
    * un au milieu, sous un **montant d'extrémité** ajouté à X = L. Dans S2, les
poutres principales se raccordaient directement au couronnement.
  * Chevêtre : 0,25 m de large en X sur 0,40 m de haut, de +0,69 à +1,09 NGF,
de Y = −1,00 à +1,00. Sa largeur est à affiner.
* **P4.** Les poutres principales sont en **MP1200** (note de
dimensionnement, §2.3, et fiche du fabricant). S2 utilise une section
« I300 - T19 », environ 12 fois plus raide : c'est un écart de l'AVP à
signaler, qui n'est pas repris.
* **P5. Appuis.** Rotules fixes côté quai, aux deux extrémités des poutres
principales : translations bloquées, rotations libres (`FIX PP` dans S2).
Les profilés supports sont fixes, sans glissement, côté chevêtre.
* **P6.** Tous les assemblages de la travée sont **soudés et encastrés**. Les
assemblages entre travées sont boulonnés, sans objet ici.
* **P7. Plans.**

  * Les poutres principales, les montants et les diagonales ont le même plan
moyen.
  * Les pannes secondaires reposent sur les montants et les diagonales, et y
sont soudées à chaque croisement : S2 coupe toutes les lignes à leurs
intersections.
  * L'axe des pannes est à **0,10 m** au-dessus du plan moyen, soit
(150 + 50)/2 mm. S2 prend 0,09 m.
* **P8. G2 = 1,0 kN/m²** sur tout le tablier : platelage bois et équipements,
valeur du modèle AVP (S2).
* **P9. Houle.**

  * Jeu PRO : on garde **5 kPa vers le haut et 5 kPa vers le bas**, comme dans
la note d'hypothèses et selon la décision de MM. Pas de poussée
d'Archimède ni de cas immergé pour l'instant.
  * Le modèle AVP (S2) appliquait en réalité **20 kPa vers le haut et 10 kPa
vers le bas**. C'est un écart signalé à MM, et ces valeurs ne sont
reprises que dans le jeu A.
  * Réserve : le niveau d'eau le plus élevé (+1,61 NGF) dépasse le dessus du
tablier.
* **P10. Température.** T0 = 10 °C (NF EN 1991-1-5/AN). Tmax = +40 °C,
Tmin = −15 °C. Tablier de type 1 :

  * Te,max = Tmax + 16 = +56 °C ;
  * Te,min = Tmin − 3 = −18 °C ;
  * **ΔTN,exp = +46 °C** ;
  * **ΔTN,con = 28 °C**, soit une variation de −28 °C ;
  * composante uniforme, appliquée à **tout l'aluminium**.

  S2 appliquait +56 °C et −23 °C (−15 − 8), sans T0, aux poutres
principales, aux montants et aux diagonales seulement. Ces valeurs ne sont
reprises que dans le jeu A.

* **P11. Coefficients**, d'après le tableau complet de la note d'hypothèses
(§D5).
* Jeu PRO : γ = 1,5 pour la houle (MM) et pour la température (EN 1990,
annexe A2). L'AVP prenait 1 pour les deux. 
* **P12. Combinaisons.** Le jeu A reproduit S2 (§D5). Le jeu B est généré
par les formules de l'EN 1990.
* **P13. Amarrage et accostage**, comme dans S2.

  * **Amarrage** : 2 × 8,0 kN horizontaux transversaux, à X = 1,60 et
X = 4,60, sur une poutre principale, tirant vers l'extérieur.
  * **Accostage** caractéristique (16 kN/m) et accidentel (77 kN/m) : de
X = 1,63 à X = 3,63, sur une poutre principale, poussant vers
l'intérieur.
  * S2 charge seulement la poutre en Y = −0,75. Le jeu B traite aussi le côté
Y = +0,75, en symétrique, dans des cas exclusifs.
  * Défaut relevé dans S2 : l'amarrage y est appliqué sur la ligne `SLN 11`,
qui est le couronnement, avec des abscisses hors de sa longueur. Il est
remis ici sur la poutre principale.
* **P14.** Les flèches sont rapportées, sans critère.
* **P15.** On en fait le maximum ; l'EC9 viendra après.
* **P16.** Le chevêtre est dimensionné. Les poteaux ne sont pas vérifiés.
* **P17. Section des profilés supports.** Ils figurent sur la coupe PRO, mais
leur section n'est donnée nulle part. Hypothèse : tube carré 150 × 150 × 7
en 6082-T6, comme les montants, de +1,09 à +1,24 NGF. 
* **P18. Liaison des profilés supports.** Soudés et encastrés sous le
tablier. Articulés sur le chevêtre (platine boulonnée), translations
transmises. 
* **P19. Semelle et sol.**

  * On modélise la demi-semelle sous la file de poteaux : X ∈ \[L − 0,50 ;
L + 0,76], Y ∈ \[−1,45 ; 1,45]. Le débord de 0,50 et 0,70 m vient de S2.
  * Épaisseur **0,25 m** (note de dimensionnement ; S2 prend 0,17 m). Dessus
à −0,63 NGF.
  * Raideur normale du sol 5 000 kN/m³, raideur tangentielle 1 000 kN/m³ (S2
et note).
* **P20. Béton.** C35/45, Ecm = 34 GPa, ν = 0,2, pour les poteaux existants
(Ø 0,50 m), le chevêtre neuf et la semelle.
* **P21. Cotes verticales.**

  * Dessous des poutres principales : +1,24 NGF. Plan moyen : +1,3575.
  * Axe des pannes secondaires : +1,4575.
  * Réserve : le dessus du platelage arrive vers +1,51, contre +1,40 sur la
coupe PRO. L'écart est signalé à MM ; il est sans effet notable sur les
efforts.
* **P22.** Les actions de surface (G2, Q, houle) sont réparties sur les barres
longitudinales (poutres principales et pannes secondaires) par largeurs
d'influence. Le platelage n'a pas de raideur.
* **P23.** La fissuration du chevêtre est vérifiée à l'ELS quasi permanent
(défaut de l'outil), avec ds = di = 0,07 m. 

## D2. Géométrie (X le long du tablier, Y transversal, Z en NGF)

* **Rotules côté quai** : X = 0, Y = ±0,75.
* **Poutres principales** : Y = ±0,75, de X = 0 à X = 6,25.
* **Montants** : de Y = −0,75 à +0,75, à **X = 0 ; 0,75 ; 2,25 ; 3,75 ;
5,25** (S2), plus le montant d'extrémité à X = 6,25 (P3).
* **Diagonales**, d'après S2 :

  * (0 ; +0,75) → (0,75 ; −0,75) ;
  * (0,75 ; +0,75) → (2,25 ; −0,75) ;
  * (2,25 ; +0,75) → (3,75 ; −0,75) ;
  * (3,75 ; +0,75) → (5,25 ; −0,75) ;
  * (5,25 ; +0,75) → (6,25 ; −0,75).
* **Pannes secondaires** : Y = **+0,56 ; +0,19 ; −0,18 ; −0,55** (S2), de
X = 0 à X = 6,25, reliées à chaque croisement (P7).
* **Profilés supports** : X = 6,25 et Y = −0,75 ; 0 ; +0,75, de +1,09 à +1,24.
* **Chevêtre** : axe à Z = +0,89 et X = 6,25, de Y = −1,00 à +1,00.
* **Poteaux** : X = 6,25 et Y = ±0,75, de −0,63 à +0,69.

  * En tête, un tronçon rigide de +0,69 à +0,89 les relie à l'axe du chevêtre.
  * En pied, un tronçon rigide les relie au plan moyen de la semelle, à
−0,755.
* **Semelle** : plan moyen à −0,755 ; X ∈ \[5,75 ; 7,01] ; Y ∈ \[−1,45 ; 1,45].

## D3. Sections et matériaux

**Aluminium** :

* E = 70 000 MPa, G = 27 000 MPa, ν = 0,3, α = 23·10⁻⁶ /°C ;
* poids volumique 27 kN/m³.

|Famille|Section|Alliage|Caractéristiques|
|-|-|-|-|
|Poutres principales|MP1200 (fiche du fabricant)|6005A-T6|A = 4 440 mm² ; I axe fort = 25 641 511 mm⁴ ; I axe faible = 10 209 212 mm⁴ ; Wel,fort = 218 166 mm³ ; Wel,faible = 145 794 mm³ ; h = 235 mm ; It = 1 207 cm⁴ et Avz = 17,41 cm² (feuilles AVP)|
|Montants, diagonales, profilés supports (P17)|tube carré 150 × 150 × 7|6082-T6|A = 4 004 mm² ; I = 1 368 cm⁴ ; It ≈ 2 047 cm⁴|
|Pannes secondaires|tube carré 50 × 50 × 5|6082-T6|A = 900 mm² ; I = 30,75 cm⁴ ; It ≈ 45,6 cm⁴|

Les sections des tubes sont prises à angles vifs, avec It par la formule de
Bredt. Vérifie-les par ton propre calcul. Si un catalogue du fabricant donne
des valeurs avec rayons d'angle, elles priment et sont citées.

**Béton** : chevêtre en rectangle de 0,25 × 0,40 m ; poteaux en cercle plein
de Ø 0,50 m ; semelle en coque de 0,25 m.

## D4. Cas de charge élémentaires

|Cas|Description|
|-|-|
|G1|Poids propre de tous les éléments (aluminium 27 kN/m³, béton armé 25 kN/m³)|
|G2|1,0 kN/m² sur tout le tablier (P8, P22)|
|Q|5 kPa sur tout le tablier ; variante Q½ sur la moitié côté Y > 0|
|Hu|Pression unitaire de 1 kPa vers le haut sur tout le tablier (houle « sous-pression »)|
|Hd|Pression unitaire de 1 kPa vers le bas (houle « surpression »)|
|T+ / T−|+46 °C / −28 °C uniformes sur tout l'aluminium (jeu B)|
|TA+ / TA−|+56 °C / −23 °C sur les poutres principales, les montants et les diagonales (jeu A, S2)|
|AM− / AM+|Amarrage 2 × 8,0 kN à X = 1,60 et 4,60, vers l'extérieur, sur la poutre Y = −0,75 ou Y = +0,75|
|AC− / AC+|Accostage caractéristique 16 kN/m de X = 1,63 à 3,63, vers l'intérieur, sur la poutre Y = −0,75 ou Y = +0,75|
|ACA− / ACA+|Accostage accidentel 77 kN/m, mêmes positions|

## D5. Combinaisons

### Jeu A — reproduction des combinaisons de S2

G = G1 + G2. H désigne 20·Hu ou 10·Hd, exclusifs. TA désigne TA+ ou TA−,
exclusifs.

|N° S2|Type|G (défavorable / favorable)|H|TA|Q|Autre|
|-|-|-|-|-|-|-|
|10|ELU fondamental|1,2 / 0,9|1,0|0,6|1,3|AC− 1,0|
|20|ELU fondamental|1,2 / 0,9|1,0|0,6|1,3|AM− 1,0|
|30|ELU fondamental|1,2 / 0,9|1,0|0,6|1,0|AM− 1,0|
|40|ELU fondamental|1,2 / 0,9|1,0|0,6|1,0|AC− 1,3|
|50|ELU accidentel|1,0|1,0|0,6|0,26|ACA− 1,0|
|60|ELS caractéristique|1,0|1,0|0,6|1,0|AC− 0,77|
|70|ELS caractéristique|1,0|1,0|0,6|1,0|AM− 1,0|
|80|ELS caractéristique|1,0|1,0|0,6|0,77|AM− 1,0|
|90|ELS caractéristique (typée ELU fondamental dans S2)|1,0|1,0|0,6|0,77|AC− 1,0|

Dans S2, les actions variables affectées d'un facteur 0 côté favorable
(Q, AM, AC, ACA) sont prises à 0 ou au facteur indiqué, au plus défavorable.

**Défauts de S2**, à rapporter sans les corriger dans le jeu A :

* en 30 et 40, les libellés « accostage » et « amarrage » sont inversés, et
les facteurs de AM et AC sont échangés par rapport au tableau de la note ;
* la houle est déclarée comme une action permanente, présente à 1,0 dans
toutes les combinaisons ;
* l'ELU accidentel prend Q à 0,26 et la température à 0,6 ;
* la combinaison 90 est typée ELU ;
* une instruction `end` après la combinaison 40 laisse peut-être les
combinaisons 50 à 90 hors du module de combinaison. C'est à signaler, mais
impossible à vérifier sans Sofistik.

### Jeu B — PRO, combinaisons générées

|Action|ψ0|ψ1|ψ2|γ défavorable|γ favorable|
|-|-|-|-|-|-|
|G (G1 + G2)|—|—|—|1,2|0,9|
|H (5·Hu ou 5·Hd)|0,77|0,77|0,2|**1,5**|0|
|T (T+ ou T−)|0,6|0,6|0,5|**1,5**|0|
|AM|0,77|0,77|0,2|1,30|0|
|AC|1|0|0|1|0|
|Q (Q ou Q½)|0,77|0,77|0,2|1,3|0|

**Formules (EN 1990)** :

* ELU fondamental : Σγ\_G·G + γ\_Q1·Q\_k1 + Σγ\_Qi·ψ0,i·Q\_ki ;
* ELU accidentel : ΣG + ACA + ψ1,1·Q\_k1 + Σψ2,i·Q\_ki ;
* ELS caractéristique : ΣG + Q\_k1 + Σψ0,i·Q\_ki ;
* ELS fréquent : ΣG + ψ1,1·Q\_k1 + Σψ2,i·Q\_ki ;
* ELS quasi permanent : ΣG + Σψ2,i·Q\_ki.

**Règles de génération** :

* chaque action variable est tour à tour dominante ;
* G est pris favorable ou défavorable en bloc ;
* exclusions mutuelles :

  * Hu et Hd ;
  * T+ et T− ;
  * AM− et AM+ ;
  * AC− et AC+ ;
  * ACA− et ACA+ ;
  * Q et Q½ ;
* ACA n'entre que dans l'ELU accidentel, et AC n'y entre pas.

Rapporte le nombre de combinaisons par état limite.

## D6. Résultats AVP (note de dimensionnement), pour comparaison seulement

Ils ont été obtenus avec un modèle dont les sections (P4) et les charges (P9,
P10) diffèrent : ce sont des ordres de grandeur, pas une référence.

|Famille|ELU fondamental|ELU accidentel|
|-|-|-|
|Poutres principales|N −139 / +78 kN ; Vy −18 / 13 ; Vz −28 / 20 ; My −32 / 20 kN·m ; Mz −5 / 5|N −150 / +123 ; Vy −60 / 49 ; My −23 / 20 ; Mz −15 / 7|
|Montants|N −33 / +38 ; Vy −26 / 29 ; My −7 / 4|N −41 / +108 ; My −10 / 9|
|Diagonales|N −53 / +32 ; My −10 / 5|N −156 / +60 ; My −18 / 4|
|Pannes secondaires|N −51 / +64 ; Vy −5 / 8 ; My −1 / 1|N −42 / +53 ; Vy −10 / 10|
|Poteaux|N −72 / +14 ; My −20 / 52 kN·m|N −58 / +26 ; Mz −20 / 17|

Déplacements AVP, en ELS caractéristique : UZ = −29,6 / +7,5 mm, UY = 2,7 mm.

