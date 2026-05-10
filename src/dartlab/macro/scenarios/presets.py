"""매크로 시나리오 프리셋 — 역사적 충격 + 유형별 + 한국 특화.

실측 데이터 기반 overrides dict. Fed CCAR/DFAST, IMF, BIS 방법론 참조.
모든 수치는 역사적 실측값 또는 학술 문헌의 스트레스 기준.

Sources:
- Fed CCAR/DFAST 2025-2026 Severely Adverse
- IMF WP/13/28 (Claessens & Kose 2013)
- Gilchrist & Zakrajšek (2012 AER)
- FRED 역사적 시계열 실측
- IMF Korea FSAP (2020)
"""

from __future__ import annotations

# ══════════════════════════════════════
# 1. 역사적 재현 (8개) — 실측 수치
# ══════════════════════════════════════

HISTORICAL_SCENARIOS: dict[str, dict] = {
    "1973 오일쇼크": {
        "description": "OPEC 금수조치 — 유가 300% 급등, 스태그플레이션",
        "period": "1973-10 ~ 1975-03",
        "type": "유가/원자재",
        "severity": "extreme",
        "overrides": {
            "cpi_yoy": 12.3,
            "fedfunds": 13.0,
            "unrate": 9.0,
            "indpro_yoy": -12.6,
            "term_spread": 0.5,
        },
        "outcome": "S&P -48%. 스태그플레이션 2년. 1975-03 저점 후 회복.",
    },
    "1980 볼커 긴축": {
        "description": "Fed 기준금리 19.1% — 인플레 진압을 위한 역사적 긴축",
        "period": "1980-01 ~ 1982-11",
        "type": "금리 충격",
        "severity": "extreme",
        "overrides": {
            "fedfunds": 19.1,
            "cpi_yoy": 14.8,
            "unrate": 10.8,
            "term_spread": -2.0,
            "indpro_yoy": -8.0,
        },
        "outcome": "S&P -27%. 더블딥 침체. 인플레 진압 후 1983~89 장기 확장.",
    },
    "1987 블랙먼데이": {
        "description": "하루 만에 DJIA -22.6% — 시장 구조적 붕괴",
        "period": "1987-10",
        "type": "자산 버블 붕괴",
        "severity": "severe",
        "overrides": {
            "vix": 150,  # VIX 미존재, 추정 내재변동성
            "hy_spread": 400,
            "sp500_change": -22.6,
        },
        "outcome": "실물경제 영향 미미. Fed 유동성 공급으로 2개월 내 안정.",
    },
    "1997 아시아 위기": {
        "description": "태국 바트화 붕괴 → 한국 IMF 구제금융",
        "period": "1997-07 ~ 1998-12",
        "type": "통화/신용 충격",
        "severity": "severe",
        "overrides": {
            "hy_spread": 600,
            "vix": 45,
            "nfci": 1.0,
        },
        "outcome": "한국 GDP -5.5%, 원/달러 1,964원. 1999년부터 V자 회복.",
        "kr_overrides": {
            "usdkrw": 1964,
            "kospi_change": -65,
            "base_rate": 25.0,
        },
    },
    "2001 IT버블": {
        "description": "닷컴 버블 붕괴 — NASDAQ -78%",
        "period": "2000-03 ~ 2002-10",
        "type": "자산 버블 붕괴",
        "severity": "severe",
        "overrides": {
            "hy_spread": 1000,
            "vix": 45,
            "unrate": 6.3,
            "fedfunds": 1.0,
            "term_spread": 2.5,
            "indpro_yoy": -6.0,
            "sp500_change": -49,
        },
        "outcome": "NASDAQ -78%, S&P -49%. 얕은 침체(8개월). 2003년부터 회복.",
    },
    "2008 금융위기": {
        "description": "리먼 브라더스 파산 — 글로벌 신용 경색",
        "period": "2008-09 ~ 2009-03",
        "type": "신용 충격",
        "severity": "extreme",
        "overrides": {
            "hy_spread": 2182,
            "vix": 80.86,
            "unrate": 10.0,
            "cpi_yoy": -2.1,
            "fedfunds": 0.16,
            "term_spread": 2.5,
            "nfci": 3.0,
            "indpro_yoy": -15.0,
            "sp500_change": -57,
        },
        "outcome": "S&P -57%, 실업률 10%. 2009-03 저점 후 V자 반등. 112개월 확장.",
    },
    "2020 COVID": {
        "description": "코로나19 팬데믹 — 전세계 봉쇄",
        "period": "2020-02 ~ 2020-04",
        "type": "지정학/팬데믹",
        "severity": "extreme",
        "overrides": {
            "hy_spread": 1087,
            "vix": 82.69,
            "unrate": 14.7,
            "cpi_yoy": 0.1,
            "fedfunds": 0.05,
            "nfci": 1.5,
            "indpro_yoy": -15.0,
            "sp500_change": -34,
        },
        "outcome": "역사상 최단 침체(2개월). V자 반등, QE 무제한. NASDAQ +100% 12개월.",
    },
    "2022 인플레 긴축": {
        "description": "CPI 9.1% + Fed 역사적 속도 긴축",
        "period": "2022-01 ~ 2022-12",
        "type": "인플레이션",
        "severity": "moderate",
        "overrides": {
            "cpi_yoy": 9.1,
            "fedfunds": 5.33,
            "hy_spread": 600,
            "vix": 37,
            "term_spread": -0.8,
            "indpro_yoy": -1.0,
            "sp500_change": -25,
        },
        "outcome": "S&P -25%, NASDAQ -33%. 침체 회피. 연착륙 성공.",
    },
    # ── 추가 역사적 사건 ──
    "1998 LTCM": {
        "description": "LTCM 파산 + 러시아 디폴트 — 글로벌 유동성 경색",
        "period": "1998-08 ~ 1998-11",
        "type": "신용 충격",
        "severity": "severe",
        "overrides": {
            "hy_spread": 700,
            "vix": 45,
            "nfci": 1.2,
            "term_spread": 0.3,
            "fedfunds": 4.75,
        },
        "outcome": "S&P -22% (3개월). Fed 긴급 인하 3회 → V자 반등. 침체 없음.",
    },
    "2001 9/11": {
        "description": "9/11 테러 — 4일 거래 중단, 지정학적 충격",
        "period": "2001-09",
        "type": "지정학/팬데믹",
        "severity": "severe",
        "overrides": {
            "vix": 45,
            "hy_spread": 800,
            "sp500_change": -12,
            "fedfunds": 3.0,
            "nfci": 0.8,
        },
        "outcome": "이미 IT버블 침체 중. S&P -12% (1주). 2개월 후 반등 시작.",
    },
    "2011 유럽 재정위기": {
        "description": "그리스/이탈리아 국채 위기 + 미국 신용등급 강등",
        "period": "2011-07 ~ 2011-12",
        "type": "신용 충격",
        "severity": "moderate",
        "overrides": {
            "hy_spread": 650,
            "vix": 48,
            "nfci": 0.5,
            "sp500_change": -19,
        },
        "outcome": "S&P -19%. V자 반등. 위기는 유럽에 국한. 미국 침체 없음.",
    },
    "2015 중국 위안 절하": {
        "description": "중국 갑작스러운 위안 절하 — EM 자본유출 공포",
        "period": "2015-08 ~ 2016-02",
        "type": "통화/EM 충격",
        "severity": "moderate",
        "overrides": {
            "vix": 40,
            "hy_spread": 700,
            "indpro_yoy": -2.0,
            "sp500_change": -14,
        },
        "outcome": "S&P -14%. 중국 안정화 조치 후 회복. 미국 침체 없음.",
    },
    "2018 연말 긴축공포": {
        "description": "Fed QT + 금리인상 4회 → 시장 패닉",
        "period": "2018-10 ~ 2019-01",
        "type": "금리 충격",
        "severity": "mild",
        "overrides": {
            "fedfunds": 2.5,
            "hy_spread": 530,
            "vix": 36,
            "term_spread": 0.1,
            "sp500_change": -20,
        },
        "outcome": "S&P -20% (3개월). Fed 피벗(금리 동결) → 2019 강세장.",
    },
    "2022 러시아-우크라이나": {
        "description": "러시아 우크라이나 침공 — 유가/곡물 급등",
        "period": "2022-02 ~ 2022-06",
        "type": "지정학/팬데믹",
        "severity": "moderate",
        "overrides": {
            "cpi_yoy": 8.5,
            "vix": 37,
            "hy_spread": 500,
            "indpro_yoy": -1.0,
        },
        "outcome": "유가 $130 터치. CPI 가속. 인플레 긴축의 직접 원인.",
    },
    "2023 SVB 은행위기": {
        "description": "실리콘밸리은행 파산 — 금리 급등에 의한 은행 채권 손실",
        "period": "2023-03",
        "type": "신용 충격",
        "severity": "mild",
        "overrides": {
            "hy_spread": 500,
            "vix": 30,
            "nfci": 0.3,
        },
        "outcome": "FDIC 즉각 개입. 3주 내 안정. 시스템 위기로 번지지 않음.",
    },
}

