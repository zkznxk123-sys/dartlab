"""증분 scan prebuild 핵심 로직 단위 테스트 — P1.

prebuild OOM/디스크 고갈 근본원인(전 92K panel seed)을 제거한 증분 경로의 정합성 가드.
``mergeIncremental``(종목 단위 교체)·``pruneScanCodes``(삭제 종목 제거)·buildState ledger
roundtrip + ``buildChanges(incremental=True)`` 가 변경 종목만 재계산해 기존 parquet 에
머지하는지 검증한다. panel I/O 는 ``panelTextRows`` monkeypatch 로 합성(메모리 안전).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit


# ─── buildState ledger roundtrip ──────────────────────────────────────


def test_buildState_roundtrip(tmp_path: Path, monkeypatch) -> None:
    """saveScanBuildState → loadScanBuildState 동형 복원. 부재 시 빈 dict."""
    from dartlab.scan.builders.kr.common import loadScanBuildState, saveScanBuildState

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    assert loadScanBuildState() == {}  # 부재

    state = {"dart/panel/005930.parquet": 123, "dart/panel/000660.parquet": 456}
    saveScanBuildState(state)
    assert loadScanBuildState() == state


def test_buildState_corrupt_returns_empty(tmp_path: Path, monkeypatch) -> None:
    """파손 JSON 은 빈 dict 로 흡수(증분 대신 부트스트랩 안전 폴백)."""
    from dartlab.scan.builders.kr.common import SCAN_BUILD_STATE_FILE, loadScanBuildState

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))
    scanDir = tmp_path / "scan"
    scanDir.mkdir(parents=True)
    (scanDir / SCAN_BUILD_STATE_FILE).write_text("{not valid json", encoding="utf-8")
    assert loadScanBuildState() == {}


# ─── mergeIncremental ─────────────────────────────────────────────────


def _prior(codes_periods: list[tuple[str, str]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "stockCode": [c for c, _ in codes_periods],
            "toPeriod": [p for _, p in codes_periods],
            "val": list(range(len(codes_periods))),
        }
    )


def test_mergeIncremental_drops_and_appends(tmp_path: Path) -> None:
    """변경 종목 행을 드롭하고 재계산 행을 append. 미변경 종목은 보존."""
    from dartlab.scan.builders.kr.common import mergeIncremental

    out = tmp_path / "changes.parquet"
    _prior([("A", "2022Q4"), ("B", "2022Q4")]).write_parquet(str(out))

    rebuilt = pl.DataFrame({"stockCode": ["A", "A"], "toPeriod": ["2023Q4", "2023Q2"], "val": [99, 98]})
    n = mergeIncremental(out, rebuilt, key="stockCode")

    df = pl.read_parquet(str(out))
    assert n == df.height == 3  # B(1) + A 재계산(2)
    assert set(df.filter(pl.col("stockCode") == "A")["toPeriod"].to_list()) == {"2023Q4", "2023Q2"}
    assert df.filter(pl.col("stockCode") == "B").height == 1  # 보존


def test_mergeIncremental_no_existing_writes_rebuilt(tmp_path: Path) -> None:
    """기존 산출 부재 시 rebuilt 그대로 기록(full write)."""
    from dartlab.scan.builders.kr.common import mergeIncremental

    out = tmp_path / "changes.parquet"
    rebuilt = pl.DataFrame({"stockCode": ["A"], "toPeriod": ["2023Q4"], "val": [1]})
    n = mergeIncremental(out, rebuilt, key="stockCode")
    assert n == 1 and out.exists()


def test_mergeIncremental_empty_rebuilt_preserves(tmp_path: Path) -> None:
    """rebuilt 빈 DataFrame + 기존 존재 → 기존 보존(no-op), 기존 행수 반환."""
    from dartlab.scan.builders.kr.common import mergeIncremental

    out = tmp_path / "changes.parquet"
    _prior([("A", "2022Q4"), ("B", "2022Q4")]).write_parquet(str(out))
    n = mergeIncremental(out, pl.DataFrame(schema={"stockCode": pl.Utf8}), key="stockCode")
    assert n == 2
    assert pl.read_parquet(str(out)).height == 2


def test_mergeIncremental_categorical_safe(tmp_path: Path) -> None:
    """Categorical 컬럼(서로 다른 parquet 소스)도 string-cache 충돌 없이 머지."""
    from dartlab.scan.builders.kr.common import mergeIncremental

    out = tmp_path / "docsIndex.parquet"
    prior = pl.DataFrame({"stockCode": ["A", "B"], "reportType": ["annual", "Q1"]}).with_columns(
        pl.col("reportType").cast(pl.Categorical)
    )
    prior.write_parquet(str(out))
    rebuilt = pl.DataFrame({"stockCode": ["A"], "reportType": ["Q3"]}).with_columns(
        pl.col("reportType").cast(pl.Categorical)
    )
    n = mergeIncremental(out, rebuilt, key="stockCode")
    df = pl.read_parquet(str(out))
    assert n == 2
    assert df.filter(pl.col("stockCode") == "A")["reportType"].to_list() == ["Q3"]


# ─── pruneScanCodes ───────────────────────────────────────────────────


def test_pruneScanCodes_removes(tmp_path: Path) -> None:
    """삭제 종목 행 제거(다운로드 불요). 미존재 코드는 no-op."""
    from dartlab.scan.builders.kr.common import pruneScanCodes

    out = tmp_path / "changes.parquet"
    _prior([("A", "x"), ("B", "x"), ("C", "x")]).write_parquet(str(out))

    removed = pruneScanCodes(out, ["B"], key="stockCode")
    assert removed == 1
    assert set(pl.read_parquet(str(out))["stockCode"].to_list()) == {"A", "C"}

    assert pruneScanCodes(out, ["ZZZ"], key="stockCode") == 0  # 미존재
    assert pruneScanCodes(tmp_path / "none.parquet", ["A"], key="stockCode") == 0  # 파일 부재


# ─── buildChanges(incremental=True) 통합 ──────────────────────────────


def test_buildChanges_incremental_merges_only_changed(tmp_path: Path, monkeypatch) -> None:
    """변경 종목(A)만 재계산해 기존 changes.parquet 에 머지 — 미변경(B) 보존."""
    from dartlab.scan.builders.kr.docs.changes import buildChanges

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    panelDir = tmp_path / "panel"
    panelDir.mkdir(parents=True)
    scanDir = tmp_path / "scan"
    scanDir.mkdir(parents=True)

    # 기존 changes.parquet (seed 된 직전 산출): A 옛 행 + B 보존 대상.
    prior = pl.DataFrame(
        {
            "fromPeriod": ["2021Q4", "2021Q4"],
            "toPeriod": ["2022Q4", "2022Q4"],
            "sectionTitle": ["옛섹션", "B섹션"],
            "changeType": ["wording", "wording"],
            "sizeA": [10, 10],
            "sizeB": [12, 12],
            "sizeDelta": [2, 2],
            "preview": ["x", "y"],
            "stockCode": ["A", "B"],
        }
    )
    prior.write_parquet(str(scanDir / "changes.parquet"))

    # 증분: 변경 종목 A 만 panel dir 에 seed (B 는 다운로드 안 됨 → 미변경).
    pl.DataFrame({"_": [1]}).write_parquet(str(panelDir / "A.parquet"))

    def _fakePanelTextRows(code: str, *args, **kwargs):
        if code != "A":
            return None
        return pl.DataFrame(
            [
                {
                    "period": "2022Q4",
                    "sectionLeaf": "사업의 개요",
                    "contentRaw": "옛 내용 가가가 " * 5,
                    "blockOrder": 0,
                    "rceptNo": "r1",
                },
                {
                    "period": "2023Q4",
                    "sectionLeaf": "사업의 개요",
                    "contentRaw": "새 내용 나나나 완전 다름 " * 5,
                    "blockOrder": 0,
                    "rceptNo": "r2",
                },
            ]
        )

    monkeypatch.setattr("dartlab.providers.dart.panel.text.panelTextRows", _fakePanelTextRows)

    result = buildChanges(sinceYear=2021, verbose=False, incremental=True)
    assert result is not None

    df = pl.read_parquet(str(result))
    # B 보존
    assert df.filter(pl.col("stockCode") == "B").height == 1
    # A 는 재계산(옛 2022Q4 행 드롭, 새 2023Q4 변화행)
    aRows = df.filter(pl.col("stockCode") == "A")
    assert aRows.height >= 1
    assert "2023Q4" in aRows["toPeriod"].to_list()
    assert "옛섹션" not in aRows["sectionTitle"].to_list()  # 옛 A 행 교체됨


def test_buildSharesOutstandingScan_incremental_merges(tmp_path, monkeypatch) -> None:
    """변경 종목(A)만 발행주식수 재계산 후 기존 parquet 에 stock_code 단위 머지 — B 보존."""
    from dartlab.scan.builders.kr import shares

    monkeypatch.setattr("dartlab.core.dataLoader._dataDir", lambda subdir: str(tmp_path / subdir))

    panelDir = tmp_path / "panel"
    panelDir.mkdir(parents=True)
    scanDir = tmp_path / "scan"
    scanDir.mkdir(parents=True)

    # 기존 sharesOutstanding: A 옛값 + B 보존 대상.
    pl.DataFrame({"stock_code": ["A", "B"], "year": [2022, 2022], "outstandingShares": [1, 2]}).write_parquet(
        str(scanDir / "sharesOutstanding.parquet")
    )
    pl.DataFrame({"_": [1]}).write_parquet(str(panelDir / "A.parquet"))  # 변경 종목 A 만 seed

    def fakeTextRows(code, *a, **k):
        if code != "A":
            return None
        return pl.DataFrame({"period": ["2023Q4"], "sectionLeaf": ["주식의 총수 현황"], "rceptNo": ["20230101000001"]})

    def fakeXmlTables(code, *, sectionPattern=None, period=None):
        return [
            [
                ["발행할 주식의 총수", "", "", "1000"],
                ["현재까지 발행한 주식", "", "", "800"],
                ["발행주식의 총수", "", "", "800"],
            ]
        ]

    monkeypatch.setattr("dartlab.providers.dart.panel.text.panelTextRows", fakeTextRows)
    monkeypatch.setattr("dartlab.providers.dart.panel.text.panelXmlTables", fakeXmlTables)
    monkeypatch.setattr("dartlab.core.listingResolver.getListingResolver", lambda: None)

    shares.buildSharesOutstandingScan(incremental=True)

    df = pl.read_parquet(str(scanDir / "sharesOutstanding.parquet"))
    assert "B" in df["stock_code"].to_list()  # 미변경 보존
    aRows = df.filter(pl.col("stock_code") == "A")
    assert aRows.height == 1
    assert aRows["outstandingShares"][0] == 800  # 재계산값으로 교체
