"""Horizon Meaning Learner V231 - event-domain referential 결합축: 공시 표 수치 슬롯이 antonym 을 가르는가.

V230 은 회계 *계정* antonym(유동/비유동)을 accountMappings sj/code referential 로 99.9% 변별했으나, event/flow
antonym(유상/무상증자)은 계정이 아니라 그 referential 이 미적용이었다. V231 은 그 빈칸을 채운다 — event 공시의
*결합축 referent* 는 accountMappings 가 아니라 *공시 본문 표의 구조화 수치 슬롯*이다(유상증자=발행가액·납입금액>0,
무상증자=없음/0). 이건 gold(report_nm core)와 독립한 공시 자신의 referent 라 비순환(R1 안전)이고, 목표
[의미정의]가 의도한 "결합축을 회계 구조가 grounding" 의 event-domain 판본이다.

    가설(V224~229 분포 실패 + V230 referential 성공에서 도출): 분포(text body overlap)가 conflate 하는 event
    sibling(유상/무상증자)을, train 에서 채굴한 *class-변별 수치 슬롯*(예: 발행가액)의 존재/부호가 antonym-null
    에서 가른다. 분포 baseline 은 chance 근처, 슬롯 referent 는 chance 상회.

    절차:
    - content_raw HTML 표 셀에서 (label, 숫자값) 추출(자체 정규식, dartlab import 없음, OOM 안전).
    - sibling class = report_nm core char-bigram near, 다른 core.
    - train 에서 class 별 label DF 분할표 -> own-class 고유 슬롯(sibling 에 드문) 자동 채굴(손사전 아님, R1).
    - antonym-null: query class A, pool=A∪B test docs. (a) 분포 baseline=body-stem overlap, (b) slot referent=
      own 고유 슬롯 존재수. own1 vs chance 비교.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV231Test.py
    $env:DARTLAB_HORIZON_V231_FILE_LIMIT='40'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV231Test.py

검증 기준:
    1. allFilings report_nm + content_raw 만. 슬롯·class 는 train 통계(R1). dartlab import 없음(자체 파서). R5.
    2. train/test corp_code 분리. 슬롯 DF 분할표는 train 에서만.
    3. antonym-null: slot referent own1 이 분포 baseline·chance 를 유의하게 넘으면 event-domain 결합축 입증.

결과:
    py_compile 통과.

    40-file: docs=12718 train=9863 test=2855 siblingEvalN=580 chance=0.635, discSlotCoverage=0.617,
             avgDiscSlots=5.6, buildSeconds~=19
      분포 baseline(body overlap, unmasked) own1=0.9534 margin=+0.319
      slot referent(공시 수치 슬롯)        own1=0.8621 margin=+0.227

결론:
    부분/진단. event 공시의 구조화 수치 슬롯(발행가액 등)은 event antonym 을 실제로 가른다(slot own1 0.862,
    margin +0.227 >> chance) — event-domain 결합축 referent 가 *존재*한다(목표 의도대로 구조가 grounding).
    그러나 unmasked body overlap(+0.319)을 못 넘는다: 본문이 이미 변별 어휘(유상/발행가액 family)를 담아
    표 슬롯 referent 가 redundant.

    핵심 미완: V231 은 unmasked regime 이라 "쉬운" 변별이다. 결정적 테스트는 V224 식 *변별 morpheme 마스킹*
    하에서 slot referent 가 살아남는가 — 발행가액 슬롯은 "유상" 토큰 제거에도 남으므로(다른 토큰), 마스킹된
    본문에서 distribution 은 붕괴해도(V228) slot referent 는 버틸 가능성. V231 은 그걸 안 쟀다.

    다음(V232): strong-null(변별 morpheme byte-exact 마스킹) 하에서 slot referent vs distribution. slot 이
    마스킹 후에도 chance 상회 + distribution 붕괴면 -> event-domain 결합축이 구조 referent 에 있음을 비순환 입증.

    V230(계정)+V231(event) 종합: 결합축 referent 는 두 도메인 다 *존재* — 계정은 sj/code(99.9%), event 는 표
    수치 슬롯(+0.227, 단 unmasked 우위 미확정). 분포는 둘 다 결합축 자체는 못 만들되, event 는 unmasked body 에
    변별어가 있어 표면상 풀린다. 진짜 결합축 검증은 masked 에서 slot referent(V232).
"""

from __future__ import annotations

import hashlib
import html
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"

FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V231_FILE_LIMIT", "16"))
ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V231_ROWS_PER_FILE", "600"))
TEST_MOD = int(os.environ.get("DARTLAB_HORIZON_V231_TEST_MOD", "4"))
HTML_CHAR_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V231_HTML_CHARS", "12000"))
SIB_MIN_MEMBERS = int(os.environ.get("DARTLAB_HORIZON_V231_SIB_MIN_MEMBERS", "3"))
SIB_JACCARD_LO = float(os.environ.get("DARTLAB_HORIZON_V231_SIB_JACCARD_LO", "0.5"))
SLOT_MIN_OWN_DF = float(os.environ.get("DARTLAB_HORIZON_V231_SLOT_MIN_OWN_DF", "0.3"))
SLOT_MAX_SIB_DF = float(os.environ.get("DARTLAB_HORIZON_V231_SLOT_MAX_SIB_DF", "0.1"))

CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
HANGUL_TOK_RE = re.compile(r"[가-힣]{2,10}")
NUMVAL_RE = re.compile(r"^[\s\(\-]*[\d,]+(?:\.\d+)?[\s\)원주%]*$")
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


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def isTestCorp(corp: str) -> bool:
    return (stableHashInt(corp) % TEST_MOD) == 0 if corp else False


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


def cleanCell(s: str) -> str:
    return SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", s))).strip()


def extractSlots(htmlText: str) -> set[str]:
    """표 셀에서 (label, 양수 숫자값) 인접쌍을 찾아 label 의 hangul stem 집합 반환. 공시 자신의 수치 referent."""
    cells = [cleanCell(c) for c in CELL_RE.findall(htmlText)]
    slots: set[str] = set()
    for i, c in enumerate(cells):
        if not c or not HANGUL_RE.search(c):
            continue
        labelToks = HANGUL_TOK_RE.findall(c)
        if not labelToks:
            continue
        # 다음 1~2 셀에서 양수 숫자값?
        for j in (i + 1, i + 2):
            if j >= len(cells):
                break
            v = cells[j].replace(",", "").strip()
            if NUMVAL_RE.match(cells[j]):
                digits = re.sub(r"[^\d.]", "", v)
                if digits and float(digits or 0) > 0:
                    for t in labelToks:
                        slots.add(t)
                break
    return slots


def bodyStems(text: str) -> set[str]:
    return {t for t in HANGUL_TOK_RE.findall(text)}


def classKeyOf(core: frozenset[str]) -> str:
    return "|".join(sorted(core))


def charBigrams(key: str) -> set[str]:
    flat = key.replace("|", "")
    if len(flat) < 2:
        return {flat} if flat else set()
    return {flat[i : i + 2] for i in range(len(flat) - 1)}


@dataclass
class Doc:
    corp: str
    isTest: bool
    core: frozenset[str]
    slots: frozenset[str]
    body: frozenset[str]


def loadDocs() -> list[Doc]:
    files = sorted(ALL_FILINGS_DIR.glob("*.parquet"))[:FILE_LIMIT]
    docs: list[Doc] = []
    for path in files:
        df = pl.read_parquet(str(path), columns=["corp_code", "report_nm", "content_raw"])
        if df.height > ROWS_PER_FILE:
            df = df.head(ROWS_PER_FILE)
        for r in df.iter_rows(named=True):
            corp = str(r.get("corp_code") or "")
            core = reportNmCore(r.get("report_nm") or "")
            if not core:
                continue
            htmlText = str(r.get("content_raw") or "")[:HTML_CHAR_LIMIT]
            slots = extractSlots(htmlText)
            body = bodyStems(cleanCell(htmlText))
            if len(body) < 12:
                continue
            docs.append(Doc(corp, isTestCorp(corp), frozenset(core), frozenset(slots), frozenset(body)))
        del df
    return docs


def mineSiblings(classMembers: dict[str, list[int]]) -> dict[str, list[str]]:
    classes = sorted(c for c, m in classMembers.items() if len(m) >= SIB_MIN_MEMBERS)
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
            if uni and SIB_JACCARD_LO <= len(ba & bb) / uni < 0.999:
                sib[a].append(b)
                sib[b].append(a)
    return sib


