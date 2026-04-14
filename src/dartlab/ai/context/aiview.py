"""AI용 데이터 맥락 보강 — 엔진 반환값을 AI가 이해하기 좋은 형태로 변환.

모든 엔진의 dict/DataFrame을 자동 감지해서 맥락을 보강한다.
엔진별 수작업 0 — 구조(history + period + 숫자)만 보고 판단.

삽입 위치: _calcToContextPart()에서 encodeAuto() 직전.
    calc result → **autoEnrich()** → encodeAuto(TOON) → ContextPart

근거:
- Kim et al. (시카고대, 2024): 재무제표 + 맥락 → 이익 방향 60% 정확도
- TAP4LLM (EMNLP 2024): 서브테이블 + 보강 → +7.93%p
- 실험 110 A/B: enriched가 raw 대비 코드 0라운드, 해석 명확성 압도

Examples::

    # analysis calc 결과
    raw = calcMarginTrend(company)
    # {"history": [{"period": "2025", "operatingMargin": 13.07, ...}, ...]}

    enriched = autoEnrich(raw)
    # {"_summary": "영업이익률 13.1% · 전기비 +2.2pp(소폭 개선) · 5년평균 위 1.2pp",
    #  "history": [...],  ← 원본 유지
    #  "_context": {"marginTrend": {"avg5y": 11.86, "yoy_pp": +2.19, ...}}}
"""

from __future__ import annotations

from typing import Any

# ── 비율 필드 감지 키워드 ─────────────────────────────────

_RATIO_KEYWORDS = frozenset(
    {
        "margin",
        "ratio",
        "rate",
        "roe",
        "roa",
        "roic",
        "turnover",
        "pct",
        "yield",
        "percent",
        "coverage",
        "leverage",
        "yoy",
        "dso",
        "dio",
        "dpo",
        "ccc",
        "dol",
        "payout",
    }
)


def _isRatioField(field: str, value: Any) -> bool:
    """비율 필드인지 판단 (이름 + 값 범위)."""
    lower = field.lower()
    if any(kw in lower for kw in _RATIO_KEYWORDS):
        return True
    # 값이 -200~500 범위이고 float이면 비율일 가능성
    if isinstance(value, (int, float)) and -200 <= value <= 500:
        # 금액은 보통 1e6 이상
        return abs(value) < 1e6
    return False


# ── 변화 판단 ─────────────────────────────────────────────


def _judgeChange(delta: float | None, isRatio: bool) -> str:
    if delta is None:
        return ""
    t = 1.0 if isRatio else 5.0
    if abs(delta) < t * 0.5:
        return "보합"
    elif abs(delta) < t * 2:
        return "소폭 개선" if delta > 0 else "소폭 악화"
    elif abs(delta) < t * 5:
        return "개선" if delta > 0 else "악화"
    else:
        return "대폭 개선" if delta > 0 else "대폭 악화"


# ── 한글 필드명 ───────────────────────────────────────────

_KOREAN = {
    "operatingMargin": "영업이익률",
    "netMargin": "순이익률",
    "grossMargin": "매출총이익률",
    "roe": "ROE",
    "roa": "ROA",
    "roic": "ROIC",
    "revenue": "매출",
    "operatingIncome": "영업이익",
    "netIncome": "순이익",
    "debtRatio": "부채비율",
    "equityRatio": "자기자본비율",
    "ocf": "영업CF",
    "fcf": "FCF",
    "capex": "CAPEX",
    "ccc": "CCC",
    "dso": "매출채권회수일",
    "dio": "재고회전일",
    "dpo": "매입채무회전일",
    "totalAssetTurnover": "총자산회전율",
    "revenueYoy": "매출YoY",
    "operatingIncomeYoy": "영업이익YoY",
    "netIncomeYoy": "순이익YoY",
    "costOfSalesRatio": "매출원가율",
    "sgaRatio": "판관비율",
    "ocfToNi": "영업CF/순이익",
    "ocfMargin": "영업CF마진",
    "interestCoverage": "이자보상배율",
    "pattern": "CF패턴",
}


def _koreanName(field: str) -> str:
    return _KOREAN.get(field, field)


def _formatNum(value: Any, field: str = "") -> str:
    if value is None:
        return "-"
    if _isRatioField(field, value):
        return f"{value:.1f}%"
    if isinstance(value, (int, float)) and abs(value) > 1e12:
        return f"{value / 1e12:.1f}조"
    if isinstance(value, (int, float)) and abs(value) > 1e8:
        return f"{value / 1e8:,.0f}억"
    if isinstance(value, float):
        return f"{value:,.1f}"
    return str(value)


