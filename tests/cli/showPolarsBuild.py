"""M7: Polars 빌드 정보 캡처 — allocator (mimalloc/jemalloc/system) 실측.

Windows mimalloc 이 Polars wheel 기본인지 확인.
결과는 stdout 으로 출력 — 별도 markdown 산출물 안 만듦 (md 작성 금지 룰).

사용:
    uv run python -X utf8 tests/cli/showPolarsBuild.py

산출:
    - polars.show_versions() 본문
    - platform / python / cpu count
    - POLARS_MAX_THREADS / POLARS_ALLOCATOR 환경변수
    - mimalloc 추정 hint (Polars 1.0+ default)
"""

from __future__ import annotations

import os
import platform
import sys


def main() -> int:
    """Polars/플랫폼 빌드 정보를 stdout 으로 출력.

    Returns:
        exit code (0 = 성공, 1 = polars import 실패).

    Raises:
        없음 (예외는 stderr 로 catch + return 1).

    Example:
        >>> main()
    """
    try:
        import polars as pl
    except ImportError as e:
        print(f"[showPolarsBuild] polars import 실패: {e}", file=sys.stderr)
        return 1

    print("=" * 60)
    print("Polars 빌드 정보 (M7)")
    print("=" * 60)
    print(f"polars version : {pl.__version__}")
    print(f"python version : {sys.version.split()[0]}")
    print(f"platform       : {platform.platform()}")
    print(f"machine        : {platform.machine()}")
    print(f"cpu count      : {os.cpu_count()}")
    print()

    print("환경변수:")
    for name in ("POLARS_MAX_THREADS", "POLARS_ALLOCATOR", "POLARS_FORCE_OOC", "POLARS_STREAMING_CHUNK_SIZE"):
        print(f"  {name}={os.environ.get(name, '<unset>')}")
    print()

    print("polars.thread_pool_size:", pl.thread_pool_size())
    print()

    # show_versions — Polars 가 dependency 빌드 정보 출력 (allocator 포함 안 될 수 있음)
    print("polars.show_versions() ↓")
    print("-" * 60)
    try:
        pl.show_versions()
    except (AttributeError, Exception) as e:  # noqa: BLE001
        print(f"  show_versions 실패: {e}")
    print("-" * 60)
    print()

    # Allocator hint — Polars 1.0+ wheel 은 mimalloc 기본. show_versions 가
    # allocator 명시 안 하면 직접 확인 어렵다. POLARS_ALLOCATOR 환경변수가
    # 명시되면 그게 우선.
    allocator = os.environ.get("POLARS_ALLOCATOR")
    if allocator:
        print(f"Allocator (env 명시): {allocator}")
    else:
        print("Allocator (env 미명시): Polars 1.0+ 기본 mimalloc 추정 (Windows/Linux/Mac).")
        print("  → jemalloc fallback 검토 필요 시 wheel 빌드 옵션 또는")
        print("    POLARS_ALLOCATOR=jemalloc 환경변수 (Polars 가 지원하는 경우만).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