def main() -> None:
    import time

    t0 = time.time()
    docs = loadDocs()
    train = [d for d in docs if not d.isTest]
    test = [d for d in docs if d.isTest]
    if not train or not test:
        print(f"insufficient: train={len(train)} test={len(test)}")
        return

    # test class membership
    posClass: dict[int, str] = {}
    classMembers: dict[str, list[int]] = defaultdict(list)
    for i, d in enumerate(test):
        posClass[i] = classKeyOf(d.core)
        classMembers[classKeyOf(d.core)].append(i)
    siblings = mineSiblings(classMembers)

    # train: class 별 slot DF (분할표)
    trainByClass: dict[str, list[int]] = defaultdict(list)
    for ti, d in enumerate(train):
        trainByClass[classKeyOf(d.core)].append(ti)

    def discriminativeSlots(cls: str, sibs: list[str]) -> set[str]:
        own = trainByClass.get(cls, ())
        if not own:
            return set()
        ownDf: Counter = Counter()
        for ti in own:
            for s in train[ti].slots:
                ownDf[s] += 1
        sibDocs = [ti for s in sibs for ti in trainByClass.get(s, ())]
        sibDf: Counter = Counter()
        for ti in sibDocs:
            for s in train[ti].slots:
                sibDf[s] += 1
        nOwn = len(own)
        nSib = max(1, len(sibDocs))
        out = set()
        for s, c in ownDf.items():
            if c / nOwn >= SLOT_MIN_OWN_DF and sibDf.get(s, 0) / nSib <= SLOT_MAX_SIB_DF:
                out.add(s)
        return out

    # antonym-null: slot referent vs body-overlap baseline
    slotOwn = 0
    baseOwn = 0
    n = 0
    chanceSum = 0.0
    slotHasDisc = 0
    avgDiscSlots = 0
    for qi, d in enumerate(test):
        cls = posClass[qi]
        sibs = siblings.get(cls)
        if not sibs:
            continue
        ownM = set(classMembers.get(cls, ())) - {qi}
        sibM = {m for s in sibs for m in classMembers.get(s, ())} - ownM - {qi}
        if not ownM or not sibM:
            continue
        disc = discriminativeSlots(cls, sibs)
        pool = list(ownM | sibM)
        n += 1
        chanceSum += len(ownM) / len(pool)
        if disc:
            slotHasDisc += 1
            avgDiscSlots += len(disc)

        # slot referent: candidate 가 own 고유 슬롯을 몇 개 보유
        slotScore = {c: len(test[c].slots & disc) for c in pool}
        rankSlot = sorted(pool, key=lambda c: (-slotScore.get(c, 0), c))
        if rankSlot[0] in ownM:
            slotOwn += 1

        # 분포 baseline: query body 와 candidate body overlap
        qb = d.body
        baseScore = {c: len(test[c].body & qb) for c in pool}
        rankBase = sorted(pool, key=lambda c: (-baseScore.get(c, 0), c))
        if rankBase[0] in ownM:
            baseOwn += 1

    if n == 0:
        print("no event-sibling eval queries")
        return
    chance = chanceSum / n
    print("=" * 76)
    print(f"V231 event-domain referential 결합축 (공시 표 수치 슬롯)  ({time.time() - t0:.1f}s)")
    print(f"files={FILE_LIMIT} docs={len(docs)} train={len(train)} test={len(test)}")
    print(
        f"siblingEvalN={n} chance={chance:.4f} discSlotCoverage={slotHasDisc / n:.3f} "
        f"avgDiscSlots={(avgDiscSlots / slotHasDisc) if slotHasDisc else 0:.1f}"
    )
    print("-" * 76)
    print(f"분포 baseline(body overlap) own1 = {baseOwn / n:.4f}  margin={baseOwn / n - chance:+.4f}")
    print(f"slot referent(공시 수치 슬롯)  own1 = {slotOwn / n:.4f}  margin={slotOwn / n - chance:+.4f}")
    print("-" * 76)
    slotMargin = slotOwn / n - chance
    baseMargin = baseOwn / n - chance
    win = slotMargin > 0.03 and slotMargin > baseMargin + 0.02
    if win:
        v = "성공: 공시 표 수치 슬롯이 event antonym 을 분포 대비 유의하게 가름 = event-domain 결합축 referent 입증."
    elif slotHasDisc / n < 0.2:
        v = "미결: 변별 슬롯 coverage 낮음(표 파싱/슬롯 채굴 약). 추출기 개선 필요."
    else:
        v = "실패/부분: slot referent 가 분포 대비 유의 우위 없음. 슬롯 신호가 약하거나 noisy."
    print(f"VERDICT: {v}")
    print("=" * 76)


if __name__ == "__main__":
    main()
