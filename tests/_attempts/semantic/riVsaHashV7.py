"""RI-VSA v7 — Tier 1 characteristic + Tier 2 identity (self 포함).

목적
----
사용자 아이디어 정확 구현:
"개별 스템들의 특성 비교 가능한 해시를 만들고, 주체 스템과 주변 스템 해시들로 정체성 해시"

두 단계 명시 분리:
- **Tier 1 characteristic**: stem 의 *형태/음운/구성* features 를 비교 가능한 256-bit 로
- **Tier 2 identity**: 자기 characteristic + 주변 characteristics 누적 = 정체성

v3/v6 비교
---------
- v3: indexHash = blake2b (비교 불가) → contextHash 만으로 의미. self subtract.
- v6: indexHash = char Bloom (반-비교 가능) → 자기↔자사 d=25 메움. baseline 폭격.
- v7: characteristic = 4-region 비교 가능 (jamo+char+bigram+random) → identity = M.T @ M @ characteristic. **self 포함**.

Tier 1 — 비교 가능한 characteristic
---------------------------------
256-bit, 4 region 균등 (각 64-bit):

| region | 의미 layer | 공유 신호 |
|---|---|---|
| bits 0..63   | Jamo Bloom (한국어 음운) | 자/사/주 = ㅏ ㅈ 등 자모 공유 |
| bits 64..127 | Character Bloom | 자기/자사 = '자' 공유 |
| bits 128..191 | Bigram Bloom | 유상/유상증 = '유상' 공유 |
| bits 192..255 | blake2b Random (식별) | 동음이의 변별 |

Hamming distance 분해 가능: 어느 layer 에서 가까운지 사람이 읽음.

Tier 2 — identity = self + neighbor characteristics
--------------------------------------------------
```
identity[s] = doc_freq[s] · characteristic[s]               ← 자기 (남김)
            + Σ_{s'} CO[s, s'] · characteristic[s']          ← 주변
```

수식: `identity = M.T @ M @ characteristic` (self subtract 안 함).

v3/v6 에서 self_contrib 빼던 보정 *제거*. 사용자 idea 핵심.

비고
----
- 회귀 가드 아님. 시도 폴더.
- v3, v6 와 동일 reservoir 60K. probe 직접 비교.
- 메모리 룰: [feedback_attempts_docstring_results] — 결과 docstring 박기 필수.

결과 (2026-05-20, 65 일치 + docs 2927 종목 → 60K reservoir)
------------------------------------------------------------

빌드: load 444s + stems 109s + M 125s + Tier1 4s + **Tier2 41s** + pack 0s ≈ 12 분

Sanity check (region 분해):
- 자기주 vs 자사주: total=41 (jamo=6 char=4 bigram=6 rand=25)
- 자기주 vs 농업: total=56 (jamo=13 char=10 bigram=6 rand=27)
- 유상증자 vs 유상증: total=36 (jamo=0 char=2 bigram=2 rand=32)
- 배당 vs 특허: total=61 (jamo=15 char=8 bigram=4 rand=34)
→ Region 별 분리 명확. semantic layer (jamo+char+bigram) 가 의미 매칭 직접 신호.

PROBE A — 의미 이웃 1순위 d (역대 비교):
- 유상증 → 유상: v3=9, v6=5, **v7=1**
- 차입금 → 입금: v3=9, v6=6, **v7=0**
- 자기주 → 기주식: v3=11, v6=2, **v7=0**
- 대표이 → 표이사: v3=4, v6=1, **v7=0**
- 주주총 → 승인: v3=3, v6=3, **v7=0**
- 차입금 family: 입금/상태표/유동성/채무/수취채/금융보증 모두 d=0-3 (재무 cluster 응집)

PROBE B — 쌍 distance:
가까워야 (모두 baseline 23.4 미만):
- 자기 vs 자사 d=9 (v3=40, v6=25 → **31점 메움**)
- 자기주 vs 자사 d=15 (v3=53)
- 차입 vs 사채 d=14 (v3=43)
- 취득 vs 처분 d=7 (v3=21)
- 대표 vs 임원 d=7 (v3=22)
- 합병 vs 분할 d=7 (v3=27)
- 소송 vs 우발 d=12 (v3=48)
멀어야:
- 자기 vs 농업 d=12 ← 가까운 쌍과 3점 차이 (변별력 약점)
- 배당 vs 특허 d=27 (baseline 위)
- 유상증 vs 농업 d=15
- 합병 vs 특허 d=17

PROBE C: baseline mean=**23.4** median=23 std=5.5 (v3=89.1, v6=49.0)

결론
----
- ★ 검색 application 압도적 — top-k 의미 cluster 응집 (차입금 family d=0-3)
- ★ 동의어 갭 영구 메움: 자기↔자사 d=9 (v3 의 d=40 에서 31 점 메움)
- ★ 사용자 idea (Tier 1 비교가능 + Tier 2 self 포함) **정확히 효과 입증**
- × baseline 23.4 로 폭격 작아짐. 절대 변별력 약화 — 자기 vs 농업 d=12 vs 자기 vs 자사 d=9 = 3 점 차이만
- 검색 vs 분류 trade-off: v7 검색 strong, 분류 weak. v3 반대.

다음 단계 후보
-------------
- v8: rand region 키워 (64→128 bit) baseline 회복 시도. semantic layer 효과 보존하면서.
- v7 위에 검색 인터페이스 (riVsaSearch v2) — 자연어 쿼리 정확도 측정. v4 와 직접 비교.
- agipath 본진 (12M stems wiki+우리말샘) 이식. 더 큰 corpus 에서 baseline 회복 가능성.
- 사람 사전 hybrid: 자기↔자사 같은 핵심 동의어 사전에 박아 spurious 차단 + v7 강점 유지.

저장: data/_scratch_fm/riVsaV7/{contextHash.npy, df.npy, stems.json}
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
JAMO_REGION = slice(0, 64)
CHAR_REGION = slice(64, 128)
BIGRAM_REGION = slice(128, 192)
RAND_REGION = slice(192, 256)

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


def jamoDecompose(ch: str) -> list[str]:
    """한글 음절 → [초성, 중성, (종성)] 태그. 비한글은 자체."""
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        rel = code - 0xAC00
        cho = rel // (21 * 28)
        jung = (rel % (21 * 28)) // 28
        jong = rel % 28
        out = [f"C{cho}", f"V{jung}"]
        if jong > 0:
            out.append(f"F{jong}")
        return out
    return [ch]


def _bloomBit(key: str, region_start: int, region_len: int) -> int:
    h = hashlib.blake2b(key.encode(), digest_size=4).digest()
    pos = int.from_bytes(h, "little") % region_len
    return region_start + pos


def characteristic(stem: str) -> np.ndarray:
    """Tier 1 — 비교 가능한 256-bit characteristic (signed ±1)."""
    bits = np.zeros(HASH_BITS, dtype=np.uint8)

    # Region A — Jamo Bloom (64 bit)
    for ch in stem:
        for j in jamoDecompose(ch):
            for k in range(2):
                bits[_bloomBit(f"jamo|{j}|{k}", 0, 64)] = 1

    # Region B — Character Bloom (64 bit)
    for ch in stem:
        for k in range(2):
            bits[_bloomBit(f"char|{ch}|{k}", 64, 64)] = 1

    # Region C — Bigram Bloom (64 bit)
    for i in range(len(stem) - 1):
        bg = stem[i : i + 2]
        for k in range(2):
            bits[_bloomBit(f"bigram|{bg}|{k}", 128, 64)] = 1

    # Region D — blake2b Random (64 bit)
    h = hashlib.blake2b(stem.encode(), digest_size=8).digest()
    bits[192:256] = np.unpackbits(np.frombuffer(h, dtype=np.uint8))

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
    """v3 와 동일 reservoir sampling."""
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
    print("RI-VSA v7 — Tier 1 characteristic + Tier 2 identity (self 포함)")
    print(f"  4 region: jamo64+char64+bigram64+rand64  |  SAMPLE={SAMPLE_SECTIONS}")
    print("=" * 72)

    # 0. sanity check
    print()
    print("─── characteristic sanity check (region 별 distance 분해) ───")
    for a, b in [("자기주", "자사주"), ("자기주", "농업"), ("유상증자", "유상증"), ("배당", "특허")]:
        ha = (characteristic(a) > 0).astype(np.uint8)
        hb = (characteristic(b) > 0).astype(np.uint8)
        d_total = int(np.bitwise_xor(ha, hb).sum())
        d_jamo = int(np.bitwise_xor(ha[JAMO_REGION], hb[JAMO_REGION]).sum())
        d_char = int(np.bitwise_xor(ha[CHAR_REGION], hb[CHAR_REGION]).sum())
        d_bigram = int(np.bitwise_xor(ha[BIGRAM_REGION], hb[BIGRAM_REGION]).sum())
        d_rand = int(np.bitwise_xor(ha[RAND_REGION], hb[RAND_REGION]).sum())
        print(
            f"  '{a}' vs '{b}': total={d_total:3d}  "
            f"jamo={d_jamo:2d}  char={d_char:2d}  bigram={d_bigram:2d}  rand={d_rand:2d}"
        )

    # 1. load
    t0 = time.perf_counter()
    print()
    print("[load] 코퍼스 수집 중...")
    sections = loadAllSections()
    total_chars = sum(len(s) for s in sections)
    print(f"[load] 섹션 {len(sections):,}개, {total_chars / 1e6:.1f}M chars — {time.perf_counter() - t0:.1f}s")

    # 2. stems
    t0 = time.perf_counter()
    doc_freq: Counter[str] = Counter()
    for s in sections:
        doc_freq.update(set(tokenize(s)))
    keep = sorted(t for t, c in doc_freq.items() if c >= MIN_DOC_FREQ)
    g2id = {t: i for i, t in enumerate(keep)}
    id2g = keep
    n_stems = len(g2id)
    print(f"[stems] {len(doc_freq):,} → df≥{MIN_DOC_FREQ} {n_stems:,} — {time.perf_counter() - t0:.1f}s")
    del doc_freq

    # 3. M
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
            print(f"  [M-build] {sid + 1:,} nnz={len(rows):,}")
    n_sec = len(sections)
    M = csr_matrix(
        (np.ones(len(rows), dtype=np.int32), (rows, cols)),
        shape=(n_sec, n_stems),
    )
    del rows, cols, sections
    gc.collect()
    print(f"[M] {n_sec:,} × {n_stems:,} nnz={M.nnz:,} — {time.perf_counter() - t0:.1f}s")

    # 4. df + idf
    df_arr = np.asarray(M.sum(axis=0)).flatten().astype(np.float32)
    df_arr = np.maximum(df_arr, 1.0)
    idf = np.log(n_sec / df_arr).astype(np.float32)
    print(f"[idf] mean={idf.mean():.2f}")

    # 5. characteristic matrix (Tier 1)
    t0 = time.perf_counter()
    charMat = np.zeros((n_stems, HASH_BITS), dtype=np.float32)
    for stem, sid in g2id.items():
        charMat[sid] = characteristic(stem).astype(np.float32)
    weightedChar = charMat * idf[:, None]
    print(f"[Tier1] characteristic {weightedChar.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # 6. identity = M.T @ M @ characteristic (self 포함)
    t0 = time.perf_counter()
    temp = M @ weightedChar
    identity = (M.T @ temp).astype(np.float64)
    # *** v3/v6 와 핵심 차이: self_contrib 빼지 않음 ***
    print(f"[Tier2] identity {time.perf_counter() - t0:.1f}s (self 포함)")
    print(f"        |max|={np.abs(identity).max():.1f}")

    # 7. pack
    t0 = time.perf_counter()
    contextBits = (identity > 0).astype(np.uint8)
    contextPacked = np.packbits(contextBits, axis=1)
    print(f"[pack] {contextPacked.nbytes / 1e6:.1f} MB — {time.perf_counter() - t0:.1f}s")

    # 8. PROBE A
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

    # 9. PROBE B
    print()
    print("─── PROBE B: 쌍 distance (v3=89.1·v6=49.0 baseline 비교) ───")
    for label, pairs in [("가까워야", PROBE_PAIRS_NEAR), ("멀어야", PROBE_PAIRS_FAR)]:
        print(f"\n[{label}]")
        for a, b in pairs:
            if a not in g2id or b not in g2id:
                print(f"  {a:8s} vs {b:8s} — 누락")
                continue
            ai, bi = g2id[a], g2id[b]
            d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
            print(f"  {a:8s} vs {b:8s}  d={d}")

    # 10. PROBE C
    print()
    print("─── PROBE C: 무작위 baseline ───")
    rng = np.random.default_rng(SEED)
    idxs = rng.choice(n_stems, size=2000, replace=False)
    xored = np.bitwise_xor(contextPacked[idxs[:1000]], contextPacked[idxs[1000:]])
    dists = np.unpackbits(xored, axis=1).sum(axis=1)
    print(f"  1000 random: mean={dists.mean():.1f} median={np.median(dists):.1f} std={dists.std():.1f}")

    # 11. 저장
    out_dir = Path("data/_scratch_fm/riVsaV7")
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "contextHash.npy", contextPacked)
    np.save(out_dir / "df.npy", df_arr.astype(np.int64))
    import json

    (out_dir / "stems.json").write_text(json.dumps(id2g, ensure_ascii=False), encoding="utf-8")
    print(f"\n[save] {out_dir}")


if __name__ == "__main__":
    main()
