# Arbitrage des entrées pratique — quai en combi-wall ancré — v4

Révision de trois décisions de **MM** enregistrées aux lots 18 et 19, au format
du gabarit `gabarit_saisie_fiche_hypotheses.md` (lot 17). Cas de test fictif :
`QUAI-CW-TEST-01`, données selon `cas_test_quai_combiwall_v3.md`.

**Statut du document.** Rédigé par Claude à partir des résultats des lots 20
et 21 et des indications de MM. Les passages marqués **[À CONFIRMER MM]** doivent
être validés, corrigés ou supprimés par MM avant transmission. Une fois
transmis, le document vaut décision de MM.

## Ce qui change par rapport à v3

| Décision | point_label | Nature du changement |
|---|---|---|
| 2 | 1 | révisée : palplanche en plaque orthotrope, rigidités données directement |
| 8 | 7 | révisée : demi-tubes aux faces de symétrie, rendu explicite |
| 9 | 8 | révisée : intensité d'accostage rapportée à la surface développée, empreinte angulaire définie |

La décision du point 1 sur le tube (DKT, lot 21) est inchangée.

## Conventions communes

- `decided_by` : `"MM"`
- `decided_at` : `2026-09-22T18:00:00` (heure conventionnelle, déclarée dans la
  référence).
- Source `decision_ingenieur`, présente sur les trois décisions :
  - `origin` : `"decision_ingenieur"`
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, révision v4 prise en séance
    de travail ; heure de decided_at conventionnelle"`
  - `date` : `2026-09-22`
- Rattachement par `point_label` + `topic`, recopiés à l'identique des versions
  précédentes.

---

## Décision 2 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"1"`
- `topic` : `"Homogénéisation ou représentation distincte du tube métallique et de la palplanche intercalaire"`

**option_retained**
Tube et palplanche intercalaire représentés distinctement. Le tube est en coque
DKT à sa géométrie réelle (décision du point 1). La palplanche intercalaire est
une coque plane DKT placée dans le plan des serrures, qui partage ses nœuds avec
les tubes sur les lignes de serrure. Son comportement est une plaque élastique
orthotrope. Ses rigidités par mètre de largeur de la surface plane sont données
directement, sans épaisseur ni module équivalents. Axe L vertical, axe T
horizontal dans le plan de l'écran.

Géométrie de profil retenue (cas de test v3) : ondulation trapézoïdale de période
1,18 m, hauteur 0,45 m, semelles de 0,35 m, épaisseur 9,5 mm, acier
E = 210 000 MPa, ν = 0,3. Longueur développée sur une période :
s = 1,720 m, soit s/b = 1,458.

| Rigidité | Formule | Valeur |
|---|---|---|
| Membrane verticale | E·t·(s/b) | 2 908 MN/m |
| Membrane horizontale | D/h², avec D = E·t³/[12(1−ν²)] | 0,081 MN/m  |
| Cisaillement de membrane | G·t·(b/s) | 526 MN/m |
| Flexion verticale | E·I du profil par mètre | 89,0 MN·m²/m |
| Flexion horizontale | D·(b/s) | 0,0113 MN·m²/m |
| Torsion de plaque | G·t³/12·(s/b) | 0,0084 MN·m²/m |
| Couplages de Poisson, membrane-flexion | — | nuls |

Le poids propre de la palplanche n'est pas porté par le matériau. Il est
appliqué comme force surfacique verticale explicite sur la surface plane :
7 850 × 9,81 × t × (s/b) ≈ 1,07 kN/m².

**justification**
Un profil en Z est raide en flexion verticale et presque sans raideur en flexion
horizontale : il se déforme en accordéon. Le rapport entre les deux flexions
dépasse 7 000. Une coque isotrope d'épaisseur équivalente ne peut pas reproduire
ce rapport, alors que c'est précisément lui qui gouverne le report de la poussée
vers les tubes, c'est-à-dire la répartition des efforts que ce calcul doit
fournir. Le constat Code_Aster du lot 20 établit qu'une plaque DKT accepte des
rigidités de membrane et de flexion données séparément dans deux directions, ce
qui dispense de toute théorie d'homogénéisation pour les termes principaux. Les
rigidités verticales se calculent exactement à partir du profil. La flexion
horizontale suit la formule usuelle des tôles ondulées. Le poids propre est
appliqué explicitement parce que la prise en compte de la masse surfacique du
matériau sous pesanteur en statique n'est pas établie (lot 21).

