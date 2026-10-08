# Lot 49 — consigne (recopiée de la demande de MM)

# Lot 49 — Livrables de résultats : MED, visualisation des charges, ParaView, Excel, interrogation des résultats

**Tout en français. Profil `vm`.** Branche `lot-49`, depuis `main` après la
fusion de `lot-47quater` et la lecture de l'audit du lot 48 s'il est terminé.
Termes interdits : ceux du lot 47. Consigne copiée dans
`docs/lots/lot49_consigne.md`.

## Pourquoi

Le point noir de l'outil, relevé par MM et confirmé par deux audits : **un calcul
ne produit jamais de livrable que l'ingénieur peut ouvrir et vérifier**.

- Pas de MED de résultats.
- Pas de MED qui montre les charges réellement appliquées.
- Pas de script ParaView.
- Pas de tableau récapitulatif.

Au lot 47, il a fallu des scripts jetables pour répondre aux questions du
superviseur, et ils sont restés dans un dossier temporaire. Ce lot fait de ces
sorties des **livrables natifs du tronc commun**, produits automatiquement pour
tout projet et traçables comme le reste du paquet.

## Étape 0 — Ressources (fin du lot 47 quater)

1. **Fils d'exécution.** La courbe du lot 47 quater n'est pas monotone : avec
   4 fils, le temps relatif est de 1,03 ; avec 8, de 0,85 ; avec 12, de 0,41.
   Une seule mesure par point ne permet pas d'en tirer une règle.
   - Mesure de nouveau, **3 répétitions par point**, avec 1, 4, 8, 12 et 14
     fils, sur deux tailles : le maillage de 0,25 m et celui de production de
     l'estacade, dont la factorisation représente 52 % du temps.
   - Relève aussi la part du temps passée dans la factorisation à chaque
     point, pour comprendre où le gain se produit.
2. **Règle par défaut**, fondée sur ces mesures : nombre de fils = processeurs
   disponibles ÷ nombre d'exécutions lancées en même temps. Une exécution seule
   reçoit tous les fils utiles. Trois variantes en parallèle se partagent la
   machine.
   - Garde MPI désactivé par défaut (gain faible).
   - **Interdis `PARALLELISME_TEMPS`** tant que DIAG-027 (réactions fausses de
     1 à 2 %) n'est pas résolu : refus lisible avec le diagnostic.
3. Crée `config/machine.local.yaml` (non versionné), d'après la VM : 14
   processeurs, 21 Go.
4. Petites clôtures du lot 47 :
   - `docs/etat.yaml` cite aussi le commit 3dc21f1 ;
   - **PRE-039 est versé dans `precedents/` comme précédent décidé par MM**
     pour les projets futurs : DST pour une dalle dont les nœuds sont partagés
     par des poutres. La référence de l'estacade reste en DKT (E13), sans
     recalcul ;
   - l'étendue du bouchon d'E14 n'est pas testée : le lot 47 est clos.

## Étape 0 bis — Reprises du lot 48 bis (dans la VM)

Le lot 48 bis (`docs/essais_lot48bis.md`, « Limites ») a laissé à la VM ce que
le Cloud ne pouvait pas faire :

1. **Redémarrage de la session avant tout** : les outils `analyze_comm` et
   `validate_comm` ont changé (mode résumé, verdict `valide`, `partiel` ou
   `invalide`).
2. **Paquets de la dalle et du quai réexportés avec le harnais D**, dans un
   dépôt complet (non tronqué), à partir des `.mess` archivés. Aucune
   exécution nouvelle. L'antériorité des critères est celle que donne
   l'historique complet. Si elle diffère du paquet actuel, rapporte l'écart et
   ne le corrige pas.
3. **Quai** :
   - `planned_commands` est rempli par `fiche prevoir --ecrire`, et
     l'exemption de `projet.yaml` est levée ;
   - `projet quai_cw_test_01 maillage`, `generer` et `valider` sont rejoués de
     bout en bout ;
   - le `.comm` régénéré est **identique** au `.comm` de référence, hors
     commentaires. Sinon, rapporte l'écart sans corriger.
