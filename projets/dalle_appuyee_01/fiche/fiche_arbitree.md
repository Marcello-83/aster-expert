# Fiche arbitrée -- DALLE-APPUYEE-01

Décisions de MM reportées de `arbitrage_dalle_appuyee_01_v1` (copie : `donnees/sources/arbitrage_dalle_appuyee_01_v1.md`), origine `arbitrage_mm`. Les articles d'Eurocode sont des références normatives fournies par MM, non indexées par l'outil.

## Point 0 — Objet et périmètre du calcul

**Retenu** (MM) : Calcul élastique linéaire et non fissuré de la dalle seule (plaque), sous chargement statique. Les flèches obtenues sont des flèches instantanées et non fissurées ; la flèche à long terme (fluage, fissuration, EC2 7.4.3) est hors périmètre, et le compte rendu le dit explicitement. Le ferraillage est calculé par CALC_FERRAILLAGE sur les efforts élastiques.

*Justification* : Décision P2 de MM : « Le calcul est élastique linéaire et non fissuré. Les flèches obtenues sont des flèches instantanées et non fissurées. »

*Domaine de validité* : Flèches instantanées seulement ; aucune flèche différée, aucun effet de la fissuration sur la raideur ; EC2 7.4.3 hors périmètre.

*Variantes écartées* :
- Estimation des flèches à long terme (fluage, fissuration). — Hors périmètre de ce lot (P2).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P2 ; norme : EN 1992-1-1, 7.4.3 — référence normative fournie par MM, non indexée

## Point 1 — Choix de la modélisation de plaque de la dalle (h/L = 1/13,3)

**Retenu** (MM) : Modélisation DKT (Love-Kirchhoff) pour toute la dalle.

*Justification* : Décision P1 de MM : avec h/L = 0,30/4,00 = 1/13,3, la part de cisaillement transverse dans la flèche d'une bande simplement appuyée vaut environ 0,8·E/(κG)·(h/L)², soit à peu près 1,3 % avec ν = 0,2 et κ = 5/6, négligeable devant la précision d'ingénieur ; les moments d'une plaque appuyée y sont peu sensibles. La référence du niveau E est Kirchhoff (Navier) : DKT est la seule modélisation qui rend la comparaison exacte, sans correction.

*Domaine de validité* : Déformation d'effort tranchant négligée (environ 1,3 % de la flèche selon l'estimation de MM) ; aucune étude de sensibilité DST dans ce lot.

*Variantes écartées* :
- DST (cisaillement transverse), y compris en sensibilité. — Ajoute un écart de modèle qui brouille le niveau E, sans bénéfice pour cet ouvrage ; la sensibilité DST est hors périmètre de ce lot (P1).
- Q4GG (modélisation du cas test SSLS127). — Même raison que DST : écart de modèle par rapport à Kirchhoff (P1).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P1

## Point 4 — Valeurs et application des charges : poids volumique, g, forme de la charge d'exploitation

**Retenu** (MM) : Deux cas de charge calculés séparément, chacun comparé à Navier. G : poids propre, poids volumique 25 kN/m³, appliqué par PESANTEUR avec g = 9,81 m/s² et RHO = 25 000 / 9,81 = 2 548,42 kg/m³, de façon que ρ·g vaille exactement 25 kN/m³ ; résultante attendue 25 × 6 × 4 × 0,30 = 180,0 kN. Q : exploitation de 10 kPa en charge surfacique de direction globale −Z (FORCE_COQUE/FZ), et non en PRES, pour ne pas dépendre de l'orientation des normales ; résultante attendue 240,0 kN.

*Justification* : Décision P3 de MM.

*Domaine de validité* : Exploitation uniforme sur toute la dalle ; aucune disposition partielle. RHO est un artifice pour obtenir ρ·g = 25 kN/m³ (le poids volumique du béton armé, pas sa masse volumique réelle) : il n'est valable qu'en statique.

