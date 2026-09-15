"""Unit tests for the `.comm` structural parser (lot 9).

Every `.comm`-shaped fixture below is a verbatim excerpt of an official
Code_Aster test case from `external/codeaster-src/astest` (never generated,
never taken from a user's private calculation file — see
docs/development-plan.md, lot 9). Each fixture names its source file and
line range. Fine-grained edge cases of the internal value resolver that no
short official excerpt happens to exercise (a mixed `_F(...)`/non-`_F(...)`
list, a comprehension, ...) are covered separately, directly against a bare
`ast` expression rather than against invented `.comm` content.
"""

from __future__ import annotations

import ast

from aster_expert.parsing.comm_parser import (
    _classify_dynamic,
    _is_factor_call,
    _resolve_keyword_entry,
    _ResolveContext,
    parse_comm_source,
)
from aster_expert.parsing.errors import CommParseError
from aster_expert.parsing.models import (
    ConceptReferenceValue,
    DynamicValue,
    FactorKeywordValue,
    LiteralValue,
    SimpleKeywordValue,
)

# external/codeaster-src/astest/ssns112c.comm, verbatim, full file (49 lines
# + trailing newline).
SSNS112C = """\
# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2025 - EDF R&D - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

#

# epaisseur de la plaque
ep_beton = 0.15

DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"), DEBUG=_F(SDVERI="OUI"))

# -----------------------------------------------
# LECTURE DU MAILLAGE
# -----------------------------------------------
MAIL = LIRE_MAILLAGE(FORMAT="MED")

MAIL = DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=(_F(GROUP_MA="A"), _F(GROUP_MA="B")))

MAIL = MODI_MAILLAGE(
    reuse=MAIL,
    MAILLAGE=MAIL,
    ORIE_NORM_COQUE=_F(GROUP_MA="POUTRE", VECT_NORM=(0.0, 0.0, 1.0), GROUP_NO="AA"),
)

# -----------------------------------------------
# CREATION DU MODELE
# -----------------------------------------------
MO = AFFE_MODELE(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="DKTG"))

# -----------------------------------------------
# DEFINTION DES MATERIAUX ET CARACTERSISTIQUES
# -----------------------------------------------

FIN()
"""

# external/codeaster-src/astest/erreu14a.comm, lines 39-58: a Python-level
# if/else around two candidate FORMULE/DEFI_FONCTION statements.
ERREU14A_IF_ELSE = """\
MAIL = LIRE_MAILLAGE(FORMAT="ASTER")

MO = AFFE_MODELE(
    MAILLAGE=MAIL, AFFE=_F(GROUP_MA="CARRE", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN")
)

if 0:
    E = FORMULE(NOM_PARA=("SECH",), VALE="1.+SECH")
else:
    E = DEFI_FONCTION(NOM_PARA=("SECH",), VALE=(0.0, 1.0, 100.0, 100.0))

NU = DEFI_CONSTANTE(VALE=0.35)

ACIER = DEFI_MATERIAU(ELAS_FO=_F(E=E, NU=NU))

CHMAT = AFFE_MATERIAU(MAILLAGE=MAIL, AFFE=_F(TOUT="OUI", MATER=ACIER))

CHARGT = AFFE_CHAR_MECA(
    MODELE=MO, DDL_IMPO=(_F(GROUP_MA="BORD1", DX=0.0, DY=0.0), _F(GROUP_MA="BORD2", DY=1.0))
)
"""

# external/codeaster-src/astest/erreu14a.comm, lines 75-82: a try/except
# around a command call, with a plain-Python variable reassigned in the
# handler.
ERREU14A_TRY_EXCEPT = """\
is_ok = 0
try:
    DEF1 = MECA_STATIQUE(MODELE=MO, CHAM_MATER=CHMAT1, EXCIT=_F(CHARGE=CHARGT))
except CA.AsterError as err:
    print(fmt_raison % str(err))
    # on verifie que l'erreur fatale est bien celle que l'on attendait :
    if err.id_message == "CALCULEL6_62":
        is_ok = 1
"""

