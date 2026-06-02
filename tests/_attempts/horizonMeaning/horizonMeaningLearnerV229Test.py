"""Horizon Meaning Learner V229 - confidence-gated fusion: OOD 악화 방지(G3 회복 시도).

V228: 공정 short-query 에서 rrf(bm25Core,morph) inDist 0.926 > bm25Core 0.831 (G1 inDist YES), 그러나 OOD 는
morph 붕괴(0.210) + naive RRF 가 섞어 rrf 0.437 < bm25Core 0.738 (G3 NO). 무지성 fusion 이 미본 class 에서
해롭다.

V229 (R4: V228 자 고정, fusion 기계만 변경): morph 를 *confidence* 로 게이팅한다. confidence = query 의 title
토큰을 train 에서 본 적 있는가(= "tok:{t}" 가 SPPMI graph 에 edge 를 가지는 비율). inDist 면 conf≈1 →
morph 풀가중, OOD(class 제외)면 conf≈0 → morph 가중 0 → bm25Core 폴백. 이건 held-out 라벨이 아니라 train
self-knowledge 다(R1/R2 위반 아님).

    - weighted RRF: bm25Core 항상 full, morph 항은 conf 로 스케일.
    - 가설: gatedRrf 가 inDist 에선 naive rrf 의 G1 이득을 유지하고, OOD 에선 bm25Core 이하로 안 떨어진다
      (rrf>=bm25Core OOD) -> G3 회복.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV229Test.py
    $env:DARTLAB_HORIZON_V229_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV229Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. R1~R5 동일. confidence 는 train graph self-knowledge.
    2. 모든 scorer query=core. candidate=raw. SPPMI 는 core-masked train, OOD class 제외.
    3. naive rrf vs gatedRrf vs bm25Core 를 inDist/OOD 분리 출력.
    4. promotion: gatedRrf inDist>=naive rrf 의 이득 유지 AND OOD gatedRrf>=bm25Core(악화 0).

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 trainExp(non-OOD)=8627 test=2858 inDistN=2428 oodN=338,
             avgConf inDist=0.980 OOD=0.422, buildSeconds~=28
      scorer    inDist Top1/MRR   OOD Top1/MRR
      bm25Core  0.7961/0.8314     0.6864/0.7383
      naiveRrf  0.9016/0.9258     0.2929/0.4366
      gatedRrf  0.9065/0.9286     0.3462/0.4771

결론:
    실패(G3 미회복) + 결정적 진단. confidence(tok-edge 비율)는 inDist 0.98 / OOD 0.42 로 분리는 하나, OOD conf
    가 0 이 아니다 — class 는 token 집합이고 개별 token 이 비-OOD class 와 공유돼 tok-edge 가 샌다. 그래서 gate
    가 OOD 에서 morph 가중을 0.42 로 남겨, morph(OOD 0.21 garbage)가 여전히 rrf 를 끌어내림(gatedRrf OOD 0.477
    < bm25 0.738). gate 는 손상을 줄였으나(naive 0.437 -> gated 0.477) G3 회복 실패. inDist 는 G1 이득 유지
    (gatedRrf 0.929 >= naiveRrf 0.926 > bm25 0.831).

    핵심 통찰: hard gate(conf>=τ 면 fuse, 아니면 bm25 단독)로 OOD 를 trivially 회복할 수 있으나, 그건 *OOD 에서
    경험을 꺼버리는 것* = 경험이 미본 유형에 *0 기여* 임을 인정하는 것이다. 즉 G3 "회복"은 공허 — 경험은
    compositional 일반화가 없다. inDist 0.98 vs OOD 0.42 conf 격차가 이를 정량 확인한다.

    V221~V229 최종 경계:
    - G1: 경험은 in-dist short-query 에서 BM25 능가(real, +0.09 MRR).
    - G2: 결합축(반의/부호)은 분포 불가(definitive, V224~226).
    - G3: 경험은 미본 유형에 일반화 0(기억일 뿐). gate 는 손상만 줄일 뿐.
    - G4: referential(회계구조) 미시행 — 분포 경로 아님, 별도 과제.
    => "분포 경험 -> 두-축 의미"(G1∧G2∧G3∧G4)는 분포 경로에서 반증. 종착 목표는 분포만으론 도달 불가.

    다음 분기(운영자 결정 필요): (a) G4 referential 트랙(panel 차대변 부호 = 결합축 grounding; accounting-term
    과제로 전환), 또는 (b) 종착 목표를 분포-가능 범위(G1 in-dist 계열축)로 재정의하고 루프 종료. 둘 다 "분포만으로
    두-축 의미"는 닫힘.
"""