*Variantes écartées* :
- RHO = 2500 kg/m³ et g = 9,81 m/s² (poids 24,5 kN/m³). — MM retient 25 kN/m³ exactement (P3).
- Exploitation par FORCE_COQUE/PRES après ORIE_NORM_COQUE. — Le résultat dépendrait de l'orientation des normales (P3).
- Dispositions partielles (damier) de l'exploitation. — Non retenues par P3 : exploitation uniforme de 10 kPa.

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P3 ; norme : EN 1991-1-1, annexe A — référence normative fournie par MM, non indexée

## Point 5 — Paramètres élastiques du béton C30/37 (E, ν) et hypothèse de béton non fissuré

**Retenu** (MM) : Béton C30/37 : E = Ecm = 33 000 MPa, ν = 0,2 (béton non fissuré), fck = 30 MPa, fctm = 2,9 MPa. Calcul élastique linéaire et non fissuré. ν est figé avant l'écriture du critère du niveau E.

*Justification* : Décision P2 de MM.

*Domaine de validité* : Béton non fissuré : raideur de flexion surestimée pour une dalle fissurée ; flèches instantanées seulement.

*Variantes écartées* :
- ν = 0 (béton fissuré). — MM retient le béton non fissuré, ν = 0,2 (P2).
- Module effectif à long terme. — Flèche à long terme hors périmètre (P2).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P2 ; norme : EN 1992-1-1, tableau 3.1 — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, 3.1.3(4) — référence normative fournie par MM, non indexée

## Point 6 — Représentation de l'appui simple et des mouvements de corps rigide de membrane

**Retenu** (MM) : Dalle entière, sans symétrie. Appui bilatéral sur les quatre bords : DZ = 0 sur `APPUIS`, rotations libres (hypothèse de Navier, coins retenus). Plan de la dalle : blocage isostatique, DX = DY = 0 au coin `P_A` et DY = 0 au coin `P_B`, adjacent selon X, sans aucune redondance avec d'autres conditions (DIAG-001). La réaction concentrée aux coins, dirigée vers le bas, est attendue et se commente comme résultat physique. La symétrie des résultats selon les deux axes est un contrôle de niveau D.

*Justification* : Décision P4 de MM.

*Domaine de validité* : Appui bilatéral : un appui réel qui laisse les coins se soulever (contact unilatéral) n'est pas représenté.

*Variantes écartées* :
- Appui unilatéral (contact). — Calcul de contact non linéaire, hors périmètre (P4).
- Quart de dalle avec deux plans de symétrie. — Le modèle est petit ; la symétrie devient un contrôle de niveau D, et le piège des conditions de symétrie des coques disparaît (P4).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P4

## Point 9 — Repère global, origine et unités du modèle

**Retenu** (Claude (superviseur), section B de arbitrage_dalle_appuyee_01_v1 — document validé par MM) : Origine au coin A (0, 0, 0). X selon le côté de 6,00 m, Y selon le côté de 4,00 m, Z vers le haut. Plan de la dalle à z = 0 (feuillet moyen). Unités m, N, Pa, kg.

*Justification* : Section B de l'arbitrage (choix de modélisation vérifié par le niveau E et les contrôles D). Repère de la série de Navier (origine au coin).

*Domaine de validité* : Convention de repère : sans limite physique.

*Variantes écartées* :
- Origine au centre de la dalle. — Non retenue par la section B (origine au coin A).
- Précédent PRE-012 (repère du quai). — Repère propre au quai (axe de tube, cote CM) ; seule la déclaration du repère et des unités dans la fiche est reprise.

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, B, repère

## Point 10 — Discrétisation : type de mailles, taille, étude de convergence, nœud au centre

**Retenu** (Claude (superviseur), section B de arbitrage_dalle_appuyee_01_v1 — document validé par MM) : Mailles QUAD4 régulières sous la modélisation DKT. Suite de convergence de rapport 2 : tailles 0,50 / 0,25 / 0,125 m, soit 12×8, 24×16 et 48×32 mailles, avec un nœud au centre (3,0 ; 2,0) dans les trois maillages. Moments au centre lus en EFGE_NOEU au nœud `CENTRE` pour la comparaison à Navier ; EFGE_ELNO sert seulement à contrôler l'écart de lissage au centre.

