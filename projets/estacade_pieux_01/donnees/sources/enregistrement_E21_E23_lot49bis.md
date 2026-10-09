# Enregistrement des décisions E21 à E23 de MM — projet `estacade_pieux_01` (lot 49 bis)

Réponses de MM aux questions de la session du lot 49 bis, enregistrées par
`aster-expert fiche enregistrer`. Les textes sont ceux de MM, cités tels quels ; la
commande vérifie qu'ils figurent à l'identique dans le fichier source. Ils servent la
synthèse ingénieur (section `engineering_summary` de `projet.yaml`) : critères de service
et en-tête des fichiers de flexion composée ; le modèle et la référence ne changent pas.

Source du texte : donnees/sources/arbitrage_estacade_pieux_01_lot49bis.md
Enregistré le : 2026-10-09T10:30:00-04:00
Domaine de validité par défaut : Synthèse ingénieur du contre-calcul du modèle source d'avant-projet (lot 49 bis), telle que MM l'a décidée ; hors de cette synthèse, la décision n'est pas établie.

### E21 — Critère de déplacement en tête de pieu (h/400)

> h = hauteur libre = de la sous-face du chevêtre (recépage, +0,60 m NGF) au fond de calcul(−2,25 m NGF, §14.1 : dragage −1,25 + 1,00 m de surcreusement), soit h = 2,85 m,limite h/400 = 7,1 mm sous ELS caractéristique. Limite unique appliquée à toutes les têtesde pieux ; le critère n'est pertinent que pour les files 2 à 6 (en eau), à indiquer ennote pour les files 1 et 7 (talus, sol dès +1,00). Décision MM, à enregistrer commearbitrage avec ce motif.

- Écartée : Laisser « à fournir » — option proposée par la session, non retenue (E21)
- Écartée : Longueur du pieu 14,30 m — option proposée par la session, non retenue (E21)
- Écartée : Tête → premier ressort des files en eau (−2,00), 3,30 m — option proposée par la session, non retenue (E21)
- Note : La limite se calcule h/400 = 2,85/400 = 7,125 mm, affichée 7,1 mm ; le verdict porte sur la valeur non arrondie.

### E22 — Critère de flèche (L/400)

> L/400 sous charges d'exploitation seules (ELS caractéristique hors G et hors TE :enveloppe LM1 + FR), flèche relative aux appuis (déplacement des appuis retranché) :- chevêtres, travée entre pieux Y = ±2,00 : L = 4,00 m, limite 10 mm ;- dalle, travée entre deux files de chevêtres : L = 5,00 m, limite 12,5 mm ;- pour information, sans verdict principal : consoles de chevêtre (1,00 m, portée  conventionnelle 2 × 1,00 m, limite 5 mm) et débord de dalle en about (0,60 m,  limite 3 mm).Décision MM, à enregistrer comme arbitrage avec ce motif.

- Écartée : Chevêtre seul, L = 4,00 m — option proposée par la session, étendue par MM à la dalle (E22)
- Écartée : Laisser « à fournir » — option proposée par la session, non retenue (E22)

### E23 — Matériaux et sections des fichiers de flexion composée

> Valeurs de la source (rapport AVP, sans terme interdit) :béton C35/45 (§13.7.3, §19.1) pour chevêtres, dalle et bouchons ; acier Fe E500 classe B(§13.7.4), diagramme à branche inclinée (déduit des σs ELU > 435 MPa des §20.4.6, 20.5.5,20.6.7) ; exposition XS3 (gouvernante parmi XC4, XS3, XA1, §13.7.1) ; cnom = 55 mm(§13.7.5) ; wk ≤ 0,20 mm sous ELS fréquent (§13.7.2) ; classe structurale S4, 50 ans(§13.1, §13.6).ds/di : bouchon (carré équivalent 0,52 × 0,52) ds = di = 0,09 m (d = 0,43, §20.4.1) ;chevêtre (b = 1,20, h = 0,90) ds = di = 0,07 m (d = 0,83, §20.5.1) ; dalle (b = 1,00,h = 0,40) ds = di = 0,08 m (d = 0,32, §20.6.1 ; le §20.6.7 donne 0,33, incohérence de lasource notée). Le tube acier sous le bouchon n'est pas exporté (EC3, hors logiciel BA).

- Écartée : Laisser « à fournir » dans l'en-tête — option proposée par la session, non retenue (E23)
- Note : La tête de pieu est lue au nœud du plan moyen (+1,30), dans le bouchon (E14 : bouchon de +0,70 à −0,80, consigne du lot 47 quater : de la tête à −0,80) ; elle est exportée avec la section du bouchon. Le pieu courant (tube acier seul sous −0,80) n'est pas exporté.
