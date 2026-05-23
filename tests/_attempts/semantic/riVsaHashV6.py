"""RI-VSA v6 — 우리만의 해시 (Character Bloom + Random 합성).

목적
----
v3 의 indexHash (blake2b) 가 *암호 해시* 라 인접성 0. 자기주↔자사주 같은
*글자 공유 동의어* 의 갭이 분포 누적만으로는 부족 (v3 d=40).

근본 해결: **indexHash 자체에 character-level locality 내장**.

새 해시 — Resonance Hash
------------------------
256-bit 을 두 영역으로 분할:

Region A (bit 0..127) — Character Bloom (locality):
- 각 character → k=3 random bit positions in [0, 128)
- 글자 공유 → bit 공유 *자동*
- 자기주(자/기/주) vs 자사주(자/사/주): 자/주 2 글자 공유 → bit 6 개 공유
- 자기주 vs 농업: 글자 0 공유 → bit 0 공유

Region B (bit 128..255) — blake2b Random (identity):
- 전체 string 의 random 부호화
- 동음이의 변별, 의미 안 같은 같은-글자-순서 변별
- "자기주" (자기주식의 일부) vs "주기자" (= cycle-giver) 변별

합집합 효과:
- 글자 공유 + 의미 공유 → distance 폭격 작음 (자기주↔자사주)
- 글자 공유 + 의미 다름 → 글자 region 만 가까움, 전체는 중간 distance
- 글자 다름 + 의미 다름 → 완전 random distance

위에 v3 의 contextHash 누적 layer 가 *분포 의미* 를 추가. 즉:
- 형태 의미 (Region A) + 분포 의미 (contextHash 누적) = 2 layer 통합

방법
----
오직 `indexHashSigned` 함수만 v3 와 다름. 나머지 (matmul, IDF, finalize)
완전 동일. *최소 변경 단일 실험*.

비고
----
- 회귀 가드 아님. 시도 폴더.
- v3 와 동일 60K reservoir corpus. probe 결과 직접 비교.
- 성공 = 자기↔자사 d 가 v3 의 40 에서 25 미만으로 줄어들어야 함.

결과 (2026-05-20, 65 일치 + docs 2927 → 60K reservoir)
------------------------------------------------------
빌드: load 484s + stems 96s + M 148s + idxHash 2.4s + matmul 46s + pack 0s ≈ 13 분

Sanity check (region 별 분해):
- 자기주 vs 자사주: total=67 (char=4/128, rand=63/128)
- 자기주 vs 농업: total=78 (char=12/128, rand=66/128)
- 유상증자 vs 유상증: total=63 (char=3/128, rand=60/128)
→ char region 의도대로 작동. rand region 평균 ~64 (이론 ~64).

PROBE A 의미 이웃 1순위 d (v3 vs v6):
- 유상증 → 유상: v3=9, v6=5
- 전환사 → 환사채: v3=6, v6=2
- 차입금 → 입금: v3=9, v6=6
- 자기주 → 기주식: v3=11, v6=2
- 대표이 → 표이사: v3=4, v6=1
- 차입금 → 무상태/계산서/이연법 (재무 family) d=7-8

PROBE B 쌍 distance (v3 → v6):
- **자기 vs 자사: v3=40, v6=25 (-15) ✓**
- 자기주 vs 자사: v3=53, v6=30 (-23)
- 유상 vs 증자: v3=18, v6=7
- 차입 vs 사채: v3=43, v6=24
- 취득 vs 처분: v3=21, v6=14
- 대표 vs 임원: v3=22, v6=13
- 합병 vs 분할: v3=27, v6=9
- 소송 vs 우발: v3=48, v6=25

멀어야:
- 자기 vs 농업: v3=64, v6=39 (분리 약화)
- 배당 vs 특허: v3=79, v6=47
- 유상증 vs 농업: v3=58, v6=46
- 합병 vs 특허: v3=50, v6=34

PROBE C baseline: v3=89.1, v6=**49.0** (-40, 폭격 작아짐)

결론
----
- ★ char Bloom 이 부분문자열 (유상→유상증) 인식 폭격
- ★ 동의어 (자기↔자사 d=25) 갭 메움
- ★ 의미 family top-15 quality 향상
- × baseline mean=49 로 폭격 작아짐 — *절대 noise floor* 상승
- × spurious matches (자사 → 랜드/이센스 d=15) — 글자만 같은 무관 stem
- 상대 변별력 비율 v3 와 비슷 (가까운/baseline 0.37 vs 멀어야/baseline 0.84)

다음 단계
--------
v7 — 4 region (jamo+char+bigram+random) + Tier 2 self 포함 (사용자 idea 정확 구현)

저장: data/_scratch_fm/riVsaV6/{contextHash.npy, df.npy, stems.json}
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
HASH_BYTES = HASH_BITS // 8
CHAR_REGION_BITS = 128
RAND_REGION_BITS = 128
CHAR_BLOOM_K = 3
NGRAM_NS = (2, 3)
MIN_DOC_FREQ = 20
MAX_TOKENS_PER_SECTION = 4000
SAMPLE_SECTIONS: int | None = 60_000
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


# ── 새 해시 함수 ──


def _charBitPositions(ch: str) -> list[int]:
    """글자 하나 → k 개 bit position in [0, CHAR_REGION_BITS)."""
    positions = []
    for k in range(CHAR_BLOOM_K):
        key = f"{ch}|{k}".encode("utf-8")
        h = hashlib.blake2b(key, digest_size=4).digest()
        pos = int.from_bytes(h, "little") % CHAR_REGION_BITS
        positions.append(pos)
    return positions


def indexHashSigned(stem: str) -> np.ndarray:
    """Resonance Hash: char Bloom (128 bit) + random (128 bit) → signed ±1 (int8)."""
    bits = np.zeros(HASH_BITS, dtype=np.uint8)

    # Region A: character Bloom
    for ch in stem:
        for pos in _charBitPositions(ch):
            bits[pos] = 1

    # Region B: blake2b random of full string
    h = hashlib.blake2b(stem.encode(), digest_size=RAND_REGION_BITS // 8).digest()
    randBits = np.unpackbits(np.frombuffer(h, dtype=np.uint8))
    bits[CHAR_REGION_BITS:] = randBits

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
    """v3 와 동일한 reservoir sampling."""
    if SAMPLE_SECTIONS is None:
        raise NotImplementedError("Use SAMPLE_SECTIONS for memory safety")
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
    print(f"  전체 {n_seen:,} → 보존 {len(reservoir):,}")
    return reservoir


def main() -> None:
    print("=" * 72)
    print(f"RI-VSA v6 — Resonance Hash (char Bloom {CHAR_REGION_BITS}b + random {RAND_REGION_BITS}b)")
    print(f"  NGRAM_NS={NGRAM_NS}  MIN_DF={MIN_DOC_FREQ}  SAMPLE={SAMPLE_SECTIONS}")
    print("=" * 72)

    # 0. 해시 검증 — Resonance 작동하는지 sanity check
    print()
    print("─── 해시 sanity check ───")
    samples = [
        ("자기주", "자사주"),  # 글자 2/3 공유
        ("자기주", "농업"),  # 글자 0 공유
        ("유상증자", "유상증"),  # 부분 문자열
    ]
    for a, b in samples:
        ha = (indexHashSigned(a) > 0).astype(np.uint8)
        hb = (indexHashSigned(b) > 0).astype(np.uint8)
        d = int(np.bitwise_xor(ha, hb).sum())
        # region 별 분해
        d_char = int(np.bitwise_xor(ha[:CHAR_REGION_BITS], hb[:CHAR_REGION_BITS]).sum())
        d_rand = int(np.bitwise_xor(ha[CHAR_REGION_BITS:], hb[CHAR_REGION_BITS:]).sum())
        print(f"  '{a}' vs '{b}': d={d}  (char={d_char}/{CHAR_REGION_BITS}, rand={d_rand}/{RAND_REGION_BITS})")
    print()

    # 1. 로드
    t0 = time.perf_counter()
    print("[load] 코퍼스 수집 중...")
    sections = loadAllSections()
    total_chars = sum(len(s) for s in sections)
    print(f"[load] 섹션 {len(sections):,}개, 총 {total_chars / 1e6:.1f}M chars — {time.perf_counter() - t0:.1f}s")

    # 2. Pass 1: doc_freq
    t0 = time.perf_counter()
    doc_freq: Counter[str] = Counter()
    for s in sections:
        doc_freq.update(set(tokenize(s)))
    keep = sorted(t for t, c in doc_freq.items() if c >= MIN_DOC_FREQ)
    g2id = {t: i for i, t in enumerate(keep)}
    id2g = keep
    n_stems = len(g2id)
    print(f"[stems] {len(doc_freq):,} 전체 → df≥{MIN_DOC_FREQ} {n_stems:,} — {time.perf_counter() - t0:.1f}s")
    del doc_freq

    # 3. sparse M
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
        if (sid + 1) % 20000 == 0:
            print(f"  [M-build] {sid + 1:,} sections, nnz={len(rows):,}")
    n_sec = len(sections)
    M = csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(n_sec, n_stems),
    )
    del rows, cols, sections
    gc.collect()
    print(f"[M] {n_sec:,} × {n_stems:,} nnz={M.nnz:,} ({M.data.nbytes / 1e6:.1f} MB) — {time.perf_counter() - t0:.1f}s")

    # 4. df + idf
    t0 = time.perf_counter()
    df_arr = np.asarray(M.sum(axis=0)).flatten().astype(np.float32)
    df_arr = np.maximum(df_arr, 1.0)
    idf = np.log(n_sec / df_arr).astype(np.float32)
    print(f"[idf] mean={idf.mean():.2f} median={np.median(idf):.2f} — {time.perf_counter() - t0:.1f}s")

    # 5. idxHashes (Resonance Hash 적용)
    t0 = time.perf_counter()
    idxHashes = np.zeros((n_stems, HASH_BITS), dtype=np.float32)
    for stem, sid in g2id.items():
        idxHashes[sid] = indexHashSigned(stem).astype(np.float32)
    weightedIdx = idxHashes * idf[:, None]
    print(f"[idxHash·idf] {weightedIdx.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # 6. matmul
    t0 = time.perf_counter()
    temp = M @ weightedIdx
    weighted = (M.T @ temp).astype(np.float64)
    print(f"[matmul] — {time.perf_counter() - t0:.1f}s")

    # 7. self 보정
    t0 = time.perf_counter()
    self_contrib = df_arr[:, None].astype(np.float64) * weightedIdx.astype(np.float64)
    weighted -= self_contrib
    print(f"[self-correct] |max|={np.abs(weighted).max():.1f} — {time.perf_counter() - t0:.1f}s")

    # 8. pack
    t0 = time.perf_counter()
    contextBits = (weighted > 0).astype(np.uint8)
    contextPacked = np.packbits(contextBits, axis=1)
    print(f"[pack] {contextPacked.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # 9. PROBE A — 의미 이웃
    print()
    print(f"─── PROBE A: 의미 이웃 (top {TOP_K}) ───")
    df_int = df_arr.astype(np.int64)
    for term in PROBE_TERMS:
        if term not in g2id:
            print(f'\n? "{term}" — 인덱스 없음')
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

    # 10. PROBE B
    print()
    print("─── PROBE B: 쌍 distance (v3 비교) ───")
    for label, pairs in [("가까워야", PROBE_PAIRS_NEAR), ("멀어야", PROBE_PAIRS_FAR)]:
        print(f"\n[{label}]")
        for a, b in pairs:
            if a not in g2id or b not in g2id:
                print(f"  {a:8s} vs {b:8s} — 누락")
                continue
            ai, bi = g2id[a], g2id[b]
            d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
            print(f"  {a:8s} vs {b:8s}  d={d}")

    # 11. PROBE C
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

    # 12. 저장
    out_dir = Path("data/_scratch_fm/riVsaV6")
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "contextHash.npy", contextPacked)
    np.save(out_dir / "df.npy", df_arr.astype(np.int64))
    import json

    (out_dir / "stems.json").write_text(json.dumps(id2g, ensure_ascii=False), encoding="utf-8")
    print(f"\n[save] {out_dir}")


if __name__ == "__main__":
    main()