# ── 핵심: autoEnrich ─────────────────────────────────────


def autoEnrich(data: dict | list | None, *, company: Any = None, calc_fn: Any = None) -> dict | list | None:
    """엔진 반환값을 자동 감지해서 AI용 맥락 보강.

    3가지 패턴 자동 감지:
    - dict with history[] → 시계열 보강 (5년 평균, YoY, 판단)
    - list[dict] → history 배열로 취급
    - flat dict → 핵심 필드 요약

    엔진이 새 축을 추가해도 history + period + 숫자 패턴만 유지하면 자동 적용.

    **assumptions 투명화**: data["assumptions"] 가 있으면 _summary 에 엔진 가정 한 줄 주입
    → AI 가 "엔진이 무슨 가정으로 계산했나" 즉시 인지 → override 재호출 판단.
    """
    if data is None:
        return None

    # list[dict] — history 배열 직접 전달된 경우
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return _enrichHistory(data)

    if not isinstance(data, dict):
        return data

    # 독스트링 스키마 추출 (있으면 확정 기반, 없으면 자동 감지 fallback)
    _schema = parseReturnsSchema(calc_fn) if callable(calc_fn) else None

    # 최상위에 바로 history[]가 있는 경우 (개별 calc 결과: {"history": [...], "displayHints": {...}})
    if "history" in data and isinstance(data["history"], list) and data["history"]:
        summary = _summarizeHistory(data["history"], "data", schema=_schema)
        if summary:
            enriched = dict(data)
            enriched["_summary"] = _withAssumptions(summary, data.get("assumptions"))
            return enriched
        return _maybeAddAssumptions(data)

    # 중첩 history — 전체 analysis dict: {"marginTrend": {"history": [...]}, ...}
    tsKeys = [
        k
        for k, v in data.items()
        if isinstance(v, dict) and "history" in v and isinstance(v["history"], list) and v["history"]
    ]
    if tsKeys:
        return _enrichDictWithHistory(data, tsKeys, company=company)

    # flat dict (숫자 키가 있는) — credit, quant
    numericKeys = [k for k, v in data.items() if isinstance(v, (int, float))]
    if numericKeys:
        return _enrichFlat(data)

    # assumptions 만 있는 경우 (순수 dict of dicts) 도 커버
    return _maybeAddAssumptions(data)


# ── assumptions 투명화 ──────────────────────────────────


def _formatAssumptions(assumptions: dict) -> str:
    """assumptions dict → AI 친화 한 줄 요약. override 재호출 유도 문구 포함."""
    if not isinstance(assumptions, dict) or not assumptions:
        return ""

    overridden = assumptions.get("_overridden") or []
    parts: list[str] = []
    # 우선 순위 키: wacc / terminalGrowth / primaryModel / debtRatio / cyclePhase / window
    _ORDER = (
        "wacc",
        "terminalGrowth",
        "primaryModel",
        "growthRates",
        "opm",
        "debtRatio",
        "interestCoverage",
        "currentRatio",
        "cyclePhase",
        "rateScenario",
        "window",
        "threshold",
        "period",
        "benchmark",
    )
    _LABEL = {
        "wacc": "WACC",
        "terminalGrowth": "g",
        "primaryModel": "주모델",
        "growthRates": "성장률",
        "opm": "OPM",
        "debtRatio": "부채비율",
        "interestCoverage": "ICR",
        "currentRatio": "유동비율",
        "cyclePhase": "사이클",
        "rateScenario": "금리시나리오",
        "window": "window",
        "threshold": "임계값",
        "period": "기간",
        "benchmark": "벤치마크",
    }
    for k in _ORDER:
        if k not in assumptions:
            continue
        v = assumptions[k]
        if v is None:
            continue
        label = _LABEL.get(k, k)
        if isinstance(v, (int, float)):
            # 비율 후보: 0~100 범위 + _ORDER 에 있는 rate 계열
            if k in ("wacc", "terminalGrowth", "opm", "debtRatio", "currentRatio", "quickRatio", "threshold"):
                parts.append(f"{label}={v:.1f}%")
            elif k in ("interestCoverage",):
                parts.append(f"{label}={v:.2f}x")
            elif k in ("window", "period"):
                parts.append(f"{label}={v}")
            else:
                parts.append(f"{label}={v:.2f}")
        elif isinstance(v, (list, tuple)):
            try:
                head = ", ".join(f"{x:.1f}" for x in v[:3] if isinstance(x, (int, float)))
                parts.append(f"{label}=[{head}{'...' if len(v) > 3 else ''}]")
            except (TypeError, ValueError):
                parts.append(f"{label}={v}")
        else:
            parts.append(f"{label}={v}")

    if not parts:
        return ""

    head = "[엔진가정] " + " · ".join(parts)
    if overridden:
        head += f" (override 적용: {', '.join(overridden)})"
    else:
        head += " (의심되면 overrides={…} 로 재호출)"
    return head


