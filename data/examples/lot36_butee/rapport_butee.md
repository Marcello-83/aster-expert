# Lot 36 — diagnostic de la butée sous G

## Étape 1 — vérification à la main (cas G, base)

Aire tributaire A : lue de l'analytique (`spring_node_areas`), jamais déduite de la raideur ; raideur k : lue du `.comm` (`VALE` de la classe du nœud) ; DY : MED/`.mess`.

| | Nœud le plus sollicité en compression | Nœud en traction le plus sollicité |
|---|---|---|
| Nœud, porteur | N983, TUBE_04 | N20947, TUBE_05 |
| Cote z (m CM) | -12,00 | -16,75 |
| Groupe de raideur du `.comm` | GEN_RESS_ARGI_01 | GEN_RESS_ARGI_22 |
| Aire tributaire A (m²) | 0,002172 | 0,027767 |
| Raideur k (N/m) | 76015,35 | 971849,11 |
| k / A (MN/m³) | 35,000000 | 35,000000 |
| k_h de la couche (MN/m³) | 35,000 | 35,000 |
| DY (mm) | -12,8025 | 0,6644 |
| Pression k·DY/A (kPa) | -448,09 | 23,25 |
| σ'p bassin en z (kPa) | 47,10 | 169,97 |
| Taux vs butée bassin | 951,4 % | — |
| Butée côté terre en z (kPa) | 497,99 | 620,87 |
| Taux vs butée terre | — | 3,75 % |

Vérification à la main du nœud en compression : k/A vaut le k_h de la couche (35,000000 MN/m³) ; A = ¼ × (largeur projetée des deux facettes voisines) × hauteur de maille, soit ¼ × (R(1−cos 9°) + R(cos 9° − cos 18°)) × 0,25 m avec R = 0,71 m, ce qui donne 0,0348 × 0,25 / 4 = 0,002172 m² : aucune erreur d'aire tributaire ni d'unité (MN/m³ × 1e6 = N/m³).

## Étape 2 — part de chaque cause (cas G, modèle complet, 10 433 nœuds à ressort)

| Grandeur | Base | V1 (pression initiale côté bassin) |
|---|---:|---:|
| Nœuds en compression | 8 828 | 5 867 |
| Taux maximal de butée bassin | 951,4 % | 912,8 % |
| Nœud du taux maximal | N983, z = -12,00 | N983, z = -12,00 |
| Nœuds au-delà de 100 % | 2 413 | 2 141 |
| Force de compression totale des ressorts (MN) | 19,68 | 13,37 |
| Dont force en excès de la butée (MN) | 6,85 | 6,03 |
| Nœuds en traction | 1 605 | 4 566 |
| Pression de traction maximale (kPa) | 32,2 | 87,3 |
| Force de traction totale (MN) | 0,44 | 1,40 |
| Taux maximal vs butée limite **côté terre** | 3,75 % | 7,64 % |
| Nœuds en traction **au-delà** de la butée côté terre | 0 | 0 |
| Cote de pivot, génératrice bassin de TUBE_05 (m CM) | -14,97 | -15,04 |

### Contrôle corrigé du signe : nœuds en traction contre la butée limite côté terre (Kp·σ'v + 2c'·√Kp)

| Couche | Modèle | Nœuds en traction | Pression max (kPa) | Butée terre au nœud du taux max (kPa) | Taux max | Au-delà |
|---|---|---:|---:|---:|---:|---:|
| argile marneuse (−12,00 à −18,00) | base | 453 | 27,1 | 620,9 | 3,75 % | 0 |
| marne compacte (−18,00 à −26,00) | base | 1 193 | 32,2 | 885,2 | 3,64 % | 0 |
| argile marneuse (−12,00 à −18,00) | V1 | 524 | 22,0 | 620,9 | 3,11 % | 0 |
| marne compacte (−18,00 à −26,00) | V1 | 4 099 | 87,3 | 1135,3 | 7,64 % | 0 |

σ'v côté terre : stratigraphie du cas de test (§5), nappe à +2,00 (§6), terre-plein à +4,00 ; γ au-dessus de la nappe, γ' au-dessous. Ce calcul retrouve à 0,1 kPa près le profil de poussée active de l'annexe A.4 (test unitaire).

### V2 — sans exécution supplémentaire

| Lecture | Taux maximal | Nœuds au-delà de 100 % |
|---|---:|---:|
| Base (référence) | 951,4 % | 2 413 |
| V2, lecture littérale : (réaction de la base − pression initiale de V1)⁺ / σ'p bassin | 951,4 % | 2 205 |
| Lecture voisine : pression initiale de V1 **ajoutée** à la réaction de V1, / σ'p bassin | 912,8 % | 2 326 |

L'énoncé ne dit pas laquelle des deux lectures est celle de la figure F.1.1 : les deux sont rapportées, aucune n'est retenue. Le taux maximal est identique dans les trois cas parce que le nœud du maximum est à z = −12,00, où la pression initiale est nulle.

### Où se trouvent les dépassements (nœuds au-delà de 100 % / nœuds en compression)

| Tranche de cote (m CM) | Base | V1 |
|---|---:|---:|
| -12 à -13 | 1005 / 1005 | 1005 / 1005 |
| -13 à -14 | 841 / 1005 | 825 / 1005 |
| -14 à -15 | 560 / 996 | 496 / 1005 |
| -15 à -16 | 384 / 880 | 224 / 889 |
| -16 à -17 | 112 / 800 | 0 / 784 |

### Ce que chaque cause attribue (chiffres seulement, aucune conclusion de conception)

1. **Ressorts linéaires non plafonnés** : 6,85 MN sur 19,68 MN de compression (34,8 %) dépassent la force de butée de leur nœud, dans le modèle de base ; les dépassements sont sur les tranches −12 à −17 m.
2. **Pression initiale au repos côté bassin (V1)** : les nœuds au-delà de 100 % passent de 2 413 à 2 141 (-272), le taux maximal de 951,4 % à 912,8 % ; la force de compression baisse de 6,30 MN.
3. **Absence de ressorts côté terre** : 1 605 nœuds en traction (15,4 % des nœuds à ressort), pression maximale 32,2 kPa, soit 3,75 % de la butée limite côté terre ; 0 nœud au-delà. Sous V1 : 4 566 nœuds, 7,64 %, 0 au-delà.

