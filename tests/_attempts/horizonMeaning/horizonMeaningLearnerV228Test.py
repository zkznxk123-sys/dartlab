"""Horizon Meaning Learner V228 - 공정 short-query G1: "경험->의미" 최종 결정 실험.

V227 confound: BM25 는 full-body query, morph 는 title-core query 라 불공정(BM25 당연승). V228 은 *동일
query 형식*으로 공정 비교한다. product 실사용 regime = 짧은 의미 query(report_nm core, 1~2 토큰),
candidates = unmasked 실문서.

    - bm25Core: query=core, candidate=raw body BM25 (강 lexical baseline; 같은 의미류 문서는 title 어휘 포함).
    - morph: query core -> SPPMI 확장(경험; title 어휘 없는 paraphrase 문서도 회수 가능).
    - rrf(bm25Core, morph): 강 lexical 에 경험을 더하면 이득인가(G1 최종).
    - OOD: class 단위 SPPMI 제외 -> inDist/OOD 분리(G3).

가설(V227 confound 제거에서 도출):
    공정 regime 에서 rrf 가 bm25Core 를 이기면(G1) + OOD 유지(G3) -> "경험은 짧은-query 확장에서 vanilla
    lexical 대비 가치 있음" 한정 확정. 못 넘으면 -> 계열축에서도 경험은 표준 IR 대비 가치 없음 = "경험->의미"
    프로그램 정직하게 닫힘.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV228Test.py
    $env:DARTLAB_HORIZON_V228_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV228Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. R1~R5 동일.
    2. 모든 scorer query=core(동일 형식). candidate=raw body(실검색). SPPMI 는 core-masked train 에서만.
    3. train/test corp_code 분리. OOD class 단위 경험 제외.
    4. meaning-class gold. inDist/OOD 분리. G1=rrf>bm25Core? G3=OOD 유지?

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 trainExp(non-OOD)=8627 test=2858 inDistN=2428 oodN=338, buildSeconds~=16
      scorer                inDist Top1/MRR   OOD Top1/MRR
      bm25Core(query=core)  0.7961/0.8314     0.6864/0.7383
      morphSppmi            0.5379/0.6126     0.1893/0.2098
      rrf(bm25Core,morph)   0.9016/0.9258     0.2929/0.4367

결론:
    부분 성공 + V227 교정. 공정 short-query(모든 scorer query=core, candidate=raw) regime 에서:
    - G1(inDist) YES: rrf 0.926 > bm25Core 0.831 (morph 0.613). 경험 확장이 강 lexical baseline 에 *공정하게*
      증분(+0.09 MRR). V227 의 "프로그램 닫힘" 비관은 그 자신의 confound(full-body query) 탓이었다 — 짧은-query
      regime 에선 경험이 진짜 가치 있다. (V221~V226 의 keyword 대비 우위가 BM25-on-core 대비로도 살아남음.)
    - G3(OOD) NO: morph 가 미본 class 에서 붕괴(0.210)하고, naive RRF 가 섞어 rrf(0.437) < bm25Core(0.738).
      경험은 본 class 의 title->body 연상을 *기억*할 뿐 미본 공시유형에 compositional 일반화 못 함. 무지성
      fusion 은 OOD 를 *악화*시킨다.

    종합: "경험->의미"는 *짧은-query·in-distribution* 에서 표준 IR 대비 실재 가치(G1 fair). 그러나 OOD
    일반화(G3) 실패 + 미본 class 에서 fusion 이 해롭다. 종착 목표(G1~G4 동시)는 여전히 미달(G2 분포 불가,
    G3 미달, G4 미시행).

    다음(V229): OOD 악화 분해 -> confidence-gated fusion. morph profile 의 support(매칭 질량/coverage)가
    약하면 RRF 에서 morph 가중을 낮춰(또는 제외) 최소한 OOD 에서 bm25Core 이하로 안 떨어지게. 동시에
    char-feature compositional 일반화 가능성(공유 subgram 으로 미본 class 회수) 측정. G3 가 'rrf >= bm25Core
    (OOD)'로 회복되면 일반화 한 칸 전진.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V228_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V228_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V228_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V228_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V228_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V228_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V228_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V228_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V228_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V228_SPPMI_SHIFT", "0.7"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V228_TOPK", "10"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V228_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V228_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V228_RRF_K", "60"))

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
    raw: Counter  # full body tf (unmasked) — 실검색 candidate


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
    """train 에서 title-feature -> *core-masked* body 학습(경험은 title 어휘 자체가 아니라 context)."""
    co: dict[str, Counter] = defaultdict(Counter)
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    for d in trainDocs:
        body = {b for b in d.raw if b not in d.core}  # core-masked
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


def rrfFuse(scoreDicts: list[dict[int, float]], k: int = RRF_K) -> dict[int, float]:
    fused: dict[int, float] = defaultdict(float)
    for scores in scoreDicts:
        if not scores:
            continue
        for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
            fused[pos] += 1.0 / (k + r)
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

    def morphProf(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def bm25Scorer(qid, core):
        return scoreBm25(set(core), bm, testDocs)

    def morphScorer(qid, core):
        return scoreMorph(morphProf(qid, core), inv)

    def rrfScorer(qid, core):
        return rrfFuse([bm25Scorer(qid, core), morphScorer(qid, core)])

    scorers = {"bm25Core": bm25Scorer, "morphSppmi": morphScorer, "rrf(bm25Core,morph)": rrfScorer}
    res = {name: evalClassSplit(queries, posClass, classMembers, fn) for name, fn in scorers.items()}

    nIn = res["bm25Core"]["in"]["n"]
    nOod = res["bm25Core"]["ood"]["n"]
    print("=" * 76)
    print(f"V228 공정 short-query G1 (모든 scorer query=core)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} trainExp(non-OOD)={len(trainExp)} test={len(testDocs)}")
    print(f"queries={len(queries)} classes={len(classMembers)} inDistN={nIn} oodN={nOod}")
    print("-" * 76)
    print(f"{'scorer':<22} | inDist Top1/MRR    | OOD Top1/MRR")
    for name in scorers:
        ri = res[name]["in"]
        ro = res[name]["ood"]
        print(f"{name:<22} | {ri['top1']:.4f}/{ri['mrr']:.4f}      | {ro['top1']:.4f}/{ro['mrr']:.4f}")
    print("-" * 76)
    bIn = res["bm25Core"]["in"]["mrr"]
    rIn = res["rrf(bm25Core,morph)"]["in"]["mrr"]
    mIn = res["morphSppmi"]["in"]["mrr"]
    bOod = res["bm25Core"]["ood"]["mrr"]
    rOod = res["rrf(bm25Core,morph)"]["ood"]["mrr"]
    g1 = rIn > bIn
    g3 = rOod > bOod
    print(
        f"G1(inDist): rrf > bm25Core ? {'YES' if g1 else 'NO'}  (rrf {rIn:.4f} vs bm25Core {bIn:.4f}; morph {mIn:.4f})"
    )
    print(f"G3(OOD)   : rrf > bm25Core 유지 ? {'YES' if g3 else 'NO'}  (rrf {rOod:.4f} vs bm25Core {bOod:.4f})")
    print("-" * 76)
    if g1 and g3:
        v = "한정 확정: 공정 short-query 에서 경험이 강 lexical(bm25Core)에 inDist·OOD 모두 증분. '경험은 짧은-query 확장에서 가치 있음'."
    elif g1 and not g3:
        v = "부분: 경험이 inDist 증분이나 OOD 미유지(G3 미달). 경험은 본 class 에만."
    else:
        v = "프로그램 닫힘: 공정 regime 에서도 경험이 강 lexical 을 못 넘음. 계열축에서도 vanilla IR 대비 가치 없음 확정."
    print(f"VERDICT: {v}")
    print("=" * 76)


if __name__ == "__main__":
    main()
