"""compare — N 회사 공시 panel 을 회사 간 시점 비교 wide 로 정렬 (회사 간 수평화).

회사횡단(모듈 레벨, Company facade 밖 — ``Company.panel`` docstring 이 "회사간은 모듈 레벨"로
못박은 결정). ``dartlab.compare`` 로 노출. 한 회사 ``Panel`` 이 항목×기간이면, ``compare`` 는 같은
항목을 N 회사 × 기간으로 가로 정렬한 wide.

정렬키 = keyed ``(disclosureKey, scope, leafType)`` (era-stable canonicalKey — 보고서-로컬 라벨/번호
drift 를 자동 해소). narrative(disclosureKey 부재) = **섹션단위 병치만** (행단위 강제정렬은 거짓 1:1 =
확신오정렬 → 금지). scope(연결/별도) 가 정렬키에 포함돼야 별도-BS ↔ 연결-BS 혼선을 막는다.
"""

from __future__ import annotations

import re

import polars as pl

from dartlab.core.market import detectMarket

from .canonical import canonicalRankExpr
from .period import isPeriodColumn, sortPeriods
from .read import readWide

_MAX_COMPARE = 6
# 행 식별 컬럼 (readWide 출력 — read._INDEX_COLS 동형, leafSeq 제외).
_IDENT = ["chapter", "sectionLeaf", "blockLeaf", "leafType", "disclosureKey", "scope"]
_SEP = "␟"  # ␟ — 셀 컬럼 namespace 구분자 ({code}␟{period})

# 재무제표 토픽 — 셀(항목) 단위 비교(acode 정렬 + 원 환산). 통짜 표 병치 대신.
_FIN_KEYS = frozenset({"bs", "is", "cf", "cis", "sce"})
_VALID_FREQ = frozenset({"quarter", "year", "ytd"})
_UNIT_RE = re.compile(r"단위\s*[:：]\s*(백만원|천원|원)")
_UNIT_SCALE = {"백만원": 1_000_000, "천원": 1_000, "원": 1}
# 셀 wide 의 기간 열 — 연간(YYYY) + 분기(YYYYQn) 둘 다. isPeriodColumn(YYYYQn 전용)이 year 열을 거부하는
# 버그 회피 (freq="year" 비교가 전멸했던 원인).
_PERIOD_COL_RE = re.compile(r"^\d{4}(Q[1-4])?$")
_PERIOD_INPUT_RE = re.compile(r"^\d{4}(?:Q[1-4])?$")
_US_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _displayCodes(codes: list[str] | str | None) -> list[str]:
    """진단 표시용 codes 정규화 — 검증 없이 str→[str], strip, 순서보존 dedup."""
    if isinstance(codes, str):
        codes = [codes]
    seen: dict[str, None] = {}
    for c in codes or []:
        c = str(c).strip()
        if c and not re.fullmatch(r"\d{6}", c):
            c = c.upper()
        if c and c not in seen:
            seen[c] = None
    return list(seen)


def _normCodes(codes: list[str] | str | None) -> list[str]:
    """codes 정규화·검증 — KR 6자리 또는 US ticker 만 허용."""
    out = _displayCodes(codes)
    invalid = [c for c in out if not (re.fullmatch(r"\d{6}", c) or _US_TICKER_RE.fullmatch(c))]
    if invalid:
        raise ValueError("codes 는 한국 6자리 종목코드 또는 미국 ticker 여야 합니다.")
    return out


def _normScope(scope: str | None) -> str | None:
    """사용자 scope 어휘 → wide 의 scope 값('consolidated'/'standalone')."""
    if scope is None:
        return None
    s = scope.strip().lower()
    if s in {"consolidated", "연결", "c"}:
        return "consolidated"
    if s in {"separate", "standalone", "별도", "s"}:
        return "standalone"
    raise ValueError("scope 는 consolidated/standalone(연결/별도) 중 하나여야 합니다.")


def _normFreq(freq: str) -> str:
    """freq 정규화 — 재무 셀모드 입도 명시."""
    f = str(freq).strip().lower()
    if f not in _VALID_FREQ:
        raise ValueError("freq 는 quarter/year/ytd 중 하나여야 합니다.")
    return f


