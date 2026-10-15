# Lot 51 bis — Pontons aluminium : appuis articulés à axe, tablier rehaussé, palées types, équilibre des palées

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-51bis`, depuis `main` après
la fusion de `lot-51`. Consigne : `docs/lots/lot51bis_consigne.md`. Essais :
`docs/essais_lot51bis.md`, critère commité **avant** les exécutions (88c2ef1). Calcul linéaire
seulement ; aucune vérification EC9, béton armé ou appareil d'appui ; aucun ancrage de semelle ni
stabilisation artificielle ; aucun autre projet modifié.

## Décisions P44 à P51

Enregistrées dans la fiche depuis `donnees/sources/enregistrement_P44_P51_lot51bis.md` (texte
cité vérifié à l'identique dans la consigne), avec leurs variantes écartées (néoprène et profilé
support, têtes en rotule, semelle du lot 51, béton non déjaugé, tangentielle dans la flèche
caractéristique). Fiche : 60 entrées, aucun bloqueur ; choix de l'agent A8 (noms des groupes des
axes) et A9 (lecture des efforts des axes). Données : semelle 0,20 m, eau 10 kN/m³, niveau
+1,61 NGF (groupe `palee_lot51bis`, source P48, P49).

- **P44** : l'axe n'est pas maillé ; LIAISON_DDL sur la translation de son point P portée par
  chaque nœud, u_N + θ_N ∧ (P − N) : oreilles des deux travées liées (translations et DRX),
  oreille et nœud du chevêtre liés en Z (et en Y en YP), X libre ; en X = 14,02, Z (et Y en YP)
  du point P nuls. 25 relations.
- **P45** : X fixé aux seules rotules du quai ; réactions de la culée exportées.
- **P46** : 4 têtes de piles encastrées (LIAISON_SOLIDE vers l'axe de l'anneau).
- **P47, P48** : cotes ci-dessous ; semelle 2,60 × 2,60 × 0,20 m centrée en X = 7,01, sur
  RIGI_PARASOL 5 000 / 1 000 kN/m³ ; piles et entraxes du lot 51.
- **P49** : cas DEJ (FORCE_POUTRE sur chevêtres, longrines et piles, FORCE_COQUE sur la semelle)
  ; G × 1,2 sans DEJ, G × 0,9 avec DEJ, ELS et ELU accidentel avec et sans DEJ.
- **P50** : sous-face des poutres à +1,758, au-dessus de +1,61 : aucun cas de flottabilité.
- **P51** : flèche ELS caractéristique sans ACX ni ACZ ; ELS fréquent avec (ψ1 = 0,5).

**Semelle** : par rapport au lot 51 (2,52 × 2,90 × 0,25 m, 1,827 m³), la nouvelle (1,352 m³)
pèse **7,1 kN de moins une fois déjaugée** (0,475 m³ × 15 kN/m³).

## Cotes retenues (m NGF, grille de 1 mm)

Plan moyen du tablier +1,858 (lot 51 : 1,3575 recalé à +1,358, + 0,50) ; pannes +1,958 ;
sous-face des poutres +1,758 ; **axe d'appui +1,588** (0,170 m sous la sous-face) ; **dessus des
chevêtres +1,488**.

| | h = 0,40 | h = 0,80 |
|---|---|---|
| Axe de l'anneau | +1,288 | +1,088 |
| Sous-face de l'anneau = têtes de piles | +1,088 | +0,688 |
| Dessus de la semelle, palée courte (C) / profonde (P) | −0,612 / −3,212 | −0,612 / −3,212 |

## Variantes calculées

H40C (h 0,40, piles 1,70 m), H40P (0,40, 4,30), H80C (0,80, 1,30), H80P (0,80, 3,90), H80C-S3
(H80C, tube 200 × 200 × 10). Maillages `mesh check` 1 108/1 108 ; niveau B valide 968/968 ; les
cinq atteignent **FIN** (`completed_ok`, 0 alarme). 69 cas élémentaires, **430 914
combinaisons** par variante (ELU f. 121 556, ELU acc. 150 016, ELS c 121 556, ELS f 36 916,
ELS qp 870), livrées en règles.

## Harnais et contrôles

- Harnais D du tronc commun : **67 cas sur 69 réussis** par variante (résidu ≤ 8,1·10⁻¹¹) ;
  **DEJ** : la résultante vaut 10 kN/m³ × volume de béton modélisé, résidu 4,9·10⁻¹³ à
  3,8·10⁻¹². **TP et TM : ÉCHEC tel que le critère est écrit** : X étant libre partout sauf au
  quai, la dilatation est libre (14,8 mm en bout sous TP) et aucun effort n'apparaît (\|N\| ≤
  3·10⁻⁸ N) ; résidu et échelle Σ\|k·u\| sont deux bruits numériques. Critère non modifié ; un
  contrôle des cas sans effort est proposé à MM.
- Linéarité (H80C) 1,1·10⁻¹² ; axes (H80C) ≤ 8,9·10⁻⁸ hors TP et TM (même échec, même cause) ;
  décomposition contre énumération 4,7·10⁻¹⁵ (16 extrêmes) ; effectifs égaux à l'énumération.
- Niveau atteint : **C** pour les cinq variantes, **D** pour 67 cas sur 69.

## Comparaison (enveloppes B′ et ELU accidentel ; kN, kN·m, mm)

Flèches : travée 1, relatives à la corde, variables seules (P51). Fz des axes > 0 en compression ;
ΣRz du sol sur la semelle > 0 vers le haut. Détail : `comparaison_variantes_detail.csv`.

| Var. | PP My | Fl. ELS f bas / haut | Fl. ELS c bas / haut | Axes Fz min / max | Axes Fy | Gliss. X ELU / ELS c | Piles N min / max | Piles M tête / pied | Chev. My | ΣRz min ELU / ELS c | Lest | Culée RX / RY / RZ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H40C | −57,8 | −23,4 / 23,4 | −33,8 / 33,9 | −49,7 / 65,8 | −43,5 | 49,8 / 33,9 | −72,9 / 45,2 | 14,0 / 4,9 | 13,5 | −78,8 / −18,1 | 87,6 | 179,0 / −78,3 / 57,3 |
| H40P | −57,8 | −23,4 / 23,4 | −33,8 / 33,9 | −49,7 / 67,0 | −44,6 | 49,8 / 34,0 | −88,5 / 43,1 | 14,3 / 8,3 | 14,6 | −53,3 / 12,5 | 59,2 | 190,0 / −79,9 / 57,3 |
| H80C | −57,8 | −23,4 / 23,4 | −33,8 / 33,9 | −49,7 / 65,8 | −43,4 | 49,7 / 33,9 | −76,7 / 41,0 | 9,9 / 3,1 | 19,9 | −68,3 / −5,5 | 75,9 | 179,0 / −78,3 / 57,3 |
| H80P | −57,8 | −23,4 / 23,4 | −33,8 / 33,9 | −49,8 / 67,1 | −44,6 | 49,8 / 33,9 | −92,1 / 37,8 | 12,5 / 6,8 | 20,0 | −42,8 / 25,1 | 47,5 | 190,0 / −79,9 / 57,3 |
| H80C-S3 | −59,7 | −19,9 / 20,0 | −28,8 / 28,8 | −49,3 / 65,9 | −43,6 | 45,5 / 31,0 | −76,8 / 39,8 | 9,6 / 3,0 | 19,2 | −67,7 / −4,9 | 75,3 | 181,2 / −78,5 / 57,0 |

ΣRz min ELU et lest manquant gouvernés par l'ELU fondamental, G × 0,9 + DEJ + HU × 1,5 + TM ×
0,9 + AM1 + AC (tangentiel +Z) : la palée se soulève en bloc (tous les ressorts tendus, 168 pour
H80P). Le tablier ne dépend pas de la palée (flèches et moments identiques d'une hauteur à
l'autre) ; le glissement en X à l'ELU (49,8 mm) dépasse les ±45 mm du trou oblong, celui de
l'ELS caractéristique (≤ 34,0 mm) non.

- **H40C** : la palée la plus légère (3,84 m³) : le plus fort soulèvement, lest manquant 87,6 kN,
  palée soulevée aussi à l'ELS caractéristique (−18,1 kN) ; plus fort moment en tête de pile
  (14,0 kN·m).
- **H40P** : les piles de 4,30 m ajoutent 2,0 m³ : lest manquant 59,2 kN, ELS caractéristique
  en appui (+12,5 kN) ; compression des piles −88,5 kN, moment en pied 8,3 kN·m.
- **H80C** : l'anneau de 0,80 m porte le moment des chevêtres à 19,9 kN·m et réduit celui des
  têtes de piles (9,9) ; lest manquant 75,9 kN, ELS caractéristique juste soulevé (−5,5 kN).
- **H80P** : la plus lourde (6,73 m³) : lest manquant 47,5 kN, ELS caractéristique en appui
  (+25,1 kN) ; plus forte compression des piles (−92,1 kN).
- **H80C-S3** : flèches −15 % (ELS c −28,8 / +28,8 mm), moment des poutres +3 % ; équilibre de la
  palée inchangé (lest 75,3 kN).

## Livraison (`/media/sf_partage/echanges/lot51bis/pontons_alu_01/`, 136 Mo)

Par variante : `noeuds`, `elements`, `membres`, `efforts_elementaires`,
`deplacements_elementaires`, `reactions_elementaires`, `combinaisons`, `evenements`, `charges`,
`sections`, `piles`, **`appuis_axes`**, **`palee_equilibre`** (CSV) et `recombiner.py` ;
`comparaison_variantes.csv` et son détail ; `H80C/charges.med` et `H80C/charges_salome.py` (chaîne
des livrables du tronc commun, 69 cas, 69 vues par pvbatch puis par `exec()`) ;
`empreintes.sha256` (74 fichiers, `sha256sum -c` : 0 écart). Noms neufs.

## Points ouverts, signalés et non tranchés

1. Effort de houle sur le tablier rehaussé : forfait de 5 kPa conservé.
2. Liaison réelle pile–semelle et ferraillage des pieux existants : inconnus (ronds lisses de
   12 mm, armatures très peu denses en partie immergée).
3. Épaisseur réelle de la semelle (0,10 à 0,25 m) : le superviseur fait varier le lest.
4. Porte-à-faux d'extrémité de panne (0,85 à 1,05 m) : non modélisé.
5. Ajoutés par l'outil : angles de l'anneau comptés deux fois (0,127 / 0,255 m³ : 1,9 / 3,8 kN de
   poids déjaugé en trop, non retranchés du lest) ; glissement ELU de 49,8 mm contre ±45 mm du
   trou oblong ; contrôle d'équilibre des cas thermiques sans effort (TP, TM) à revoir.

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 32 exécutions attribuées, 1 échec (lot 51, DIAG-030) ; 0
depuis le dernier retour ; développement 29 (taux 3,5 %), vérification 3 ; « Tous les échecs sont
classés : clôture possible » ; revue inscrite (`--enregistrer --lot 51bis`). Interventions de
MM : 0 (une reprise après coupure de connexion, sans consigne nouvelle). Connaissances ayant évité
une erreur : 2 (PAT-005 : FORCE_COQUE en repère global ; DIAG-030 : DRX des oreilles liées, pas de
mécanisme de torsion), déclarées avant les exécutions.
