"""Horizon Meaning Learner V222 - class-discriminative feature weighting (결합축 1차 시도).

이 파일은 V221 의 교정된 자(尺)를 *그대로 고정*하고 기계만 바꾼다(R4).
V221 진단: morph/rwr 은 meaning-class 회수는 하지만 antonym-null(sibling 변별)에서 chance 이하
(morph own1 0.625 <= chance 0.635)다. char-morph 가 유상/무상·취득/처분류의 *공유 char-gram* 때문에
sibling 을 흐린다. 즉 계열축(치환 유사)만 있고 결합축(변별)이 없다.

가설(이번 iteration, 자 고정 / 기계만 변경):
    결합축의 가장 싼 1차 형태 = title feature 의 *class 변별력* 가중. 한 char-feature 가 train 에서
    몇 개의 의미류(report_nm core)에 걸쳐 나타나는지로 class-IDF 를 매기면, 공유 feature(`증자`,`결정`,
    `발행`)는 낮아지고 class 특이 feature(`유상`,`무상`,whole-token)는 높아진다. morph 확장을 이 가중으로
    seeding 하면 query 가 *자기 class 특이 body 어휘* 로 확장돼 sibling 과 갈린다.

    이건 손사전이 아니다(R1): class 는 DART report_nm core(행정), 가중은 train class-frequency 통계다.
    표적은 G2(antonym-null). 성공 = morphDisc 의 sibling margin 이 morph(-0.01)를 넘어 chance 를 유의하게
    상회 + meaning-class 회수 퇴보 0 + shuffle-null 유지.

    기계: V221 의 keyword/morph/rwr 에 morphDisc + keyword+morphDiscRRF 를 추가. 자(class gold,
    antonym-null, RRF, shuffle-null)는 V221 그대로.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV222Test.py
    $env:DARTLAB_HORIZON_V222_FILE_LIMIT='8'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV222Test.py
    $env:DARTLAB_HORIZON_V222_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV222Test.py

검증 기준:
    1. 데이터는 data/dart/allFilings/*.parquet 의 report_nm + content_raw 만.
    2. 라벨·class 는 report_nm(행정), 가중은 train 통계. 손사전·8 probe 미사용(R1).
    3. train/test corp_code 분리. classDf/SPPMI 는 train 에서만.
    4. V221 자(exact/class gold, antonym-null, shuffle-null) 그대로 재사용.
    5. promotion: morphDisc 의 antonym-null margin 이 morph 를 넘고 chance 를 유의(근사 이항)하게 상회 +
       class-gold 퇴보 0 + shuffle-null PASS.

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 train=9876 test=2858 classEvalN=2766 siblingEvalN=581 numTrainClasses=386, buildSeconds~=19
      [meaning-class gold] keyword Top1=0.8051/MRR=0.8454, morph 0.6099/0.6863, morphDisc 0.6103/0.6865,
        keyword+morphRRF 0.8134/0.8810, keyword+discRRF 0.8134/0.8810
      [antonym-null n=581] keyword +0.2255, morph -0.0172, morphDisc -0.0086, rwr -0.0430,
        keyword+morphRRF +0.1222, keyword+discRRF +0.1222
      SHUFFLE-NULL morphDisc exact Top1=0.00000 (chance=0.00035) -> PASS.

결론:
    부분/실패 (G2 미해결). class-IDF 변별 가중은 antonym-null margin 을 morph -0.017 -> morphDisc -0.009 로
    *살짝* 올렸지만 여전히 chance(0) 이하다. class-gold 퇴보는 0(MRR 0.6865 vs 0.6863), keyword+discRRF
    보완 소득은 유지(class MRR 0.8810 > keyword 0.8454).

    실패 분해 — 왜 안 됐나:
    title char-feature 재가중으로는 부족하다. sibling(유상증자 vs 무상증자)의 *body 확장 프로파일이 거의 같다*
    — 둘 다 증자/신주/주식 body 어휘로 확장된다. title side 를 어떻게 가중해도 body 확장이 겹치면 sibling 은
    안 갈린다. 변별은 title 이 아니라 *body side* 또는 referential 에서 와야 한다. "char-morph 가 결합축의
    잘못된 기판"이라는 V221 진단이 재확인됐다.

    [goal] escalation(기계 재가중 2 연속 G2 실패 -> 뿌리를 친다)에 따라 다음(V223)은 title 재가중을 버린다:
    (a) body term 을 class-특이성으로 가중 = sibling 에 없는 own-class 고유 body 어휘를 들어올리는 contrastive
    body profile, 또는 (b) 회계 referential anchor(panel 차대변 부호, G4 축)로 유상/무상·취득/처분 부호 분리.
    채점은 동일 antonym-null margin(chance 상회 + 근사 유의)로 한다. keyword+RRF 보완은 baseline 유지.
"""

