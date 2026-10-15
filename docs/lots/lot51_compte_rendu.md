# Lot 51 — Pontons aluminium : palée complète, appuis néoprène, actions maritimes révisées, comparaison de solutions

Profil `vm` (`env-check` OK, `mcp-check` OK : 10 outils). Branche `lot-51`, depuis `main` après la
fusion de `lot-50quinquies`. Consigne : `docs/lots/lot51_consigne.md`. Essais :
`docs/essais_lot51.md`, critère commité **avant** les exécutions (e169107). Calcul linéaire
seulement ; aucune vérification EC9, béton armé ou appareil d'appui ; aucune action maritime
calculée par l'outil ; aucun autre projet modifié. Niveau atteint : **D** pour les 11 variantes
calculées.

## Décisions P29 à P43

Enregistrées dans la fiche depuis `donnees/sources/enregistrement_P29_P43_lot51.md` (texte cité
vérifié à l'identique dans la consigne), avec leurs variantes écartées ; valeurs de l'annexe A et
de P36, P38, P43 versées au fichier de données, dans l'unité de la source. Fiche : 50 entrées
(32 + 15 décisions + 3 choix de l'agent A5 à A7 : noms des groupes, nœuds distincts aux liaisons
et ressorts de 1 mm, lecture des efforts des néoprènes), aucun bloqueur.

- **P29 à P34** : navire enveloppe ; AC 23,5 kN ⊥ + 16,45 kN tangentiel (±X ou ±Z) sur 1 m,
  γ = 1,5, ψ0 = 1,0, ψ1 = 0,5, ψ2 = 0 ; ACA 45 + 31,5 kN à l'ELU accidentel ; AM local 27,5 kN,
  AM1 (8 taquets, 23,8 ⊥ et ±13,7 ∥), AM2 (4 taquets d'un côté, 10,6 ⊥), γ = 1,5 ; AMF 49 kN.
  **ψ de l'amarrage conservés du projet (lot 50, D5) : ψ0 = 0,77, ψ1 = 0,77, ψ2 = 0,2.**
- **P35 à P37** : travée de 6,25 m, largeur chargée 2,00 m, rotules du quai inchangées, jeu B′
  seul plus l'ELU accidentel ; tube 200 × 200 × 8 (balayage 180 × 8 et 200 × 10) ; critères de
  flèche laissés au superviseur.
- **P38, P39** : néoprène Kx = Ky = 2,25 kN/mm, Kz = 476,6 kN/mm (recalculés par le générateur),
  Kθ = 0, traction admise ; profilé support 150 × 150 × 7 encastré sur le chevêtre.
- **P40 à P43** : palée complète (4 piles Ø 0,50, anneau BA 0,40 × 0,40, petite travée),
  H = 1,32 et 4,0 m, éclissages articulés ou continus.

## Modèle

Un script de maillage (`maillage/maillage_palee.py`, seul `H_PILES` change d'une variante à
l'autre), un générateur (`generation_lot51.py`), les variantes dans `variantes_lot51.yaml`.
Deux nœuds liés sont toujours distincts : petite travée et longrines arrêtées à 1 mm du nœud
lié ; néoprène = SEG2 DIS_T de 1 mm (U2.02.03 : un discret ne transmet pas le moment d'un
couple) relié au nœud de la poutre par un bras rigide. Rotule en tête de pile : translations par
bras rigide de 0,20 m, rotations libres. Signalés, conformément à la consigne : la géométrie de la
petite travée (un montant à chaque bout, une diagonale) est une hypothèse ; pour H = 4,0 m, la
semelle est inchangée (dimensions et raideurs) et abaissée au pied des piles ; aucun plan
d'amarrage n'est fourni (taquets aux positions AVP).

## Variantes calculées et instabilité

11 variantes atteignent `FIN` (niveau C), 0 alarme ; niveau B valide (751/751) pour les douze.
**A (4 poutres indépendantes) est mécaniquement instable** : `<F> <FACTOR_11>`, pivot nul sur le
ddl physique DRX du nœud 305, bout de la longrine L− en (6,251 ; −0,75 ; 0,89). Chaque longrine,
reliée à ses deux bouts par une rotule seulement, tourne librement autour de la droite de ses
appuis. Elle n'a pas été stabilisée ; nouveau diagnostic DIAG-030.

## Effectifs des combinaisons

276 235 par variante : ELU fondamental 121 556, ELU accidentel 75 008 (G + ACA : 40 événements ;
G + AMF : 24 événements), ELS caractéristique 60 778, ELS fréquent 18 458, ELS quasi permanent 435.
Variante E (G2 de chaque travée à 1,2 ou 0,9, Q et houle sur toute combinaison non vide de
travées) : 5 416 185. Énumérées une à une, les combinaisons de R sont toutes distinctes. Elles
sont livrées **en règles** (`combinaisons.csv` + `evenements.csv`, énumérées par `recombiner.py`),
et non en liste comme au lot 50 ter : la liste ferait 85 Mo par variante.

ELU accidentel, règle du projet (lot 50, D5) : G + A_d + ψ1·Q_dominante + Σ ψ2·Q_autres, la
dominante pouvant être absente ; G + ACA sans autre événement AC, G + AMF sans autre événement AM.

## Harnais

Harnais D du tronc commun RÉUSSI pour les 11 variantes, 68 cas chacune : résidu relatif maximal
1,1·10⁻¹¹ (P4E) ; cas unitaires d'accostage et d'amarrage : 1 kN à 1,1·10⁻¹¹ près au pire.
Contrôles de R : somme des travées 6,1·10⁻¹³ ; néoprènes, −K·Δu contre tête du profilé
3,0·10⁻¹² ; décomposition contre énumération 2,2·10⁻¹⁶.

## Comparaison des variantes (enveloppes B′ et ELU accidentel ; kN, kN·m, mm)

Flèches : travée 1, relatives à la corde des appuis, actions variables seules. Extrêmes signés.
Détail (état, combinaison, lieu) : `comparaison_variantes_detail.csv`.

| Var. | PP My | Flèche ELS f bas / haut | Flèche ELS c bas / haut | Néo Fz min / max | Néo Fxy | Néo dh | Piles N min / max | Piles M tête / pied | Chev. My | Long. My | Quai RX |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R | −53,8 | −22,2 / 22,4 | −44,5 / 44,7 | −49,1 / 61,1 | 57,3 | 25,5 | −77,1 / 44,5 | 0,0 / 13,2 | 11,7 | 7,2 | 200,7 |
| E | 42,2 | −14,7 / 15,0 | −30,1 / 30,4 | −73,8 / 88,0 | 55,1 | 24,5 | −95,6 / 61,6 | 0,0 / 19,3 | 16,4 | 9,0 | 201,6 |
| T1 | −53,8 | −22,2 / 22,4 | −44,5 / 44,7 | −49,1 / 61,1 | 57,3 | 25,5 | −78,8 / 47,4 | 10,8 / 11,3 | 12,3 | 11,8 | 200,7 |
| T2 | −53,8 | −22,2 / 22,4 | −44,5 / 44,7 | −49,2 / 61,2 | 57,3 | 25,5 | −75,4 / 45,3 | 10,7 / 7,0 | 11,7 | 12,0 | 200,8 |
| A | instable | | | | | | | | | | |
| P4 | −53,7 | −22,1 / 22,3 | −44,4 / 44,5 | −49,1 / 61,3 | 58,0 | 25,8 | −91,6 / 41,6 | 0,0 / 16,8 | 11,6 | −5,0 | 196,6 |
| P4E | −53,7 | −22,1 / 22,3 | −44,4 / 44,5 | −49,1 / 61,3 | 58,0 | 25,8 | −88,0 / 41,6 | 11,5 / 8,7 | 12,5 | 11,2 | 196,8 |
| N− | −54,0 | −22,3 / 22,4 | −44,6 / 44,7 | −48,8 / 61,0 | 32,0 | 28,5 | −77,4 / 44,3 | 0,0 / 11,6 | 11,4 | 5,4 | 182,8 |
| N+ | −53,4 | −22,1 / 22,4 | −44,2 / 44,5 | −49,6 / 61,3 | 104,0 | 23,1 | −76,4 / 44,6 | 0,0 / 14,0 | 12,3 | 9,7 | 241,9 |
| M | −54,2 | −22,4 / 22,4 | −44,9 / 44,9 | −49,2 / 61,9 | 151,7 | 27,8 | −76,8 / 43,8 | 0,0 / 11,1 | 59,4 | −2,0 | −153,6 |
| S1 | −50,8 | −28,4 / 28,7 | −56,6 / 56,9 | −49,8 / 61,8 | 58,9 | 26,2 | −77,6 / 45,1 | 0,0 / 13,4 | 11,8 | 7,6 | 199,7 |
| S3 | −55,8 | −19,0 / 19,2 | −38,1 / 38,2 | −48,6 / 60,9 | 56,5 | 25,1 | −76,9 / 44,0 | 0,0 / 13,0 | 11,6 | 7,0 | 203,5 |

Fz < 0 : effort de retenue (soulèvement) à reprendre par un dispositif anti-soulèvement (P38).
Toutes les grandeurs du § 7 (dont Mz, N, V des poutres, V des piles, T et V de l'anneau, nœuds
d'angle, réactions RY et RZ du quai) sont dans `comparaison_variantes.csv`.

Par rapport à R :

- **E** : la continuité réduit le moment des poutres de 22 % et les flèches d'un tiers, mais
  augmente la retenue des néoprènes (−74 kN), leur compression (88 kN), l'effort des piles et les
  chevêtres (My 16,4 kN·m, V 90 kN).
- **T1** : une pile encastrée par chevêtre prend 10,8 kN·m en tête ; les longrines passent de 7,2 à
  11,8 kN·m ; le tablier ne change pas.
- **T2** : quatre encastrements, 10,7 kN·m en tête et 7,0 en pied ; longrines à 12,0 kN·m ;
  tablier inchangé.
- **A** : instable, non calculée (torsion libre des longrines).
- **P4** : piles de 4,0 m ; moment en pied 16,8 kN·m, effort tranchant divisé par plus de 2,
  compression plus forte (poids des piles) ; tablier quasi inchangé.
- **P4E** : idem avec têtes encastrées : 11,5 kN·m en tête, 8,7 en pied.
- **N−** : effort horizontal des néoprènes divisé par 1,8 (32 kN) contre 3 mm de déplacement en
  plus ; la rotule fixe du quai reprend 183 kN en X.
- **N+** : effort horizontal des néoprènes de 104 kN, rotule du quai à 242 kN en X, compression
  des poutres à −212 kN.
- **M** : l'appui mécanique concentre l'effort transversal (151,7 kN) et charge les chevêtres en
  flexion (My 59,4 kN·m) ; X libre, la rotule du quai reprend la dilatation (−154 kN).
- **S1** : flèches + 28 % (ELS c −56,6 / +56,9 mm), moment des poutres − 6 %.
- **S3** : flèches − 15 % (ELS c −38,1 / +38,2 mm), moment des poutres + 4 %.

## Livraison (`/media/sf_partage/echanges/lot51/pontons_alu_01/`, 292 Mo)

Par variante calculée : `noeuds`, `elements`, `membres`, `efforts_elementaires`,
`deplacements_elementaires`, `reactions_elementaires`, `combinaisons`, `evenements`, `charges`,
`sections`, `appuis_neoprene`, `piles` (CSV, format du lot 50 ter) et `recombiner.py` ; `A/` :
`instabilite.txt` ; `comparaison_variantes.csv` et son détail ; `R/charges.med` et
`R/charges_salome.py` (chaîne des livrables du tronc commun : 68 cas, 68 vues rendues par pvbatch
puis par `exec()`) ; `empreintes.sha256` (148 fichiers, `sha256sum -c` : 0 écart). Noms neufs.

## Points ouverts, signalés et non tranchés

1. Durée de moyennage du vent Météo-France.
2. Coefficients Cv et Ct du fournisseur de défenses.
3. Fiche fournisseur des taquets de 5 t.
4. Plan d'amarrage absent (taquets aux positions AVP).
5. Géométrie de la petite travée (un montant à chaque bout, une diagonale).
6. Semelle pour H = 4,0 m (inchangée, abaissée).
7. Fixation de la défense sous 36,6 kN, vérification locale.
8. Interprétations de l'outil, à confirmer par MM : G2 par travée en E (1,2 ou 0,9 par travée, G1
   en bloc) ; M, N− et N+ appliqués aux six appuis, ceux de X = 14,02 compris ; G + AMF
   accompagné d'un événement AC (ψ1 = 0,5) ; accostage appliqué sur l'axe de la poutre de rive.
9. Variante A : liaison réelle des longrines aux têtes de pile à définir si la solution est
   gardée.

## `rex` et interventions

`aster-expert rex pontons_alu_01` : 25 exécutions attribuées, 1 échec (A), classé **nouveau**
(DIAG-030) ; développement 23 (taux d'échec 4,3 %), vérification 2 ; « Tous les échecs sont
classés : clôture possible ». Précédent PRE-040 (statut observé) : « navire enveloppe de plaisance
défini par le maître de port plutôt que par L·B·T·Cb ». Interventions de MM : 0. Connaissances
ayant évité une erreur : 2 (DIAG-004, masses nulles des discrets ; DIAG-001 lu et écarté sur le
FACTOR_11 de A). PAT-009 appliqué sans déclaration préalable dans `connaissances_appliquees.yaml` :
non attribué a posteriori.

## Limites

- Résultantes (V, Fxy, M des piles, déplacement horizontal) : maximum sur 2 048 directions, à
  1,2·10⁻⁶ près par défaut.
- Les livrables locaux du lot 50 bis (non versionnés) ont été remplacés par ceux de R pour
  produire `charges.med` ; le test d'export du lot 50 ter est désormais ignoré avec son motif.
- `deliverables`, `engineering_summary` et `results_package` de `projet.yaml` : seul
  `deliverables` est passé au lot 51 ; les deux autres décrivent encore la travée du lot 50 bis.
- Le paquet versionné (`resultats/paquet/`) reste celui du lot 50 bis.
