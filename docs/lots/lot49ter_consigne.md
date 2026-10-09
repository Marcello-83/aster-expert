# Lot 49 ter — consigne (recopiée de la demande de MM)

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-49ter` créée depuis `main` après fusion de `lot-49bis`).

# Lot 49 ter — Livrables de l'estacade : corriger ce qui fausserait un ferraillage

Tout en français. Profil `vm`. Branche `lot-49ter`, depuis `main` après fusion
de `lot-49bis`. Termes interdits : ceux du lot 47. Consigne copiée dans
`docs/lots/lot49ter_consigne.md`.

Les lots 49 et 49 bis ont produit le premier livrable exploitable. La relecture
du superviseur, qui a confronté la synthèse de l'estacade au §20 de la source, a
relevé :

- six défauts, dont deux peuvent conduire à un ferraillage faux ;
- deux arbitrages pris par MM sur les points du compte rendu 49 bis ;
- deux décisions de MM : la section de calcul du bouchon, et le moment de
  dimensionnement sur appui, max(M_nu ; 0,65 × M_encastrement).

Ce lot les traite tous. Le format des livrables doit être juste avant que le
lot 50 le fige dans un générateur.

## Périmètre

- Estacade : c'est le seul projet dont les livrables sont refaits.
- Quai (`quai_cw_test_01`) : projet d'essai sans réalité physique, déjà
  exploité. Il n'est plus travaillé.
  - La réserve sur sa poutre de couronnement (efforts nuls, LIAISON_SOLIDE)
    reste écrite telle quelle.
  - Ses livrables ne sont pas régénérés.
  - Les changements génériques ne doivent cependant casser aucun de ses tests.
- Dalle : seuls les changements génériques l'atteignent (convention,
  arrondis). Son niveau E se conserve par la règle habituelle.

## Étape 0 — Décisions à enregistrer

Enregistre-les par `aster-expert fiche enregistrer`, avant tout développement.

**E24, section de calcul du bouchon.**
Le dimensionnement en béton armé du bouchon se fait au nu inférieur du
chevêtre, à +0,60 : le chevêtre réel va de +0,60 à +1,50, et +0,60 est
aussi la cote du recépage (E21).
La valeur au nœud +1,30, situé à l'intérieur du chevêtre, est conservée
pour mémoire et pour la comparaison avec la source. La source a
dimensionné le bouchon avec M = 450 kN·m lu à ce nœud.

**E25, chevêtres.**
Le torseur de dimensionnement est le total de la section en T (règle
E17.2 du lot 47 bis : barre plus bande de dalle), pour M comme pour V, à
tous les états limites.
La barre seule passe dans les colonnes de traçabilité. Sa part dépend de la
formulation de plaque (DKT ou DST : C8, CA-058). C'est un artefact numérique,
pas une grandeur physique.

**E26, bande d'exclusion le long des lignes de nœuds partagés poutre–plaque.**
La bande vaut ±b/2 de part et d'autre de la ligne, b étant la largeur de la
poutre : ±0,60 m pour les chevêtres.
Elle est déclarée par famille de poutres dans `engineering_summary` et
s'applique à toutes les familles de coque, MYY compris. La lecture se fait
ainsi au nu, conformément à l'EN 1992-1-1 §5.3.2.2(3) pour un appui
monolithique. La clause est citée d'après MM et le superviseur (voir E27).
Les valeurs situées dans la bande restent visibles dans une colonne
« axe (comparaison) », jamais comme valeur de dimensionnement.
Elle s'ajoute aux disques d'exclusion de PAT-013 autour des têtes ; elle ne
les remplace pas.

**E27, moment de dimensionnement sur appui (règle de MM, EN 1992-1-1
§5.3.2.2(3) et sa note).**
M_dim = max(M_nu ; 0,65 × M_encastrement). La règle s'applique au chapeau de
la dalle, au chevêtre sur appui et, par extension décidée par MM, au bouchon
encastré dans le chevêtre.
La clause est citée d'après MM et le superviseur. Le corpus du dépôt ne
contient pas l'Eurocode : ne prétends pas l'avoir relue.

M_encastrement est le vrai moment d'encastrement parfait (décision de
MM). Ce n'est pas le moment élastique du modèle à l'axe. On l'obtient par
des modèles auxiliaires, dérivés du modèle de référence. Chacun est
calculé sous les mêmes cas, les mêmes combinaisons et les mêmes positions
mobiles que la référence.

- A1, chevêtres. Tablier (dalle et chevêtres) sans les pieux, avec
  les nœuds de tête encastrés : translations et rotations bloquées.
  M_encastrement du chevêtre est le moment de la section en T (E25) à
  l'axe de la file de pieux.
- A2, dalle. Tablier dont les lignes d'axe des chevêtres sont des
  encastrements parfaits : déplacement vertical et rotation autour de
  la ligne bloqués. Chaque travée de 5 m est ainsi bi-encastrée.
  M_encastrement du chapeau est le MXX à l'axe, hors des disques PAT-013,
  au maximum sur la ligne.
- A3, bouchon (extension de la règle décidée par MM). Modèle complet,
  tronçon +0,60 → +1,30 rendu indéformable comme en V1, et rotations des
  têtes bloquées, translations libres. M_encastrement est le moment à
  +0,60.

Actions des modèles auxiliaires. Charges verticales seulement : G,
G2, LM1 (TS et UDL), TR, essieu de trottoir, avec les coefficients de la
combinaison. Le freinage et la température en sont exclus : dans un
modèle bi-encastré, un gradient thermique produit un moment artificiel
sans rapport avec l'objet de la règle. Écris ce choix dans la synthèse ;
MM peut le renverser.

Le moyen de bloquer les degrés de liberté et de rendre un tronçon
indéformable se choisit dans la documentation 17.4, avec sa référence.
Aucun mot-clé de mémoire.

Contrôles des modèles auxiliaires.

- Harnais D : équilibre, réactions égales à la somme des charges
  verticales.
- Validation sur un cas analytique, l'un pour A1, l'autre pour A2.
  - A1 : charge linéique uniforme q appliquée seulement sur la ligne
    d'un chevêtre, consoles non chargées. La section en T doit
    retrouver q·L²/12 à l'axe des pieux (L = 4 m), à 2 % près.
  - A2 : charge surfacique uniforme q sur toute la dalle. On doit
    retrouver q·L²/12 à l'axe des chevêtres (L = 5 m), loin des bords
    libres, à 2 % près.
  - Écris les écarts, et explique-les s'ils dépassent 2 %.

Formation de M_dim. Pour chaque combinaison et chaque position mobile :
M_dim = max(M_nu de la référence ; 0,65 × M_encastrement de l'auxiliaire
correspondant). On prend ensuite l'enveloppe. Le torseur exporté porte
M_dim, avec N et V lus au nu, dans la référence, au même instant. Écris la
convention.

La méthode est déclarée par section dans `engineering_summary` (champ
obligatoire pour toute section « appui », « chapeau » ou « nu »). Le
classeur et les CSV donnent M_nu, M_encastrement, 0,65 × M_encastrement,
M_dim et le terme qui gouverne. Le moment élastique à l'axe (M_axe) est
donné pour comparaison seulement.

La génération des modèles auxiliaires est générique : une option du
tronc commun, déclarée dans `engineering_summary`, et non un script de
projet. Le lot 50 la reprendra.

**Constat sur E19.** Le §20.5.1 de la source écrit « h = 0.80 m (augmenté à
0.90m) ». Les efforts Robot ont donc très probablement été calculés avec
0,80 m. L'attribution de C6 passe de « hypothèse non établie » à « probable,
appuyée par le texte de la source ». Mets à jour l'attribution et le constat
correspondant. La référence E1 à E23 ne change pas.

## Étape 1 — Les six défauts

### D1 (grave) — Chevêtres exportés en barre seule

Constat. Sur appui et en effort tranchant, la barre seule sous-estime la
source d'un facteur 3 à 4 : V = 180 à 198 kN contre 654 kN, et M au nu =
37,5 kN·m contre 178 kN·m.

Correctif. Applique E25 : synthèse, feuille Torseurs, détail des
chevêtres et CSV `chevetre_travee.csv` et `chevetre_nu_appui.csv`.
Les torseurs concomitants (N, M, V au même lieu, même combinaison, même
position mobile) se calculent sur la section en T.
Écris la méthode d'intégration de la bande dans le rapport : largeur,
nœuds, champ, repère.

Preuve.

- Pour un cas élémentaire, la somme barre + bande à mi-portée est comparée à
  l'équilibre d'une coupe. Réutilise CTL-005 si possible.
- Comparaison à la source, avec le lieu déclaré : V ELU contre 654 kN (C8 au
  lot 47 bis : environ +7 % attendu), M sur appui contre 178 kN·m, M en
  travée contre 408 kN·m.

### D2 (grave) — Effort tranchant de la dalle absent de la synthèse

Correctif. Ajoute la grandeur « V max » aux familles de dalle (courante,
chapeau, rive). Il s'agit de la résultante des efforts tranchants de coque
par unité de largeur, avec N et M concomitants, hors bandes E26 et hors
disques PAT-013.
Les noms de composantes viennent du catalogue de la version 17.4, pas de la
mémoire.
Ajoute les CSV de flexion composée correspondants si la grandeur y a sa
place, sinon une colonne V.

Comparaison. La source donne V ELU = 321 kN/m, obtenu en bordure sous TR
(combinaison 100, essieu sur le trottoir, E18). Lis notre valeur en rive
sous la même combinaison.

### D3 — Zones de lecture qui se recouvrent

Constats.

- `dalle_travee_MXX.csv` contient des moments de chapeau : lignes 2 et 3 à
  X = 29,95, à 0,65 m de l'axe de la file 7.
- Les familles « chevêtre en travée » et « chevêtre au nu de l'appui » ont
  trois lignes identiques (N min, MFY max, |VZ| max à Y = 1,65).

Correctifs.

- Les zones d'une même famille sont disjointes, et leur définition
  géométrique est écrite dans `engineering_summary`.
- Une section « travée » ne retient que le signe de moment de la travée. Une
  section « chapeau » ou « appui » ne retient que celui de l'appui. Le signe
  opposé n'apparaît que s'il dimensionne, et il est alors déclaré.
- Ajoute un test générique : aucun nœud ni élément n'appartient à deux zones
  d'une même famille, et deux lignes identiques dans deux sections sont
  refusées sauf déclaration explicite.

### D4 — Convention de la feuille « Synthèse ingénieur »

Constat. La feuille est en convention Code_Aster : « N max » y désigne la
compression minimale. Elle contredit les CSV.

Correctif.

- La synthèse adopte la convention ingénieur des CSV : N > 0 en
  compression, et le signe de M déclaré par section.
- Les intitulés deviennent physiques : « compression max », « traction max »,
  « moment de travée max », « moment sur appui max ».
- La feuille Torseurs et les colonnes brutes gardent la convention
  Code_Aster, et l'en-tête de chaque feuille dit laquelle s'applique.

### D5 — Arrondis absents du classeur

Constat. Les cellules du classeur sont au format « Standard » : on lit
−166.3100644693008.

Correctif.

- Applique `config/arrondis.yaml` aux formats d'affichage de toutes les
  feuilles, la valeur stockée restant exacte.
- Ajoute un test qui relit le `number_format` des cellules de valeurs pour
  chaque unité.

### D6 — Section du bouchon au nu (E24)

Correctif. Ajoute la section « bouchon au nu du chevêtre (+0,60) ». Elle
remplace `tete_de_pieu.csv` comme export de dimensionnement, sous le nom
`bouchon_nu_chevetre.csv`. La tête à +1,30 passe dans la feuille Comparaison
externe, avec la valeur de la source.

Lecture à +0,60. Si aucun nœud n'existe à +0,60, interpole linéairement
entre les deux extrémités de l'élément (ELNO). Ce n'est exact pour M et V que
si l'élément ne porte aucune charge transversale répartie ni ressort
intermédiaire. Vérifie-le et écris-le. Sinon, signale-le, sans maillage
nouveau dans ce lot.

E27 au bouchon. M_dim = max(M_nu à +0,60 dans la référence ;
0,65 × M à +0,60 dans A3). Ordre de grandeur de M_nu à l'ELU : environ
260 kN·m. Le terme qui gouverne n'est pas connu d'avance.

Variante déclarée V1, une exécution. Dans notre modèle, entre +0,60 et
+1,30, le pieu est représenté par sa propre section. En réalité, c'est un
massif de chevêtre. Le moment au nu dépend donc de cette hypothèse.

- Lance une variante où ce tronçon est rendu indéformable. Choisis le
  moyen dans la documentation 17.4 (section très raide ou liaison
  cinématique) et cite la référence. Aucun mot-clé de mémoire.
- Critère, écrit et commité avant l'exécution : si M_dim du bouchon
  (E27) varie de plus de 5 % entre la référence et V1, la valeur de
  dimensionnement est l'enveloppe des deux, et l'écart est écrit dans la
  synthèse. Sinon, la référence suffit.
- Rapporte aussi l'effet de V1 sur la tête (comparaison C3), sur le chevêtre
  et sur le déplacement en tête.

## Étape 2 — Compléments de la comparaison à la source

Chapeau de dalle. La source donne 174 / 119 / 80 kN·m/m. Notre valeur au
nu est de 90,2 / 60,1 / 41,3 kN·m/m.

- Trace un profil de MXX perpendiculaire aux chevêtres, à Y = 0 et
  Y = ±1,00, donc hors des disques des têtes. Il va de l'axe jusqu'à
  1,00 m, sous la combinaison 111, à l'ELU, à l'ELS c et à l'ELS f, avec les
  valeurs à l'axe, à 0,30 m et au nu.
- Ce profil sert à la comparaison : compare la valeur de la source à
  M_axe, à M_nu et à M_dim. La conclusion attendue est l'une de deux :
  soit « écart dû au lieu de lecture », soit « écart non expliqué ».

Feuille Comparaison externe. Pour chaque point de comparaison, elle donne
le lieu, la composante, la famille et l'état limite, la valeur de la source,
la nôtre, l'écart et son attribution (A à G). La règle des points de
comparaison du lot 47 quater s'applique. Le tableau du superviseur sert de
point de départ, à vérifier ligne par ligne :

- pointes : N ;
- tête et bouchon : M, N, V ;
- chevêtre : travée, appui, V ;
- dalle : travée, chapeau, N, V.

N dans la dalle. La source compose son N à la main (65 + 0,7 × 19), sans
concomitance, et ses coefficients d'ELS fréquent ne sont pas cohérents avec
sa combinaison 111. Classe ce point « non comparable directement » et donne
l'ordre de grandeur. N'ouvre aucune enquête.

## Étape 3 — Intégrité des exports

Un des CSV déposés au lot 49 bis, `tete_de_pieu.csv`, a été réenregistré par
Excel : sa mise en forme diffère de celle des autres. Ajoute l'empreinte
SHA-256 de chaque fichier livré (CSV, classeur, images) au manifeste de
livraison.

Ajoute une commande de vérification, ou une option d'une commande existante,
qui signale tout fichier modifié après la livraison.

## Étape 4 — Connaissances

- Patron « barre partageant ses nœuds avec une plaque ». Les efforts de la
  barre seule ne sont pas une grandeur de dimensionnement. On dimensionne sur la
  section en T. Il est dérivé de CA-058 et de E25, et sa preuve est la
  comparaison de D1.
- Patron « lecture au nu ». Les bandes d'exclusion valent ±b/2 le long des
  lignes poutre–plaque et un disque autour des appuis ponctuels. Il est dérivé
  de PAT-013 et de E26.
- Contrôle de livrable. Il s'agit des tests génériques de D3, D4 et D5,
  déclarés comme contrôles de la chaîne de livraison.

## Contrôles

```bash
aster-expert env-check
aster-expert mcp-check
ruff format --check
ruff check
pytest
pytest -m lent_aster
mypy src
mypy
aster-expert connaissances verifier
aster-expert etat verifier
aster-expert projet estacade_pieux_01 verifier
```

## Compte rendu attendu — EN FRANÇAIS

- Décisions E24 à E27 et constat E19 : ce qui a été enregistré.
- Modèles auxiliaires A1 à A3 : description, contrôles, validation
  analytique.
- D1 à D6 : avant et après, chacun avec sa preuve. Pour D6, la variante V1
  avec son critère, son verdict et son effet sur la tête, le chevêtre et le
  déplacement en tête.
- Comparaison complète à la source, avec le profil du chapeau.
- Intégrité des exports et connaissances créées.
- Synthèse de l'estacade à présenter à MM : la nouvelle synthèse
  ingénieur, en particulier :
  - le bouchon : M_nu, 0,65 × M_encastrement et M_dim (E24, E27) ;
  - le chevêtre en section en T (E25), avec M_dim sur appui ;
  - le chapeau de la dalle, avec M_dim ;
  - pour chacune de ces trois sections, le terme qui gouverne M_dim.
- Contrôles, `rex`, interventions, et la consigne de redémarrage si un outil
  MCP a changé.

Dépôt dans `/media/sf_partage/echanges/lot49ter/estacade_pieux_01/` :

- le classeur ;
- les CSV de flexion composée ;
- les diagrammes ;
- le profil du chapeau ;
- le manifeste avec ses empreintes.

## Interdits

- Aucun changement de la référence E1 à E23. V1 est une variante déclarée ;
  A1 à A3 sont des modèles auxiliaires, et non des variantes de la référence.
- Aucun travail sur le quai au-delà du maintien de ses tests.
- Aucun nom de champ, de composante ou de mot-clé Code_Aster énoncé de mémoire.
- Aucune suppression dans `data/processed/runs/`.
- Aucun terme interdit dans le dépôt, un journal ou un message de commit.
