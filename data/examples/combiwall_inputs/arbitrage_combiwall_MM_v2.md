# Arbitrage des entrées pratique — quai en combi-wall ancré — v2

Resoumission des décisions de **MM** au format du gabarit
`gabarit_saisie_fiche_hypotheses.md` (lot 17). Les décisions sont inchangées par
rapport à `arbitrage_combiwall_MM.md` ; seule leur mise en forme change, et un
champ `justification` distinct est désormais rédigé pour chacune.

Cas de test fictif : `QUAI-CW-TEST-01`.

## Conventions communes aux neuf décisions

- `decided_by` : `"MM"`
- `decided_at` : `2026-09-18T18:00:00` — heure conventionnelle, l'horodatage
  exact de la décision n'ayant pas été relevé. La convention est déclarée dans
  `sources[0].reference`.
- `sources` : un unique élément
  - `origin` : `"decision_ingenieur"`
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, décision de test prise en
    séance de travail ; heure de decided_at conventionnelle"`
  - `date` : `2026-09-18`
- Rattachement : par `point_label` + `topic`, recopiés de la fiche. Les `topic`
  ci-dessous sont repris des intitulés de la fiche de décision du lot 15 ; ils
  doivent être confrontés à `HypothesesSheet.entries` avant enregistrement.

---

## Décision 0 — point neuf

- **Opération** : `insert_practice_entry` (absent de la fiche)
- `point_label` : `"0"`
- `topic` : `"Objet et périmètre du calcul"`

**option_retained**
Le modèle Code_Aster est un calcul de structure tridimensionnel. Il ne
dimensionne pas géotechniquement l'écran : cette part relève d'un logiciel dédié
aux écrans de soutènement, qui fournit en amont les profils de poussée et les
raideurs de réaction du sol. Ce modèle traite la diffusion d'un effort d'amarrage
ponctuel dans l'écran, la répartition des efforts entre tubes et palplanches
intercalaires, le travail de la poutre de couronnement en flexion horizontale et
en torsion, et les effets tridimensionnels qu'un calcul en tranche
bidimensionnelle ne capte pas. Il ne traite pas la stabilité d'ensemble, la
vérification de la fiche, l'équilibre des poussées et butées, ni le
dimensionnement géotechnique des tirants.

**justification**
La vérification géotechnique d'un écran — équilibre poussée-butée, fiche,
stabilité — est couverte en agence par un logiciel dédié (K-Réa), qui porte la
démarche propre à ce type d'ouvrage. Ce que ce logiciel ne fournit pas, c'est la
réponse tridimensionnelle de la structure sous charges localisées. C'est ce
besoin, et lui seul, qui justifie un modèle Code_Aster ; lui donner un périmètre
plus large reviendrait à dupliquer un calcul existant avec un outil moins adapté.

**validity_domain**
La validité de ce calcul dépend entièrement de la qualité des données fournies en
amont — profils de poussée et raideurs de sol — qu'il ne vérifie pas. Il ne peut
servir ni à justifier la fiche, ni à justifier la stabilité de l'écran.

**discarded_variants**
1. *description* : Calcul géotechnique complet sous Code_Aster.
   *reason* : Un logiciel dédié le fait mieux et c'est sa place ; reproduire sa
   démarche ici n'apporterait rien et demanderait de mailler le sol.

---

## Décision 1

- **Opération** : `apply_decision` (entrée existante non tranchée)
- `point_label` : `"1"`
- `topic` : `"Choix de la famille d'éléments (coque, poutre ou massif) pour le tube métallique + palplanche intercalaire"`

**option_retained**
Modélisation tridimensionnelle par éléments de coque, sur une tranche
représentative d'ouvrage et non sur les 120 m réels. Le choix de la
modélisation de coque précise relève de la moitié Code_Aster de la fiche ; la
présente décision porte sur la stratégie, pas sur l'identifiant.