from __future__ import annotations

import hashlib
import html
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V222_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V222_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V222_MAX_QUERIES", "1500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V222_TEST_MOD", "4"))
SEED = int(os.environ.get("DARTLAB_HORIZON_V222_SEED", "20260602"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V222_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V222_EXPAND_TOPN", "60"))
RWR_TOPN = int(os.environ.get("DARTLAB_HORIZON_V222_RWR_TOPN", "90"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V222_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V222_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V222_SPPMI_SHIFT", "0.7"))
RWR_ALPHA = float(os.environ.get("DARTLAB_HORIZON_V222_RWR_ALPHA", "0.64"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V222_TOPK", "10"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V222_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V222_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V222_SIB_JACCARD_LO", "0.5"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V222_RRF_K", "60"))
DISC_POWER = float(os.environ.get("DARTLAB_HORIZON_V222_DISC_POWER", "1.0"))  # class-IDF 지수

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
        if NUM_RE.search(token):
            continue
        if not HANGUL_RE.fullmatch(token):
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
    body: Counter
    rawBody: frozenset[str]


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
            text = cleanText(r.get("content_raw"), limit=BODY_CHAR_LIMIT)
            stems = bodyStems(text)
            if len(stems) < 12:
                continue
            rawSet = frozenset(stems)
            masked = Counter(s for s in stems if s not in core)
            if not masked:
                continue
            docs.append(Doc(idx, corp, isTestCorp(corp), frozenset(core), masked, rawSet))
            idx += 1
        del df
    return docs


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def buildClassDf(trainDocs: list[Doc]) -> tuple[Counter, int]:
    """title char-feature 가 train 에서 몇 개의 *의미류*(report_nm core)에 걸쳐 나타나는가 = class-IDF 재료."""
    featureClasses: dict[str, set[str]] = defaultdict(set)
    classes: set[str] = set()
    for d in trainDocs:
        cls = classKeyOf(d.core)
        classes.add(cls)
        for feature in coreFeatureWeights(d.core):
            featureClasses[feature].add(cls)
    classDf = Counter({f: len(cs) for f, cs in featureClasses.items() for c in [None] for s in [cs]})
    return classDf, max(1, len(classes))


def discWeight(feature: str, classDf: Counter, numClasses: int) -> float:
    df = classDf.get(feature, 0)
    if df <= 0:
        return 1.0
    return math.log(1.0 + numClasses / df) ** DISC_POWER


def buildAssoc(trainDocs: list[Doc]) -> tuple[dict[str, Counter], Counter, int]:
    assoc: dict[str, Counter] = defaultdict(Counter)
    bodyDf: Counter = Counter()
    for d in trainDocs:
        seen = set(d.body.keys())
        for b in seen:
            bodyDf[b] += 1
        for t in d.core:
            assoc[t].update(seen)
    return assoc, bodyDf, len(trainDocs)


@dataclass
class SppmiGraph:
    titleToBody: dict[str, dict[str, float]]
    bodyToTitle: dict[str, dict[str, float]]
    titleDf: Counter
    bodyDf: Counter
    nTrain: int


def buildSppmiGraph(trainDocs: list[Doc]) -> SppmiGraph:
    co: dict[str, Counter] = defaultdict(Counter)
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    for d in trainDocs:
        body = set(d.body.keys())
        features = set(coreFeatureWeights(d.core))
        if not features or not body:
            continue
        for b in body:
            bodyDf[b] += 1
        for feature in features:
            titleDf[feature] += 1
            co[feature].update(body)

    titleToBody: dict[str, dict[str, float]] = {}
    reverseRaw: dict[str, dict[str, float]] = defaultdict(dict)
    nTrain = max(1, len(trainDocs))
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
            idf = math.log(1.0 + nTrain / bDf)
            weighted[bodyTerm] = pmi * idf
        if not weighted:
            continue
        top = dict(sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH])
        titleToBody[feature] = top
        for bodyTerm, weight in top.items():
            reverseRaw[bodyTerm][feature] = weight

    bodyToTitle: dict[str, dict[str, float]] = {}
    for bodyTerm, features in reverseRaw.items():
        bodyToTitle[bodyTerm] = dict(sorted(features.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH])
    return SppmiGraph(titleToBody, bodyToTitle, titleDf, bodyDf, nTrain)


def topProfile(profile: dict[str, float], limit: int) -> dict[str, float]:
    if not profile:
        return {}
    return dict(sorted(profile.items(), key=lambda kv: kv[1], reverse=True)[:limit])


def normalizeProfile(profile: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in profile.values())
    if total <= 0:
        return {}
    return {key: max(0.0, value) / total for key, value in profile.items() if value > 0}


def expandMorphSppmi(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * edgeWeight
    return topProfile(profile, EXPAND_TOPN)


def expandMorphDisc(core: frozenset[str], graph: SppmiGraph, classDf: Counter, numClasses: int) -> dict[str, float]:
    """결합축: title feature 를 class-IDF(변별력)로 가중해 seeding. 공유 feature 억제, class 특이 feature 강화."""
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        dw = discWeight(feature, classDf, numClasses)
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * dw * edgeWeight
    return topProfile(profile, EXPAND_TOPN)


def expandRwr2Hop(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    first = normalizeProfile(expandMorphSppmi(core, graph))
    if not first:
        return {}
    titleWalk: dict[str, float] = defaultdict(float)
    for bodyTerm, bodyProb in topProfile(first, RWR_BRANCH).items():
        for feature, edgeWeight in graph.bodyToTitle.get(bodyTerm, {}).items():
            titleWalk[feature] += bodyProb * edgeWeight
    titleWalk = normalizeProfile(topProfile(titleWalk, RWR_BRANCH * 2))
    second: dict[str, float] = defaultdict(float)
    for feature, featureProb in titleWalk.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            second[bodyTerm] += featureProb * edgeWeight
    second = normalizeProfile(topProfile(second, RWR_TOPN))
    final: dict[str, float] = defaultdict(float)
    for bodyTerm, value in first.items():
        final[bodyTerm] += RWR_ALPHA * value
    for bodyTerm, value in second.items():
        final[bodyTerm] += (1.0 - RWR_ALPHA) * value
    return topProfile(final, RWR_TOPN)


def buildInverted(docs: list[Doc], key) -> dict[str, list[int]]:
    inv: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(docs):
        for b in key(d):
            inv[b].append(pos)
    return inv


def scoreAssoc(profile, testDocs, inv) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for b, w in profile.items():
        for pos in inv.get(b, ()):
            scores[pos] += w
    return scores


def scoreKeyword(core, invRaw) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for t in core:
        for pos in invRaw.get(t, ()):
            scores[pos] += 1.0
    return scores


def rrfFuse(scoreDicts: list[dict[int, float]], k: int = RRF_K) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for scores in scoreDicts:
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        for r, (pos, _) in enumerate(ranked, start=1):
            fused[pos] += 1.0 / (k + r)
    return dict(fused)


def charBigrams(key: str) -> set[str]:
    flat = key.replace("|", "")
    if len(flat) < 2:
        return {flat} if flat else set()
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


def evaluateExact(queries, goldPos, scorer) -> dict[str, float]:
    top1 = top5 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        gold = goldPos[qid]
        scores = scorer(qid, core)
        n += 1
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        rank = None
        for r, (pos, _) in enumerate(ranked[:TOPK], start=1):
            if pos == gold:
                rank = r
                break
        if rank == 1:
            top1 += 1
        if rank is not None and rank <= 5:
            top5 += 1
        if rank is not None:
            mrr += 1.0 / rank
    return {"top1": top1 / n if n else 0.0, "top5": top5 / n if n else 0.0, "mrr": mrr / n if n else 0.0, "n": n}


def evaluateClass(queries, posClass, classMembers, scorer) -> dict[str, float]:
    top1 = top5 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        cls = posClass[qid]
        gold = set(classMembers.get(cls, ())) - {qid}
        if not gold:
            continue
        n += 1
        scores = scorer(qid, core)
        if not scores:
            continue
        ranked = [pos for pos, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if pos != qid]
        rank = None
        for r, pos in enumerate(ranked[:TOPK], start=1):
            if pos in gold:
                rank = r
                break
        if rank == 1:
            top1 += 1
        if rank is not None and rank <= 5:
            top5 += 1
        if rank is not None:
            mrr += 1.0 / rank
    return {"top1": top1 / n if n else 0.0, "top5": top5 / n if n else 0.0, "mrr": mrr / n if n else 0.0, "n": n}


def mineSiblings(classMembers: dict[str, list[int]]) -> dict[str, list[str]]:
    classes = [c for c, m in classMembers.items() if len(m) >= SIB_MIN_MEMBERS]
    classes = sorted(classes)[:SIB_MAX_CLASSES]
    bigr = {c: charBigrams(c) for c in classes}
    sib: dict[str, list[str]] = defaultdict(list)
    for i in range(len(classes)):
        a = classes[i]
        ba = bigr[a]
        if not ba:
            continue
        for j in range(i + 1, len(classes)):
            b = classes[j]
            bb = bigr[b]
            uni = len(ba | bb)
            if uni == 0:
                continue
            jac = len(ba & bb) / uni
            if SIB_JACCARD_LO <= jac < 0.999:
                sib[a].append(b)
                sib[b].append(a)
    return sib


def evaluateSibling(queries, posClass, classMembers, siblings, scorer) -> dict[str, float]:
    own1 = 0
    n = 0
    chanceSum = 0.0
    for qid, core, _ in queries:
        cls = posClass[qid]
        sibs = siblings.get(cls)
        if not sibs:
            continue
        ownM = set(classMembers.get(cls, ())) - {qid}
        if not ownM:
            continue
        sibM: set[int] = set()
        for s in sibs:
            sibM |= set(classMembers.get(s, ()))
        sibM -= {qid}
        sibM -= ownM
        if not sibM:
            continue
        pool = ownM | sibM
        scores = scorer(qid, core)
        ranked = sorted(pool, key=lambda p: (-scores.get(p, 0.0), p))
        n += 1
        if ranked[0] in ownM:
            own1 += 1
        chanceSum += len(ownM) / len(pool)
    return {"own1": own1 / n if n else 0.0, "chance": chanceSum / n if n else 0.0, "n": n}


def main() -> None:
    t0 = time.time()
    rng = random.Random(SEED)
    docs = loadDocs()
    trainDocs = [d for d in docs if not d.isTest]
    testDocs = [d for d in docs if d.isTest]
    if not testDocs or not trainDocs:
        print(f"insufficient split: train={len(trainDocs)} test={len(testDocs)} (need both)")
        return

    graph = buildSppmiGraph(trainDocs)
    classDf, numClasses = buildClassDf(trainDocs)
    inv = buildInverted(testDocs, lambda d: d.body)
    invRaw = buildInverted(testDocs, lambda d: d.rawBody)

    queries: list[tuple[int, frozenset[str], bool]] = []
    goldPos: dict[int, int] = {}
    posClass: dict[int, str] = {}
    classMembers: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(testDocs):
        posClass[pos] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(pos)
    for pos, d in enumerate(testDocs):
        queries.append((pos, d.core, len(d.core) >= 2))
        goldPos[pos] = pos
        if len(queries) >= MAX_QUERIES:
            break

    siblings = mineSiblings(classMembers)

    morphCache: dict[int, dict[str, float]] = {}
    discCache: dict[int, dict[str, float]] = {}
    rwrCache: dict[int, dict[str, float]] = {}

    def getMorph(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def getDisc(qid, core):
        if qid not in discCache:
            discCache[qid] = expandMorphDisc(core, graph, classDf, numClasses)
        return discCache[qid]

    def getRwr(qid, core):
        if qid not in rwrCache:
            rwrCache[qid] = expandRwr2Hop(core, graph)
        return rwrCache[qid]

    def keywordScorer(qid, core):
        return scoreKeyword(core, invRaw)

    def morphScorer(qid, core):
        return scoreAssoc(getMorph(qid, core), testDocs, inv)

    def discScorer(qid, core):
        return scoreAssoc(getDisc(qid, core), testDocs, inv)

    def rwrScorer(qid, core):
        return scoreAssoc(getRwr(qid, core), testDocs, inv)

    def fusedMorph(qid, core):
        return rrfFuse([keywordScorer(qid, core), morphScorer(qid, core)])

    def fusedDisc(qid, core):
        return rrfFuse([keywordScorer(qid, core), discScorer(qid, core)])

    scorers = {
        "keyword": keywordScorer,
        "morphSppmi": morphScorer,
        "morphDisc": discScorer,
        "rwr2Hop": rwrScorer,
        "keyword+morphRRF": fusedMorph,
        "keyword+discRRF": fusedDisc,
    }

    exactRes = {name: evaluateExact(queries, goldPos, fn) for name, fn in scorers.items()}
    classRes = {name: evaluateClass(queries, posClass, classMembers, fn) for name, fn in scorers.items()}
    sibRes = {name: evaluateSibling(queries, posClass, classMembers, siblings, fn) for name, fn in scorers.items()}

    shufGold = dict(goldPos)
    shuffled = [q[0] for q in queries]
    rng.shuffle(shuffled)
    for q, sp in zip(queries, shuffled):
        shufGold[q[0]] = sp
    shufDisc = evaluateExact(queries, shufGold, discScorer)

    chance = 1.0 / len(testDocs)
    sibN = sibRes["morphDisc"]["n"]

    print("=" * 72)
    print(f"V222 class-discriminative feature weighting (결합축 1차)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(
        f"queries={len(queries)} classEvalN={classRes['morphDisc']['n']} siblingEvalN={sibN} "
        f"classes={len(classMembers)} numTrainClasses={numClasses} chanceTop1={chance:.5f}"
    )
    print("-" * 72)
    print("[meaning-class gold]")
    for name in scorers:
        r = classRes[name]
        print(f"  {name:<18}: Top1={r['top1']:.4f} Top5={r['top5']:.4f} MRR={r['mrr']:.4f}")
    print("[antonym-null] sibling discrimination (own1 가 chance 를 넘어야 G2 신호)")
    for name in scorers:
        r = sibRes[name]
        print(f"  {name:<18}: own1={r['own1']:.4f} chance={r['chance']:.4f} margin={r['own1'] - r['chance']:+.4f}")
    print("-" * 72)
    gatePass = shufDisc["top1"] <= max(chance * 5, 0.01)
    print(
        f"SHUFFLE-NULL morphDisc exact Top1={shufDisc['top1']:.5f} (chance={chance:.5f}) "
        f"-> {'PASS' if gatePass else 'FAIL'}"
    )
    # promotion: morphDisc 가 G2(antonym-null)에서 morph 를 넘고 class-gold 퇴보 0 인가
    mSib = sibRes["morphSppmi"]["own1"] - sibRes["morphSppmi"]["chance"]
    dSib = sibRes["morphDisc"]["own1"] - sibRes["morphDisc"]["chance"]
    g2Gain = dSib > mSib
    classNoReg = classRes["morphDisc"]["mrr"] >= classRes["morphSppmi"]["mrr"] - 0.005
    print("-" * 72)
    print(f"G2: morphDisc margin {dSib:+.4f} vs morph {mSib:+.4f} -> {'IMPROVED' if g2Gain else 'NOT IMPROVED'}")
    print(f"   morphDisc margin > 0 (chance 상회): {'YES' if dSib > 0 else 'NO'} (n={sibN})")
    print(
        f"class-gold 퇴보 0: {'OK' if classNoReg else 'REGRESSED'} "
        f"(morphDisc MRR {classRes['morphDisc']['mrr']:.4f} vs morph {classRes['morphSppmi']['mrr']:.4f})"
    )
    discFuse = classRes["keyword+discRRF"]["mrr"]
    kw = classRes["keyword"]["mrr"]
    print(
        f"보완: keyword+discRRF class MRR {discFuse:.4f} vs keyword {kw:.4f} -> {'ADDS' if discFuse > kw else 'NO ADD'}"
    )
    promote = g2Gain and dSib > 0 and gatePass and classNoReg
    print(f"PROMOTION: {'PASS (G2 결합축 신호)' if promote else '부분/실패 — 결론에 분해 기록'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
