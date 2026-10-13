# Lot 50 ter — Pontons aluminium : export des données pour l'EC9, les vues et les plans

**Tout en français. Profil `vm`. Branche `lot-50ter`, depuis `main` après
fusion de `lot-50bis`.** Consigne copiée dans `docs/lots/lot50ter_consigne.md`.

## Objet

**Lot d'export seulement.** Ni maillage nouveau, ni exécution Code_Aster
nouvelle, ni livrable de classeur ou d'image.

- Tout est lu dans les résultats du lot 50 bis : exécution de référence,
  P24 et P25, MP1200, k = 1.
- Le superviseur fera lui-même, dans Cowork, les vérifications EC9, les vues
  3D avec profils et charges, et les plans DXF, à partir de ces fichiers.

Règles d'économie du lot 50 : tests ciblés, batterie complète à la fin, rien
sur les autres projets.

## Format commun de tous les fichiers

- CSV, séparateur `;`, **point décimal**, UTF-8 sans BOM.
- Unités SI : N, N·m, m, Pa.
- Une ligne de commentaire en tête, commençant par `#`, donne :
  - la source (exécution, empreinte du MED) ;
  - les unités ;
  - les conventions de signe (Code_Aster brut : N > 0 en traction).
- Dépôt : `/media/sf_partage/echanges/lot50ter/pontons_alu_01/`, avec
  `empreintes.sha256`.

## Fichiers à produire

1. **`noeuds.csv`** : nœud, x, y, z, groupes d'appartenance.

2. **`elements.csv`**, pour toutes les barres, y compris le chevêtre, les
   poteaux et les liaisons rigides :
   - élément, type, nœud 1, nœud 2 ;
   - famille et groupe ;
   - section ;
   - vecteur y local (vx, vy, vz) tel qu'il est réellement affecté ;
   - excentricité ou liaison rigide éventuelle.

3. **`membres.csv`**. Un membre est une barre physique entre deux nœuds de
   soudure ou d'appui, par exemple « PP_YP de X = 0,75 à 2,25 ». Colonnes :
   - membre, famille, section ;
   - coordonnées de début et de fin ;
   - longueur ;
   - liste ordonnée des éléments ;
   - pour chaque extrémité et chaque nœud intermédiaire connecté : la liste
     des membres qui s'y raccordent, et la nature du raccord (soudé, liaison
     rigide, appui, articulation).

   C'est de là que le superviseur tire les longueurs de flambement, les
   maintiens latéraux et les zones soudées.

4. **`efforts_elementaires.csv`** : efforts aux deux extrémités de chaque
   élément (ELNO), pour **chaque cas élémentaire**. Colonnes :
   - cas, élément, membre ;
   - extrémité (1 ou 2) et nœud ;
   - abscisse le long du membre ;
   - N, VY, VZ, MT, MFY, MFZ.

   Les cas sont tous ceux du lot 50 bis : G1, G2, Q, Q½, Hu et Hd (1 kPa),
   T+, T−, AM±, AC±, ACA±, ainsi que TA± s'ils existent encore.

   Familles concernées : poutres principales, montants, diagonales, pannes
   secondaires, profilés supports, chevêtre.

5. **`deplacements_elementaires.csv`** : DX, DY, DZ, DRX, DRY, DRZ par nœud
   et par cas élémentaire.

6. **`reactions_elementaires.csv`** : réactions par nœud d'appui (rotules côté
   quai, ressorts de la semelle cumulés) et par cas élémentaire.

7. **`combinaisons.csv`** : jeux B et B′. Une ligne par combinaison :
   - identifiant ;
   - état limite (ELU fondamental, ELU accidentel, ELS caractéristique,
     fréquent, quasi permanent) ;
   - jeu ;
   - une colonne de facteur par cas élémentaire, en tenant compte de l'échelle
     de la houle.

8. **`charges.csv`** : les charges réellement appliquées, par cas élémentaire.
   Colonnes :
   - cas, type (répartie, ponctuelle, pression, température), groupe ou
     éléments ;
   - direction (repère global) ;
   - valeur ;
   - début et fin d'application, en abscisse ou en coordonnées.

   Le superviseur s'en sert pour dessiner les cas de charge. Ce sont les
   charges du `.comm`, pas celles de la consigne.

9. **`sections.csv`** : pour chaque section du `.comm`, toutes les
   caractéristiques réellement affectées (A, IY, IZ, JX, AY, AZ, etc.), avec
   leurs mots-clés et leurs valeurs.

**Contrôle unique.** Recombiner les cas élémentaires avec `combinaisons.csv`
doit redonner trois valeurs du lot 50 bis à 10⁻⁶ près en relatif :

- My max des poutres principales à l'ELU B : 53,2175 kN·m ;
- N min des pannes à l'ELU B : −85,6 kN ;
- N du profilé SUP_1 à l'ELU B : −58,0 kN.

Le script de recombinaison est livré avec les fichiers.

## Compte rendu attendu — EN FRANÇAIS, court

- Liste des fichiers avec leur nombre de lignes et leurs empreintes.
- Résultat du contrôle de recombinaison.
- Convention du repère local, avec un exemple par famille.
- Contrôles, `rex` et interventions.

## Interdits

- Aucune exécution Code_Aster nouvelle.
- Aucune modification des résultats du lot 50 bis.
- Aucune modification des autres projets.
