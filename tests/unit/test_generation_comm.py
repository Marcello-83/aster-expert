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
    check_symmetry_ddl_impo_no_ring_redundancy,
    symmetry_and_support_block,
)
from aster_expert.generation.errors import GenerationError


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
