"""Random Indexing + VSA 의미 해시 — RI-VSA.

목적
----
의미를 *학습된 임베딩* 없이, *역인덱스 구조 + 결정론적 해시* 만으로 구축.
사용자 아이디어 정확화: "문장 MinHash + 안에 토큰별 MinHash + 토큰 해시는
주변 해시로 결정". 이게 곧 Sahlgren (2005) 의 Random Indexing + Kanerva 의 VSA.

동기
----
- vector embedding: 학습 필요, 메모리 2~3× 텍스트, 증분 X — 거부 조건
- BM25 / suffix array: 글자 매칭만, 의미 X
- doc2query: LLM 필요, sweep 비용
- RI-VSA: 학습 0, 메모리 <1% 텍스트, 증분 자연, *분포 의미* 만으로 의미 잡힘

agipath v7 (postingTable + 7 사전계산필드) 와 결합 시 자연스럽게 다음 layer.
dartlab 의 DART 도메인 corpus 가 *작고 도메인 일관성 높은* sandbox.

연결
----
agipath core spec 의 핵심 원칙:
- "이해 = 수평선 근사 stem 들의 posting 경험"
- "역인덱스가 유일한 기본 구조"
- "별도 벡터 학습 제안 금지"

RI-VSA 는 위 원칙 안에서 *분포 의미* 를 256-bit 결정론 해시에 적재한다.
indexHash = 정체성 (blake2b), contextHash = 의미 (이웃 누적), sentenceHash =
맥락 (구성). 셋 다 같은 해시 공간 → Hamming distance 단일 척도.

방법
----
Layer 1. indexHash[stem] = blake2b(stem, 32 byte)  → 256-bit
         결정론적, 학습 X, 같은 stem 항상 같은 해시.

Layer 2. contextHash[stem] = 분포 누적 결과
         counter[stem][256] 에 sweep 동안:
           각 stem 등장마다 → 윈도우 K 내 이웃 stem 의
           indexHash(±1 변환) 을 누적 add
         counter > 0 인 bit = 1, else 0 → 256-bit 의미 해시.
         의미 = "이 stem 이 어떤 이웃과 자주 등장하나" 의 압축.

Layer 3. sentenceHash[section] = XOR{ contextHash[s_i] for s_i in section }
         (위치 보존 회전은 v2 에서 추가)

Layer 4. 의미 검색
         query → tokenize → contextHash bundle → 모든 stem/section 과
         Hamming distance → 가까운 것 retrieval.

메모리 (53 일치 dartlab 30K 섹션 sample)
-------------------------------------
- 고유 trigram (doc_freq ≥ 10): ~200K
- idxHashes: 200K × 256 × int8 = 50 MB
- counter (build 중): 200K × 256 × int32 = 200 MB
- 최종 contextHash: 200K × 32 byte = 6 MB
- peak < 500 MB. 전 OOM 사고 (20 GB) 와 비교 40× 작음.

기대 결과
--------
1. "유상증자" 의 Hamming-가까운 trigram 상위 = {신주, 발행, 청약, 자본금, 운영자금, ...}
   같은 *공기어*. 학습 모델 없이.
2. 무관 쌍 (유상증자 vs 공장화재) 은 Hamming distance 멀어야 함.
3. 같은 의미 문장 (sentenceHash) 은 짧은 Hamming distance.

이 셋 중 1 만 보여도 RI-VSA 가 *분포 의미* 를 잡는 증명. 2, 3 까지 가면 검색
엔진 base 로 직진 가능.

비고
----
- 회귀 가드 아님. 시도용 보관.
- v1: 위치 회전 없음 (bag-of-context). v2 에서 rotateBits 추가.
- 30K 섹션 sample. scale up 검증은 agipath core 본진 (12M stems) 으로 이식 후.

결과 (2026-05-20, 65 일치 dartlab 본문 30K 섹션 sample)
---------------------------------------------------
- 빌드: load 11s + stems 9s + idxHash 0.4s + Pass2 762s + finalize 0s = **약 13 분**
- 메모리 peak: ~200 MB (Python set OOM 사고 20+ GB 와 비교 100× 작음)
- 87,739 trigram (doc_freq ≥ 10) × 256 bit = 최종 contextHash **2.8 MB**

PROBE A — 의미 이웃 (Hamming distance 가까운 상위 trigram):
- 전환사 (전환사채, freq 1889): d=63 사채권 / d=63 환사채 / d=64 채권 / d=70 교환사 — *채권 류 자동 묶임*
- 차입금 (freq 1310): d=67 장기차 / d=71 기차입 / d=77 단기차 / d=80 차입 — *만기별 차입 자동 묶임*
- 자기주 (자기주식, freq 1837): d=58 식 취 (취득) / d=65  자기 / d=71  소각 — **액션 (취득/소각) 잡힘**
- 주주총 (주주총회, freq 5597): d=59 정기주 / d=64  정기 / d=68 총회 / d=69 총회일 — *시점 변형 묶임*
- 최대주 (최대주주, freq 2810): d=59 주주와 / d=72  최대 / d=78 주변경 — **변경 액션 잡힘**

PROBE B — 의미 쌍 distance:
- 대표이 vs 대표자: d=102 (mean 125.6 대비 23 점 가까움 = 신호 ○)
- 자기주 vs 자사주: d=130 (mean 과 동일 = 신호 ×)
  → "자기주식" 과 "자사주" 가 *다른 문서 장르* 에 등장 → 분포 분리됨.
    사람 직관 동의어지만 RI-VSA 는 공기어 분포만 봄. 한계 명확.

PROBE C — 무작위 baseline:
- 무작위 1000 쌍 Hamming: mean=125.6, median=126, std=9.4 (이론 128 에 근접)
- 의미 쌍 d=53~77 = mean 대비 약 2~3σ 강한 신호

결론
----
- ○ 작동 — 공기 의미 (report_type 내부, 액션, 시점) 분포 누적만으로 자동 묶임
- ○ 메모리 vector 의 1% 이하, 학습 모델 0, 결정론 100%, 증분 자연 (counter ++)
- × 장르 다른 동의어 (자기주↔자사주) 못 묶음 — agipath rootDict / CTT 같은 동의 layer 보강 필수
- × 저빈도 stem (HBM freq 16) 분포 신호 약함 — 충분한 corpus 누적 필요

다음 단계 후보
-------------
- v2: 위치 회전 (rotateBits) 추가, K 윈도우 확장 (5→10) 비교
- v3: bigram + trigram 동시 인덱싱
- v4: agipath rootDict / CTT 동의 layer 결합 → 동의어 갭 메움
- scale up: agipath core 본진 (wiki + 우리말샘 12M stems) 이식
"""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

