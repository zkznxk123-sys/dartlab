"""providersV2 DART Company — read facade (역할 1: 로컬 artifact read).

3 역할 중 역할 1 (read) 구현. show(topic) 가 ``classify`` 로 finance / report /
sections 분기. 네트워크·write·상위 엔진 import 0.
    - 역할 2 (네트워크: liveFilings/update/readFiling) → gather 위임 (Phase 7
      openapi→gather 이동 후 실구현).
    - 역할 3 (엔진: analysis/story/credit/quant/...) → core 레지스트리 IoC
      (Phase 4 후속).

LLM Specifications:
    AntiPatterns:
        - 네트워크/외부 API 호출 금지 — read facade 는 로컬 parquet 만.
        - 상위 엔진(analysis/quant/...) 정적·lazy import 금지 — 레지스트리 IoC.
        - show topic 을 옛 docs/finance 런타임 파서로 dispatch 금지 — classify →
          finance 정규화 / report / sections contentRaw.
    OutputSchema:
        - ``Company(stockCode)`` · ``.show(topic) -> pl.DataFrame | None`` ·
          ``.sections -> pl.DataFrame | None``.
    Prerequisites:
        - data/dart/sections|finance|report parquet (gather build/collect 산출).
    Dataflow:
        - topic → classify → (finance buildTimeseries | report extractClean |
          sections readSectionsWide) → wide DataFrame.
    TargetMarkets:
        - KR (DART). EDGAR 는 edgar/company.py.
"""

from __future__ import annotations

import difflib

import polars as pl

from dartlab.core.dualAccess import CallableAccessor

from .finance import AccountMapper, buildTimeseries
from .report import API_TYPE_LABELS, API_TYPES, extractClean
from .sections import readSectionsMeta, readSectionsWide

# finance 재무제표 statement 별칭 → buildTimeseries series 키 (BS/IS/CF).
_FINANCE_ALIASES: dict[str, str] = {
    "BS": "BS",
    "재무상태표": "BS",
    "대차대조표": "BS",
    "balanceSheet": "BS",
    "IS": "IS",
    "손익계산서": "IS",
    "incomeStatement": "IS",
    "CF": "CF",
    "현금흐름표": "CF",
    "cashFlow": "CF",
    "cashFlowStatement": "CF",
}

# report apiType 역인덱스 (한글 라벨 → apiType).
_REPORT_LABEL_TO_TYPE: dict[str, str] = {v: k for k, v in API_TYPE_LABELS.items()}


def classify(topic: str) -> tuple[str, str]:
    """topic → (kind, resolved) — show dispatch 분기 결정.

    Args:
        topic: 사용자 topic (예: "BS" / "재무상태표" / "dividend" / "배당" /
            "inventoryDisclosure").

    Returns:
        ``(kind, resolved)`` — kind ∈ {"finance", "report", "sections"}.
            finance → resolved = "BS"/"IS"/"CF". report → resolved = apiType.
            sections → resolved = topic 그대로 (disclosureKey 후보).

    Examples:
        >>> classify("재무상태표")
        ('finance', 'BS')
        >>> classify("배당")
        ('report', 'dividend')
        >>> classify("inventoryDisclosure")
        ('sections', 'inventoryDisclosure')

    LLM Specifications:
        AntiPatterns:
            - 미상 topic 을 finance/report 로 강제 금지 — 기본 sections (narrative).
            - 옛 _MODULE_REGISTRY(docs/finance 파서) 경로 금지.
        OutputSchema:
            - ``tuple[str, str]`` (kind, resolved).
        Prerequisites:
            - report API_TYPES / API_TYPE_LABELS.
        TargetMarkets:
            - KR.
    """
    if topic in _FINANCE_ALIASES:
        return ("finance", _FINANCE_ALIASES[topic])
    if topic in API_TYPES:
        return ("report", topic)
    if topic in _REPORT_LABEL_TO_TYPE:
        return ("report", _REPORT_LABEL_TO_TYPE[topic])
    return ("sections", topic)


