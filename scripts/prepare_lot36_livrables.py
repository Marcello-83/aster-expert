"""Lot 36, étape 3 : prépare les deux dossiers de livraison.

1. `résultats_MED_Paravis/` (dans le dépôt, sur la VM, jamais commité : les `.med` sont
   ignorés) : le maillage de l'ouvrage, le MED de résultats de la base, celui de la
   variante de diagnostic V1, leurs empreintes et le `LISEZMOI.md` d'ouverture dans
   ParaVis (Salomé-Méca 2024, installé dans la VM).
2. `/media/sf_partage/echanges/lot36/` (dossier partagé, ouvert depuis Windows) : les
   images, la synthèse, les contrôles, le rapport de butée et le `LISEZMOI.md` -- pas
   de MED (le dossier partagé est sur OneDrive ; le MED de résultats fait 143 Mo).

Usage : python scripts/prepare_lot36_livrables.py <run base> <run V1> <maillage .med>
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VM_DIR = ROOT / "résultats_MED_Paravis"
SHARE_DIR = Path("/media/sf_partage/echanges/lot36")
EXAMPLES = ROOT / "data" / "examples" / "lot36_butee"

MESH_NAME = "combiwall_maillage.med"
BASE_NAME = "quai_combiwall_resultats_base.med"
V1_NAME = "quai_combiwall_resultats_V1_diagnostic.med"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _mo(path: Path) -> str:
    return f"{path.stat().st_size / 1e6:.1f} Mo".replace(".", ",")


LISEZMOI = """# Lot 36 — fichiers MED du quai combi-wall et ouverture dans ParaVis

Ces fichiers ont été produits par la chaîne de production (`aster-expert generate`,
`aster-expert run`, Code_Aster 17.4.0). Ce sont les **cas élémentaires** G, EAU_P,
EAU_A, Q1, Q3 et A : aucune combinaison, aucun verdict de dimensionnement (la fiche ne
décide aucune combinaison). Niveau de validation du calcul : C (exécuté jusqu'à `FIN`)
avec contrôles D, jamais E.

## Contenu de `résultats_MED_Paravis/`

| Fichier | Taille | SHA-256 | Ce que c'est |
|---|---:|---|---|
| `{mesh}` | {mesh_size} | `{mesh_sha}` | Maillage de l'ouvrage produit par Salomé (`mesh run`), vérifié par `mesh check` (599 invariants sur 599) : 40 114 nœuds, 40 120 QUAD4, 39 583 SEG2, 57 groupes. |
| `{base}` | {base_size} | `{base_sha}` | **Résultats du modèle de calcul** (base) : les six cas élémentaires. Contient aussi son maillage (Code_Aster y a ajouté les mailles ponctuelles des ressorts et les groupes `GEN_*`). |
| `{v1}` | {v1_size} | `{v1_sha}` | Résultats de la variante de **diagnostic** V1 (pression initiale au repos côté bassin ajoutée au cas G). **Ce n'est pas le modèle de calcul** : ne pas l'utiliser pour autre chose que la comparaison du diagnostic de butée. Les cinq autres cas y sont identiques à la base. |
| `EMPREINTES.sha256` | | | Les empreintes ci-dessus, vérifiables par `sha256sum -c EMPREINTES.sha256`. |

Les `.med` ne sont pas versionnés (Git les ignore). Ils sont reproductibles : le `.comm`
exécuté est `data/examples/lot36_butee/complet_base.comm` (base) et
`complet_v1.comm` (V1) ; les répertoires d'exécution sont
`{run_base}` et `{run_v1}` (`proc.0/fort.80`).

## Champs (nom exact dans le MED)

Le nom d'un champ est le nom du résultat (`NOM_RESU_MED`, 8 caractères, complété par des
`_`) suivi du nom du champ. Six cas : `G`, `EAU_P`, `EAU_A`, `Q1`, `Q3`, `A`.

| Champ | Nom MED (exemple : cas G) | Support | Composantes | Unité | Repère |
|---|---|---|---|---|---|
| Déplacements | `G_______DEPL` | nœuds | `DX DY DZ DRX DRY DRZ` | m ; rad | global |
| Réactions | `G_______REAC_NODA` | nœuds | `DX DY DZ DRX DRY DRZ` | N ; N.m | global |
| Efforts des ressorts | `G_______FORC_NODA` | nœuds, **mailles `POI1` seulement** | `DX DY DZ DRX DRY DRZ` (`DY` est la force) | N | global |
| Efforts des tubes, de la poutre, des tirants | `G_ET____EFGE_ELNO` | par élément aux nœuds (ELNO) | `N VY VZ MT MFY MFZ` (poutre, tirants), `NXX NYY NXY MXX MYY MXY QX QY` (tubes) | N, N.m (poutre, tirants) ; N/m, N.m/m (tubes) | repère de l'élément |
| Efforts des palplanches | `G_EP____EFGE_NOEU` | nœuds des palplanches | `NXX NYY NXY MXX MYY MXY QX QY` | N/m ; N.m/m | repère de l'élément |

