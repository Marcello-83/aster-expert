# QUAI-CW-TEST-01 — données complémentaires et décision 11

Réponse aux valeurs « à fournir » du lot 25. Toutes les valeurs sont **inventées**
pour le test.

Le document a deux parties :

- **Partie A** : des données du cas de test. Elles complètent
  `cas_test_quai_combiwall_v2.md`, au même titre que le delta v3. Leur source est
  une section du cas de test.
- **Partie B** : une décision pratique nouvelle, au point `"10"`.

**Statut.** Rédigé par Claude, validé intégralement par MM (partie A et
partie B), sans réserve.

---

## Partie A — Données du cas de test

### A.1 Matériaux (complète §2, §3 et §4)

| Élément | E (MPa) | ν | ρ (kg/m³) |
|---|---|---|---|
| Tubes (S355) | 210 000 | 0,30 | 7 850 |
| Palplanches (S355) | 210 000 | 0,30 | 7 850 |
| Poutre de couronnement (C35/45) | 34 000 | 0,20 | 2 500 |
| Barres d'ancrage (500/700) | 210 000 | 0,30 | 7 850 |

### A.2 Pesanteur

g = 9,81 m/s², dirigée selon −Z.

### A.3 Position de la poutre de couronnement (complète §3)

La face avant (côté bassin) de la poutre est à 0,20 m en avant de la face bassin
des tubes. Dans le repère du point 9 :

- face avant en Y = −0,91 ;
- face arrière en Y = +1,59 ;
- axe en Y = +0,34 et Z = +3,30.

### A.4 Profils de poussée des terres (point 5)

Ces profils sont fictifs. Ils remplacent un calcul géotechnique amont, sont
établis par Claude selon Rankine (poussée active, sans frottement sol-écran, avec
cohésion), et ne sont représentatifs d'aucun calcul K-Réa.

Conventions :

- la pression est normale à l'écran, côté terre, en kPa, et varie linéairement
  entre les points du tableau ;
- une double valeur à une même cote signale une discontinuité à l'interface de
  deux couches ;
- le profil est appliqué de +4,00 au pied des profils ;
- Q1 est représentée par une surcharge uniforme de 40 kPa sur tout le
  terre-plein, ce qui simplifie les deux bandes du §7.

| Z (m CM) | G, poussée des terres (kPa) | Q1, incrément dû à la surcharge (kPa) |
|---|---|---|
| +4,00 | 0,0 | 12,3 |
| +2,00 | 11,7 | 12,3 |
| −2,00 (remblai) | 24,0 | 12,3 |
| −2,00 (sable) | 21,2 | 10,8 |
| −9,00 (sable) | 41,1 | 10,8 |
| −9,00 (argile) | 42,4 | 16,2 |
| −18,00 (argile) | 80,8 | 16,2 |
| −18,00 (marne) | 35,8 | 13,3 |
| −26,00 | 66,5 | 13,3 |

### A.5 Pression d'eau différentielle nette (point 5)

La pression est normale à l'écran, côté terre, et le régime est hydrostatique de
part et d'autre, sans écoulement.

| Situation | Nappe terre | Niveau bassin | Profil net |
|---|---|---|---|
| Permanente | +2,00 | +0,50 | 0 à +2,00, croissant linéairement jusqu'à 15 kPa à +0,50, constant en dessous |
| Accidentelle | +3,00 | −0,50 | 0 à +3,00, croissant linéairement jusqu'à 35 kPa à −0,50, constant en dessous |

En situation accidentelle, les profils de poussée des terres de A.4 sont conservés
tels quels : seule l'eau change.

---

## Partie B — Décision 11 (point neuf)

- **Opération** : `insert_practice_entry`
- `point_label` : `"10"`
- `topic` : `"Détails de représentation géométrique et discrétisation"`
- `decided_by` : `"MM"`
- `decided_at` : heure d'enregistrement
- `sources` : `decision_ingenieur`, avec la référence `"MM, cas de test
  QUAI-CW-TEST-01, données complémentaires prises en séance de travail"`, datée du
  jour d'enregistrement.

**option_retained**

| Sujet | Retenu |
|---|---|
| Tête des tubes | Tubes maillés jusqu'à la sous-face de la poutre (+2,60). Anneau `TETE_TUBE_xx` à +2,60, relié par liaison de corps solide au nœud de l'axe de la poutre de même X. |
| Tête des palplanches | Palplanches maillées jusqu'à +2,60, bord supérieur libre. |
| Épaisseur de coque des tubes | 14 mm sur toute la circonférence, soit 16 mm moins 2 mm de corrosion. |
| Accrochage des tirants | Nœud du tube sur la génératrice côté terre (Y = +0,71), à +2,50. Direction du tirant : dans le plan YZ, vers +Y, descendante de 20°. Extrémité `ANC_xx` à Y = +25,14, Z = −6,39. |
| Surface de poussée | `ECRAN_POUSSEE` regroupe les facettes des tubes situées côté terre (Y ≥ 0) et les palplanches. Au-dessous de −18,00, seuls les tubes la reçoivent. |
| Facettisation des tubes | 40 facettes sur la circonférence (9°). Des génératrices tombent donc exactement en Y = 0 (serrures) et à ±45° de la génératrice côté bassin (empreinte `DEFENSE`). |
| Taille verticale des mailles | 0,25 m visé. Des nœuds sont imposés aux cotes −26,00 ; −18,00 ; −12,00 ; +1,00 ; +2,00 ; +2,50 ; +2,60. |
| Palplanches, sens horizontal | 5 mailles par intervalle de 1,18 m. |
| Poutre de couronnement | Éléments de poutre, 8 par entraxe, avec un nœud au droit de chaque tube (X = 0 compris, pour `BOLLARD`). |
| Tirants | Un élément de barre par tirant. |

**justification**
Le tube encastré dans le béton n'a pas de comportement de coque propre. Couper sa
représentation à la sous-face de la poutre, et reporter l'encastrement par la
liaison de corps solide de la décision du point 3, évite de mailler une coque
fictive noyée dans la poutre. Une épaisseur uniforme de 14 mm applique la
corrosion donnée par le cas de test sans découper le tube en deux demi-coques.
Le nombre de facettes est choisi pour que les lignes géométriques imposées par
les décisions — serrures et empreinte de défense — tombent sur des génératrices :
les groupes sont alors exacts sans projection. Les cotes imposées portent les
interfaces de strates, les limites de ressorts et les points d'application de
charge.

**validity_domain**

- L'épaisseur uniforme de 14 mm sous-estime la raideur côté terre, où il n'y a
  pas de corrosion.
- Le bord libre des palplanches en tête ignore leur encastrement réel dans la
  poutre.
- L'accrochage du tirant en un seul nœud crée une singularité locale de
  contrainte : les contraintes du tube autour de ce nœud ne sont pas
  exploitables.
- La taille de maille (0,25 m, 40 facettes) n'a fait l'objet d'aucune étude de
  convergence.

**discarded_variants**
1. *description* : Tube maillé jusqu'à son sommet réel (+3,40) dans le volume de
   la poutre.
   *reason* : Coque fictive noyée dans le béton, sans comportement propre.
2. *description* : 16 mm côté terre et 14 mm côté bassin.
   *reason* : Découpe le tube en deux groupes de coques pour un effet sans objet
   dans ce test.
3. *description* : 36 facettes (10°).
   *reason* : Ne place pas de génératrice à ±45°, limite de l'empreinte de défense.