4. **`data/config/obligations_execution.yaml`** : classe les mots-clés de
   lecture de tables que `fiche obligatoires` laisse « mm:non classé » sur la
   dalle et l'estacade (`DEFI_CONSTANTE/VALE`, `POST_RELEVE_T/ACTION.*`,
   `CREA_CHAMP/TYPE_CHAM`, `AFFE.NOM_CMP`, `CREA_RESU/AFFE.NOM_CHAM`), avec
   leur source. Objectif : `fiche obligatoires` en code 0 sur les deux
   projets, sans masquer un vrai manque.
5. **Maillages et recalage sur la grille** : ne modifie **aucun** maillage
   dans ce lot. Un maillage recalé changerait l'empreinte, et la règle de
   conservation des niveaux imposerait un rejeu. La règle de recalage
   s'appliquera à la prochaine régénération d'un maillage.

## Étape 1 — Contrat de livrables dans `projet.yaml`

Ajoute une section générique `livrables` (nom libre, à justifier), validée par
le schéma. Elle déclare :

- les **champs de résultats** à écrire dans le MED, par famille d'éléments :
  - déplacements ;
  - efforts généralisés aux nœuds pour les coques et les poutres ;
  - contraintes pour les volumes ;
  - réactions ;
  - efforts dans les ressorts ;
- les **cas** à écrire :
  - tous les cas élémentaires ;
  - les combinaisons déclarées ;
  - les **enveloppes** (max et min par composante), avec la combinaison et la
    position de charge mobile qui gouvernent ;
- les **groupes** sur lesquels restreindre l'écriture, pour maîtriser la
  taille ;
- les livrables non pertinents pour le projet, chacun **avec un motif écrit**.

Le contrat est obligatoire pour tout nouveau projet. Il est rempli pour les
trois projets existants.

## Étape 2 — MED de résultats

1. **Exécution de post-traitement séparée de préférence.** Elle relit le
   résultat de l'exécution de production archivée (sa base, ou son MED), et le
   `.comm` de référence n'est pas modifié. Ce `.comm` est comparé à l'octet par
   la règle de conservation des niveaux et par le paquet : y ajouter des
   sorties obligerait à rejouer C, D et E, et coûterait les 30 à 50 minutes
   d'un calcul complet de l'estacade. Établis dans la documentation 17.4 la
   méthode de relecture (poursuite de la base, ou relecture d'un MED de
   résultats), et vérifie qu'elle reproduit les valeurs du calcul. Le `.comm`
   de post-traitement doit obtenir le verdict B `valide`. Si cette voie est
   impossible pour un projet, ajoute les sorties au `.comm` de production et
   rejoue les niveaux.
   **Les noms de champs sont explicites et stables** : cas, grandeur, unité
   dans les métadonnées. Vérifie dans la documentation et le catalogue 17.4 les
   mots-clés d'`IMPR_RESU` qui permettent de nommer les champs MED, et leurs
   limites de longueur. N'en énonce aucun de mémoire.
2. **Taille.** Mesure-la pour chaque projet. Pour l'estacade, il n'y a pas 247
   cas dans le MED : on y met les cas élémentaires, les combinaisons et les
   enveloppes. Le MED n'est jamais versionné.
3. **Provenance.** Dans le paquet, ajoute une section `visualisation` qui donne,
   pour chaque fichier :
   - le chemin et l'empreinte SHA-256 ;
   - l'exécution source, le `.comm`, le maillage, la version de Code_Aster ;
   - la liste des cas et des champs ;
   - l'unité de chaque champ.

## Étape 3 — MED des charges appliquées : vérification visuelle et numérique

C'est la vérification que MM fait à la main depuis toujours. Elle devient
automatique.