**validity_domain**
1. La raideur de membrane horizontale est un ordre de grandeur : elle résulte de
   la flexion des plis, et son coefficient de forme n'est pas établi. Une étude
   de sensibilité à ×10 et ÷10 de cette raideur est requise. Si la répartition
   tube/palplanche en dépend sensiblement, la décision doit être revue vers la
   géométrie réelle.
2. Le cisaillement de membrane néglige le gauchissement du profil ; il est donc
   surestimé.
3. La palplanche est représentée dans le plan des serrures : l'excentricité réelle
   du profil par rapport à ce plan n'est pas représentée.
4. Les contraintes dans la palplanche ne sont pas données directement. Elles se
   déduisent des efforts généralisés avec les caractéristiques du profil réel.
5. Le partage de nœuds surestime la continuité de flexion des serrures.

**discarded_variants**
1. *description* : Coque plane isotrope d'épaisseur équivalente calée sur le
   module de flexion (décision v2).
   *reason* : Ne reproduit ni l'inertie verticale ni l'orthotropie ; la raideur
   horizontale est fausse d'environ trois ordres de grandeur.
2. *description* : Géométrie réelle du Z maillée en coques minces de 9,5 mm.
   *reason* : Fidèle, mais alourdit sensiblement la branche maillage. Elle reste
   la variante de repli si l'étude de sensibilité invalide la représentation
   orthotrope.
3. *description* : Loi orthotrope par modules et épaisseur communs, associée à
   la définition d'un composite.
   *reason* : Une épaisseur commune ne permet pas d'imposer séparément les
   raideurs de flexion verticale et horizontale (lot 20, critère C3).
4. *description* : Homogénéisation en une plaque équivalente unique pour tubes et
   palplanches.
   *reason* : Perd la répartition des efforts entre les deux profils.

---

## Décision 8 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"7"`
- `topic` : `"Position et blocages des limites latérales/inférieures d'un modèle de sol stratifié semi-infini"`

**option_retained**
Le point tel que formulé devient sans objet du fait de la décision du point 4 :
le sol n'étant pas maillé, il n'existe ni bord latéral ni fond de modèle. La
décision porte sur l'étendue de la tranche et ses faces de coupe.

La tranche représentative fait 20,80 m, soit huit entraxes de tube. Ses deux
faces de coupe sont des plans de symétrie passant par l'axe des tubes 1 et 9.
Les tubes 1 et 9 sont donc des demi-tubes. Leurs tirants, situés dans les plans
de symétrie, ont une demi-section, et leurs ressorts de sol ne comptent que la
largeur projetée située dans la tranche. La tranche comporte ainsi sept tubes
entiers, deux demi-tubes et huit palplanches intercalaires. Le bollard
d'amarrage et la défense d'accostage sont au droit du tube central, `TUBE_05`.
Les conditions de symétrie s'appliquent aux deux faces de coupe. La composante
hors plan de 15° de l'effort d'amarrage est supprimée pour ce cas de test.

**justification**
Bollards et défenses se répètent tous les huit tubes. La cellule répétitive de
l'ouvrage va donc de l'axe d'un tube à l'axe du huitième suivant. Des tubes
entiers aux deux faces compteraient deux fois le tube partagé avec la tranche
voisine. Le demi-tube, la demi-section de tirant et la demi-largeur de ressort
aux faces sont la traduction exacte de la symétrie.

**validity_domain**
La symétrie impose un chargement symétrique. Tout cas de charge dissymétrique —
amarrage oblique réel, accostage hors de l'axe du tube central — sort du domaine
de validité et demanderait une tranche allongée. La symétrie des résultats par
rapport à l'axe de `TUBE_05` est un contrôle de niveau D.

