"""strategy 빌더 공통 유틸."""

from __future__ import annotations

import re
from dataclasses import dataclass

import polars as pl

_TRIANGLE_RE = re.compile(r"[△▲\u25B3\u25B2]")


def parseNumStr(s: str | None) -> float | None:
    """문자열 숫자를 float로 변환. 콤마, △(마이너스), % 처리."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or s == "-":
        return None
    negative = False
    if _TRIANGLE_RE.match(s):
        negative = True
        s = _TRIANGLE_RE.sub("", s)
    s = s.replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        v = float(s)
        return -v if negative else v
    except ValueError:
        return None


def periodCols(df: pl.DataFrame) -> list[str]:
    """DataFrame에서 기간 컬럼만 추출 (최신 먼저)."""
    from dartlab.core.show import isPeriodColumn

    return [c for c in df.columns if isPeriodColumn(c)]


def annualCols(df: pl.DataFrame, maxYears: int = 8) -> list[str]:
    """연도 컬럼만 추출 (Q4 또는 연도)."""
    cols = periodCols(df)
    annual = [c for c in cols if "Q" not in c]
    if annual:
        return annual[:maxYears]
    return [c for c in cols if c.endswith("Q4")][:maxYears]


def quarterlyCols(df: pl.DataFrame, maxQuarters: int = 8) -> list[str]:
    """분기 컬럼만 추출 (최신 먼저)."""
    cols = periodCols(df)
    return [c for c in cols if "Q" in c][:maxQuarters]


def fetchNotesDetail(company, noteKeys: list[str]) -> dict[str, list[dict]]:
    """company.notes에서 noteKeys의 DataFrame을 dict 리스트로 반환.

    실패 시 해당 키를 건너뜀 (안전). to_dicts()로 즉시 변환하여
    DataFrame 참조를 해제.
    """
    result: dict[str, list[dict]] = {}
    notesAccessor = getattr(company, "_notesAccessor", None) or getattr(company, "notes", None)
    if notesAccessor is None:
        return result
    for key in noteKeys:
        try:
            df = getattr(notesAccessor, key, None)
            if df is not None and hasattr(df, "to_dicts"):
                result[key] = df.to_dicts()
        except (AttributeError, FileNotFoundError, ValueError, KeyError):
            pass
    return result


MAX_RATIO_YEARS = 8


def getRatioSeries(company) -> tuple[dict, list[str]] | None:
    """ratioSeries 를 안전하게 가져온다 (private internal helper)."""
    try:
        result = company._ratioSeries()
        if result is None:
            return None
        return result
    except (ValueError, KeyError, AttributeError):
        return None


def mergeRows(primary: dict | None, fallback: dict | None) -> dict:
    """두 행을 merge. primary의 값이 None이면 fallback 값 사용."""
    if primary is None and fallback is None:
        return {}
    if primary is None:
        return fallback or {}
    if fallback is None:
        return primary
    merged = dict(primary)
    for k, v in fallback.items():
        if merged.get(k) is None and v is not None:
            merged[k] = v
    return merged


def getRatios(company):
    """ratios DataFrame 을 안전하게 가져온다 — c.show("ratios") 위임."""
    try:
        return company.show("ratios")
    except (ValueError, KeyError, AttributeError):
        return None


def toDict(selectResult, maxPeriods: int = 0) -> tuple[dict[str, dict], list[str]] | None:
    """SelectResult → ({계정명: {period: val}}, periodCols).

    ``toDictBySnakeId`` 가 한국어 라벨도 키로 노출하므로 이 함수는 deprecated thin
    wrapper. 신규 코드는 ``toDictBySnakeId`` 사용.

    maxPeriods=0이면 전체 기간, >0이면 최신 N개만.
    EDGAR DataFrame(account 컬럼 = snakeId)일 때 키를 한국어 라벨로 자동 변환하여
    analysis 함수에서 data.get("매출액") 등이 양쪽 provider에서 동일하게 작동한다.
    """
    if selectResult is None:
        return None

    df = selectResult.df
    periods = sorted(periodCols(df), reverse=True)
    if maxPeriods > 0:
        periods = periods[:maxPeriods]
    if not periods:
        return None

    labelCol = "계정명" if "계정명" in df.columns else (df.columns[0] if df.columns else None)
    if labelCol is None:
        return None

    # EDGAR bridge: snakeId 키 → 한국어 라벨 키로 변환 (analysis 함수 호환)
    needsBridge = labelCol != "계정명" and "계정명" not in df.columns
    krLabels: dict[str, str] | None = None
    if needsBridge:
        from dartlab.core.finance.labels import get_korean_labels

        krLabels = get_korean_labels()

    data: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        label = str(row.get(labelCol, ""))
        # snakeId → 한국어 키 변환 (EDGAR)
        key = krLabels.get(label, label) if krLabels else label
        data[key] = {c: row.get(c) for c in periods}
    if not data:
        return None
    # 분기에서 연간 합성 — SSOT 헬퍼 위임 (core/finance/flow.py)
    from dartlab.core.finance.flow import synthesizeAnnualFromQuarters

    periods = synthesizeAnnualFromQuarters(data, periods, getattr(selectResult, "topic", None))
    return (data, periods)


def toDictBySnakeId(selectResult, maxPeriods: int = 0) -> tuple[dict[str, dict], list[str]] | None:
    """SelectResult → ({snakeId: {period: val}}, periodCols).

    toDict와 동일하되, 키를 snakeId 컬럼으로 사용한다.
    snakeId로 select한 뒤 .get()도 snakeId로 접근할 때 사용.

    ``SNAKEID_ALIASES`` 의 alias key 도 같은 데이터로 자동 노출.
    예: ``data.get("liabilities")`` 가 있으면 ``data.get("total_liabilities")``
    도 같은 값 반환. EDGAR↔DART snakeId 차이를 calc 함수가 무시할 수 있다.
    """
    if selectResult is None:
        return None

    df = selectResult.df
    periods = sorted(periodCols(df), reverse=True)
    if maxPeriods > 0:
        periods = periods[:maxPeriods]
    if not periods:
        return None

    idCol = "snakeId" if "snakeId" in df.columns else None
    if idCol is None:
        return toDict(selectResult, maxPeriods)

    # 한국어 라벨도 함께 키로 노출 (toDict 와 단일 경로 통합).
    # data.get("매출액") 와 data.get("sales") 둘 다 같은 row 반환.
    labelCol = "계정명" if "계정명" in df.columns else None

    data: dict[str, dict] = {}
    for row in df.iter_rows(named=True):
        sid = str(row.get(idCol, ""))
        rowData = {c: row.get(c) for c in periods}
        data[sid] = rowData
        if labelCol:
            label = str(row.get(labelCol, ""))
            if label and label != sid:
                data[label] = rowData

    if not data:
        return None

    # 연간 합성 — SSOT 헬퍼 위임 (toDict 와 동일 경로)
    from dartlab.core.finance.flow import synthesizeAnnualFromQuarters

    periods = synthesizeAnnualFromQuarters(data, periods, getattr(selectResult, "topic", None))

    # SNAKEID_ALIASES 머지 + 양방향 노출 — SSOT 헬퍼 위임 (core/finance/labels.py).
    # 두 키 모두 row 가 존재하면 col 별 not-null 머지, 한쪽만 존재하면 다른 쪽도
    # 같은 row 를 가리키도록 노출하여 calc 가 어느 쪽 키로도 접근 가능.
    from dartlab.core.finance.labels import SNAKEID_ALIASES, mergeAliasRows

    mergeAliasRows(data, metaCols=set())  # dict 머지 — 메타 컬럼 없음
    for alias, canonical in SNAKEID_ALIASES.items():
        canonRow = data.get(canonical)
        aliasRow = data.get(alias)
        if canonRow is not None and aliasRow is None:
            data[alias] = canonRow
        elif aliasRow is not None and canonRow is None:
            data[canonical] = aliasRow

    return (data, periods)


# ── basePeriod 인프라 ──

_QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")
_YEAR_RE = re.compile(r"^(\d{4})$")


@dataclass(frozen=True)
class PeriodRange:
    """basePeriod로부터 결정된 분석 기간 범위."""

    basePeriod: str
    annualCols: list[str]
    quarterlyCols: list[str]


def _periodSortKey(p: str) -> str:
    """기간 문자열을 정렬 가능한 키로 변환. "2024" -> "2024Q5", "2024Q3" -> "2024Q3"."""
    if "Q" not in p:
        return p + "Q5"
    return p


def annualColsFromPeriods(
    periods: list[str],
    basePeriod: str | None = None,
    maxYears: int = 8,
) -> list[str]:
    """기간 목록에서 연간 컬럼 추출 — basePeriod 이하만.

    14개 파일의 _annualCols를 대체하는 통합 함수.
    연도("2024") 우선, 없으면 Q4("2024Q4") fallback.
    basePeriod=None이면 전체에서 최신 maxYears개.
    basePeriod="2022Q4"이면 2022Q4 이하에서 maxYears개.
    basePeriod="2022"이면 2022 이하 연도에서 maxYears개.
    """
    cols = sorted([c for c in periods if "Q" not in c], reverse=True)
    if not cols:
        cols = sorted([c for c in periods if c.endswith("Q4")], reverse=True)
    if basePeriod is not None:
        limit = _periodSortKey(basePeriod)
        cols = [c for c in cols if _periodSortKey(c) <= limit]
    return cols[:maxYears]


def annualLabel(period: str) -> str:
    """연간 기간 표시용 라벨. Q4 fallback 컬럼의 접미사를 제거한다.

    "2025Q4" -> "2025", "2025" -> "2025", "2025Q3" -> "2025Q3" (분기는 유지)
    """
    if period.endswith("Q4"):
        return period[:-2]
    return period


# 차입금 snakeId 후보 리스트 — 회사마다 다른 변형 모두 합산.
# 분리 키 (단/장기) + 통합 키 (borrowings).
# SNAKEID_ALIASES 가 자동으로 short_term_borrowings/long_term_borrowings 같은
# 변형을 canonical 키 (shortterm_borrowings/longterm_borrowings) 로 매핑하므로
# 여기선 canonical 만 나열한다 (변형 키 중복 합산 방지).
_BORROWING_KEYS = (
    "shortterm_borrowings",
    "longterm_borrowings",
    "noncurrent_borrowings",  # 비유동/장기 변형 (LG에솔)
    "current_portion_of_longterm_borrowings",  # 유동성장기차입금
    "borrowings",  # 통합 (SK하이닉스)
)
_BOND_KEYS = ("debentures", "bonds_payable", "current_portion_of_debentures")

# 매출원가 분리 키 (제품/상품/공사/용역원가)
_COGS_KEYS = (
    "cost_of_sales",
    "cost_of_goods_sold",
    "product_cost_of_sales",
    "merchandise_cost_of_sales",
    "construction_cost_of_sales",
    "service_cost_of_sales",
)

# 판관비 분리 키 (판매비/관리비)
_SGA_KEYS = (
    "selling_and_administrative_expenses",
    "selling_expenses",
    "administrative_expenses",
    "sga",
)

# 법인세 분리 키 (당기/이연)
_INCOME_TAX_KEYS = (
    "income_taxes",
    "income_tax_expense",
    "current_income_tax_expense",
    "deferred_income_tax_expense",
)


def _sumWithFallback(snakeData: dict, col: str, separateKeys: tuple, fallbackKey: str) -> float:
    """분리 키 우선 합산, 모두 결손이면 통합 키 fallback. None vs 0 구분."""
    parts = []
    for sid in separateKeys:
        if sid == fallbackKey:
            continue
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)
    if not parts:
        v = snakeData.get(fallbackKey, {}).get(col)
        if v is not None:
            parts.append(v)
    return sum(parts)


def sumBorrowings(snakeData: dict, col: str) -> float:
    """차입금 합산 — 회사 키 패턴 무관.

    snakeData 는 toDictBySnakeId 결과. 단/장기 분리 키 우선 합산하되,
    분리 키가 모두 0/None 이면 통합 borrowings 키 fallback.
    bonds 는 별도로 _BOND_KEYS 에서 추가.
    """
    parts = []
    for sid in _BORROWING_KEYS:
        if sid == "borrowings":
            continue  # 통합 키는 fallback 으로만 사용
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)

    # 분리 키가 모두 비어있으면 통합 borrowings fallback
    if not parts:
        v = snakeData.get("borrowings", {}).get(col)
        if v is not None:
            parts.append(v)

    # 사채 추가
    for sid in _BOND_KEYS:
        v = snakeData.get(sid, {}).get(col)
        if v is not None and v != 0:
            parts.append(v)

    return sum(parts)


def sumCostOfSales(snakeData: dict, col: str) -> float:
    """매출원가 합산 — 제품/상품/공사/용역원가 분리 키 fallback."""
    return _sumWithFallback(snakeData, col, _COGS_KEYS, "cost_of_sales")


def sumSGA(snakeData: dict, col: str) -> float:
    """판매관리비 합산 — 판매비/관리비 분리 키 fallback."""
    return _sumWithFallback(snakeData, col, _SGA_KEYS, "selling_and_administrative_expenses")


def sumIncomeTax(snakeData: dict, col: str) -> float:
    """법인세 합산 — 당기/이연 분리 키 fallback."""
    return _sumWithFallback(snakeData, col, _INCOME_TAX_KEYS, "income_taxes")


# 한국어 키 dict 용 차입금 합산 (credit/metrics.py 가 위임).
_KR_BORROWING_SHORT = ("단기차입금", "차입금단기", "short_term_borrowings")
_KR_BORROWING_LONG = ("장기차입금", "long_term_borrowings")
_KR_BORROWING_UNIFIED = ("차입부채", "차입금", "장기차입부채", "유동성장기차입금")


def sumBorrowingsKorean(bsData: dict, col: str) -> tuple[float, float, float]:
    """한국어 키 BS dict 의 차입금 합산.

    credit/metrics.py 처럼 toDict 결과(한국어 키 dict)를 받아
    (단기차입금, 장기차입금, 통합 fallback) 형태로 분해 반환.

    Returns:
        (stBorrow, ltBorrow, totalBorrowing) — 분리/통합 fallback 적용 후
    """
    stb = 0.0
    for k in _KR_BORROWING_SHORT:
        v = bsData.get(k, {}).get(col)
        if v is not None:
            stb = float(v)
            break

    ltb = 0.0
    for k in _KR_BORROWING_LONG:
        v = bsData.get(k, {}).get(col)
        if v is not None:
            ltb = float(v)
            break

    # Fallback: 분리 키 모두 0/None → 통합 키 (audit 04 #B)
    if stb == 0 and ltb == 0:
        for k in _KR_BORROWING_UNIFIED:
            v = bsData.get(k, {}).get(col)
            if v is not None:
                stb = float(v)  # 통합값을 stb 에 1번만 (credit 호환)
                break

    bondsVal = bsData.get("사채", {}).get(col) or 0
    total = stb + ltb + float(bondsVal)
    return stb, ltb, total


def annualLabels(periods: list[str]) -> dict[str, str]:
    """연간 기간 컬럼 → 표시 라벨 매핑. 테이블 렌더링에서 헤더 치환용."""
    return {p: annualLabel(p) for p in periods}


def quarterlyColsFromPeriods(
    periods: list[str],
    basePeriod: str | None = None,
    maxQuarters: int = 8,
) -> list[str]:
    """기간 목록에서 분기 컬럼 추출 — basePeriod 이하만."""
    qs = sorted([c for c in periods if "Q" in c], reverse=True)
    if not qs:
        # EDGAR fallback: 연간 데이터 (2024, 2023, ...)
        qs = sorted([c for c in periods if c.isdigit() and len(c) == 4], reverse=True)
    if basePeriod is not None:
        limit = _periodSortKey(basePeriod)
        qs = [c for c in qs if _periodSortKey(c) <= limit]
    return qs[:maxQuarters]


def resolveBasePeriod(
    company,
    basePeriod: str | None = None,
    maxYears: int = 8,
    maxQuarters: int = 8,
) -> PeriodRange:
    """basePeriod를 Company의 실제 기간으로 해석.

    basePeriod=None이면 최신 기간 자동 감지.
    ratioSeries 캐시를 활용하여 속도 우선.
    """
    rs = getRatioSeries(company)
    if rs is not None:
        _, allPeriods = rs
    else:
        allPeriods = []

    if basePeriod is None:
        qs = sorted([p for p in allPeriods if "Q" in p], reverse=True)
        resolved = qs[0] if qs else "9999Q4"
    else:
        resolved = basePeriod

    return PeriodRange(
        basePeriod=resolved,
        annualCols=annualColsFromPeriods(allPeriods, resolved, maxYears),
        quarterlyCols=quarterlyColsFromPeriods(allPeriods, resolved, maxQuarters),
    )
