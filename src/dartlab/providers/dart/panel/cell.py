"""panel 셀 read 표면 — panel.parquet 5표 contentRaw 를 read-time 분해 → 항목×period (별 artifact 0).

``_cellsFromPanel`` 이 panel.parquet 의 5표 row contentRaw 를 ``build.cell.cellsFromContent`` 로
lazy 분해(콜드 0)해, freq(연간/분기/누적)에 맞는 ACONTEXT 토큰을 **선택만** 해서 acode×period wide 로 pivot. 산수 0
(정부가 단독/누적/연간 다 계산해 토큰으로 박음). 모듈 top-level lxml 0 — 분해는 함수 lazy(콜드 보존, R2).

freq→토큰 규칙 (행별 ctxFlow 분기):
    - ``year``  : ctxMode=="Y" (dFY 흐름 / eFY 잔액). 열 = ctxYear. 사업보고서가 당기/전기/전전기 3년 운반.
    - ``quarter``: 흐름 d→ctxMode=="Q"(단독 3M), 시점 e→당기말 잔액(mode A/Y). 열 = YYYYQn.
    - ``ytd``   : ctxMode in (A,Y) (누적 흐름 FQA/HYA/TQA/dFY + 잔액). 열 = YYYYQn.

LLM Specifications:
    AntiPatterns:
        - lxml/zipfile import 금지 (R2 read 표면) — 분해 완료 컬럼만 filter.
        - freq 별 빼기 산수 금지 — ctxMode 토큰 선택만 (정부 native).
        - 5표 외 호출 금지 — statement ∈ {BS,IS2,IS3,CF,EF}.
    OutputSchema:
        - ``readCellWide(code,*,statement,freq,scope,...) -> pl.DataFrame | None`` (acode×period wide).
    Prerequisites:
        - data/dart/panel/{code}.parquet 의 5표 contentRaw (별 panelCell 0).
    Freshness:
        - 매 read (artifact 변경 즉시).
    Dataflow:
        - parquet glob → statement/scope/freq filter → 최신filing dedup → acode×period pivot.
    TargetMarkets:
        - KR (DART). ACONTEXT 2025-03+ (그 이전 셀 없음 → 열 부재).
"""

from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

# 재무비율 = native 5표 항목의 산수. 공식·매핑·파서·라벨 전부 core(L0) SSOT 호출 (panel 자급, 농장 0).
from dartlab.core.ratioCategories import RATIO_CATEGORIES, RATIO_FIELD_LABELS
from dartlab.core.ratios import calcRatioSeries, toSeriesDict
from dartlab.core.utils.helpers import parseNumStr
from dartlab.core.utils.labels import _loadAccountMappings

from .cellSchema import CELL_PIVOT_INDEX, CELL_SCHEMA

# 재무 5표 물리 statement (build/cell.CELL_STATEMENTS 와 동일 값 — read 표면 SSOT).
# IS1/IS2/IS3 = 손익(단일/별도/포괄) — 회사마다 표현이 달라 셋 다 포함.
_CELL_STATEMENTS: frozenset[str] = frozenset({"BS", "IS1", "IS2", "IS3", "CF", "EF"})

# ── statement resolution SSOT — 논리 키(사용자) → 물리 XBRL class 후보(우선순위) ──
# 회사마다 손익 표현(단일 IS1 / 별도 IS2 / 포괄 IS3)·공시 범위(연결/별도)가 달라, 그 변형을 *한 곳*에서
# 흡수한다. 폴백 체인을 코드에 흩지 않고 이 테이블이 단일 진실 — panel.py 는 논리 키만 넘긴다.
STATEMENT_VARIANTS: dict[str, tuple[str, ...]] = {
    "bs": ("BS",),  # 재무상태표
    "is": ("IS2", "IS3", "IS1"),  # 손익 — 별도손익 > 포괄손익 > 단일
    "cis": ("IS3", "IS2", "IS1"),  # 포괄손익 — 포괄 우선, 없으면 손익
    "cf": ("CF",),  # 현금흐름표
    "sce": ("EF",),  # 자본변동표
}
# scope 우선순위 — 연결(consolidated) 우선, 없으면 별도(standalone, 별도만 공시하는 회사).
SCOPE_ORDER: tuple[str, ...] = ("consolidated", "standalone")


def cellStatements() -> frozenset[str]:
    """셀 세분화 대상 재무 5표 statement 집합 (BS/IS2/IS3/CF/EF).

    Args:
        없음.

    Returns:
        ``frozenset[str]`` — canonicalKey 형식 statement 코드 (불변).

    Raises:
        없음.

    Example:
        >>> "IS2" in cellStatements()
        True
        >>> len(cellStatements())
        5
    """
    return _CELL_STATEMENTS


