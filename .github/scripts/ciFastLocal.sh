#!/usr/bin/env bash
# ciFastLocal.sh — CI Fast 의 test-fast 잡을 fresh venv 에서 정확히 재현.
#
# CI 가 매번 9 분 걸려 fail 발견하는 사이클 차단. 로컬에서 fresh `.venv-ci/`
# 를 만들고 .github/workflows/ci-fast.yml 의 test-fast 잡과 동일한 install
# 명령 + pytest 명령을 실행한다.
#
# 사용법:
#     bash .github/scripts/ciFastLocal.sh             # 전체 (fresh venv + test-fast)
#     bash .github/scripts/ciFastLocal.sh --import    # mcp.server 등 import smoke 만
#     bash .github/scripts/ciFastLocal.sh --no-reset  # venv 재사용 (빠른 재시도)
#
# venv 위치: 프로젝트 루트의 .venv-ci/. .gitignore 등록 필요.

set -e

VENV=".venv-ci"
RESET=1
IMPORT_ONLY=0

for arg in "$@"; do
    case "$arg" in
        --import) IMPORT_ONLY=1 ;;
        --no-reset) RESET=0 ;;
    esac
done

if [ $RESET -eq 1 ] || [ ! -d "$VENV" ]; then
    echo "[ciFastLocal] fresh venv 생성: $VENV"
    rm -rf "$VENV" 2>/dev/null || true
    uv venv "$VENV" --python 3.12
fi

# Python 경로 — Windows/Unix 양쪽 지원
if [ -x "$VENV/Scripts/python.exe" ]; then
    PY="$VENV/Scripts/python.exe"
elif [ -x "$VENV/bin/python" ]; then
    PY="$VENV/bin/python"
else
    echo "[ciFastLocal] python 실행파일 못 찾음 ($VENV/Scripts 또는 $VENV/bin)"
    exit 1
fi

if [ $RESET -eq 1 ]; then
    echo "[ciFastLocal] dependency install (.github/workflows/ci-fast.yml test-fast 잡과 동일)"
    VIRTUAL_ENV="$(pwd)/$VENV" uv pip install --quiet \
        pytest pytest-asyncio pytest-cov hypothesis pytest-xdist pytest-benchmark
    VIRTUAL_ENV="$(pwd)/$VENV" uv pip install --quiet \
        "pandera[polars]>=0.29.0" "vcrpy>=6.0.0" "syrupy>=4.7.0"
    VIRTUAL_ENV="$(pwd)/$VENV" uv pip install --quiet -e ".[all]"
fi

echo "[ciFastLocal] import smoke — mcp.server / 핵심 모듈"
"$PY" -X utf8 -c "
import sys
try:
    from mcp.server.stdio import stdio_server  # noqa: F401
    print('  mcp.server.stdio: OK')
except Exception as e:
    print(f'  mcp.server.stdio: FAIL — {e}')
    sys.exit(1)
import dartlab
missing = [n for n in dartlab.__all__ if not hasattr(dartlab, n)]
assert not missing, f'dartlab public API 누락: {missing}'
print('  dartlab.__all__: OK')
from dartlab.mcp import createServer
createServer()
print('  dartlab.mcp.createServer: OK')
"

if [ $IMPORT_ONLY -eq 1 ]; then
    echo "[ciFastLocal] --import 모드 끝. exit 0."
    exit 0
fi

echo "[ciFastLocal] test-fast 잡 실행 (ci-fast.yml 과 동일 인자)"
export DARTLAB_DATA_DIR="$(pwd)/tests/fixtures"
export PYTEST_MEMORY_LIMIT_MB=1900
export DARTLAB_TEST_LOCKED=1
"$PY" -X utf8 -m pytest tests/ -n auto --dist loadfile --tb=short \
    -m "unit and not requires_data" \
    --ignore=tests/test_fixture_analysis_real.py \
    --ignore=tests/test_fixture_credit_real.py \
    --ignore=tests/test_fixture_story_real.py \
    --ignore=tests/realData \
    --benchmark-disable --no-cov
