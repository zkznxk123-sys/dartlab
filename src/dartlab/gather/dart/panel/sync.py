"""panel 생산 오케스트레이션 (L1 gather) — refScan → learn → build → index.

panel artifact 의 build-time 파이프라인을 단일 진입점으로 묶는다. 수집(zip 다운로드)·HF
업로드는 본 함수 범위 밖 — 수집은 CI entry(``.github/scripts/sync``, layer-밖)가 기존
DART 수집기로 수행(gather↛providers, R1), HF 업로드는 ``uploadData.py``(SYNC_CATEGORY=panel,
DATA_RELEASES nested 자동). 즉 본 함수는 **로컬 zip → panel artifact 생산** 전담.

LLM Specifications:
    AntiPatterns:
        - collect(network) 포함 금지 — gather↛providers(R1), 수집은 CI entry(layer-밖).
        - HF push 포함 금지 — uploadData.py(SYNC_CATEGORY=panel) 분리.
        - refScan 기본 활성 금지 — 102k zip ~시간, 명시 플래그(refScan=True).
    OutputSchema:
        - ``syncPanel(...) -> dict`` (단계별 통계 ref/learn/build/index).
    Prerequisites:
        - polars. data/dart/original/docs/{code}/*.zip (수집 완료 선행).
    Freshness:
        - 분기 incremental — changed codes 만 build.
    Dataflow:
        - (refScan→panelXbrlRef) → learnBridge→panelBridge → buildPanelAll → buildIndex.
    TargetMarkets:
        - KR (DART). US 는 별도 sync(후속).
"""

from __future__ import annotations

import logging

import polars as pl

from .build import buildPanelAll
from .index import buildIndex, panelXbrlRefPath
from .learn import learnBridge

_log = logging.getLogger(__name__)


def syncPanel(
    *,
    codes: list[str] | None = None,
    refScan: bool = False,
    learn: bool = True,
    build: bool = True,
    index: bool = True,
    numWorkers: int = 8,
    verbose: bool = True,
) -> dict:
    """panel build-time 파이프라인 오케스트레이션 — refScan→learn→build→index.

    Args:
        codes: build 대상 종목 list. None = 전종목.
        refScan: True 면 전 corpus refScan 재실행(102k zip ~시간) → panelXbrlRef.parquet.
            기본 False (기존 ref 재사용).
        learn: True 면 ref → learnBridge → panelBridge (회사간 disclosureKey).
        build: True 면 buildPanelAll (zip → 14-col artifact).
        index: True 면 buildIndex (slim _index.parquet).
        numWorkers: build/refScan multiprocessing workers.
        verbose: 진행 로그.

    Returns:
        단계별 통계 dict — ``{ref, learn, build, index}`` (수행 안 한 단계는 None).

    Raises:
        없음 — 단계별 실패는 흡수(로그).

    Example:
        >>> syncPanel(codes=["005930"], refScan=False)  # doctest: +SKIP
        {'ref': None, 'learn': {...}, 'build': {...}, 'index': {...}}

    SeeAlso:
        - ``build.scanAllZips`` — refScan(ref truth).
        - ``learn.learnBridge`` — disclosureKey 전파.
        - ``build.buildPanelAll`` — artifact 생산.
        - ``index.buildIndex`` — slim 인덱스.

    Requires:
        - polars. 로컬 zip (수집 선행). 기존 또는 신규 panelXbrlRef.

    Capabilities:
        - panel 생산 전 단계를 한 호출로 — CI sync 잡 / 운영자 진입점.

    Guide:
        - 수집(zip)·HF push 는 본 함수 밖 — CI entry buildPanel.py 가 앞뒤로 묶음.

    AIContext:
        - 단계 플래그로 부분 실행 — refScan 은 비싸 기본 off.

    When:
        - panel 생산 전 단계를 한 진입점으로 묶어 실행할 때 (CI/운영자).

    How:
        - 단계 플래그로 refScan→learn→build→index 순차 호출.

    LLM Specifications:
        AntiPatterns:
            - collect/HF 포함 금지 — 분리(R1).
            - refScan 기본 on 금지 — 명시 플래그.
        OutputSchema:
            - ``dict`` (ref/learn/build/index 통계).
        Prerequisites:
            - 로컬 zip + (refScan off 시) 기존 panelXbrlRef.
        Freshness:
            - changed codes incremental.
        Dataflow:
            - refScan → learn → buildPanelAll → buildIndex.
        TargetMarkets:
            - KR (DART).
    """
    out: dict = {"ref": None, "learn": None, "build": None, "index": None}
    refPath = panelXbrlRefPath()

    if refScan:
        from .build.refScan import scanAllZips

        if verbose:
            _log.info("[syncPanel] refScan 전 corpus 시작")
        refDf = scanAllZips(minCorpCount=3, numWorkers=numWorkers, verbose=verbose)
        refPath.parent.mkdir(parents=True, exist_ok=True)
        refDf.write_parquet(str(refPath))
        out["ref"] = {"rows": refDf.height, "path": str(refPath)}

    if learn:
        ref = pl.read_parquet(str(refPath)) if refPath.exists() else None
        if ref is not None:
            out["learn"] = learnBridge(ref, write=True)
        elif verbose:
            _log.warning("[syncPanel] panelXbrlRef 없음 — learn 스킵 (refScan=True 필요)")

    if build:
        out["build"] = {
            "codes": len(buildPanelAll(refPath=str(refPath), codes=codes, numWorkers=numWorkers, verbose=verbose))
        }

    if index:
        out["index"] = buildIndex(verbose=verbose)

    if verbose:
        _log.info("[syncPanel] 완료: %s", out)
    return out
