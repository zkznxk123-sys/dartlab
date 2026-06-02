"""Horizon Meaning Learner V221 - meaning-class retrieval gold + antonym-null (자 correction).

이 파일은 깨끗한 open-harness 라인(V214 harness -> V215 morphSppmi/RWR)을 잇는다.
V216~V219 의 purpose-gating/routing 은 morphSppmi 대비 4 버전 연속 평탄(saturated)했고, V220 은
옛 panel/accountMappings heavy-machinery 로 회귀했다(미실행). [goal] escalation 규칙
"같은 지표 3 버전 정지=saturated 경보 -> eval 을 더 어렵게(OOD·antonym)" + "2 회 연속
promotion 실패 -> 측정/표현의 뿌리를 친다" 에 따라, V221 은 기계를 더 얹지 않고 *자(尺)* 를 교정한다.

직전 실패 분해(V214 자기비판 + V215~219 측정):
    F1. gold 가 "정확히 1 건"이라 near-duplicate 동일유형을 오답 처리 -> 의미를 잘못 잰다.
    F2. null 이 무작위(shuffle)뿐 -> antonym-null 부재(약한 바닥). G2 미측정.
    F3. keyword vs keyword+experience 증분 미측정.
    F4. 40-file 에서 어떤 기계도 keyword 를 못 이김(morph 0.048 vs keyword 0.073) -> G1 미달.

가설(이번 iteration, 기계 불변 / 자만 교정):
    F1·F2 를 때린다. gold 를 *report_nm 의미류(meaning-class) 회수* 로 바꾸고(같은 report_nm core =
    같은 의미류), 코퍼스에서 char-bigram 으로 sibling 류를 채굴해 *antonym-null(sibling discrimination)*
    을 추가한다. 또 keyword+morph RRF 융합으로 experience 증분(F3)을 측정한다. 기계(keyword/assoc/
    balAPinc/morphSppmi/rwr2Hop)는 V215 그대로다. 라벨은 report_nm·char 구조에서만(R1).

    예상: type-gold 로 바꾸면 near-duplicate 오답이 사라져 절대 수치가 오르고, morphSppmi 가 keyword 를
    type 기준에서 이기는지(G1), sibling discrimination 이 chance 를 넘는지(G2)가 처음으로 보인다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV221Test.py
    $env:DARTLAB_HORIZON_V221_FILE_LIMIT='8'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV221Test.py
    $env:DARTLAB_HORIZON_V221_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV221Test.py

검증 기준:
    1. 데이터는 data/dart/allFilings/*.parquet 의 report_nm + content_raw 만.
    2. 라벨은 report_nm(행정) + char 구조. 손사전·8 probe 미사용(R1).
    3. train/test 는 corp_code 분리. SPPMI/연상은 train 에서만 학습.
    4. exact-doc gold(F1 비교용)와 meaning-class gold 를 동시 출력.
    5. antonym-null: sibling 류 discrimination 이 chance 를 유의하게 넘어야 G2 신호.
    6. RRF(keyword+morph)가 keyword 단독을 넘으면 experience 증분(F3) 존재.

결과:
    py_compile + lint-camelcase 통과.

    8-file smoke: docs=2514 train=1926 test=588 classEvalN=525 siblingEvalN=31 (siblingClasses=4, 표본 작음)
      [class gold] keyword Top1=0.8495/MRR=0.8834, morphSppmi 0.8952/0.9262, RRF 0.9010/0.9371
      [antonym-null] morph own1=0.6129 vs chance=0.5647 (margin +0.048, n=31 무의미)
      -> 8-file 에선 morph 가 keyword 를 이기는 듯 보였으나 표본이 작아 아티팩트.

    40-file: docs=12734 train=9876 test=2858 classEvalN=2766 siblingEvalN=581 (siblingClasses=36), buildSeconds~=23
      [exact-doc gold]    keyword Top1=0.0535/MRR=0.0935, morph 0.0420/0.0859, RRF 0.0546/0.1080
      [meaning-class gold] keyword Top1=0.8051/MRR=0.8454, morph 0.6099/0.6863, rwr 0.5499/0.6272,
                           keyword+morphRRF 0.8134/0.8810
      [antonym-null n=581] keyword own1=0.8606 chance=0.6351 (+0.2255), morph 0.6248 (-0.0103),
                           rwr 0.5990 (-0.0361), RRF 0.7573 (+0.1222)
      SHUFFLE-NULL morph exact Top1=0.00000 (chance=0.00035) -> PASS.

결론:
    진단 성공 / 기계 promotion 실패. 자(尺) 교정이 그림을 뒤집었다.

    - F1: exact-doc gold(Top1 0.04~0.05)는 의미를 심하게 과소측정했다. meaning-class gold 로 바꾸니
      기계들이 같은 의미류 공시를 keyword 0.805 / RRF 0.813 Top1 로 회수 — 진짜 신호는 컸다.
    - F3: keyword+morphRRF 가 keyword 단독을 class·exact 양쪽에서 넘었다(MRR 0.881 vs 0.845). 즉
      experience 는 keyword 의 *대체*가 아니라 *보완*으로 증분을 준다. 이번의 가장 견고한 소득.
    - G1: morph 단독은 40-file class 기준 keyword 에 진다(0.686 vs 0.845). 8-file 의 "morph 승"은 소표본 아티팩트.
    - G2(antonym-null, n=581): morph own1=0.625 <= chance 0.635 (margin -0.01), rwr -0.036. morph/rwr 은
      sibling/반의어를 구별 못 한다. char-morph 가 유상/무상·취득/처분류를 흐린다. keyword(정확 stem)는 +0.226.
      이론 예측 그대로 — morph 는 계열축(치환 유사)만 주고 결합축(부호·변별)을 못 준다.

    promotion 판정: PASS 아님(G2 실패 + morph 단독 G1 미달). 단 자 교정으로 "무엇이 막혔는지"가 처음 분리됐다.

    다음 가설(V222) — 위 실패 분해에서 도출:
    G2 가 결합축 부재를 정확히 가리킨다. 다음 기계는 char-morph 유사를 키우는 방향이 아니라 sibling 을
    *가르는* 결합축을 추가한다 — (a) 공유 carrier 를 뺀 변별 modifier 가중, 또는 (b) 회계 referential
    anchor(panel 셀/차대변 부호)로 유상/무상·취득/처분을 부호 분리(G4 축). 채점은 antonym-null margin 이
    chance 를 유의(p<0.01)하게 넘는지로 한다. keyword+morphRRF 보완 소득은 baseline 으로 유지한다.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V221_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V221_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V221_MAX_QUERIES", "1500"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V221_TEST_MOD", "4"))  # stable corp hash %TEST_MOD==0 -> test
SEED = int(os.environ.get("DARTLAB_HORIZON_V221_SEED", "20260602"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V221_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V221_EXPAND_TOPN", "60"))
RWR_TOPN = int(os.environ.get("DARTLAB_HORIZON_V221_RWR_TOPN", "90"))
RWR_BRANCH = int(os.environ.get("DARTLAB_HORIZON_V221_RWR_BRANCH", "24"))
MIN_ASSOC_DF = int(os.environ.get("DARTLAB_HORIZON_V221_MIN_ASSOC_DF", "3"))
SPPMI_SHIFT = float(os.environ.get("DARTLAB_HORIZON_V221_SPPMI_SHIFT", "0.7"))
RWR_ALPHA = float(os.environ.get("DARTLAB_HORIZON_V221_RWR_ALPHA", "0.64"))
TOPK = int(os.environ.get("DARTLAB_HORIZON_V221_TOPK", "10"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V221_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V221_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V221_SIB_JACCARD_LO", "0.5"))
RRF_K = int(os.environ.get("DARTLAB_HORIZON_V221_RRF_K", "60"))

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


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def isTestCorp(corp: str) -> bool:
    return (stableHashInt(corp) % TEST_MOD) == 0 if corp else False


def tokenFeatureWeights(token: str) -> dict[str, float]:
    """Korean tokenizer 없이 쓰는 conservative morph proxy. Feature 는 title side 주소일 뿐 의미가 아니다."""
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


def buildAssoc(trainDocs: list[Doc]) -> tuple[dict[str, Counter], Counter, int]:
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
    return dict(sorted(profile.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])


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


def normalizeProfile(profile: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in profile.values())
    if total <= 0:
        return {}
    return {key: max(0.0, value) / total for key, value in profile.items() if value > 0}


def expandMorphSppmi(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    seeds = coreFeatureWeights(core)
    profile: dict[str, float] = defaultdict(float)
    for feature, seedWeight in seeds.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            profile[bodyTerm] += seedWeight * edgeWeight
    return topProfile(profile, EXPAND_TOPN)


def expandRwr2Hop(core: frozenset[str], graph: SppmiGraph) -> dict[str, float]:
    first = normalizeProfile(expandMorphSppmi(core, graph))
    if not first:
        return {}
    titleWalk: dict[str, float] = defaultdict(float)
    for bodyTerm, bodyProb in topProfile(first, RWR_BRANCH).items():
        for feature, edgeWeight in graph.bodyToTitle.get(bodyTerm, {}).items():
            titleWalk[feature] += bodyProb * edgeWeight
    titleWalk = normalizeProfile(topProfile(titleWalk, RWR_BRANCH * 2))
    second: dict[str, float] = defaultdict(float)
    for feature, featureProb in titleWalk.items():
        for bodyTerm, edgeWeight in graph.titleToBody.get(feature, {}).items():
            second[bodyTerm] += featureProb * edgeWeight
    second = normalizeProfile(topProfile(second, RWR_TOPN))
    final: dict[str, float] = defaultdict(float)
    for bodyTerm, value in first.items():
        final[bodyTerm] += RWR_ALPHA * value
    for bodyTerm, value in second.items():
        final[bodyTerm] += (1.0 - RWR_ALPHA) * value
    return topProfile(final, RWR_TOPN)


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


def rrfFuse(scoreDicts: list[dict[int, float]], k: int = RRF_K) -> dict[int, float]:
    """reciprocal rank fusion — tuning-free 결합. keyword+experience 증분 측정용."""
    fused: dict[int, float] = defaultdict(float)
    for scores in scoreDicts:
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        for r, (pos, _) in enumerate(ranked, start=1):
            fused[pos] += 1.0 / (k + r)
    return dict(fused)


# ---- 자(尺): exact-doc / meaning-class / antonym-null ----


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def charBigrams(key: str) -> set[str]:
    flat = key.replace("|", "")
    if len(flat) < 2:
        return {flat} if flat else set()
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


def evaluateExact(queries, goldPos, scorer) -> dict[str, float]:
    top1 = top5 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        gold = goldPos[qid]
        scores = scorer(qid, core)
        n += 1
        if not scores:
            continue
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
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


def evaluateClass(queries, posClass, classMembers, scorer) -> dict[str, float]:
    """meaning-class gold: 같은 report_nm core 의 *다른* test 문서를 맞히면 정답(F1 교정)."""
    top1 = top5 = 0
    mrr = 0.0
    n = 0
    for qid, core, _ in queries:
        cls = posClass[qid]
        gold = set(classMembers.get(cls, ())) - {qid}
        if not gold:  # singleton 의미류는 type-eval 불가
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


def mineSiblings(classMembers: dict[str, list[int]]) -> dict[str, list[str]]:
    """char-bigram 유사하지만 동일하지 않은 의미류 쌍 = sibling/antonym 후보(코퍼스 채굴, 손사전 아님)."""
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
    """antonym-null: own-class 후보를 sibling-class 후보 위로 올리는가. own1 이 chance 를 넘어야 G2 신호."""
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

    assoc, bodyDf, nTrain = buildAssoc(trainDocs)
    graph = buildSppmiGraph(trainDocs)
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
    rwrCache: dict[int, dict[str, float]] = {}
    assocCache: dict[int, dict[str, float]] = {}

    def getAssoc(qid, core):
        if qid not in assocCache:
            assocCache[qid] = expandQuery(core, assoc, bodyDf, nTrain)
        return assocCache[qid]

    def getMorph(qid, core):
        if qid not in morphCache:
            morphCache[qid] = expandMorphSppmi(core, graph)
        return morphCache[qid]

    def getRwr(qid, core):
        if qid not in rwrCache:
            rwrCache[qid] = expandRwr2Hop(core, graph)
        return rwrCache[qid]

    def keywordScorer(qid, core):
        return scoreKeyword(core, invRaw)

    def morphScorer(qid, core):
        return scoreAssoc(getMorph(qid, core), testDocs, inv)

    def rwrScorer(qid, core):
        return scoreAssoc(getRwr(qid, core), testDocs, inv)

    def fusedScorer(qid, core):  # keyword + morph (RRF) — experience 증분 측정
        return rrfFuse([keywordScorer(qid, core), morphScorer(qid, core)])

    scorers = {
        "keyword": keywordScorer,
        "morphSppmi": morphScorer,
        "rwr2Hop": rwrScorer,
        "keyword+morphRRF": fusedScorer,
    }

    # exact-doc (F1 비교용) vs meaning-class (교정된 자)
    exactRes = {name: evaluateExact(queries, goldPos, fn) for name, fn in scorers.items()}
    classRes = {name: evaluateClass(queries, posClass, classMembers, fn) for name, fn in scorers.items()}

    # antonym-null
    sibRes = {name: evaluateSibling(queries, posClass, classMembers, siblings, fn) for name, fn in scorers.items()}

    # shuffle-null (morph 기준)
    shufGold = dict(goldPos)
    shuffled = [q[0] for q in queries]
    rng.shuffle(shuffled)
    for q, sp in zip(queries, shuffled):
        shufGold[q[0]] = sp
    shufMorph = evaluateExact(queries, shufGold, morphScorer)

    chance = 1.0 / len(testDocs)
    morphCoverage = sum(1 for q in queries if getMorph(q[0], q[1])) / len(queries)
    classEvalN = classRes["morphSppmi"]["n"]
    sibN = sibRes["morphSppmi"]["n"]

    print("=" * 70)
    print(f"V221 meaning-class gold + antonym-null (자 correction)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(
        f"queries={len(queries)} classEvalN={classEvalN} siblingEvalN={sibN} "
        f"classes={len(classMembers)} siblingClasses={len(siblings)} "
        f"morphCoverage={morphCoverage:.3f} chanceTop1={chance:.5f}"
    )
    print("-" * 70)
    print("[exact-doc gold] (F1: near-duplicate 동일유형도 오답 — 의미 오측정)")
    for name in scorers:
        r = exactRes[name]
        print(f"  {name:<18}: Top1={r['top1']:.4f} Top5={r['top5']:.4f} MRR={r['mrr']:.4f}")
    print("[meaning-class gold] (교정: 같은 report_nm 의미류 회수면 정답)")
    for name in scorers:
        r = classRes[name]
        print(f"  {name:<18}: Top1={r['top1']:.4f} Top5={r['top5']:.4f} MRR={r['mrr']:.4f}")
    print("-" * 70)
    print("[antonym-null] sibling discrimination (own1 가 chance 를 넘어야 G2 신호)")
    for name in scorers:
        r = sibRes[name]
        margin = r["own1"] - r["chance"]
        print(f"  {name:<18}: own1={r['own1']:.4f} chance={r['chance']:.4f} margin={margin:+.4f} n={r['n']}")
    print("-" * 70)
    gatePass = shufMorph["top1"] <= max(chance * 5, 0.01)
    print(
        f"SHUFFLE-NULL: morphSppmi exact Top1={shufMorph['top1']:.5f} (chance={chance:.5f}) "
        f"-> {'PASS' if gatePass else 'FAIL'}"
    )
    # promotion 신호 요약 (자 교정 iteration 이므로 기계 promotion 이 아니라 자 진단)
    kClass = classRes["keyword"]
    mClass = classRes["morphSppmi"]
    fClass = classRes["keyword+morphRRF"]
    print("-" * 70)
    print(
        f"G1 proxy(class): morphSppmi vs keyword  MRR {mClass['mrr']:.4f} vs {kClass['mrr']:.4f} "
        f"-> {'morph WINS' if mClass['mrr'] > kClass['mrr'] else 'keyword WINS'}"
    )
    print(
        f"F3 증분: keyword+morphRRF vs keyword     MRR {fClass['mrr']:.4f} vs {kClass['mrr']:.4f} "
        f"-> {'RRF ADDS' if fClass['mrr'] > kClass['mrr'] else 'NO ADD'}"
    )
    sibMorph = sibRes["morphSppmi"]
    print(
        f"G2 proxy: morph sibling own1 {sibMorph['own1']:.4f} vs chance {sibMorph['chance']:.4f} "
        f"-> {'DISCRIMINATES' if sibMorph['own1'] > sibMorph['chance'] + 0.03 else 'NO (antonym-null fail)'}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
