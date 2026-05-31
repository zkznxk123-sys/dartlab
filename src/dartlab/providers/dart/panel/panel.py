"""Panel — 한 회사 공시 수평화 보드 (그 자체가 pl.DataFrame, callable 로 섹션 검색).

``Panel(code)`` 또는 ``Company(code).panel`` 을 잡는 순간 그 회사의 큰 분기별 시계열 wide
DataFrame 이 된다 (행 = 공시 항목, 열 = period, cell = 본문). ``Panel`` 은 ``pl.DataFrame``
subclass — polars 연산(filter/shape/select…)을 그대로 받는다. ``panel("재고")`` callable 로
섹션명·canonicalKey 매칭 행을 검색한다.

성능·메모리: 로컬 artifact read only (network·lxml import 0, R2). ``tag=False``(기본) 면 build 가
저장한 raw XML 을 collapse 단계에서 1회 strip → plain wide(raw 의 ~22%, 표시·메모리 경량).
``tag=True`` 면 원본 XML 무손실(R4). 상태 없는 read — ``c.panel`` 매 접근 새 인스턴스(누적 0,
Polars Rust heap OOM 가드). 대형 종목은 ``periods=`` 로 파일 prune.

LLM Specifications:
    AntiPatterns:
        - network/외부 API 호출 금지 — 로컬 panel artifact only(R2).
        - per-instance unbounded 캐시 금지 — 상태 없는 read(누적 0).
        - tag=False 결과를 raw 로 가정 금지 — plain(태그 제거). raw 는 tag=True.
        - 큰 wide 를 인스턴스에 보관 후 다종목 루프 금지 — 매 회사 새 Panel + GC.
    OutputSchema:
        - ``Panel(code, *, marketNs, periods, tag)`` → pl.DataFrame subclass (wide).
        - ``Panel(code)(key, *, tag, periods) -> pl.DataFrame | None`` (매칭 행).
    Prerequisites:
        - data/{dart|edgar}/panel/{code}/*.parquet (build 결과).
    Freshness:
        - 매 생성 read (artifact 변경 즉시 반영).
    Dataflow:
        - Panel(code) → read.readWide → wide. Panel(code)(key) → in-memory 행 필터.
    TargetMarkets:
        - KR (DART). US 는 marketNs="us" (EDGAR panel).
"""

from __future__ import annotations

import polars as pl

from . import read as _read