# external/codeaster-src/astest/mfron02h.comm, lines 22-51: a lowercase
# assignment target, a `for` loop, and a keyword value (`ORDONNEE`) that
# references a plain Python variable computed from a subprocess return code,
# followed by a TEST_FONCTION (not TEST_RESU) call.
MFRON02H_EXCERPT = """\
DEBUT(CODE="OUI", ERREUR=_F(ALARME="EXCEPTION"))

import os
from glob import glob

behaviour = CREA_LIB_MFRONT(NOM_COMPOR="BurgerAgeing", UNITE_MFRONT=38, UNITE_LIBRAIRIE=39)

from subprocess import Popen, PIPE

mtest = "mtest"
for path in os.environ["PATH"].split(os.pathsep):
    found = glob(os.path.join(path, "mtest*"))
    if found:
        mtest = found[0]
        break

proc = Popen([mtest, "fort.22"], stdout=PIPE)

out = proc.communicate()[0]

codret = proc.returncode + 1
print("codret=", codret)

if codret != 0:
    print(out)


Fres = DEFI_FONCTION(NOM_PARA="INST", ABSCISSE=[0.0, 1.0], ORDONNEE=[0.0, codret])

TEST_FONCTION(VALEUR=(_F(VALE_CALC=1.0, VALE_PARA=1.0, FONCTION=Fres),))
"""

# external/codeaster-src/astest/sdll129a.comm, lines 849-850: dict-unpacking
# used to build a command's keywords.
SDLL129A_KWARGS = """\
motcles = tab.dict_CREA_TABLE()
tab_out = CREA_TABLE(TYPE_TABLE="TABLE_CONTAINER", **motcles)
"""

# external/codeaster-src/astest/sdll129a.comm, lines 768-770 (dedented from
# their original `for kk in range(...):` loop body to stand alone as a valid
# top-level snippet): a command call assigned to a subscript target inside a
# loop (`RIGI[kk] = CO(...)`).
SDLL129A_SUBSCRIPT_TARGET = """\
RIGI[kk] = CO("RIGI_%d" % (kk))
MASS[kk] = CO("MASS_%d" % (kk))
AMOR[kk] = CO("AMOR_%d" % (kk))
"""


def test_simple_file_fully_resolved_no_warnings() -> None:
    analysis = parse_comm_source(SSNS112C, file_path="ssns112c.comm")

    assert [s.command for s in analysis.statements] == [
        "DEBUT",
        "LIRE_MAILLAGE",
        "DEFI_GROUP",
        "MODI_MAILLAGE",
        "AFFE_MODELE",
        "FIN",
    ]
    assert analysis.parse_warnings == []
    assert all(not s.dynamic for s in analysis.statements)
    assert all(s.unresolved == [] for s in analysis.statements)


def test_reuse_is_captured_separately_from_referenced_concepts() -> None:
    analysis = parse_comm_source(SSNS112C, file_path="ssns112c.comm")
    defi_group = analysis.statements[2]

    assert defi_group.command == "DEFI_GROUP"
    assert defi_group.assigned_concept == "MAIL"
    assert defi_group.reuse == "MAIL"
    assert defi_group.referenced_concepts == ["MAIL"]


def test_factor_keyword_with_multiple_occurrences() -> None:
    analysis = parse_comm_source(SSNS112C, file_path="ssns112c.comm")
    defi_group = analysis.statements[2]

    crea_group_no = defi_group.keywords["CREA_GROUP_NO"]
    assert isinstance(crea_group_no, FactorKeywordValue)
    assert len(crea_group_no.occurrences) == 2
    first = crea_group_no.occurrences[0].keywords["GROUP_MA"]
    assert isinstance(first, SimpleKeywordValue)
    assert isinstance(first.value, LiteralValue)
    assert first.value.value == "A"


def test_literal_group_and_modelisation_extraction() -> None:
    analysis = parse_comm_source(SSNS112C, file_path="ssns112c.comm")
    modi_maillage = analysis.statements[3]
    affe_modele = analysis.statements[4]

    assert modi_maillage.mesh_groups == ["POUTRE"]
    assert modi_maillage.node_groups == ["AA"]
    assert affe_modele.modelisations == ["DKTG"]
    assert affe_modele.phenomena == ["MECANIQUE"]


