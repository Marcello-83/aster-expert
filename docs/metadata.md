# Métadonnées

Toutes les structures décrites ici sont des modèles validés (`pydantic`). Une
donnée qui ne satisfait pas son modèle n'entre pas dans le corpus : elle est
rejetée et journalisée.

## 1. Fragment documentaire

```json
{
  "fragment_id": "U4.51.03#COMPORTEMENT.RELATION",
  "source_name": "codeaster-doc",
  "source_commit": "0000000000000000000000000000000000000000",
  "document_id": "U4.51.03",
  "document_title": "Opérateur STAT_NON_LINE",
  "family": "U4",
  "aster_version": "18",
  "doc_revision": "revision documentaire si distincte",
  "section_path": ["STAT_NON_LINE", "COMPORTEMENT", "RELATION"],
  "content": "texte du fragment",
  "content_hash": "sha256:...",
  "source_path": "chemin/relatif/dans/le/depot",
  "source_url": "url stable si disponible",
  "line_start": 0,
  "line_end": 0,
  "related_commands": ["STAT_NON_LINE"],
  "related_keywords": ["COMPORTEMENT", "RELATION"],
  "related_documents": ["R5.03.02"],
  "language": "fr",
  "extracted_at": "2026-01-01T00:00:00+00:00"
}
```

Règles :

- `fragment_id` est déterministe et reproductible à partir du document et du
  chemin de section. Il ne contient pas d'horodatage ni de compteur global.
- `source_commit` est obligatoire. Un fragment sans révision Git n'est pas
  indexable.
- `content_hash` permet de détecter les changements réels entre deux
  synchronisations et d'éviter une réindexation inutile.
- `related_documents` ne contient que des liens présents dans la source. Aucun
  lien n'est inféré.

## 2. Schéma de commande issu du catalogue

Structure produite par l'introspection, indépendante du texte des manuels.
Schéma établi et vérifié par exploration exhaustive du catalogue de la
version 17.4.0 (lot 4) : 268 commandes, 0 type de nœud non reconnu, 0 type de
valeur non reconnu (voir compte rendu du lot 4 pour le détail). Corrigé au
lot 4b (relecture externe) : identifiant de variante (C1), sémantique des
bornes (C2), statut `hidden` documenté (C3), complétude de `docu` (C4).

```json
{
  "command": "STAT_NON_LINE",
  "aster_version": "17.4.0",
  "image_digest": "sha256:d8d19ea9...",
  "catalogue_source": "chemin du package code_aster dans le conteneur",
  "catalogue_hash": "sha256:...",
  "kind": "operator",
  "result_type": "evol_noli",
  "result_type_dynamic": false,
  "docu": null,
  "keywords": [
    {
      "path": ["COMPORTEMENT"],
      "variant_id": "1a2b3c4d5e6f7a8b",
      "kind": "factor",
      "status": "optional",
      "min_occurrences": 1,
      "max_occurrences": null,
      "condition": [],
      "children": [
        {
          "path": ["COMPORTEMENT", "RELATION"],
          "variant_id": "9f8e7d6c5b4a3210",
          "kind": "simple",
          "status": "required",
          "value_type": "TXM",
          "allowed_values": ["ELAS", "VMIS_ISOT_LINE"],
          "default": null,
          "min_values": 1,
          "max_values": 1,
          "condition": []
        }
      ]
    }
  ],
  "extracted_at": "2026-01-01T00:00:00+00:00"
}
```

Règles :

- Les noms de champs ci-dessus sont ceux du projet, pas ceux du catalogue. La
  correspondance est établie à l'introspection et documentée dans le code.
- `image_digest` (ajouté au lot 4) est le digest de l'image conteneur dont le
  catalogue a été introspecté (`sha256:...`, jamais un tag — voir
  `docs/architecture.md`, ADR-002). `catalogue_hash` reste l'empreinte propre
  au contenu du paquet `Cata` (identique pour toutes les commandes d'une même
  extraction). Ce sont deux données indépendantes, jamais déduites l'une de
  l'autre : la même empreinte de catalogue pourrait en théorie apparaître
  dans deux images différentes ne différant que par autre chose que `Cata`.