1. Pour chaque cas élémentaire, le **vecteur des forces nodales équivalentes à
   la charge déclarée** est écrit dans un MED dédié, en un champ par cas, avec
   ses trois composantes de force (et les moments si la modélisation en a).
   Établis la méthode dans la documentation (assemblage du second membre d'un
   chargement, ou autre), et cite-la. Les charges thermiques et imposées
   (déplacements, températures) sont représentées par leur champ propre, avec
   un motif.
2. **Contrôle numérique associé.** La somme des forces nodales de chaque cas
   doit égaler la résultante déclarée (CTL-013), et le MED doit le permettre :
   c'est la même source de vérité. Une charge mal placée doit **se voir** sur le
   MED et **échouer** au contrôle.
3. **Essai de mutation.** Décale volontairement une charge d'un groupe de
   mailles dans un cas d'essai. Le contrôle doit échouer, et le MED montrer le
   décalage.

## Étape 4 — Scripts ParaView générés

1. **Script des charges.** Il part de celui que MM utilisait sur un projet
   précédent, joint à la consigne en annexe A. Il est **généré depuis le
   manifeste** du MED (liste des cas et des champs), sans liste écrite à la
   main. Pour chaque cas :
   - un `Calculator` qui forme le vecteur ;
   - un `Glyph` en flèches, coloré selon la norme, avec une légende ;
   - un facteur d'échelle **calculé** à partir de la taille du modèle et du
     maximum du cas, et non une constante ;
   - seul le premier cas est visible à l'ouverture.
2. **Script des résultats** :
   - déformée amplifiée (`WarpByVector`) avec un facteur calculé ;
   - cartes des efforts (coques, et poutres en tubes colorés) ;
   - réactions et efforts des ressorts en glyphes ;
   - un groupe par cas ou combinaison, masqué par défaut ;
   - légendes nommées avec leur unité.
3. **Exécution sans interface.** Les deux scripts tournent aussi en mode
   `pvpython` sans écran et produisent des PNG standard : une vue des charges
   par cas, la déformée et les efforts principaux. Le rendu hors écran était
   un problème ouvert de ParaVis : établis ce qui fonctionne dans la VM (Salomé
   ou ParaView, rendu hors écran natif ou `xvfb-run`) et documente-le.
4. **Ouverture sous Windows.** MM veut ouvrir les résultats sur son PC.
   Vérifie si un ParaView standard y lit le MED. Sinon, ajoute une conversion
   vers un format standard (`.vtu` ou `.pvd`) **en plus** du MED, avec un
   contrôle que les valeurs sont identiques.

## Étape 5 — Classeur Excel récapitulatif

Généré depuis le paquet, sans recalcul. Mise en forme demandée par MM : **police
Arial 10, texte noir, en-têtes de tableaux sur fond gris, jamais bleu**.

Les valeurs affichées sont arrondies selon la table du lot 48 bis
(`config/arrondis.yaml`, `aster_expert.arrondis`). La valeur exacte reste dans la
cellule, seul l'affichage est arrondi (format de cellule). Les CSV de livrables
suivent la même table. Les CSV qui alimentent un calcul (combinaisons,
ferraillage) restent en pleine précision. Les notes Word adoptent la table, par
`NoteColumn.unit`, à leur régénération.
Feuilles minimales :

1. **Synthèse** : pour chaque famille d'éléments et chaque grandeur, le maximum
   et le minimum, avec leur lieu (groupe, nœud ou maille, coordonnées), la
   combinaison et la position de charge mobile qui gouvernent.
2. **Réactions et équilibre** : par cas, la charge appliquée, les réactions et
   l'écart.
3. **Efforts par élément** : têtes de pieux, poutres, appuis, selon le projet.
4. **Enveloppes** le long des éléments linéiques (pieux, poutres).
5. **Contrôles de niveau D et E** : critère, valeur, verdict, date du commit
   du critère.
6. **Comparaison externe**, si le projet en a une (estacade : C1 à C13, v1 et
   v2, attribution des écarts).
