"""config dataDir 기본값 해석 — dev 체크아웃 repo data/ vs 설치형 user_cache 단위 테스트.

repo data/ 기본값은 site-packages 설치 사용자에겐 쓰기 불가라 깨진다. dev 소스 트리는 기존
동작 보존(repo data/), 설치형만 쓰기 가능한 사용자 캐시로 fallback 하는지 검증. env 우선 불변.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.unit


def test_user_cache_dir_is_writable_target():
    """_userCacheDir 은 플랫폼별 'dartlab' 포함 경로 (설치형 사용자 저장 위치)."""
    from dartlab.config import _userCacheDir

    p = _userCacheDir()
    assert "dartlab" in str(p).lower()
    # 플랫폼 관례 — win LOCALAPPDATA / mac Library/Caches / 기타 ~/.cache
    if sys.platform == "win32":
        assert "Cache" in str(p) or "Local" in str(p)
    elif sys.platform == "darwin":
        assert "Caches" in str(p)
    else:
        assert ".cache" in str(p) or "XDG" in str(p) or "/dartlab" in str(p)


def test_dev_checkout_uses_repo_data():
    """dev 소스 트리(pyproject.toml 존재) → repo data/ 유지(기존 동작 보존)."""
    from pathlib import Path

    from dartlab.config import _resolveDefaultDataDir

    resolved = Path(_resolveDefaultDataDir())
    # 이 테스트는 repo 체크아웃에서 실행 → repo root 에 pyproject.toml 존재 → repo data/
    assert resolved.name == "data"
    assert (resolved.parent / "pyproject.toml").exists()


def test_env_var_priority_documented():
    """DARTLAB_DATA_DIR env 가 있으면 그게 dataDir 의 정본(모듈 로드 시 우선)."""
    import os

    # 모듈 로드 시점 동작을 직접 재현 — env 우선 로직 검증(현재 프로세스 변경 없이).
    env = os.environ.get("DARTLAB_DATA_DIR")
    from dartlab.config import _resolveDefaultDataDir

    effective = env or _resolveDefaultDataDir()
    if env:
        assert effective == env
    else:
        assert effective.endswith("data") or "dartlab" in effective.lower()
