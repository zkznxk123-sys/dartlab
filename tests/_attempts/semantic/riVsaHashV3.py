"""RI-VSA v3 — IDF 가중 + 풀 corpus (allFilings + docs).

목적
----
v2 의 한계 2 종 해결:
1. **변별력 약화**: baseline mean 72.5, 의미 쌍과 무관 쌍 distance 비슷.
   "주식", "회사", " 의 " 같은 *흔한 stem* 이 모든 contextHash 에 골고루 박혀
   변별력 떨어뜨림.
2. **표본 작음**: 30K 섹션 → 분포 신호 부족.

핵심 개선
---------
- **IDF 가중**: idf[s] = log(n_sec / df[s]). 흔한 stem 의 영향력 줄임.
  수학적 트릭: `weighted_idxHash = idxHash * idf`. 한 matmul 안에 자연스럽게 적용.
  공식: weighted = M.T @ M @ (idf · idxHash)
              = M.T @ (M @ (idf · idxHash))
  PPMI 비슷한 효과지만 *비선형 X* → matmul 으로 가능.
- **풀 corpus**: allFilings 65 일 + docs/ 전 종목 → 분포 정확도 폭증.
  메모리 예산 신중: scipy.sparse 가 *데이터에 비례* (Python set 안 씀).

방법
----
1. allFilings 2026* + docs/*.parquet 모두 load
2. section_content 추출 (null 제외)
3. tokenize: bigram + trigram 합집합
4. doc_freq ≥ MIN_DF 필터
5. M = section × stem 이진 sparse
6. df_arr = M.sum(axis=0) → idf 계산
7. weighted_idxHash = idxHash * idf[:, None]
8. weighted = M.T @ (M @ weighted_idxHash)
9. self 보정
10. pack → 256-bit contextHash

비고
----
- 시도 폴더 (회귀 가드 아님)
- 메모리 OOM 시 SAMPLE_SECTIONS 로 cap
- 성공 → v4 (위치 회전) → v5 (검색 인터페이스 = 쿼리 해시 → Hamming NN)

결과 (2026-05-20, 65 일치 allFilings + docs 2927 → 60K reservoir)
-------------------------------------------------------------------
빌드: load 444s (reservoir) + stems 109s + M 125s + idf 0.4s + idxHash 0.8s + **matmul 45s** + pack 0s ≈ 12 분
표본: 4.7M 전체 섹션 중 60K reservoir 보존
stems: 169,142 (df≥20)
M: 60,000 × 169,142 nnz=78M, 313 MB
contextHash: 5.4 MB

PROBE A 의미 이웃 1순위 d (v2 30K vs v3 60K reservoir):
- 유상증 → 유상: v2=4, v3=9
- 전환사 → 환사채: v2=5, v3=6
- 차입금 → 입금: v2=10, v3=9
- 자기주 → 기주식: v2=11, v3=11
- 대표이 → 표이사: v2=5, v3=4 (df 12K — docs 추가 효과)
- 차입금 → 손익계산서/포괄손익 (v2 안 잡힘) — docs 추가로 *재무제표 위치* 학습

PROBE B 쌍 distance (v2 → v3):
- 자기 vs 자사: v2=27, v3=40 (회귀!)
- 자기주 vs 자사: v2=39, v3=53 (회귀)
- 유상 vs 증자: v2=37, v3=18
- 차입 vs 사채: v2=45, v3=43
- 취득 vs 처분: v2=15, v3=21
- 대표 vs 임원: v2=27, v3=22
- 합병 vs 분할: 신규 v3=27
- 소송 vs 우발: 신규 v3=48

멀어야:
- 자기 vs 농업: v2=43, v3=64 (분리 더 명확)
- 배당 vs 특허: v2=54, v3=79
- 유상증 vs 농업: v2=46, v3=58
- 합병 vs 특허: 신규 v3=50

PROBE C baseline: v2=72.5, v3=**89.1** (이론 128 에 더 가까움 — IDF 가 1-bit 편향 회복).

결론
----
- ★ IDF 가중이 baseline 편향 회복 (72.5 → 89.1)
- ★ docs 추가로 *재무 도메인 의미 layer* 학습 (차입금 → 포괄손익/재무상태표)
- ★ 변별력 폭증: 가까운 쌍 d=18~53 vs 멀어야 d=50~79 *분리*
- × 일부 동의어 쌍 회귀 (자기↔자사 v2=27 → v3=40) — IDF 가중이 흔한 stem 영향 줄여서 발생
- 60K reservoir 가 4.7M 풀 분포의 통계적 대표 가능

저장: data/_scratch_fm/riVsaV3/{contextHash.npy, df.npy, stems.json}
v4, v5, v7 의 기반 자산.

다음 단계
--------
v4 — 검색 인터페이스 (자연어 쿼리 → hash → Hamming NN)
v6 — Resonance Hash (char Bloom + random)
v7 — Tier 1 + Tier 2 self 포함 (사용자 idea 정확 구현)
"""