7. **Conventions** : repères, signes, unités, pour chaque famille.
8. **Provenance** : empreintes et exécutions.

Ajoute un test qui relit le classeur : valeurs identiques à la source, police,
fond gris des en-têtes.

## Étape 6 — Interroger les résultats sans script jetable

Commande `aster-expert resultats lire <projet>`, avec des filtres :

- groupe ;
- champ et composante ;
- cas ou combinaison ;
- extremum ou valeur en un point ;
- disque d'exclusion autour des singularités (règle PAT-013).

Elle rend un CSV et une ligne de provenance. Elle sert aussi d'**outil MCP**
(`query_results`), pour que l'agent réponde à une question sur les résultats en
lisant les données, et non de mémoire.

Rejeu de validation : les huit fichiers de l'export du lot 47 doivent être
reproduits par cette commande, à l'identique aux arrondis près.

## Étape 7 — Application aux trois projets

Pour le quai, la dalle et l'estacade :

- MED des résultats et des charges ;
- scripts ParaView et PNG ;
- classeur ;
- paquet mis à jour.

Des exécutions nouvelles sont nécessaires pour écrire les MED. Elles se lancent
**en parallèle** selon la règle de l'étape 0. Les **niveaux C, D et E doivent
être conservés** selon la règle du lot 45 : `.comm` identique hors sorties, ou
rejeu des critères. Dépose dans `/media/sf_partage/echanges/lot49/`, pour
chaque projet :

- le classeur ;
- les deux scripts ;
- les PNG ;
- les MED, ou leur conversion, sauf si leur taille dépasse 2 Go. Dans ce cas,
  indique où ils sont dans la VM.

## Compte rendu attendu — EN FRANÇAIS

1. Ressources : courbe répétée, règle retenue, `PARALLELISME_TEMPS` bloqué.
2. Contrat de livrables : schéma et exemples.
3. MED de résultats et MED des charges : méthode et références documentaires,
   tailles, provenance, essai de mutation.
4. ParaView : scripts, rendu hors écran, ouverture sous Windows.
5. Classeur : feuilles, test de relecture.
6. `resultats lire` et `query_results` : rejeu de l'export du lot 47.
7. Trois projets : livrables produits, niveaux conservés.
8. `rex`, contrôles, interventions. Redémarrage nécessaire si un outil MCP est
   ajouté.

## Interdits

- Aucun MED dans Git.
- Aucun mot-clé `IMPR_RESU` ou de post-traitement énoncé de mémoire.
- Aucune perte de niveau de validation sans le déclarer.
- Aucune liste de cas écrite à la main dans un script ParaView.
- Aucun terme interdit dans le dépôt.

## Annexe A — Script ParaView de MM (projet antérieur, modèle de départ)

Le texte du script `paraview_glyphs_charges.py` est fourni par MM dans le chat.
Il n'est pas recopié ici (projet antérieur de MM : noms de cas et de groupes
propres à cet ouvrage). Principe retenu, relevé dans le texte fourni :

1. Calculator de vecteur `FN_<cas>_DX/DY/DZ` (`AttributeType = 'Point Data'`,
   `Function = "<DX>*iHat + <DY>*jHat + <DZ>*kHat"`), renommé `Calc_<cas>`.
2. Glyph en flèches (`GlyphType='Arrow'`, orientation et échelle par le vecteur,
   `VectorScaleMode = 'Scale by Magnitude'`, `GlyphMode = 'All Points'`),
   renommé `Glyph_<cas>`, coloré par la norme, palette « Cool to Warm »
   (`ApplyPreset`), option de borne basse à 0.
3. Légende par cas (`GetScalarBar`, titre `|F| <cas> (N)`).
4. Seul le premier cas est visible à l'ouverture, avec sa légende.

Remplace la liste `CASES` codée en dur et le facteur d'échelle constant
(`DEFAULT_SCALE_FACTOR = 5e-4` dans le script fourni) par des valeurs lues dans
le manifeste.
