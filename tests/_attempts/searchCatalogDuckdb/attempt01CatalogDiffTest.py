"""Attempt 01 — DuckDB catalog diff and CSR export parity.

Run:
    uv run python -X utf8 tests/_attempts/searchCatalogDuckdb/attempt01CatalogDiffTest.py
"""

from __future__ import annotations

import numpy as np
from catalogDuckdb import (
    buildChangedSegment,
    commitStagedDocuments,
    connectCatalog,
    diffStagedDocuments,
    exportChangedForCsr,
    stageDocuments,
)

from dartlab.providers.dart.search.fieldIndex import buildContentSegment


def seedDocs() -> list[dict]:
    """Initial synthetic filings."""
    return [
        {
            "source": "allFilings",
            "rcept_no": "20250101000001",
            "stock_code": "005930",
            "corp_name": "삼성전자",
            "rcept_dt": "20250101",
            "report_nm": "현금ㆍ현물배당결정",
            "section_content": "보통주 배당금 지급을 결정했다.",
        },
        {
            "source": "allFilings",
            "rcept_no": "20250102000002",
            "stock_code": "000660",
            "corp_name": "SK하이닉스",
            "rcept_dt": "20250102",
            "report_nm": "신규시설투자등",
            "section_content": "HBM 생산능력 확대를 위한 신규시설투자를 진행한다.",
        },
        {
            "source": "panel",
            "rcept_no": "20250331000003",
            "stock_code": "005930",
            "corp_name": "삼성전자",
            "rcept_dt": "20250331",
            "report_nm": "사업보고서",
            "section_title": "위험관리",
            "section_content": "환율 변동은 매출과 원가에 영향을 줄 수 있다.",
        },
    ]


def nextDocs() -> list[dict]:
    """Second collection batch: two unchanged, one changed, one new."""
    docs = seedDocs()
    docs[1] = {
        **docs[1],
        "section_content": "HBM 생산능력 확대와 패키징 라인 증설을 위한 신규시설투자를 진행한다.",
    }
    docs.append(
        {
            "source": "allFilings",
            "rcept_no": "20250103000004",
            "stock_code": "035420",
            "corp_name": "NAVER",
            "rcept_dt": "20250103",
            "report_nm": "자기주식취득결정",
            "section_content": "주주가치 제고를 위해 자기주식 취득을 결정했다.",
        }
    )
    return docs


def main() -> None:
    """Run attempt assertions without pytest collection."""
    con = connectCatalog()

    stageDocuments(con, seedDocs())
    firstDiff = diffStagedDocuments(con, includeUnchanged=True)
    firstCounts = firstDiff.get_column("change_type").value_counts()
    assert firstCounts.filter(firstCounts["change_type"] == "new")["count"].item() == 3
    assert commitStagedDocuments(con) == 3

    stageDocuments(con, nextDocs())
    secondDiff = diffStagedDocuments(con, includeUnchanged=True)
    counts = {
        row["change_type"]: row["count"] for row in secondDiff.get_column("change_type").value_counts().to_dicts()
    }
    assert counts == {"unchanged": 2, "changed": 1, "new": 1}, counts

    export = exportChangedForCsr(con)
    assert export.height == 2
    assert export.get_column("rcept_no").to_list() == ["20250103000004", "20250102000002"]

    idxDuck, metaDuck, docsDuck = buildChangedSegment(con)
    idxDirect, metaDirect = buildContentSegment(docsDuck.to_dicts(), showProgress=False)
    assert idxDuck["nDocs"] == idxDirect["nDocs"] == 2
    assert idxDuck["stemDict"] == idxDirect["stemDict"]
    np.testing.assert_array_equal(idxDuck["docLengths"], idxDirect["docLengths"])
    assert metaDuck.to_dicts() == metaDirect.to_dicts()

    assert commitStagedDocuments(con) == 4
    con.close()
    print("PASS searchCatalogDuckdb attempt01: diff=new/changed/unchanged, CSR export parity")


if __name__ == "__main__":
    main()