# ── 설정 ──
HASH_BITS = 256
HASH_BYTES = HASH_BITS // 8  # 32
NGRAM_N = 3
WINDOW_K = 5  # 이웃 윈도우 (앞/뒤 각 K)
MIN_DOC_FREQ = 10  # trigram 이 등장한 섹션 수 최소
MAX_NGRAMS_PER_SECTION = 2000  # 긴 섹션 cap (메모리 보호)
SAMPLE_SECTIONS = 30000  # 표본 크기 (53 일치 417K 중)
TOP_K = 15
SEED = 42

INPUT_DIR = Path("data/dart/allFilings")
PROBE_TERMS = [
    "유상증자",
    "전환사",
    "차입금",
    "자기주",
    "대표이",
    "주주총",
    "합병",
    "특허",
    "소송",
    "최대주",
    "임원ㆍ",
    "HBM",
]
PROBE_PAIRS_NEAR = [
    ("유상증자", "신주발"),
    ("유상증자", "전환사"),
    ("차입금", "사채"),
    ("자기주", "자사주"),
    ("대표이", "대표자"),
    ("합병", "인수"),
]
PROBE_PAIRS_FAR = [
    ("유상증자", "공장화"),
    ("배당금", "특허"),
    ("HBM", "농업"),
]


def indexHashSigned(stem: str) -> np.ndarray:
    """blake2b → 256 dim ±1 signed array (int8)."""
    h = hashlib.blake2b(stem.encode(), digest_size=HASH_BYTES).digest()
    bits = np.unpackbits(np.frombuffer(h, dtype=np.uint8))
    return bits.astype(np.int8) * 2 - 1