from __future__ import annotations

import hashlib
import html
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V229_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V229_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V229_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V229_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V229_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V229_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V229_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V229_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V229_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V229_SPPMI_SHIFT", "0.7"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V229_TOPK", "10"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V229_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V229_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V229_RRF_K", "60"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
PAREN_RE = re.compile(r"[(\[]([^)\]]+)[)\]]")
BRACKET_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]")

GENERIC_TITLE_STOP = frozenset(
    {
        "보고서",
        "공시",
        "제출",
        "정정",
        "기재",
        "첨부",
        "첨부정정",
        "자료",
        "자율",
        "주요사항보고서",
        "주요사항",
        "조회공시",
        "조회",
        "요구",
        "답변",
        "풍문",
        "보도",
        "정지",
        "해제",
        "신청",
        "결과",
        "안내",
        "변경",
        "예고",
        "관련",
        "여부",
        "확인",
        "공고",
        "통지",
        "사업",
        "분기",
        "반기",
        "감사",
        "검토",
        "연결",
        "재무제표",
    }
)


def cleanText(value: object, *, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    text = SPACE_RE.sub(" ", text).strip()
    return text


def bodyStems(text: str) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall(text):
        if len(token) < 2 or len(token) > 14:
            continue
        if NUM_RE.search(token) or not HANGUL_RE.fullmatch(token):
            continue
        out.append(token)
    return out


def reportNmCore(report_nm: str) -> set[str]:
    raw = (report_nm or "").strip()
    raw = BRACKET_PREFIX_RE.sub("", raw).strip()
    parens = PAREN_RE.findall(raw)
    head = PAREN_RE.sub(" ", raw)
    pool = " ".join(parens) if parens else head
    core: set[str] = set()
    for token in TOKEN_RE.findall(pool):
        if len(token) < 2 or len(token) > 14:
            continue
        if NUM_RE.search(token) or not HANGUL_RE.fullmatch(token):
            continue
        if token in GENERIC_TITLE_STOP:
            continue
        core.add(token)
    return core


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def isTestCorp(corp: str) -> bool:
    return (stableHashInt(corp) % TEST_MOD) == 0 if corp else False


def tokenFeatureWeights(token: str) -> dict[str, float]:
    if not token:
        return {}
    features: dict[str, float] = {f"tok:{token}": 1.0}
    length = len(token)
    for size, weight in ((2, 0.18), (3, 0.34), (4, 0.42)):
        if length < size:
            continue
        features[f"pre{size}:{token[:size]}"] = max(features.get(f"pre{size}:{token[:size]}", 0.0), weight)
        features[f"suf{size}:{token[-size:]}"] = max(features.get(f"suf{size}:{token[-size:]}", 0.0), weight)
    for size, weight in ((2, 0.10), (3, 0.22), (4, 0.30)):
        if length < size + 1:
            continue
        for start in range(0, length - size + 1):
            gram = token[start : start + size]
            if gram in GENERIC_TITLE_STOP:
                continue
            key = f"ng{size}:{gram}"
            features[key] = max(features.get(key, 0.0), weight)
    return features


def coreFeatureWeights(core: frozenset[str]) -> dict[str, float]:
    features: dict[str, float] = defaultdict(float)
    for token in core:
        for feature, weight in tokenFeatureWeights(token).items():
            features[feature] = max(features[feature], weight)
    return dict(features)


@dataclass
class Doc:
    idx: int
    corp: str
    isTest: bool
    core: frozenset[str]
    raw: Counter


def loadDocs() -> list[Doc]:
    files = sorted(ALL_FILINGS_DIR.glob("*.parquet"))[:FILE_LIMIT]
    docs: list[Doc] = []
    idx = 0
    for path in files:
        df = pl.read_parquet(str(path), columns=["corp_code", "report_nm", "content_raw"])
        if df.height > ROWS_PER_FILE:
            df = df.head(ROWS_PER_FILE)
        for r in df.iter_rows(named=True):
            corp = str(r.get("corp_code") or "")
            core = reportNmCore(r.get("report_nm") or "")
            if not core:
                continue
            stems = bodyStems(cleanText(r.get("content_raw"), limit=BODY_CHAR_LIMIT))
            if len(stems) < 12:
                continue
            docs.append(Doc(idx, corp, isTestCorp(corp), frozenset(core), Counter(stems)))
            idx += 1
        del df
    return docs


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def isOodClass(cls: str) -> bool:
    return (stableHashInt("ood:" + cls) % OOD_MOD) == 0


@dataclass
class SppmiGraph:
    titleToBody: dict[str, dict[str, float]]


def buildSppmiGraph(trainDocs: list[Doc]) -> SppmiGraph:
    co: dict[str, Counter] = defaultdict(Counter)
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    for d in trainDocs:
        body = {b for b in d.raw if b not in d.core}
        features = set(coreFeatureWeights(d.core))
        if not features or not body:
            continue
        for b in body:
            bodyDf[b] += 1
        for feature in features:
            titleDf[feature] += 1
            co[feature].update(body)
    nTrain = max(1, len(trainDocs))
    titleToBody: dict[str, dict[str, float]] = {}
    for feature, counts in co.items():
        fDf = titleDf[feature]
        if fDf <= 0:
            continue
        weighted: dict[str, float] = {}
        for bodyTerm, c in counts.items():
            if c < MIN_ASSOC_DF:
                continue
            bDf = bodyDf.get(bodyTerm, 0)
            if bDf <= 0:
                continue
            pmi = math.log((c * nTrain) / (fDf * bDf)) - SPPMI_SHIFT
            if pmi <= 0:
                continue
            weighted[bodyTerm] = pmi * math.log(1.0 + nTrain / bDf)
        if weighted:
            titleToBody[feature] = dict(sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH])
    return SppmiGraph(titleToBody)


