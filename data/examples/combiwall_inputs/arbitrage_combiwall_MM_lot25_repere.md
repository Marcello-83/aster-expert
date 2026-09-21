# Arbitrage — quai en combi-wall ancré — lot 25, repère global

Décision de MM sur le repère global et l'origine du modèle, transmise dans
l'énoncé du lot 25. Recopiée telle qu'elle est rédigée.

**Statut du document.** Rédigé par MM. Enregistrée telle quelle par la session.

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure d'enregistrement, déclarée dans le compte rendu.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, convention de repère prise
    en séance de travail"`
  - `date` : jour d'enregistrement.

---

## Décision 10 — repère global

- **Opération** : `insert_practice_entry` (absent de la fiche)
- `point_label` : `"9"`
- `topic` : `"Repère global et origine du modèle"`

**option_retained**
Repère global orthonormé direct :

- X horizontal, le long du quai, de la face `SYM_G` vers la face `SYM_D` ;
- Y horizontal, perpendiculaire au quai, positif vers la terre ;
- Z vertical ascendant.

Origine : X = 0 dans l'axe de `TUBE_05`, Y = 0 dans le plan des axes des tubes,
Z = 0 à la cote 0,00 CM. Les cotes du cas de test sont donc directement les
valeurs de Z. Les faces de coupe sont à X = −10,40 et X = +10,40. La palplanche
intercalaire est dans le plan Y = 0 et rejoint chaque tube sur ses génératrices
situées en Y = 0, à X = ±0,71 m de l'axe du tube. Unités du modèle : mètre,
newton, pascal, kilogramme.

**justification**
Un repère unique, déclaré dans la fiche, est la condition pour que le maillage
et le fichier de commandes soient générés de façon cohérente et relus sans
ambiguïté. Placer l'origine sur l'axe de symétrie et à la cote 0 CM rend les
coordonnées directement lisibles : les cotes deviennent Z, et la symétrie se
contrôle par le signe de X. Placer la palplanche dans le plan des axes fait
coïncider les lignes de serrure avec des génératrices du tube, donc avec des
nœuds de sa facettisation.

**validity_domain**
Le plan des serrures dans l'axe des tubes est une idéalisation : la position
réelle des serrures dépend du type de connecteur. Les unités SI imposent des
charges en N et des raideurs en N/m ou N·m, et non les MN utilisés dans les
décisions ; la conversion est à la charge du générateur et doit être contrôlée.

**discarded_variants**
1. *description* : Origine au pied de l'écran, sur la face `SYM_G`.
   *reason* : Rend les cotes illisibles et masque la symétrie.
