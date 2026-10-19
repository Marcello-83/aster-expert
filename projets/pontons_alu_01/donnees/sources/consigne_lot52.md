# Lot 52 — Pontons aluminium : géométrie PRO (B12, treillis constructible, appui v4) et recalcul complet

**Tout en français. Profil `vm`. Branche `lot-52`, depuis `main` après
fusion de `lot-51quater`.** Consigne copiée dans `docs/lots/lot52_consigne.md`.

## Objet

Acter les arbitrages de MM du 16/10/2026 sur la géométrie du tablier et relancer
le calcul complet. La géométrie change, il faut donc relancer Code_Aster et
recombiner. Le modèle obtenu est celui du PRO : il servira aux revérifications
EC9, béton armé et appuis faites par le superviseur.

Tout le lot 51 quater est repris (modèle, cas, événements, combinaisons, houle
P60/P61, exports), **sauf** ce qui est modifié ci-dessous.

Calcul linéaire uniquement. Ni EC9, ni béton armé, ni vérification d'appui dans
le lot. Règles d'économie habituelles :

- un `.comm` paramétré ;
- un script de maillage paramétré ;
- les variantes dans `variantes_lot52.yaml` ;
- les barres générées par boucle.

## Décisions à enregistrer (MM, 16/10/2026)

**P62 — La houle reste dans le critère de flèche.** HU, HD et HU_IMP entrent
dans l'ELS caractéristique. La proposition d'exclusion du superviseur est
refusée. Les critères P37/P51 sont inchangés.

**P63 — Sections retenues.**

- Poutres principales : 200 × 200 × 12, comme la variante 12 du lot 51 quater.
- Pannes allégées : **50 × 50 × 5**. Sensibilité en 50 × 50 × 4.
- Montants et diagonales : **120 × 120 × 6**, 6082-T6.
  - Justification : la zone adoucie sur la poutre principale au droit d'un
    montant mesure 120 + 2 × 30 = 180 mm, ce qui reste sous la largeur de
    200 mm de la poutre.
  - 30 mm est le bhaz de l'EN 1999-1-1, 6.1.6.3, pour une épaisseur moyenne de
    9 mm.

**P64 — Treillis horizontal constructible.**

1. **Montants et diagonales sous les pannes.** Le dessus des montants et des
   diagonales est au niveau de la sous-face des pannes, soit +1,35 pour des
   pannes de 50.
   - Axe des montants et des diagonales 120 × 120 à **+1,29**.
   - Montants soudés sur le flanc des poutres principales (axe +1,30). Dans le
     modèle, ils sont reliés aux nœuds des poutres par une liaison rigide de
     0,01 m.
   - Les pannes posent sur les montants et sur les diagonales. Elles y sont
     reliées par une liaison rigide de 1,375 − 1,29 = 0,085 m.
   - Aucune barre ne pénètre dans une autre.
2. **Diagonales soudées sur les montants, plus sur les poutres principales.**
   - Le nœud diagonale–montant est sur l'axe du montant, à **e = 0,25 m de l'axe
     de la poutre principale**, soit |Y| = 0,68.
   - Le dessin en N du treillis est conservé : chaque diagonale relie le nœud
     à Y = +0,68 d'un montant au nœud à Y = −0,68 du montant suivant (même sens
     de diagonale qu'aujourd'hui).
   - Le tronçon de montant entre la poutre et ce nœud travaille en flexion :
     c'est voulu, il faut l'exporter.
   - Paramètre `e_diag` dans le yaml.
3. Positions en X des montants inchangées. Le découpage des pannes aux
   croisements suit la nouvelle géométrie.

**P65 — Appui articulé : principe P44/P54 conservé** (schéma
`schema_appui_articule_v4`).

- Une oreille par travée, sous le tube, portée par un étrier en T en inox
  duplex fixé sous la poutre par boulons aveugles : aucune soudure sur la
  poutre.
- Les deux oreilles sont côte à côte sur un axe Ø 24 commun, placé à
  **+1,175** au lieu de +1,16.
- Dans le modèle, le point de l'axe passe à Z = +1,175. Les liaisons sont
  inchangées :
  - oreilles liées en translation et en DRX ;
  - Z bloqué ;
  - Y bloqué côté YP ;
  - X libre.

**P66 — Défenses.** Défenses Delta continues en caoutchouc, frottement μ = 0,7,
inchangé. Le frontal PEHD est abandonné.

## Variantes

| Code | Géométrie (piles, Lpf) | Poutres principales | Pannes | Montants et diagonales |
|---|---|---|---|---|
| B52 | panne B | 200 × 200 × 12 | 50 × 50 × 5 | 120 × 120 × 6, P64 |
| A52 | panne A | 200 × 200 × 12 | 50 × 50 × 5 | 120 × 120 × 6, P64 |
| B52P4 | panne B | 200 × 200 × 12 | 50 × 50 × 4 | 120 × 120 × 6, P64 |

Les cas unitaires de houle gardent leurs largeurs. HU_PANNES vaut 0,05 m par
panne, ce qui est maintenant cohérent.

