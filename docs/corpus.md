# Corpus

## 1. Sources

| Source | Dépôt | Contenu attendu | Licence |
|--------|-------|-----------------|---------|
| `codeaster-src` | `https://gitlab.com/codeaster/src.git` | sources, catalogues, cas tests de vérification, guide développeur | GPL v3 |
| `codeaster-doc` | `https://gitlab.com/codeaster/doc/docaster.git` | manuels U, R, V, D | GFDL v1.3 |

Les deux dépôts sont clonés sous `external/`, jamais commités, et déclarés dans
`config/sources.yaml`.

Une troisième source, l'installation Code_Aster locale elle-même, fournit le
catalogue effectivement appliqué. Elle n'est pas clonée : elle est introspectée.
C'est la seule source faisant autorité en matière de syntaxe.

## 2. État d'inspection

Au moment de la rédaction, la structure interne des deux dépôts n'a pas été
vérifiée. Les chemins internes ne doivent pas être écrits en dur avant
inspection. Le premier lot de corpus a pour objet cette inspection.

Points à établir avant toute écriture de parseur :

1. Emplacement et format des catalogues de commandes dans `codeaster/src`.
2. Emplacement des cas tests, et fichiers associés à chaque cas
   (`.comm`, `.mmed`, `.export`, `.mail`, fichiers de référence).
3. Format des sources documentaires dans `docaster` : texte structuré,
   traitement de texte, ou document composé. Cette réponse détermine à elle
   seule la faisabilité et le coût du lot de parsing documentaire.
4. Existence d'un rendu construit exploitable (HTML) et de sa procédure de
   construction.
5. Convention de nommage des tags de version des deux dépôts, et correspondance
   entre version de code et version documentaire.

Tant que le point 3 n'est pas tranché, deux stratégies restent ouvertes :
parsing des sources, ou consommation d'un rendu construit. Ne pas en choisir
une par défaut.

## 3. Familles documentaires

| Famille | Objet | Usage dans le système |
|---------|-------|-----------------------|
| U1 | présentation générale, supervision | contexte |
| U2 | guides méthodologiques | démarche de modélisation |
| U3 | formats et fichiers | entrées/sorties |
| U4, U7 | documentation des commandes | sémantique des mots-clés |
| R | références théoriques | hypothèses, formulations, lois |
| V | documents de validation | cas de référence et valeurs attendues |
| D | documents divers | selon contenu |
| cas tests | fichiers exécutables | exemples de mise en œuvre |
| catalogue | définition formelle | grammaire, seule autorité syntaxique |

Cette classification est celle attendue. Elle doit être confirmée par
l'inventaire réel et non présumée exhaustive.

## 4. Politique de version

Une version cible est un triplet :

- version de code (déterminée par l'installation) ;
- tag ou branche du dépôt `src` correspondant ;
- tag ou branche du dépôt `docaster` correspondant.

Règles :

1. Aucun fragment n'entre dans un index sans étiquette de version.
2. Une requête sans version explicite utilise la version cible déclarée dans
   `config/versions.yaml`, et l'indique dans la réponse.
3. Un fragment issu d'une version différente de la version interrogée n'est
   jamais renvoyé silencieusement. Il peut l'être avec un avertissement
   explicite, si aucun fragment de la bonne version ne répond.
4. Les correspondances entre versions sont déclarées, jamais déduites d'une
   similarité de numérotation.

## 5. Manifeste de synchronisation

Chaque exécution de `aster-expert sources sync` écrit
`data/raw/manifest.json` :

```json
{
  "generated_at": "2026-01-01T00:00:00+00:00",
  "sources": [
    {
      "name": "codeaster-src",
      "url": "https://gitlab.com/codeaster/src.git",
      "ref": "v18.0.0",
      "commit": "0000000000000000000000000000000000000000",
      "local_path": "external/codeaster-src",
      "synchronized_at": "2026-01-01T00:00:00+00:00",
      "dirty": false,
      "families": ["catalogue", "testcases"]
    }
  ]
}
```

Le champ `dirty` signale des modifications locales non commitées. Une source
`dirty` bloque la synchronisation de cette source et le fait est journalisé.

**Amendement lot 3.** Chaque entrée porte aussi `status` (`"cloned"`,
`"adopted"`, `"blocked_dirty"`, `"blocked_diverged"`, `"blocked_error"`) et
`detail` (texte explicatif, obligatoire pour tout `status` `blocked_*`) :
une simple liste de noms/commits ne permet pas de distinguer une source
réellement synchronisée d'une source dont la synchronisation a été refusée,
ce que `CLAUDE.md` interdit de faire silencieusement. `"cloned"` et
`"adopted"` signifient tous deux que la copie de travail correspond
exactement à la déclaration (`ref` résolu sur le dépôt distant) : le premier
la première fois qu'une source est clonée, le second à toute exécution
suivante où elle s'y trouvait déjà — l'idempotence porte sur ce second cas
(deux exécutions consécutives sur une source déjà présente et à jour
produisent le même `status`, le même `commit`, le même `detail`), jamais sur
la comparaison d'un premier clonage à une absence de dépôt, qui n'a pas de
sens. Une source existante dont le commit courant diverge de ce que `ref`
résout sur le dépôt distant n'est jamais réalignée d'autorité : `status`
vaut `"blocked_diverged"`, `detail` cite les deux commits, et la copie de
travail n'est ni `checkout`-ée ni `reset`-ée (`aster_expert.ingestion.sync`).

## 6. Inventaire

L'inventaire produit `data/raw/inventory.jsonl`, une entrée par document
identifié, avant tout découpage. Champs attendus : identifiant documentaire,
titre, famille, version, chemin relatif, format source, taille, empreinte,
liens internes repérés, fichiers associés.

L'inventaire produit également :

- des statistiques par famille et par version ;
- une liste d'anomalies : document sans identifiant, identifiant en double,
  document orphelin, lien interne non résolu, format inattendu.

Les anomalies ne sont pas corrigées silencieusement. Elles sont listées et
tranchées explicitement.

## 7. Découpage

Le découpage n'est pas fondé sur une taille fixe. Règles cibles, à valider par
le banc d'évaluation :

- U4 et U7 : un fragment par commande, puis par mot-clé facteur, puis par
  mot-clé simple, en conservant le rattachement hiérarchique ;
- R : section théorique complète, équations et définitions maintenues
  ensemble ;
- V : problème, modélisation, valeurs de référence, synthèse, séparés mais liés ;
- cas tests : blocs fonctionnels et commandes, avec numéros de lignes ;
- catalogue : un fragment par commande, issu de l'introspection, pas du texte.

Contrôles automatiques exigés :

1. aucun contenu significatif perdu entre le document source et l'ensemble de
   ses fragments ;
2. chaque fragment rattaché à une source, un chemin et une version ;
3. liens U/R/V/cas tests conservés lorsqu'ils existent dans la source ;
4. idempotence : deux exécutions sur la même révision produisent des fragments
   identiques.

## 8. Jeu d'évaluation

`data/evaluations/questions.jsonl` contient les questions de référence :

```json
{
  "id": "eval-001",
  "question": "Comment définir un choc unilatéral entre deux noeuds ?",
  "version": "18",
  "expected_documents": ["U4.44.01"],
  "expected_commands": ["DEFI_MATERIAU", "AFFE_CHAR_MECA"],
  "domain": "mecanique_non_lineaire",
  "origin": "travail reel"
}
```

Les questions proviennent de problèmes réellement rencontrés, pas de
reformulations de la documentation. Une question dont la réponse attendue n'est
pas vérifiée dans la documentation n'entre pas dans le jeu.
