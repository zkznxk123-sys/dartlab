"""Phase C-2 — ``BoundedCache`` 의 IPC mmap backing 회귀.

검증:
  1. ``_sections`` prefix + ``pl.DataFrame`` 값 set 시 IPC 파일 자동 생성.
  2. evict 후 다시 get 하면 mmap 으로 reload (RSS 절감).
  3. EMERGENCY clear 후에도 IPC 파일 잔존 → 다음 get 성공.
  4. ``_sections`` 외 prefix 는 IPC 영향 0 (기존 동작).
  5. DataFrame 아닌 값 (dict, tuple) 도 IPC 미적용 (호환 보존).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_sections_value_writes_ipc() -> None:
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)
    df = pl.DataFrame({"topic": ["a"], "value": [1.0]})

    cache["_sections"] = df

    ipcPath = cache._ipc_cache_dir / "_sections.arrow"
    assert ipcPath.exists(), f"IPC 파일 미생성: {ipcPath}"


def test_evicted_key_reloaded_from_ipc() -> None:
    """store dict 에서 manual delete 후 __getitem__ 이 mmap reload."""
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)
    df = pl.DataFrame({"topic": ["a", "b"], "value": [1.0, 2.0]})

    cache["_sections"] = df
    assert "_sections" in cache._store

    # 인위 evict — IPC 는 남음
    del cache._store["_sections"]
    assert "_sections" not in cache._store
    assert (cache._ipc_cache_dir / "_sections.arrow").exists()

    # __getitem__ 가 mmap reload
    reloaded = cache["_sections"]
    assert reloaded.height == 2
    assert reloaded.get_column("value").to_list() == [1.0, 2.0]


def test_emergency_clear_preserves_ipc() -> None:
    """EMERGENCY clear (store dict 비움) 후에도 IPC 잔존 → 재호출 성공."""
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)
    df = pl.DataFrame({"topic": ["a"], "value": [1.0]})
    cache["_sections"] = df

    # EMERGENCY simulate — store 전체 clear
    cache._store.clear()

    # IPC 통해 재진입
    assert "_sections" in cache
    reloaded = cache["_sections"]
    assert reloaded.equals(df)


def test_non_sections_prefix_no_ipc() -> None:
    """_sections 외 prefix 는 IPC 미생성 (기존 동작)."""
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)
    df = pl.DataFrame({"a": [1]})

    cache["_finance_q_CFS"] = df
    cache["_quant_ohlcv"] = df
    cache["_calcRoicTimeline"] = {"key": "value"}

    assert not (cache._ipc_cache_dir / "_finance_q_CFS.arrow").exists()
    assert not (cache._ipc_cache_dir / "_quant_ohlcv.arrow").exists()
    assert not (cache._ipc_cache_dir / "_calcRoicTimeline.arrow").exists()


def test_non_dataframe_value_no_ipc() -> None:
    """_sections prefix 라도 DataFrame 아닌 값은 IPC 미적용."""
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)

    cache["_sectionsMeta"] = {"period": "2024Q4"}  # dict, not DataFrame
    assert "_sectionsMeta" in cache._store
    assert not (cache._ipc_cache_dir / "_sectionsMeta.arrow").exists()


def test_missing_key_raises_after_no_ipc() -> None:
    """IPC 도 없고 store 에도 없으면 KeyError."""
    from dartlab.core.memory import BoundedCache

    cache = BoundedCache(maxEntries=10)
    with pytest.raises(KeyError):
        _ = cache["_sections"]
