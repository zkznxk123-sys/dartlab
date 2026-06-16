"""providers/dart/search/resultContract.py mirror tests."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _good_row() -> dict[str, object]:
    return {
        "query": "유상증자",
        "source": "allFilings",
        "sourceRef": "dart:allFilings:1#section=0",
        "dataAsOf": "20260615",
        "snippet": "유상증자 결정",
        "answerable": True,
        "fieldCards": json.dumps(
            [
                {
                    "label": "sourceRef",
                    "value": "dart:allFilings:1#section=0",
                    "sourceRef": "dart:allFilings:1#section=0",
                    "evidence": "유상증자 결정",
                }
            ],
            ensure_ascii=False,
        ),
    }


def test_audit_search_result_rows_accepts_product_contract() -> None:
    from dartlab.providers.dart.search.resultContract import auditSearchResultRows

    report = auditSearchResultRows([_good_row()])

    assert report["valid"] is True
    assert report["metrics"]["validRate"] == 1.0


def test_audit_search_result_rows_reports_missing_contract_fields() -> None:
    from dartlab.providers.dart.search.resultContract import auditSearchResultRows

    row = _good_row()
    row["sourceRef"] = ""
    row["dataAsOf"] = ""
    row["fieldCards"] = "[]"

    report = auditSearchResultRows([row])

    assert report["valid"] is False
    assert report["blockers"] == ["invalidRows:1"]
    assert set(report["invalidRows"][0]["reasons"]) == {
        "missingSourceRef",
        "missingDataAsOf",
        "emptyFieldCards",
    }


def test_load_result_rows_flattens_query_mapping(tmp_path) -> None:
    from dartlab.providers.dart.search.resultContract import loadResultRows

    path = tmp_path / "results.json"
    path.write_text(json.dumps({"q": [_good_row()]}, ensure_ascii=False), encoding="utf-8")

    rows = loadResultRows(path)

    assert len(rows) == 1
    assert rows[0]["query"] == "유상증자"


def test_load_result_rows_flattens_jsonl_query_results(tmp_path) -> None:
    from dartlab.providers.dart.search.resultContract import loadResultRows

    path = tmp_path / "results.jsonl"
    row = _good_row()
    row.pop("query")
    path.write_text(
        json.dumps({"query": "뉴스", "results": [row]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rows = loadResultRows(path)

    assert len(rows) == 1
    assert rows[0]["query"] == "뉴스"
