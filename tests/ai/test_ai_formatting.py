"""dict / list[dict] / DataFrame → 사람-읽는 마크다운 변환 dispatch."""

from __future__ import annotations

import pytest

from dartlab.ai.tools.formatting import (
    formatDictAsMarkdown,
    formatEngineResult,
    formatRecordsAsMarkdown,
    formatTableAsMarkdown,
)


class TestFormatDictAsMarkdown:
    def test_flat_dict_to_bullets(self) -> None:
        result = formatDictAsMarkdown({"name": "삼성전자", "code": "005930"})
        assert "- **name**: 삼성전자" in result
        assert "- **code**: 005930" in result

    def test_nested_dict_indents(self) -> None:
        result = formatDictAsMarkdown({"company": {"name": "삼성", "code": "005930"}})
        assert "- **company**" in result
        assert "  - **name**: 삼성" in result

    def test_list_value_summarizes_with_count(self) -> None:
        result = formatDictAsMarkdown({"axes": ["수익성", "안정성", "성장성", "효율성"]})
        assert "4개 항목" in result
        assert "수익성" in result

    def test_long_string_truncated(self) -> None:
        long_value = "가" * 500
        result = formatDictAsMarkdown({"text": long_value}, maxValue=50)
        assert "..." in result

    def test_empty_dict(self) -> None:
        assert "빈 dict" in formatDictAsMarkdown({})

    def test_none_returns_empty(self) -> None:
        assert formatDictAsMarkdown(None) == ""

    def test_max_keys_truncates_with_summary(self) -> None:
        payload = {f"k{i}": i for i in range(20)}
        result = formatDictAsMarkdown(payload, maxKeys=5)
        assert "+15 키 생략" in result


class TestFormatRecordsAsMarkdown:
    def test_records_to_table(self) -> None:
        records = [
            {"종목코드": "005930", "종목명": "삼성전자", "매출": 280_000_000_000_000},
            {"종목코드": "000660", "종목명": "SK하이닉스", "매출": 50_000_000_000_000},
        ]
        result = formatRecordsAsMarkdown(records)
        assert "| 종목코드 | 종목명 | 매출 |" in result
        assert "005930" in result
        assert "조원" in result  # format_money 자동 적용

    def test_percent_columns_auto_format(self) -> None:
        records = [{"종목코드": "005930", "ROE": 12.4}, {"종목코드": "000660", "ROE": 8.2}]
        result = formatRecordsAsMarkdown(records)
        # ROE 라는 컬럼명에는 percent hint 미일치 → numeric 그대로. 명시적 비율 컬럼:
        records2 = [{"종목": "삼성", "성장률": 5.4}]
        result2 = formatRecordsAsMarkdown(records2)
        assert "5.4%" in result2

    def test_empty_records(self) -> None:
        assert "빈 결과" in formatRecordsAsMarkdown([])

    def test_truncates_with_footer(self) -> None:
        records = [{"i": i, "v": i * 2} for i in range(30)]
        result = formatRecordsAsMarkdown(records, maxRows=5)
        assert "전체 30행" in result

    def test_max_cols(self) -> None:
        records = [{f"c{i}": i for i in range(20)}]
        result = formatRecordsAsMarkdown(records, maxCols=4)
        assert result.count("c0") >= 1
        assert "c10" not in result


class TestFormatTableAsMarkdown:
    def test_polars_dataframe(self) -> None:
        pl = pytest.importorskip("polars")
        df = pl.DataFrame({"종목코드": ["005930", "000660"], "매출": [280_000_000_000_000, 50_000_000_000_000]})
        result = formatTableAsMarkdown(df)
        assert "_dtype_" in result
        assert "종목코드" in result
        assert "조원" in result

    def test_non_dataframe_returns_empty(self) -> None:
        assert formatTableAsMarkdown({"not": "a df"}) == ""


class TestFormatEngineResult:
    def test_dict_with_markdown_key_passthrough(self) -> None:
        result = {"markdown": "# 이미 변환됨"}
        assert formatEngineResult(result) == "# 이미 변환됨"

    def test_records_list_dispatches_to_records(self) -> None:
        records = [{"종목": "삼성", "value": 1}, {"종목": "SK", "value": 2}]
        result = formatEngineResult(records)
        assert result is not None
        assert "| 종목 | value |" in result

    def test_dict_with_rows_key_dispatches_to_records(self) -> None:
        payload = {"rows": [{"a": 1}, {"a": 2}]}
        result = formatEngineResult(payload)
        assert result is not None
        assert "| a |" in result

    def test_plain_dict_dispatches_to_dict(self) -> None:
        payload = {"name": "삼성", "code": "005930"}
        result = formatEngineResult(payload)
        assert result is not None
        assert "- **name**: 삼성" in result

    def test_none_returns_none(self) -> None:
        assert formatEngineResult(None) is None

    def test_hint_records_overrides_shape_inference(self) -> None:
        result = formatEngineResult([{"x": 1}], hint="records")
        assert "| x |" in result

    def test_hint_dict_forces_dict_format(self) -> None:
        result = formatEngineResult({"a": 1, "b": 2}, hint="dict")
        assert "- **a**: 1" in result

    def test_polars_dataframe_dispatches_to_table(self) -> None:
        pl = pytest.importorskip("polars")
        df = pl.DataFrame({"a": [1, 2]})
        result = formatEngineResult(df)
        assert result is not None
        assert "_dtype_" in result
