"""구조적 시나리오 (5 개) — regime 유형별 4 심각도.

"스태그플레이션", "디플레이션", "골디락스", "경착륙", "연착륙" — 매크로 환경
유형 자체를 표현. 각 4 심각도 (mild/moderate/severe/extreme).

본 모듈은 데이터 정의만 담는다. 호출 로직은 ``presets.py``.
"""

from __future__ import annotations

STRUCTURAL_SCENARIOS: dict[str, dict] = {
    "스태그플레이션": {
        "description": "고물가 + 저성장 — 최악의 조합",
        "type": "인플레이션",
        "transmission": "공급 충격 → CPI 급등 + GDP 위축 동시 → 중앙은행 딜레마 (긴축하면 침체, 완화하면 인플레)",
        "reference": "1973-74 오일쇼크, 2022 일부 시기",
        "mild": {"cpi_yoy": 5.0, "indpro_yoy": -1.0, "fedfunds": 5.0, "unrate": 5.0},
        "moderate": {"cpi_yoy": 7.0, "indpro_yoy": -3.0, "fedfunds": 6.0, "unrate": 6.0, "hy_spread": 500},
        "severe": {"cpi_yoy": 9.0, "indpro_yoy": -6.0, "fedfunds": 7.0, "unrate": 8.0, "hy_spread": 700, "vix": 40},
        "extreme": {
            "cpi_yoy": 14.0,
            "indpro_yoy": -12.0,
            "fedfunds": 12.0,
            "unrate": 10.0,
            "hy_spread": 1000,
            "vix": 55,
        },
    },
    "디플레이션": {
        "description": "물가 하락 + 경기 위축 — 유동성 함정",
        "type": "디플레이션",
        "transmission": "수요 붕괴 → CPI 하락 → 실질금리 상승 → 소비 연기 → 기업 이익 악화 → 악순환",
        "reference": "일본 1990~2010, 2008-09 미국",
        "mild": {"cpi_yoy": 0.5, "fedfunds": 0.5, "indpro_yoy": -1.0},
        "moderate": {"cpi_yoy": -0.5, "fedfunds": 0.1, "indpro_yoy": -3.0, "unrate": 6.0},
        "severe": {"cpi_yoy": -1.5, "fedfunds": 0.0, "indpro_yoy": -6.0, "unrate": 8.0, "hy_spread": 600},
        "extreme": {"cpi_yoy": -3.0, "fedfunds": 0.0, "indpro_yoy": -10.0, "unrate": 10.0, "hy_spread": 1000},
    },
    "골디락스": {
        "description": "저인플레 + 완전고용 + 안정 성장 — 이상적 환경",
        "type": "호황",
        "transmission": "물가 안정 → 금리 안정 → 기업 이익 증가 → 고용 증가 → 선순환",
        "reference": "1995-98 미국, 2017 미국",
        "mild": {"cpi_yoy": 2.5, "unrate": 4.5, "fedfunds": 3.0, "vix": 18, "hy_spread": 350},
        "moderate": {"cpi_yoy": 2.0, "unrate": 4.0, "fedfunds": 2.5, "vix": 14, "hy_spread": 300, "indpro_yoy": 3.0},
        "severe": {"cpi_yoy": 1.8, "unrate": 3.5, "fedfunds": 2.0, "vix": 12, "hy_spread": 250, "indpro_yoy": 4.0},
        "extreme": {
            "cpi_yoy": 1.5,
            "unrate": 3.0,
            "fedfunds": 1.5,
            "vix": 10,
            "hy_spread": 200,
            "indpro_yoy": 5.0,
            "nfci": -1.0,
        },
    },
    "경착륙": {
        "description": "급격한 긴축 후 침체 진입",
        "type": "금리 충격",
        "transmission": "급격한 금리 인상 → 경기 급랭 → 실업률 급등 → 신용 위축 → 디플레이션 위험",
        "reference": "1980 볼커, 2007-08",
        "mild": {"fedfunds": 6.0, "unrate": 5.5, "indpro_yoy": -2.0, "hy_spread": 500},
        "moderate": {"fedfunds": 6.5, "unrate": 7.0, "indpro_yoy": -5.0, "hy_spread": 700, "vix": 35},
        "severe": {"fedfunds": 7.0, "unrate": 8.5, "indpro_yoy": -8.0, "hy_spread": 1000, "vix": 50},
        "extreme": {"fedfunds": 8.0, "unrate": 10.0, "indpro_yoy": -12.0, "hy_spread": 1500, "vix": 65},
    },
    "연착륙": {
        "description": "적절한 긴축 → 인플레 진정 → 침체 회피",
        "type": "호황",
        "transmission": "점진적 금리 인상 → 인플레 둔화 → 실업률 소폭 상승 후 안정 → 성장 재가속",
        "reference": "1995 그린스펀, 2023-24",
        "mild": {"cpi_yoy": 3.0, "fedfunds": 4.5, "unrate": 4.5, "vix": 18, "hy_spread": 380},
        "moderate": {"cpi_yoy": 2.5, "fedfunds": 4.0, "unrate": 4.2, "vix": 15, "hy_spread": 340, "indpro_yoy": 2.0},
        "severe": {"cpi_yoy": 2.2, "fedfunds": 3.5, "unrate": 4.0, "vix": 13, "hy_spread": 300, "indpro_yoy": 3.0},
        "extreme": {
            "cpi_yoy": 2.0,
            "fedfunds": 3.0,
            "unrate": 3.8,
            "vix": 12,
            "hy_spread": 280,
            "indpro_yoy": 4.0,
            "nfci": -0.8,
        },
    },
}

__all__ = ["STRUCTURAL_SCENARIOS"]
