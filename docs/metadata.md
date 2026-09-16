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

Structure produite par `aster_expert.parsing.comm_parser` (lot 9), par
inspection statique du module `ast` de la bibliothèque standard, sans jamais
exécuter le fichier. Modèles pydantic dans `aster_expert/parsing/models.py`.

```json
{
  "file_path": "chemin/du/fichier.comm",
  "file_hash": "sha256:...",
  "assumed_version": null,
  "version_source": "undetermined",
  "statements": [
    {
      "index": 3,
      "command": "MODI_MAILLAGE",
      "line_start": 34,
      "line_end": 38,
      "assigned_concept": "MAIL",
      "reuse": "MAIL",
      "referenced_concepts": ["MAIL"],
      "keywords": {
        "MAILLAGE": {
          "node": "simple",
          "name": "MAILLAGE",
          "value": {
            "kind": "concept",
            "resolved": false,
            "concept": "MAIL",
            "source": "MAIL"
          }
        },
        "ORIE_NORM_COQUE": {
          "node": "factor",
          "name": "ORIE_NORM_COQUE",
          "occurrences": [
            {
              "keywords": {
                "GROUP_MA": {
                  "node": "simple",
                  "name": "GROUP_MA",
                  "value": {
                    "kind": "literal",
                    "resolved": true,
                    "value": "POUTRE",
                    "value_type": "str"
                  }
                },
                "VECT_NORM": {
                  "node": "simple",
                  "name": "VECT_NORM",
                  "value": {
                    "kind": "literal",
                    "resolved": true,
                    "value": [0.0, 0.0, 1.0],
                    "value_type": "tuple"
                  }
                },
                "GROUP_NO": {
                  "node": "simple",
                  "name": "GROUP_NO",
                  "value": {
                    "kind": "literal",
                    "resolved": true,
                    "value": "AA",
                    "value_type": "str"
                  }
                }
              }
            }
          ]
        }
      },
      "mesh_groups": ["POUTRE"],
      "node_groups": ["AA"],
      "modelisations": [],
      "phenomena": [],
      "behaviours": [],
      "logical_units": [],
      "control_flow": [],
      "raw_text": "MAIL = MODI_MAILLAGE(\n    reuse=MAIL,\n    ...\n)",
      "dynamic": false,
      "unresolved": []
    }
  ],
  "test_statements": [12],
  "external_files": [
    {"statement_index": 1, "command": "LIRE_MAILLAGE", "unite": 20, "fichier": null}
  ],
  "imported_names": ["DEFI_CONT", "LIRE_MAILLAGE", "STAT_NON_LINE"],
  "parse_warnings": [
    {
      "line": 553,
      "node_type": "Assign",
      "message": "call to 'AFFE_CARA_ELEM' assigned with an unsupported target shape (1 target(s), not a single plain name): not represented as a statement."
    }
  ]
}
```

Règles :

- Le fichier n'est jamais exécuté, y compris pour lever une ambiguïté (lot 9,
  `docs/architecture.md` §5). L'analyse repose exclusivement sur `ast.parse` et
  `ast.literal_eval` ; aucune expression régulière, aucun `exec`, aucun import
  du fichier analysé.
- `assumed_version`/`version_source` ne sont jamais renseignés par le parseur
  lui-même : il ne résout aucune version (périmètre du lot 2/lot 10).
  `parse_comm_file`/`parse_comm_source` les laissent respectivement à `null`
  et `"undetermined"`. Un consommateur aval qui connaît la version cible peut
  les compléter ; ce n'est pas un fait constaté par l'analyse structurelle.