# ══════════════════════════════════════
# 현대적 리스크 시나리오 (아직 발생 안 함)
# ══════════════════════════════════════

MODERN_RISK_SCENARIOS: dict[str, dict] = {
    "AI 버블 붕괴": {
        "description": "AI 과잉투자 → 수익 실현 실패 → 기술주 폭락",
        "type": "자산 버블 붕괴",
        "transmission": "기술주 폭락 → HY 확대(기술 기업 부채) → VC/PE 손실 → 신용 경색 확산",
        "reference": "2001 IT버블 패턴 + 현대 AI 투자 규모",
        "mild": {"sp500_change": -20, "vix": 35, "hy_spread": 500},
        "moderate": {"sp500_change": -35, "vix": 50, "hy_spread": 700, "nfci": 0.5},
        "severe": {"sp500_change": -50, "vix": 65, "hy_spread": 1000, "nfci": 1.5, "unrate": 7.0},
        "extreme": {"sp500_change": -70, "vix": 80, "hy_spread": 1500, "nfci": 2.5, "unrate": 9.0, "indpro_yoy": -5.0},
    },
    "중국 디플레이션": {
        "description": "중국 부동산 붕괴 + 디플레이션 수출 → 글로벌 수요 위축",
        "type": "디플레이션",
        "transmission": "중국 수요 붕괴 → 원자재 가격 하락 → EM 수출 급감 → 글로벌 산업생산 위축",
        "reference": "일본 1990년대 + 중국 2024~ 부동산 위기",
        "mild": {"indpro_yoy": -2.0, "cpi_yoy": 1.0},
        "moderate": {"indpro_yoy": -5.0, "cpi_yoy": 0.5, "hy_spread": 500, "vix": 30},
        "severe": {"indpro_yoy": -10.0, "cpi_yoy": -0.5, "hy_spread": 700, "vix": 40, "unrate": 6.0},
        "extreme": {"indpro_yoy": -15.0, "cpi_yoy": -2.0, "hy_spread": 1000, "vix": 55, "unrate": 8.0, "fedfunds": 0.5},
    },
    "일본식 장기침체": {
        "description": "재무상태표 침체 — 장기 저성장 + 제로금리 함정",
        "type": "디플레이션",
        "transmission": "자산 버블 붕괴 → 민간 디레버리징 → 소비/투자 장기 위축 → 제로금리에도 회복 안 됨",
        "reference": "Koo (2009) Balance Sheet Recession, 일본 1990~2010",
        "mild": {"fedfunds": 0.5, "cpi_yoy": 0.5, "indpro_yoy": 0.0, "term_spread": 0.5},
        "moderate": {"fedfunds": 0.1, "cpi_yoy": 0.0, "indpro_yoy": -1.0, "term_spread": 0.3, "unrate": 5.5},
        "severe": {
            "fedfunds": 0.0,
            "cpi_yoy": -0.5,
            "indpro_yoy": -3.0,
            "term_spread": 0.2,
            "unrate": 7.0,
            "hy_spread": 400,
        },
        "extreme": {
            "fedfunds": 0.0,
            "cpi_yoy": -1.5,
            "indpro_yoy": -5.0,
            "term_spread": 0.1,
            "unrate": 8.0,
            "hy_spread": 600,
        },
    },
    "대만 해협 분쟁": {
        "description": "미중 군사 대치 — 반도체 공급망 단절 + 글로벌 무역 마비",
        "type": "지정학/팬데믹",
        "transmission": "군사 대치 → VIX 급등 + 안전자산 쏠림 → 반도체 공급 단절 → 산업생산 마비 → 글로벌 침체",
        "reference": "2020 COVID 공급 충격 + 1973 오일쇼크 규모",
        "mild": {"vix": 45, "hy_spread": 600, "indpro_yoy": -5.0},
        "moderate": {"vix": 60, "hy_spread": 900, "indpro_yoy": -10.0, "cpi_yoy": 6.0, "nfci": 1.0},
        "severe": {"vix": 75, "hy_spread": 1200, "indpro_yoy": -18.0, "cpi_yoy": 8.0, "nfci": 2.0, "unrate": 9.0},
        "extreme": {"vix": 90, "hy_spread": 2000, "indpro_yoy": -25.0, "cpi_yoy": 12.0, "nfci": 3.0, "unrate": 12.0},
    },
    "글로벌 무역전쟁": {
        "description": "미중 관세 전면전 + WTO 체제 붕괴",
        "type": "지정학/팬데믹",
        "transmission": "관세 급등 → 수입물가 상승 → 공급망 재편 비용 → 산업생산 위축 → 스태그플레이션",
        "reference": "2018-19 미중 무역분쟁 확대 버전",
        "mild": {"cpi_yoy": 4.0, "indpro_yoy": -2.0, "vix": 30},
        "moderate": {"cpi_yoy": 5.5, "indpro_yoy": -5.0, "vix": 40, "hy_spread": 500},
        "severe": {"cpi_yoy": 7.0, "indpro_yoy": -8.0, "vix": 50, "hy_spread": 700, "unrate": 6.0},
        "extreme": {"cpi_yoy": 10.0, "indpro_yoy": -15.0, "vix": 65, "hy_spread": 1000, "unrate": 9.0},
    },
    "미국 국채 위기": {
        "description": "미국 재정적자 급증 → 국채 수요 급감 → 금리 급등",
        "type": "금리 충격",
        "transmission": "국채 매도 → 장기금리 급등 → 모기지/기업 차입 비용 폭증 → 부동산/기업 동시 위기",
        "reference": "2011 미국 신용등급 강등 + 영국 2022 미니버짓 위기",
        "mild": {"term_spread": 2.0, "fedfunds": 5.5, "vix": 30, "hy_spread": 500},
        "moderate": {"term_spread": 3.0, "fedfunds": 6.0, "vix": 45, "hy_spread": 700},
        "severe": {"term_spread": 4.0, "fedfunds": 7.0, "vix": 55, "hy_spread": 1000, "unrate": 7.0},
        "extreme": {"term_spread": 5.0, "fedfunds": 8.0, "vix": 70, "hy_spread": 1500, "unrate": 10.0},
    },
}

