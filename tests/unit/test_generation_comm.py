"""Lot 32, étape 1 : la règle de construction des conditions aux limites --
dans un ensemble de nœuds liés par `LIAISON_SOLIDE`, un degré de liberté que
la relation détermine (translations et rotations de l'anneau de tête, dérivées
du nœud de poutre) n'est imposé directement que sur un seul nœud de
l'ensemble. `symmetry_and_support_block` construit le texte, et
`check_symmetry_ddl_impo_no_ring_redundancy` (le contrôle du générateur,
appelé avant écriture) le vérifie."""

from __future__ import annotations

import pytest

from aster_expert.generation.comm import (
    SYMD_ROT_GROUP,
    SYMG_ROT_GROUP,
    TABLE_FORMAT_R,
    TABLE_TITLE_MAX,
    assembled_load_block,
    check_symmetry_ddl_impo_no_ring_redundancy,
    controls_block,
    full_block_charge_block,
    mesh_prep_block,
    reaction_table_title,
    six_dof_group_block,
    spring_force_block,
    symmetry_and_support_block,
)
from aster_expert.generation.errors import GenerationError
from aster_expert.generation.springs import COMBINED_BAND, SpringClass


def test_symmetry_block_excludes_the_ring_from_every_determined_dof() -> None:
    text = symmetry_and_support_block()
    assert f'_F(GROUP_NO=("{SYMG_ROT_GROUP}",), DX=0.0, DRY=0.0, DRZ=0.0),' in text
    assert f'_F(GROUP_NO=("{SYMD_ROT_GROUP}",), DX=0.0, DRY=0.0, DRZ=0.0),' in text
    assert 'GROUP_NO=("SYM_G",)' not in text
    assert 'GROUP_NO=("SYM_D",)' not in text


def test_symmetry_block_passes_its_own_control() -> None:
    # `symmetry_and_support_block` calls the control itself before
    # returning -- a passing call already proves this, but this test makes
    # the invariant explicit and independent of that internal call.
    text = symmetry_and_support_block()
    check_symmetry_ddl_impo_no_ring_redundancy(text, split_ring_rotation=True)


def test_symmetry_block_without_split_uses_the_raw_plane_groups() -> None:
    """Candidats de jonction C1/C4 (lot 31) : aucune liaison rigide ne dérive
    le dof de l'anneau depuis le nœud de poutre, la règle du lot 32 ne
    s'applique donc pas -- le contrôle ne doit rien y détecter."""
    text = symmetry_and_support_block(split_ring_rotation=False)
    assert '_F(GROUP_NO=("SYM_G",), DX=0.0, DRY=0.0, DRZ=0.0),' in text
    assert '_F(GROUP_NO=("SYM_D",), DX=0.0, DRY=0.0, DRZ=0.0),' in text
    check_symmetry_ddl_impo_no_ring_redundancy(text, split_ring_rotation=False)


def test_control_rejects_a_direct_dx_block_on_the_raw_plane() -> None:
    """Reproduit le défaut du lot 31 (translation encore redondante) : un
    texte qui impose DX sur SYM_G brut, en plus de LIAISON_SOLIDE, doit être
    refusé par le contrôle avant écriture."""
    buggy_text = (
        "CH_BLOC = AFFE_CHAR_MECA(\n"
        "    MODELE=MO,\n"
        "    DDL_IMPO=(\n"
        '        _F(GROUP_NO=("SYM_G",), DX=0.0),\n'
        f'        _F(GROUP_NO=("{SYMG_ROT_GROUP}",), DRY=0.0, DRZ=0.0),\n'
        "    ),\n"
        ")\n"
    )
    with pytest.raises(GenerationError, match="redondance CL"):
        check_symmetry_ddl_impo_no_ring_redundancy(buggy_text, split_ring_rotation=True)


def test_control_rejects_a_direct_rotation_block_on_the_raw_plane() -> None:
    buggy_text = '_F(GROUP_NO=("SYM_D",), DRY=0.0, DRZ=0.0),\n'
    with pytest.raises(GenerationError, match="redondance CL"):
        check_symmetry_ddl_impo_no_ring_redundancy(buggy_text, split_ring_rotation=True)


_CASES = ("G", "EAU_P", "EAU_A", "Q1", "Q3", "A")


def test_every_reaction_table_title_fits_the_printed_column_and_is_unique() -> None:
    """`IMPR_TABLE` tronque l'intitulé à 16 caractères : deux tables dont les
    intitulés ne diffèrent qu'après le 16e sont indiscernables dans le `.mess`
    (lot 34 : `REAC_PIED_TUBES_G` et `REAC_PIED_TUBES_Q1` devenaient tous deux
    `REAC_PIED_TUBES_`)."""
    titles = [
        reaction_table_title(group, case)
        for group in ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D", "TOUS")
        for case in _CASES
    ]
    assert all(len(t) <= TABLE_TITLE_MAX for t in titles)
    assert len({t[:TABLE_TITLE_MAX] for t in titles}) == len(titles)