- **`keywords`** est un arbre, pas une simple liste de noms de mots-clés
  (amendement lot 9, voir `docs/development-plan.md`). Chaque entrée est un
  nœud discriminé par `node` :
  - `"simple"` : un mot-clé simple. Son champ `value` est lui-même discriminé
    par `kind` :
    - `"literal"` (`resolved: true`) : valeur reconstruite par
      `ast.literal_eval`, avec `value` (la valeur Python exacte, y compris
      listes, tuples, dicts et nombres complexes littéraux) et `value_type`
      (`type(value).__name__` — `"str"`, `"int"`, `"float"`, `"tuple"`,
      `"list"`, `"dict"`, `"bool"`, `"NoneType"`, `"complex"`).
    - `"concept"` (`resolved: false`) : référence nue à un concept produit
      ailleurs dans le fichier (ex. `MODELE=MO`) — identifiée statiquement,
      mais pas une valeur Python littérale : `checkCommandSyntax` (lot 10) a
      besoin d'un véritable objet `DataStructure` ici, pas d'un nom (note du
      lot 9 et du lot 10, `docs/development-plan.md`). `concept` porte le nom
      référencé, `source` le texte source exact (`ast.unparse`).
    - `"dynamic"` (`resolved: false`) : valeur non résolue statiquement.
      `reason` est une typologie grossière (`boucle`, `dictionnaire_assemble`,
      `appel_fonction`, `concatenation`, `comprehension`,
      `reference_variable`, `autre`), `node_type` le nom du nœud `ast`
      responsable (`Call`, `Dict`, `BinOp`, ...), `source` le texte source
      exact.
  - `"factor"` : un mot-clé facteur — un appel `_F(...)` reconnu comme tel,
    ou une liste/tuple d'appels `_F(...)` pour des occurrences multiples
    (amendement lot 9). `occurrences` est la liste des occurrences ; chaque
    occurrence porte son propre `keywords`, de même forme, récursivement (un
    mot-clé facteur peut en contenir un autre).
  - Une liste/tuple qui mélange des `_F(...)` et des éléments qui n'en sont
    pas est traitée comme un mot-clé simple non résolu (`dynamic`, raison
    `"autre"`, `node_type: "MixedFactorList"`) et signalée dans
    `parse_warnings` — jamais devinée.
  - `reuse=` est capturé dans son propre champ `reuse` (nom du concept
    réutilisé), jamais mélangé aux entrées de `keywords`.
  - **Limite de résolution assumée** : la résolution ne porte que sur
    l'expression directement portée par le mot-clé. Aucune propagation de
    constante entre instructions n'est tentée, y compris pour une simple
    affectation scalaire Python précédente (`UN = 1.0` puis `VALE=UN`) : une
    réaffectation, un branchement conditionnel ou une boucle rendraient une
    telle valeur devinée, pas déterminée. `UN` y est donc une référence non
    résolue (`"dynamic"`, raison `"reference_variable"`), jamais la valeur
    `1.0`.
- `dynamic` (au niveau du `statement`) vaut vrai dès qu'au moins un mot-clé de
  la commande est `"dynamic"` (jamais pour une simple référence de concept,
  qui est une forme statiquement identifiée, distincte — voir la note du
  lot 9). `unresolved` liste alors le chemin pointé (`COMPORTEMENT[0].RELATION`
  pour un mot-clé sous la première occurrence d'un facteur), un par entrée
  `"dynamic"` rencontrée dans l'arbre — jamais une supposition.
- `control_flow` liste les types de nœuds `ast` de contrôle Python (`If`,
  `For`, `While`, `Try`, `With`) dans lesquels la commande est imbriquée au
  niveau module, de l'extérieur vers l'intérieur ; vide si la commande est au
  niveau du module. Une commande dont `control_flow` n'est pas vide a
  `dynamic: true` et une entrée `unresolved` dédiée (préfixe `"@statement:"`) :
  sa présence, ou son nombre de répétitions, n'est pas déterminée
  statiquement — ceci est distinct, et sans rapport, avec les blocs `Bloc` du
  catalogue (mini-langage `is_in`/`equal_to`/`value`/`not`, propre au
  catalogue Python des commandes, jamais rencontré dans un fichier `.comm`
  utilisateur) : le lot 9 n'évalue ni l'un ni l'autre.
- `mesh_groups`/`node_groups` : valeurs littérales trouvées sous un mot-clé
  dont le nom commence par `GROUP_MA`/`GROUP_NO`, à n'importe quelle
  profondeur de l'arbre, dédupliquées et triées. `modelisations` (mot-clé
  `MODELISATION`), `phenomena` (mot-clé `PHENOMENE`, pluriel : un
  `AFFE_MODELE` peut porter plusieurs occurrences `AFFE`, chacune avec son
  propre `PHENOMENE`), `behaviours` (mot-clés `RELATION`/`RELATION_KIT`) et
  `logical_units` (mot-clé `UNITE`) suivent le même principe.
