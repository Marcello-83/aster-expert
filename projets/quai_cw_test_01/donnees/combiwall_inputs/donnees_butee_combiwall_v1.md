# QUAI-CW-TEST-01 — profil de butée limite (donnée complémentaire)

Donnée fictive du cas de test, validée par MM au lancement du lot 35. Elle sert
uniquement au contrôle de validité de la décision 5 (domaine de validité,
item 1) : la pression de réaction des ressorts doit rester inférieure à la butée
limite.

Établie par Claude selon Rankine (butée passive, sans frottement sol-écran, avec
cohésion), côté bassin, sol immergé sous la cote de dragage (σ'v = 0 à −12,00).
Elle n'est représentative d'aucun calcul K-Réa.

| Z (m CM) | Couche | σ'p, butée limite (kPa) |
|---|---|---:|
| −12,00 | argile marneuse (Kp = 2,464) | 47,1 |
| −18,00 | argile marneuse | 202,3 |
| −18,00 | marne compacte (Kp = 3,000) | 327,6 |
| −26,00 | marne compacte | 603,6 |

Variation linéaire entre les points ; discontinuité à −18,00 (deux valeurs,
une par couche).

**Convention du contrôle.** La pression de réaction d'un ressort vaut
k_i·u_i / A_i, où A_i est l'aire tributaire projetée du nœud. Elle est comparée
à σ'p(z) sans ajouter la pression initiale au repos, qui n'est pas modélisée
(décision 5, domaine de validité, item 3). Le contrôle porte sur les réactions
en compression ; une réaction en traction est signalée à part (item 2).