# ══════════════════════════════════════
# 구조적 시나리오 (regime 유형)
# ══════════════════════════════════════

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

# ══════════════════════════════════════
# 2. 유형별 × 심각도 (6 × 4 = 24개)
# ══════════════════════════════════════

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

# ══════════════════════════════════════
# 3. 한국 특화 (3개)
# ══════════════════════════════════════

KR_SCENARIOS: dict[str, dict] = {
    "환율 위기": {
        "description": "원/달러 급등 — 자본유출 + 수입물가 급등",
        "transmission": "환율 급등 → 자본유출 → 수입물가 상승 → 금리인상 압력 → 가계부채 이자부담 → 소비 위축",
        "reference": "1997 IMF, IMF Korea FSAP (2020)",
        "mild": {"usdkrw": 1450, "hy_spread": 400, "cpi_yoy": 4.0},
        "moderate": {"usdkrw": 1550, "hy_spread": 600, "cpi_yoy": 5.0, "vix": 35},
        "severe": {"usdkrw": 1700, "hy_spread": 900, "cpi_yoy": 7.0, "vix": 50, "base_rate": 5.0},
        "extreme": {"usdkrw": 1900, "hy_spread": 1500, "cpi_yoy": 10.0, "vix": 65, "base_rate": 10.0},
    },
    "가계부채 위기": {
        "description": "DSR 급등 — 부동산 가격 하락 + 가계 디레버리징",
        "transmission": "금리 인상 → DSR 급등 → 소비 위축 → 부동산 하락 → 은행 부실 → 신용 경색",
        "reference": "IMF Korea FSAP (2020), BOK 금융안정보고서",
        "mild": {"base_rate": 4.5, "apt_yoy": -5, "hy_spread": 400},
        "moderate": {"base_rate": 5.5, "apt_yoy": -15, "hy_spread": 600, "unrate": 5.0},
        "severe": {"base_rate": 6.0, "apt_yoy": -25, "hy_spread": 900, "unrate": 7.0},
        "extreme": {"base_rate": 7.0, "apt_yoy": -40, "hy_spread": 1500, "unrate": 10.0},
    },
    "수출 급감": {
        "description": "글로벌 수요 붕괴 — 반도체/자동차 수출 급락",
        "transmission": "수출 급감 → 기업 이익 악화 → 고용 감소 → 소비 위축 → 환율 약세",
        "reference": "2009 금융위기, 2020 COVID",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1400},
        "moderate": {"indpro_yoy": -8.0, "usdkrw": 1500, "hy_spread": 500},
        "severe": {"indpro_yoy": -15.0, "usdkrw": 1600, "hy_spread": 800, "unrate": 6.0},
        "extreme": {"indpro_yoy": -25.0, "usdkrw": 1800, "hy_spread": 1200, "unrate": 9.0},
    },
    "북한 리스크": {
        "description": "한반도 군사적 긴장 고조 — 외국인 자본 이탈",
        "transmission": "지정학 리스크 → 외국인 매도 → KOSPI 급락 + 원화 약세 → 금리 방어 → 경기 위축",
        "reference": "2017 북한 핵실험, 2010 천안함/연평도",
        "mild": {"usdkrw": 1400, "vix": 30, "kospi_change": -10},
        "moderate": {"usdkrw": 1500, "vix": 40, "kospi_change": -20, "hy_spread": 500},
        "severe": {"usdkrw": 1650, "vix": 55, "kospi_change": -35, "hy_spread": 800, "base_rate": 5.0},
        "extreme": {"usdkrw": 1900, "vix": 75, "kospi_change": -50, "hy_spread": 1500, "base_rate": 8.0},
    },
    "반도체 다운사이클": {
        "description": "글로벌 반도체 수요 급감 — 삼성/SK 실적 직격",
        "transmission": "DRAM/NAND 가격 급락 → 반도체 기업 감산 → 수출 감소 → GDP 직격 → 관련 산업 연쇄",
        "reference": "2019 반도체 다운사이클, 2022-23 메모리 불황",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1380},
        "moderate": {"indpro_yoy": -8.0, "usdkrw": 1450, "kospi_change": -15},
        "severe": {"indpro_yoy": -15.0, "usdkrw": 1550, "kospi_change": -30, "hy_spread": 500},
        "extreme": {"indpro_yoy": -25.0, "usdkrw": 1700, "kospi_change": -45, "hy_spread": 800, "unrate": 6.0},
    },
    "중국 수요 급감": {
        "description": "중국 경기 급랭 — 한국 대중 수출 붕괴",
        "transmission": "중국 GDP 급락 → 대중 수출 -30%+ → 석유화학/철강/반도체 타격 → 기업이익 급감 → 고용 악화",
        "reference": "2015 중국 위안 절하 + 중국 부동산 위기 확대",
        "mild": {"indpro_yoy": -3.0, "usdkrw": 1400, "cpi_yoy": 1.0},
        "moderate": {"indpro_yoy": -7.0, "usdkrw": 1500, "hy_spread": 500, "vix": 35},
        "severe": {"indpro_yoy": -12.0, "usdkrw": 1600, "hy_spread": 700, "vix": 45, "unrate": 5.5},
        "extreme": {"indpro_yoy": -20.0, "usdkrw": 1750, "hy_spread": 1000, "vix": 60, "unrate": 8.0},
    },
}