from __future__ import annotations

import gc
import hashlib
import time
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl
from scipy.sparse import csr_matrix

HASH_BITS = 256
HASH_BYTES = 32
NGRAM_NS = (2, 3)
MIN_DOC_FREQ = 20  # 풀 corpus 라 좀 더 보수적
MAX_TOKENS_PER_SECTION = 4000
SAMPLE_SECTIONS: int | None = 60_000  # reservoir sampling. 60K = v2 (30K) 의 2×, 메모리 안전.
TOP_K = 15
SEED = 42

ALLFILINGS_DIR = Path("data/dart/allFilings")
DOCS_DIR = Path("data/dart/docs")

PROBE_TERMS = [
    "유상증",
    "전환사",
    "차입금",
    "자기주",
    "대표이",
    "주주총",
    "최대주",
    "유상",
    "사채",
    "차입",
    "자사",
    "자기",
    "대표",
    "총회",
    "변경",
    "취득",
    "처분",
    "합병",
    "소송",
    "특허",
    "HBM",
    "신주",
    "배당",
    "감자",
]

PROBE_PAIRS_NEAR = [
    ("자기", "자사"),
    ("자기주", "자사"),
    ("유상", "증자"),
    ("유상증", "신주"),
    ("차입", "사채"),
    ("취득", "처분"),
    ("대표", "임원"),
    ("합병", "분할"),
    ("소송", "우발"),
]
PROBE_PAIRS_FAR = [
    ("자기", "농업"),
    ("배당", "특허"),
    ("HBM", "농업"),
    ("유상증", "농업"),
    ("합병", "특허"),
]


def indexHashSigned(stem: str) -> np.ndarray:
    h = hashlib.blake2b(stem.encode(), digest_size=HASH_BYTES).digest()
    bits = np.unpackbits(np.frombuffer(h, dtype=np.uint8))
    return bits.astype(np.int8) * 2 - 1


def tokenize(s: str, *, max_count: int = MAX_TOKENS_PER_SECTION) -> list[str]:
    tokens: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        upto = min(len(s) - n + 1, max_count)
        for i in range(upto):
            tokens.append(s[i : i + n])
    return tokens