class Panel(pl.DataFrame):
    """한 회사 공시 수평화 wide — pl.DataFrame subclass, callable 로 섹션 검색.

    Args:
        code: 종목코드 (KR 6자리) 또는 CIK/ticker (US).
        marketNs: 시장 namespace ("kr" / "us", 기본 "kr").
        periods: 특정 period 만 (파일 prune, 대형 종목 메모리 핸들). None = 전체.
        tag: False(기본) 면 본문 태그 strip(plain), True 면 원본 XML 무손실(raw).

    Returns:
        ``Panel`` 인스턴스 = wide pl.DataFrame (행 = 공시 항목, 열 = period). artifact 없으면 빈.

    Raises:
        없음 — artifact 부재 시 빈 DataFrame (예외 없음).

    Example:
        >>> from dartlab.providers.dart.panel import Panel
        >>> p = Panel("005930")              # doctest: +SKIP
        >>> p.shape                          # doctest: +SKIP
        (25, 47)
        >>> inv = p("재고")                  # doctest: +SKIP  — 섹션명/canonicalKey 행
        >>> raw = p("재고", tag=True)        # doctest: +SKIP  — 원본 XML

    SeeAlso:
        - ``read.readWide`` — wide 수평화 구현.
        - ``providers.dart.company.Company.panel`` — facade 진입점 (finance/report 주입).

    Requires:
        - polars. panel artifact.

    Capabilities:
        - 한 회사 공시(재무제표·주석·서술)를 항목 × period wide 로 — 잡는 순간 DataFrame.
        - callable 로 섹션명/canonicalKey 행 검색 — 별도 verb 없이 호출.
        - tag 로 plain(기본)/raw 전환 — 무손실 저장, 표시 경량.

    Guide:
        - ``p = Panel(code)`` → 그대로 polars 연산. ``p("재고")`` → 행 검색. 다종목은 매 회사 새 Panel.

    AIContext:
        - 상태 없는 lazy read — 외부 본문(contentRaw)은 untrusted(ai 층이 마커로 감쌈).

    When:
        - 한 회사 공시를 다기간 wide 로 보거나 특정 섹션 행을 검색할 때.

    How:
        - __init__: readWide(code, tag) → super().__init__(wide). __call__: in-memory 행 필터.

    LLM Specifications:
        AntiPatterns:
            - network 호출 금지(R2). per-instance unbounded cache 금지(누적 0).
            - tag=False 를 raw 로 가정 금지 — plain.
        OutputSchema:
            - pl.DataFrame subclass (wide) / ``__call__`` → ``pl.DataFrame | None``.
        Prerequisites:
            - panel artifact.
        Freshness:
            - 매 생성 read.
        Dataflow:
            - Panel(code) → readWide → wide. (key) → 행 필터.
        TargetMarkets:
            - KR + US.
    """

    def __init__(
        self,
        code: str,
        *,
        marketNs: str = "kr",
        periods: list[str] | None = None,
        tag: bool = False,
    ) -> None:
        """code → wide read 후 pl.DataFrame 초기화 + 검색용 메타 보관.

        Args:
            code: 종목코드 (KR 6자리) 또는 CIK/ticker (US).
            marketNs: 시장 namespace ("kr" / "us").
            periods: 특정 period 만 (파일 prune). None = 전체.
            tag: False(기본) plain / True raw XML.

        Returns:
            None (생성자). self 가 wide pl.DataFrame.

        Raises:
            없음 — artifact 부재 시 빈 DataFrame.

        Example:
            >>> Panel("005930", tag=True).is_empty()  # doctest: +SKIP
            False

        SeeAlso:
            - ``read.readWide`` — wide 생성.
            - ``__call__`` — 행 검색.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 잡는 순간 wide — readWide 결과를 DataFrame 본체로 채택, 검색 메타(code/tag) 보관.

        Guide:
            - 직접 또는 facade(c.panel) 경유 생성. 다종목은 매 회사 새 인스턴스.

        AIContext:
            - readWide(tag) 1회 — raw wide 2중 materialize 회피(strip 은 collapse 단계).

        LLM Specifications:
            AntiPatterns:
                - super().__init__ 우회(_df 직접 대입) 금지 — polars 정식 경로.
            OutputSchema:
                - None (self = wide).
            Prerequisites:
                - panel artifact.
            Freshness:
                - 매 생성 read.
            Dataflow:
                - readWide(code, marketNs, periods, tag) → super().__init__.
            TargetMarkets:
                - KR + US.
        """
        wide = _read.readWide(code, marketNs=marketNs, periods=periods, tag=tag)
        super().__init__(wide if wide is not None else pl.DataFrame())
        self._code = code
        self._marketNs = marketNs
        self._periods = periods
        self._tag = tag

    def __call__(
        self,
        key: str,
        *,
        source: str = "auto",
        tag: bool | None = None,
        periods: list[str] | None = None,
    ) -> pl.DataFrame | None:
        """섹션 행 검색 + 강한 소스(finance/report) 주입 — facade 진입점.

        ``source="auto"``(기본): 강한 소스 topic(BS/IS/CF/ratios/inventory/dividend…)은 facade 가
        주입한 ``c.show`` 로 위임(finance/report 가 raw 공시보다 강함). canonicalKey·한글 섹션명은
        raw 공시(panel) 행 검색. ``source="raw"`` 면 강제로 raw 공시만. 주입(``_showFn``/``_strongFn``)은
        ``Company.panel`` facade 가 set — standalone ``Panel(code)`` 는 주입 없어 항상 raw 검색.

        Args:
            key: canonicalKey("NT_D826380"/"BS") 또는 한글 섹션명("재고"), 또는 강한 소스 topic("IS").
            source: "auto"(기본, 강한 소스는 show 주입) / "raw"(강제 raw 공시) / "finance"/"report"(강제 주입).
            tag: None(기본) 면 인스턴스 tag 상속, 명시하면 그 tag 로 재read(override). raw 검색만 적용.
            periods: None(기본) 면 인스턴스 그대로, 명시하면 그 period 로 재read. raw 검색만 적용.

        Returns:
            매칭 행 wide DataFrame (period 가로 정렬) 또는 None (빈 key / 매칭 0 / artifact 없음).

        Raises:
            없음.

        Example:
            >>> p = Panel("005930")               # doctest: +SKIP
            >>> p("재고")                         # doctest: +SKIP  — sectionLeaf/blockLeaf substring
            >>> p("NT_D826380")                   # doctest: +SKIP  — canonicalKey exact
            >>> p("재고", tag=True)               # doctest: +SKIP  — 원본 XML 행

        SeeAlso:
            - ``read.readWide`` — tag/periods override 시 재read.
            - ``Panel`` — 본 callable 의 wide 본체.

        Requires:
            - polars. panel artifact.

        Capabilities:
            - 별도 verb 없이 호출로 섹션 행 검색 — canonicalKey exact + 섹션명 substring(라벨 테이블 0).

        Guide:
            - board 없이 바로 ``p("재고")``. 원본 태그는 ``p("재고", tag=True)``.

        AIContext:
            - 기본은 self(이미 wide) in-memory 필터(즉시). tag/periods override 시만 readWide 재호출.

        When:
            - 한 공시 섹션의 다기간 행을 검색할 때.

        How:
            - (override 시 readWide) → disclosureKey==key | sectionLeaf/blockLeaf.contains(key) 필터.

        LLM Specifications:
            AntiPatterns:
                - _label.parquet 검색 테이블 의존 금지 — wide 행 식별 컬럼 in-memory 필터.
                - 빈 key 에 전체 반환 금지 — None.
            OutputSchema:
                - ``pl.DataFrame | None`` (매칭 행).
            Prerequisites:
                - panel artifact (override 시) 또는 self(이미 wide).
            Freshness:
                - override 시 재read, 아니면 self 스냅샷.
            Dataflow:
                - key → (disclosureKey exact | sectionLeaf/blockLeaf substring) 필터.
            TargetMarkets:
                - KR + US.
        """
        if not key:
            return None
        # 강한 소스(finance/report/notes) 주입 — facade(Company.panel)가 _showFn/_strongFn 주입 시.
        # panel.py 는 finance 를 모름 — 주입된 callable 만 호출(layer 격리, cycle 0).
        if source != "raw":
            showFn = getattr(self, "_showFn", None)
            strongFn = getattr(self, "_strongFn", None)
            if showFn is not None and (source in ("finance", "report") or (strongFn is not None and strongFn(key))):
                return showFn(key)
        effTag = self._tag if tag is None else tag
        code = getattr(self, "_code", None)
        # tag/periods override + code 보유(fresh 인스턴스) 시 재read, 그 외 self 필터.
        if code is not None and ((tag is not None and effTag != self._tag) or periods is not None):
            board: pl.DataFrame | None = _read.readWide(
                code, marketNs=self._marketNs, periods=periods or self._periods, tag=effTag
            )
        else:
            board = self
        if board is None or board.is_empty():
            return None
        cols = [c for c in ("disclosureKey", "sectionLeaf", "blockLeaf") if c in board.columns]
        if not cols:
            return None
        mask = pl.lit(False)
        for c in cols:
            colExpr = pl.col(c)
            mask = mask | (colExpr == key) | colExpr.str.contains(key, literal=True)
        out = board.filter(mask)
        return out if not out.is_empty() else None
