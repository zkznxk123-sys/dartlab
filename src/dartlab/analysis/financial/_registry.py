"""Analysis financial 축 레지스트리 — facade. 본체는 `_registryTypes` / `_registryAxesA` / `_registryAxesB`.

15축 + 그룹 + alias + axis 해석. 내부 모듈. 외부는 `dartlab.analysis.financial.Analysis` 만 import.
"""

from __future__ import annotations

from dartlab.analysis.financial._registryAxesA import _AXES_A
from dartlab.analysis.financial._registryAxesB import _AXES_B
from dartlab.analysis.financial._registryTypes import _AxisEntry, _CalcEntry

_AXIS_REGISTRY: dict[str, _AxisEntry] = {**_AXES_A, **_AXES_B}


# ── 그룹 정의 — analysis("그룹", "하위") 2단계 호출 ──

_GROUPS: dict[str, list[str]] = {
    "financial": [
        "수익구조",
        "자금조달",
        "자산구조",
        "현금흐름",
        "수익성",
        "성장성",
        "안정성",
        "효율성",
        "종합평가",
        "이익품질",
        "비용구조",
        "자본배분",
        "투자효율",
        "재무정합성",
    ],
    "valuation": ["가치평가"],
    "governance": ["지배구조", "공시변화", "비교분석"],
    "forecast": ["매출전망", "예측신호"],
    "macro": ["매크로민감도", "밸류에이션밴드"],
}

# 역매핑: 축 → 소속 그룹
_AXIS_TO_GROUP: dict[str, str] = {}
for _g, _axes in _GROUPS.items():
    for _a in _axes:
        _AXIS_TO_GROUP[_a] = _g

# ── alias — 한글↔영문 양방향 ──

_ALIASES: dict[str, str] = {
    "revenue": "수익구조",
    "revenueStructure": "수익구조",
    "capital": "자금조달",
    "funding": "자금조달",
    "asset": "자산구조",
    "assetStructure": "자산구조",
    "cashflow": "현금흐름",
    "profitability": "수익성",
    "growth": "성장성",
    "stability": "안정성",
    "efficiency": "효율성",
    "scorecard": "종합평가",
    "earningsQuality": "이익품질",
    "costStructure": "비용구조",
    "capitalAllocation": "자본배분",
    "investment": "투자효율",
    "investmentEfficiency": "투자효율",
    "crossStatement": "재무정합성",
    "financialConsistency": "재무정합성",
    "valuation": "가치평가",
    "governance": "지배구조",
    "disclosureDelta": "공시변화",
    "disclosureChange": "공시변화",
    "peerBenchmark": "비교분석",
    "peerComparison": "비교분석",
    "forecast": "매출전망",
    "전망": "매출전망",
    "prediction": "예측신호",
    "predictionSignals": "예측신호",
    "전망신호": "예측신호",
    "macroSensitivity": "매크로민감도",
    "valuationBand": "밸류에이션밴드",
    "민감도": "매크로민감도",
    "멀티플밴드": "밸류에이션밴드",
    "재무": "financial",
    "재무분석": "financial",
    "가치": "valuation",
    "지배": "governance",
    "전망분석": "forecast",
    "매크로": "macro",
    "매크로분석": "macro",
}


def _resolveAxis(axis: str) -> str:
    """축 이름 또는 명시 alias → 정규 축 이름.

    consistency_no_alias 원칙: case-insensitive 매칭 ``axis.lower()`` 는 silent
    alias 라 인정하지 않는다. 사용자는 정식 표기 (한글 정식 또는 _ALIASES 의
    명시 매핑) 를 정확히 사용해야 한다.
    """
    if axis in _AXIS_REGISTRY:
        return axis
    if axis in _ALIASES:
        return _ALIASES[axis]
    available = ", ".join(sorted(_AXIS_REGISTRY))
    raise ValueError(
        f"알 수 없는 분석 축: '{axis}'. 가용 축: {available}\n  사용법: c.analysis() 로 전체 축 가이드를 확인하세요."
    )


__all__ = [
    "_ALIASES",
    "_AXIS_REGISTRY",
    "_AXIS_TO_GROUP",
    "_GROUPS",
    "_AxisEntry",
    "_CalcEntry",
    "_resolveAxis",
]