def _withAssumptions(summary: str, assumptions: dict | None) -> str:
    line = _formatAssumptions(assumptions) if assumptions else ""
    if not line:
        return summary
    return f"{summary}\n{line}" if summary else line


def _maybeAddAssumptions(data: dict) -> dict:
    """data 에 assumptions 가 있으면 _summary 필드에 한 줄 주입."""
    assumptions = data.get("assumptions") if isinstance(data, dict) else None
    line = _formatAssumptions(assumptions) if assumptions else ""
    if not line:
        return data
    enriched = dict(data)
    existing = enriched.get("_summary") or ""
    enriched["_summary"] = f"{existing}\n{line}".strip() if existing else line
    return enriched


# ── 패턴 1: dict with history[] ──────────────────────────


def _enrichDictWithHistory(
    data: dict,
    tsKeys: list[str],
    *,
    company: Any = None,
) -> dict:
    """history[] 시계열을 자동 보강. 모든 analysis 축에 범용 적용."""
    summaries: list[str] = []

    for tsKey in tsKeys:
        hist = data[tsKey]["history"]
        if not hist:
            continue
        summary = _summarizeHistory(hist, tsKey)
        if summary:
            summaries.append(summary)

    # _summary 필드에 전체 요약 삽입 (원본 data에 추가)
    enriched = dict(data)
    if summaries:
        enriched["_summary"] = " / ".join(summaries[:4])

    # assumptions 한 줄 주입 (있으면)
    return _maybeAddAssumptions(enriched)


def _enrichHistory(rows: list[dict]) -> dict:
    """history 배열 직접 전달 시."""
    summary = _summarizeHistory(rows, "data")
    return {"_summary": summary, "history": rows} if summary else {"history": rows}


def _summarizeHistory(hist: list[dict], label: str, *, schema: dict | None = None) -> str:
    """history 배열에서 비율 필드를 자동 감지, 핵심 3개의 요약문 생성."""
    if not hist or len(hist) < 2:
        return ""

    latest = hist[0]
    prev = hist[1]

    # 모든 숫자 필드 감지
    numericFields = [k for k, v in latest.items() if isinstance(v, (int, float)) and k != "period"]
    if not numericFields:
        return ""

    fieldInfos: list[dict] = []
    for field in numericFields:
        values = [h.get(field) for h in hist[:5] if h.get(field) is not None]
        if not values:
            continue

        current = values[0]
        # 독스트링 스키마 우선, 없으면 자동 감지 fallback
        schemaResult = isRatioBySchema(field, schema) if schema else None
        isRatio = schemaResult if schemaResult is not None else _isRatioField(field, current)
        prevVal = values[1] if len(values) >= 2 else None
        avg5 = sum(values) / len(values)

        # YoY — 비율은 pp 차이, 금액은 변화율(%)
        yoy = None
        if prevVal is not None:
            if isRatio:
                yoy = current - prevVal
            elif prevVal != 0:
                yoy = (current - prevVal) / abs(prevVal) * 100

        # 5년 평균 대비
        vsAvg = None
        if isRatio:
            vsAvg = current - avg5
        elif avg5 != 0:
            vsAvg = (current - avg5) / abs(avg5) * 100

        fieldInfos.append(
            {
                "field": field,
                "current": current,
                "isRatio": isRatio,
                "yoy": round(yoy, 2) if yoy is not None else None,
                "vsAvg": round(vsAvg, 2) if vsAvg is not None else None,
                "judgment": _judgeChange(yoy, isRatio),
                "avg5": round(avg5, 2),
            }
        )

    # 비율 필드 우선, 변화가 큰 순
    ratios = [f for f in fieldInfos if f["isRatio"]]
    amounts = [f for f in fieldInfos if not f["isRatio"]]
    picked = sorted(ratios, key=lambda x: abs(x["yoy"] or 0), reverse=True)[:3]
    if not picked:
        picked = sorted(amounts, key=lambda x: abs(x["yoy"] or 0), reverse=True)[:2]

    # 요약 문장 생성
    parts = []
    for fi in picked:
        unit = "pp" if fi["isRatio"] else "%"
        segs = [f"{_koreanName(fi['field'])} {_formatNum(fi['current'], fi['field'])}"]
        if fi["yoy"] is not None:
            segs.append(f"전기비 {fi['yoy']:+.1f}{unit}({fi['judgment']})")
        if fi["vsAvg"] is not None:
            pos = "위" if fi["vsAvg"] > 0 else "아래"
            segs.append(f"5년평균 {pos} {abs(fi['vsAvg']):.1f}{unit}")
        parts.append(" · ".join(segs))

    return f"[{label}] {' | '.join(parts)}" if parts else ""