- `aster_version` est la version lisible (le tag résolu, jamais `stable`),
  fournie pour la lecture humaine ; `image_digest` reste la seule identité
  faisant foi.
- `path` **n'identifie pas un nœud de façon unique** (constaté au lot 4b sur
  relecture externe : 37 chemins en double rien que sur `STAT_NON_LINE`, 72
  entrées surnuméraires — ex. `COMPORTEMENT.RESI_INTE` × 5). La cause est
  l'aplatissement volontaire des `Bloc` (ADR : la condition d'un bloc est
  conservée sur chaque mot-clé qu'il contient plutôt que représentée comme
  un nœud séparé) : un même nom de mot-clé peut être déclaré une fois par
  bloc frère (une variante par valeur de `RELATION`, par exemple). `path`
  garde donc sa forme aplatie (compatibilité, lisibilité), mais **n'est
  jamais utilisé seul pour identifier un nœud** :
  `variant_id` (ajouté au lot 4b) est un identifiant court, déterministe et
  stable, calculé à partir du chemin complet ET de la suite des clés de
  `Bloc` traversées (jamais du texte de la condition seul, qui pourrait par
  coïncidence être identique pour deux blocs différents). Deux extractions
  successives du même catalogue produisent les mêmes `variant_id`.
  `aster-expert catalogue show <CMD> --keyword <CHEMIN>` renvoie **toutes**
  les variantes d'un chemin, jamais une seule silencieusement choisie.
- `allowed_values` reflète exactement l'énumération du catalogue (`into`).
  Une liste tronquée ou complétée est une faute.
- **Trois notions distinctes, souvent confondues (lot 4b, C2) :**
  - `status` : la **présence** du mot-clé lui-même est-elle obligatoire,
    facultative, cachée ou par défaut ? Ne dit rien sur le nombre
    d'occurrences ni sur le nombre de valeurs.
  - `min_occurrences`/`max_occurrences` (mots-clés facteurs uniquement) : une
    fois le mot-clé facteur présent, combien de fois peut-il être répété
    (`FACT(max="**")` permet plusieurs occurrences, ex. `EXCIT`).
  - `min_values`/`max_values` (mots-clés simples uniquement) : une fois le
    mot-clé simple présent, combien de valeurs individuelles attend-il (ex.
    `TRANSF_GEOM_MAIT` dans `AFFE_CHAR_MECA` attend exactement 3 réels).
  - `status` vaut `"required"` (`statut="o"`), `"optional"` (`"f"`),
    `"hidden"` (`"c"`, voir plus bas) ou `"default"` (`"d"`, mot-clé facteur
    présent par défaut même sans intervention de l'utilisateur, via
    `addDefaultKeywords`) — correspondance directe avec
    `PartOfSyntax.isMandatory/isOptional/isHidden` et le statut brut `"d"`.
    Aucune autre valeur n'a été observée sur le catalogue 17.4.0 ; toute
    autre valeur est une erreur d'extraction.
  - Vérifié empiriquement contre `checkCommandSyntax` (lot 4b, sorties
    réelles rapportées dans le compte rendu de lot) : un mot-clé facteur
    obligatoire absent (`STAT_NON_LINE` sans `INCREMENT`) lève
    `KeyError: 'Keyword INCREMENT is mandatory'`. Un mot-clé simple
    obligatoire réduit à une liste vide (`INCREMENT.LIST_INST = []`) lève la
    **même famille d'erreur** (`KeyError: 'Keyword LIST_INST is mandatory'`),
    pas une erreur de cardinalité : `is_undefined([])` vaut `True` dans le
    vérificateur officiel, donc une liste vide est traitée comme une
    absence — le contrôle qui intercepte est celui de la *présence*
    (`status`), jamais celui du *nombre de valeurs* (`min_values`), qui
    n'est même pas atteint dans ce cas. `min_values`/`max_values` ne
    s'appliquent qu'à une valeur déjà considérée comme présente et non vide.
- `max_occurrences`/`max_values` valent `null` quand le catalogue porte la
  valeur `"**"` (illimité). Aucune autre transformation n'est appliquée aux
  bornes numériques.