def _normPeriod(period: list[str] | str | None) -> list[str] | str | None:
    """period 입력 검증·정렬 — YYYY 또는 YYYYQn, list 는 최신순."""
    if period is None:
        return None
    single = isinstance(period, str)
    raw = [period] if single else period
    if not isinstance(raw, list):
        raise ValueError("period 는 YYYY/YYYYQn 문자열 또는 그 리스트여야 합니다.")
    vals: list[str] = []
    for p in raw:
        val = str(p).strip()
        if not _PERIOD_INPUT_RE.fullmatch(val):
            raise ValueError("period 는 YYYY 또는 YYYYQn 형식이어야 합니다.")
        vals.append(val)
    vals = list(dict.fromkeys(vals))
    if single:
        return vals[0] if vals else None
    return sortPeriods(vals, descending=True)


def _detectUnitScale(code: str, marketNs: str) -> int:
    """회사 재무표 caption '단위:X' → 원 배율. 미발견=백만원(DART 표준).

    XBRL valueRaw 는 회사 신고단위 무손실 저장(삼성·SK=백만원, 카카오=원). 회사 간 비교 시
    raw 나란히 두면 1000배 착시 → 원 환산 필수. 단위 토큰은 셀이 아니라 표 caption 에 있다.
    """
    from .build.cell import CELL_STATEMENTS
    from .read import _panelDir, ensurePanelFromHf

    ensurePanelFromHf(code, marketNs)
    flat = _panelDir(code, marketNs).parent / f"{code}.parquet"
    if not flat.exists():
        return 1_000_000
    df = pl.read_parquet(str(flat), columns=["disclosureKey", "contentRaw", "period"])
    stmt = df.filter(pl.col("disclosureKey").is_in(list(CELL_STATEMENTS)))
    # 캡션 = **ACODE 없는 캡션 leaf**에서만 (본문 leaf 의 EPS 행단위 '단위:원' 오염 차단 — 본문은 ACODE
    # 보유). **최신 period 우선**(옛 era '단위:원' 캡션이 최신 백만원 본표 오염 차단). 한 표가 캡션 leaf +
    # 본문 leaf 로 쪼개져 저장되므로 표머리 단위는 캡션 leaf 에 산다.
    cap = stmt.filter(~pl.col("contentRaw").str.contains("ACODE=", literal=True)).sort("period", descending=True)
    for r in cap.iter_rows(named=True):
        m = _UNIT_RE.search(r["contentRaw"] or "")
        if m:
            return _UNIT_SCALE[m.group(1)]
    return 1_000_000  # 캡션 부재 = DART 표준 백만원


def _financePeriodLabel(period: str, freq: str) -> str:
    """사용자 period 입력 → finance wide 컬럼 라벨."""
    p = str(period).strip()
    if freq == "year":
        m = re.fullmatch(r"(\d{4})(?:Q[1-4])?", p)
        return m.group(1) if m else p
    if re.fullmatch(r"\d{4}", p):
        return f"{p}Q4"
    return p


def _financePanelPeriod(period: str) -> str:
    """사용자 period 입력 → panel filing period prune 라벨."""
    p = str(period).strip()
    if re.fullmatch(r"\d{4}", p):
        return f"{p}Q4"
    return p


def _financeTargets(period: list[str] | str | None, freq: str) -> tuple[list[str] | None, list[str] | None]:
    """finance mode period 입력을 출력 라벨과 panel prune 라벨로 분리."""
    if period is None:
        return None, None
    raw = [period] if isinstance(period, str) else list(period)
    labels = list(dict.fromkeys(_financePeriodLabel(str(p), freq) for p in raw))
    panelPeriods = list(dict.fromkeys(_financePanelPeriod(str(p)) for p in raw))
    return labels, panelPeriods


def _companyCellsByPeriod(
    code: str,
    statement: str,
    freq: str,
    scope: str,
    marketNs: str,
    *,
    targetLabels: list[str] | None = None,
    panelPeriods: list[str] | None = None,
) -> dict[str, dict[str, tuple[str, float]]]:
    """{period: {acode: (label, 원환산값)}} — statement 변형 union, depth-1 라인아이템."""
    from dartlab.core.utils.helpers import parseNumStr

    from . import cell as _cell

    cells = _cell._cellsFromPanel(code, marketNs=marketNs, periods=panelPeriods)
    if cells is None:
        return {}
    scale = _detectUnitScale(code, marketNs)
    variants = _cell.STATEMENT_VARIANTS.get(statement, (statement.upper(),))
    wanted = set(targetLabels) if targetLabels is not None else None
    out: dict[str, dict[str, tuple[str, float]]] = {}
    for v in variants:
        w = _cell._cellWideFromCells(cells, statement=v, freq=freq, scope=scope)
        if w is None or w.is_empty():
            continue
        # 연간(YYYY)+분기(YYYYQn) 둘 다 — isPeriodColumn(YYYYQn 전용)은 year 열 거부(freq="year" 전멸 버그).
        periods = [c for c in w.columns if _PERIOD_COL_RE.match(c)]
        if wanted is not None:
            periods = [p for p in periods if p in wanted]
        if not periods:
            continue
        for p in periods:
            bucket = out.setdefault(p, {})
            for r in w.sort("axisPath").iter_rows(named=True):
                ac = r.get("acode")
                ax = r.get("axisPath") or ""
                raw = r.get(p)
                lab = r.get("label") or ""
                # depth-1(파이프 없음 = top-level 라인아이템), acode 첫 등장 우선.
                if ac and raw is not None and "|" not in ax and ac not in bucket:
                    num = parseNumStr(str(raw))
                    if num is not None:
                        bucket[ac] = (str(lab), num * scale)
    return out


