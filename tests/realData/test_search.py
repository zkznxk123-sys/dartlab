"""search 엔진 실제 데이터 스모크 — 공시 전문검색 (BETA).

인덱스 신선도 부족 상태이므로 보수적으로 검증.
"""

from __future__ import annotations

import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestSearchEngine:
    def test_search_callable(self):
        import dartlab

        assert callable(dartlab.search)

    def test_search_runsWithoutCrash(self):
        """흔한 키워드 1개로 호출 — 빈 결과는 허용, 크래시는 실패."""
        import dartlab

        try:
            result = dartlab.search("반도체", limit=3)
        except FileNotFoundError:
            pytest.skip("search 인덱스 parquet 없음")
        except Exception as e:
            pytest.fail(f"search 크래시: {type(e).__name__}: {e}")
        # 결과가 None 이어도 크래시 아니면 통과 (beta 정책)
        assert result is None or hasattr(result, "__class__")
