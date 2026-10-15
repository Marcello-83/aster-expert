# Enregistrement des décisions P29 à P43 de MM — projet `pontons_alu_01` (lot 51)

Décisions de la consigne du lot 51 (MM, échanges internes du 15/10/2026), enregistrées par la même
fonction que `aster-expert fiche enregistrer`. Les textes sont recopiés tels quels de la source par
script (jamais retapés) ; la vérification exige qu'ils y figurent à l'identique.

Source du texte : donnees/sources/consigne_lot51.md
Enregistré le : 2026-10-15T09:00:00-04:00
Domaine de validité par défaut : Calcul linéaire de la palée complète et des trois travées de PONTONS-ALU-01 (lot 51), tel que MM l'a décidé ; hors de ce calcul, la décision n'est pas établie.

### P29 — Navire de projet enveloppe

> - **P29** : navire de projet enveloppe (L 9,0 m, B 3,0 m, tirant d'eau
>   0,9 m, 5,0 t). Il remplace le navire AVP.

- Écartée : Navire de projet de l'AVP — remplacé par le navire enveloppe de la note d'accostage et d'amarrage, indice C (P29)
- Note : Valeurs de l'annexe A de la consigne du lot 51 (note Carro_note_accostage_amarrage.docx, indice C, non lue par la session).

### P30 — Accostage selon PIANC WG 211

> - **P30** : accostage selon PIANC WG 211, par l'arrière, perpendiculaire à la
>   panne :
>   - Ce = 1,0, Cm = 1,1 ;
>   - γE = 1,81 ;
>   - défense D100, longueur de contact Lc = 1 m.

- Écartée : Accostage de l'AVP : 16 kN/m sur 2 m — remplacé par l'accostage PIANC WG 211 de la note, indice C (P30, annexe A)
- Note : Les efforts caractéristiques (AC 23,5 kN, ACA 45 kN sur 1 m) sont ceux de l'annexe A ; aucune action maritime n'est calculée par l'outil.

### P31 — Coefficients de l'accostage

> - **P31** : accostage normal à γ = 1,5, avec ψ0 = 1,0, ψ1 = 0,5, ψ2 = 0. ACA
>   est traité à l'ELU accidentel, γ = 1,0.

- Écartée : Accostage de l'AVP à γ = 1,0, ψ0 = 1,0, ψ1 = ψ2 = 0 — remplacé par γ = 1,5, ψ0 = 1,0, ψ1 = 0,5, ψ2 = 0 (P31)

### P32 — Effort tangentiel d'accostage

> - **P32** : effort tangentiel de 0,7 × l'effort normal. Il est concomitant de
>   l'effort normal, soit horizontal le long de la panne, soit vertical, jamais
>   les deux.

- Écartée : Accostage sans effort tangentiel (AVP) — effort tangentiel de 0,7 × l'effort normal, concomitant, horizontal le long de la panne ou vertical (P32)

### P33 — Amarrage : cas et coefficient

> - **P33** : cas d'amarrage AM local, AM1 et AM2, γ = 1,5. Ce γ remplace le
>   1,3 de l'AVP. La note ne donne pas de ψ pour l'amarrage : conserver ceux du
>   projet et les citer dans le compte rendu.

- Écartée : Amarrage de l'AVP, 8,0 kN sur deux points, γ = 1,3 — remplacé par AM local, AM1 et AM2 à γ = 1,5 (P33, annexe A)
- Note : ψ de l'amarrage conservés du projet : ψ0 = 0,77, ψ1 = 0,77, ψ2 = 0,2 (lot 50, D5).

### P34 — Taquets et amarrage accidentel

> - **P34** : taquets de 5 t. La structure locale est vérifiée sous 49 kN à
>   l'ELU accidentel (AMF).

- Écartée : Amarrage accidentel non considéré (AVP) — AMF 49 kN sur un taquet à l'ELU accidentel (P34, annexe A)
- Note : Fiche fournisseur des taquets de 5 t : point ouvert.

### P35 — Travée, largeur chargée, appuis côté quai et jeu de combinaisons

> - **P35** : travée de 6,25 m confirmée.
>   - Largeur chargée du platelage : 2,00 m.
>   - Appuis côté quai inchangés : une rotule fixe, une rotule guidée en Y.
>   - Jeu B′ seul retenu, plus l'ELU accidentel. Les jeux A et B ne sont plus
>     calculés.

- Écartée : Jeux A (S2) et B (PRO) — ne sont plus calculés : jeu B′ seul, plus l'ELU accidentel (P35)
- Note : Remplace le choix entre B et B′ laissé ouvert par P27 : B′ est retenu.

### P36 — Poutres principales en tube carré

> - **P36** : poutres principales en **tube carré** soudé (solution soudée
>   conservée), alliage 6082-T6, angles vifs.
>   - Section de référence : 200 × 200 × 8.
>   - Balayage : 180 × 180 × 8 et 200 × 200 × 10.
>   - Pannes, montants et diagonales inchangés.

