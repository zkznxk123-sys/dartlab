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

    @property
    def BS(self) -> pl.DataFrame | None:
        """재무상태표 (stock — 시점잔액).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점:
                - DART ``{year}Q{n}``: 분기 컬럼 + ``{year}`` 연간 alias (= Q4 = 연말잔액)
                - EDGAR ``{year}``: fiscal year-end 연말잔액
            null: 데이터 없음 (진짜 0 과 구분 불가)
            컬럼: snakeId, 계정명, 분기 컬럼(역순), 연간 컬럼(역순)
        """
        ...

    @property
    def IS(self) -> pl.DataFrame | None:
        """손익계산서 (flow — 매출/이익 흐름).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점:
                - DART ``{year}Q{n}``: 분기 단독값 (예: 2025Q4 = Q4 한 분기)
                - DART ``{year}``: 그 해 연간 합 (= Q1+Q2+Q3+Q4)
                - EDGAR ``{year}``: fiscal year 합 (회사별 결산일)
            null: 데이터 없음
            컬럼: snakeId, 계정명, 분기 컬럼(역순), 연간 컬럼(역순)

        Note:
            calc 함수는 ``row['2025']`` 직접 read 권장 (분기 합산 헬퍼 우회).
            ``row['2025Q4']`` 는 Q4 단독값이며 연간값이 아님.
        """
        ...

    @property
    def CF(self) -> pl.DataFrame | None:
        """현금흐름표 (flow — 영업/투자/재무 활동).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점: IS 와 동일 — 분기 컬럼은 단독값, 연간 컬럼은 합
            null: 데이터 없음

        Note:
            DART raw CF 는 누적 형태이지만 ``pivot.py::_normalizeQ4`` 가
            standalone 분기로 변환. 위층은 분기/연간 컬럼 의미만 알면 됨.
        """
        ...

    @property
    def CIS(self) -> pl.DataFrame | None:
        """포괄손익계산서 (flow — 기타포괄손익 포함).

        데이터 계약:
            단위/시점/null: IS 와 동일
        """
        ...

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

    def chat(
        self,
        question: str,
        *,
        provider: str | None = None,
        model: str | None = None,
        max_turns: int = 5,
        **kwargs: Any,
    ) -> str:
        """에이전트 모드 대화형 분석."""
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
    """finance namespace 공통 인터페이스."""

    @property
    def BS(self) -> pl.DataFrame | None:
        """재무상태표 (stock — 시점잔액).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점:
                - DART ``{year}Q{n}``: 분기 컬럼 + ``{year}`` 연간 alias (= Q4 = 연말잔액)
                - EDGAR ``{year}``: fiscal year-end 연말잔액
            null: 데이터 없음 (진짜 0 과 구분 불가)
            컬럼: snakeId, 계정명, 분기 컬럼(역순), 연간 컬럼(역순)
        """
        ...

    @property
    def IS(self) -> pl.DataFrame | None:
        """손익계산서 (flow — 매출/이익 흐름).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점:
                - DART ``{year}Q{n}``: 분기 단독값 (예: 2025Q4 = Q4 한 분기)
                - DART ``{year}``: 그 해 연간 합 (= Q1+Q2+Q3+Q4)
                - EDGAR ``{year}``: fiscal year 합 (회사별 결산일)
            null: 데이터 없음
            컬럼: snakeId, 계정명, 분기 컬럼(역순), 연간 컬럼(역순)

        Note:
            calc 함수는 ``row['2025']`` 직접 read 권장 (분기 합산 헬퍼 우회).
            ``row['2025Q4']`` 는 Q4 단독값이며 연간값이 아님.
        """
        ...

    @property
    def CF(self) -> pl.DataFrame | None:
        """현금흐름표 (flow — 영업/투자/재무 활동).

        데이터 계약:
            단위: KRW 원 (DART) / USD raw (EDGAR)
            시점: IS 와 동일 — 분기 컬럼은 단독값, 연간 컬럼은 합
            null: 데이터 없음

        Note:
            DART raw CF 는 누적 형태이지만 ``pivot.py::_normalizeQ4`` 가
            standalone 분기로 변환. 위층은 분기/연간 컬럼 의미만 알면 됨.
        """
        ...

    @property
    def CIS(self) -> pl.DataFrame | None:
        """포괄손익계산서 (flow — 기타포괄손익 포함).

        데이터 계약:
            단위/시점/null: IS 와 동일
        """
        ...

    @property
    def ratios(self) -> Any:
        """재무비율."""
        ...


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