def test_file_hash_and_no_version_guessed() -> None:
    analysis = parse_comm_source(SSNS112C, file_path="ssns112c.comm")

    assert analysis.file_hash.startswith("sha256:")
    assert analysis.assumed_version is None
    assert analysis.version_source == "undetermined"


def test_if_else_marks_both_branches_dynamic_without_choosing_one() -> None:
    analysis = parse_comm_source(ERREU14A_IF_ELSE, file_path="erreu14a.comm")

    # Both branches assign the same concept "E": both must be present, in
    # document order, each explicitly marked as conditional. Neither branch
    # is "selected" -- lot 9 never executes the file to find out which runs.
    e_statements = [s for s in analysis.statements if s.assigned_concept == "E"]
    assert [s.command for s in e_statements] == ["FORMULE", "DEFI_FONCTION"]
    for s in e_statements:
        assert s.control_flow == ["If"]
        assert s.dynamic is True
        assert any(u.startswith("@statement:") for u in s.unresolved)


def test_try_except_marks_statement_dynamic_and_resolves_reference_variable() -> None:
    source = (
        'MO = AFFE_MODELE(MAILLAGE="MAIL")\n'
        'CHMAT1 = AFFE_MATERIAU(MAILLAGE="MAIL")\n'
        "CHARGT = AFFE_CHAR_MECA(MODELE=MO)\n" + ERREU14A_TRY_EXCEPT
    )
    analysis = parse_comm_source(source, file_path="erreu14a.comm")
    meca_statique = next(s for s in analysis.statements if s.command == "MECA_STATIQUE")

    assert meca_statique.control_flow == ["Try"]
    assert meca_statique.dynamic is True
    assert meca_statique.referenced_concepts == ["CHARGT", "CHMAT1", "MO"]


def test_lowercase_target_and_reference_variable_reason() -> None:
    analysis = parse_comm_source(MFRON02H_EXCERPT, file_path="mfron02h.comm")

    crea_lib = analysis.statements[1]
    assert crea_lib.command == "CREA_LIB_MFRONT"
    assert crea_lib.assigned_concept == "behaviour"
    assert crea_lib.dynamic is False

    defi_fonction = next(s for s in analysis.statements if s.command == "DEFI_FONCTION")
    assert defi_fonction.dynamic is True
    assert defi_fonction.unresolved == ["ORDONNEE"]
    ordonnee = defi_fonction.keywords["ORDONNEE"]
    assert isinstance(ordonnee, SimpleKeywordValue)
    assert isinstance(ordonnee.value, DynamicValue)
    # ORDONNEE=[0.0, codret] fails `literal_eval` as a whole (one element,
    # `codret`, is a plain Python name computed from a subprocess return
    # code): resolution is per-keyword, not per-element, so this falls into
    # the generic "autre" bucket, not "reference_variable" (that reason is
    # reserved for a keyword value that is *itself* a bare name reference,
    # see test_concept_reference_vs_dynamic_name below).
    assert ordonnee.value.reason == "autre"
    assert ordonnee.value.node_type == "List"


def test_test_fonction_is_not_counted_as_test_resu() -> None:
    analysis = parse_comm_source(MFRON02H_EXCERPT, file_path="mfron02h.comm")

    assert any(s.command == "TEST_FONCTION" for s in analysis.statements)
    assert analysis.test_statements == []


def test_kwargs_unpacking_is_reported_and_marks_statement_dynamic() -> None:
    source = "tab = None\n" + SDLL129A_KWARGS
    analysis = parse_comm_source(source, file_path="sdll129a.comm")
    crea_table = next(s for s in analysis.statements if s.command == "CREA_TABLE")

    assert crea_table.dynamic is True
    assert any(u.startswith("**kwargs") for u in crea_table.unresolved)
    assert any(w.node_type == "keyword-unpacking" for w in analysis.parse_warnings)


