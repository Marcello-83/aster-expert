# Arbitrage — quai en combi-wall ancré — lot 39, décision D19

Décision de MM énoncée à l'étape 1 bis du lot 39 (« le lancement de ce lot vaut
validation »). Le texte des champs `option_retained`, `justification`,
`validity_domain` et `discarded_variants` est recopié à l'identique de l'énoncé
du lot 39 ; seules les césures de ligne sont celles de ce fichier. L'en-tête, les
conventions, le libellé `topic` (l'énoncé n'en donne pas) et la mise en forme des
variantes écartées (`*description*`/`*reason*`, déjà celle de l'énoncé) sont de
la session.

**Statut du document.** Transcrit par Claude. Validé par MM par le lancement du
lot 39.

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure de l'enregistrement par la session (MM n'en a écrit aucune) :
  `lot39_enregistrement.json`.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décision D19 (énoncé du lot
    39, étape 1 bis)"`
  - `date` : jour de l'enregistrement.

---

## Décision 19 — position des armatures longitudinales dans les calculs de section

- **Opération** : nouvelle entrée pratique au point 14
- `point_label` : `"14"`
- `topic` : `"Position de l'axe des armatures longitudinales dans les calculs de section (poutre de couronnement)"`

**option_retained**
Dans les calculs de section, la distance entre le parement et l'axe des
armatures longitudinales est de 0,10 m sur toutes les faces. Ce sont les valeurs
`C_SUP_*` et `C_INF_*` de `CALC_FERRAILLAGE`, ou ds et di du logiciel de MM. Le
diamètre équivalent des armatures longitudinales est de 40 mm.

**justification**
L'enrobage nominal de 65 mm de D18 se mesure au nu de l'armature la plus proche
du parement, c'est-à-dire l'étrier. L'axe des armatures longitudinales se trouve
donc à environ 65 + diamètre de l'étrier + la moitié du diamètre longitudinal,
soit environ 0,10 m. Le lot 38 avait pris 0,065 m comme distance à l'axe, ce qui
surestime le bras de levier.

**validity_domain**
La valeur est forfaitaire ; elle sera à ajuster au ferraillage réellement
retenu.

**discarded_variants**
1. *description* : distance à l'axe égale à l'enrobage nominal, 0,065 m (lot 38).
   *reason* : confond l'enrobage, mesuré au nu de l'étrier, avec la position de
   l'axe des barres longitudinales.

---
