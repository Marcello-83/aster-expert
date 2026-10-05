# Lot 47 bis — Estacade : relecture des écarts, critères v2, variantes ciblées

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-47bis` créée depuis `main` après fusion de `lot-47`).

---

**Tout en français. Profil `vm`. Branche `lot-47bis`, depuis `main` après
fusion de `lot-47`.** Termes interdits : ceux du lot 47 (fichier local). Consigne
copiée dans `docs/lots/lot47bis_consigne.md`.

## 1. Diagnostic du superviseur (sur les exports du lot 47)

Il s'appuie sur `tetes_de_pieux.csv` et `chevetres.csv`. C'est une relecture,
pas un verdict. À toi de le vérifier et de le réfuter si les données le
contredisent.

**(a) C3 et C5 : erreur de lieu de lecture, pas de modèle.**

- La source publie le moment maximal **en tête de pieu** : le §20.3.2 indique
  « moments maximaux obtenus en tête de pieux », et la figure 80 porte la valeur
  en haut des files 1 et 7, sous ELU(+) 111.
- Au lot 47, C3 a été lu à +0,70 m et C5 à −2,50 m, en ELU−.
- Au nœud de tête (+1,30), la combinaison 111 ELU+ donne pour F7_YP **435,5
  kN·m**, à comparer à 449 kN·m (C3, −3,0 %) et 463 kN·m (C5, −5,9 %).
- L'écart venait de l'élément +1,30 → +0,70 : sous un effort tranchant
  d'environ 260 kN, ces 0,6 m font varier le moment d'environ 150 kN·m.

**(b) C7 et C8 : ton explication (B) était juste.**

- La dalle DKT, rigide au cisaillement, et le chevêtre POU_D_T partagent leurs
  nœuds. La bande de dalle de 1,20 m au-dessus du chevêtre reprend environ 70 %
  de l'effort tranchant transversal près des pieux.
- À Y = ±1,90, en 112 ELU+ : VZ du chevêtre ≈ 190 kN, et ∫QY de la dalle sur
  1,20 m ≈ 476 kN, soit un total d'environ **666 kN pour 653 kN dans la
  source (+2 %)**.
- Sur appui : MFY du chevêtre ≈ −125 à −133 kN·m, plus −42 kN·m pour la dalle,
  soit environ −170 kN·m pour −177 kN·m dans la source.
- La source semble publier l'effort de la section en T, ou n'avoir pas ce
  partage. La grandeur comparable est donc **le total chevêtre + bande de dalle**.

**(c) C6 reste hors tolérance** : +8,6 % pour la barre seule, environ +15 % pour
le total. La piste à tester est l'incohérence I2 de la source. Le modèle Robot a
vraisemblablement tourné avec un chevêtre de **0,80 m** :

- le poids sismique est calculé avec 0,80 m ;
- le §20.5.1 indique « h = 0,80 (augmenté à 0,90) ».

**(d) Dalle (C9, C11, C12, C13)** : les lectures sur le nœud singulier de tête de
pieu ne veulent rien dire (lot 47, § 3 (A)). Il faut une règle de lecture écrite.

**(e) C12 « rive » : erreur de données du superviseur.** Dans la source, le cas
TR de la combinaison 100 n'est pas seulement la charge de 5 kPa. Il comprend
aussi **un essieu de 160 kN sur le trottoir**, valeur αQ2·Q2k = 0,8 × 200
(§15.3.3 de la source ; figure 100, où deux charges ponctuelles apparaissent sur
le trottoir). B4 l'avait omis.

## 2. Décisions de MM, validées par le lancement du lot

- **E17, règles de lecture v2.** Elles sont écrites et commitées **avant** toute
  nouvelle exécution, et déclarées « écrites après la première exécution ». Les
  verdicts v1 sont conservés tels quels dans l'historique.
  1. **Pieux.**
     - C3 : maximum sur la zone qui va de la tête (+1,30) à −0,80, élément de
       tête compris.
     - C5 : maximum sur tout le pieu.
     - Enveloppe ELU+ et ELU− ; la famille qui gouverne est indiquée.
  2. **Chevêtres** (C6, C7, C8) : on compare le **total** barre + bande de dalle
     |X − X_file| ≤ 0,60, c'est-à-dire s·MFY − ∫MYY dX et VZ + ∫QY dX. La barre
     seule est rapportée pour information.
  3. **Dalle** (C9, C12, C13) : maximum hors des disques de rayon 0,60 m centrés
     sur les têtes de pieux.
  4. **C11** : moyenne de NXX sur une section transversale. C'est la grandeur
     que publie la source.
- **E18, cas TR de la combinaison 100.** Sources :
  - le §15.3.3 de la source : « un essieu : αQ2·Q2k = 0,8 × 200 = 160 kN
    (essieu du système LM1, voie n° 2) », parmi les charges des trottoirs ;
  - le §20.6.5 : « un essieu est appliqué sur le trottoir du tablier » ;
  - la figure 100 : deux charges concentrées, en kN, **alignées selon X sur le
    même trottoir**, distantes d'environ 2 m, la première juste avant le
    chevêtre 4.

  Les figures 68 et 69 concernent le tandem TS de LM1 sur la voie et non ce cas.

  Le cas TR comprend :
  - 5 kPa sur les deux trottoirs ;
  - 2 roues de 80 kN, **alignées selon X**, à 2,00 m d'entraxe longitudinal,
    centrées sur le trottoir (Y = +2,25) ;
  - une empreinte de 0,40 × 0,40 m, et non une charge ponctuelle : une force
    nodale sur une plaque est singulière. La source a utilisé des charges
    ponctuelles, et sa valeur de 568 kN/m dépend donc de son maillage.
    L'écart sur C12 « rive » s'interprète en conséquence ;
  - un déplacement par pas de 0,50 m selon X, avec enveloppe ; la position
    gouvernante est rapportée et comparée à celle de la figure 100 ;
  - la charge de 10 kN sur 0,10 × 0,10 m est négligée (effet local de
    poinçonnement).

  L'orientation longitudinale est **déduite de la figure 100**, pas écrite
  dans la source. C'est cohérent avec un trottoir de 1,50 m, trop étroit pour
  un essieu de 2,00 m posé en travers. Ce cas ne s'applique qu'à la combinaison
  100. Dans LM1, la charge des trottoirs reste à 5 kPa (cas source « LM1 UDL
  TR »).
- **E19, variante de sensibilité déclarée** : chevêtre de 0,80 m (HZ = 0,80, le
  reste inchangé), pour tester (c). La référence reste à 0,90 m (E2).

## 3. Travaux

1. **Critères v2** (E17), commités avant exécution. Ajoute une ligne de lecture
   exacte (lieu, composante, famille) pour chaque point.
2. **Relecture sans calcul** du résultat de production du lot 47 selon E17. Les
   lectures de pieu et de chevêtre se font aussi en ELS f et ELS c, en plus de
   l'ELU.
3. **Exécutions** :
   - le cas TR selon E18, avec la combinaison 100 recalculée (C12 « rive ») ;
   - la variante E19, en un seul run, pour lire C6, C7 et C8.
4. **Vérifier ou réfuter les diagnostics (a), (b), (c) et (e)**, chacun avec ses
   chiffres.
5. **Harnais D, cas autoéquilibrés** (TE±). Donne à CTL-005 et CTL-013 une
   échelle définie pour un cas dont la charge est nulle, par exemple la somme
   des |forces de ressort|, ou αΔT·E·A d'une section de référence. Fais-en une
   nouvelle version de contrôle, réévalue le niveau D, et garde le verdict v1
   dans l'historique.
6. **Capitalisation** :
   - un constat sur la dalle DKT et la poutre POU_D_T coplanaires qui
     partagent leurs nœuds : partage de l'effort tranchant, et grandeur à
     comparer (le total de la section en T). Il est établi par les données du
     lot 47 ;
   - un diagnostic ou un patron « lecture au nœud singulier d'un appui
     ponctuel de plaque » ;
   - une règle dans le skill : **tout point de comparaison externe déclare,
     avant exécution, son lieu, sa composante et sa famille de combinaison**.
     Au lot 47, c'est le superviseur qui avait omis le lieu de lecture.
7. Paquet de résultats, notes, `rex`, et `docs/etat.yaml`.

## Compte rendu attendu — EN FRANÇAIS

1. Tableau de C1 à C13, avec les verdicts v1 et v2 côte à côte et la règle de
   lecture appliquée.
2. Diagnostics (a), (b), (c) et (e) : confirmés ou réfutés, chiffres à l'appui.
3. Variante E19 : effet sur C6, C7 et C8.
4. Harnais D : nouvelle échelle et niveau obtenu.
5. Connaissances créées, `rex`, contrôles, interventions du lot.

## Interdits

- Aucun critère v1 modifié ou effacé.
- Aucune modification de la référence (E1 à E16) en dehors des variantes
  déclarées.
- Aucun terme interdit dans le dépôt.
- Aucun identifiant Code_Aster énoncé de mémoire.
