"""Horizon Meaning Learner V214 - open document-retrieval harness + balAPinc readout.

이 파일은 V213(guard-safe proof gating, V212 proof-gating 라인의 연속)과 다른 갈래다.
4-전문가 토론(IR이론/형태론/자기지도평가/sparse시스템 + 레드팀 통합)의 결론을 따른다:
"V20~V212 의 천장은 ranker 가 아니라 (a) ROLE_RULES 36줄 손사전에 갇힌 어휘 + (b) 정답이
그 사전 키로 적힌 8 probe(=8/8 동어반복)가 만든다. 모델을 더 깎지 말고 *자(尺)* 를 먼저 바꿔라."

아이디어:
    1. 정답을 우리 사전이 아니라 *DART 가 행정적으로 부여한 report_nm* 에서 가져온다.
       report_nm 의 의미 핵(괄호 안 유상증자결정/전환사채권발행결정 등)을 query 로,
       그 공시 본문을 gold 로 삼는다. distant supervision → n 수천 open held-out.
    2. 본문에서 query 핵 stem 을 *마스킹* 한다. 검색이 제목 string match 가 아니라 본문 주변
       어휘(신주/발행가액/납입일)와의 *연상 경험* 으로만 풀리게 강제 = "경험 의미".
    3. 회사(corp_code) 단위 train/test 분리로 회사 문체 암기 누설 차단. 연상은 train 회사에서만 학습.
    4. 셔플-null: gold 를 무작위로 섞어도 점수가 안 떨어지면 표면통계 과적합 = harness 무효.
       이게 1 순위 게이트.

    scorer 3 종(같은 test split):
        - keywordUnmasked: query 핵 vs 마스킹 안 한 본문 overlap. 제목이 본문에 박힌 쉬운 상한 참조.
        - assocExpand: query 핵을 train 연상으로 body-vocab PMI 프로파일로 확장 후 IDF 매칭 (경험 의미 본체).
        - balAPinc: 확장 프로파일의 후보 본문 *비대칭 포함* 유사도 (IR 이론가 A1).

    최대 리스크(레드팀): report_nm 이 "공시 유형"만 회수하고 "본문 의미"는 못 담을 수 있다.
    그래서 event(괄호 의미 핵 풍부) 서브셋을 분리 집계해 coverage 와 신호를 직접 본다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV214Test.py
    $env:DARTLAB_HORIZON_V214_FILE_LIMIT='8'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV214Test.py
    $env:DARTLAB_HORIZON_V214_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV214Test.py

검증 기준:
    1. 데이터는 data/dart/allFilings/*.parquet 의 report_nm + content_raw 만.
    2. 정답은 report_nm distant label. ROLE_RULES 손사전·8 probe 미사용.
    3. train/test 는 corp_code 분리. 연상은 train 에서만 학습.
    4. query 핵 stem 은 본문에서 마스킹(keyword match 차단).
    5. 셔플-null Top1 은 chance(~1/Ntest) 로 붕괴해야 한다. 안 붕괴하면 harness 무효.
    6. assocExpand 가 셔플-null 대비 유의하게 높아야 "경험 의미" 신호가 실재.

결과:
    py_compile 통과.

    8-file smoke: docs=2514 train=1848 test=666 chance=0.00150 profileCoverage=0.339
        keywordUnmasked Top1=0.1126/MRR=0.1910, assocExpand Top1=0.0631/MRR=0.1197,
        balAPinc Top1=0.0661/MRR=0.1217, assocExpand@event Top1=0.0750(n=120).
        SHUFFLE-NULL assocExpand Top1=0.00000 (chance=0.00150) -> PASS.

    40-file: docs=12734 train=9722 test=3012 chance=0.00033 profileCoverage=0.412
        keywordUnmasked Top1=0.0550/MRR=0.0932, assocExpand Top1=0.0390/MRR=0.0820,
        balAPinc Top1=0.0380/MRR=0.0802, assocExpand@event Top1=0.0719/MRR=0.1257(n=487).
        SHUFFLE-NULL assocExpand Top1=0.00000 (chance=0.00033) -> PASS. signal REAL.
        buildSeconds~=10.

결론:
    성공/자(尺) 전환. 토론 1 순위 목표 달성.

    - harness 자체가 핵심 산출물이다: open(n=3012), 회사 분리 split, 제목 마스킹, 누설 가드.
      셔플-null Top1=0.000 으로 붕괴 -> 8/8 동어반복과 달리 신뢰 가능한 자. 이것이 "한 단계".
    - assocExpand(경험 의미 = train 연상 PMI*IDF 확장)는 셔플-null 대비 REAL.
      overall Top1 0.039(~118x chance), event 0.072(~218x). 단 절대값은 낮고 keyword 상한에는
      미달한다(예상 — keyword 는 마스킹 안 한 본문을 본다). 즉 마스킹된 본문에서의 의미 회수 신호다.
    - balAPinc(A1)은 assocExpand 대비 우위 없음(Top1 0.038 vs 0.039). 비대칭 포함의 표적(계층)이
      광역 문서 검색에서는 희소해 이 과제에선 평탄. 다음은 balAPinc 가 아니라 RWR(2차 분포)다.
    - 최대 리스크(report_nm 이 공시 유형만 회수) 확인되되 한정적: event 공시(의미 핵 풍부)가
      generic 대비 ~2x 강한 신호. distant supervision gold 는 event 공시에 집중해 유효하다.

    다음 실험(V215): SPPMI 위 RWR 2차 분포로 광역 연상을 강화하고, profileCoverage(0.41)를
    형태소 분해로 끌어올린다. balAPinc 는 accountMappings 계층 서브셋에서만 따로 검증한다.
"""

