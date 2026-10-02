# Arbitrage — quai en combi-wall ancré — lot 45, D20 et D21 corrigées, module de l'acier

Décisions de MM énoncées dans la consigne du lot 45 (« Décisions de MM, validées
par le lancement du lot », copie : `docs/lots/lot45_consigne.md`). Les champs
`option_retained`, `validity_domain` et `discarded_variants` de D20 et D21 sont
recopiés à l'identique du texte de MM ; seules les césures de ligne sont celles de
ce fichier. L'en-tête, les conventions, les libellés `topic` (inchangés : ils
rattachent la révision à l'entrée de D20 et de D21 du lot 44) et la décision du
module de l'acier (dont l'énoncé de MM tient en une phrase) sont de la session.

**Statut du document.** Transcrit par Claude. Validé par MM par le lancement du
lot 45.

**Correction.** La consigne du lot 44, rédigée par Claude, décrivait mal D21
(« Act = b·h, élément tendu, flexion simple exclue ») : le texte exact est celui
de la décision 21 ci-dessous. La décision 20 reçoit le texte de la décision de
MM, qui remplace le domaine de validité rédigé par la session au lot 44. Les
textes du lot 44 restent dans `decision_history` de chaque entrée.

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure de l'enregistrement par la session (MM n'en a écrit aucune) :
  `lot45_enregistrement.json`.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décisions D20, D21 et module
    de l'acier (consigne du lot 45)"`
  - `date` : jour de l'enregistrement.

---

## Décision 20 — révisée

- **Opération** : révision d'une entrée tranchée (texte de MM, qui remplace celui du lot 44)
- `point_label` : `"14"`
- `topic` : `"Coefficients partiels des matériaux en situation accidentelle (ELU accidentelle)"`

**option_retained**
ELU accidentelle, γc = 1,2 et γs = 1,0.

**justification**
Valeurs du tableau 2.1N de l'EN 1992-1-1 pour les situations accidentelles.
L'accostage est traité en combinaison accidentelle (D17).

**validity_domain**
Combinaison ELU accidentelle uniquement.

**discarded_variants**
1. *description* : Conserver γc = 1,5 et γs = 1,15 en situation accidentelle.
   *reason* : Ignore la distinction entre situations durables et accidentelles
   faite par l'EN 1992-1-1, et n'apporte qu'une marge non justifiée.

---

## Décision 21 — révisée

- **Opération** : révision d'une entrée tranchée (texte de MM, qui remplace celui du lot 44)
- `point_label` : `"14"`
- `topic` : `"Maîtrise de la fissuration de la poutre de couronnement (section minimale, contrainte de l'acier)"`

**option_retained**
As,min selon l'EN 1992-1-1, 7.3.2. Act est égale à la zone tendue complète de la
section avant fissuration, soit b·h/2 en flexion. kc dépend de la sollicitation.
k dépend de h : 0,65 pour h ≥ 800 mm. fct,eff = fctm. σs est tirée du tableau
7.2N, avec la correction 7.6N, pour φ = 40 mm et wk = 0,2 mm.

**justification**
Lecture littérale de 7.3.2, retenue par MM pour la poutre de couronnement.

**validity_domain**
Lecture littérale de Act, par opposition à une aire effective hc,eff. Pour une
pièce massive, elle est plus pénalisante : environ 68 cm² sur les faces AY et
91 cm² sur les faces AZ. Sur les faces AZ, φ*s sort du tableau 7.2N et σs est
bornée à 160 MPa. MM confirmera la transcription complète du tableau 7.2N sur
son exemplaire.

**discarded_variants**
1. *description* : Act limitée à une hauteur effective hc,eff autour des aciers.
   *reason* : Non retenue par MM pour cet ouvrage, qui préfère la lecture
   littérale de 7.3.2.

**sources supplémentaires**
- `origin` : `"norme"`
- `reference` : `"NF EN 1992-1-1, 7.3.2, tableau 7.2N, expression 7.6N"`
- `date` : `non précisée par MM (le schéma n'accepte une date complète seulement)`

---

## Décision 22 — module de l'acier (Es), en attente d'application

- **Opération** : nouvelle entrée pratique au point 14
- `point_label` : `"14"`
- `topic` : `"Module d'élasticité de l'acier de ferraillage (Es)"`

**option_retained**
Es = 200 GPa (EN 1992-1-1, 3.2.7(4)), pour tous les projets. Le quai garde
210 GPa (valeur employée depuis le lot 39) jusqu'au prochain lot qui recalcule son
ferraillage ; la décision est en attente d'application.

**justification**
Décision de MM (consigne du lot 44, confirmée au lot 45) : la valeur de 210 GPa
est celle des aciers de construction (EN 1993) ; la réglementation du béton armé
retient 200 GPa pour les armatures. Appliquée à la dalle au lot 44.

**validity_domain**
Tous les projets. Tant que le ferraillage du quai n'est pas recalculé, les
résultats du quai (lot 39, eys_pa = 2,1e11 Pa) portent 210 GPa : la fiche
déclare cette décision « en révision » (bloqueur de génération visible) jusqu'à
l'application.

**discarded_variants**
1. *description* : Es = 210 GPa.
   *reason* : Valeur des aciers de construction (EN 1993), non celle des armatures
   de béton armé.

---