def _cellsFromPanel(code: str, marketNs: str = "kr", periods: list[str] | None = None) -> pl.DataFrame | None:
    """panel.parquet 5표 row contentRaw → in-memory 셀 DataFrame (호출 시 lazy 파싱, 별 artifact 0).

    panelCell 파일을 따로 두지 않고 **panel.parquet 의 5표 contentRaw 를 그 자리에서 분해**한다 (단일
    artifact). lxml 은 함수 내 lazy import — ``import dartlab`` 콜드스타트 무영향(R2 목적 보존,
    panel("is") 호출 시에만 로드). panel.parquet 자동로드(HF)는 read.ensurePanelFromHf 가 담당.

    Args:
        code: 종목코드.
        marketNs: 시장 namespace.
        periods: 특정 filing period parquet 만 (prune). None=전체.

    Returns:
        CELL_SCHEMA in-memory DataFrame 또는 None (panel.parquet/5표 부재).
    """
    from . import read as _read
    from .build.cell import CELL_STATEMENTS, cellsFromContent  # lazy: 콜드 0, 호출 시에만 lxml

    _read.ensurePanelFromHf(code, marketNs)
    panelDir = _read._panelDir(code, marketNs)
    flat = panelDir.parent / f"{code}.parquet"  # flat: data/dart/panel/{code}.parquet (회사당 1파일)
    cols = ["disclosureKey", "xbrlClass", "contentRaw", "period", "rceptNo"]
    frames: list[pl.DataFrame] = []
    if flat.exists():
        df = pl.read_parquet(str(flat), columns=cols)
        if periods is not None:
            df = df.filter(pl.col("period").is_in(list(periods)))  # 1파일 → 행 필터
        frames = [df]
    elif panelDir.exists():  # 하위호환 — 옛 period-shard 폴더
        files = sorted(panelDir.glob("*.parquet"))
        if periods is not None:
            files = [f for f in files if f.stem in set(periods)]
        frames = [pl.read_parquet(str(f), columns=cols) for f in files]
    if not frames:
        return None
    rows: list[dict] = []
    for df in frames:
        stmt = df.filter(pl.col("disclosureKey").is_in(list(CELL_STATEMENTS)))
        for row in stmt.iter_rows(named=True):
            scope2 = "standalone" if "_S" in (row["xbrlClass"] or "") else "consolidated"
            for cell in cellsFromContent(
                row["contentRaw"],
                statement=row["disclosureKey"],
                scope=scope2,
                period=row["period"],
                code=code,
                rcept=row["rceptNo"] or "",
            ):
                rows.append(cell)
    if not rows:
        return None
    return pl.DataFrame(rows, schema=CELL_SCHEMA)


# 콤마 천단위 숫자런 (데이터표 leaf = 가장 많은 것).
_NUMRUN_RE = re.compile(r"\d{1,3}(?:,\d{3})+")
# 단일축 lineitem 주석의 degenerate axis 멤버 (연도 아닌 진짜 축 아님) — collapse 해 depth-1 통과.
_DEGEN_AXIS: frozenset[str] = frozenset(
    {"ConsolidatedMember", "ReportedAmount", "ReportedAmountMember", "EntityWideTotalMember", ""}
)


def _collapseDegenAxis(ap: str | None) -> str:
    """단일축 lineitem 의 degenerate axisPath(ConsolidatedMember|ReportedAmount) → "" (depth-1 통과).

    진짜 축 멤버(세그먼트·거래처 등)면 그대로 둠 → ``_statementFromCells`` depth-1 필터가 matrix 주석 배제.
    """
    if not ap:
        return ""
    members = [m for m in ap.split("|") if m]
    return "" if all(m in _DEGEN_AXIS for m in members) else ap


def _noteCellsFromPanel(code: str, ntCode: str, marketNs: str = "kr") -> pl.DataFrame | None:
    """주석(NT_) 가족 contentRaw → CELL_SCHEMA 셀 — ``alignNotes`` 정체성 소스(``_cellsFromPanel`` 깊은과거 짝).

    5표 ``_cellsFromPanel`` 은 flat parquet 의 keyed 5표(2023+)만 본다. 주석은 read-time ``alignNotes`` 가
    null-key 깊은과거 주석행에 NT_ 정체성을 부여(2013~)하므로, 본 함수는 ``readLong→alignNotes→anchorLatest``
    aligned long 을 소스로 주석가족(ntCode)을 분해한다. XBRL leaf = ``_xbrlCellsFromContent``(+ degenerate axis
    collapse), 옛 leaf = ``_parseOldNoteTable``(병합행 가드). 연간 deep-history(Q4 사업보고서)만.

    Args:
        code: 종목코드.
        ntCode: 주석 표준코드(NT_D######) substring.
        marketNs: 시장 namespace.

    Returns:
        CELL_SCHEMA in-memory DataFrame 또는 None (주석가족/데이터표 부재).
    """
    from . import read as _read
    from .build.cell import _parseFragment, _parseOldNoteTable, _xbrlCellsFromContent

    long = _read.readLong(code, marketNs=marketNs)  # 전 period — alignNotes 뼈대는 최근 native 주석 필요
    if long is None:
        return None
    aligned = _read.anchorLatest(_read.alignNotes(long))
    fam = aligned.filter(
        pl.col("disclosureKey").fill_null("").str.contains(ntCode)
        & (pl.col("leafType") == "table")
        & pl.col("period").str.ends_with("Q4")
    )
    if fam.is_empty():
        return None
    # (period, scope) 별 데이터표 leaf 1개 = 콤마숫자 가장 많은 contentRaw.
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in fam.iter_rows(named=True):
        groups.setdefault((r["period"], r.get("scope") or "consolidated"), []).append(r)
    rows: list[dict] = []
    for (period, scope), leaves in groups.items():
        best, bn = None, 0
        for r in leaves:
            n = len(_NUMRUN_RE.findall(r.get("contentRaw") or ""))
            if n > bn:
                bn, best = n, r
        if best is None or bn < 2:
            continue
        root = _parseFragment(best["contentRaw"])
        if root is None:
            continue
        rcept = best.get("rceptNo") or ""
        if root.find(".//TE[@ACONTEXT]") is not None:
            for c in _xbrlCellsFromContent(root, statement=ntCode, scope=scope, period=period, code=code, rcept=rcept):
                c["axisPath"] = _collapseDegenAxis(c["axisPath"])
                rows.append(c)
        else:
            rows.extend(_parseOldNoteTable(root, statement=ntCode, scope=scope, period=period, code=code, rcept=rcept))
    if not rows:
        return None
    return pl.DataFrame(rows, schema=CELL_SCHEMA)


