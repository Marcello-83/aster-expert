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

```json
{
  "command": "STAT_NON_LINE",
  "aster_version": "18",
  "catalogue_source": "chemin du package code_aster",
  "catalogue_hash": "sha256:...",
  "kind": "operator",
  "result_type": "evol_noli",
  "docu": "U4.51.03",
  "keywords": [
    {
      "path": ["COMPORTEMENT"],
      "kind": "factor",
      "status": "optional",
      "min_occurrences": 1,
      "max_occurrences": null,
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
          "condition": null
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
- `allowed_values` reflète exactement l'énumération du catalogue. Une liste
  tronquée ou complétée est une faute.
- `condition` conserve l'expression des blocs conditionnels sous sa forme
  d'origine. Elle n'est pas réécrite ni simplifiée.
- Un élément du catalogue non reconnu par l'extracteur provoque un échec
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
