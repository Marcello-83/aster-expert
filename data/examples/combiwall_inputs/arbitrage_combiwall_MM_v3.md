# Arbitrage des entrées pratique — quai en combi-wall ancré — v3

Révision des décisions de **MM** enregistrées au lot 18 (v2), au format du gabarit
`gabarit_saisie_fiche_hypotheses.md` (lot 17). Cas de test fictif :
`QUAI-CW-TEST-01`, données selon `cas_test_quai_combiwall_v2.md`.

**Statut du document.** Rédigé par Claude à partir des indications de MM du
21 septembre 2026. Une fois transmis, le document vaut décision de MM. Tous les points
sont validés par MM suite à relecture de cette note.

## Ce qui change par rapport à v2

| Décision | point_label | Nature du changement |
|---|---|---|
| 0 | 0 | inchangée |
| 1 | 1 | révisée : la grue est retirée de la justification et des variantes écartées |
| 2 | 1 | inchangée |
| 3 | 2 | révisée : raideur d'ancrage selon NF P 94-282 F.4.2, précontrainte supprimée |
| 4 | 3 | inchangée |
| 5 | 4 | révisée : ressorts côté bassin, du dragage au pied des profils, source norme ajoutée |
| 6 | 5 | révisée : Q1 n'intervient que par le profil de poussée |
| 7 | 6 | révisée : domaine de validité complété (usage du modèle sans phasage) |
| 8 | 7 | révisée : domaine de validité sans grue, défense sur le tube central |
| 9 | 8 | nouvelle : application des charges localisées d'amarrage et d'accostage |

Les décisions révisées remplacent la décision en vigueur de leur entrée ; la
décision v2 doit rester dans l'historique de l'entrée, jamais être écrasée.

## Conventions communes

- `decided_by` : `"MM"`
- `decided_at` : `2026-09-21T18:00:00` — heure conventionnelle, déclarée dans la
  référence de la source `decision_ingenieur`.
- Source `decision_ingenieur`, présente sur toutes les décisions :
  - `origin` : `"decision_ingenieur"`
  - `reference` : `"MM, cas de test QUAI-CW-TEST-01, révision v3 prise en séance
    de travail ; heure de decided_at conventionnelle"`
  - `date` : `2026-09-21`
- Source `norme`, ajoutée aux décisions 3 et 5 uniquement, avec la référence
  indiquée dans chaque décision. La NF P 94-282 est citée par article ; son texte
  n'est pas versé au dépôt (document sous licence AFNOR).
- Rattachement par `point_label` + `topic`, recopiés à l'identique de v2.

---

## Décision 1 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"1"`
- `topic` : `"Choix de la famille d'éléments (coque, poutre ou massif) pour le tube métallique + palplanche intercalaire"`

**option_retained**
Modélisation tridimensionnelle par éléments de coque, sur une tranche
représentative d'ouvrage et non sur les 120 m réels. Le choix de la
modélisation de coque précise relève de la moitié Code_Aster de la fiche ; la
présente décision porte sur la stratégie, pas sur l'identifiant.

**justification**
Les charges qui motivent ce calcul — amarrage et accostage — sont localisées et
se répètent le long du quai. Seul un modèle tridimensionnel représente leur
diffusion dans l'écran et dans la poutre de couronnement. Le comportement en
tranche courante est couvert par le calcul géotechnique amont. L'écran étant un
élément mince devant sa hauteur et sa longueur, une représentation surfacique en
rend compte sans surcoût de maillage.

**validity_domain**
Les efforts sont obtenus en efforts généralisés de coque et demandent un
post-traitement pour être exploités en dimensionnement, là où une modélisation
poutre les fournirait directement.

**discarded_variants**
1. *description* : Poutre par mètre linéaire, calcul en tranche bidimensionnelle.
   *reason* : Ne sait pas traiter les charges localisées d'amarrage et
   d'accostage, qui sont précisément l'objet du calcul.
2. *description* : Massif continu tridimensionnel.
   *reason* : Disproportionné pour un écran mince ; contredit le critère
   d'élancement.

