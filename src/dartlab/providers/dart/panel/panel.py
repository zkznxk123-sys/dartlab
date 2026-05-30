"""Panel facade (L1 read) — DART 공시 수평화 보드 진입점.

``Panel(code)`` 로 한 회사의 panel artifact 를 읽어 회사내 수평화 보드(항목 × period)를
제공한다. 로컬 artifact read only — network·lxml import 0 (R2). 상태 없는 lazy read →
multi-company 루프에서 누적 0 (Polars Rust heap OOM 가드, ``with Panel() as p:`` 권장).

LLM Specifications:
    AntiPatterns:
        - network/외부 API 호출 금지 — 로컬 panel artifact only(R2).
        - per-instance unbounded 캐시 금지 — 상태 없는 read(누적 0).
        - contentRaw 사전 strip 저장 금지 — show(raw=False) 가 runtime on-demand.
    OutputSchema:
        - ``Panel(code).board() -> pl.DataFrame | None`` (presence board).
        - ``Panel(code).show(disclosureKey, ...) -> pl.DataFrame | None`` (한 disclosure wide).
        - ``Panel(code).wide(...) / .long(...) / .periods()``.
    Prerequisites:
        - data/dart/panel/{code}/*.parquet.
    Freshness:
        - 매 호출 read (artifact 변경 즉시 반영).
    Dataflow:
        - Panel(code) → reader/pivot → wide board.
    TargetMarkets:
        - KR (DART). US 는 marketNs="us" (EDGAR panel, 후속).
"""

from __future__ import annotations

import polars as pl

from . import pivot as _pivot
from .reader import readLong, scanPanel


