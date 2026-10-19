# Enregistrement des décisions P62 à P66 de MM — projet `pontons_alu_01` (lot 52)

Décisions de la consigne du lot 52 (MM, 16/10/2026), enregistrées par `aster-expert fiche
enregistrer`. P64 révise P53 (plan des montants et des diagonales) et P65 révise P54 (cote de l'axe) :
P53 et P54 sont ré-arbitrées (l'ancienne décision va dans l'historique). Les textes sont extraits de
la source par script (jamais retapés) ; la vérification exige qu'ils y figurent à l'identique.

Source du texte : donnees/sources/consigne_lot52.md
Enregistré le : 2026-10-19T09:00:00-04:00
Domaine de validité par défaut : Calcul linéaire du ponton intégral de PONTONS-ALU-01, géométrie PRO (lot 52), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P53 — Cotes de l'AVP

> **P64 — Treillis horizontal constructible.**
>
> 1. **Montants et diagonales sous les pannes.** Le dessus des montants et des
>    diagonales est au niveau de la sous-face des pannes, soit +1,35 pour des
>    pannes de 50.
>    - Axe des montants et des diagonales 120 × 120 à **+1,29**.
>    - Montants soudés sur le flanc des poutres principales (axe +1,30). Dans le
>      modèle, ils sont reliés aux nœuds des poutres par une liaison rigide de
>      0,01 m.
>    - Les pannes posent sur les montants et sur les diagonales. Elles y sont
>      reliées par une liaison rigide de 1,375 − 1,29 = 0,085 m.
>    - Aucune barre ne pénètre dans une autre.

- Écartée : Montants et diagonales dans le plan des poutres principales (P53, lot 51 ter : axe +1,30) — barres qui pénètrent les pannes ; montants et diagonales 120 × 120 sous les pannes, axe +1,29 (P64)
- Note : Ré-arbitrage : les autres cotes de P53 sont inchangées (dessus +1,40, poutres +1,30, pannes 50 × 50 +1,375, anneau +0,69 à +1,09) ; seul le plan des montants et des diagonales change (P64). L'ancienne décision reste dans l'historique de la fiche.

### P54 — Appui articulé compact

> **P65 — Appui articulé : principe P44/P54 conservé** (schéma
> `schema_appui_articule_v4`).
>
> - Une oreille par travée, sous le tube, portée par un étrier en T en inox
>   duplex fixé sous la poutre par boulons aveugles : aucune soudure sur la
>   poutre.
> - Les deux oreilles sont côte à côte sur un axe Ø 24 commun, placé à
>   **+1,175** au lieu de +1,16.
> - Dans le modèle, le point de l'axe passe à Z = +1,175. Les liaisons sont
>   inchangées :
>   - oreilles liées en translation et en DRX ;
>   - Z bloqué ;
>   - Y bloqué côté YP ;
>   - X libre.

- Écartée : Axe d'appui à +1,16 NGF (P54, lot 51 ter) — axe Ø 24 commun aux deux oreilles placé à +1,175 (schéma v4, P65)
- Note : Ré-arbitrage : la modélisation de P54 est conservée (LIAISON_DDL au point de l'axe), seul Z du point de l'axe passe à +1,175 (P65).

### P62 — Houle dans le critère de flèche

> **P62 — La houle reste dans le critère de flèche.** HU, HD et HU_IMP entrent
> dans l'ELS caractéristique. La proposition d'exclusion du superviseur est
> refusée. Les critères P37/P51 sont inchangés.

- Écartée : Exclusion de HU, HD et HU_IMP de l'ELS caractéristique pour la flèche (proposition du superviseur) — refusée par MM (P62)
- Note : Critères P37 et P51 inchangés ; l'enveloppe de flèche de l'ELS caractéristique garde HU, HD et HU_IMP_Mk.

### P63 — Sections retenues

> **P63 — Sections retenues.**
>
> - Poutres principales : 200 × 200 × 12, comme la variante 12 du lot 51 quater.
> - Pannes allégées : **50 × 50 × 5**. Sensibilité en 50 × 50 × 4.
> - Montants et diagonales : **120 × 120 × 6**, 6082-T6.
>   - Justification : la zone adoucie sur la poutre principale au droit d'un
>     montant mesure 120 + 2 × 30 = 180 mm, ce qui reste sous la largeur de
>     200 mm de la poutre.
>   - 30 mm est le bhaz de l'EN 1999-1-1, 6.1.6.3, pour une épaisseur moyenne de
>     9 mm.

- Écartée : Montants et diagonales 150 × 150 × 7 (lots 50 à 51 quater) — 120 × 120 × 6 en 6082-T6, zone adoucie de 180 mm sous la largeur de 200 mm de la poutre (P63)
- Écartée : Pannes 60 × 60 × 5 (variantes 12 du lot 51 ter) — pannes allégées 50 × 50 × 5, sensibilité 50 × 50 × 4 (P63)
- Note : Variantes B52, A52 (pannes 50 × 50 × 5) et B52P4 (sensibilité 50 × 50 × 4) dans variantes_lot52.yaml.

### P64 — Treillis horizontal constructible

> **P64 — Treillis horizontal constructible.**
>
> 1. **Montants et diagonales sous les pannes.** Le dessus des montants et des
>    diagonales est au niveau de la sous-face des pannes, soit +1,35 pour des
>    pannes de 50.
>    - Axe des montants et des diagonales 120 × 120 à **+1,29**.
>    - Montants soudés sur le flanc des poutres principales (axe +1,30). Dans le
>      modèle, ils sont reliés aux nœuds des poutres par une liaison rigide de
>      0,01 m.
>    - Les pannes posent sur les montants et sur les diagonales. Elles y sont
>      reliées par une liaison rigide de 1,375 − 1,29 = 0,085 m.
>    - Aucune barre ne pénètre dans une autre.
> 2. **Diagonales soudées sur les montants, plus sur les poutres principales.**
>    - Le nœud diagonale–montant est sur l'axe du montant, à **e = 0,25 m de l'axe
>      de la poutre principale**, soit |Y| = 0,68.
>    - Le dessin en N du treillis est conservé : chaque diagonale relie le nœud
>      à Y = +0,68 d'un montant au nœud à Y = −0,68 du montant suivant (même sens
>      de diagonale qu'aujourd'hui).
>    - Le tronçon de montant entre la poutre et ce nœud travaille en flexion :
>      c'est voulu, il faut l'exporter.
>    - Paramètre `e_diag` dans le yaml.
> 3. Positions en X des montants inchangées. Le découpage des pannes aux
>    croisements suit la nouvelle géométrie.

- Écartée : Diagonales soudées sur les poutres principales, dans leur plan (lots 50 à 51 quater) — diagonales soudées sur les montants à e = 0,25 m de l'axe des poutres, sous les pannes (P64)
- Note : Paramètre e_diag (variantes_lot52.yaml, E_DIAG du script de maillage) ; axe des montants et des diagonales = dessus des poutres − cote des pannes − cote des montants / 2 = +1,29 ; liaisons rigides LIAISON_SOLIDE de 0,01 m (montant / poutre) et 0,085 m (panne / montant ou diagonale).

### P65 — Appui articulé, schéma v4

> **P65 — Appui articulé : principe P44/P54 conservé** (schéma
> `schema_appui_articule_v4`).
>
> - Une oreille par travée, sous le tube, portée par un étrier en T en inox
>   duplex fixé sous la poutre par boulons aveugles : aucune soudure sur la
>   poutre.
> - Les deux oreilles sont côte à côte sur un axe Ø 24 commun, placé à
>   **+1,175** au lieu de +1,16.
> - Dans le modèle, le point de l'axe passe à Z = +1,175. Les liaisons sont
>   inchangées :
>   - oreilles liées en translation et en DRX ;
>   - Z bloqué ;
>   - Y bloqué côté YP ;
>   - X libre.

- Écartée : Étrier soudé sous la poutre — étrier en T en inox duplex fixé par boulons aveugles, aucune soudure sur la poutre (P65)
- Note : Schéma de principe donnees/sources/schema_appui_articule_v4.pdf (copie du partage, MM). Modèle : point de l'axe à Z = +1,175, liaisons de P54 inchangées.

### P66 — Défenses

> **P66 — Défenses.** Défenses Delta continues en caoutchouc, frottement μ = 0,7,
> inchangé. Le frontal PEHD est abandonné.

- Écartée : Frontal PEHD — abandonné (P66)
- Note : Frottement μ = 0,7 inchangé : l'effort tangentiel d'accostage (P32) et les cas unitaires sont inchangés.
