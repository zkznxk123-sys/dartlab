"""역사적 재현 시나리오 (15 개) — 실측 수치 기반.

Sources:
- FRED 역사적 시계열 실측 (1973~2023)
- 한국 IMF FSAP (2020), 한국은행 통계
- 학술 문헌 (Claessens & Kose 2013, Gilchrist & Zakrajšek 2012)

본 모듈은 데이터 정의만 담는다. 호출 로직은 ``presets.py``.
"""

from __future__ import annotations

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

__all__ = ["HISTORICAL_SCENARIOS"]