- `test_statements` est la liste des index (dans `statements`) des commandes
  `TEST_RESU` — uniquement celle-ci, pas `TEST_TABLE`/`TEST_FONCTION`/etc.
  (périmètre du lot 9, `docs/development-plan.md`).
- `external_files` recense, pour chaque `statement` qui porte un mot-clé
  `UNITE` et/ou `FICHIER` littéral à son premier niveau, l'unité logique et/ou
  le chemin référencés. Une seule entrée peut ne porter que l'un des deux
  (ex. `LIRE_MAILLAGE(UNITE=20)`, sans `FICHIER` — l'unité est ouverte
  ailleurs, typiquement par le fichier `.export`).
- `parse_warnings` consigne, sans jamais l'omettre silencieusement, toute
  construction rencontrée que le parseur ne modélise pas : une affectation à
  une cible qui n'est pas un simple nom (`cara[kk] = AFFE_CARA_ELEM(...)`,
  très fréquent dans les fichiers qui bouclent sur plusieurs calculs — la
  commande n'apparaît alors dans aucun `statement`, faute de concept
  identifiable sans deviner), une fonction ou une classe définie au niveau du
  module (son corps n'est pas analysé, le fichier n'étant jamais exécuté pour
  savoir s'il est appelé), un dépaquetage `**kwargs` utilisé pour construire
  les mots-clés d'une commande ou d'un `_F(...)`, des arguments positionnels
  dans un appel de commande. Un `import`, une affectation Python ordinaire
  sans rapport avec une commande, ou une structure de contrôle qui ne contient
  aucune commande ne produisent pas d'avertissement : ce n'est pas une
  construction de commande non gérée, seulement du Python ordinaire.
- **`imported_names`** (amendement lot 10b, point D) liste, dédupliqués et
  triés, les noms explicitement liés par un `import`/`from ... import ...`
  n'importe où dans le fichier — jamais les membres d'un import générique
  (`from ... import *`), qui ne peuvent être énumérés sans exécuter le
  fichier. Ne sert jamais à décider qu'un appel est une commande (voir la
  règle de mise à l'écart module-niveau du §3 concernant `_command_name` du
  parseur, distincte et sans lien : un nom importé est au contraire la façon
  normale dont une vraie commande atteint le fichier, jamais une raison de
  l'exclure). Sert uniquement en aval (`docs/metadata.md` §4) à distinguer
  une commande absente du catalogue extrait mais réelle (importée
  explicitement d'un paquet hors `code_aster.Cata.Commands`, ex.
  `code_aster.MacroCommands`) d'une simple faute de frappe.
- **Mise à l'écart au niveau du nom de commande (amendement lot 10b,
  point C).** Un appel `NOM(...)` n'est reconnu comme commande que si `NOM`
  correspond à `_COMMAND_NAME_RE` **et** n'est pas défini par le fichier
  lui-même : une classe, une fonction, ou une variable Python ordinaire liée
  au niveau module (au besoin sous `if`/`for`/`while`/`try`/`with`, jamais
  dans le corps d'une fonction ou d'une classe imbriquée — portée Python
  différente) l'emporte toujours, quelle que soit sa casse. Un nom importé
  n'est jamais mis à l'écart par cette règle (voir `imported_names`
  ci-dessus) : c'est la seule façon dont une commande réelle arrive dans le
  fichier.