def loadAllSections() -> list[str]:
    """allFilings + docs 합쳐서 reservoir sample (메모리 안전).

    7M+ 섹션을 다 들고 있으면 OOM. 그래서 reservoir sampling 으로
    *streaming 중에* SAMPLE_SECTIONS 개만 보존. 전체 corpus 분포 통계적 대표.
    """
    if SAMPLE_SECTIONS is None:
        # full corpus 모드 — 메모리 주의
        sections: list[str] = []
        af_files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
        print(f"  allFilings: {len(af_files)} 일치")
        for f in af_files:
            df = pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null())
            sections.extend(df["section_content"].to_list())
        docs_files = sorted(DOCS_DIR.glob("*.parquet"))
        print(f"  docs: {len(docs_files)} 종목")
        for i, f in enumerate(docs_files):
            try:
                df = pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null())
                sections.extend(df["section_content"].to_list())
            except Exception:
                continue
            if (i + 1) % 500 == 0:
                print(f"    [{i + 1}/{len(docs_files)}] 누적 {len(sections):,} 섹션")
        return sections

    # Reservoir sampling — 메모리 = O(SAMPLE_SECTIONS) 상한
    K = SAMPLE_SECTIONS
    rng = np.random.default_rng(SEED)
    reservoir: list[str] = []
    n_seen = 0

    def consume(items: list[str]) -> None:
        nonlocal n_seen
        for x in items:
            if len(reservoir) < K:
                reservoir.append(x)
            else:
                # Algorithm R: replace random reservoir element with prob K/n_seen
                j = rng.integers(0, n_seen + 1)
                if j < K:
                    reservoir[j] = x
            n_seen += 1

    af_files = sorted(p for p in ALLFILINGS_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    print(f"  allFilings: {len(af_files)} 일치")
    for f in af_files:
        df = pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null())
        consume(df["section_content"].to_list())

    docs_files = sorted(DOCS_DIR.glob("*.parquet"))
    print(f"  docs: {len(docs_files)} 종목")
    for i, f in enumerate(docs_files):
        try:
            df = pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null())
            consume(df["section_content"].to_list())
        except Exception:
            continue
        if (i + 1) % 500 == 0:
            print(f"    [{i + 1}/{len(docs_files)}] seen={n_seen:,} reservoir={len(reservoir):,}")

    print(f"  reservoir sampling: 전체 {n_seen:,} → 보존 {len(reservoir):,}")
    return reservoir


