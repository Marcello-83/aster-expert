# Lot 33 — Critères d'équilibre et de symétrie (écrits avant l'exécution du modèle complet)

Ce document fixe, **avant** toute lecture des résultats du modèle complet
(étape 5), les critères de réussite des étapes 3 et 4. Une fois l'exécution
faite, ce document n'est complété que par les valeurs obtenues et le
verdict par cas -- le texte des critères eux-mêmes n'est jamais modifié
après coup (règle du projet, `docs/modele_rapport_essai.md`).

## Critère d'équilibre (étape 3, point 5)

Pour chaque cas de charge élémentaire (G, EAU_P, EAU_A, Q1) et pour la
direction Y (la seule où l'écran/la poutre appliquent un effort horizontal
significatif -- X et Z sont vérifiés séparément, informatifs) :

```
gap = (réactions_Y + ressorts_sur_la_structure_Y) + (résultante_écran_Y + résultante_poutre_Y)
écart_relatif = gap / résultante_appliquée_Y
```

- résultante_écran_Y : intégrale de Gauss (2x2 par maille QUAD4,
  `aster_expert.meshing.equilibrium.group_pressure_resultant`) de p(z) sur
  les mailles réelles de `ECRAN_POUSSEE`, lue du MED du maillage vérifié --
  indépendante de Code_Aster.
- résultante_poutre_Y : somme des `FY` des occurrences `FORCE_NODALE` de la
  décision 13, lue du `.comm` généré (déjà un fait écrit, jamais recalculée
  ici).
- réactions_Y : `REAC_NODA`/`RESULTANTE` restreint aux quatre groupes sans
  élément `ELAS_COQUE` (`ANCRAGES`, `PIED_TUBES`, `SYM_G`, `SYM_D` -- lot 23).
- ressorts_sur_la_structure_Y : `-Σ k_i * DY_i` (le signe : `k_i * DY_i` a
  la même convention que la force externe appliquée au nœud, vérifié sur un
  cas isolé à réponse analytique connue, `data/examples/lot33_equilibre/
  ressort_seul.comm` -- la force que le ressort exerce SUR la structure est
  l'opposée), sommé sur tous les nœuds de ressort, chaque nœud pondéré par
  la somme des raideurs de toutes les classes auxquelles il appartient (un
  nœud de bordure de bande ARGI/MARNE porte deux ressorts en parallèle,
  `aster_expert.generation.springs.build_spring_classes`).

**Seuil : `|écart_relatif| <= 1e-6`.** Tout cas où ce seuil n'est pas tenu
est un ÉCHEC de ce critère pour ce cas, rapporté tel quel -- jamais
requalifié en suivi (CLAUDE.md, lot 33 étape 1).

Les cas Q3 et A ne sont pas soumis à ce critère (efforts ponctuels
directement appliqués, FORCE_NODALE/FORCE_COQUE, sans profil à intégrer
indépendamment) ; leurs réactions et efforts de ressort restent des
grandeurs informatives (niveau D), comme au lot 32.

## Critère de symétrie (étape 4, point 2)

Pour chaque cas de charge (G, EAU_P, EAU_A, Q1, Q3, A) et pour **chaque
paire** de nœuds symétriques par rapport au plan X = 0 (tout le maillage,
`GROUP_NO=(GEN_TOUS_NOEUDS,)`, apparié par coordonnées à la tolérance du
maillage, `1e-6` normalisée) :

```
écart = max(|DY_a - DY_b|, |DZ_a - DZ_b|, |DX_a + DX_b|)
écart_relatif = écart / max(|DX|, |DY|, |DZ|) sur tout le cas
```

**Seuil : `écart_relatif <= 1e-6`,** pris sur la paire la plus défavorable
du cas. Le maillage lui-même doit satisfaire l'invariant de symétrie de
connectivité exacte (`aster_expert.meshing.invariants.SymmetryInvariant`,
`check_connectivity=True`) avant l'exécution -- déjà vérifié (`mesh check`,
233/233 invariants, quai réduit et modèle complet, tolérance 1e-9).

## Méthode vérifiée avant l'exécution du modèle complet