def _chooseFinanceTargets(per: dict[str, dict[str, dict[str, tuple[str, float]]]]) -> list[str]:
    """회사별 finance period map 에서 최신 공통 period, 없으면 최신 union period 1개."""
    periodSets = [set(byPeriod) for byPeriod in per.values() if byPeriod]
    if not periodSets:
        return []
    common = set.intersection(*periodSets) if len(periodSets) > 1 else periodSets[0]
    pool = common or set().union(*periodSets)
    return [sorted(pool, reverse=True)[0]] if pool else []


def _compareCellsResult(
    codes: list[str],
    *,
    statement: str,
    freq: str,
    scope: str | None,
    marketNs: str,
    period: list[str] | str | None,
) -> tuple[pl.DataFrame, list[str]]:
    """N사 재무 frame 과 실제 period 를 함께 만든다.

    이름 정렬(IS 6%)이 라벨 drift 로 실패하는 곳을 acode(IS 37%+)가 해소. scope 고정(자동폴백 금지 —
    연결↔별도 혼선 차단), freq 일치(분기↔연간 기간 착시 차단), 원 환산(단위 착시 차단)을 강제한다.
    """
    scope = _normScope(scope) or "consolidated"  # 비교는 scope 명시 고정
    targetLabels, panelPeriods = _financeTargets(period, freq)
    per: dict[str, dict[str, dict[str, tuple[str, float]]]] = {}
    for c in codes:
        cc = _companyCellsByPeriod(
            c, statement, freq, scope, marketNs, targetLabels=targetLabels, panelPeriods=panelPeriods
        )
        if cc:
            per[c] = cc
    targets = targetLabels or _chooseFinanceTargets(per)
    if not targets:
        return pl.DataFrame(), []
    single = len(targets) == 1
    # acode union (첫 등장 라벨 대표 — acode 가 정체성, label 은 표시용)
    repr_label: dict[str, str] = {}
    order: list[str] = []
    for c in codes:
        for p in targets:
            for ac, (lab, _v) in per.get(c, {}).get(p, {}).items():
                if ac not in repr_label:
                    repr_label[ac] = lab
                    order.append(ac)
    if not order:
        return pl.DataFrame(), targets
    rows: list[dict[str, object]] = []
    for ac in order:
        row: dict[str, object] = {"acode": ac, "label": repr_label[ac], "scope": scope}
        for c in codes:
            for p in targets:
                key = c if single else f"{c}{_SEP}{p}"
                row[key] = per.get(c, {}).get(p, {}).get(ac, (None, None))[1]  # 원 환산값 or None(honest-gap)
        rows.append(row)
    return pl.DataFrame(rows), targets


def _compareCells(
    codes: list[str],
    *,
    statement: str,
    freq: str,
    scope: str | None,
    marketNs: str,
    period: list[str] | str | None,
) -> pl.DataFrame:
    """N사 재무를 acode(XBRL 코드) 단위로 정렬 — 행=(acode,label), 열=회사, 셀=원 환산값."""
    df, _ = _compareCellsResult(codes, statement=statement, freq=freq, scope=scope, marketNs=marketNs, period=period)
    return df


