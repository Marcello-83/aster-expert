# Essais du lot 49 bis — synthèse ingénieur (familles d'éléments, torseurs concomitants, états limites, diagrammes)

Consigne : `docs/lots/lot49bis_consigne.md`. Profil **vm**. Code_Aster 17.4.0 (aucune
exécution nouvelle : les données lues sont celles des exécutions de post-traitement du
lot 49). Ce rapport suit `docs/modele_rapport_essai.md` : les sections 1 à 3 (objet,
méthode, critères) sont écrites et commitées **avant** la première lecture de la
synthèse sur les données réelles des trois projets ; elles ne sont pas modifiées ensuite
(une erreur s'y corrige dans une section datée « Correction du critère »).

## 1. Objet

1. Une couche de **synthèse ingénieur générique**, déclarée par projet dans
   `projet.yaml` (section `engineering_summary`) : familles d'éléments d'ouvrage,
   sections de dimensionnement avec leur règle de lecture, états limites tirés des
   familles de combinaisons, critères de service, en-tête des fichiers de flexion
   composée.
2. Pour chaque famille × section × état limite, les **torseurs concomitants** (N, V, M
   au même lieu, pour la même combinaison et la même position de charge mobile).
3. L'export pour le logiciel de flexion composée de MM, un fichier par section et par
   plan de flexion, conventions converties (N > 0 en compression, M > 0 comprime la
   fibre supérieure).
4. Un classeur restructuré (Synthèse ingénieur, Vérifications de service, Torseurs,
   détails en format large, feuilles du lot 49 conservées après) et des diagrammes 2D.
5. Des images ParaView en unités d'affichage, titrées, en trois vues, avec des flèches
   de charges regroupées.

Niveau visé : **aucun niveau nouveau**. La synthèse est une lecture des livrables du
lot 49 ; les niveaux des paquets (quai D, dalle E, estacade D) doivent être conservés,
aucun `.comm` de production n'est modifié, aucune exécution Code_Aster n'est lancée.

## 2. Méthode (écrite avant la lecture des données réelles)

### 2.1 Combinaisons et concomitance

**Fait établi dans la documentation 17.4 (niveau A)** : R3.08.01, § « Le tenseur des
contraintes » : N = ∫ σxx dS, MFY = ∫ z σxx dS, MFZ = −∫ y σxx dS (N > 0 en traction).
U4.42.01, § ORIENTATION : sans orientation donnée, le repère local d'une SEG2 suit la
maille (x_l le long du segment, rotation γ nulle). CA-045 : MXX > 0 tend la face
supérieure d'une coque DKT.

Une combinaison est la superposition des cas élémentaires et des positions mobiles
livrés (`cas/<cas>`, `pos/<position>` des tableaux du lot 49), avec les coefficients
déclarés : c'est l'arithmétique des combinaisons du lot 49 et de `aster-expert
resultats lire` (`<combinaison>@<position>`). Aucune grandeur ne manque dans les MED du
lot 49 : aucun recalcul n'est nécessaire.

Pour chaque état limite (familles de combinaisons déclarées) et chaque ligne d'une
famille (extrémité d'élément, nœud), le max et le min de chaque composante (et de
√(MFY² + MFZ²), √(VY² + VZ²) pour une section circulaire) sont gardés avec la
combinaison et la position qui les donnent. La valeur de dimensionnement d'une section
est l'extremum sur ses lignes ; son torseur est le vecteur complet en cette ligne, pour
cette combinaison et cette position.

### 2.2 Valeurs non significatives

Une coque exclut de sa valeur de dimensionnement les nœuds des disques d'exclusion
(PAT-013, `deliverables.exclusion_disks`) et les nœuds partagés avec une poutre
(CA-058, `shared_with` de la section). L'extremum lu dans ces zones, s'il dépasse la
valeur retenue, est rapporté à côté, marqué « non significative » avec son motif.

### 2.3 Conversion pour le logiciel de flexion composée

N(logiciel) = −N(Code_Aster). M(logiciel) = −MFY pour une fibre supérieure en +z_l,
+MFY en −z_l, +MFZ en +y_l, −MFZ en −y_l, −MXX (ou −MYY) pour la face de la normale
d'une coque. Section circulaire : √(MFY² + MFZ²) ≥ 0, avec un avertissement.

### 2.4 Critères de service (E21, E22, décisions de MM du lot 49 bis)

Déplacement horizontal en tête √(DX² + DY²) sous ELS caractéristique, limite
2,85 / 400 ; flèche relative aux appuis (corde des appuis retranchée ; console :
déplacement de l'appui retranché) sous ELS caractéristique hors PP, G2, TE+ et TE−.

## 3. Critères de réussite (écrits avant la lecture des données réelles)

| Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- |
| Torseur de tête de pieu, ELU fondamental, estacade : M résultant max | 435,49 kN·m (lot 47 bis, § 8 a), au nœud de tête +1,30 de PIEU_F7_YP, combinaison 111 ELU+, position TSB_P25 | exacte (même superposition des mêmes tableaux) | écart relatif ≤ 10⁻⁶ sur la valeur imprimée au lot 47 bis à 0,01 kN·m près : |M − 435,49| ≤ 0,005 kN·m ; lieu, combinaison et position identiques |
| Fichier de flexion composée de la tête de pieu, ligne ELU « M max » | M = 435,5 kN·m ; N = −N(Code_Aster) du même torseur | exacte | égalité à 0,1 kN·m (arrondi du fichier) |
| Chaque valeur de chaque torseur de la synthèse, relue par `resultats lire` (`<combinaison>@<position>` ou combinaison du lot 49, au même nœud et à la même extrémité) | égale | exacte | écart rapporté à la plus grande composante du torseur ≤ 10⁻⁹ |
| Combinaisons recalculées par superposition, aux lignes de leur maximum | égales aux combinaisons du lot 49 (`comb/<i>/max`) | exacte | ≤ 10⁻⁹ (même contrôle croisé) |
| Équilibre par état limite : Σ charges + Σ réactions + Σ ressorts, chaque combinaison, chaque position mobile | 0 | exacte | ≤ seuil du projet (`controls.threshold`, 10⁻⁶) rapporté à la plus grande composante de la charge |
| Grille des flèches de charges : Σ des flèches d'un cas | Σ des forces nodales du cas | exacte | ≤ 10⁻⁹ relatif |
| `.comm` de production, niveaux des paquets | inchangés (dalle E, quai D, estacade D) | exacte | identiques |
| Classeur relu | valeurs égales à leur source du paquet ; Arial 10 ; en-têtes gris D9D9D9 ; en-têtes figés ; valeur non significative grisée avec son motif | exacte | aucune exception |

Toute autre issue est un échec, rapporté tel quel.

## 4. Résultats

(Rédigés après les lectures ; les sections 1 à 3 ne sont pas modifiées.)
