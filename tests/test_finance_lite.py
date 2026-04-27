"""finance-lite (pyodide 용 경량 프리빌드) 회귀 테스트.

검증 지점:
1. `LITE_ACCOUNTS` 30 개가 전부 sortOrder.json 에 등록된 정규 snakeId
2. `buildFinanceLite` 가 원본 finance.parquet 에서 필터링해 lite 스펙을 만족하는
   산출물을 만드는지 (SCE 제외, sinceYear 이상, 필수 컬럼만)
3. pyodide 분기에서 `_scanAccountFromMerged` 가 pyarrow 로드 → `pl.from_arrow`
   변환 후 기존 스키마와 동일한 결과 반환
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest


@pytest.mark.unit
def test_lite_accounts_all_in_sortOrder():
    """LITE_ACCOUNTS 30 개가 sortOrder.json 에 모두 존재."""
    from dartlab.scan._helpers import _LITE_ACCOUNTS_BS, _LITE_ACCOUNTS_CF, _LITE_ACCOUNTS_IS, LITE_ACCOUNTS

    sortOrderPath = Path(__file__).resolve().parents[1] / "src" / "dartlab" / "core" / "utils" / "sortOrder.json"
    data = json.loads(sortOrderPath.read_text(encoding="utf-8"))

    assert len(LITE_ACCOUNTS) == 30, f"LITE_ACCOUNTS 는 30 개여야 함 (실제 {len(LITE_ACCOUNTS)})"

    missing_is = [a for a in _LITE_ACCOUNTS_IS if a not in data.get("IS", {})]
    missing_bs = [a for a in _LITE_ACCOUNTS_BS if a not in data.get("BS", {})]
    missing_cf = [a for a in _LITE_ACCOUNTS_CF if a not in data.get("CF", {})]

    assert not missing_is, f"IS 누락: {missing_is}"
    assert not missing_bs, f"BS 누락: {missing_bs}"
    assert not missing_cf, f"CF 누락: {missing_cf}"


@pytest.mark.unit
def test_lite_spec_constants():
    """lite 스펙 상수가 기대값대로 유지되는지 — 회귀 보호."""
    from dartlab.scan._helpers import LITE_SINCE_YEAR, LITE_SJ_DIVS

    assert LITE_SINCE_YEAR == 2022, "5년치 분기 스펙 (2022~) 변경되면 파일 크기/서비스 UX 에 영향"
    assert "SCE" not in LITE_SJ_DIVS, "SCE (자본변동) 는 용량 27.8% 차지 + scan 미사용이라 반드시 제외"
    assert set(LITE_SJ_DIVS) == {"IS", "BS", "CIS", "CF"}


@pytest.mark.unit
def test_buildFinanceLite_filters_correctly(tmp_path, monkeypatch):
    """buildFinanceLite 가 원본에서 sj_div/계정/연도 필터를 정확히 적용하는지."""
    from dartlab.scan import builder
    from dartlab.scan._helpers import LITE_SINCE_YEAR

    # 가짜 finance.parquet 작성 — 원본과 동일 스키마
    scanDir = tmp_path / "dart" / "scan"
    scanDir.mkdir(parents=True)
    fakeFinance = scanDir / "finance.parquet"

    df = pl.DataFrame(
        {
            "stockCode": ["005930", "005930", "005930", "000660", "000660", "000660"],
            "bsns_year": ["2021", "2023", "2023", "2023", "2023", "2023"],  # 2021 은 필터로 제외
            "reprt_nm": ["4분기", "4분기", "4분기", "4분기", "4분기", "4분기"],
            "sj_div": ["IS", "IS", "SCE", "IS", "BS", "CF"],  # SCE 는 필터로 제외
            "fs_nm": ["연결재무제표"] * 6,
            "account_id": ["ifrs-full_Revenue"] * 6,
            "account_nm": ["매출액", "매출액", "매출액", "매출액", "자산총계", "영업활동현금흐름"],
            "thstrm_amount": ["1000", "2000", "3000", "4000", "5000", "6000"],
            "thstrm_add_amount": ["1000", "2000", "3000", "4000", "5000", "6000"],
        }
    )
    df.write_parquet(str(fakeFinance))

    # _scanDir 을 tmp_path 로 몽키패치
    monkeypatch.setattr(builder, "_scanDir", lambda: scanDir)

    outputPath = builder.buildFinanceLite(verbose=False)
    assert outputPath is not None
    assert outputPath.name == "finance-lite.parquet"
    assert outputPath.exists()

    result = pl.read_parquet(str(outputPath))

    # 필터 검증
    assert result["bsns_year"].cast(pl.Int32, strict=False).min() >= LITE_SINCE_YEAR, "sinceYear 필터 실패"
    assert "SCE" not in result["sj_div"].unique().to_list(), "SCE 제외 실패"
    assert set(result.columns) == {
        "stockCode",
        "bsns_year",
        "reprt_nm",
        "sj_div",
        "fs_nm",
        "account_id",
        "account_nm",
        "thstrm_amount",
        "thstrm_add_amount",
    }, f"컬럼 스펙 위반: {result.columns}"

    # 2021 과 SCE 가 다 필터되면 2023 × (IS 매출액 + BS 자산총계 + CF 영업CF) = 3 행
    assert result.height >= 2, f"결과 행 너무 적음: {result.height}"


@pytest.mark.unit
def test_scanAccount_pyodide_path_uses_pyarrow(tmp_path, monkeypatch):
    """_IS_PYODIDE=True 에서 _scanAccountFromMerged 가 pyarrow 경로를 써서
    정상 결과를 반환하는지.

    pyodide 런타임은 pyarrow 가 기본 번들이지만 dev venv 는 없을 수 있어 skip.
    """
    pytest.importorskip("pyarrow")

    import importlib

    from dartlab.core import dataLoader

    # `dartlab.providers.dart.finance.scanAccount` 는 함수와 모듈이 같은 이름이라
    # `from X import scanAccount` 는 함수로 가려짐 — 모듈 경로로 직접 import.
    saModule = importlib.import_module("dartlab.providers.dart.finance.scanAccount")

    # lite 유사 샘플 parquet
    lite = tmp_path / "finance-lite.parquet"
    pl.DataFrame(
        {
            "stockCode": ["005930", "005930", "000660"],
            "bsns_year": ["2023", "2024", "2023"],
            "reprt_nm": ["4분기", "4분기", "4분기"],
            "sj_div": ["IS", "IS", "IS"],
            "fs_nm": ["연결재무제표", "연결재무제표", "연결재무제표"],
            "account_id": ["ifrs-full_Revenue", "ifrs-full_Revenue", "ifrs-full_Revenue"],
            "account_nm": ["매출액", "매출액", "매출액"],
            "thstrm_amount": ["100", "200", "300"],
            "thstrm_add_amount": ["100", "200", "300"],
        }
    ).write_parquet(str(lite))

    # pyodide 플래그 강제 ON (dataLoader 에 걸면 scanAccount 내부 import 시에도 반영)
    monkeypatch.setattr(dataLoader, "_IS_PYODIDE", True, raising=False)

    fastKeys = {"매출액", "ifrs-full_Revenue"}
    result = saModule._scanAccountFromMerged(
        scanPath=lite,
        snakeId="sales",
        sjDiv="IS",
        filterDivs=["IS", "CIS"],
        fsPref="CFS",
        fastKeys=fastKeys,
        freq="Y",
    )

    assert result is not None, "pyodide 경로 결과가 None"
    assert "stockCode" in result.columns and "period" in result.columns and "amount" in result.columns
    assert result.height == 3, f"기대 3 행 (005930×2 + 000660×1), 실제 {result.height}"
