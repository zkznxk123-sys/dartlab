"""AI runtime core.py 단위 테스트 — 종목 검색, 외부 검색 판단, Polars 변환.

외부 API 호출은 모두 mock 처리.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ══════════════════════════════════════
# 4. _polarsTableToMarkdown
# ══════════════════════════════════════


class TestPolarsTableToMarkdown:
    def test_no_table_passthrough(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = "Hello world\nNo tables here"
        assert _polarsTableToMarkdown(text) == text

    def test_simple_polars_table(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = (
            "┌──────┬──────┐\n"
            "│ col1 ┆ col2 │\n"
            "│ ---  ┆ ---  │\n"
            "│ str  ┆ f64  │\n"
            "╞══════╪══════╡\n"
            "│ a    ┆ 1.0  │\n"
            "│ b    ┆ 2.0  │\n"
            "└──────┴──────┘"
        )
        result = _polarsTableToMarkdown(text)
        assert "| col1 | col2 |" in result
        assert "| --- | --- |" in result
        assert "| a | 1.0 |" in result
        assert "| b | 2.0 |" in result
        assert "┌" not in result
        assert "└" not in result

    def test_null_converted_to_dash(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = (
            "┌──────┬──────┐\n"
            "│ col1 ┆ col2 │\n"
            "│ ---  ┆ ---  │\n"
            "│ str  ┆ f64  │\n"
            "╞══════╪══════╡\n"
            "│ a    ┆ null │\n"
            "└──────┴──────┘"
        )
        result = _polarsTableToMarkdown(text)
        assert "| a | - |" in result

    def test_mixed_content(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = "Before table\n┌──────┐\n│ col1 │\n│ ---  │\n│ str  │\n╞══════╡\n│ val  │\n└──────┘\nAfter table"
        result = _polarsTableToMarkdown(text)
        assert "Before table" in result
        assert "After table" in result
        assert "| col1 |" in result

    def test_preserves_non_table_lines(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = "line1\nline2\nline3"
        result = _polarsTableToMarkdown(text)
        assert result == text

    def test_multiple_tables(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = (
            "Table 1:\n"
            "┌──────┐\n│ A │\n│ --- │\n│ str │\n╞══════╡\n│ x │\n└──────┘\n"
            "Table 2:\n"
            "┌──────┐\n│ B │\n│ --- │\n│ str │\n╞══════╡\n│ y │\n└──────┘\n"
        )
        result = _polarsTableToMarkdown(text)
        assert "| A |" in result
        assert "| B |" in result
        assert "| x |" in result
        assert "| y |" in result

    def test_ellipsis_rows_skipped(self):
        from dartlab.ai.tools.serialize import polarsTableToMarkdown as _polarsTableToMarkdown

        text = (
            "┌──────┬──────┐\n"
            "│ col1 ┆ col2 │\n"
            "│ ---  ┆ ---  │\n"
            "│ str  ┆ f64  │\n"
            "╞══════╪══════╡\n"
            "│ a    ┆ 1.0  │\n"
            "│ …    ┆ …    │\n"
            "│ z    ┆ 9.0  │\n"
            "└──────┴──────┘"
        )
        result = _polarsTableToMarkdown(text)
        assert "| a | 1.0 |" in result
        assert "| z | 9.0 |" in result
        # Ellipsis row should be skipped
        assert "…" not in result


# ══════════════════════════════════════
# 6. _validateCode (from ai/tools/coding.py)
# ══════════════════════════════════════


class TestValidateCode:
    def test_valid_code(self):
        from dartlab.ai.tools.coding import _validateCode

        _validateCode("x = 1 + 2")  # should not raise

    def test_valid_function(self):
        from dartlab.ai.tools.coding import _validateCode

        code = "def foo():\n    return 42"
        _validateCode(code)

    def test_valid_import(self):
        from dartlab.ai.tools.coding import _validateCode

        _validateCode("import os\nprint(os.getcwd())")

    def test_invalid_syntax_raises(self):
        from dartlab.ai.tools.coding import _validateCode

        with pytest.raises(SyntaxError):
            _validateCode("def foo(")

    def test_invalid_indent_raises(self):
        from dartlab.ai.tools.coding import _validateCode

        with pytest.raises(SyntaxError):
            _validateCode("def foo():\nreturn 1")

    def test_empty_code_is_valid(self):
        from dartlab.ai.tools.coding import _validateCode

        _validateCode("")  # empty is syntactically valid

    def test_multiline_valid(self):
        from dartlab.ai.tools.coding import _validateCode

        code = """
import polars as pl