*Justification* : Section B de l'arbitrage. Le précédent PRE-013 (quai) n'avait fait l'objet d'aucune étude de convergence : la suite de rapport 2 en tient lieu ici.

*Domaine de validité* : Convergence établie aux seuls points de comparaison (centre) ; les coins, où Mxy est maximal, ne sont pas couverts par la référence de Navier au même titre.

*Variantes écartées* :
- TRIA3. — Non retenus par la section B (QUAD4 réguliers).
- Moments lus en EFGE_ELNO d'une maille pour la comparaison. — EFGE_ELNO ne sert qu'à contrôler l'écart de lissage (section B).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, B, mailles, suite de convergence, lecture des moments

## Point 13 — Combinaisons d'actions ELU et ELS (poids propre G, exploitation Q)

**Retenu** (MM) : Catégorie d'usage E (aires de stockage) : ψ0 = 1,0, ψ1 = 0,9, ψ2 = 0,8. ELU fondamental : 1,35 G + 1,5 Q, G toujours défavorable (aucun cas favorable). ELS caractéristique : G + Q. ELS quasi permanent : G + 0,8 Q. PRE-016 (quai) n'est retenu que pour γG = 1,35 et γQ = 1,5.

*Justification* : Décision P5 de MM : 10 kPa dépasse les valeurs usuelles des catégories A à D ; la catégorie E est la seule cohérente avec cette intensité. G est toujours défavorable sur une travée isostatique.

*Domaine de validité* : Dalle isostatique sous deux actions (G, Q) ; le reste de PRE-016 (actions du quai) ne s'applique pas.

*Variantes écartées* :
- γG favorable (1,0 G + 1,5 Q). — G est toujours défavorable sur une travée isostatique (P5).
- Catégories d'usage A à D. — 10 kPa dépasse leurs valeurs usuelles (P5).
- Reste du précédent PRE-016 (actions G, EAU, Q1, Q3, A du quai). — Actions propres au quai (P5).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P5 ; precedent_projet : PRE-016 — quai_cw_test_01, point 13 (projets/quai_cw_test_01/fiche/hypotheses_combiwall_reference_arbitree.json), décidé par MM le 2026-09-25 ; norme : EN 1991-1-1, tableau 6.1 — référence normative fournie par MM, non indexée ; norme : EN 1990, tableau A1.1 — référence normative fournie par MM, non indexée ; norme : EN 1990, 6.10 — référence normative fournie par MM, non indexée

## Point 14 — Ferraillage : acier, distance parement–axe, ELS en XC1 (contraintes, fissuration), ferraillage minimal

**Retenu** (MM) : Acier B500B, fyk = 500 MPa. γc = 1,5 et γs = 1,15 en situation durable ; ALPHA_CC = 1,0 écrit explicitement dans le .comm (la valeur par défaut 0,85 n'est pas retenue). Barres HA12 dans les deux directions, nappes inférieure et supérieure. Distance du parement à l'axe, enrobage nominal 30 mm : lit extérieur (barres portant dans la petite portée, Y) 30 + 6 = 36 mm ; lit intérieur (barres portant dans la grande portée, X) 30 + 12 + 6 = 48 mm. CALC_FERRAILLAGE n'admet qu'une distance par face en 2D (catalogue 17.4 : C_INF et C_SUP, un réel chacun) : 48 mm est retenu pour les deux directions et déclaré ; la contre-vérification manuelle utilise la même valeur. ELS en XC1 : wk limite = 0,4 mm sous combinaison quasi permanente ; σs ≤ 0,8 fyk sous combinaison caractéristique ; pas de limite sur σc en XC1. Ferraillage minimal : non-fragilité As,min = max(0,26·fctm/fyk ; 0,0013)·b·d ; maîtrise de la fissuration en flexion simple, kc = 0,4, k = 1,0, fct,eff = fctm, Act = b·h/2 ; armatures de répartition ≥ 20 % des armatures principales. Méthode 2D native de CALC_FERRAILLAGE pour les plaques ; contre-vérification indépendante au centre de la dalle (Mxy nul par symétrie) ; coins relevés et commentés, armatures de coin signalées, non calculées.

*Justification* : Décision P6 de MM. Distance à l'axe selon PRE-018 (enrobage mesuré au nu de l'armature). MM écarte « PRE-021 (D21, Act = zone tendue complète) », poutre tendue du quai : aucune entrée PRE-021 n'existe dans la base (PRE-001 à PRE-018) et D21 n'est enregistrée dans aucune fiche du dépôt ; le domaine de validité invoqué est consigné tel quel (dalle fléchie, pas tendue).