**discarded_variants**
1. *description* : Neuf tubes entiers entre les faces de coupe.
   *reason* : Compte deux fois les tubes des faces ; la raideur et les charges de
   la tranche sont surestimées d'un tube.
2. *description* : Demi-tranche de 10,40 m, avec symétrie supplémentaire dans
   l'axe de `TUBE_05`.
   *reason* : Divise le modèle par deux, mais demande de répartir sur demi-tube
   les charges de bollard et de défense, et supprime le contrôle de symétrie des
   résultats.
3. *description* : Tranche de 41,60 m, composante hors plan conservée.
   *reason* : Plus fidèle, mais quadruple le modèle pour un cas de test.

---

## Décision 9 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"8"`
- `topic` : `"Application des charges localisées d'amarrage et d'accostage"`

**option_retained**
Les seules charges localisées du modèle sont l'amarrage (Q3) et l'accostage (A).
Aucune charge de grue : la voie de grue est un ouvrage distinct, fondé sur pieux,
sans interaction avec l'écran.

*Amarrage.* Effort de 1 000 kN incliné de 30° au-dessus de l'horizontale, dans le
plan perpendiculaire au quai, dirigé vers le bassin. Appliqué comme force nodale
au nœud `BOLLARD`, sur l'axe de la poutre de couronnement (cote +3,30) au droit
de `TUBE_05`, avec le moment de transport dû au décalage vertical de 0,70 m :
M = 866 kN × 0,70 m ≈ 606 kN·m, d'axe parallèle au quai. Le bollard est supposé
sur l'axe de la poutre en plan.

*Accostage.* Effort horizontal de 800 kN, perpendiculaire au quai, dirigé vers la
terre. La défense n'est pas modélisée. Sa réaction est répartie uniformément sur
l'empreinte `DEFENSE`, formée des facettes de `TUBE_05` comprises entre +1,00 et
+2,00 et à ±45° de la génératrice tournée vers le bassin. Cela correspond à une
platine de fixation d'environ 1,00 m de large. La charge est
une force surfacique de direction fixe dans le repère global. Son intensité est
calculée par le générateur à partir de la surface développée réelle des mailles
de l'empreinte : q = 800 kN / Σ A_mailles. La valeur est d'environ 717 kN/m²
pour une empreinte cylindrique idéale de 1,115 m².

**justification**
La réaction de la défense est une donnée établie en amont par le choix de la
défense ; seule compte, pour la structure, la façon dont elle entre dans
l'écran. L'essai d'exécution du lot 21 établit que l'intensité d'une force
surfacique sur coque se rapporte à la surface développée des mailles, avec un
écart de 0,0001 % sur la résultante. Calculer l'intensité sur la surface
développée des mailles effectivement générées garantit donc une résultante
exacte de 800 kN, quel que soit le nombre de facettes. L'empreinte angulaire
représente une platine plane sur un tube courbe, plutôt que la demi-circonférence
entière. Pour l'amarrage, le moment de transport restitue l'excentricité du point
d'application par rapport à l'axe de la poutre.

**validity_domain**
Les dimensions de l'empreinte sont inventées. Les contraintes locales du tube sous
l'empreinte y sont sensibles et demandent un maillage raffiné dans cette zone. La
répartition uniforme ne représente pas la distribution réelle de contact d'une
platine. Le moment de transport suppose la section de la poutre indéformable.
L'excentricité en plan du bollard n'est pas représentée.

**discarded_variants**
1. *description* : Intensité rapportée à la surface projetée,
   800 / (1,00 × 1,42) ≈ 563 kN/m² (décision v3).
   *reason* : L'essai du lot 21 montre que la force surfacique sur coque se
   rapporte à la surface développée ; la résultante aurait été fausse.
2. *description* : Empreinte sur toute la demi-circonférence tournée vers le
   bassin.
   *reason* : Ne correspond à aucune platine réelle et étale la charge sur toute
   la largeur du tube.
3. *description* : Défense modélisée en éléments de coque.
   *reason* : Le comportement d'une défense en élastomère n'est pas celui d'une
   coque élastique, et sa réaction est déjà une donnée.
4. *description* : Force ponctuelle nodale pour l'accostage.
   *reason* : Singularité locale dans les coques.
