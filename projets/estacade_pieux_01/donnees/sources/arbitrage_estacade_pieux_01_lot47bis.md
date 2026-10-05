# Arbitrage de MM — projet `estacade_pieux_01` (lot 47 bis)

Décisions E17 à E19 de MM, recopiées à l'identique de la consigne du lot 47 bis
(`docs/lots/lot47bis_consigne.md`, section « 2. Décisions de MM, validées par le
lancement du lot »). Les décisions E1 à E16
(`arbitrage_estacade_pieux_01_lot47.md`) ne sont pas modifiées : E17 change la
lecture des résultats, E18 complète le cas TR de la seule combinaison 100, E19
déclare une variante de sensibilité ; la référence reste E1 à E16.

### E17 — Règles de lecture v2

> **E17, règles de lecture v2.** Elles sont écrites et commitées **avant** toute nouvelle exécution, et déclarées « écrites après la première exécution ». Les verdicts v1 sont conservés tels quels dans l'historique.
> 1. **Pieux.** C3 : maximum sur la zone qui va de la tête (+1,30) à −0,80, élément de tête compris. C5 : maximum sur tout le pieu. Enveloppe ELU+ et ELU− ; la famille qui gouverne est indiquée.
> 2. **Chevêtres** (C6, C7, C8) : on compare le **total** barre + bande de dalle |X − X_file| ≤ 0,60, c'est-à-dire s·MFY − ∫MYY dX et VZ + ∫QY dX. La barre seule est rapportée pour information.
> 3. **Dalle** (C9, C12, C13) : maximum hors des disques de rayon 0,60 m centrés sur les têtes de pieux.
> 4. **C11** : moyenne de NXX sur une section transversale. C'est la grandeur que publie la source.

### E18 — Cas TR de la combinaison 100

> **E18, cas TR de la combinaison 100.** Sources : le §15.3.3 de la source : « un essieu : αQ2·Q2k = 0,8 × 200 = 160 kN (essieu du système LM1, voie n° 2) », parmi les charges des trottoirs ; le §20.6.5 : « un essieu est appliqué sur le trottoir du tablier » ; la figure 100 : deux charges concentrées, en kN, **alignées selon X sur le même trottoir**, distantes d'environ 2 m, la première juste avant le chevêtre 4. Les figures 68 et 69 concernent le tandem TS de LM1 sur la voie et non ce cas.
> Le cas TR comprend : 5 kPa sur les deux trottoirs ; 2 roues de 80 kN, **alignées selon X**, à 2,00 m d'entraxe longitudinal, centrées sur le trottoir (Y = +2,25) ; une empreinte de 0,40 × 0,40 m, et non une charge ponctuelle : une force nodale sur une plaque est singulière. La source a utilisé des charges ponctuelles, et sa valeur de 568 kN/m dépend donc de son maillage. L'écart sur C12 « rive » s'interprète en conséquence ; un déplacement par pas de 0,50 m selon X, avec enveloppe ; la position gouvernante est rapportée et comparée à celle de la figure 100 ; la charge de 10 kN sur 0,10 × 0,10 m est négligée (effet local de poinçonnement).
> L'orientation longitudinale est **déduite de la figure 100**, pas écrite dans la source. C'est cohérent avec un trottoir de 1,50 m, trop étroit pour un essieu de 2,00 m posé en travers. Ce cas ne s'applique qu'à la combinaison 100. Dans LM1, la charge des trottoirs reste à 5 kPa (cas source « LM1 UDL TR »).

### E19 — Variante de sensibilité : chevêtre de 0,80 m

> **E19, variante de sensibilité déclarée** : chevêtre de 0,80 m (HZ = 0,80, le reste inchangé), pour tester (c). La référence reste à 0,90 m (E2).
