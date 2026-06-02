"""Horizon Meaning Learner V240 - 3층 조합 의미 검색기: 키워드 + type→본문 경험 + stem-경험(단어 QE).

목표: allFilings 의미 조회 *빠른 검색기*(RAG 아님, 임베딩無). 세 층을 잘 조합:
    (1) bm25 키워드, (2) type(report_nm)→본문 경험(V237, 문서/유형 수준 의미),
    (3) stem-경험그래프(V234 씨앗, 단어 수준 의미=동의/연관어) — *질의 확장*으로.

    V239 교훈: stem-경험을 flat scoreProf 별도팔로 RRF 하면 generic 이웃 범람으로 망함(사각 0.194).
    교정: 같은 stem-경험을 **IDF 살아있는 weighted-bm25 질의확장**으로 — generic 이웃은 df 높아 IDF 낮으니
    자동 억제, 특정 동의어만 부각. 이게 단어 수준 의미를 정밀하게 조합하는 길.

    arm: bm25 / bm25+QE(stem 질의확장) / typeBody / v237=gated(bm25,typeBody) / full=gated(bm25+QE,typeBody).
    질문: 단어 수준(QE)이 V237(유형 수준)에 *추가* 이득(특히 사각)을 주는가. + 쿼리 latency(빠른 검색기 확인).

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV240Test.py
    DARTLAB_HORIZON_V240_FILE_LIMIT=40 uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV240Test.py

검증 기준:
    1. allFilings 만. R1~R5. dartlab import 없음. 파일별 load+del.
    2. 두 그래프 train(비-test)만. gate ref=bm25core top1(gold 미사용). corp-split 누수가드.
    3. QE 는 weighted-bm25(IDF 보존)로 — flat scoreProf 아님. 결정적.
    4. full(3층) vs v237(2층) 전체·사각 비교 + latency.

결과:
    py_compile 통과. 결정적. (full gate 는 QE 자신 top1/ref 로 — 초판 core-ref mismatch 버그 교정 후.)

    40-file: docs=12734 train=8627 test=2858 inDistQ=2428 buildSec=10.0, 5-arm latency 4.57 ms/q, 임베딩/GPU 0
      arm           Top1    Top5    MRR    | 사각    완전포함
      bm25          0.7961  0.9114  0.8314 | 0.4643  0.8908
      bm25+QE       0.8303  0.9090  0.8648 | 0.4528  0.9314
      typeBody      0.5379  0.6845  0.6141 | 0.6414  0.6097
      v237(2층)      0.9366  0.9806  0.9545 | 0.7981  0.9798
      full(3층)      0.7797  0.9329  0.8559 | 0.5391  0.9072
    rescue(bm25 top5 실패 215): bm25+QE 0.177 / v237 0.800 / full 0.809.  harm: v237 0.002 / full 0.049

결론:
    단어층(stem-QE)을 IDF 보존 weighted-bm25 질의확장으로 *정공* 결합 — 정직한 결과.
    - 단어층 QE 는 bm25 를 실제 개선(MRR 0.831->0.865 +0.033, 완전포함 0.891->0.931). V239 broken scoreProf 와
      달리 IDF 가 generic 이웃을 자동 억제 = 씨앗 단어의미가 *질의확장으로는* 실가치. (V239 의 "씨앗 약함"은
      flat scoreProf 탓이었음을 한 번 더 교정.)
    - 그러나 3층 full(0.856) < 2층 v237(0.955), 전 슬라이스 열위. 이유: (a) type->본문이 retrieval 가치를 이미
      흡수(사각 typeBody 0.641 >> QE 0.453), (b) QE 를 키워드팔에 넣으면 gate 의 신뢰도신호(bm25core top1)를
      오염 — 확장어가 점수 부풀려 gate 가 키워드 강함으로 착각, typeBody 비중 잘못↓(harm 0.002->0.049).
    - 즉 *report_nm-type 질의* regime 에선 2층(v237)이 최적, 단어층 추가이득 없음 (V239 와 정합).

    ⚠ 평가 regime 함정(중요): 본 평가는 질의=report_nm core(공시유형)라 type->본문이 구조적으로 유리,
    단어층이 묻힌다. "단어로까지 하는 의미 검색기"의 본 쓰임은 *자유어 질의*(임의 단어/구, 예 "유상증자")이고
    거기선 typeBody 가 안 걸리고 stem-경험(단어의미)이 본령. 단어층 가치는 *그 regime*에서 측정해야 공정.

    종합: 현재 확정 — type-질의 문서조회 = v237(2층) recipe. 단어층은 bm25 단독 개선엔 유효하나 v237 위엔
    무익(이 regime). 단어층+문서층 조합의 정당한 무대 = 자유어 질의(V241).

    다음(V241): 자유어 질의 평가 — 질의=본문 임의 핵심어(report_nm 아님), gold=관련 문서. typeBody 약한
    regime 에서 stem-QE 가 bm25 위에 의미 이득 내는가. 거기가 단어층의 진짜 자리.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V240_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V240_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V240_MAX_QUERIES", "2500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V240_TEST_MOD", "4"))
OOD_MOD = int(os.environ.get("DARTLAB_HORIZON_V240_OOD_MOD", "5"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V240_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V240_EXPAND_TOPN", "60"))
ASSOC_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V240_ASSOC_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V240_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V240_SPPMI_SHIFT", "0.7"))
STEM_VOCAB = int(os.environ.get("DARTLAB_HORIZON_V240_STEM_VOCAB", "4000"))
STEM_CO_TOPM = int(os.environ.get("DARTLAB_HORIZON_V240_STEM_CO_TOPM", "40"))
STEM_MIN_CO = int(os.environ.get("DARTLAB_HORIZON_V240_STEM_MIN_CO", "3"))
STEM_TOPK = int(os.environ.get("DARTLAB_HORIZON_V240_STEM_TOPK", "40"))
STEM_QE_TOPN = int(os.environ.get("DARTLAB_HORIZON_V240_STEM_QE_TOPN", "20"))
STEM_QE_ALPHA = float(os.environ.get("DARTLAB_HORIZON_V240_STEM_QE_ALPHA", "0.35"))
BM25_K1 = float(os.environ.get("DARTLAB_HORIZON_V240_BM25_K1", "1.5"))
BM25_B = float(os.environ.get("DARTLAB_HORIZON_V240_BM25_B", "0.75"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V240_RRF_K", "60"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V240_TOPK", "10"))
GMIN = float(os.environ.get("DARTLAB_HORIZON_V240_GMIN", "0.20"))
GMAX = float(os.environ.get("DARTLAB_HORIZON_V240_GMAX", "0.85"))
GATE_X = float(os.environ.get("DARTLAB_HORIZON_V240_GATE_X", "1.5"))
GAP_THRESH = float(os.environ.get("DARTLAB_HORIZON_V240_GAP_THRESH", "0.999"))

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


def stemQueryWeights(core, exp):
    """씨앗 stem-경험으로 질의 확장: core 1.0 + 이웃 동의/연관어 α·정규화. weighted-bm25 가 IDF 로 generic 억제."""
    qw: dict[str, float] = {t: 1.0 for t in core}
    raw: dict[str, float] = defaultdict(float)
    for t in core:
        for b, ew in exp.get(t, {}).items():
            if b not in core:
                raw[b] += ew
    if raw:
        items = sorted(raw.items(), key=lambda kv: (-kv[1], kv[0]))[:STEM_QE_TOPN]
        mx = items[0][1]
        for term, w in items:
            qw[term] = max(qw.get(term, 0.0), STEM_QE_ALPHA * (w / mx))
    return qw


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


def scoreBm25W(qw, bm, test):
    """가중 bm25: 질의어별 가중치 qw[t] 곱. qw={t:1.0} 면 표준 bm25."""
    s: dict[int, float] = defaultdict(float)
    for t, qwt in qw.items():
        df = bm.df.get(t, 0)
        if df <= 0:
            continue
        idf = math.log((bm.n - df + 0.5) / (df + 0.5) + 1.0)
        for pos in bm.inv.get(t, ()):
            tf = test[pos].raw.get(t, 0)
            denom = tf + BM25_K1 * (1 - BM25_B + BM25_B * bm.docLen[pos] / bm.avgdl)
            if denom > 0:
                s[pos] += qwt * idf * (tf * (BM25_K1 + 1)) / denom
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


def gatedFuse(recA, recB, top1, ref):
    g = gateW(top1, ref)
    return {p: (1 - g) * recA.get(p, 0.0) + g * recB.get(p, 0.0) for p in set(recA) | set(recB)}


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
    top1qe = []
    for pos, core, ck in queries:
        bs = scoreBm25W({t: 1.0 for t in core}, bm, test)
        qs = scoreBm25W(stemQueryWeights(core, stemExp), bm, test)
        top1s.append(max(bs.values()) if bs else 0.0)
        top1qe.append(max(qs.values()) if qs else 0.0)
    ref = sorted(top1s)[len(top1s) // 2] if top1s else 0.0
    refQe = sorted(top1qe)[len(top1qe) // 2] if top1qe else 0.0

    names = ["bm25", "bm25+QE", "typeBody", "v237(2층)", "full(3층)"]
    agg = {nm: [0, 0, 0.0] for nm in names}
    perQuery = []
    tq = time.time()
    for qi, (pos, core, ck) in enumerate(queries):
        gold = set(classMembers[ck]) - {pos}
        bs = scoreBm25W({t: 1.0 for t in core}, bm, test)
        qe = scoreBm25W(stemQueryWeights(core, stemExp), bm, test)
        tbody = scoreProf(expandTitle(core, titleG), inv)
        recBm, recQe, recTb = recipRanks(bs), recipRanks(qe), recipRanks(tbody)
        v237 = gatedFuse(recBm, recTb, top1s[qi], ref)
        full = gatedFuse(recQe, recTb, top1qe[qi], refQe)  # full 은 QE 자신의 신뢰도로 gate
        scores = {"bm25": bs, "bm25+QE": qe, "typeBody": tbody, "v237(2층)": v237, "full(3층)": full}
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
    qSec = time.time() - tq
    nq = len(queries)
    fullLatency = qSec / nq * 1000 if nq else 0.0  # 5-arm 합산이라 full 단독은 이보다 빠름

    def top5(ranks, nm):
        return 0 < ranks[nm] <= 5

    rescueDenom = sum(1 for ranks, _ in perQuery if not top5(ranks, "bm25"))
    rescue = {
        nm: sum(1 for ranks, _ in perQuery if not top5(ranks, "bm25") and top5(ranks, nm))
        for nm in ("bm25+QE", "v237(2층)", "full(3층)")
    }
    harmDenom = sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1)
    harm = {
        nm: sum(1 for ranks, _ in perQuery if ranks["bm25"] == 1 and not top5(ranks, nm))
        for nm in ("v237(2층)", "full(3층)")
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
    print(f"V240 3층 조합 의미 검색기: 키워드+type경험+stem-QE  (total {time.time() - t0:.1f}s)")
    print(
        f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)} inDistQ={nq} buildSec={buildSec:.1f}"
    )
    print(f"5-arm 쿼리 latency={fullLatency:.2f} ms/q (full 단독은 더 빠름) · 임베딩/GPU 0")
    print("-" * 84)
    print(f"{'arm':<14} Top1    Top5    MRR     | 사각    완전포함")
    for nm in names:
        h, h5, mrr = agg[nm]
        lo = lowMrr[nm] / lowN if lowN else 0.0
        hi = highMrr[nm] / highN if highN else 0.0
        print(f"{nm:<14} {h / nq:.4f}  {h5 / nq:.4f}  {mrr / nq:.4f}  | {lo:.4f}  {hi:.4f}")
    print("-" * 84)
    if rescueDenom:
        print(
            f"rescue (bm25 top5 실패 {rescueDenom}): "
            + "  ".join(f"{nm} {rescue[nm] / rescueDenom:.3f}" for nm in rescue)
        )
    if harmDenom:
        print(f"harm   (bm25 top1 {harmDenom}): " + "  ".join(f"{nm} {harm[nm] / harmDenom:.3f}" for nm in harm))
    print("-" * 84)
    mV237 = agg["v237(2층)"][2] / nq
    mFull = agg["full(3층)"][2] / nq
    loV237 = lowMrr["v237(2층)"] / lowN if lowN else 0.0
    loFull = lowMrr["full(3층)"] / lowN if lowN else 0.0
    mBm = agg["bm25"][2] / nq
    mQe = agg["bm25+QE"][2] / nq
    loBm = lowMrr["bm25"] / lowN if lowN else 0.0
    loQe = lowMrr["bm25+QE"] / lowN if lowN else 0.0
    print(f"단어층(QE) 단독효과: bm25+QE MRR {mQe:.4f}(vs bm25 {mBm:.4f}) / 사각 {loQe:.4f}(vs {loBm:.4f})")
    print(
        f"VERDICT: full(3층) MRR {mFull:.4f}(vs v237 {mV237:.4f}) / 사각 {loFull:.4f}(vs v237 {loV237:.4f}) "
        f"-> {'단어층 추가 이득' if mFull > mV237 + 0.002 or loFull > loV237 + 0.005 else '추가 이득 미미(2층이 충분)'}"
    )
    print("=" * 84)


if __name__ == "__main__":
    main()
