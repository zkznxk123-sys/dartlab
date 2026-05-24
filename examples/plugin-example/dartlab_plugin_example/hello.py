"""Hello plugin — dartlab entry-points 진입 함수 + 메타.

T5-2 — plugin 작성 *최소 예시*. 실제 plugin 은 본 패턴을 확장:
    - PLUGIN_KIND: "scan" / "analysis" / "tool" / "recipe"
    - PLUGIN_SCHEMA: dict (입력/출력 schema, dartlab.core.plugins.listPlugins 로 노출)
    - main(): plugin entry function — dartlab 의 호출 패턴 정합 시그니처
"""

from __future__ import annotations

from typing import Any

# T5-1 core/plugins.py 가 read 하는 메타.
PLUGIN_KIND: str = "example"
PLUGIN_SCHEMA: dict[str, Any] = {
    "inputs": {"name": "str"},
    "outputs": {"greeting": "str"},
    "description": "dartlab plugin 진입 예시 — name 받아서 greeting 반환",
}


def main(*, name: str = "world") -> dict[str, str]:
    """Hello plugin entry function.

    Args:
        name: 인사 대상 이름 (default "world").
    Returns:
        {"greeting": "Hello, {name}!"} dict.
    Example:
        >>> from dartlab_plugin_example.hello import main
        >>> main(name="dartlab")
        {'greeting': 'Hello, dartlab!'}
    """
    return {"greeting": f"Hello, {name}!"}