def _companyLong(code: str, wide: pl.DataFrame, scope: str | None) -> pl.DataFrame | None:
    """한 회사 wide → long (joinKey·code·식별·period·value). content-bearing(비빈 셀)만."""
    if scope is not None and "scope" in wide.columns:
        wide = wide.filter(pl.col("scope") == scope)
    if wide.is_empty():
        return None
    periodCols = [c for c in wide.columns if isPeriodColumn(c)]
    idCols = [c for c in _IDENT if c in wide.columns]
    if not periodCols or "disclosureKey" not in wide.columns:
        return None
    # keyed = (disclosureKey, scope, leafType); narrative = 회사·행 고유(절대 병합 안 됨).
    scopeCol = pl.col("scope").cast(pl.Utf8).fill_null("") if "scope" in idCols else pl.lit("")
    leafCol = pl.col("leafType").cast(pl.Utf8).fill_null("") if "leafType" in idCols else pl.lit("")
    keyed = pl.col("disclosureKey").cast(pl.Utf8) + _SEP + scopeCol + _SEP + leafCol
    narr = pl.lit(f"NARR{_SEP}{code}{_SEP}") + pl.col("_ri").cast(pl.Utf8)
    wide = wide.with_row_index("_ri").with_columns(
        pl.lit(code).alias("_code"),
        pl.when(pl.col("disclosureKey").is_not_null()).then(keyed).otherwise(narr).alias("_joinKey"),
    )
    long = wide.unpivot(
        index=["_joinKey", "_code", *idCols], on=periodCols, variable_name="_period", value_name="_value"
    )
    return long.filter(pl.col("_value").is_not_null() & (pl.col("_value").str.strip_chars() != ""))


def _matchTopic(df: pl.DataFrame, topic: str) -> pl.DataFrame:
    """topic 필터 — disclosureKey exact | native 표(BS/IS/CF/CIS/EF/SCE) | sectionLeaf/blockLeaf substring.

    ``Panel.__call__`` 의 key 흡수 규칙과 동형 (topic vs disclosureKey 인자 분리 금지).
    """
    up = topic.strip().upper()
    natives = {"BS", "IS", "CF", "CIS", "EF", "SCE"}
    dk = pl.col("disclosureKey").cast(pl.Utf8)
    mask = dk == topic
    if up in natives:
        mask = mask | (dk == up)
    for c in ("sectionLeaf", "blockLeaf"):
        if c in df.columns:
            mask = mask | pl.col(c).cast(pl.Utf8).str.contains(topic, literal=True)
    return df.filter(mask.fill_null(False))


def _orderedCellColumns(present: list[str], targets: list[str], *, single: bool) -> list[str]:
    """출력 셀 컬럼 순서 — 단일=회사, 다기간=회사×기간 최신순."""
    if single:
        return list(present)
    expected = [f"{code}{_SEP}{period}" for code in present for period in targets]
    return sorted(
        expected,
        key=lambda x: (present.index(x.split(_SEP)[0]) if x.split(_SEP)[0] in present else 99, _negPeriodKey(x)),
    )


def _ensureCellColumns(out: pl.DataFrame, ordered: list[str]) -> pl.DataFrame:
    """topic 필터 후 한 회사가 전부 결손이어도 비교 컬럼을 null 로 보존."""
    missing = [c for c in ordered if c not in out.columns]
    if not missing:
        return out
    return out.with_columns([pl.lit(None, dtype=pl.Utf8).alias(c) for c in missing])


def _rowLongFrame(
    codes: list[str],
    *,
    marketNs: str,
    scopeVal: str | None,
    period: list[str] | str | None,
    topic: str | None,
) -> tuple[pl.DataFrame | None, list[str]]:
    """row 모드 입력 panel 을 topic 적용 long frame 으로 정규화."""
    periodArg = [period] if isinstance(period, str) else period  # readWide 파일 prune
    longs: list[pl.DataFrame] = []
    present: list[str] = []
    for c in codes:
        wide = readWide(c, marketNs=marketNs, periods=periodArg, tag=False)
        if wide is None or wide.is_empty():
            continue
        lg = _companyLong(c, wide, scopeVal)
        if lg is not None and not lg.is_empty():
            longs.append(lg)
            present.append(c)
    if not longs:
        return None, present
    long = pl.concat(longs, how="diagonal_relaxed")
    if topic:
        # topic 이 있을 때는 period 선택 전에 먼저 좁힌다. 전체 패널 최신 공통분기가
        # topic 을 담지 않으면 직전 사업보고서 주석이 빈 표로 사라진다.
        long = _matchTopic(long, topic)
        if long.is_empty():
            return None, present
    return long, present


