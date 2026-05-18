"""sectorThresholds 의 B 분류 — shipbuilding/semiconductor/auto/airline/holding/metals/telecom + financialTrackB + _INDUSTRY_THRESHOLDS."""

from __future__ import annotations

from dartlab.credit.features._sectorThresholdsA import (
    _SECTOR_THRESHOLDS,
    _constructionThresholds,
    _defaultThresholds,
    _energyThresholds,
    _financialsThresholds,
    _itThresholds,
    _utilitiesThresholds,
)
from dartlab.frame.sector import IndustryGroup, Sector


def _shipbuildingThresholds() -> dict:
    """조선 — 극심한 사이클, 선수금 구조, 장기 프로젝트."""
    base = _constructionThresholds()
    # 부채비율 완화 (수주산업 특성)
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (50.0, 2),
        (100.0, 5),
        (200.0, 12),
        (300.0, 22),
        (400.0, 38),
        (600.0, 58),
        (800.0, 78),
        (1000.0, 90),
    ]
    return base


def _semiconductorThresholds() -> dict:
    """반도체 — 극심한 사이클, 대규모 CAPEX, 현금흐름 변동.

    삼성SDI D/EBITDA ~15x, SK하이닉스 CAPEX 사이클 ~5-10x.
    """
    base = _itThresholds()
    # D/EBITDA: 반도체 CAPEX 사이클 감안. 15x까지도 투자적격.
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (4.0, 15),
        (6.0, 22),
        (10.0, 32),
        (15.0, 45),
        (20.0, 62),
        (30.0, 82),
    ]
    base["net_debt_to_ebitda"]["breakpoints"] = [
        (-5.0, 0),
        (0.0, 3),
        (2.0, 10),
        (4.0, 18),
        (6.0, 25),
        (10.0, 35),
        (15.0, 48),
        (20.0, 65),
        (30.0, 85),
    ]
    return base


def _autoThresholds() -> dict:
    """자동차 — 캡티브 금융 연결, 높은 부채비율 정상."""
    base = _defaultThresholds()
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (50.0, 2),
        (100.0, 5),
        (150.0, 10),
        (200.0, 18),
        (300.0, 28),
        (400.0, 42),
        (600.0, 62),
        (800.0, 82),
    ]
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (3.0, 15),
        (5.0, 25),
        (8.0, 40),
        (12.0, 58),
        (20.0, 78),
        (30.0, 90),
    ]
    base["borrowing_dependency"]["breakpoints"] = [
        (0.0, 0),
        (10.0, 3),
        (20.0, 8),
        (30.0, 15),
        (40.0, 25),
        (50.0, 38),
        (60.0, 52),
        (70.0, 68),
        (80.0, 82),
    ]
    return base


def _airlineThresholds() -> dict:
    """항공/해운 — IFRS16 리스 부채, 높은 감가상각, 탑승률 민감."""
    base = _defaultThresholds()
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (50.0, 2),
        (100.0, 5),
        (150.0, 10),
        (200.0, 15),
        (300.0, 25),
        (400.0, 38),
        (500.0, 55),
        (700.0, 75),
    ]
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (3.0, 15),
        (4.0, 22),
        (5.0, 32),
        (7.0, 48),
        (10.0, 65),
        (15.0, 85),
    ]
    base["net_debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 5),
        (2.0, 10),
        (3.0, 18),
        (5.0, 30),
        (7.0, 48),
        (10.0, 68),
        (15.0, 88),
    ]
    base["borrowing_dependency"]["breakpoints"] = [
        (0.0, 0),
        (10.0, 3),
        (20.0, 8),
        (30.0, 15),
        (40.0, 28),
        (50.0, 42),
        (60.0, 62),
        (70.0, 80),
    ]
    return base


def _holdingThresholds() -> dict:
    """지주사 — 지분법 자산/손익, 연결 부채 과대. 비영업자산 비중 높음."""
    base = _defaultThresholds()
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (50.0, 2),
        (100.0, 5),
        (150.0, 10),
        (200.0, 18),
        (300.0, 28),
        (400.0, 42),
        (600.0, 62),
        (800.0, 80),
    ]
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (3.0, 15),
        (5.0, 25),
        (8.0, 40),
        (12.0, 58),
        (18.0, 75),
        (25.0, 90),
    ]
    base["net_debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 5),
        (3.0, 12),
        (5.0, 22),
        (8.0, 35),
        (12.0, 52),
        (18.0, 72),
        (25.0, 88),
    ]
    return base


