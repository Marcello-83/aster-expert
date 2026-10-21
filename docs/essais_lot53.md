# Essais du lot 53 — PONTONS-ALU-01 : déplacements sous accostage et amarrage (post-traitement B52)

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot53_consigne.md`. Code_Aster 17.4.0
(image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). Lot de post-traitement de la variante
B52 du lot 52 : ni modèle modifié, ni cas ajouté, ni événement ou combinaison modifiés. Calcul
linéaire ; niveau visé D au plus. Ni EC9, ni béton armé, ni appareil d'appui ; aucun ancrage modélisé.

## Objet

Donner les déplacements DX, DY, DZ (et les rotations des têtes de piles et des semelles) aux points de
sortie de la consigne sous les actions d'accostage (AC, ACA) et d'amarrage (AML, AM1, AM2, AMF),
caractéristiques et combinées (ELS caractéristique, ELS fréquent, ELU accidentel), et les verser dans
un MED de résultats.

**Relecture, pas de recalcul.** Les déplacements des 221 cas unitaires de B52 existent : tables
E25.16 de l'exécution du lot 52 (`data/processed/runs/20261019T080553-0565f41d/proc.0/fort.32`, DEPL
de tous les nœuds, six composantes), reprises dans `deplacements_elementaires.csv` du lot 52 et, par
le MED unitaire du rejeu du lot 52, dans `med_unitaires/resultats.med` (contrôlés égaux aux tables au
lot 52). Le lot relit les tables de cette exécution par le lecteur du lot 52 (`exports_lot52.load`) ;
aucune exécution Code_Aster n'est lancée.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | Empreintes SHA-256 du `.comm` et du maillage de l'exécution relue contre celles du lot 52 (`etat.json`, en-tête des CSV : `bd8663c6…`, `2cc66b5d…`) | identiques | exacte | égalité |
| 2 | Relecture : pour 5 cas unitaires tirés au sort parmi les 221 (graine 53), réactions (REAC_NODA, unité 33, après le repli CA-036), efforts (EFGE_ELNO, unité 31) et déplacements (DEPL, unité 32) relus contre `reactions_elementaires.csv`, `efforts_elementaires.csv` et `deplacements_elementaires.csv` du lot 52 | égalité | exacte (même table) | 10⁻⁶ × max \|v\| du cas et de la grandeur |
| 3 | DX de l'axe de C2 de P5 (YM et YP) sous TP contre la colonne `DX_TP` de `deplacements_axes.csv` du lot 52 | égalité | exacte (même calcul) | 10⁻⁹ en relatif |
| 4 | Linéarité : pour 3 événements tirés au sort (graine 53) parmi AC, ACA, AML, AM1, AM2 et AMF, déplacement de chaque point de `deplacements_evenements.csv` recalculé par un lecteur indépendant (module `csv` seul) comme Σ coefficient (`evenements.csv` du lot 52) × valeur du cas unitaire (`deplacements_unitaires.csv` de ce lot) | égalité | exacte (linéarité) | 10⁻⁹ × max \|u\| de l'événement |
| 5 | Enveloppes de `deplacements_combinaisons.csv` contre l'énumération explicite (`brute_force`, toutes les dispositions de Q et QD) sur 12 extrêmes tirés au sort (graine 53 ; état, point, direction, sens, variante) ; et chaque extrême contre la valeur de sa combinaison gouvernante réévaluée depuis ses coefficients | égalité | exacte | 10⁻⁹ en relatif (10⁻¹² m absolu sous 10⁻⁹ m) |
| 6 | Côté guidé YP : déplacement relatif tablier/chevêtre en Y ; tous les axes : déplacement relatif en Z (LIAISON_DDL de P44, P54, P65), sur tous les cas unitaires | nul | exacte (liaison) | 10⁻⁹ × max \|u\| du cas |
| 7 | MED : `resultats_deplacements_lot53.med` relu : les 18 champs de `resultats.med` du lot 52 identiques ; 10 champs DEPL nouveaux sur le maillage d'origine et 10 sur `PONTON_B52_ELNO` égaux à leurs tableaux ; le DEPL d'un nœud ELNO égal à celui de son nœud d'origine ; aux points de sortie, le champ d'une combinaison égal à la valeur de `deplacements_combinaisons.csv` (points nodaux) | égalité | exacte | écart de relecture nul ; 10⁻⁹ × max \|u\| aux points |
| 8 | PNG (vues A, B, C) : fichier non vide, 1 920 × 1 080 au moins ; vues A et C regardées à l'œil | conforme | — | — |

Rapporté sans seuil (consigne) : **ordre de grandeur** de DY de la tête de P5 sous un ACN unitaire
contre une estimation à la main, écart commenté en une phrase. Estimation écrite ici avant le calcul,
pour la force transversale F_P5 que P5 reprend réellement dans le modèle (somme des forces Y des
ressorts de sa semelle) :

DY_tête ≈ F_P5 × [ 1 / (4 × 12 E I / L³) + 1 / (k_t × A) + h × H / (k_n × I_x) ]

- piles : 4 piles Ø 0,50 m encastrées en tête (anneau, chevêtres) et en pied, E = 34 GPa,
  I = π d⁴ / 64, L = 0,69 − (−3,21) = 3,90 m ;
- semelle sur ressorts : A = 2,60 × 2,60 m², k_t = 1 MN/m³ (translation), k_n = 5 MN/m³,
  I_x = 2,60 × 2,60³ / 12 (balancement autour de X) ;
- bras de levier de la force (axe des appuis +1,175, plan moyen de la semelle −3,31) : h = 4,485 m ;
  hauteur de la tête au-dessus de la semelle : H = 4,00 m.

Valeurs attendues : 0,012 + 0,148 + 0,942 ≈ 1,10 mm par kN repris par P5 (le balancement de la
semelle domine). Le cas retenu est ACN_PT5_YM (zone au droit de P5) ; un écart de plus de 30 % est
commenté comme tel, sans changer de cas ni de formule.

Toute autre issue des critères 1 à 8 est un échec, rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Points de sortie** (99, lus sur les groupes du maillage, aucun numéro de nœud écrit à la main) :
  - axes d'appui (20 : 5 palées × C1, C2 × YM, YP) : `axe` = translation du point de l'axe porté par
    l'oreille 1 (tablier, u + θ ∧ (P − N), choix A11 du lot 51 ter) ; `chevetre` = nœud du chevêtre
    sous l'axe (groupe `AX_<axe>_K`) ; `relatif` = point de l'axe porté par l'oreille 1 − point de
    l'axe porté par le nœud du chevêtre (même définition que le glissement de `deplacements_axes.csv`) ;
  - poutres principales, mi-travée de T1 à T5, YM et YP : nœud du groupe `PP_Tk_<rive>` à mi-longueur
    du groupe ;
  - porte-à-faux, YM et YP : dernier nœud du groupe `PP_PF_<rive>` ;
  - têtes de piles (20) : nœud `TP_<palée>_<chevêtre>_<rive>_A` à +0,69 ;
  - centre des semelles (5) : aucun nœud au centre ; moyenne des deux nœuds de Y = 0 qui l'encadrent
    (à mi-distance exacte : X = 37,981 et 38,199 pour P5), soit l'interpolation linéaire ;
  - culée : `APP_CULEE_YM`, `APP_CULEE_YP`.
- **Unités** : mm pour les translations, mrad pour les rotations ; repère global (X le long du
  ponton, Y transversal, Z vers le haut).
- **Cas unitaires exportés** : ACN_*, ACX_*, ACZ_* (21 zones × 2 rives), AMY_*, AMX_* (10 taquets × 2
  rives), TP, TM. ACA et AMF n'ont pas de cas unitaires propres : ce sont les mêmes cas avec d'autres
  coefficients (`evenements.csv`).
- **Événements** : ceux du lot 52 (`evenements.csv`), valeurs caractéristiques ; familles AC (168),
  ACA (168), AM (AML 120, AM1 2, AM2 2), AMF (120).
- **Combinaisons** : règles du lot 52 (`combinaisons_lot51quater.branches`, avec les dispositions
  défavorables de Q et QD par modules), états ELS caractéristique, ELS fréquent, ELU accidentel.
  Quatre variantes par extrême : **total** ; **total hors T** ; **variables seules avec T** (G, DEJ
  exclus : les événements de l'action G mis à zéro) ; **variables seules sans T** (G, DEJ et T exclus).
  Exclure une action revient à la mettre à zéro dans toutes les branches (option ∅ de son
  emplacement ; dans une branche où elle est dominante, la combinaison se réduit aux accompagnements).
- **Champs MED** (noms courts, table de correspondance dans le compte rendu) : 6 événements (AC, ACA,
  AML, AMF les plus défavorables en \|DY\| sur les points de sortie absolus ; AM1_+X ; AM2_YP) et 4
  combinaisons (max \|DY\| ELS caractéristique, max \|DX\| ELS caractéristique hors T, max \|DY\| ELS
  fréquent, max \|DY\| ELU accidentel ; totaux), DEPL sur le maillage d'origine (`<nom>__DEPL`) et sur
  le support commun `PONTON_B52_ELNO` (`E_<nom>__DEPL`). Le fichier part d'une copie de `resultats.med`
  du lot 52 (champs conservés) et porte un nom neuf.
- **Vues** : PNG en plan (A, B) et en élévation (C) par matplotlib, depuis les coordonnées et les
  déplacements des nœuds, amplification écrite sur la vue.

## 3. Exécution (après le commit du critère)

Commit du critère : `dbf6cc7` (21/10/2026), avant toute exécution du post-traitement. Commande :
`PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/lot53.py tout` (étapes `exports`,
`verifier`, `med`, `vues`, `references`, `depot`), 73 s, dont 13,5 s de lecture des tables. Aucune
exécution Code_Aster. Listing versionné : `projets/pontons_alu_01/references/post_traitement_lot53/`
(`synthese_lot53.json`, `deplacements_synthese.csv`, `deplacements_evenements.csv`,
`verification_evenements.txt`).

### Correction des hypothèses (21/10/2026, après la première lecture des événements)

Le § 2 annonce « AM (AML 120, …), AMF (120) ». Les règles du lot 52 comptent **60** événements AML et
**60** AMF (10 taquets × 2 rives × 3 sens : ⊥, +X, −X), donc AM = 64. Le dénombrement n'entre dans aucun
critère ; le texte du § 2 n'est pas modifié.

## 4. Résultats

| # | Grandeur | Obtenu | Verdict |
| --- | --- | --- | --- |
| 1 | Empreintes | `.comm` de l'exécution et du lot 52 : `bd8663c6…` ; maillage `2cc66b5d…` ; identiques à `etat.json` et aux en-têtes des CSV | réussi |
| 2 | Relecture de 5 cas (ACX_T1D_YP, ACX_T5M_YP, ACZ_T3F_YP, ACZ_T4D_YP, TM) | réactions, efforts, DEPL : écart relatif 0,0 | réussi |
| 3 | DX de l'axe de C2 de P5 sous TP | 41,093778 mm (YM et YP), écart 0,0 avec `deplacements_axes.csv` | réussi |
| 4 | Linéarité, lecteur indépendant (AC_PT1_YM_+Z, AMF_TQ5_YP_PERP, AMF_TQ9_YP_PERP) | écart ≤ 3,6·10⁻¹⁵ mm (6, 28 et 47 extrêmes nommés) ; 694 lignes encadrées par événement | réussi |
| 5 | Enveloppes contre l'énumération explicite, 12 tirages | écart relatif ≤ 2,8·10⁻¹⁵ ; combinaisons gouvernantes réévaluées égales | réussi |
| 6 | Liaisons : DY relatif côté YP ; DZ relatif | ≤ 2,7·10⁻¹⁶ et 1,4·10⁻¹⁶ × max \|u\| | réussi |
| 7 | MED `resultats_deplacements_lot53.med` | MED 3.3 ; 18 champs du lot 52 conservés, écart 0 ; 20 champs nouveaux, écart de relecture 0 ; ELNO = nœud d'origine, écart 0 ; aux points nodaux, écart 0 | réussi |
| 8 | PNG | 5 PNG de 1 920 × 1 080, non vides ; vues A, B et C regardées | réussi |

**Ordre de grandeur (sans seuil).** ACN_PT5_YM (1 kN) : P5 reprend 695,8 N en Y (somme des ressorts de
sa semelle), le reste allant aux autres palées et à la culée par le tablier. Estimation :
695,8 N × 1,102 mm/kN = **0,767 mm** (balancement de la semelle 0,942, translation 0,148, piles
0,012 mm/kN) ; modèle, moyenne des 4 têtes : **0,770 mm**, rapport 1,004. L'écart de 0,4 % tient aux
termes négligés à la main (raccourcissement axial des piles, souplesse de l'anneau et des chevêtres,
répartition discrète des ressorts) ; la tête de P5 se déplace surtout par le balancement de la semelle
sur le sol (k_n = 5 MN/m³).

## 5. Verdict

Critères 1 à 8 : **réussis**. Niveau des résultats : D (celui du lot 52, harnais 221/221), inchangé :
le lot ne fait que relire et combiner linéairement des tables déjà contrôlées.

## 6. Lecture

- Faits : les plus grands déplacements sont au bout du porte-à-faux et à P5. DY : 79,1 mm (ELU
  accidentel, ACA_PF_YM_+Z), 56,0 mm (ELS caractéristique) ; DX : 70,9 mm à l'ELS caractéristique
  avec TP, 31,8 mm hors thermique à l'axe de P5.
- Fait : DX hors thermique de l'axe de C2 de P5 (31,8 mm) se décompose en Q 14,6, AM 9,4, G et DEJ
  4,0, AC 3,9 mm. Déduction, non isolée par un calcul : la part de G et de Q vient de la rotation
  des abouts des poutres sous charge verticale, l'axe (+1,175) étant sous l'axe neutre (+1,30), cumulée
  de la culée (seul point fixe en X) à P5.
- Fait : le jeu relatif en Y côté YM (libre) reste de 1,6 à 3,1 mm, quand le tablier se déplace de
  10 à 68 mm : le chevêtre suit le tablier par le côté YP guidé ; l'extrême est à l'ELS caractéristique
  (T × 1,0 en tête ou 0,6 en accompagnement) plus qu'à l'ELU accidentel (T × 0,5). Déduction : c'est la
  dilatation transversale du tablier qui le gouverne.

## 7. Limites

- Points sur les nœuds du modèle filaire ; centre de semelle interpolé (aucun nœud) ; semelles non
  dessinées sur les vues (coques).
- « Hors T » et « variables seules » : actions mises à zéro dans les règles du lot 52, pas de règles
  nouvelles.
- Aucune vérification EC9, béton armé ni appareil d'appui ; aucun ancrage ; aucune limite de
  déplacement n'est comparée (aucune n'est donnée par la consigne).
