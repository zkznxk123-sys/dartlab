"""DART 본문 / heading 의 period marker (날짜·분기·누계·단위) 제거 SSOT.

cross-period 정합 (같은 logical heading 또는 표 의 *동일 segmentKey* 보장) 의 단일
정규화 위치. 옛 분산 회귀 — ``textStructure.semanticKey`` 가 leaf "기준일: 2025년
06월 30일" 같은 날짜 박힌 heading 을 그대로 정규화 → period 별 semantic 분기 →
같은 표가 다른 row 로. 본 모듈의 ``stripPeriodMarkers`` 가 단일 정규화 진입점.

display 라벨 (``textPath``) 은 보존 — 사용자 화면에 "기준일: 2025년 06월 30일"
원본 그대로 노출. 본 strip 은 *semantic key* (cross-period 매칭 키) 만 대상.

Example:
    >>> stripPeriodMarkers("기준일: 2025년 06월 30일")
    '기준일:'
    >>> stripPeriodMarkers("(단위: 백만원)")
    ''
    >>> stripPeriodMarkers("제78기 반기누계")
    ''
    >>> stripPeriodMarkers("당사의 시설 2026년 1분기말")
    '당사의 시설 '
"""

from __future__ import annotations

import re

# period marker — 분기/말/누계/날짜/단위.
# 매칭 우선순위: 더 긴 매치가 먼저 (한국어 + 숫자 결합).
_PERIOD_MARKER_RE = re.compile(
    r"(?:"
    r"\d+\s*년\s*\d*\s*월?\s*\d*\s*일?|"  # 2025년 12월 31일 / 2025년 12월 / 2025년
    r"\d+\s*년말|\d+\s*년\s*반기말?|\d+\s*년\s*\d*\s*분기말?|"  # 2025년말 / 반기말 / 1분기말
    r"제\s*\d+\s*기\s*\S*\s*누계|"  # 제78기 누계 / 제79기 1분기누계
    r"제\s*\d+\s*기|"  # 제78기
    r"\(\s*단위\s*[:：]\s*[^)]+\)|"  # (단위: 백만원)
    r"기준일\s*[:：]\s*\d+\.\d+\.\d+|"  # 기준일: 2025.12.31
    r"\d+\.\d+\.\d+|"  # 2025.12.31
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"  # 2025/12/31 또는 2025-12-31
    r")"
)


def stripPeriodMarkers(text: str | None) -> str:
    """text 안 period marker 토큰 제거. None / empty 는 빈 문자열 반환.

    cross-period semantic key 계산 진입점. caller 는 strip 후 추가 정규화
    (공백 제거 / lowercase 등) 를 자유롭게 적용.

    Args:
        text: 원본 본문 / heading 텍스트.

    Returns:
        period marker 제거된 문자열. display 라벨 변경 금지 — semantic key 용도만.
    """
    if not text:
        return ""
    return _PERIOD_MARKER_RE.sub("", text)


__all__ = ["stripPeriodMarkers"]
