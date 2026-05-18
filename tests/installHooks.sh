#!/usr/bin/env bash
# dartlab git hooks 활성화 — 한 줄 실행.
#
# 사용:   bash tests/installHooks.sh
# 비활성: git config --unset core.hooksPath
#
# 동작:
#   core.hooksPath = tests/hooks 로 git 설정. push 전 tests/hooks/pre-push 가
#   tests/run.py preflight 를 돌려 CI Fast 차단 12 게이트 로컬 통과 강제.
#   .git/hooks 는 추적 안 되므로 추적 가능한 tests/hooks 를 hooksPath 로 사용.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath tests/hooks
chmod +x tests/hooks/pre-push 2>/dev/null || true

echo "[installHooks] core.hooksPath = tests/hooks 설정 완료"
echo "[installHooks] 활성 hook: pre-push (CI Fast 차단 12 게이트 preflight)"
echo ""
echo "  비활성화:    git config --unset core.hooksPath"
echo "  일회 우회:   DARTLAB_SKIP_PREPUSH=1 git push"
