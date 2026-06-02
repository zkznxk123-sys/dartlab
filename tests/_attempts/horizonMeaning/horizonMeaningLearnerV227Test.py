"""Horizon Meaning Learner V227 - 계열축 라인 확정: BM25 강 baseline 대비 + OOD 일반화 (G1·G3).

V221~V226 결판: 분포에 결합축 없음. 계열축(vocabulary 회수)만 분포로 실재. 하이브리드(keyword/experience)가
정답 표상. 직전 미측정 = G1(검증된 강 baseline 대비)·G3(OOD 일반화).

V227 (R4: 측정 iteration, 새 기계 없음): 검증된 계열축 기계(morph SPPMI)와 강 baseline(BM25)을 같은
meaning-class 자(尺)에서 비교하고, *OOD 공시유형*(train 경험에서 class 단위로 제외)에서도 유지되는지 본다.

    - BM25: query doc 의 masked body 로 candidate masked body 검색(강 content baseline, char/stem).
    - morphSppmi: query core -> train SPPMI 확장(경험).
    - rrf(bm25, morph): 강 baseline 에 경험을 더하면 이득인가(G1 핵심).
    - OOD: class hash 로 OOD class 지정 -> train 경험(SPPMI)에서 그 class 문서 제외. test query 를
      inDist(경험 본 class) vs OOD(경험 못 본 class)로 나눠 각각 측정(G3).

가설(직전 결판에서 도출):
    계열축은 분포로 실재하므로 rrf(bm25,morph)가 bm25 단독을 meaning-class 에서 이기고(G1), 그 이득이 OOD
    class 에서도 유지되면(G3) "계열축 경험 의미"가 일반화로 확정. morph 가 OOD 에서 무너지면 char-feature
    경험이 미본 class 에 일반화 못 함을 뜻함.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV227Test.py
    $env:DARTLAB_HORIZON_V227_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV227Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. R1/R2/R3/R5 동일.
    2. train/test corp_code 분리. OOD 는 class 단위로 SPPMI 학습에서 제외(누설 가드).
    3. meaning-class gold(같은 report_nm core), exact-doc 아님.
    4. inDist/OOD 분리 출력. G1=rrf>bm25? G3=OOD 에서 유지?

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 trainAll=9876 trainExp(non-OOD)=8627 test=2858, inDistN=2428 oodN=338, buildSeconds~=75
      scorer             inDist Top1/MRR    OOD Top1/MRR
      bm25(full-body q)  0.9300/0.9500      0.9083/0.9409
      morphSppmi(core q) 0.5507/0.6206      0.1893/0.2073
      rrf(bm25,morph)    0.7694/0.8404      0.3994/0.5113

결론:
    G1 미달(as-measured) + 중대한 측정 confound 발견 — 이전 "하이브리드가 답" 주장 교정.

    1. BM25 강 baseline 이 morph/rrf 를 압도(inDist MRR 0.950 vs rrf 0.840 vs morph 0.621). 즉 V221~V226 에서
       "RRF 하이브리드가 keyword(0.895)를 이긴다"던 건 *약한 baseline(keyword)* 대비였고, *강 baseline(BM25)*
       앞에서는 경험 기계가 오히려 손해다(rrf<bm25). 강 baseline 미달 = G1 실패.
    2. 단 confound: BM25 는 query doc 의 *full masked body*(top-40 tf)를 query 로 썼고 morph 는 *title core
       (1~2 토큰)* 만 썼다. BM25 가 본 query 정보가 압도적으로 많다 — apples-to-apples 아님. doc-to-doc
       유사검색에선 BM25 가 당연히 이기고 경험은 불필요. product 의 *짧은 의미 query* regime 은 미검증.
    3. morph 는 OOD class 에서 붕괴(0.207, inDist 의 1/3) = char-feature 경험이 미본 공시유형에 일반화 못 함(G3 실패).

    종합 교정: 경험 기계의 가치는 *짧은 query(core->확장) regime* 에 한정될 수 있고, full-doc query 에선 vanilla
    BM25 가 정답. 이전 턴의 "하이브리드 검증" 낙관은 약-baseline 대비 착시였다(self-correction).

    다음(V228): 공정 G1 — 모든 scorer 가 *동일 query 형식*(query=core, 짧은 query regime)에서 경쟁.
    BM25-on-core(=강 lexical baseline) vs morph(core 확장) vs rrf. 여기서도 경험이 BM25-on-core 를 못 넘으면
    "경험->의미"는 계열축에서도 vanilla IR 대비 가치 없음으로 최종 결론. 넘으면 "경험은 짧은-query 확장에서만
    가치 있음"으로 한정 확정. (riVsaHash 정식 비교는 별도 자산 통합 필요, 미시행.)
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V227_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V227_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V227_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V227_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V227_OOD_MOD", "5"))  # class hash %OOD_MOD==0 -> OOD(경험 제외)
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V227_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V227_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V227_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V227_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V227_SPPMI_SHIFT", "0.7"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V227_TOPK", "10"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V227_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V227_BM25_B", "0.75"))
BM25_QTOP = int(os.environ.get("DARTLAB_HORIZON_V227_BM25_QTOP", "40"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V227_RRF_K", "60"))

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
            masked = Counter(s for s in stems if s not in core)
            if not masked:
                continue
            docs.append(Doc(idx, corp, isTestCorp(corp), frozenset(core), masked, frozenset(stems)))
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
        body = set(d.body.keys())
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
        docLen.append(sum(d.body.values()))
        for b in d.body:
            inv[b].append(pos)
            df[b] += 1
    n = len(testDocs)
    avgdl = (sum(docLen) / n) if n else 1.0
    return Bm25Index(inv, docLen, max(1.0, avgdl), n, df)


def scoreBm25(qStems: set[str], bm: Bm25Index, testDocs: list[Doc], poolSet: set[int]) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for t in qStems:
        df = bm.df.get(t, 0)
        if df <= 0:
            continue
        idf = math.log((bm.n - df + 0.5) / (df + 0.5) + 1.0)
        for pos in bm.inv.get(t, ()):
            if pos not in poolSet:
                continue
            tf = testDocs[pos].body.get(t, 0)
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * bm.docLen[pos] / bm.avgdl)
            if denom > 0:
                scores[pos] += idf * (tf * (BM25_K1 + 1)) / denom
    return scores


def scoreMorph(profile: dict[str, float], inv: dict[str, list[int]], poolSet: set[int]) -> dict[int, float]:
    scores: dict[int, float] = defaultdict(float)
    for b, w in profile.items():
        for pos in inv.get(b, ()):
            if pos in poolSet:
                scores[pos] += w
    return scores


def rrfFuse(scoreDicts: list[dict[int, float]], k: int = RRF_K) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for scores in scoreDicts:
        if not scores:
            continue
        for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
            fused[pos] += 1.0 / (k + r)
    return dict(fused)


def evalClassSplit(queries, posClass, classMembers, scorer):
    """meaning-class gold. 반환: inDist/OOD 각각 (top1, mrr, n)."""
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
        hit, mrr, n = acc[b]
        out[b] = {"top1": hit / n if n else 0.0, "mrr": mrr / n if n else 0.0, "n": n}
    return out


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    trainAll = [d for d in docs if not d.isTest]
    testDocs = [d for d in docs if d.isTest]
    if not testDocs or not trainAll:
        print(f"insufficient split: train={len(trainAll)} test={len(testDocs)}")
        return

    # OOD: class 단위로 train 경험(SPPMI)에서 제외
    trainExp = [d for d in trainAll if not isOodClass(classKeyOf(d.core))]
    graph = buildSppmiGraph(trainExp)
    bm = buildBm25(testDocs)
    inv: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(testDocs):
        for b in d.body:
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

    poolSet = set(range(len(testDocs)))
    morphCache: dict[int, dict[str, float]] = {}
    qbodyCache: dict[int, set[str]] = {}

    def morphProf(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def qbody(qid):
        if qid not in qbodyCache:
            # query doc 의 상위 tf body stem (BM25 query)
            qbodyCache[qid] = {b for b, _ in testDocs[qid].body.most_common(BM25_QTOP)}
        return qbodyCache[qid]

    def bm25Scorer(qid, core):
        return scoreBm25(qbody(qid), bm, testDocs, poolSet)

    def morphScorer(qid, core):
        return scoreMorph(morphProf(qid, core), inv, poolSet)

    def rrfScorer(qid, core):
        return rrfFuse([bm25Scorer(qid, core), morphScorer(qid, core)])

    scorers = {"bm25": bm25Scorer, "morphSppmi": morphScorer, "rrf(bm25,morph)": rrfScorer}
    res = {name: evalClassSplit(queries, posClass, classMembers, fn) for name, fn in scorers.items()}

    nIn = res["bm25"]["in"]["n"]
    nOod = res["bm25"]["ood"]["n"]
    print("=" * 74)
    print(f"V227 계열축 확정: BM25 강 baseline + OOD  ({time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={len(docs)} trainAll={len(trainAll)} trainExp(non-OOD)={len(trainExp)} test={len(testDocs)}"
    )
    print(f"queries={len(queries)} classes={len(classMembers)} inDistN={nIn} oodN={nOod}")
    print("-" * 74)
    print(f"{'scorer':<18} | inDist Top1/MRR        | OOD Top1/MRR")
    for name in scorers:
        ri = res[name]["in"]
        ro = res[name]["ood"]
        print(f"{name:<18} | {ri['top1']:.4f}/{ri['mrr']:.4f}          | {ro['top1']:.4f}/{ro['mrr']:.4f}")
    print("-" * 74)
    g1In = res["rrf(bm25,morph)"]["in"]["mrr"] > res["bm25"]["in"]["mrr"]
    g1Ood = res["rrf(bm25,morph)"]["ood"]["mrr"] > res["bm25"]["ood"]["mrr"]
    morphOodHolds = res["morphSppmi"]["ood"]["mrr"] > 0.5 * res["morphSppmi"]["in"]["mrr"]
    print(
        f"G1(inDist): rrf > bm25 ? {'YES' if g1In else 'NO'} "
        f"(rrf {res['rrf(bm25,morph)']['in']['mrr']:.4f} vs bm25 {res['bm25']['in']['mrr']:.4f})"
    )
    print(
        f"G3(OOD)   : rrf > bm25 유지 ? {'YES' if g1Ood else 'NO'} "
        f"(rrf {res['rrf(bm25,morph)']['ood']['mrr']:.4f} vs bm25 {res['bm25']['ood']['mrr']:.4f})"
    )
    print(f"morph OOD 일반화(>50% of inDist): {'YES' if morphOodHolds else 'NO'}")
    print("-" * 74)
    if g1In and g1Ood:
        v = "계열축 확정: 경험(morph)이 BM25 강 baseline 에 inDist·OOD 모두에서 증분. 계열축 의미 일반화."
    elif g1In and not g1Ood:
        v = "부분: inDist 증분 있으나 OOD 에서 사라짐 = 경험이 미본 class 에 일반화 못 함(G3 미달)."
    else:
        v = "실패: rrf 가 bm25 를 못 넘음 = 경험 증분이 강 baseline 앞에서 사라짐(G1 미달). riVsaHash 정식 비교 필요."
    print(f"VERDICT: {v}")
    print("주의: 본 baseline 은 BM25(char/stem). 검증된 riVsaHash 정식 비교는 별도 자산 통합 필요(미시행).")
    print("=" * 74)


if __name__ == "__main__":
    main()
