"""EDGAR 벌크 다운로더·파서 단위 테스트.

네트워크 I/O 없이 동작:
- companyfacts.zip 소형 가짜 데이터 주입 → convertBulkToParquets 동작 검증
- 분기 zip TSV 형식 파싱 검증
- freshness TTL/ETag 캐시 검증

실제 SEC 엔드포인트 호출 테스트는 `test_edgarBulk_integration.py` 로 분리.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import polars as pl
import pytest


pytestmark = pytest.mark.unit


# ── companyfactsBulk ──────────────────────────────────────────────────


def _makeFakeCompanyFacts(cik: int = 1234567) -> dict:
    """최소 companyfacts JSON 픽스처."""
    return {
        "cik": cik,
        "entityName": "TestCo Inc.",
        "facts": {
            "us-gaap": {
                "Assets": {
                    "label": "Assets",
                    "units": {
                        "USD": [
                            {
                                "accn": "0001234567-24-000001",
                                "fy": 2024,
                                "fp": "FY",
                                "form": "10-K",
                                "filed": "2024-12-31",
                                "frame": "CY2024",
                                "start": "2024-01-01",
                                "end": "2024-12-31",
                                "val": 1000000000,
                            },
                        ]
                    },
                },
            }
        },
    }


def test_companyfacts_zip_convert(tmp_path: Path) -> None:
    from dartlab.providers.edgar.bulk import convertBulkToParquets

    # 가짜 companyfacts.zip 생성
    zipPath = tmp_path / "companyfacts.zip"
    payload = _makeFakeCompanyFacts(cik=1234567)
    with zipfile.ZipFile(zipPath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("CIK0001234567.json", json.dumps(payload))

    outDir = tmp_path / "finance"
    result = convertBulkToParquets(
        zipPath=zipPath, outDir=outDir, progress=False
    )
    assert result["converted"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0

    outPath = outDir / "0001234567.parquet"
    assert outPath.exists()
    df = pl.read_parquet(outPath)
    assert df.height == 1
    assert df["tag"][0] == "Assets"
    assert df["val"][0] == 1e9
    # 스키마 보존: companyfacts API 와 동일 (15 컬럼)
    assert "plabel" not in df.columns  # plabel 은 분기 pre.tsv 에서 별도 enrich


def test_extract_companyfacts_iter(tmp_path: Path) -> None:
    from dartlab.providers.edgar.bulk import extractCompanyfactsZip

    zipPath = tmp_path / "bulk.zip"
    with zipfile.ZipFile(zipPath, "w", zipfile.ZIP_DEFLATED) as zf:
        for cikInt in (1, 42, 999999):
            cikStr = str(cikInt).zfill(10)
            zf.writestr(
                f"CIK{cikStr}.json",
                json.dumps(_makeFakeCompanyFacts(cikInt)),
            )

    ciks = []
    payloads = []
    for cik, payload in extractCompanyfactsZip(zipPath):
        ciks.append(cik)
        payloads.append(payload)

    assert sorted(ciks) == ["0000000001", "0000000042", "0000999999"]
    assert all(p.get("facts", {}).get("us-gaap", {}).get("Assets") for p in payloads)


def test_convert_bulk_only_ciks_filter(tmp_path: Path) -> None:
    from dartlab.providers.edgar.bulk import convertBulkToParquets

    zipPath = tmp_path / "companyfacts.zip"
    with zipfile.ZipFile(zipPath, "w", zipfile.ZIP_DEFLATED) as zf:
        for cikInt in (1, 42, 999999):
            cikStr = str(cikInt).zfill(10)
            zf.writestr(f"CIK{cikStr}.json", json.dumps(_makeFakeCompanyFacts(cikInt)))

    outDir = tmp_path / "finance"
    result = convertBulkToParquets(
        zipPath=zipPath,
        outDir=outDir,
        onlyCiks={"0000000042"},
        progress=False,
    )
    assert result["converted"] == 1
    assert result["skipped"] == 2
    assert (outDir / "0000000042.parquet").exists()
    assert not (outDir / "0000000001.parquet").exists()


# ── freshness ─────────────────────────────────────────────────────────


def test_freshness_touch_and_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import dartlab
    from dartlab.providers.edgar.bulk import (
        inspectBulkFreshness,
        invalidateBulkFreshness,
        isBulkFresh,
        touchBulkFreshness,
    )

    monkeypatch.setattr(dartlab.config, "dataDir", str(tmp_path))

    tag = "test_bulk"
    snap = inspectBulkFreshness(tag)
    assert not snap.exists
    assert snap.etag is None

    touchBulkFreshness(tag, etag="abc123")
    snap = inspectBulkFreshness(tag)
    assert snap.exists
    assert snap.etag == "abc123"
    assert snap.ageHours is not None
    assert snap.ageHours < 0.01  # 방금 생성

    assert isBulkFresh(tag, ttlHours=24)
    assert not isBulkFresh(tag, ttlHours=0)  # TTL 0 = 항상 stale

    invalidateBulkFreshness(tag)
    snap = inspectBulkFreshness(tag)
    assert not snap.exists
    assert snap.etag is None


# ── datasetBulk TSV 파싱 ──────────────────────────────────────────────


def _makeQuarterlyZip(tmp_path: Path, year: int = 2025, quarter: int = 4) -> Path:
    """최소 분기 zip 픽스처 (sub/pre/tag TSV)."""
    zipPath = tmp_path / f"{year}q{quarter}.zip"
    with zipfile.ZipFile(zipPath, "w", zipfile.ZIP_DEFLATED) as zf:
        sub = (
            "adsh\tcik\tname\tform\tperiod\tfy\tfp\tfiled\taccepted\tinstance\t"
            "countryba\tstprba\tcityba\tsic\tein\tfye\tdetail\tnbr\n"
            "0001234567-25-000001\t1234567\tTestCo Inc.\t10-K\t20251231\t2025\tFY\t"
            "20260201\t20260201120000\ttest-10k.xml\tUS\tCA\tCupertino\t3674\t"
            "123456789\t1231\t1\t1\n"
        )
        zf.writestr("sub.txt", sub)

        pre = (
            "adsh\treport\tline\tstmt\tinpth\trfile\ttag\tversion\tplabel\tnegating\n"
            "0001234567-25-000001\t1\t10\tBS\t0\tH\tAssets\tus-gaap/2024\tTotal assets\t0\n"
            "0001234567-25-000001\t1\t20\tBS\t1\tH\tAssetsCurrent\tus-gaap/2024\tCurrent assets\t0\n"
        )
        zf.writestr("pre.txt", pre)

        tag = (
            "tag\tversion\tcustom\tabstract\tdatatype\tiord\tcrdr\ttlabel\tdoc\n"
            "Assets\tus-gaap/2024\t0\t0\tmonetaryItemType\tI\tdebit\tAssets\t"
            "Sum of the carrying amounts...\n"
        )
        zf.writestr("tag.txt", tag)
    return zipPath


def test_quarterly_convert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import dartlab
    from dartlab.providers.edgar.bulk import convertQuarterlyToParquets

    monkeypatch.setattr(dartlab.config, "dataDir", str(tmp_path))

    zipPath = _makeQuarterlyZip(tmp_path, 2025, 4)
    outPaths = convertQuarterlyToParquets(2025, 4, zipPath=zipPath)

    assert set(outPaths.keys()) == {"sub", "pre", "tag"}
    for kind, path in outPaths.items():
        assert path.exists(), f"{kind} parquet 없음"
        df = pl.read_parquet(path)
        assert df.height >= 1, f"{kind} 비어있음"

    # 핵심 컬럼 보존
    pre = pl.read_parquet(outPaths["pre"])
    assert "plabel" in pre.columns
    assert "stmt" in pre.columns
    assert pre["plabel"][0] == "Total assets"

    sub = pl.read_parquet(outPaths["sub"])
    assert sub["cik"][0] == "0001234567"  # 0-padded 10자리


def test_dataset_files_excludes_num() -> None:
    """num.tsv 는 받지 않는다 — companyfacts.zip 이 원본 (ops/edgar.md 원칙)."""
    from dartlab.providers.edgar.bulk import DATASET_FILES

    assert "num" not in DATASET_FILES
    assert set(DATASET_FILES) == {"sub", "pre", "tag"}


# ── DataConfig 통합 ──────────────────────────────────────────────────


def test_dataconfig_edgar_meta_registered() -> None:
    from dartlab.core.dataConfig import DATA_RELEASES

    assert "edgarMeta" in DATA_RELEASES
    assert DATA_RELEASES["edgarMeta"]["dir"] == "edgar/meta"
    assert DATA_RELEASES["edgar"]["dir"] == "edgar/finance"
    assert DATA_RELEASES["edgarScan"]["dir"] == "edgar/scan"
    assert DATA_RELEASES["edgarDocs"]["dir"] == "edgar/docs"