*Domaine de validité* : Une seule distance (48 mm) pour les deux directions : défavorable pour le lit extérieur (Y, 36 mm réels). wk = 0,4 mm est la valeur recommandée du tableau 7.1N ; MM vérifie le tableau 7.1NF de l'annexe nationale. Armatures de coin (9.3.1.3) non calculées.

*Variantes écartées* :
- ALPHA_CC = 0,85 (défaut de CALC_FERRAILLAGE). — Annexe nationale française : αcc = 1,0, comme au quai (P6).
- Deux distances par face (36 mm en Y, 48 mm en X). — Une seule distance par face en 2D dans CALC_FERRAILLAGE ; 48 mm, sécuritaire, est retenu (P6).
- Précédent PRE-017 (XS3, wk = 0,2 mm, enrobage 65 mm du quai). — Exposition XC1 et enrobage de 30 mm donnés par MM.
- Act = zone tendue complète (« PRE-021 / D21 » cité par MM). — Concerne une poutre tendue ; la dalle est fléchie (P6).
- Calcul des armatures de coin (9.3.1.3). — Signalées, non calculées (P6).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_v1, A, P6 ; precedent_projet : PRE-018 — quai_cw_test_01, point 14 (projets/quai_cw_test_01/fiche/hypotheses_combiwall_reference_arbitree.json), décidé par MM le 2026-09-28 ; norme : EN 1992-1-1, tableau 2.1N — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, 3.1.6(1)P (annexe nationale française) — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, tableau 7.1N — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, 7.2(5) — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, 9.3.1.1 et 9.2.1.1 — référence normative fournie par MM, non indexée ; norme : EN 1992-1-1, 7.3.2 — référence normative fournie par MM, non indexée

## Point 14 — Paramètres ELS obligatoires de CALC_FERRAILLAGE en 2D (ALPHA_E, SIGC_*_ELS, SIGC_ELS_QP, KT, EYS)

**Retenu** (MM) : ALPHA_E = 15. SIGC_INF_ELS = SIGC_SUP_ELS = 0,6 fck = 18 MPa, avec un second calcul à valeur non contraignante pour montrer que la limite n'est pas active (rapportée si elle l'est). SIGC_ELS_QP = 0,45 fck = 13,5 MPa. KT = 0,4 (chargement de longue durée). EYS = 200 000 MPa (Es = 200 GPa, EN 1992-1-1, 3.2.7(4) ; décision de MM au lot 44, au lieu des 210 GPa du lot 43).