- `condition` est la liste des expressions brutes (`Bloc.getCondition()`, non
  réévaluées, non combinées) des blocs conditionnels englobant le mot-clé, de
  l'extérieur vers l'intérieur ; liste vide si le mot-clé n'est sous aucun
  bloc. Une commande peut imbriquer des blocs (profondeur observée jusqu'à 6
  sur le catalogue 17.4.0) : chaque condition traversée est ajoutée à la
  liste, jamais fusionnée en une seule expression synthétique.
- **`status: "hidden"` (lot 4b, C3).** Établi par lecture du code source
  (`external/codeaster-src`) : `statut="c"` signifie « mot-clé caché ». Deux
  exemples réels : `reuse` (présent sur toute commande réentrante, lié à la
  convention d'appel Python `reuse=` qui réutilise un concept existant, pas
  à un mot-clé normal) et `SOLVEUR.RESI_RELA_PC` (commentaire du catalogue :
  « Mot-clé caché pour désactiver le critère en norme non préconditionnée
  dans PETSC »). Fait vérifié par recherche exhaustive dans le dépôt source :
  `isHidden()` (`_def_status()=='c'`) n'est référencé **nulle part ailleurs**
  dans tout `code_aster` — ni dans `SyntaxChecker.py`, ni dans le
  superviseur. Un mot-clé caché n'est jamais obligatoire
  (`isMandatory()` vaut `False`) ; s'il porte un `defaut`,
  `addDefaultKeywords` l'ajoute automatiquement au dict de mots-clés que
  l'utilisateur le mentionne ou non ; s'il est explicitement renseigné par
  l'utilisateur, il est validé exactement comme un mot-clé ordinaire (aucune
  exemption dans `visitSimpleKeyword`/`getKeyword`). Règle de traitement
  attendue côté validation (lot 10, à trancher formellement à l'ouverture de
  ce lot — voir `docs/development-plan.md`) : traiter `"hidden"` comme
  fonctionnellement équivalent à `"optional"` pour la vérification (jamais
  requis, accepté s'il est présent), mais ne jamais le suggérer comme mot-clé
  disponible dans un outil de complétion ou de génération de `.comm` neuf,
  puisque son statut caché signale une intention de réserve interne/de
  compatibilité de la part de l'auteur du catalogue.
- `value_type` est soit une chaîne (un seul type accepté : `"TXM"`, `"I"`,
  `"R"`, `"C"`, ou le nom Python d'une classe-concept comme
  `"cham_no_sdaster"`), soit une liste de chaînes quand plusieurs types sont
  acceptés (`typ` est alors un tuple dans le catalogue). Aucun renommage des
  classes-concept : le nom retenu est exactement `cls.__name__`.
- `default` : les valeurs complexes (`complex` Python, rencontrées par
  exemple sur `INFO_MODE.CENTRE_CONTOUR`) sont sérialisées
  `{"real": ..., "imag": ...}`, jamais tronquées à leur partie réelle.
- `result_type_dynamic` vaut `true` quand `sd_prod` est une fonction (le type
  réel dépend des arguments fournis, non déterminable statiquement) ; dans ce
  cas `result_type` vaut `null`, jamais un type deviné à partir du nom de la
  commande.
- `docu` reflète exactement ce que porte le catalogue, y compris quand ce
  n'est manifestement pas exploitable : sur 268 commandes de la version
  17.4.0, seules 8 portent un `docu` non nul, dont un textuellement
  `"UX.YZ.AB"` (`REST_HOMO_LOCAL`) et un vide (`TEST_COMPOR`). Ces valeurs
  sont conservées telles quelles, jamais filtrées ni corrigées, et signalées
  comme anomalies dans le rapport de synthèse de l'extraction — ce champ ne
  doit pas être utilisé comme source de citation fiable en l'état. Le
  rapport de synthèse (`catalogue_summary.json`) compte, en plus des
  anomalies individuelles, le nombre total de commandes sans `docu`
  exploitable (`commands_without_usable_docu`, ajouté au lot 4b : 262/268 sur
  la version 17.4.0 — 260 `docu` nuls et 2 malformés — le lot 4 ne
  dénombrait que ces 2 derniers, sous-déclarant l'ampleur réelle du manque).
  Voir `docs/development-plan.md` : le lien commande → manuel U4 devra être
  construit depuis le corpus documentaire, pas déduit du catalogue.
- Un élément du catalogue non reconnu par l'extracteur (type de nœud,
  `statut`, ou atome de `typ` en dehors de ceux ci-dessus) provoque un échec
  explicite, pas une omission silencieuse.

## 3. Analyse d'un fichier `.comm`

```json
{
  "file_path": "chemin/du/fichier.comm",
  "file_hash": "sha256:...",
  "assumed_version": "18",
  "version_source": "config | argument | fichier .export",
  "statements": [
    {
      "index": 0,
      "command": "AFFE_MODELE",
      "line_start": 12,
      "line_end": 20,
      "assigned_concept": "MODELE",
      "referenced_concepts": ["MAILLAGE"],
      "keywords": {},
      "mesh_groups": ["RADIER"],
      "node_groups": [],
      "modelisations": ["3D"],
      "phenomenon": "MECANIQUE",
      "behaviours": [],
      "logical_units": [],
      "raw_text": "texte exact du bloc",
      "dynamic": false,
      "unresolved": []
    }
  ],
  "test_statements": [],
  "external_files": [],
  "parse_warnings": []
}
```

Règles :

- `dynamic` vaut vrai lorsque les arguments d'une commande sont construits par
  le programme (boucle, dictionnaire assemblé, appel de fonction). Dans ce cas
  `unresolved` liste ce qui n'a pas pu être déterminé statiquement.
- Le fichier n'est jamais exécuté, y compris pour lever une ambiguïté.
- `raw_text` conserve le texte exact, indentation comprise, afin qu'aucune
  restitution ne repose sur une reconstruction.

## 4. Rapport de validation

```json
{
  "file_path": "chemin/du/fichier.comm",
  "aster_version": "18",
  "validation_level": "B",
  "catalogue_hash": "sha256:...",
  "valid": false,
  "errors": [
    {
      "code": "UNKNOWN_KEYWORD",
      "command": "STAT_NON_LINE",
      "path": ["COMPORTEMENT", "RELATON"],
      "line": 42,
      "message": "mot-clé absent du catalogue",
      "suggestion": "RELATION",
      "source": "catalogue"
    }
  ],
  "warnings": [],
  "commands_checked": ["AFFE_MODELE", "STAT_NON_LINE"],
  "commands_not_checked": [],
  "checked_at": "2026-01-01T00:00:00+00:00"
}
```

Règles :

- `validation_level` ne dépasse jamais ce qui a réellement été fait.
- `commands_not_checked` est obligatoire et non vide dès qu'une commande n'a pas
  pu être confrontée au catalogue. Un silence sur ce point est interdit.
- `suggestion` provient d'une distance d'édition sur les noms du catalogue. Elle
  est présentée comme une suggestion, jamais comme une correction établie.

## 5. Rapport d'exécution

```json
{
  "comm_path": "chemin/du/fichier.comm",
  "aster_version": "18",
  "status": "completed_with_alarms",
  "return_code": 0,
  "work_dir": "chemin du répertoire de travail",
  "mess_path": "chemin du .mess",
  "result_files": [],
  "duration_s": 0.0,
  "alarms": [
    {
      "code": "MECANONLINE10_1",
      "count": 3,
      "first_line": 1200,
      "excerpt": "texte exact"
    }
  ],
  "errors": [],
  "extracted_by": "run_aster.error_messages",
  "executed_at": "2026-01-01T00:00:00+00:00"
}
```

Le champ `extracted_by` trace l'outil ayant produit l'analyse, afin de
distinguer ce qui vient de `run_aster` de ce qui vient d'un traitement propre au
projet.

## 6. Citation

Toute réponse produite cite ses sources avec, au minimum :

- identifiant du document ou nom de la commande ;
- section ou chemin de mot-clé ;
- version Code_Aster ;
- chemin local ou URL ;
- cas test le cas échéant ;
- révision Git de la source.

Une affirmation sans citation possible est présentée comme une déduction ou
une recommandation, pas comme un fait documenté.
