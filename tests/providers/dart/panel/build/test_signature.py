"""panel build signature mirror — leaf 내용 SimHash 결정론·값무관·태그strip (데이터 0).

``build/signature.py`` — 전체구조 수평화의 강한 앵커(leaf 내용 fingerprint)를 BUILD 가 굽는다.
순수함수라 데이터·네트워크 0. 결정론(증분 재현성)·값무관(같은 구조면 숫자 달라도 근접)·빈/짧음 0 검증.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_simhash_deterministic() -> None:
    """같은 입력 → 같은 출력 (프로세스 무관, build 재현성·증분 안전)."""
    from dartlab.providers.dart.panel.build.signature import simhash

    a = simhash("<TABLE><TD>재고자산</TD><TD>1,234,567</TD></TABLE>")
    b = simhash("<TABLE><TD>재고자산</TD><TD>1,234,567</TD></TABLE>")
    assert a == b
    assert isinstance(a, int) and 0 <= a < (1 << 64)


def test_simhash_value_invariant() -> None:
    """숫자(값)만 다른 같은 표 → Hamming 거의 0 (구조·라벨 지문 = 기간 간 정렬 앵커)."""
    from dartlab.providers.dart.panel.build.signature import hamming, simhash

    a = simhash("<TABLE><TD>재고자산</TD><TD>1,234,567</TD></TABLE>")
    c = simhash("<TABLE><TD>재고자산</TD><TD>9,999,999</TD></TABLE>")
    assert hamming(a, c) <= 2  # 값만 다름 → 동일/근접 (당신의 '빼서 0'의 내용판)


def test_simhash_different_content_far() -> None:
    """다른 내용 → Hamming 큼 (오정렬 방지)."""
    from dartlab.providers.dart.panel.build.signature import hamming, simhash

    a = simhash("<TABLE><TD>재고자산</TD><TD>1,234,567</TD></TABLE>")
    d = simhash("<P>당사는 반도체를 제조하는 회사로서 주요 사업은 메모리와 시스템반도체이다</P>")
    assert hamming(a, d) >= 10


def test_simhash_empty_short_zero() -> None:
    """빈/너무 짧은 leaf → 0 (시그니처 없음)."""
    from dartlab.providers.dart.panel.build.signature import simhash

    assert simhash("") == 0
    assert simhash("<P>가</P>") == 0


def test_plain_structure_strips_tags_and_digits() -> None:
    """plainStructure: 태그 + 숫자(값) 제거 → 구조·라벨만."""
    from dartlab.providers.dart.panel.build.signature import plainStructure

    out = plainStructure("<TD>매출액</TD><TD>1,234,567</TD>")
    assert "<" not in out and ">" not in out
    assert "1" not in out and "," not in out
    assert "매출액" in out
