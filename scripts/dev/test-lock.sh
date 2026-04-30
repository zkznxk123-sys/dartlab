#!/usr/bin/env bash
# test-lock.sh — pytest를 세션 간 직렬화하는 wrapper
# 사용법: bash scripts/test-lock.sh tests/ -v
#
# mkdir은 atomic 연산이므로 flock 없는 Windows bash에서도 동작한다.
# 다른 세션이 테스트 중이면 최대 300초 대기 후 타임아웃.
# PID 파일로 stale lock 자동 감지.

LOCK_DIR="/tmp/dartlab-test.lock"
PID_FILE="$LOCK_DIR/pid"
MAX_WAIT=300
WAIT=0

cleanup() {
    rm -rf "$LOCK_DIR" 2>/dev/null
}

# stale lock 감지: lock 폴더 있고 PID 파일의 프로세스가 죽었으면 제거
check_stale() {
    if [ -d "$LOCK_DIR" ] && [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$OLD_PID" ] && ! kill -0 "$OLD_PID" 2>/dev/null; then
            echo "[test-lock] stale lock 감지 (PID $OLD_PID 종료됨). 자동 해제."
            rm -rf "$LOCK_DIR" 2>/dev/null
        fi
    fi
}

# 첫 시도 전 stale lock 확인
check_stale

# 대기 루프: lock 획득까지 3초 간격으로 재시도
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    if [ $WAIT -ge $MAX_WAIT ]; then
        echo "[test-lock] 다른 세션이 테스트 중 — ${MAX_WAIT}초 대기 초과. 포기합니다."
        echo "[test-lock] 수동 해제: rm -rf $LOCK_DIR"
        exit 1
    fi
    # 매 시도마다 stale lock 재확인
    check_stale
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        break
    fi
    echo "[test-lock] 다른 세션이 테스트 중... 대기 (${WAIT}/${MAX_WAIT}s)"
    sleep 3
    WAIT=$((WAIT + 3))
done

# lock 획득 성공 — PID 기록 + 종료 시 반드시 해제
echo $$ > "$PID_FILE"
trap cleanup EXIT INT TERM

echo "[test-lock] lock 획득 (PID $$). pytest 시작."
export DARTLAB_TEST_LOCKED=1
# repo venv가 있으면 우선 사용한다. Windows bash에서 `uv run`을 먼저 타면
# pytest 쪽 환경변수 감지가 깨지는 경우가 있어 lock 경고가 잘못 출력된다.
if [ -x ".venv/Scripts/python.exe" ]; then
    DARTLAB_TEST_LOCKED=1 .venv/Scripts/python.exe -X utf8 -m pytest "$@"
elif [ -x ".venv/bin/python" ]; then
    DARTLAB_TEST_LOCKED=1 .venv/bin/python -X utf8 -m pytest "$@"
elif command -v uv >/dev/null 2>&1; then
    DARTLAB_TEST_LOCKED=1 uv run pytest "$@"
else
    DARTLAB_TEST_LOCKED=1 python -X utf8 -m pytest "$@"
fi
EXIT_CODE=$?

echo "[test-lock] pytest 완료 (exit=$EXIT_CODE). lock 해제."
exit $EXIT_CODE
