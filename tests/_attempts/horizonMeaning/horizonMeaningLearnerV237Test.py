"""Horizon Meaning Learner V237 - confidence-gated fusion: 키워드 약하면 의미 비중 동적 상향.

V236 입증: allFilings 의미 조회는 키워드 위의 실가치(사각 메움). 단 약점 — 키워드 사각 슬라이스에서
plain rrf(0.603) < meaning 단독(0.642): 실패한 bm25 와 동등가중으로 섞으면 오히려 희석.

    V237 은 그 한 칸을 친다: 질의-시점 bm25 신뢰도(top1 score)로 융합가중을 동적 조절.
    bm25 강함(top1 score 높음=키워드로 잘 찾음) -> bm25 비중↑(rrf 수준 유지). bm25 약함(사각) -> 의미 비중↑.
    목표: gated 가 사각 슬라이스를 meaning(~0.64)까지 끌면서 완전포함 슬라이스 0.978 유지 = 한 엔진이 양쪽 석권.

    신뢰도 = bm25 top1 raw score (gold 미사용, 순수 질의-시점 신호). ref = 질의셋 median top1 로 정규화.
    가중 RRF: gated[pos] = (1-g)*recip_bm[pos] + g*recip_me[pos], g = 의미가중(bm25 약할수록 ↑).
    arm: bm25 / meaning / rrf(동등) / gated. 그 외 데이터·gold·누수가드·rescue·synonym-gap 은 V236 동일.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV237Test.py
    DARTLAB_HORIZON_V237_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV237Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음. 파일별 load+del.
    2. 그래프·gate ref 는 query-시점 신호만(gold 미사용). corp-split 누수가드.
    3. gated 가 (a) 사각 슬라이스 MRR > plain rrf, (b) 완전포함 슬라이스 ≈ rrf, (c) 전체 MRR ≥ rrf 면 성공.
    4. 단일 하이퍼(GMIN/GMAX/GATE_X) 고정. 결정적.

결과:
    py_compile 통과. 결정적.

    40-file: docs=12734 train=8627 test=2858 inDistQ=2428, build 1.7s, 임베딩/GPU 0
    gate: ref(median bm25 top1)=6.46, g범위[0.2,0.85] GATE_X=1.5, 평균g=0.428
      arm       Top1    Top5    MRR     사각(n=338)  완전포함(n=2090)
      bm25      0.7961  0.9114  0.8314  0.4643       0.8908
      meaning   0.5507  0.6845  0.6205  0.6414       0.6171
      rrf(동등)  0.9020  0.9395  0.9260  0.6031       0.9782
      gated     0.9370  0.9806  0.9547  0.7981       0.9800
    rescue (bm25 top5 실패 215): meaning 0.879 / rrf 0.814 / gated 0.800
    harm   (bm25 top1 1933):    rrf 0.041 / gated 0.002

결론:
    성공(목표 초과) — confidence-gated fusion 이 양 슬라이스 동시 석권. V236 마지막 약점(사각에서 rrf 희석) 해소.
    - gated MRR 0.955 (rrf 0.926·bm25 0.831 모두 상회), Top5 0.981.
    - 사각 슬라이스 gated 0.798: plain rrf(0.603) 대폭 상회 + **meaning 단독(0.641)마저 상회** — 잔여 bm25 신호 +
      의미 고가중 융합이 두 단일 arm 보다 우월(목표 ~0.64 초과). 키워드가 못 보는 문서를 가장 잘 건진다.
    - 완전포함 슬라이스 0.980 ≈ rrf 0.978 유지(희생 0). harm 0.002 ≈ 0(rrf 0.041 의 1/20) — 키워드 성공 거의 안 해침.
    - gate 는 query-시점 bm25 top1 신뢰도만 사용(gold 미사용), build 1.7s·임베딩/GPU 0.

    최종 recipe 확정(allFilings 의미 조회): **bm25 코어 + 1-hop 경험확장 + bm25-신뢰도 gated RRF.**
    경험=의미 그래프(V234 검증)가 문서 의미 조회에서 키워드 *위*의 실가치를 안정적으로 낸다 — MRR 0.955,
    사각 0.798, 완전포함 0.980, harm~0, sub-2s build, GPU 0. 프로젝트 핵심(빠른 의미 검색) 부품 완성.

    다음: (1) gate 하이퍼(GMIN/GMAX/GATE_X) 민감도·안정성, (2) 전체 222 파일 스케일, (3) _attempts -> 실제
    검색기 모듈 이관(쿼리스트링->랭킹 API, 전체 색인, mmap/FM-index).
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V237_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V237_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V237_MAX_QUERIES", "2500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V237_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V237_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V237_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V237_EXPAND_TOPN", "60"))
ASSOC_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V237_ASSOC_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V237_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V237_SPPMI_SHIFT", "0.7"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V237_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V237_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V237_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V237_TOPK", "10"))
GMIN = float(os.environ.get("DARTLAB_HORIZON_V237_GMIN", "0.20"))
GMAX = float(os.environ.get("DARTLAB_HORIZON_V237_GMAX", "0.85"))
GATE_X = float(os.environ.get("DARTLAB_HORIZON_V237_GATE_X", "1.5"))
GAP_THRESH = float(os.environ.get("DARTLAB_HORIZON_V237_GAP_THRESH", "0.999"))

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


def recipRanks(scores, k=RRF_K):
    """RRF 기여항 pos -> 1/(k+rank)."""
    out: dict[int, float] = {}
    for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
        out[pos] = 1.0 / (k + r)
    return out


def meaningGate(bmTop1, ref):
    """bm25 top1 신뢰도로 의미가중 g 산출. bm25 약할수록(top1 낮을수록) g↑."""
    if ref <= 0:
        return (GMIN + GMAX) / 2
    x = min(bmTop1 / ref, GATE_X)  # x>=GATE_X 면 충분히 신뢰 -> gmin
    g = GMAX - (GMAX - GMIN) * (x / GATE_X)
    return max(GMIN, min(GMAX, g))


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
    tb = time.time()
    t2b = buildGraph(train)
    bm = buildBm25(test)
    inv: dict[str, list[int]] = defaultdict(list)
    classMembers = defaultdict(list)
    for pos, d in enumerate(test):
        classMembers[classKeyOf(d.core)].append(pos)
        for b in d.raw:
            inv[b].append(pos)
    buildSec = time.time() - tb

    queries = []
    for pos, d in enumerate(test):
        ck = classKeyOf(d.core)
        if isOodClass(ck):
            continue
        if set(classMembers[ck]) - {pos}:
            queries.append((pos, d.core, ck))
        if len(queries) >= MAX_QUERIES:
            break

    # pass A: bm25 top1 분포 -> ref(median) (query-시점 신호, gold 미사용)
    top1s = []
    for pos, core, ck in queries:
        bScore = scoreBm25(core, bm, test)
        top1s.append(max(bScore.values()) if bScore else 0.0)
    ref = sorted(top1s)[len(top1s) // 2] if top1s else 0.0

    names = ["bm25", "meaning", "rrf", "gated"]
    agg = {nm: [0, 0, 0.0] for nm in names}
    perQuery = []
    gateVals = []
    for qi, (pos, core, ck) in enumerate(queries):
        gold = set(classMembers[ck]) - {pos}
        bScore = scoreBm25(core, bm, test)
        mScore = scoreProf(expandMeaning(core, t2b), inv)
        recBm = recipRanks(bScore)
        recMe = recipRanks(mScore)
        rrfScore = {p: recBm.get(p, 0.0) + recMe.get(p, 0.0) for p in set(recBm) | set(recMe)}
        g = meaningGate(top1s[qi], ref)
        gateVals.append(g)
        gatedScore = {p: (1 - g) * recBm.get(p, 0.0) + g * recMe.get(p, 0.0) for p in set(recBm) | set(recMe)}
        scores = {"bm25": bScore, "meaning": mScore, "rrf": rrfScore, "gated": gatedScore}
        ranks = {nm: firstGoldRank(scores[nm], gold, pos) for nm in names}
        for nm in names:
            r = ranks[nm]
            if r:
                if r == 1:
                    agg[nm][0] += 1
                if r <= 5:
                    agg[nm][1] += 1
                agg[nm][2] += 1.0 / r
        nc = max(1, len(core))
        covs = [sum(1 for t in core if t in test[gp].raw) / nc for gp in gold]
        fnd = sum(covs) / len(covs) if covs else 0.0
        perQuery.append((ranks, fnd))

    nq = len(queries)

    def top5(ranks, nm):
        return 0 < ranks[nm] <= 5

    rescueDenom = sum(1 for ranks, _ in perQuery if not top5(ranks, "bm25"))
    rescue = {
        nm: sum(1 for ranks, _ in perQuery if not top5(ranks, "bm25") and top5(ranks, nm))
        for nm in ("rrf", "gated", "meaning")
    }
    harmDenom = sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1)
    harm = {
        nm: sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1 and not top5(ranks, nm)) for nm in ("rrf", "gated")
    }

    lowMrr = {nm: 0.0 for nm in names}
    highMrr = {nm: 0.0 for nm in names}
    lowN = highN = 0
    for ranks, fnd in perQuery:
        isLow = fnd < GAP_THRESH
        if isLow:
            lowN += 1
        else:
            highN += 1
        for nm in names:
            r = ranks[nm]
            (lowMrr if isLow else highMrr)[nm] += (1.0 / r) if r else 0.0

    print("=" * 82)
    print(f"V237 confidence-gated fusion: 키워드 약하면 의미 비중↑  (total {time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq} buildSec={buildSec:.1f}"
    )
    print(
        f"gate: ref(median bm25 top1)={ref:.2f}  g 범위[{GMIN},{GMAX}] GATE_X={GATE_X}  평균g={sum(gateVals) / len(gateVals):.3f}"
    )
    print("-" * 82)
    print(f"{'arm':<10} Top1    Top5    MRR")
    for nm in names:
        h, h5, mrr = agg[nm]
        print(f"{nm:<10} {h / nq:.4f}  {h5 / nq:.4f}  {mrr / nq:.4f}")
    print("-" * 82)
    if rescueDenom:
        print(
            f"rescue (bm25 top5 실패 {rescueDenom}): "
            + "  ".join(f"{nm} {rescue[nm] / rescueDenom:.3f}" for nm in ("meaning", "rrf", "gated"))
        )
    if harmDenom:
        print(
            f"harm   (bm25 top1 {harmDenom}): "
            + "  ".join(f"{nm} {harm[nm] / harmDenom:.3f}" for nm in ("rrf", "gated"))
        )
    print("-" * 82)
    print(f"[synonym-gap] low=findability<{GAP_THRESH} (키워드 사각, n={lowN})  high=완전포함 (n={highN})")
    print(f"{'arm':<10} low-MRR   high-MRR")
    for nm in names:
        lo = lowMrr[nm] / lowN if lowN else 0.0
        hi = highMrr[nm] / highN if highN else 0.0
        print(f"{nm:<10} {lo:.4f}    {hi:.4f}")
    print("-" * 82)
    loRrf = lowMrr["rrf"] / lowN if lowN else 0.0
    loGated = lowMrr["gated"] / lowN if lowN else 0.0
    loMeaning = lowMrr["meaning"] / lowN if lowN else 0.0
    hiRrf = highMrr["rrf"] / highN if highN else 0.0
    hiGated = highMrr["gated"] / highN if highN else 0.0
    mRrf = agg["rrf"][2] / nq
    mGated = agg["gated"][2] / nq
    ok = loGated > loRrf and hiGated >= hiRrf - 0.01 and mGated >= mRrf - 0.005
    print(
        f"VERDICT: gated 사각 {loGated:.3f}(vs rrf {loRrf:.3f}, meaning {loMeaning:.3f}) / "
        f"완전포함 {hiGated:.3f}(vs rrf {hiRrf:.3f}) / 전체 {mGated:.3f}(vs rrf {mRrf:.3f}) "
        f"-> {'성공: gate 가 양 슬라이스 동시 석권' if ok else '부분/미달'}"
    )
    print("=" * 82)


if __name__ == "__main__":
    main()