def _chooseRowTargets(long: pl.DataFrame, present: list[str], period: list[str] | str | None) -> list[str]:
    """row 모드 실제 비교 시점 — 명시 period 또는 최신 공통(없으면 union 최신)."""
    if isinstance(period, str):
        return [period]
    if isinstance(period, list):
        return sortPeriods(list(dict.fromkeys(period)), descending=True)
    perByCode = {c: set(long.filter(pl.col("_code") == c)["_period"].to_list()) for c in present}
    common = set.intersection(*perByCode.values()) if perByCode else set()
    pool = common or set().union(*perByCode.values())
    return [sortPeriods(list(pool), descending=True)[0]] if pool else []


def _compareRows(
    codes: list[str],
    *,
    marketNs: str,
    scopeVal: str | None,
    period: list[str] | str | None,
    topic: str | None,
) -> tuple[pl.DataFrame, list[str], str | None]:
    """row 모드 compare 결과와 실제 period/emptyReason 을 한 번에 만든다."""
    long, present = _rowLongFrame(codes, marketNs=marketNs, scopeVal=scopeVal, period=period, topic=topic)
    if long is None:
        if topic:
            unfiltered, _ = _rowLongFrame(codes, marketNs=marketNs, scopeVal=scopeVal, period=period, topic=None)
            return pl.DataFrame(), [], "noPanelRows" if unfiltered is None else "topicFilteredEmpty"
        return pl.DataFrame(), [], "noPanelRows"

    targets = _chooseRowTargets(long, present, period)
    if not targets:
        return pl.DataFrame(), [], "noComparablePeriods"
    long = long.filter(pl.col("_period").is_in(targets))
    if long.is_empty():
        return pl.DataFrame(), targets, "periodFilteredEmpty"

    single = len(targets) == 1
    long = long.with_columns((pl.col("_code") if single else pl.col("_code") + _SEP + pl.col("_period")).alias("_cell"))

    # 대표 식별(같은 joinKey 의 라벨 drift → 첫 등장 1개) + 셀 pivot.
    idCols = [c for c in _IDENT if c in long.columns]
    repr_ = long.group_by("_joinKey", maintain_order=True).agg([pl.col(c).first() for c in idCols])
    grid = long.pivot("_cell", index="_joinKey", values="_value", aggregate_function="first")
    out = repr_.join(grid, on="_joinKey", how="left").drop("_joinKey")

    # 행 정렬 — canonical chapter rank → 절 번호 → sectionLeaf → disclosureKey (셀 컬럼은 보존).
    out = out.with_columns(
        canonicalRankExpr("chapter").alias("_cr") if "chapter" in out.columns else pl.lit(0).alias("_cr"),
        pl.col("sectionLeaf").cast(pl.Utf8).str.extract(r"^\s*(\d+)", 1).cast(pl.Int64).alias("_sn")
        if "sectionLeaf" in out.columns
        else pl.lit(None, dtype=pl.Int64).alias("_sn"),
    )
    sortCols = ["_cr", "_sn", *([c for c in ("sectionLeaf", "disclosureKey") if c in out.columns])]
    out = out.sort(sortCols, nulls_last=True).drop("_cr", "_sn")

    # 컬럼 순서 — 식별 먼저, 셀은 회사(codes 순) → 기간 최신순. topic 필터 후 한 회사가 전부 결손이어도
    # 컬럼을 null 로 보존해야 honest-gap 이 화면/API 에 남는다.
    ordered = _orderedCellColumns(codes, targets, single=single)
    out = _ensureCellColumns(out, ordered)
    return out.select([*idCols, *ordered]), targets, None


