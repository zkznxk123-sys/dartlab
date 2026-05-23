"""mmap 된 suffix array 검색 — RAM 사용 0 으로 µs~ms 검색 가능한지 검증.

목적
----
fmIndexBench 의 SA 가 텍스트 4× RAM 의 단점이 *disk 로 옮기면 사라지는지* 검증.
np.memmap 으로 SA 를 디스크 상주 → OS 페이지 캐시가 알아서 띄움.

방법
----
1. fmIndexBench 의 build artifacts (text.bin, sa.npy, offsets.npy) 재사용
2. np.load(mmap_mode='r') 로 SA 로드
3. pydivsufsort.sa_search 가 readonly array 거부 → 직접 binary search 구현
4. cold/warm 측정

결과 (2026-05-20, 1.5 GB 텍스트, SA on disk = 6 GB)
---------------------------------------------------
RAM:
- before load: 54.9 MB
- after mmap load: 54.9 MB (+436 KB)
- after 7 쿼리: 57.5 MB (delta 2.7 MB)
→ **RAM 거의 0 — mmap 작동 확인**

검색 시간 (binary search 2회 = lower bound + upper bound):
| 쿼리 | occ | cold (µs) | warm (µs) | sample sections |
|---|---|---|---|---|
| 유상증자 | 16,552 | 371 | 43 | [318, 322, 1266] |
| HBM | 395 | 216 | 25 | [17782, 17784, 20354] |
| 대표이사 변경 | 646 | 173 | 24 | [197, 214, 7241] |
| 자기주식취득 | 1,989 | 166 | 23 | [30003, 30007, 38911] |
| 환율 변동 | 3,273 | 141 | 21 | [6043, 6046, 11514] |
| 최대주주변경 | 236 | 138 | 22 | [219, 221, 11415] |
| 전환사채 | 38,622 | 148 | 21 | [4995, 10535, 5000] |

빌드: 178 초 (1 일치 1.5 GB).
디스크: text 1.5 GB + SA 6 GB = 7.5 GB (= text 5×).

결론
----
- ★ RAM 0 — 페이지 캐시가 자동 hot
- ★ warm 검색 ~20-40 µs — naive (600-1300 ms) 대비 ~30000× 빠름
- ★ vector 의 "메모리 두 배" 약점 해결 — *디스크는 RAM 보다 50× 싸다*
- 디스크 5× 텍스트 비용은 NVMe SSD 시대에 거의 무료

다음 단계
--------
- 의미 검색 안 됨 (substring 만) — riVsa* 트랙으로 의미 layer 추가
- 압축 FM-index (sdsl-lite) 까지 가면 디스크도 0.4× 가능 — 지금은 필요 없음
"""

from __future__ import annotations

import gc
import os
import time
from pathlib import Path

import numpy as np
import polars as pl
from pydivsufsort import divsufsort


def sa_search_manual(text, sa: np.ndarray, q: bytes) -> tuple[int, int]:
    """suffix array 에서 q 가 prefix 인 suffix 범위 찾기 — 표준 binary search 2 회.

    Returns
    -------
    (count, start)  --- sa[start:start+count] 가 q 매칭 위치들.
    """
    n = len(sa)
    qlen = len(q)
    # lower bound
    lo, hi = 0, n
    while lo < hi:
        mid = (lo + hi) >> 1
        pos = int(sa[mid])
        if bytes(text[pos : pos + qlen]) < q:
            lo = mid + 1
        else:
            hi = mid
    start = lo
    # upper bound
    lo, hi = start, n
    while lo < hi:
        mid = (lo + hi) >> 1
        pos = int(sa[mid])
        if bytes(text[pos : pos + qlen]) <= q:
            lo = mid + 1
        else:
            hi = mid
    end = lo
    return end - start, start


PARQUET = "data/dart/allFilings/20260318.parquet"
SCRATCH = Path("data/_scratch_fm")
SCRATCH.mkdir(parents=True, exist_ok=True)
TEXT_PATH = SCRATCH / "text.bin"
SA_PATH = SCRATCH / "sa.npy"
OFFSETS_PATH = SCRATCH / "offsets.npy"

QUERIES = [
    "유상증자",
    "HBM",
    "대표이사 변경",
    "자기주식취득",
    "환율 변동",
    "최대주주변경",
    "전환사채",
]


def fmt_bytes(n: int) -> str:
    if n > 1 << 30:
        return f"{n / (1 << 30):.2f} GB"
    if n > 1 << 20:
        return f"{n / (1 << 20):.1f} MB"
    return f"{n / 1024:.1f} KB"


def proc_rss() -> int:
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss
    except ImportError:
        return -1


