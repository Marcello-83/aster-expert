# QUAI-CW-TEST-01 — décision 12 : appui vertical de l'écran

Rédigé par Claude. **Lancer le lot 28 vaut validation de cette décision par MM.**
Le fichier ne comporte aucune mention à lever.

- **Opération** : `insert_practice_entry`
- `point_label` : `"11"`
- `topic` : `"Appui vertical de l'écran"`
- `decided_by` : `"MM"`
- `decided_at` : heure d'enregistrement
- `sources` : `decision_ingenieur`, avec la référence `"MM, cas de test
  QUAI-CW-TEST-01, appui vertical décidé en séance de travail"`, datée du jour
  d'enregistrement.

**option_retained**
Le déplacement vertical est bloqué aux nœuds du pied des tubes, à la cote
−26,00, qui forment le groupe de nœuds `PIED_TUBES`. Seul le déplacement
vertical est bloqué : les déplacements horizontaux et les rotations du pied
restent libres. Le pied des palplanches (−18,00) n'a pas d'appui vertical.

**justification**
Les ressorts de sol de la décision 5 sont horizontaux. Sans autre appui, le poids
de l'écran et de la poutre, la composante verticale des tirants et celle de
l'effort d'amarrage ne seraient repris que par la composante verticale des
tirants inclinés. Ce mécanisme est artificiel, et proche d'un mode rigide. La
reprise verticale réelle se fait par la pointe et le frottement latéral des
tubes ; la représenter par un appui en pointe est la forme la plus simple qui
place la réaction verticale au bon endroit.

**validity_domain**
- Le frottement latéral n'est pas représenté : tout l'effort vertical descend
  jusqu'à la pointe, donc l'effort normal dans les tubes est surestimé en partie
  basse.
- L'appui est rigide : le tassement de la pointe n'est pas représenté.
- Les palplanches ne portent pas verticalement ; leur poids transite par les
  serrures vers les tubes.

**discarded_variants**
1. *description* : Aucun appui vertical.
   *reason* : Reprise verticale par les seuls tirants ; mécanisme artificiel,
   voisin d'un mode rigide.
2. *description* : Ressorts verticaux de frottement répartis le long de la fiche.
   *reason* : Exige des raideurs de frottement absentes des données du cas.

**Convention de nommage** : ajout du groupe de nœuds `PIED_TUBES` (nœuds des
tubes à Z = −26,00), rattaché au point `"11"`.
