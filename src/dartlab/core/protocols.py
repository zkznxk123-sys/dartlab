"""DART/EDGAR Company 공통 Protocol — 구조적 타이핑."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import polars as pl


@runtime_checkable
class CompanyProtocol(Protocol):
    """Company 공통 인터페이스.

    DART Company와 EDGAR Company 모두 이 Protocol을 만족한다.
    """

    corpName: str
    market: str
    currency: str

    @property
    def index(self) -> pl.DataFrame:
        """회사 데이터 구조 인덱스."""
        ...

    @property
    def topics(self) -> pl.DataFrame:
        """사용 가능한 topic 목록."""
        ...

    @property
    def sections(self) -> pl.DataFrame | None:
        """merged topic x period 수평화 테이블."""
        ...

    # Plan v10 P0/P1: c.BS / c.IS / c.CF / c.CIS / c.ratios / c.SCE property 제거.
    # 사용자 진입점은 c.show("IS", freq=, scope=) / c.select(...) 만 (api-contract).

    def show(
        self,
        topic: str,
        block: int | None = None,
        *,
        period: str | list[str] | None = None,
    ) -> pl.DataFrame | None:
        """topic payload 조회."""
        ...

    def select(
        self,
        topic: str,
        indList: str | list[str] | None = None,
        colList: str | list[str] | None = None,
    ) -> Any:  # SelectResult | None
        """topic 데이터에서 행/열을 선택."""
        ...

    def trace(self, topic: str, period: str | None = None) -> dict[str, Any] | None:
        """topic 출처 추적 (docs/finance/report)."""
        ...

    def diff(
        self,
        topic: str | None = None,
        fromPeriod: str | None = None,
        toPeriod: str | None = None,
    ) -> pl.DataFrame | None:
        """기간간 텍스트 변화 감지."""
        ...

    def filings(self) -> pl.DataFrame | None:
        """공시 문서 목록."""
        ...

    def disclosure(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        days: int = 365,
        type: str | None = None,
        keyword: str | None = None,
        finalOnly: bool = False,
    ) -> pl.DataFrame:
        """실시간 공시 검색."""
        ...

    def liveFilings(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        days: int | None = None,
        limit: int = 20,
        keyword: str | None = None,
        forms: list[str] | tuple[str, ...] | None = None,
        finalOnly: bool = False,
    ) -> pl.DataFrame:
        """실시간 공시 목록 (OpenAPI)."""
        ...

    def readFiling(
        self,
        filing: Any,
        *,
        maxChars: int | None = None,
    ) -> dict[str, Any]:
        """공시 원문 읽기."""
        ...

    def view(self, *, port: int = 8400) -> None:
        """웹 뷰어 실행."""
        ...

    def quant(
        self,
        metric: str | None = None,
        **kwargs: Any,
    ) -> dict | pl.DataFrame | None:
        """기술적 분석 (25개 지표 + 종합 판단)."""
        ...

    def ask(
        self,
        question: str,
        *,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        provider: str | None = None,
        model: str | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str | Any:
        """LLM에게 기업 분석 질문."""
        ...


@runtime_checkable
class DocsProtocol(Protocol):
    """docs namespace 공통 인터페이스."""

    @property
    def sections(self) -> pl.DataFrame | None:
        """pure docs 수평화 sections."""
        ...

    def filings(self) -> pl.DataFrame | None:
        """공시 문서 목록."""
        ...


@runtime_checkable
class FinanceProtocol(Protocol):
    """[INTERNAL] finance namespace — 사용자 진입점 아님.

    Plan v10 P3a: 사용자는 ``c.show("IS", freq=, scope=)`` 만 사용한다.
    이 protocol 은 내부 backend interface 로만 의미.
    """

    pass


@runtime_checkable
class ProfileProtocol(Protocol):
    """profile namespace 공통 인터페이스."""

    @property
    def sections(self) -> pl.DataFrame | None:
        """merged canonical company table."""
        ...

    def trace(self, topic: str, period: str | None = None) -> dict[str, Any] | None:
        """topic 출처 추적."""
        ...


# ── F3: L2 분석엔진 데이터 의존성 추상화 (구현은 L1 gather, L1.5 scan) ──


@runtime_checkable
class FinanceDataAccessor(Protocol):
    """analysis 엔진의 재무·가격·매크로 fetch 추상.

    구현체는 gather/accessors.DefaultFinanceAccessor (gather 호출),
    또는 테스트의 mock. caller (story/Company) 가 인스턴스를 L2 에 전달한다.
    """

    def fetchPriceSnapshot(
        self, stockCode: str, *, market: str = "KR", start: str | None = None, end: str | None = None
    ) -> pl.DataFrame | None:
        """OHLCV 스냅샷 fetch."""
        ...

    def fetchMacroSeries(self, seriesId: str, *, source: str = "fred", start: str | None = None) -> pl.DataFrame | None:
        """단일 macro 시계열 fetch."""
        ...

    def fetchExogenousAxes(self, stockCode: str) -> list[tuple[str, str]]:
        """종목별 매크로 축 매핑 (seriesId, label) 리스트."""
        ...

    def fetchAlignedMacro(self, stockCode: str, periods: list[str]) -> pl.DataFrame | None:
        """period 기준 정렬된 매크로 패널."""
        ...

    def lookupCompany(self, stockCode: str) -> "CompanyProtocol | None":
        """종목코드 → CompanyProtocol 인스턴스."""
        ...


@runtime_checkable
class QuantDataAccessor(Protocol):
    """quant 엔진의 OHLCV·factor·indicator fetch 추상."""

    def fetchOhlcv(self, stockCode: str, *, market: str = "KR", start: str | None = None) -> pl.DataFrame | None:
        """단일 종목 OHLCV."""
        ...

    def fetchBenchmarkOhlcv(
        self, stockCode: str, *, market: str = "KR", benchmark: str | None = None
    ) -> tuple[pl.DataFrame | None, dict | None]:
        """벤치마크 OHLCV + meta."""
        ...

    def fetchUniverseBulk(self, stockCodes: list[str], *, columns: list[str]) -> pl.DataFrame | None:
        """다종목 bulk 패널."""
        ...

    def fetchTechnicalIndicators(self, stockCode: str, indicators: list[str]) -> dict[str, pl.DataFrame]:
        """지표 번들."""
        ...


@runtime_checkable
class IndustryDataAccessor(Protocol):
    """industry 엔진의 listing·scan parquet fetch 추상."""

    def fetchListing(self, *, market: str = "KR") -> pl.DataFrame | None:
        """전종목 listing snapshot."""
        ...

    def fetchScanProfitability(self) -> pl.DataFrame | None:
        """scan profitability parquet."""
        ...

    def fetchScanFinanceParquet(self, name: str = "finance") -> pl.DataFrame | None:
        """scan finance parquet (또는 변형)."""
        ...


@runtime_checkable
class MacroDataProvider(Protocol):
    """macro 엔진의 gather·cycle 추상."""

    def getDefaultGather(self) -> Any:
        """현재 기본 GatherEntry 인스턴스."""
        ...

    def applyAsOf(self, dataFrame: pl.DataFrame, asOf: str) -> pl.DataFrame:
        """as-of 필터링."""
        ...

    def fetchSeriesLatest(self, seriesId: str) -> float | None:
        """seriesId 의 최신 값."""
        ...

    def fetchSeriesYoy(self, seriesId: str) -> float | None:
        """seriesId 의 YoY 변화율."""
        ...
