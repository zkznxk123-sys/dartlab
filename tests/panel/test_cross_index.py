"""panel 회사간 cross-entity 정렬 (G6·G3) — plan snazzy-wibbling-origami.

slim ``_index.parquet`` 가 locator 만 보관(contentRaw 제외) → 회사간 read 가 본문 풀로드
없이 disclosure 보유 종목을 식별(G6). 같은 disclosureKey 를 여러 회사에 가로 정렬(회사간
정규화, G3 데이터 위 동작).

⚠️ OOM 가드: ``crossCompany(codes=None, key)`` 는 index 가 해당 key 보유 종목을 *자동
발견* 하지만, 현 P5 구현은 발견된 종목마다 ``readPanelWide`` (full contentRaw)를 로드 후
필터한다. 흔한 key(예: consolidatedBalanceSheet, ~2900 종목)에 codes=None 을 주면 전 회사
wide 를 메모리에 올려 Polars 네이티브 힙 OOM → 시스템 크래시. 따라서 본 테스트는 **명시
소수 codes** 만 쓴다. 전종목 cross 는 locator 기반 lazy cell pull 최적화(후속) 후에만 안전.

requires_data — ``_index.parquet`` 없으면 skip. fast/full preflight 제외.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg

pytestmark = pytest.mark.requires_data

_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"
_INDEX = _PANEL_DIR / "_index.parquet"

# 메모리 bounded — 5 baseline 만 (전종목 codes=None 풀로드 OOM 회피).
_SAFE_CODES = ["005930", "000660", "005380", "035720", "207940"]

requires_index = pytest.mark.skipif(not _INDEX.exists(), reason="panel artifact 없음 (_index.parquet)")


def _keySharedBy(codes: list[str]) -> str | None:
    """주어진 소수 codes 중 2+ 회사가 공통 보유한 disclosureKey (최다) — 없으면 None."""
    idx = pl.read_parquet(str(_INDEX))
    if "disclosureKey" not in idx.columns or "corp" not in idx.columns:
        return None
    sub = idx.filter(
        pl.col("corp").is_in(codes) & pl.col("disclosureKey").is_not_null() & (pl.col("disclosureKey") != "")
    )
    if sub.is_empty():
        return None
    cand = (
        sub.group_by("disclosureKey")
        .agg(pl.col("corp").n_unique().alias("ncorp"))
        .filter(pl.col("ncorp") >= 2)
        .sort("ncorp", descending=True)
    )
    return None if cand.is_empty() else cand["disclosureKey"][0]


@requires_index
def test_index_is_slim_locator_only() -> None:
    """G6 — _index 는 locator 만 (contentRaw 미보관 → cross 가속의 전제)."""
    idx = pl.read_parquet(str(_INDEX))
    assert "contentRaw" not in idx.columns, "_index 에 contentRaw 누출 — slim 위반(G6 무력화)"
    assert "disclosureKey" in idx.columns and "corp" in idx.columns


@requires_index
def test_cross_company_bounded_codes_span_multiple_corps() -> None:
    """G6·G3 — 명시 소수 codes 로 동일 disclosureKey 를 2+ 회사 한 보드에 정렬 (OOM-safe)."""
    from dartlab.providers.dart.panel import crossCompany

    key = _keySharedBy(_SAFE_CODES)
    if key is None:
        pytest.skip("baseline codes 공통 disclosureKey 없음")

    # ⚠️ 반드시 명시 codes — codes=None(전종목 자동발견)은 흔한 key 에서 OOM.
    cc = crossCompany(_SAFE_CODES, key)
    assert cc is not None, f"crossCompany({_SAFE_CODES}, '{key}') None — 회사간 정렬 실패"
    assert "corp" in cc.columns, f"corp 출처 컬럼 부재: {cc.columns}"
    nCorp = cc["corp"].n_unique()
    assert nCorp >= 2, f"'{key}' 회사간 정렬 회사 {nCorp} — 2+ 기대 (회사간 수평화 실패)"
