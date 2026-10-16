# Essais du lot 51 quater — PONTONS-ALU-01 : houle « tablier noyé », impact quasi statique, vues 3D, MED complets

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot51quater_consigne.md`. Code_Aster 17.4.0
(image `simvia/code_aster:17.4.0`, digest `sha256:d8d19ea9…`). **Aucune réexécution pour les
résultats** : les 221 cas unitaires des quatre exécutions du lot 51 ter (tables E25.16 des unités 31,
32 et 33) sont recombinés avec les événements de P60 et P61. Code_Aster n'est relancé que pour obtenir
les champs unitaires en MED de B12 (B10 : déjà écrits par la chaîne du tronc commun au lot 51 ter), avec
le `.comm` du lot 51 ter inchangé. Niveau des résultats : celui du lot 51 ter (**D**), jamais plus.
Aucune vérification EC9, béton armé ou appareil d'appui ; aucun ancrage modélisé.

## Objet

Recombiner les cas unitaires du lot 51 ter avec la houle « tablier noyé » (P60, P56 révisée : seuls
les coefficients changent) et l'impact quasi statique local (P61, six événements HU_IMP_M0 à
HU_IMP_M5, alternatifs à HU), évaluer la sensibilité HU_S5 (forfait AVP de 5 kPa, sans décision) pour
l'ancrage et l'équilibre des palées, refaire les exports du lot 51 ter, livrer les efforts en `.npz`,
des vues 3D en volume (B10, B12) et, pour B10 et B12, la structure, les charges et des résultats
combinés en MED avec un script ParaVis.

## 1. Critère de réussite (écrit avant l'exécution)

| # | Grandeur | Attendu | Nature | Seuil |
| --- | --- | --- | --- | --- |
| 1 | Rejeu B12 pour les MED unitaires : `.comm` produit par la chaîne du tronc commun (`PONTONS_VARIANTE=B12`, maillage B12 du lot 51 ter, `mesh check` 3 526/3 526) contre `resultats/lot51ter/B12/pontons_alu_01.comm` | identique (sha256 `8f95ea87…`) | exacte | égalité d'octets ; sinon le rejeu est abandonné |
| 2 | Rejeu B12 : fin d'exécution ; post-traitement des livrables (tables E20.12 du post-traitement contre la production) ; déplacements DEPL et efforts EFGE_ELNO unitaires du MED contre les tables E25.16 de l'exécution du lot 51 ter, tous les cas, tous les nœuds et toutes les extrémités | `completed_ok` ; tables identiques ; égalité | exacte (même `.comm`, même image) | écart ≤ 10⁻⁹ × max \|v\| du cas |
| 3 | Résultante de HU (P60) sur la longueur totale, chaque variante : Σ coefficient × résultante déclarée des cas unitaires contre (4,92 × 0,40 + c_p × 0,20 + 0,90 × 1,327) × L × 1 kPa, c_p = 1,91 (variantes 10) ou 2,11 (variantes 12), L = longueur chargée du modèle (40,091 m pour B : jeux de 1 mm) ; de même HD (1,01 × 1,895 × L) | égalité | exacte | 10⁻⁶ en relatif |
| 4 | Résultante de chaque HU_IMP_Mk : 5,9 × 1,927 × longueur chargée du module × 1 kPa (largeurs des cas unitaires : 0,40 + 0,20 + 1,327 m) | égalité | exacte | 10⁻⁶ en relatif |
| 5 | Les résultantes des critères 3 et 4 contre les réactions verticales de l'exécution (axes de la culée + ressorts des cinq semelles), combinées avec les mêmes coefficients | somme nulle | exacte (équilibre discret) | 10⁻⁶ en relatif |
| 6 | Identité avec le lot 51 ter, combinaisons sans houle : enveloppes (max et min, cinq états limites) avec les options de houle annulées, sous les règles du lot 51 ter (P56) et sous celles du lot (P60, P61), aux lieux du contrôle 8 du lot 51 ter (MFY des poutres principales, N des piles, Fz des axes, ΣRz de chaque palée, RX de la culée), quatre variantes | valeurs identiques | exacte | écart nul |
| 7 | Identité avec le lot 51 ter, coefficients P56 passés par les règles du lot : chaque grandeur de `comparaison_variantes.csv` du lot 51 ter (valeur, combinaison et lieu qui gouvernent), quatre variantes | identique | exacte | écart nul |
| 8 | Enveloppes par décomposition contre (a) le `recombiner.py` livré, combinaison par combinaison, et (b) l'énumération explicite des 63 dispositions de Q et de QD (`brute_force`) : B10, **36 extrêmes tirés au sort** (graine 51 : lieu parmi MFY des poutres principales, N des piles, Fz des axes, ΣRz de chaque palée, RX de la culée, MFZ des barres ; état limite parmi ELU fondamental, ELU accidentel, ELS caractéristique ; max ou min) | égalité | exacte | écart ≤ 10⁻⁹ en relatif |
| 9 | Effectifs en règles : formule contre `recombiner.py` relu dans les CSV et contre l'énumération des règles sans doublon ; exclusions : aucune branche n'admet Q avec la houle (B′), la houle avec AC ou ACA (P57), deux événements de houle, un impact hors de l'ELU fondamental et de l'ELS caractéristique (P61) | égalité ; aucune violation | exacte | égalité stricte ; zéro |
| 10 | `efforts_elementaires.npz` (float32), chaque variante : taille ; lecture par un script indépendant (`scripts/lire_npz_lot51quater.py`, numpy et `csv` seuls) d'efforts tirés au sort (graine 51, 20 tirages dont le premier est l'effort demandé par la consigne) contre `efforts_elementaires.csv` de B10 | < 60 Mo ; égalité à l'arrondi float32 près | exacte | \|Δ\| ≤ 2⁻²⁴ × \|v\| (+ 10⁻³⁰) |
| 11 | MED (B10, B12) relus par medcoupling : nombre de nœuds, de mailles par niveau et de groupes de `structure.med` égal au maillage de l'exécution ; `charges.med` : un champ par cas unitaire et par événement P60/P61, résultante de chaque champ d'événement = Σ coefficient × résultante des champs unitaires ; `resultats.med` : DEPL et EFGE_ELNO des quatre combinaisons de la vue 7 contre la même combinaison recalculée depuis les tables E25.16 ; enveloppes ELU de N, MFY, MFZ par extrémité contre l'enveloppe de l'outil | égalité | exacte | écart ≤ 10⁻⁹ × max \|v\| |
| 12 | Chaque PNG : fichier non vide, 1 920 × 1 080 pixels au moins ; deux vues au moins regardées à l'œil (désignées dans le compte rendu) | conforme | — | — |

Les temps de recombinaison par variante sont rapportés sans seuil. Toute autre issue est un échec,
rapporté tel quel : pas de seuil relâché après coup.

## 2. Hypothèses de l'outil (écrites avant l'exécution)

- **Règles** : celles du lot 51 ter (`combinaisons_lot51ter`), avec P60 et P61. HU_IMP_Mk (action
  « HI ») est une option de l'emplacement de la houle, à côté de HU et HD, à l'ELU fondamental (× 1,5
  en dominante, × 1,5 × 0,77 en accompagnement) et à l'ELS caractéristique (× 1,0 ; × 0,77) ; jamais à
  l'ELU accidentel, à l'ELS fréquent ni à l'ELS quasi permanent ; jamais avec Q (B′), AC ou ACA (P57).
  À l'ELU accidentel, HU ou HD × 0,77 en dominante comme au lot 51 ter, avec les coefficients P60.
- **HU_PANNES des variantes 12** : coefficient 2,11 kPa (P60) sur le cas unitaire du lot 51 ter, dont
  la largeur reste 0,05 m par panne (P56) alors que les pannes 60 × 60 ont 0,06 m de sous-face : écart
  signalé, non corrigé (aucun nouveau cas unitaire).
- **p_imp = 5,9 kPa**, valeur décidée ; vérification : 5,84 kPa avec w = 1,1 m/s, 5,94 kPa avec
  w = 2π × 2,03 / 11,5 = 1,109 m/s.
- **HU_S5** : HU remplacé par 5,0 × (HU_TUBES + HU_PANNES + HU_PLATELAGE) sur toute la longueur, HD
  (P60) conservé, aucun impact, mêmes règles ; évalué pour `ancrage.csv`, `palee_equilibre.csv` et les
  colonnes d'ancrage `_S5` de `comparaison_variantes.csv` (la consigne les demande), nulle part
  ailleurs.
- **Événement de houle gouvernant** : celui que nomme la combinaison gouvernante (HU, HD, HU_IMP_Mk,
  ou « aucun ») ; pour la flèche de l'ELS caractéristique, travée au plus petit L/f.
- **Quatre combinaisons de la vue 7 et de `resultats.med`** : combinaisons gouvernantes de PP My
  (extrême en valeur absolue), de la flèche de l'ELS fréquent (travée au plus petit L/f) et de ΣRX de
  la culée à l'ELU fondamental, telles que les écrit la comparaison ; impact : ELS caractéristique
  G + DEJ + HU_IMP_M0 (× 1,0, impact en dominante, sans accompagnement). Les déformées montrent la
  combinaison entière (G compris) ; enveloppes ELU de `resultats.med` : ELU fondamental et ELU
  accidentel, max et min de chaque composante séparément (valeurs non concomitantes).
- **Champs de `resultats.med` et des événements de `charges.med`** : écrits en Python avec
  medcoupling (dans l'image Docker de `cave`) à partir des champs unitaires que Code_Aster a écrits en
  MED (chaîne du tronc commun), combinés par leurs coefficients ; ni nouvelle commande Code_Aster ni
  modification du `.comm`.
- **Vues 3D** : pvbatch (ParaView 5.11 de Salomé-Méca, hors écran, `xvfb-run`), géométrie construite
  dans le script à partir des exports (nœuds, éléments, repères locaux, sections), projection
  parallèle et barre d'échelle. Axes d'appui : cylindre Ø 0,04 m parallèle à Y et platine
  0,30 × 0,30 de +1,09 à +1,125 (représentation : le diamètre de l'axe n'est pas donné). Culée non
  modélisée : ses deux appuis sont représentés. Coupe transversale (vue 6) : dessin plan
  (matplotlib), cotes du modèle (P53, P54).

## 3. Exécution (après le commit du critère)