def main() -> None:
    print("=" * 72)
    print("RI-VSA — 결정론 해시 + 분포 누적 + Hamming")
    print(f"  NGRAM_N={NGRAM_N}  WINDOW_K={WINDOW_K}  MIN_DF={MIN_DOC_FREQ}")
    print(f"  HASH_BITS={HASH_BITS}  SAMPLE={SAMPLE_SECTIONS}")
    print("=" * 72)

    # ── 1. 로드 + 표본 ──
    t0 = time.perf_counter()
    files = sorted(p for p in INPUT_DIR.glob("2026*.parquet") if "_meta" not in p.name)
    df = pl.concat(
        [pl.read_parquet(f, columns=["section_content"]).filter(pl.col("section_content").is_not_null()) for f in files]
    )
    if df.height > SAMPLE_SECTIONS:
        df = df.sample(SAMPLE_SECTIONS, seed=SEED)
    sections = df["section_content"].to_list()
    total_chars = sum(len(s) for s in sections)
    print(
        f"[load] {len(files)} 일치 → 섹션 {len(sections):,} 샘플, "
        f"총 {total_chars / 1e6:.1f}M chars, {time.perf_counter() - t0:.1f}s"
    )

    # ── 2. Pass 1: trigram doc_freq ──
    t0 = time.perf_counter()
    doc_freq: Counter[str] = Counter()
    for s in sections:
        n_max = min(len(s) - NGRAM_N + 1, MAX_NGRAMS_PER_SECTION)
        if n_max <= 0:
            continue
        # 섹션 내 unique trigram (doc_freq 용)
        seen = set()
        for i in range(n_max):
            seen.add(s[i : i + NGRAM_N])
        doc_freq.update(seen)
    keep = [t for t, c in doc_freq.items() if c >= MIN_DOC_FREQ]
    keep.sort()
    g2id = {t: i for i, t in enumerate(keep)}
    id2g = keep  # list indexable by id
    n_stems = len(g2id)
    print(f"[stems] 전체 {len(doc_freq):,} → doc_freq≥{MIN_DOC_FREQ} {n_stems:,}, {time.perf_counter() - t0:.1f}s")

    # ── 3. idxHashes ──
    t0 = time.perf_counter()
    idxHashes = np.zeros((n_stems, HASH_BITS), dtype=np.int8)
    for stem, sid in g2id.items():
        idxHashes[sid] = indexHashSigned(stem)
    print(f"[idxHash] {idxHashes.nbytes / 1e6:.1f} MB, {time.perf_counter() - t0:.1f}s")

    # ── 4. Pass 2: contextHash counter 누적 ──
    t0 = time.perf_counter()
    counter = np.zeros((n_stems, HASH_BITS), dtype=np.int32)

    for sec_idx, s in enumerate(sections):
        n_max = min(len(s) - NGRAM_N + 1, MAX_NGRAMS_PER_SECTION)
        if n_max <= 0:
            continue
        # 섹션 trigram 순서 id list
        ids = []
        for i in range(n_max):
            sid = g2id.get(s[i : i + NGRAM_N])
            if sid is not None:
                ids.append(sid)
        if len(ids) < 2:
            continue
        ids = np.asarray(ids, dtype=np.int32)
        n = len(ids)
        # 각 delta 별 누적 (대칭)
        for delta in range(1, WINDOW_K + 1):
            if n <= delta:
                break
            # forward: stem at i, neighbor at i+delta
            src = ids[: n - delta]
            nbr = ids[delta:]
            np.add.at(counter, src, idxHashes[nbr].astype(np.int32))
            # backward: stem at i+delta, neighbor at i
            np.add.at(counter, nbr, idxHashes[src].astype(np.int32))

        if (sec_idx + 1) % 5000 == 0:
            print(f"  [pass2] {sec_idx + 1:,}/{len(sections):,} sections, peak counter |max|={np.abs(counter).max()}")
    print(f"[context] counter 누적 완료, |max|={np.abs(counter).max()}, {time.perf_counter() - t0:.1f}s")

    # ── 5. Finalize contextHash → packed bits ──
    t0 = time.perf_counter()
    contextBits = (counter > 0).astype(np.uint8)
    contextPacked = np.packbits(contextBits, axis=1)  # (n_stems, 32)
    print(f"[finalize] contextHash packed {contextPacked.nbytes / 1e6:.1f} MB, {time.perf_counter() - t0:.1f}s")

    # ── 6. Probe — 의미 이웃 ──
    print()
    print(f"─── PROBE A: 의미 이웃 (Hamming 가까운 trigram 상위 {TOP_K}) ───")
    df_arr = np.asarray([doc_freq[id2g[i]] for i in range(n_stems)])
    for term in PROBE_TERMS:
        if term not in g2id:
            print(f'\n? "{term}" — 인덱스 없음 (doc_freq < {MIN_DOC_FREQ})')
            continue
        sid = g2id[term]
        xored = np.bitwise_xor(contextPacked, contextPacked[sid : sid + 1])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        nearest = np.argpartition(dist, TOP_K + 1)[: TOP_K + 1]
        nearest = sorted(nearest, key=lambda i: dist[i])
        nearest = [i for i in nearest if i != sid][:TOP_K]
        print(f'\n? "{term}"  (id={sid}  doc_freq={doc_freq[term]:,})')
        for i in nearest:
            print(f"    d={int(dist[i]):3d}  df={df_arr[i]:>6d}  {id2g[i]}")

    # ── 7. Probe — 가까울/멀 쌍 검증 ──
    print()
    print("─── PROBE B: 의미 쌍 Hamming distance ───")
    print("\n[가까워야]")
    for a, b in PROBE_PAIRS_NEAR:
        if a not in g2id or b not in g2id:
            print(f"  {a:8s} vs {b:8s} — 누락")
            continue
        ai, bi = g2id[a], g2id[b]
        d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
        print(f"  {a:8s} vs {b:8s}  d={d}")
    print("\n[멀어야]")
    for a, b in PROBE_PAIRS_FAR:
        if a not in g2id or b not in g2id:
            print(f"  {a:8s} vs {b:8s} — 누락")
            continue
        ai, bi = g2id[a], g2id[b]
        d = int(np.unpackbits(np.bitwise_xor(contextPacked[ai], contextPacked[bi])).sum())
        print(f"  {a:8s} vs {b:8s}  d={d}")

    # ── 8. Probe — Hamming distance 분포 ──
    print()
    print("─── PROBE C: 전체 stem 쌍 Hamming distance 분포 ───")
    # 1000 무작위 쌍
    rng = np.random.default_rng(SEED)
    idxs = rng.choice(n_stems, size=2000, replace=False)
    a = idxs[:1000]
    b = idxs[1000:]
    xored = np.bitwise_xor(contextPacked[a], contextPacked[b])
    dists = np.unpackbits(xored, axis=1).sum(axis=1)
    print("  무작위 1000 쌍 Hamming distance:")
    print(
        f"    mean={dists.mean():.1f}  median={np.median(dists):.1f}  "
        f"std={dists.std():.1f}  min={dists.min()}  max={dists.max()}"
    )
    print("  (256-bit 무작위 = mean 128 예상. 가까운 쌍은 mean 보다 작아야 의미 있음.)")


if __name__ == "__main__":
    main()
