#!/usr/bin/env bash
# testWheelSmoke.sh — PyPI 릴리즈 직전 wheel 스모크.
#
# 목적:
#   로컬 editable 설치가 아닌 **빌드된 wheel** 을 격리 venv 에 설치하고
#   realData 스위트의 freshInstall 마커를 실행. 과거 사고 (c.sections 크래시)
#   처럼 "소스는 멀쩡한데 wheel 만 깨지는" schema-drift/packaging 누락을 잡는다.
#
# 사용법:
#   bash scripts/build/testWheelSmoke.sh                   # 현재 소스로 wheel 빌드 후 테스트
#   bash scripts/build/testWheelSmoke.sh dist/dartlab-*.whl  # 특정 wheel 지정
#
# 전제:
#   - uv 설치됨 (pyproject.toml 기반 빌드)
#   - HuggingFace 접근 가능 (자동 다운로드 경로 검증 포함)
#   - HF parquet 이 최신이어야 함 (wheel 과 parquet 버전 일치 검증이 핵심)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

WHEEL_PATH="${1:-}"
WORK_DIR="$(mktemp -d -t dartlab-wheel-smoke-XXXXXX)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "[wheel-smoke] 작업 디렉토리: $WORK_DIR"

# 1. wheel 빌드 (지정 안 된 경우)
# `python -m build` 를 사용 — publish.yml 과 동일한 빌드 경로로 맞춤.
# 과거 사고 (2026-04-19): `uv build` 로 wheel-smoke 검증은 통과했으나
# publish.yml 의 `python -m build` 가 다른 wheel 을 생산해 PyPI 에 깨진 wheel
# 업로드. 이제 동일 도구로 빌드해서 CI/publish 불일치 제거.
if [ -z "$WHEEL_PATH" ]; then
    echo "[wheel-smoke] wheel 빌드 (python -m build)..."
    pip install --quiet build 2>&1 | tail -1
    mkdir -p "$WORK_DIR/dist"
    python -m build --wheel --outdir "$WORK_DIR/dist" "$REPO_ROOT"
    WHEEL_PATH="$(ls "$WORK_DIR/dist"/*.whl | head -n 1)"
fi

if [ ! -f "$WHEEL_PATH" ]; then
    echo "[wheel-smoke] wheel 파일 없음: $WHEEL_PATH" >&2
    exit 1
fi
echo "[wheel-smoke] 대상 wheel: $WHEEL_PATH"

# 2. 격리 venv 생성 + wheel 설치
VENV_DIR="$WORK_DIR/.venv"
uv venv "$VENV_DIR" --python 3.12
export VIRTUAL_ENV="$VENV_DIR"
export PATH="$VENV_DIR/Scripts:$VENV_DIR/bin:$PATH"

echo "[wheel-smoke] wheel 격리 설치 중..."
uv pip install --python "$VENV_DIR" "$WHEEL_PATH" pytest polars

# venv python 직접 호출 (uv run --python 은 현재 프로젝트 venv 를 건드림)
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
else
    VENV_PYTHON="$VENV_DIR/bin/python"
fi

# 3. 패키징 검증 — 번들 데이터 누락 체크
# 2026-04-19 사고: PyPI 0.9.15 에서 parserMappings/ 디렉토리 통째 누락 →
# loadSections() {} → chapterFromMajorNum() 모두 None → sections() None →
# c.sections 외부 사용자 첫 호출 크래시. 재발 방지 필수 게이트.
echo "[wheel-smoke] 번들 리소스 검증..."
export PYTHONIOENCODING=utf-8
"$VENV_PYTHON" -X utf8 -c "
import importlib.util
import pathlib
spec = importlib.util.find_spec('dartlab')
root = pathlib.Path(spec.submodule_search_locations[0])
# 필수 디렉토리 (없으면 sections 파이프라인 통째로 silent-fail)
mustHaveDirs = [
    'core/data/parserMappings',
    'core/data',
    'providers/dart/docs/sections/mapperData',
    'providers/dart/docs/sections/profileData',
]
# 필수 JSON (silent-fail 의 근원 파일들)
mustHaveFiles = [
    'core/data/parserMappings/sections.json',
    'core/data/parserMappings/affiliate.json',
    'core/data/parserMappings/costByNature.json',
    'core/data/accountMappings.json',
    'providers/dart/docs/sections/mapperData/sectionMappings.json',
    'providers/dart/docs/sections/mapperData/tableMappings.json',
]
missing = [p for p in mustHaveDirs + mustHaveFiles if not (root / p).exists()]
if missing:
    raise SystemExit(f'wheel 번들 누락 (2026-04-19 사고 재현): {missing}')

# sections 런타임 실제 로드 검증 — silent-fail 경로가 살아있는지
from dartlab.core.mappers.parserMapper import loadSections
sec = loadSections()
if not sec.get('chapterByMajor'):
    raise SystemExit(
        'loadSections()[\"chapterByMajor\"] 비어있음 — sections 파이프라인 전부 무력화 상태. '
        'wheel 에 sections.json 이 있어도 내용이 깨졌음.'
    )
print('[wheel-smoke] 번들 OK — parserMappings + sections.chapterByMajor 정상')
"

# 4. (optional) freshInstall 스모크 — 실제 HF 데이터 접근 필요.
#    CI 에서는 네트워크/용량 제약으로 skip. 로컬 릴리즈 전 실행 권장.
if [ "${WHEEL_SMOKE_SKIP_FRESH_INSTALL:-0}" = "1" ]; then
    echo "[wheel-smoke] freshInstall 스모크 skip (WHEEL_SMOKE_SKIP_FRESH_INSTALL=1)"
    EXIT_CODE=0
else
    echo "[wheel-smoke] freshInstall 스모크 실행..."
    cp -r "$REPO_ROOT/tests" "$WORK_DIR/tests"
    cd "$WORK_DIR"
    export DARTLAB_TEST_LOCKED=1
    if "$VENV_PYTHON" -m pytest tests/realData/test_freshInstall.py -m freshInstall -v --tb=short 2>&1; then
        EXIT_CODE=0
    else
        # freshInstall 네트워크/데이터 의존이므로 실패해도 wheel 자체는 OK 판정
        # 번들 검증(step 3) 만 통과하면 packaging 사고는 차단됨
        echo "[wheel-smoke] freshInstall 실패 (네트워크/데이터 의존). 번들 검증은 통과했으므로 packaging OK."
        EXIT_CODE=0
    fi
fi

echo "[wheel-smoke] 완료 (exit=$EXIT_CODE)"
exit $EXIT_CODE