- `raw_text` conserve le texte exact (`ast.get_source_segment`), indentation
  comprise, afin qu'aucune restitution ne repose sur une reconstruction.
- Un fichier qui n'est pas syntaxiquement du Python lève `CommParseError`
  (`aster_expert.parsing.errors`) — jamais une analyse partielle silencieuse.

## 4. Rapport de validation

Structure produite par `aster_expert.validation.validate` (lot 10, amendé
lot 10b, lot 10c), par délégation à `checkCommandSyntax`
(`code_aster.Cata.SyntaxChecker`) et, pour le type d'un concept produit par
une commande à `result_type_dynamic` vrai (§2), à `Command.get_type_sd_prod`
— jamais une grammaire, une règle de cardinalité, ni un calcul de type
réimplémenté. Modèles pydantic dans `aster_expert/validation/models.py`.

```json
{
  "file_path": "chemin/du/fichier.comm",
  "aster_version": "17.4.0",
  "image_digest": "sha256:d8d19ea9...",
  "validation_level": "B",
  "catalogue_hash": "sha256:...",
  "valid": false,
  "errors": [
    {
      "code": "UNKNOWN_KEYWORD",
      "command": "STAT_NON_LINE",
      "statement_index": 5,
      "line": 42,
      "path": ["COMPORTEMENT", "RELATON"],
      "variant_id": null,
      "message": "Unauthorized keyword: 'RELATON'",
      "suggestion": "RELATION",
      "source": "checkCommandSyntax"
    }
  ],
  "warnings": [],
  "commands_checked": [
    {"statement_index": 4, "command": "AFFE_MODELE", "line": 12, "ok": true, "warnings": []},
    {"statement_index": 5, "command": "STAT_NON_LINE", "line": 40, "ok": false, "warnings": []}
  ],
  "commands_not_checked": [
    {
      "statement_index": 7,
      "command": "CALC_CHAMP",
      "line": 88,
      "reasons": ["unresolved keyword: RESULTAT[0].NOM_CHAM"]
    }
  ],
  "checked_at": "2026-01-01T00:00:00+00:00"
}
```

Règles :

- `validation_level` ne dépasse jamais ce qui a réellement été fait.
- `image_digest` (amendement lot 10) identifie, par digest — jamais par tag,
  voir `docs/architecture.md` ADR-002 — le catalogue confronté, indépendamment
  de la chaîne lisible `aster_version`. Ce sont deux données indépendantes,
  jamais déduites l'une de l'autre (même principe qu'au lot 4,
  `docs/metadata.md` §2).
- **`commands_checked`/`commands_not_checked`** (amendement lot 10) : une
  simple liste de noms de commandes ne permet ni de distinguer deux
  occurrences de la même commande, ni de rapporter un motif ou une ligne —
  strictement insuffisant pour la mesure de sortie exigée par ce lot
  (`docs/development-plan.md`). Chaque entrée porte `statement_index` (index
  dans `statements` du lot 9), `command` et `line` (`line_start` du
  `statement`, seule granularité disponible : le lot 9 ne trace pas de
  numéro de ligne par mot-clé). `commands_checked[].ok` vaut faux exactement
  quand une entrée de `errors` partage ce même `statement_index` — redondant
  avec `errors` mais évite un croisement au lecteur du rapport.
  `commands_not_checked[].reasons` liste **toutes** les conditions
  structurelles rencontrées parmi les trois de la RÈGLE ABSOLUE du lot 10
  (mot-clé non résolu, `parse_warning` du lot 9 concernant ce `statement`,
  `control_flow` non vide) — jamais seulement la première — plus, le cas
  échéant, une entrée unique décrivant pourquoi un concept référencé reste
  non résolu (voir plus bas) : jamais devinée, jamais silencieuse.
