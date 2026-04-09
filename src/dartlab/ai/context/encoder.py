"""TOON (Token-Oriented Object Notation) 인코더.

LLM 입력용 압축 표현. 같은 데이터를 JSON 대비 30~60% 적은 토큰으로 주입.
일부 케이스(작은 dict)에는 효과 없음 — encodeAuto가 작은 입력은 JSON 유지.

참조: TOON 사양 (2026, llm-data 압축 포맷)
- 키: 한 번만 등장 (헤더 행)
- 값: 행 단위 정렬
- 깊은 중첩 최소화 (LLM 어텐션이 가장 잘 처리하는 형태)

dartlab은 외부 의존성 추가 없이 자체 구현 — 단순 직렬화.
"""

from __future__ import annotations

import json
from typing import Any


def _isFlatList(value: Any) -> bool:
    """list[dict] 형태이고 모든 dict가 같은 키 집합인지."""
    if not isinstance(value, list) or not value:
        return False
    if not all(isinstance(x, dict) for x in value):
        return False
    first_keys = tuple(value[0].keys())
    return all(tuple(x.keys()) == first_keys for x in value)


def _encodeFlatList(rows: list[dict[str, Any]]) -> str:
    """list[dict] → TOON 표 형식.

    예::

        [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        →
        a|b
        1|2
        3|4
    """
    if not rows:
        return ""
    keys = list(rows[0].keys())
    header = "|".join(keys)
    lines = [header]
    for row in rows:
        cells = []
        for k in keys:
            v = row.get(k)
            if v is None:
                cells.append("")
            elif isinstance(v, (int, float, str, bool)):
                cells.append(str(v))
            else:
                cells.append(json.dumps(v, ensure_ascii=False, default=str))
        lines.append("|".join(cells))
    return "\n".join(lines)


def _encodeDict(d: dict[str, Any], depth: int = 0) -> str:
    """dict → TOON key:value 행 형식. 중첩 list[dict]는 표로 변환."""
    if not d:
        return ""
    lines = []
    indent = "  " * depth
    for k, v in d.items():
        if _isFlatList(v):
            lines.append(f"{indent}{k}:")
            table = _encodeFlatList(v)
            lines.extend(f"{indent}  {ln}" for ln in table.split("\n"))
        elif isinstance(v, dict):
            lines.append(f"{indent}{k}:")
            lines.append(_encodeDict(v, depth + 1))
        elif isinstance(v, list):
            # 단순 list[scalar] — 한 줄에 ,로
            lines.append(f"{indent}{k}: " + ", ".join(str(x) for x in v))
        elif v is None:
            lines.append(f"{indent}{k}: -")
        else:
            lines.append(f"{indent}{k}: {v}")
    return "\n".join(lines)


def encodeTOON(data: Any) -> str:
    """임의 데이터 → TOON 텍스트.

    list[dict] (균질) → 표 형식
    dict → key:value (중첩 처리)
    그 외 → JSON fallback
    """
    if _isFlatList(data):
        return _encodeFlatList(data)
    if isinstance(data, dict):
        return _encodeDict(data)
    return json.dumps(data, ensure_ascii=False, default=str)


def encodeAuto(data: Any, *, jsonThresholdChars: int = 200) -> str:
    """작은 입력은 JSON, 큰 입력은 TOON.

    작은 dict는 JSON이 더 짧을 수 있음 (헤더 오버헤드 없음).
    """
    js = json.dumps(data, ensure_ascii=False, default=str)
    if len(js) < jsonThresholdChars:
        return js
    toon = encodeTOON(data)
    # TOON이 더 길면 JSON 사용 (안전장치)
    return toon if len(toon) < len(js) else js


def estimateTokens(text: str) -> int:
    """rough 토큰 추정 — 한국어 + 영문 혼합 기준 평균 1토큰 ≈ 2.5 chars."""
    if not text:
        return 0
    return max(1, len(text) // 3)