# ══════════════════════════════════════
# Fed DFAST 공식 시나리오 (2026)
# ══════════════════════════════════════

DFAST_SCENARIOS: dict[str, dict] = {
    "DFAST Baseline": {
        "description": "Fed 공식 기준 시나리오 — 완만한 성장 지속",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "기준",
        "severity": "mild",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 4.5,
            "vix": 18,
            "hy_spread": 350,
            "fedfunds": 3.5,
            "term_spread": 0.8,
            "cpi_yoy": 2.3,
            "indpro_yoy": 1.5,
        },
        "outcome": "GDP +2.2%, 실업률 4.5%. 점진적 금리 인하. 안정적 성장.",
    },
    "DFAST Adverse": {
        "description": "Fed 공식 역경 시나리오 — 글로벌 경기 둔화",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "복합 충격",
        "severity": "severe",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 7.2,
            "vix": 50,
            "hy_spread": 350,  # 3.5pp
            "fedfunds": 1.0,
            "term_spread": 2.0,
            "cpi_yoy": 1.5,
            "sp500_change": -38,
            "indpro_yoy": -5.0,
        },
        "outcome": "GDP -2.8%, 실업률 7.2%, 주가 -38%, 주택 -18%.",
    },
    "DFAST Severely Adverse": {
        "description": "Fed 공식 극심 시나리오 — 극심한 글로벌 침체",
        "period": "가상 (Fed 2026 시나리오)",
        "type": "복합 충격",
        "severity": "extreme",
        "reference": "Federal Reserve 2026 Stress Test Scenarios",
        "overrides": {
            "unrate": 10.0,
            "vix": 72,
            "hy_spread": 570,
            "fedfunds": 0.1,
            "term_spread": 3.0,
            "cpi_yoy": 1.0,
            "sp500_change": -58,
            "indpro_yoy": -8.0,
        },
        "outcome": "GDP -4.6%, 실업률 10%, 주가 -58%, 주택 -30%, 상업용부동산 -39%.",
    },
}


