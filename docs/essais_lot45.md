# Lot 45, partie B (Cloud) — notes Word génériques, règle de conservation des niveaux

Profil : `cloud` (`aster-expert env-check`, 8 vérifications, 3 absences attendues :
`cave`, Salomé, dossier partagé). Branche `lot-45`, partie A (`0ece15e`) présente.

## 1. Ce que le lot change

- **Décisions de MM** : D20 et D21 au texte exact (PRE-019, PRE-020) ; D21 s'applique à
  la dalle (P6 révisée, PRE-030) ; Es = 200 GPa pour tous les projets, en attente
  d'application au quai (PRE-032, fiche du quai « en révision »).
- **Règle de conservation d'un niveau** (`aster_expert.projet.paquet`) : un niveau reste
  acquis pour un `.comm` identique hors commentaires et en-tête (`normalize_comm`),
  sinon il est rejoué avec les critères d'origine. Critères commités après l'exécution
  ou avec des résultats : signalés par le paquet. `projet exporter-resultats
  --reevaluer` ré-applique le tout à un paquet existant, sans archive.
- **`FERR_MIN`** : refus de toute demande hors `UNITE_CONTRAINTE='MPa'`
  (`aster_expert.ferraillage.unites`) ; signalement factuel dans
  `docs/signalements/ferr_min_unite_contrainte.md`.
- **Notes Word** : `aster-expert note hypotheses|resultats|controler <projet>`
  (`aster_expert.notes`), quatre livrables dans `projets/<projet>/livrables/notes/`.

## 2. Critères (écrits avant l'exécution) et exécution

La seule exécution du lot est le rejeu de E0, E1, E2 de la dalle, autorisé par MM
(exception à l'interdit d'exécution), avec les **critères du lot 43**
(`docs/essais_lot43.md`, commit `4093f12`), ni le texte ni les seuils réécrits :

- E0 : signes de la flèche et des moments ; E1 : erreur de `w`, `Mx`, `My` décroissante
  au raffinement ×2 ; E2 : erreur ≤ 1 % sur le maillage fin 48 × 32.
- Maillages **versionnés** (`references/cas/dalle_h*.mmed`), chacun passé à `mesh check`
  (48/48) avant usage ; `.comm` regénéré par le générateur du projet (EYS = 200 GPa).

Résultat : E0, E1, E2 **RÉUSSI** ; flèche et moments au centre **identiques à ceux du
lot 43** (bit à bit : EYS n'agit que sur le ferraillage) ; F4 reste en échec comme au
lot 43 (limite active, `ÉCHEC (limite active)`, rapporté tel quel, CA-052). Trois
exécutions `completed_ok`, 7,7 s, 7,0 s et 8,5 s, aucune alarme. Fichiers :
`projets/dalle_appuyee_01/references/rejeu_niveau_e_lot45.json`,
`references/rejeu_lot45/dalle_h*.comm`. Niveau atteint par le paquet de la dalle : **E**
(le `.comm` du maillage fin du rejeu ne diffère de l'exécution du paquet que par un
commentaire, `meme_comm_octets: false`, `meme_comm_que_l_execution: true`).

Le quai : le `.comm` régénéré ne diffère de l'exécuté que par l'empreinte de la fiche
en en-tête (un commentaire) : **niveau D conservé**. Ses trois documents de critères
(lots 34, 37, 39) sont signalés « commités avec les résultats, antériorité non
démontrable » par le paquet, automatiquement.

## 3. Contrôles des notes

`scripts/build_lot45_notes.py` (`controle_notes.json` à côté de chaque note) :

| Note | Pages | Tableaux | Figures | Contrôle |
| --- | --- | --- | --- | --- |
| quai, hypothèses | 39 | 26 | 0 | OK |
| quai, résultats | 39 | 32 | 25 | OK |
| dalle, hypothèses | 13 | 15 | 0 | OK |
| dalle, résultats | 8 | 25 | 0 | OK |

Le contrôle relit le `.docx` : chaque point de la fiche, chaque valeur de donnée
(identique à la source), chaque cellule des tableaux déclarés (relue dans le paquet),
chaque valeur mesurée (retrouvée dans les fichiers du paquet au chiffre affiché près),
les textes de décision mot pour mot, l'absence de `[À CONFIRMER`, `[QUESTION`, `TODO`,
et la mise en forme (police Arial, 10 pt, noir, fond gris `D9D9D9` des en-têtes, titres
numérotés, aucune couleur de thème). Il est éprouvé par altération du fichier
(`tests/unit/test_notes.py` : valeur, police, taille, couleur, fond bleu, fond de corps,
titre, gras, marqueurs, cellule de tableau) : chaque altération est détectée.

## 4. Limites et points à relire

- Le marqueur `[À CONFIRMER MM]` est cité par le texte d'une révision levée de la fiche du
  quai (point 1, lot 24). La note le montre entre guillemets (`« À CONFIRMER MM »`) : le
  texte de la fiche n'est pas modifié.
- Les nombres de pages sont ceux de LibreOffice (installé à la main dans le Cloud,
  `libreoffice-writer`) ; Word peut paginer autrement.
- Les 54 vues du quai ne sont pas toutes reprises : 25 figures (charges, déformées,
  efforts des tubes, butée, ferraillage), choisies dans `projet.yaml`. La dalle n'a
  aucune figure dans son paquet (aucun PNG produit par le projet).
- Les deux notes du quai reportent la fiche actuelle, qui diffère de celle de
  l'exportation du paquet (D20, D21, Es) : l'écart d'empreinte est montré.
- Es = 200 GPa n'est pas appliqué au quai ; le ferraillage du quai (lot 39) porte 210 GPa.
- La fiche de la dalle (P6) a été révisée pour corriger la mention de D21 (texte de MM) :
  la décision du lot 43 reste dans `decision_history`.
- `rex` : sans archives d'exécution (Cloud), aucune revue n'est inscrite ; les trois
  exécutions du rejeu sont hors du dépôt (`data/processed/runs/` n'est pas versionné).
