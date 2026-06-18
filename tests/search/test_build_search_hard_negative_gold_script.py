"""Tests for current-data hard-negative search gold builder."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import polars as pl

SCRIPT = Path(".github/scripts/search/buildSearchHardNegativeGold.py")


def test_build_search_hard_negative_gold_from_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.parquet"
    pl.DataFrame(_catalogRows()).write_parquet(catalog)
    out = tmp_path / "hardNegative.jsonl"
    summaryOut = tmp_path / "summary.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog),
            "--out",
            str(out),
            "--summary-out",
            str(summaryOut),
            "--limit",
            "8",
            "--per-type",
            "4",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summaryOut.read_text(encoding="utf-8"))
    hardNegativeTypes = {row["hardNegativeType"] for row in rows}

    assert len(rows) == 8
    assert summary["totalRows"] == 8
    assert summary["reviewState"] == "candidate"
    assert summary["releaseEvidence"] is False
    assert "same-company-different-year" in hardNegativeTypes
    assert "news-filing-confusion" in hardNegativeTypes
    assert "filing-news-confusion" in hardNegativeTypes
    assert "edgar-dart-confusion" in hardNegativeTypes
    assert "panel-filing-confusion" in hardNegativeTypes
    assert all(row["expectedSourceRef"] for row in rows)
    assert all(row["expectedSourceRefs"] == [row["expectedSourceRef"]] for row in rows)
    assert all(row["goldOrigin"] == "currentDataHardNegative" for row in rows)
    assert all(row["reviewStatus"] == "candidate" for row in rows)
    assert any(row["forbiddenSourceFamilies"] == ["filing"] for row in rows)
    assert any(row["forbiddenSourceFamilies"] == ["news"] for row in rows)
    assert all(row["forbiddenSourceRefs"] or row["forbiddenSourceFamilies"] for row in rows)


def test_build_search_hard_negative_gold_mark_reviewed(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.parquet"
    pl.DataFrame(_catalogRows()).write_parquet(catalog)
    out = tmp_path / "reviewed.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog),
            "--out",
            str(out),
            "--limit",
            "2",
            "--mark-reviewed",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert {row["goldOrigin"] for row in rows} == {"operator"}
    assert {row["reviewStatus"] for row in rows} == {"reviewed"}


def test_build_search_hard_negative_gold_can_append_no_answer_rows(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog.parquet"
    pl.DataFrame(_catalogRows()).write_parquet(catalog)
    out = tmp_path / "hardNegativeWithNoAnswer.jsonl"
    summaryOut = tmp_path / "summary.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--catalog",
            str(catalog),
            "--out",
            str(out),
            "--summary-out",
            str(summaryOut),
            "--limit",
            "10",
            "--per-type",
            "4",
            "--no-answer-rows",
            "2",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    summary = json.loads(summaryOut.read_text(encoding="utf-8"))
    noAnswerRows = [row for row in rows if row["targetKind"] == "noAnswer"]

    assert len(rows) == 10
    assert len(noAnswerRows) == 2
    assert summary["byTargetKind"]["noAnswer"] == 2
    assert {row["expectedAnswerable"] for row in noAnswerRows} == {False}
    assert {row["expectedSourceRef"] for row in noAnswerRows} == {""}
    assert all(row["expectedSourceRefs"] == [] for row in noAnswerRows)
    assert all(row["forbiddenSourceRefs"] or row["forbiddenSourceFamilies"] for row in noAnswerRows)
    assert any(row["hardNegativeType"] == "no-answer-missing-company-year-event" for row in noAnswerRows)


def _catalogRows() -> list[dict[str, str]]:
    return [
        _row(
            "allFilings",
            "dart:allFilings:samsung-2025-rights",
            "삼성전자",
            "005930",
            "",
            "20250301",
            "유상증자 결정",
            "유상증자 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:samsung-2024-rights",
            "삼성전자",
            "005930",
            "",
            "20240301",
            "유상증자 결정",
            "유상증자 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:samsung-2024-dividend",
            "삼성전자",
            "005930",
            "",
            "20240310",
            "배당 결정",
            "배당 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:samsung-2025-rights-correction",
            "삼성전자",
            "005930",
            "",
            "20250302",
            "[정정] 유상증자 결정",
            "[정정] 유상증자 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:lg-2025-rights",
            "LG전자",
            "066570",
            "",
            "20250302",
            "유상증자 결정",
            "유상증자 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:lg-2025-dividend",
            "LG전자",
            "066570",
            "",
            "20250310",
            "배당 결정",
            "배당 결정",
        ),
        _row(
            "allFilings",
            "dart:allFilings:samsung-2025-annual",
            "삼성전자",
            "005930",
            "",
            "20250330",
            "사업보고서",
            "사업보고서",
        ),
        _row(
            "allFilings",
            "dart:allFilings:samsung-2025-q",
            "삼성전자",
            "005930",
            "",
            "20250515",
            "분기보고서",
            "분기보고서",
        ),
        _row(
            "dartPanel",
            "dart:panel:samsung-2025-risk#section=0",
            "삼성전자",
            "005930",
            "",
            "20250330",
            "사업보고서",
            "위험요인",
        ),
        _row(
            "edgarPanel", "edgar:panel:aapl-2024-10k#section=0", "AAPL", "", "AAPL", "20241231", "", "10-K risk factors"
        ),
        _row("edgarPanel", "edgar:panel:aapl-2024-10q#section=0", "AAPL", "", "AAPL", "20240331", "", "10-Q liquidity"),
        _row(
            "allFilings",
            "dart:allFilings:aapl-like-2024-annual",
            "애플코리아",
            "123456",
            "",
            "20241231",
            "사업보고서",
            "사업보고서",
        ),
        _row("newsPublic", "news:samsung-rights-2025", "", "", "", "20250301", "", "삼성전자 유상증자 결정 뉴스"),
        _row("newsPublic", "news:aapl-risk-2024", "", "", "", "20241231", "", "Apple 10-K risk factors news"),
    ]


def _row(
    source: str,
    sourceRef: str,
    companyName: str,
    stockCode: str,
    ticker: str,
    date: str,
    reportName: str,
    title: str,
) -> dict[str, str]:
    return {
        "source": source,
        "sourceRef": sourceRef,
        "companyName": companyName,
        "stockCode": stockCode,
        "ticker": ticker,
        "date": date,
        "reportName": reportName,
        "title": title,
        "sourceDataAsOf": "20260618",
    }