# ══════════════════════════════════════
# 유틸리티
# ══════════════════════════════════════


def getScenario(name: str, *, severity: str | None = None, market: str = "US") -> dict | None:
    """시나리오 이름으로 프리셋 조회.

    역사적 재현 → DFAST → 현대적 리스크 → 구조적 → 유형별 → 한국 특화
    → 복합(+ 구분) 순으로 탐색하며, 부분 문자열 매칭으로 찾는다.

    Parameters
    ----------
    name : str
        시나리오 이름 (한글/영문). 부분 매칭 가능.
        복합 시나리오는 ``"금리 충격 + 유가 충격"`` 형태.
    severity : str | None
        심각도. ``"mild"`` / ``"moderate"`` / ``"severe"`` / ``"extreme"``.
        유형별·구조적 시나리오에서 사용. 미지정 시 ``"moderate"``.
    market : str
        시장 구분. ``"US"`` | ``"KR"``.
        ``"KR"`` 이면 역사적 재현의 ``kr_overrides`` 병합.

    Returns
    -------
    dict | None
        매칭 시나리오가 없으면 ``None``. 있으면:

        description : str — 시나리오 설명
        type : str — 충격 유형 (신용 충격, 금리 충격 등)
        severity : str — 심각도
        transmission : str — 전파 경로
        reference : str — 참조 문헌/사건
        overrides : dict — 매크로 지표 override 값
    """
    # 1. 역사적 재현
    for key, val in HISTORICAL_SCENARIOS.items():
        if name in key or key in name:
            result = dict(val)
            if market == "KR" and "kr_overrides" in val:
                result["overrides"] = {**val["overrides"], **val["kr_overrides"]}
            return result

    # 2. DFAST
    for key, val in DFAST_SCENARIOS.items():
        if name in key or key in name or "DFAST" in name.upper():
            return dict(val)

    # 3. 현대적 리스크
    for key, val in MODERN_RISK_SCENARIOS.items():
        if name in key or key in name:
            sev = severity or "moderate"
            if sev not in val:
                return None
            return {
                "description": val["description"],
                "type": val.get("type", key),
                "severity": sev,
                "transmission": val.get("transmission"),
                "reference": val.get("reference"),
                "overrides": val[sev],
            }

    # 4. 구조적 시나리오
    for key, val in STRUCTURAL_SCENARIOS.items():
        if name in key or key in name:
            sev = severity or "moderate"
            if sev not in val:
                return None
            return {
                "description": val["description"],
                "type": val.get("type", key),
                "severity": sev,
                "transmission": val.get("transmission"),
                "reference": val.get("reference"),
                "overrides": val[sev],
            }

    # 5. 유형별
    for key, val in TYPED_SCENARIOS.items():
        if name in key or key in name:
            sev = severity or "moderate"
            if sev not in val:
                return None
            overrides = val[sev]
            return {
                "description": val["description"],
                "type": key,
                "severity": sev,
                "transmission": val.get("transmission"),
                "reference": val.get("reference"),
                "overrides": overrides,
            }

    # 6. 한국 특화
    for key, val in KR_SCENARIOS.items():
        if name in key or key in name:
            sev = severity or "moderate"
            if sev not in val:
                return None
            return {
                "description": val["description"],
                "type": key,
                "severity": sev,
                "transmission": val.get("transmission"),
                "reference": val.get("reference"),
                "overrides": val[sev],
            }

    # 5. 복합 시나리오 (+ 구분)
    if "+" in name:
        parts = [p.strip() for p in name.split("+")]
        combined_overrides: dict = {}
        descriptions: list[str] = []
        for part in parts:
            sub = getScenario(part, severity=severity, market=market)
            if sub:
                combined_overrides.update(sub["overrides"])
                descriptions.append(sub.get("description", part))
        if combined_overrides:
            return {
                "description": " + ".join(descriptions),
                "type": "복합",
                "severity": severity or "moderate",
                "overrides": combined_overrides,
            }

    return None


