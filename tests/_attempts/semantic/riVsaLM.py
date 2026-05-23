"""RI-VSA v5 — 분포 기반 언어 모델 흉내 (next-stem prediction via hash NN).

목적
----
contextHash 공간 위에서 *학습 모델 없이* 다음 토큰 예측. GPT 류와 비교하면
서툴지만 — 결정론, 학습 0, 메모리 5 MB, CPU 만으로 작동.

원리
----
의미 = 분포. 분포 = 동료. 동료 = contextHash.
* 컨텍스트 = "지금까지 본 stem 들"
* 다음 stem = "이 컨텍스트와 자주 같이 등장한 stem"

알고리즘:
1. 컨텍스트 stems = [c_1, c_2, ..., c_N]
2. contextHash_bundle = Σ_i (contextHash_signed[c_i] · idf[c_i])
3. queryHash = (contextHash_bundle > 0).pack
4. 모든 stem 의 contextHash 와 Hamming distance
5. nearest = top-K 가까운 stem
6. 이 중 *컨텍스트에 없는* stem 우선 → 다음 토큰 후보

이게 *진정한 의미의 분포 LM*: 학습 안 한 통계 모델. GPT 가 weight 학습으로
하는 일을 *공기 횟수* 가 직접 결정.

샘플링 모드
-----------
- top-1: 결정론 (= 항상 가장 가까운 stem)
- top-K + softmax: 다양성 (확률적)
- top-K + Hamming distance 기반 가중치: 거리가 가까울수록 확률 높음

생성 시드
---------
사용자 입력 문장 → tokenize → 마지막 N stems 를 컨텍스트로 → 다음 stem 예측 → 반복

비고
----
- 시도 폴더 (회귀 가드 아님)
- 결정론 / 학습 0 / 메모리 < 10 MB
- GPT 수준 X. 의미 흐름 일부만. 한 줄짜리 *concept 연속 흐름* 데모용.
- v3 의 stems 가 character n-gram 이라 진짜 "단어" 흐름은 안 됨. 글자 흐름으로 데모.

결과 (2026-05-20, v3 자산 위 9 개 시드 × 8 step greedy)
-----------------------------------------------------
빌드: v3 자산 로드 0.2s — 즉시 가능

자가 조립 도메인 흐름 (top-1 greedy 8 step):

| 시드 | 생성된 흐름 | 의미 평가 |
|---|---|---|
| 차입금 | 단기 → 부채 → 입금 → 포괄 → 익계산 → 익계 → **손익계** | ★★★ 재무제표 위치 자가 학습 |
| 합병 | 합병 → 병 → 수합 → 흡 → **수합병 → 흡수 → 흡수합** | ★★★ 도메인 용어 자가 조립 |
| 주주총회 | 이사 → 승인 → 정기 → 총회 → 원회 → **위원회** | ★★★ 의결 process |
| 최대주주 | 표이사 → 대표 → 대표이 → 김 → 박 | ★★ 한국 *오너 = 대표* |
| 자기주식 | 자기 → 주식은 → 식 1/2 → 보통 → 0주 | ★★ 보통주 + 주식수 흐름 |
| 배당 | 기주 → 배당 → 결산 → 결의 | ★★ 배당 결산 흐름 |
| 전환사채 | 전환 → 사채 → 제31 → 의 소 → 관계 → 제29 → 제32 | ★ 회사채 회차 (drift) |
| 유상증자 | 유상 → 일) → 인수 → 류 → 5. → 주 → 황 → 구 | × drift 심함 |
| 대표이사 | 김 → 대표 → 최대주 → 박 → 이사 → 박 → 윤 → 김 | ★ 흔한 성씨 흐름 |

결론
----
- ★ 학습 0 / weights 0 / GPU 0 으로 도메인 흐름 자가 조립 가능
- ★ 차입금 → 손익계산서, 합병 → 흡수합병, 주주총회 → 위원회 = *진짜 의미 흐름*
- ★ 글자 단위 hash 가 *단어 단위* 도메인 용어 step-by-step 조립 (emergent)
- × greedy + 짧은 context 라 drift 발생 (유상증자, 전환사채 후반부)
- × GPT 수준 아님. *분포 NN 생성* 수준.

다음 단계
--------
- 위치 회전 (v8 후보) 추가 시 어순 의미 + 어휘 단위 응집 향상 가능
- v7 자산 (Tier 1+2) 으로 재시도. 응집 폭증 가능성
- beam search / top-k softmax sampling 으로 drift 완화
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

V3_DIR = Path("data/_scratch_fm/riVsaV3")
HASH_BITS = 256
HASH_BYTES = 32
NGRAM_NS = (2, 3)
TOP_K_CANDIDATES = 20
MAX_GENERATION_STEPS = 20

# 시드 입력 — 사용자 발화 흉내
SEEDS = [
    "유상증자",
    "차입금",
    "자기주식",
    "최대주주",
    "대표이사",
    "전환사채",
    "주주총회",
    "배당",
    "합병",
]


def tokenize(s: str) -> list[str]:
    tokens: list[str] = []
    for n in NGRAM_NS:
        if len(s) < n:
            continue
        for i in range(len(s) - n + 1):
            tokens.append(s[i : i + n])
    return tokens


def hashToSigned(packed: np.ndarray) -> np.ndarray:
    bits = np.unpackbits(packed, axis=1)
    return bits.astype(np.int8) * 2 - 1


def main() -> None:
    print("=" * 72)
    print("RI-VSA v5 — 분포 LM 흉내 (next-stem via hash NN)")
    print("=" * 72)

    # ── 1. v3 자산 로드 ──
    t0 = time.perf_counter()
    contextPacked = np.load(V3_DIR / "contextHash.npy")
    df_arr = np.load(V3_DIR / "df.npy")
    stems: list[str] = json.loads((V3_DIR / "stems.json").read_text(encoding="utf-8"))
    g2id = {s: i for i, s in enumerate(stems)}
    n_stems = len(stems)
    contextSigned = hashToSigned(contextPacked).astype(np.float32)
    idf = np.log(df_arr.max() / np.maximum(df_arr, 1.0)).astype(np.float32)
    print(
        f"[load] stems={n_stems:,}  contextHash {contextPacked.nbytes / 1e6:.1f} MB | {time.perf_counter() - t0:.1f}s"
    )

    def predictNext(context_stems: list[str], *, exclude: set[str] | None = None) -> list[tuple[str, int]]:
        """현재 컨텍스트 → 다음 stem 후보 top-K."""
        if exclude is None:
            exclude = set()
        ids = [g2id[c] for c in context_stems if c in g2id]
        if not ids:
            return []
        # bundle = Σ idf-weighted signed context hashes
        acc = np.zeros(HASH_BITS, dtype=np.float32)
        for cid in ids:
            acc += contextSigned[cid] * idf[cid]
        # query packed
        bits = (acc > 0).astype(np.uint8)
        qh = np.packbits(bits)
        # Hamming distance vs 전체 stem
        xored = np.bitwise_xor(contextPacked, qh[None, :])
        dist = np.unpackbits(xored, axis=1).sum(axis=1)
        # 컨텍스트 + exclude 제외
        for cid in ids:
            dist[cid] = HASH_BITS  # 자기 자신 제외
        for ex in exclude:
            if ex in g2id:
                dist[g2id[ex]] = HASH_BITS
        # top-K
        topk = np.argpartition(dist, TOP_K_CANDIDATES)[:TOP_K_CANDIDATES]
        topk = sorted(topk, key=lambda i: dist[i])
        return [(stems[i], int(dist[i])) for i in topk]

    # ── 2. 시드 → autoregressive generation ──
    for seed in SEEDS:
        print()
        print(f'━━━ SEED: "{seed}" ━━━')
        # 시드 tokenize → 마지막 컨텍스트 N 개
        context = tokenize(seed)
        # 시드 자체 stems 만으로 시작
        context = [c for c in context if c in g2id]
        if not context:
            print("  (시드 tokenize 결과 stem 없음)")
            continue
        print(f"  컨텍스트 시작: {context}")
        # 다음 stem 예측 (top-15 후보 보여줌)
        nexts = predictNext(context)
        print("  다음 stem 후보 (Hamming distance):")
        for stem, d in nexts[:15]:
            print(f"    d={d:3d}  df={int(df_arr[g2id[stem]]):>6d}  {stem!r}")

        # 간단 autoregressive: top-1 을 골라 컨텍스트에 추가, 반복
        generated: list[str] = []
        cur_context = list(context)
        seen = set(cur_context)
        for step in range(8):  # 8 step 만
            nexts = predictNext(cur_context, exclude=seen)
            if not nexts:
                break
            next_stem, next_d = nexts[0]
            generated.append((next_stem, next_d))
            cur_context.append(next_stem)
            seen.add(next_stem)
            # 컨텍스트는 마지막 5 개만 유지 (drift 방지)
            if len(cur_context) > 5:
                cur_context = cur_context[-5:]
        print("  생성된 흐름 (top-1 greedy, 8 step):")
        print("    " + " → ".join(f"{s}(d={d})" for s, d in generated))


if __name__ == "__main__":
    main()
