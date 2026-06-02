"""Horizon Meaning Learner V223 - contrastive body-term specificity (결합축 2차, body-side).

V221 의 교정된 자(尺)를 고정하고 기계만 바꾼다(R4).
V222 진단: title char-feature 를 class-IDF 로 재가중해도 antonym-null 은 chance 이하(-0.009)였다.
이유는 sibling(유상증자 vs 무상증자)의 *body 확장 프로파일이 거의 같기* 때문이다 — title 을 어떻게 가중해도
body 가 겹치면 안 갈린다. [goal] escalation("2 연속 G2 실패 -> 뿌리를 친다")대로 title 재가중을 버리고
*body side* 를 친다.

가설(이번 iteration, 자 고정 / 기계만 변경):
    body term 의 *class 특이성*(body class-IDF)으로 확장 프로파일을 재가중한다. 한 body term 이 train 에서
    몇 개의 의미류에 걸쳐 나타나는지로, 공유 body 어휘(`주식`,`회사`,`결정`)는 낮추고 class 고유 body 어휘
    (`제3자배정`,`자본전입` 등)는 들어올린다. 이러면 sibling 의 겹치는 body 질량이 깎이고 고유 body 가 남아
    own-class 가 갈린다. 표적은 G2(antonym-null). 손사전 아님(R1): class=report_nm core, 가중=train 통계.

    비교: morph(무가중) / morphDisc(title class-IDF, V222) / morphBodyDisc(body class-IDF, 신규).
    성공 = morphBodyDisc 의 sibling margin 이 chance 를 유의(근사 이항)하게 상회 + class-gold 퇴보 0 +
    shuffle-null 유지.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV223Test.py
    $env:DARTLAB_HORIZON_V223_FILE_LIMIT='8'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV223Test.py
    $env:DARTLAB_HORIZON_V223_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV223Test.py

검증 기준:
    1. 데이터는 data/dart/allFilings/*.parquet 의 report_nm + content_raw 만.
    2. class·가중은 report_nm core + train 통계. 손사전·8 probe 미사용(R1).
    3. train/test corp_code 분리. bodyClassDf/SPPMI 는 train 에서만.
    4. V221 자(class gold, antonym-null, shuffle-null) 그대로.
    5. promotion: morphBodyDisc antonym-null margin > 0 (chance 상회) + class-gold 퇴보 0 + shuffle-null PASS.

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 train=9876 test=2858 siblingEvalN=581 numTrainClasses=386, buildSeconds~=15
      [meaning-class] keyword Top1=0.8051/MRR=0.8454, morph 0.6099/0.6861, morphTitleDisc 0.6103/0.6863,
        morphBodyDisc 0.6182/0.6915, keyword+bodyDiscRRF 0.8427/0.8954
      [antonym-null n=581] keyword +0.2255, morph -0.0103, morphTitleDisc -0.0086, morphBodyDisc -0.0430,
        keyword+bodyDiscRRF +0.1222
      SHUFFLE-NULL morphBodyDisc exact Top1=0.00000 (chance=0.00035) -> PASS.

결론:
    부분/실패 (G2 미해결, 오히려 악화). body class-IDF 는 antonym-null 을 morph -0.010 -> -0.043 으로 *악화*
    시켰다. rare class-특이 body term 을 들어올리면 noise 가 커져 own/sibling 경계가 더 흐려진다. 단 class-gold
    MRR 은 소폭↑(0.686->0.692), keyword+bodyDiscRRF class MRR 0.8954 로 RRF 보완 소득은 최고 갱신.

    결정적 진단 (3 연속 G2 실패: morph / titleDisc / bodyDisc 모두 chance 이하):
    text-분포/char-morph 계열은 *근본적으로* 이 event-filing sibling(유상/무상증자류)의 antonym 변별을 못 한다.
    유일하게 변별하는 건 keyword(정확 stem, +0.226)뿐 — 분포 확장은 변별 morpheme 을 smear 한다. 이론 예측
    그대로: 결합축(부호·변별)은 공기(co-occurrence)에서 복원 불가. 정확 토큰 또는 referential 이 필요하다.

    [goal] escalation(3 버전 G2 정지 -> 개념 재도출): 분포 experience 단독으로 결합축을 만들려는 시도는 폐기.
    남은 두 길:
      (1) 하이브리드 수용 — keyword 가 결합축(변별), experience 가 계열축(recall)을 맡고 RRF 로 결합.
          이미 class MRR 0.845 -> 0.895 로 견고한 증분. "경험 단독 의미"가 아니라 "정확토큰+경험 하이브리드".
      (2) referential anchor — event sibling 은 panel 셀이 아니라 공시 구조 수치(발행가액>0 vs =0 등)로 부호
          분리(G4 변형). 큰 파싱이라 V 파일 깎기 전 개념 토론(다축 렌즈+레드팀)이 필요하다.
    다음은 V224 를 더 깎는 게 아니라 이 분기 결정이다.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V223_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V223_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V223_MAX_QUERIES", "1500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V223_TEST_MOD", "4"))
SEED = int(os.environ.get("DARTLAB_HORIZON_V223_SEED", "20260602"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V223_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V223_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V223_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V223_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V223_SPPMI_SHIFT", "0.7"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V223_TOPK", "10"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V223_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V223_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V223_SIB_JACCARD_LO", "0.5"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V223_RRF_K", "60"))
TITLE_DISC_POWER = float(os.environ.get("DARTLAB_HORIZON_V223_TITLE_DISC_POWER", "1.0"))
BODY_DISC_POWER = float(os.environ.get("DARTLAB_HORIZON_V223_BODY_DISC_POWER", "1.0"))

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


def buildClassDfs(trainDocs: list[Doc]) -> tuple[Counter, Counter, int]:
    """title feature 와 body term 각각의 *의미류 분포 수*(class-IDF 재료)를 train 에서 학습."""
    featureClasses: dict[str, set[str]] = defaultdict(set)
    bodyClasses: dict[str, set[str]] = defaultdict(set)
    classes: set[str] = set()
    for d in trainDocs:
        cls = classKeyOf(d.core)
        classes.add(cls)
        for feature in coreFeatureWeights(d.core):
            featureClasses[feature].add(cls)
        for b in d.body:
            bodyClasses[b].add(cls)
    titleClassDf = Counter({f: len(cs) for f, cs in featureClasses.items()})
    bodyClassDf = Counter({b: len(cs) for b, cs in bodyClasses.items()})
    return titleClassDf, bodyClassDf, max(1, len(classes))


def classIdf(key: str, classDf: Counter, numClasses: int, power: float) -> float:
    df = classDf.get(key, 0)
    if df <= 0:
        return 1.0
    return math.log(1.0 + numClasses / df) ** power


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


def expandMorphSppmi(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * edgeWeight
    return topProfile(profile, EXPAND_TOPN)


def expandMorphTitleDisc(core, graph, titleClassDf, numClasses) -> dict[str, float]:
    """V222 재현: title feature 를 class-IDF 로 가중."""
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        dw = classIdf(feature, titleClassDf, numClasses, TITLE_DISC_POWER)
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * dw * edgeWeight
    return topProfile(profile, EXPAND_TOPN)


def expandMorphBodyDisc(core, graph, bodyClassDf, numClasses) -> dict[str, float]:
    """신규: morph 확장 후 body term 을 body class-IDF(특이성)로 재가중. 공유 body 억제, 고유 body 강화."""
    base = expandMorphSppmi(core, graph)
    reweighted = {b: w * classIdf(b, bodyClassDf, numClasses, BODY_DISC_POWER) for b, w in base.items()}
    return topProfile(reweighted, EXPAND_TOPN)


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


def evaluateExact(queries, goldPos, scorer) -> dict[str, float]:
    top1 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        gold = goldPos[qid]
        scores = scorer(qid, core)
        n += 1
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        for r, (pos, _) in enumerate(ranked[:TOPK], start=1):
            if pos == gold:
                if r == 1:
                    top1 += 1
                mrr += 1.0 / r
                break
    return {"top1": top1 / n if n else 0.0, "mrr": mrr / n if n else 0.0, "n": n}


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
    titleClassDf, bodyClassDf, numClasses = buildClassDfs(trainDocs)
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
    titleDiscCache: dict[int, dict[str, float]] = {}
    bodyDiscCache: dict[int, dict[str, float]] = {}

    def getMorph(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def getTitleDisc(qid, core):
        if qid not in titleDiscCache:
            titleDiscCache[qid] = expandMorphTitleDisc(core, graph, titleClassDf, numClasses)
        return titleDiscCache[qid]

    def getBodyDisc(qid, core):
        if qid not in bodyDiscCache:
            bodyDiscCache[qid] = expandMorphBodyDisc(core, graph, bodyClassDf, numClasses)
        return bodyDiscCache[qid]

    def keywordScorer(qid, core):
        return scoreKeyword(core, invRaw)

    def morphScorer(qid, core):
        return scoreAssoc(getMorph(qid, core), testDocs, inv)

    def titleDiscScorer(qid, core):
        return scoreAssoc(getTitleDisc(qid, core), testDocs, inv)

    def bodyDiscScorer(qid, core):
        return scoreAssoc(getBodyDisc(qid, core), testDocs, inv)

    def fusedBodyDisc(qid, core):
        return rrfFuse([keywordScorer(qid, core), bodyDiscScorer(qid, core)])

    scorers = {
        "keyword": keywordScorer,
        "morphSppmi": morphScorer,
        "morphTitleDisc": titleDiscScorer,
        "morphBodyDisc": bodyDiscScorer,
        "keyword+bodyDiscRRF": fusedBodyDisc,
    }

    classRes = {name: evaluateClass(queries, posClass, classMembers, fn) for name, fn in scorers.items()}
    sibRes = {name: evaluateSibling(queries, posClass, classMembers, siblings, fn) for name, fn in scorers.items()}

    shufGold = dict(goldPos)
    shuffled = [q[0] for q in queries]
    rng.shuffle(shuffled)
    for q, sp in zip(queries, shuffled):
        shufGold[q[0]] = sp
    shufBody = evaluateExact(queries, shufGold, bodyDiscScorer)

    chance = 1.0 / len(testDocs)
    sibN = sibRes["morphBodyDisc"]["n"]

    print("=" * 72)
    print(f"V223 contrastive body-term specificity (결합축 2차)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(
        f"queries={len(queries)} classEvalN={classRes['morphBodyDisc']['n']} siblingEvalN={sibN} "
        f"classes={len(classMembers)} numTrainClasses={numClasses} chanceTop1={chance:.5f}"
    )
    print("-" * 72)
    print("[meaning-class gold]")
    for name in scorers:
        r = classRes[name]
        print(f"  {name:<20}: Top1={r['top1']:.4f} Top5={r['top5']:.4f} MRR={r['mrr']:.4f}")
    print("[antonym-null] sibling discrimination (own1 가 chance 를 넘어야 G2 신호)")
    for name in scorers:
        r = sibRes[name]
        print(f"  {name:<20}: own1={r['own1']:.4f} chance={r['chance']:.4f} margin={r['own1'] - r['chance']:+.4f}")
    print("-" * 72)
    gatePass = shufBody["top1"] <= max(chance * 5, 0.01)
    print(
        f"SHUFFLE-NULL morphBodyDisc exact Top1={shufBody['top1']:.5f} (chance={chance:.5f}) "
        f"-> {'PASS' if gatePass else 'FAIL'}"
    )
    bSib = sibRes["morphBodyDisc"]["own1"] - sibRes["morphBodyDisc"]["chance"]
    mSib = sibRes["morphSppmi"]["own1"] - sibRes["morphSppmi"]["chance"]
    classNoReg = classRes["morphBodyDisc"]["mrr"] >= classRes["morphSppmi"]["mrr"] - 0.005
    print("-" * 72)
    print(
        f"G2: morphBodyDisc margin {bSib:+.4f} vs morph {mSib:+.4f} -> {'IMPROVED' if bSib > mSib else 'NOT IMPROVED'}"
    )
    print(f"   morphBodyDisc margin > 0 (chance 상회): {'YES' if bSib > 0 else 'NO'} (n={sibN})")
    print(
        f"class-gold 퇴보 0: {'OK' if classNoReg else 'REGRESSED'} "
        f"(bodyDisc MRR {classRes['morphBodyDisc']['mrr']:.4f} vs morph {classRes['morphSppmi']['mrr']:.4f})"
    )
    promote = bSib > 0 and bSib > mSib and gatePass and classNoReg
    print(f"PROMOTION: {'PASS (G2 결합축 신호)' if promote else '부분/실패 — 결론에 분해 기록'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