# ── 패턴 2: flat dict ────────────────────────────────────


def _enrichFlat(data: dict) -> dict:
    """flat dict 보강 — credit, quant 결과."""
    summaryParts = []
    for k, v in data.items():
        if isinstance(v, str) and len(v) < 50:
            summaryParts.append(f"{_koreanName(k)}={v}")
        elif isinstance(v, (int, float)):
            summaryParts.append(f"{_koreanName(k)}={_formatNum(v, k)}")
    if not summaryParts:
        return data
    enriched = dict(data)
    enriched["_summary"] = " · ".join(summaryParts[:6])
    return enriched


# ── 독스트링 기반 스키마 파싱 ──────────────────────────────

import re
from functools import lru_cache
from typing import Callable

_UNIT_PATTERN = re.compile(r"\((%|원|일|배|점)\)")


@lru_cache(maxsize=256)
def parseReturnsSchema(fn: Callable) -> dict[str, dict] | None:
    """함수의 docstring에서 Returns 스키마를 파싱.

    Returns dict 예시::

        {
            "operatingMargin": {"type": "float", "unit": "%", "desc": "영업이익률"},
            "revenue": {"type": "float", "unit": "원", "desc": "매출"},
        }

    독스트링에 Returns 섹션이 없으면 None.
    """
    doc = getattr(fn, "__doc__", None)
    if not doc:
        return None

    # Returns 섹션 추출
    lines = doc.split("\n")
    inReturns = False
    returnsLines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "Returns":
            inReturns = True
            continue
        if inReturns and stripped.startswith("-------"):
            continue
        if inReturns:
            # 다른 섹션 시작 감지 (Raises, Examples, Notes, Guide, See Also)
            if (
                stripped
                and not stripped[0].isspace()
                and stripped[0] != " "
                and ":" not in stripped
                and stripped
                in (
                    "Raises",
                    "Examples",
                    "Notes",
                    "Guide",
                    "See Also",
                    "Parameters",
                )
            ):
                break
            # 빈 줄 다음에 섹션 헤더가 올 수 있음
            if stripped and re.match(r"^[A-Z][a-z]", stripped) and not any(c in stripped for c in (":", "—", "-")):
                break
            returnsLines.append(line)

    if not returnsLines:
        return None

    # 키 : 타입 — 설명 (단위) 패턴 파싱
    schema: dict[str, dict] = {}
    for line in returnsLines:
        # "    operatingMargin : float — 영업이익률 (%)" 패턴
        m = re.match(r"\s+(\w+)\s*:\s*(\w[\w\[\]]*)\s*[—-]\s*(.+)", line)
        if not m:
            continue
        key, typ, desc = m.group(1), m.group(2), m.group(3).strip()

        # 단위 추출
        unit_match = _UNIT_PATTERN.search(desc)
        unit = unit_match.group(1) if unit_match else None

        schema[key] = {"type": typ, "desc": desc, "unit": unit}

    return schema if schema else None


def isRatioBySchema(field: str, schema: dict[str, dict] | None) -> bool | None:
    """스키마에서 필드의 단위를 확인해서 비율인지 확정.

    Returns True(비율)/False(금액)/None(스키마에 없음 → fallback 필요).
    """
    if schema is None or field not in schema:
        return None
    unit = schema[field].get("unit")
    if unit == "%":
        return True
    if unit in ("원", "일"):
        return False
    return None
