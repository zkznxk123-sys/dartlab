"""Fresh-install 회귀 — 외부 사용자 첫 호출 시나리오.

========================================
이 파일이 잡는 버그 클래스 (실제 사고 2026-04-19):
========================================
외부 `uv run python -X utf8 main.py` 에서 Company("005930").sections 한 줄이
`AttributeError: 'NoneType' object has no attribute 'columns'` 로 크래시.

원인:
    HF parquet 은 현재 소스 스키마로 생성되지만 PyPI wheel 0.9.15 는
    이전 소스 스냅샷. 구버전 wheel 이 신버전 parquet 에서 row 0 추출 →
    sections() None 리턴 → _SectionsSource.raw is None → .columns 접근 크래시.

    이 테스트는 "sections 가 None 이 아니어야 한다" 는 불변을 PyPI 릴리즈 직전에
    반드시 실행해서, 스키마 드리프트 또는 파이프라인 silent-fail 을 즉시 노출한다.

실행:
    bash scripts/dev/test-lock.sh tests/realData/test_freshInstall.py -m freshInstall -v

주의:
    `freshInstall` 마커가 붙은 테스트는 Phase-1 캐시를 강제로 비우므로
    다른 테스트보다 초기 로딩 시간이 길다. 독립 실행 권장.
"""

from __future__ import annotations

import polars as pl
import pytest

from tests.conftest import SAMSUNG, _has_data


@pytest.fixture
def freshSectionsCache():
    """sections pipeline Phase-1 캐시를 테스트 전후로 모두 비운다.

    `_preparedCache` 가 남아있으면 이전 호출 결과를 재사용해서
    "fresh install 첫 호출" 시나리오가 재현되지 않는다.
    """
    try:
        from dartlab.providers.dart.docs.sections.pipeline import clearPreparedCache

        clearPreparedCache()
        yield
        clearPreparedCache()
    except ImportError:
        yield


@pytest.fixture(scope="class")
def freshScanDataDir(tmp_path_factory):
    """scan 프리빌드 데이터 디렉터리를 빈 경로로 바꿔 첫 호출을 재현한다."""
    import dartlab
    from dartlab.core.dataLoader import _clearLoadCache

    oldDataDir = dartlab.config.dataDir
    dataRoot = tmp_path_factory.mktemp("dartlab-fresh-scan-data")
    dartlab.config.dataDir = str(dataRoot)
    _clearLoadCache()
    try:
        yield dataRoot
    finally:
        _clearLoadCache()
        dartlab.config.dataDir = oldDataDir


def _assertScanFrame(result, name: str, *, minHeight: int = 1) -> pl.DataFrame:
    assert result is not None, f"{name} 결과가 None — fresh install silent fail"
    assert isinstance(result, pl.DataFrame), f"{name} 결과 타입 오류: {type(result).__name__}"
    assert result.height >= minHeight, f"{name} 결과가 너무 작음: {result.height} < {minHeight}"
    return result


@pytest.mark.realData
@pytest.mark.freshInstall
@pytest.mark.integration
class TestFreshInstallSmoke:
    """캐시 없는 상태에서 Company 핵심 속성 접근이 크래시 없이 성공."""

    def test_sectionsNotNone_coldCache(self, freshSectionsCache):
        """c.sections 가 cold cache 에서도 DataFrame — 과거 크래시 직접 재현 방어."""
        if not _has_data(SAMSUNG, "docs"):
            pytest.skip("삼성전자 docs 데이터 없음")
        from dartlab import Company

        c = Company(SAMSUNG)
        # 과거 버그: 이 한 줄에서 AttributeError 크래시
        sec = c.sections
        assert sec is not None, "c.sections 가 None — fresh install 크래시 회귀"
        assert isinstance(sec, pl.DataFrame)
        assert sec.height > 0, "sections DataFrame 이 비어있음 — parquet 파싱 전멸"
        # chapter 컬럼이 있어야 section 구조가 정상
        assert "chapter" in sec.columns
        assert "topic" in sec.columns

    def test_showIS_coldCache(self, freshSectionsCache):
        """c.show("IS") 가 cold cache 에서도 실제 값 반환."""
        if not _has_data(SAMSUNG, "docs"):
            pytest.skip("삼성전자 docs 데이터 없음")
        from dartlab import Company

        c = Company(SAMSUNG)
        isDf = c.show("IS")
        assert isDf is not None
        assert isinstance(isDf, pl.DataFrame)
        assert isDf.height > 0
        periodCols = [col for col in isDf.columns if len(col) >= 4 and col[:4].isdigit()]
        assert periodCols, "IS 기간 컬럼이 없음 — show() 메타 컬럼만 반환하는 회귀"

    def test_selectIS_renderHtml_hasPeriodColumns(self, freshSectionsCache):
        """select("IS").render("html") 이 기간 컬럼을 누락하지 않는지.

        과거 버그: Console(width=120) 고정 때문에 노트북에서 snakeId/항목
        2 컬럼만 렌더되고 기간 60+ 컬럼이 전부 잘려서 사용자가 "값이 안 나온다"
        고 착각.
        """
        if not _has_data(SAMSUNG, "docs"):
            pytest.skip("삼성전자 docs 데이터 없음")
        from dartlab import Company

        c = Company(SAMSUNG)
        result = c.select("IS")
        html = result.render("html") if hasattr(result, "render") else ""
        import re

        periods = re.findall(r"20\d\dQ[1-4]", html)
        assert len(set(periods)) >= 4, f"HTML 렌더에 기간 컬럼이 {len(set(periods))}개 — Rich width 고정 회귀"

    def test_scanAccountSales_coldPrebuild(self, freshScanDataDir):
        """빈 데이터 디렉터리에서 scan("account", "매출액") 첫 호출이 성공해야 한다."""
        import dartlab
        from dartlab.core.memory import MemoryBudgetExceeded

        try:
            result = dartlab.scan("account", "매출액")
        except MemoryBudgetExceeded as e:
            pytest.fail(f"scan('account', '매출액') fresh install 메모리 예산 회귀: {e}")
        df = _assertScanFrame(result, "fresh scan.account.sales", minHeight=1000)
        periodCols = [col for col in df.columns if str(col)[:4].isdigit()]
        assert periodCols, "fresh scan.account.sales 기간 컬럼 없음"

    def test_scanRatioRoe_coldPrebuild(self, freshScanDataDir):
        """빈 데이터 디렉터리에서 scan("ratio", "roe") 첫 호출이 성공해야 한다."""
        import dartlab
        from dartlab.core.memory import MemoryBudgetExceeded

        try:
            result = dartlab.scan("ratio", "roe")
        except MemoryBudgetExceeded as e:
            pytest.fail(f"scan('ratio', 'roe') fresh install 메모리 예산 회귀: {e}")
        df = _assertScanFrame(result, "fresh scan.ratio.roe", minHeight=1000)
        periodCols = [col for col in df.columns if str(col)[:4].isdigit()]
        assert periodCols, "fresh scan.ratio.roe 기간 컬럼 없음"
