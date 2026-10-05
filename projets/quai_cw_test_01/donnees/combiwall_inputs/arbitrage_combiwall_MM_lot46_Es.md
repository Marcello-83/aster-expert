# Arbitrage — quai en combi-wall ancré — lot 46, module d'élasticité des armatures

Décision de MM énoncée dans la consigne du lot 46 (« Décisions de MM, validées par le
lancement du lot », copie : `docs/lots/lot46_consigne.md`, décision 1). Elle **remplace**
le texte que la session du lot 45 avait rédigé pour la décision sur Es (le lot 45 notait
que l'énoncé de MM « tient en une phrase » ; le texte détaillé est désormais celui de
MM). Les champs `option_retained`, `justification`, `validity_domain` et
`discarded_variants` sont recopiés à l'identique ; seules les césures de ligne sont celles
de ce fichier. L'en-tête, les conventions et le libellé `topic` (inchangé : il rattache la
révision à l'entrée du lot 45) sont de la session. Le texte du lot 45 reste dans
`decision_history`.

**Statut du document.** Transcrit par Claude. Validé par MM par le lancement du lot 46.

**Application.** Le quai n'est pas recalculé au lot 46 : la décision reste « en révision »
(bloqueur de génération visible) jusqu'au prochain lot qui recalcule son ferraillage
(`lot46_enregistrement.json`).

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure de l'enregistrement par la session (MM n'en a écrit aucune) :
  `lot46_enregistrement.json`.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, module d'élasticité des armatures
    (consigne du lot 46, décision 1)"`
  - `date` : jour de l'enregistrement.

---

## Décision 22 — Es, révisée

- **Opération** : révision d'une entrée tranchée (texte de MM, qui remplace celui du lot 45)
- `point_label` : `"14"`
- `topic` : `"Module d'élasticité de l'acier de ferraillage (Es)"`

**option_retained**
Module d'élasticité des armatures de béton armé, Es = 200 GPa, pour tous les projets.

**justification**
Valeur de calcul de l'EN 1992-1-1, 3.2.7(4). La valeur de 210 GPa est celle des aciers
de construction (EN 1993-1-1, 3.2.6) et ne s'applique pas aux armatures.

**validity_domain**
Armatures passives de béton armé. Hors domaine : acier de construction (tubes,
palplanches, profilés), qui garde 210 GPa.

**discarded_variants**
1. *description* : Es = 210 GPa pour les armatures.
   *reason* : Valeur de l'EN 1993, non conforme à l'EN 1992-1-1.

---
