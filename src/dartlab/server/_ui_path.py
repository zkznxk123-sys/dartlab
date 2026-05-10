"""UI 빌드 경로 해석 — web.py와 cli/commands/ai.py가 공유한다.

우선순위:
1. DARTLAB_UI_DIR 환경변수 (dartlab-desktop이 설정)
2. 패키지 내부: site-packages/dartlab/ui/build/ (pip install)
3. 개발 환경: project_root/ui/web/client/dist/ (LibreChat-derived web)
4. 과거 개발 환경: project_root/ui/web/build/
"""

from __future__ import annotations

import os
from pathlib import Path

# dartlab 패키지 루트: site-packages/dartlab/ 또는 src/dartlab/
_PKG_ROOT = Path(__file__).resolve().parent.parent


def resolveUiBuildDir() -> Path:
    """UI 빌드 결과물(index.html, assets/) 디렉토리를 반환한다."""
    # 1. 환경변수 — dartlab-desktop 등 외부 소비자가 명시
    if env := os.environ.get("DARTLAB_UI_DIR"):
        return Path(env)

    # 2. 패키지 내부 (pip install 환경)
    #    site-packages/dartlab/ui/build/
    pip_build = _PKG_ROOT / "ui" / "build"
    if pip_build.is_dir():
        return pip_build

    # 3. 개발 환경 (editable install)
    #    project_root/ui/web/client/dist/ (LibreChat-derived React app)
    repo_root = _PKG_ROOT.parent.parent
    librechat_build = repo_root / "ui" / "web" / "client" / "dist"
    if librechat_build.is_dir():
        return librechat_build

    # 4. 과거 개발 환경
    #    project_root/ui/web/build/
    return repo_root / "ui" / "web" / "build"


def resolveUiSourceDir() -> Path:
    """UI 소스 디렉토리를 반환한다 (dev 모드 npm 명령용)."""
    if env := os.environ.get("DARTLAB_UI_DIR"):
        return Path(env)

    return _PKG_ROOT.parent.parent / "ui" / "web"
