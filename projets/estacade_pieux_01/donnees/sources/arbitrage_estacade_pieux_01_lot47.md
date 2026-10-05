# Arbitrage de MM — projet `estacade_pieux_01` (lot 47)

Décisions de MM, recopiées à l'identique : E1 à E12 de la consigne du lot 47
(`docs/lots/lot47_consigne.md`, section « Décisions de MM, validées par le
lancement du lot »), E13 à E16 des réponses de MM dans le chat de la session du
2026-10-05, aux quatre points pratiques que ni E1 à E12 ni l'annexe B ne
couvraient. La numérotation E14 à E16 est celle de la session : MM n'a numéroté
que E13.

## E1 à E12 (consigne du lot 47)

| N° | Décision |
|---|---|
| E1 | Géométrie du **modèle Robot** : 31,20 m, 7 files de pieux à 5,00 m, 14 pieux. La description à 36,2 m et 8 files n'est **pas** retenue. |
| E2 | Chevêtres : barre de **1,20 × 0,90 m**, section rectangulaire, **au plan moyen de la dalle**, sans excentrement. Conséquence connue et acceptée : la dalle et le chevêtre se recouvrent sur 1,20 × 0,40 m, ce qui compte deux fois ce volume en raideur et en poids, comme dans le modèle Robot. La session chiffre ce double compte en kN par chevêtre et le rapporte, sans le corriger. |
| E3 | Pieux : sections corrodées par tronçon (annexe B, tableau B2), sans section mixte au droit du bouchon. Entre +0,70 m NGF et le nœud du tablier, la section du tronçon supérieur est prolongée. |
| E4 | Appui vertical en pointe : **DZ = 0** à −13,00 m NGF, rotations libres. Les ressorts sont horizontaux (kx = ky) : sans cet appui, le mouvement vertical d'ensemble n'est pas bloqué. |
| E5 | Calcul **linéaire** : ressorts élastiques, sans palier. |
| E6 | Ressorts de la file 1 aux nœuds −8,00 et −8,50 m : kx = ky = 21 200 kN/m (erreur de recopie du tableau source). Les nœuds manquants à −10,00 et −10,50 m sont complétés à 21 200 kN/m. Les files 1 et 7 sont identiques. |
| E7 | Béton : Ecm = 34 GPa, ν = 0,2, 25 kN/m³. Acier : 210 GPa, ν = 0,3, 78,5 kN/m³ (la valeur du modèle source). |
| E8 | Charge mobile TS : **pas de 0,50 m** sur toute la longueur ; deux positions transversales, « axé » et « bord de voie », déduites de la géométrie de la voie (annexe B). UDL de 6,30 kPa sur toute la longueur de la voie. |
| E9 | Freinage : **381 kN**, réparti uniformément sur la surface de la voie, appliqué dans le plan moyen de la dalle, selon X. |
| E10 | Température : ΔT uniforme de ±27,5 °C sur la dalle et les chevêtres seulement, α = 1×10⁻⁵ /°C. |
| E11 | Combinaisons : celles du modèle source, **reproduites telles quelles** (n° 100 à 115, en ELS f, ELS c, ELU+ et ELU−). LM1 y est l'enveloppe sur les positions de la charge mobile. |
| E12 | Tolérances de comparaison : **3 %** pour les efforts globaux (réactions, N des pieux) ; **5 %** pour les moments et efforts tranchants des barres (pieux, bouchons, chevêtres) ; **10 %** pour les efforts locaux de la dalle (Mxx, Qxx). |

## E13 à E16 (réponses de MM dans le chat, 2026-10-05)

### E13 — Formulations d'éléments

Question posée : quelles formulations d'éléments retenir (choix de modélisation
qui change la physique représentée) ; précédents PRE-023 (dalle : DKT) et D14
(quai : POU_D_T pour la poutre de couronnement).

Réponse de MM, à l'identique :

> Choix 1 : DKT pour la dalle, POU_D_T pour les pieux et les chevêtres.Variantes de sensibilité déclarées :  (a) DST pour la dalle ;  (b) POU_D_E pour les chevêtres seulement, pour tester l'hypothèse      « le modèle source ne prend pas en compte la déformation d'effort tranchant      des barres » si C6 à C8 sortent de tolérance.À inscrire comme décision E13, origine arbitrage_mm.

### E14 — Étendue du bouchon des pieux

Question posée : étendue du bouchon, qui sépare C3/C4 (« dans le bouchon ») de
C5 (« dans le pieu ») ; le modèle n'en dépend pas (E3 exclut toute section mixte).

Réponse de MM, à l'identique :

> Le bouchon va de +0.70 à -0.80

### E15 — Surface d'application des roues (TS et LM2)

Question posée : empreinte de B4 telle quelle au plan moyen, ou surface diffusée
jusqu'au plan moyen.

Option choisie par MM (libellé et description proposés par la session) :

> Empreinte B4 telle quelle (Recommandé) — Je lis B4 comme la donnée du modèle source : 0,40 × 0,40 m (TS) et 0,35 × 0,60 m (LM2), en pression uniforme au plan moyen, sans diffusion.

### E16 — Positions de LM2

Question posée : quelles positions retenir pour LM2 (E8 ne règle que TS).

Option choisie par MM (libellé et description proposés par la session) :

> Comme TS (Recommandé) — Pas de 0,50 m selon X sur toute la longueur. Deux positions transversales : « axé » (roues à Y = ±1,00) et « bord de voie » (roue tangente au bord de la voie, à Y = ±1,325).

**Erreur de la session dans la description, signalée à MM.** La cote ±1,325
écrite dans la description proposée est fausse : elle prend 0,35 m comme
dimension transversale de l'empreinte, alors que B4 donne 0,35 m selon X et donc
0,60 m selon Y. La règle choisie (« roue tangente au bord de la voie », comme
pour TS en E8) donne, avec la voie de B1 (Y de −1,50 à +1,50) : roue extérieure
centrée à Y = 1,50 − 0,30 = **1,20**, roue intérieure à 1,20 − 2,00 = **−0,80**.
C'est la règle, et non la cote erronée, qui est appliquée ; à confirmer par MM à
la relecture.