def _freqMask(freq: str) -> pl.Expr:
    """freq → ctxFlow/ctxMode filter mask (토큰 선택, 산수 0).

    Args:
        freq: "year" / "quarter" / "ytd".

    Returns:
        polars 불리언 Expr. 미지원 freq 는 항상 False.
    """
    if freq == "year":
        # 연간 = dFY/eFY(Y) 또는 Q4 누적(A & Q4=12M=연간). 회사마다 연간 인코딩이 Y 또는 A-Q4 로 갈림.
        return (pl.col("ctxMode") == "Y") | ((pl.col("ctxMode") == "A") & (pl.col("ctxQuarter") == 4))
    if freq == "quarter":
        # 흐름=단독(Q), 시점=당기말 잔액(A 또는 연말 Y).
        return ((pl.col("ctxFlow") == "d") & (pl.col("ctxMode") == "Q")) | (
            (pl.col("ctxFlow") == "e") & pl.col("ctxMode").is_in(["A", "Y"])
        )
    if freq == "ytd":
        # 누적 흐름(A) + 연간(Y, =Q4 누적) + 잔액(A/Y).
        return pl.col("ctxMode").is_in(["A", "Y"])
    return pl.lit(False)


def _periodLabelExpr(freq: str) -> pl.Expr:
    """freq → period 열 라벨 Expr. year=YYYY, 그 외=YYYYQn."""
    if freq == "year":
        return pl.col("ctxYear").cast(pl.Utf8)
    return pl.col("ctxYear").cast(pl.Utf8) + "Q" + pl.col("ctxQuarter").cast(pl.Utf8)


