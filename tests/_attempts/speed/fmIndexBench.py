"""FM-index (suffix array) vs naive str.find vs polars BM25-ish — DART 1 일치 본문 벤치.

목적
----
DART 공시 본문 빠른 검색 — vector/RAG 없이 substring 매칭. 게놈 분석의 표준 자료구조
suffix array 를 한국 금융 corpus 에 처음 적용.

방법
----
1. allFilings 20260318.parquet (1 일치 = 41K 섹션, 1.5 GB 본문) 로드
2. naive baseline: Python `str.find` 섹션별 루프
3. naive baseline 2: `bytes.find` on concatenated blob
4. pydivsufsort 로 suffix array 빌드 → sa_search

쿼리: 유상증자, HBM, 대표이사 변경, 자기주식취득, 환율 변동, 최대주주변경, 전환사채

결과 (2026-05-20, 데이터 1.5 GB)
-----------------------------------
| 방식 | 쿼리당 시간 | 비고 |
|---|---|---|
| Python str.find loop | 600~1280 ms | 사람 grep 한 번 |
| bytes.find blob | 550~955 ms | 약간 빠른 변형 |
| **suffix array (sa_search)** | **7~16 µs** | **50000~80000× 빠름** |

빌드: 1.5GB 텍스트 → SA = 103 초 (1 회).
메모리: SA = 텍스트의 **4×** (1.5GB → 6GB int32 indices).
정확성: naive 와 occurrence 수치 정확히 일치 (검증).

결론
----
- ★ 5만~8만배 속도 — 검색 횟수 무관 (5GB든 100GB든 동일)
- ★ 단어 사전·임베딩 모델·LLM 의존 0
- ★ 한글·영어·약어·신조어 무관 (글자 단위 substring)
- × SA = 텍스트 4× 메모리 — 풀 corpus 50GB → 200GB SA
- × 의미 검색 X (substring 만)

다음 단계
--------
- fmIndexMmap — mmap 으로 메모리 0 검증
- 의미 검색은 별도 트랙 (riVsa*)
"""

from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
from pydivsufsort import divsufsort, sa_search

PARQUET = "data/dart/allFilings/20260318.parquet"
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


def main() -> None:
    print("=" * 72)
    print("FM-index (suffix array) DART 본문 검색 벤치")
    print("=" * 72)

    # ── 1. 로드 ──
    t0 = time.perf_counter()
    df = pl.read_parquet(
        PARQUET,
        columns=["rcept_no", "corp_name", "report_nm", "section_title", "section_content"],
    ).filter(pl.col("section_content").is_not_null())
    sections = df["section_content"].to_list()
    t1 = time.perf_counter()
    print(f"[load] sections: {len(sections):,} rows, parquet read: {t1 - t0:.2f}s")

    # ── 2. 통째 텍스트로 합치고 offset 표 만들기 ──
    # 각 섹션 사이에 \x01 구분자 (0xFE 같은 거 써도 됨; 한국어 본문에 없을 글자)
    t0 = time.perf_counter()
    SEP = b"\x01"
    offsets = [0]
    chunks: list[bytes] = []
    for s in sections:
        b = s.encode("utf-8")
        chunks.append(b)
        offsets.append(offsets[-1] + len(b) + 1)
    text = SEP.join(chunks)
    t1 = time.perf_counter()
    print(f"[concat] text size: {fmt_bytes(len(text))}, concat: {t1 - t0:.2f}s")
    print(f"[concat] sections: {len(sections):,}")

    # offsets 를 numpy 로 (sorted) — searchsorted 로 byte_offset → section_idx 매핑
    offsets_arr = np.asarray(offsets, dtype=np.int64)

    # ── 3. naive baseline: str.find 로 모든 섹션 스캔 ──
    print()
    print("─── baseline 1: naive str.find loop (Python) ───")
    for q in QUERIES:
        qb = q.encode("utf-8")
        t0 = time.perf_counter()
        hits = 0
        for s in sections:
            if q in s:
                hits += 1
        elapsed = time.perf_counter() - t0
        print(f"  {q!r:30s} hits={hits:6d}  time={elapsed * 1000:8.1f} ms")

    # ── 4. naive baseline 2: bytes.find on the joined blob ──
    print()
    print("─── baseline 2: bytes.find on concat blob (count occurrences) ───")
    for q in QUERIES:
        qb = q.encode("utf-8")
        t0 = time.perf_counter()
        count = text.count(qb)
        elapsed = time.perf_counter() - t0
        print(f"  {q!r:30s} occ={count:6d}  time={elapsed * 1000:8.1f} ms")

    # ── 5. suffix array 빌드 ──
    print()
    print("─── FM-index (suffix array) build ───")
    gc.collect()
    t0 = time.perf_counter()
    sa = divsufsort(text)
    t1 = time.perf_counter()
    print(
        f"[sa-build] {t1 - t0:.2f}s  sa.nbytes={fmt_bytes(sa.nbytes)}  text={fmt_bytes(len(text))}  ratio={sa.nbytes / len(text):.2f}x"
    )

    # ── 6. suffix-array 검색 (occurrence count + 위치 → section 매핑) ──
    print()
    print("─── suffix array search ───")
    for q in QUERIES:
        qb = q.encode("utf-8")
        # warmup
        sa_search(text, sa, qb)
        t0 = time.perf_counter()
        count, start = sa_search(text, sa, qb)
        elapsed = time.perf_counter() - t0
        # 첫 10 개 매칭 → section 매핑
        positions = sorted(sa[start : start + min(count, 10)].tolist())
        section_idxs = (np.searchsorted(offsets_arr, positions, side="right") - 1).tolist()
        sample_sections = list({i for i in section_idxs})[:5]
        elapsed2 = time.perf_counter() - t0
        print(
            f"  {q!r:30s} occ={count:6d}  sa_search={elapsed * 1e6:7.1f}µs  "
            f"+section_map={elapsed2 * 1e6:7.1f}µs  sample_secs={sample_sections}"
        )


if __name__ == "__main__":
    main()