def test_a_too_long_reaction_table_title_is_refused() -> None:
    with pytest.raises(GenerationError, match="intitulé de table trop long"):
        reaction_table_title("ANCRAGES", "UN_CAS_AU_NOM_BIEN_TROP_LONG")


def test_controls_read_every_reaction_component_per_support_group() -> None:
    text = controls_block("EAU_P", ["GEN_RESS_ARGI_01"])
    for group in ("ANCRAGES", "PIED_TUBES", "SYM_G", "SYM_D"):
        assert f'GROUP_NO=("{group}",)' in text
        assert f'INTITULE="{reaction_table_title(group, "EAU_P")}"' in text
    assert f'INTITULE="{reaction_table_title("TOUS", "EAU_P")}"' in text
    assert 'RESULTANTE=("DX", "DY", "DZ")' in text
    assert "GEN_TOUS_NOEUDS" in text


def test_control_tables_print_twelve_significant_digits() -> None:
    """Le format par défaut (`E12.5`, six chiffres) arrondit une résultante de
    1e6 N à 5 N près : trop grossier pour un critère d'équilibre à 1e-6."""
    text = controls_block("G", ["GEN_RESS_ARGI_01"])
    assert TABLE_FORMAT_R == "E20.12"
    assert text.count("IMPR_TABLE(") == text.count(f'FORMAT_R="{TABLE_FORMAT_R}"')


def test_spring_force_check_is_off_by_default_and_restricted_to_the_poi1() -> None:
    assert "FORC_NODA" not in controls_block("G", ["GEN_RESS_ARGI_01"])
    text = controls_block("G", ["GEN_RESS_ARGI_01"], spring_force_check=True)
    assert 'GROUP_MA=("GEN_RESS_ARGI_01")' in text
    assert 'FORCE=("FORC_NODA",)' in text
    assert spring_force_block("G", ["A", "B"]).count('"A", "B"') == 2


def test_the_probe_blocks_every_dof_and_sums_the_reactions_of_all_nodes() -> None:
    blocks = full_block_charge_block()
    assert 'GROUP_NO=("GEN_TOUS_NOEUDS",), DX=0.0, DY=0.0, DZ=0.0' in blocks
    assert f'GROUP_NO=("{"GEN_NOEUDS_6DDL"}",), DRX=0.0, DRY=0.0, DRZ=0.0' in blocks
    assert "GEN_TOUS_TUBES" in six_dof_group_block()
    assert "GEN_TOUS_TIRANTS" not in six_dof_group_block()
    nodal = assembled_load_block("G", nodal=True)
    assert "TAB_CHARGE_G" in nodal
    assert 'RESULTANTE=("DX", "DY", "DZ")' in nodal
    assert "CH_NOEUDS_G" in nodal
    assert "CH_NOEUDS" not in assembled_load_block("G")


def _spring_class(name: str, band: str, parents: tuple[str, ...] = ()) -> SpringClass:
    return SpringClass(
        band=band,
        group_name=name,
        stiffness_mn_per_m=1.0,
        nodes=((0.0, 0.0, 0.0),),
        parents=parents,
    )


def test_a_common_spring_class_is_the_intersection_of_its_two_parent_groups() -> None:
    classes = [
        _spring_class("GEN_RESS_ARGI_01", "RESS_AV_ARGI"),
        _spring_class("GEN_RESS_MARNE_01", "RESS_AV_MARNE"),
        _spring_class(
            "GEN_RESS_COMM_01",
            COMBINED_BAND,
            ("GEN_RESS_ARGI_01", "GEN_RESS_MARNE_01"),
        ),
    ]
    text = mesh_prep_block(
        beam_points={},
        normal_ref_point=(0.0, 0.0, 0.0),
        spring_classes=classes,
        spring_bands={"RESS_AV_ARGI": (-18.0, -9.0), "RESS_AV_MARNE": (-26.0, -18.0)},
        edge_tube_low="01",
        edge_tube_high="03",
    )
    expected = (
        '_F(NOM="GEN_RESS_COMM_01", '
        'INTERSEC=("GEN_RESS_ARGI_01", "GEN_RESS_MARNE_01",)),'
    )
    assert expected in text
    assert 'NOM_GROUP_MA="GEN_RESS_COMM_01", GROUP_NO=("GEN_RESS_COMM_01",)' in text
    # créée après les groupes de classe (une commande de plus), avant CREA_POI1
    assert text.index('INTERSEC=("GEN_RESS_ARGI_01"') < text.index("CREA_POI1")
