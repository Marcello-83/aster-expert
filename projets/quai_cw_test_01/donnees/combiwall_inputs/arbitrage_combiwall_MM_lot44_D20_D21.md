# Arbitrage — quai en combi-wall ancré — lot 44, décisions D20 et D21

Décisions de MM énoncées dans la consigne du lot 44 (« Décisions de MM, validées
par le lancement du lot », copie : `docs/lots/lot44_consigne.md`). Les valeurs
retenues et le domaine de validité de D21 sont recopiés à l'identique de la
consigne ; seules les césures de ligne sont celles de ce fichier. L'en-tête, les
conventions, les libellés `topic`, les justifications, le domaine de validité de
D20 (la consigne n'en donne pas) et les variantes écartées sont rédigés par la
session à partir de la consigne et de l'état du quai (lot 39) : ils sont à relire
par MM.

**Statut du document.** Transcrit par Claude. Validé par MM par le lancement du
lot 44.

**Correspondance.** L'arbitrage de la dalle (`arbitrage_dalle_appuyee_01_v1`, P6)
citait « PRE-021 (D21, Act = zone tendue complète) » : aucune entrée PRE-021
n'existait. D21 est versée au lot 44 sous l'identifiant attribué par la session
(`connaissances/precedents/`, note de correspondance dans l'entrée).

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure de l'enregistrement par la session (MM n'en a écrit aucune) :
  `lot44_enregistrement.json`.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décisions D20 et D21
    (consigne du lot 44)"`
  - `date` : jour de l'enregistrement.

---

## Décision 20 — coefficients partiels des matériaux en situation accidentelle

- **Opération** : nouvelle entrée pratique au point 14
- `point_label` : `"14"`
- `topic` : `"Coefficients partiels des matériaux en situation accidentelle (ELU accidentelle)"`

**option_retained**
Situation accidentelle : γc = 1,2 et γs = 1,0.

**justification**
Décision de MM (consigne du lot 44, D20). Ces valeurs étaient déjà employées
depuis le lot 39 pour la famille ELU accidentelle du ferraillage de la poutre de
couronnement (EN 1992-1-1, tableau 2.1N, valeurs recommandées), sans décision de
MM : D20 les retient, aucun résultat du quai ne change.

**validity_domain**
Combinaison ELU accidentelle de D17 seulement ; les situations durables et
transitoires gardent γc = 1,5 et γs = 1,15 (D18).

**discarded_variants**
1. *description* : γc = 1,5 et γs = 1,15 en situation accidentelle. *reason* :
   valeurs des situations durables et transitoires, non celles de la situation
   accidentelle.

---

## Décision 21 — maîtrise de la fissuration de la poutre de couronnement

- **Opération** : nouvelle entrée pratique au point 14
- `point_label` : `"14"`
- `topic` : `"Maîtrise de la fissuration de la poutre de couronnement (section minimale, contrainte de l'acier)"`

**option_retained**
Act est la zone tendue complète, b·h, l'élément étant tendu (EN 1992-1-1,
7.3.2) ; σs est tiré du tableau 7.2N, avec le diamètre modifié par 7.6N ; φ40 ;
wk = 0,2 mm.

**justification**
Décision de MM (consigne du lot 44, D21). La poutre de couronnement est tendue :
la section minimale de 7.3.2 porte sur toute la section, et non sur la moitié
comme en flexion simple.

**validity_domain**
Éléments tendus ou en traction gênée. Il exclut la flexion simple, comme la dalle
l'a montré au lot 43 (kc = 0,4 et Act = b·h/2).

**discarded_variants**
1. *description* : Act = b·h/2 et kc = 0,4 (flexion simple). *reason* : la poutre
   de couronnement est tendue ; c'est le cas de la dalle (lot 43), hors du
   domaine de D21.

---
