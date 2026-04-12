"""제약·바이오 KPI — 임상 파이프라인/마일스톤/R&D 집중도.

DART sections(사업개요/주요제품) + IS(R&D비용) 활용.
"""

from __future__ import annotations

import re

from dartlab.analysis.financial._memoize import memoized_calc

_PHASE_PATTERNS = [
    (re.compile(r"(phase\s*3|임상\s*3상|3상)", re.IGNORECASE), "Phase III"),
    (re.compile(r"(phase\s*2|임상\s*2상|2상)", re.IGNORECASE), "Phase II"),
    (re.compile(r"(phase\s*1|임상\s*1상|1상)", re.IGNORECASE), "Phase I"),
    (re.compile(r"(전임상|비임상|preclinical)", re.IGNORECASE), "Preclinical"),
    (re.compile(r"(허가|승인|NDA|BLA)", re.IGNORECASE), "Approved"),
]

_POS_BY_PHASE = {
    "Preclinical": 0.05,
    "Phase I": 0.10,
    "Phase II": 0.15,
    "Phase III": 0.50,
    "Approved": 0.90,
}


@memoized_calc
def calcPharmaKpis(company, *, basePeriod: str | None = None) -> dict | None:
    """제약·바이오 핵심 KPI.

    Returns
    -------
    dict | None
        pipelineStages : dict — 임상 단계별 카운트 (sections 텍스트 키워드 추출)
        rdIntensity : dict | None — R&D/매출 비율
    """
    result: dict = {}

    # ── 파이프라인 단계별 감지 (사업개요/연구개발 텍스트) ──
    try:
        topics = ["사업의내용", "연구개발활동", "사업개요"]
        text = ""
        for topic in topics:
            try:
                df = company.show(topic)
                if df is not None:
                    if hasattr(df, "to_dicts"):
                        text += " ".join(str(r) for r in df.to_dicts())
                    else:
                        text += str(df)
            except (AttributeError, ValueError, KeyError):
                continue

        if text:
            stages: dict[str, int] = {}
            for pattern, phase in _PHASE_PATTERNS:
                count = len(pattern.findall(text))
                if count > 0:
                    stages[phase] = count

            if stages:
                weighted_pos = sum(_POS_BY_PHASE.get(p, 0) * c for p, c in stages.items())
                total_mentions = sum(stages.values())
                avg_pos = weighted_pos / total_mentions if total_mentions > 0 else 0

                result["pipelineStages"] = {
                    "stages": stages,
                    "totalMentions": total_mentions,
                    "avgPOS": round(avg_pos * 100, 1),
                    "note": "사업보고서 텍스트 키워드 기반 추정 — 정확한 파이프라인은 IR 자료 참조",
                }
    except (AttributeError, ValueError, TypeError):
        pass

    # ── R&D/매출 비율 ──
    try:
        from dartlab.analysis.financial._helpers import toDictBySnakeId
        from dartlab.core.finance.helpers import annualColsFromPeriods

        parsed = toDictBySnakeId(company.select("IS", ["sales", "research_and_development"]))
        if parsed:
            isData, periods = parsed
            yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=3)
            salesRow = isData.get("sales", {})
            rdRow = isData.get("research_and_development", {})

            history = []
            for col in yCols:
                rev = salesRow.get(col)
                rd = rdRow.get(col)
                if rev and rd and float(rev) > 0:
                    ratio = abs(float(rd)) / float(rev) * 100
                    history.append({"period": col, "rdToRevenue": round(ratio, 1)})

            if history:
                result["rdIntensity"] = {
                    "history": history,
                    "latest": history[-1]["rdToRevenue"],
                    "verdict": "고R&D"
                    if history[-1]["rdToRevenue"] > 20
                    else "중R&D"
                    if history[-1]["rdToRevenue"] > 10
                    else "저R&D",
                }
    except (AttributeError, ValueError, TypeError):
        pass

    return result if result else None
