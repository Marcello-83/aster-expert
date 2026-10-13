# Essais du lot 50 ter — PONTONS-ALU-01 : export des données pour l'EC9, les vues et les plans

Projet `projets/pontons_alu_01/`. Consigne : `docs/lots/lot50ter_consigne.md`. Lot d'export
seulement : aucun maillage, aucune exécution Code_Aster, aucun classeur ni image. Tout est lu dans
les résultats du lot 50 bis (exécution de référence `20261012T144404-2cf50a46`, `.comm` d'empreinte
`5964ae42…b262`, P24 et P25, MP1200, k = 1) : tableaux des livrables
`resultats/livrables/donnees/*.npz`, extraits du MED des livrables (`resultats/livrables/med/
resultats.med`), et le `.comm` lui-même pour les sections, l'orientation et les charges.

## 1. Critère du contrôle de recombinaison (écrit avant l'export)

Recombiner les cas élémentaires de `efforts_elementaires.csv` avec les facteurs de
`combinaisons.csv` (jeu B, états limites ELU fondamental et ELU accidentel), par le script livré
`recombiner.py` (bibliothèque standard de Python seulement, aucune lecture des tableaux du projet),
doit redonner les trois valeurs du lot 50 bis :

| Grandeur | Valeur publiée au lot 50 bis | Famille, lieu |
|---|---|---|
| \|MFY\| max des poutres principales, ELU B | 53,2175 kN·m | POUTRES_PRINC |
| N min des pannes secondaires, ELU B | −85,6 kN (−85,6496) | PANNES_SEC |
| N min du profilé support SUP_1, ELU B | −58,0 kN (−58,0077) | SUP_1 |

Les valeurs publiées sont arrondies (6 chiffres significatifs au mieux) : le critère de 10⁻⁶ en
relatif porte sur les **valeurs non arrondies** du lot 50 bis, obtenues par le code inchangé du lot
50 bis (`pontons_alu_01.lot50bis.family_summary` sur `resultats/livrables/`, jeu B, maximum des
ELU fondamental et accidentel), et inscrites dans `recombiner.py` avec 17 chiffres significatifs.
Critère : |valeur recombinée − valeur du lot 50 bis| ≤ 10⁻⁶ × |valeur du lot 50 bis| pour chacune
des trois ; l'arrondi de la valeur recombinée doit en outre égaler la valeur publiée. Toute autre
issue est un échec, rapporté tel quel.

Les nombres des CSV sont écrits avec 17 chiffres significatifs (`repr` de Python) : la
recombinaison depuis les fichiers n'ajoute aucune erreur d'arrondi au-delà de la double précision.

## 2. Contrôles de cohérence de l'export (sans critère numérique nouveau)

- Chaque élément de barre du modèle (groupes `POUTRES_PRINC`, `MONTANTS`, `DIAGONALES`,
  `PANNES_SEC`, `SUPPORTS`, `CHEVETRE`, `POTEAUX`) figure une fois dans `elements.csv` et dans un
  membre exactement.
- Les longueurs des membres d'une barre (groupe `PP_YM`, `MONT_1`…) somment la longueur de la
  barre.
- Équilibre global de chaque cas mécanique : réactions des rotules + réactions cumulées des
  ressorts + charge appliquée (extension `resultant` du projet) = 0, à 10⁻⁶ près de l'échelle du
  cas — c'est le harnais D du lot 50 bis relu dans les fichiers exportés, pas un contrôle nouveau.

## 3. Résultats (après l'export)

Commande : `PYTHONPATH=projets .venv/bin/python projets/pontons_alu_01/scripts/export_lot50ter.py`
(code de sortie 0), puis copie vers `/media/sf_partage/echanges/lot50ter/pontons_alu_01/` et
`sha256sum -c empreintes.sha256` (10 fichiers OK). Le script livré a été rejoué depuis le partage
sans aucun paquet tiers (`python -I -S recombiner.py`) : réussi.

Contrôle de recombinaison (critère du § 1) : **réussi**.

| Grandeur | Recombinée (N, N·m) | Lot 50 bis (N, N·m) | Écart relatif | Lieu, combinaison |
|---|---|---|---|---|
| \|MFY\| max, poutres principales | 53217,46915097666 | 53217,46915097667 | 1,4·10⁻¹⁶ | élément 79 (PP_YM, X = 3,75), extrémité 1 ; B_ELU_G1.2_HD_TM_AMP_ACP_Q |
| N min, pannes secondaires | −85649,60688741648 | −85649,60688741648 | 0 | élément 334 (PANNE_4), extrémité 1 ; B_ELU_G1.2_HD_TM_AMM_ACP_Q |
| N min, SUP_1 | −58007,69303457486 | −58007,69303457486 | 0 | élément 349 (pied), extrémité 1 ; B_ELU_G1.2_TP_HD_AMM_ACP_Q |

Les arrondis égalent les valeurs publiées (53,2175 kN·m ; −85,6 kN ; −58,0 kN). 2 214 combinaisons
ELU du jeu B (fondamental et accidentel), 9 984 lignes d'efforts.

Cohérence (§ 2) : 324 éléments de barre, chacun dans un membre et un seul (117 membres) ; longueurs
des membres sommées égales à la barre (PP_YM 6,25 m, MONT_2 1,86 m, test
`test_full_export_and_recombination`) ; équilibre des 16 cas relu dans les fichiers : résidu
relatif maximal 2,1·10⁻¹¹ (TAM), 4·10⁻¹³ à 4·10⁻¹² pour les cas mécaniques.

Convention ELNO vérifiée sur PP_YM sous Q : N, VZ, MFY égaux aux deux côtés de chaque nœud
intérieur d'une barre (efforts intérieurs, diagramme continu), sauts aux seuls raccords
(montants, diagonales).
