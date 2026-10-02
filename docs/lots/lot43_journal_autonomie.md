# Lot 43 — Journal d'autonomie (dalle appuyée)

Tenu au fil de la session. Chaque ligne est classée :

- **BLOCAGE** : impossible d'avancer sans MM ;
- **MANQUE** : information ou consigne absente, contournée ou laissée « à fournir » ;
- **ÉVITÉ** : consultation de la base (`connaissances/`) ou de la documentation qui a évité une erreur ;
- **LACUNE** : connaissance ou capacité de l'outil qui manquait pour traiter seul ce type d'ouvrage ;
- **OUTIL** : défaut ou inconfort d'un outil (MCP, CLI, interface projet).

## Phase 1 — avant arbitrage (fiche proposée)

| # | Classe | Constat | Conséquence |
|---|---|---|---|
| 1 | LACUNE | La section `rebar` de `projet.yaml` (`RebarMember`) ne connaît que le ferraillage **1D** (schéma `ssll13*`, efforts `EFPOUT_<cas>` de poutre). Rien pour une plaque (`TYPE_STRUCTURE='2D'`). La section `combinations` ne combine que des tables d'efforts de poutre (`N, VY, VZ, MT, MFY, MFZ`). | Le ferraillage 2D et ses combinaisons ne passeront pas par `aster-expert projet … combinaisons/ferraillage` : à écrire dans le `.comm` ou dans le projet, après arbitrage. |
| 2 | OUTIL | `get_command_schema(command, keyword=…)` renvoie aussi **tout** le schéma de la commande : 67 000 caractères pour `AFFE_CARA_ELEM/COQUE`, 109 000 pour `AFFE_CHAR_MECA/FORCE_COQUE`, 721 000 pour `DEFI_MATERIAU/ELAS`, au-delà de la limite de sortie de la session (fichier sauvegardé, relu par `jq`). | Lecture possible mais détournée ; le filtre par mot-clé n'allège rien. |
| 3 | ÉVITÉ | `PRE-018` (quai, point 14) : l'enrobage nominal se mesure au nu de l'armature la plus proche ; la distance parement–axe (`C_SUP`/`C_INF`) n'est **pas** l'enrobage. MM donne « enrobage de 30 mm » : le prendre pour `C_INF` aurait surestimé le bras de levier (erreur commise au lot 38 sur le quai). | Distance à l'axe laissée à MM (point 14), avec le précédent proposé. |
| 4 | ÉVITÉ | `CA-045` : en 2D, `MXX > 0` tend la face **supérieure** (`DNSXS`), la face « supérieure » étant celle du côté de la normale ; `ORIE_NORM_COQUE` fixe donc la nappe. Sans ce constat, la nappe inférieure d'une dalle appuyée (moments positifs au sens usuel) aurait pu être lue sur la mauvaise face. | Orientation des normales à imposer et à contrôler (point 6/10). |
| 5 | ÉVITÉ | `CA-041` / `REF-013` : `FERR_MIN='EC2'` n'est juste qu'en `UNITE_CONTRAINTE='MPa'`. | Unité imposée au `.comm` de ferraillage. |
| 6 | ÉVITÉ | `CA-023` / `CA-026` : sous `ELAS_COQUE`, `REAC_NODA` est faux si `FLEX ≠ MEMB·EPAIS²/12`. La dalle sera en `ELAS` isotrope + `EPAIS` (cohérent par construction, cas « exact » de `CA-023`) : `REAC_NODA` y est lisible. Sans la base, le doute aurait demandé un essai. | Contrôle d'équilibre par `REAC_NODA` aux appuis admissible, à confirmer à l'exécution. |
| 7 | MANQUE | MM ne donne ni la nuance d'acier, ni la catégorie d'usage de l'exploitation (donc ψ0, ψ1, ψ2), ni E/ν du béton, ni le poids volumique, ni l'ouverture de fissure limite en XC1, ni le diamètre des barres. | Valeurs « à fournir » dans `donnees/dalle_model_data.yaml`, questions dans la fiche. |
| 8 | LACUNE | Aucun précédent sur les paramètres d'un béton (E, ν, ρ), sur la convergence de maillage, ni sur la représentation d'un appui simple (`search_connaissances` : « module béton », « convergence maillage », « appui » → seul `PRE-014`, appui vertical d'un écran, hors sujet). | Points pratiques proposés sans précédent. |
| 9 | MANQUE | h/L = 0,30/4,00 = 1/13,3 : entre la limite « plaque mince, Kirchhoff, DKT conseillé » (h/L < 1/20) et la limite « plaque épaisse, DST/Q4G » de U2.02.01. La documentation ne tranche pas cette zone ; la référence de Navier demandée est de Kirchhoff. | Choix DKT / DST / Q4GG remis à MM (point 1), avec la conséquence sur le niveau E. |
| 10 | LACUNE | `render_decision_sheet` (document d'arbitrage) n'affiche ni les `options_considered` de l'entrée pratique — là où `propose_precedent` écrit le texte du précédent — ni les constats référencés (`FindingReference`) tant que la fiche n'est pas résolue contre la base. MM n'aurait pas vu le contenu des précédents proposés. | Corrigé dans le tronc commun (affichage des options proposées), avec test. |
| 11 | LACUNE | L'interface projet n'admet pas d'état « fiche en cours d'arbitrage » : `projet.yaml` exige les invariants du maillage et un générateur (`mesh`, `comm` obligatoires). Un projet ne peut donc pas être déclaré, ni passer `verifier`, avant que les groupes et le maillage soient décidés. | `projet.yaml` écrit après arbitrage ; avant, le projet n'a que fiche, données et sources. |
| 12 | OUTIL | `propose_precedent` produit une entrée sans trace de recherche, `record_unfounded_point` une trace sans précédent : la consigne du skill (« un précédent se cite dans la trace du point non fondé et se propose ») oblige à fusionner les deux sorties à la main. | Fusion faite dans le script de la fiche (`_with_precedent`), entrée toujours non tranchée. |
| 13 | LACUNE | L'outil n'indexe aucune norme (EN 1990, EN 1991-1-1, EN 1992-1-1) : les articles cités dans les options (poids volumique, Ecm, ν, ψ, wk en XC1, γ, αcc) viennent de la connaissance de la session, sans texte vérifiable. | Avertissement en tête du document d'arbitrage ; chaque renvoi est à vérifier par MM. |
| 14 | OUTIL | Le schéma de fiche n'a pas de type de source « cas test officiel » (`DocumentarySource`, `CatalogueSource`, `ExecutionSource`) : `ssls127d.comm`, `ssls135a.comm` sont cités dans le texte des justifications, avec le commit de `codeaster-src`, comme au quai. | Citation non vérifiable mécaniquement. |
| 15 | MANQUE | `aster-expert rex dalle_appuyee_01` refuse sans registre `connaissances/rex/<projet>.yaml` ; rien ne le crée à la naissance d'un projet. | Registre minimal écrit à la main (`project`, `case_roots`). |
| 16 | ÉVITÉ | SSLS127 (V3.03.127, `ssls127d.comm`) : cas officiel d'une dalle appuyée sur 4 côtés ; il montre l'appui simple par `DZ = 0` seul et les blocages de symétrie `DY, DRX` / `DX, DRY`, différents de `CA-030` (qui ajoute `DRZ` pour DKT). Sans ce cas, la condition de symétrie du quai aurait été reprise telle quelle. | Les deux écritures rapportées au point 6 sans être départagées. |
| 17 | ÉVITÉ | `CALC_FERRAILLAGE` : `ALPHA_CC` vaut 0,85 par défaut dans le catalogue, alors que le quai a retenu 1,0 (`projet.yaml` du quai). Un `.comm` sans `ALPHA_CC` explicite aurait pris 0,85 sans le dire. | Valeur à fixer par MM (point 14). |

### Bilan de la phase 1

- Arrêt volontaire : fiche prête à arbitrer, remise à MM (`projets/dalle_appuyee_01/fiche/fiche_a_arbitrer.md`).
- Blocages vrais (impossible d'avancer sans MM) : les 9 points pratiques, les 9 noms de groupes et les 13 valeurs « à fournir ».
- Aucune intervention de MM pendant la phase 1.

## Phase 2 — après arbitrage

Interventions de MM comptées (règle de la section C de l'arbitrage) : l'arrêt pour
arbitrage ne compte pas ; la section B compte pour **une** intervention (information
manquante fournie par le superviseur) ; les questions ELS ci-dessous comptent pour
**une** seconde intervention.

| # | Classe | Constat | Conséquence |
|---|---|---|---|
| 18 | OUTIL | L'origine `arbitrage_mm` demandée par MM n'existait pas dans le schéma (`PracticeOrigin` : `norme`, `precedent_projet`, `decision_ingenieur`). | Ajoutée au tronc commun (date obligatoire, comme `decision_ingenieur`), deux tests. |
| 19 | MANQUE | L'arbitrage cite « PRE-021 (D21, Act = zone tendue complète) » : aucune entrée PRE-021 dans la base (PRE-001 à PRE-018), et D21 n'est enregistrée dans aucune fiche du dépôt (elle n'apparaît que comme exemple dans la consigne du lot 42). | Consigné tel quel dans la justification du point 14 ; la décision (Act = b·h/2) n'en dépend pas. |
| 20 | LACUNE | La fiche n'a pas de catégorie « choix de modélisation proposé par l'agent, vérifié par contrôle » (section C, 2) : les choix de la section B (repère, mailles, convergence, lecture des moments, groupes) ont dû être enregistrés comme décisions pratiques d'origine `arbitrage_mm`, avec `decided_by` = « Claude (superviseur), section B — document validé par MM ». | Catégorie à créer au lot 44 (annoncée par MM). |
| 21 | BLOCAGE | U4.81.42 rend **obligatoires** en 2D, pour l'ELS, `SIGC_INF_ELS`/`SIGC_SUP_ELS`, `ALPHA_E`, `SIGC_ELS_QP`, `KT` (et `PHI_*`, `WMAX_*`), alors que l'arbitrage dit « pas de limite sur σc en XC1 » et ne fixe ni αe, ni KT, ni σc QP, ni Es. Décisions de pratique : posées à MM (quatre questions, une réponse). | Complément d'arbitrage `donnees/sources/arbitrage_dalle_appuyee_01_complement_els.md` ; entrée pratique ajoutée au point 14. Seconde intervention. |
| 22 | LACUNE | U4.81.42 dit que `CALC_FERRAILLAGE` lit `EFGE_ELNO` (« But »), mais ni U4.81.42 ni R7.04.05 ne disent comment les valeurs aux nœuds d'une maille sont réduites à une densité par maille. | Le contrôle exact module/Code_Aster est déclaré exploratoire (F1) ; le critère porte sur la convergence au centre (F2). |
| 23 | ÉVITÉ | PAT-009 / DIAG-012 : les efforts se lisent par `CREA_TABLE`, jamais par `POST_RELEVE_T` ; CTL-010 : intitulés de 16 caractères au plus et uniques (contrôlé par le générateur). | Aucune erreur de lecture de table. |
| 24 | ÉVITÉ | DIAG-001 : chaque ddl bloqué une seule fois (DZ sur `APPUIS`, DX/DY en `P_A`, DY en `P_B`) ; CA-036 : seules les composantes bloquées entrent dans l'équilibre (`supports` de `projet.yaml`). | Pas de pivot nul, bilan juste. |
| 25 | ÉVITÉ | CA-041 : `FERR_MIN='EC2'` faux hors MPa. Le modèle étant en N et Pa, `UNITE_CONTRAINTE='Pa'` et minima calculés par le module `aster_expert.rebar` (9.2.1.1, 7.3.2), jamais par `FERR_MIN`. | Pas de minimum faux. |
| 26 | OUTIL | `ctx.number` ne convertit jamais : les champs de la plaque portent leur unité dans leur nom (`cover_mm`, `fck_mpa`…), confrontée à l'unité des données. | Pas de confusion mm/m possible. |
| 27 | ÉVITÉ | Premier maillage Salomé produit et vérifié du premier coup (PAT-008 : partition unique, groupes sur la géométrie, nombre de segments imposé ; arguments nommés). 60 et 48 invariants tenus. | Aucun aller-retour de maillage. |
| 28 | MANQUE | `aster-expert projet … executer` refuse un `.comm` hors des racines de `config/validation.yaml` (`execution.allowed_roots`) ; rien ne les étend à un nouveau projet, et le rejeu (`constats rejouer`) bute sur la même règle pour les cas versionnés du projet. | Deux racines ajoutées à la main (`projets/dalle_appuyee_01/resultats`, `…/references/cas`). À automatiser (lot 44 : naissance d'un projet). |
| 29 | ÉVITÉ | E0 : la correspondance des signes (MXX < 0 en flexion positive, normales +Z), déduite de CA-045, a été écrite **dans le critère** avant exécution : elle est confirmée, pas supposée. | Niveau E sans ambiguïté de signe. |
| 30 | LACUNE | `CALC_FERRAILLAGE` 2D à l'ELS : les densités dépendent de `SIGC_*_ELS` même au pivot acier, contrairement au cas 1D de R7.04.05, et s'écartent de 3 à 4 % du pivot acier refait par le module. Le critère F4 (écrit avant exécution) supposait le contraire : **échec rapporté tel quel**. | Constat CA-052 (niveau D, rejoué) ; cause non établie (même famille que CA-044). |
| 31 | OUTIL | `project_aliases` (base) et `rex` n'attribuaient un constat à son projet que par `fiche_project_name`, alors que la vérification de cohérence retombe sur `structure` : les 7 constats de la dalle n'étaient attribués à aucun projet. | Corrigé dans le tronc commun (même règle partout), test ajouté. |
| 32 | LACUNE | La condition de promotion « deux projets » compte la **citation** d'un constat par une fiche comme une réutilisation : CA-025 (sous `ELAS_COQUE`) et CA-041 (`FERR_MIN`) la remplissent grâce à la dalle sans y avoir été éprouvés (la dalle est en `ELAS`, sans `FERR_MIN`). | Signalé ; aucune promotion faite. Une réutilisation devrait porter sa preuve, comme `reuses` pour les entrées YAML. |
| 33 | OUTIL | Les tests du lot 42 supposaient une base amorcée par le seul quai (effectifs fixes, entrées du quai reconstruites à l'octet) : l'ajout de réutilisations par la dalle les faisait échouer. | Tests adaptés : les entrées du quai sont reconstruites à l'octet hors `reuses`, les effectifs incluent la dalle. |
| 34 | MANQUE | Aucun MED de résultats : l'`.export` produit par le tronc commun ne déclare que le `.comm` et le maillage, pas d'unité de sortie. | Contrôles faits sur les tables du listing ; pas de vue graphique. |

### Bilan de la phase 2

- Niveau E atteint (flèche et moments au centre, G et Q, Navier), D sur l'équilibre, la
  symétrie et les combinaisons ; ferraillage 2D : C avec contrôles D, un échec (F4).
- Exécutions Code_Aster : 4 réussies pour le projet (chaîne projet + 3 maillages de
  convergence), 1 rejeu (CA-052), 0 échec d'exécution ; tests réels lents : 3 réussis.
- Interventions de MM : **2** (section B ; questions ELS), selon la règle de la section C.
- Consultations de la base : `search_connaissances` **12** (journal `query_log.jsonl`, appels de
  `mcp-check` exclus) : 6 en phase 1, 6 en phase 2, toutes du lot 43 (0 au lot 42, selon MM).

## Écarts entre l'outil et ce qu'il faudrait pour traiter seul une dalle

1. **Catégorie « choix de modélisation de l'agent, vérifié par contrôle »** dans la fiche
   (repère, mailles, convergence, lecture, groupes) : 15 des 31 bloqueurs de la phase 1
   n'avaient pas à remonter à MM (n° 20 ; lot 44).
2. **Paramètres obligatoires des commandes** : l'outil n'a pas signalé, à la rédaction de
   la fiche, que `CALC_FERRAILLAGE` 2D exige des valeurs ELS (σc, αe, KT, Es) qui sont des
   décisions de pratique ; ils ont été découverts au moment d'écrire le `.comm` (n° 21).
   Une lecture des opérandes « obligatoires » de U4 au moment de la fiche l'aurait évité.
3. **Naissance d'un projet** : racines d'exécution et registre `rex` à créer à la main
   (n° 15, 28) ; état « fiche en cours d'arbitrage » absent de `projet.yaml` (n° 11).
4. **Normes non indexées** : tout article d'Eurocode vient de la mémoire de la session
   ou de MM (n° 13).
5. **Ferraillage 2D** : désormais dans le tronc commun (lot 43), mais la réduction par
   maille et l'ELS 2D de `CALC_FERRAILLAGE` restent inexpliqués (n° 22, 30).
6. **Promotion** : la citation d'un constat vaut réutilisation (n° 32).
7. **`get_command_schema`** : le filtre par mot-clé n'allège pas la sortie (n° 2 ; lot 44).
