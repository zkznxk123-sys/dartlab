"""intentModel 을 HF 공개 데이터셋에 올린다 — 프론트 queryCanon 이 라이브로 fetch(dart/queries/intentModel.json).
HF_TOKEN: 환경변수(GitHub Action secret) 우선, 없으면 .env(로컬). 회귀게이트 PASS 후에만 호출(워크플로가 게이팅).
실행: uv run --with huggingface-hub python -X utf8 .github/scripts/queries/uploadIntentModel.py
"""

from __future__ import annotations

import os
from pathlib import Path

from huggingface_hub import HfApi

REPO = "eddmpython/dartlab-data"
LOCAL = Path(__file__).resolve().parent / "intentModel.json"  # build 산출물(스크립트 옆)


def load_token() -> str:
    t = os.environ.get("HF_TOKEN")
    if t:
        return t
    env = Path(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("HF_TOKEN 없음 (.env 또는 환경변수)")


def main() -> None:
    api = HfApi(token=load_token())
    api.upload_file(
        path_or_fileobj=str(LOCAL),
        path_in_repo="dart/queries/intentModel.json",
        repo_id=REPO,
        repo_type="dataset",
        commit_message="intentModel v2 — 결정론 섹션 target + IDF route (curated 384q)",
    )
    print(f"✅ uploaded dart/queries/intentModel.json ({LOCAL.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
