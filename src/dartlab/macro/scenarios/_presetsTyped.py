"""유형별 시나리오 (6 유형 × 4 심각도 = 24 조합).

신용/금리/유가/지정학/자산버블/인플레이션 6 충격 유형 각각의 mild/moderate/severe/extreme.
``getScenario`` 가 severity 인자로 분기 선택, ``listAllScenarios`` 가 24 개 평탄화 노출.

본 모듈은 데이터 정의만 담는다. 호출 로직은 ``presets.py``.
"""

from __future__ import annotations

SEVERITIES = ("mild", "moderate", "severe", "extreme")

TYPED_SCENARIOS: dict[str, dict] = {
    "신용 충격": {
        "description": "은행/기업 신용 경색",
        "transmission": "NFCI 긴축 → 설비투자 축소(3-6개월) → GDP 하락 → 실업률 상승",
        "reference": "Gilchrist & Zakrajšek (2012 AER)",
        "mild": {"hy_spread": 500, "vix": 30, "nfci": 0.3, "ig_spread": 150},
        "moderate": {"hy_spread": 700, "vix": 40, "nfci": 0.8, "ig_spread": 250},
        "severe": {"hy_spread": 1000, "vix": 55, "nfci": 1.5, "ig_spread": 400, "unrate": 7.0},
        "extreme": {"hy_spread": 2000, "vix": 75, "nfci": 3.0, "ig_spread": 600, "unrate": 10.0},
    },
    "금리 충격": {
        "description": "급격한 금리 인상 또는 예기치 못한 긴축",
        "transmission": "기준금리 급등 → HY/IG 스프레드 확대 → 소비/투자 위축(6-18개월) → 고용 악화",
        "reference": "Fed CCAR/DFAST Severely Adverse",
        "mild": {"fedfunds": 6.0, "hy_spread": 450, "term_spread": -0.3, "vix": 25},
        "moderate": {"fedfunds": 7.0, "hy_spread": 600, "term_spread": -1.0, "vix": 35},
        "severe": {"fedfunds": 8.0, "hy_spread": 800, "term_spread": -1.5, "vix": 50, "unrate": 7.0},
        "extreme": {"fedfunds": 12.0, "hy_spread": 1200, "term_spread": -2.0, "vix": 60, "unrate": 10.0},
    },
    "유가/원자재 충격": {
        "description": "에너지 가격 급등으로 인한 비용 인플레이션",
        "transmission": "유가 급등 → CPI/PPI 상승(즉시~3개월) → 기업 마진 압축 → 산업생산 하락(~10개월)",
        "reference": "1973 오일쇼크, 2022 에너지 위기",
        "mild": {"cpi_yoy": 4.5, "indpro_yoy": -1.0},
        "moderate": {"cpi_yoy": 6.0, "indpro_yoy": -3.0, "hy_spread": 500, "vix": 30},
        "severe": {"cpi_yoy": 8.0, "indpro_yoy": -5.0, "hy_spread": 700, "vix": 40},
        "extreme": {"cpi_yoy": 12.0, "indpro_yoy": -10.0, "hy_spread": 1000, "vix": 50, "unrate": 8.0},
    },
    "지정학/팬데믹": {
        "description": "전쟁, 테러, 팬데믹 등 외생적 충격",
        "transmission": "VIX 급등 → 모든 자산 동시 매도 → HY 확대 → 실물 위축",
        "reference": "2020 COVID, 9/11, 러시아-우크라이나",
        "mild": {"vix": 35, "hy_spread": 500},
        "moderate": {"vix": 50, "hy_spread": 700, "nfci": 0.5, "indpro_yoy": -3.0},
        "severe": {"vix": 65, "hy_spread": 1000, "nfci": 1.5, "indpro_yoy": -8.0, "unrate": 8.0},
        "extreme": {"vix": 80, "hy_spread": 1500, "nfci": 2.0, "indpro_yoy": -15.0, "unrate": 14.0},
    },
    "자산 버블 붕괴": {
        "description": "주식/부동산 버블 붕괴",
        "transmission": "주가 급락 → 역부의효과 → 소비 위축 → HY 확대 → 실업 증가",
        "reference": "2001 IT버블, 1987 블랙먼데이",
        "mild": {"sp500_change": -15, "vix": 30, "hy_spread": 450},
        "moderate": {"sp500_change": -25, "vix": 40, "hy_spread": 600},
        "severe": {"sp500_change": -40, "vix": 55, "hy_spread": 900, "unrate": 7.0},
        "extreme": {"sp500_change": -55, "vix": 75, "hy_spread": 1500, "unrate": 10.0},
    },
    "인플레이션 충격": {
        "description": "급격한 물가 상승 + 중앙은행 긴축 대응",
        "transmission": "CPI 급등 → 금리 인상 압력 → HY 확대 → 소비/투자 위축",
        "reference": "1980 볼커, 2022 인플레",
        "mild": {"cpi_yoy": 5.0, "fedfunds": 5.5, "term_spread": -0.3},
        "moderate": {"cpi_yoy": 7.0, "fedfunds": 7.0, "term_spread": -0.8, "hy_spread": 500},
        "severe": {"cpi_yoy": 9.0, "fedfunds": 9.0, "term_spread": -1.5, "hy_spread": 700, "vix": 40},
        "extreme": {
            "cpi_yoy": 14.0,
            "fedfunds": 15.0,
            "term_spread": -2.0,
            "hy_spread": 1000,
            "vix": 50,
            "unrate": 10.0,
        },
    },
}

__all__ = ["SEVERITIES", "TYPED_SCENARIOS"]
