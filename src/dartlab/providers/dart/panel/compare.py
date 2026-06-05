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


def _normCodes(codes: list[str] | str | None) -> list[str]:
    """codes 정규화 — str→[str], strip, 순서보존 dedup."""
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


def _companyCells(code: str, statement: str, freq: str, scope: str, marketNs: str) -> dict[str, tuple[str, float]]:
    """{acode: (label, 원환산값)} — statement 변형 union, depth-1 라인아이템, 단위 환산."""
    from dartlab.core.utils.helpers import parseNumStr

    from . import cell as _cell

    cells = _cell._cellsFromPanel(code, marketNs=marketNs)
    if cells is None:
        return {}
    scale = _detectUnitScale(code, marketNs)
    variants = _cell.STATEMENT_VARIANTS.get(statement, (statement.upper(),))
    out: dict[str, tuple[str, float]] = {}
    for v in variants:
        w = _cell._cellWideFromCells(cells, statement=v, freq=freq, scope=scope)
        if w is None or w.is_empty():
            continue
        # 연간(YYYY)+분기(YYYYQn) 둘 다 — isPeriodColumn(YYYYQn 전용)은 year 열 거부(freq="year" 전멸 버그).
        periods = [c for c in w.columns if _PERIOD_COL_RE.match(c)]
        if not periods:
            continue
        latest = max(periods)  # 동일 포맷 내 문자열 max = 최신
        for r in w.sort("axisPath").iter_rows(named=True):
            ac = r.get("acode")
            ax = r.get("axisPath") or ""
            raw = r.get(latest)
            lab = r.get("label") or ""
            # depth-1(파이프 없음 = top-level 라인아이템), acode 첫 등장 우선.
            if ac and raw is not None and "|" not in ax and ac not in out:
                num = parseNumStr(str(raw))
                if num is not None:
                    out[ac] = (str(lab), num * scale)
    return out


def _compareCells(codes: list[str], *, statement: str, freq: str, scope: str | None, marketNs: str) -> pl.DataFrame:
    """N사 재무를 acode(XBRL 코드) 단위로 정렬 — 행=(acode,label), 열=회사, 셀=원 환산값.

    이름 정렬(IS 6%)이 라벨 drift 로 실패하는 곳을 acode(IS 37%+)가 해소. scope 고정(자동폴백 금지 —
    연결↔별도 혼선 차단), freq 일치(분기↔연간 기간 착시 차단), 원 환산(단위 착시 차단)을 강제한다.
    """
    scope = _normScope(scope) or "consolidated"  # 비교는 scope 명시 고정
    per: dict[str, dict[str, tuple[str, float]]] = {}
    for c in codes:
        cc = _companyCells(c, statement, freq, scope, marketNs)
        if cc:
            per[c] = cc
    if len(per) < 2:
        return pl.DataFrame()
    present = [c for c in codes if c in per]
    # acode union (첫 등장 라벨 대표 — acode 가 정체성, label 은 표시용)
    repr_label: dict[str, str] = {}
    order: list[str] = []
    for c in present:
        for ac, (lab, _v) in per[c].items():
            if ac not in repr_label:
                repr_label[ac] = lab
                order.append(ac)
    rows: list[dict[str, object]] = []
    for ac in order:
        row: dict[str, object] = {"acode": ac, "label": repr_label[ac], "scope": scope}
        for c in present:
            row[c] = per[c].get(ac, (None, None))[1]  # 원 환산값 or None(honest-gap)
        rows.append(row)
    return pl.DataFrame(rows)


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
            회사×기간(열=``{code}␟{period}``), None 이면 최신 공통 시점. (재무 셀모드는 freq 최신 1시점.)
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
            - codes → readWide×N → (disclosureKey,scope,leafType) outer-align → topic 필터 → period 투영.
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
    freq = _normFreq(freq)
    markets = {detectMarket(c) for c in codes}
    if len(markets) > 1:
        raise ValueError(
            f"KO↔US 혼합 비교는 불가 ({markets}). 같은 시장 종목끼리만 — cross-market 은 후속(crossMarket)."
        )
    marketNs = "us" if markets == {"US"} else "kr"

    # 재무제표 토픽 = 셀(항목) 단위 비교 — acode 정렬 + 원 환산 (통짜 표 병치 대신).
    if topic and topic.strip().lower() in _FIN_KEYS:
        return _compareCells(codes, statement=topic.strip().lower(), freq=freq, scope=scope, marketNs=marketNs)

    scopeVal = _normScope(scope)
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
    if len(longs) < 2:
        return pl.DataFrame()

    long = pl.concat(longs, how="diagonal_relaxed")

    # 비교 시점 결정 — period 지정 시 그대로, 아니면 최신 공통(없으면 union 최신).
    if isinstance(period, str):
        targets = [period]
    elif isinstance(period, list):
        targets = list(period)
    else:
        perByCode = {c: set(long.filter(pl.col("_code") == c)["_period"].to_list()) for c in present}
        common = set.intersection(*perByCode.values()) if perByCode else set()
        pool = common or set().union(*perByCode.values())
        targets = [sortPeriods(list(pool), descending=True)[0]] if pool else []
    if not targets:
        return pl.DataFrame()
    long = long.filter(pl.col("_period").is_in(targets))
    if long.is_empty():
        return pl.DataFrame()

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

    # 컬럼 순서 — 식별 먼저, 셀은 회사(codes 순) → 기간 최신순.
    cellCols = [c for c in out.columns if c not in idCols]
    if single:
        ordered = [c for c in present if c in cellCols]
    else:
        ordered = sorted(
            cellCols,
            key=lambda x: (present.index(x.split(_SEP)[0]) if x.split(_SEP)[0] in present else 99, _negPeriodKey(x)),
        )
    if topic:
        out = _matchTopic(out, topic)
    return out.select([*idCols, *ordered])


def _negPeriodKey(cell: str) -> str:
    """다기간 셀 컬럼 '{code}␟{period}' 의 period 최신순 정렬키 (역순 문자열)."""
    parts = cell.split(_SEP)
    p = parts[1] if len(parts) > 1 else ""
    return "".join(chr(255 - ord(ch)) for ch in p)  # 내림차순


__all__ = ["compare"]