def _metalsThresholds() -> dict:
    """비철금속/광업 — CAPEX 사이클, 원자재 가격 민감.

    고려아연 D/EBITDA ~8x, 현대제철 ~10x. 광업/철강 CAPEX 정상 범위.
    """
    base = _energyThresholds()
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (3.0, 15),
        (5.0, 22),
        (8.0, 32),
        (12.0, 48),
        (18.0, 68),
        (25.0, 85),
    ]
    # 유동비율도 광업 특성 반영 (설비 자산 비중 높음)
    base["current_ratio"]["breakpoints"] = [
        (200.0, 0),
        (150.0, 5),
        (120.0, 12),
        (100.0, 20),
        (80.0, 30),
        (60.0, 42),
        (40.0, 62),
        (20.0, 82),
    ]
    return base


def financialTrackBThresholds() -> dict:
    """금융업 Track B 전용 기준표.

    D/EBITDA, FFO/Debt를 사용하지 않음.
    자기자본비율, ROA, NIM, 충당금 비율이 핵심.
    은행: 자기자본비율 7~15%, ROA 0.3~1.5%, NIM 1~3%.

    Raises:
        없음.

    Example:
        >>> from dartlab.credit.features.sectorThresholds import financialTrackBThresholds
        >>> financialTrackBThresholds()["equity_ratio"]["lower_is_better"]
        False

    Requires:
        - 외부 의존 없음 (정적 dict).
    """
    return {
        "equity_ratio": {  # 금융지주 자기자본비율: 7~15% 정상, BIS 최저 8%
            "lower_is_better": False,
            "breakpoints": [
                (15.0, 0),
                (12.0, 3),
                (10.0, 8),
                (8.0, 15),
                (7.0, 25),
                (6.0, 38),
                (5.0, 55),
                (4.0, 75),
                (3.0, 90),
            ],
        },
        "roa": {  # 금융지주 ROA: 0.3~1.0%가 정상 범위
            "lower_is_better": False,
            "breakpoints": [
                (1.2, 0),
                (0.8, 5),
                (0.6, 12),
                (0.4, 22),
                (0.3, 32),
                (0.2, 45),
                (0.1, 62),
                (0.0, 80),
                (-0.3, 95),
            ],
        },
        "nim_proxy": {  # 이자수익/자산 (NIM 대리, 순마진 아닌 총이자수익 비율)
            "lower_is_better": False,
            "breakpoints": [
                (4.0, 0),
                (3.0, 5),
                (2.0, 12),
                (1.5, 22),
                (1.0, 35),
                (0.5, 52),
                (0.2, 72),
                (0.0, 90),
            ],
        },
        "provision_ratio": {
            "lower_is_better": True,
            "breakpoints": [
                (0.0, 0),
                (0.1, 5),
                (0.3, 12),
                (0.5, 25),
                (1.0, 42),
                (2.0, 65),
                (3.0, 85),
            ],
        },
        "cash_to_asset": {
            "lower_is_better": False,
            "breakpoints": [
                (20.0, 0),
                (15.0, 8),
                (10.0, 18),
                (5.0, 35),
                (3.0, 52),
                (1.0, 72),
                (0.0, 90),
            ],
        },
        "current_ratio": {
            "lower_is_better": False,
            "breakpoints": [
                (200.0, 0),
                (150.0, 10),
                (120.0, 20),
                (100.0, 35),
                (80.0, 52),
                (60.0, 68),
                (40.0, 85),
            ],
        },
    }


def _telecomThresholds() -> dict:
    """통신 — 높은 설비투자, 안정 현금흐름, 규제 산업."""
    base = _utilitiesThresholds()
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (0.5, 2),
        (1.0, 5),
        (1.5, 10),
        (2.0, 15),
        (3.0, 25),
        (4.0, 38),
        (6.0, 55),
        (8.0, 75),
    ]
    return base


# ── IndustryGroup별 override ──

_INDUSTRY_THRESHOLDS: dict[IndustryGroup, dict] = {
    IndustryGroup.CONSTRUCTION: _constructionThresholds(),
    IndustryGroup.SHIPBUILDING: _shipbuildingThresholds(),
    IndustryGroup.SEMICONDUCTOR: _semiconductorThresholds(),
    IndustryGroup.AUTO: _autoThresholds(),
    IndustryGroup.BANK: _financialsThresholds(),
    IndustryGroup.INSURANCE: _financialsThresholds(),
    IndustryGroup.DIVERSIFIED_FINANCIALS: _financialsThresholds(),
    IndustryGroup.OIL_GAS: _energyThresholds(),
    IndustryGroup.CHEMICAL: _semiconductorThresholds(),  # 화학/배터리 = 반도체급 CAPEX 사이클
    IndustryGroup.ELECTRIC: _utilitiesThresholds(),
    IndustryGroup.GAS_UTILITY: _utilitiesThresholds(),
    IndustryGroup.AEROSPACE_DEFENSE: _airlineThresholds(),
    IndustryGroup.METALS: _metalsThresholds(),
    IndustryGroup.TELECOM: _telecomThresholds(),
}

_SECTOR_THRESHOLDS[Sector.ENERGY] = _energyThresholds()
