# Enregistrement des décisions P60 et P61 de MM — projet `pontons_alu_01` (lot 51 quater)

Décisions de la consigne du lot 51 quater (MM, 16/10/2026), enregistrées par `aster-expert fiche
enregistrer`. P60 révise P56 : P56 est ré-arbitrée (l'ancienne décision va dans l'historique ; ses cas
unitaires et ses règles de combinaison sont conservés, seuls les coefficients changent). Les textes
sont extraits de la source par script (jamais retapés) ; la vérification exige qu'ils y figurent à
l'identique. La sensibilité HU_S5 (forfait AVP de 5 kPa) n'est pas une décision : elle n'est pas
enregistrée.

Source du texte : donnees/sources/consigne_lot51quater.md
Enregistré le : 2026-10-16T12:00:00-04:00
Domaine de validité par défaut : Recombinaison des cas unitaires du lot 51 ter de PONTONS-ALU-01 (lot 51 quater, calcul linéaire, aucune réexécution pour les résultats), telle que MM l'a décidée ; hors de ce calcul, la décision n'est pas établie.

### P56 — Houle par surfaces et par état limite

> **P60 — Houle « tablier noyé », P56 révisée.** Les cas unitaires et les règles
> de combinaison de P56 sont conservés. Seuls les coefficients changent.

- Écartée : Coefficients P56 (HU 14,49 / 12,99 / 12,48 kPa ; HD 12,03 kPa), dessus du tablier supposé sec alors que la crête le dépasse d'environ 1,2 m — borne non physique pour un tablier de 2 m ajouré à tubes drainés ; modèle du tablier noyé (P60)
- Note : Ré-arbitrage : P56 est révisée par P60 ; les quatre cas unitaires de 1 kPa (et leurs découpages par module), la houle en phase sur toute la longueur et les règles de combinaison de P56 restent en vigueur ; l'ancienne décision reste dans l'historique de la fiche.

### P60 — Houle « tablier noyé »

> **P60 — Houle « tablier noyé », P56 révisée.** Les cas unitaires et les règles
> de combinaison de P56 sont conservés. Seuls les coefficients changent.
>
> Principe : quand la crête dépasse le dessus du platelage (+1,445), la pression
> s'équilibre de part et d'autre des surfaces. La sous-pression quasi statique
> nette est bornée par la hauteur immergée de chaque surface jusqu'au dessus du
> platelage, soit ρg × (1,445 − z_sous-face), avec ρg = 10,05 kN/m³. Elle est
> majorée d'un facteur 2 pour le retard de remplissage.
>
> | Événement | HU_TUBES | HU_PANNES | HU_PLATELAGE | HD_TABLIER |
> |---|---|---|---|---|
> | HU (caractéristique), variantes 10 (pannes 50 × 50, sous-face +1,35) | 4,92 | 1,91 | 0,90 | — |
> | HU (caractéristique), variantes 12 (pannes 60 × 60, sous-face +1,34) | 4,92 | 2,11 | 0,90 | — |
> | HD (caractéristique) : retard de vidange, 0,10 m d'eau sur le platelage | — | — | — | 1,01 |
> | HU_F (fréquent) : inchangé, la crête fréquente +1,435 reste sous le dessus | 2,36 | 0,85 | 0,35 | — |
>
> HU et HD restent appliqués sur toute la longueur, en phase.

- Écartée : Dessus du tablier sec sous la crête (P56, lot 51 ter : HU_TUBES 14,49, HU_PANNES 12,99, HU_PLATELAGE 12,48, HD_TABLIER 12,03 kPa) — sous-pression nette bornée par la hauteur immergée jusqu'au dessus du platelage, × 2 pour le retard de remplissage (P60)
- Écartée : Étude dynamique de la houle sur le tablier — reportée à un lot dédié (MM, lot 51 quater)
- Note : Coefficients dans le groupe houle_lot51quater du fichier de données ; vérification : 2 × 10,05 × (1,445 − 1,20) = 4,92 ; 2 × 10,05 × (1,445 − 1,35) = 1,91 ; 2 × 10,05 × (1,445 − 1,34) = 2,11 ; 2 × 10,05 × (1,445 − 1,40) = 0,90 ; 10,05 × 0,10 = 1,01 (arrondi au centième supérieur). Le cas unitaire HU_PANNES garde 0,05 m par panne (P56) pour les variantes 12, dont les pannes ont 0,06 m de sous-face : écart signalé, non corrigé (aucun nouveau cas unitaire).

### P61 — Impact quasi statique

> **P61 — Impact quasi statique.** Pression d'impact à l'entrée de l'eau sous
> les surfaces :
>
> p_imp = DAF × ½ ρ Cs w² = 1,5 × 0,5 × 1,025 × 2π × 1,1² ≈ **5,9 kPa**
>
> Hypothèses du superviseur, à citer telles quelles :
>
> - w = 1,1 m/s : vitesse verticale de la surface libre au niveau de la
>   sous-face. C'est 2 × πHmax/T, avec Hmax = 2,03 m et T = 11,5 s, pour le
>   front raide d'une houle en faible profondeur.
> - Cs = 2π.
> - DAF = 1,5 : durée d'impact de l'ordre de la période propre d'une travée.
>
> L'impact est **local** : un module à la fois. Six événements exclusifs
> HU_IMP_Mk, avec k = 0 à 5. Chacun est la somme, sur le seul module Mk, de :
>
> 5,9 × (HU_TUBES_Mk + HU_PANNES_Mk + HU_PLATELAGE_Mk)
>
> Règles :
>
> - HU_IMP_Mk et HU sont **alternatifs** dans l'emplacement de la houle :
>   l'impact précède l'immersion.
> - Mêmes facteurs que HU à l'ELU fondamental et à l'ELS caractéristique.
> - Pas d'impact à l'ELU accidentel, à l'ELS fréquent ni à l'ELS quasi
>   permanent.
> - P57 s'applique : jamais avec AC ou ACA.

- Écartée : Impact simultané sur toute la longueur — impact local, un module à la fois, six événements exclusifs HU_IMP_M0 à HU_IMP_M5 (P61)
- Écartée : Étude dynamique de l'impact — traitement quasi statique avec DAF = 1,5 ; étude dynamique reportée à un lot dédié (MM, lot 51 quater)
- Note : Valeur décidée 5,9 kPa ; vérification : 1,5 × 0,5 × 1,025 × 2π × 1,1² = 5,84 kPa avec w arrondi à 1,1 m/s, 5,94 kPa avec w = 2π × 2,03 / 11,5 = 1,109 m/s ; 5,9 kPa retenu tel que décidé. Coefficients dans le groupe houle_lot51quater du fichier de données.
