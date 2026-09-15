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
valeur non reconnu (voir compte rendu du lot 4 pour le détail).

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
      "kind": "factor",
      "status": "optional",
      "min_occurrences": 1,
      "max_occurrences": null,
      "condition": [],
      "children": [
        {
          "path": ["COMPORTEMENT", "RELATION"],
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
- `allowed_values` reflète exactement l'énumération du catalogue (`into`).
  Une liste tronquée ou complétée est une faute.
- `status` vaut `"required"` (`statut="o"`), `"optional"` (`"f"`), `"hidden"`
  (`"c"`) ou `"default"` (`"d"`, mot-clé facteur présent par défaut) —
  correspondance directe avec `PartOfSyntax.isMandatory/isOptional/isHidden`
  et le statut brut `"d"`. Aucune autre valeur n'a été observée sur le
  catalogue 17.4.0 ; toute autre valeur est une erreur d'extraction.
- `max_occurrences`/`max_values` valent `null` quand le catalogue porte la
  valeur `"**"` (illimité). Aucune autre transformation n'est appliquée aux
  bornes numériques.
- `condition` est la liste des expressions brutes (`Bloc.getCondition()`, non
  réévaluées, non combinées) des blocs conditionnels englobant le mot-clé, de
  l'extérieur vers l'intérieur ; liste vide si le mot-clé n'est sous aucun
  bloc. Une commande peut imbriquer des blocs (profondeur observée jusqu'à 6
  sur le catalogue 17.4.0) : chaque condition traversée est ajoutée à la
  liste, jamais fusionnée en une seule expression synthétique.
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
  doit pas être utilisé comme source de citation fiable en l'état.
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
