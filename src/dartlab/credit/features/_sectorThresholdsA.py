"""sectorThresholds 의 A 분류 — default/utilities/financials/construction/it/energy + _SECTOR_THRESHOLDS dict."""

from __future__ import annotations

from dartlab.frame.sector import Sector


def _defaultThresholds() -> dict:
    """기본(제조업) 기준표. 미분류 업종 fallback."""
    return {
        # ── 채무상환능력 ──
        "ebitda_interest_coverage": {
            "lower_is_better": False,
            "breakpoints": [
                (12.0, 0),
                (8.5, 5),
                (6.5, 10),
                (5.0, 18),
                (3.5, 28),
                (2.0, 42),
                (1.0, 62),
                (0.5, 78),
                (0.0, 95),
            ],
        },
        "debt_to_ebitda": {
            "lower_is_better": True,
            "breakpoints": [
                (0.0, 0),
                (0.5, 3),
                (1.0, 8),
                (1.5, 15),
                (2.5, 25),
                (3.5, 38),
                (5.0, 58),
                (7.0, 75),
                (10.0, 90),
            ],
        },
        "ffo_to_debt": {
            "lower_is_better": False,
            "breakpoints": [
                (60.0, 0),
                (45.0, 5),
                (35.0, 12),
                (25.0, 20),
                (15.0, 35),
                (10.0, 50),
                (5.0, 68),
                (0.0, 85),
            ],
        },
        "focf_to_debt": {
            "lower_is_better": False,
            "breakpoints": [
                (40.0, 0),
                (25.0, 8),
                (15.0, 18),
                (10.0, 28),
                (5.0, 42),
                (0.0, 60),
                (-10.0, 80),
                (-20.0, 95),
            ],
        },
        # ── 레버리지 ──
        "debt_ratio": {
            "lower_is_better": True,
            "breakpoints": [
                (0.0, 0),
                (30.0, 2),
                (50.0, 5),
                (80.0, 10),
                (120.0, 18),
                (180.0, 30),
                (250.0, 48),
                (350.0, 68),
                (500.0, 85),
                (800.0, 95),
            ],
        },
        "borrowing_dependency": {
            "lower_is_better": True,
            "breakpoints": [
                (0.0, 0),
                (5.0, 3),
                (10.0, 8),
                (20.0, 18),
                (30.0, 30),
                (40.0, 48),
                (50.0, 65),
                (60.0, 80),
            ],
        },
        "net_debt_to_ebitda": {
            "lower_is_better": True,
            "breakpoints": [
                (-2.0, 0),
                (0.0, 3),
                (1.0, 10),
                (2.0, 18),
                (3.0, 28),
                (4.0, 42),
                (6.0, 60),
                (8.0, 78),
                (10.0, 90),
            ],
        },
        # ── 유동성 ──
        "current_ratio": {
            "lower_is_better": False,
            "breakpoints": [
                (300.0, 0),
                (200.0, 5),
                (150.0, 12),
                (120.0, 20),
                (100.0, 32),
                (80.0, 48),
                (50.0, 68),
                (30.0, 85),
            ],
        },
        "cash_ratio": {
            "lower_is_better": False,
            "breakpoints": [
                (50.0, 0),
                (30.0, 8),
                (20.0, 18),
                (10.0, 32),
                (5.0, 50),
                (2.0, 70),
                (0.0, 88),
            ],
        },
        "short_term_debt_ratio": {
            "lower_is_better": True,
            "breakpoints": [
                (0.0, 0),
                (10.0, 5),
                (20.0, 12),
                (30.0, 22),
                (40.0, 35),
                (50.0, 50),
                (70.0, 72),
                (90.0, 90),
            ],
        },
    }