- **RÈGLE ABSOLUE (lot 10, aucun faux positif)** : un `statement` du lot 9
  n'est jamais confronté à `checkCommandSyntax` dès lors qu'il porte un
  mot-clé non résolu statiquement, est concerné par un `parse_warning` du
  lot 9 (rapprochement par recouvrement de plage de lignes, faute de
  `statement_index` porté par `ParseWarning`), ou se trouve sous un
  `control_flow` non vide. Mieux vaut sous-déclarer que remonter une erreur
  inexistante ; le taux de commandes non vérifiées est à rapporter tel quel,
  jamais masqué.
- **Résolution du type d'un concept produit, en direct (amendement lot 10b,
  point A) — remplace le mécanisme du lot 10.** Le lot 10 calculait une
  table concept → type *hors conteneur*, à partir du seul `result_type`
  statique du catalogue (§2) : un concept produit par une commande à
  `result_type_dynamic` vrai (94 commandes sur 268 en 17.4.0 — `LIRE_MAILLAGE`,
  `CALC_CHAMP`, `CREA_CHAMP`, `CREA_RESU`, ... — voir le compte rendu du
  lot 10b) restait donc toujours de type inconnu, quel que soit le contenu du
  fichier ; c'était la première cause des 225 erreurs et du taux de 53 % du
  lot 10. Le lot 10b ne calcule plus ce type lui-même : un mot-clé qui
  référence un concept (`reuse=` compris) est reconstruit en un marqueur
  `{"__concept_ref__": "<nom>"}`, jamais un type deviné à l'avance
  (`aster_expert.validation.reconstruct`, M2). `scripts/check_command_syntax.py`
  (M3), exécuté dans le conteneur, traite les `statement` d'un même fichier
  **dans l'ordre**, maintient une table de placeholders vivante, et, pour
  chaque `statement` qui passe `checkCommandSyntax`, appelle
  `command.get_type_sd_prod(**keywords)` — la méthode officielle qui ajoute
  les mots-clés par défaut, complète les arguments manquants de `sd_prod` par
  `None`, et distingue elle-même un `Operator` (`sd_prod(**ctxt)`) d'un
  `Macro` (`sd_prod(self, **ctxt)`) — pour enregistrer le placeholder produit
  sous le nom du concept assigné, disponible aux `statement` suivants. Un
  `reuse=` n'est pas un cas particulier séparé : pour une commande réentrante,
  l'objet produit est l'objet réutilisé par construction (vérifié
  empiriquement, voir le compte rendu de lot), donc le même appel uniforme
  donne déjà la bonne réponse. Une exception (le type reste alors inconnu
  pour tout `statement` ultérieur qui le référence, sans jamais bloquer le
  `statement` producteur lui-même s'il a par ailleurs réussi
  `checkCommandSyntax`) ou une référence à un concept jamais résolu (parce
  que son producteur a lui-même été exclu, a échoué, ou n'a pas encore été
  atteint) ne provoque jamais de repli par défaut ni de supposition — un
  `statement` de ce type devient `commands_not_checked`, avec, dans
  `reasons`, le nom du concept et le statut de son producteur (index de
  `statement`, exclu ou en échec). Jamais un type deviné à partir du nom de
  la commande ou de la ressemblance avec un autre concept.
