"""Company facade 실제 데이터 스모크.

dartlab 사상의 1원칙 "종목코드 하나면 끝" 의 정면 검증.
외부 사용자가 `Company("005930").topics` / `Company("005930").panel(...)` 처럼
호출했을 때 **None/크래시 없이 정상 객체** 가 돌아오는지 확인.

과거 사고: 공개 facade 의 문서/패널 표면이 빈 데이터/스키마 드리프트로 None 을
리턴 → 후속 .columns 접근에서 AttributeError (외부 venv crash).
"""

from __future__ import annotations

import polars as pl
import pytest


@pytest.mark.realData
@pytest.mark.integration
class TestCompanyFacade:
    """단일 종목 → 모든 공개 진입점이 데이터 반환."""

    def test_corpName_notEmpty(self, samsungRealData):
        assert isinstance(samsungRealData.corpName, str)
        assert samsungRealData.corpName.strip()

    def test_topics_returnsDataFrame(self, samsungRealData):
        """topics 가 None 이면 공개 facade 스키마 드리프트 회귀."""
        topics = samsungRealData.topics
        assert topics is not None, "c.topics 가 None — 공개 facade 빈 결과 회귀"
        assert isinstance(topics, pl.DataFrame)
        assert topics.height > 0
        assert "topic" in topics.columns
        assert "chapter" in topics.columns

    def test_show_IS_hasPeriodColumns(self, samsungRealData):
        isDf = samsungRealData.panel("IS")
        assert isDf is not None
        assert isinstance(isDf, pl.DataFrame)
        periodCols = [c for c in isDf.columns if len(c) >= 4 and c[:4].isdigit()]
        assert periodCols, "IS 기간 컬럼이 하나도 없음 — select() 빈칸 버그 재현"
        # 실제 값이 존재하는지 — 최소 1개 cell non-null
        latest = periodCols[0]
        nonNull = isDf[latest].is_not_null().sum()
        assert nonNull > 0, f"IS {latest} 전부 null — 데이터 빔"

    def test_show_BS_basic(self, samsungRealData):
        bs = samsungRealData.panel("BS")
        assert bs is not None
        assert bs.height > 0

    def test_show_CF_basic(self, samsungRealData):
        cf = samsungRealData.panel("CF")
        assert cf is not None
        assert cf.height > 0

    def test_select_IS_sales_hasValues(self, samsungRealData):
        """select("IS", ["매출액"]) 가 실제 매출 숫자를 돌려주는지."""
        result = samsungRealData.select("IS", ["매출액"])
        assert result is not None
        df = result.df if hasattr(result, "df") else result
        assert df.height >= 1
        periodCols = [c for c in df.columns if len(c) >= 4 and c[:4].isdigit()]
        assert periodCols, "select 결과에 기간 컬럼 없음"
        latest = periodCols[0]
        sales = df[latest][0]
        assert sales is not None
        assert sales > 0

    def test_topics_nonEmpty(self, samsungRealData):
        topics = samsungRealData.topics
        assert topics is not None
        # DataFrame 이든 list 든 최소 1건
        length = len(topics) if hasattr(topics, "__len__") else topics.height
        assert length > 0

    def test_disclosure_callable(self, samsungRealData):
        """disclosure 접근이 크래시 없이 동작 — 결과 None 은 허용."""
        d = samsungRealData.disclosure
        # None 도 OK (공시 조회 실패 가능). 단, AttributeError 등은 안 됨
        assert d is None or hasattr(d, "__class__")
