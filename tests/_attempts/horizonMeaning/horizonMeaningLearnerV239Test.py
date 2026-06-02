"""Horizon Meaning Learner V239 - 씨앗 정렬: 진짜 stem-수평선 경험그래프로 의미 조회 (제목→본문과 정면비교).

자기교정: V236/V237 의 의미확장 엔진은 *제목(report_nm core) -> 본문 stem* 연관(V233 혈통)이었다. 그건
V234 가 검증한 씨앗 — *본문 stem <-> stem 공기 경험그래프*(stem 수평선 좌표에 같이 나온 stem = 경험) — 이
아니다. V239 는 씨앗에 정렬: 질의 core stem 들을 *각자의 stem-경험그래프*로 확장해 문서를 조회한다.

    엔진 비교(같은 harness, 같은 gold/누수가드):
      mStem  = 씨앗: 질의 stem -> 본문 stem<->stem 경험그래프(SPPMI 1-hop) -> 의미 프로필 -> 문서매칭
      mTitle = 기존: 질의 core특징 -> 제목->본문 그래프(V236) -> 문서매칭
      bm25 / rrf(bm25+mStem) / gated(bm25+mStem)
    질문: 씨앗(mStem)이 검색에서 실가치를 내는가? mTitle 대비/대등한가? rescue·synonym-gap 으로 직접 측정.

    경험그래프·gold·corp-split·rescue·synonym-gap 정의는 V234/V236 계승. 임베딩/GPU 0.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV239Test.py
    DARTLAB_HORIZON_V239_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV239Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음. 파일별 load+del.
    2. 두 그래프 모두 train(비-test corp)에서만 — 누수 없음. mStem 은 본문 stem<->stem(제목 미사용).
    3. 평가 = MRR/Top5 + rescue + synonym-gap. 결정적.
    4. mStem vs mTitle 정면 비교로 "씨앗이 검색 엔진으로 유효한가" 판정.

결과:
    py_compile 통과. 결정적.

    40-file: docs=12734 train=8627 test=2858 inDistQ=2428 buildSec=5.8
    stemExp 노드=3300, 질의 core 의 stem-경험 커버리지 평균=0.917 (커버리지 충분 — 그래프 부재가 원인 아님)
      arm              Top1    Top5    MRR
      bm25             0.7961  0.9114  0.8314
      mStem(씨앗)       0.7414  0.7759  0.7581
      mTitle(제목→본문)  0.5511  0.6845  0.6207
      rrf(bm+stem)     0.7710  0.8806  0.8131
      gated(bm+stem)   0.8550  0.8979  0.8724
    rescue (bm25 top5 실패 215): mStem 0.014 / mTitle 0.879 / rrf 0.009 / gated 0.005
    synonym-gap  low(사각,n=338)  high(완전포함,n=2090)
      bm25    0.4643   0.8908
      mStem   0.1938   0.8494   <- 사각에서 bm25(0.464)보다도 못함
      mTitle  0.6414   0.6173   <- 사각에서 압도
      gated   0.4640   0.9385

결론:
    씨앗 정렬 검증 — 정직한 반전. (V236/237 "씨앗" 호칭 오류 교정.)
    - 자기교정 확인: V236/237 의미확장 엔진은 씨앗(stem<->stem 경험)이 아니라 *제목(report_nm type)->본문* 그래프였다.
    - 진짜 씨앗(mStem)을 만들어 정면비교 -> **문서 의미 조회에선 씨앗이 더 약하다.** 특히 가치영역(키워드 사각/
      synonym gap)에서 mStem 0.194 << mTitle 0.641, 심지어 bm25 0.464 미만. rescue 도 mStem 0.014 vs mTitle 0.879
      — 씨앗은 키워드 실패를 거의 못 건진다.
    - 이유(커버리지 0.917 충분, 그래프 종류 문제): 순수 stem-경험 확장은 질의어의 *일반 공기 이웃*(generic)으로
      퍼져 정밀도 낮음 -> 특정 gold 문서 못 집음. 반면 제목->본문은 report_nm type 으로 *distant-supervised* —
      type->본문 manifestation 을 학습해 다른 단어를 쓴 문서도 type 으로 연결(synonym gap 다리).
    - mStem 전체 MRR 0.758 > mTitle 0.621 은 high 슬라이스(완전포함 0.849)에서 stem 확장이 작동하기 때문 —
      즉 씨앗은 *쉬운 질의*엔 되지만 *의미 조회의 가치영역(사각)*에선 type-supervised 다리에 진다.

    종합(정직): 씨앗(stem 수평선 경험그래프)의 강점은 V234 의 *stem<->stem graded 유사도*(동의어 판정)이지
    *문서 의미 조회*가 아니다. 문서 조회는 *type(report_nm)->본문 experience*(distant-supervised)가 정답.
    둘은 같은 experience-graph 가족의 다른 granularity — stem-경험=단어유사, type-경험=문서검색. V236/237 의
    엔진(제목->본문)은 *문서 조회 목표엔 올바른 선택*이었다(이름만 "씨앗"이라 부른 게 오류).
    함의: mStem 을 RRF 보조로 섞는 것도 사각에서 해로움(rrf(bm+stem) 사각 0.282 < gated 0.464) -> 안 섞는 게 낫다.

    다음: (1) 문서 의미 조회 = V237 recipe(type->본문 gated) 확정 유지. (2) 씨앗 stem-경험은 동의어 사전/쿼리
    재작성 용도로 분리 검토(별도 가치 — V234 stem 유사). (3) _attempts -> 검색기 모듈 이관.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V239_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V239_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V239_MAX_QUERIES", "2500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V239_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V239_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V239_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V239_EXPAND_TOPN", "60"))
ASSOC_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V239_ASSOC_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V239_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V239_SPPMI_SHIFT", "0.7"))
STEM_VOCAB = int(os.environ.get("DARTLAB_HORIZON_V239_STEM_VOCAB", "4000"))
STEM_CO_TOPM = int(os.environ.get("DARTLAB_HORIZON_V239_STEM_CO_TOPM", "40"))
STEM_MIN_CO = int(os.environ.get("DARTLAB_HORIZON_V239_STEM_MIN_CO", "3"))
STEM_TOPK = int(os.environ.get("DARTLAB_HORIZON_V239_STEM_TOPK", "40"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V239_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V239_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V239_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V239_TOPK", "10"))
GMIN = float(os.environ.get("DARTLAB_HORIZON_V239_GMIN", "0.20"))
GMAX = float(os.environ.get("DARTLAB_HORIZON_V239_GMAX", "0.85"))
GATE_X = float(os.environ.get("DARTLAB_HORIZON_V239_GATE_X", "1.5"))
GAP_THRESH = float(os.environ.get("DARTLAB_HORIZON_V239_GAP_THRESH", "0.999"))

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


def buildTitleGraph(trainDocs):
    """기존(V236): 제목 core특징 -> 본문 stem (SPPMI)."""
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


def buildStemExp(trainDocs):
    """씨앗(V234): 본문 stem <-> stem 문서공기 경험그래프 (SPPMI). 제목 미사용."""
    df1: Counter = Counter()
    for d in trainDocs:
        for s in d.raw:
            df1[s] += 1
    vocab = {s for s, _ in df1.most_common(STEM_VOCAB)}
    co: dict[str, Counter] = defaultdict(Counter)
    sdf: Counter = Counter()
    nDocs = 0
    for d in trainDocs:
        nDocs += 1
        top = [s for s, _ in d.raw.most_common(STEM_CO_TOPM) if s in vocab]
        for s in top:
            sdf[s] += 1
        for i in range(len(top)):
            ca = co[top[i]]
            for j in range(len(top)):
                if i != j:
                    ca[top[j]] += 1
    logN = math.log(max(1, nDocs))
    exp: dict[str, dict[str, float]] = {}
    for a, counts in co.items():
        dfa = sdf.get(a, 0)
        if dfa <= 0:
            continue
        w = {}
        for b, c in counts.items():
            if c < STEM_MIN_CO:
                continue
            dfb = sdf.get(b, 0)
            if dfb <= 0:
                continue
            pmi = (math.log(c) + logN) - (math.log(dfa) + math.log(dfb)) - SPPMI_SHIFT
            if pmi > 0:
                w[b] = pmi
        if w:
            exp[a] = dict(sorted(w.items(), key=lambda kv: kv[1], reverse=True)[:STEM_TOPK])
    return exp


def expandTitle(core, t2b):
    prof: dict[str, float] = defaultdict(float)
    for f, sw in coreFeatureWeights(core).items():
        for b, ew in t2b.get(f, {}).items():
            prof[b] += sw * ew
    return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])


def expandStem(core, exp):
    """씨앗: 질의 stem 각자의 경험그래프 이웃을 합산."""
    prof: dict[str, float] = defaultdict(float)
    for t in core:
        for b, ew in exp.get(t, {}).items():
            prof[b] += ew
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
    return {
        pos: 1.0 / (k + r) for r, (pos, _) in enumerate(sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])), start=1)
    }


def gateW(top1, ref):
    if ref <= 0:
        return (GMIN + GMAX) / 2
    x = min(top1 / ref, GATE_X)
    return max(GMIN, min(GMAX, GMAX - (GMAX - GMIN) * (x / GATE_X)))


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
    titleG = buildTitleGraph(train)
    stemExp = buildStemExp(train)
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

    top1s = []
    for pos, core, ck in queries:
        bs = scoreBm25(core, bm, test)
        top1s.append(max(bs.values()) if bs else 0.0)
    ref = sorted(top1s)[len(top1s) // 2] if top1s else 0.0

    names = ["bm25", "mStem", "mTitle", "rrf(bm+stem)", "gated(bm+stem)"]
    agg = {nm: [0, 0, 0.0] for nm in names}
    perQuery = []
    stemCover = 0  # 질의 core 중 stem-경험 그래프에 존재한 비율 평균
    for qi, (pos, core, ck) in enumerate(queries):
        gold = set(classMembers[ck]) - {pos}
        bs = scoreBm25(core, bm, test)
        pStem = expandStem(core, stemExp)
        pTitle = expandTitle(core, titleG)
        msStem = scoreProf(pStem, inv)
        msTitle = scoreProf(pTitle, inv)
        recBm, recStem = recipRanks(bs), recipRanks(msStem)
        rrfS = {p: recBm.get(p, 0.0) + recStem.get(p, 0.0) for p in set(recBm) | set(recStem)}
        g = gateW(top1s[qi], ref)
        gatedS = {p: (1 - g) * recBm.get(p, 0.0) + g * recStem.get(p, 0.0) for p in set(recBm) | set(recStem)}
        scores = {"bm25": bs, "mStem": msStem, "mTitle": msTitle, "rrf(bm+stem)": rrfS, "gated(bm+stem)": gatedS}
        ranks = {nm: firstGoldRank(scores[nm], gold, pos) for nm in names}
        for nm in names:
            r = ranks[nm]
            if r:
                if r == 1:
                    agg[nm][0] += 1
                if r <= 5:
                    agg[nm][1] += 1
                agg[nm][2] += 1.0 / r
        stemCover += sum(1 for t in core if t in stemExp) / max(1, len(core))
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
        for nm in ("mStem", "mTitle", "rrf(bm+stem)", "gated(bm+stem)")
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

    print("=" * 84)
    print(f"V239 씨앗 정렬: stem-수평선 경험그래프(mStem) vs 제목→본문(mTitle)  (total {time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq} buildSec={buildSec:.1f}"
    )
    print(f"stemExp 노드={len(stemExp)}  질의 core 의 stem-경험 커버리지 평균={stemCover / nq:.3f}")
    print("-" * 84)
    print(f"{'arm':<16} Top1    Top5    MRR")
    for nm in names:
        h, h5, mrr = agg[nm]
        print(f"{nm:<16} {h / nq:.4f}  {h5 / nq:.4f}  {mrr / nq:.4f}")
    print("-" * 84)
    if rescueDenom:
        print(
            f"rescue (bm25 top5 실패 {rescueDenom}): "
            + "  ".join(f"{nm.replace('(bm+stem)', '')} {rescue[nm] / rescueDenom:.3f}" for nm in rescue)
        )
    print("-" * 84)
    print(f"[synonym-gap] low(키워드 사각, n={lowN})  high(완전포함, n={highN})")
    print(f"{'arm':<16} low-MRR   high-MRR")
    for nm in names:
        lo = lowMrr[nm] / lowN if lowN else 0.0
        hi = highMrr[nm] / highN if highN else 0.0
        print(f"{nm:<16} {lo:.4f}    {hi:.4f}")
    print("-" * 84)
    mStem = agg["mStem"][2] / nq
    mTitle = agg["mTitle"][2] / nq
    loStem = lowMrr["mStem"] / lowN if lowN else 0.0
    loTitle = lowMrr["mTitle"] / lowN if lowN else 0.0
    print(
        f"VERDICT: 씨앗 mStem MRR {mStem:.4f} vs 제목 mTitle {mTitle:.4f} / 사각 mStem {loStem:.4f} vs mTitle {loTitle:.4f} "
        f"-> {'씨앗이 검색엔진으로 유효(대등+)' if mStem >= mTitle - 0.03 or loStem >= loTitle else '씨앗 단독 약함'}"
    )
    print("=" * 84)


if __name__ == "__main__":
    main()
