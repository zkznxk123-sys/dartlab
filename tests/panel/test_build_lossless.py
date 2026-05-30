"""panel 빌드 태그 무손실/무중복 회귀 (G1·R4) — plan snazzy-wibbling-origami.

빌드 무손실의 정의(§10): 한 종목 zip 의 leaf element contentRaw 글자 합 ==
빌드된 artifact contentRaw 글자 합 **+ 태그 토큰(`<`) 수 일치**. horizontalize 가
element contentRaw 를 ``str.join("")`` 로 무손실 concat 하고 build 가 태그를 strip 하지
않으므로(R4), 전역 글자·태그 합이 정확히 보존된다. 합 동치 = 손실0 ∧ dup0 ∧ 태그무손실
동시 증명.

heavy + requires_data — 로컬 zip(``data/dart/original/docs/{code}``, local-only) + 빌드
artifact 둘 다 있어야 실행, 없으면 skip (CI 는 zip 미보유 → skip, collection green).
zip 전수 재파싱이라 무겁다 → test-lock.sh 단독 실행, fast/full preflight 제외.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

import dartlab.config as _cfg

pytestmark = [pytest.mark.requires_data, pytest.mark.heavy]

_BASE = "005930"
_PANEL_DIR = Path(_cfg.dataDir) / "dart" / "panel"
_ZIP_DIR = Path(_cfg.dataDir) / "dart" / "original" / "docs"
_REF_PATH = Path(_cfg.dataDir) / "dart" / "panelXbrlRef.parquet"


def _hasInputs(code: str) -> bool:
    art = _PANEL_DIR / code
    zips = _ZIP_DIR / code
    return art.exists() and any(art.glob("*.parquet")) and zips.exists() and any(zips.glob("*.zip"))


requires_inputs = pytest.mark.skipif(not _hasInputs(_BASE), reason="panel artifact 없음 (005930)")


def _sourceTotals(code: str) -> tuple[int, int]:
    """zip → walker element rows 의 (contentRaw 글자 합, `<` 태그 합). build 와 동일 경로."""
    from lxml import etree

    from dartlab.gather.dart.panel.build.builder import _readZip
    from dartlab.gather.dart.panel.build.refScan import scanRefBaseline
    from dartlab.gather.dart.panel.build.refScan.refMatcher import (
        _REF_TOKENS,
        precomputeRefTokens,
        setGlobalRefTokens,
    )
    from dartlab.gather.dart.panel.build.walker import detectSchemaEra, walkSections

    ref = pl.read_parquet(str(_REF_PATH)) if _REF_PATH.exists() else scanRefBaseline(minCorpCount=1)
    if _REF_TOKENS is None:
        setGlobalRefTokens(precomputeRefTokens(ref))

    parser = etree.XMLParser(recover=True, huge_tree=True)
    chars = 0
    tags = 0
    for zp in sorted((_ZIP_DIR / code).glob("*.zip")):
        rcept, xmls = _readZip(zp)
        if not xmls or not rcept:
            continue
        for xml in xmls:
            try:
                root = etree.fromstring(xml.encode("utf-8"), parser)
            except (etree.XMLSyntaxError, ValueError):
                continue
            if root is None:
                continue
            era = detectSchemaEra(root)
            for row in walkSections(root, era, ref, matchThreshold=0.70):
                cr = row.get("contentRaw") or ""
                chars += len(cr)
                tags += cr.count("<")
    return chars, tags


def _artifactTotals(code: str) -> tuple[int, int]:
    """빌드 artifact 전 period 의 (contentRaw 글자 합, `<` 태그 합)."""
    files = [str(f) for f in sorted((_PANEL_DIR / code).glob("*.parquet")) if f.name != "_index.parquet"]
    art = pl.read_parquet(files)
    chars = art.select(pl.col("contentRaw").str.len_chars().sum()).item() or 0
    tags = art.select(pl.col("contentRaw").str.count_matches("<", literal=True).sum()).item() or 0
    return int(chars), int(tags)


@requires_inputs
def test_build_tag_lossless() -> None:
    """G1 — source element 글자·태그 합 == artifact contentRaw 글자·태그 합 (손실0·dup0·태그무손실)."""
    srcChars, srcTags = _sourceTotals(_BASE)
    assert srcChars > 0, "source 글자 0 — zip 파싱 실패 (테스트 환경 문제)"

    artChars, artTags = _artifactTotals(_BASE)

    assert artChars == srcChars, (
        f"contentRaw 글자 합 불일치 — source {srcChars:,} vs artifact {artChars:,} "
        f"(차 {artChars - srcChars:,}) — 손실 또는 중복 발생"
    )
    assert artTags == srcTags, (
        f"태그(`<`) 토큰 수 불일치 — source {srcTags:,} vs artifact {artTags:,} "
        f"(차 {artTags - srcTags:,}) — build 에서 태그 strip/가공 발생 (R4 위반)"
    )