Pour les autres cas, remplacer `G` : `EAU_P___DEPL`, `EAU_A___DEPL`, `Q1______DEPL`,
`Q3______DEPL`, `A_______DEPL` ; efforts : `EAU_P_ETEFGE_ELNO`, `EAU_A_ETEFGE_ELNO`,
`Q1_ET___EFGE_ELNO`, `Q3_ET___EFGE_ELNO`, `A_ET____EFGE_ELNO`, et de même
`..._EPEFGE_NOEU` pour les palplanches. Cinq champs par cas et par famille : 30 champs en tout.

Points à savoir :

- Dans `..._ET...EFGE_ELNO`, les 14 composantes sont l'union des deux familles : les
  composantes qui ne concernent pas le type de maille valent 0. Se restreindre au groupe
  voulu (`TUBES` pour `NXX…QY`, `POUTRE_COUR` ou `TIRANTS` pour `N…MFZ`).
- Repère de l'élément, `EFGE_*` : pour les tubes et les palplanches, `x_l` est **vertical**
  (`VECTEUR = (0, 0, 1)`) : `MXX` et `NXX` sont le moment et l'effort normal **verticaux**
  par mètre de largeur. Pour la poutre, `x_l = +X`. Les efforts des tubes sont donnés par
  élément et par nœud, **sans moyenne** entre éléments (le repère local des facettes de
  tube diffère de 9° d'une facette à l'autre).
- `EFGE_*` des palplanches et des tubes ne sont **pas** des contraintes : aucune
  contrainte n'est écrite (`SIEF_ELGA` est faux sous `ELAS_COQUE`, il est volontairement
  absent du MED).
- Le MED contient `REAC_NODA` de **tous** les nœuds : seules les réactions des composantes
  réellement bloquées sont des réactions d'appui (`SYM_G`/`SYM_D` : DX ; `PIED_TUBES` : DZ ;
  `ANCRAGES` : DX, DY, DZ). Les autres sont des forces de liaison qui s'annulent sur
  l'ensemble.

## Unités et repère

Unités du système international : mètre, newton, pascal, kilogramme, radian.
Repère global (point 9 de la fiche) : **X** le long du quai, de `SYM_G` vers `SYM_D` ;
**Y** vers la terre (le bassin est en Y négatif) ; **Z** ascendant ; origine dans l'axe de
`TUBE_05` à la cote 0,00 m CM. Palplanches dans le plan Y = 0. Un déplacement DY négatif
va vers le bassin.

## Groupes

Groupes de mailles : `TUBES`, `TUBE_01` à `TUBE_09`, `PALPS`, `PALP_01` à `PALP_08`,
`ECRAN` (tubes et palplanches), `ECRAN_POUSSEE` (faces côté terre et palplanches),
`POUTRE_COUR`, `TIRANTS`, `TIRANT_01` à `TIRANT_09`, `RESS_AV_ARGI`, `RESS_AV_MARNE` (bandes
de ressorts), `DEFENSE`, et, dans le MED de résultats, `GEN_*` (groupes créés à l'exécution
: ressorts `GEN_RESS_*`, couches de poussée `GEN_COUCHE_*`).
Groupes de nœuds : `TETE_TUBE_01` à `TETE_TUBE_09` (anneaux de tête), `ANC_01` à `ANC_09`,
`ANCRAGES`, `BOLLARD`, `SYM_G`, `SYM_D`, `PIED_TUBES`.

## Ouvrir les MED dans ParaVis (Salomé-Méca 2024)

ParaVis est installé dans la VM (image Salomé-Méca 2024.1.0), pas sur l'hôte Windows.

