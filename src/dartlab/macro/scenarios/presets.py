"""매크로 시나리오 프리셋 facade — 6 카탈로그 통합 진입점.

본 모듈은 4 카탈로그 (HISTORICAL/MODERN_RISK/STRUCTURAL/TYPED) + KR/DFAST 2 카탈로그를
import 로 재노출하고, ``getScenario`` / ``listAllScenarios`` 호출 로직만 담는다.

카탈로그 데이터 위치:
- HISTORICAL_SCENARIOS  → ``_presetsHistorical.py`` (15 시나리오)
- MODERN_RISK_SCENARIOS → ``_presetsModernRisk.py`` (6 시나리오)
- STRUCTURAL_SCENARIOS  → ``_presetsStructural.py`` (5 시나리오)
- SEVERITIES + TYPED_SCENARIOS → ``_presetsTyped.py`` (6 유형 × 4 심각도)
- DFAST_SCENARIOS + KR_SCENARIOS → ``_presetsKr.py`` (Fed DFAST + 한국 특화)

외부 호출자는 본 모듈의 ``getScenario`` / ``listAllScenarios`` 만 호출.
4 dict 직접 import 도 BC 보존을 위해 가능하지만 신규 코드는 함수 진입점 사용 권장.

Sources:
- Fed CCAR/DFAST 2025-2026 Severely Adverse
- IMF WP/13/28 (Claessens & Kose 2013)
- Gilchrist & Zakrajšek (2012 AER)
- FRED 역사적 시계열 실측
- IMF Korea FSAP (2020)
"""

from __future__ import annotations

from dartlab.macro.scenarios._presetsHistorical import HISTORICAL_SCENARIOS
from dartlab.macro.scenarios._presetsKr import DFAST_SCENARIOS, KR_SCENARIOS
from dartlab.macro.scenarios._presetsModernRisk import MODERN_RISK_SCENARIOS
from dartlab.macro.scenarios._presetsStructural import STRUCTURAL_SCENARIOS
from dartlab.macro.scenarios._presetsTyped import SEVERITIES, TYPED_SCENARIOS


def getScenario(name: str, *, severity: str | None = None, market: str = "US") -> dict | None:
    """시나리오 이름 → 프리셋 dict (역사/DFAST/현대/구조/유형/KR 6 카탈로그 부분 매칭).

    Capabilities:
        부분 문자열 매칭으로 6 카탈로그 (HISTORICAL/DFAST/MODERN_RISK/STRUCTURAL/
        TYPED/KR_SCENARIOS) + 복합 시나리오 ("A + B" 형태) 를 탐색하여 매크로
        override dict 를 반환. macro 시나리오 분석의 단일 진입점.

    Args:
        name: 시나리오 이름 (한글/영문). 부분 매칭. 복합은 ``"금리 충격 + 유가 충격"``.
        severity: ``"mild"``/``"moderate"``/``"severe"``/``"extreme"``. 유형별/
            구조적 시나리오에 적용. 기본 ``"moderate"``.
        market: ``"US"``/``"KR"``. ``"KR"`` 이면 역사적 재현의 ``kr_overrides`` 병합.

    Returns:
        dict | None: 매칭 시나리오 dict (description/type/severity/transmission/
            reference/overrides 키). 매칭 실패 시 ``None``.

    Raises:
        없음.

    Example:
        >>> getScenario("2008 GFC", market="KR")
        {'description': '...', 'overrides': {'gdpGrowth': [-5.1, ...], ...}}
        >>> getScenario("금리 충격 + 유가 충격", severity="severe")

    Guide:
        탐색 순서: 역사적 재현 → DFAST → 현대 리스크 → 구조적 → 유형별 →
        KR → 복합 (마지막). 가장 먼저 매칭된 시나리오 반환. 호출자는 결과
        dict 의 ``overrides`` 를 macro/summary 의 ``overrides`` 인자로 전달.

    SeeAlso:
        - ``listAllScenarios``: 사용 가능한 시나리오 목록
        - ``dartlab.macro.summary.analyzeSummary``: overrides 소비

    Requires:
        없음 (순수 함수).

    AIContext:
        시나리오 이름이 모호하면 listAllScenarios 로 카탈로그 확인 권장.
        market="KR" 호출 시 KR 특화 overrides 가 자동 병합되므로 미국 시나리오에서도
        한국 환율/금리 차이가 반영됨.

    LLM Specifications:
        AntiPatterns:
            - severity 추측 금지 — 4 옵션만 (mild/moderate/severe/extreme).
            - 매칭 실패 시 None 받고 그대로 호출자에 전파 금지 — 호출자가
              fallback (baseline) 사용하도록 분기 필요.
        OutputSchema:
            ``{description: str, type: str, severity: str, transmission: str,
            reference: str, overrides: dict}`` 또는 ``None``.
        Prerequisites:
            없음. 정적 카탈로그 룩업.
        Freshness:
            stateless — 카탈로그 수정 시 dartlab 버전 업그레이드 필요.
        Dataflow:
            name → 6 카탈로그 순차 탐색 → 부분 매칭 → 복합 시나리오 분해 →
            override dict 합성.
        TargetMarkets: US (DFAST/FRED), KR (KR_SCENARIOS + kr_overrides 병합).
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

    # 7. 복합 시나리오 (+ 구분)
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


__all__ = [
    "DFAST_SCENARIOS",
    "HISTORICAL_SCENARIOS",
    "KR_SCENARIOS",
    "MODERN_RISK_SCENARIOS",
    "SEVERITIES",
    "STRUCTURAL_SCENARIOS",
    "TYPED_SCENARIOS",
    "getScenario",
    "listAllScenarios",
]
