"""core/plugins hypothesis property — T6-1."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestPluginsProperty:
    """plugins discoverPlugins / listPlugins / describePlugin property 4."""

    def test_discover_returns_list(self) -> None:
        from dartlab.core.plugins import discoverPlugins

        plugins = discoverPlugins()
        assert isinstance(plugins, list)

    def test_list_plugins_returns_dicts(self) -> None:
        from dartlab.core.plugins import listPlugins

        plugins = listPlugins()
        assert isinstance(plugins, list)
        for p in plugins:
            assert isinstance(p, dict)
            assert "name" in p

    def test_describe_missing_raises_keyerror(self) -> None:
        from dartlab.core.plugins import describePlugin

        with pytest.raises(KeyError):
            describePlugin("NEVER_EXISTS_PLUGIN_XYZ_123")

    def test_descriptor_default_kind_unknown(self) -> None:
        from dartlab.core.plugins import PluginDescriptor

        d = PluginDescriptor(name="x", moduleName="x.y:main")
        assert d.kind == "unknown"
        assert d.version == "0.0.0"
