"""EDGAR 데이터 → HuggingFace 데이터셋 배포.

`upload_folder` 를 사용해 카테고리별 폴더를 **단일 커밋**으로 업로드한다.
과거 `upload_file` 루프는 HF per-repo 커밋 제한(128/hr) 에 걸렸음.

사용법::

    from dartlab.providers.edgar.openapi.deploy import deployEdgarToHF
    deployEdgarToHF(categories=["finance", "meta", "scan", "docs"])

카테고리:
- finance → edgar/finance  (companyfacts.zip 벌크 파생 parquet)
- meta    → edgar/meta     (분기 벌크 sub/pre/tag 파생)
- scan    → edgar/scan     (buildEdgarFinance() 프리빌드)
- docs    → edgar/docs     (submissions API 10-K/10-Q HTML 섹션)

`data.sec.gov/api/xbrl/companyfacts` API 파생물은 업로드 대상이 아니다 —
사용자가 `c.finance.refreshFromApi()` 로 로컬만 갱신한다.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

_log = logging.getLogger(__name__)

# cat 키 → DATA_RELEASES 키
_CATEGORY_MAP = {
    "finance": "edgar",
    "meta": "edgarMeta",
    "scan": "edgarScan",
    "docs": "edgarDocs",
}


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
    """
    from huggingface_hub import HfApi

    hfToken = token or os.getenv("HF_TOKEN")
    if not hfToken and not dryRun:
        raise ValueError("HF_TOKEN이 필요합니다. 환경변수 또는 token 파라미터로 설정하세요.")

    cats = categories or ["finance", "meta", "scan", "docs"]

    validCats: list[str] = []
    for cat in cats:
        configKey = _CATEGORY_MAP.get(cat, cat)
        if configKey not in DATA_RELEASES:
            print(f"[deploy] 카테고리 '{cat}' → configKey '{configKey}'가 DATA_RELEASES에 없음. 스킵.")
            continue
        validCats.append(cat)

    if not validCats:
        print("[deploy] 유효한 카테고리가 없습니다.")
        return {}

    api = HfApi(token=hfToken) if not dryRun else None
    result: dict[str, int] = {}

    for cat in validCats:
        configKey = _CATEGORY_MAP.get(cat, cat)
        config = DATA_RELEASES[configKey]

        from dartlab import config as _cfg

        localDir = Path(_cfg.dataDir) / config["dir"]
        if not localDir.exists():
            print(f"[deploy] {localDir} 없음. 스킵.")
            result[cat] = 0
            continue

        # scan/meta 는 하위 폴더 구조가 있음 (scan/finance.parquet, meta/sub/*.parquet)
        parquets = sorted(localDir.rglob("*.parquet"))
        if not parquets:
            print(f"[deploy] {localDir}에 parquet 없음. 스킵.")
            result[cat] = 0
            continue

        hfDir = config["dir"]
        nFiles = len(parquets)

        if dryRun:
            print(f"[deploy] DRY RUN — {cat}: {nFiles}개 파일 → {HF_REPO}/{hfDir}/")
            result[cat] = nFiles
            continue

        msg = commitMessage or f"sync: edgar {cat} ({nFiles} files)"
        print(f"[deploy] {cat}: {nFiles}개 파일 upload_folder → {HF_REPO}/{hfDir}/")

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
            print(f"[deploy] {cat}: {nFiles} 업로드 완료 (단일 커밋)")
        except (OSError, ValueError, RuntimeError) as exc:
            _log.error("[deploy] %s 실패: %s", cat, exc)
            result[cat] = 0

    return result
