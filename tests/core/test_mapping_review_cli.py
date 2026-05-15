"""mappingReview CLI — confirm/reject/alias/defer/export-pr 단위 테스트."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "dev" / "mappingReview.py"


@pytest.fixture
def reviewMod():
    spec = importlib.util.spec_from_file_location("mappingReview", _SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mappingReview"] = mod
    spec.loader.exec_module(mod)
    return mod


def _seedStaging(path: Path) -> None:
    schema = {
        "firstSeenAt": pl.String,
        "lastSeenAt": pl.String,
        "accountId": pl.String,
        "accountNm": pl.String,
        "occurrenceCount": pl.Int64,
        "stockCodes": pl.List(pl.String),
        "sjDivs": pl.List(pl.String),
        "corporateDispersion": pl.Int64,
        "suggestedSnakeId": pl.String,
        "confidence": pl.Float64,
        "signalBreakdown": pl.String,
        "autoEligible": pl.Boolean,
        "status": pl.String,
        "operatorNote": pl.String,
        "decidedAt": pl.String,
    }
    rows = [
        {
            "firstSeenAt": "2026-05-15T00:00:00+00:00",
            "lastSeenAt": "2026-05-15T00:00:00+00:00",
            "accountId": "-표준계정코드 미사용-",
            "accountNm": "기타의금융자산",
            "occurrenceCount": 14,
            "stockCodes": ["005930", "000660", "035720"],
            "sjDivs": ["BS"],
            "corporateDispersion": 3,
            "suggestedSnakeId": "other_financial_assets",
            "confidence": 0.86,
            "signalBreakdown": json.dumps({"s1": True}, ensure_ascii=False),
            "autoEligible": True,
            "status": "auto_proposed",
            "operatorNote": None,
            "decidedAt": None,
        },
        {
            "firstSeenAt": "2026-05-15T00:00:00+00:00",
            "lastSeenAt": "2026-05-15T00:00:00+00:00",
            "accountId": "-표준계정코드 미사용-",
            "accountNm": "지배지업소유주지분",
            "occurrenceCount": 6,
            "stockCodes": ["005930", "000660", "035720"],
            "sjDivs": ["BS"],
            "corporateDispersion": 3,
            "suggestedSnakeId": None,
            "confidence": 0.0,
            "signalBreakdown": json.dumps({"s5Typo": True, "s5Fix": "지배기업소유주지분"}, ensure_ascii=False),
            "autoEligible": False,
            "status": "human_review",
            "operatorNote": None,
            "decidedAt": None,
        },
    ]
    pl.DataFrame(rows, schema=schema).write_parquet(path)


def test_confirm_sets_status_and_decided_at(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)

    rc = reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "confirm",
            "기타의금융자산",
            "--to",
            "other_financial_assets",
        ]
    )
    assert rc == 0

    df = pl.read_parquet(parquet)
    row = df.filter(pl.col("accountNm") == "기타의금융자산").row(0, named=True)
    assert row["status"] == "confirmed"
    assert row["suggestedSnakeId"] == "other_financial_assets"
    assert row["decidedAt"] is not None


def test_reject_sets_status_and_note(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)

    rc = reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "reject",
            "지배지업소유주지분",
            "--reason",
            "typo_suspect",
        ]
    )
    assert rc == 0

    df = pl.read_parquet(parquet)
    row = df.filter(pl.col("accountNm") == "지배지업소유주지분").row(0, named=True)
    assert row["status"] == "rejected"
    assert row["operatorNote"] == "typo_suspect"
    assert row["decidedAt"] is not None


def test_defer_keeps_in_staging(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)

    reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "defer",
            "기타의금융자산",
            "--reason",
            "more_data_needed",
        ]
    )
    df = pl.read_parquet(parquet)
    row = df.filter(pl.col("accountNm") == "기타의금융자산").row(0, named=True)
    assert row["status"] == "deferred"
    assert row["operatorNote"] == "more_data_needed"


def test_alias_writes_to_csv_and_status(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    aliasCsv = tmp_path / "aliases.csv"
    _seedStaging(parquet)

    reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "alias",
            "지배지업소유주지분",
            "--to",
            "controlling_equity",
            "--alias-csv",
            str(aliasCsv),
        ]
    )

    df = pl.read_parquet(parquet)
    row = df.filter(pl.col("accountNm") == "지배지업소유주지분").row(0, named=True)
    assert row["status"] == "alias_only"
    assert row["suggestedSnakeId"] == "controlling_equity"

    assert aliasCsv.exists()
    lines = aliasCsv.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("accountNm")
    assert "지배지업소유주지분" in lines[1]
    assert "controlling_equity" in lines[1]


def test_export_pr_includes_only_status_match(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)
    # 우선 confirm
    reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "confirm",
            "기타의금융자산",
            "--to",
            "other_financial_assets",
        ]
    )

    out = tmp_path / "patch.json"
    rc = reviewMod.main(
        [
            "--parquet",
            str(parquet),
            "export-pr",
            "--status",
            "confirmed",
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    patch = json.loads(out.read_text(encoding="utf-8"))
    assert patch == {"기타의금융자산": "other_financial_assets"}


def test_confirm_unknown_row_raises(reviewMod, tmp_path: Path) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)
    with pytest.raises(ValueError, match="staging 부재"):
        reviewMod.main(
            [
                "--parquet",
                str(parquet),
                "confirm",
                "없는계정",
                "--to",
                "x",
            ]
        )


def test_list_filter_status_auto_eligible(reviewMod, tmp_path: Path, capsys) -> None:
    parquet = tmp_path / "staging.parquet"
    _seedStaging(parquet)

    rc = reviewMod.main(["--parquet", str(parquet), "list", "--auto-eligible-only"])
    assert rc == 0
    captured = capsys.readouterr()
    # autoEligible True 만 — 1 행
    assert "1 행" in captured.out
    assert "기타의금융자산" in captured.out
    assert "지배지업소유주지분" not in captured.out