---

## Décision 3 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"2"`
- `topic` : `"Représentation d'un tirant d'ancrage géotechnique scellé dans le sol (choix d'élément, représentation du bulbe de scellement)"`

**option_retained**
Éléments de barre travaillant en effort normal, un tirant par tube, section brute
de 75 mm de diamètre, inclinaison de 20° descendant vers l'arrière, tête à la cote
+2,50 sur le tube. La barre est modélisée sur la longueur de calcul
lf + lb/2 = 22,00 + 8,00/2 = 26,00 m le long de son axe, et son extrémité arrière,
placée au milieu du scellement, est bloquée. La raideur axiale du tirant est ainsi
égale à la raideur d'ancrage de la NF P 94-282, F.4.2 :
KMA = Et·A / (lf + lb/2) ≈ 35,7 MN/m par tirant, avec Et = 210 000 MPa et
A = 44,2 cm². Aucune précontrainte n'est appliquée : les tirants sont passifs.


**justification**
Un tirant d'ancrage travaille en traction axiale ; un élément de barre en rend
compte avec sa géométrie réelle et conserve la composante verticale de l'effort
d'ancrage transmise à l'écran. La norme donne pour un tirant scellé une raideur
qui compte la longueur libre et la moitié de la longueur scellée : modéliser la
barre sur cette longueur, extrémité bloquée, reproduit exactement cette raideur
sans introduire de ressort discret. La précontrainte est supprimée parce qu'elle
n'a de sens qu'au sein d'un phasage — mise en tension à un stade d'excavation
donné — que la décision du point 6 exclut : appliquée dans un état unique, elle se
superposerait aux autres chargements sans séquence et l'effort final dans le
tirant ne correspondrait à aucun état réel. Un tirant passif est cohérent avec un
calcul en état unique.

**validity_domain**
La raideur F.4.2 est une raideur conventionnelle : elle ignore l'interaction
entre le scellement et le terrain et la déformabilité du massif d'ancrage. La
section est prise brute ; la section utile nette de corrosion (F.4.2, NOTE 4)
n'est pas appliquée dans ce cas de test. Sans précontrainte ni phasage, l'effort
dans le tirant ne résulte que des chargements appliqués au modèle ; il ne se
compare pas à l'effort d'un calcul géotechnique phasé.

**discarded_variants**
1. *description* : Barre sur la seule longueur libre de 22,00 m, extrémité
   bloquée (décision v2).
   *reason* : Raideur EA/lf ≈ 42,2 MN/m, supérieure de 18 % à la raideur
   d'ancrage de la norme ; surestime la raideur de l'appui en tête.
2. *description* : Barre de 22,00 m prolongée par un ressort discret de raideur
   EA/(lb/2) ≈ 232 MN/m.
   *reason* : Raideur équivalente en série à la variante retenue, mais ajoute un
   type d'élément et une caractéristique discrète sans information supplémentaire.
3. *description* : Précontrainte de 250 kN appliquée comme chargement dans un
   état unique.
   *reason* : Sans phasage, l'état de mise en tension et l'état final ne sont pas
   séquencés ; l'effort obtenu dans le tirant n'a pas de signification physique.
4. *description* : Ressort ponctuel équivalent en tête d'écran.
   *reason* : Perd l'inclinaison du tirant et la composante verticale de
   l'effort d'ancrage.
5. *description* : Modélisation explicite du bulbe de scellement.
   *reason* : Exigerait de mailler le sol autour du bulbe, ce que la décision du
   point 4 exclut.

**sources supplémentaires**
- `origin` : `"norme"`
- `reference` : `"NF P 94-282 (mars 2009), Annexe F (informative), F.4.2 —
  raideur d'un tirant scellé KMA = Et·A/(lf + lb/2), et NOTE 4 (section utile)"`
- `date` : `2009-03`

---

## Décision 5 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"4"`
- `topic` : `"Choix entre contact surfacique, ressorts discrets et éléments de joint pour représenter l'interaction sol-écran"`