def expandMorphSppmi(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * edgeWeight
    return dict(sorted(profile.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])


def morphConfidence(core: frozenset[str], graph: SppmiGraph) -> float:
    """train self-knowledge: query 의 *정확 title 토큰*("tok:{t}")이 graph 에 edge 를 가지는 비율.
    inDist(본 적 있음)≈1, OOD(class 제외)≈0. held-out 라벨 미사용(R1/R2)."""
    if not core:
        return 0.0
    seen = sum(1 for t in core if f"tok:{t}" in graph.titleToBody)
    return seen / len(core)


@dataclass
class Bm25Index:
    inv: dict[str, list[int]]
    docLen: list[int]
    avgdl: float
    n: int
    df: Counter


def buildBm25(testDocs: list[Doc]) -> Bm25Index:
    inv: dict[str, list[int]] = defaultdict(list)
    docLen: list[int] = []
    df: Counter = Counter()
    for pos, d in enumerate(testDocs):
        docLen.append(sum(d.raw.values()))
        for b in d.raw:
            inv[b].append(pos)
            df[b] += 1
    n = len(testDocs)
    avgdl = (sum(docLen) / n) if n else 1.0
    return Bm25Index(inv, docLen, max(1.0, avgdl), n, df)


def scoreBm25(qStems: set[str], bm: Bm25Index, testDocs: list[Doc]) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for t in qStems:
        df = bm.df.get(t, 0)
        if df <= 0:
            continue
        idf = math.log((bm.n - df + 0.5) / (df + 0.5) + 1.0)
        for pos in bm.inv.get(t, ()):
            tf = testDocs[pos].raw.get(t, 0)
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * bm.docLen[pos] / bm.avgdl)
            if denom > 0:
                scores[pos] += idf * (tf * (BM25_K1 + 1)) / denom
    return scores


def scoreMorph(profile: dict[str, float], inv: dict[str, list[int]]) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for b, w in profile.items():
        for pos in inv.get(b, ()):
            scores[pos] += w
    return scores


def weightedRrf(weightedScores: list[tuple[dict[int, float], float]], k: int = RRF_K) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for scores, weight in weightedScores:
        if not scores or weight <= 0:
            continue
        for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
            fused[pos] += weight / (k + r)
    return dict(fused)


