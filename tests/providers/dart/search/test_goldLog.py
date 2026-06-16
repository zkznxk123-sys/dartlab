"""providers/dart/search/goldLog.py mirror tests."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def test_merge_gold_log_rows_applies_reviewer_labels() -> None:
    from dartlab.providers.dart.search.goldLog import mergeGoldLogRows

    rows = mergeGoldLogRows(
        [{"queryId": "q1", "q": "삼성전자 유상증자 공시"}],
        [
            {
                "queryId": "q1",
                "target": "filing",
                "expectedSourceRef": "dart:allFilings:20260615000001#section=0",
                "goldOrigin": "real",
                "reviewStatus": "reviewed",
            }
        ],
    )

    assert rows == [
        {
            "query": "삼성전자 유상증자 공시",
            "queryId": "q1",
            "targetKind": "filing",
            "expectedAnswerable": True,
            "expectedSourceRefs": ["dart:allFilings:20260615000001#section=0"],
            "expectedSourceRef": "dart:allFilings:20260615000001#section=0",
            "goldOrigin": "real",
            "reviewStatus": "reviewed",
        }
    ]


def test_summarize_gold_log_rows_requires_release_coverage() -> None:
    from dartlab.providers.dart.search.goldLog import mergeGoldLogRows, summarizeGoldLogRows

    rows = mergeGoldLogRows(
        [
            {
                "query": "뉴스 원문",
                "target": "news",
                "expectedSourceRef": "news:a",
                "goldOrigin": "real",
                "reviewStatus": "reviewed",
            },
            {
                "query": "없는 공시",
                "target": "noAnswer",
                "goldOrigin": "real",
                "reviewStatus": "reviewed",
            },
        ]
    )

    summary = summarizeGoldLogRows(rows, minRows=2, requiredTargets=("news", "noAnswer"))

    assert summary["releaseEligible"] is True
    assert summary["coverageByKind"] == {"news": 1, "noAnswer": 1}
    assert summary["invalidRows"] == []


def test_summarize_gold_log_rows_blocks_proxy_and_missing_source_ref() -> None:
    from dartlab.providers.dart.search.goldLog import mergeGoldLogRows, summarizeGoldLogRows

    rows = mergeGoldLogRows(
        [
            {
                "query": "뉴스 원문",
                "target": "news",
                "goldOrigin": "runtimeGenerated",
                "reviewStatus": "draft",
            }
        ]
    )

    summary = summarizeGoldLogRows(rows, minRows=1, requiredTargets=("news",))

    assert summary["releaseEligible"] is False
    assert "invalidRows:1" in summary["blockers"]
    assert set(summary["invalidRows"][0]["reasons"]) == {
        "missingExpectedSourceRef",
        "proxyGoldOrigin",
        "unreviewedGold",
    }


def test_write_and_load_gold_log_rows(tmp_path) -> None:
    from dartlab.providers.dart.search.goldLog import loadGoldLogRows, writeGoldLogRows

    out = tmp_path / "gold.jsonl"
    writeGoldLogRows(out, [{"query": "q", "targetKind": "noAnswer"}])

    assert loadGoldLogRows([out]) == [{"query": "q", "targetKind": "noAnswer"}]

    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"labels": [{"query": "q2"}]}), encoding="utf-8")
    assert loadGoldLogRows([wrapped]) == [{"query": "q2"}]


def test_record_raw_query_log_event_writes_review_candidate(tmp_path) -> None:
    from dartlab.providers.dart.search.goldLog import loadGoldLogRows, recordRawQueryLogEvent

    out = tmp_path / "queryLogRaw.jsonl"
    event = recordRawQueryLogEvent(
        query="삼성전자 대표이사 변경",
        params={"scope": "auto", "limit": 3},
        results=[
            {
                "source": "allFilings",
                "sourceRef": "dart:allFilings:20260615000001#section=0",
                "rcept_no": "20260615000001",
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "dataAsOf": "20260615",
                "answerable": True,
                "score": 12.5,
            }
        ],
        path=out,
    )

    rows = loadGoldLogRows([out])

    assert event is not None
    assert rows[0]["query"] == "삼성전자 대표이사 변경"
    assert rows[0]["goldOrigin"] == "userLog"
    assert rows[0]["reviewStatus"] == "candidate"
    assert rows[0]["topSourceRefs"] == ["dart:allFilings:20260615000001#section=0"]
    assert rows[0]["topResults"][0]["stockCode"] == "005930"


def test_build_reviewer_label_template_keeps_candidate_refs_unconfirmed() -> None:
    from dartlab.providers.dart.search.goldLog import buildReviewerLabelTemplateRows

    labels = buildReviewerLabelTemplateRows(
        [
            {
                "queryId": "q1",
                "query": "뉴스 원문",
                "topSourceRefs": ["news:a"],
                "topResults": [{"sourceRef": "news:a", "source": "news"}],
            }
        ]
    )

    assert labels[0]["queryId"] == "q1"
    assert labels[0]["candidateSourceRefs"] == ["news:a"]
    assert labels[0]["expectedSourceRef"] == ""
    assert labels[0]["reviewStatus"] == "draft"
