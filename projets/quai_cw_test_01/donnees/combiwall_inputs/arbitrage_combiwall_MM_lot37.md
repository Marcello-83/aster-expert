# Arbitrage — quai en combi-wall ancré — lot 37, décisions 14, 15 et 16

Décisions de MM énoncées à l'étape 2 du lot 37 (« le lancement de ce lot vaut
validation par MM des décisions de l'étape 2 »). Le texte des champs
`option_retained`, `justification`, `validity_domain`, `discarded_variants` de la
décision 14 et les deux ajouts de domaine de validité (décisions 15 et 16) sont
recopiés à l'identique de l'énoncé du lot 37 ; seules les césures de ligne sont
celles de ce fichier. L'en-tête, les opérations, les libellés `point_label`/`topic`
(ceux des entrées de la fiche) et la mise en forme des variantes écartées
(`*description*`/`*reason*`) sont de la session.

**Statut du document.** Transcrit par Claude. Validé par MM par le lancement du
lot 37.

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : heure de l'enregistrement par la session (MM n'en a écrit aucune) :
  `lot37_enregistrement.json`.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décisions 14 à 16 prises à la
    relecture des résultats du lot 36 (énoncé du lot 37, étape 2)"`
  - `date` : jour de l'enregistrement.

---

## Décision 14 — révisée

- **Opération** : révision d'une entrée tranchée (décision 4)
- `point_label` : `"3"`
- `topic` : `"Choix entre maillage coïncident (liaison rigide directe) et raccord par méthode variationnelle (LIAISON_ELEM/COQ_POU) pour la liaison poutre de couronnement - écran"`

**option_retained**
La poutre de couronnement reste représentée par un élément de poutre sur son
axe, mais avec la formulation qui prend en compte la déformation d'effort
tranchant. L'identifiant de modélisation est à établir par la documentation et
le catalogue.

**justification**
En flexion horizontale, la poutre a une hauteur de 2,50 m pour une portée de
2,60 m entre tubes. Ce rapport, de l'ordre de 1, rend la déformation d'effort
tranchant non négligeable, et l'élément d'Euler-Bernoulli la néglige. L'élément
de poutre reste préféré à une modélisation en coques ou en volume, parce qu'il
fournit directement les efforts N, V, M et T nécessaires au ferraillage selon
l'EN 1992.

**validity_domain**
La poutre sur son axe ne représente pas les effets locaux : zone d'encastrement
des tubes, ancrage du bollard, diffusion sous platine. Ces effets relèvent de
vérifications locales séparées.

**discarded_variants**
1. *description* : poutre en coques ou en éléments volumiques
   *reason* : les efforts de ferraillage devraient être reconstitués par
   intégration de contraintes, le maillage s'alourdit, et la liaison avec les
   tubes pose à nouveau un raccord cinématique.
2. *description* : élément d'Euler-Bernoulli (état actuel)
   *reason* : néglige la déformation d'effort tranchant d'une poutre courte.

---

## Décision 15 — ajout au domaine de validité

- **Opération** : ajout au `validity_domain` d'une entrée tranchée (décision 7) ;
  les autres champs ne sont pas touchés
- `point_label` : `"6"`
- `topic` : `"Phasage construction/excavation/mise en tension des tirants pour un ouvrage de quai"`

**validity_domain (ajout)**
> Les contrôles du lot 35 montrent que, sous les cas G, EAU_P, EAU_A et Q1, la
> pression de réaction des ressorts dépasse la butée limite sur une large part
> de la fiche. Sous Q3 et A, elle reste inférieure à 10 % de la butée limite.
> Le modèle linéaire est donc représentatif pour les effets des charges
> localisées (Q3, A), qui sont son objet (décision 0). Les efforts sous charges
> de terre et d'eau sont à prendre dans le calcul géotechnique amont.

---

## Décision 16 — ajout au domaine de validité

- **Opération** : ajout au `validity_domain` d'une entrée tranchée (décision 5) ;
  les autres champs ne sont pas touchés
- `point_label` : `"4"`
- `topic` : `"Choix entre contact surfacique, ressorts discrets et éléments de joint pour représenter l'interaction sol-écran"`

**validity_domain (ajout)**
> La poussée est appliquée sur la seule moitié terre des tubes, et les ressorts
> sur la seule moitié bassin. La section du tube s'ovalise donc artificiellement,
> jusqu'à 3,5 mm d'écart entre génératrices en pied sous G. Les efforts
> circonférentiels (NYY, MYY) des tubes ne sont pas exploitables pour le
> dimensionnement. Seuls les efforts de flexion d'ensemble du tube, obtenus par
> intégration de NXX sur la section, le sont.
