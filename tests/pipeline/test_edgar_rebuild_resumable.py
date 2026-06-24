"""EDGAR full-rebuild resumable 로직 회귀 — ledger skip · 배치 경계 · processed vs uploaded · 시간가드.

옛 ``_runFullRebuild`` 는 전 ticker 빌드 후 마지막 1회 upload(all-at-end) → 180분 timeout 시 3시간
전부 손실(실측 run 27240725637). 재개 가능 버전은 배치마다 upload+ledger push 라 timeout 손실이
'진행 중 1배치'로 bounded + 다음 run 이 ledger 로 이어간다. SEC/HF 미접촉(monkeypatch) — 루프 제어만 검증.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_full_rebuild_resumable_skips_ledger_batches_and_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    """ledger 완료분 skip + 배치 경계 flush + processed(0행 포함) vs uploaded(rows>0) 분리."""
    import dartlab.pipeline.stages.edgarPanel as ep
    from dartlab.pipeline.types import StageResult

    monkeypatch.setattr(ep, "_priorityTickers", lambda: ["AAA", "BBB", "CCC", "DDD", "EEE"])
    monkeypatch.setattr(ep, "_loadRebuildLedger", lambda token: {"AAA"})  # AAA 이미 완료
    monkeypatch.setattr(ep, "_REBUILD_BATCH", 2)
    monkeypatch.setattr(ep, "_publishTickers", lambda token: None)  # hermetic — SEC/HF 미접촉
    monkeypatch.setattr(
        "dartlab.core.dataLoader.loadEdgarListedUniverse", lambda *, forceUpdate=False: pl.DataFrame({"ticker": []})
    )
    monkeypatch.setattr(
        "dartlab.gather.original.edgar.submissions.listAllFilings", lambda t, *, forms, sinceYear: [{"x": 1}]
    )
    monkeypatch.setattr("dartlab.gather.original.edgar.collect.fetchFilingTexts", lambda rows: {"c": [{"text": "t"}]})
    # DDD 는 재무공시 0행(ETF/shell) — 나머지 rows>0
    monkeypatch.setattr(
        "dartlab.providers.edgar.panel.build.buildEdgarPanel",
        lambda t, recs, *, overwrite, verbose: {"rows": 0 if t == "DDD" else 10},
    )

    flushes: list[dict] = []

    def fakeFlush(uploaded, processed, done, *, upload, token):
        flushes.append({"uploaded": list(uploaded), "processed": list(processed)})
        done.update(processed)  # 실제 동작 미러(remaining 계산 정합)

    monkeypatch.setattr(ep, "_flushRebuildBatch", fakeFlush)

    res = ep._runFullRebuild(StageResult(category="edgarPanel"), upload=True, token=None)

    allProcessed = [t for f in flushes for t in f["processed"]]
    assert "AAA" not in allProcessed, "ledger 완료분 skip"
    assert allProcessed == ["BBB", "CCC", "DDD", "EEE"], "잔여만 순서대로 처리"
    # 배치 2: [BBB,CCC] / [DDD,EEE]
    assert flushes[0]["processed"] == ["BBB", "CCC"] and flushes[0]["uploaded"] == ["BBB", "CCC"]
    assert flushes[1]["processed"] == ["DDD", "EEE"] and flushes[1]["uploaded"] == ["EEE"], "0행 DDD 는 upload 제외"
    assert res.report.ok == 1
    assert res.rows == 30  # BBB10 + CCC10 + EEE10 (DDD 0)


def test_full_rebuild_time_guard_breaks_before_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """시간가드 — deadline 경과면 첫 ticker 처리 전 break(취소돼도 진행분 보존 설계의 핵심)."""
    import dartlab.pipeline.stages.edgarPanel as ep
    from dartlab.pipeline.types import StageResult

    monkeypatch.setattr(ep, "_priorityTickers", lambda: ["AAA", "BBB"])
    monkeypatch.setattr(ep, "_loadRebuildLedger", lambda token: set())
    monkeypatch.setattr(ep, "_REBUILD_DEADLINE_MIN", -1)  # deadline 과거 → 즉시 break
    monkeypatch.setattr(ep, "_publishTickers", lambda token: None)  # hermetic — SEC/HF 미접촉
    monkeypatch.setattr(
        "dartlab.core.dataLoader.loadEdgarListedUniverse", lambda *, forceUpdate=False: pl.DataFrame({"ticker": []})
    )
    called: list[int] = []
    monkeypatch.setattr(
        "dartlab.gather.original.edgar.submissions.listAllFilings",
        lambda *a, **k: called.append(1) or [],
    )
    monkeypatch.setattr(ep, "_flushRebuildBatch", lambda *a, **k: None)

    res = ep._runFullRebuild(StageResult(category="edgarPanel"), upload=True, token=None)
    assert res.report.ok == 1
    assert called == [], "deadline 경과 → SEC fetch 0건(첫 ticker 전 break)"


def test_publish_tickers_uploads_to_canonical_path(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """S0.2 — tickers.parquet 을 HF edgar/tickers/tickers.parquet 로 upload(브라우저 기대경로 계약)."""
    import dartlab.config as cfg
    import dartlab.pipeline.stages.edgarPanel as ep

    edgardir = tmp_path / "edgar"
    edgardir.mkdir(parents=True)
    (edgardir / "tickers.parquet").write_bytes(b"PAR1")  # 존재만 — 내용 무관(업로드 mock)
    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    monkeypatch.setattr("dartlab.gather.edgar.identity.loadTickers", lambda *, refresh: None)
    monkeypatch.setattr(ep, "_enrichTickerGaps", lambda src: None)  # gap 보강은 별도 테스트
    monkeypatch.setattr("dartlab.pipeline.hfUpload._resolveHfToken", lambda token: "tok")

    captured: dict = {}
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, **kw: captured.update(kw))

    ep._publishTickers(None)
    assert captured["path_in_repo"] == "edgar/tickers/tickers.parquet", "브라우저 기대 경로 고정"
    assert captured["repo_type"] == "dataset"


def test_enrich_ticker_gaps_fills_company_tickers_misses(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """S0.2 — company_tickers.json 누락 universe ticker(CTRA 등)를 browse-edgar CIK 로 보강."""
    import polars as pl

    import dartlab.pipeline.stages.edgarPanel as ep

    src = tmp_path / "tickers.parquet"
    # 발행 스키마(cik Utf8 zero-pad) — AAPL 만 있고 CTRA 누락
    pl.DataFrame({"ticker": ["AAPL"], "cik": ["0000320193"], "title": ["Apple Inc."]}).write_parquet(str(src))

    monkeypatch.setattr(ep, "_priorityTickers", lambda: ["AAPL", "CTRA", "ZZZZQQ"])
    # CTRA 는 해소, ZZZZQQ 는 미해소(None) → skip
    resolved = {"CTRA": "0000858470"}
    monkeypatch.setattr(
        "dartlab.gather.original.edgar.submissions._browseEdgarCik",
        lambda t: resolved.get(t),
    )

    ep._enrichTickerGaps(src)

    df = pl.read_parquet(str(src))
    by = dict(zip(df["ticker"].to_list(), df["cik"].to_list()))
    assert by.get("CTRA") == "0000858470", "gap 보강"
    assert "ZZZZQQ" not in by, "미해소는 skip"
    assert by.get("AAPL") == "0000320193", "기존 무회귀"


def test_publish_tickers_skips_when_file_absent(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """tickers.parquet 부재면 upload 미시도(클린 러너 안전)."""
    import dartlab.config as cfg
    import dartlab.pipeline.stages.edgarPanel as ep

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))  # edgar/tickers.parquet 부재
    monkeypatch.setattr("dartlab.gather.edgar.identity.loadTickers", lambda *, refresh: None)
    called: list[int] = []
    monkeypatch.setattr("dartlab.core.hfRetry.retryHfCall", lambda fn, **kw: called.append(1))

    ep._publishTickers(None)
    assert called == [], "파일 부재 → upload 0건"
