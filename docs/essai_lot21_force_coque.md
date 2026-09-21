# Lot 21 — Essai d'exécution : `FORCE_COQUE` sur une surface courbe

Premier essai d'exécution ciblé de la chaîne (`aster-expert run`, niveau C). Modèle
entièrement synthétique, aucun fichier de MM lu ou copié.

## Question

La documentation (U4.44.01, lot 20) ne dit pas si l'intensité de `FORCE_COQUE`
se rapporte à la surface développée des mailles ou à leur surface projetée.

## Modèle

- Demi-cylindre de rayon 0,71 m et de hauteur 1,00 m (axe Z, θ de −90° à +90°,
  plan diamétral X = 0), acier élastique isotrope (E = 2,1×10¹¹ Pa, ν = 0,3),
  épaisseur 0,010 m (h/R ≈ 1/71, mince), `MODELISATION = "DKT"`.
- Maillage : 36 × 10 = 360 QUAD4 plans (facettes de 5°), 407 nœuds, écrit par
  `scripts/build_fcoque_essai.py` **au format ASCII natif de Code_Aster**
  (`LIRE_MAILLAGE`, `FORMAT = "ASTER"`) : ni Salomé, ni bibliothèque MED. Le
  script est déterministe ; un test le rejoue octet pour octet.
- Chargement : `FORCE_COQUE = _F(GROUP_MA="COQUE", FX=1.0)`, sur toute la surface.
- Appuis isostatiques : nœud A (θ = −90°, z = 0) DX, DY, DZ ; nœud B (θ = +90°, z = 0)
  DX, DZ ; nœud C (θ = −90°, z = H) DX. Six blocages, six mouvements de corps
  rigide.
- Post-traitement : `CALC_CHAMP(FORCE="REAC_NODA")`, puis `POST_RELEVE_T` avec
  `RESULTANTE=("DX","DY","DZ")` sur le groupe des trois appuis.

Fichiers versionnés (`data/examples/fcoque_essai/`) : `demi_cylindre.mail`,
`demi_cylindre.comm`, `demi_cylindre.export`, `mess_execution_lot21.txt` (le `.mess`
analysé, copie de `fort.6`). Racine ajoutée à `execution.allowed_roots`
(`config/validation.yaml`), pour ce seul essai.

## Commandes et sorties

```
aster-expert validate data/examples/fcoque_essai/demi_cylindre.comm
  Niveau de validation : B ; Commandes vérifiées : 12/12 (100.0 %) ; Erreurs : 0
aster-expert run data/examples/fcoque_essai/demi_cylindre.comm
  Statut : completed_ok ; Diagnostic : OK ; 11,4 s
  version 17.4.0, image sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5
  .mess : data/processed/runs/20260921T093900-2a80f342/proc.0/fort.6
```

Table imprimée dans le `.mess` :

```
INTITULE         RESU     NOM_CHAM         NUME_ORDRE   INST         DX           DY           DZ
RESULTANTE_REACT 00000007 REAC_NODA                   1  0.00000E+00 -2.22982E+00 -1.22888E-10 -3.63536E-11
```

**Alarmes du `.mess` analysé : aucune** (« aucune alarme » dans la liste des
alarmes de fin de calcul ; aucune balise `<A>`).

Une première exécution a échoué (`<S>_ERROR`, exception CALCULEL_6) et son
`.mess` portait deux alarmes, énoncées ici plutôt que masquées :
`MODELISA5_8` (« La maille MA1 est en double dans le GROUP_MA COQUE ») et
`CALCULEL_58` (composante COQ_NCOU manquante sur la maille 17). Cause : le groupe
`COQUE` était écrit sur une seule ligne de 360 noms, mal lu par le format ASTER
(enregistrements de largeur fixe). Correction : liste de noms répartie sur des
lignes de 8 noms. Le fichier versionné est celui de la seconde exécution.

## Comparaison

| Référence | Valeur (m²) | Écart relatif de \|résultante\| = 2,22982 |
|---|---|---|
| Surface développée π × 0,71 × 1,00 | 2,230531 | −0,032 % |
| Surface développée des facettes (calcul exact, 36 cordes) | 2,229823 | −0,0001 % (à la précision d'impression, 5 chiffres) |
| Surface projetée 1,42 × 1,00 | 1,420 | +57,03 % |

Les composantes DY et DZ de la résultante valent ~10⁻¹⁰, soit ~5×10⁻¹¹ de DX
(équilibre).

## Constat

**L'intensité de `FORCE_COQUE` se rapporte à la surface développée des mailles,
non à la surface projetée** : la résultante des réactions vaut 2,22982 N pour une
intensité unitaire, soit la surface des facettes (2,229823 m²), pour cette
modélisation (DKT, QUAD4), cette version (17.4.0) et ce cas (composante globale
constante). Conséquence pratique, à traiter au lot suivant sans être décidée ici :
une intensité exprimée par surface projetée devrait être ramenée à la surface
développée de chaque maille (facteur variable avec l'inclinaison de la facette).

Niveau de validation atteint : **C** (exécution jusqu'à `FIN`, sans alarme).
**D** atteint pour cet essai seul : la résultante correspond à l'une des deux
hypothèses à mieux que 1 % (−0,03 %) et le contrôle d'équilibre (DY, DZ nuls)
est satisfait. Ce niveau ne vaut que pour la question posée ; il ne dit rien du
comportement de la coque orthotrope, ni du calcul du combi-wall.

## Consignation dans la fiche : proposition, non implémentée

Le schéma de la fiche ne porte pas de source « exécution » : `CodeAsterSource` est
l'union `DocumentarySource | CatalogueSource`, l'une exigeant un extrait de
documentation, l'autre une référence de catalogue. Le résultat n'est donc **pas**
enregistré comme constat `code_aster`. Modification minimale proposée (non
implémentée, à décider) : une troisième classe `ExecutionSource` dans l'union
`CodeAsterSource`, gelée, avec `aster_version`, `image_digest`, `case_path`
(chemin du cas, relatif au dépôt), `case_sha256`, `mess_path`, `observed` (texte de
la grandeur relevée, ici la résultante), la règle N1 (« un extrait réel ») étant
remplacée pour cette classe par la présence de `mess_path` et de `observed`.
Les faits résultant d'une exécution resteraient explicitement distincts des
sources documentaires.

## Limites

- Un seul maillage (36 facettes), une seule modélisation (DKT, QUAD4), une seule
  direction de charge (X), une intensité uniforme : le facteur mesuré est celui
  de la surface développée ; il n'est pas testé sur des TRIA3, ni sur COQUE_3D.
- Résultante lue avec 5 chiffres significatifs (`FORMAT_R = E12.5`).
- Les alarmes analysées sont celles du `.mess` (`fort.6`) ; aucune extension
  maison du parseur n'a été écrite.
