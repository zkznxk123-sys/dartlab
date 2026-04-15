"""프로세스 메모리 모니터링 + 메모리 압박 감지 LRU 캐시.

⚠ Polars는 네이티브 Rust 힙을 사용하므로 Python gc.collect()로 회수 불가.
   Company 1개 로드 ≈ 200~500MB, 3개 이상 동시 로드 시 OOM 위험.
   BoundedCache + check_memory_and_gc()로 방어.
"""

from __future__ import annotations

import functools
import gc
import logging
import os
from collections import OrderedDict
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable)

log = logging.getLogger(__name__)

# ── 메모리 임계값 (MB) ──
# Polars 네이티브 메모리 포함, 단일 프로세스 기준
PRESSURE_WARNING_MB = 800.0  # 경고: 캐시 절반 축소
PRESSURE_CRITICAL_MB = 1500.0  # 위험: 캐시 1/4 축소 + GC
PRESSURE_FATAL_MB = 1900.0  # 치명: 캐시 전체 비우기 + GC


def get_memory_mb() -> float:
    """현재 프로세스 RSS(Resident Set Size)를 MB로 반환.

    Polars Rust 힙을 포함한 실제 물리 메모리 사용량.
    psutil 없이 OS API 직접 사용.
    """
    try:
        import ctypes
        import ctypes.wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess  # type: ignore[attr-defined]
        GetCurrentProcess.restype = ctypes.wintypes.HANDLE

        GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined]
        GetProcessMemoryInfo.argtypes = [
            ctypes.wintypes.HANDLE,
            ctypes.POINTER(PMC),
            ctypes.wintypes.DWORD,
        ]
        GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL

        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        if GetProcessMemoryInfo(GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
            return pmc.WorkingSetSize / (1024 * 1024)
    except (AttributeError, OSError, ImportError):
        pass

    # Linux/macOS fallback
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024  # kB → MB
    except (FileNotFoundError, PermissionError):
        pass

    return -1.0


def _get_total_memory_mb() -> float:
    """시스템 전체 물리 메모리(MB)."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullTotalPhys / (1024 * 1024)
    except (AttributeError, OSError):
        pass

    # Linux fallback
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024
    except (FileNotFoundError, PermissionError):
        pass

    return -1.0


def check_memory_and_gc(label: str = "") -> float:
    """현재 메모리 확인 + 위험 시 GC 강제 실행. RSS(MB) 반환.

    테스트/데이터 로드 전후에 호출하여 OOM 사전 방지.
    """
    mem = get_memory_mb()
    if mem <= 0:
        return mem
    if mem > PRESSURE_FATAL_MB:
        log.warning("[memory] FATAL %s: %.0fMB > %.0fMB — full GC", label, mem, PRESSURE_FATAL_MB)
        gc.collect()
        mem = get_memory_mb()
    elif mem > PRESSURE_CRITICAL_MB:
        log.warning("[memory] CRITICAL %s: %.0fMB > %.0fMB — GC", label, mem, PRESSURE_CRITICAL_MB)
        gc.collect()
        mem = get_memory_mb()
    elif mem > PRESSURE_WARNING_MB:
        log.debug("[memory] WARNING %s: %.0fMB > %.0fMB", label, mem, PRESSURE_WARNING_MB)
    return mem


class BoundedCache:
    """메모리 압박 감지 LRU 캐시 (thread-safe + pinned 키 보호).

    dict와 동일한 인터페이스(`in`, `[]`, `[]=`)를 제공하되,
    max_entries 초과 시 가장 오래된 항목을 제거하고
    주기적으로 프로세스 RSS를 체크하여 메모리 압박 시 용량을 축소한다.

    [thread-safety] threading.RLock으로 모든 mutation 보호.
    review/buildBlocks의 ThreadPoolExecutor 병렬 호출 안전.

    [pinned] 외부 API 결과(_quant_ohlcv, _quant_benchmark 등)는 evict 면제.
    작은 dict이고 재로드 비용이 크므로 메모리 압박 시에도 보존.

    ⚠ pressure_mb 기본값 800MB — Polars Company 2개 수준에서 이미 경고.
    """

    __slots__ = ("_store", "_max", "_default_max", "_pressure_mb", "_put_count", "_lock", "_pinned_prefixes")

    def __init__(self, max_entries: int = 30, pressure_mb: float = 800.0):
        import threading

        self._store: OrderedDict[str, Any] = OrderedDict()
        self._max = max_entries
        self._default_max = max_entries
        self._pressure_mb = pressure_mb
        self._put_count = 0
        self._lock = threading.RLock()
        # pinned: 이 prefix로 시작하는 키는 evict하지 않음 (외부 API + 무거운 계산 결과 보호)
        # review에서 여러 calc가 공유하는 핵심 캐시. 작은 dict이고 재로드 비용 큼.
        self._pinned_prefixes: tuple[str, ...] = (
            # Accessor (dualAccess wrapper — 재생성 로직이 없음, 반드시 보호)
            # Phase 4 G11: 대형 기업 (한국전력 등) 에서 메모리 압박 시
            # _check_pressure() 가 accessor 까지 삭제 → 다음 select/show 에서 KeyError
            "_showAccessor",
            "_selectAccessor",
            "_reviewAccessor",
            "_creditAccessor",
            "_analysisAccessor",
            # 외부 API / 데이터 로드
            "_quant_ohlcv",
            "_quant_benchmark",
            "_priceContext",
            "_diffResult",
            "_peerRanking",
            "_estimateWacc",
            "_estimateWacc_v2",
            "_fetchBeta",
            # finance series builders — 매우 무거운 parquet load + pivot
            # evict 시 14축 calc 가 매번 finance 를 다시 빌드해서 메모리 폭발
            "_finance_",
            "_financeStmt_",
            "_financeCisQuarterly",
            "_sceDataFrame",
            "_ratios_",
            "_insights_analyze",
            # 무거운 calc 결과 (review 안 다중 호출)
            "_calcMarketBeta",
            "_calcTechnicalVerdict",
            "_calcTechnicalSignals",
            "_calcMarketRisk",
            "_calcMarketAnalysisFlags",
            "_calcFundamentalDivergence",
            "_calcRoicTimeline",
            "_calcCreditMetrics",
            "_calcCreditScore",
            "_calcScorecard",
            "_calcPeerRanking",
            "_calcDisclosureChangeSummary",
            "_calcKeyTopicChanges",
        )

    def _is_pinned(self, key: str) -> bool:
        return any(key.startswith(p) for p in self._pinned_prefixes)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            self._store.move_to_end(key)
            return self._store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = value
                return
            self._store[key] = value
            self._put_count += 1
            if self._put_count % 5 == 0:
                self._check_pressure()
            # LRU evict — pinned 키는 건너뜀
            while len(self._store) > self._max:
                # 가장 오래된 unpinned 키 찾기
                evicted = False
                for k in list(self._store.keys()):
                    if not self._is_pinned(k):
                        del self._store[k]
                        evicted = True
                        break
                if not evicted:
                    break  # 모두 pinned면 그냥 초과 허용

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def _check_pressure(self) -> None:
        # caller already holds _lock (called from __setitem__)
        mem = get_memory_mb()
        if mem <= 0:
            return
        if mem > PRESSURE_FATAL_MB:
            # 치명: pinned 제외 모두 비우기
            log.warning("[BoundedCache] FATAL: %.0fMB — clearing unpinned entries", mem)
            for k in list(self._store.keys()):
                if not self._is_pinned(k):
                    del self._store[k]
            self._max = max(self._default_max // 4, 2)
            gc.collect()
        elif mem > PRESSURE_CRITICAL_MB:
            self._max = max(self._default_max // 4, 5)
            self._evict()
            gc.collect()
        elif mem > PRESSURE_WARNING_MB:
            self._max = max(self._default_max // 2, 10)
            self._evict()
        else:
            self._max = self._default_max

    def _evict(self) -> None:
        # caller already holds _lock — pinned 키 건너뜀
        while len(self._store) > self._max:
            evicted = False
            for k in list(self._store.keys()):
                if not self._is_pinned(k):
                    del self._store[k]
                    evicted = True
                    break
            if not evicted:
                break  # 모두 pinned면 초과 허용

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._max = self._default_max
            self._put_count = 0

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                return self._store[key]
            return default

    def __del__(self) -> None:
        try:
            self._store.clear()
        except (AttributeError, TypeError):
            pass


def memory_guard(threshold_pct: float = 60) -> Callable[[F], F]:
    """메모리 사용률이 threshold_pct 초과 시 GC 강제 실행하는 데코레이터.

    Usage::

        @memory_guard(threshold_pct=60)
        def heavy_computation():
            ...
    """
    total = _get_total_memory_mb()

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if total > 0:
                current = get_memory_mb()
                if current > 0 and (current / total * 100) > threshold_pct:
                    gc.collect()
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


# ── calc 함수 메모이제이션 ──


def memoized_calc(fn: Callable[..., Any]) -> Callable[..., Any]:
    """calc 함수 결과를 Company._cache에 메모이제이션.

    analysis/credit/quant의 calc 함수가 공통으로 사용.
    key: ``_{함수명}:{basePeriod}``
    Company._cache(BoundedCache)가 없으면 캐시 없이 실행.
    결과가 None이면 캐시하지 않는다.

    overrides 가 전달되면 **캐시 skip** + override 그대로 통과 — 같은 가정
    재실행 시 캐시가 오래된 값을 돌려주는 사고 방지.
    """
    import inspect

    params = inspect.signature(fn).parameters
    _has_base_period = "basePeriod" in params
    _has_overrides = "overrides" in params

    @functools.wraps(fn)
    def wrapper(
        company: Any,
        *,
        basePeriod: str | None = None,
        overrides: dict | None = None,
    ) -> Any:
        kw: dict[str, Any] = {}
        if _has_base_period:
            kw["basePeriod"] = basePeriod
        if _has_overrides and overrides:
            kw["overrides"] = overrides

        # override 적용 시 캐시 우회 (값이 달라지므로)
        useCache = not overrides
        cache = getattr(company, "_cache", None) if useCache else None
        key = f"_{fn.__name__}:{basePeriod}"

        if cache is not None and key in cache:
            return cache[key]

        result = fn(company, **kw)

        if cache is not None and result is not None:
            cache[key] = result

        return result

    return wrapper