def evalClassSplit(queries, posClass, classMembers, scorer):
    acc = {"in": [0, 0.0, 0], "ood": [0, 0.0, 0]}
    for qid, core, _ in queries:
        cls = posClass[qid]
        gold = set(classMembers.get(cls, ())) - {qid}
        if not gold:
            continue
        bucket = "ood" if isOodClass(cls) else "in"
        acc[bucket][2] += 1
        scores = scorer(qid, core)
        if not scores:
            continue
        ranked = [pos for pos, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if pos != qid]
        for r, pos in enumerate(ranked[:TOPK], start=1):
            if pos in gold:
                if r == 1:
                    acc[bucket][0] += 1
                acc[bucket][1] += 1.0 / r
                break
    out = {}
    for b in ("in", "ood"):
        hit, mrr, nn = acc[b]
        out[b] = {"top1": hit / nn if nn else 0.0, "mrr": mrr / nn if nn else 0.0, "n": nn}
    return out


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    trainAll = [d for d in docs if not d.isTest]
    testDocs = [d for d in docs if d.isTest]
    if not testDocs or not trainAll:
        print(f"insufficient split: train={len(trainAll)} test={len(testDocs)}")
        return

    trainExp = [d for d in trainAll if not isOodClass(classKeyOf(d.core))]
    graph = buildSppmiGraph(trainExp)
    bm = buildBm25(testDocs)
    inv: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(testDocs):
        for b in d.raw:
            inv[b].append(pos)

    posClass: dict[int, str] = {}
    classMembers: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(testDocs):
        posClass[pos] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(pos)

    queries = []
    for pos, d in enumerate(testDocs):
        queries.append((pos, d.core, classKeyOf(d.core)))
        if len(queries) >= MAX_QUERIES:
            break

    morphCache: dict[int, dict[str, float]] = {}
    confCache: dict[int, float] = {}

    def morphProf(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def conf(qid, core):
        if qid not in confCache:
            confCache[qid] = morphConfidence(core, graph)
        return confCache[qid]

    def bm25Scorer(qid, core):
        return scoreBm25(set(core), bm, testDocs)

    def morphScorer(qid, core):
        return scoreMorph(morphProf(qid, core), inv)

    def naiveRrf(qid, core):
        return weightedRrf([(bm25Scorer(qid, core), 1.0), (morphScorer(qid, core), 1.0)])

    def gatedRrf(qid, core):
        return weightedRrf([(bm25Scorer(qid, core), 1.0), (morphScorer(qid, core), conf(qid, core))])

    scorers = {
        "bm25Core": bm25Scorer,
        "naiveRrf": naiveRrf,
        "gatedRrf": gatedRrf,
    }
    res = {name: evalClassSplit(queries, posClass, classMembers, fn) for name, fn in scorers.items()}

    # 평균 confidence 진단
    confIn = []
    confOod = []
    for qid, core, cls in queries:
        if not (set(classMembers.get(cls, ())) - {qid}):
            continue
        (confOod if isOodClass(cls) else confIn).append(conf(qid, core))
    avgConfIn = sum(confIn) / len(confIn) if confIn else 0.0
    avgConfOod = sum(confOod) / len(confOod) if confOod else 0.0

    nIn = res["bm25Core"]["in"]["n"]
    nOod = res["bm25Core"]["ood"]["n"]
    print("=" * 76)
    print(f"V229 confidence-gated fusion (G3 회복)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} trainExp(non-OOD)={len(trainExp)} test={len(testDocs)}")
    print(f"queries={len(queries)} inDistN={nIn} oodN={nOod} avgConf inDist={avgConfIn:.3f} OOD={avgConfOod:.3f}")
    print("-" * 76)
    print(f"{'scorer':<12} | inDist Top1/MRR    | OOD Top1/MRR")
    for name in scorers:
        ri = res[name]["in"]
        ro = res[name]["ood"]
        print(f"{name:<12} | {ri['top1']:.4f}/{ri['mrr']:.4f}      | {ro['top1']:.4f}/{ro['mrr']:.4f}")
    print("-" * 76)
    bIn = res["bm25Core"]["in"]["mrr"]
    gIn = res["gatedRrf"]["in"]["mrr"]
    nvIn = res["naiveRrf"]["in"]["mrr"]
    bOod = res["bm25Core"]["ood"]["mrr"]
    gOod = res["gatedRrf"]["ood"]["mrr"]
    nvOod = res["naiveRrf"]["ood"]["mrr"]
    g1Keep = gIn > bIn and gIn >= nvIn - 0.01
    g3Recover = gOod >= bOod - 0.005
    print(
        f"G1 유지(inDist): gatedRrf {gIn:.4f} > bm25Core {bIn:.4f} & ~>= naiveRrf {nvIn:.4f} ? {'YES' if g1Keep else 'NO'}"
    )
    print(
        f"G3 회복(OOD)  : gatedRrf {gOod:.4f} >= bm25Core {bOod:.4f} (naiveRrf {nvOod:.4f}) ? {'YES' if g3Recover else 'NO'}"
    )
    print("-" * 76)
    if g1Keep and g3Recover:
        v = "성공: confidence gate 가 inDist G1 이득 유지 + OOD 악화 제거(G3 회복). 경험은 본 class 에서만 발화, 미본 class 엔 무해."
    elif g3Recover and not g1Keep:
        v = "부분: OOD 악화는 막았으나 inDist 이득 일부 손실. gate 가 너무 보수적."
    else:
        v = "실패: gate 가 OOD 악화를 못 막음(또는 inDist 손상). confidence 신호 재설계 필요."
    print(f"VERDICT: {v}")
    print("=" * 76)


if __name__ == "__main__":
    main()
