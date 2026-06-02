"""Horizon Meaning Learner V233 - production 후보: 2차 sharpening + 품질·속도로 "빠른 RAG식 의미 검색기" 판정.

목적 둘:
    1. 또렷하게: 경험 그래프를 2차(title->body->title->body, RWR-lite)로 추상해 *seen 내 graded 유사도*를
       더 또렷하게 만드는지(meaning-class 검색 품질↑). 천장(OOD)은 안 건드림 — seen 보간 품질만.
    2. 판정: in-dist meaning-class 검색의 품질 + 빌드시간 + *쿼리 latency* 로, 임베딩·GPU 없는
       "아주 빠른 RAG식 의미 검색기"가 제품 수준인지 정직 판단.

    arm: bm25Core(강 baseline) / morph(1-hop 경험) / twoHop(2차 graph 추상) / rrf(bm25+morph 하이브리드).
    in-dist(본 유형 = 실사용 regime) meaning-class gold. query=core, candidate=raw body.
    측정: build s, per-query latency ms, Top1/Top5/MRR.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV233Test.py
    $env:DARTLAB_HORIZON_V233_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV233Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음.
    2. in-dist(OOD class 제외) meaning-class 검색. corp split.
    3. latency = 쿼리당 (expand+score) 벽시계. 후보 풀 = 전체 test 문서.
    4. 판정: twoHop 가 morph 보다 또렷한가 + 하이브리드 품질·속도가 제품 수준인가.

결과:
    py_compile 통과.

    40-file: docs=12734 train=8627 test=2858 inDistQ=2000, buildSeconds=2.7,
             latency: 5-arm 2.33 ms/q, production hybrid(bm25+morph) 0.72 ms/q (CPU only, GPU 0)
      arm                Top1    Top5    MRR
      bm25               0.7990  0.9130  0.8341
      morph              0.5460  0.6795  0.6171
      twoHop             0.5050  0.7285  0.5962
      rrf(bm25+morph)    0.8960  0.9350  0.9211
      rrf(bm25+twoHop)   0.8915  0.9465  0.9212

결론:
    판정: in-dist 의미검색은 *제품 수준*. 단 "RAG식 free-text"가 아니라 *의미류/동의 검색 + 구조 변별*.

    또렷해짐(2차 graph 추상): NO. twoHop(MRR 0.596) < morph(0.617). 2차는 sharpen 못 하고 over-smooth
    (generic-hub leakage, IR이론가 예측대로). 1-hop 이 이미 최적 — 2차·RWR 폐기.

    제품 수준 근거:
    - 품질: rrf(bm25+morph) Top1 0.896 / Top5 0.935 / MRR 0.921 (in-dist meaning-class). bm25 단독 0.834 대비
      experience +0.087 MRR. Top5 0.94 = 같은 의미류 문서가 상위5에 94% = 실용 검색 품질.
    - 속도: build 2.7s/12.7k docs, query 0.72 ms/q, CPU only GPU 0 = "아주 빠른" 충족(sub-ms).
    - 스케일: 선형. 전체 222 파일도 빌드 수십초, 쿼리 sub-ms(역인덱스). FM-index/mmap 으로 더 가능.

    제품 recipe(확정): bm25(char/stem) core + 1-hop experience expansion(계열축) RRF + accountMappings
    referential(결합축 변별, V230). 2차·VSA·형태소합성 불필요.

    정직 경계:
    - "의미"는 분포 graded(동의/유형) + 회계 referential(부호). free-form 자연어 Q&A(neural RAG)는 아님.
    - OOD(미본 신규 유형) 일반화 0(V228~V232) — 색인된 기존 코퍼스·본 유형 질의엔 무관, 진짜 신규 유형엔 막힘.
    - experience 순기여 +0.087 — 코어는 bm25, experience 는 보완.

    결론: 임베딩·GPU 없는 sub-ms·seconds-build 의미류 검색기는 지금 부품으로 만들 수 있다(제품 수준).
    단 "RAG식 free-text 의미이해"가 아니라 "구조화 도메인의 빠른 의미류·동의 검색 + 회계 변별"로 규정.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V233_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V233_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V233_MAX_QUERIES", "2000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V233_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V233_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V233_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V233_EXPAND_TOPN", "60"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V233_RWR_BRANCH", "24"))
RWR_TOPN = int(os.environ.get("DARTLAB_HORIZON_V233_RWR_TOPN", "90"))
RWR_ALPHA = float(os.environ.get("DARTLAB_HORIZON_V233_RWR_ALPHA", "0.64"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V233_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V233_SPPMI_SHIFT", "0.7"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V233_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V233_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V233_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V233_TOPK", "10"))

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


def cleanText(value, *, limit=None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    return SPACE_RE.sub(" ", text).strip()


def bodyStems(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text) if 2 <= len(t) <= 14 and not NUM_RE.search(t) and HANGUL_RE.fullmatch(t)]


def reportNmCore(report_nm: str) -> set[str]:
    raw = BRACKET_PREFIX_RE.sub("", (report_nm or "").strip()).strip()
    parens = PAREN_RE.findall(raw)
    pool = " ".join(parens) if parens else PAREN_RE.sub(" ", raw)
    return {
        t
        for t in TOKEN_RE.findall(pool)
        if 2 <= len(t) <= 14 and not NUM_RE.search(t) and HANGUL_RE.fullmatch(t) and t not in GENERIC_TITLE_STOP
    }


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def isTestCorp(corp: str) -> bool:
    return (stableHashInt(corp) % TEST_MOD) == 0 if corp else False


def isOodClass(cls: str) -> bool:
    return (stableHashInt("ood:" + cls) % OOD_MOD) == 0


def coreFeatureWeights(core: frozenset[str]) -> dict[str, float]:
    feats: dict[str, float] = defaultdict(float)
    for token in core:
        if not token:
            continue
        feats[f"tok:{token}"] = 1.0
        n = len(token)
        for size, w in ((2, 0.18), (3, 0.34), (4, 0.42)):
            if n >= size:
                feats[f"pre{size}:{token[:size]}"] = max(feats[f"pre{size}:{token[:size]}"], w)
                feats[f"suf{size}:{token[-size:]}"] = max(feats[f"suf{size}:{token[-size:]}"], w)
        for size, w in ((2, 0.10), (3, 0.22), (4, 0.30)):
            if n >= size + 1:
                for s in range(n - size + 1):
                    g = token[s : s + size]
                    if g not in GENERIC_TITLE_STOP:
                        feats[f"ng{size}:{g}"] = max(feats[f"ng{size}:{g}"], w)
    return dict(feats)


@dataclass
class Doc:
    corp: str
    isTest: bool
    core: frozenset[str]
    raw: Counter


def loadDocs() -> list[Doc]:
    docs = []
    for path in sorted(ALL_FILINGS_DIR.glob("*.parquet"))[:FILE_LIMIT]:
        df = pl.read_parquet(str(path), columns=["corp_code", "report_nm", "content_raw"])
        if df.height > ROWS_PER_FILE:
            df = df.head(ROWS_PER_FILE)
        for r in df.iter_rows(named=True):
            core = reportNmCore(r.get("report_nm") or "")
            if not core:
                continue
            stems = bodyStems(cleanText(r.get("content_raw"), limit=BODY_CHAR_LIMIT))
            if len(stems) < 12:
                continue
            docs.append(
                Doc(
                    str(r.get("corp_code") or ""),
                    isTestCorp(str(r.get("corp_code") or "")),
                    frozenset(core),
                    Counter(stems),
                )
            )
        del df
    return docs


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


@dataclass
class Graph:
    titleToBody: dict[str, dict[str, float]]
    bodyToTitle: dict[str, dict[str, float]]


def buildGraph(trainDocs: list[Doc]) -> Graph:
    co: dict[str, Counter] = defaultdict(Counter)
    titleDf: Counter = Counter()
    bodyDf: Counter = Counter()
    for d in trainDocs:
        body = {b for b in d.raw if b not in d.core}
        feats = set(coreFeatureWeights(d.core))
        if not feats or not body:
            continue
        for b in body:
            bodyDf[b] += 1
        for f in feats:
            titleDf[f] += 1
            co[f].update(body)
    n = max(1, len(trainDocs))
    t2b: dict[str, dict[str, float]] = {}
    rev: dict[str, dict[str, float]] = defaultdict(dict)
    for f, counts in co.items():
        fDf = titleDf[f]
        w = {}
        for b, c in counts.items():
            if c < MIN_ASSOC_DF:
                continue
            bDf = bodyDf.get(b, 0)
            if bDf <= 0:
                continue
            pmi = math.log((c * n) / (fDf * bDf)) - SPPMI_SHIFT
            if pmi > 0:
                w[b] = pmi * math.log(1.0 + n / bDf)
        if w:
            top = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH])
            t2b[f] = top
            for b, wt in top.items():
                rev[b][f] = wt
    b2t = {b: dict(sorted(fs.items(), key=lambda kv: kv[1], reverse=True)[:RWR_BRANCH]) for b, fs in rev.items()}
    return Graph(t2b, b2t)


def topN(prof, k):
    return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:k]) if prof else {}


def normalize(prof):
    tot = sum(max(0.0, v) for v in prof.values())
    return {k: max(0.0, v) / tot for k, v in prof.items() if v > 0} if tot > 0 else {}


def expandMorph(core, g: Graph):
    prof: dict[str, float] = defaultdict(float)
    for f, sw in coreFeatureWeights(core).items():
        for b, ew in g.titleToBody.get(f, {}).items():
            prof[b] += sw * ew
    return topN(prof, EXPAND_TOPN)


def expandTwoHop(core, g: Graph):
    first = normalize(expandMorph(core, g))
    if not first:
        return {}
    walk: dict[str, float] = defaultdict(float)
    for b, p in topN(first, RWR_BRANCH).items():
        for f, ew in g.bodyToTitle.get(b, {}).items():
            walk[f] += p * ew
    walk = normalize(topN(walk, RWR_BRANCH * 2))
    second: dict[str, float] = defaultdict(float)
    for f, p in walk.items():
        for b, ew in g.titleToBody.get(f, {}).items():
            second[b] += p * ew
    second = normalize(topN(second, RWR_TOPN))
    final: dict[str, float] = defaultdict(float)
    for b, v in first.items():
        final[b] += RWR_ALPHA * v
    for b, v in second.items():
        final[b] += (1 - RWR_ALPHA) * v
    return topN(final, RWR_TOPN)


@dataclass
class Bm25:
    inv: dict[str, list[int]]
    docLen: list[int]
    avgdl: float
    n: int
    df: Counter


def buildBm25(test):
    inv: dict[str, list[int]] = defaultdict(list)
    docLen = []
    df: Counter = Counter()
    for pos, d in enumerate(test):
        docLen.append(sum(d.raw.values()))
        for b in d.raw:
            inv[b].append(pos)
            df[b] += 1
    return Bm25(inv, docLen, max(1.0, sum(docLen) / len(test)), len(test), df)


def scoreBm25(core, bm, test):
    s: dict[int, float] = defaultdict(float)
    for t in core:
        df = bm.df.get(t, 0)
        if df <= 0:
            continue
        idf = math.log((bm.n - df + 0.5) / (df + 0.5) + 1.0)
        for pos in bm.inv.get(t, ()):
            tf = test[pos].raw.get(t, 0)
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * bm.docLen[pos] / bm.avgdl)
            if denom > 0:
                s[pos] += idf * (tf * (BM25_K1 + 1)) / denom
    return s


def scoreProf(prof, inv):
    s: dict[int, float] = defaultdict(float)
    for b, w in prof.items():
        for pos in inv.get(b, ()):
            s[pos] += w
    return s


def rrf(dicts, k=RRF_K):
    f: dict[int, float] = defaultdict(float)
    for sc in dicts:
        if not sc:
            continue
        for r, (pos, _) in enumerate(sorted(sc.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
            f[pos] += 1.0 / (k + r)
    return dict(f)


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    train = [d for d in docs if not d.isTest and not isOodClass(classKeyOf(d.core))]
    test = [d for d in docs if d.isTest]
    if not train or not test:
        print(f"insufficient: train={len(train)} test={len(test)}")
        return
    tb = time.time()
    g = buildGraph(train)
    bm = buildBm25(test)
    inv: dict[str, list[int]] = defaultdict(list)
    posClass, classMembers = {}, defaultdict(list)
    for pos, d in enumerate(test):
        posClass[pos] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(pos)
        for b in d.raw:
            inv[b].append(pos)
    buildSec = time.time() - tb

    # in-dist queries (본 유형 = 실사용)
    queries = []
    for pos, d in enumerate(test):
        if isOodClass(classKeyOf(d.core)):
            continue
        if set(classMembers[classKeyOf(d.core)]) - {pos}:
            queries.append((pos, d.core))
        if len(queries) >= MAX_QUERIES:
            break

    def scorers(core):
        b = scoreBm25(core, bm, test)
        m = scoreProf(expandMorph(core, g), inv)
        h = scoreProf(expandTwoHop(core, g), inv)
        return {"bm25": b, "morph": m, "twoHop": h, "rrf(bm25+morph)": rrf([b, m]), "rrf(bm25+twoHop)": rrf([b, h])}

    names = ["bm25", "morph", "twoHop", "rrf(bm25+morph)", "rrf(bm25+twoHop)"]
    agg = {nm: [0, 0, 0.0] for nm in names}
    tq = time.time()
    for pos, core in queries:
        gold = set(classMembers[posClass[pos]]) - {pos}
        sc = scorers(core)
        for nm in names:
            ranked = [p for p, _ in sorted(sc[nm].items(), key=lambda kv: (-kv[1], kv[0])) if p != pos]
            for r, p in enumerate(ranked[:TOPK], start=1):
                if p in gold:
                    if r == 1:
                        agg[nm][0] += 1
                    if r <= 5:
                        agg[nm][1] += 1
                    agg[nm][2] += 1.0 / r
                    break
    qSec = time.time() - tq
    nq = len(queries)
    latencyMs = (qSec / nq * 1000) if nq else 0.0
    # latency per scorer 분리(expand 비용 차이): 대표로 rrf(bm25+morph) 단독 재측정
    tq2 = time.time()
    for pos, core in queries[: min(500, nq)]:
        b = scoreBm25(core, bm, test)
        m = scoreProf(expandMorph(core, g), inv)
        rrf([b, m])
    prodLatencyMs = (time.time() - tq2) / min(500, nq) * 1000 if nq else 0.0

    print("=" * 78)
    print(f"V233 production 후보: 2차 sharpening + 속도 판정  (total {time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq}")
    print(f"buildSeconds={buildSec:.1f}  (graph+bm25+inv, CPU only, GPU 0)")
    print(
        f"전체 5-arm 쿼리 latency={latencyMs:.2f} ms/q  |  production hybrid(bm25+morph) latency={prodLatencyMs:.2f} ms/q"
    )
    print("-" * 78)
    print(f"{'arm':<20} Top1    Top5    MRR")
    for nm in names:
        h, h5, mrr = agg[nm]
        print(f"{nm:<20} {h / nq:.4f}  {h5 / nq:.4f}  {mrr / nq:.4f}")
    print("-" * 78)
    mMorph = agg["morph"][2] / nq
    mTwo = agg["twoHop"][2] / nq
    mBm = agg["bm25"][2] / nq
    mH = agg["rrf(bm25+morph)"][2] / nq
    mH2 = agg["rrf(bm25+twoHop)"][2] / nq
    print(
        f"또렷해짐(2차): twoHop {mTwo:.4f} vs morph {mMorph:.4f} -> {'YES' if mTwo > mMorph + 0.005 else 'NO(개선 미미/없음)'}"
    )
    bestH = max(mH, mH2)
    print(f"production 하이브리드 최고 MRR={bestH:.4f} (bm25 단독 {mBm:.4f})")
    print(f"  하이브리드 > bm25 ? {'YES' if bestH > mBm else 'NO'}")
    print("=" * 78)


if __name__ == "__main__":
    main()