def build_if_missing() -> None:
    if TEXT_PATH.exists() and SA_PATH.exists() and OFFSETS_PATH.exists():
        print("[build] 이미 빌드됨 — 스킵")
        return

    print("[build] parquet → text + sa + offsets 빌드 중...")
    t0 = time.perf_counter()
    df = pl.read_parquet(
        PARQUET,
        columns=["section_content"],
    ).filter(pl.col("section_content").is_not_null())
    sections = df["section_content"].to_list()
    t1 = time.perf_counter()
    print(f"[build] parquet read: {t1 - t0:.2f}s, sections: {len(sections):,}")

    SEP = b"\x01"
    offsets = [0]
    chunks: list[bytes] = []
    for s in sections:
        b = s.encode("utf-8")
        chunks.append(b)
        offsets.append(offsets[-1] + len(b) + 1)
    text = SEP.join(chunks)
    print(f"[build] text: {fmt_bytes(len(text))}")

    TEXT_PATH.write_bytes(text)
    print(f"[build] text 저장: {TEXT_PATH}")

    t0 = time.perf_counter()
    sa = divsufsort(text)
    t1 = time.perf_counter()
    print(f"[build] sa-build: {t1 - t0:.2f}s, sa.nbytes={fmt_bytes(sa.nbytes)}")

    np.save(SA_PATH, sa)
    np.save(OFFSETS_PATH, np.asarray(offsets, dtype=np.int64))
    print(f"[build] sa 저장: {SA_PATH} ({fmt_bytes(SA_PATH.stat().st_size)})")
    print(f"[build] offsets 저장: {OFFSETS_PATH} ({fmt_bytes(OFFSETS_PATH.stat().st_size)})")


def main() -> None:
    print("=" * 72)
    print("mmap suffix array — RAM 사용 0 검색 검증")
    print("=" * 72)

    build_if_missing()

    # ── mmap 로드 ──
    print()
    rss_before = proc_rss()
    print(f"[mmap] RSS before load: {fmt_bytes(rss_before) if rss_before > 0 else 'n/a'}")

    # text 는 bytes 로 (mmap)
    import mmap

    text_file = open(TEXT_PATH, "rb")
    text = mmap.mmap(text_file.fileno(), 0, access=mmap.ACCESS_READ)
    # numpy array mmap
    sa = np.load(SA_PATH, mmap_mode="r")
    offsets = np.load(OFFSETS_PATH, mmap_mode="r")

    rss_after = proc_rss()
    print(f"[mmap] RSS after  load: {fmt_bytes(rss_after) if rss_after > 0 else 'n/a'}")
    print(f"[mmap] RSS delta: {fmt_bytes(rss_after - rss_before) if rss_before > 0 else 'n/a'}")
    print(f"[mmap] text size: {fmt_bytes(len(text))}, sa shape: {sa.shape}, dtype: {sa.dtype}")

    # ── cold 검색 (페이지 캐시 X 보장 위해 OS drop_caches 못 함 — Windows; 그냥 첫 호출만 cold 로 측정) ──
    print()
    print("─── cold + warm 검색 (mmap'd SA) ───")
    # 첫 호출: cold
    # 두 번째 호출: warm
    for q in QUERIES:
        qb = q.encode("utf-8")
        # cold (mmap'd SA 로 직접 binary search)
        t0 = time.perf_counter()
        count, start = sa_search_manual(text, sa, qb)
        cold_us = (time.perf_counter() - t0) * 1e6
        # warm
        t0 = time.perf_counter()
        count, start = sa_search_manual(text, sa, qb)
        warm_us = (time.perf_counter() - t0) * 1e6
        # top 5 매칭 위치 → section 매핑
        if count > 0:
            positions = sorted(int(p) for p in sa[start : start + min(count, 10)])
            section_idxs = np.searchsorted(offsets, positions, side="right") - 1
            sample = sorted(set(int(s) for s in section_idxs))[:3]
        else:
            sample = []
        print(f"  {q!r:30s} occ={count:6d}  cold={cold_us:9.1f}µs  warm={warm_us:9.1f}µs  secs={sample}")

    rss_final = proc_rss()
    print()
    print(f"[mmap] RSS final: {fmt_bytes(rss_final) if rss_final > 0 else 'n/a'}")
    print(f"[mmap] RSS delta from start: {fmt_bytes(rss_final - rss_before) if rss_before > 0 else 'n/a'}")
    print()
    print(f"[disk] text on disk: {fmt_bytes(TEXT_PATH.stat().st_size)}")
    print(f"[disk] sa   on disk: {fmt_bytes(SA_PATH.stat().st_size)}")
    print(
        f"[disk] total: {fmt_bytes(TEXT_PATH.stat().st_size + SA_PATH.stat().st_size)} "
        f"(={(TEXT_PATH.stat().st_size + SA_PATH.stat().st_size) / TEXT_PATH.stat().st_size:.1f}x text)"
    )


if __name__ == "__main__":
    main()
