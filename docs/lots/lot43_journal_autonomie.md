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