def compare(
    codes: list[str] | str,
    *,
    topic: str | None = None,
    period: list[str] | str | None = None,
    scope: str | None = None,
    freq: str = "quarter",
) -> pl.DataFrame:
    """N 회사 공시 panel 을 회사 간 비교 wide 로 정렬한다 (재무는 셀 단위, 그 외는 항목 단위).

    한 회사 ``Panel`` 이 항목×기간이라면, ``compare`` 는 같은 공시 항목을 여러 회사에 걸쳐 가로로
    세운 wide 다. **콘텐츠 타입별 적응**:
        - **재무제표(topic="bs"/"is"/"cf"/"cis"/"sce")**: 통짜 표가 아니라 **셀(항목) 단위** —
          행=acode(XBRL 코드)·label, 열=회사, 셀=**원 환산 숫자**. 이름 drift(영업이익↔영업이익(손실))를
          acode 가 해소하고, 단위(백만원↔원)·scope(연결↔별도)·freq(분기↔연간)를 강제 일치시킨다.
          예: 자산총계 삼성 633조 / SK 222조 / 카카오 28.8조 (단위 착시 0).
        - **그 외(주석·서술·None)**: 정렬키(disclosureKey, scope, leafType)로 항목 단위 정렬. 회사마다
          다른 라벨·절 번호 drift 자동 해소 (삼성 "7. 유형자산" ↔ SK "11. 유형자산" 한 행).
    한쪽 회사에만 있는 항목은 honest-gap(null) — 거짓 정렬보다 빈 칸이 정직하다.

    Args:
        codes: 종목코드 2개 이상 (``list[str]`` 또는 단일 ``str``). 같은 시장(marketNs)끼리만.
        topic: 비교할 항목 — 재무표("bs"/"is"/"cf"/"cis"/"sce")는 셀 단위, 한글 섹션명("재고")·
            canonicalKey("NT_D826380")는 항목 단위. None 이면 전체 격자.
        period: 비교 시점 — 단일 ``str``("2025Q4") 이면 그 시점 board(열=회사코드), ``list`` 면
            회사×기간(열=``{code}␟{period}``), None 이면 최신 공통 시점. 재무 셀모드도 같은 시점 계약을 따른다.
        scope: "consolidated"/"separate"(=standalone). 연결↔별도 혼선 차단. None 이면 둘 다(재무는 연결 고정).
        freq: 재무 셀모드 입도 — "quarter"(분기, 기본)/"year"(연간)/"ytd"(누적). 회사 간 freq 일치 강제.

    시장(KR/US)은 codes 로 자동 판별(``detectMarket``) — 같은 시장끼리만. KO↔US 혼합은
    ValueError(crossMarket 후속).

    Returns:
        ``pl.DataFrame`` — 행=정렬된 공시 항목(식별 컬럼 + 회사별 셀), 컬럼=식별
        (chapter/sectionLeaf/blockLeaf/disclosureKey/scope/leafType) + 셀(단일 시점→회사코드,
        다기간→{code}␟{period}). 빈(2사 미만 데이터)이면 빈 DataFrame.

    Raises:
        ValueError: codes 2개 미만, 6개 초과, scope/freq 오타, 또는 marketNs 외 시장 혼합 시도.

    Example:
        >>> import dartlab
        >>> dartlab.compare(["005930", "000660"], topic="재고")          # doctest: +SKIP
        >>> dartlab.compare(["005930", "000660", "035720"])              # doctest: +SKIP  전체 격자
        >>> dartlab.compare(["005930", "000660"], topic="bs", scope="consolidated")  # doctest: +SKIP

    SeeAlso:
        - ``Panel`` — 한 회사 wide (compare 의 입력 단위).
        - ``read.readWide`` — 회사내 수평화(compare 가 회사당 1회 호출).
        - ``dartlab.scan`` — 전종목 횡단 스크리닝(compare 는 지정 N 사 구조 비교).

    Requires:
        - polars. 각 code 의 panel artifact(data/{dart|edgar}/panel/{code}.parquet).

    Capabilities:
        - N 회사 공시 항목(재무표·주석·서술)을 era-stable 정렬키로 가로 정렬 — 라벨/번호 drift 자동 해소.
        - 한쪽만 있는 항목은 honest-gap(null) — 확신오정렬보다 빈 칸.
        - 반환이 평범한 wide DataFrame — polars 연산 즉시.

    Guide:
        - 같은 시장 N 사를 codes 로, 비교 항목은 topic, 시점은 period. KO↔US 는 후속.

    AIContext:
        - scalar 지표 랭킹은 peerCompareN(축 다름). compare 는 공시 항목 구조 그대로 가로 비교.
        - 외부 본문(contentRaw)은 untrusted — ai 층이 마커로 감쌈.

    LLM Specifications:
        AntiPatterns:
            - codes 1개 — 비교 의미 0(단일 종목은 Company.panel).
            - bare disclosureKey 정렬 — scope/leafType 누락 시 별도↔연결·표↔서술 혼선.
            - narrative 행단위 강제정렬 — 거짓 1:1(섹션단위만).
        OutputSchema:
            - ``pl.DataFrame`` (식별 컬럼 + 회사 셀). 단일 시점=회사코드 열, 다기간={code}␟{period}.
        Prerequisites:
            - 각 code panel artifact. 동일 marketNs.
        Freshness:
            - 매 호출 readWide(파생물 미저장).
        Dataflow:
            - codes → readWide×N → (disclosureKey,scope,leafType) outer-align → topic 필터 → period 결정/투영.
        TargetMarkets:
            - KR(DART) 끼리 / US(EDGAR) 끼리. KO↔US 혼합은 후속(crossMarket).
    """
    codes = _normCodes(codes)
    if len(codes) < 2:
        raise ValueError(
            "compare 는 2개 이상 종목코드가 필요합니다 (예: dartlab.compare(['005930','000660'])). "
            "단일 종목은 Company(code).panel 사용."
        )
    if len(codes) > _MAX_COMPARE:
        raise ValueError(f"compare 는 최대 {_MAX_COMPARE}개 종목까지만 지원합니다.")
    periodVal = _normPeriod(period)
    freq = _normFreq(freq)
    markets = {detectMarket(c) for c in codes}
    if len(markets) > 1:
        raise ValueError(
            f"KO↔US 혼합 비교는 불가 ({markets}). 같은 시장 종목끼리만 — cross-market 은 후속(crossMarket)."
        )
    marketNs = "us" if markets == {"US"} else "kr"

    # 재무제표 토픽 = 셀(항목) 단위 비교 — acode 정렬 + 원 환산 (통짜 표 병치 대신).
    if topic and topic.strip().lower() in _FIN_KEYS:
        if marketNs != "kr":
            raise ValueError("US 재무 compare 는 아직 지원하지 않습니다. EDGAR 재무 adapter 확정 후 열립니다.")
        return _compareCells(
            codes, statement=topic.strip().lower(), freq=freq, scope=scope, marketNs=marketNs, period=periodVal
        )

    scopeVal = _normScope(scope)
    out, _, _ = _compareRows(codes, marketNs=marketNs, scopeVal=scopeVal, period=periodVal, topic=topic)
    return out


