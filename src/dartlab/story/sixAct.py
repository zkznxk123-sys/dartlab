"""6 막 인과 (macro·sector·firm·financial·value·risk) 종합 점수.

dartlab 의 4 가지 비교 가능성 중 "회사간" 의 단일 시각화를 위한 0~100 점수.
landing/company hero radar 와 viz ``spec_six_act_radar`` 의 데이터원.

축 정의:

- **macro**: 거시 환경이 회사에 우호적인가 (금리·환율·경기 사이클).
- **sector**: 산업 위치가 좋은가 (산업 구조·점유·성장률).
- **firm**: 기업 자체 경쟁력 (제품·시장지배·경영진·지배구조).
- **financial**: 재무 건전성 (수익성·성장성·안정성·이익품질).
- **value**: 가치평가 위치 (PER/PBR/EV-EBITDA 백분위·DCF 안전마진).
- **risk**: 리스크 (재무 distress·공시 변화·리스크 신호).

각 축의 점수는 0~100. 100 = 가장 좋음, 0 = 가장 나쁨. risk 축도 동일 방향
(점수 높을수록 리스크 낮음).

각 축의 evidence 는 evidenceIds list — landing/EvidencePanel 이 같은 키를
들고 있는 row 와 join 한다. 본격 evidence 회로 (rcept_no 까지) 는 Phase 2 의
viz refs 와 정합.

본 모듈은 분산된 엔진 (analysis/credit/industry/quant/macro) 출력을 안전하게
조회한다 — 데이터가 없으면 None 반환 (값 추정 금지).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SixActScore:
    """6 축 종합 점수 + 축별 evidence + 축별 코멘트."""

    stockCode: str
    corpName: str = ""
    macro: float | None = None
    sector: float | None = None
    firm: float | None = None
    financial: float | None = None
    value: float | None = None
    risk: float | None = None
    evidence: dict[str, list[str]] = field(default_factory=dict)
    notes: dict[str, str] = field(default_factory=dict)
    coverage: dict[str, str] = field(default_factory=dict)

    AXES = ("macro", "sector", "firm", "financial", "value", "risk")

    def asDict(self) -> dict[str, Any]:
        """spec_six_act_radar 가 받는 형태."""
        return {
            "stockCode": self.stockCode,
            "corpName": self.corpName,
            "score": {axis: getattr(self, axis) for axis in self.AXES},
            "evidence": dict(self.evidence),
            "notes": dict(self.notes),
            "coverage": dict(self.coverage),
        }

    def asScoreDict(self) -> dict[str, float | None]:
        """6 축 점수만 — spec_six_act_radar(score=...) 의 score 인자."""
        return {axis: getattr(self, axis) for axis in self.AXES}


# ── 점수 변환 helper ───────────────────────────────────────────────────────


_GRADE_TO_SCORE = {"A": 92.0, "B": 78.0, "C": 64.0, "D": 48.0, "F": 28.0}


def _gradeScore(grade: str | None) -> float | None:
    if grade is None:
        return None
    return _GRADE_TO_SCORE.get(str(grade).upper())


def _clip(v: float | None, lo: float = 0.0, hi: float = 100.0) -> float | None:
    if v is None:
        return None
    return max(lo, min(hi, float(v)))


# ── 축별 점수 함수 ─────────────────────────────────────────────────────────


def _financialScore(c: Any) -> tuple[float | None, list[str], str]:
    """financial 축 — 수익성 + 성장성 + 안정성 + 이익품질의 가중평균.

    AnalysisResult.grades() 의 7 영역 중 (profitability, performance, health,
    cashflow) 4 영역 평균. evidence: ``analysis:insights:grades``.
    """
    insights = getattr(c, "insights", None)
    if insights is None:
        return None, [], "analysis 인사이트 미수집"
    weights = [
        ("profitability", 0.30),
        ("performance", 0.30),
        ("health", 0.25),
        ("cashflow", 0.15),
    ]
    parts: list[tuple[float, float]] = []
    for name, w in weights:
        area = getattr(insights, name, None)
        score = _gradeScore(getattr(area, "grade", None) if area is not None else None)
        if score is not None:
            parts.append((score, w))
    if not parts:
        return None, [], "등급 데이터 없음"
    total_w = sum(w for _, w in parts) or 1.0
    score = sum(s * w for s, w in parts) / total_w
    return _clip(score), ["analysis:insights:grades"], f"4 영역 가중평균 ({len(parts)}/4 채움)"


def _riskScore(c: Any) -> tuple[float | None, list[str], str]:
    """risk 축 — credit DistressResult 의 신용등급 매핑 + 7 영역의 risk 등급.

    100 = 가장 안전. credit grade AAA→100, A→85, BBB→70, BB→55, B→40, CCC→25,
    CC→15, D→5. analysis 의 risk 영역 grade 와 평균.
    """
    sub_scores: list[float] = []
    refs: list[str] = []
    notes: list[str] = []

    insights = getattr(c, "insights", None)
    if insights is not None:
        risk_area = getattr(insights, "risk", None)
        riskScore = _gradeScore(getattr(risk_area, "grade", None) if risk_area else None)
        if riskScore is not None:
            sub_scores.append(riskScore)
            refs.append("analysis:insights:risk")

    try:
        credit = c.credit() if callable(getattr(c, "credit", None)) else None
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        credit = None
    if credit is not None:
        # DistressResult 가 grade 또는 creditGrade 속성을 가진다.
        cg = getattr(credit, "creditGrade", None) or getattr(credit, "grade", None)
        cg_map = {
            "AAA": 100,
            "AA": 92,
            "A": 84,
            "BBB": 72,
            "BB": 58,
            "B": 44,
            "CCC": 30,
            "CC": 18,
            "C": 12,
            "D": 4,
        }
        if cg and str(cg).upper() in cg_map:
            sub_scores.append(float(cg_map[str(cg).upper()]))
            refs.append("credit:distress")

    if not sub_scores:
        return None, [], "credit/risk 데이터 없음"
    notes.append(f"평균 ({len(sub_scores)} 소스)")
    return _clip(sum(sub_scores) / len(sub_scores)), refs, "; ".join(notes)


def _firmScore(c: Any) -> tuple[float | None, list[str], str]:
    """firm 축 — analysis 의 governance + opportunity 평균."""
    insights = getattr(c, "insights", None)
    if insights is None:
        return None, [], "analysis 인사이트 미수집"
    parts: list[float] = []
    for name in ("governance", "opportunity"):
        area = getattr(insights, name, None)
        s = _gradeScore(getattr(area, "grade", None) if area else None)
        if s is not None:
            parts.append(s)
    if not parts:
        return None, [], "governance/opportunity 등급 없음"
    return _clip(sum(parts) / len(parts)), ["analysis:insights:firm"], f"{len(parts)} 영역 평균"


def _sectorScore(c: Any) -> tuple[float | None, list[str], str]:
    """sector 축 — industry 위치. industry() 의 marketShareRank 또는 산업 내
    매출 랭킹을 백분위로 변환. 데이터가 없으면 None.
    """
    try:
        ind = c.industry() if callable(getattr(c, "industry", None)) else None
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        ind = None
    if not ind or not isinstance(ind, dict):
        return None, [], "industry 데이터 없음"
    # 가능한 필드 후보들.
    rank = ind.get("rank") or ind.get("marketShareRank")
    total = ind.get("total") or ind.get("industrySize") or ind.get("peerCount")
    if rank is not None and total and total > 0:
        # rank 1 = 최상위 → 100. rank N = 최하위 → 0.
        pct = max(0.0, 100.0 - (float(rank) - 1) / float(total) * 100.0)
        return _clip(pct), ["industry:position"], f"산업 내 {rank}/{total} 위"
    return None, [], "rank/total 미산출"


def _macroScore(c: Any) -> tuple[float | None, list[str], str]:
    """macro 축 — 현재 단계: 데이터 없음 (None).

    macro 엔진이 단일 회사 단위 점수를 제공하지 않는다. Phase 3-2 에서
    business cycle quadrant + 회사 매크로 민감도 계산 후 채울 자리.
    """
    return None, [], "macro 단계 평가 함수 미구현 (회사 민감도 매핑 대기)"


def _valueScore(c: Any) -> tuple[float | None, list[str], str]:
    """value 축 — quant 의 PER/PBR 백분위 또는 DCF 안전마진.

    quant() 결과가 없으면 None.
    """
    try:
        q = c.quant() if callable(getattr(c, "quant", None)) else None
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        q = None
    if q is None:
        return None, [], "quant 데이터 없음"
    # quant 결과는 다양한 형태일 수 있다 — dict 또는 dataclass.
    per_pct = None
    if isinstance(q, dict):
        per_pct = q.get("perPercentile") or q.get("per_pct") or q.get("valuePercentile")
    else:
        per_pct = getattr(q, "perPercentile", None) or getattr(q, "valuePercentile", None)
    if per_pct is None:
        return None, [], "valuation 백분위 필드 없음"
    # PER 백분위가 낮을수록 (저평가) value 점수 높다 → 100 - pct.
    score = 100.0 - float(per_pct)
    return _clip(score), ["quant:valuation"], f"PER 백분위 {per_pct:.0f}%"


# ── 진입점 ─────────────────────────────────────────────────────────────────


def sixActScore(c: Any) -> SixActScore:
    """Company → 6 축 종합 점수.

    데이터가 없는 축은 None 으로 둔다 (값 추정 금지). landing 측에서 None
    축은 점선/회색 처리.

    Args:
        c: Company facade (dartlab.Company(stockCode)).

    Returns:
        SixActScore — 6 축 점수 + evidence ids + 축별 coverage 노트.
    """
    stockCode = getattr(c, "stockCode", "")
    corpName = getattr(c, "corpName", "")
    out = SixActScore(stockCode=stockCode, corpName=corpName)

    for axis, fn in (
        ("macro", _macroScore),
        ("sector", _sectorScore),
        ("firm", _firmScore),
        ("financial", _financialScore),
        ("value", _valueScore),
        ("risk", _riskScore),
    ):
        try:
            score, refs, note = fn(c)
        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError) as e:
            score, refs, note = None, [], f"{type(e).__name__}: {e}"
        setattr(out, axis, score)
        if refs:
            out.evidence[axis] = refs
        out.notes[axis] = note
        out.coverage[axis] = "ready" if score is not None else "missing"

    return out
