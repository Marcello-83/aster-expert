# Lot 47 — Contre-calcul d'une estacade sur pieux (projet `estacade_pieux_01`)

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-47` créée depuis `main` à jour), **sans l'annexe B**, versée dans les données
du projet (`projets/estacade_pieux_01/donnees/`). L'annexe A (liste des termes
interdits) a été donnée par MM dans le chat ; elle n'est écrite que dans le fichier
local non versionné `config/termes_interdits.local.txt`.

---

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français : terminal,
résumé final, compte rendu, commit, rapports, commentaires.

**Profil : `vm`** (maillage Salomé). Branche `lot-47`, depuis `main` à jour.
Consigne copiée dans `docs/lots/lot47_consigne.md`, **sans l'annexe B**, qui
reste dans les données du projet.

## Nature du lot

C'est le premier ouvrage réel. Il s'agit de **contre-calculer avec Code_Aster
un modèle Robot d'avant-projet** : un tablier-dalle sur chevêtres, des pieux
métalliques et des ressorts de sol. On compare ensuite les résultats aux valeurs
publiées.

**Statut de la comparaison.** Le calcul Robot n'est pas validé. La comparaison
est un **contre-calcul**, pas un niveau E. Un écart ne désigne pas d'avance le
logiciel fautif : chaque écart hors tolérance doit être expliqué, par une
hypothèse, une erreur d'un côté ou de l'autre, ou une différence de
formulation. « Inexpliqué » est une réponse admise, si les pistes examinées
sont listées.

**Confidentialité (décision de MM).** Les données viennent d'un projet réel.

- Le nom du projet est `estacade_pieux_01`.
- **Aucun nom de site, de client, de maître d'ouvrage ou de bureau d'études**
  n'apparaît nulle part : code, données, commits, comptes rendus, notes.
- Aucun document source, aucune figure et aucun extrait de texte ne sont
  versés : seules les valeurs numériques de l'annexe B le sont.
- Ajoute un test qui échoue si l'un des termes interdits listés en annexe A
  apparaît dans le dépôt. Il s'ajoute au contrôle de publication existant.

Le prompt est **moins court** que celui de la dalle : MM a déjà tranché la moitié
pratique (section « Décisions »). **Ne t'arrête pour arbitrage que si un point
pratique n'est couvert ni par ces décisions ni par l'annexe B.** Liste alors ces
seuls points.

## Étape 0 — Environnement et intégration continue

1. `aster-expert env-check`, puis `aster-expert mcp-check`.
2. **Image des runners GitHub.** Le label `ubuntu-latest` passe à Ubuntu 26 le
   19 octobre 2026. Ce sont les machines de GitHub, indépendantes de la VM de
   MM. Fixe le label explicitement dans `ci.yml` et `ci-lent.yml` :
   - `ubuntu-26.04` si GitHub le publie comme disponible (pas en préversion),
     ce qui aligne l'intégration continue sur la VM ;
   - sinon `ubuntu-24.04`.

   Vérifie la disponibilité dans la documentation de GitHub, ne la suppose pas.
3. **pip-audit, pyjwt 2.14.0.** Relève l'identifiant de l'avis. Si une version
   corrigée est compatible avec `mcp`, mets à jour cette seule dépendance
   (`uv lock --upgrade-package`). Sinon, documente-le.

## Décisions de MM, validées par le lancement du lot

| N° | Décision |
|---|---|
| E1 | Géométrie du **modèle Robot** : 31,20 m, 7 files de pieux à 5,00 m, 14 pieux. La description à 36,2 m et 8 files n'est **pas** retenue. |
| E2 | Chevêtres : barre de **1,20 × 0,90 m**, section rectangulaire, **au plan moyen de la dalle**, sans excentrement. Conséquence connue et acceptée : la dalle et le chevêtre se recouvrent sur 1,20 × 0,40 m, ce qui compte deux fois ce volume en raideur et en poids, comme dans le modèle Robot. La session chiffre ce double compte en kN par chevêtre et le rapporte, sans le corriger. |
| E3 | Pieux : sections corrodées par tronçon (annexe B, tableau B2), sans section mixte au droit du bouchon. Entre +0,70 m NGF et le nœud du tablier, la section du tronçon supérieur est prolongée. |
| E4 | Appui vertical en pointe : **DZ = 0** à −13,00 m NGF, rotations libres. Les ressorts sont horizontaux (kx = ky) : sans cet appui, le mouvement vertical d'ensemble n'est pas bloqué. |
| E5 | Calcul **linéaire** : ressorts élastiques, sans palier. |
| E6 | Ressorts de la file 1 aux nœuds −8,00 et −8,50 m : kx = ky = 21 200 kN/m (erreur de recopie du tableau source). Les nœuds manquants à −10,00 et −10,50 m sont complétés à 21 200 kN/m. Les files 1 et 7 sont identiques. |
| E7 | Béton : Ecm = 34 GPa, ν = 0,2, 25 kN/m³. Acier : 210 GPa, ν = 0,3, 78,5 kN/m³ (la valeur du modèle source). |
| E8 | Charge mobile TS : **pas de 0,50 m** sur toute la longueur ; deux positions transversales, « axé » et « bord de voie », déduites de la géométrie de la voie (annexe B). UDL de 6,30 kPa sur toute la longueur de la voie. |
| E9 | Freinage : **381 kN**, réparti uniformément sur la surface de la voie, appliqué dans le plan moyen de la dalle, selon X. |
| E10 | Température : ΔT uniforme de ±27,5 °C sur la dalle et les chevêtres seulement, α = 1×10⁻⁵ /°C. |
| E11 | Combinaisons : celles du modèle source, **reproduites telles quelles** (n° 100 à 115, en ELS f, ELS c, ELU+ et ELU−). LM1 y est l'enveloppe sur les positions de la charge mobile. |
| E12 | Tolérances de comparaison : **3 %** pour les efforts globaux (réactions, N des pieux) ; **5 %** pour les moments et efforts tranchants des barres (pieux, bouchons, chevêtres) ; **10 %** pour les efforts locaux de la dalle (Mxx, Qxx). |

## Ce qui est attendu

1. **Projet** créé par `aster-expert projet creer estacade_pieux_01`. L'annexe B
   est versée en données structurées, chaque valeur portant sa source sous la
   forme « référence externe, tableau ou figure n° », sans titre de document.
2. **Fiche.** La moitié pratique est reprise des décisions E1 à E12, avec
   l'origine `arbitrage_mm`. Les choix techniques sont en `choix_agent`, avec
   leur contrôle (lot 44) : maillage, raffinement local sous les roues, groupes,
   repère, lecture des champs. La moitié `code_aster` est fondée sur la
   documentation et la base de connaissances.

   Consultation obligatoire de la base, au minimum sur :
   - les ressorts nodaux et la somme aux nœuds communs ;
   - la liaison entre une barre et une coque ;
   - `FORCE_COQUE` et le report des charges sur la surface ;
   - les charges définies par fonction et leur évaluation aux nœuds ;
   - les pivots nuls.

   La session dit lesquelles ont évité une erreur.
3. **Critères écrits et commités avant toute exécution** :
   - points de comparaison C1 à C13 (annexe B) et tolérances E12 ;
   - harnais D par défaut : équilibre, résultantes de chaque cas comparées aux
     charges déclarées, symétrie si elle s'applique ;
   - convergence de maillage de la dalle sous charge de roue.
4. **Maillage Salomé, `.comm` et exécution.**
   - Chaque exécution déclare ses connaissances appliquées (fichier compagnon,
     lot 46).
   - Les 62 positions de la charge mobile, ou celles qu'impose le pas de E8,
     se traitent sans écrire un cas à la main par position.
5. **Comparaison.**
   - Commence par **C13**, les enveloppes non pondérées : c'est la comparaison
     qui dépend le moins des combinaisons.
   - Puis C1 à C12.
   - Un tableau donne pour chaque point : valeur Code_Aster, valeur source,
     écart, verdict, explication.
   - Les conventions de signe et de repère de chaque grandeur sont précisées
     (« direction automatique » des plaques de Robot, axes locaux des barres).
6. **Paquet de résultats et notes Word** (lots 45 et 46), avec la mention
   « contre-calcul d'un modèle non validé ».
7. **Capitalisation.**
   - Ajoute à `references_validation/` un type d'entrée « calcul externe non
     validé ». Il ne peut servir à aucune promotion.
   - `aster-expert rex estacade_pieux_01`.
   - Les nouvelles connaissances, avec leur épreuve.

## Compte rendu attendu — EN FRANÇAIS

1. Étape 0 : label des runners, pyjwt.
2. Points pratiques non couverts, s'il y en a. C'est le seul motif d'arrêt.
3. Modèle : maillage, convergence, double compte E2 chiffré, harnais D.
4. Tableau de comparaison C1 à C13, avec les écarts expliqués ou listés comme
   inexpliqués.
5. Journal d'autonomie : connaissances consultées, erreurs évitées, lacunes.
6. `rex`, commandes de contrôle, interventions du lot.

## Contrôles

```bash
aster-expert env-check
aster-expert mcp-check
ruff format --check
ruff check
pytest tests/unit
pytest
pytest -m lent
mypy src
mypy
aster-expert connaissances verifier
aster-expert rex estacade_pieux_01
```

## Interdits

- Aucun terme de l'annexe A dans le dépôt.
- Aucun critère écrit ou modifié après exécution.
- Aucun ajustement du modèle pour se rapprocher de la source sans hypothèse
  physique nommée. Une variante de sensibilité est permise, déclarée comme
  telle.
- Aucune décision pratique hors de E1 à E12 sans arbitrage de MM.
- Aucun code propre à l'estacade dans `src/`.
- Aucun identifiant Code_Aster énoncé de mémoire.

---

## Annexe A — Termes interdits dans le dépôt

La session reçoit cette liste de MM, dans le chat, au lancement. Elle ne l'écrit
dans aucun fichier versionné. Le test lit la liste depuis un fichier local non
versionné, `config/termes_interdits.local.txt`, et s'ignore avec un motif
lisible si ce fichier est absent.

Précision donnée par MM avec la liste : le test ignore la casse et les accents.

## Annexe B — Données (à verser dans le projet)

Non recopiée ici (consigne de MM) : voir `projets/estacade_pieux_01/donnees/`.