class Panel:
    """한 회사의 panel(공시 수평화) 보드 facade — 로컬 artifact read only.

    Args:
        code: 종목코드 (KR 6자리) 또는 CIK/ticker (US).
        marketNs: 시장 namespace ("kr" / "us", 기본 "kr").

    Returns:
        Panel 인스턴스 (메서드로 board/show/wide/long 제공).

    Raises:
        없음 — artifact 부재 시 메서드가 None 반환.

    Example:
        >>> with Panel("005930") as p:  # doctest: +SKIP
        ...     board = p.board()
        ...     inv = p.show("inventoryDisclosure")

    SeeAlso:
        - ``pivot.readPanelWide`` — 회사내 수평화.
        - ``cross.crossCompany`` — 회사간 정렬.
        - ``reader.readLong`` — long read.

    Requires:
        - polars. panel artifact.

    Capabilities:
        - 한 회사 공시(재무제표·주석·서술)를 항목 × period 보드로 — 콜드 <1s, 태그 무손실.

    Guide:
        - ``with Panel(code) as p:`` 로 multi-company 루프 (누적 0). 단건은 직접 사용.

    AIContext:
        - 상태 없는 lazy read — 외부 본문은 untrusted(soruceType external 마커는 ai 층).

    LLM Specifications:
        AntiPatterns:
            - network 호출 금지(R2). per-instance unbounded cache 금지.
        OutputSchema:
            - 메서드별 ``pl.DataFrame | None`` / ``list[str]``.
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 호출 read.
        Dataflow:
            - Panel(code) → reader/pivot.
        TargetMarkets:
            - KR + US.
    """

    def __init__(self, code: str, *, marketNs: str = "kr") -> None:
        self.code = code
        self.marketNs = marketNs

    def __enter__(self) -> "Panel":
        """context 진입 — Panel 반환.

        Args:
            없음.

        Returns:
            self.

        Raises:
            없음.

        Example:
            >>> with Panel("005930") as p:  # doctest: +SKIP
            ...     pass

        SeeAlso:
            - ``__exit__`` — context 종료.

        Requires:
            - 없음.

        Capabilities:
            - ``with`` 블록 — multi-company 루프 누적 0 패턴.

        Guide:
            - ``with Panel(code) as p:``.

        AIContext:
            - 상태 없음 — 진입 부작용 0.

        LLM Specifications:
            AntiPatterns:
                - 없음.
            OutputSchema:
                - ``Panel``.
            Prerequisites:
                - 없음.
            Freshness:
                - N/A.
            Dataflow:
                - self 반환.
            TargetMarkets:
                - KR + US.
        """
        return self

    def __exit__(self, *exc) -> bool:
        """context 종료 — 상태 없어 정리 0 (예외 비흡수).

        Args:
            *exc: 예외 정보 (type, value, tb).

        Returns:
            False (예외 전파).

        Raises:
            없음.

        Example:
            >>> with Panel("005930"):  # doctest: +SKIP
            ...     pass

        SeeAlso:
            - ``__enter__``.

        Requires:
            - 없음.

        Capabilities:
            - 상태 없는 reader → 정리 불필요(누적 0).

        Guide:
            - 자동 호출.

        AIContext:
            - 예외 비흡수(False).

        LLM Specifications:
            AntiPatterns:
                - 예외 흡수(True 반환) 금지.
            OutputSchema:
                - ``bool`` (False).
            Prerequisites:
                - 없음.
            Freshness:
                - N/A.
            Dataflow:
                - no-op.
            TargetMarkets:
                - KR + US.
        """
        return False

    def board(self, *, periods: list[str] | None = None) -> pl.DataFrame | None:
        """presence board — 어떤 disclosure 가 어느 기간에 있는지 (콜드 <1s, contentRaw 제외).

        Args:
            periods: 특정 period 만. None = 전체.

        Returns:
            blockOrder presence board (항목 × period) 또는 None.

        Raises:
            없음.

        Example:
            >>> Panel("005930").board()  # doctest: +SKIP

        SeeAlso:
            - ``pivot.readMeta`` — 구현.
            - ``show`` — 한 disclosure 본문.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 회사 공시 구조 한눈에 — 본문 디코드 0(<1MB).

        Guide:
            - 첫 진입 overview. 본문은 show 로.

        AIContext:
            - cheap board — presence 만.

        LLM Specifications:
            AntiPatterns:
                - contentRaw 포함 금지.
            OutputSchema:
                - ``pl.DataFrame | None``.
            Prerequisites:
                - panel artifact.
            Freshness:
                - 매 호출.
            Dataflow:
                - readMeta(code).
            TargetMarkets:
                - KR + US.
        """
        return _pivot.readMeta(self.code, marketNs=self.marketNs, periods=periods)

    def wide(self, *, periods: list[str] | None = None, valueColumn: str = "contentRaw") -> pl.DataFrame | None:
        """전체 회사내 수평화 wide (항목 × period, cell=contentRaw).

        Args:
            periods: 특정 period 만. None = 전체.
            valueColumn: cell 값 컬럼 (기본 contentRaw).

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> Panel("005930").wide()  # doctest: +SKIP

        SeeAlso:
            - ``pivot.readPanelWide`` — 구현.
            - ``show`` — 한 disclosure 필터.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 회사 전 disclosure 다기간 수평화(G2).

        Guide:
            - 전체 보드 필요 시. 단일 항목은 show.

        AIContext:
            - contentRaw join(무손실), anchorLatest 정렬.

        LLM Specifications:
            AntiPatterns:
                - 없음.
            OutputSchema:
                - ``pl.DataFrame | None``.
            Prerequisites:
                - panel artifact.
            Freshness:
                - 매 호출.
            Dataflow:
                - readPanelWide(code).
            TargetMarkets:
                - KR + US.
        """
        return _pivot.readPanelWide(self.code, marketNs=self.marketNs, periods=periods, valueColumn=valueColumn)

    def show(self, disclosureKey: str, *, periods: list[str] | None = None) -> pl.DataFrame | None:
        """한 disclosure 의 다기간 수평화 (해당 disclosureKey 행만).

        Args:
            disclosureKey: universal disclosureKey (예: "inventoryDisclosure").
            periods: 특정 period 만. None = 전체.

        Returns:
            해당 disclosure 의 wide DataFrame (period 가로 정렬) 또는 None.

        Raises:
            없음.

        Example:
            >>> Panel("005930").show("inventoryDisclosure")  # doctest: +SKIP

        SeeAlso:
            - ``wide`` — 전체.
            - ``cross.crossCompany`` — 회사간 동일 disclosure.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 재무제표·주석을 동일 호출로 — disclosureKey 로 기간 가로 정렬.

        Guide:
            - board 에서 키 확인 후 show(key).

        AIContext:
            - disclosureKey 필터 후 wide — 태그 무손실(raw).

        When:
            - 한 disclosure 의 다기간 본문을 볼 때.

        How:
            - readPanelWide → filter(disclosureKey == key).

        LLM Specifications:
            AntiPatterns:
                - disclosureKey null 행 반환 금지 — 지정 키만.
            OutputSchema:
                - ``pl.DataFrame | None``.
            Prerequisites:
                - panel artifact + disclosureKey.
            Freshness:
                - 매 호출.
            Dataflow:
                - readPanelWide → filter(disclosureKey == key).
            TargetMarkets:
                - KR + US.
        """
        wide = _pivot.readPanelWide(self.code, marketNs=self.marketNs, periods=periods)
        if wide is None or "disclosureKey" not in wide.columns:
            return None
        out = wide.filter(pl.col("disclosureKey") == disclosureKey)
        return out if not out.is_empty() else None

    def long(self, *, periods: list[str] | None = None) -> pl.DataFrame | None:
        """raw long read (14-col + disclosureKey, 수평화 전).

        Args:
            periods: 특정 period 만. None = 전체.

        Returns:
            long DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> Panel("005930").long()  # doctest: +SKIP

        SeeAlso:
            - ``reader.readLong`` — 구현.
            - ``wide`` — 수평화.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 수평화 전 원본 long (디버그·커스텀 집계).

        Guide:
            - 일반 사용은 board/show/wide. long 은 raw.

        AIContext:
            - build 산출 그대로.

        LLM Specifications:
            AntiPatterns:
                - 없음.
            OutputSchema:
                - ``pl.DataFrame | None``.
            Prerequisites:
                - panel artifact.
            Freshness:
                - 매 호출.
            Dataflow:
                - readLong(code).
            TargetMarkets:
                - KR + US.
        """
        return readLong(self.code, marketNs=self.marketNs, periods=periods)

    def periods(self) -> list[str]:
        """사용 가능한 period 목록 (정렬).

        Args:
            없음.

        Returns:
            "YYYYQn" period 문자열 list (오름차순). artifact 없으면 빈 list.

        Raises:
            없음.

        Example:
            >>> Panel("005930").periods()  # doctest: +SKIP
            ['2015Q4', ..., '2026Q1']

        SeeAlso:
            - ``reader.scanPanel`` — period 파일 스캔.
            - ``core.panel.sortPeriods`` — 정렬.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 회사 가용 기간 조회 — board/show periods 인자 결정.

        Guide:
            - period 선택 전 호출.

        AIContext:
            - scan only — 본문 read 0.

        When:
            - 회사 가용 기간을 조회해 periods 인자를 정할 때.

        How:
            - scanPanel → period unique → sortPeriods.

        LLM Specifications:
            AntiPatterns:
                - 본문 read 금지 — period 컬럼 unique 만.
            OutputSchema:
                - ``list[str]`` (정렬).
            Prerequisites:
                - panel artifact.
            Freshness:
                - 매 호출.
            Dataflow:
                - scanPanel → period unique → sortPeriods.
            TargetMarkets:
                - KR + US.
        """
        from dartlab.core.panel import sortPeriods

        lf = scanPanel(self.code, marketNs=self.marketNs)
        if lf is None:
            return []
        vals = lf.select("period").unique().collect()["period"].to_list()
        return sortPeriods([v for v in vals if v])
