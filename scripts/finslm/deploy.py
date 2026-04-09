"""Stage F — HF 업로드 + Ollama Modelfile 생성 + dartlab provider 테스트.

사전 준비:
    - outputs/finslm-gguf/ 에 GGUF 파일 존재
    - HF_TOKEN 환경변수 설정
    - ollama 설치

실행:
    uv run python -X utf8 scripts/finslm/deploy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GGUF_DIR = ROOT / "outputs" / "finslm-gguf"


def upload_hf() -> bool:
    """HF 업로드."""
    token = os.getenv("HF_TOKEN")
    if not token:
        print("[SKIP] HF_TOKEN 없음 — HF 업로드 건너뜀")
        return False

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=token)

        repo_id = "eddmpython/dartlab-finslm-8b"
        api.create_repo(repo_id, exist_ok=True, repo_type="model")

        # GGUF 파일 업로드
        gguf_files = list(GGUF_DIR.glob("*.gguf"))
        if not gguf_files:
            print(f"[FAIL] GGUF 파일 없음: {GGUF_DIR}")
            return False

        for f in gguf_files:
            print(f"  업로드: {f.name} ({f.stat().st_size / 1e9:.1f}GB)")
            api.upload_file(
                path_or_fileobj=str(f),
                path_in_repo=f.name,
                repo_id=repo_id,
                repo_type="model",
            )

        print(f"  → https://huggingface.co/{repo_id}")
        return True
    except ImportError:
        print("[SKIP] huggingface_hub 없음")
        return False


def create_modelfile() -> Path:
    """Ollama Modelfile 생성."""
    gguf_files = list(GGUF_DIR.glob("*q4_k_m*.gguf"))
    if not gguf_files:
        gguf_files = list(GGUF_DIR.glob("*.gguf"))
    if not gguf_files:
        print(f"[FAIL] GGUF 파일 없음: {GGUF_DIR}")
        return Path()

    gguf_path = gguf_files[0]
    modelfile_path = GGUF_DIR / "Modelfile"

    content = f"""FROM {gguf_path.name}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096

SYSTEM \"\"\"당신은 dartlab 한국/미국 공시 분석 전문가입니다.
재무제표 데이터를 기반으로 기업을 분석합니다.
숫자는 원본 그대로 인용하고, 근거 없는 주장은 하지 않습니다.
6막 서사 구조(사업이해→수익성→현금→안정성→자본배분→전망)로 분석합니다.
dartlab Python API를 사용하여 코드를 실행하고 결과를 해석합니다.\"\"\"
"""
    modelfile_path.write_text(content, encoding="utf-8")
    print(f"  Modelfile → {modelfile_path}")
    print(f"  ollama create dartlab-finslm -f {modelfile_path}")
    return modelfile_path


def test_provider() -> bool:
    """dartlab.ask()로 로컬 모델 테스트."""
    try:
        import subprocess
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5,
        )
        if "dartlab-finslm" not in result.stdout:
            print("[SKIP] dartlab-finslm 모델 미설치")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[SKIP] ollama 없음")
        return False

    print("dartlab.ask() 테스트...")
    os.environ["DARTLAB_CONTEXT_V2"] = "1"

    from dartlab.ai.runtime.core import analyze
    import dartlab

    c = dartlab.Company("005930")
    full = ""
    for event in analyze(
        company=c,
        question="삼성전자 마진 분석해줘",
        provider="ollama",
        model="dartlab-finslm",
        max_turns=2,
    ):
        if event.kind == "chunk":
            full += event.data.get("text", "")

    print(f"  응답: {len(full)}자")
    return len(full) > 100


def main() -> int:
    print("Stage F — FinSLM 배포")
    print("=" * 60)

    # 1. HF 업로드
    print("\n[1/3] HuggingFace 업로드...")
    upload_hf()

    # 2. Modelfile
    print("\n[2/3] Ollama Modelfile...")
    mf = create_modelfile()

    # 3. 테스트
    print("\n[3/3] Provider 테스트...")
    test_provider()

    print("\n완료!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
