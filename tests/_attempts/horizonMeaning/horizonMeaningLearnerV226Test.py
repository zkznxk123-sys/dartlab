"""Horizon Meaning Learner V226 - boilerplate strip: 의미 신호 vs 공시양식 지문 결판.

V225: masked-query(라벨 없이)가 sibling 을 +0.313 으로 가르되, negative-control(무관 쌍)도 +0.334 로 *동등하게*
가른다 -> 신호가 generic class-vocabulary(template 오염 포함)이지 antonym 특이 결합축인지 미분리.

V226 (R4: V225 자를 잇는 측정, 기계 무변): cross-class boilerplate 를 제거하고 *contentful 잔존어* 만으로
재측정한다.
    - boilerplate = train 에서 여러 의미류에 두루 나타나는 high class-DF 잔존어(공통 공시양식어).
    - contentful = class-희소 잔존어(제3자배정/자본전입 등). 양식이 아니라 내용에 가깝다.
    가설: 신호가 *의미* 면 contentful-only 에서 sibling margin 이 살아남고 negative-control margin 은
    *떨어진다*(양식이 무관쌍을 갈랐던 것이므로). 신호가 *양식 지문* 이면 contentful 제거 시 둘 다 붕괴하거나,
    sibling 과 무관쌍이 계속 동급.

판정:
    - contentful sibling margin > 0(유지) AND (sibling - neg) 격차가 full 대비 *커짐* -> 의미 특이 신호. G2 격상.
    - contentful 에서 sibling 붕괴 -> 신호는 boilerplate/template 지문.
    - contentful 에서도 sibling≈neg -> generic class-vocabulary, antonym 특이 아님(별도 결합축 미입증 확정).

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV226Test.py
    $env:DARTLAB_HORIZON_V226_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV226Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. 변별 morpheme = report_nm char 구조(R1).
    2. train/test corp_code 분리. classDf/IDF/centroid 는 train.
    3. 누수 0(byte-exact). contentful 임계는 train 통계 기반 단일값(R2, eval 튜닝 금지).
    4. full residual vs contentful-only 를 sibling·negative-control 양쪽에서 동시 출력.

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 train=9876 test=2858 siblingEvalN=581 negControlN=581 leak=0,
             numTrainClasses=386, contentMaxClassDf=38, buildSeconds~=19
      maskedQ(라벨 없음): FULL sibling=+0.3133 neg=+0.3343 (sib-neg=-0.021);
                          CONTENTFUL sibling=+0.2961 neg=+0.3343 (sib-neg=-0.038)
      centroid 참고: FULL sib +0.3563 / CONT sib +0.3511

결론:
    강등/결판 (결정적 음성 결과). boilerplate(cross-class high-DF 잔존어, contentMaxClassDf=38) 제거 후에도:
    - contentful sibling margin +0.296 으로 유지되나 neg-control 도 +0.334 그대로 — 오히려 sib-neg 격차가
      -0.021 -> -0.038 로 *벌어졌다*(sibling 이 무관쌍보다 더 안 가려짐). 양식 제거가 의미 특이성을 못 만들었다.
    => 분포 신호에 *별도의 sign-bearing 결합축은 없다*. V224 의 +0.356 은 antonym 특이 의미가 아니라 generic
       class-vocabulary 식별(계열축)이며, 그것이 siblings 까지 *부수적으로* 가른 것일 뿐(무관쌍보다 특이하지 않음).

    V221~V226 종합 결판:
    - 계열축(의미류/vocabulary 회수)은 분포 experience 로 강하게 실재(class MRR 0.895, full-body overlap +0.30).
    - 결합축(반의/부호)은 분포에 *없다*. 유상 vs 무상 같은 antonym 변별은 (a) 정확 토큰(lexical) 또는 (b) 외부
      referential(회계 구조)로만 가능. "결합축을 분포가 grounding 한다"는 가설은 이 데이터에서 반증됐다.
    - 따라서 하이브리드(keyword=결합축 + 분포=계열축)는 우회가 아니라 *정답 표상*이고 이미 검증됨.

    G2 판정: 분포-experience 로의 G2 통과는 불가(입증). keyword 하이브리드로는 margin 충족되나 lexical 이라
    "학습된 의미표상"은 아님. event-disclosure antonym 엔 panel referential(G4)이 대응 안 됨.

    다음(분기): (1) 계열축 라인 확정 — riVsaHash 비교(G1 완성) + OOD(G3) 로 하이브리드 일반화 측정, 또는
    (2) G4 referential 은 accounting-term(재무제표 라인) 쿼리로 *과제를 바꿔* 별도 트랙(event antonym 아님).
    어느 쪽이든 "분포로 결합축"은 닫혔다.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V226_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V226_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V226_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V226_TEST_MOD", "4"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V226_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V226_EXPAND_TOPN", "80"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V226_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V226_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V226_SIB_JACCARD_LO", "0.5"))
MIN_DISC_LEN = int(os.environ.get("DARTLAB_HORIZON_V226_MIN_DISC_LEN", "1"))
NEG_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V226_NEG_CLASSES", "3"))
CONTENT_MAX_CLASS_RATIO = float(os.environ.get("DARTLAB_HORIZON_V226_CONTENT_MAX_CLASS_RATIO", "0.10"))

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
    numTrainClasses = max(1, len(trainByClass))
    trainDf: Counter = Counter()
    bodyClassSets: dict[str, set[str]] = defaultdict(set)
    trainStemCache: list[set[str]] = []
    for d in trainDocs:
        s = set(bodyStemsFrom(d.bodyText))
        trainStemCache.append(s)
        cls = classKeyOf(d.core)
        for b in s:
            trainDf[b] += 1
            bodyClassSets[b].add(cls)
    bodyClassDf = {b: len(cs) for b, cs in bodyClassSets.items()}
    contentMax = max(2, int(CONTENT_MAX_CLASS_RATIO * numTrainClasses))

    def idf(b: str) -> float:
        df = trainDf.get(b, 0)
        return math.log(1.0 + nTrain / df) if df > 0 else 0.0

    def contentful(b: str) -> bool:
        return bodyClassDf.get(b, 0) <= contentMax

    def centroidProfile(cls: str, discSet: set[str], contentOnly: bool) -> dict[str, float]:
        members = trainByClass.get(cls, ())
        if not members:
            return {}
        agg: Counter = Counter()
        for ti in members:
            for b in trainStemCache[ti]:
                if any(d in b for d in discSet):
                    continue
                if contentOnly and not contentful(b):
                    continue
                agg[b] += 1
        prof = {b: (c / len(members)) * idf(b) for b, c in agg.items() if idf(b) > 0}
        return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])

    def maskedStems(cand: int, discSet: set[str]) -> set[str]:
        return set(bodyStemsFrom(strongMask(testDocs[cand].bodyText, discSet)))

    keys = [f"{cond}_{pl_}_{m}" for cond in ("full", "cont") for pl_ in ("sib", "neg") for m in ("c", "m")]
    agg = {k: [0, 0.0] for k in keys}
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

        candStems: dict[int, set[str]] = {}
        for cand in pool:
            mt = strongMask(testDocs[cand].bodyText, discSet)
            for dd in discSet:
                if dd and dd in mt:
                    leak += 1
                    break
            candStems[cand] = set(bodyStemsFrom(mt))
        qStems = candStems.get(pos) or maskedStems(pos, discSet)

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
        negPool = list(ownM | negPoolSib) if negPoolSib else None
        if negPool:
            for cand in negPool:
                if cand not in candStems:
                    candStems[cand] = maskedStems(cand, discSet)

        n += 1
        done += 1
        if negPool:
            negN += 1

        for cond, contentOnly in (("full", False), ("cont", True)):
            prof = centroidProfile(cls, discSet, contentOnly)
            qProf = {b: idf(b) for b in qStems if idf(b) > 0 and (not contentOnly or contentful(b))}

            def cscore(poolList, prof=prof):
                return {c: sum(w for b, w in prof.items() if b in candStems[c]) for c in poolList}

            def mscore(poolList, qProf=qProf):
                return {c: sum(w for b, w in qProf.items() if b in candStems[c]) for c in poolList}

            chance = len(ownM) / len(pool)
            agg[f"{cond}_sib_c"][0] += int(own1OverPool(cscore(pool), ownM, pool))
            agg[f"{cond}_sib_c"][1] += chance
            agg[f"{cond}_sib_m"][0] += int(own1OverPool(mscore(pool), ownM, pool))
            agg[f"{cond}_sib_m"][1] += chance
            if negPool:
                chanceN = len(ownM) / len(negPool)
                agg[f"{cond}_neg_c"][0] += int(own1OverPool(cscore(negPool), ownM, negPool))
                agg[f"{cond}_neg_c"][1] += chanceN
                agg[f"{cond}_neg_m"][0] += int(own1OverPool(mscore(negPool), ownM, negPool))
                agg[f"{cond}_neg_m"][1] += chanceN

        if done >= MAX_QUERIES:
            break

    if n == 0:
        print("no sibling-eval queries")
        return

    def marg(key, denom):
        hits, chsum = agg[key]
        return (hits / denom - chsum / denom) if denom else 0.0

    print("=" * 76)
    print(f"V226 boilerplate strip: 의미 vs 양식 결판  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(
        f"siblingEvalN={n} negControlN={negN} leak={leak} "
        f"numTrainClasses={numTrainClasses} contentMaxClassDf={contentMax}"
    )
    print("-" * 76)
    print("margin(own1-chance), maskedQ(라벨 없음) 기준:")
    fsm = marg("full_sib_m", n)
    fnm = marg("full_neg_m", negN)
    csm = marg("cont_sib_m", n)
    cnm = marg("cont_neg_m", negN)
    print(f"  FULL residual  : sibling={fsm:+.4f}  neg-control={fnm:+.4f}  (sib-neg={fsm - fnm:+.4f})")
    print(f"  CONTENTFUL only: sibling={csm:+.4f}  neg-control={cnm:+.4f}  (sib-neg={csm - cnm:+.4f})")
    print(f"  centroid 참고  : FULL sib={marg('full_sib_c', n):+.4f} / CONT sib={marg('cont_sib_c', n):+.4f}")
    print("-" * 76)
    sibSurvives = csm > 0.03
    negDropped = (fnm - cnm) > 0.05
    specGained = (csm - cnm) > (fsm - fnm) + 0.03
    print(f"누수: {'OK(0)' if leak == 0 else f'FAIL({leak})'}")
    print(f"contentful 에서 sibling 유지: {'YES' if sibSurvives else 'NO(붕괴)'}")
    print(f"contentful 에서 neg-control 하락(양식 제거 효과): {'YES' if negDropped else 'NO'}")
    print(f"의미 특이성 증가(sib-neg 격차 ↑): {'YES' if specGained else 'NO'}")
    print("-" * 76)
    if leak == 0 and sibSurvives and specGained:
        v = "결판: contentful 잔존어가 sibling 을 무관쌍보다 특이하게 가른다 = 의미 신호 입증. G2 진짜 격상."
    elif leak == 0 and sibSurvives and not specGained:
        v = "강등: contentful 에서도 sibling≈neg = generic class-vocabulary(양식 포함), antonym 특이 아님. 결합축 미입증."
    elif not sibSurvives:
        v = "강등: contentful 제거 시 sibling 붕괴 = V224/225 신호는 상당부분 boilerplate/template 지문."
    else:
        v = "비결정: 누수/표본 재점검."
    print(f"VERDICT: {v}")
    print("=" * 76)


if __name__ == "__main__":
    main()
