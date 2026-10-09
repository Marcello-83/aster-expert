# Lot 49 bis — consigne (recopiée de la demande de MM)

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-49bis` créée depuis `main` après fusion de `lot-49`).

# Lot 49 bis — Synthèse ingénieur : efforts par famille d'éléments, torseurs concomitants, états limites, diagrammes

**Tout en français. Profil `vm`.** Branche `lot-49bis`, depuis `main` après la
fusion de `lot-49`. Termes interdits : ceux du lot 47. Consigne copiée dans
`docs/lots/lot49bis_consigne.md`. Redémarre la session avant de commencer :
l'outil `query_results` a été ajouté au lot 49.

## Pourquoi

Le lot 49 a produit des livrables justes et traçables, mais **le classeur n'est
pas lisible par un ingénieur**. Constats de MM et du superviseur sur le
classeur de l'estacade :

1. **Le classeur est trop long.** « Efforts par élément » compte 2 520 lignes, en
   format long : une ligne par composante. « Enveloppes » en compte 2 578.
2. **La « famille » est un type de champ, pas un élément d'ouvrage.** La
   Synthèse regroupe « efforts_poutres » et mélange ainsi pieux et chevêtres.
   Il manque la lecture naturelle : « pieux : N max, M max ; chevêtres : M en
   travée, M sur appui, V ; tablier : M en chapeau, M en travée, V ».
3. **Pas de torseur concomitant.** Un M max sans le N et le V qui
   l'accompagnent ne sert à rien pour une vérification en flexion composée.
4. **Tous les états limites sont confondus** dans une seule enveloppe, si bien
   que l'ELU masque tout. L'ELS caractéristique, l'ELS fréquent et l'ELS quasi
   permanent sont nécessaires pour la fissuration et les contraintes.
5. **Des valeurs sans signification physique** sont affichées sans
   avertissement. Exemple : QY de la dalle = 10 409 kN/m sur la ligne du
   chevêtre, nœuds partagés entre la dalle et la poutre (CA-058). La
   Synthèse dit « hors disques d'exclusion », mais une ligne de nœuds partagés
   n'est pas un disque.
6. **Images.**
   - Les unités sont en SI brut (N·m, avec des légendes comme « 2,7e+05 »).
   - Les charges sont dessinées à chaque nœud du maillage de 0,05 m, et
     forment des blocs illisibles.
   - Il n'y a ni titre portant le cas et la valeur extrême, ni vue en plan ou
     en élévation.
   - Il manque surtout les **diagrammes classiques** : M, N et V le long d'un
     pieu ou d'un chevêtre, en 2D, avec les valeurs extrêmes inscrites.

Ce lot ne change ni les calculs ni les MED. Il ajoute une **couche de synthèse
ingénieur générique**, déclarée par projet.

## Étape 1 — Déclaration générique dans `projet.yaml`

Section `synthese` (nom à justifier), validée par le schéma :

1. **Familles d'éléments d'ouvrage** : un nom métier (« pieux », « chevêtres »,
   « tablier », « ressorts de sol », « appuis »), les groupes de mailles, le
   type (poutre, coque, discret, appui) et les grandeurs de dimensionnement de
   la famille.
2. **Sections de dimensionnement** nommées, chacune avec une règle de lecture
   explicite :
   - estacade : tête de pieu, bouchon, pieu courant, chevêtre en travée,
     chevêtre au nu de l'appui, dalle en chapeau au nu du chevêtre, dalle en
     travée, dalle en rive ;
   - pour une coque : soit une ligne de coupe, soit une zone. Elle exclut les
     disques de singularité (PAT-013) **et les lignes de nœuds partagés avec
     des poutres** (CA-058), sans quoi la valeur est marquée « non
     significative ».
3. **Familles de combinaisons par état limite**, tirées des combinaisons
   déclarées : ELU fondamental, ELU accidentel, ELS caractéristique, ELS
   fréquent, ELS quasi permanent.
4. **Critères de service déclarés** et leur source : flèche de poutre ≤ L/400,
   déplacement en tête de pieu ≤ h/400 pour l'estacade (§14.2 de la source).
5. Remplis la section pour les trois projets, et justifie chaque section de
   dimensionnement en une ligne.

## Étape 2 — Torseurs concomitants

Pour chaque famille × section × état limite :

- **poutres** :
  - N max et N min, avec les M et V concomitants ;
  - M max (composantes et résultante pour les sections circulaires), avec
    les N et V concomitants ;
  - V max, avec les N et M concomitants ;
- **coques** : Mxx et Myy max et min, avec les N concomitants (pour la flexion
  composée par bande) et les V associés ;
- **pour chaque ligne** : la combinaison, la position de charge mobile, le lieu
  (groupe, élément, coordonnées) et l'unité.

Les torseurs sont lus dans les résultats du lot 49, par `resultats lire`, sans
calcul nouveau. **Test** : sur l'estacade, le torseur de tête de pieu ELU de
F7_YP retrouve M = 435,5 kN·m (lot 47 bis), avec ses N et V.

**Export pour le logiciel de flexion composée de MM (saisie manuelle).** MM
recopie à la main, dans son logiciel, la géométrie et un tableau
« Type | N (kN) | M (kN·m) », avec la convention « M > 0 comprime la fibre
supérieure ». Le fichier doit donc se recopier ligne par ligne, sans
réfléchir.

- **Un fichier par section de dimensionnement** :
  `flexion_composee/<section>.csv`. Séparateur `;`, virgule décimale, UTF-8 avec
  BOM, pour qu'Excel en français l'ouvre directement.
- **Bloc d'en-tête**, une ligne par donnée, dans l'ordre de saisie du logiciel :
  - type de section, h (m), b (m), ds (m), di (m) ;
  - classe de béton, acier, classe d'exposition, cnom (mm) ;
  - pour une dalle, b = 1,00 m : les efforts sont par mètre ;
  - pour une section circulaire saisie en section équivalente, la règle
    d'équivalence et sa source (bouchon : carré de 52 × 52 cm de même module
    d'inertie, §20.4.1 de la source).
- **Tableau des efforts**, avec les colonnes **dans l'ordre du logiciel** :
  `N° ; Type ; N (kN) ; M (kN.m)`.
  - Les colonnes de traçabilité viennent **après**, séparées par une colonne
    vide : combinaison, position de charge mobile, lieu (élément et cote),
    V concomitant, M et N bruts de Code_Aster avec leur repère.
- **Lignes limitées aux cas dimensionnants**, au plus 4 par état limite :
  - M max et M min, avec le N concomitant ;
  - N max et N min, avec le M concomitant.

  L'ordre des états limites est celui des libellés de la colonne « Type »
  (voir plus bas).
- **Conventions converties dans le fichier, jamais laissées à MM** :
  - M est mis dans la convention du logiciel, « M > 0 comprime la fibre
    supérieure ». La fibre supérieure de chaque section est déclarée dans la
    section `synthese` de `projet.yaml` (axe local et sens) ;
  - **N > 0 en compression**, confirmé par MM d'après une saisie de contrôle :
    section de 1,50 × 1,50 m, N = 5 000 kN, M = 2 000 kN·m, σb max = 6,35 MPa,
    résultat cohérent avec une compression dans une section fissurée.
    Code_Aster donne N > 0 en traction : la conversion est écrite en clair dans
    l'en-tête ;
  - pour une section circulaire en flexion déviée, le moment résultant
    √(MFY² + MFZ²) est exporté, avec une ligne d'avertissement. Le logiciel
    traite une flexion plane.
- Arrondi : N et M à 0,1. Une ligne de pied donne l'empreinte du MED source.
- **Libellés de la colonne « Type »** : exactement ceux de la liste déroulante
  du logiciel, donnés par MM : `ELU`, `ELUA`, `ELS`, `ELSfiss`. Correspondance :
  - ELU fondamental → `ELU` ;
  - ELU accidentel ou sismique → `ELUA` ;
  - ELS caractéristique → `ELS`, pour les limites de contraintes ;
  - **la famille de combinaisons qui sert à la maîtrise de la fissuration** →
    `ELSfiss`. Elle est **déclarée par projet** dans la section `synthese` et
    vaut par défaut l'ELS quasi permanent (EC2, 7.3.1).
    - Pour l'estacade, c'est l'**ELS fréquent** : la source vérifie
      wk ≤ 0,20 mm « sous combinaisons fréquentes » (§13.7.2).
    - Pour le quai, c'est l'ELS quasi permanent (décision D21, wk = 0,2 mm).
    - Une famille d'ELS qui n'est ni caractéristique ni de fissuration n'est
      pas exportée, et l'en-tête le signale.

  L'ordre des lignes devient : `ELU`, `ELUA`, `ELS`, `ELSfiss`.
- **Test** : le fichier de la tête de pieu F7_YP contient la ligne ELU avec
  |M| = 435,5 kN·m, et son N concomitant converti.

Joins dans le compte rendu un exemple complet, celui du bouchon de F7_YP.

## Étape 3 — Classeur restructuré

1. **Feuille 1 « Synthèse ingénieur »**, lisible sur un ou deux écrans :
   - un bloc par famille d'éléments ;
   - une ligne par section ;
   - des colonnes par état limite : ELU, ELS car., ELS fréq., ELS QP ;
   - des valeurs dimensionnantes avec torseurs concomitants ;
   - un renvoi au détail.
2. **Feuille 2 « Vérifications de service »** : critère, valeur, limite, taux,
   verdict.
3. **Feuille 3 « Torseurs »** en **format large** : une ligne par section ×
   combinaison, avec N, VY, VZ, MT, MFY, MFZ et la résultante.
4. **Feuilles de détail en format large** : un pieu ou un élément par ligne,
   les composantes en colonnes. Les tables longues brutes partent en CSV
   annexes, et ne restent pas dans le classeur.
5. Les feuilles existantes du lot 49 (réactions et équilibre, contrôles D et E,
   comparaison externe, conventions, provenance) sont **conservées, placées
   après**.
6. Partout :
   - en-têtes figés ;
   - largeurs de colonnes adaptées ;
   - format d'affichage par unité (table d'arrondis) ;
   - Arial 10, en-têtes sur fond gris ;
   - toute valeur « non significative » est grisée et accompagnée de son motif.

## Étape 4 — Diagrammes et images

1. **Diagrammes 2D (matplotlib), génériques par famille de poutres** :
   - M, N et V le long de chaque pieu, chevêtre ou poutre ;
   - enveloppe ELU et enveloppe ELS car. superposées ;
   - extrema annotés, avec leur valeur et leur cote ;
   - une planche par famille ;
   - unités en kN et kN·m.
2. **Coupes de dalle** : Mxx et Myy le long de coupes déclarées, avec les zones
   exclues hachurées.
3. **ParaView** :
   - unités converties en kN et kN·m dans les légendes ;
   - titres portant le cas ou la combinaison et la valeur extrême ;
   - deux vues en plus de l'isométrique : plan et élévation ;
   - **flèches des charges sous-échantillonnées**, avec un nombre maximal de
     flèches, ou regroupement sur une grille. Les flèches d'un cas
     surfacique doivent se lire comme une charge répartie, pas comme des blocs.
4. Toutes les images restent générées depuis le manifeste, sans aucune liste
   écrite à la main.

## Étape 5 — Application et retour de MM

1. Produis la synthèse des trois projets. **L'estacade sert de cas pilote** :
   dépose d'abord son classeur et ses planches dans
   `/media/sf_partage/echanges/lot49bis/estacade_pieux_01/`. Le lot ne s'arrête
   pas pour autant.
2. **Contrôles croisés** : chaque valeur de la Synthèse ingénieur retrouve sa
   source dans le MED par `resultats lire`, avec un test. La somme des réactions
   reste égale à la charge, par état limite.

## Compte rendu attendu — EN FRANÇAIS

1. Schéma de la section `synthese`, et sections de dimensionnement des trois
   projets.
2. Torseurs concomitants : méthode et test de F7_YP.
3. Classeur : plan des feuilles, avec une capture texte de la Synthèse
   ingénieur de l'estacade.
4. Diagrammes et images : liste, et corrections des défauts relevés.
5. Contrôles, `rex`, interventions.

## Interdits

- Aucun recalcul Code_Aster, sauf si une grandeur manque dans le MED. Dans ce
  cas, signale-le d'abord.
- Aucune section de dimensionnement propre à un ouvrage dans `src/` : tout est
  déclaré dans `projet.yaml`.
- Aucune valeur singulière présentée comme dimensionnante sans le marquage
  « non significative ».
- Aucun terme interdit dans le dépôt.
