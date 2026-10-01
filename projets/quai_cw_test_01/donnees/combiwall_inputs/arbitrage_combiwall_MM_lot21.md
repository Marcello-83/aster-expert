# Arbitrage des entrées pratique — quai en combi-wall ancré — lot 21

Décision de **MM** sur la modélisation de coque du tube, au format du gabarit
`gabarit_saisie_fiche_hypotheses.md` (lot 17). Cas de test fictif :
`QUAI-CW-TEST-01`.

## Conventions communes

- `decided_by` : `"MM"`
- `decided_at` : `2026-09-21T18:00:00` — heure conventionnelle, déclarée dans la
  référence de la source `decision_ingenieur`.
- Source `decision_ingenieur` :
  - `origin` : `"decision_ingenieur"`
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décision prise en séance
    de travail ; heure de decided_at conventionnelle"`
  - `date` : `2026-09-21`

---

## Décision 10

- **Opération** : arbitrage de l'entrée ouverte du point 1
- `point_label` : `"1"`
- `topic` : `"Choix de la modélisation de coque du tube entre les modélisations recevables (DKT ou COQUE_3D)"`

**option_retained**
Le tube est modélisé en DKT, sur une surface facettisée représentant sa
géométrie cylindrique. La discrétisation angulaire est fixée par la branche
maillage, et figure dans les invariants de maillage déclarés par la fiche.

**justification**
DKT et COQUE_3D sont tous deux recevables pour ce tube selon le constat
Code_Aster du point 1 (U2.02.01, structure mince, h/R ≈ 1/44). DKT est retenu
pour l'homogénéité avec la palplanche intercalaire, qui partage ses nœuds avec
le tube sur les lignes de serrure : la représentation orthotrope envisagée pour
la palplanche n'est admise qu'en DKT, DST ou Q4G, et DKT reste recevable si la
géométrie réelle du profil est retenue à la place. La documentation officielle
modélise elle-même un cylindre mince en facettes DKT (cas test SSLS502).

**validity_domain**
La facettisation remplace la courbure par des facettes planes. Aucun critère
chiffré de discrétisation angulaire n'a été trouvé dans la documentation ;
l'écart géométrique et son effet sur la raideur du tube dépendent du nombre de
facettes retenu par la branche maillage.

**discarded_variants**
1. *description* : Tube en COQUE_3D.
   *reason* : N'apporte rien pour un tube mince. Et la compatibilité d'un
   maillage coïncident entre COQUE_3D et une palplanche en DKT n'est pas établie.
