# Contrôle post-lot 54 — compte rendu

Profil `vm`. Branche `lot-54-controle`, créée depuis `main` à jour (`c844d75`, fusion de `lot-54`). Consigne :
`docs/lots/controle_post_lot54.md`. Aucun changement du modèle, des cas unitaires, des événements ni des
combinaisons ; aucune décision P nouvelle ; ni EC9 ni EC2. Niveau de validation inchangé : D (le `.comm` de B54
est celui du lot 54).

## 1. Emplacement, Git, environnement

- `pwd` : `/home/ubuntu/projets/aster-expert`. `origin` : `Marcello-83/aster-expert`. Au départ `main` local
  retardait sur `origin/main` (`66a6279` contre `c844d75`) : avancé en fast-forward, arbre propre.
- `env-check` : OK (profil `vm`, 10 vérifications). `mcp-check` : **10/10 verts**.
  - Au lot 54, 9/10 : `query_results`, « aucun livrable local, clone neuf » (cause : absence des résultats d'un
    projet dans un clone neuf, pas la configuration). Ici `dalle_appuyee_01` a ses livrables locaux : l'outil répond.
- `.env` : **absent** dans `projets/aster-expert` comme dans le répertoire parasite ; `env-check` n'en exige pas.
  `.env.example` déclare 13 noms (`ASTER_DOCKER_BIN`, `ASTER_IMAGE_REPOSITORY`, `ASTER_IMAGE_REF`,
  `ASTER_CONTAINER_NETWORK`, `_MEMORY`, `_CPUS`, `_WORKROOT`, `ASTER_RUN_TIMEOUT`, `ASTER_GIT_TIMEOUT`,
  `ASTER_EXPERT_ROOT`, `ASTER_EXPERT_LOG_LEVEL`, plus la clé API en commentaire). Rien à signaler.
- `pytest` (série par défaut) : **1918 réussis, 1 ignoré** (livrables du lot 50 bis absents), 4 désélectionnés,
  324 s. `etat verifier` : cohérent. `projet pontons_alu_01 verifier` : cohérent, 86 entrées, aucun bloqueur.
- Fiche : P67 à P76 présentes ; P43, P48, P56 (2 versions), P60, P62, P64 avec leur ancienne version dans
  `decision_history` ; P61 annulée (ancienne version conservée dans l'historique).
- Intégration continue de `main` : `ci` et `ci-lent` **réussis** sur `c844d75` (3 min 35 s et 3 min 26 s).

## 2. Répertoire créé à tort : `/home/ubuntu/aster-expert` (rien supprimé ni déplacé)

- Clone Git complet, `main` à `c844d75` (même commit), propre ; `.venv` propre à lui ; **pas de `.env`** ; 5,2 Go.
  `.mcp.json` et `.claude/skills` identiques à ceux du dépôt de travail ; `.claude/settings.local.json` active le
  serveur MCP du projet : sans effet sur `projets/aster-expert` sauf si une session y est lancée.
- Fichiers produits au lot 54 qui n'existent que là : `projets/pontons_alu_01/resultats/lot54/` (A54, B54, 417 Mo
  d'exports, journaux, 13 vues, maillages et rapports `mesh check`) et `data/processed/runs/` (1,8 Go, dont
  l'exécution B54 `20261023T081230-ebb19a19`, tables `fort.31/32/33`).
  - Empreintes comparées au dépôt `/media/sf_partage/echanges/lot54/` : tous les fichiers déposés sont identiques
    (`sha256sum -c` sans écart ; exports A54 et B54, 13 vues). **Seuls** non déposés : `deplacements_elementaires.csv`
    (A54 104 Mo, B54 105 Mo) et `efforts_elementaires.csv` (B54 180 Mo), volontairement exclus.
- Aussi à la racine de `/home/ubuntu` (hors consigne, non examinés plus avant) : `pontons.med`,
  `pontons.meta.json`, `pontons.progress.txt`, `salome_create_radier.py`, `test.py`, `commactuel.txt`.
- **Proposition à MM.** À rapatrier avant toute suppression (facultatif) : les trois CSV de 100 Mo ci-dessus si on
  veut les garder (ils se régénèrent par la chaîne). Tout le reste est reproductible ou déjà déposé/versionné : le
  répertoire peut être supprimé en entier, ainsi que ses `.venv`, `data/processed` et `external`. À faire par MM
  (je n'ai rien supprimé).

## 3. Exports complémentaires (B54)

### 3.1 MED — relance (les MED de B54 n'existaient pas)

Le `.comm` du lot 54 n'écrit aucun MED de résultats (son `.mmed` est le maillage d'entrée). Relance de la chaîne du
tronc commun (`scripts/chaine_B54_controle.sh`, sur le modèle de `chaine_B52.sh`, `PONTONS_VARIANTE=B54`) :
`maillage`, `generer`, `valider`, `executer`, puis `livrables` (`preparer`, `executer`, `verifier`, `traiter`).

- **`.comm` de production** : sha256 `56f07a292560d747d82ff9d95e7ccbedd180451d11acca8849ff938b95b7719e`, **identique
  octet pour octet (`cmp`)** à celui du lot 54. Exécution `20261023T131755-9ebda504` : `completed_ok`, 187,5 s,
  0 alarme. Niveau B : valide, 1616/1616.
- **`.comm` de post-traitement** (`pontons_alu_01_livrables.comm`) : c'est lui qui écrit les MED ; il est généré par
  la chaîne avec sorties insérées, ce n'est pas le `.comm` de production. Niveau B valide, 2515/2515 commandes ;
  exécution `20261023T132145-2dc5c415`, `completed_ok`, 312,8 s ; **tables E20.12 identiques à la production**
  (1 412 077 valeurs).
- Commande : `IMPR_RESU(FORMAT='MED', UNITE=…, RESU=_F(RESULTAT, NUME_ORDRE, NOM_CHAM_MED='CAS_<cas>__DEPL',
  NOM_CHAM, NOM_CMP, CARA_ELEM…))`. Catalogue 17.4.0 (`get_command_schema`, `IMPR_RESU`, mot-clé
  `RESU.NOM_CHAM_MED`) : simple, optionnel, `TXM`, condition `FORMAT == 'MED'` et (`CHAM_GD` ou `RESULTAT`) ;
  `catalogue_hash` `b59726e0…`. Le même `.comm` est confronté au catalogue par `valider` (niveau B).
- Fichiers : `resultats.med` (87,1 Mo : DEPL et EFGE_ELNO des 225 cas) et `charges.med` (37,1 Mo), plus le maillage
  `maillage_B54.med`. Le MED n'entre pas dans Git.
- **Non-régression** (exécution relancée, relue par les lecteurs du lot 54) : `efforts_elementaires.npz`,
  `deplacements_unitaires.csv` (16 632 lignes), `appuis_axes.csv` (4 420 lignes) : **écart relatif nul (0,0)**, seuil
  1e-9. Le maillage régénéré par Salomé n'a pas la même empreinte que celui du lot 54 (`dc2d841e…` contre
  `05b45087…`, métadonnées MED) ; les résultats sont néanmoins identiques.
