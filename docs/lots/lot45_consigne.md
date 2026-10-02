# Lot 45 — Notes Word génériques (hypothèses et résultats)

**RÈGLE DE LANGUE — PRIORITAIRE.** Tout est rédigé en français : terminal,
résumé final, compte rendu, commit, rapports, commentaires.

**Deux profils, une seule branche `lot-45`, créée depuis `main` après fusion de
`lot-44`.**

- **Partie A — VM**, courte : elle versionne les résultats dont les notes ont
  besoin. Le Cloud n'a pas accès aux archives d'exécution ni au dossier
  partagé.
- **Partie B — Cloud** : tout le reste.

La session de la partie B commence par vérifier que la partie A est présente sur
la branche. Si elle ne l'est pas, elle s'arrête et le dit.

Consigne copiée dans `docs/lots/lot45_consigne.md`.

---

## Décisions de MM, validées par le lancement du lot

**Correction de PRE-020 (D21).** La consigne du lot 44, rédigée par Claude,
décrivait mal D21 : « Act = b·h, élément tendu, flexion simple exclue ». C'est
**faux**. Le texte exact de la décision est le suivant ; remplace celui de
PRE-020.

- *option_retained* : As,min selon l'EN 1992-1-1, 7.3.2.
  - Act est égale à la zone tendue complète de la section avant fissuration,
    soit b·h/2 en flexion.
  - kc dépend de la sollicitation.
  - k dépend de h : 0,65 pour h ≥ 800 mm.
  - fct,eff = fctm.
  - σs est tirée du tableau 7.2N, avec la correction 7.6N, pour φ = 40 mm et
    wk = 0,2 mm.
- *justification* : lecture littérale de 7.3.2, retenue par MM pour la poutre
  de couronnement.
- *validity_domain* :
  - lecture littérale de Act, par opposition à une aire effective hc,eff ;
  - pour une pièce massive, elle est plus pénalisante : environ 68 cm² sur les
    faces AY et 91 cm² sur les faces AZ ;
  - sur les faces AZ, φ*s sort du tableau 7.2N et σs est bornée à 160 MPa.
- *discarded_variants* : Act limitée à une hauteur effective hc,eff autour des
  aciers. Motif : non retenue par MM pour cet ouvrage, qui préfère la lecture
  littérale de 7.3.2.
- *sources* :
  - `decision_ingenieur` (MM) ;
  - `norme` : « NF EN 1992-1-1, 7.3.2, tableau 7.2N, expression 7.6N ».
- Note : MM confirmera la transcription complète du tableau 7.2N sur son
  exemplaire.

**Conséquence pour la dalle.** Le lot 43 a retenu kc = 0,4 et Act = b·h/2. C'est
**l'application de D21** à une pièce fléchie, et non une exception à D21 comme
l'affirmait l'arbitrage de Claude. Corrige en conséquence la mention dans le
précédent de la dalle concerné, et dans la note de correspondance de PRE-020.

**Texte de PRE-019 (D20).** Remplace le domaine de validité rédigé par la
session au lot 44 par le texte de la décision :

- *option_retained* : ELU accidentelle, γc = 1,2 et γs = 1,0.
- *justification* : valeurs du tableau 2.1N de l'EN 1992-1-1 pour les
  situations accidentelles. L'accostage est traité en combinaison accidentelle
  (D17).
- *validity_domain* : combinaison ELU accidentelle uniquement.
- *discarded_variants* : conserver γc = 1,5 et γs = 1,15 en situation
  accidentelle. Motif : ignore la distinction entre situations durables et
  accidentelles faite par l'EN 1992-1-1, et n'apporte qu'une marge non
  justifiée.

**Es du quai.** Es = 200 GPa est la décision pour tous les projets.

- Le quai garde 210 GPa (depuis le lot 39) jusqu'au prochain lot qui le
  recalcule.
- Enregistre-le comme décision en attente d'application, avec un bloqueur
  visible dans la fiche du quai.
- Ne recalcule pas le quai dans ce lot.

---

## Partie A — VM

1. `aster-expert env-check`.
2. Commande générique `aster-expert projet exporter-resultats <projet>`. Elle
   écrit dans `projets/<projet>/resultats/` un **paquet de résultats
   versionnable** :
   - tableaux en CSV ou JSON ;
   - figures PNG existantes ;
   - empreintes de la fiche, des données, du `.comm`, du maillage et de
     l'exécution ;
   - niveau de validation atteint.

   Elle n'inclut aucun fichier MED.
3. Taille plafonnée : 20 Mo par projet. Le crochet `pre-commit` reste actif.
4. Exécute la commande pour `quai_cw_test_01` (lots 34 à 39) et pour
   `dalle_appuyee_01` (lot 43, avec le recalcul Es du lot 44).
5. Commit et envoi sur `lot-45`. Le message dit « partie A terminée ».

## Partie B — Cloud

### Étape 0

