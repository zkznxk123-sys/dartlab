"""leaf 내용 시그니처 (SimHash 64-bit) — 전체구조 수평화의 강한 앵커를 BUILD 가 굽는다.

수평화 정렬(READ)은 leaf(text/table) *내용* 으로 기간 간 매치한다(제목은 약한 앵커 53%, 내용은 강한 앵커 82%
— `tests/_attempts/horizonMapperDemo/contentHashDemo.py` 실증). 그 내용 fingerprint 를 leaf 마다 1개 64-bit
SimHash 로 BUILD 가 굽는다 (per-leaf 결정론 = 그 zip 하나로 결정, 증분 안전; 8B/leaf, OOM 무관).

지문 추출: contentRaw → 태그 제거 + **숫자(값) 제거**(값은 해마다 변하니 구조·라벨만 남김) → char 4-shingle →
SimHash 64-bit. 비슷한 내용 = 가까운 Hamming 거리. 생성=BUILD, 비교(Hamming/LSH)=READ (책임 분리).
"""

from __future__ import annotations

import re

import numpy as np

_TAG = re.compile(r"<[^>]+>")
_DIGIT = re.compile(r"[\d,.\-()%]+")  # 값(숫자·콤마·괄호·부호·퍼센트) 제거 — 구조·라벨 지문만
_WS = re.compile(r"\s+")
_MASK64 = (1 << 64) - 1
_FNV_OFFSET = 14695981039346656037
_FNV_PRIME = 1099511628211
_BITS = np.arange(64, dtype=np.uint64)
_MINLEN = 6


def plainStructure(content_raw: str) -> str:
    """contentRaw → 태그·숫자 제거 plain (구조·라벨 지문). 순수함수."""
    t = _TAG.sub(" ", content_raw or "")
    t = _DIGIT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def _fnv64(s: str) -> int:
    """FNV-1a 64-bit (결정론 — 프로세스 무관 안정, build 재현성)."""
    h = _FNV_OFFSET
    for ch in s:
        h = ((h ^ ord(ch)) * _FNV_PRIME) & _MASK64
    return h


def simhash(content_raw: str) -> int:
    """leaf contentRaw → 64-bit SimHash uint64 (내용 fingerprint). 빈/짧으면 0.

    Args:
        content_raw: leaf 원본 XML 문자열 (태그 포함).

    Returns:
        64-bit 부호없는 정수 SimHash. 같은 입력 같은 출력(결정론). 내용 유사 → Hamming 가까움.
        숫자(값) 제거 후이므로 같은 표가 값만 다르면 동일/근접 — 기간 간 정렬 앵커.

    Example:
        >>> simhash("<P>재고자산</P>") == simhash("<P>재고자산</P>")
        True
        >>> simhash("") == 0
        True
    """
    text = plainStructure(content_raw)
    if len(text) < _MINLEN:
        return 0
    shingles = {text[i : i + 4] for i in range(0, len(text) - 3, 2)}
    if not shingles:
        return 0
    hs = np.fromiter((_fnv64(s) for s in shingles), dtype=np.uint64, count=len(shingles))
    # 각 shingle 해시의 비트를 +1/-1 누적 → 양수 비트만 1.
    bitmat = ((hs[:, None] >> _BITS) & np.uint64(1)).astype(np.int64)  # (n, 64)
    summed = bitmat.sum(axis=0) * 2 - len(hs)  # +1(set)/-1(unset)
    sign = (summed > 0).astype(np.uint64)  # (64,)
    return int((sign << _BITS).sum())


def hamming(a: int, b: int) -> int:
    """두 SimHash 간 Hamming 거리 (0~64, 작을수록 유사) — READ 비교용 헬퍼."""
    return int(bin((a ^ b) & _MASK64).count("1"))
