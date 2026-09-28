# QUAI-CW-TEST-01 — arbitrage v6 : décision 4 complétée, combinaisons, durabilité

Rédigé par Claude à partir des indications de MM du 25 septembre 2026.
**Lancer le lot 38 vaut validation de ce document par MM**, à l'exception du
seul point marqué **[QUESTION MM]**, qui doit être tranché dans le fichier avant
le lancement.

Conventions : `decided_by` `"MM"` ; `decided_at` = heure d'enregistrement ;
source `decision_ingenieur`, avec la référence `"MM, cas de test QUAI-CW-TEST-01,
arbitrage v6 en séance de travail"`, datée du jour d'enregistrement.

---

## D14 bis — révision de la décision 4 (point 3), texte complet

La rédaction D14 du lot 37 a omis le maillage coïncident et la liaison de corps
solide. C'est une erreur de rédaction de Claude. Le texte ci-dessous remplace D14
dans son intégralité.

**option_retained**
Maillage coïncident, généré par la chaîne. La poutre de couronnement est
représentée par un élément de poutre de Timoshenko sur son axe (Y = +0,34,
Z = +3,30), avec une section rectangulaire de 2,50 m × 1,40 m. Elle est reliée à
chaque tube par une liaison de corps solide entre l'anneau de tête du tube
(+2,60) et le nœud de poutre au droit du tube. Dans chaque ensemble lié, un
degré de liberté bloqué par une condition aux limites ne l'est que sur un seul
nœud (lot 32).

**justification**
Les maillages de l'écran et de la poutre sont produits par la même chaîne, donc
coïncidents par construction. La liaison de corps solide représente
l'encastrement des tubes dans la poutre. L'élément de poutre fournit
directement N, V, M et T, nécessaires au ferraillage selon l'EN 1992. La
formulation de Timoshenko est retenue parce que, en flexion horizontale, la
hauteur de la poutre (2,50 m) est du même ordre que la portée entre tubes
(2,60 m) : la déformation d'effort tranchant n'y est pas négligeable.

**validity_domain**
- La liaison de corps solide est plus raide que l'encastrement réel sur 0,80 m :
  moments en tête de tube surestimés, déplacements de la poutre sous-estimés.
- La poutre sur son axe ne représente pas les effets locaux (zone
  d'encastrement des tubes, ancrage du bollard, diffusion sous platine), qui
  relèvent de vérifications locales séparées.

**discarded_variants**
1. *description* : Raccord par méthode variationnelle entre maillages non
   coïncidents.
   *reason* : Sans objet, les maillages étant coïncidents par construction ; le
   raccord coque-poutre documenté ne s'applique pas à une jonction en T (lot 31).
2. *description* : Poutre en coques ou en éléments volumiques.
   *reason* : Les efforts de ferraillage devraient être reconstitués par
   intégration de contraintes, et la liaison avec les tubes redeviendrait un
   raccord cinématique.
3. *description* : Élément de poutre d'Euler-Bernoulli.
   *reason* : Néglige la déformation d'effort tranchant d'une poutre courte.

---

## D17 — point neuf `"13"` : combinaisons d'actions

`topic` : `"Combinaisons d'actions ELU et ELS"`

**option_retained**
Combinaisons de l'EN 1990, avec les coefficients usuels.

*Classement des actions.*
- **Permanentes :**
  - G, poids propre et poussée des terres ;
  - EAU_P, pression d'eau différentielle permanente, traitée comme une action
    permanente avec G et affectée du même coefficient.
- **Variables :**
  - Q1, surcharge de terre-plein : ψ0 = 0,7, ψ1 = 0,5, ψ2 = 0,3 ;
  - Q3, amarrage : ψ0 = 0,7, ψ1 = 0,5, ψ2 = 0.
- **Accidentelle :** A, accostage, qui ne se cumule qu'avec EAU_A (nappe
  accidentelle) à la place d'EAU_P.

*Coefficients partiels.* γG = 1,35 (défavorable) ou 1,00 (favorable), appliqué à
G + EAU_P considérés comme un bloc ; γQ = 1,50.

*Combinaisons*, avec Q1 et Q3 tour à tour en action dominante, et chaque action
variable présente ou absente :
- **ELU fondamentale :** γG (G + EAU_P) + 1,5 Q_dom + 1,5 ψ0 Q_acc ;
- **ELU accidentelle :** (G + EAU_A) + A + 0,5 Q1, sans Q3 : amarrage et
  accostage ne sont pas simultanés. 
- **ELS caractéristique :** (G + EAU_P) + Q_dom + ψ0 Q_acc ;
- **ELS fréquente :** (G + EAU_P) + ψ1 Q_dom + ψ2 Q_acc ;
- **ELS quasi permanente :** (G + EAU_P) + ψ2 Q1 + ψ2 Q3.

Le résultat est une enveloppe par famille de combinaisons, où chaque extremum
d'effort est accompagné des efforts concomitants.

**justification**
Ce sont les combinaisons usuelles de l'EN 1990 pour un ouvrage portuaire, avec
les coefficients habituels, sans spécificité propre à ce cas de test.
L'amarrage et l'accostage sont traités comme non simultanés, parce qu'un navire
n'est pas amarré au poste qu'il est en train d'accoster. La pression d'eau
permanente, liée au niveau de nappe, suit les actions permanentes.

**validity_domain**
- Les coefficients ψ de Q1 et Q3 sont des valeurs usuelles non justifiées par un
  référentiel portuaire propre au projet.
- Conformément à la décision 7 (D15), le modèle n'est représentatif que pour les
  effets des charges localisées. Les efforts des tubes et des palplanches sous
  G, EAU et Q1 relèvent du calcul géotechnique amont : leurs combinaisons issues
  de ce modèle ne sont pas des efforts de dimensionnement des tubes. Pour la
  poutre de couronnement, les charges de terre et d'eau uniformes ne produisent
  pas de flexion dans son plan (lot 37), et ses efforts sont dominés par Q3 et A.

---

## D18 — point neuf `"14"` : durabilité et maîtrise de la fissuration (poutre de couronnement)

`topic` : `"Durabilité, enrobage et maîtrise de la fissuration du béton armé"`

**option_retained**
- Béton C35/45, acier B500B (cas de test, §3).
- Classe d'exposition XS3 ; durée d'utilisation de projet de 100 ans.
- Enrobage nominal de 65 mm.
- Maîtrise de la fissuration sous combinaison quasi permanente, avec une
  ouverture de fissure limite wk = 0,2 mm.

**justification**
La poutre de couronnement d'un quai est en zone de marnage et d'éclaboussures,
d'où la classe XS3. La durée de 100 ans est celle d'un ouvrage portuaire.
L'enrobage et l'ouverture de fissure limite sont les valeurs usuelles de MM pour
ce type d'ouvrage.

**validity_domain**
Ces valeurs s'appliquent à la seule poutre de couronnement, seul élément en
béton armé du modèle. Les tubes et les palplanches en acier relèvent de
l'EN 1993-5, hors de cette décision.