1. `aster-expert env-check`, en profil `cloud`.
2. `aster-expert mcp-check`.
3. Présence des deux paquets de résultats.
4. Ajout de `python-docx` aux dépendances, avec `uv.lock` mis à jour, si la
   bibliothèque n'y est pas déjà.

### Étape 1 — Décisions

Applique les trois décisions ci-dessus, puis lance
`aster-expert connaissances verifier`.

### Étape 2 — Règle d'unités de `FERR_MIN`

Vérifie d'abord ce qui existe déjà : CA-041 et le générateur.

- Si le générateur n'impose pas encore `UNITE_CONTRAINTE='MPa'` dès que
  `FERR_MIN` est demandé, fais-le, avec un test.
- Rédige dans `docs/signalements/` un court texte factuel, en français,
  reproductible avec le cas d'essai versionné. MM décidera s'il le publie.

### Étape 3 — Note d'hypothèses

Commande `aster-expert note hypotheses <projet>`, qui produit un `.docx` à partir
de la fiche, des données et de la convention de nommage.

- **Mise en forme**, voulue par MM : police Arial 10, texte noir, en-têtes de
  tableaux sur fond gris (jamais bleu), titres numérotés.
- **Contenu** :
  1. en-tête : ouvrage, date de génération, version de Code_Aster et digest de
     l'image, empreintes ;
  2. objet et périmètre ;
  3. données en tableaux, chaque valeur avec sa source ;
  4. un paragraphe par point de la fiche : option retenue, justification,
     domaine de validité, variantes écartées, sources et leur origine, date,
     décideur. Les points `choix_agent` sont regroupés à part, avec leur
     contrôle ;
  5. constats Code_Aster cités, avec leur niveau et leur statut (`établi`,
     `promu`) ;
  6. combinaisons et coefficients ;
  7. en annexe, l'historique des révisions.
- **Générique** : aucune section propre à un ouvrage dans `src/`. Le contenu
  vient entièrement de la fiche et des données. Les seules phrases fixes sont
  les titres et les libellés.

### Étape 4 — Note de résultats

Commande `aster-expert note resultats <projet>`, même mise en forme, qui lit le
paquet de résultats. Rien n'est recalculé.

1. Traçabilité et niveau de validation atteint, énoncé sans complaisance.
2. Contrôles de niveau D, et de niveau E s'il est atteint, avec les critères
   écrits avant l'exécution et la date de leur commit.
3. Résultats par cas, en tableaux et figures.
4. Ferraillage :
   - la part calculée par `CALC_FERRAILLAGE` et la part calculée hors de
     Code_Aster, avec les articles de l'EN 1992 ;
   - les minima ;
   - les anomalies ouvertes qui touchent la lecture des résultats (ANO-001).
5. Limites et domaine de validité des décisions qui conditionnent la lecture
   des résultats.

Les sections affichées dépendent de ce que le paquet contient, déclaré dans
`projet.yaml`, et non du nom du projet.

### Étape 5 — Contrôle automatique des notes

Pour chaque note de chaque projet :

- chaque point de la fiche apparaît dans la note ;
- chaque valeur numérique citée est identique à sa source ;
- aucune mention `[À CONFIRMER`, `[QUESTION` ou `TODO` ;
- la mise en forme est vérifiée par relecture du `.docx` : police, taille,
  couleur, fond gris des en-têtes.

### Livrables

Les quatre notes sont produites par `scripts/` et versionnées dans
`projets/<projet>/livrables/notes/` :

- note d'hypothèses et note de résultats de `quai_cw_test_01` ;
- note d'hypothèses et note de résultats de `dalle_appuyee_01`.

## Contrôles (partie B)

```bash
aster-expert env-check
aster-expert mcp-check
ruff format --check
ruff check
pytest tests/unit
pytest
pytest -m lent_aster
mypy src
mypy
aster-expert connaissances verifier
aster-expert rex dalle_appuyee_01
```

`pytest -m lent_salome` est ignoré dans le Cloud, avec son motif.

## Compte rendu attendu — EN FRANÇAIS

1. Partie A : paquets de résultats, contenu et taille.
2. Décisions appliquées : PRE-019, PRE-020, mention de la dalle, Es du quai.
3. Règle `FERR_MIN` et texte de signalement.
4. Structure des notes : nombre de pages, figures, sections affichées par
   projet.
5. Résultats des contrôles des notes.
6. Commandes de contrôle, `rex`, interventions du lot.
7. Durée de préparation de l'environnement Cloud, et tout ce qui a manqué dans
   le Cloud.

## Interdits

- Aucun texte d'hypothèse rédigé à la main dans les notes ou le générateur.
- Aucun verdict de conformité d'ouvrage.
- Aucune exécution des modèles, sauf pour un test lent.
- Aucun envoi sur `main` depuis le Cloud.
- Aucun identifiant Code_Aster énoncé de mémoire.
