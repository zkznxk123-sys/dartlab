"""업종별 KPI 모듈 — 범용 14축으로 안 잡히는 업종 특수 지표.

4개 업종 지원: 건설 / 반도체 / 게임·엔터 / 제약·바이오.
각 모듈은 2~4 calc 함수를 제공하며, sectorKpi(company)가 업종 자동 감지 후 dispatch.
"""

from __future__ import annotations

from dartlab.analysis.financial.sectorKpi.dispatcher import detectSector, sectorKpi

__all__ = ["detectSector", "sectorKpi"]