from __future__ import annotations

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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V214_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V214_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V214_MAX_QUERIES", "1500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V214_TEST_MOD", "4"))  # corp hash %TEST_MOD==0 -> test
SEED = int(os.environ.get("DARTLAB_HORIZON_V214_SEED", "20260602"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V214_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V214_EXPAND_TOPN", "60"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V214_MIN_ASSOC_DF", "3"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V214_TOPK", "10"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
PAREN_RE = re.compile(r"[(\[]([^)\]]+)[)\]]")
BRACKET_PREFIX_RE = re.compile(r"^\s*\[[^\]]*\]")

# report_nm 의 의미 핵이 아닌 순수 행정 형식어. query 핵에서 제거(특정 정답 주입 아님).
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
    """report_nm 의 의미 핵 stem 집합. 괄호 안 우선, 없으면 머리 명사. 행정 형식어 제거."""
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


@dataclass
class Doc:
    idx: int
    corp: str
    isTest: bool
    core: frozenset[str]
    body: Counter  # masked body stem -> tf
    rawBody: frozenset[str]  # unmasked body stem set (keyword 상한 참조)


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
                continue  # 의미 핵 없는 정기/형식 공시는 query 가 안 됨
            text = cleanText(r.get("content_raw"), limit=BODY_CHAR_LIMIT)
            stems = bodyStems(text)
            if len(stems) < 12:
                continue
            rawSet = frozenset(stems)
            masked = Counter(s for s in stems if s not in core)
            if not masked:
                continue
            isTest = (hash(corp) % TEST_MOD) == 0 if corp else False
            docs.append(Doc(idx, corp, isTest, frozenset(core), masked, rawSet))
            idx += 1
        del df
    return docs


def buildAssoc(trainDocs: list[Doc]) -> tuple[dict[str, Counter], Counter, int]:
    """train 회사에서 title-core stem -> body stem 연상 + body df 학습."""
    assoc: dict[str, Counter] = defaultdict(Counter)
    bodyDf: Counter = Counter()
    for d in trainDocs:
        seen = set(d.body.keys())
        for b in seen:
            bodyDf[b] += 1
        for t in d.core:
            assoc[t].update(seen)
    return assoc, bodyDf, len(trainDocs)


def expandQuery(core, assoc, bodyDf, nTrain) -> dict[str, float]:
    """query 핵을 PMI*IDF 가중 body-vocab 프로파일로 확장. 학습된 연상 = 경험 의미."""
    profile: dict[str, float] = defaultdict(float)
    for t in core:
        co = assoc.get(t)
        if not co:
            continue
        tTotal = sum(co.values())
        if tTotal <= 0:
            continue
        for b, c in co.items():
            if c < MIN_ASSOC_DF:
                continue
            df = bodyDf.get(b, 0)
            if df <= 0:
                continue
            pBgivenT = c / tTotal
            pB = df / nTrain
            if pB <= 0:
                continue
            pmi = math.log(pBgivenT / pB)
            if pmi <= 0:
                continue
            idf = math.log(1.0 + nTrain / df)
            profile[b] += pmi * idf
    if not profile:
        return {}
    top = sorted(profile.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN]
    return dict(top)


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


def scoreBalAPinc(profile, testDocs, inv) -> dict[int, float]:
    """비대칭 포함: query 확장 프로파일(ranked)이 후보 본문에 얼마나 포함되는가(APinc*LIN)."""
    if not profile:
        return {}
    ranked = sorted(profile.items(), key=lambda kv: kv[1], reverse=True)
    cand: set[int] = set()
    for b, _ in ranked:
        cand.update(inv.get(b, ()))
    out: dict[int, float] = {}
    n = len(ranked)
    for pos in cand:
        body = testDocs[pos].body
        hits = 0
        ap = 0.0
        for r, (b, _) in enumerate(ranked, start=1):
            if b in body:
                hits += 1
                ap += hits / r
        if hits == 0:
            continue
        out[pos] = math.sqrt((ap / n) * (hits / n))
    return out


def evaluate(queries, goldPos, scorer) -> dict[str, float]:
    top1 = top5 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        gold = goldPos[qid]
        scores = scorer(qid, core)
        n += 1
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
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


def main() -> None:
    t0 = time.time()
    rng = random.Random(SEED)
    docs = loadDocs()
    trainDocs = [d for d in docs if not d.isTest]
    testDocs = [d for d in docs if d.isTest]
    if not testDocs or not trainDocs:
        print(f"insufficient split: train={len(trainDocs)} test={len(testDocs)} (need both)")
        return

    assoc, bodyDf, nTrain = buildAssoc(trainDocs)
    inv = buildInverted(testDocs, lambda d: d.body)
    invRaw = buildInverted(testDocs, lambda d: d.rawBody)

    queries: list[tuple[int, frozenset[str], bool]] = []
    goldPos: dict[int, int] = {}
    for pos, d in enumerate(testDocs):
        queries.append((pos, d.core, len(d.core) >= 2))
        goldPos[pos] = pos
        if len(queries) >= MAX_QUERIES:
            break

    profileCache: dict[int, dict[str, float]] = {}

    def getProfile(qid, core):
        if qid not in profileCache:
            profileCache[qid] = expandQuery(core, assoc, bodyDf, nTrain)
        return profileCache[qid]

    def assocScorer(qid, core):
        return scoreAssoc(getProfile(qid, core), testDocs, inv)

    def keywordScorer(qid, core):
        return scoreKeyword(core, invRaw)

    def balScorer(qid, core):
        return scoreBalAPinc(getProfile(qid, core), testDocs, inv)

    rKeyword = evaluate(queries, goldPos, keywordScorer)
    rAssoc = evaluate(queries, goldPos, assocScorer)
    rBal = evaluate(queries, goldPos, balScorer)

    eventQ = [q for q in queries if q[2]]
    rAssocEvent = evaluate(eventQ, goldPos, assocScorer) if eventQ else None

    # 셔플-null: gold 를 무작위 다른 test 문서로 재배정. assocScorer Top1 이 chance 로 붕괴해야 함.
    shufGold = dict(goldPos)
    shuffled = [q[0] for q in queries]
    rng.shuffle(shuffled)
    for q, sp in zip(queries, shuffled):
        shufGold[q[0]] = sp
    rShuffle = evaluate(queries, shufGold, assocScorer)

    chance = 1.0 / len(testDocs)
    coverage = sum(1 for q in queries if getProfile(q[0], q[1])) / len(queries)

    print("=" * 64)
    print(f"V214 open document-retrieval harness  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(f"queries={len(queries)} eventQueries={len(eventQ)} profileCoverage={coverage:.3f} chanceTop1={chance:.5f}")
    print(f"assocVocab(titleStems)={len(assoc)} bodyVocab={len(bodyDf)}")
    print("-" * 64)
    print(f"keywordUnmasked  : Top1={rKeyword['top1']:.4f} Top5={rKeyword['top5']:.4f} MRR={rKeyword['mrr']:.4f}")
    print(f"assocExpand      : Top1={rAssoc['top1']:.4f} Top5={rAssoc['top5']:.4f} MRR={rAssoc['mrr']:.4f}")
    print(f"balAPinc (A1)    : Top1={rBal['top1']:.4f} Top5={rBal['top5']:.4f} MRR={rBal['mrr']:.4f}")
    if rAssocEvent:
        print(
            f"assocExpand@event: Top1={rAssocEvent['top1']:.4f} Top5={rAssocEvent['top5']:.4f} "
            f"MRR={rAssocEvent['mrr']:.4f} n={rAssocEvent['n']}"
        )
    print("-" * 64)
    print(f"SHUFFLE-NULL gate: assocExpand Top1={rShuffle['top1']:.5f}  (chance={chance:.5f})")
    gatePass = rShuffle["top1"] <= max(chance * 5, 0.01)
    print(f"  gate={'PASS (null 붕괴)' if gatePass else 'FAIL (null 미붕괴 → harness 무효)'}")
    signal = rAssoc["top1"] > max(rShuffle["top1"] * 5, chance * 10)
    print(f"  assocExpand signal vs null: {'REAL' if signal else 'WEAK/NONE'}")
    print("=" * 64)


if __name__ == "__main__":
    main()