**option_retained**
Le sol n'est pas maillé. La réaction du terrain de la fiche est représentée par
des ressorts horizontaux linéaires, perpendiculaires au quai, **côté bassin
uniquement**, de la cote de dragage −12,00 jusqu'au pied de chaque profil :
−26,00 pour les tubes, −18,00 pour les palplanches intercalaires.
Deux strates sont concernées : l'argile marneuse raide de −12,00 à
−18,00, k_h = 35 MN/m³ ; la marne compacte de −18,00 à −26,00, k_h = 80 MN/m³.
La raideur est rapportée à la surface projetée sur le plan de l'écran, et non à
la surface développée des tubes. Au-dessus de la cote de dragage, aucun ressort :
côté terre, l'action du terrain est introduite en totalité par le profil de
poussée de la décision du point 5.

**justification**
La méthode aux coefficients de réaction de la NF P 94-282, Annexe F, représente
l'écran comme une poutre sur appuis élastiques. Sa loi de réaction (F.1,
Figure F.1.1) est bornée par la poussée et la butée limites ; seule sa branche
élastique, de pente k_h, est retenue ici. Côté terre, le terrain est supposé à
l'état de poussée sous l'effet des charges permanentes et cette action est
appliquée en chargement : y ajouter des ressorts la compterait deux fois. Côté
bassin, le terrain de la fiche est l'appui de l'écran et ses ressorts portent la
butée mobilisée. L'ordre de grandeur des k_h du cas a été confronté à la formule
F.3.1 avec l'inertie des tubes seule ramenée au mètre linéaire
(Estr·Istr/B0 ≈ 1 405 MN·m²/m, palplanches négligées) : 24 à 42 MN/m³ pour
l'argile selon α = 1 ou 2/3, ce qui encadre la valeur 35 ; 106 à 266 MN/m³ pour
la marne selon α = 1 ou 1/2, au-dessus de la valeur 80 du cas, qui est donc plus
souple. Les valeurs du cas sont conservées comme données de test : α n'est pas
déterminable depuis les données du cas, le Tableau F.3.1 l'indexant sur le
rapport EM/pl et la pression limite n'étant pas fournie. La fiche de 14 m
dépasse 1,5·l0 (environ 5,3 m avec k_h = 35 MN/m³), la correction F.3.3 est sans
objet ; la correction F.3.4 vise une fouille étroite entre deux écrans et ne
concerne pas un quai.

**validity_domain**
1. Les ressorts sont linéaires et ne plafonnent pas à la butée limite
   (Figure F.1.1) : le modèle peut mobiliser une réaction supérieure à ce que le
   terrain peut fournir. Contrôle de niveau D requis : à chaque cote de la fiche,
   la pression de réaction k_h·y reste inférieure à la butée limite fournie par
   le calcul géotechnique amont.
2. Les ressorts travaillent dans les deux sens. Un déplacement de la fiche vers la
   terre produirait une traction sans signification physique. Contrôle de
   niveau D requis : réactions de même signe, en compression, sur toute la fiche,
   pour chaque combinaison ; l'accostage est le cas à surveiller.