- Champs unitaires du MED contre les tables du calcul (G1, Q_M0, QD_M3, HU_TUBES, TP) : écart ≤ 1e-9.

### 3.2 `deplacements_unitaires_complet.csv`

187 cas (ceux de `evenements.csv` plus ACN/ACX/ACZ/AMX/AMY/TP/TM du lot 54), mêmes points et colonnes ; le fichier
du lot 54 y est contenu sans écart. Recombinaison depuis ce seul fichier (module `csv`) des étiquettes de
`deplacements_combinaisons.csv` : PF_bout_YM, DY : **55,855 mm (ELS caractéristique) et 78,888 mm (ELU accidentel)**
(55,85 et 78,89 attendus) ; palée : P5C2_YM_axe DX 69,319 / 31,555 hors T, DY 48,703 ; P3_semelle_centre DZ −0,537 ;
tous les extrêmes testés à 7·10⁻¹⁵ mm près.

### 3.3 Déformées ParaView

Champ combiné à partir du MED (Σ coefficient × champ unitaire, G et Q compris, coefficients de `evenements.csv`
appliqués à l'étiquette) ; valeur au point de sortie égale à celle du CSV (écart 0 pour A et B, −1,4·10⁻¹⁴ pour C) et
champ MED égal au champ des tables (écart 0). Rendu par pvbatch de Salomé-Méca.

| Vue | Combinaison | Valeur | Amplification | Échelle |
|---|---|---|---|---|
| A | ELS c., max DY en PF_bout_YM | 55,854 mm | × 10 | 0 à 60 mm |
| B | ELU acc., idem | 78,888 mm | × 10 | voir PNG |
| C | ELS c., max DX hors T en P5C2_YM_axe | 31,555 mm | × 25 | −10 à 40 mm |

Vérification à l'œil (A et C ouvertes) : vue de dessus, non-déformée gris clair, filaire bleu–blanc–rouge, barre
horizontale sous la vue avec graduations rondes, étiquettes culée, P1 à P5 discrètes, aucun titre ni trièdre. Images de
3 200 px, fond blanc, ouvrage à 97 % de la largeur, aucune troncature (marge d'encre 45 px à gauche et à droite),
texte de 24 px (8,5 pt à 200 dpi). **Limite** : seules les barres (SEG2, piles comprises) sont tracées ; les semelles
DKT ne le sont pas. Les étiquettes sont posées au-dessus du filaire, à distance de celui-ci (le filaire déformé
se décale vers le haut).

## Dépôt et commit

`/media/sf_partage/echanges/controle_post_lot54/pontons_alu_01/` : `B54/` (MED, maillage, CSV complet, JSON de
contrôle), `vues/` (3 PNG, `controle_vues.json`), `scripts/`, `empreintes.sha256` (16 fichiers, vérifié, 124 Mo).
Versionné : `controle_lot54.py`, `tests/test_controle_lot54.py` (2 tests), `scripts/chaine_B54_controle.sh`,
`controle_lot54_deplacements.py`, `champ_combine_lot54.py`, `vues_deformees_lot54.py`,
`paraview/vues_deformees_lot54_pv.py`, la consigne et ce compte rendu. `ruff` et `mypy` : propres sur ces fichiers.

## `rex`

    Retour d'expérience du projet pontons_alu_01
    Archive d'exécution refusée : archive non conforme au manifeste : l'empreinte des 49 plus anciennes exécutions diffère. Aucun échec examiné, métriques mesurées ni recalculées ni écrites ; seuls les champs déclarés (interventions, erreurs évitées, notes) sont mis à jour.
    Constats de la fiche à verser dans la base : 0.
    Candidats patrons dans le code du projet : 0 (similarité ≥ 0,40 ; 24 fonction(s) sous le seuil, non listées).
    Connaissances créées par le projet : 3 ; promues : 0.
    Consultations journalisées (tous projets) : search_connaissances 74, search_constats 3.
    Champs déclarés seuls mis à jour : connaissances/metriques/pontons_alu_01.yaml

Même limite qu'au lot 54 : le clone n'a pas les 49 plus anciennes exécutions, l'archive est refusée, aucune métrique
mesurée ni recalculée, aucun échec non classé. Les rejeux de cette session (calcul et post-traitement identiques à
une exécution déjà réussie) sont des exécutions de vérification.
