"""Panel — 한 회사 공시 수평화 보드 (그 자체가 pl.DataFrame, callable 로 섹션 검색).

``Panel(code)`` 또는 ``Company(code).panel`` 을 잡는 순간 그 회사의 큰 분기별 시계열 wide
DataFrame 이 된다 (행 = 공시 항목, 열 = period, cell = 본문). ``Panel`` 은 ``pl.DataFrame``
subclass — polars 연산(filter/shape/select…)을 그대로 받는다. ``panel("재고")`` callable 로
섹션명·canonicalKey 매칭 행을 검색한다.

성능·메모리: 로컬 artifact read only (network·lxml import 0, R2). ``tag=True``(기본) 면 build 가
저장한 원본 XML 무손실(R4) — 정부 native 태그(ACODE/ACONTEXT) 보존, AI 이해·strip 생략으로 콜드 경량.
``tag=False`` 면 wide 셀 1회 strip → plain wide(raw 의 ~22%, 사람 표시용 경량). 상태 없는 read —
``c.panel`` 매 접근 새 인스턴스(누적 0, Polars Rust heap OOM 가드). 대형 종목은 ``periods=`` 로 파일 prune.

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
from .period import isPeriodColumn as _isPeriodColumn

# 소스 = 대소문자. 소문자 논리 키 → native(panel 자급 statement). 대문자 → finance(파사드 _showFn).
# 논리 키→물리 XBRL 해소는 cell.STATEMENT_VARIANTS SSOT (회사별 손익 IS1/2/3·연결/별도 변형 흡수).
_NATIVE_KEYS: frozenset[str] = frozenset({"is", "bs", "cf", "cis", "sce"})
# panel freq(입도) → finance freq (대문자 IS 경로). 소스 스위치 아님.
_FINANCE_FREQ: dict[str, str] = {"year": "Y", "quarter": "Q", "ytd": "YTD"}


class Panel(pl.DataFrame):
    """한 회사 공시 수평화 wide — pl.DataFrame subclass, callable 로 섹션 검색.

    Args:
        code: 종목코드 (KR 6자리) 또는 CIK/ticker (US).
        marketNs: 시장 namespace ("kr" / "us", 기본 "kr").
        periods: 특정 period 만 (파일 prune, 대형 종목 메모리 핸들). None = 전체.
        tag: True(기본) 면 원본 XML 무손실(raw, 정부 native 태그 보존), False 면 본문 태그 strip(plain).

    Returns:
        ``Panel`` 인스턴스 = wide pl.DataFrame (행 = 공시 항목, 열 = period). artifact 없으면 빈.

    Raises:
        없음 — artifact 부재 시 빈 DataFrame (예외 없음).

    Example:
        >>> from dartlab.providers.dart.panel import Panel
        >>> p = Panel("005930")              # doctest: +SKIP
        >>> p.shape                          # doctest: +SKIP
        (25, 47)
        >>> inv = p("재고")                  # doctest: +SKIP  — 섹션명/canonicalKey 행 (raw 기본)
        >>> plain = p("재고", tag=False)     # doctest: +SKIP  — 태그 strip plain
        >>> hits = p.search("반도체")        # doctest: +SKIP  — 본문 전체검색

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
        tag: bool = True,
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
            - readWide(tag) 1회 — strip 은 pivot·정렬 후 wide 셀(collapse fragment 보다 2.8x).

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
        key: str | None = None,
        *,
        source: str = "auto",
        tag: bool | None = None,
        periods: list[str] | None = None,
        freq: str | None = None,
    ) -> pl.DataFrame | None:
        """섹션 행 검색 + 강한 소스(finance/report) 주입 — facade 진입점.

        ``source="auto"``(기본): 강한 소스 topic(BS/IS/CF/ratios/inventory/dividend…)은 facade 가
        주입한 ``c.show`` 로 위임(finance/report 가 raw 공시보다 강함). canonicalKey·한글 섹션명은
        raw 공시(panel) 행 검색. ``source="raw"`` 면 강제로 raw 공시만. 주입(``_showFn``/``_strongFn``)은
        ``Company.panel`` facade 가 set — standalone ``Panel(code)`` 는 주입 없어 항상 raw 검색.

        Args:
            key: None(기본) 면 전체 격자. **소스 = 대소문자** — 소문자 5표(is/bs/cf/cis/sce) = native
                재무제표(panel 자급, XBRL+옛 통합 전기간). 대문자 5표(IS/BS/CF/CIS/SCE) = finance(파사드
                _showFn 주입). 소문자 "ratios" = native 재무비율(BS/IS/CF native 항목 → core 공식, 자급),
                대문자 "RATIOS" = finance 비율(파사드). canonicalKey("NT_D826380")·한글 섹션명("재고") = raw
                공시 행 검색.
            source: "auto"(기본) / "raw"(강제 raw 공시) / "finance"/"report"(강제 주입).
            tag: None(기본) 면 인스턴스 tag 상속, 명시하면 그 tag 로 재read(override). raw 검색만 적용.
            periods: None(기본) 면 인스턴스 그대로, 명시하면 그 period 로 재read.
            freq: **입도** — "year"(연)/"quarter"(분기)/"ytd"(누적). native(소문자)·finance(대문자) 둘 다
                받음. 소스 스위치 아님. native 기본 year, finance 는 _FINANCE_FREQ 매핑(Y/Q/YTD).

        Returns:
            소문자 5표 → native 재무제표 wide(항목명×기간). 대문자 5표 → finance wide. key 없으면 전체
            격자. 한글/canonicalKey → 매칭 행. 또는 None (매칭 0 / artifact 없음 / finance 주입 없음).

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
        code = getattr(self, "_code", None)
        effTag = self._tag if tag is None else tag
        # key 미전달(None): tag/periods override 면 전체 격자 재read, 아니면 self (이미 격자).
        if key is None:
            if code is not None and ((tag is not None and effTag != self._tag) or periods is not None):
                return _read.readWide(code, marketNs=self._marketNs, periods=periods or self._periods, tag=effTag)
            return self
        # 명시 빈 key("") → None (하위호환).
        if not key:
            return None
        # native 재무제표 (소문자 논리 키 is/bs/cf/cis/sce) → panel 자급 statement(XBRL+옛 통합, docs 0).
        # 논리 키→물리 해소는 cell.STATEMENT_VARIANTS. freq=입도(year/quarter/ytd), 기본 year. 소스 스위치 아님.
        if key in _NATIVE_KEYS and code is not None:
            from . import cell as _cell

            return _cell.readStatement(
                code,
                statement=key,
                freq=freq or "year",
                marketNs=self._marketNs,
                periods=periods or self._periods,
            )
        # native 재무비율 (소문자 ratios) → panel 자급 (BS/IS/CF native 항목 → core 공식, docs 0).
        # 대문자 RATIOS → finance topic 으로 치환해 아래 strong 블록(파사드 _showFn) 위임. is/IS 와 대칭.
        if key == "ratios" and code is not None:
            from . import cell as _cell

            return _cell.readRatios(
                code,
                freq=freq or "year",
                marketNs=self._marketNs,
                periods=periods or self._periods,
            )
        if key == "RATIOS":
            key = "ratios"
        # 강한 소스(finance/report, 대문자 5표 IS/BS/CF/CIS/SCE 포함) 주입 — facade(Company.panel) _showFn.
        # panel.py 는 finance 를 모름 — 주입된 callable 만 호출(layer 격리, cycle 0). freq 는 finance 입도로 전달.
        if source != "raw":
            showFn = getattr(self, "_showFn", None)
            strongFn = getattr(self, "_strongFn", None)
            if showFn is not None and (source in ("finance", "report") or (strongFn is not None and strongFn(key))):
                if freq is not None:
                    return showFn(key, freq=_FINANCE_FREQ.get(freq, freq))
                return showFn(key)
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

    def search(
        self,
        term: str,
        *,
        tag: bool | None = None,
        periods: list[str] | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame | None:
        """본문 전체검색 — period 열 어디든 term 이 나오는 행 반환 (행이름 검색과 분리).

        ``__call__`` 은 왼쪽 이름표(disclosureKey/sectionLeaf/blockLeaf)로 *아는 행을 고르고*,
        ``search`` 는 *모르는 글자를 본문 셀에서 찾는다* — 의도가 달라 별 메서드. period 값 열
        전체에 substring 매칭(literal). 기본은 self(이미 wide) in-memory 필터, tag/periods override
        시만 readWide 재호출 (raw 기본이면 태그 포함 매칭, plain 이면 텍스트만).

        Args:
            term: 찾을 substring (literal, 정규식 아님).
            tag: None(기본) 면 인스턴스 tag 상속, 명시하면 그 tag 로 재read.
            periods: None(기본) 면 인스턴스 그대로, 명시하면 그 period 로 재read.
            limit: None(기본) 면 전체 매칭, 정수면 상위 N 행만 (head).

        Returns:
            매칭 행 wide DataFrame, 또는 None (빈 term / 매칭 0 / artifact 없음).

        Raises:
            없음.

        Example:
            >>> p = Panel("005930")               # doctest: +SKIP
            >>> p.search("반도체")                # doctest: +SKIP  — 본문에 '반도체' 나오는 행

        SeeAlso:
            - ``__call__`` — 이름표 행 선택 (아는 행).
            - ``period.isPeriodColumn`` — period 열 판별.

        Requires:
            - polars. panel artifact (override 시) 또는 self.

        Capabilities:
            - 행이름이 아닌 본문 내용으로 행 발견 — period 열 전체 substring 스캔.

        Guide:
            - ``p.search("키워드")`` — 어느 섹션인지 몰라도 본문으로 찾기.

        AIContext:
            - 기본 self in-memory 필터(즉시). contentRaw 는 외부 untrusted.

        When:
            - 행이름을 모르고 본문 텍스트로 공시 행을 찾을 때.

        How:
            - period 열 OR ``str.contains(term, literal=True)`` 필터.

        LLM Specifications:
            AntiPatterns:
                - index 컬럼(이름표) 검색 금지 — 그건 ``__call__``. search 는 period 값 열만.
                - 빈 term 에 전체 반환 금지 — None.
            OutputSchema:
                - ``pl.DataFrame | None`` (매칭 행).
            Prerequisites:
                - panel artifact 또는 self.
            Freshness:
                - override 시 재read, 아니면 self 스냅샷.
            Dataflow:
                - term → period 열 substring OR 필터.
            TargetMarkets:
                - KR + US.
        """
        if not term:
            return None
        effTag = self._tag if tag is None else tag
        code = getattr(self, "_code", None)
        if code is not None and ((tag is not None and effTag != self._tag) or periods is not None):
            board: pl.DataFrame | None = _read.readWide(
                code, marketNs=self._marketNs, periods=periods or self._periods, tag=effTag
            )
        else:
            board = self
        if board is None or board.is_empty():
            return None
        periodCols = [c for c in board.columns if _isPeriodColumn(c)]
        if not periodCols:
            return None
        mask = pl.lit(False)
        for c in periodCols:
            mask = mask | pl.col(c).cast(pl.Utf8).str.contains(term, literal=True)
        out = board.filter(mask.fill_null(False))
        if out.is_empty():
            return None
        return out.head(limit) if limit is not None else out