- Écran (intégration de Gauss) : reproduit exactement les valeurs de
  référence de l'énoncé (119,2/358,2/0,0/16,6 kN pour la poutre, à la
  facettisation près pour l'écran) -- `tests/unit/test_meshing_equilibrium
  .py`, `tests/unit/test_generation_profiles.py`.
- Ressort isolé (`k * DY`, signe) : vérifié exactement sur un cas
  analytique (`data/examples/lot33_equilibre/ressort_seul.comm`, exécution
  réelle, DY = 2,00 m, VY = k*DY = 1000 N = FY appliqué).
- Symétrie de connectivité et de déplacement : vérifiée sur le quai réduit
  (exécution réelle, `data/processed/runs/20260924T130758-094ef769/`) --
  écart relatif maximal sur les six cas : 7,1e-11 (A), 2,4e-11 (EAU_A),
  1,6e-12 (EAU_P), 3,9e-13 (G), 1,0e-12 (Q1), 6,7e-11 (Q3) -- **critère
  tenu, très en dessous du seuil, sur les 10 204 nœuds du quai réduit.**
- Équilibre (écran + poutre contre réactions + ressorts) : sur le quai
  réduit, l'écart relatif observé est de 0,6 % (G) à 1,9 % (Q1) --
  **très supérieur au seuil de 1e-6, donc un ÉCHEC de ce critère sur le
  quai réduit.** La cause exacte de cet écart n'a pas été établie avant la
  clôture de ce lot (voir « Limites » du compte rendu) : le critère est
  donc attendu en échec sur le modèle complet également, et sera rapporté
  comme tel, sans requalification.

## Résultats obtenus sur le modèle complet (étape 5, exécution unique)

Exécution : `data/processed/runs/20260924T131247-32c8ce39/` (non versionné),
`.mess` à `proc.0/fort.6`. `DIAGNOSTIC JOB : OK`, 0 ligne `<F>`/`<E>`/`<A>`/`<S>`
sur l'ensemble du journal, ~431 s. Analyse (script pur Python, aucune
ré-exécution) : `data/examples/lot28_quai/rapports/equilibre_analyse_lot33.json`.

| Cas | Écart relatif équilibre (Y) | Verdict (seuil 1e-6) |
|---|---:|---|
| G | -0,3816 % | **ÉCHEC** |
| Q1 | -2,3846 % | **ÉCHEC** |
| EAU_P | -0,2211 % | **ÉCHEC** |
| EAU_A | -0,2340 % | **ÉCHEC** |

Le critère d'équilibre échoue sur les quatre cas soumis à ce contrôle, dans le
même ordre de grandeur que sur le quai réduit (0,2 % à 2,4 % contre 0,6 % à
1,9 %) -- confirmation de l'échec anticipé, cause toujours non établie,
**rapporté tel quel, sans requalification.**

| Cas | Écart relatif symétrie (pire paire, 20 057 paires) | Verdict (seuil 1e-6) |
|---|---:|---|
| G | 2,60e-8 | RÉUSSI |
| Q1 | 6,07e-7 | RÉUSSI |
| EAU_P | 5,42e-9 | RÉUSSI |
| EAU_A | 2,34e-9 | RÉUSSI |
| Q3 | 2,12e-9 | RÉUSSI |
| A | 1,36e-7 | RÉUSSI |

Le critère de symétrie des déplacements est tenu sur les six cas, sur
l'ensemble des 40 114 nœuds du modèle complet (20 057 paires par cas) --
marge la plus faible sur Q1 (6,07e-7, à un facteur 1,6 du seuil), les cinq
autres cas restant à plus d'un ordre de grandeur en dessous.

Pesanteur (cas G, résultante verticale) : **non vérifiée**. `TAB_REAC_G` n'a
extrait que la composante DY (`reaction_components` par défaut de
`controls_block`, fixée avant l'exécution unique) ; la composante DZ,
nécessaire à ce contrôle, n'a pas été demandée. Poids attendu calculé
(tubes + palplanches + tirants, `expected_masses`) : -1 386 344,2 N. Limite
connue, non anticipée avant l'exécution unique, non contournable sans une
seconde exécution -- interdite par ce lot.
