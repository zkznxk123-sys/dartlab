"""로컬 parquet을 HuggingFace에 배치 업로드 (초기 마이그레이션용).

사용법:
    python bulkUploadHf.py finance              # 미업로드만 (기존 skip)
    python bulkUploadHf.py krxPricesV2 --force  # bitemporal v2 schema 일괄 push
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # _hfRetry (scripts/) import 경로
from _hfRetry import retryHfCall  # noqa: E402 — 429/503/504 에 "retry in X min" 파싱해 윈도우만큼 대기(공용 SSOT)

from dartlab.core.dataConfig import (  # noqa: E402 — 카테고리별 전용 repo 라우팅(미등록은 기본 repo)
    DATA_RELEASES,
    repoFor,
)

REPO = "eddmpython/dartlab-data"  # 기본/fallback (repoFor 가 미등록 카테고리에 반환하는 값과 동일)
BATCH_SIZE = 300  # 큰 배치 = 적은 commit = rate-limit 압력 감소 (HF 무료 1000 req/5min)
_INTER_BATCH_SLEEP = 3  # 배치 간 선제 페이싱(초)


def _existingCachePath(category: str) -> Path:
    """원격 기존-파일 목록의 로컬 영속 캐시 경로 (dist/, gitignored)."""
    return Path(f"dist/hfExisting_{category}.json")


def _loadExistingCache(category: str) -> set:
    """로컬 캐시 로드 — list_repo_tree 가 429 로 실패해도 진행 상태를 잃지 않는 resumability 정본."""
    p = _existingCachePath(category)
    if p.exists():
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001 — 캐시 손상 시 빈 set 으로 복구
            return set()
    return set()


def _saveExistingCache(category: str, existing: set) -> None:
    """업로드 진행분을 즉시 영속화 — 배치 성공마다 호출해 중단·재실행에 강건."""
    p = _existingCachePath(category)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(sorted(existing)), encoding="utf-8")


# 뉴스 카테고리 dir 은 dataConfig SSOT 에서 파생 (drift 차단 — newsSources/dataConfig 와 일치).
# naver(private) 는 repoFor 가 자동으로 전용 private repo 로 라우팅 → 공개 dartlab-data 안 감.
_NEWS_CATEGORIES = ("newsHeadlines", "newsEnriched", "newsGdelt", "newsNaver", "newsNaverEnriched")

# dir 은 dataConfig.DATA_RELEASES SSOT 파생 (하드코딩 복제 금지 — 한쪽만 바꾸면 조용히 drift).
# krxPricesV2 는 1 회용 bitemporal 마이그레이션 ad-hoc 키라 DATA_RELEASES 미등록 → 명시 유지.
CATEGORY_DIR = {
    **{c: DATA_RELEASES[c]["dir"] for c in ("finance", "report", "panel", *_NEWS_CATEGORIES)},
    "krxPricesV2": "krx/prices/v2",
}

# nested=True 카테고리는 sub-dir (예: news/public/rss/{market}/ · dart/panel/{code}/) 까지 rglob 으로 수집,
# HF path_in_repo 도 dirPath + relpath 형태로 유지. nested=False 는 flat dirPath/*.parquet.
# panel: period-sharded {code}/{period}.parquet ~92k 파일 — list_repo_tree 로 미업로드만 골라 resumable·
# 배치 재시도(실패 배치 건너뜀, 재실행시 이어감)로 한도 내 점진 업로드(uploadData 의 one-shot upload_large_folder 대체).
NESTED_CATEGORIES = {"panel", *_NEWS_CATEGORIES}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("category", nargs="?", default="finance", help="finance/report/panel/krxPricesV2")
    parser.add_argument("--force", action="store_true", help="전체 재업로드 (schema 마이그레이션)")
    parser.add_argument(
        "--since",
        type=float,
        default=0,
        help="최근 N초 안 mtime 변경분만 (--force 와 동시 사용 X)",
    )
    args = parser.parse_args()
    category = args.category
    # 원본=SSOT 전략 전환(사용자 결정) — 옛 "원본 비공개" 가드 폐기. 원본 repo 는 비공개(public=False).
    dirPath = CATEGORY_DIR[category]
    localDir = Path(f"data/{dirPath}")

    # 토큰 일원화 — env > .env (옛 .env-only 는 env 만 있는 CI/파이프라인에서 FileNotFoundError).
    from dartlab.pipeline.hfUpload import _resolveHfToken

    token = _resolveHfToken()
    api = HfApi(token=token)
    nested = category in NESTED_CATEGORIES
    repo = repoFor(category)  # 전용 repo 분리 카테고리면 그쪽, 아니면 기본 REPO

    # 이미 올라간 파일 확인 — nested 면 recursive, flat 이면 surface 만. retryHfCall 로 감싸 rate-limit 에도
    # 목록을 확보(resumability 핵심 — 목록 실패하면 매 패스가 전체 재업로드라 수렴 안 됨).
    def _collectExisting() -> set:
        s = set()
        for f in api.list_repo_tree(repo, path_in_repo=dirPath, repo_type="dataset", recursive=nested):
            # list_repo_tree 는 RepoFile + RepoFolder 둘 다 yield. RepoFolder 엔 rfilename 없음
            # (AttributeError → 과거 resumability 무력화 근본버그). 둘 다 가진 .path 사용 + .parquet 만.
            rf = f.path
            if not rf.endswith(".parquet"):
                continue  # 폴더/비-parquet 제외
            # nested: 'dart/panel/000010/2025Q4.parquet' → '000010/2025Q4.parquet' relpath
            # flat: 'dart/finance/foo.parquet' → 'foo.parquet'
            relpath = rf[len(dirPath) + 1 :] if rf.startswith(dirPath + "/") else rf
            s.add(relpath)
        return s

    # 로컬 캐시 = resumability 정본. 원격 목록은 갱신용(성공 시 병합). list_repo_tree 가 92k 파일 페이지네이션
    # 중 429 로 실패해도 캐시로 진행 → 매 패스 26배치 헛검사·재업로드 없이 신규 프런티어 직행.
    existing = _loadExistingCache(category)
    if existing:
        print(f"로컬 캐시 기존: {len(existing)}개")
    try:
        remote = retryHfCall(_collectExisting)
        before = len(existing)
        existing |= remote
        if len(existing) != before or not _existingCachePath(category).exists():
            _saveExistingCache(category, existing)
        print(f"원격 목록 병합: 총 {len(existing)}개 (신규 +{len(existing) - before})")
    except Exception as e:  # noqa: BLE001 — 원격 실패해도 로컬 캐시로 진행(수렴 보장)
        print(f"원격 목록 조회 실패 — 로컬 캐시 {len(existing)}개로 진행: {e}")

    allFiles = sorted(localDir.rglob("*.parquet") if nested else localDir.glob("*.parquet"))

    # 파일수 벽 경고 — 실제 대용량(panel 9.2만·gdelt) 업로드는 이 경로로 오므로 여기서도 감시.
    # uploadData._monitorFileCount 는 sync 증분 경로 전용이라 bulk 마이그레이션 경로(panel)를 못 본다.
    _warn = int(os.environ.get("DARTLAB_HF_FILECOUNT_WARN", "80000"))
    if len(allFiles) >= _warn:
        print(
            f"⚠ 파일수 경고 — {category} {len(allFiles):,}개 파일 (repo={repo}, 경고임계 {_warn:,}). "
            f"HF repo 당 ~10만 파일 권장 한계 접근 → 전용 repo 분리(DATA_RELEASES['{category}']['repo']) 검토."
        )

    def _relpath(p: Path) -> str:
        return str(p.relative_to(localDir)).replace("\\", "/") if nested else p.name

    if args.force:
        remaining = list(allFiles)
        print(f"--force: 전체 {len(remaining)}개 재업로드 (schema 마이그레이션 모드)")
    elif args.since > 0:
        cutoff = time.time() - args.since
        remaining = [f for f in allFiles if f.stat().st_mtime >= cutoff]
        print(f"--since {args.since}s: 최근 변경 {len(remaining)}개 / 전체 {len(allFiles)}개")
    else:
        remaining = [f for f in allFiles if _relpath(f) not in existing]
        print(f"미업로드: {len(remaining)}개 / 전체: {len(allFiles)}개")

    if not remaining:
        print("모두 업로드 완료")
        return

    total = len(remaining)
    totalBatches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total, BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        batchNum = i // BATCH_SIZE + 1
        print(f"[{batchNum}/{totalBatches}] {len(batch)}개 업로드 중...")

        operations = [
            CommitOperationAdd(path_in_repo=f"{dirPath}/{_relpath(f)}", path_or_fileobj=str(f)) for f in batch
        ]
        try:
            # retryHfCall: 429/503/504 에 "retry in X min" 파싱해 윈도우만큼 대기 → 한도 내 점진(15s 고정보다 정확).
            retryHfCall(
                api.create_commit,
                repo_id=repo,
                repo_type="dataset",
                operations=operations,
                commit_message=f"{category} {batchNum}/{totalBatches} ({len(batch)} files)",
            )
            print(f"  batch {batchNum} 완료")
            # 성공분 즉시 캐시 영속화 — 다음 패스/재실행은 이 배치를 건너뛰고 프런티어 직행.
            existing |= {_relpath(f) for f in batch}
            _saveExistingCache(category, existing)
        except Exception as e:  # noqa: BLE001 — 실패 배치는 건너뛰고 진행, 재실행시 미업로드로 재시도(resumable)
            print(f"  batch {batchNum} 실패(건너뜀, 재실행시 재시도): {e}")
        time.sleep(_INTER_BATCH_SLEEP)  # 한도 선제 페이싱

    print(f"{category} 업로드 완료 (미완분은 재실행시 이어감)")


if __name__ == "__main__":
    main()
