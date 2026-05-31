"""panel online 1패스 동등성 (P6 design-in) — plan snazzy-wibbling-origami.

build core 입력원-중립 리팩터(P2) 검증: 같은 zip 입력을 (A) 디스크 경로 ``buildPanel`` 과
(B) 메모리 bytes 스트림 ``buildPanelFromStream`` 으로 빌드하면 **period 별 14-col parquet 가
바이트 동형**이어야 한다. 둘 다 동일 코어(``_xmlsToPeriodRows`` → ``_writePeriodShards``)를 거치고
입력원만 zip(Path) vs zip(bytes) 로 다르다 — 동등성이 곧 online 트랙의 무손실 보장.

heavy + requires_data — 로컬 zip(``data/dart/original/docs/{code}``, local-only) 있어야 실행,
없으면 skip (CI 는 zip 미보유 → skip). 한 종목 2회 빌드라 무겁다 → test-lock.sh 단독, preflight 제외.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg

pytestmark = [pytest.mark.requires_data, pytest.mark.heavy]

_BASE = "005930"
_ZIP_DIR = Path(_cfg.dataDir) / "dart" / "original" / "docs"
_REF_PATH = Path(_cfg.dataDir) / "dart" / "panelXbrlRef.parquet"


def _hasZips(code: str) -> bool:
    zips = _ZIP_DIR / code
    return zips.exists() and any(zips.glob("*.zip"))


requires_zips = pytest.mark.skipif(not _hasZips(_BASE), reason="로컬 zip 없음 (005930)")


def _loadRef() -> pl.DataFrame:
    from dartlab.gather.dart.panel.build.refScan import scanRefBaseline

    if _REF_PATH.exists():
        return pl.read_parquet(str(_REF_PATH))
    return scanRefBaseline(minCorpCount=1)


@requires_zips
def test_disk_and_stream_builds_are_identical(tmp_path: Path) -> None:
    """buildPanel(zip 디스크) ≡ buildPanelFromStream(zip bytes) — period 별 parquet 바이트 동형."""
    from dartlab.gather.dart.panel.build import buildPanel, buildPanelFromStream

    ref = _loadRef()
    zps = sorted((_ZIP_DIR / _BASE).glob("*.zip"))
    assert zps, "zip 0 — 테스트 환경 문제"

    diskBase = tmp_path / "disk"
    streamBase = tmp_path / "stream"

    diskRes = buildPanel(_BASE, refDf=ref, outBaseDir=diskBase, overwrite=True)
    # 디스크와 동일 zip 순서(sorted glob) 로 bytes 스트림 구성 — rcept = 파일 stem(14자리).
    stream = [(zp.stem, zp.read_bytes()) for zp in zps]
    streamRes = buildPanelFromStream(_BASE, stream, refDf=ref, outBaseDir=streamBase, overwrite=True)

    assert diskRes == streamRes, f"period→rowCount 불일치: disk {diskRes} vs stream {streamRes}"

    diskFiles = sorted((diskBase / _BASE).glob("*.parquet"))
    assert diskFiles, "disk 빌드 산출 0"
    for pA in diskFiles:
        pB = streamBase / _BASE / pA.name
        assert pB.exists(), f"stream 빌드에 {pA.name} 없음"
        dfA = pl.read_parquet(pA).sort(["rceptNo", "blockOrder"])
        dfB = pl.read_parquet(pB).sort(["rceptNo", "blockOrder"])
        assert dfA.equals(dfB), f"{pA.name} contentRaw/14-col 불일치 — 입력원별 산출 drift"


@requires_zips
def test_read_zip_bytes_matches_disk() -> None:
    """_readZipBytes(bytes) ≡ _readZip(Path) — 동일 zip 의 decoded XML 동일."""
    from dartlab.gather.dart.panel.build.builder import _readZip, _readZipBytes

    zp = sorted((_ZIP_DIR / _BASE).glob("*.zip"))[0]
    rceptDisk, xmlsDisk = _readZip(zp)
    rceptBytes, xmlsBytes = _readZipBytes(zp.read_bytes(), rceptDisk or zp.stem)
    assert rceptBytes == (rceptDisk or zp.stem)
    assert xmlsDisk == xmlsBytes, "디스크/bytes decoded XML 불일치"
