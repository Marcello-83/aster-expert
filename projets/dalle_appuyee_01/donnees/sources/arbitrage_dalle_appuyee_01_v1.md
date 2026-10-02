# Arbitrage de MM — dalle_appuyee_01 (lot 43, phase 2)

**Statut.** Ce document est une proposition de Claude (superviseur). Les décisions
de pratique sont celles de MM : **le lancement de la phase 2 avec ce document vaut
validation par MM** de toutes les lignes. MM confirme sa prise en compte de ce document
et a effectué une relecture et une validation complète.
Chaque décision est à reporter dans la fiche avec l'origine `arbitrage_mm`, et
la référence « arbitrage_dalle_appuyee_01_v1 ».

**Articles d'Eurocode.** Ils sont cités de mémoire par Claude, et non tirés d'une
source indexée. La session les reporte tels quels avec la mention « référence
normative fournie par MM, non indexée ». Elle ne doit pas les présenter comme
vérifiés par l'outil.

---

## A. Décisions de pratique

### P1 — Modélisation de la plaque : **DKT**

- Avec h/L = 0,30/4,00 = 1/13,3, la part de cisaillement transverse dans la
  flèche d'une bande simplement appuyée vaut environ 0,8·E/(κG)·(h/L)², soit
  à peu près 1,3 % avec ν = 0,2 et κ = 5/6. Elle est négligeable devant la
  précision d'ingénieur, et les moments d'une plaque appuyée y sont peu
  sensibles.
- La référence du niveau E est Kirchhoff (Navier). Le DKT est donc la seule
  modélisation qui rend la comparaison exacte, sans correction.
- DST et Q4GG sont écartés : ils ajoutent un écart de modèle qui brouille le
  niveau E, sans bénéfice pour cet ouvrage.
- Variante écartée : DST, en sensibilité. Elle est **hors périmètre** de ce lot.

### P2 — Béton C30/37

- E = Ecm = **33 000 MPa** (EN 1992-1-1, tableau 3.1).
- ν = **0,2**, béton non fissuré (EN 1992-1-1, 3.1.3(4)). Cette valeur est
  figée avant l'écriture du critère du niveau E.
- fck = 30 MPa et fctm = 2,9 MPa (tableau 3.1).
- Le calcul est élastique linéaire et non fissuré.
- **Les flèches obtenues sont des flèches instantanées et non fissurées.** La
  flèche à long terme (fluage, fissuration, EC2 7.4.3) est hors périmètre, et
  le compte rendu doit le dire explicitement.

### P3 — Charges

- **Poids propre** : poids volumique **25 kN/m³** (EN 1991-1-1, annexe A).
  - Il est appliqué par `PESANTEUR` avec g = 9,81 m/s² et RHO =
    25 000 / 9,81 = **2 548,42 kg/m³**, de façon que ρ·g vaille exactement
    25 kN/m³.
  - Contrôle de résultante attendu : 25 × 6 × 4 × 0,30 = **180,0 kN**.
- **Exploitation** : 10 kPa, en charge surfacique de direction globale **−Z**
  (FZ), et non en PRES. Ainsi, le résultat ne dépend pas de l'orientation des
  normales.
  - Contrôle de résultante attendu : **240,0 kN**.
- Les deux cas de charge sont calculés séparément. Navier se compare à chacun
  d'eux.

### P4 — Appuis et étendue du modèle

- **Appui bilatéral** sur les quatre bords : DZ = 0, rotations libres. C'est
  l'hypothèse de Navier, avec les coins retenus.
  - L'appui unilatéral relève d'un calcul de contact non linéaire : hors
    périmètre.
  - La réaction concentrée aux coins, dirigée vers le bas (soulèvement
    empêché), est attendue. Elle est à relever et à commenter comme résultat
    physique, pas comme anomalie.
- **Plan de la dalle** : le blocage est isostatique, sans plus. DX = DY = 0 en
  un coin A, et DY = 0 au coin B, adjacent selon X. Il ne doit y avoir aucune
  redondance avec d'autres conditions (DIAG-001).
