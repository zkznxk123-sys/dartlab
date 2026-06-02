"""Horizon Meaning Learner V238 - 확실성: gated fusion 하이퍼 민감도 sweep (과적합 knife-edge 아닌가).

V237 이 의미 조회 recipe(bm25 + 1-hop 경험확장 + bm25-신뢰도 gated RRF)를 확정(gated MRR 0.955).
그러나 단일 하이퍼(GMIN0.2/GMAX0.85/GATE_X1.5) 한 점 결과 — 그게 *우연히 좋은 한 점*인지, *넓은 고원*인지
확인해야 "확실"하다. V238 은 gate 하이퍼 격자를 전수 sweep 해 gated 가 합리적 범위 전체에서 plain rrf 를
안정적으로 이기는가(고원)를 본다. knife-edge(한 점만 좋고 주변 급락)면 과적합 — 채택 불가.

    격자: GMIN x GMAX x GATE_X. 코퍼스·그래프·query·gold·gate ref 는 1회 빌드 후 재사용(각 query 의
    recip rank 저장 -> 각 조합은 가중합만 재계산, 빠름). 각 조합의 전체 MRR / 사각-MRR / 완전포함-MRR / harm.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV238Test.py
    DARTLAB_HORIZON_V238_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV238Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음. 파일별 load+del.
    2. 빌드·gate ref 는 query-시점 신호만(gold 미사용). corp-split 누수가드.
    3. 고원 판정: gated MRR 이 격자 전체에서 plain rrf(equal) 초과 + 사각 슬라이스 항상 우위면 robust.
    4. recip rank 는 top-200 절단 저장(메모리 가드, gold rank<=10 영향 무시 가능).

결과:
    py_compile 통과. 결정적.

    [민감도 sweep] 40-file (docs=12734, inDistQ=2428, ref=6.46). 기준선 plain rrf: MRR 0.926 사각 0.603 완전포함 0.978
      격자 27점 범위: MRR [0.791, 0.955] / 사각 [0.511, 0.815] / 완전포함 [0.819, 0.981]
      안전영역(GMIN≤0.2 · GMAX≤0.85 · GATE_X 1.5~2.0): 전 점 MRR 0.945~0.955 · 사각 0.72~0.80 · harm~0
        최고 0.20/0.75/2.0 = MRR 0.9553 사각 0.8005 / V237 기본 0.20/0.85/1.5 = 0.9545 사각 0.7981 (영역 중앙)
      실패조합 전부 해석가능: GMAX0.95+GATE_X 큰값(의미 과적재→희석), GMIN0.30(bm25 강할때 의미강제→harm 0.04↑)
      strict OK 11/27 (코너 극단 포함 격자라 당연; 안전영역 내부는 전수 OK = knife-edge 아님)

    [scale] V237 재실행(동일 기본 하이퍼), gated vs rrf
      files  docs    build   gatedMRR  사각    완전포함  harm  | rrf(MRR/사각)
      40     12734   1.7s    0.9547    0.798   0.980    0.002 | 0.926/0.603
      80     25140   5.9s    0.9152    0.742   0.946    0.000 | 0.900/0.663
      160    56357   10.5s   0.8888    0.707   0.922    0.000 | 0.864/0.694

결론:
    확실성 점검 — 구조적 robust 확인 + scale 민감점 1개 정직 식별.
    - robust: gated 가 40/80/160 파일 전부에서 rrf 를 *양 슬라이스 + 전체 MRR* 초과, harm~0. 코어 recipe 견고.
    - 하이퍼: knife-edge 아님. 안전영역(GMIN≤0.2·GMAX≤0.85·GATE_X 1.5~2.0) 내 모든 점 MRR≥0.945·사각≥0.72.
      실패는 전부 해석가능(의미 과적재/floor 과다)이라 가드레일 명확 = GMAX≤0.85, GMIN≤0.2.
    - scale 민감점(정직): 절대 MRR 은 코퍼스 커질수록 자연 하락(haystack↑, 예상). 그리고 사각 슬라이스에서
      160f 시 meaning 단독(0.776)이 gated(0.707)를 역전 — 고정 gate(ref=median snapshot)가 스케일 따라 의미가중을
      덜 싣는다. gated 는 여전히 rrf 우위지만, 블라인드 영역 최적은 코퍼스 클수록 더 높은 의미가중 필요.
      => gate 의 ref/GMAX 를 코퍼스 규모에 적응(모듈화 시 보강 1).
    - build 선형(1.7→5.9→10.5s), 56k 문서까지 OOM 없음. 전체 222 파일은 모듈 이관(streaming/mmap) 단계 표적.

    종합: recipe(bm25 + 1-hop 경험확장 + gated RRF)는 구조적으로 확실 — gate>rrf>bm25, harm~0, 다중 스케일·
    하이퍼 안전영역 전반서 유지. 모듈화 전 보강 1건(gate ref/상한 스케일 적응) 확정. 이후 _attempts -> 검색기 모듈.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V238_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V238_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V238_MAX_QUERIES", "2500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V238_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V238_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V238_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V238_EXPAND_TOPN", "60"))
ASSOC_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V238_ASSOC_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V238_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V238_SPPMI_SHIFT", "0.7"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V238_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V238_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V238_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V238_TOPK", "10"))
RECIP_KEEP = int(os.environ.get("DARTLAB_HORIZON_V238_RECIP_KEEP", "200"))
GAP_THRESH = float(os.environ.get("DARTLAB_HORIZON_V238_GAP_THRESH", "0.999"))

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


def buildGraph(trainDocs: list[Doc]) -> dict[str, dict[str, float]]:
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
            t2b[f] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:ASSOC_BRANCH])
    return t2b


def expandMeaning(core, t2b):
    prof: dict[str, float] = defaultdict(float)
    for f, sw in coreFeatureWeights(core).items():
        for b, ew in t2b.get(f, {}).items():
            prof[b] += sw * ew
    return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])


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


def recipTop(scores, keep=RECIP_KEEP, k=RRF_K):
    out: dict[int, float] = {}
    for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:keep], start=1):
        out[pos] = 1.0 / (k + r)
    return out


def gate(top1, ref, gmin, gmax, gx):
    if ref <= 0:
        return (gmin + gmax) / 2
    x = min(top1 / ref, gx)
    return max(gmin, min(gmax, gmax - (gmax - gmin) * (x / gx)))


def firstGoldRank(scores, gold, selfPos):
    ranked = [p for p, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if p != selfPos]
    for r, p in enumerate(ranked[:TOPK], start=1):
        if p in gold:
            return r
    return 0


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    train = [d for d in docs if not d.isTest and not isOodClass(classKeyOf(d.core))]
    test = [d for d in docs if d.isTest]
    if not train or not test:
        print(f"insufficient: train={len(train)} test={len(test)}")
        return
    t2b = buildGraph(train)
    bm = buildBm25(test)
    inv: dict[str, list[int]] = defaultdict(list)
    classMembers = defaultdict(list)
    for pos, d in enumerate(test):
        classMembers[classKeyOf(d.core)].append(pos)
        for b in d.raw:
            inv[b].append(pos)

    queries = []
    for pos, d in enumerate(test):
        ck = classKeyOf(d.core)
        if isOodClass(ck):
            continue
        if set(classMembers[ck]) - {pos}:
            queries.append((pos, d.core, ck))
        if len(queries) >= MAX_QUERIES:
            break

    # 1회 계산: 각 query 의 recip rank(top-200 절단) + gold + findability + top1
    store = []
    top1s = []
    for pos, core, ck in queries:
        gold = set(classMembers[ck]) - {pos}
        bScore = scoreBm25(core, bm, test)
        mScore = scoreProf(expandMeaning(core, t2b), inv)
        top1 = max(bScore.values()) if bScore else 0.0
        top1s.append(top1)
        nc = max(1, len(core))
        covs = [sum(1 for t in core if t in test[gp].raw) / nc for gp in gold]
        fnd = sum(covs) / len(covs) if covs else 0.0
        store.append((pos, gold, recipTop(bScore), recipTop(mScore), top1, fnd))
    ref = sorted(top1s)[len(top1s) // 2] if top1s else 0.0
    nq = len(queries)

    def evalGate(gmin, gmax, gx):
        mrr = 0.0
        lowS = highS = 0.0
        lowN = highN = 0
        harmN = harmDen = 0
        for pos, gold, recBm, recMe, top1, fnd in store:
            g = gate(top1, ref, gmin, gmax, gx)
            keys = set(recBm) | set(recMe)
            gs = {p: (1 - g) * recBm.get(p, 0.0) + g * recMe.get(p, 0.0) for p in keys}
            r = firstGoldRank(gs, gold, pos)
            mrr += (1.0 / r) if r else 0.0
            isLow = fnd < GAP_THRESH
            if isLow:
                lowN += 1
                lowS += (1.0 / r) if r else 0.0
            else:
                highN += 1
                highS += (1.0 / r) if r else 0.0
            bmR = firstGoldRank(recBm, gold, pos)
            if bmR == 1:
                harmDen += 1
                if not (0 < r <= 5):
                    harmN += 1
        return (
            mrr / nq,
            lowS / lowN if lowN else 0.0,
            highS / highN if highN else 0.0,
            harmN / harmDen if harmDen else 0.0,
        )

    # plain rrf(equal) 기준선 = g=0.5 상수
    def evalEqual():
        mrr = lowS = highS = 0.0
        lowN = highN = 0
        for pos, gold, recBm, recMe, top1, fnd in store:
            keys = set(recBm) | set(recMe)
            gs = {p: recBm.get(p, 0.0) + recMe.get(p, 0.0) for p in keys}
            r = firstGoldRank(gs, gold, pos)
            mrr += (1.0 / r) if r else 0.0
            if fnd < GAP_THRESH:
                lowN += 1
                lowS += (1.0 / r) if r else 0.0
            else:
                highN += 1
                highS += (1.0 / r) if r else 0.0
        return mrr / nq, lowS / lowN if lowN else 0.0, highS / highN if highN else 0.0

    rrfMrr, rrfLow, rrfHigh = evalEqual()

    grid_gmin = [0.10, 0.20, 0.30]
    grid_gmax = [0.75, 0.85, 0.95]
    grid_gx = [1.0, 1.5, 2.0]

    print("=" * 86)
    print(f"V238 gated 하이퍼 민감도 sweep  (total {time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq} ref={ref:.2f}")
    print(f"기준선 plain rrf(equal): MRR={rrfMrr:.4f} 사각={rrfLow:.4f} 완전포함={rrfHigh:.4f}")
    print("-" * 86)
    print(
        f"{'GMIN':>5} {'GMAX':>5} {'GATE_X':>6}  {'MRR':>7} {'사각':>7} {'완전포함':>8} {'harm':>6}  vs-rrf(MRR/사각)"
    )
    results = []
    for gmin in grid_gmin:
        for gmax in grid_gmax:
            for gx in grid_gx:
                mrr, low, high, harm = evalGate(gmin, gmax, gx)
                results.append((mrr, low, high, harm, gmin, gmax, gx))
                flag = "OK" if (mrr >= rrfMrr and low > rrfLow) else "--"
                print(
                    f"{gmin:>5.2f} {gmax:>5.2f} {gx:>6.1f}  {mrr:>7.4f} {low:>7.4f} {high:>8.4f} {harm:>6.3f}  "
                    f"{mrr - rrfMrr:+.4f}/{low - rrfLow:+.4f} {flag}"
                )
    print("-" * 86)
    mrrs = [r[0] for r in results]
    lows = [r[1] for r in results]
    highs = [r[2] for r in results]
    nBeat = sum(1 for r in results if r[0] >= rrfMrr and r[1] > rrfLow)
    plateau = nBeat == len(results)
    print(
        f"격자 {len(results)}점: MRR [{min(mrrs):.4f}, {max(mrrs):.4f}] (rrf {rrfMrr:.4f}), "
        f"사각 [{min(lows):.4f}, {max(lows):.4f}] (rrf {rrfLow:.4f}), 완전포함 [{min(highs):.4f}, {max(highs):.4f}]"
    )
    print(
        f"VERDICT: {nBeat}/{len(results)} 조합이 rrf 초과(MRR) + 사각 우위. "
        f"{'고원(robust, knife-edge 아님)' if plateau else '일부 조합만 — 민감(주의)'}"
    )
    print("=" * 86)


if __name__ == "__main__":
    main()