*Justification* : Réponses de MM aux questions de la session (complément d'arbitrage, donnees/sources/arbitrage_dalle_appuyee_01_complement_els.md) : ces paramètres sont obligatoires en 2D selon U4.81.42 et l'arbitrage v1 dit « pas de limite sur σc en XC1 ». Lot 44, décision de MM : « La valeur de 210 GPa est celle des aciers de construction (EN 1993). La réglementation du béton armé retient 200 GPa pour les armatures. »

*Domaine de validité* : La limite σc = 18 MPa est un artifice de saisie exigé par la commande, sans exigence de l'EC2 en XC1 : son inactivité est vérifiée par la sensibilité. αe = 15 est maintenu : c'est un coefficient d'équivalence de long terme, choisi délibérément, indépendant de Es (lot 44).

*Variantes écartées* :
- ALPHA_E = Es/Ecm (≈ 6,1). — MM retient 15.
- SIGC_*_ELS non contraignant sans sensibilité. — MM retient 0,6 fck et demande la sensibilité.
- KT = 0,6 (courte durée). — Longue durée.
- EYS = 210 000 MPa (décision du lot 43). — valeur des aciers de construction (EN 1993) ; le béton armé retient 200 GPa pour les armatures (lot 44).

*Sources* : arbitrage_mm : arbitrage_dalle_appuyee_01_complement_els (réponses de MM en séance, lot 43, phase 2) ; arbitrage_mm : consigne du lot 44 (docs/lots/lot44_consigne.md), module de l'acier Es = 200 GPa ; référence normative fournie par MM, non indexée

## Points établis par la documentation

- Point 1 — Modélisations de plaque recevables pour une dalle plane et leur cinématique
- Point 1 — Caractéristiques de plaque : épaisseur et repère local (AFFE_CARA_ELEM/COQUE)
- Point 4 — Application du poids propre et d'une charge surfacique uniforme sur une plaque
- Point 5 — Opérateur de résolution et loi élastique isotrope
- Point 6 — Appui simple d'une dalle en plaque et blocages de symétrie dans le cas test officiel
- Point 14 — CALC_FERRAILLAGE en 2D : options disponibles dans le catalogue 17.4
- Point 1 — Critère d'élancement (épaisseur/longueur caractéristique) pour une modélisation de coque/plaque
- Point 1 — Efforts généralisés (EFGE_ELNO, EFGE_NOEU) sous ELAS_COQUE (DKT) : exactitude et indépendance vis-à-vis de EPAIS et de CISA_L/CISA_T
- Point 4 — Poids propre des éléments ELAS_COQUE sous PESANTEUR en statique : sens de RHO
- Point 4 — Application d'une force surfacique de direction globale fixe sur une empreinte d'éléments de coque courbes (et non d'une pression normale à la paroi)
- Point 6 — Conditions de symétrie par rapport à un plan X = constante pour des coques DKT et des poutres POU_D_E
- Point 6 — Résultante des réactions nodales (REAC_NODA) sous ELAS_COQUE lorsque la rigidité de flexion n'est pas MEMB × EPAIS² / 12
- Point 14 — État des lieux des commandes de ferraillage de Code_Aster 17.4 (CALC_FERRAILLAGE, COMBINAISON_FERRAILLAGE, POST_COMBINAISON, VERI_FERRAILLAGE, POST_VERI_FERRAILLAGE)
- Point 14 — Ferraillage minimal de CALC_FERRAILLAGE en 1D (FERR_MIN, FERR_MIN_FISS) : ce qui est appliqué, sur quelles faces, et dépendance aux unités
- Point 14 — CALC_FERRAILLAGE en 2D sur une plaque DKT (méthode de Capra et Maury) : faces, flexion simple et effet de MXY

## Noms de groupes (tranchés)

- `DALLE` (maille, point 1) : Toutes les mailles QUAD4 de la dalle (surface).
- `APPUI_X0` (maille, point 6) : Bord X = 0 (SEG2).
- `APPUI_X6` (maille, point 6) : Bord X = 6,00 (SEG2).
- `APPUI_Y0` (maille, point 6) : Bord Y = 0 (SEG2).
- `APPUI_Y4` (maille, point 6) : Bord Y = 4,00 (SEG2).
- `APPUIS` (noeud, point 6) : Réunion des nœuds des quatre bords : DZ = 0.
- `P_A` (noeud, point 6) : Coin A (0, 0, 0) : DX = DY = 0.
- `P_B` (noeud, point 6) : Coin B (6, 0, 0), adjacent selon X : DY = 0.
- `CENTRE` (noeud, point 10) : Nœud central (3,0 ; 2,0) : comparaison à Navier.

## Bloqueurs de génération : 0

- Aucun.
