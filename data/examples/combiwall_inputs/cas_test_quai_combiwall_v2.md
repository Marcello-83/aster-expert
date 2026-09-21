# Cas de test fictif — Quai en combi-wall ancré — v2

**Données entièrement inventées, destinées au seul test de la chaîne AsterExpert.
Aucune valeur de ce document ne constitue une donnée de projet, une
recommandation de dimensionnement ou un avis d'ingénierie. Les valeurs sont
choisies pour être mutuellement cohérentes et d'ordre de grandeur plausible, pas
pour être justes.**

Référence de cas : `QUAI-CW-TEST-01`. Cotes en mètres CM (cote marine fictive).

**Modifications par rapport à v1** : tirants passifs sans précontrainte ; cas de
charge Q2 (grue) supprimé, la voie de grue étant un ouvrage distinct fondé sur
pieux ; bollards et défenses tous les 20,80 m ; empreinte de défense définie ;
Q1 précisé comme donnée du calcul de poussée amont.

---

## 1. Géométrie générale

| Donnée | Valeur |
|---|---|
| Longueur de quai | 120,00 m |
| Cote d'arase du terre-plein | +4,00 |
| Cote de dragage devant l'écran | −12,00 |
| Hauteur libre | 16,00 m |
| Cote de pied des tubes | −26,00 (fiche 14,00 m sous dragage) |
| Cote de pied des palplanches intercalaires | −18,00 |

## 2. Écran — combi-wall

| Donnée | Valeur |
|---|---|
| Tubes | Ø 1420 mm, épaisseur 16 mm |
| Nuance acier tubes | S355 |
| Entraxe des tubes | 2,60 m |
| Nombre de tubes sur 120 m | 47 |
| Palplanches intercalaires | profil en Z, module 1800 cm³/m, épaisseur âme 9,5 mm |
| Nuance acier palplanches | S355 |
| Protection anticorrosion | non modélisée ; surépaisseur de corrosion 2,0 mm déduite sur la face bassin des tubes |

## 3. Poutre de couronnement

| Donnée | Valeur |
|---|---|
| Section | 2,50 m (largeur) × 1,40 m (hauteur) |
| Cote de sous-face | +2,60 |
| Cote d'arase | +4,00 |
| Béton | C35/45 |
| Acier passif | B500B |
| Liaison à l'écran | tubes encastrés sur 0,80 m dans la poutre |

## 4. Tirants d'ancrage

| Donnée | Valeur |
|---|---|
| Type | barres d'ancrage passives, scellées, un tirant par tube, sans mise en tension |
| Diamètre | 75 mm |
| Nuance | 500/700 |
| Module d'élasticité | 210 000 MPa |
| Entraxe | 2,60 m |
| Inclinaison sur l'horizontale | 20° (descendant vers l'arrière) |
| Cote de la tête d'ancrage | +2,50 |
| Longueur libre | 22,00 m |
| Longueur de scellement | 8,00 m |
| Diamètre de scellement | 200 mm |

## 5. Stratigraphie et paramètres géotechniques

| Couche | De | À | γ (kN/m³) | γ' (kN/m³) | φ' (°) | c' (kPa) | cu (kPa) | E_M (MPa) | k_h (MN/m³) |
|---|---|---|---|---|---|---|---|---|---|
| Remblai hydraulique sablo-graveleux | +4,00 | −2,00 | 19,0 | 10,0 | 32 | 0 | — | 8 | 6 |
| Sable moyen dense | −2,00 | −9,00 | 20,0 | 10,5 | 35 | 0 | — | 25 | 20 |
| Argile marneuse raide | −9,00 | −18,00 | 20,0 | 10,5 | 25 | 15 | 120 | 40 | 35 |
| Marne compacte | −18,00 | −35,00 | 21,0 | 11,5 | 30 | 40 | — | 120 | 80 |

Substratum rigide supposé à −35,00. Les k_h sont des données de test ; leur
confrontation à la NF P 94-282, formule F.3.1, figure dans la décision 5 de
l'arbitrage v3.

## 6. Niveaux d'eau

| Donnée | Valeur |
|---|---|
| Nappe côté terre — niveau normal | +2,00 |
| Nappe côté terre — niveau haut (cas accidentel) | +3,00 |
| Marnage côté bassin | +3,50 / −0,50 |
| Différentiel de calcul, situation permanente | 1,50 m |
| Différentiel de calcul, situation accidentelle | 3,50 m |

## 7. Cas de charge

### G — permanentes
- Poids propre de l'écran, de la poutre de couronnement et des tirants.
- Poussée des terres sur la hauteur libre et la fiche.
- Poussée d'eau différentielle correspondant au différentiel permanent de 1,50 m.

### Q1 — exploitation, terre-plein
- Surcharge uniforme 40 kPa, de 1,00 m à 10,00 m derrière la face avant.
- Zone de stockage 60 kPa, de 10,00 m à 25,00 m derrière la face avant.
- Donnée du calcul géotechnique amont : Q1 entre dans le modèle uniquement par
  l'incrément de poussée qu'elle produit.

### Q3 — amarrage
- Bollards tous les 20,80 m, soit un bollard tous les huit tubes.
- Effort de traction 1000 kN par bollard.
- Inclinaison : 30° au-dessus de l'horizontale, 15° hors du plan perpendiculaire
  au quai (composante supprimée dans le modèle en tranche, décision 8).
- Point d'application : arase de la poutre de couronnement, +4,00, supposé sur
  l'axe de la poutre en plan.

### A — accidentel, accostage
- Effort horizontal perpendiculaire au quai de 800 kN, dirigé vers la terre.
- Défenses tous les 20,80 m, au droit d'un tube ; un seul point chargé à la fois.
- Empreinte de fixation de la défense : face bassin du tube, de +1,00 à +2,00
  (hauteur 1,00 m, centre à +1,50).
- Combiné au différentiel de nappe accidentel de 3,50 m.

### Hors périmètre du test
Grue et voie de grue (ouvrage distinct), situation sismique, phasage de
construction et mise en tension des tirants, fluage et retrait du béton,
corrosion évolutive.

## 8. Résultats attendus du test

L'objet n'est pas d'obtenir un dimensionnement juste, mais de vérifier que la
chaîne produit un ensemble cohérent et exécutable :

1. une fiche d'hypothèses complète, dont les entrées `pratique` sont tranchées
   par l'ingénieur et les entrées `code_aster` fondées sur un extrait réel ;
2. un maillage dont les invariants — nombre de tubes, entraxe réel, cotes des
   interfaces de strates, groupes déclarés et leur cardinalité, boîte
   englobante — correspondent à ce que la fiche déclare ;
3. un fichier de commandes lisible, commenté, dont chaque bloc renvoie à une
   ligne de la fiche ;
4. une validation de niveau B sans erreur ;
5. une exécution allant jusqu'à `FIN`, avec ses alarmes énoncées et non
   masquées ;
6. des contrôles physiques élémentaires : équilibre global, résultante des
   réactions comparée à la résultante des charges appliquées, ordres de grandeur
   des déplacements en tête d'écran, signe des réactions des ressorts sur toute
   la fiche, pression de réaction comparée à la butée limite.

Un résultat numériquement faux mais dont la chaîne est cohérente et le niveau de
validation honnêtement annoncé est un succès du test. Un résultat plausible
obtenu en comblant une hypothèse non tranchée est un échec.
