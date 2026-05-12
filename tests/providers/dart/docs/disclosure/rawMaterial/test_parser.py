"""providers/dart/docs/disclosure/rawMaterial/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.disclosure.rawMaterial.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_capex_callable() -> None:
    """parseCapex() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.rawMaterial.parser import parseCapex

    assert callable(parseCapex)


def test_parse_equipment_callable() -> None:
    """parseEquipment() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.rawMaterial.parser import parseEquipment

    assert callable(parseEquipment)


def test_parse_raw_materials_callable() -> None:
    """parseRawMaterials() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.rawMaterial.parser import parseRawMaterials

    assert callable(parseRawMaterials)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.disclosure.rawMaterial.parser import splitCells

    assert callable(splitCells)
