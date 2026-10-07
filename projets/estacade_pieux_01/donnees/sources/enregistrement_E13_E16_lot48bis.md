# Enregistrement des décisions E13 à E16 de MM — projet `estacade_pieux_01` (lot 48 bis)

Rejeu, par `aster-expert fiche enregistrer`, de l'enregistrement fait au lot 47 par
`scripts/fiche_lot47.py` (`mm_entries`, `TOPICS`, `DISCARDED`, `NOTES`). Les textes sont ceux de
MM, cités tels quels ; la commande vérifie qu'ils figurent à l'identique dans le fichier source.

Source du texte : donnees/sources/arbitrage_estacade_pieux_01_lot47.md
Enregistré le : 2026-10-05T05:48:41-04:00
Domaine de validité par défaut : Contre-calcul du modèle source d'avant-projet (lot 47), tel que MM l'a décidé ; hors de ce contre-calcul, la décision n'est pas établie.

### E13 — Formulations d'éléments et variantes de sensibilité

> Choix 1 : DKT pour la dalle, POU_D_T pour les pieux et les chevêtres.Variantes de sensibilité déclarées :  (a) DST pour la dalle ;  (b) POU_D_E pour les chevêtres seulement, pour tester l'hypothèse      « le modèle source ne prend pas en compte la déformation d'effort tranchant      des barres » si C6 à C8 sortent de tolérance.À inscrire comme décision E13, origine arbitrage_mm.

- Écartée : DKT et POU_D_E — option proposée, non retenue par MM (E13)
- Écartée : DST et POU_D_T — option proposée, non retenue ; DST gardé en variante de sensibilité (E13)

### E14 — Étendue du bouchon des pieux

> Le bouchon va de +0.70 à -0.80

- Écartée : Nœud du tablier à +0,70, à 0,00, à −0,80 ou à −2,25 — options proposées, non retenues (E14)

### E15 — Surface d'application des roues (TS et LM2)

> Empreinte B4 telle quelle (Recommandé) — Je lis B4 comme la donnée du modèle source : 0,40 × 0,40 m (TS) et 0,35 × 0,60 m (LM2), en pression uniforme au plan moyen, sans diffusion.

- Écartée : Diffusion à 45° jusqu'au plan moyen — non retenue par MM (E15)
- Écartée : Les deux, la diffusion en sensibilité — non retenue par MM (E15)

### E16 — Positions de LM2

> Comme TS (Recommandé) — Pas de 0,50 m selon X sur toute la longueur. Deux positions transversales : « axé » (roues à Y = ±1,00) et « bord de voie » (roue tangente au bord de la voie, à Y = ±1,325).

- Écartée : Toute la largeur de la dalle — non retenue par MM (E16)
- Écartée : Axé seulement — non retenue par MM (E16)
- Note : Erreur de la session dans la description proposée (Y = ±1,325) : la règle choisie, roue tangente au bord de la voie avec l'empreinte de 0,60 m selon Y, donne Y = 1,20 et −0,80 ; c'est la règle qui est appliquée. Positions selon X : 15,575 − 0,50 k et 15,625 + 0,50 k, k = 0 … 30 (62 positions, empreintes de 0,35 m alignées sur les mailles de 0,05 m).
