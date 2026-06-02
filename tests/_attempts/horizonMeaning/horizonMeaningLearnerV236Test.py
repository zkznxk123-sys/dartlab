"""Horizon Meaning Learner V236 - allFilings 의미 조회: 경험그래프 검색이 키워드가 놓친 문서를 건지는가.

재정렬(운영자 교정): 핵심은 *allFilings 문서를 의미로 조회*하는 것. accountMappings 는 "경험->graded 의미"
검증용 자(尺)였을 뿐 목표 아님. V234 가 검증한 경험=의미 그래프는 *엔진*이고, allFilings 에 적용하면
임베딩 없는 *의미 검색* — 질의를 경험그래프로 확장해 키워드가 못 잡는 동의·관련 문서까지 건진다.

    V236 은 그 가치를 정조준한다: 키워드(BM25)가 *놓친* 질의를 의미검색이 건지는가(rescue), 키워드가
    *성공한* 질의를 의미혼입이 *해치는가*(harm). net(rescue≫harm) 이면 의미 조회가 키워드 위에 실재 가치.
    + synonym-gap 슬라이스: gold 문서가 질의어를 본문에 거의 안 쓰는(저-표면중복) 질의에서 의미가 이기는가.

    arm: bm25(키워드) / meaning(1-hop 경험확장) / rrf(하이브리드). query=report_nm core(의미 질의),
    candidate=문서 본문, gold=같은 report_nm class(같은 의미유형) 문서. in-dist(본 유형=실사용). corp-split 누수가드.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV236Test.py
    DARTLAB_HORIZON_V236_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV236Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음. 파일별 load+del(OOM 가드).
    2. 경험그래프는 train(비-test corp)에서만 — query/candidate 누수 없음.
    3. rescue = (bm25 top5 실패) 중 rrf/meaning top5 성공률. harm = (bm25 top1) 중 rrf top5 이탈률.
    4. synonym-gap = gold 본문의 질의어 포함률 하위슬라이스에서 arm 별 MRR.

결과:
    py_compile 통과. 결정적.

    40-file: docs=12734 train=8627 test=2858 inDistQ=2428, build 1.6s, 임베딩/GPU 0
      arm       Top1    Top5    MRR
      bm25      0.7961  0.9114  0.8314
      meaning   0.5507  0.6849  0.6205
      rrf       0.9016  0.9395  0.9258
    rescue (bm25 top5 실패 215건 중 top5 회복): rrf 175/215=0.814  meaning 189/215=0.879
    harm   (bm25 top1 1933건 중 rrf top5 이탈): rrf 79/1933=0.041
    synonym-gap  low(키워드 사각, n=338)   high(완전포함, n=2090)
      bm25       0.4643                 0.8908
      meaning    0.6418  <- 역전!        0.6171
      rrf        0.6031                 0.9780

결론:
    의미 조회 = 실재 가치. 프로젝트 핵심(allFilings 문서를 의미로 조회)을 정면 입증.
    - 의미확장이 *키워드 실패의 81%(rrf)~88%(meaning)*를 top5 로 건짐, harm 4% → 순가치 +0.77.
    - **키워드 사각(저 표면중복) 슬라이스에서 meaning 단독이 bm25 를 역전(0.642 vs 0.464)** — 의미가 키워드가
      못 보는 동의·관련 문서를 본다. 의미 조회의 핵심 증명(검색 척도로 직접).
    - 전체는 rrf 최고(MRR 0.926, Top5 0.940), build 1.6s·임베딩/GPU 0 = 빠른 의미검색 제품성 유지.
    - 정직 단서: 사각 슬라이스에선 rrf(0.603) < meaning(0.642) — 실패한 bm25 와 섞으면 오히려 희석.
      bm25 신뢰도 낮을 때 meaning 비중을 올리는 confidence-gated fusion 이 다음 한 칸.

    종합: V234 가 검증한 경험=의미 그래프가 allFilings 문서 의미 조회에서 키워드 *위*의 실가치(사각 메움)를
    낸다. accountMappings 우회 없이 검색 척도로 직접 입증 — 엔진=1-hop 경험확장, 코어=bm25, 융합=rrf,
    사각 보정=gated(미시행). (V235 의 "구조 grounding"은 이 문서-조회 목표와 별개 분기 — 본선은 의미 조회.)

    다음(V237): confidence-gated fusion — bm25 약하면(저 score/저 findability) meaning 비중 동적 상향.
    목표: 사각 슬라이스를 meaning 수준(~0.64)까지 끌면서 high 슬라이스 0.978 유지 → 단일 엔진이 양 슬라이스 석권.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V236_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V236_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V236_MAX_QUERIES", "2500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V236_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V236_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V236_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V236_EXPAND_TOPN", "60"))
ASSOC_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V236_ASSOC_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V236_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V236_SPPMI_SHIFT", "0.7"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V236_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V236_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V236_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V236_TOPK", "10"))

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
    """질의 의미확장 엔진: core 특징 -> 연관 본문 stem (SPPMI). train(비-test) 에서만."""
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


def rrf(dicts, k=RRF_K):
    f: dict[int, float] = defaultdict(float)
    for sc in dicts:
        if not sc:
            continue
        for r, (pos, _) in enumerate(sorted(sc.items(), key=lambda kv: (-kv[1], kv[0])), start=1):
            f[pos] += 1.0 / (k + r)
    return dict(f)


def firstGoldRank(scores, gold, selfPos):
    ranked = [p for p, _ in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if p != selfPos]
    for r, p in enumerate(ranked[:TOPK], start=1):
        if p in gold:
            return r
    return 0  # top-K 안에 gold 없음


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

    names = ["bm25", "meaning", "rrf"]
    agg = {nm: [0, 0, 0.0] for nm in names}  # top1, top5, mrrSum
    # synonym-gap: gold 본문이 질의어를 얼마나 포함하나 (낮을수록 키워드로 못 찾음)
    findability = []
    perQuery = []  # (ranks dict, findability)
    for pos, core, ck in queries:
        gold = set(classMembers[ck]) - {pos}
        bScore = scoreBm25(core, bm, test)
        mScore = scoreProf(expandMeaning(core, t2b), inv)
        scores = {"bm25": bScore, "meaning": mScore, "rrf": rrf([bScore, mScore])}
        ranks = {nm: firstGoldRank(scores[nm], gold, pos) for nm in names}
        for nm in names:
            r = ranks[nm]
            if r:
                if r == 1:
                    agg[nm][0] += 1
                if r <= 5:
                    agg[nm][1] += 1
                agg[nm][2] += 1.0 / r
        # findability = gold 본문의 질의어 평균 커버리지(연속) — 낮을수록 키워드로 못 찾음(동의어 갭)
        nc = max(1, len(core))
        covs = [sum(1 for t in core if t in test[gp].raw) / nc for gp in gold]
        fnd = sum(covs) / len(covs) if covs else 0.0
        findability.append(fnd)
        perQuery.append((ranks, fnd))

    nq = len(queries)

    # rescue / harm
    rescueDenom = sum(1 for ranks, _ in perQuery if not (0 < ranks["bm25"] <= 5))
    rescueRrf = sum(1 for ranks, _ in perQuery if not (0 < ranks["bm25"] <= 5) and 0 < ranks["rrf"] <= 5)
    rescueMeaning = sum(1 for ranks, _ in perQuery if not (0 < ranks["bm25"] <= 5) and 0 < ranks["meaning"] <= 5)
    harmDenom = sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1)
    harmRrf = sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1 and not (0 < ranks["rrf"] <= 5))

    # synonym-gap slice: 분포가 1.0 에 쏠리므로(대부분 유형은 제목어를 본문이 반복) 완전중복(=1.0) vs
    # 미만(동의어 갭)으로 분할 — low = gold 본문이 질의어를 다 담지 않는 질의(키워드 사각).
    med = float(os.environ.get("DARTLAB_HORIZON_V236_GAP_THRESH", "0.999"))
    lowMrr = {nm: 0.0 for nm in names}
    highMrr = {nm: 0.0 for nm in names}
    lowN = highN = 0
    for ranks, fnd in perQuery:
        isLow = fnd < med
        if isLow:
            lowN += 1
        else:
            highN += 1
        for nm in names:
            r = ranks[nm]
            (lowMrr if isLow else highMrr)[nm] += (1.0 / r) if r else 0.0

    print("=" * 80)
    print(f"V236 allFilings 의미 조회: 키워드가 놓친 문서를 의미가 건지는가  (total {time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq} buildSec={buildSec:.1f}"
    )
    print("-" * 80)
    print(f"{'arm':<10} Top1    Top5    MRR")
    for nm in names:
        h, h5, mrr = agg[nm]
        print(f"{nm:<10} {h / nq:.4f}  {h5 / nq:.4f}  {mrr / nq:.4f}")
    print("-" * 80)
    print("[의미 조회의 순가치]")
    print(
        f"  rescue (bm25 top5 실패 {rescueDenom}건 중 top5 회복): "
        f"rrf {rescueRrf}/{rescueDenom}={rescueRrf / rescueDenom:.3f}  "
        f"meaning {rescueMeaning}/{rescueDenom}={rescueMeaning / rescueDenom:.3f}"
        if rescueDenom
        else "  rescue: bm25 실패 0건"
    )
    print(
        f"  harm   (bm25 top1 {harmDenom}건 중 rrf top5 이탈): rrf {harmRrf}/{harmDenom}={harmRrf / harmDenom:.3f}"
        if harmDenom
        else "  harm: bm25 top1 0건"
    )
    print("-" * 80)
    print(f"[synonym-gap] low=findability<{med} (gold 본문이 질의어 미완전포함=키워드 사각), high=완전포함")
    print(f"{'arm':<10} low-MRR(n={lowN})  high-MRR(n={highN})")
    for nm in names:
        lo = lowMrr[nm] / lowN if lowN else 0.0
        hi = highMrr[nm] / highN if highN else 0.0
        print(f"{nm:<10} {lo:.4f}        {hi:.4f}")
    print("-" * 80)
    mBm = agg["bm25"][2] / nq
    mRrf = agg["rrf"][2] / nq
    loBm = lowMrr["bm25"] / lowN if lowN else 0.0
    loRrf = lowMrr["rrf"] / lowN if lowN else 0.0
    netRescue = (rescueRrf / rescueDenom if rescueDenom else 0.0) - (harmRrf / harmDenom if harmDenom else 0.0)
    print(
        f"VERDICT: 의미 조회 순가치 = rescue-harm = {netRescue:+.3f}. "
        f"저-표면중복 슬라이스 rrf {loRrf:.3f} vs bm25 {loBm:.3f} "
        f"-> {'의미가 키워드 사각을 메움' if loRrf > loBm and netRescue > 0 else '이득 불명확'}"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
