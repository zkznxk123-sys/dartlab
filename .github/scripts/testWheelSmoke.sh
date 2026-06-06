#!/usr/bin/env bash
# testWheelSmoke.sh — PyPI 릴리즈 직전 wheel 스모크.
#
# 목적:
#   로컬 editable 설치가 아닌 **빌드된 wheel** 을 격리 venv 에 설치하고
#   realData 스위트의 freshInstall 마커를 실행. 과거 사고 (Company.panel 크래시)
#   처럼 "소스는 멀쩡한데 wheel 만 깨지는" schema-drift/packaging 누락을 잡는다.
#
# 사용법:
#   bash .github/scripts/testWheelSmoke.sh                   # 현재 소스로 wheel 빌드 후 테스트
#   bash .github/scripts/testWheelSmoke.sh dist/dartlab-*.whl  # 특정 wheel 지정
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
# `python -m build` 를 uv 로 실행 — publish.yml 과 동일한 빌드 경로로 맞춤.
# 과거 사고 (2026-04-19): `uv build` 로 wheel-smoke 검증은 통과했으나
# publish.yml 의 `python -m build` 가 다른 wheel 을 생산해 PyPI 에 깨진 wheel
# 업로드. build frontend 은 유지하고, 의존성 설치/격리는 uv 로 통일한다.
if [ -z "$WHEEL_PATH" ]; then
    echo "[wheel-smoke] wheel 빌드 (uv run python -m build)..."
    mkdir -p "$WORK_DIR/dist"
    uv run --with build python -m build --wheel --outdir "$WORK_DIR/dist" "$REPO_ROOT"
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
# loadSections() {} → chapterFromMajorNum() 모두 None → panel topic rows 0개 →
# Company.panel 외부 사용자 첫 호출 크래시. 재발 방지 필수 게이트.
echo "[wheel-smoke] 번들 리소스 검증..."
export PYTHONIOENCODING=utf-8
"$VENV_PYTHON" -X utf8 -c "
import importlib.util
import pathlib
spec = importlib.util.find_spec('dartlab')
root = pathlib.Path(spec.submodule_search_locations[0])
# 필수 디렉토리 (없으면 panel topic 라우팅이 silent-fail)
mustHaveDirs = [
    'providers/mappers/mapperData/parserMappings',
    'reference/data',
]
# 필수 JSON (silent-fail 의 근원 파일들)
mustHaveFiles = [
    'providers/mappers/mapperData/parserMappings/panelTopics.json',
    'providers/mappers/mapperData/parserMappings/affiliate.json',
    'providers/mappers/mapperData/parserMappings/costByNature.json',
    'reference/data/accountMappings.json',
]
missing = [p for p in mustHaveDirs + mustHaveFiles if not (root / p).exists()]
if missing:
    raise SystemExit(f'wheel 번들 누락 (2026-04-19 사고 재현): {missing}')

# panel topic 런타임 실제 로드 검증 — silent-fail 경로가 살아있는지
from dartlab.providers.mappers.parserMapper import loadSections
sec = loadSections()
if not sec.get('chapterByMajor'):
    raise SystemExit(
        'loadSections()[\"chapterByMajor\"] 비어있음 — panel topic 라우팅 전부 무력화 상태. '
        'wheel 에 panelTopics.json 이 있어도 내용이 깨졌음.'
    )
print('[wheel-smoke] 번들 OK — parserMappings + panelTopics.chapterByMajor 정상')
"

# 4. 제품 스모크 — 배포될 wheel 을 fixture 데이터로 사용자 대표 API 실행.
#    외부 HF/PyPI empty 경로는 nightly external-venv-smoke 가 별도로 맡는다.
echo "[wheel-smoke] product smoke release 실행 (fixture 데이터)..."
"$VENV_PYTHON" -X utf8 "$REPO_ROOT/tests/audit/productSmoke.py" \
    --suite release \
    --data-mode fixtures \
    --import-mode installed \
    --json-out "$WORK_DIR/product-smoke-release.json"
EXIT_CODE=$?

echo "[wheel-smoke] 완료 (exit=$EXIT_CODE)"
exit $EXIT_CODE
