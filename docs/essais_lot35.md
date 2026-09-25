# Lot 35 — Consolidation, contrôles de validité et synthèse des résultats

Ce document fixe les critères **avant** l'unique exécution du modèle complet du lot.
Le texte des critères n'est jamais modifié après coup ; seules les sections
« Résultats », « Verdict » et suivantes sont complétées (`docs/modele_rapport_essai.md`).

## Objet

1. Consolider ce que le lot 34 a établi : enregistrer ses quatre constats
   `code_aster` dans la fiche, retirer du générateur la table combinée
   `REACTIONS_<cas>`, remplacer la vérification d'orientation des normales
   (`VERI_NORM="NON"` sur la charge par couche) par une vérification explicite, ajouter
   à `mesh check` l'invariant d'alignement des couches.
2. Ajouter les contrôles de validité de la décision 5 (signe et butée des ressorts), par
   cas **élémentaire**, sans verdict de dimensionnement.
3. Produire la première synthèse de résultats destinée à l'ingénieur
   (`aster-expert report`).
4. Une exécution du modèle complet avec le générateur modifié : les contrôles de niveau D
   du lot 34 doivent rester tenus.

Code_Aster 17.4.0 (image du manifeste). Niveau visé : **C avec contrôles D**, jamais E.

## Étape 0

`aster-expert mcp-check` : 7 outils appelés sur un serveur neuf, identiques aux outils du
code (`mcp-check OK`). Les sept outils MCP sont visibles dans la session.

## Critères de réussite (écrits avant l'exécution du modèle complet)

Règle du dépôt : une grandeur que la théorie reproduit exactement l'est à 1e-6 près en
relatif ; toute autre issue est un échec, rapporté tel quel. Aucun seuil ci-dessous ne
sera relâché après lecture des résultats.

