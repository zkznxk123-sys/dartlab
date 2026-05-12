"""EDGAR 데이터 → HuggingFace 데이터셋 배포.

⛔ **원칙: finance / meta 는 HF 에 올리지 않는다.**
SEC 자체 벌크(`companyfacts.zip` daily + 분기 `{Y}q{Q}.zip`) 가 원본이고
사용자 PC 에서 자동 다운로드·변환하므로 HF 미러링은 낭비 + rate limit 원인.

HF 에 올리는 것은 **dartlab 파생물** 만:
- `scan` → edgar/scan  (buildEdgarFinance() 프리빌드, 재계산 비용 큼)
- `docs` → edgar/docs  (submissions API HTML 섹션 파싱 결과)

사용법::

    from dartlab.providers.edgar.openapi.deploy import deployEdgarToHF
    deployEdgarToHF(categories=["scan", "docs"])  # 기본값

`data.sec.gov/api/xbrl/companyfacts` API 파생물은 업로드 대상이 아니다 —
사용자가 `c.refreshFromApi()` 로 로컬만 갱신한다.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dartlab.frame.dataConfig import DATA_RELEASES, HF_REPO

_log = logging.getLogger(__name__)

# HF 에 업로드 허용된 카테고리 — dartlab 파생물만.
# finance / meta 는 SEC 벌크가 원본이므로 사용자 PC 에서 자동 다운로드 (HF 미러링 없음).
_CATEGORY_MAP = {
    "scan": "edgarScan",
    "docs": "edgarDocs",
}

# 업로드 명시 차단 목록 (원본이 SEC 벌크, HF 미러링 정책상 제외)
_BULK_ORIGIN_CATEGORIES = {"finance", "meta"}


def deployEdgarToHF(
    categories: list[str] | None = None,
    *,
    token: str | None = None,
    dryRun: bool = False,
    commitMessage: str | None = None,
) -> dict[str, int]:
    """EDGAR 데이터를 HuggingFace datasets repo 에 `upload_folder` 로 업로드.

    각 카테고리는 **단일 커밋** 으로 업로드된다 (HF rate limit 회피).

    Parameters
    ----------
    categories : list
        업로드할 카테고리 — "finance" | "meta" | "scan" | "docs".
        None 이면 ["finance", "meta", "scan", "docs"] 전체.
    token : str
        HuggingFace API 토큰 (없으면 HF_TOKEN 환경변수).
    dryRun : bool
        True 면 업로드하지 않고 파일 개수만 반환.
    commitMessage : str
        커밋 메시지 prefix. 없으면 기본값 "sync: edgar {cat}".

    Returns
    -------
    dict : {"finance": N, ...} 업로드한 카테고리별 파일 수.

    Raises:
        ValueError: HF_TOKEN 부재 + dryRun=False.

    Example:
        >>> deployEdgarToHF(categories=["scan"], dryRun=True)

    Args:
        categories: <TODO: param desc> (list[str] | None)
        token: <TODO: param desc> (str | None)
        dryRun: <TODO: param desc> (bool)
        commitMessage: <TODO: param desc> (str | None)

    Returns:
        <TODO: return desc> (dict[str, int])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - logging

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
    """
    from huggingface_hub import HfApi

    hfToken = token or os.getenv("HF_TOKEN")
    if not hfToken and not dryRun:
        raise ValueError("HF_TOKEN이 필요합니다. 환경변수 또는 token 파라미터로 설정하세요.")

    cats = categories or ["scan", "docs"]

    validCats: list[str] = []
    for cat in cats:
        if cat in _BULK_ORIGIN_CATEGORIES:
            _log.info(
                "[deploy] '%s' 는 SEC 벌크가 원본이라 HF 미러링 정책상 제외 (사용자 PC 에서 자동 다운로드). 스킵.",
                cat,
            )
            continue
        configKey = _CATEGORY_MAP.get(cat, cat)
        if configKey not in DATA_RELEASES:
            _log.info(f"[deploy] 카테고리 '{cat}' → configKey '{configKey}'가 DATA_RELEASES에 없음. 스킵.")
            continue
        validCats.append(cat)

    if not validCats:
        _log.info("[deploy] 유효한 카테고리가 없습니다.")
        return {}

    api = HfApi(token=hfToken) if not dryRun else None
    result: dict[str, int] = {}

    for cat in validCats:
        configKey = _CATEGORY_MAP.get(cat, cat)
        config = DATA_RELEASES[configKey]

        from dartlab import config as _cfg

        localDir = Path(_cfg.dataDir) / config["dir"]
        if not localDir.exists():
            _log.info(f"[deploy] {localDir} 없음. 스킵.")
            result[cat] = 0
            continue

        # scan/meta 는 하위 폴더 구조가 있음 (scan/finance.parquet, meta/sub/*.parquet)
        parquets = sorted(localDir.rglob("*.parquet"))
        if not parquets:
            _log.info(f"[deploy] {localDir}에 parquet 없음. 스킵.")
            result[cat] = 0
            continue

        hfDir = config["dir"]
        nFiles = len(parquets)

        if dryRun:
            _log.info(f"[deploy] DRY RUN — {cat}: {nFiles}개 파일 → {HF_REPO}/{hfDir}/")
            result[cat] = nFiles
            continue

        msg = commitMessage or f"sync: edgar {cat} ({nFiles} files)"
        _log.info(f"[deploy] {cat}: {nFiles}개 파일 upload_folder → {HF_REPO}/{hfDir}/")

        try:
            api.upload_folder(
                folder_path=str(localDir),
                path_in_repo=hfDir,
                repo_id=HF_REPO,
                repo_type="dataset",
                commit_message=msg,
                ignore_patterns=["*.freshness", "*.etag", "*.tmp-*", "*.tmp", "*.bak-*"],
            )
            result[cat] = nFiles
            _log.info(f"[deploy] {cat}: {nFiles} 업로드 완료 (단일 커밋)")
        except (OSError, ValueError, RuntimeError) as exc:
            _log.error("[deploy] %s 실패: %s", cat, exc)
            result[cat] = 0

    return result