**justification**
Les charges qui motivent ce calcul — amarrage, accostage, galets de grue — sont
ponctuelles et espacées le long du quai. Seul un modèle tridimensionnel
représente leur diffusion dans l'écran et dans la poutre de couronnement. Le
comportement en tranche courante, lui, est déjà couvert par le calcul
géotechnique amont. L'écran étant un élément mince devant sa hauteur et sa
longueur, une représentation surfacique en rend compte sans surcoût de maillage.

**validity_domain**
Les efforts sont obtenus en efforts généralisés de coque et demandent un
post-traitement pour être exploités en dimensionnement, là où une modélisation
poutre les fournirait directement.

**discarded_variants**
1. *description* : Poutre par mètre linéaire, calcul en tranche bidimensionnelle.
   *reason* : Ne sait pas traiter les charges ponctuelles d'amarrage,
   d'accostage et de grue, qui sont précisément l'objet du calcul.
2. *description* : Massif continu tridimensionnel.
   *reason* : Disproportionné pour un écran mince ; contredit le critère
   d'élancement.

---

## Décision 2

- **Opération** : `apply_decision`
- `point_label` : `"1"`
- `topic` : `"Homogénéisation ou représentation distincte du tube métallique et de la palplanche intercalaire"`

**option_retained**
Représentation distincte des deux profils. Tubes en coque cylindrique au diamètre
réel, palplanches intercalaires en coque plane d'épaisseur équivalente calée sur
le module de flexion. Serrures représentées par partage de nœuds entre les deux.

**justification**
Le combi-wall associe deux profils de raideurs très différentes : les tubes
reprennent l'essentiel de la flexion verticale, les palplanches assurent la
continuité de l'écran et transmettent la poussée aux tubes. La répartition des
efforts entre ces deux profils sous une charge localisée est l'une des
informations que ce calcul doit fournir ; les représenter distinctement est la
condition pour l'obtenir.

**validity_domain**
Le partage de nœuds surestime la continuité de flexion d'une serrure réelle, qui
transmet essentiellement du cisaillement. Les moments transmis de la palplanche
au tube au droit des serrures sont donc surestimés.

**discarded_variants**
1. *description* : Homogénéisation en une plaque équivalente unique.
   *reason* : Reviendrait à payer un modèle tridimensionnel pour en perdre le
   bénéfice, et interdirait de sortir les contraintes réelles dans chaque
   profil.

---

## Décision 3

- **Opération** : `apply_decision`
- `point_label` : `"2"`
- `topic` : `"Représentation d'un tirant d'ancrage géotechnique scellé dans le sol (choix d'élément, représentation du bulbe de scellement)"`

**option_retained**
Éléments de barre travaillant en effort normal, section réelle de 75 mm de
diamètre, inclinaison de 20°, un tirant par tube. Extrémité arrière bloquée en un
point fixe représentant le scellement. Précontrainte de 250 kN par tirant
introduite comme chargement.

**justification**
Un tirant d'ancrage travaille en traction axiale. Un élément de barre en rend
compte avec sa section et sa géométrie réelles, ce qui conserve la composante
verticale de l'effort d'ancrage transmise à l'écran et à la poutre de
couronnement. C'est la représentation la plus simple qui reste fidèle à la
géométrie réelle du tirant, ce qui correspond à l'objet de ce cas de test.

**validity_domain**
Un point d'ancrage parfaitement fixe surestime la raideur de l'ancrage. Le
raffinement naturel serait un ressort à l'extrémité arrière, calé sur la raideur
du scellement.

**discarded_variants**
1. *description* : Ressort ponctuel équivalent en tête d'écran.
   *reason* : Perd l'inclinaison et la longueur libre du tirant, qui participent
   au comportement d'ensemble.
2. *description* : Modélisation de type câble.
   *reason* : Les documents correspondants du corpus traitent la précontrainte de
   béton armé, pas un tirant géotechnique scellé.