def _utilitiesThresholds() -> dict:
    """유틸리티 업종 — 높은 부채 허용, 안정 현금흐름, 공기업 특성.

    한전: 유동비율 ~60%, 부채비율 300%+는 공기업 구조상 정상.
    """
    base = _defaultThresholds()
    # 부채비율 기준 완화
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (50.0, 2),
        (100.0, 5),
        (150.0, 10),
        (200.0, 18),
        (300.0, 30),
        (400.0, 48),
        (600.0, 68),
        (800.0, 85),
    ]
    # 유동비율 완화 (공기업/전력은 설비 자산 비중 높아 유동비율 낮음)
    base["current_ratio"]["breakpoints"] = [
        (200.0, 0),
        (150.0, 5),
        (120.0, 10),
        (100.0, 18),
        (80.0, 25),
        (60.0, 35),
        (40.0, 52),
        (20.0, 72),
    ]
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (1.0, 3),
        (2.0, 8),
        (3.0, 15),
        (4.0, 25),
        (5.0, 38),
        (7.0, 58),
        (10.0, 75),
        (15.0, 90),
    ]
    base["net_debt_to_ebitda"]["breakpoints"] = [
        (-2.0, 0),
        (0.0, 3),
        (2.0, 10),
        (3.0, 18),
        (4.0, 28),
        (6.0, 42),
        (8.0, 60),
        (10.0, 78),
        (15.0, 90),
    ]
    return base


def _financialsThresholds() -> dict:
    """금융업 — 레버리지 구조 다름, 자본 적정성 중심."""
    base = _defaultThresholds()
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (100.0, 2),
        (200.0, 5),
        (400.0, 10),
        (600.0, 20),
        (800.0, 35),
        (1000.0, 55),
        (1500.0, 75),
        (2000.0, 90),
    ]
    # Debt/EBITDA는 금융업에서 의미 제한적 — 가중치 감소로 처리
    base["borrowing_dependency"]["breakpoints"] = [
        (0.0, 0),
        (20.0, 3),
        (40.0, 8),
        (60.0, 18),
        (70.0, 30),
        (80.0, 48),
        (90.0, 65),
        (95.0, 80),
    ]
    return base


def _constructionThresholds() -> dict:
    """건설업 — 프로젝트 기반, 현금흐름 불규칙."""
    base = _defaultThresholds()
    # 유동비율 기준 강화 (선수금/미청구공사 구조)
    base["current_ratio"]["breakpoints"] = [
        (350.0, 0),
        (250.0, 5),
        (180.0, 12),
        (150.0, 20),
        (120.0, 32),
        (100.0, 48),
        (70.0, 68),
        (40.0, 85),
    ]
    return base


def _itThresholds() -> dict:
    """IT — 무형자산 비중 높음, 현금 보유 중시."""
    base = _defaultThresholds()
    # 부채비율 기준 강화 (유형자산 적어 담보력 약함)
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (20.0, 2),
        (40.0, 5),
        (60.0, 10),
        (100.0, 20),
        (150.0, 35),
        (200.0, 52),
        (300.0, 72),
        (500.0, 90),
    ]
    return base


# ── 업종 매핑 ──

_SECTOR_THRESHOLDS: dict[Sector, dict] = {
    Sector.ENERGY: _defaultThresholds(),
    Sector.MATERIALS: _defaultThresholds(),
    Sector.INDUSTRIALS: _defaultThresholds(),
    Sector.CONSUMER_DISC: _defaultThresholds(),
    Sector.CONSUMER_STAPLES: _defaultThresholds(),
    Sector.HEALTHCARE: _defaultThresholds(),
    Sector.FINANCIALS: _financialsThresholds(),
    Sector.IT: _itThresholds(),
    Sector.COMMUNICATION: _itThresholds(),
    Sector.UTILITIES: _utilitiesThresholds(),
    Sector.REAL_ESTATE: _utilitiesThresholds(),
    Sector.UNKNOWN: _defaultThresholds(),
}


def _energyThresholds() -> dict:
    """에너지 — 사이클 업종, 높은 부채/CAPEX 허용."""
    base = _defaultThresholds()
    base["debt_ratio"]["breakpoints"] = [
        (0.0, 0),
        (40.0, 2),
        (80.0, 5),
        (120.0, 10),
        (180.0, 18),
        (250.0, 30),
        (350.0, 48),
        (500.0, 68),
        (700.0, 85),
    ]
    base["debt_to_ebitda"]["breakpoints"] = [
        (0.0, 0),
        (0.5, 3),
        (1.5, 8),
        (2.5, 15),
        (3.5, 25),
        (5.0, 38),
        (7.0, 55),
        (10.0, 75),
        (15.0, 90),
    ]
    return base
