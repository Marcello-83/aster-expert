# Lot 50 quinquies — Charges : un MED et un script pour Salomé-Méca, rien d'autre

**Tout en français. Profil `vm`. Branche `lot-50quinquies`, depuis `main`
après fusion de `lot-50quater` (intégration continue verte).** Consigne copiée
dans `docs/lots/lot50quinquies_consigne.md`. Elle **remplace** les versions 1
et 2, non lancées.

## Objectif, fixé par MM

Pour chaque projet, deux livrables simples :

1. un **`charges.med`** des cas de charge ;
2. un **script `.py` que MM lance lui-même dans Salomé-Méca** (module ParaVis).
   Il affiche, cas par cas, des **flèches** d'application des efforts.

Les visées « ParaView Windows » et « .vtu » du lot 50 quater sont
abandonnées : Salomé-Méca lit le MED nativement. Aucune exécution
Code_Aster. Règles d'économie habituelles.

## 1. Le MED : celui que Code_Aster écrit déjà

Le post-traitement du tronc commun produit déjà, par Code_Aster, le bon
contenu. Pour `pontons_alu_01`, c'est `resultats/livrables/med/charges.med`
de l'exécution `20261012T144424-430251f1` :

- un champ de forces nodales par cas (`FN_<cas>`, `FV_<cas>`) ;
- un champ de température par cas thermique (`VARC_<cas>_TEMP_1`).

Ce fichier **devient le livrable**, tel quel.

- **Désactiver par défaut**, sans les supprimer :
  - le reconditionnement du lot 50 quater (16 pas, `CHARGE_REPARTIE`,
    `ECART_TEMPERATURE`) ;
  - la lecture statique du `.comm` ;
  - les `.vtu`.
- **Documenter dans le compte rendu**, en une ligne chacun :
  - ce que contiennent `FN_` et `FV_` et pourquoi deux préfixes ;
  - la commande Code_Aster qui les écrit, avec sa source (catalogue ou U4).

## 2. Le script `charges_salome.py`

Généré par le tronc commun, court, lisible, modifiable à la main.

**En-tête de paramètres :**

- `FICHIER_MED` : chemin absolu dans la VM, rempli à la génération (chemin du
  dépôt sur `/media/sf_partage`) ;
- `CAS_AFFICHE` ;
- `FACTEUR_ECHELLE` : `None` par défaut, pour l'échelle automatique par cas ;
- `SOUS_ECHANTILLONNAGE`.

**Comportement :**

- Ouvre le MED. Si le fichier est introuvable, le script s'arrête
  **avant de créer quoi que ce soit**, avec le message : « renseigner
  FICHIER_MED en tête du script ».
- Affiche le modèle en fond, en filaire gris.
- Pour chaque cas mécanique, crée un objet de pipeline nommé `Cas <nom>` :
  - flèches orientées selon le vecteur force ;
  - couleur selon la norme, légende en kN ;
  - **échelle propre au cas** : la plus grande flèche vaut 15 % de la taille
    du modèle.
- Pour les cas thermiques : éléments colorés selon la température, plage
  symétrique, sans flèches par défaut.
- Fonction `afficher_cas("Q")` : cache les autres cas, puis **recale la
  légende sur le cas affiché**. C'est le correctif du défaut de légende
  partagée du lot 50 quater.
- Titre : cas et résultante (ΣFX, ΣFY, ΣFZ en kN).

**Essais obligatoires dans l'image Salomé-Méca de la VM**, pas seulement en
`pvbatch` :

- exécution par `exec(open(...).read())`, sans `__file__` et depuis un autre
  dossier courant (situation de MM) ;
- chargement de MEDReader tel que ParaVis le fait.

Le `LISEZMOI.txt` fait 5 lignes au plus : comment lancer le script dans
Salomé-Méca, avec le menu exact vérifié dans la version installée, et
comment changer de cas.

## 3. Sous-étape `images` : manifeste de 10 Mo

Correctif minimal pour que la chaîne ne soit plus en échec : le script des
résultats lit le manifeste dans un fichier JSON voisin au lieu de l'embarquer
(`paraview.py:200`). Un test avec un manifeste synthétique de plus de 10 Mo.

Aucune autre évolution du post-traitement des résultats dans ce lot.

## Dépôt

`/media/sf_partage/echanges/lot50quinquies/pontons_alu_01/` :

- `charges.med` ;
- `charges_salome.py` ;
- `LISEZMOI.txt` ;
- `png/` : 16 vues iso rendues par le script lui-même ;
- `empreintes.sha256`.

## Compte rendu attendu — EN FRANÇAIS, court

- Contenu du MED (champs, préfixes, commande source).
- Résultat des deux essais du §2.
- Correctif `images`.
- Fichiers déposés.
- Tests, `rex` et interventions.

## Interdits

- Aucune exécution Code_Aster.
- Aucune modification du `.comm` ni des résultats.
- Aucune modification des autres projets, en dehors du tronc commun et de ses
  tests.
