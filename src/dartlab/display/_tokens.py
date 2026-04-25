"""display 공용 디자인 토큰 SSOT — 등급 점수·영역 라벨.

display/{notebook,richInsight}.py 등이 import. AnalysisResult 영역 한글 라벨은
여기서만 정의. 라벨 추가·변경 시 이 파일만 수정.
"""

from __future__ import annotations

GRADE_SCORE: dict[str, int] = {"A": 90, "B": 75, "C": 60, "D": 45, "F": 20}

AREA_LABELS: dict[str, str] = {
    "performance": "실적",
    "profitability": "수익성",
    "health": "건전성",
    "cashflow": "현금흐름",
    "governance": "지배구조",
    "risk": "리스크",
    "opportunity": "기회",
    "predictability": "예측성",
    "uncertainty": "불확실성",
    "coreEarnings": "핵심이익",
}