- **Règle du placeholder en deux branches (amendement lot 10c, point P1) —
  assouplit, sans le contredire, le mécanisme ci-dessus.** Le lot 10b
  n'enregistrait un placeholder qu'après un `checkCommandSyntax` réussi sur
  le `statement` producteur — correct pour un `result_type_dynamic` vrai
  (le type dépend réellement des mots-clés), inutilement pénalisant pour un
  `result_type` statique : le type produit est alors un **fait du
  catalogue**, indépendant du contenu ou de la résolubilité des mots-clés
  du producteur. Prouvé par lecture directe de `Command.get_type_sd_prod`
  (`Cata/Language/SyntaxObjects.py`) : la branche non-fonction ignore
  totalement `ctxt` (`if type(resultType) is types.FunctionType: ... else:
  return resultType`) — l'appeler avec un dict vide est aussi correct que
  l'appeler avec les mots-clés reconstruits. `scripts/check_command_syntax.py`
  distingue donc deux branches, décidées par le même fait de catalogue que
  `result_type_dynamic` (`isinstance(command.definition.get("sd_prod"),
  type)`) :
  - **statique** : le placeholder est enregistré **immédiatement**, avant
    même de tenter `compat_syntax`/`checkCommandSyntax` sur le `statement`
    producteur — y compris pour un `statement` **exclu** par la RÈGLE
    ABSOLUE (mot-clé non résolu, `parse_warning`, `control_flow`). Un tel
    `statement` exclu ne devient jamais `commands_checked` pour autant — sa
    propre entrée `commands_not_checked` et ses motifs restent inchangés,
    décidés uniquement par `aster_expert.validation.reconstruct` — mais il
    contribue désormais un placeholder via une requête `"type_probe"`
    (nom de commande et concept assigné seuls, aucun mot-clé) envoyée au
    même script, dans le même ordre de fichier, sans jamais être confronté
    au vérificateur. Ceci ne viole pas la RÈGLE ABSOLUE : aucun verdict
    n'est rendu sur le `statement` exclu lui-même, seul un fait de
    catalogue indépendant de ses mots-clés est exploité ;
  - **dynamique** : inchangé du lot 10b — placeholder après
    `checkCommandSyntax` réussi uniquement.
  - **Producteur en erreur (et non simplement non vérifié).** Un
    `statement` producteur à `result_type` statique qui échoue son propre
    `checkCommandSyntax` (une vraie entrée `errors`) a néanmoins déjà
    enregistré son placeholder (branche statique, ci-dessus) : un
    `statement` consommateur qui le référence directement est donc
    quand même confronté au vérificateur, mais son entrée
    `commands_checked` porte un `warnings` non vide nommant le
    `statement` producteur en erreur — jamais pour un producteur
    simplement `commands_not_checked` (exclu), qui ne déclenche aucun
    avertissement : ce n'est pas une anomalie, seulement l'exploitation
    d'un fait de catalogue disponible immédiatement. Cette distinction
    explicite entre **« non vérifié »** (`commands_not_checked`, aucun
    verdict rendu) et **« en erreur »** (`errors`, un vrai rejet du
    vérificateur officiel) est reprise partout dans le code de validation
    — jamais confondues.
- **`CheckedEntry.warnings` (amendement lot 10c, points P1 et P3).** Liste
  de mises en garde textuelles, non vide uniquement dans deux cas, jamais
  pour signaler un doute non étayé :
  - ce `statement` dépend directement d'un concept dont le producteur est
    en erreur (voir ci-dessus, P1) ;
  - ce `statement` a été rejeté par `checkCommandSyntax` selon une
    signature **confirmée par exécution réelle** comme un faux positif du
    contrôle statique de ce projet, jamais de `checkCommandSyntax`
    lui-même (amendement lot 10c, point P3, voir plus bas) : dans ce seul
    cas, `ok` vaut `true` malgré le rejet du vérificateur — le fait
    qu'une exécution réelle d'un cas test officiel équivalent atteigne
    `FIN` est une preuve de niveau C, plus forte que le rejet statique de
    niveau B (`docs/architecture.md`, niveaux de validation) ; le
    `warnings` documente toujours la preuve précise (cas test, lignes),
    jamais une affirmation sans citation.