3. *description* : Modélisation explicite du bulbe de scellement.
   *reason* : Exigerait de mailler le sol autour du bulbe, ce que la décision du
   point 5 exclut.

---

## Décision 4

- **Opération** : `apply_decision`
- `point_label` : `"3"`
- `topic` : `"Choix entre maillage coïncident (liaison rigide directe) et raccord par méthode variationnelle (LIAISON_ELEM/COQ_POU) pour la liaison poutre de couronnement - écran"`

**option_retained**
Maillage coïncident, généré de façon cohérente par la chaîne elle-même. Poutre de
couronnement représentée par une poutre à son centre de gravité, reliée à la tête
de chaque tube par une liaison de corps solide sur l'anneau de nœuds supérieur du
tube.

**justification**
Le maillage de l'écran et celui de la poutre de couronnement sont produits par la
même chaîne, à partir de la même fiche. Leur coïncidence peut donc être imposée à
la génération au lieu d'être subie. Une liaison cinématique directe sur les nœuds
de tête de tube est alors le moyen le plus simple et le plus lisible de
représenter l'encastrement des tubes dans la poutre.

**validity_domain**
La liaison de corps solide encastre parfaitement la tête de tube dans la poutre,
ce qui est plus rigide que l'encastrement réel sur 0,80 m. Les moments en tête de
tube sont donc surestimés et les déplacements de la poutre sous-estimés.

**discarded_variants**
1. *description* : Raccord par méthode variationnelle entre maillages non
   coïncidents.
   *reason* : Sans objet dès lors que la chaîne génère les deux maillages depuis
   la même fiche ; la coïncidence est acquise par construction plutôt que subie.

---

## Décision 5

- **Opération** : `apply_decision`
- `point_label` : `"4"`
- `topic` : `"Choix entre contact surfacique, ressorts discrets et éléments de joint pour représenter l'interaction sol-écran"`

**option_retained**
Le sol n'est pas maillé. Son action est représentée par des ressorts horizontaux
répartis le long de la partie fichée de l'écran, de raideur définie par couche
selon les modules de réaction du cas de test : 6, 20, 35 et 80 MN/m³
respectivement pour le remblai, le sable, l'argile marneuse et la marne
compacte. Affectation par groupe de mailles correspondant à chaque strate. Seule
la poussée est appliquée en chargement ; la butée est produite par la réaction
des ressorts.

**justification**
La représentation de la réaction du sol le long d'un écran par des ressorts de
raideur fonction du module de réaction de chaque couche est la pratique courante
du calcul des écrans ; l'ingénieur la rattache à la méthode aux coefficients de
réaction de la NF P 94-282, référence non vérifiée article par article dans ce
cas de test. Elle est cohérente avec l'objet du calcul : le sol n'y est pas
étudié pour lui-même, il fournit l'appui élastique de l'écran.

**validity_domain**
Deux limites, importantes. Des ressorts linéaires ne plafonnent pas à la butée
limite : le modèle peut mobiliser une réaction supérieure à ce que le sol peut
fournir. Et l'équilibre poussée-butée n'étant pas vérifié par ce modèle, il doit
l'être par le calcul géotechnique amont.

**discarded_variants**
1. *description* : Contact-frottement surfacique.
   *reason* : Exige un massif de sol maillé, donc un modèle hors de proportion
   avec l'objet du calcul, et déplace le sujet vers la convergence.
2. *description* : Éléments de joint.
   *reason* : Même exigence de maillage du sol.

---

## Décision 6

- **Opération** : `apply_decision`
- `point_label` : `"5"`
- `topic` : `"Calcul du profil de pression (coefficient de poussée des terres Ko/actif/passif, combinaison avec le niveau d'eau) pour un écran de soutènement"`

