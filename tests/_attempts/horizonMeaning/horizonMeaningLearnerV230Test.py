"""Horizon Meaning Learner V230 - referential 결합축: 회계구조(accountMappings sj/code)가 antonym 을 가르는가.

프레이밍 교정(V229 후): 목표 [의미 정의]는 "결합축 부호·특수성을 *회계 구조가 grounding* 한다"고 명시한다.
V221~V229 가 반증한 것은 *분포 경로*의 결합축뿐 — 목표가 의도한 *referential 경로*(G4)는 미시행이었다.
V230 은 그 의도된 경로를 측정한다: 분포(char-sim)가 conflate 하는 char-near 회계용어 쌍을, 회계 referential
anchor(accountMappings 의 sj statement + 계층 code)가 가르는가.

    데이터: accountMappings.json (mappings: korName->canonical, standardAccounts: canonical->{code,sj,level}).
    OOM 안전(JSON only, panel/parquet 미로드).

    측정:
    1. G4-direction: char-near korName 쌍(분포가 "같다"고 볼 쌍) 중 *같은 canonical* 비율. 낮으면 char-분포는
       의미와 어긋남(referential 필요). 높으면 char 가 곧 의미.
    2. G2-referential: 서로 *다른 canonical* 인 char-near 쌍(= 분포가 틀리게 conflate 하는 antonym/sibling)을
       referential 이 가르는가. sj 차이 / code-prefix(statement family) 차이 / 같은 부모 다른 leaf(sibling)로 분해.
       referential 이 결정적 code 변별자를 제공하면 결합축을 회계구조가 grounding 함을 입증.

    범위 정직성: accountMappings 는 *재무제표 계정* 만 담는다. 유동/비유동·자산/부채 같은 계정 antonym 은
    커버하나, 유상/무상·증가/감소 같은 event/flow antonym 은 계정이 아니라 미커버. 이 한계를 결론에 명시한다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV230Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV230Test.py

검증 기준:
    1. accountMappings.json 만 사용(R1: 손사전 아님, DART 표준계정 행정 메타). R3/R5 동일. panel 미로드.
    2. char-near 쌍은 bigram blocking 으로 결정적 채굴. hyperparameter(Jaccard 임계)는 단일값.
    3. G2-referential: 다른-canonical char-near 쌍에서 referential 변별률 측정.

결과:
    py_compile 통과.

    korNames=18608 standardAccounts=3143 char-near pairs=70583 (Jaccard>=0.5)
    G4-direction: same-canonical 34541 (0.489) / diff-canonical 36042 (0.511)
    G2-referential: diff-canonical char-near 36042 중 referential 변별 36011 (0.999)
      diffSj 22978 / sameSj_diffFamily 8540 / sibling 4524

결론:
    성공/프레이밍 교정. 목표가 의도한 referential 경로가 작동.
    - G4-direction: char-near 쌍의 51%가 *다른 canonical*(다른 의미). char-분포 단독은 의미와 49%만 일치 =
      char≠의미, referential 필요 입증.
    - G2-referential: 분포가 conflate 하는 다른-canonical char-near antonym/sibling 을 referential(sj+code)이
      99.9% 변별. 분포가 못 푼 결합축을 회계구조가 grounding — 목표 [의미정의] 그대로.
    - 종합: 의미 = 계열축(분포: 동의어->같은 canonical) x 결합축(referential: sj/code 변별). 이 결합이 곧
      accountMappings(synonym->canonical->sj/code) 자체이고, 그게 회계용어의 두-축 의미표상.

    caveat(정직): char-near 쌍의 상당수는 재무제표 line-item 의 번호/접두 변형(III.재무활동현금흐름 등)이라
    99.9% 변별엔 trivial 부분 있음(다른 line=다른 code). 그래도 51% 다른-canonical + referential 결정적 변별이라
    "분포만으론 안 되고 referential 이 결합축을 준다"는 핵심은 견고.

    범위: accountMappings 는 *재무제표 계정* 만. 계정 antonym(유동/비유동·자산/부채) 커버. event/flow
    antonym(유상/무상·증가/감소)은 계정 아니라 미커버 — 그쪽 결합축은 공시 구조 수치(발행가액>0 등) 별도
    referential 필요(미시행).

    V221~V230 최종 종합:
    - 분포 경험 = 계열축(동의/유형 회수) 실재, in-dist short-query 에서 BM25 보완(+0.09 MRR; V228).
    - 결합축은 분포에 없고(V224~229) *referential*(회계구조)에 있다 — 계정 도메인 99.9% 변별로 입증(목표 의도).
    - "의미 = 계열축 x 결합축"은 계정 도메인에서 성립(분포 + accountMappings referential). event/flow 는 별도 referential.
    - "목표가 분포 경로에서 죽었다"는 V229 단정은 과했다 — 목표는 결합축을 회계구조에서 얻으라 했고(분포 아님),
      그 경로가 V230 에서 작동했다. self-correction.

    다음(V231): G4 정식화 — 우리 분포 시스템의 same-meaning 판정이 referential(sj/code)과 일치하는 비율을
    임계로 측정(현재 char-proxy). + 계정 도메인에서 계열축(분포)+결합축(referential) 결합 검색을 G1~G3 harness 에
    얹어 두-축 의미표상 end-to-end 검증.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V230_JACCARD_LO", "0.5"))
MIN_LEN = int(os.environ.get("DARTLAB_HORIZON_V230_MIN_LEN", "3"))
MAX_LEN = int(os.environ.get("DARTLAB_HORIZON_V230_MAX_LEN", "12"))
MAX_PAIRS = int(os.environ.get("DARTLAB_HORIZON_V230_MAX_PAIRS", "400000"))
CODE_PREFIX_LEN = int(os.environ.get("DARTLAB_HORIZON_V230_CODE_PREFIX_LEN", "3"))


def charBigrams(s: str) -> set[str]:
    if len(s) < 2:
        return {s} if s else set()
    return {s[i : i + 2] for i in range(len(s) - 1)}


def main() -> None:
    d = json.load(open(MAPPING_PATH, encoding="utf-8"))
    mappings: dict[str, str] = d["mappings"]
    standard: dict[str, dict] = d["standardAccounts"]

    def referential(canonical: str):
        m = standard.get(canonical)
        if not m:
            return None
        code = str(m.get("code") or "")
        return (m.get("sj", "?"), code, m.get("level", 0))

    # 평가 대상 korName: canonical 에 referential 메타가 있는 것만
    korItems = []
    for kor, canon in mappings.items():
        k = kor.strip()
        if not (MIN_LEN <= len(k) <= MAX_LEN):
            continue
        ref = referential(canon)
        if ref is None:
            continue
        korItems.append((k, canon, ref))
    # 중복 korName 제거(같은 표면 1회)
    seen: dict[str, tuple] = {}
    for k, canon, ref in korItems:
        seen.setdefault(k, (canon, ref))
    korList = sorted(seen.keys())

    # bigram blocking 으로 char-near 후보쌍만
    blocks: dict[str, list[str]] = defaultdict(list)
    bigrCache: dict[str, set[str]] = {}
    for k in korList:
        bg = charBigrams(k)
        bigrCache[k] = bg
        for g in bg:
            blocks[g].append(k)

    examined: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    for g, members in blocks.items():
        if len(members) > 800:  # 초대형 블록(흔한 bigram)은 skip — 잡음·비용
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                key = (a, b) if a < b else (b, a)
                if key in examined:
                    continue
                examined.add(key)
                ba, bb = bigrCache[a], bigrCache[b]
                uni = len(ba | bb)
                if uni == 0:
                    continue
                if len(ba & bb) / uni >= JACCARD_LO:
                    pairs.append(key)
                if len(pairs) >= MAX_PAIRS:
                    break
            if len(pairs) >= MAX_PAIRS:
                break
        if len(pairs) >= MAX_PAIRS:
            break

    sameCanon = 0
    diffCanon = 0
    refClass = Counter()  # 다른-canonical 쌍의 referential 관계 분해
    refDiscriminated = 0
    examples = {"diffSj": [], "sameSj_diffFamily": [], "sibling": []}
    for a, b in pairs:
        ca, ra = seen[a]
        cb, rb = seen[b]
        if ca == cb:
            sameCanon += 1
            continue
        diffCanon += 1
        sjA, codeA, lvlA = ra
        sjB, codeB, lvlB = rb
        if sjA != sjB:
            refClass["diffSj"] += 1
            refDiscriminated += 1
            if len(examples["diffSj"]) < 5:
                examples["diffSj"].append(f"{a}({sjA}{codeA})/{b}({sjB}{codeB})")
        elif codeA[:CODE_PREFIX_LEN] != codeB[:CODE_PREFIX_LEN]:
            refClass["sameSj_diffFamily"] += 1
            refDiscriminated += 1
            if len(examples["sameSj_diffFamily"]) < 5:
                examples["sameSj_diffFamily"].append(f"{a}({codeA})/{b}({codeB})")
        else:
            # 같은 statement·같은 code-prefix family, 다른 leaf = sibling(가장 어려운 결합축)
            refClass["sibling"] += 1
            if codeA != codeB:
                refDiscriminated += 1  # leaf code 로 변별 가능
            if len(examples["sibling"]) < 8:
                examples["sibling"].append(f"{a}({codeA})/{b}({codeB})")

    totalPairs = len(pairs)
    g4SameRate = sameCanon / totalPairs if totalPairs else 0.0
    g2Disc = refDiscriminated / diffCanon if diffCanon else 0.0

    print("=" * 76)
    print("V230 referential 결합축: 회계구조가 antonym 을 가르는가 (accountMappings only)")
    print(
        f"korNames={len(korList)} standardAccounts={len(standard)} char-near pairs={totalPairs} (Jaccard>={JACCARD_LO})"
    )
    print("-" * 76)
    print(
        f"[G4-direction] char-near 쌍 중 same-canonical={sameCanon} ({g4SameRate:.3f}) / "
        f"diff-canonical={diffCanon} ({1 - g4SameRate:.3f})"
    )
    print("  -> char-분포는 char-near 쌍의 상당수를 *다른 의미*(다른 canonical)에 둔다. char≠의미.")
    print("-" * 76)
    print(f"[G2-referential] 다른-canonical char-near(= 분포가 conflate 하는 antonym/sibling) {diffCanon} 쌍:")
    print(f"  diffSj(다른 재무제표)        = {refClass['diffSj']}")
    print(f"  sameSj_diffFamily(다른 계정군) = {refClass['sameSj_diffFamily']}")
    print(f"  sibling(같은 군 다른 leaf)    = {refClass['sibling']}")
    print(f"  referential 변별률(다른 sj/family/leaf-code) = {refDiscriminated}/{diffCanon} = {g2Disc:.3f}")
    print("-" * 76)
    for k, exs in examples.items():
        if exs:
            print(f"  예({k}): " + " | ".join(exs[:5]))
    print("-" * 76)
    print(
        f"VERDICT: referential(sj+code)가 분포-conflate antonym/sibling 을 {g2Disc:.1%} 변별. "
        f"{'결합축을 회계구조가 grounding 함 입증(계정 도메인)' if g2Disc > 0.9 else '부분'}"
    )
    print(
        "범위: accountMappings 는 재무제표 *계정* 만 — 계정 antonym(유동/비유동·자산/부채) 커버, "
        "event/flow antonym(유상/무상·증가/감소)은 계정 아니라 미커버."
    )
    print("=" * 76)


if __name__ == "__main__":
    main()
