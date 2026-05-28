"""xmlAdapter._tableToHtml ALIGN/VALIGN 보존 회귀 가드.

plan snazzy-wibbling-origami PR-1b. DART 원본 ``<TD ALIGN="RIGHT">`` 의 ALIGN 속성을
``<td align="right">`` 로 emit. 옛 구현은 ALIGN 을 cell.get() 호출조차 안 해 viewer
에서 모든 cell 좌측정렬 회귀 (2026-05-28 사용자 발견).
"""

from __future__ import annotations

import pytest

from dartlab.providers.dart.docs.sectionsArchive.xmlAdapter import xmlChunkToMixed

pytestmark = [pytest.mark.unit]


def test_align_attribute_preserved_lowercase():
    xml = '<TABLE BORDER="1"><TR><TD ALIGN="RIGHT">100</TD><TD ALIGN="LEFT">A</TD></TR><TR><TD>X</TD><TD>Y</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert 'align="right"' in out
    assert 'align="left"' in out


def test_align_center_and_justify():
    xml = '<TABLE BORDER="1"><TR><TD ALIGN="CENTER">A</TD><TD ALIGN="JUSTIFY">B</TD></TR><TR><TD>X</TD><TD>Y</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert 'align="center"' in out
    assert 'align="justify"' in out


def test_valign_top_middle_bottom():
    xml = '<TABLE BORDER="1"><TR><TD VALIGN="TOP">A</TD><TD VALIGN="MIDDLE">B</TD><TD VALIGN="BOTTOM">C</TD></TR><TR><TD>X</TD><TD>Y</TD><TD>Z</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert 'valign="top"' in out
    assert 'valign="middle"' in out
    assert 'valign="bottom"' in out


def test_align_with_colspan_rowspan_combined():
    xml = '<TABLE BORDER="1"><TR><TD COLSPAN="2" ALIGN="RIGHT">금액</TD></TR><TR><TD ROWSPAN="2" ALIGN="CENTER">A</TD><TD>1</TD></TR><TR><TD>2</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    # colspan 과 align 동시 보존 — 옛 구현이 colspan 만 박았으면 attr 순서 의존 검증
    assert 'colspan="2"' in out and 'align="right"' in out
    assert 'rowspan="2"' in out and 'align="center"' in out


def test_invalid_align_value_dropped():
    # ALIGN whitelist 외 값은 silent drop (XSS 등 보안 회피 + sanitize 위생).
    xml = '<TABLE BORDER="1"><TR><TD ALIGN="INVALID">A</TD><TD ALIGN="onclick=alert(1)">B</TD></TR><TR><TD>X</TD><TD>Y</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert "align" not in out


def test_dart_uppercase_attr_only_supported():
    # lxml.cell.get() 은 case-sensitive — DART 표준 "ALIGN" uppercase 만 매치.
    # lowercase "align" 는 attr 부재로 본다. DART XML 실제 양식은 uppercase 라 실용 문제 X.
    xml = '<TABLE BORDER="1"><TR><TD align="right">100</TD></TR><TR><TD>X</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    # lowercase attr 는 인식 안 됨 → align 없는 그냥 td
    assert "align" not in out


def test_empty_align_attribute_no_emit():
    xml = '<TABLE BORDER="1"><TR><TD ALIGN="">A</TD></TR><TR><TD>B</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert "align" not in out


def test_th_tag_also_preserves_align():
    xml = '<TABLE BORDER="1"><TR><TH ALIGN="CENTER">헤더</TH></TR><TR><TD ALIGN="RIGHT">100</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert '<th align="center">' in out
    assert '<td align="right">' in out


def test_paragraph_framing_unchanged_by_align():
    # 1×1 cell paragraph framing 은 plain text emit — align 정보는 layout 손실 (옛 동작 유지).
    xml = '<TABLE BORDER="0"><TR><TD ALIGN="RIGHT">단위 : 백만원</TD></TR></TABLE>'
    out = xmlChunkToMixed(xml)
    assert out == "단위 : 백만원"
    assert "align" not in out
    assert "<table" not in out