1. Lancer Salomé-Méca (comme d'habitude dans la VM) et activer le module **ParaVis**.
2. *File > Open ParaView File…* (Ctrl+O), choisir un des `.med` de ce dossier ; le lecteur
   proposé est **MEDReader**.
3. Dans le panneau *Properties*, l'arbre des champs est réparti en trois « supports »
   (`ComSup`) :
   - `ComSup0` : les efforts `..._ETEFGE_ELNO` (tubes, poutre, tirants) — **le seul coché par
     défaut** ;
   - `ComSup1` : les efforts `..._EPEFGE_NOEU` des palplanches ;
   - `ComSup2` : `DEPL`, `REAC_NODA`, `FORC_NODA` de chaque cas.

   **MEDReader n'accepte qu'un seul support activé par lecteur** (sinon le message
   « Only one leaf must be activated » apparaît et rien n'est chargé) : décocher `ComSup0`,
   cocher les champs voulus d'**un** support, *Apply*. Pour afficher des déplacements et des
   efforts ensemble, ouvrir le fichier **deux fois** (deux lecteurs).
4. Déformée : sur le lecteur qui porte `ComSup2`, filtre *Calculator* (*Attribute Type* =
   *Point Data*), expression
   `G_______DEPL_DX*iHat+G_______DEPL_DY*jHat+G_______DEPL_DZ*kHat`, résultat `U` ; puis filtre
   *Warp By Vector* (*Vectors* = `U`, *Scale Factor* : le déplacement maximal est de l'ordre
   de 0,01 à 0,04 m, un facteur de 20 à 50 est lisible). Pour colorer par DY en mm :
   *Calculator*, `G_______DEPL_DY*1000`. Les noms de composantes du *Calculator* sont
   `<champ>_DX`, `_DY`, `_DZ`, `_DRX`, `_DRY`, `_DRZ`.
5. Isoler une partie de l'ouvrage : filtre *Extract Group* (MEDReader), noms de groupes
   ci-dessus.

Ce qui a été **vérifié sans interface** (`pvbatch`, Salomé-Méca 2024.1.0, sur le MED de
résultats du quai réduit, même structure) : le lecteur MEDReader lit le fichier, liste les
trois supports et leurs champs, les composantes s'appellent `DX … DRZ`, le cochage de
`ComSup2` charge `DEPL`, `REAC_NODA` et `FORC_NODA` (6 composantes), l'expression du
*Calculator* ci-dessus est acceptée, cocher deux supports produit l'erreur citée. **Non
vérifié** : le rendu et les menus de l'interface graphique (aucun affichage n'est
disponible pour l'agent), le filtre *Extract Group*.

## Ce qui n'est pas dans ces fichiers

Aucune combinaison de cas, aucun effort dimensionnant, aucune vérification normative
(EN 1992, EN 1993-5) : ils supposent des décisions sur les combinaisons et les coefficients
partiels qui ne sont pas dans la fiche. Les tableaux de synthèse et les vues PNG sont dans
le dossier partagé `/media/sf_partage/echanges/lot36/`.
"""


def main(run_base: Path, run_v1: Path, mesh: Path) -> int:
    VM_DIR.mkdir(exist_ok=True)
    files = {
        MESH_NAME: mesh,
        BASE_NAME: run_base / "proc.0" / "fort.80",
        V1_NAME: run_v1 / "proc.0" / "fort.80",
    }
    for name, source in files.items():
        target = VM_DIR / name
        if not target.exists() or _sha256(target) != _sha256(source):
            shutil.copyfile(source, target)
    shas = {name: _sha256(VM_DIR / name) for name in files}
    (VM_DIR / "EMPREINTES.sha256").write_text(
        "".join(f"{sha}  {name}\n" for name, sha in shas.items()), encoding="utf-8"
    )
    text = LISEZMOI.format(
        mesh=MESH_NAME,
        base=BASE_NAME,
        v1=V1_NAME,
        mesh_size=_mo(VM_DIR / MESH_NAME),
        base_size=_mo(VM_DIR / BASE_NAME),
        v1_size=_mo(VM_DIR / V1_NAME),
        mesh_sha=shas[MESH_NAME],
        base_sha=shas[BASE_NAME],
        v1_sha=shas[V1_NAME],
        run_base=run_base.relative_to(ROOT),
        run_v1=run_v1.relative_to(ROOT),
    )
    (VM_DIR / "LISEZMOI.md").write_text(text, encoding="utf-8")

    # dossier partagé : aucune copie de MED
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    reports = EXAMPLES / "rapports_base"
    for name in ("synthese.md", "controles.md", "synthese.json", "equilibre_base.json"):
        shutil.copyfile(reports / name, SHARE_DIR / name)
    views = SHARE_DIR / "vues"
    if views.exists():
        shutil.rmtree(views)
    shutil.copytree(reports / "vues", views)
    for name in (
        "rapport_butee.md",
        "butee_g_base_v1.json",
        "noeuds_base_G.json",
        "controles_c2_c6.json",
        "complet_base.comm",
    ):
        shutil.copyfile(EXAMPLES / name, SHARE_DIR / name)
    share_text = text + (
        "\n## Où sont les MED\n\nDans la VM : `~/projets/aster-expert/résultats_MED_Paravis/` "
        "(non copiés ici : le dossier partagé est sur OneDrive et le MED de résultats fait "
        f"{_mo(VM_DIR / BASE_NAME)}). Vérifier une copie par les empreintes ci-dessus.\n"
    )
    (SHARE_DIR / "LISEZMOI.md").write_text(share_text, encoding="utf-8")
    print(f"{VM_DIR} : {sorted(p.name for p in VM_DIR.iterdir())}")
    print(f"{SHARE_DIR} : {sorted(p.name for p in SHARE_DIR.iterdir())}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*(Path(a).resolve() for a in sys.argv[1:4])))
