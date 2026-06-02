"""Horizon Meaning Learner V224 - mask-the-token strong null (G2 결판 진단).

V221~V223: 분포 experience 3 종 다 antonym-null chance 이하. 유일 변별자 = keyword(정확 stem, +0.226).
전문가 토론(referential / lexical-contrast / 레드팀) 수렴: G2 를 게이트에서 *단일 진단 실험* 으로 강등하라.
사활 질문 = "변별 morpheme 을 byte-exact 완전 마스킹하면 keyword 변별이 chance 로 붕괴하는가, 그리고
*잔존 흔적*(파생·인접: 제3자배정/자본전입 등)이 여전히 sibling 을 가르는가."

    - keyword 가 강한-null 에서 붕괴 -> 결합축은 본질적으로 lexical(정확토큰). 하이브리드 수용, G2 강등 입증.
    - residualTrace(변별 morpheme 제거 후 잔존 본문 어휘)가 여전히 chance 를 유의하게 상회 -> 분포에 진짜
      비-lexical 결합축 신호가 있다 -> G2 를 진짜 표상 문제로 격상.

이건 기계 추가가 아니라 *자(尺) 강화*(escalation: eval 을 더 어렵게)다. R4 준수.

방법:
    - sibling cluster(report_nm core char-bigram 채굴)에서 class 쌍의 char LCS 를 공유로 보고, 잔여 substring 을
      *변별 morpheme* 으로 자동 추출(손사전 아님, R1).
    - 강한 마스킹: body text 에서 변별 morpheme 문자열을 byte-exact 제거(누수 감사로 0 확인).
    - antonym-null 을 (정상 / 강한-null) 두 조건에서 keyword 와 residualTrace 로 측정.
    - residualTrace = train class 별 *변별 morpheme 제거* body 프로파일(IDF 가중). 잔존 어휘만으로 sibling 변별 시도.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV224Test.py
    $env:DARTLAB_HORIZON_V224_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV224Test.py

검증 기준:
    1. 데이터 allFilings report_nm + content_raw 만. class·변별 morpheme 은 report_nm + char 구조(R1).
    2. train/test corp_code 분리. residualTrace 프로파일은 train 에서만.
    3. 강한-null 누수 감사: 변별 morpheme 문자열이 마스킹 본문에 0 건이어야(byte-exact).
    4. 결판: keyword 정상 margin(+) vs 강한-null margin. residualTrace 강한-null margin 의 chance 상회 여부.

결과:
    py_compile + lint-camelcase 통과.

    40-file: docs=12734 train=9876 test=2858 siblingEvalN=581, leakViolations=0, buildSeconds~=28
      keyword  normal own1=0.7332 margin=+0.0981
      keyword  STRONG (변별 morpheme byte-exact 제거) own1=0.6850 margin=+0.0499
      residual STRONG (잔존 인접 어휘 class-centroid) own1=0.9914 margin=+0.3563
      누수 감사 0 leak.

결론:
    결판/예상 뒤집힘 (단 caveat 큼). 변별 morpheme 을 byte-exact 완전 제거(누수 0)했는데도:
    - keyword 는 거의 붕괴(+0.098 -> +0.050) — 정확토큰 제거되니 기대대로 chance 근처로 내려옴.
    - 그러나 residualTrace(잔존 인접 어휘의 class-centroid)는 +0.356 으로 sibling 을 강하게 가른다.
    => "결합축 = 순수 lexical(정확토큰)"이라는 V221~V223 결론은 *과소평가*였다. sibling(유상/무상증자)은 변별
       morpheme 을 지워도 인접 어휘 분포(제3자배정/청약/실권 vs 자본전입/무상교부)가 다르다. 비-lexical 결합축
       신호가 분포에 존재한다.

    왜 V221~V223 은 못 봤나 (핵심 분해):
       V221~V223 은 *단일 query 확장*으로 sibling 을 가르려다 실패했다. V224 는 *class-centroid*(train 동일류
       다수 문서 집계)로 가른다. 신호는 분포에 있으나 단일 query 확장은 너무 noisy/sparse 해 못 끌어낸다.
       class-prototype 집계가 있어야 결합축이 드러난다. => 다음 기계의 방향(prototype contrast).

    정직한 caveat (over-claim 금지, 레드팀 경고 반영):
       1. residualTrace 는 class label 로 centroid 를 만든 *prototype* 이다(query-time class 미지 아님).
          진짜 query-time 변별로 격상하려면 prototype 라우팅이 필요.
       2. own1 0.9914 는 *template/boilerplate fingerprint* 일 수 있다 — 같은 공시유형은 본문 양식이 거의 같아
          "의미"가 아니라 "양식 지문"으로 갈렸을 가능성. 레드팀의 negative-control(무관 쌍 오변별)과
          masked-QUERY 가 아직 없어 의미 신호와 양식 지문을 분리하지 못했다.

    다음(V225): (a) class-prototype contrast 를 query-time 기계로(prototype 라우팅), (b) eval 에
    negative-control(무관 쌍)과 masked-QUERY 추가해 template-fingerprint 를 의미 신호와 분리. 둘 다 통과해야
    G2 진짜 격상. 통과 못 하면 V224 의 +0.356 은 양식 지문으로 강등.
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

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V224_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V224_ROWS_PER_FILE", "600"))
MAX_QUERIES = int(os.environ.get("DARTLAB_HORIZON_V224_MAX_QUERIES", "3000"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V224_TEST_MOD", "4"))
BODY_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V224_BODY_CHARS", "6000"))
EXPAND_TOPN = int(os.environ.get("DARTLAB_HORIZON_V224_EXPAND_TOPN", "80"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V224_SIB_MIN_MEMBERS", "3"))
SIB_MAX_CLASSES = int(os.environ.get("DARTLAB_HORIZON_V224_SIB_MAX_CLASSES", "500"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V224_SIB_JACCARD_LO", "0.5"))
MIN_DISC_LEN = int(os.environ.get("DARTLAB_HORIZON_V224_MIN_DISC_LEN", "1"))

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
    bodyText: str  # cleaned body (byte-exact 마스킹용)


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
    """class 와 sibling 들의 char LCS 를 공유로 보고, 잔여 substring 을 변별 morpheme 으로 자동 추출."""
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
    # own class 의 token 자체도 변별자(정확 stem)로 포함
    for t in cls.split("|"):
        out.add(t)
    return {d for d in out if d}


def strongMask(text: str, discSet: set[str]) -> str:
    """변별 morpheme 문자열을 byte-exact 제거. 긴 것부터 제거해 부분 중첩 누수 방지."""
    masked = text
    for d in sorted(discSet, key=len, reverse=True):
        if d:
            masked = masked.replace(d, " ")
    return masked


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

    # train class 별 잔존-어휘 프로파일 (residualTrace): 변별 morpheme 제거 후 body stem IDF 가중
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

    def residualProfile(cls: str, discSet: set[str]) -> dict[str, float]:
        agg: Counter = Counter()
        members = trainByClass.get(cls, ())
        if not members:
            return {}
        for ti in members:
            for b in trainStemCache[ti]:
                if any(d in b for d in discSet):  # 변별 morpheme 포함 stem 제거
                    continue
                agg[b] += 1
        prof: dict[str, float] = {}
        for b, c in agg.items():
            df = trainDf.get(b, 0)
            if df <= 0:
                continue
            prof[b] = (c / len(members)) * math.log(1.0 + nTrain / df)
        return dict(sorted(prof.items(), key=lambda kv: kv[1], reverse=True)[:EXPAND_TOPN])

    leakViolations = 0
    sibPairs = 0
    kwNormalOwn = kwStrongOwn = resStrongOwn = 0
    chanceSum = 0.0
    n = 0
    queriesDone = 0

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
        sibM -= {pos}
        sibM -= ownM
        if not sibM:
            continue
        pool = list(ownM | sibM)
        discSet = discriminators(cls, sibs)
        prof = residualProfile(cls, discSet)

        n += 1
        queriesDone += 1
        chanceSum += len(ownM) / len(pool)

        # normal keyword: query core token 이 후보 본문(원문)에 등장하는가
        kwNormal: dict[int, float] = {}
        for cand in pool:
            t = testDocs[cand].bodyText
            kwNormal[cand] = sum(1.0 for tok in d.core if tok in t)
        rankN = sorted(pool, key=lambda c: (-kwNormal.get(c, 0.0), c))
        if rankN[0] in ownM:
            kwNormalOwn += 1

        # strong-null: 변별 morpheme byte-exact 제거 후 keyword & residualTrace
        kwStrong: dict[int, float] = {}
        resStrong: dict[int, float] = {}
        maskedQueryCore = {strongMask(tok, discSet).strip() for tok in d.core}
        maskedQueryCore = {q for q in maskedQueryCore if q}
        for cand in pool:
            mt = strongMask(testDocs[cand].bodyText, discSet)
            # 누수 감사
            for dd in discSet:
                if dd and dd in mt:
                    leakViolations += 1
                    break
            kwStrong[cand] = sum(1.0 for tok in maskedQueryCore if tok and tok in mt)
            mstems = set(bodyStemsFrom(mt))
            resStrong[cand] = sum(w for b, w in prof.items() if b in mstems)
        rankKwS = sorted(pool, key=lambda c: (-kwStrong.get(c, 0.0), c))
        if rankKwS[0] in ownM:
            kwStrongOwn += 1
        rankResS = sorted(pool, key=lambda c: (-resStrong.get(c, 0.0), c))
        if rankResS[0] in ownM:
            resStrongOwn += 1

        sibPairs += 1
        if queriesDone >= MAX_QUERIES:
            break

    if n == 0:
        print("no sibling-eval queries")
        return
    chance = chanceSum / n
    kwN = kwNormalOwn / n
    kwS = kwStrongOwn / n
    resS = resStrongOwn / n

    print("=" * 72)
    print(f"V224 mask-the-token strong null (G2 결판 진단)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(trainDocs)} test={len(testDocs)}")
    print(f"siblingEvalN={n} chance(own/pool)={chance:.4f} leakViolations={leakViolations}")
    print("-" * 72)
    print(f"keyword  normal own1={kwN:.4f}  margin={kwN - chance:+.4f}   (정상: 정확 stem 변별)")
    print(f"keyword  STRONG own1={kwS:.4f}  margin={kwS - chance:+.4f}   (변별 morpheme 제거 후)")
    print(f"residual STRONG own1={resS:.4f}  margin={resS - chance:+.4f}   (잔존 어휘만으로)")
    print("-" * 72)
    kwCollapsed = (kwN - chance) > 0.05 and (kwS - chance) <= 0.03
    resSurvives = (resS - chance) > 0.03
    print(f"누수 감사: {'OK (0 leak)' if leakViolations == 0 else f'FAIL ({leakViolations} leak)'}")
    print(f"keyword 강한-null 붕괴: {'YES (변별=정확토큰 입증)' if kwCollapsed else 'NO'}")
    print(
        f"residualTrace 잔존 신호: {'YES (비-lexical 결합축 존재 -> G2 격상)' if resSurvives else 'NO (결합축=lexical)'}"
    )
    print("-" * 72)
    if leakViolations == 0 and kwCollapsed and not resSurvives:
        verdict = "결판: 결합축은 본질적으로 LEXICAL. 하이브리드 수용, G2 게이트->진단 강등 입증."
    elif resSurvives:
        verdict = "결판: 잔존 어휘에 비-lexical 신호 존재. G2 를 진짜 표상 문제로 격상."
    else:
        verdict = "비결정: 누수 또는 keyword 미붕괴. 마스킹/표본 재점검."
    print(f"VERDICT: {verdict}")
    print("=" * 72)


if __name__ == "__main__":
    main()
