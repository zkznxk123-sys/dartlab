"""gather/dart/keys.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.keys  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_check_callable() -> None:
    """check() callable smoke."""
    from dartlab.gather.dart.keys import DartKeyProvider

    assert hasattr(DartKeyProvider, "check")


def test_save_callable() -> None:
    """save() callable smoke."""
    from dartlab.gather.dart.keys import DartKeyProvider

    assert hasattr(DartKeyProvider, "save")


def test_to_dict_callable() -> None:
    """toDict() callable smoke."""
    from dartlab.gather.dart.keys import DartKeyStatus

    assert hasattr(DartKeyStatus, "toDict")


def test_clear_dart_key_from_dotenv_callable() -> None:
    """clearDartKeyFromDotenv() callable smoke."""
    from dartlab.gather.dart.keys import clearDartKeyFromDotenv

    assert callable(clearDartKeyFromDotenv)


def test_find_project_env_path_callable() -> None:
    """findProjectEnvPath() callable smoke."""
    from dartlab.gather.dart.keys import findProjectEnvPath

    assert callable(findProjectEnvPath)


def test_get_dart_key_status_callable() -> None:
    """getDartKeyStatus() callable smoke."""
    from dartlab.gather.dart.keys import getDartKeyStatus

    assert callable(getDartKeyStatus)


def test_has_dart_api_key_callable() -> None:
    """hasDartApiKey() callable smoke."""
    from dartlab.gather.dart.keys import hasDartApiKey

    assert callable(hasDartApiKey)


def test_load_dotenv_dart_keys_callable() -> None:
    """loadDotenvDartKeys() callable smoke."""
    from dartlab.gather.dart.keys import loadDotenvDartKeys

    assert callable(loadDotenvDartKeys)


def test_resolve_dart_keys_callable() -> None:
    """resolveDartKeys() callable smoke."""
    from dartlab.gather.dart.keys import resolveDartKeys

    assert callable(resolveDartKeys)


def test_save_dart_key_to_dotenv_callable() -> None:
    """saveDartKeyToDotenv() callable smoke."""
    from dartlab.gather.dart.keys import saveDartKeyToDotenv

    assert callable(saveDartKeyToDotenv)


def test_validate_dart_api_key_callable() -> None:
    """validateDartApiKey() callable smoke."""
    from dartlab.gather.dart.keys import validateDartApiKey

    assert callable(validateDartApiKey)