Coefficients P60 pour des pannes de 50, sous-face à +1,35 :

- HU = 4,92 × HU_TUBES + 1,91 × HU_PANNES + 0,90 × HU_PLATELAGE ;
- HD = 1,01 × HD_TABLIER ;
- HU_IMP_Mk = 5,9 × (HU_TUBES_Mk + HU_PANNES_Mk + HU_PLATELAGE_Mk), comme au
  lot 51 quater.

## Exécution

- Code_Aster jusqu'à FIN pour les 3 variantes.
- Harnais D sur les 221 cas.
- Recombinaison par décomposition (méthode du lot 51 quater), avec le temps de
  calcul.
- Énumération de contrôle sur B52 (36 extrêmes tirés au sort).

## Exports

Mêmes fichiers qu'au lot 51 quater, pour chaque variante :

- `efforts_elementaires.npz`, toutes les barres, en float32 ;
- `comparaison_variantes.csv` et son détail ;
- `ancrage.csv` et `palee_equilibre.csv`, avec la sensibilité HU_S5 ;
- `culee.csv`, `chaine_x.csv`, `deplacements_axes.csv`, `appuis_axes.csv`,
  `piles.csv` ;
- `membres.csv`, `elements.csv`, `sections.csv`, `noeuds.csv`, `evenements.csv`,
  `combinaisons.csv`, `charges.csv`, `recombiner.py`.

Les CSV de 100 à 200 Mo ne sont pas déposés.

Ajouts :

- **`geometrie_noeuds.csv`** : pour chaque croisement panne/montant,
  panne/diagonale et montant/poutre :
  - cotes du dessus et du dessous de chaque barre ;
  - jeu ou recouvrement en mm ;
  - longueur de la zone de soudure projetée sur la poutre principale (largeur
    du montant + 2 × 30 mm).

  Contrôle attendu : aucun recouvrement, zone de soudure ≤ 200 mm.
- Dans `comparaison_variantes.csv`, par famille (poutres, pannes, montants,
  diagonales, tronçon de montant entre poutre et nœud de diagonale) : N min,
  N max, My, Mz et V extrêmes.

## Vues et MED

Pour B52 :

- **Vues PNG** 1 à 7 du lot 51 quater, refaites, avec les côtés nommés « vue
  depuis la culée » et « vue depuis le porte-à-faux », plus :
  - **vue 8** : vue en plan du treillis horizontal de T1 et PT1, avec repérage
    des montants, des diagonales, des nœuds à e = 0,25 m et des pannes en
    transparence ;
  - **vue 9** : zoom 3D sur un nœud poutre / montant / diagonale / panne, où
    l'on doit voir les pannes posées sur les montants sans pénétration ;
  - **vue 6** (coupe) corrigée : l'axe d'appui est transversal (barre selon Y)
    et l'étrier en T est dessiné selon le schéma v4.
- **MED** : `structure.med`, `charges.med`, `resultats.med`, et le script
  ParaVis du lot 51 quater adapté.
  - Corriger le défaut signalé : dans `resultats.med`, porter les efforts et
    les déplacements sur le même support, pour pouvoir colorer la déformée par
    composante d'effort.
  - Si ce n'est pas possible, le dire et proposer une solution.

## Contrôles

- `geometrie_noeuds.csv` : zéro recouvrement, zone de soudure maximale ≤ 200 mm.
- Résultantes de HU, HD et HU_IMP_Mk exactes.
- Somme des modules égale au cas total.
- Sous AM1 : ΣRX des palées ≈ 0.
- Sous TP : DX de l'axe de P5 égal à α·ΔT·38,85.
- Comparaison avec B12 du lot 51 quater sur les grandeurs de
  `comparaison_variantes.csv`, avec les écarts commentés en une phrase chacun.
  On attend :
  - des flèches un peu plus grandes ;
  - une flexion des montants nouvelle ;
  - un ancrage quasi inchangé.
- Pour chaque PNG : fichier non vide et dimensions attendues. Vérifier à l'œil
  au moins les vues 4, 8 et 9.

## Dépôt

`/media/sf_partage/echanges/lot52/pontons_alu_01/` :

- `<variante>/` : exports ;
- `comparaison_variantes.csv` ;
- `vues/` ;
- `B52/MED/` ;
- `scripts/` ;
- `empreintes.sha256`.

Les noms de fichiers sont neufs.

## Compte rendu attendu — EN FRANÇAIS, court

- Décisions P62 à P66.
- Géométrie des nœuds : tableau de synthèse de `geometrie_noeuds.csv`.
- Harnais et contrôles.
- Tableau de comparaison avec B12 du lot 51 quater, avec une phrase par écart
  notable.
- Ancrage par palée.
- Temps de recombinaison.
- PNG vérifiés à l'œil.
- MED.
- `rex` et interventions.

## Interdits

- Aucune vérification EC9, béton armé ou appareil d'appui dans le lot.
- Aucun ancrage modélisé.
- Aucune modification des autres projets.
- Aucun bloc recopié à la main par travée ou par palée.
