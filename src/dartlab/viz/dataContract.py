"""viz spec 이 호출자에게 요구하는 데이터 모양 명세 — Track F.

viz/ 는 표현 헬퍼 (CLAUDE.md "비즈니스 로직 0"). raw fetch 책임을 갖지 않고 *데이터 명세* 만 제공.
호출자 (L3 story 또는 L4 ai/tools) 가 본 contract 를 읽고 L1.5 frame/scan 으로 데이터를 채운다.

4 계층 단방향 import 룰 (CLAUDE.md):
- viz → L0 core / L1.5 frame.scan 을 import 하지 않는다. 명세만.
- 호출자가 dataContract 를 dict 로 받아 자기 책임으로 frame/scan 호출 → ViewSpec 의 series 데이터 채움.

별도 모듈 분리 이유:
- viz/schema.py 본체에 추가하지 않고 신규 모듈로 분리 — 다른 작업과의 충돌 회피.
- shape Literal + TypedDict 만 export. View / CatalogEntry 등 schema 의존 0.
"""

from __future__ import annotations

from typing import Literal, TypedDict

DataShape = Literal["timeseries", "crossSection", "scalar", "matrix"]
"""데이터 모양 분류 SSOT.

- timeseries: list[dict] — period 키 + 메트릭 키. 시계열 line/bar/area 차트.
- crossSection: list[dict] — 종목 식별자 + 메트릭 키. peer-matrix / 횡단면 스캔.
- scalar: dict[str, float] — 단일 시점 단일 메트릭 묶음 (KPI ribbon 등).
- matrix: 2D 매트릭스 — heatmap / 민감도 매트릭스.
"""


class DataContract(TypedDict, total=False):
    """viz spec 이 호출자에게 요구하는 데이터 모양 명세.

    - requiredKeys: list[str] — 데이터 dict 가 반드시 가져야 할 키 (예: ["stockCode", "revenue", "netIncome"]).
    - shape: DataShape — 위 4 분류 중 하나.
    - rowCount: tuple[int, int] — (min, max) 행 수 가드 (선택).
    - peerCount: int — crossSection 의 종목 수 (peer-matrix 권장 max 3).
    """

    requiredKeys: list[str]
    shape: DataShape
    rowCount: tuple[int, int]
    peerCount: int


def validate(contract: DataContract, data: object) -> tuple[bool, str]:
    """data 가 contract 를 만족하는지 검증.

    반환: (ok, errorMessage). ok=True 면 errorMessage 빈 문자열.
    silent fail 방지를 위해 viz dispatcher 에서 호출자에게 명확한 에러 메시지 노출.
    """
    shape = contract.get("shape")
    if shape == "timeseries" or shape == "crossSection":
        if not isinstance(data, list):
            return False, f"shape={shape!r} 요구: list 인데 받음 {type(data).__name__!r}"
        required = contract.get("requiredKeys") or []
        for index, row in enumerate(data):
            if not isinstance(row, dict):
                return False, f"row[{index}] 가 dict 아님 ({type(row).__name__!r})"
            missing = [key for key in required if key not in row]
            if missing:
                return False, f"row[{index}] requiredKeys 누락: {missing}"
        peer = contract.get("peerCount")
        if shape == "crossSection" and peer is not None and len(data) > peer:
            return False, f"crossSection peerCount={peer} 초과: 받음 {len(data)}"
        bounds = contract.get("rowCount")
        if bounds is not None:
            lower, upper = bounds
            if not lower <= len(data) <= upper:
                return False, f"rowCount {bounds} 위반: 받음 {len(data)}"
        return True, ""
    if shape == "scalar":
        if not isinstance(data, dict):
            return False, f"shape='scalar' 요구: dict 인데 받음 {type(data).__name__!r}"
        required = contract.get("requiredKeys") or []
        missing = [key for key in required if key not in data]
        if missing:
            return False, f"scalar requiredKeys 누락: {missing}"
        return True, ""
    if shape == "matrix":
        if not isinstance(data, list) or (data and not all(isinstance(row, list) for row in data)):
            return False, "shape='matrix' 요구: list[list]"
        return True, ""
    return False, f"알 수 없는 shape: {shape!r}"


__all__ = ["DataContract", "DataShape", "validate"]
