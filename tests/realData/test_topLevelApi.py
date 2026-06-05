"""dartlab.* 최상위 공개 API 전수 스모크.

`dir(dartlab)` 의 공개 심볼 전부를 iterate — 외부 사용자가 `from dartlab import X`
로 접근했을 때 import/접근 자체가 크래시하지 않는지 검증.

callable 은 접근 가능만 확인 (인자 없이 호출하면 TypeError 발생 가능).
"""

from __future__ import annotations

import pytest


def _publicTopLevel() -> list[str]:
    """dartlab 공개 심볼 — 단, 서브모듈/대문자 클래스 제외하고 함수 위주로."""
    import dartlab

    skip = {
        "sys",  # 표준 라이브러리 re-export
        "config",  # 구성 객체 (접근해도 의미 없음)
        "core",  # 내부 패키지
        "providers",  # 내부 패키지
    }
    return sorted(name for name in dir(dartlab) if not name.startswith("_") and name not in skip)


TOP_LEVEL = _publicTopLevel()


@pytest.mark.realData
@pytest.mark.integration
@pytest.mark.parametrize("symbol", TOP_LEVEL)
def test_topLevelSymbol_accessible(symbol):
    """dartlab.<symbol> 접근이 크래시 없이 동작."""
    import dartlab

    try:
        value = getattr(dartlab, symbol)
    except Exception as e:
        pytest.fail(f"dartlab.{symbol} 접근 크래시: {type(e).__name__}: {e}")
    # 접근만 보장 — 값 자체는 타입 무관
    assert value is not None or symbol in {"reloadPlugins"}, f"dartlab.{symbol} 가 None — 공개 심볼에서 None 은 의심"


@pytest.mark.realData
@pytest.mark.integration
def test_capabilities_listsAllEngines():
    """dartlab.capabilities 가 엔진 목록 반환 (loadCapabilities 소비자)."""
    import dartlab

    try:
        caps = dartlab.capabilities()
    except TypeError:
        # capabilities 가 속성이면
        caps = dartlab.capabilities
    assert caps is not None
    # list/dict/DataFrame 중 하나
    length = getattr(caps, "height", None) or (len(caps) if hasattr(caps, "__len__") else 0)
    assert length > 0, "capabilities 가 비어있음 — 엔진 자동 등록 실패"