3. La pression initiale au repos côté bassin (K0·σ'v, F.2) n'est pas appliquée :
   la réaction part de zéro.
4. Côté terre, aucun ressort : sous une charge qui pousse l'écran vers la terre
   au-dessus du dragage, la réaction du remblai n'est pas mobilisée ; le modèle
   est localement trop souple sous accostage.
5. k_h dépend de la raideur de l'écran (F.3.1) ; les valeurs du cas ne sont pas
   recalées sur la raideur de l'écran modélisé.
6. Sous −18,00, l'écran est discontinu : les tubes seuls, de diamètre projeté
   1,42 m à l'entraxe de 2,60 m, reçoivent la réaction. L'Annexe F ne traite pas
   ce cas ; l'effet tridimensionnel du terrain entre tubes n'est pas représenté.
7. L'équilibre poussée-butée et la fiche ne sont pas vérifiés par ce modèle ; ils
   relèvent du calcul géotechnique amont.

**discarded_variants**
1. *description* : Ressorts sur les quatre strates, le long de toute la hauteur en
   contact avec le terrain (décision v2).
   *reason* : Côté terre, double compte avec le profil de poussée appliqué en
   chargement.
2. *description* : Ressorts non linéaires bornés par la poussée et la butée
   limites, des deux côtés de l'écran, conformément à la Figure F.1.1.
   *reason* : Reproduit le calcul aux coefficients de réaction du logiciel
   géotechnique ; n'a de sens qu'avec le phasage (F.1, NOTE 4), exclu au point 6.
3. *description* : Contact-frottement surfacique.
   *reason* : Exige un massif de sol maillé.
4. *description* : Éléments de joint.
   *reason* : Même exigence de maillage du sol.

**sources supplémentaires**
- `origin` : `"norme"`
- `reference` : `"NF P 94-282 (mars 2009), Annexe F (informative), méthode aux
  coefficients de réaction : F.1 et Figure F.1.1 (loi de réaction), F.2 (K0 et
  valeurs limites), F.3 formule F.3.1 et Tableaux F.3.1 et F.3.2 (k_h), F.3 (2)
  et (3) formules F.3.3 et F.3.4"`
- `date` : `2009-03`

---

## Décision 6 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"5"`
- `topic` : `"Calcul du profil de pression (coefficient de poussée des terres Ko/actif/passif, combinaison avec le niveau d'eau) pour un écran de soutènement"`

**option_retained**
Poussée des terres et pression d'eau appliquées en pression imposée, variable
avec la profondeur, par la variante fonction de la commande de chargement
mécanique. Profils calculés hors Code_Aster. Différentiel de nappe de 1,50 m en
situation permanente, 3,50 m en situation accidentelle. La surcharge
d'exploitation du terre-plein (Q1) n'est pas appliquée comme charge de surface
dans le modèle : elle n'intervient que par l'incrément de poussée qu'elle
produit, inclus dans le profil calculé en amont.

**justification**
Le sol n'étant pas maillé, son action motrice ne peut être introduite qu'en
chargement. Les profils de poussée et de pression d'eau, y compris l'effet de la
surcharge de terre-plein, sont des résultats du calcul géotechnique amont ; les
appliquer tels quels garantit la cohérence entre les deux calculs.

**validity_domain**
Le profil de poussée est une donnée d'entrée que le modèle ne vérifie pas. Sa
justification appartient à la note géotechnique.

**discarded_variants**
1. *description* : Couplage hydromécanique avec pression interstitielle imposée.
   *reason* : Suppose un sol maillé en modélisation poromécanique, exclu par la
   décision du point 4.
2. *description* : Surcharge Q1 appliquée comme pression sur un terre-plein
   modélisé.
   *reason* : Le terre-plein n'est pas modélisé ; la diffusion de la surcharge
   vers l'écran est un résultat géotechnique.

---

## Décision 7 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"6"`
- `topic` : `"Phasage construction/excavation/mise en tension des tirants pour un ouvrage de quai"`

**option_retained**
Aucun phasage. Tous les chargements sont appliqués sur la géométrie finale, en un
seul état. Les tirants sont passifs (décision du point 2).

**justification**
L'objet du cas est d'exercer la chaîne de bout en bout. Un état final unique
suffit à produire les grandeurs à contrôler — équilibre global, réactions,
déplacements — et c'est la configuration où un écart de résultat est le plus
facile à attribuer à sa cause. La suppression de la précontrainte retire la
seule donnée du cas qui imposait un phasage.

**validity_domain**
Le phasage réel — excavation par étapes, pose des tirants à un stade
intermédiaire — détermine les moments dans l'écran et l'effort dans les tirants
sous charges permanentes. Ce modèle ne les représente pas : sous charges
permanentes, ses résultats ne se comparent pas à ceux du calcul géotechnique
phasé. Son usage légitime en projet est la détermination des effets des charges
localisées, à superposer à l'état de base donné par le calcul géotechnique.
Acceptable pour un test, pas pour justifier l'écran sous charges permanentes.

**discarded_variants**
1. *description* : Phasage sous Code_Aster représentant excavation par étapes et
   mise en tension des tirants.
   *reason* : Faisable, mais demande un calcul plus complexe hors de l'objet de
   ce cas de test ; réservé à un cas ultérieur dédié.

---

## Décision 8 — révisée

- **Opération** : révision d'une entrée tranchée
- `point_label` : `"7"`
- `topic` : `"Position et blocages des limites latérales/inférieures d'un modèle de sol stratifié semi-infini"`

**option_retained**
Le point tel que formulé devient sans objet du fait de la décision du point 4 :
le sol n'étant pas maillé, il n'existe ni bord latéral ni fond de modèle. La
décision porte sur l'étendue de la tranche et ses faces de coupe. Tranche
représentative de 20,80 m, soit exactement huit entraxes de tube, comportant
neuf tubes et huit palplanches intercalaires ; un bollard d'amarrage et une
défense d'accostage au droit du tube central ; conditions de symétrie aux deux
faces de coupe. En conséquence, la composante hors plan de 15° de l'effort
d'amarrage est supprimée pour ce cas de test.

**justification**
L'ouvrage est régulier le long du quai et les bollards et défenses s'y répètent
tous les huit tubes : une tranche de huit entraxes centrée sur ces équipements
est l'unité répétitive de l'ouvrage. Les conditions de symétrie aux faces de
coupe représentent la continuité avec les tranches voisines, ce qui suppose un
chargement lui-même symétrique — d'où la suppression de la composante hors plan.

**validity_domain**
La symétrie impose un chargement symétrique. Tout cas de charge dissymétrique —
amarrage oblique réel, accostage hors axe du tube central — sort du domaine de
validité de ce modèle et demanderait une tranche allongée.

**discarded_variants**
1. *description* : Tranche de 41,60 m avec faces de coupe éloignées et
   composante hors plan conservée.
   *reason* : Plus fidèle, mais quadruple le modèle pour un cas de test dont
   l'objet est d'exercer la chaîne.
2. *description* : Modélisation des 120 m réels.
   *reason* : Sans objet, l'ouvrage étant régulier et décomposable en tranches.

---

## Décision 9 — point neuf

- **Opération** : `insert_practice_entry`
- `point_label` : `"8"`
- `topic` : `"Application des charges localisées d'amarrage et d'accostage"`

**option_retained**
Les seules charges localisées du modèle sont l'amarrage (Q3) et l'accostage (A).
Aucune charge de grue : la voie de grue est un ouvrage distinct, fondé sur pieux,
sans interaction avec l'écran.

*Amarrage.* Effort de 1 000 kN incliné de 30° au-dessus de l'horizontale, dans le
plan perpendiculaire au quai, dirigé vers le bassin. Appliqué comme force nodale
au nœud `BOLLARD`, situé sur l'axe de la poutre de couronnement (cote +3,30) au
droit du tube central, accompagné du moment de transport dû au décalage vertical
de 0,70 m entre le point d'application réel (+4,00) et l'axe de la poutre :
M = 866 kN × 0,70 m ≈ 606 kN·m, d'axe parallèle au quai. Le bollard est supposé
sur l'axe de la poutre en plan. 

*Accostage.* Effort horizontal de 800 kN, perpendiculaire au quai, dirigé vers la
terre. La défense elle-même n'est pas modélisée. Sa réaction est répartie
uniformément sur une empreinte, le groupe de mailles `DEFENSE` : face bassin du
tube central, de +1,00 à +2,00, soit une hauteur d'empreinte de 1,00 m. L'intensité est une force par unité
de surface projetée, de direction fixe dans le repère global :
800 / (1,00 × 1,42) ≈ 563 kN/m². Ce n'est pas une pression normale à la paroi.

**justification**
La réaction de la défense est un résultat du choix de la défense — courbe
énergie-réaction — établi en amont ; pour la structure, seule compte la façon
dont cette réaction entre dans l'écran. Une force ponctuelle sur des coques crée
une singularité locale sans signification ; une répartition sur l'empreinte de
fixation donne des contraintes locales exploitables. La direction fixe
correspond à la réaction d'un panneau plan ; une pression normale à la paroi
courbe du tube produirait des composantes radiales sans contrepartie physique.
Pour l'amarrage, la poutre de couronnement étant représentée par son axe, le
moment de transport restitue l'effet de l'excentricité du point d'application.

**validity_domain**
Les dimensions de l'empreinte sont inventées ; les contraintes locales dans le
tube sous l'empreinte y sont sensibles et demandent un maillage raffiné dans
cette zone. Le moment de transport suppose la section de la poutre indéformable,
cohérent avec sa représentation par un élément de poutre. L'excentricité en plan
du bollard n'est pas représentée.

**discarded_variants**
1. *description* : Défense modélisée en éléments de coque, force surfacique
   appliquée sur la défense.
   *reason* : Le comportement d'une défense — élastomère, fortement non
   linéaire — n'est pas celui d'une coque élastique, et sa réaction est déjà une
   donnée ; modéliser son panneau ajouterait des éléments sans information pour
   l'écran.
2. *description* : Force ponctuelle nodale pour l'accostage.
   *reason* : Singularité locale dans les coques ; contraintes inexploitables au
   point d'application.
3. *description* : Force d'amarrage appliquée à l'axe de la poutre sans moment de
   transport.
   *reason* : Omet un moment de l'ordre de 600 kN·m sur la poutre de
   couronnement.

---

## Convention de nommage des groupes — validée par MM

Convention commune au maillage et au fichier de commandes. Tout groupe cité par
une décision doit y figurer, et tout groupe de la convention doit être utilisé.

**Groupes de mailles**

| Groupe | Contenu |
|---|---|
| `TUBE_01` … `TUBE_09` | coques de chaque tube, numérotées dans le sens du quai |
| `TUBES` | réunion des neuf tubes |
| `PALP_01` … `PALP_08` | coques de chaque palplanche intercalaire |
| `PALPS` | réunion des huit palplanches |
| `ECRAN` | `TUBES` ∪ `PALPS` |
| `ECRAN_POUSSEE` | mailles de l'écran recevant le profil de poussée et de pression d'eau |
| `POUTRE_COUR` | poutre de couronnement, sur son axe à +3,30 |
| `TIRANT_01` … `TIRANT_09` | barre d'ancrage de chaque tube |
| `TIRANTS` | réunion des neuf tirants |
| `RESS_AV_ARGI` | mailles de l'écran de −12,00 à −18,00 (tubes et palplanches) |
| `RESS_AV_MARNE` | mailles des tubes de −18,00 à −26,00 |
| `DEFENSE` | empreinte d'accostage, face bassin de `TUBE_05`, de +1,00 à +2,00 |

**Groupes de nœuds**

| Groupe | Contenu |
|---|---|
| `TETE_TUBE_01` … `TETE_TUBE_09` | anneau de nœuds supérieur de chaque tube |
| `ANC_01` … `ANC_09` | extrémité arrière bloquée de chaque tirant, à 26,00 m de la tête le long de l'axe |
| `ANCRAGES` | réunion des `ANC_xx` |
| `BOLLARD` | nœud de l'axe de `POUTRE_COUR` au droit de `TUBE_05` |
| `SYM_G`, `SYM_D` | nœuds des deux faces de coupe |

Changements par rapport à la convention proposée précédemment : les groupes
`RESS_AR_*`, `RESS_AV_REMB` et `RESS_AV_SABLE` sont supprimés (décision 5) ;
`DEFENSE` devient un groupe de mailles d'empreinte au lieu d'un nœud
(décision 9).

**Cotes que le maillage doit porter en nœuds** : −26,00 ; −18,00 ; −12,00 ;
+1,00 ; +2,00 ; +2,50 ; +2,60 ; +3,30. La cote de l'anneau `TETE_TUBE_xx` sera en
sous-face de poutre à +2,60.
