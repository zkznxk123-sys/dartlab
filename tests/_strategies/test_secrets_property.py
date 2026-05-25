"""core/secrets hypothesis property — T6-1 (8/10)."""

from __future__ import annotations

import os

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestSecretsProperty:
    """EnvSecretStore property 5."""

    @given(
        key=st.text(
            alphabet=st.characters(min_codepoint=ord("A"), max_codepoint=ord("Z")), min_size=5, max_size=20
        ).map(lambda s: f"DARTLAB_TEST_{s}"),
        value=st.text(
            alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E, blacklist_categories=("Cs",)),
            min_size=1,
            max_size=50,
        ),
    )
    def test_env_store_set_get_round_trip(self, key: str, value: str) -> None:
        from dartlab.core.secrets import EnvSecretStore

        store = EnvSecretStore()
        try:
            store.set(key, value)
            assert store.get(key) == value
        finally:
            store.delete(key)

    def test_env_store_get_missing_returns_none(self) -> None:
        from dartlab.core.secrets import EnvSecretStore

        store = EnvSecretStore()
        assert store.get("DARTLAB_NEVER_EXISTS_KEY_XYZ_123") is None

    def test_env_store_delete_idempotent(self) -> None:
        from dartlab.core.secrets import EnvSecretStore

        store = EnvSecretStore()
        store.delete("DARTLAB_NEVER_EXISTS_KEY_DELETE")
        store.delete("DARTLAB_NEVER_EXISTS_KEY_DELETE")  # 2번째도 raise X

    def test_env_store_list_keys_returns_list(self) -> None:
        from dartlab.core.secrets import EnvSecretStore

        store = EnvSecretStore()
        keys = store.listKeys()
        assert isinstance(keys, list)
        assert all(isinstance(k, str) for k in keys)

    @given(key=st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ_", min_size=3, max_size=20))
    def test_env_store_set_visible_in_environ(self, key: str) -> None:
        from dartlab.core.secrets import EnvSecretStore

        store = EnvSecretStore()
        testKey = f"DARTLAB_TEST_VISIBLE_{key}"
        try:
            store.set(testKey, "v")
            assert os.environ.get(testKey) == "v"
        finally:
            store.delete(testKey)
