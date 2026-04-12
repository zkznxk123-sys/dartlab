"""dartlab pyodide wheel 빌드 + HF 업로드."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
HF_REPO = "eddmpython/dartlab-data"
HF_DIR = "pyodide"


def build_wheel() -> Path:
    """uv build --wheel → dist/*.whl 경로 반환."""
    subprocess.run(["uv", "build", "--wheel"], cwd=ROOT, check=True)
    wheels = sorted(DIST.glob("dartlab-*.whl"), key=lambda p: p.stat().st_mtime)
    if not wheels:
        raise FileNotFoundError("빌드된 wheel 없음")
    return wheels[-1]


def upload_to_hf(wheel_path: Path, token: str | None = None) -> str:
    """wheel을 HF datasets에 업로드."""
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    url = api.upload_file(
        path_or_fileobj=str(wheel_path),
        path_in_repo=f"{HF_DIR}/{wheel_path.name}",
        repo_id=HF_REPO,
        repo_type="dataset",
    )
    print(f"업로드 완료: {url}")
    return url


def main():
    import argparse

    parser = argparse.ArgumentParser(description="dartlab pyodide wheel 빌드/업로드")
    parser.add_argument("--upload", action="store_true", help="HF에 업로드")
    parser.add_argument("--token", help="HF 토큰 (없으면 환경변수 HF_TOKEN)")
    args = parser.parse_args()

    whl = build_wheel()
    print(f"wheel: {whl} ({whl.stat().st_size / 1024:.0f} KB)")

    # pyodide/ 폴더에도 복사 (로컬 테스트용)
    local_copy = Path(__file__).parent / whl.name
    import shutil
    shutil.copy2(whl, local_copy)
    print(f"로컬 복사: {local_copy}")

    if args.upload:
        import os
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        token = args.token or os.environ.get("HF_TOKEN")
        if not token:
            print("⚠ HF_TOKEN 필요: --token 또는 환경변수", file=sys.stderr)
            sys.exit(1)
        upload_to_hf(whl, token)


if __name__ == "__main__":
    main()
