"""UI 빌드 경로 해석 — web.py와 cli/commands/ai.py가 공유한다.

기본 UI = ui/apps/local (SvelteKit 챗·터미널 셸, 단계-10 전환). 옛 ui/web(React) 는
DARTLAB_UI_LEGACY=1 로 명시 fallback 한다(가역, 한 줄 escape).

pip wheel 번들(publish.yml → site-packages/dartlab/ui/build/)은 provider 설정 배선(단계-5-3)
완료·패리티 확인 후 ui/apps/local 로 전환한다 — 그 전까지 번들 UI 는 옛 React UI 다. dev 체크아웃은
이미 svelte 로 전환(아래 4번)되어 `dartlab ai` 가 로컬 SvelteKit 앱을 서빙한다.

resolveUiBuildDir 우선순위:
1. DARTLAB_UI_DIR 환경변수 (dartlab-desktop 등 외부 소비자가 명시)
2. DARTLAB_UI_LEGACY=1 → 옛 React UI(ui/web) 명시 요청 (가역 escape)
3. 패키지 내부: site-packages/dartlab/ui/build/ (pip install — wheel 번들)
4. 개발 환경: project_root/ui/apps/local/build/ (SvelteKit adapter-static)
5. 개발 fallback: project_root/ui/web/build → ui/web/client/dist (svelte build 부재 시)
"""

from __future__ import annotations

import os
from pathlib import Path

# dartlab 패키지 루트: site-packages/dartlab/ 또는 src/dartlab/
_PKG_ROOT = Path(__file__).resolve().parent.parent


def _repoRoot() -> Path:
    """editable/dev 체크아웃의 repo 루트 (src/dartlab/server/_ui_path.py → repo)."""
    return _PKG_ROOT.parent.parent


def _legacyWebBuild() -> Path:
    """옛 React UI(ui/web) 빌드 디렉토리 — DARTLAB_UI_LEGACY 및 dev fallback 공용."""
    repo_root = _repoRoot()
    web_build = repo_root / "ui" / "web" / "build"
    if web_build.is_dir():
        return web_build
    # 과거 LibreChat-derived 산출물
    return repo_root / "ui" / "web" / "client" / "dist"


def resolveUiBuildDir() -> Path:
    """UI 빌드 결과물(index.html, assets/) 디렉토리를 반환한다."""
    # 1. 환경변수 — dartlab-desktop 등 외부 소비자가 명시
    if env := os.environ.get("DARTLAB_UI_DIR"):
        return Path(env)

    # 2. 가역 escape — 옛 React UI(ui/web) 명시 요청
    if os.environ.get("DARTLAB_UI_LEGACY"):
        return _legacyWebBuild()

    # 3. 패키지 내부 (pip install 환경) — site-packages/dartlab/ui/build/
    pip_build = _PKG_ROOT / "ui" / "build"
    if pip_build.is_dir():
        return pip_build

    # 4. 개발 환경 — SvelteKit 로컬 앱 (adapter-static build)
    local_build = _repoRoot() / "ui" / "apps" / "local" / "build"
    if local_build.is_dir():
        return local_build

    # 5. 개발 fallback — 옛 React UI 빌드 (svelte build 미존재 시)
    return _legacyWebBuild()


def resolveUiSourceDir() -> Path:
    """UI 소스 디렉토리를 반환한다 (dev 모드 npm 명령용)."""
    if env := os.environ.get("DARTLAB_UI_DIR"):
        return Path(env)
    if os.environ.get("DARTLAB_UI_LEGACY"):
        return _repoRoot() / "ui" / "web"
    return _repoRoot() / "ui" / "apps" / "local"