def listAllScenarios(market: str = "US") -> list[dict]:
    """모든 시나리오 목록.

    역사적 재현, DFAST, 유형별, 현대적 리스크, 구조적, 한국 특화
    카테고리의 전체 시나리오를 평탄화하여 반환한다.

    Parameters
    ----------
    market : str
        시장 구분. ``"US"`` | ``"KR"``.

    Returns
    -------
    list[dict]
        각 항목:

        name : str — 시나리오 이름
        category : str — 분류 (역사적 재현 / Fed DFAST / 유형별 / 현대적 리스크 / 구조적 / 한국 특화)
        type : str — 충격 유형
        severity : str — 심각도 (mild/moderate/severe/extreme)
        description : str — 시나리오 설명
    """
    result: list[dict] = []

    for name, val in HISTORICAL_SCENARIOS.items():
        result.append(
            {
                "name": name,
                "category": "역사적 재현",
                "type": val.get("type", ""),
                "severity": val.get("severity", ""),
                "description": val["description"],
            }
        )

    for name, val in DFAST_SCENARIOS.items():
        result.append(
            {
                "name": name,
                "category": "Fed DFAST",
                "type": val.get("type", ""),
                "severity": val.get("severity", ""),
                "description": val["description"],
            }
        )

    for type_name, val in TYPED_SCENARIOS.items():
        for sev in SEVERITIES:
            if sev in val:
                result.append(
                    {
                        "name": f"{type_name} ({sev})",
                        "category": "유형별",
                        "type": type_name,
                        "severity": sev,
                        "description": val["description"],
                    }
                )

    for name, val in MODERN_RISK_SCENARIOS.items():
        for sev in SEVERITIES:
            if sev in val:
                result.append(
                    {
                        "name": f"{name} ({sev})",
                        "category": "현대적 리스크",
                        "type": val.get("type", name),
                        "severity": sev,
                        "description": val["description"],
                    }
                )

    for name, val in STRUCTURAL_SCENARIOS.items():
        for sev in SEVERITIES:
            if sev in val:
                result.append(
                    {
                        "name": f"{name} ({sev})",
                        "category": "구조적",
                        "type": val.get("type", name),
                        "severity": sev,
                        "description": val["description"],
                    }
                )

    for name, val in KR_SCENARIOS.items():
        for sev in SEVERITIES:
            if sev in val:
                result.append(
                    {
                        "name": f"{name} ({sev})",
                        "category": "한국 특화",
                        "type": name,
                        "severity": sev,
                        "description": val["description"],
                    }
                )

    return result