- Écartée : Poutres principales MP1200 (P4) — remplacées par un tube carré soudé 200 × 200 × 8 en 6082-T6, angles vifs (P36)
- Note : Balayage de section : variantes S1 (180 × 180 × 8) et S3 (200 × 200 × 10).

### P37 — Critères de flèche

> - **P37** : critères de flèche, appliqués par le superviseur :
>   - L/200 à l'ELS fréquent ;
>   - L/150 à l'ELS caractéristique.

- Écartée : Flèches rapportées sans critère (P14) — critères L/200 (ELS fréquent) et L/150 (ELS caractéristique), appliqués par le superviseur (P37)
- Note : L'outil rapporte les flèches ; il n'applique pas les critères.

### P38 — Appareils d'appui en élastomère fretté

> - **P38** : **appareils d'appui en élastomère fretté**, type B, NF EN 1337-3,
>   tableau 3 : 200 × 300 mm, 3 feuillets de 8 mm (Te = 24 mm), G = 0,9 MPa.
>   Raideurs selon NF EN 1337-3 §5.3.3.7, reprises par le guide Sétra
>   « Appareils d'appui en élastomère fretté », annexe 1, tableau A.2 :
>   - **Kx = Ky = G·A/Te** = 0,9 × 60 000 / 24 = **2,25 kN/mm** ;
>   - **Kz** = [Σ tᵢ/A′ · (1/(5·G·S²) + 1/Eb)]⁻¹, avec :
>     - A′ = 190 × 290 mm² ;
>     - S = A′/(2·(a′+b′)·tᵢ) = 7,17 ;
>     - Eb = 2 000 MPa ;
>     - d'où **Kz ≈ 476 kN/mm** ;
>   - **Kθ = 0** : rotule, formule simplifiée du guide.
>   Les ressorts travaillent **aussi en traction**. Toute traction est rapportée
>   comme un **effort de retenue** à reprendre par un dispositif
>   anti-soulèvement. Sensibilité sur Kx et Ky : × 0,5 et × 2. Le facteur 2
>   correspond à Gdyn = 1,8 MPa (guide Sétra §3.2.2).

- Écartée : Profilés supports soudés au tablier et articulés sur le chevêtre (P18) — remplacés par des appareils d'appui en élastomère fretté sous les poutres principales (P38)
- Note : Raideurs recalculées par le générateur à partir des dimensions (Kx = Ky = 2,25 kN/mm ; Kz ≈ 476 kN/mm) ; sensibilité N− et N+ sur Kx et Ky.

### P39 — Profilé support encastré sur le chevêtre

> - **P39** : profilé support 150 × 150 × 7, haut de 0,15 m, **encastré** sur le
>   chevêtre (platine boulonnée sur tiges scellées). Le néoprène est posé sur le
>   profilé, sous le nœud de la poutre principale.

- Écartée : Profilé support articulé en pied sur le chevêtre (P18) — encastré sur le chevêtre, platine boulonnée sur tiges scellées (P39)

### P40 — Palée complète

> - **P40** : palée complète, avec :
>   - 4 piles Ø 0,50 encastrées dans la semelle ;
>   - 4 poutres BA en anneau ;
>   - une petite travée aluminium entre les deux chevêtres.

- Écartée : Demi-semelle et chevêtre seul (lot 50) — palée complète : 4 piles, anneau BA de 4 poutres, petite travée (P40)
- Note : La géométrie de la petite travée (un montant à chaque extrémité, une diagonale) est une hypothèse de la consigne, point ouvert.

### P41 — Hauteur des piles

> - **P41** : hauteur des piles variable le long du ponton. Une palée a 4 piles
>   de même hauteur. Hauteurs étudiées : 1,32 m et 4,0 m.

- Écartée : Hauteur unique de 1,32 m (lot 50) — hauteurs étudiées 1,32 m et 4,0 m (P41)
- Note : Pour H = 4,0 m, la semelle est inchangée (dimensions et raideurs) et abaissée au pied des piles : point ouvert.

### P42 — Éclissages entre travées

> - **P42** : éclissages boulonnés entre travées, au droit des appuis, en deux
>   variantes :
>   - **articulé** : rotations libérées autour de y et de z locaux de la
>     poutre ;
>   - **continu**.

- Écartée : Travées indépendantes (une seule travée modélisée au lot 50) — éclissages boulonnés au droit des appuis, articulé ou continu (P42)

### P43 — Section des poutres BA de l'anneau

> - **P43** : section des poutres BA de l'anneau (chevêtres et longrines) portée
>   à **0,40 × 0,40**. La section 0,25 × 0,40 est écartée sans calcul,
>   décision de MM. Motifs, établis par le superviseur à la main :
>   - assise de la platine et des tiges d'ancrage du profilé support, avec des
>     distances aux bords compatibles avec la NF EN 1992-4 ;
>   - reprise de la traction des ancrages anti-soulèvement ;
>   - torsion des chevêtres sous effort longitudinal des néoprènes, alors que la
>     tête de pile est articulée ;
>   - enrobage du goujon de tête de pile ;
>   - poids propre favorable à la traction des piles.

- Écartée : Section 0,25 × 0,40 (P3) — écartée sans calcul par MM pour les motifs cités (P43)