def readCellWide(
    code: str,
    *,
    statement: str,
    freq: str = "quarter",
    scope: str = "consolidated",
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """재무 5표 panel contentRaw read-time 셀 → acode×period wide (freq 토큰 선택, 평탄화 acode@axisPath).

    Args:
        code: 종목코드.
        statement: 5표 canonicalKey ("BS"/"IS2"/"IS3"/"CF"/"EF").
        freq: "year"(연간) / "quarter"(분기 단독) / "ytd"(분기 누적). 기본 quarter.
        scope: "consolidated"(연결) / "standalone"(별도). 기본 consolidated.
        marketNs: 시장 namespace.
        periods: 특정 filing period(YYYYQn) parquet 만 (파일 prune). None = 전체.

    Returns:
        wide DataFrame — 행 = (statement, acode, label, axisPath, scope), 열 = period(최신 좌측),
        cell = valueRaw. 또는 None (artifact 없음 / statement 미존재 / freq 매칭 0).

    Raises:
        없음 — panel/cell 부재·빈 시 None.

    Example:
        >>> readCellWide("005930", statement="IS2", freq="year")  # doctest: +SKIP — 손익 연간 acode×연도
        >>> readCellWide("005930", statement="BS", freq="quarter")  # doctest: +SKIP — 재무상태 분기말

    SeeAlso:
        - ``build.cell.cellsFromContent`` — 5표 contentRaw → 셀 분해 (lazy).
        - ``readStatement`` — 항목명 statement view(`c.panel("is")`). 본 함수는 acode 정밀 차원 view(직접 호출).

    Requires:
        - polars. data/dart/panel/{code}.parquet (5표 contentRaw).

    Capabilities:
        - 정부 native XBRL 셀을 freq 토큰 선택만으로 acode×period 격자 — 추측·산수 0, 깊이는 axisPath 행.

    Guide:
        - 직접 호출 (acode/축 정밀 view). 사람용 statement 는 ``readStatement``/``c.panel("is")``.

    AIContext:
        - 상태 없는 read. valueRaw(콤마/괄호) 그대로 — 숫자화는 소비자.

    When:
        - 재무 5표를 연간/분기/누적 native 셀 격자로 볼 때.

    How:
        - parquet glob → statement/scope/freq filter → 최신filing dedup → acode×period pivot → 정렬.

    LLM Specifications:
        AntiPatterns:
            - 모듈 top-level lxml import 금지(R2 콜드). freq 빼기 산수 금지(토큰 선택).
            - 5표 외 statement 금지.
        OutputSchema:
            - ``pl.DataFrame | None`` (acode×period wide).
        Prerequisites:
            - panel.parquet 5표 contentRaw.
        Freshness:
            - 매 read.
        Dataflow:
            - glob → filter → dedup → pivot.
        TargetMarkets:
            - KR + US.
    """
    if statement not in _CELL_STATEMENTS:
        return None
    df = _cellsFromPanel(code, marketNs, periods)
    if df is None:
        return None
    return _cellWideFromCells(df, statement=statement, freq=freq, scope=scope)


def _cellWideFromCells(df: pl.DataFrame, *, statement: str, freq: str, scope: str) -> pl.DataFrame | None:
    """셀 DataFrame → acode×period wide (XBRL acode 정밀 view). 소스-중립 순수 함수."""
    df = df.filter(
        (pl.col("statement") == statement)
        & (pl.col("scope") == scope)
        & pl.col("acode").is_not_null()  # 옛 acode=None 셀은 readStatement 전용
        & _freqMask(freq)
    )
    if df.is_empty():
        return None

    df = df.with_columns(_periodLabelExpr(freq).alias("_period"))
    # 최신 접수(rceptNo desc) 우선 — dedup·대표 label·대표 cellOrder 모두 최신 filing 기준.
    df = df.sort("rceptNo", descending=True)
    deduped = df.unique(subset=[*CELL_PIVOT_INDEX, "_period"], keep="first", maintain_order=True)
    meta = df.group_by(CELL_PIVOT_INDEX, maintain_order=True).agg(
        pl.col("label").first().alias("label"),  # rceptNo desc 정렬 후라 최신 filing label
        pl.col("cellOrder").min().alias("_ord"),
    )

    wide = deduped.pivot(values="valueRaw", index=CELL_PIVOT_INDEX, on="_period", aggregate_function="first")
    wide = wide.join(meta, on=CELL_PIVOT_INDEX, how="left").sort("_ord").drop("_ord")

    periodCols = sorted((c for c in wide.columns if c not in CELL_PIVOT_INDEX and c != "label"), reverse=True)
    return wide.select([*CELL_PIVOT_INDEX, "label", *periodCols])


# 정규화 매칭 키 — era 표기변형 흡수해 같은 항목 통합 (XBRL label ↔ 옛 항목명):
#   (1) (주N)·(단위) 주석/단위 annotation 제거  (2) 로마numeral 섹션 prefix(Ⅰ.~Ⅹ.) 제거  (3) 중점ㆍ·공백 제거.
# 아라비아/한글 ordinal(1./가.)은 *보존* — CF 리스트항목 번호만 다른 별개행 오병합 위험(로마만 섹션마커라 안전).
# tests/_attempts/pastAxisConnection 100사 over-merge 0 검증. _normKey 가 본 함수의 스칼라 쌍둥이(동일 3패스).
_NOTE_PAT = r"\((?:주[\s\d,]+|단위[^)]*)\)"
_ROMAN_PREFIX = r"^\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\s*[.)]\s*"
_DOT_WS = r"[ㆍ·∙•\s]+"


def _normalizeLabel(col: pl.Expr) -> pl.Expr:
    """label → 매칭 키: (주N)·(단위) strip + 로마numeral prefix strip + 중점·공백 제거.

    "매출액 (주30)"→"매출액" · "Ⅰ.매출액"→"매출액" · "주당이익(단위:원)"→"주당이익" · "자산ㆍ부채"→"자산부채".
    아라비아/한글 ordinal 보존. ``_normKey`` 와 동일 정규화(쌍둥이 — ratio snakeId 매칭 정합).
    """
    return col.str.replace_all(_NOTE_PAT, "").str.replace_all(_ROMAN_PREFIX, "").str.replace_all(_DOT_WS, "")


def _find(parent: dict, x: str) -> str:
    """union-find root (경로 압축)."""
    parent.setdefault(x, x)
    r = x
    while parent[r] != r:
        r = parent[r]
    while parent[x] != r:
        parent[x], x = r, parent[x]
    return r


def _stitchRecentName(df: pl.DataFrame) -> pl.DataFrame:
    """개명 항목 통합 — 금액 겹침으로 같은 라인 묶어 **최신 filing 이름** 부여 (공존 별개계정 가드).

    연속 보고서가 당기/전기/전전기로 연도 겹침 → 개명 전후 같은 라인은 **겹친 해의 금액이 같다**. 그 금액
    동치((ctxYear, valueRaw) 공유, 식별력 있는 콤마 큰금액만)로 ``_name`` 동치류를 만들고, 각 류 canonical =
    최신 rceptNo 의 ``_name``.

    **공존 불변식**: 한 공시(rceptNo) 내 distinct 라인으로 같이 나오는 두 이름은 *정의상 별개계정*
    (증가/감소·기본/희석주당·자본총계/지배기업소유주귀속자본) → 우연한 금액일치로도 같은 클러스터 금지.
    개명(매도가능→기타포괄)은 시대 달라 공존 안 해 통합 보존 → over-merge 데이터손실 제거 + rename 과거연결
    유지. 충돌맵은 union 대상인 sig 이름(콤마 큰금액)으로 한정(속도). 그룹 정렬 순회로 결정론.
    tests/_attempts/principledStitch — 471사 distinct 오염칸 8.58%→2.38%(72% 제거)·무손실 fragmentation.

    Args:
        df: ``_name``/``ctxYear``/``valueRaw``/``rceptNo`` 보유 cell DataFrame.

    Returns:
        ``_name`` 을 canonical(최근 이름)로 치환한 DataFrame. 공존(별개계정) 쌍은 분리 유지.
    """
    sig = df.filter(pl.col("valueRaw").str.contains(",", literal=True)).select("_name", "ctxYear", "valueRaw")
    if sig.is_empty():
        return df
    sigNames = set(sig["_name"].unique().to_list())  # union 후보 = sig 이름뿐
    # 공존 충돌맵 — 한 공시 내 같이 나오는 sig 이름쌍(별개계정). 멤버가 전부 sig 라 sig 한정으로 충분·빠름.
    conflict: dict[str, set[str]] = defaultdict(set)
    cooc = df.filter(pl.col("_name").is_in(sigNames)).group_by("rceptNo").agg(pl.col("_name").unique().alias("ns"))
    for names in cooc["ns"].to_list():
        s = set(names)
        for a in names:
            conflict[a] |= s - {a}
    groups: dict[tuple, list[str]] = {}
    for name, yr, val in sig.iter_rows():
        groups.setdefault((yr, val), []).append(name)
    parent: dict[str, str] = {}
    members: dict[str, set[str]] = {}  # root → 클러스터 멤버 전체 (공존 검사용)
    for key in sorted(groups, key=lambda k: (str(k[0]), str(k[1]))):  # 결정론 순회
        names = groups[key]
        rb = _find(parent, names[0])
        members.setdefault(rb, {rb})
        for n in names[1:]:
            rn = _find(parent, n)
            if rn == rb:
                continue
            cb = members.setdefault(rb, {rb})
            cn = members.setdefault(rn, {rn})
            if any(b in conflict.get(a, ()) for a in cb for b in cn):
                continue  # 두 클러스터 합치면 공존쌍 발생 → 병합 거부 (별개계정)
            parent[rn] = rb
            cb |= cn
            members.pop(rn, None)
            rb = _find(parent, rb)
    recency: dict[str, str] = dict(df.group_by("_name").agg(pl.col("rceptNo").max().alias("r")).iter_rows())
    comp: dict[str, list[str]] = {}
    for name in recency:
        comp.setdefault(_find(parent, name), []).append(name)
    nameToCanon: dict[str, str] = {}
    for mem in comp.values():
        best = max(mem, key=lambda n: recency.get(n) or "")  # 최신 filing 이름
        for m in mem:
            nameToCanon[m] = best
    return df.with_columns(pl.col("_name").replace(nameToCanon).alias("_name"))


def readStatement(
    code: str,
    *,
    statement: str,
    freq: str = "quarter",
    scope: str | None = None,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """native 재무제표 — 논리 키 → 회사별 표현 해소 → 항목명 × 전 기간 (XBRL 최근 + 옛 표 통합, 2011~).

    ``statement`` 은 **논리 키**(``STATEMENT_VARIANTS``: is/bs/cf/cis/sce)다. 회사마다 손익을 단일(IS1)/
    별도(IS2)/포괄(IS3)로, 공시를 연결/별도로 달리 내므로, 그 변형을 단일 테이블이 해소한다(폴백 흩지 않음).
    셀을 **정규화 항목명**으로 통합 pivot — top-level axis(깊이 1) 라인아이템, 겹치는 해는 최신 filing 우선.
    `readCellWide`(acode 정밀 차원 view) 와 별개 — 본 함수가 `c.panel("is")` statement view.

    Args:
        code: 종목코드.
        statement: 논리 키 — "is"(손익)/"bs"(재무상태)/"cf"(현금흐름)/"cis"(포괄손익)/"sce"(자본변동).
        freq: "year"(연간) / "quarter"(분기) / "ytd"(누적). 기본 quarter (raw 격자와 동일 입도).
        scope: None(기본)=연결→별도 자동 / "consolidated" / "standalone" 강제.
        marketNs: 시장 namespace.
        periods: 특정 filing period parquet 만 (prune). None=전체.

    Returns:
        wide DataFrame — 행=(account 정규화명, label 표시명), 열=period(최신 좌측), cell=valueRaw.
        또는 None (artifact 없음 / statement 미존재 / 매칭 0).

    Raises:
        없음.

    Example:
        >>> readStatement("005930", statement="IS2", freq="year")  # doctest: +SKIP — 손익 2011~ 연속

    SeeAlso:
        - ``build.cell.cellsFromContent`` — XBRL+옛 셀 분해 (lazy).
        - ``readCellWide`` — acode 정밀 차원 view (본 함수는 항목명 statement view).
        - ``panel.Panel.__call__`` — ``c.panel("is", freq=)`` 진입점.

    Requires:
        - polars. data/dart/panel/{code}.parquet (5표 contentRaw).

    Capabilities:
        - native 재무제표를 XBRL 경계(2022) 넘어 항목명 매칭으로 과거 연장.

    Guide:
        - ``c.panel("is")`` 소문자 호출 → 본 함수. 대문자 IS 는 finance(파사드).

    AIContext:
        - 상태 없는 read. valueRaw 그대로. 개명 항목은 금액 겹침으로 최근 이름 통합(_stitchRecentName).

    When:
        - native 재무제표를 전 기간 연속으로 볼 때.

    How:
        - parquet glob → statement/scope/depth-1/freq filter → 정규화명 pivot → 최신 filing dedup.

    LLM Specifications:
        AntiPatterns:
            - lxml import 금지(R2). over-merge 회피 — 식별력 있는 큰 금액(콤마)만 stitch 링크.
        OutputSchema:
            - ``pl.DataFrame | None`` (항목명×period).
        Prerequisites:
            - panel.parquet 5표 contentRaw.
        Freshness:
            - 매 read.
        Dataflow:
            - glob → filter → 정규화명 pivot → dedup.
        TargetMarkets:
            - KR + US.
    """
    variants = STATEMENT_VARIANTS.get(statement)
    if variants is None:
        return None
    df = _cellsFromPanel(code, marketNs, periods)
    if df is None:
        return None
    return _resolveStatement(df, variants=variants, freq=freq, scope=scope)


def readNoteStatement(
    code: str,
    *,
    statement: str,
    freq: str = "year",
    scope: str | None = None,
    marketNs: str = "kr",
) -> pl.DataFrame | None:
    """주석(NT_) 표를 IS/BS 처럼 항목명 × 전 기간 정규화 — 5표 read 엔진(`_resolveStatement`) 재사용.

    ``c.panel("NT_D834300")`` 진입점. 단일축 lineitem 주석(비용성격별·판관비·법인세·금융손익·퇴직급여 등)을
    ``readStatement`` 와 **동일 계약**(raw valueRaw, source 단위, `_stitchRecentName` 개명통합)으로 정규화한다.
    셀 소스만 ``alignNotes`` aligned(깊은과거 2013~)로 다르고, stitch/pivot/scope 해소는 5표와 같은
    ``_resolveStatement``. 다축 matrix 주석(세그먼트·특수관계자)은 axisPath 가 보존돼 depth-1 필터에서 제외
    → None(축차원 view 는 별도). 순수 서술 주석도 셀 0 → None (honest gap).

    Args:
        code: 종목코드.
        statement: 주석 표준코드 ("NT_D######").
        freq: "year"(기본, 사업보고서 당기/전기 연장) / "quarter" / "ytd".
        scope: None(기본)=연결→별도 자동 / "consolidated" / "standalone".
        marketNs: 시장 namespace.

    Returns:
        항목명×period wide(raw valueRaw, 최신 좌측) 또는 None (주석가족 부재 / 다축·서술 주석 / 매칭 0).

    Raises:
        없음 — 주석/셀 부재 시 None.

    Example:
        >>> readNoteStatement("005930", statement="NT_D834300", freq="year")  # doctest: +SKIP — 비용성격별 12년

    SeeAlso:
        - ``readStatement`` — 5표 항목명 view (본 함수는 그 주석 짝, 엔진 공유).
        - ``_noteCellsFromPanel`` — ``alignNotes`` 정체성 소스 셀(깊은과거).
        - ``panel.Panel.__call__`` — ``c.panel("NT_D834300")`` 진입점.

    AIContext:
        - 상태 없는 read. valueRaw 그대로(숫자화는 소비자) — 5표와 동일 계약. 단위환산·content-signal 미적용.
    """
    if not statement.startswith("NT_"):
        return None
    df = _noteCellsFromPanel(code, statement, marketNs)
    if df is None:
        return None
    # keyed era(2023+)는 native per-table NT_ 라 0 오염. 깊은과거 combined-note 에서 인접 tax 표가 같은 제목으로
    # co-tagged 되면 그 period 만 행 혼입 — 큐레이션(content-signal) 없는 honest-gap(구조 정밀화는 alignNotes/dechunk 후속).
    return _resolveStatement(df, variants=(statement,), freq=freq, scope=scope)


def _resolveStatement(
    df: pl.DataFrame, *, variants: tuple[str, ...], freq: str, scope: str | None = None
) -> pl.DataFrame | None:
    """셀 → 물리 후보(variants) × scope 우선순위로 가장 적합한 statement (소스-중립 SSOT 해소).

    scope=None 이면 ``SCOPE_ORDER``(연결→별도) 자동, 지정 시 그 scope 만. variants 는 손익처럼 표현
    변형이 있는 논리 키의 물리 후보(우선순위) — 첫 비어있지 않은 결과 반환.
    """
    scopes = SCOPE_ORDER if scope is None else (scope,)
    for sc in scopes:
        for st in variants:
            out = _statementFromCells(df, statement=st, freq=freq, scope=sc)
            if out is not None:
                return out
    return None


def _statementFromCells(df: pl.DataFrame, *, statement: str, freq: str, scope: str) -> pl.DataFrame | None:
    """셀 DataFrame → 정규화 항목명×period statement (XBRL+옛 통합). 소스-중립 순수 함수."""
    df = df.filter(
        (pl.col("statement") == statement)
        & (pl.col("scope") == scope)
        & ~pl.col("axisPath").str.contains("|", literal=True)  # depth-1 top-level 라인아이템
        & _freqMask(freq)
    )
    if df.is_empty():
        return None

    df = df.with_columns(
        _normalizeLabel(pl.col("label")).alias("_name"),
        _periodLabelExpr(freq).alias("_period"),
    ).sort("rceptNo", descending=True)  # 최신 filing(=XBRL) 우선
    df = _stitchRecentName(df)  # 개명 항목 → 금액 겹침으로 최근 이름 통합
    deduped = df.unique(subset=["_name", "_period"], keep="first", maintain_order=True)
    meta = df.group_by("_name", maintain_order=True).agg(
        pl.col("label").first().alias("label"),  # 최신 filing 표시명
        pl.col("cellOrder").min().alias("_ord"),
    )

    wide = deduped.pivot(values="valueRaw", index="_name", on="_period", aggregate_function="first")
    wide = wide.join(meta, on="_name", how="left").sort("_ord").drop("_ord").rename({"_name": "account"})
    periodCols = sorted((c for c in wide.columns if c not in ("account", "label")), reverse=True)
    return wide.select(["account", "label", *periodCols])


# ── native 재무비율 (소문자 ratios — BS/IS/CF native 항목으로 core 공식 산출, panel 자급) ──

# 비율 재료 — series 버킷(BS/IS/CF) → 논리 키(STATEMENT_VARIANTS). 손익은 is(IS2→IS3→IS1) 자동 해소.
_RATIO_SOURCE: dict[str, str] = {"BS": "bs", "IS": "is", "CF": "cf"}

_NOTE_RE = re.compile(_NOTE_PAT)
_ROMAN_RE = re.compile(_ROMAN_PREFIX)
_DOTWS_RE = re.compile(_DOT_WS)


def _normKey(s: str) -> str:
    """항목명 → 매칭 키 — ``_normalizeLabel`` 의 스칼라 쌍둥이 (동일 3패스: 주N·단위 / 로마prefix / 중점·공백)."""
    s = _NOTE_RE.sub("", s or "")
    s = _ROMAN_RE.sub("", s)
    return _DOTWS_RE.sub("", s)


@lru_cache(maxsize=1)
def _labelToSnakeId() -> dict[str, str]:
    """정규화 한국어 항목명 → snakeId — core ``mappings`` SSOT 재색인 (readStatement account 와 동일 정규화).

    Returns:
        ``{정규화항목명: snakeId}`` — 충돌 시 첫 등록 우선.

    SeeAlso:
        - ``core.utils.labels._loadAccountMappings`` — 원천 mappings(34,000+) 로더.
    """
    mappings = _loadAccountMappings().get("mappings", {})
    out: dict[str, str] = {}
    for korName, snakeId in mappings.items():
        key = _normKey(korName)
        if key and key not in out:
            out[key] = snakeId
    return out


def _assembleRatioSeries(
    statements: dict[str, pl.DataFrame | None],
) -> tuple[dict[str, dict[str, list[float | None]]], list[str]] | None:
    """native statement wide(항목명×period) → ``calcRatioSeries`` series + years.

    버킷 = 읽은 statement(BS/IS/CF). snakeId = core mappings(정규화 항목명). 값 = ``parseNumStr``(valueRaw,
    △/콤마). period = 표 간 union(오름차순 — YoY 정합, 각 series list 가 years 와 같은 길이로 정렬·None-fill).

    Args:
        statements: ``{"BS"|"IS"|"CF": readStatement 결과 | None}``.

    Returns:
        ``(series, years)`` 또는 None (재료 0). ``series={"BS":{snakeId:[...]}, ...}``.
    """
    labelMap = _labelToSnakeId()
    periodSet: set[str] = set()
    for df in statements.values():
        if df is not None:
            periodSet.update(c for c in df.columns if c not in ("account", "label"))
    if not periodSet:
        return None
    years = sorted(periodSet)  # 오름차순 (calcRatioSeries yoyLag 정합)
    series: dict[str, dict[str, list[float | None]]] = {}
    for sjKey, df in statements.items():
        if df is None or df.is_empty():
            continue
        bucket: dict[str, list[float | None]] = {}
        for row in df.iter_rows(named=True):
            snakeId = labelMap.get(row["account"])
            if snakeId is None or snakeId in bucket:  # 첫 행 우선(최신 filing 정렬됨)
                continue
            bucket[snakeId] = [parseNumStr(row.get(y)) for y in years]
        if bucket:
            series[sjKey] = bucket
    if not series:
        return None
    return series, years


def _ratiosToWide(rs, years: list[str]) -> pl.DataFrame | None:
    """RatioSeriesResult → ``[ratio, label, *period]`` wide (period 최신 좌측, RATIO_CATEGORIES 순서)."""
    ratioDict = toSeriesDict(rs)[0]["RATIO"]
    if not ratioDict:
        return None
    ordered = [f for _, fields in RATIO_CATEGORIES for f in fields if f in ratioDict]
    rows: list[dict] = []
    for field in ordered:
        vals = ratioDict[field]
        rec: dict = {"ratio": field, "label": RATIO_FIELD_LABELS.get(field, field)}
        for i, y in enumerate(years):
            rec[y] = vals[i] if i < len(vals) else None
        rows.append(rec)
    if not rows:
        return None
    wide = pl.DataFrame(rows)
    periodCols = sorted((c for c in wide.columns if c not in ("ratio", "label")), reverse=True)
    return wide.select(["ratio", "label", *periodCols])


def readRatios(
    code: str,
    *,
    freq: str = "quarter",
    scope: str | None = None,
    marketNs: str = "kr",
    periods: list[str] | None = None,
) -> pl.DataFrame | None:
    """native 재무비율 — BS/IS/CF native statement 항목으로 core 공식 산출 (panel 자급, docs 0).

    ``readStatement``(bs/is/cf, XBRL+옛 통합 전기간) 의 항목을 core mappings 로 snakeId series 로 조립 →
    ``core.ratios.calcRatioSeries`` (공식 SSOT) → 비율 wide. 공식·매핑·파서·라벨 전부 core(L0) 호출,
    panel 재구현 0. native 5표 과거연장 덕에 finance(``c.panel("RATIOS")``)보다 깊은 history.

    Args:
        code: 종목코드.
        freq: "year"(연, yoyLag=1) / "quarter"(분기, yoyLag=4) / "ytd"(누적). 기본 quarter (raw 격자와 동일 입도).
        scope: "consolidated" / "standalone". 기본 consolidated.
        marketNs: 시장 namespace.
        periods: 특정 filing period parquet 만 (prune). None=전체.

    Returns:
        wide DataFrame — 행=(ratio snakeId, label 한글), 열=period(최신 좌측), cell=비율값. 재료 없으면 None.

    Raises:
        없음 — artifact/재료 부재 시 None.

    Example:
        >>> readRatios("005930", freq="year")  # doctest: +SKIP  — ROE/부채비율 × 연도

    SeeAlso:
        - ``readStatement`` — 재료 native 재무제표(bs/is/cf).
        - ``core.ratios.calcRatioSeries`` / ``toSeriesDict`` — 비율 공식·시계열 dict SSOT.
        - ``core.ratioCategories.RATIO_FIELD_LABELS`` — 비율 한글 라벨 SSOT.

    Requires:
        - polars. data/dart/panel/{code}.parquet. core(L0) 공식·매핑.

    Capabilities:
        - native 재무제표 항목만으로 재무비율 — 외부 price 0 → 밸류에이션 제외 statement-only.

    Guide:
        - ``c.panel("ratios")`` 소문자 → 본 함수(native). 대문자 RATIOS 는 finance(파사드).

    AIContext:
        - 상태 없는 read. 공식·매핑·파서 core SSOT 호출(농장 0). 매핑 갭은 core accountMappings.json 보강.

    When:
        - native 재무비율을 깊은 기간으로 볼 때.

    How:
        - bs/is/cf readStatement → _assembleRatioSeries(snakeId series) → calcRatioSeries → _ratiosToWide.

    LLM Specifications:
        AntiPatterns:
            - 비율 공식·snakeId 매핑 재구현 금지(농장) — core SSOT 호출만.
            - lxml import 금지(R2). finance/company import 금지(R1). panel.parquet contentRaw 만 소비(R3).
        OutputSchema:
            - ``pl.DataFrame | None`` ([ratio, label, *period]).
        Prerequisites:
            - panel.parquet 5표 contentRaw + core 번들 리소스.
        Freshness:
            - 매 read.
        Dataflow:
            - readStatement×3 → snakeId series → calcRatioSeries → wide.
        TargetMarkets:
            - KR (DART).
    """
    # panel.parquet 1회 파싱 후 bs/is/cf 를 캐시 셀에서 해소 (readStatement×3 = 파싱 3회 중복 회피).
    cells = _cellsFromPanel(code, marketNs, periods)
    if cells is None:
        return None
    statements = {
        sjKey: _resolveStatement(cells, variants=STATEMENT_VARIANTS[key], freq=freq, scope=scope)
        for sjKey, key in _RATIO_SOURCE.items()
    }
    assembled = _assembleRatioSeries(statements)
    if assembled is None:
        return None
    series, years = assembled
    rs = calcRatioSeries(series, years, yoyLag=(4 if freq == "quarter" else 1))
    return _ratiosToWide(rs, years)
