# Arbitrage — quai en combi-wall ancré — v5, décision 2 seule

Révision de la décision 2 (point 1) après les lots 22 et 23. Elle remplace la
rédaction v4 de la décision 2, qui n'a jamais été enregistrée. Les autres
décisions ne sont pas touchées.

**Statut du document.** Rédigé par Claude. Validé par MM.

## Conventions

- `decided_by` : `"MM"`
- `decided_at` : date et heure de transmission par MM, à renseigner par la
  session au moment de l'enregistrement si MM ne l'a pas écrite ci-dessous.
- Source `decision_ingenieur` :
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, révision v5 de la décision
    2 prise en séance de travail"`
  - `date` : même jour que `decided_at`.

---

## Décision 2 — révisée

- **Opération** : révision d'une entrée en révision, qui clôt la révision
- `point_label` : `"1"`
- `topic` : `"Homogénéisation ou représentation distincte du tube métallique et de la palplanche intercalaire"`

**option_retained**
Tube et palplanche intercalaire représentés distinctement. Le tube est en coque
DKT à sa géométrie réelle (décision du point 1). La palplanche intercalaire est
une coque plane DKT placée dans le plan des serrures, qui partage ses nœuds avec
les tubes sur les lignes de serrure. Son comportement est une plaque élastique
orthotrope dont les rigidités par mètre de largeur de la surface plane sont
données directement. Axe L vertical, axe T horizontal dans le plan de l'écran.

Géométrie de profil (cas de test v3) : ondulation trapézoïdale de période
1,18 m, hauteur 0,45 m, semelles de 0,35 m, épaisseur 9,5 mm, acier
E = 210 000 MPa, ν = 0,3, G = 80 770 MPa. Longueur développée par période :
s = 1,720 m, soit s/b = 1,458.

| Rigidité | Formule | Valeur |
|---|---|---|
| Membrane verticale | E·t·(s/b) | 2 908 MN/m |
| Membrane horizontale | D/h², avec D = E·t³/[12(1−ν²)] | 0,081 MN/m |
| Cisaillement de membrane | G·t·(b/s) | 526 MN/m |
| Flexion verticale | E·I du profil par mètre | 89,0 MN·m²/m |
| Flexion horizontale | D·(b/s) | 0,0113 MN·m²/m |
| Torsion de plaque | G·t³/12·(s/b) | 0,0084 MN·m²/m |
| Couplages de Poisson, membrane-flexion | — | nuls |
| Cisaillement transverse | G·t·(b/s), sans effet en DKT | 526 MN/m |

*Poids propre.* Il est porté par le matériau : masse volumique
ρ = 7 850 kg/m³ et épaisseur de coque déclarée `EPAIS` = t·(s/b) = 13,85 mm, soit
ρ·EPAIS ≈ 108,7 kg/m², la masse surfacique du profil rapportée au plan de
l'écran. Aucune force surfacique de poids propre n'est ajoutée.

*Règles d'exploitation.*

- Les efforts dans la palplanche sont lus **uniquement** dans les efforts
  généralisés aux nœuds (`EFGE_NOEU`) ou aux éléments.
- Les contraintes dans le profil sont calculées hors Code_Aster, à partir de ces
  efforts et des caractéristiques du profil réel.
- Les contraintes, forces nodales et réactions calculées par Code_Aster sur les
  éléments de palplanche ne sont pas utilisées.
- Les contrôles d'équilibre utilisent les efforts dans les ressorts discrets et
  les réactions aux nœuds qui ne portent aucun élément de palplanche.

**justification**
Un profil en Z est raide en flexion verticale et presque sans raideur en flexion
horizontale : il se déforme en accordéon, avec un rapport de plus de 7 000 entre
les deux. Ce rapport gouverne le report de la poussée vers les tubes, donc la
répartition des efforts que ce calcul doit fournir. Une coque isotrope ne peut
pas le reproduire. Une plaque DKT accepte des rigidités données séparément dans
les deux directions (lot 20). Leur convention, rigidité par unité de largeur
dans le repère utilisateur, est établie par essai (lot 22, niveau D).

Les essais du lot 23 établissent que les déplacements et les efforts
généralisés sont exacts, indépendants de l'épaisseur déclarée et des
coefficients de cisaillement transverse. En revanche, les contraintes, les
forces nodales et les réactions sont calculées avec une rigidité de flexion
reconstruite à partir de la membrane et de l'épaisseur. Elles sont donc fausses
pour une plaque dont la flexion n'est pas celle d'une plaque pleine homogène,
ce qui est le cas de ce profil. D'où les règles d'exploitation. L'épaisseur
déclarée n'ayant pas d'effet sur la raideur, elle est choisie pour que le poids
propre soit exact : la pesanteur exige une masse volumique sur tous ces éléments
et la multiplie par l'épaisseur (lot 22).

**validity_domain**
1. La membrane horizontale est un ordre de grandeur, issu de la flexion des plis,
   dont le coefficient de forme n'est pas établi. Une étude de sensibilité à ×10
   et ÷10 est requise. Si la répartition tube/palplanche en dépend sensiblement,
   la décision doit être revue vers la géométrie réelle.
2. Le cisaillement de membrane néglige le gauchissement du profil ; il est donc
   surestimé.
3. La palplanche est représentée dans le plan des serrures : l'excentricité réelle
   du profil par rapport à ce plan n'est pas représentée.
4. L'exactitude des efforts généralisés est établie en flexion uniaxiale sur
   quadrangles. Les autres composantes utilisées — membrane, flexion
   horizontale, torsion — relèvent de l'essai du lot 24.
5. Le partage de nœuds surestime la continuité de flexion des serrures.
6. Les réactions des nœuds de serrure et de la palplanche ne sont pas
   exploitables (lot 23).

**discarded_variants**
1. *description* : Coque isotrope d'épaisseur équivalente calée sur le module de
   flexion (décision v2).
   *reason* : Ne reproduit ni l'inertie verticale ni l'orthotropie ; la raideur
   horizontale est fausse d'environ trois ordres de grandeur.
2. *description* : Géométrie réelle du Z maillée en coques minces de 9,5 mm, en
   acier isotrope.
   *reason* : Fidèle, sans restriction de post-traitement, mais alourdit
   sensiblement la branche maillage. C'est la variante de repli si l'essai du
   lot 24 ou l'étude de sensibilité invalident la représentation orthotrope.
3. *description* : Loi orthotrope par modules et épaisseur communs.
   *reason* : Ne permet pas d'imposer séparément les deux flexions (lot 20).
4. *description* : Poids propre appliqué par force surfacique explicite, sans
   masse volumique (rédaction v4).
   *reason* : Non exécutable : la pesanteur exige une masse volumique sur ces
   éléments. Une masse volumique nulle est acceptée en silence (lot 23), mais le
   poids disparaîtrait alors sans signal si la force explicite était omise.
5. *description* : Homogénéisation en une plaque unique pour tubes et
   palplanches.
   *reason* : Perd la répartition des efforts entre les deux profils.