class Company:
    """DART 종목 read facade — sections/finance/report 통합 조회.

    Capabilities:
        - ``show(topic)`` classify dispatch (finance 정규화 / report / sections).
        - ``sections`` 수평화 보드 (meta, contentRaw 제외 경량).
        - 로컬 artifact only — 네트워크·write 0.

    Args:
        stockCode: 6 자리 종목코드 (예: ``"005930"``).

    Returns:
        Company 인스턴스.

    Raises:
        없음 (데이터 부재 시 메서드가 None 반환).

    Example:
        >>> c = Company("005930")
        >>> c.show("BS")          # doctest: +SKIP
        >>> c.show("배당")        # doctest: +SKIP
        >>> c.show("inventoryDisclosure")  # doctest: +SKIP

    Guide:
        - 재무제표 → ``show("BS"/"IS"/"CF")``.
        - 정형 공시(배당·임원 등) → ``show("dividend")`` 등 apiType.
        - 주석·서술 → ``show(disclosureKey)`` (sections contentRaw).

    SeeAlso:
        - ``classify`` — dispatch 분기 결정.
        - ``dartlab.gather.dart.sections.build`` — sections 생산(BUILD).

    Requires:
        - dartlab
        - polars

    AIContext:
        read facade 진입 — 네트워크·엔진 위임은 후속 phase. 본체는 로컬 read.
    """

    market = "KR"
    currency = "KRW"

    def __init__(self, stockCode: str) -> None:
        self.stockCode = str(stockCode).strip()
        self._cache: dict = {}

    def __repr__(self) -> str:
        return f"Company({self.stockCode!r}, market={self.market})"

    @property
    def sections(self) -> pl.DataFrame | None:
        """sections 수평화 보드 (meta presence, contentRaw 제외 경량).

        Returns:
            wide meta DataFrame (canonical 행 × period, cell=blockOrder presence)
            또는 None (artifact 부재).

        Raises:
            없음.

        Example:
            >>> Company("005930").sections  # doctest: +SKIP

        SeeAlso:
            - ``show`` — 특정 topic 의 contentRaw 조회.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - sections artifact 의 구조 보드 — 어떤 disclosure 가 어느 기간에
              있는지. contentRaw 디코드 0 (footprint <1MB).

        AIContext:
            토픽 discovery 진입 — 행 = canonical key (disclosureKey/scope/제목).
        """
        return readSectionsMeta(self.stockCode)

    @property
    def show(self) -> CallableAccessor:
        """topic 보드 dual-access — ``c.show("BS")`` = ``c.show.BS()``.

        Returns:
            CallableAccessor — call/attribute 양형. 실 dispatch 는 ``_showImpl``.

        Raises:
            없음.

        Example:
            >>> Company("005930").show("BS")   # doctest: +SKIP
            >>> Company("005930").show.BS()    # doctest: +SKIP

        SeeAlso:
            - ``_showImpl`` — classify dispatch 실구현.
            - ``index`` — 가용 topic 카탈로그.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - dual-access proxy (옛 dart facade api-contract 동일). topic 을 인자
              또는 attribute 로 (``c.show.dividend()``).

        AIContext:
            단일 read 진입 — attribute 형도 동일 classify dispatch.
        """
        if "_show" not in self._cache:
            self._cache["_show"] = CallableAccessor(self._showImpl, name="show")
        return self._cache["_show"]

    def _showImpl(
        self,
        topic: str,
        *,
        periods: list[str] | None = None,
        scope: str = "consolidated",
        raw: bool = False,
    ) -> pl.DataFrame | None:
        """topic 보드 조회 (실 dispatch) — classify 로 finance/report/sections 분기.

        Capabilities:
            - 재무제표(BS/IS/CF) → finance 정규화 wide (label 행 × period 열, 정렬).
            - 정형 공시(apiType) → report extractClean.
            - 주석·서술(disclosureKey) → sections contentRaw wide (최신앵커 정렬).

        Args:
            topic: 조회 대상 (재무제표/apiType/disclosureKey).
            periods: 특정 period 만 (sections/finance). None = 전체.
            scope: "consolidated"(연결) / "standalone"(별도). finance·sections.
            raw: sections contentRaw 태그 보존 여부 (False=태그 strip).

        Returns:
            wide ``pl.DataFrame`` 또는 None.

        Raises:
            없음.

        Example:
            >>> Company("005930").show("BS")  # doctest: +SKIP

        SeeAlso:
            - ``classify`` — dispatch 결정.
            - ``sections`` — 전체 보드.

        Requires:
            - dartlab
            - polars

        AIContext:
            단일 진입 read — 옛 select 흡수(periods 필터). 행 fuzzy 필터는 후속.
        """
        kind, resolved = classify(topic)
        if kind == "finance":
            return self._financeWide(resolved, scope)
        if kind == "report":
            return extractClean(self.stockCode, resolved)
        return self._sectionsShow(resolved, periods=periods, scope=scope, raw=raw)

    def _financeWide(self, stmt: str, scope: str) -> pl.DataFrame | None:
        """buildTimeseries → label 행 × period 열 wide (sortOrder 정렬).

        Args:
            stmt: "BS" / "IS" / "CF".
            scope: "consolidated" → CFS / "standalone" → OFS.

        Returns:
            wide DataFrame (account 열 + period 열) 또는 None.
        """
        pref = "OFS" if scope.startswith("stand") or scope.startswith("별도") else "CFS"
        res = buildTimeseries(self.stockCode, fsDivPref=pref)
        if res is None:
            return None
        series, periods = res
        block = series.get(stmt)
        if not block:
            return None
        mapper = AccountMapper.get()
        labels = mapper.labelMap()
        order = mapper.sortOrder(stmt)
        rows: list[dict] = []
        for snakeId, vals in block.items():
            row: dict = {
                "account": labels.get(snakeId, snakeId),
                "_ord": order.get(snakeId, 9999),
            }
            row.update({p: v for p, v in zip(periods, vals)})
            rows.append(row)
        if not rows:
            return None
        return pl.DataFrame(rows).sort("_ord").drop("_ord")

    def _sectionsShow(
        self,
        disclosureKey: str,
        *,
        periods: list[str] | None,
        scope: str,
        raw: bool,
    ) -> pl.DataFrame | None:
        """sections wide 에서 disclosureKey(+scope) 행 추출 — 주석·서술 조회.

        Args:
            disclosureKey: canonical key (예: "inventoryDisclosure").
            periods: 특정 period 만.
            scope: "consolidated"/"standalone" 필터 (sections scope 컬럼).
            raw: 태그 보존(True) / strip(False).

        Returns:
            해당 disclosure 의 period 가로 정렬 DataFrame 또는 None.
        """
        wide = readSectionsWide(self.stockCode, periods=periods)
        if wide is None or "disclosureKey" not in wide.columns:
            return None
        sub = wide.filter(pl.col("disclosureKey") == disclosureKey)
        if "scope" in sub.columns and scope:
            target = "standalone" if (scope.startswith("stand") or scope.startswith("별도")) else "consolidated"
            scoped = sub.filter(pl.col("scope") == target)
            sub = scoped if not scoped.is_empty() else sub
        if sub.is_empty():
            return None
        if not raw:
            from .sections.tagstrip import stripExpr

            periodCols = [c for c in sub.columns if c[:4].isdigit()]
            sub = sub.with_columns([stripExpr(c) for c in periodCols])
        return sub

    @property
    def index(self) -> pl.DataFrame | None:
        """가용 topic 카탈로그 — finance/report/sections 통합 discovery 보드.

        Returns:
            DataFrame ``(topic, label, kind, scope, nPeriods)`` 또는 None.
                kind ∈ {finance, report, sections}. nPeriods = 데이터 있는 기간 수.

        Raises:
            없음.

        Example:
            >>> Company("005930").index  # doctest: +SKIP

        SeeAlso:
            - ``show`` — 카탈로그의 topic 을 조회.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - 옛 topics/sources 흡수 — 한 보드에 3-source 가용 topic + 기간 수.
              finance(BS/IS/CF) + report(present apiType) + sections(disclosure).

        AIContext:
            discovery 진입 — show 전 "무엇이 있나" 카탈로그. 본문 디코드 0.
        """
        rows: list[dict] = []
        fin = buildTimeseries(self.stockCode)
        if fin is not None:
            series, periods = fin
            for stmt, label in (("BS", "재무상태표"), ("IS", "손익계산서"), ("CF", "현금흐름표")):
                if series.get(stmt):
                    rows.append(
                        {
                            "topic": stmt,
                            "label": label,
                            "kind": "finance",
                            "scope": "consolidated",
                            "nPeriods": len(periods),
                        }
                    )
        from dartlab.core.dataLoader import loadData

        rep = loadData(self.stockCode, category="report")
        if rep is not None and "apiType" in rep.columns:
            for at in rep["apiType"].unique().to_list():
                if not at:
                    continue
                sub = rep.filter(pl.col("apiType") == at)
                nper = sub.select([c for c in ("year", "quarterNum") if c in sub.columns]).unique().height
                rows.append(
                    {
                        "topic": at,
                        "label": API_TYPE_LABELS.get(at, at),
                        "kind": "report",
                        "scope": "consolidated",
                        "nPeriods": nper,
                    }
                )
        meta = readSectionsMeta(self.stockCode)
        if meta is not None:
            pcols = [c for c in meta.columns if c[:4].isdigit()]
            for r in meta.iter_rows(named=True):
                nper = sum(1 for c in pcols if r[c] is not None)
                label = r.get("blockLeaf") or r.get("sectionLeaf") or ""
                rows.append(
                    {
                        "topic": r.get("disclosureKey") or label,
                        "label": label,
                        "kind": "sections",
                        "scope": r.get("scope") or "",
                        "nPeriods": nper,
                    }
                )
        if not rows:
            return None
        return pl.DataFrame(rows)

    def trace(self, topic: str) -> dict:
        """topic 의 데이터 출처(provenance) — classify 부산물.

        Args:
            topic: 조회 대상 topic.

        Returns:
            ``{topic, kind, resolved, source}`` dict. kind ∈ {finance, report,
            sections}, source = 사람용 출처 설명.

        Raises:
            없음.

        Example:
            >>> Company("005930").trace("BS")
            {'topic': 'BS', 'kind': 'finance', 'resolved': 'BS', 'source': 'finance parquet (XBRL 정규화)'}

        SeeAlso:
            - ``classify`` — kind/resolved 결정.
            - ``show`` — 실제 데이터 조회.

        Requires:
            - dartlab

        Capabilities:
            - show 가 어느 source 로 분기하는지 미리 확인 — 디버그/감사 진입.

        AIContext:
            치환 정책(재무제표→finance / 정형→report / 서술→sections) 추적.
        """
        kind, resolved = classify(topic)
        source = {
            "finance": "finance parquet (XBRL 정규화)",
            "report": "report parquet (OpenDART apiType)",
            "sections": "sections artifact (수평화 contentRaw)",
        }[kind]
        return {"topic": topic, "kind": kind, "resolved": resolved, "source": source}

    def diff(
        self,
        topic: str,
        fromPeriod: str,
        toPeriod: str,
        *,
        scope: str = "consolidated",
    ) -> pl.DataFrame | None:
        """topic 의 두 기간 line-level 텍스트 변경 (unified diff).

        Args:
            topic: 비교 대상 (주로 sections 서술 — finance/report 도 셀 텍스트 비교).
            fromPeriod: 기준 기간 (예: "2024Q4" 또는 "2024-Q4").
            toPeriod: 비교 기간.
            scope: "consolidated"/"standalone".

        Returns:
            DataFrame ``(change, text)`` — change ∈ {added, removed}. 변경 없으면
            빈 DataFrame, topic/기간 부재 시 None.

        Raises:
            없음.

        Example:
            >>> Company("005930").diff("inventoryDisclosure", "2024Q4", "2025Q4")  # doctest: +SKIP

        SeeAlso:
            - ``show`` — diff 가 내부적으로 raw=False wide 를 사용.
            - ``trace`` — topic 출처.

        Requires:
            - dartlab
            - polars

        Capabilities:
            - sections 위 얇은 derivation — 태그 strip 후 line unified_diff. period 명
              은 dash 유무 (2024Q4 / 2024-Q4) 양형 매칭.

        AIContext:
            공시 변화 추적 진입 — 두 기간 같은 disclosure 의 +/- 라인.
        """
        df = self._showImpl(topic, scope=scope, raw=False)
        if df is None or df.is_empty():
            return None
        cols = set(df.columns)

        def _findCol(p: str) -> str | None:
            for cand in (p, p.replace("-", ""), p.replace("Q", "-Q")):
                if cand in cols:
                    return cand
            return None

        cFrom, cTo = _findCol(fromPeriod), _findCol(toPeriod)
        if cFrom is None or cTo is None:
            return None

        def _lines(col: str) -> list[str]:
            return "\n".join(str(v) for v in df[col].to_list() if v).splitlines()

        rows: list[dict] = []
        for line in difflib.unified_diff(_lines(cFrom), _lines(cTo), lineterm="", n=0):
            if line.startswith(("---", "+++", "@@")):
                continue
            tag = line[:1]
            content = line[1:].strip()
            if not content:  # strip 후 빈 줄(HTML 공백) 노이즈 제거
                continue
            if tag == "+":
                rows.append({"change": "added", "text": content})
            elif tag == "-":
                rows.append({"change": "removed", "text": content})
        return pl.DataFrame(rows, schema={"change": pl.Utf8, "text": pl.Utf8})
