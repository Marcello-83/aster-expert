# Lot 53 — Pontons aluminium : déplacements sous accostage et amarrage (post-traitement B52)

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-53`, depuis `main` après la
fusion de `lot-52`. Consigne : `docs/lots/lot53_consigne.md`. Essais : `docs/essais_lot53.md`, critère
commité avant tout calcul (`dbf6cc7`) et non modifié depuis. Niveau des résultats : **D** (celui du
lot 52). Ni modèle, ni cas, ni événement, ni combinaison modifiés ; ni EC9, ni béton armé, ni appareil
d'appui ; aucun ancrage modélisé ; aucun autre projet modifié.

## Relecture, pas de recalcul

Les déplacements des 221 cas unitaires de B52 sont dans les tables de l'exécution du lot 52
(`20261019T080553-0565f41d`, unité 32 : DEPL de tous les nœuds, six composantes). Ces tables sont
toujours présentes, et le `.comm` comme le maillage gardent leurs empreintes (`bd8663c6…`,
`2cc66b5d…`). Je les ai relues par le lecteur du lot 52 ; aucune exécution Code_Aster n'a été lancée.
Contrôle : sur 5 cas tirés au sort, les réactions, les efforts et les DEPL relus sont égaux aux CSV du
lot 52, à écart nul.

## `deplacements_synthese.csv` (mm, totaux)

| Palée | DY tête ELS c | DY tête ELU acc | DY tablier ELS c | DY tablier ELU acc | Jeu Y YM ELS c | Jeu Y YM ELU acc | DX axe hors T ELS c | DX axe hors T ELU acc | DZ axe ELS c (min / max) | DZ axe ELU acc (min / max) |
|---|---|---|---|---|---|---|---|---|---|---|
| P1 | 7,6 | 8,7 | 9,6 | −11,1 | −2,5 | −1,6 | 5,7 | 4,6 | −7,6 / 1,4 | −7,5 / 2,7 |
| P2 | 15,8 | 17,4 | 19,0 | 20,9 | −2,6 | −1,7 | 13,7 | 10,4 | −9,5 / 3,0 | −9,1 / 4,5 |
| P3 | 22,8 | 24,7 | 26,6 | 28,8 | −2,6 | −1,7 | 20,2 | 14,8 | −11,0 / 4,1 | −10,7 / 5,6 |
| P4 | 28,7 | 32,5 | 32,6 | 36,8 | −2,6 | −1,7 | 26,5 | 20,0 | −12,0 / 3,9 | −12,0 / 5,7 |
| P5 | 43,7 | 60,1 | 48,8 | −67,6 | −3,1 | −2,2 | 31,8 | 25,1 | −14,5 / 6,8 | −17,1 / 11,3 |

Lecture du tableau :
- Chaque valeur est l'extrême en valeur absolue, rendu avec son signe.
- **Tête** : têtes des 4 piles, à +0,69.
- **Tablier** : point de l'axe d'appui porté par l'oreille 1, sur les 4 axes de la palée.
- **Jeu Y** : tablier − chevêtre au point de l'axe, côté YM, où Y est libre. Côté YP, guidé, le jeu
  est nul par la liaison : ≤ 1,3·10⁻¹⁴ mm, colonne de contrôle du CSV.
- **Hors T** : TP et TM mis à zéro.

## Les 3 plus grands DY et DX (totaux, mm)

| | Valeur | Point | État | Combinaison |
|---|---|---|---|---|
| DY | 79,1 | PF_bout_YM | ELU acc | G_DEJ_100 + ACA_PF_YM_+Z + AML_TQ10_YP_PERP × 0,77 + TM × 0,5 + QD[M4+M5] × 0,2 |
| DY | −78,4 | PF_bout_YP | ELU acc | G + ACA_PF_YP_+Z + AML_TQ10_YM_PERP × 0,77 + TP × 0,5 + QD[M0..M3] × 0,2 |
| DY | −67,6 | P5C2_YM_axe | ELU acc | G + ACA_PF_YP_+Z + AML_TQ10_YM_PERP × 0,77 + TP × 0,5 + Q[M0..M5] × 0,2 |
| DX | 70,9 | PF_bout_YP | ELS c | G_DEJ_100 + TP + AM1_+X × 0,77 + AC_PF_YP_+X + Q[M0..M5] × 0,77 |
| DX | 70,5 | PF_bout_YM | ELS c | idem, AC_PF_YM_+X |
| DX | 69,6 | P5C2_YP_axe | ELS c | G_DEJ_100 + TP + AM1_+X × 0,77 + AC_PF_YP_+X + Q[M0..M4] × 0,77 |

Sous les seuls événements caractéristiques :
- DY maximal : 61,9 mm au bout du porte-à-faux, sous ACA_PF_YM_+Z ;
- DX maximal : −14,7 mm aux chevêtres de P5, sous ACA_PF_YP_+Z.

DX hors thermique de l'axe de P5 vaut 31,8 mm. Il se décompose en Q 14,6, AM 9,4, G et DEJ 4,0, AC
3,9 mm (fait). Explication probable, non isolée par un calcul (déduction) : l'axe (+1,175) est sous
l'axe neutre des poutres (+1,30). La rotation des abouts sous charge verticale déplace donc l'axe en
X, et cet effet se cumule de la culée, seul point fixe en X, jusqu'à P5.

## Contrôles

Tous réussis (critère commité `dbf6cc7`) :
- **Empreintes** du `.comm` et du maillage : identiques.
- **Relecture de 5 cas** : écart 0.
- **DX de l'axe de P5 sous TP** : 41,0938 mm, égal à `deplacements_axes.csv`.
- **Linéarité** (lecteur indépendant, `csv` seul, 3 événements) : écart ≤ 3,6·10⁻¹⁵ mm.
- **Énumération explicite**, 12 extrêmes : écart ≤ 2,8·10⁻¹⁵.
- **Liaisons** (Y relatif côté YP, Z relatif) : ≤ 2,7·10⁻¹⁶.
- **MED relu** : écart 0.

**Ordre de grandeur, DY de la tête de P5 sous ACN_PT5_YM (1 kN).** P5 en reprend 696 N ; le
tablier répartit le reste. À la main, avec cette force : 0,767 mm (4 piles encastrées 0,012 mm/kN,
semelle en translation 0,148, en balancement 0,942). Modèle : 0,770 mm, soit un écart de 0,4 %, qui
vient des termes négligés à la main (raccourcissement des piles, souplesse de l'anneau). Le
balancement de la semelle domine.

## Champs MED (`B52/MED/resultats_deplacements_lot53.med`)

Le fichier est une copie de `resultats.med` du lot 52, dont les 18 champs sont conservés, plus 20
champs nouveaux. Chaque clé de la table donne deux champs :
- `<clé>__DEPL` sur le maillage `PONTON_B52` ;
- `E_<clé>__DEPL` sur le support commun `PONTON_B52_ELNO`.

| Clé | Contenu | Événement ou combinaison retenue |
|---|---|---|
| EV_AC_DY | AC le plus défavorable en \|DY\| | AC_PF_YM_+Z (32,3 mm, PF_bout_YM) |
| EV_ACA_DY | ACA le plus défavorable en \|DY\| | ACA_PF_YM_+Z (61,9 mm) |
| EV_AML_DY | AML gouvernant en \|DY\| | AML_TQ10_YP_PERP (21,1 mm) |
| EV_AMF_DY | AMF gouvernant en \|DY\| | AMF_TQ10_YP_PERP (37,7 mm) |
| EV_AM1_PX | AM1_+X | AM1_+X |
| EV_AM2_YP | AM2_YP | AM2_YP |
| CO_ELSC_DY | max \|DY\| ELS caractéristique | G_DEJ_100 + AML_TQ10_YP_PERP + TM × 0,6 + AC_PF_YM_+Z + QD[M4+M5] × 0,77 (56,0 mm) |
| CO_ELSC_DX_HT | max \|DX\| ELS caractéristique hors thermique | G_DEJ_100 + Q[M0..M4] + AM1_+X × 0,77 + AC_PF_YP_+X (31,8 mm, P5C2_YP_axe) |
| CO_ELSF_DY | max \|DY\| ELS fréquent | G + AC_PF_YP_+Z × 0,5 + TP × 0,5 + AML_TQ10_YM_PERP × 0,2 + QD[M0..M3] × 0,2 (−21,6 mm) |
| CO_ELUA_DY | max \|DY\| ELU accidentel | G_DEJ_100 + ACA_PF_YM_+Z + AML_TQ10_YP_PERP × 0,77 + TM × 0,5 + QD[M4+M5] × 0,2 (79,1 mm) |

Script ParaVis : `scripts/afficher_pontons_salome_53.py`. Il affiche la déformée amplifiée, colorée
par DX, DY ou DZ (en mm) sur le support commun, ou par famille. Il a été exécuté par pvbatch, qui a
produit deux PNG.

## PNG vérifiés à l'œil

Les 5 PNG font 1 920 × 1 080 et ne sont pas vides. J'ai regardé A, B, C et le PNG ParaVis coloré par
DY.
- **Vue A** (plan, ELS caractéristique, × 10) : le tablier fléchit en plan à partir de P3. Valeurs
  aux palées : tablier / tête 6,4 / 5,1 mm à P3, 48,8 / 43,7 mm à P5 ; bout du porte-à-faux 56,0 mm.
- **Vue B** (ELU accidentel, × 10) : même allure ; 67,2 / 60,1 mm à P5, bout du porte-à-faux
  79,1 mm.
- **Vue C** (élévation, ELS caractéristique hors T, × 25) : DX croît de la culée (0) à P5 (31,8 mm) ;
  les têtes de piles restent entre −7,1 et +0,2 mm, puisque X est libre aux axes.
- **Correction faite** : l'étiquette du bout du porte-à-faux recouvrait celle de P5 sur la première
  version. Elle a été déplacée sous le dessin, puis les vues ont été régénérées.

## Dépôt

`/media/sf_partage/echanges/lot53/pontons_alu_01/` contient 13 fichiers (14,1 Mo) et
`empreintes.sha256`, vérifiées par `sha256sum -c` :
- `B52/` : 4 CSV et `synthese_lot53.json` ;
- `B52/MED/` ;
- `vues/` : 5 PNG ;
- `scripts/` : script ParaVis et lecteur indépendant.

## `rex` et interventions

```
Retour d'expérience du projet pontons_alu_01
Exécutions attribuées au projet : 49 ; échecs : 2 ; depuis le dernier retour d'expérience (2026-10-19) : 0.
Développement : 43 exécution(s), 2 échec(s), taux 4,7 % ; vérification : 6 exécution(s), 0 échec(s) (hors taux).
Classement : nouveau 1, écarté 1.
Diagnostic retrouvé automatiquement par la base (seul et égal au classement) : 0/1 échecs rattachés.
Répartition par cause : DIAG-030 1, écarté 1.
Constats de la fiche à verser dans la base : 0.
Candidats patrons dans le code du projet : 0 (similarité ≥ 0,40 ; 23 fonction(s) sous le seuil, non listées).
Connaissances créées par le projet : 3 ; promues : 0.
Consultations journalisées (tous projets) : search_connaissances 74, search_constats 3.
Tous les échecs sont classés : clôture possible.
```

- **Interventions de MM** : aucune.
- **Connaissance ayant évité une erreur** : aucune à attribuer à ce lot, qui n'écrit aucune commande
  et ne lance aucune exécution. CA-036 reste appliqué par le lecteur du lot 52.

## Limites

- **Dénombrement des hypothèses** : le § 2 des essais annonçait 120 événements AML et 120 AMF ; il y
  en a 60 de chaque. L'erreur est corrigée dans une section datée.
- **Centre des semelles** : il est interpolé, faute de nœud au centre. Les semelles ne sont pas
  dessinées sur les vues.
- **Hors T et variables seules** : ce sont des actions mises à zéro dans les règles du lot 52, pas
  des règles nouvelles.
- **Pas de comparaison à des limites** : aucune limite de déplacement n'est donnée, aucune n'est
  vérifiée.
- Niveau D au mieux.
