"""dartlab 단위 정규화 — 단일 진실의 원천.

dartlab 의 모든 금액 데이터는 **원 단위 (KRW) 또는 USD raw** 로 노출된다.
DART 공시 raw 의 단위 표기 (백만원/천원/원) 를 원 단위로 일관 변환하는
단일 헬퍼.

기존 분산:
- `core/constants.py::UNIT_SCALE` 백만원=1.0 (거꾸로 표준 — 백만원 기준)
- `core/tableParser.py::detectUnit` (단위 감지)
- `notesDetail/pipeline.py::_buildTableDf` 의 ×1_000_000 (Phase 1 임시 fix)
- 33+ docs/finance parser 가 각자 `if unit != 1.0: val *= unit` 처리

이 헬퍼가 단일 진입점:
- 36 parser 모두 amount 노출 직전 `normalizeFinanceAmount` 호출
- 단위 표기 (`백만원/천원/원`) 를 받아 원 단위 float 반환
- None / 빈 문자열 / 0 / 음수 모두 안전 처리

데이터 계약:
- DART finance/notes/report → 원 단위 (KRW)
- EDGAR finance/notes/report → USD raw (XBRL companyfacts)
- BS = stock (시점 잔액), IS/CF = flow (분기 단독값, dartlab pivot 이 변환)

검증: tests/test_unit_scale_consistency.py — 5 sample 종목 magnitude
회귀 ground truth.
"""

from __future__ import annotations

# 원 단위 기준 변환 계수.
# `1 백만원 = 1_000_000 원`
# 기존 `core/constants.py::UNIT_SCALE` 은 백만원=1.0 표준이라 거꾸로.
# 이 헬퍼는 원 기준 — 곱하면 원 단위로 변환됨.
_UNIT_TO_WON: dict[str, int] = {
    "백만원": 1_000_000,
    "백만 원": 1_000_000,
    "천원": 1_000,
    "천 원": 1_000,
    "원": 1,
    "KRW": 1,
}


def normalizeFinanceAmount(
    amount: float | int | str | None,
    unitLabel: str | None = "백만원",
) -> float | None:
    """raw 금액 + 단위 표기 → 원 단위 float.

    Args:
        amount: raw 값. None / 빈 문자열 / 숫자 / 콤마 포함 문자열 모두 처리.
        unitLabel: DART 공시의 "단위:" 표기 (`백만원`, `천원`, `원`).
                   None 이면 백만원 기본 (DART 공시 표준).

    Returns:
        원 단위 float. amount 가 None/빈/파싱 실패면 None.

    Examples:
        >>> normalizeFinanceAmount(12_097_207, "백만원")
        12097207000000.0   # 12.1조
        >>> normalizeFinanceAmount("1,234,567", "백만원")
        1234567000000.0
        >>> normalizeFinanceAmount(None, "백만원")
        None
        >>> normalizeFinanceAmount("", "백만원")
        None
        >>> normalizeFinanceAmount(0, "원")
        0.0
    """
    if amount is None:
        return None
    if isinstance(amount, str):
        s = amount.strip().replace(",", "")
        if not s or s == "-":
            return None
        try:
            value = float(s)
        except ValueError:
            return None
    elif isinstance(amount, (int, float)):
        value = float(amount)
    else:
        return None

    factor = _UNIT_TO_WON.get(unitLabel or "백만원", 1_000_000)
    return value * factor


def normalizeFromUnitScale(
    amount: float | int | str | None,
    unitScale: float,
) -> float | None:
    """`core/constants.py::UNIT_SCALE` 의 곱셈 계수 (백만원=1.0 표준) 를 받는 변형.

    기존 parser 코드와의 호환을 위해. 새 코드는 `normalizeFinanceAmount` 사용 권장.

    Args:
        amount: raw 값
        unitScale: UNIT_SCALE 값 (백만원=1.0, 천원=0.001, 원=0.000001)

    Returns:
        원 단위 float

    Examples:
        >>> from dartlab.core.constants import UNIT_SCALE
        >>> normalizeFromUnitScale(12_097_207, UNIT_SCALE["백만원"])
        12097207000000.0
        >>> normalizeFromUnitScale(12_097_207_000_000, UNIT_SCALE["원"])
        12097207000000.0
    """
    if amount is None:
        return None
    if isinstance(amount, str):
        s = amount.strip().replace(",", "")
        if not s or s == "-":
            return None
        try:
            value = float(s)
        except ValueError:
            return None
    elif isinstance(amount, (int, float)):
        value = float(amount)
    else:
        return None

    # UNIT_SCALE 백만원=1.0 표준 → 백만원 단위로 수렴 후 ×1_000_000 해서 원 단위로
    return value * unitScale * 1_000_000
