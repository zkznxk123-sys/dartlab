"""EDGAR scan helpers 회귀 — scanEdgarAccounts 의 scanAccount freq 계약 + join 키 coalesce.

회귀 가드 2건:
  1. ``scanEdgarAccounts`` 가 ``scanAccount(annual=...)`` 로 호출해 TypeError → EDGAR scan 전
     재무축(profitability/growth/.../valuation) 무력화. scanAccount 계약은 ``freq``("Q"/"Y").
  2. 계정별 outer join 이 키를 coalesce 안 해 ``stockCode_{sid}`` 누출 + 키 불일치 행 stockCode
     null. ``how="full", coalesce=True`` 로 키 병합.

monkeypatch 로 scanAccount 를 합성 대체 — 16795 parquet 스캔 없이 계약만 검증.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_scan_edgar_accounts_uses_freq_and_coalesces_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """scanEdgarAccounts: scanAccount(freq=) 호출 + stockCode 단일 coalesce (누출·null 0)."""
    import dartlab.scan.builders.edgar.helpers as h

    calls: dict[str, str] = {}
    # 계정마다 종목 집합이 달라야 coalesce 검증됨 (sales=A,B / net_profit=B,C → union A,B,C).
    perAccount = {
        "sales": {"A": 10.0, "B": 20.0},
        "net_profit": {"B": 2.0, "C": 3.0},
    }

    def fakeScanAccount(sid: str, *, freq: str = "Q") -> pl.DataFrame:
        calls[sid] = freq  # annual= 로 호출되면 TypeError(회귀) — freq= 만 받는다
        data = perAccount[sid]
        return pl.DataFrame(
            {
                "stockCode": list(data),
                "corpName": [f"{k} Inc" for k in data],
                "2024": list(data.values()),
                "2023": [v * 0.9 for v in data.values()],
            }
        )

    # scanEdgarAccounts 내부 lazy import 경로(원천 모듈 attr)를 패치.
    monkeypatch.setattr("dartlab.providers.edgar.finance.scanAccount.scanAccount", fakeScanAccount)

    df = h.scanEdgarAccounts(["sales", "net_profit"])

    assert calls == {"sales": "Y", "net_profit": "Y"}, "annual=True → freq='Y' 계약"
    assert [c for c in df.columns if c.startswith("stockCode_")] == [], "stockCode 키 누출 0"
    assert df.filter(pl.col("stockCode").is_null()).height == 0, "키 불일치 행 stockCode null 0"
    assert set(df["stockCode"].to_list()) == {"A", "B", "C"}, "계정별 종목 union 보존"