| Id | Grandeur | Attendu et origine | Nature | Seuil de réussite |
| --- | --- | --- | --- | --- |
| C1 | Exécution du modèle complet | `DIAGNOSTIC JOB : OK`, aucune alarme, aucune ligne `<F>`, `<E>`, `<S>` dans le `.mess` | binaire | tenu ou échec |
| C2a | Équilibre X, Y, Z des cas G, EAU_P, EAU_A, Q1 | 0 (charge appliquée intégrée indépendamment + réactions des composantes bloquées + ressorts, `scripts/analyze_lot34_equilibre.py`) | exacte | écart relatif <= 1e-6 sur chaque composante |
| C2b | Symétrie des déplacements, tous les nœuds, six cas | image miroir identique (x -> -x) | exacte | écart relatif <= 1e-6 |
| C2c | Pesanteur (cas G, Z) | poids maillage + poutre + pression = réactions bloquées | exacte | écart relatif <= 1e-6 |
| C3 | Normales des mailles de chaque couche de `ECRAN_POUSSEE` (maillage relu après `MODI_MAILLAGE`) | tournées vers la terre : radiales sortantes pour un tube, +Y pour une palplanche (fiche, point 5) | binaire par maille | 0 maille à contresens ou hors seuil (cosinus >= 0,9), 0 normale non horizontale, 0 maille sans famille, sur chacune des quatre couches ; un maillage altéré (une maille inversée) est rejeté |
| C4 | Invariant de couche de `mesh check` (maillage complet vérifié) | aucune maille à cheval sur une interface, chaque couche bordée par ses cotes | binaire | tous les invariants tenus (599 avec l'invariant) ; le maillage altéré des tests est rejeté |
| C5 | Lecture croisée tirants / ancrages | Σ N cos θ = réaction d'ancrage selon Y (tous les cas) ; Σ N sin θ = réaction selon Z (hors pesanteur : sous pesanteur l'ancrage porte une part du poids des tirants) | exacte (statique du nœud d'ancrage) | écart relatif <= 1e-6 |
| C6 | Lecture croisée ressorts | force par bande de la synthèse = −Σ k·DY du script d'équilibre du lot 34 | exacte (même table, deux codes) | écart relatif <= 1e-9 |
| C7 | Lecture croisée tête | max abs de DY de la synthèse = `POST_RELEVE_T/EXTREMA` (`ORDRE_GRANDEUR_<cas>`, cas G et Q3, six chiffres imprimés) | exacte, limitée par l'impression | écart relatif <= 1e-4 |
| C8 | Complétude de la synthèse | toutes les tables attendues (6 cas x tables de tête, de profils, d'efforts des tubes, des palplanches, de la poutre et des tirants, réactions, ressorts) présentes ; aucune valeur non finie ; chaque grandeur avec son unité, son champ, sa composante et son repère | binaire | `aster-expert report` sans erreur ; aucune table absente |
| C9 | Taux de butée extrême | recalculé par les classes de ressorts du générateur (autre voie que les aires par bande de la synthèse) | exacte | écart relatif <= 1e-9 |
| C10 | Palplanches | aucune contrainte lue (`SIEF_*`, `SIGM_*`) ; efforts lus en `EFGE_NOEU` (décision 2) | binaire | 0 lecture de contrainte dans le `.comm` ; table des palplanches en `EFGE_NOEU` |

Le repère de chaque grandeur de la synthèse est établi par la documentation (U4.42.01,
U2.01.05), non supposé ; les sources sont dans la synthèse. Les tubes reçoivent
`VECTEUR = (0, 0, 1)` : le repère local d'une coque n'a aucun effet sur la raideur d'un
matériau isotrope, donc les déplacements sont **inchangés** -- écart critère : **0** sur
tous les déplacements du quai réduit (essai `essais/sans_vecteur_tubes`, avant le modèle
complet).

Les contrôles de l'étape 2 (signe, butée) **n'ont pas de critère de réussite** : ce sont des
constats sur le domaine de validité du modèle linéaire (décision 5, domaine de validité,
items 1 et 2), rapportés sans verdict de dimensionnement (CLAUDE.md, principe 6).
Une exécution **ne valide pas** l'ouvrage : aucune combinaison n'est décidée dans la fiche.

## Précisions consignées avant l'exécution du modèle complet

Le texte des critères ci-dessus est inchangé. Ce qui suit dit comment ils sont appliqués,
écrit avant l'exécution :

1. **Développement sur le quai réduit** (maillage vérifié, trois tubes) : le nombre
   d'exécutions du quai réduit n'est pas plafonné par le lot ; celui du modèle complet
   l'est à **une**.
2. **Table combinée** : `REACTIONS_<cas>` (`POST_RELEVE_T/RESULTANTE` sur quatre groupes en
   une extraction) est retirée du générateur ; le `.comm` exécuté n'en contient plus.
3. **Efforts généralisés** : lus par `CREA_TABLE` (valeurs stockées, repère de l'élément) ;
   `POST_RELEVE_T` s'arrête sur les champs de structure (`<POSTRELE_70>` aggravée en erreur
   par `DEBUT/ERREUR`, `<POSTRELE_38>` avec `REPERE="LOCAL"`), `CALC_CHAMP/EFGE_NOEU` sur les
   tubes s'arrête sur les repères locaux des facettes (`<UTILITAI_4>`, 92°), exécutions
   réelles du quai réduit. Les tubes, la poutre et les tirants sont donc lus en
   `EFGE_ELNO` (valeur par élément et par nœud, sans moyenne) ; les palplanches en
   `EFGE_NOEU` uniquement, sur un résultat restreint aux `PALPS`.
4. **Le MED de résultats n'est pas relu** : le Python du projet n'a aucun module MED ;
   chaque grandeur de la synthèse vient d'une table imprimée, traçable à une commande du
   `.comm`. C'est une limite déclarée, pas un choix caché.
5. **Figures** : `matplotlib` n'est pas dans l'environnement du projet ; la synthèse
   porte les profils en tableaux seuls (consigne du lot).
6. **Cas A et Q3** : contrôles C2 informatifs (comme aux lots 33 et 34), sans verdict.
7. **Ce qui a été observé avant la rédaction de ce document.** L'invariant de couche (C4)
   et l'égalité des déplacements avec et sans `VECTEUR` sur les tubes ont été observés sur
   le quai réduit pendant le développement, avant l'écriture des critères ; le maillage
   complet a aussi passé l'invariant (599/599) à ce moment. Ils figurent ici comme
   critères du lot, écrits avant l'exécution du **modèle complet**, seule exécution que le
   lot borne.

## Modèle et exécution

- Fiche : `data/examples/hypotheses_combiwall_reference_arbitree.json` (51 entrées,
  régénérée par `scripts/build_combiwall_reference.py`) ; données :
  `data/examples/combiwall_model_data.yaml` (114 valeurs, dont le profil de butée) ;
  maillage : le MED vérifié du lot 27 (`combiwall_mesh.med`, SHA-256 `1bd724bd…`,
  40 114 nœuds), inchangé.
- `.comm` : `data/examples/lot28_quai/quai_combiwall.comm` (3 619 lignes, généré par
  `aster-expert generate`, SHA-256 `3d5fb5c0…`) ; niveau B : `validate_comm` (MCP),
  `valid = true`, **253 commandes confrontées au catalogue 17.4.0 sur 253, aucune non
  vérifiée** (les `DETRUIRE(NOM=…)` d'un concept à la fois sont confrontés ; la forme à
  tuple ne l'était pas).
- Exécution unique : `aster-expert run data/examples/lot28_quai/quai_combiwall.comm`,
  répertoire `data/processed/runs/20260925T075049-b1de2c32/`, image
  `sha256:d8d19ea9…`, HEAD `f6da541` (arbre modifié : le lot n'est pas encore commité),
  **436,5 s**.
- Quai réduit (développement) : `data/examples/lot35_synthese/` (`.comm`, `essais/`,
  `rapports/`).

## Résultats

### Étape 1 — constats et consolidation

1. **Quatre constats `code_aster` enregistrés** (`combiwall_inputs/lot35_essais.json`,
   `_lot35_facts` de `scripts/build_combiwall_reference.py`, preuves archivées par
   `scripts/build_lot35_constats.py` dans `data/examples/lot35_constats/` : le `.comm`
   exécuté octet pour octet et l'extrait de listing, chaque valeur de source étant
   imprimée dans son listing) :

   | Point | Constat | Sources d'exécution (niveau D) | Écart mesuré |
   | --- | --- | --- | --- |
   | 5 | `FORCE_COQUE/PRES` (fonction) évaluée **aux nœuds** : une marche déborde d'une demi-maille ; **remplace** « doublement à 1 mm sûr » (conservé dans les notes) | 3 | avant −1,185e-3 de la poussée G (règle nodale : 1,7e-14) ; par couche 2,1e-12 |
   | 4 | `CREA_POI1` : une maille ponctuelle par nœud ; nœud commun = somme des raideurs | 2 | nœud 65, z = −18 m : −0,304 (raideur de la marne seule) avant, 1e-13 après |
   | 12 | poutre continue à plusieurs `LIAISON_SOLIDE` : `<F> <CALCULEL2_92>` ; forces nodales tributaires | 1 | résultante assemblée = somme des forces nodales (6 chiffres) ; l'échec (niveau B) est archivé en extrait |
   | 3 | `REAC_NODA` aux nœuds liés : composantes non bloquées non nulles, nulles en somme globale | 1 | −1,5e-10 |

   Historique : l'entrée du point 5 remplacée reste dans les `notes` du nouveau constat
   (option retenue, notes, sujet) et ses sources documentaires sont conservées ; la fiche
   passe de 48 à 51 entrées et de 55 à 62 sources d'exécution. Le sujet exigé par le
   générateur (`_REQUIRED_FACT_TOPICS`) est mis à jour. La fiche de référence n'a plus de
   bloqueur. **Aucune décision pratique n'est prise ni complétée** : ce sont des constats
   `code_aster`, que la session a qualité pour enregistrer.
2. **Table combinée `REACTIONS_<cas>` retirée** du générateur (test : aucune occurrence
   dans le `.comm`) ; `scripts/analyze_lot34_equilibre.py` ne la lit plus.
3. **Invariant de couche** de `mesh check` (`LayerBandsInvariant`, groupe
   `ECRAN_POUSSEE`, interfaces −26 ; −18 ; −9 ; −2 ; +4 tirées de la donnée) : maillage
   complet **599/599** (593 + 6), quai réduit **239/239**. Chaque couche est bordée
   exactement (−26/−18 : 5 120 mailles ; −18/−9 : 7 200 ; −9/−2 : 5 600 ; −2/+4, bornée par
   la tête à +2,6 : 3 800), aucune maille à cheval. Tests : maillage aligné accepté,
   **maillage altéré rejeté** (maille à cheval, maille hors des couches, rangée manquante).
4. **Normales** (C3) : le `.comm` écrit le maillage tel que Code_Aster le tient après
   `MODI_MAILLAGE/ORIE_NORM_COQUE` (unité 81, `IMPR_RESU/MAILLAGE`) ; relu par
   `medcoupling` dans le conteneur, chaque maille de chaque couche est contrôlée
   (`aster_expert.meshing.normals`) : **21 720 mailles, 0 à contresens, 0 normale non
   horizontale, 0 sans famille, cosinus minimal 1** (les facettes sont radiales exactes).
   **Altération** sur le maillage réel (une maille inversée) : rejetée (cosinus −1,
   `--altere`, code retour 1). `VERI_NORM="NON"` reste sur les occurrences par couche ; il
   est désormais remplacé par cette vérification explicite.

### Étape 2 — contrôles de validité de la décision 5 (cas élémentaires)

Sans critère de réussite, sans verdict (`controles.md`). Modèle complet, 10 433 nœuds à
ressort ; compression si DY < 0.

| Cas | Nœuds en traction | Cotes | Réaction de traction max (kN) | Taux de butée max | Cote | Tube | Nœuds > 100 % |
| --- | ---: | --- | ---: | ---: | ---: | --- | ---: |
| G | 1 605 | −26,0 à −15,0 | 0,894 | 951 % | −12,00 | TUBE_04 | 2 413 |
| EAU_P | 1 781 | −26,0 à −15,0 | 0,355 | 369 % | −12,00 | TUBE_06 | 1 122 |
| EAU_A | 1 781 | −26,0 à −15,0 | 0,826 | 858 % | −12,00 | TUBE_06 | 2 029 |
| Q1 | 1 765 | −26,0 à −15,0 | 0,319 | 336 % | −12,00 | TUBE_04 | 978 |
| Q3 | 7 828 | −26,0 à −13,5 | 0,056 | 9,2 % | −12,00 | TUBE_07 | 0 |
| A | 3 662 | −26,0 à −12,0 | 0,738 | 1,4 % | −19,75 | TUBE_05 | 0 |

Constat sur les limites du modèle linéaire : sous G, EAU_P, EAU_A et Q1 des ressorts
dépassent la butée de Rankine fictive du cas de test, surtout au sommet de la bande
(cote −12,00, où σ'p = 47,1 kPa ne vaut que la part cohésive) ; la pression de réaction
k·|DY|/A y vaut k_h·|DY| (448 kPa sous G). Le taux est d'abord fonction de k_h·|DY| / σ'p(z)
et croît vers le sommet de la bande. **Ce n'est pas une vérification de l'ouvrage** : les
cas sont élémentaires, aucune combinaison n'est décidée, la pression initiale au repos
n'est pas modélisée (décision 5, item 3).

### Étape 3 — synthèse (`aster-expert report`)

Fichiers : `data/examples/lot35_synthese/modele_complet/` (`synthese.md` : 720 lignes,
`controles.md`, `synthese.json`). Structure : ce que le document est et n'est pas ;
provenance (SHA-256 du listing et du `.comm`) ; **table des repères, champs et unités** ;
par cas élémentaire : déplacement en tête, effort axial de chacun des neuf tirants, extrêmes
des efforts généralisés des tubes, des palplanches et de la poutre (valeur, cote, porteur,
maille, nœud), réactions (composantes bloquées en gras), somme des ressorts par couche,
lecture croisée tirants/ancrages ; contrôles de la décision 5 ; profils de DY de
`TUBE_05` et `TUBE_01` (moyenne annulaire et étendue, tous les cas dans un tableau) ;
contrôles de niveau D. Figures : **aucune** (`matplotlib` absent de l'environnement du
projet, tableaux seuls, comme la consigne le prévoit ; le code de tracé est testé avec un
module de remplacement).

Repères, établis par la documentation : déplacements en global (point 9) ; tirants,
`EFGE_ELNO/N`, repère local de la barre (> 0 en traction) ; tubes, repère utilisateur de la
facette avec `VECTEUR = (0, 0, 1)` : `x_l` **verticale**, donc `NXX`/`MXX` effort normal et
moment de flexion **verticaux** (U4.42.01, opérande ANGL_REP / VECTEUR) ; palplanches,
**`EFGE_NOEU` uniquement** (décision 2), `x_l` verticale (`VECTEUR = L`) ; poutre, repère
par défaut (`ANGL_VRIL = 0`), `x_l` le long de l'élément, `y_l` selon Y, `z_l` selon Z ;
`MFY` moment de flexion vertical. L'orientation des éléments de poutre (du X le plus bas au
plus haut, donc `x_l = +X`) est **déduite** de l'ordre des lignes de la table, non de la
documentation ; elle est signalée comme telle.

### Étape 4 — exécution et contrôles

| Id | Résultat | Verdict |
| --- | --- | --- |
| C1 | `DIAGNOSTIC JOB : OK`, 436,5 s, « aucune alarme », 0 ligne `<F>`/`<E>`/`<S>` (`.mess` de 332 Mo) | RÉUSSI |
| C2a | équilibre : X ≤ 4,5e-12, Y ≤ 8,8e-11, Z ≤ 1,1e-12 (G, EAU_P, EAU_A, Q1) ; Q3 et A informatifs ≤ 2,3e-10 | RÉUSSI |
| C2b | symétrie : 20 057 paires, 0 sans image, pire écart 5,7e-11 (Q1) | RÉUSSI |
| C2c | pesanteur (G, Z) : poids maillage 1 386 344,209 N (= analytique à 6,5e-13), bilan −2,4e-5 N, écart 1,07e-12 | RÉUSSI |
| C3 | 21 720 mailles, 0 à contresens ; altération rejetée | RÉUSSI |
| C4 | 599/599 ; altérations rejetées (tests) | RÉUSSI |
| C5 | Σ N cos θ = ancrages selon Y : 2,2e-13 (six cas) ; selon Z hors pesanteur : 2,1e-13 | RÉUSSI |
| C6 | force par bande : 4,3e-15 (douze valeurs) | RÉUSSI |
| C7 | tête (G et Q3) : 2,5e-6 (limité par l'impression à six chiffres) | RÉUSSI |
| C8 | aucune table absente, 6 cas, aucune valeur non finie ; unités, champs, composantes, repères dans la synthèse | RÉUSSI |
| C9 | taux extrême recalculé par les classes : 1,9e-16 | RÉUSSI |
| C10 | aucune lecture de contrainte ; palplanches en `EFGE_NOEU` | RÉUSSI |

Le modèle est **inchangé** : les déplacements des 40 114 nœuds des six cas sont identiques
**bit à bit** à ceux du modèle complet du lot 34
(`modele_complet/deplacements_contre_lot34.json`, écart maximal 0). Sur le quai réduit,
`VECTEUR` sur les tubes donne des déplacements identiques bit à bit
(`rapports/vecteur_tubes_comparaison.json`).

## Verdict

Tous les critères C1 à C10 sont **réussis**. **Niveau atteint : C (exécuté jusqu'à `FIN`,
253/253 commandes confrontées au catalogue au niveau B) avec contrôles D** (équilibre,
symétrie, pesanteur et lectures croisées) ; **aucun niveau E**.

## Lecture

Faits :

- Sous pesanteur, l'écart vertical de la lecture croisée des tirants (Σ N sin θ =
  −1 167,972 kN contre −1 128,152 kN de réaction d'ancrage) vaut 39,820 kN : c'est **la
  moitié du poids des neuf tirants** (9 × ρ·A·L·g / 2 = 39,820 kN, ρ = 7 850 kg/m³,
  A = 0,00442 m², L = 25,997 m) : la masse d'un tirant est répartie sur ses deux nœuds
  d'extrémité, et l'ancrage n'en reprend que la moitié. Vérifié numériquement ; hors
  pesanteur, l'écart est 1e-13.
- Le maximum de DY en tête est −15,665 mm (G, TUBE_05).
- Les efforts extrêmes des tubes se situent à la cote +2,5 m sur les tubes de bord
  (`TUBE_09`, `TUBE_01`), au voisinage de l'anneau de tête lié à la poutre par
  `LIAISON_SOLIDE` : ce sont des valeurs **locales à la jonction rigide**, à lire avec
  prudence ; ce sont des constats, non des vérifications.

Déductions (marquées) : les efforts de liaison lus aux nœuds de `SYM_G`/`SYM_D` sur les
composantes non bloquées sont les multiplicateurs de `LIAISON_SOLIDE` (constat du point 3).

Recommandations :

- Sous G, 2 413 des 8 828 ressorts comprimés (27 %) dépassent la butée fictive : le
  comportement linéaire des ressorts n'y est plus représentatif. Que faire de ce
  constat (plafonnement, autre modèle de sol) est une décision de MM, non prise ici.
- Le doublement à Z ± 1 mm n'est plus tenu pour sûr dans la fiche ; aucune entrée
  pratique n'y renvoie (vérifié dans la fiche régénérée) : aucune décision à réviser.

## Coût

Quai réduit : **7 exécutions**, 471,3 s cumulées (dont **3 échecs expliqués** de 26,9, 51,1 et
53,0 s : `<UTILITAI_4>`, `<POSTRELE_70>`, `<POSTRELE_38>`, extraits archivés dans
`data/examples/lot35_synthese/essais/`). Modèle complet : **1 exécution**, 436,5 s.
Total 907,8 s (`rapports/executions.json`). Les analyses hors Code_Aster (équilibre,
normales, lectures croisées, synthèse) sont du Python pur, quelques minutes au total.

## Limites

- **Le MED de résultats n'est pas relu** (le Python du projet n'a aucun module MED) : la
  synthèse vient des tables du listing. Un champ non imprimé (par exemple `EFGE_ELGA`) n'y
  est pas.
- **Pas de figures** : `matplotlib` n'est pas dans l'environnement du projet.
- **Efforts des tubes, de la poutre et des tirants par élément et par nœud**, sans moyenne
  aux nœuds : `CALC_CHAMP/EFGE_NOEU` s'arrête sur ces groupes (`<UTILITAI_4>`, jusqu'à 92°
  d'écart entre repères locaux) ; les extrêmes sont ceux des valeurs par élément. Seules
  les palplanches sont lues en `EFGE_NOEU` (décision 2).
- **Signe des moments de poutre** : établi pour `x_l = +X` (déduit de l'ordre des lignes) ;
  la documentation ne donne le repère par défaut que pour l'orientation sans angle.
- **Porteur d'un nœud de serrure** (sur un tube et sur une palplanche) : attribué au tube.
- **Extrêmes locaux** au voisinage des liaisons rigides (anneaux de tête) : non interprétés.
- **Butée** : profil de Rankine fictif du cas de test (pas de calcul K-Réa), sans pression
  initiale au repos ; taux calculé nœud par nœud, une combinaison de cas n'est pas faite.
- **Cas non testés** : maillages non alignés sur les interfaces de couche (l'invariant
  les rejette à la vérification du maillage, le générateur ne le sait pas) ; le raffinement
  du maillage (aucun critère d'erreur de discrétisation dans ce lot).
- Le mécanisme de `CALC_CHAMP/EFGE_NOEU` sur les repères locaux et celui de
  `POST_RELEVE_T/RESULTANTE` sur plusieurs groupes ne sont pas établis par la
  documentation ; ils sont contournés, non expliqués.
