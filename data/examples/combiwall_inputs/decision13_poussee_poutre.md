# QUAI-CW-TEST-01 — décision 13 : poussée sur la poutre de couronnement

Rédigé par Claude. **Lancer le lot 33 vaut validation de cette décision par MM.**
Aucune mention n'est à lever dans ce fichier.

- **Opération** : `insert_practice_entry`
- `point_label` : `"12"`
- `topic` : `"Poussée et pression d'eau sur la hauteur de la poutre de couronnement"`
- `decided_by` : `"MM"`
- `decided_at` : heure d'enregistrement
- `sources` : `decision_ingenieur`, avec la référence `"MM, cas de test
  QUAI-CW-TEST-01, lacune relevée à la relecture du lot 32"`, datée du jour
  d'enregistrement.

**option_retained**
Entre +2,60 et +4,00, les profils de poussée G et Q1 et les profils de pression
d'eau sont intégrés sur la hauteur de la poutre de couronnement. Leur résultante,
par mètre de quai, est appliquée comme une charge linéique répartie sur l'élément
de poutre `POUTRE_COUR`, dirigée vers le bassin (−Y), sur toute la longueur de la
tranche. Le moment de cette résultante par rapport à l'axe de la poutre (+3,30)
est appliqué comme un moment linéique d'axe X.

**justification**
L'écran n'est maillé que jusqu'à +2,60 (décision 11). Le terrain pousse pourtant
sur toute la hauteur jusqu'à l'arase (+4,00). Sans cette charge, la poussée sur
la hauteur de la poutre est perdue, soit environ 119 kN pour G et 358 kN pour Q1
sur la tranche. La poutre étant représentée par son axe, une charge linéique
équivalente, avec son moment de transport, est la représentation cohérente avec
la décision du point 3.

**validity_domain**
La poutre étant un élément de poutre, la répartition de la poussée sur sa hauteur
n'est pas représentée : seule sa résultante et son moment le sont.

**discarded_variants**
1. *description* : Ignorer la poussée au-dessus de +2,60.
   *reason* : Charge perdue, et équilibre faussé d'environ 0,5 % pour G et 5 %
   pour Q1.