- **Faux positifs statiques confirmés par exécution (amendement lot 10c,
  point P3), routés vers `commands_checked` avec `ok: true` et un
  `warnings`, jamais vers `errors`.** `EXTR_COUPE` déclare un `sd_prod`
  statique unique (`cham_gd_sdaster`), mais son exécuteur
  (`code_aster/MacroCommands/extr_coupe_ops.py`) peut retyper le résultat
  extrait comme le `RESULTAT` d'origine via `LIRE_RESU(TYPE_RESU=resu.
  getType(), ...)` — un sous-type de `resultat_sdaster` (`evol_*`), jamais
  littéralement `cham_gd_sdaster` : un désaccord réel entre la déclaration
  statique du catalogue et le comportement effectif, dépendant du chemin
  d'exécution, indécidable par simple lecture du catalogue. Confirmé par
  exécution réelle (`run_aster`, dans le conteneur, hors périmètre
  d'infrastructure du lot 12 — exécution ponctuelle de diagnostic
  seulement) d'un cas test officiel portant exactement ce motif
  (`astest/zzzz169a.comm`, `CREA_CHAMP(OPERATION="EXTR", RESULTAT=<résultat
  EXTR_COUPE>)` et `POST_RELEVE_T(ACTION=_F(RESULTAT=<résultat
  EXTR_COUPE>, ...))`) : `DIAGNOSTIC JOB : OK`, tous les `TEST_RESU`/
  `TEST_TABLE` réussis. Le contrôle statique de ce projet est donc plus
  strict que le superviseur réel sur ce motif précis, jamais l'inverse —
  reconnu **uniquement** quand le concept `RESULTAT`/`ACTION.RESULTAT`
  rejeté provient directement d'un `statement` `EXTR_COUPE` (vérifié
  mot-clé par mot-clé, jamais deviné du seul texte du message) : une même
  incompatibilité de type `cham_gd_sdaster`/`resultat_sdaster` issue d'un
  autre producteur reste une vraie `errors` `INVALID_TYPE`.
- **Trois issues qui ne sont jamais un verdict de syntaxe (amendement
  lot 10b, points D et E), routées vers `commands_not_checked`, jamais
  `errors` :**
  - une commande absente du catalogue extrait **mais explicitement importée**
    dans le fichier (`imported_names` du lot 9, §3) : elle existe réellement
    mais hors `code_aster.Cata.Commands` (typiquement
    `code_aster.MacroCommands`, ex. `DEFI_CONT`, `MACR_ROTA_GLOBALE` — jamais
    introspectée par le lot 4, voir `docs/development-plan.md`, lot 4). Une
    commande absente du catalogue **et non importée** reste une vraie
    `UNKNOWN_COMMAND` dans `errors` : une faute de frappe, pas une lacune de
    couverture ;
  - un nom du catalogue qui n'est pas une instance de `Command`
    (`code_aster.Cata.Language.SyntaxObjects.Command`) : `VARIABLE`
    (`code_aster.Cata.Commands.variable.VariableSupport`, un objet
    catalogue non standard) en est le seul exemple constaté sur la version
    17.4.0 — jamais soumis à `checkCommandSyntax`, qui suppose un `Command` ;
  - un concept référencé jamais résolu par le batch en cours (voir le point
    précédent).
- **`FORMULE` (amendement lot 10b, point E, déclaré explicitement plutôt que
  subi).** `FORMULE` accepte, en plus de `VALE`/`VALE_C`/`NOM_PARA` (les
  seuls mots-clés du catalogue), des mots-clés libres portant les constantes
  nommées de l'expression (ex. `FORMULE(NOM_PARA="X", VALE="A*X+B", A=2.0,
  B=1.0)`). Le mécanisme officiel qui les retire avant vérification
  (`FormulaDefinition.change_syntax`,
  `code_aster/CodeCommands/formule.py`) vit dans la couche d'exécution
  (`libaster`, indisponible dans ce conteneur — `docs/architecture.md`,
  ADR-002) et ne peut donc pas être rejoué comme un `compat_syntax` de
  catalogue (point B). `aster_expert.validation.reconstruct` (M2) reproduit
  cette seule substitution, de façon étroite et documentée : tout mot-clé
  autre que `VALE`/`VALE_C`/`NOM_PARA` est retiré avant l'appel à
  `checkCommandSyntax`, jamais une grammaire propre au projet. Une commande
  `FORMULE` n'apparaît donc jamais dans `commands_not_checked` pour cette
  seule raison.
- `variant_id` (amendement lot 10) : résolu depuis `path` via
  `find_keyword_variants` (lot 4b) uniquement quand exactement une variante
  correspond ; `null` sinon — y compris quand `path` lui-même n'existe pas
  dans le catalogue (mot-clé inconnu) ou reste ambigu (plusieurs variantes,
  lot 4b C1). Jamais choisi silencieusement parmi plusieurs candidats.
- `path` provient de la pile (`CheckerError._stack`, "/"-séparée) que
  `checkCommandSyntax` construit lui-même ; à défaut (exception brute sans
  pile — mot-clé obligatoire absent, règle violée), du nom de mot-clé
  extrait du message quand le motif le permet, `[]` sinon. Ce n'est jamais
  une reconstruction indépendante du chemin.
- `source` vaut `"checkCommandSyntax"` pour toute entrée où le vérificateur
  officiel a effectivement été appelé (y compris ses exceptions brutes,
  `KeyError`/`ValueError`/`TypeError` non enveloppées — voir
  `docs/development-plan.md`, lot 10), `"catalogue"` uniquement pour
  `UNKNOWN_COMMAND` : la commande elle-même est absente du catalogue local,
  donc il n'existe aucun objet `Command` à passer à `checkCommandSyntax`.
- `code` est une classification du message déjà décidé par le vérificateur
  (`UNKNOWN_KEYWORD`, `MISSING_MANDATORY_KEYWORD`, `INVALID_TYPE`,
  `INVALID_VALUE`, `INVALID_VALUE_CARDINALITY`,
  `INVALID_OCCURRENCE_CARDINALITY`, `REUSE_NOT_ALLOWED`,
  `RESULT_TYPE_ERROR`, `INVALID_STRUCTURE`, `RULE_VIOLATION`,
  `UNKNOWN_COMMAND`, ou `CHECKER_ERROR` pour une forme de message non encore
  répertoriée — jamais silencieusement absorbée, le texte original est
  conservé intégralement dans `message`), jamais une décision de validité
  propre au projet.
- `suggestion` provient d'une distance d'édition (`difflib.get_close_matches`)
  sur les noms du catalogue. Elle est présentée comme une suggestion, jamais
  comme une correction établie — **sauf** pour un nom de commande
  individuellement confirmé absent du catalogue par une investigation
  propre à ce projet (amendement lot 10c, point P4/R4,
  `aster_expert.validation.validate._CONFIRMED_ABSENT_COMMANDS`) : `POST_GOUJ`
  en est le seul exemple constaté sur la version 17.4.0 — absent de tout
  `code_aster` 17.4.0 (source comme paquet du conteneur), une commande
  disparue du produit depuis une dizaine de versions majeures, encore
  appelée dans deux cas tests officiels devenus orphelins
  (`astest/zzzz120a.comm`, `astest/zzzz120b.comm`) : un vrai défaut de ces
  deux fichiers, pas une faute de frappe. Dans ce seul cas, `suggestion`
  vaut `null` (jamais une correspondance de distance d'édition trompeuse) et
  `message` porte directement le fait établi plutôt que le texte générique
  du vérificateur. Une table étroite, qui ne grandit que sur preuve, jamais
  une règle générale : `_suggest` seul ne peut pas distinguer une commande
  supprimée d'une commande mal orthographiée.
- `commands_not_checked` est obligatoire et non vide dès qu'une commande n'a pas
  pu être confrontée au catalogue. Un silence sur ce point est interdit.

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
