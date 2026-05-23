"""parseDef14aHtml 실 구현 — SEC DEF 14A Summary Compensation Table 파싱."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


_SAMPLE_DEF14A_HTML = """
<html><body>
<h2>Executive Compensation</h2>
<table>
  <tr>
    <th>Name and Principal Position</th>
    <th>Year</th>
    <th>Salary ($)</th>
    <th>Bonus ($)</th>
    <th>Stock Awards ($)</th>
    <th>Total ($)</th>
  </tr>
  <tr>
    <td>Timothy D. Cook</td>
    <td>2024</td>
    <td>3,000,000</td>
    <td>0</td>
    <td>50,000,000</td>
    <td>63,209,845</td>
  </tr>
  <tr>
    <td>Luca Maestri</td>
    <td>2024</td>
    <td>1,000,000</td>
    <td>0</td>
    <td>21,000,000</td>
    <td>27,154,302</td>
  </tr>
</table>
</body></html>
"""


def test_empty_html() -> None:
    """빈 HTML → 빈 DataFrame (schema 보존)."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    df = parseDef14aHtml("")
    assert df.is_empty()
    assert set(df.columns) == {
        "name",
        "position",
        "year",
        "salary",
        "bonus",
        "stockAwards",
        "total",
    }


def test_html_without_table() -> None:
    """table 없는 HTML → 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    df = parseDef14aHtml("<html><body>No table</body></html>")
    assert df.is_empty()


def test_extract_compensation_rows() -> None:
    """Summary Compensation Table → 2 row 추출."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    df = parseDef14aHtml(_SAMPLE_DEF14A_HTML)
    assert df.shape[0] == 2
    names = df["name"].to_list()
    assert "Timothy D. Cook" in names
    assert "Luca Maestri" in names


def test_extract_amounts() -> None:
    """salary / stockAwards / total 정확 파싱."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    df = parseDef14aHtml(_SAMPLE_DEF14A_HTML)
    cookRow = df.filter(df["name"] == "Timothy D. Cook").row(0, named=True)
    assert cookRow["year"] == 2024
    assert cookRow["salary"] == 3_000_000.0
    assert cookRow["stockAwards"] == 50_000_000.0
    assert cookRow["total"] == 63_209_845.0


def test_no_compensation_keyword() -> None:
    """compensation / salary 키워드 없는 table → skip."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    html = """
    <html><body>
    <table>
      <tr><th>Director</th><th>Year</th><th>Fee</th></tr>
      <tr><td>John Doe</td><td>2024</td><td>100,000</td></tr>
    </table>
    </body></html>
    """
    df = parseDef14aHtml(html)
    # compensation keyword 없으면 빈 → header detection 필터 효과.
    assert df.is_empty()