- **Dalle entière**, sans symétrie. Le modèle est petit. La symétrie des
  résultats devient alors un **contrôle de niveau D** au lieu d'une hypothèse,
  et le piège des conditions de symétrie des coques disparaît.

### P5 — Combinaisons (P13 de la fiche)

- **Catégorie d'usage : E, aires de stockage** (EN 1991-1-1, tableau 6.1).
  - 10 kPa dépasse les valeurs usuelles des catégories A à D. La catégorie E
    est donc la seule qui soit cohérente avec cette intensité.
  - ψ0 = 1,0, ψ1 = 0,9, ψ2 = 0,8 (EN 1990, tableau A1.1).
- ELU fondamental (EN 1990, 6.10) : **1,35 G + 1,5 Q**. G est toujours
  défavorable sur une travée isostatique, sans cas favorable.
- ELS caractéristique : G + Q. ELS quasi permanent : G + 0,8 Q.
- PRE-016 (quai) n'est retenu **que pour γG = 1,35 et γQ = 1,5**. Le reste de
  ce précédent (actions du quai) ne s'applique pas.

### P6 — Ferraillage (P14 de la fiche)

- **Acier** : B500B, fyk = 500 MPa.
- **Coefficients et αcc** :
  - γc = 1,5 et γs = 1,15 en situation durable ;
  - **ALPHA_CC = 1,0** (annexe nationale française, 3.1.6(1)P), comme au
    quai. La valeur par défaut de Code_Aster, 0,85, n'est **pas** retenue. Ce
    choix doit être écrit explicitement dans le `.comm`.
- **Barres** : HA12 dans les deux directions, en nappe inférieure et en nappe
  supérieure.
- **Distance du parement à l'axe des armatures**, avec un enrobage nominal de
  30 mm, conformément à PRE-018 :
  - lit extérieur, barres portant dans la petite portée (direction Y, 4 m) :
    30 + 6 = **36 mm** ;
  - lit intérieur, barres portant dans la grande portée (direction X, 6 m) :
    30 + 12 + 6 = **48 mm**.
  - Si `CALC_FERRAILLAGE` n'admet qu'**une seule distance par face** pour les
    éléments de plaque, la session le vérifie dans le catalogue 17.4. Dans ce
    cas, elle retient **48 mm** (valeur sécuritaire pour les deux directions)
    et le déclare. La contre-vérification manuelle utilise la même valeur que
    l'outil.
- **ELS en XC1** :
  - wk limite = **0,4 mm** sous combinaison quasi permanente. C'est la valeur
    recommandée par le tableau 7.1N. MM vérifie le tableau 7.1NF de l'annexe
    nationale.
  - σs ≤ 0,8 fyk sous combinaison caractéristique (7.2(5)).
  - Pas de limite sur σc en XC1 (7.2(2) ne vise pas XC1).
- **Ferraillage minimal** :
  - Non-fragilité (9.3.1.1 renvoyant à 9.2.1.1) :
    As,min = max(0,26·fctm/fyk ; 0,0013)·b·d.
  - Maîtrise de la fissuration (7.3.2) : **flexion simple**, donc kc = 0,4,
    k = 1,0 (h ≤ 300 mm), fct,eff = fctm et Act = b·h/2.
  - **PRE-021 (D21, Act = zone tendue complète) ne s'applique pas.** Il
    concernait la poutre de couronnement du quai, tendue. Ici, la dalle est
    fléchie. C'est un cas d'usage du domaine de validité d'un précédent : la
    session le consigne comme tel.
  - Armatures de répartition ≥ 20 % des armatures principales (9.3.1.1(2)).