def test_subscript_assignment_target_is_warned_and_excluded() -> None:
    source = "kk = 0\n" + SDLL129A_SUBSCRIPT_TARGET
    analysis = parse_comm_source(source, file_path="sdll129a.comm")

    assert analysis.statements == []
    assert len(analysis.parse_warnings) == 3
    assert all(w.node_type == "Assign" for w in analysis.parse_warnings)
    assert "CO" in analysis.parse_warnings[0].message


def test_test_resu_is_indexed_and_external_unite_captured() -> None:
    source = (
        'MAIL = LIRE_MAILLAGE(UNITE=20, FORMAT="MED")\n'
        "TEST_RESU(RESU=_F(RESULTAT=MAIL))\n"
    )
    analysis = parse_comm_source(source, file_path="synthetic.comm")

    assert analysis.test_statements == [1]
    assert len(analysis.external_files) == 1
    ref = analysis.external_files[0]
    assert ref.command == "LIRE_MAILLAGE"
    assert ref.unite == 20
    assert ref.fichier is None


def test_syntax_error_raises_comm_parse_error() -> None:
    try:
        parse_comm_source("DEBUT(CODE=", file_path="broken.comm")
    except CommParseError:
        return
    raise AssertionError("expected CommParseError")


# --------------------------------------------------------------------------
# Internal resolver edge cases, exercised against bare `ast` expressions
# rather than invented `.comm` content (see the module docstring).
# --------------------------------------------------------------------------


def _expr(text: str) -> ast.expr:
    node = ast.parse(text, mode="eval").body
    ast.fix_missing_locations(node)
    return node


def test_classify_dynamic_dict_is_dictionnaire_assemble() -> None:
    reason, node_type = _classify_dynamic(_expr('{"A": x}'))
    assert reason == "dictionnaire_assemble"
    assert node_type == "Dict"


def test_classify_dynamic_comprehension() -> None:
    reason, _ = _classify_dynamic(_expr("[x for x in y]"))
    assert reason == "comprehension"


def test_classify_dynamic_concatenation() -> None:
    reason, _ = _classify_dynamic(_expr('"a" + b'))
    assert reason == "concatenation"


def test_classify_dynamic_function_call() -> None:
    reason, _ = _classify_dynamic(_expr("f(x)"))
    assert reason == "appel_fonction"


def test_classify_dynamic_fallback_is_autre() -> None:
    reason, node_type = _classify_dynamic(_expr("x.attr"))
    assert reason == "autre"
    assert node_type == "Attribute"


def test_is_factor_call_matches_only_underscore_f() -> None:
    assert _is_factor_call(_expr("_F(A=1)")) is True
    assert _is_factor_call(_expr("G(A=1)")) is False
    assert _is_factor_call(_expr("1")) is False


def test_mixed_factor_list_is_unresolved_not_a_factor_keyword() -> None:
    node = _expr("(_F(A=1), autre_valeur)")
    ctx = _ResolveContext(known_concepts=set(), loop_names=set(), warnings=[])

    result = _resolve_keyword_entry("EXCIT", node, ctx)

    assert isinstance(result, SimpleKeywordValue)
    assert isinstance(result.value, DynamicValue)
    assert result.value.node_type == "MixedFactorList"
    assert len(ctx.warnings) == 1


def test_concept_reference_vs_dynamic_name() -> None:
    ctx = _ResolveContext(known_concepts={"MO"}, loop_names=set(), warnings=[])

    concept = _resolve_keyword_entry("MODELE", _expr("MO"), ctx)
    assert isinstance(concept, SimpleKeywordValue)
    assert isinstance(concept.value, ConceptReferenceValue)
    assert concept.value.concept == "MO"

    other = _resolve_keyword_entry("VALE", _expr("coef"), ctx)
    assert isinstance(other, SimpleKeywordValue)
    assert isinstance(other.value, DynamicValue)
    assert other.value.reason == "reference_variable"


def test_loop_variable_name_is_classified_as_boucle() -> None:
    ctx = _ResolveContext(known_concepts=set(), loop_names={"nom"}, warnings=[])

    result = _resolve_keyword_entry("GROUP_MA", _expr("nom"), ctx)

    assert isinstance(result, SimpleKeywordValue)
    assert isinstance(result.value, DynamicValue)
    assert result.value.reason == "boucle"
