"""gather/dart viewer 단위 테스트 — fixture HTML + 형식 검증.

requires_network 통합 테스트는 별도 마커로 표시. 일반 unit run 에서 제외.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


# ══════════════════════════════════════
# _viewerParse 공용 헬퍼 — providers/dart 측
# ══════════════════════════════════════


class TestViewerParseHelpers:
    """providers/dart/_viewerParse 의 4 헬퍼 + 2 정규식 단위 테스트."""

    def test_tableToMarkdown_simple_table(self):
        from bs4 import BeautifulSoup

        from dartlab.core.parse.dartViewerPage import tableToMarkdown

        html = "<table><tr><th>회사명</th><th>코드</th></tr><tr><td>삼성</td><td>005930</td></tr></table>"
        table = BeautifulSoup(html, "lxml").find("table")
        md = tableToMarkdown(table)
        assert "| 회사명 | 코드 |" in md
        assert "| --- | --- |" in md
        assert "| 삼성 | 005930 |" in md

    def test_tableToMarkdown_empty_returns_empty(self):
        from bs4 import BeautifulSoup

        from dartlab.core.parse.dartViewerPage import tableToMarkdown

        table = BeautifulSoup("<table></table>", "lxml").find("table")
        assert tableToMarkdown(table) == ""

    def test_htmlToText_preserves_table_markdown(self):
        from dartlab.core.parse.dartViewerPage import htmlToText

        html = "<p>단락 1</p><table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table><p>단락 2</p>"
        text = htmlToText(html)
        assert "단락 1" in text
        assert "단락 2" in text
        assert "| A | B |" in text

    def test_htmlToText_strips_script_style(self):
        from dartlab.core.parse.dartViewerPage import htmlToText

        html = "<script>alert(1)</script><style>p{color:red}</style><p>본문</p>"
        text = htmlToText(html)
        assert "본문" in text
        assert "alert" not in text
        assert "color" not in text

    def test_parseSubDocs_multi_page(self):
        from dartlab.core.parse.dartViewerPage import parseSubDocs

        # MULTI_PAGE_RE 가 매칭되는 viewer 페이지 인덱스 구조 mock
        content = (
            " node1['text'] = \"1. 회사의 개요\";\n"
            " node1['id'] = \"01\";\n"
            " node1['rcpNo'] = \"20240315000123\";\n"
            " node1['dcmNo'] = \"9999999\";\n"
            " node1['eleId'] = \"0\";\n"
            " node1['offset'] = \"0\";\n"
            " node1['length'] = \"12345\";\n"
            " node1['dtd'] = \"dart3.xsd\";\n"
            " node1['tocNo'] = \"01\";\n"
        )
        result = parseSubDocs(content, "20240315000123")
        assert len(result) == 1
        assert result[0]["title"] == "1. 회사의 개요"
        assert result[0]["order"] == 0
        assert result[0]["rcept_no"] == "20240315000123"
        assert "rcpNo=20240315000123" in result[0]["url"]
        assert "report/viewer.do" in result[0]["url"]

    def test_parseSubDocs_empty_when_no_match(self):
        from dartlab.core.parse.dartViewerPage import parseSubDocs

        assert parseSubDocs("<html><body>no nodes</body></html>", "20240315000123") == []


# ══════════════════════════════════════
# gather/dart/viewer — 형식 검증
# ══════════════════════════════════════


class TestRceptNoValidation:
    """rcept_no 형식 검증 (14자리 숫자)."""

    def test_valid_14digit(self):
        from dartlab.gather.dart.viewer import _validateRceptNo

        _validateRceptNo("20240315000123")  # 예외 없음

    def test_invalid_short(self):
        from dartlab.gather.dart.types import InvalidRceptNoError
        from dartlab.gather.dart.viewer import _validateRceptNo

        with pytest.raises(InvalidRceptNoError, match="14자리"):
            _validateRceptNo("12345")

    def test_invalid_letters(self):
        from dartlab.gather.dart.types import InvalidRceptNoError
        from dartlab.gather.dart.viewer import _validateRceptNo

        with pytest.raises(InvalidRceptNoError):
            _validateRceptNo("abcdefghijklmn")

    def test_invalid_15digit(self):
        from dartlab.gather.dart.types import InvalidRceptNoError
        from dartlab.gather.dart.viewer import _validateRceptNo

        with pytest.raises(InvalidRceptNoError):
            _validateRceptNo("123456789012345")


# ══════════════════════════════════════
# gather/dart/__init__ + GatherEntry 통합
# ══════════════════════════════════════


class TestPublicSurface:
    """Dart facade, GatherEntry 축 등록 확인."""

    def test_dart_class_available(self):
        from dartlab.gather.dart import Dart

        d = Dart()
        assert callable(d.doc)
        assert callable(d.meta)

    def test_gather_entry_axis_registered(self):
        from dartlab.gather.entry import API_KEY_INFO, AXIS_REGISTRY

        assert "dartDoc" in AXIS_REGISTRY
        assert "dartDoc" in API_KEY_INFO
        assert API_KEY_INFO["dartDoc"].startswith("불필요")
        entry = AXIS_REGISTRY["dartDoc"]
        assert entry.targetType == "rceptNo"

    def test_gather_class_has_dartDoc_method(self):
        from dartlab.gather import Gather

        assert callable(getattr(Gather, "dartDoc", None))

    def test_domain_policy_registered(self):
        from dartlab.gather.infra.http import DOMAIN_POLICY

        assert "dart.fss.or.kr" in DOMAIN_POLICY