def _negPeriodKey(cell: str) -> str:
    """다기간 셀 컬럼 '{code}␟{period}' 의 period 최신순 정렬키 (역순 문자열)."""
    parts = cell.split(_SEP)
    p = parts[1] if len(parts) > 1 else ""
    return "".join(chr(255 - ord(ch)) for ch in p)  # 내림차순


def _compareMode(topic: str | None) -> str:
    """topic 기반 compare 실행 모드."""
    return "finance" if topic and topic.strip().lower() in _FIN_KEYS else "row"


def _periodValue(period: list[str] | str | None) -> list[str] | None:
    """diagnostics 용 period 입력 정규화."""
    if isinstance(period, str):
        return [period]
    if period is None:
        return None
    return [str(p) for p in period]


def _isFilled(value: object) -> bool:
    """셀 값 존재 판정 — 결손 0 채움 없이 빈 문자열만 결손."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _cellColumns(columns: list[str], codes: list[str]) -> list[str]:
    """compare 출력에서 회사 셀 컬럼만 추출."""
    out: list[str] = []
    for col in columns:
        if col in codes or any(col.startswith(f"{code}{_SEP}") for code in codes):
            out.append(col)
    return out


def _codeHasValue(row: dict[str, object], code: str) -> bool:
    """단일 행에서 특정 회사가 직접/다기간 셀 중 하나라도 값을 갖는지."""
    if _isFilled(row.get(code)):
        return True
    prefix = f"{code}{_SEP}"
    return any(col.startswith(prefix) and _isFilled(value) for col, value in row.items())


def _shareStats(df: pl.DataFrame, codes: list[str]) -> tuple[list[str], int, int, int]:
    """회사별 존재와 shared/partial/solo 행수를 계산."""
    presentSeen = {code: False for code in codes}
    sharedRows = 0
    partialRows = 0
    soloRows = 0
    for row in df.iter_rows(named=True):
        filledCodes = 0
        for code in codes:
            if _codeHasValue(row, code):
                presentSeen[code] = True
                filledCodes += 1
        if filledCodes == len(codes):
            sharedRows += 1
        elif filledCodes >= 2:
            partialRows += 1
        elif filledCodes == 1:
            soloRows += 1
    presentCodes = [code for code in codes if presentSeen[code]]
    return presentCodes, sharedRows, partialRows, soloRows


def compareDiagnostics(
    codes: list[str] | str,
    *,
    topic: str | None = None,
    period: list[str] | str | None = None,
    scope: str | None = None,
    freq: str = "quarter",
) -> dict[str, object]:
    """N 회사 compare 실행 계약을 표와 분리해 진단한다.

    Args:
        codes: 비교할 종목코드 2~6개.
        topic: compare 와 동일한 topic. 재무표 키는 finance 모드로 판정된다.
        period: compare 와 동일한 period 입력. None 이면 compare 가 최신 공통 시점을 고른다.
        scope: compare 와 동일한 연결/별도 scope.
        freq: compare 와 동일한 재무 셀모드 입도.

    Returns:
        ``dict[str, object]`` — 입력 정규화, 시장, 실행 모드, 출력 행/열, 회사별 존재,
        shared/partial/solo 행수, 실제 비교 period(``resolvedPeriods``), 빈 결과 사유를 담은 진단 payload.

    Raises:
        없음. 입력 계약 오류도 ``ok=False`` 와 ``reason="invalidInput"`` 으로 반환한다.

    Example:
        >>> from dartlab.providers.dart.panel import compareDiagnostics
        >>> compareDiagnostics(["005930", "000660"], topic="재고")  # doctest: +SKIP
    """
    displayCodes = _displayCodes(codes)
    mode = _compareMode(topic)
    diag: dict[str, object] = {
        "ok": False,
        "reason": None,
        "mode": mode,
        "codes": displayCodes,
        "requestedCodeCount": len(displayCodes),
        "maxCompare": _MAX_COMPARE,
        "marketNs": None,
        "topic": topic,
        "period": None,
        "resolvedPeriods": None,
        "scope": scope,
        "freq": freq,
        "rowCount": 0,
        "columns": [],
        "cellColumns": [],
        "presentCodes": [],
        "missingCodes": displayCodes,
        "sharedRows": 0,
        "partialRows": 0,
        "soloRows": 0,
        "emptyReason": None,
        "error": None,
    }
    try:
        normCodes = _normCodes(codes)
        if len(normCodes) < 2:
            raise ValueError(
                "compare 는 2개 이상 종목코드가 필요합니다 (예: dartlab.compare(['005930','000660'])). "
                "단일 종목은 Company(code).panel 사용."
            )
        if len(normCodes) > _MAX_COMPARE:
            raise ValueError(f"compare 는 최대 {_MAX_COMPARE}개 종목까지만 지원합니다.")
        normPeriod = _normPeriod(period)
        normFreq = _normFreq(freq)
        normScope = _normScope(scope)
        markets = {detectMarket(c) for c in normCodes}
        if len(markets) > 1:
            raise ValueError(
                f"KO↔US 혼합 비교는 불가 ({markets}). 같은 시장 종목끼리만 — cross-market 은 후속(crossMarket)."
            )
        marketNs = "us" if markets == {"US"} else "kr"
        if mode == "finance":
            if marketNs != "kr":
                raise ValueError("US 재무 compare 는 아직 지원하지 않습니다. EDGAR 재무 adapter 확정 후 열립니다.")
            actualScope = normScope or "consolidated"
            df, resolvedPeriods = _compareCellsResult(
                normCodes,
                statement=str(topic).strip().lower(),
                freq=normFreq,
                scope=actualScope,
                marketNs=marketNs,
                period=normPeriod,
            )
            emptyReason = "insufficientFinanceCells" if df.height == 0 else None
        else:
            actualScope = normScope
            df, resolvedPeriods, emptyReason = _compareRows(
                normCodes, marketNs=marketNs, scopeVal=normScope, period=normPeriod, topic=topic
            )
    except ValueError as exc:
        diag["reason"] = "invalidInput"
        diag["emptyReason"] = "invalidInput"
        diag["error"] = str(exc)
        return diag

    diag["codes"] = normCodes
    diag["requestedCodeCount"] = len(normCodes)
    diag["missingCodes"] = normCodes
    columns = list(df.columns)
    cellCols = _cellColumns(columns, normCodes)
    presentCodes, sharedRows, partialRows, soloRows = _shareStats(df, normCodes)
    missingCodes = [code for code in normCodes if code not in presentCodes]
    rowCount = df.height

    diag.update(
        {
            "ok": rowCount > 0,
            "reason": "ready" if rowCount > 0 else "emptyResult",
            "marketNs": marketNs,
            "period": _periodValue(normPeriod),
            "resolvedPeriods": resolvedPeriods,
            "scope": actualScope,
            "freq": normFreq,
            "rowCount": rowCount,
            "columns": columns,
            "cellColumns": cellCols,
            "presentCodes": presentCodes,
            "missingCodes": missingCodes,
            "sharedRows": sharedRows,
            "partialRows": partialRows,
            "soloRows": soloRows,
            "emptyReason": emptyReason,
        }
    )
    return diag


__all__ = ["compare", "compareDiagnostics"]
