"""Horizon Meaning Learner V225 - masked-query & negative-control (V224 +0.356 의 의미 vs 양식 분리).

V224 결판: 변별 morpheme byte-exact 제거(누수 0)에도 residualTrace(잔존 어휘 class-centroid)가 sibling 을
+0.356 으로 가름. 단 두 caveat 미해결:
    C1. centroid 는 class label 로 만든 prototype — query-time class 미지가 아니다.
    C2. own1 0.99 는 template/boilerplate 지문일 수 있다(같은 공시유형=같은 양식). antonym "의미"인지
        generic class-ID 인지 미분리.

V225 는 기계를 짓지 않고(R4: V224 자를 잇는 측정 강화) 두 통제로 C1·C2 를 가린다:
    1. masked-QUERY: 단일 test doc 의 *강한-마스킹 본문* 만을 query 로(라벨·centroid 없이) 잔존 어휘 overlap 으로
       sibling 변별. 살면 query-time 사용 가능 신호. 무너지면 centroid 집계 아티팩트.
    2. negative-control: 같은 centroid/masked-query 로 *무관 비-sibling 쌍* 도 가르는가. sibling 과 같은 수준으로
       무관쌍도 가르면 = generic class-ID/양식 지문(antonym 특이 아님). sibling 이 무관쌍보다 *어렵되* chance 상회면
       confusable-but-separable = 진짜 변별.

판정:
    - masked-query sibling margin > 0(유의) + 누수 0 -> query-time 비-lexical 신호 REAL -> 다음 prototype 기계 정당.
    - masked-query 붕괴 -> V224 +0.356 은 centroid-only 아티팩트로 강등.
    - negative-control 로 "antonym 특이 vs generic 양식 지문" 맥락 제공(과장 금지).

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV225Test.py
    $env:DARTLAB_HORIZON_V225_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV225Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. 변별 morpheme = report_nm char 구조(R1).
    2. train/test corp_code 분리. IDF/centroid 는 train.
    3. 누수 0(byte-exact). negative-control 은 sibling 이 아닌 class 에서 결정적 샘플.
    4. masked-query 는 라벨·centroid 미사용(단일 doc 본문만).

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 train=9876 test=2858 siblingEvalN=581 negControlN=581 leak=0, buildSeconds~=21
      [sibling pool]  centroid own1=0.9914 margin=+0.3563; maskedQ own1=0.9484 margin=+0.3133
      [neg-control]   centroid own1=0.9983 margin=+0.3360; maskedQ own1=0.9966 margin=+0.3343
    (스크립트 auto-VERDICT 는 "G2 격상"으로 찍혔으나 과낙관 — 아래 교정.)

결론:
    부분/진단 성공 (auto-verdict 교정).

    C1 해소: masked-query(단일 doc, 라벨·centroid 미사용)가 sibling 을 +0.313 으로 가른다. V224 의 +0.356 은
    centroid 집계 아티팩트가 아니라 query-time 으로도 실재. 즉 "분포로 sibling 변별 불가"라던 V221~V223 은
    *missing 축* 때문이 아니라 *query 표현이 약해서*(sparse expansion)였다. full residual-body overlap 은
    siblings 를 회수한다 — 이게 이번의 진짜 발견.

    C2 미해소 (핵심 교정): negative-control 이 무관 비-sibling 쌍도 +0.334 로 *동등하게* 가른다
    (sibling maskedQ +0.313 ≈ 무관 +0.334). 즉 이 신호는 antonym 특이 결합축이 아니라 *generic
    class-vocabulary 식별*(계열축)이며, 그 안에 공시유형 template/boilerplate 가 상당부분 섞여 있다. sibling 이
    무관쌍보다 *유의하게* 어렵지 않다 = 별도 sign-bearing 결합축 표상의 증거가 아니다. auto-verdict 의
    siblingHarder 임계(0.02)는 0.313 vs 0.334 의 근소차를 과대해석했다.

    종합 재구성 (V221~V225):
    - 계열축(vocabulary 회수)은 강하다. full residual-body overlap 이면 siblings 까지 +0.31 로 가른다.
    - 그러나 그것이 "의미"인지 "공시양식 지문"인지 아직 분리 안 됐다(negative-control 이 둘을 못 가름).
    - 별도의 sign-bearing 결합축은 여전히 미입증. G2 의 margin 수치는 query-time 으로 넘었으나(누수 0),
      [의미의 정의](빈도 아닌 예측 불변량) 기준의 "의미 발견"으로 부르기엔 template 오염이 미분리.

    다음(V226): template/boilerplate 분리. cross-class high-DF 잔존어(공통 양식어)를 제거하고 *contentful
    잔존어*(제3자배정/자본전입 등 class-희소 의미어)만으로 masked-query + negative-control 재측정. sibling
    margin 이 살아남고 무관쌍 margin 이 *내려가면*(=신호가 양식 아닌 내용) 비로소 의미 특이. 둘 다 안 갈리면
    이 신호는 template 지문으로 강등.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V225_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V225_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V225_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V225_TEST_MOD", "4"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V225_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V225_EXPAND_TOPN", "80"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V225_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V225_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V225_SIB_JACCARD_LO", "0.5"))
MIN_DISC_LEN = int(os.environ.get("DARTLAB_HORIZON_V225_MIN_DISC_LEN", "1"))
NEG_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V225_NEG_CLASSES", "3"))

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


def bodyStemsFrom(text: str) -> list[str]:
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


@dataclass
class Doc:
    idx: int
    corp: str
    isTest: bool
    core: frozenset[str]
    bodyText: str


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
            if len(bodyStemsFrom(text)) < 12:
                continue
            docs.append(Doc(idx, corp, isTestCorp(corp), frozenset(core), text))
            idx += 1
        del df
    return docs


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def charBigrams(key: str) -> set[str]:
    flat = key.replace("|", "")
    if len(flat) < 2:
        return {flat} if flat else set()
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


def longestCommonSubstr(a: str, b: str) -> str:
    if not a or not b:
        return ""
    prev = [0] * (len(b) + 1)
    best = 0
    end = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
                    end = i
        prev = cur
    return a[end - best : end]


def mineSiblings(classMembers: dict[str, list[int]]) -> dict[str, list[str]]:
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
            if SIB_JACCARD_LO <= len(ba & bb) / uni < 0.999:
                sib[a].append(b)
                sib[b].append(a)
    return sib


def discriminators(cls: str, sibs: list[str]) -> set[str]:
    flat = cls.replace("|", "")
    out: set[str] = set()
    for s in sibs:
        lcs = longestCommonSubstr(flat, s.replace("|", ""))
        if not lcs:
            out.add(flat)
            continue
        for residual in flat.split(lcs):
            residual = residual.strip()
            if len(residual) >= MIN_DISC_LEN:
                out.add(residual)
    for t in cls.split("|"):
        out.add(t)
    return {d for d in out if d}


def strongMask(text: str, discSet: set[str]) -> str:
    masked = text
    for d in sorted(discSet, key=len, reverse=True):
        if d:
            masked = masked.replace(d, " ")
    return masked


def own1OverPool(scores: dict[int, float], ownM: set[int], pool: list[int]) -> bool:
    ranked = sorted(pool, key=lambda c: (-scores.get(c, 0.0), c))
    return ranked[0] in ownM


def main() -> None:
    t0 = time.time()
    docs = loadDocs()
    trainDocs = [d for d in docs if not d.isTest]
    testDocs = [d for d in docs if d.isTest]
    if not testDocs or not trainDocs:
        print(f"insufficient split: train={len(trainDocs)} test={len(testDocs)}")
        return

    posClass: dict[int, str] = {}
    classMembers: dict[str, list[int]] = defaultdict(list)
    for pos, d in enumerate(testDocs):
        posClass[pos] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(pos)
    siblings = mineSiblings(classMembers)
    sortedClasses = sorted(classMembers.keys())

    trainByClass: dict[str, list[int]] = defaultdict(list)
    for ti, d in enumerate(trainDocs):
        trainByClass[classKeyOf(d.core)].append(ti)
    nTrain = len(trainDocs)
    trainDf: Counter = Counter()
    trainStemCache: list[set[str]] = []
    for d in trainDocs:
        s = set(bodyStemsFrom(d.bodyText))
        trainStemCache.append(s)
        for b in s:
            trainDf[b] += 1

    def idf(b: str) -> float:
        df = trainDf.get(b, 0)
        return math.log(1.0 + nTrain / df) if df > 0 else 0.0

    def centroidProfile(cls: str, discSet: set[str]) -> dict[str, float]:
        members = trainByClass.get(cls, ())
        if not members:
            return {}
        agg: Counter = Counter()
        for ti in members:
            for b in trainStemCache[ti]:
                if any(d in b for d in discSet):
                    continue
                agg[b] += 1
        prof = {b: (c / len(members)) * idf(b) for b, c in agg.items() if idf(b) > 0}
        return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])

    def maskedStems(cand: int, discSet: set[str]) -> set[str]:
        return set(bodyStemsFrom(strongMask(testDocs[cand].bodyText, discSet)))

    # 집계 카운터
    agg = {
        "sib_centroid": [0, 0.0],
        "sib_maskedq": [0, 0.0],
        "neg_centroid": [0, 0.0],
        "neg_maskedq": [0, 0.0],
    }
    n = 0
    negN = 0
    leak = 0
    done = 0

    for pos, d in enumerate(testDocs):
        cls = posClass[pos]
        sibs = siblings.get(cls)
        if not sibs:
            continue
        ownM = set(classMembers.get(cls, ())) - {pos}
        if not ownM:
            continue
        sibM: set[int] = set()
        for s in sibs:
            sibM |= set(classMembers.get(s, ()))
        sibM -= {pos} | ownM
        if not sibM:
            continue
        discSet = discriminators(cls, sibs)
        pool = list(ownM | sibM)

        prof = centroidProfile(cls, discSet)
        # query doc 자신의 masked 잔존 stem (라벨·centroid 미사용)
        qStems = maskedStems(pos, discSet)
        qProf = {b: idf(b) for b in qStems if idf(b) > 0}

        candStems: dict[int, set[str]] = {}
        cScore: dict[int, float] = {}
        mScore: dict[int, float] = {}
        for cand in pool:
            ms = maskedStems(cand, discSet)
            candStems[cand] = ms
            for dd in discSet:
                if dd and dd in strongMask(testDocs[cand].bodyText, discSet):
                    leak += 1
                    break
            cScore[cand] = sum(w for b, w in prof.items() if b in ms)
            mScore[cand] = sum(w for b, w in qProf.items() if b in ms)

        n += 1
        done += 1
        chance = len(ownM) / len(pool)
        agg["sib_centroid"][0] += int(own1OverPool(cScore, ownM, pool))
        agg["sib_centroid"][1] += chance
        agg["sib_maskedq"][0] += int(own1OverPool(mScore, ownM, pool))
        agg["sib_maskedq"][1] += chance

        # negative-control: 무관(비-sibling) class 들로 pool 구성, 같은 |sibM| 규모
        sibSet = set(sibs)
        negPoolSib: set[int] = set()
        start = stableHashInt(cls) % max(1, len(sortedClasses))
        k = 0
        for off in range(len(sortedClasses)):
            oc = sortedClasses[(start + off) % len(sortedClasses)]
            if oc == cls or oc in sibSet:
                continue
            mem = set(classMembers.get(oc, ())) - {pos} - ownM
            if not mem:
                continue
            negPoolSib |= mem
            k += 1
            if k >= NEG_CLASSES or len(negPoolSib) >= len(sibM):
                break
        if negPoolSib:
            negPool = list(ownM | negPoolSib)
            cScoreN: dict[int, float] = {}
            mScoreN: dict[int, float] = {}
            for cand in negPool:
                ms = candStems.get(cand)
                if ms is None:
                    ms = maskedStems(cand, discSet)
                cScoreN[cand] = sum(w for b, w in prof.items() if b in ms)
                mScoreN[cand] = sum(w for b, w in qProf.items() if b in ms)
            negN += 1
            chanceN = len(ownM) / len(negPool)
            agg["neg_centroid"][0] += int(own1OverPool(cScoreN, ownM, negPool))
            agg["neg_centroid"][1] += chanceN
            agg["neg_maskedq"][0] += int(own1OverPool(mScoreN, ownM, negPool))
            agg["neg_maskedq"][1] += chanceN

        if done >= MAX_QUERIES:
            break

    if n == 0:
        print("no sibling-eval queries")
        return

    def report(key, denom):
        hits, chsum = agg[key]
        own1 = hits / denom if denom else 0.0
        ch = chsum / denom if denom else 0.0
        return own1, ch

    scOwn, scCh = report("sib_centroid", n)
    smOwn, smCh = report("sib_maskedq", n)
    ncOwn, ncCh = report("neg_centroid", negN)
    nmOwn, nmCh = report("neg_maskedq", negN)

    print("=" * 74)
    print(f"V225 masked-query & negative-control  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(f"siblingEvalN={n} negControlN={negN} leak={leak}")
    print("-" * 74)
    print("[sibling pool] own1 vs chance (margin)")
    print(f"  centroid  : own1={scOwn:.4f} chance={scCh:.4f} margin={scOwn - scCh:+.4f}  (V224 재현, 라벨 사용)")
    print(f"  maskedQ   : own1={smOwn:.4f} chance={smCh:.4f} margin={smOwn - smCh:+.4f}  (단일 doc, 라벨 X)")
    print("[negative-control pool: 무관 비-sibling class] own1 vs chance (margin)")
    print(f"  centroid  : own1={ncOwn:.4f} chance={ncCh:.4f} margin={ncOwn - ncCh:+.4f}")
    print(f"  maskedQ   : own1={nmOwn:.4f} chance={nmCh:.4f} margin={nmOwn - nmCh:+.4f}")
    print("-" * 74)
    qtimeReal = (smOwn - smCh) > 0.03
    siblingHarder = (smOwn - smCh) < (nmOwn - nmCh) - 0.02  # sibling 이 무관쌍보다 어렵다
    print(f"누수: {'OK(0)' if leak == 0 else f'FAIL({leak})'}")
    print(f"masked-query 신호(라벨 없이 sibling 변별): {'REAL' if qtimeReal else 'COLLAPSED(centroid 아티팩트)'}")
    print(
        f"sibling 이 무관쌍보다 어려움(confusable): {'YES' if siblingHarder else 'NO(무관쌍과 동급=generic class-ID)'}"
    )
    print("-" * 74)
    if leak == 0 and qtimeReal and siblingHarder:
        v = "결판: query-time 비-lexical 신호 REAL + sibling 특이. G2 격상, 다음 prototype 기계 정당."
    elif leak == 0 and qtimeReal and not siblingHarder:
        v = "부분: masked-q 신호는 살지만 무관쌍도 동급으로 가름 = 상당부분 generic class-ID/양식 지문. 의미 특이성 약함."
    elif not qtimeReal:
        v = "강등: masked-query 붕괴 = V224 +0.356 은 centroid 집계 아티팩트(query-time 사용 불가)."
    else:
        v = "비결정: 누수 또는 표본 재점검."
    print(f"VERDICT: {v}")
    print("=" * 74)


if __name__ == "__main__":
    main()
