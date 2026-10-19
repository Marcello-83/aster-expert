# Tableau de bord des projets

Produit par `aster-expert rex <projet>` (lot 42) à partir de `connaissances/metriques/*.yaml` : ne pas éditer à la main.

Les métriques sont la « fonction de perte » de l'outil : d'un projet à l'autre, le taux d'échec, les interventions du superviseur et le nombre de lots par ouvrage doivent baisser. « Base » : chiffres déclarés (audit du lot 40) ; « mesuré » : recompté par `rex` sur les archives d'exécution.

Depuis le lot 44, les exécutions mesurées se séparent en **développement** et **vérification** (lancée par une commande de rejeu -- constats, références, tests lents -- ou rejeu d'un `.comm` déjà réussi, même empreinte) ; le taux d'échec mesuré porte sur le développement seul. Les interventions déclarées sont comptées lot par lot à partir du lot 42.

| Projet | Lots (base) | Exécutions (base) | Exécutions mesurées (dév. + vérif.) | Taux d'échec (base / dév.) | Échecs en vérification | Calcul (h, base) | Interventions (base) | Interventions déclarées (lots) | Connaissances créées | Promues |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `dalle_appuyee_01` | non renseigné | non renseigné | 8 + 2 | — / 12,5 % | 0 | non renseigné | non renseigné | 3 (lot 43 : 2, lot 44 : 0, lot 45 : 1, lot 49 : 0, lot 49bis : 0) | 22 | 3 |
| `estacade_pieux_01` | non renseigné | non renseigné | 37 + 48 | — / 18,9 % | 3 | non renseigné | non renseigné | 3 (lot 47 : 1, lot 47bis : 0, lot 47ter : 1, lot 47quater : 0, lot 49 : 0, lot 49bis : 1, lot 49ter : 0) | 25 | 0 |
| `pontons_alu_01` | non renseigné | non renseigné | 43 + 6 | — / 4,7 % | 0 | non renseigné | non renseigné | 2 (lot 50 : 0, lot 50bis : 1, lot 50ter : 0, lot 51 : 0, lot 51bis : 0, lot 51ter : 0, lot 52 : 1) | 3 | 0 |
| `quai_cw_test_01` | 40 | 190 | 180 + 196 | 38,4 % / 41,7 % | 0 | 1,54 | 25 (estimation) | 0 (lot 42 : 0, lot 44 : 0, lot 49 : 0, lot 49bis : 0) | 126 | 2 |