df = pl.DataFrame({"a": [1, 2, 3]})
print(df)
"""
        _validateCode(code)

    def test_expression_valid(self):
        from dartlab.ai.tools.coding import _validateCode

        _validateCode("2 + 2")

    def test_incomplete_string_raises(self):
        from dartlab.ai.tools.coding import _validateCode

        with pytest.raises(SyntaxError):
            _validateCode('x = "hello')


# ══════════════════════════════════════
# 7. _replaceLargeNumber (nested in LocalPythonBackend._postprocessAnswer)
# ══════════════════════════════════════


class TestReplaceLargeNumber:
    r"""_replaceLargeNumber is a nested function. We test its behavior
    via the regex pattern it uses: r"-?\d{9,}(?:\.0)?"."""

    _PATTERN = re.compile(r"-?\d{9,}(?:\.0)?")

    @staticmethod
    def _replace(m: re.Match) -> str:
        """Replicate the nested _replaceLargeNumber logic."""
        try:
            raw = m.group(0)
            if "." in raw and not raw.endswith(".0"):
                return raw
            val = float(raw)
            absVal = abs(val)
            sign = "-" if val < 0 else ""
            if absVal >= 1e12:
                return f"{sign}{absVal / 1e12:,.1f}조"
            if absVal >= 1e8:
                return f"{sign}{absVal / 1e8:,.0f}억"
            return raw
        except (ValueError, OverflowError):
            return m.group(0)

    def test_trillion_conversion(self):
        result = self._PATTERN.sub(self._replace, "매출: 15000000000000")
        assert "조" in result

    def test_billion_conversion(self):
        result = self._PATTERN.sub(self._replace, "이익: 500000000000")
        assert "억" in result

    def test_small_number_unchanged(self):
        result = self._PATTERN.sub(self._replace, "가격: 12345678")
        assert result == "가격: 12345678"

    def test_nine_digit_becomes_eok(self):
        result = self._PATTERN.sub(self._replace, "금액: 123456789")
        assert "억" in result

    def test_negative_number(self):
        result = self._PATTERN.sub(self._replace, "손실: -5000000000000")
        assert "-" in result
        assert "조" in result

    def test_float_ending_dot_zero(self):
        result = self._PATTERN.sub(self._replace, "값: 1500000000000.0")
        assert "조" in result

    def test_decimal_not_dot_zero_unchanged(self):
        # Numbers with meaningful decimal parts should be left alone
        # This pattern only matches 9+ digits, so 12345.678 won't match
        text = "비율: 12345.678"
        result = self._PATTERN.sub(self._replace, text)
        assert result == text


# ══════════════════════════════════════
# 9. _classify_error
# ══════════════════════════════════════


class TestClassifyError:
    def test_file_not_found(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(FileNotFoundError("missing file"))
        assert result["action"] == "install"

    def test_permission_error(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(PermissionError("denied"))
        assert result["action"] == "login"

    def test_connection_error(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(ConnectionError("refused"))
        assert result["action"] == "retry"

    def test_timeout_error(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(TimeoutError("timed out"))
        assert result["action"] == "retry"

    def test_generic_error(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(RuntimeError("unknown"))
        assert result["action"] == ""
        assert "unknown" in result["error"]

    def test_ollama_connection_refused(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(RuntimeError("connection refused 11434"))
        assert result["action"] == "config"
        assert "Ollama" in result["error"]

    def test_openai_api_key_error(self):
        from dartlab.ai.runtime.core import _classify_error

        result = _classify_error(RuntimeError("invalid api_key"))
        assert result["action"] == "config"

    def test_gemini_503_error(self):
        from dartlab.ai.runtime.core import _classify_error

        # Simulate a Google ServerError
        class ServerError(Exception):
            pass

        err = ServerError("503 Service Unavailable")
        err.__class__.__name__ = "ServerError"
        result = _classify_error(err)
        assert result["action"] == "retry"

    def test_gemini_429_rate_limit(self):
        from dartlab.ai.runtime.core import _classify_error

        class ClientError(Exception):
            pass

        err = ClientError("429 resource_exhausted")
        err.__class__.__name__ = "ClientError"
        result = _classify_error(err)
        assert result["action"] == "rate_limit"


# ══════════════════════════════════════
# 10. _extract_data_date
# ══════════════════════════════════════


class TestExtractDataDate:
    def test_with_filings(self):
        from dartlab.ai.runtime.core import _extract_data_date

        company = MagicMock()
        mock_df = MagicMock()
        mock_df.columns = ["date"]
        mock_dates = MagicMock()
        mock_dates.__len__ = MagicMock(return_value=1)
        mock_dates.max.return_value = "2024-12-31"
        mock_df.__getitem__ = MagicMock(return_value=MagicMock(drop_nulls=MagicMock(return_value=mock_dates)))
        company.filings.return_value = mock_df

        result = _extract_data_date(company)
        assert result == "2024-12-31"

    def test_with_no_filings(self):
        from dartlab.ai.runtime.core import _extract_data_date

        company = MagicMock()
        company.filings.return_value = None

        result = _extract_data_date(company)
        assert result is None

    def test_with_no_filings_method(self):
        from dartlab.ai.runtime.core import _extract_data_date

        company = MagicMock(spec=[])
        result = _extract_data_date(company)
        assert result is None
