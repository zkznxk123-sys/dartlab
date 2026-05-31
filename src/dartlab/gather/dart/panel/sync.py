"""panel 생산 오케스트레이션 (L1 gather) — refScan → build → index → label.

panel artifact 의 build-time 파이프라인을 단일 진입점으로 묶는다. 수집(zip 다운로드)·HF
업로드는 본 함수 범위 밖 — 수집은 CI entry(``.github/scripts/sync``, layer-밖)가 기존
DART 수집기로 수행(gather↛providers, R1), HF 업로드는 ``uploadData.py``(SYNC_CATEGORY=panel,
DATA_RELEASES nested 자동). 즉 본 함수는 **로컬 zip → panel artifact 생산** 전담.

정렬키는 native canonicalKey(build 가 scope-strip 채움) — 손수 bridge-learning 단계 폐기
(2026-05 redesign). bridge 는 US cross-market overlay 전용이라 본 KR 파이프라인 밖(운영자 seed).

LLM Specifications:
    AntiPatterns:
        - collect(network) 포함 금지 — gather↛providers(R1), 수집은 CI entry(layer-밖).
        - HF push 포함 금지 — uploadData.py(SYNC_CATEGORY=panel) 분리.
        - refScan 기본 활성 금지 — 102k zip ~시간, 명시 플래그(refScan=True).
        - bridge-learning 단계 부활 금지 — KR 정렬은 canonicalKey(코드 규칙).
    OutputSchema:
        - ``syncPanel(...) -> dict`` (단계별 통계 ref/build/index/label).
    Prerequisites:
        - polars. data/dart/original/docs/{code}/*.zip (수집 완료 선행).
    Freshness:
        - 분기 incremental — changed codes 만 build.
    Dataflow:
        - (refScan→panelXbrlRef) → buildPanelAll(canonicalKey) → buildIndex → buildLabel.
    TargetMarkets:
        - KR (DART). US 는 별도 sync(후속).
"""

from __future__ import annotations

import logging

from .build import buildPanelAll
from .index import buildIndex, buildLabel, panelXbrlRefPath

_log = logging.getLogger(__name__)


def syncPanel(
    *,
    codes: list[str] | None = None,
    refScan: bool = False,
    build: bool = True,
    index: bool = True,
    label: bool = True,
    numWorkers: int = 8,
    verbose: bool = True,
) -> dict:
    """panel build-time 파이프라인 오케스트레이션 — refScan→build→index→label.

    Args:
        codes: build 대상 종목 list. None = 전종목.
        refScan: True 면 전 corpus refScan 재실행(102k zip ~시간) → panelXbrlRef.parquet.
            기본 False (기존 ref 재사용). 옛 양식(v1) fuzzy 복원·라벨 보강의 입력.
        build: True 면 buildPanelAll (zip → 14-col artifact, canonicalKey 정렬키).
        index: True 면 buildIndex (slim _index.parquet).
        label: True 면 buildLabel (canonicalKey → 한글 표시라벨 _label.parquet).
        numWorkers: build/refScan multiprocessing workers.
        verbose: 진행 로그.

    Returns:
        단계별 통계 dict — ``{ref, build, index, label}`` (수행 안 한 단계는 None).

    Raises:
        없음 — 단계별 실패는 흡수(로그).

    Example:
        >>> syncPanel(codes=["005930"], refScan=False)  # doctest: +SKIP
        {'ref': None, 'build': {...}, 'index': {...}, 'label': {...}}

    SeeAlso:
        - ``build.scanAllZips`` — refScan(ref truth, v1 fuzzy·라벨 입력).
        - ``build.buildPanelAll`` — artifact 생산(canonicalKey).
        - ``index.buildIndex`` — slim 인덱스.
        - ``index.buildLabel`` — 표시라벨.

    Requires:
        - polars. 로컬 zip (수집 선행). 기존 또는 신규 panelXbrlRef.

    Capabilities:
        - panel 생산 전 단계를 한 호출로 — CI sync 잡 / 운영자 진입점.

    Guide:
        - 수집(zip)·HF push 는 본 함수 밖 — CI entry buildPanel.py 가 앞뒤로 묶음.

    AIContext:
        - 단계 플래그로 부분 실행 — refScan 은 비싸 기본 off. KR 정렬은 canonicalKey(bridge 없음).

    When:
        - panel 생산 전 단계를 한 진입점으로 묶어 실행할 때 (CI/운영자).

    How:
        - 단계 플래그로 refScan→build→index→label 순차 호출.

    LLM Specifications:
        AntiPatterns:
            - collect/HF 포함 금지 — 분리(R1).
            - refScan 기본 on 금지 — 명시 플래그.
            - bridge-learning 단계 부활 금지 — canonicalKey SSOT.
        OutputSchema:
            - ``dict`` (ref/build/index/label 통계).
        Prerequisites:
            - 로컬 zip + (refScan off 시) 기존 panelXbrlRef.
        Freshness:
            - changed codes incremental.
        Dataflow:
            - refScan → buildPanelAll → buildIndex → buildLabel.
        TargetMarkets:
            - KR (DART).
    """
    out: dict = {"ref": None, "build": None, "index": None, "label": None}
    refPath = panelXbrlRefPath()

    if refScan:
        from .build.refScan import scanAllZips

        if verbose:
            _log.info("[syncPanel] refScan 전 corpus 시작")
        refDf = scanAllZips(minCorpCount=3, numWorkers=numWorkers, verbose=verbose)
        refPath.parent.mkdir(parents=True, exist_ok=True)
        refDf.write_parquet(str(refPath))
        out["ref"] = {"rows": refDf.height, "path": str(refPath)}

    if build:
        out["build"] = {
            "codes": len(buildPanelAll(refPath=str(refPath), codes=codes, numWorkers=numWorkers, verbose=verbose))
        }

    if index:
        out["index"] = buildIndex(verbose=verbose)

    if label:
        out["label"] = buildLabel(verbose=verbose)

    if verbose:
        _log.info("[syncPanel] 완료: %s", out)
    return out
