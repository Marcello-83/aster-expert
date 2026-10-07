# Lot 47 quater — Estacade : clôture (fidélité au modèle source, performances de calcul)

Consigne de MM, copiée telle quelle au lancement du lot (profil `vm`, branche
`lot-47quater` créée depuis `main` après fusion de `lot-47ter`).

---

**Tout en français. Profil `vm`. Branche `lot-47quater`, depuis `main` après
fusion de `lot-47ter`.** Termes interdits : ceux du lot 47. Consigne copiée dans
`docs/lots/lot47quater_consigne.md`.

C'est le **dernier lot de l'estacade**. Il reste trois choses à faire :

1. utiliser enfin les capacités de la VM ;
2. tester les deux écarts de transcription que le superviseur a trouvés en
   relisant la source ;
3. clore le lot 47 par un bilan d'apprentissage.

## Étape 0 — Performances de calcul (mesurer avant de changer)

La VM aura 372 Go de disque et, au choix de MM, jusqu'à 14 processeurs et
22 à 24 Go de mémoire. L'exécution N1 a pourtant duré 3 127 s, et `aster-expert
run` impose un délai de 1 800 s (DIAG-025).

1. **État des lieux.** Relève :
   - `nproc` et `free -g` dans la VM ;
   - les limites que `aster-expert run` passe à `docker run` (CPU, mémoire) ;
   - les paramètres de l'`.export` réellement transmis (`ncpus`, `mpi_nbcpu`,
     mémoire, temps) ;
   - la version de l'image : séquentielle, ou parallèle avec MPI. **Vérifie-le,
     ne le suppose pas** : binaire, bibliothèques, cas test parallèle de la
     version.
2. **Profil d'une exécution de production.** À partir du `.mess` de N1 ou de la
   production du lot 47, répartis le temps entre :
   - la lecture du maillage ;
   - l'assemblage et la factorisation (`MACRO_ELAS_MULT`) ;
   - `CALC_CHAMP` ;
   - `IMPR_RESU` ;
   - le reste.

   On saura ainsi ce qu'il faut accélérer.
3. **Documentation du parallélisme dans la version 17.4.** Cherche dans le
   corpus, notamment les notices U2 et U1 sur le parallélisme et sur `.export`,
   et dans le catalogue :
   - le parallélisme par fils d'exécution (OpenMP, `ncpus`) ;
   - le parallélisme MPI (`mpi_nbcpu`) ;
   - les mots-clés du `.comm` qui en dépendent : `SOLVEUR` et `MUMPS`,
     distribution du modèle, maillage parallèle par `LIRE_MAILLAGE`.

   MM a noté « `mpi_nbcpu` dans l'`.export`, et des réglages dans `SOLVEUR` et
   `LIRE_MAILLAGE` » : confirme ou corrige à partir des documents, avec leurs
   références.
4. **Correctifs génériques** dans le tronc commun, avec tests :
   - les limites CPU et mémoire de `docker run` et le délai viennent de
     l'`.export`, ou d'une configuration de la machine, avec des valeurs par
     défaut calculées (`nproc`, mémoire libre). Il n'y a plus de 1 800 s
     codés en dur ;
   - `env-check` affiche les ressources disponibles ;
   - un test qui vérifie que l'`.export` est bien répercuté sur `docker run`.
5. **Mesure de l'accélération.** Sur un cas de taille moyenne (le maillage de
   dalle de 0,25 m), mesure le temps avec 1, 4, 8 puis 12 fils, et avec MPI si
   l'image le permet. Ajoute aussi deux exécutions indépendantes lancées en
   même temps. Fixe ensuite les valeurs par défaut sur ces mesures.
6. **Diagnostic ENV-003, disque plein.** Ajoute la prévention, puisque
   `env-check` signale déjà l'espace disque : un seuil d'alerte avant
   exécution. Ajoute aussi une politique de rétention documentée pour
   `data/processed/` : que garder, que régénérer.

## Étape 1 — Relecture de la source par le superviseur : deux écarts de transcription

Le superviseur a relu la source page par page. Deux informations du modèle
Robot ont été **perdues ou modifiées** entre la source et nos données. Les
deux peuvent expliquer C3 et C5, qui restent seuls « inexpliqués » (G),
insensibles à la plaque et au chevêtre.

**H1, bouchon en béton dans la section des pieux.**

- La légende de la figure 66 de la source distingue quatre familles de pieux :
  « Pieu (att. élevée-béton) », « Pieu (im-béton) », « Pieu (immergé) » et
  « Pieu (sol) ». Le modèle Robot donnait donc aux tronçons de tête une section
  **acier + béton du bouchon**.
- Notre décision E3, issue de la question Q3, l'a exclu.
- Le bouchon est un béton C35/45 de Ø 62,2 cm (§20.4.1 de la source), placé de
  la tête à −0,80 (E14).
- En béton non fissuré, EI du noyau ≈ 34 GPa × π × 0,622⁴ / 64 ≈ 250 MN·m², à
  comparer à environ 325 MN·m² pour le tube seul. La tête serait donc presque
  deux fois plus raide en flexion, et attirerait davantage de moment.

**H2, plan du tablier à +1,50 m et non +1,30 m.**

- La figure 66 porte le niveau « +1,50 » au tablier.
- Les ressorts de la file 1 commencent à +1,00 puis suivent des pas de 0,50 m
  (+0,50, 0,00…). C'est cohérent avec un pieu discrétisé tous les 0,50 m à
  partir de +1,50.
- B1 avait placé le plan moyen à +1,30. Dans la source, la tête de pieu est
  donc 0,20 m plus haute, ce qui allonge le bras de levier en tête des files de
  rive, très raides.

**Éléments contradictoires, à garder en tête.** Le §19.1 de la source décrit le
modèle Robot avec un chevêtre « 120 × 90ht ». L'hypothèse d'un chevêtre de
0,80 m (E19) ne repose donc que sur le poids sismique et sur le §20.5.1. Elle a
en outre dégradé C2. **Elle n'est pas établie.**

### Variantes, critères commités avant exécution

Toutes sur base DST (E13, variante (a)) :

| Run | Chevêtre | H1 bouchon mixte | H2 plan à +1,50 |
|---|---|---|---|
| Q1 | 0,90 | oui | non |
| Q2 | 0,90 | non | oui |
| Q3 | 0,90 | oui | oui |
| Q4 | 0,80 | oui | oui |

- Section mixte du bouchon : section homogénéisée en acier, n = Es / Ecm
  (Ecm = 34 GPa, béton non fissuré), pour A et I. Le poids du béton du bouchon
  est ajouté (25 kN/m³). Écris le calcul des caractéristiques dans le rapport.
- H2 : le tablier, les chevêtres et les têtes de pieux sont à +1,50. Les
  ressorts restent à leurs cotes (B3).
- **Critère de conclusion**, écrit avant l'exécution : H1, H2 ou leur
  combinaison expliquent C3 et C5 si C3 (ELS f, ELS c, ELU) et C5 sont tous
  dans les 5 %, **sans que C2, C4, C6, C7 et C8 (barre seule) en sortent**.
- Lis aussi C6, C7 et C8 (barre seule) sur les maillages de 0,25 et 0,50 m
  déjà calculés au lot 47 ter, sans nouveau calcul. La part de la barre dépend
  peut-être du maillage.

Lance les exécutions indépendantes **en parallèle** si l'étape 0 montre que la
mémoire le permet.

## Étape 2 — Clôture et bilan d'apprentissage du lot 47

1. **Tableau final d'attribution** (A à G), mis à jour par l'étape 1.
2. **Précédent PRE-039** (DKT ou DST pour une dalle couplée à des poutres qui
   partagent ses nœuds). Décision de MM, validée par le lancement du lot :
   - **DST** pour une dalle dont les nœuds sont partagés par des poutres
     POU_D_T (chevêtres, nervures) ;
   - **DKT** reste admis pour une dalle sans poutre couplée ;
   - domaine de validité : dalle mince à moyennement épaisse (h/L ≤ 1/10),
     poutres au plan moyen ;
   - justification : CA-058 et le plan factoriel du lot 47 ter.
3. **Leçons pour l'outil**, chacune avec la règle ou la connaissance créée :
   - transcription d'une source : relever **toutes** les légendes, les
     niveaux et les sections du modèle source, pas seulement le texte (H1 et
     H2 avaient été perdus) ;
   - points de comparaison : lieu, composante et famille déclarés ;
   - lecture hors singularité ;
   - partage de l'effort tranchant entre plaque et poutre.
4. **Métriques du projet** : lots (47, bis, ter, quater), exécutions de
   développement et de vérification, échecs, interventions de MM et du
   superviseur, erreurs évitées par la base. Compare-les au quai et à la dalle.
5. `rex`, paquet de résultats, notes, `docs/etat.yaml`. Le statut final de
   l'estacade est un **contre-calcul au niveau D**, chaque écart étant attribué.

## Compte rendu attendu — EN FRANÇAIS

1. Performances : ressources, profil, documentation du parallélisme avec ses
   références, correctifs, accélérations mesurées, valeurs par défaut
   retenues.
2. H1 et H2 : tableau Q1 à Q4, verdict selon le critère, et lecture de C6 à C8
   sur les maillages grossiers.
3. Attribution finale, PRE-039, leçons, métriques.
4. `rex`, contrôles, interventions.

## Interdits

- Aucun changement de la référence (E1 à E19). Q1 à Q4 sont des variantes
  déclarées.
- Aucun paramètre de parallélisme ou mot-clé Code_Aster énoncé de mémoire.
- Aucune suppression dans `data/processed/runs/`.
- Aucun terme interdit dans le dépôt.