def main() -> None:
    print("=" * 72)
    print("RI-VSA v3 — IDF 가중 + 풀 corpus")
    print(f"  NGRAM_NS={NGRAM_NS}  MIN_DF={MIN_DOC_FREQ}  SAMPLE={SAMPLE_SECTIONS}")
    print("=" * 72)

    # ── 1. 로드 ──
    t0 = time.perf_counter()
    print("[load] 코퍼스 수집 중...")
    sections = loadAllSections()
    if SAMPLE_SECTIONS is not None and len(sections) > SAMPLE_SECTIONS:
        rng = np.random.default_rng(SEED)
        idxs = rng.choice(len(sections), size=SAMPLE_SECTIONS, replace=False)
        sections = [sections[i] for i in idxs]
    total_chars = sum(len(s) for s in sections)
    print(f"[load] 섹션 {len(sections):,} 개, 총 {total_chars / 1e6:.1f}M chars — {time.perf_counter() - t0:.1f}s")

    # ── 2. Pass 1: doc_freq ──
    t0 = time.perf_counter()
    doc_freq: Counter[str] = Counter()
    for s in sections:
        doc_freq.update(set(tokenize(s)))
    keep = sorted(t for t, c in doc_freq.items() if c >= MIN_DOC_FREQ)
    g2id = {t: i for i, t in enumerate(keep)}
    id2g = keep
    n_stems = len(g2id)
    print(f"[stems] {len(doc_freq):,} 전체 → df≥{MIN_DOC_FREQ} {n_stems:,} — {time.perf_counter() - t0:.1f}s")
    del doc_freq  # 곧 M 으로부터 다시 계산

    # ── 3. sparse M ──
    t0 = time.perf_counter()
    rows: list[int] = []
    cols: list[int] = []
    for sid, s in enumerate(sections):
        seen = set()
        for t in tokenize(s):
            gid = g2id.get(t)
            if gid is not None and gid not in seen:
                seen.add(gid)
                rows.append(sid)
                cols.append(gid)
        if (sid + 1) % 50000 == 0:
            print(f"  [M-build] {sid + 1:,} sections, nnz={len(rows):,}")
    n_sec = len(sections)
    M = csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(n_sec, n_stems),
    )
    del rows, cols, sections
    gc.collect()
    print(
        f"[M] {n_sec:,} × {n_stems:,}  nnz={M.nnz:,}  ({M.data.nbytes / 1e6:.1f} MB data) "
        f"— {time.perf_counter() - t0:.1f}s"
    )

    # ── 4. df_arr & idf ──
    t0 = time.perf_counter()
    df_arr = np.asarray(M.sum(axis=0)).flatten().astype(np.float32)
    df_arr = np.maximum(df_arr, 1.0)
    idf = np.log(n_sec / df_arr).astype(np.float32)
    print(
        f"[idf] mean={idf.mean():.2f}  median={np.median(idf):.2f}  "
        f"min={idf.min():.2f}  max={idf.max():.2f} — {time.perf_counter() - t0:.1f}s"
    )

    # ── 5. idxHashes (가중 적용) ──
    t0 = time.perf_counter()
    idxHashes = np.zeros((n_stems, HASH_BITS), dtype=np.float32)
    for stem, sid in g2id.items():
        idxHashes[sid] = indexHashSigned(stem).astype(np.float32)
    weightedIdx = idxHashes * idf[:, None]  # IDF 적용
    print(f"[idxHash·idf] {weightedIdx.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # ── 6. weighted = M.T @ (M @ weightedIdx) ──
    t0 = time.perf_counter()
    temp = M @ weightedIdx  # (n_sec, 256)
    weighted = (M.T @ temp).astype(np.float64)  # (n_stems, 256)
    print(f"[matmul] — {time.perf_counter() - t0:.1f}s")

    # ── 7. self 보정 ──
    t0 = time.perf_counter()
    self_contrib = df_arr[:, None].astype(np.float64) * weightedIdx.astype(np.float64)
    weighted -= self_contrib
    print(f"[self-correct] |max|={np.abs(weighted).max():.1f} — {time.perf_counter() - t0:.1f}s")

    # ── 8. pack ──
    t0 = time.perf_counter()
    contextBits = (weighted > 0).astype(np.uint8)
    contextPacked = np.packbits(contextBits, axis=1)
    print(f"[pack] {contextPacked.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # ── 9. PROBE A ──
    print()
    print(f"─── PROBE A: 의미 이웃 (top {TOP_K}) ───")
    df_int = df_arr.astype(np.int64)
    for term in PROBE_TERMS:
        if term not in g2id:
            print(f'\n? "{term}" — 인덱스 없음 (df < {MIN_DOC_FREQ})')
            continue
        sid = g2id[term]
        xored = np.bitwise_xor(contextPacked, contextPacked[sid : sid + 1])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        nearest = np.argpartition(dist, TOP_K + 1)[: TOP_K + 1]
        nearest = sorted(nearest, key=lambda i: dist[i])
        nearest = [i for i in nearest if i != sid][:TOP_K]
        print(f'\n? "{term}"  (df={int(df_int[sid]):,})')
        for i in nearest:
            print(f"    d={int(dist[i]):3d}  df={int(df_int[i]):>7d}  {id2g[i]!r}")

    # ── 10. PROBE B ──
    print()
    print("─── PROBE B: 쌍 distance ───")
    for label, pairs in [("가까워야", PROBE_PAIRS_NEAR), ("멀어야", PROBE_PAIRS_FAR)]:
        print(f"\n[{label}]")
        for a, b in pairs:
            if a not in g2id or b not in g2id:
                print(f"  {a:8s} vs {b:8s} — 누락")
                continue
            ai, bi = g2id[a], g2id[b]
            d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
            print(f"  {a:8s} vs {b:8s}  d={d}")

    # ── 11. PROBE C ──
    print()
    print("─── PROBE C: 무작위 baseline ───")
    rng = np.random.default_rng(SEED)
    idxs = rng.choice(n_stems, size=2000, replace=False)
    xored = np.bitwise_xor(contextPacked[idxs[:1000]], contextPacked[idxs[1000:]])
    dists = np.unpackbits(xored, axis=1).sum(axis=1)
    print(
        f"  1000 random pairs: mean={dists.mean():.1f}  median={np.median(dists):.1f}  "
        f"std={dists.std():.1f}  min={dists.min()}  max={dists.max()}"
    )

    # ── 12. 결과 저장 (다음 단계 검색 인터페이스용) ──
    out_dir = Path("data/_scratch_fm/riVsaV3")
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "contextHash.npy", contextPacked)
    np.save(out_dir / "df.npy", df_arr.astype(np.int64))
    import json

    (out_dir / "stems.json").write_text(json.dumps(id2g, ensure_ascii=False), encoding="utf-8")
    print(f"\n[save] {out_dir} 에 contextHash + df + stems 저장")


if __name__ == "__main__":
    main()
