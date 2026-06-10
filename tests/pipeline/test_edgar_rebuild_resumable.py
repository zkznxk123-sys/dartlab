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