- **Méthode 2D** : la méthode native de `CALC_FERRAILLAGE` pour les éléments de
  plaque, telle que documentée en 17.4.
  - Contre-vérification indépendante **au centre de la dalle**. Par symétrie,
    Mxy y est nul : le calcul se réduit à deux flexions simples, et le calcul
    manuel est exact.
  - Les **coins**, où Mxy est maximal, sont relevés et commentés. Les
    armatures de coin (9.3.1.3) sont signalées mais ne sont pas calculées.

---

## B. Choix de modélisation : décidés par Claude, non par MM

Les points suivants ne relèvent pas du jugement d'ingénieur sur l'ouvrage. Ce
sont des choix techniques que le niveau E et les contrôles de niveau D
vérifient. **L'outil aurait dû les proposer lui-même** : voir la section C.

| Point | Décision |
|---|---|
| Repère | Origine au coin A (0, 0, 0). X selon 6,00 m, Y selon 4,00 m, Z vers le haut. Plan de la dalle à z = 0, feuillet moyen. |
| Mailles | QUAD4 réguliers, sous la modélisation DKT retenue en P1. La session vérifie dans U3 la formulation affectée aux QUAD4. |
| Suite de convergence | Tailles 0,50 / 0,25 / 0,125 m, soit 12×8, 24×16 et 48×32 mailles. Rapport 2 ; nœud au centre (3,0 ; 2,0) dans les trois maillages. |
| Lecture des moments | `EFGE_NOEU` au nœud central, pour la comparaison à Navier. `EFGE_ELNO` sert seulement à contrôler l'écart de lissage au centre. |
| Noms de groupes | `DALLE` (surface) ; `APPUI_X0`, `APPUI_X6`, `APPUI_Y0`, `APPUI_Y4` (bords) ; `APPUIS` (réunion des bords) ; `P_A` et `P_B` (coins du blocage dans le plan) ; `CENTRE` (nœud). Tous les noms font moins de 24 caractères (DIAG-002). Si la liste de la fiche diffère, la session l'adapte en gardant cette convention. |

Contrôles de niveau D attendus, en plus de ceux de la base :

- résultantes de 180,0 et 240,0 kN ;
- équilibre des réactions, coins compris ;
- symétrie des résultats selon les deux axes ;
- Mxy nul au centre.

Le critère du niveau E reste à écrire par la session **avant** l'exécution.

---

## C. Retour du superviseur sur la phase 1

1. **Fiche.** La fiche est sérieuse et le blocage de la génération a
   fonctionné. Trois points sont acquis :
   - PRE-018 a évité de confondre l'enrobage avec la distance à l'axe ;
   - CA-041 et CA-045 ont été réutilisés ;
   - ALPHA_CC est signalé.

   C'est exactement le comportement attendu de la base.
2. **Trop de questions remontent à MM.** Sur les 31 bloqueurs, environ 15
   portent sur des choix techniques : groupes, repère, mailles, taille,
   `NOEU`/`ELNO`. Un ingénieur n'a pas à les trancher : les contrôles et le
   niveau E les vérifient. Il manque une troisième catégorie dans la fiche,
   « choix de modélisation proposé par l'agent, vérifié par contrôle ». Elle
   sera ajoutée au lot 44. Pour ce lot, la session l'inscrit comme lacune dans
   son journal d'autonomie.
3. **Comptage des interventions.** L'arrêt pour arbitrage était prévu. **Il ne
   compte pas** comme intervention de fond. La section B, elle, compte comme
   **une** intervention : de l'information manquante, fournie par le
   superviseur.
4. **Extensions autorisées dans ce lot**, de façon générique et avec des
   tests :
   - le ferraillage 2D (plaques) dans `projet.yaml` et dans le tronc commun ;
   - l'état « fiche en cours d'arbitrage », s'il est nécessaire pour avancer.
5. **Extensions reportées au lot 44, sauf si elles bloquent** :
   - la création automatique du registre `rex` d'un nouveau projet ;
   - le filtrage de `get_command_schema` par mot-clé (721 000 caractères).
6. **Compte rendu final.** Il doit donner le compteur de consultations de
   `search_connaissances` : au lot 42, il valait 0.