**option_retained**
Poussée des terres et pression d'eau appliquées en pression imposée, variable
avec la profondeur, par la variante fonction de la commande de chargement
mécanique. Profils calculés hors Code_Aster. Différentiel de nappe de 1,50 m en
situation permanente, 3,50 m en situation accidentelle.

**justification**
Le sol n'étant pas maillé, son action motrice ne peut être introduite qu'en
chargement. Les profils de poussée et de pression d'eau sont des résultats du
calcul géotechnique amont ; les appliquer tels quels garantit la cohérence entre
les deux calculs, au lieu d'en recalculer une version concurrente.

**validity_domain**
Le profil de poussée est une donnée d'entrée que le modèle ne vérifie pas. Sa
justification appartient à la note géotechnique.

**discarded_variants**
1. *description* : Couplage hydromécanique avec pression interstitielle imposée.
   *reason* : Suppose un sol maillé en modélisation poromécanique, exclu par la
   décision du point 5.

---

## Décision 7

- **Opération** : `apply_decision`
- `point_label` : `"6"`
- `topic` : `"Phasage construction/excavation/mise en tension des tirants pour un ouvrage de quai"`

**option_retained**
Aucun phasage. Tous les chargements sont appliqués sur la géométrie finale, en un
seul état.

**justification**
L'objet du cas est d'exercer la chaîne de bout en bout. Un état final unique
suffit à produire toutes les grandeurs à contrôler — équilibre global,
réactions, déplacements — et c'est la configuration où un écart de résultat est
le plus facile à attribuer à sa cause.

**validity_domain**
Le phasage réel modifie sensiblement la répartition des efforts entre tirants et
encastrement en pied. Cette simplification est acceptable pour un test, pas pour
un calcul de projet.

**discarded_variants**
1. *description* : Phasage par incréments représentant excavation puis mise en
   tension.
   *reason* : Hors périmètre d'un cas de test ; alourdit la chaîne sans éclairer
   ce qu'on cherche à vérifier.

---

## Décision 8 — point reformulé

- **Opération** : `apply_decision`
- `point_label` : `"7"`
- `topic` : `"Position et blocages des limites latérales/inférieures d'un modèle de sol stratifié semi-infini"`

**option_retained**
Le point tel que formulé devient sans objet du fait de la décision du point 5 :
le sol n'étant pas maillé, il n'existe ni bord latéral ni fond de modèle. La
décision porte sur l'étendue de la tranche et ses faces de coupe. Tranche
représentative de 20,80 m, soit exactement huit entraxes de tube, comportant
neuf tubes et huit palplanches intercalaires ; un bollard d'amarrage sur le tube
central ; conditions de symétrie aux deux faces de coupe. En conséquence, la
composante hors plan de 15° de l'effort d'amarrage est supprimée pour ce cas de
test, et l'espacement des bollards du cas fictif est porté de 20,00 m à 20,80 m
pour le rendre compatible avec l'entraxe des tubes.

**justification**
L'ouvrage est régulier le long du quai et les bollards s'y répètent tous les huit
tubes : une tranche de huit entraxes centrée sur un bollard est l'unité
répétitive de l'ouvrage. Les conditions de symétrie aux faces de coupe
représentent la continuité avec les tranches voisines, ce qui suppose un
chargement lui-même symétrique — d'où la suppression de la composante hors plan.

**validity_domain**
La symétrie impose un chargement symétrique. Tout cas de charge dissymétrique —
amarrage oblique réel, grue en position excentrée, accostage hors axe — sort du
domaine de validité de ce modèle et demanderait une tranche allongée.

**discarded_variants**
1. *description* : Tranche de 41,60 m avec faces de coupe éloignées et
   composante hors plan conservée.
   *reason* : Plus fidèle, mais quadruple le modèle pour un cas de test dont
   l'objet est d'exercer la chaîne.
2. *description* : Modélisation des 120 m réels.
   *reason* : Sans objet, l'ouvrage étant régulier et décomposable en tranches.
