"""Horizon Meaning Learner V190 - canonical token typed sibling proof.

아이디어:
    V189 의 local deletion sibling 은 term 표면이 너무 넓어 문자 유사 충돌이 의미 충돌보다 많았다. V190 은 sibling 을
    한국어 term 자체에서 직접 만들지 않고, train alias 가 연결된 canonical snakeId 의 token 경험으로 한 단계 올린다.

    절차:
    - candidate snakeId 를 canonical token sequence 로 분해한다. 예: cash_inflows_from_other_investing_activities 는
      cash/inflow/other/investing/activity token 경험이 된다.
    - train alias 의 2~5 gram surface term 이 어떤 canonical token 들을 예측하는지 term->token proof 를 학습한다.
      held-out alias 는 train entry 에서 제거되어 query surface leak 이 없다.
    - canonical token sequence 에서 같은 context 를 공유하는 token 대체항을 자동 sibling 으로 학습한다. 예를 들어
      cash_*_from_other_investing_activity 문맥에서는 inflow/outflow 가 손으로 적지 않아도 갈라진다.
    - scoring 은 V188 counterPath 위에 typedSiblingDelta 를 더한다. query 가 예측한 token 과 candidate token 이 겹치면
      작은 support, query token 의 자동 sibling 을 candidate 가 갖고 있으면 counter proof 로 penalty 를 준다.

    목표는 hand contrast group 을 늘리는 것이 아니라, `유입/유출`, `증가/감소`, `유동/비유동`, broad/current/other
    계열을 canonical object/action token 경험으로 자동 분리해 V188 counterPathWithSj 를 넘는지 확인하는 것이다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV190Test.py
    $env:DARTLAB_HORIZON_V190_HELDOUT_LIMIT='80'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV190Test.py
    $env:DARTLAB_HORIZON_V190_HELDOUT_LIMIT='600'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV190Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV190Test.py

검증 기준:
    - held-out query surface 는 train candidate alias 에 없어야 한다.
    - corpus matcher 도 train alias 만 사용해야 하며 held-out alias 를 문서에서 직접 찾으면 안 된다.
    - 후보는 평가 11개가 아니라 accountMappings 의 수천 canonical snakeId 여야 한다.
    - baseline, V186 alias path, V187 corpus path, V188 counter path, V190 typed sibling path 를 같은 split 에서 비교한다.
    - V190 typedSiblingPathWithSj 가 V188 counterPathWithSj 의 320/497 MRR 을 넘고 Top1 을 떨어뜨리지 않으면 성공이다.

결과:
    실행 후 기록한다.

결론:
    실행 후 기록한다.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"
DOCS_DIR = ROOT / "data" / "dart" / "docs"
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"

HELDOUT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_HELDOUT_LIMIT", "320"))
MIN_CLUSTER_SIZE = int(os.environ.get("DARTLAB_HORIZON_V190_MIN_CLUSTER_SIZE", "4"))
MAX_TRAIN_ALIASES_PER_SNAKE = int(os.environ.get("DARTLAB_HORIZON_V190_MAX_TRAIN_ALIASES_PER_SNAKE", "80"))
POOL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_POOL_LIMIT", "5200"))
POSTING_ROW_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_POSTING_ROW_LIMIT", "2600"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V190_TOP_K", "10"))
NUM_MH = int(os.environ.get("DARTLAB_HORIZON_V190_NUM_MH", "32"))
PATH_ATOM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_PATH_ATOM_LIMIT", "96"))
PATH_RESIDUAL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_PATH_RESIDUAL_LIMIT", "64"))
CORPUS_DOC_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_DOC_FILE_LIMIT", "18"))
CORPUS_ALL_FILINGS_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_ALL_FILINGS_FILE_LIMIT", "6"))
CORPUS_ROW_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_ROW_LIMIT", "18000"))
CORPUS_TEXT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_TEXT_LIMIT", "3600"))
CORPUS_GRAM_POSTING_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_GRAM_POSTING_LIMIT", "160"))
CORPUS_ALIAS_MATCH_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_ALIAS_MATCH_LIMIT", "90000"))
CORPUS_PROFILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_PROFILE_LIMIT", "96"))
CORPUS_RESIDUAL_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_RESIDUAL_LIMIT", "64"))
CORPUS_FRAGMENT_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_CORPUS_FRAGMENT_LIMIT", "64"))
COUNTER_SCALE = float(os.environ.get("DARTLAB_HORIZON_V190_COUNTER_SCALE", "0.50"))
TYPED_SIBLING_SCALE = float(os.environ.get("DARTLAB_HORIZON_V190_TYPED_SIBLING_SCALE", "0.55"))
TYPED_SUPPORT_SCALE = float(os.environ.get("DARTLAB_HORIZON_V190_TYPED_SUPPORT_SCALE", "0.30"))
TYPED_TERM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V190_TYPED_TERM_LIMIT", "80"))

HANGUL_START = 0xAC00
HANGUL_END = 0xD7A3
JAMO_BASE = 0xAC00
SPACE_RE = re.compile(r"\s+")
TAG_RE = re.compile(r"<[^>]+>")
NUM_RE = re.compile(r"\d")
CORPUS_FRAGMENT_ATOMS: dict[str, Counter[str]] = {}
CANON_TOKEN_ALTERNATIVES: dict[str, frozenset[str]] = {}
CANON_TOKEN_IDF: dict[str, float] = {}
SURFACE_TOKEN_HINTS: dict[str, Counter[str]] = {}

SLOT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flow:in", ("유입", "수입", "입금", "수취", "회수")),
    ("flow:out", ("유출", "지출", "지급", "상환", "납부")),
    ("delta:increase", ("증가", "증대", "증액", "확대")),
    ("delta:decrease", ("감소", "감액", "축소", "차감")),
    ("delta:net", ("증감", "변동", "순증감", "순증가", "순감소")),
    ("transaction:acquire", ("취득", "매입", "인수", "매수")),
    ("transaction:dispose", ("처분", "매각", "양도", "제거")),
    ("transaction:issue", ("발행", "유상증자", "신주")),
    ("transaction:redeem", ("상환", "소각", "감자")),
    ("valuation:gain", ("이익", "수익", "환입", "차익")),
    ("valuation:loss", ("손실", "비용", "손상", "상각", "차손")),
    ("statement:cashflow", ("현금흐름", "현금유입", "현금유출", "영업활동", "투자활동", "재무활동")),
    ("statement:balance", ("자산", "부채", "자본", "채권", "채무", "재고", "유형", "무형")),
    ("statement:income", ("매출", "수익", "비용", "손익", "이익", "원가", "판관")),
    ("cf:operating", ("영업활동",)),
    ("cf:investing", ("투자활동",)),
    ("cf:financing", ("재무활동",)),
    ("object:cash", ("현금", "예금")),
    ("object:receivable", ("채권", "매출채권", "미수", "수취")),
    ("object:payable", ("채무", "매입채무", "미지급")),
    ("object:debt", ("차입", "사채", "채무증권", "전환사채", "신종자본증권")),
    ("object:lease", ("리스",)),
    ("object:derivative", ("파생",)),
    ("object:equity", ("자본", "지분", "주식", "주주", "신주", "자기주")),
    ("object:subsidiary", ("종속기업", "종속회사", "연결범위")),
    ("object:associate", ("관계기업", "공동기업")),
    ("object:financialAsset", ("금융자산", "상각후원가", "공정가치", "매도가능")),
    ("object:provision", ("충당", "충당부채")),
    ("object:tax", ("법인세", "세금")),
    ("object:inventory", ("재고", "제품", "상품", "완성")),
    ("object:tangible", ("유형자산", "설비", "건물", "토지")),
    ("object:intangible", ("무형자산", "영업권", "개발비", "라이선스")),
)

EXCLUSIVE_SLOT_GROUPS: tuple[tuple[str, ...], ...] = (
    ("flow:in", "flow:out"),
    ("delta:increase", "delta:decrease"),
    ("transaction:acquire", "transaction:dispose"),
    ("transaction:issue", "transaction:redeem"),
    ("valuation:gain", "valuation:loss"),
    ("cf:operating", "cf:investing", "cf:financing"),
)

CONTRAST_TERM_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flowYuip", ("유입", "유출")),
    ("flowIncome", ("수입", "지출")),
    ("flowCash", ("입금", "출금")),
    ("flowReceivePay", ("수취", "지급")),
    ("delta", ("순증가", "순감소", "증가", "감소")),
    ("dealAcquireDispose", ("취득", "처분")),
    ("dealBuySell", ("매입", "매각")),
    ("dealTakeTransfer", ("인수", "양도")),
    ("issueRedeem", ("발행", "상환", "소각", "감자")),
    ("valuationGainLoss", ("이익", "손실")),
    ("valuationRevenueCost", ("수익", "비용")),
    ("valuationReversalAmort", ("환입", "상각")),
    ("maturityTerm", ("단기", "장기")),
    ("maturityCurrent", ("유동", "비유동")),
    ("completion", ("미완성", "완성")),
    ("cfLane", ("영업활동", "투자활동", "재무활동")),
)

REQUIRED_MODIFIER_TERMS: tuple[str, ...] = (
    "기타",
    "비유동",
    "유동",
    "단기",
    "장기",
    "상각후원가",
    "공정가치",
    "투자활동",
    "재무활동",
    "영업활동",
    "신주인수권",
    "초과금",
    "미완성",
)

SLOT_TO_CONTRAST_GROUP: dict[str, str] = {
    "flow:in": "flow",
    "flow:out": "flow",
    "delta:increase": "delta",
    "delta:decrease": "delta",
    "delta:net": "delta",
    "transaction:acquire": "transaction",
    "transaction:dispose": "transaction",
    "transaction:issue": "issueRedeem",
    "transaction:redeem": "issueRedeem",
    "valuation:gain": "valuation",
    "valuation:loss": "valuation",
    "cf:operating": "cfLane",
    "cf:investing": "cfLane",
    "cf:financing": "cfLane",
}


@dataclass(frozen=True)
class AliasEntry:
    alias: str
    snake: str
    sj: str
    clusterSize: int
    regions: tuple[int, int, int, int]
    mh: tuple[int, ...]
    bigrams: frozenset[str]
    trigrams: frozenset[str]
    chars: frozenset[str]
    surfaceTerms: frozenset[str]
    canonTokens: tuple[str, ...]
    slots: Counter[str]
    coreSlots: frozenset[str]
    pathAtoms: Counter[str]


@dataclass(frozen=True)
class HeldoutCase:
    alias: str
    snake: str
    sj: str
    trainSize: int
    clusterSize: int


@dataclass(frozen=True)
class SnakeProfile:
    snake: str
    sj: str
    slots: Counter[str]
    coreSlots: frozenset[str]
    pathAtoms: Counter[str]
    residualAtoms: Counter[str]
    corpusAtoms: Counter[str]
    corpusResidualAtoms: Counter[str]
    termHints: frozenset[str]
    canonTokens: Counter[str]
    aliasCount: int


@dataclass(frozen=True)
class CorpusStats:
    docFiles: int
    allFilingsFiles: int
    rowsScanned: int
    aliasMatches: int
    snakesWithCorpus: int
    corpusAtomKeys: int
    typedTerms: int = 0
    typedAltLinks: int = 0


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def hasHangul(value: str) -> bool:
    return any(HANGUL_START <= ord(ch) <= HANGUL_END for ch in value)


def cleanSurface(value: object) -> str:
    text = "" if value is None else str(value)
    text = SPACE_RE.sub("", text)
    out = []
    for ch in text:
        code = ord(ch)
        if HANGUL_START <= code <= HANGUL_END or ch.isascii() and ch.isalnum():
            out.append(ch)
    return "".join(out)


def usefulAlias(value: str) -> bool:
    if not value or not hasHangul(value):
        return False
    if len(value) < 3 or len(value) > 48:
        return False
    if sum(1 for ch in value if HANGUL_START <= ord(ch) <= HANGUL_END) < 2:
        return False
    return True


def ngrams(value: str, n: int) -> frozenset[str]:
    if len(value) < n:
        return frozenset({value}) if value else frozenset()
    return frozenset(value[index : index + n] for index in range(len(value) - n + 1))


def structuralSlots(value: str, sj: str = "") -> Counter[str]:
    slots: Counter[str] = Counter()
    for slot, terms in SLOT_RULES:
        for term in terms:
            if term in value:
                slots[slot] += 1
                slots[f"term:{term}"] += 1
    if sj:
        slots[f"sj:{sj}"] += 2
    if "현금" in value and ("유입" in value or "유출" in value or "흐름" in value):
        slots["statement:cashflow"] += 2
    if ("증가" in value or "감소" in value or "증감" in value) and ("현금" in value or "흐름" in value):
        slots["statement:cashflow"] += 1
    if "순" in value and ("증가" in value or "감소" in value or "증감" in value):
        slots["delta:net"] += 1
    return slots


def coreSlotKeys(slots: Counter[str]) -> frozenset[str]:
    return frozenset(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))


def longestTermHits(value: str, terms: tuple[str, ...]) -> frozenset[str]:
    text = cleanSurface(value)
    hits: list[str] = []
    for term in sorted(terms, key=len, reverse=True):
        if term not in text:
            continue
        if any(term != other and term in other for other in hits):
            continue
        hits.append(term)
    return frozenset(hits)


def contrastTermHits(value: str) -> dict[str, frozenset[str]]:
    hits: dict[str, frozenset[str]] = {}
    for group, terms in CONTRAST_TERM_GROUPS:
        groupHits = longestTermHits(value, terms)
        if groupHits:
            hits[group] = groupHits
    return hits


def requiredModifierTerms(value: str) -> frozenset[str]:
    return longestTermHits(value, REQUIRED_MODIFIER_TERMS)


def counterVocabulary() -> frozenset[str]:
    terms: set[str] = set(REQUIRED_MODIFIER_TERMS)
    for _group, groupTerms in CONTRAST_TERM_GROUPS:
        terms.update(groupTerms)
    return frozenset(terms)


def surfaceHasTerm(value: str, term: str) -> bool:
    text = cleanSurface(value)
    if term == "완성":
        return "완성" in text and "미완성" not in text
    if term == "유동":
        return "유동" in text and "비유동" not in text
    return term in text


def profileHasTerm(term: str, entry: AliasEntry, profile: SnakeProfile | None) -> bool:
    if surfaceHasTerm(entry.alias, term):
        return True
    return profile is not None and term in profile.termHints


def buildTermHints(*atomSets: Counter[str]) -> frozenset[str]:
    hints: set[str] = set()
    terms = counterVocabulary()
    for atomSet in atomSets:
        for atom in atomSet:
            for term in terms:
                if surfaceHasTerm(atom, term):
                    hints.add(term)
    return frozenset(hints)


def textTermHints(value: str) -> frozenset[str]:
    hints: set[str] = set(requiredModifierTerms(value))
    for terms in contrastTermHits(value).values():
        hints.update(terms)
    return frozenset(hints)


CANON_STOP_TOKENS = frozenset(
    {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)


def normalizeCanonToken(token: str) -> str:
    token = token.lower().strip("_")
    if not token or token in CANON_STOP_TOKENS:
        return ""
    token = token.replace("amortised", "amortized").replace("recognised", "recognized")
    token = token.replace("authorised", "authorized").replace("capitalised", "capitalized")
    if token.endswith("ies") and len(token) > 5:
        return token[:-3] + "y"
    if token.endswith("ves") and len(token) > 5:
        return token[:-3] + "f"
    if token.endswith("s") and not token.endswith("ss") and len(token) > 4:
        return token[:-1]
    return token


def canonicalTokensForSnake(snake: str) -> tuple[str, ...]:
    raw = [part for part in re.split(r"_+", snake) if part]
    tokens: list[str] = []
    for part in raw:
        normalized = normalizeCanonToken(part)
        if not normalized:
            continue
        tokens.append(normalized)
        if normalized == "decreaseincrease":
            tokens.extend(("decrease", "increase"))
        elif normalized == "increaseincrease":
            tokens.append("increase")
        elif normalized == "decreasedecrease":
            tokens.append("decrease")
    return tuple(dict.fromkeys(tokens))


def typedSurfaceTerms(value: str) -> frozenset[str]:
    text = cleanSurface(value)
    terms: set[str] = set()
    for size in (2, 3, 4, 5):
        if len(text) < size:
            continue
        for index in range(len(text) - size + 1):
            term = text[index : index + size]
            if NUM_RE.search(term):
                continue
            if all(HANGUL_START <= ord(ch) <= HANGUL_END for ch in term):
                terms.add(term)
    for size in (2, 3, 4, 5, 6):
        if len(text) >= size:
            prefix = text[:size]
            suffix = text[-size:]
            if hasHangul(prefix) and not NUM_RE.search(prefix):
                terms.add(prefix)
            if hasHangul(suffix) and not NUM_RE.search(suffix):
                terms.add(suffix)
    return frozenset(terms)


def buildCanonicalTokenAlternatives(tokensBySnake: dict[str, tuple[str, ...]]) -> dict[str, frozenset[str]]:
    contextTerms: dict[tuple[str, ...], set[str]] = defaultdict(set)
    localTerms: dict[tuple[str, str], set[str]] = defaultdict(set)
    for tokens in tokensBySnake.values():
        if len(tokens) < 2:
            continue
        for index, token in enumerate(tokens):
            context = tuple(tokens[:index] + tokens[index + 1 :])
            if context:
                contextTerms[context].add(token)
            left = tokens[index - 1] if index > 0 else ""
            right = tokens[index + 1] if index + 1 < len(tokens) else ""
            if left or right:
                localTerms[(left, right)].add(token)

    alternatives: dict[str, set[str]] = defaultdict(set)
    for groups in (contextTerms, localTerms):
        for _context, terms in groups.items():
            if len(terms) < 2 or len(terms) > 8:
                continue
            sortedTerms = sorted(terms)
            for leftIndex, left in enumerate(sortedTerms):
                for right in sortedTerms[leftIndex + 1 :]:
                    alternatives[left].add(right)
                    alternatives[right].add(left)
    return {term: frozenset(sorted(values)) for term, values in alternatives.items() if values}


def buildTypedTokenProof(entries: list[AliasEntry]) -> tuple[dict[str, Counter[str]], int, int]:
    global CANON_TOKEN_ALTERNATIVES, CANON_TOKEN_IDF, SURFACE_TOKEN_HINTS

    tokensBySnake: dict[str, tuple[str, ...]] = {}
    for entry in entries:
        if entry.snake not in tokensBySnake:
            tokensBySnake[entry.snake] = tuple(entry.canonTokens)
    CANON_TOKEN_ALTERNATIVES = buildCanonicalTokenAlternatives(tokensBySnake)

    tokenSnakeDf: Counter[str] = Counter()
    for tokens in tokensBySnake.values():
        for token in set(tokens):
            tokenSnakeDf[token] += 1
    totalSnakes = max(1, len(tokensBySnake))
    CANON_TOKEN_IDF = {token: math.log((totalSnakes + 1.0) / (df + 0.5)) for token, df in tokenSnakeDf.items()}

    termTokenCounts: dict[str, Counter[str]] = defaultdict(Counter)
    termSnakeDf: dict[str, set[str]] = defaultdict(set)
    profileTokens: dict[str, Counter[str]] = defaultdict(Counter)
    for entry in entries:
        for token in entry.canonTokens:
            profileTokens[entry.snake][token] += max(0.0, CANON_TOKEN_IDF.get(token, 0.0))
        for term in entry.surfaceTerms:
            termSnakeDf[term].add(entry.snake)
            for token in entry.canonTokens:
                termTokenCounts[term][token] += 1

    hints: dict[str, Counter[str]] = {}
    for term, counts in termTokenCounts.items():
        df = len(termSnakeDf.get(term, ()))
        if df < 2:
            continue
        weighted = Counter()
        for token, count in counts.items():
            tokenIdf = CANON_TOKEN_IDF.get(token, 0.0)
            if tokenIdf < 0.45:
                continue
            support = float(count) / max(1.0, float(df))
            score = support * tokenIdf
            if score >= 0.24:
                weighted[token] = score
        if weighted:
            hints[term] = Counter(dict(weighted.most_common(10)))
    SURFACE_TOKEN_HINTS = hints

    return (
        {snake: Counter(dict(tokens.most_common(TYPED_TERM_LIMIT))) for snake, tokens in profileTokens.items()},
        len(hints),
        sum(len(values) for values in CANON_TOKEN_ALTERNATIVES.values()),
    )


def queryTokenProof(query: str) -> Counter[str]:
    proof = Counter()
    for term in typedSurfaceTerms(query):
        for token, score in SURFACE_TOKEN_HINTS.get(term, {}).items():
            proof[token] += float(score)
    if not proof:
        return Counter()
    return Counter(dict(proof.most_common(16)))


def corpusSlotWeight(profile: SnakeProfile | None, slot: str) -> float:
    if profile is None:
        return 0.0
    atom = f"corp:slot:{slot}"
    return float(profile.corpusAtoms.get(atom, 0.0)) + float(profile.corpusResidualAtoms.get(atom, 0.0)) * 1.6


def corpusStmtWeight(profile: SnakeProfile | None, stmt: str) -> float:
    if profile is None:
        return 0.0
    atom = f"corp:stmt:{stmt}"
    return float(profile.corpusAtoms.get(atom, 0.0)) + float(profile.corpusResidualAtoms.get(atom, 0.0)) * 1.6


def boundaryAtoms(value: str) -> tuple[str, ...]:
    atoms: list[str] = []
    grams2 = sorted(ngrams(value, 2))
    grams3 = sorted(ngrams(value, 3))
    grams4 = sorted(ngrams(value, 4))
    for gram in grams2:
        atoms.append(f"g2:{gram}")
    for gram in grams3:
        atoms.append(f"g3:{gram}")
    for gram in grams4[:24]:
        atoms.append(f"g4:{gram}")
    for size in (2, 3, 4, 5):
        if len(value) >= size:
            atoms.append(f"pre{size}:{value[:size]}")
            atoms.append(f"suf{size}:{value[-size:]}")
    for index in range(2, min(len(value), 13)):
        left = value[:index]
        right = value[index:]
        if 2 <= len(left) <= 8 and 2 <= len(right) <= 10:
            atoms.append(f"cut:{left}>{right}")
    return tuple(atoms)


def pathAtomsForAlias(value: str, sj: str = "") -> Counter[str]:
    slots = structuralSlots(value, sj)
    atoms: Counter[str] = Counter()
    for atom in boundaryAtoms(value):
        atoms[atom] += 1.0
    slotKeys = sorted(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))
    termKeys = sorted(slot for slot in slots if slot.startswith("term:"))
    for slot in slotKeys:
        atoms[f"slot:{slot}"] += 2.0
    for term in termKeys:
        atoms[f"termPath:{term[5:]}"] += 1.0
    grams3 = tuple(sorted(ngrams(value, 3)))[:28]
    for slot in slotKeys[:10]:
        for gram in grams3:
            atoms[f"slotGram:{slot}|{gram}"] += 0.85
    for leftIndex, left in enumerate(slotKeys):
        for right in slotKeys[leftIndex + 1 :]:
            atoms[f"slotPair:{left}|{right}"] += 1.5
    for size in (2, 3, 4):
        if len(value) >= size:
            prefix = value[:size]
            suffix = value[-size:]
            for slot in slotKeys[:10]:
                atoms[f"preSlot:{prefix}|{slot}"] += 1.1
                atoms[f"sufSlot:{suffix}|{slot}"] += 1.1
    if sj:
        for slot in slotKeys[:10]:
            atoms[f"sjSlot:{sj}|{slot}"] += 1.2
    return Counter(dict(atoms.most_common(PATH_ATOM_LIMIT)))


def statementRole(value: str, sj: str = "") -> str:
    text = value or ""
    if sj in {"BS", "IS", "CF", "SCE"}:
        return sj
    if "현금흐름" in text or "영업활동" in text or "투자활동" in text or "재무활동" in text:
        return "CF"
    if "손익" in text or "포괄손익" in text or "매출" in text:
        return "IS"
    if "재무상태" in text or "자산" in text or "부채" in text or "자본" in text:
        return "BS"
    return sj or ""


def corpusSelectorGrams(value: str) -> frozenset[str]:
    if len(value) >= 3:
        return ngrams(value, 3)
    return ngrams(value, 2)


def corpusProjectionAtoms(value: str, sj: str = "") -> Counter[str]:
    slots = structuralSlots(value, sj)
    slotKeys = sorted(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))
    atoms: Counter[str] = Counter()
    for slot in slotKeys:
        atoms[f"corp:slot:{slot}"] += 2.0
    for leftIndex, left in enumerate(slotKeys):
        for right in slotKeys[leftIndex + 1 :]:
            atoms[f"corp:slotPair:{left}|{right}"] += 1.7
    role = statementRole(value, sj)
    if role:
        atoms[f"corp:stmt:{role}"] += 1.4
        for slot in slotKeys[:10]:
            atoms[f"corp:sjSlot:{role}|{slot}"] += 1.8
    return Counter(dict(atoms.most_common(CORPUS_PROFILE_LIMIT)))


def cleanedText(value: object, *, limit: int = CORPUS_TEXT_LIMIT) -> str:
    raw = "" if value is None else str(value)
    raw = html.unescape(raw[:limit])
    raw = TAG_RE.sub(" ", raw)
    return cleanSurface(raw)


def selectedParquetFiles(root: Path, limit: int) -> tuple[Path, ...]:
    if limit <= 0 or not root.exists():
        return ()
    files = [path for path in root.glob("*.parquet") if not path.name.endswith("_meta.parquet")]
    files.sort(key=lambda path: (stableHashInt(path.name), path.name))
    return tuple(files[:limit])


def buildCorpusAliasPostings(entries: list[AliasEntry]) -> dict[str, tuple[int, ...]]:
    postings: dict[str, list[int]] = defaultdict(list)
    for index, entry in enumerate(entries):
        for gram in corpusSelectorGrams(entry.alias):
            postings[gram].append(index)
    return {gram: tuple(indexes) for gram, indexes in postings.items() if len(indexes) <= CORPUS_GRAM_POSTING_LIMIT}


def corpusAtomsForOccurrence(
    alias: str,
    sj: str,
    cleanTextValue: str,
    rawText: str,
    title: str,
    report: str,
    source: str,
) -> Counter[str]:
    position = cleanTextValue.find(alias)
    left = cleanTextValue[max(0, position - 16) : position] if position >= 0 else ""
    rightStart = position + len(alias) if position >= 0 else 0
    right = cleanTextValue[rightStart : rightStart + 16]
    window = f"{left}{alias}{right}{cleanSurface(title)}{cleanSurface(report)}"
    atoms = corpusProjectionAtoms(window, sj)
    role = statementRole(f"{title}{report}{window}", sj)
    atoms[f"corp:source:{source}"] += 0.8
    if role:
        atoms[f"corp:stmt:{role}"] += 1.6
    titleKey = cleanSurface(title)[:18]
    reportKey = cleanSurface(report)[:18]
    if titleKey:
        atoms[f"corp:title:{titleKey}"] += 0.9
    if reportKey:
        atoms[f"corp:report:{reportKey}"] += 0.8
    if left:
        atoms[f"corp:left:{left[-4:]}"] += 0.75
    if right:
        atoms[f"corp:right:{right[:4]}"] += 0.75
    if NUM_RE.search(rawText):
        atoms["corp:valueNear"] += 0.9
    return Counter(dict(atoms.most_common(CORPUS_PROFILE_LIMIT)))


def corpusContextAtoms(cleanTextValue: str, rawText: str, title: str, report: str, source: str) -> Counter[str]:
    context = f"{cleanTextValue}{cleanSurface(title)}{cleanSurface(report)}"
    slots = structuralSlots(context)
    slotKeys = sorted(slot for slot in slots if not slot.startswith("term:") and not slot.startswith("sj:"))
    atoms: Counter[str] = Counter()
    role = statementRole(context)
    if role:
        atoms[f"corp:stmt:{role}"] += 1.5
    for slot in slotKeys:
        atoms[f"corp:slot:{slot}"] += 1.5
    for leftIndex, left in enumerate(slotKeys):
        for right in slotKeys[leftIndex + 1 :]:
            atoms[f"corp:slotPair:{left}|{right}"] += 1.2
    atoms[f"corp:source:{source}"] += 0.6
    titleKey = cleanSurface(title)[:18]
    reportKey = cleanSurface(report)[:18]
    if titleKey:
        atoms[f"corp:title:{titleKey}"] += 0.5
    if reportKey:
        atoms[f"corp:report:{reportKey}"] += 0.45
    if NUM_RE.search(rawText):
        atoms["corp:valueNear"] += 0.8
    return Counter(dict(atoms.most_common(CORPUS_FRAGMENT_LIMIT)))


def corpusAtomsFromFragments(value: str, sj: str, fragmentAtoms: dict[str, Counter[str]]) -> Counter[str]:
    atoms = corpusProjectionAtoms(value, sj)
    for gram in corpusSelectorGrams(value):
        for atom, weight in fragmentAtoms.get(gram, {}).items():
            if not atom.startswith(("corp:stmt:", "corp:slot:", "corp:slotPair:", "corp:valueNear")):
                continue
            atoms[atom] += min(3.0, math.log1p(float(weight))) * 0.55
    return Counter(dict(atoms.most_common(CORPUS_PROFILE_LIMIT)))


def scanCorpusRows(
    files: tuple[Path, ...],
    source: str,
    entries: list[AliasEntry],
    aliasPostings: dict[str, tuple[int, ...]],
    profileAtoms: dict[str, Counter[str]],
    fragmentAtoms: dict[str, Counter[str]],
    rowsLeft: int,
    matchesLeft: int,
) -> tuple[int, int, int]:
    rowsScanned = 0
    aliasMatches = 0
    filesUsed = 0
    for path in files:
        if rowsLeft <= 0 or matchesLeft <= 0:
            break
        schema = pl.scan_parquet(path).collect_schema()
        names = set(schema.names())
        if source == "docs":
            wanted = ["section_title", "assocnote", "report_type", "section_content_mixed"]
            textCol = "section_content_mixed"
            titleCol = "section_title"
            reportCol = "report_type"
        else:
            wanted = ["report_nm", "flr_nm", "content_raw"]
            textCol = "content_raw"
            titleCol = "report_nm"
            reportCol = "flr_nm"
        present = [col for col in wanted if col in names]
        if textCol not in present:
            continue
        exprs = []
        for col in present:
            expr = pl.col(col).cast(pl.Utf8).fill_null("")
            if col == textCol:
                expr = expr.str.slice(0, CORPUS_TEXT_LIMIT)
            exprs.append(expr.alias(col))
        try:
            frame = pl.scan_parquet(path).select(exprs).head(rowsLeft).collect(engine="streaming")
        except TypeError:
            frame = pl.scan_parquet(path).select(exprs).head(rowsLeft).collect()
        filesUsed += 1
        for row in frame.iter_rows(named=True):
            if rowsLeft <= 0 or matchesLeft <= 0:
                break
            rawText = " ".join(str(row.get(col, "")) for col in present)
            clean = cleanedText(rawText, limit=CORPUS_TEXT_LIMIT * 2)
            rowsLeft -= 1
            rowsScanned += 1
            if len(clean) < 5:
                continue
            rowGrams = corpusSelectorGrams(clean)
            contextAtoms = corpusContextAtoms(
                clean, rawText, str(row.get(titleCol, "")), str(row.get(reportCol, "")), source
            )
            for gram in rowGrams:
                if gram not in aliasPostings:
                    continue
                for atom, value in contextAtoms.items():
                    fragmentAtoms[gram][atom] += value
            candidateIndexes: set[int] = set()
            for gram in rowGrams:
                candidateIndexes.update(aliasPostings.get(gram, ()))
            if not candidateIndexes:
                continue
            title = str(row.get(titleCol, ""))
            report = str(row.get(reportCol, ""))
            for index in candidateIndexes:
                entry = entries[index]
                if entry.alias not in clean:
                    continue
                atoms = corpusAtomsForOccurrence(entry.alias, entry.sj, clean, rawText, title, report, source)
                for atom, value in atoms.items():
                    profileAtoms[entry.snake][atom] += value
                aliasMatches += 1
                matchesLeft -= 1
                if matchesLeft <= 0:
                    break
    return filesUsed, rowsScanned, aliasMatches


def buildCorpusProfiles(
    entries: list[AliasEntry],
) -> tuple[dict[str, Counter[str]], dict[str, Counter[str]], CorpusStats]:
    global CORPUS_FRAGMENT_ATOMS
    aliasPostings = buildCorpusAliasPostings(entries)
    profileAtoms: dict[str, Counter[str]] = defaultdict(Counter)
    fragmentAtoms: dict[str, Counter[str]] = defaultdict(Counter)
    docsFiles = selectedParquetFiles(DOCS_DIR, CORPUS_DOC_FILE_LIMIT)
    allFilingsFiles = selectedParquetFiles(ALL_FILINGS_DIR, CORPUS_ALL_FILINGS_FILE_LIMIT)
    docsRowLimit = max(0, int(CORPUS_ROW_LIMIT * 0.72))
    filingsRowLimit = max(0, CORPUS_ROW_LIMIT - docsRowLimit)
    docsMatchLimit = max(0, int(CORPUS_ALIAS_MATCH_LIMIT * 0.72))
    filingsMatchLimit = max(0, CORPUS_ALIAS_MATCH_LIMIT - docsMatchLimit)
    docFilesUsed, docRows, docMatches = scanCorpusRows(
        docsFiles,
        "docs",
        entries,
        aliasPostings,
        profileAtoms,
        fragmentAtoms,
        docsRowLimit,
        docsMatchLimit,
    )
    filingsUsed, filingRows, filingMatches = scanCorpusRows(
        allFilingsFiles,
        "allFilings",
        entries,
        aliasPostings,
        profileAtoms,
        fragmentAtoms,
        filingsRowLimit,
        filingsMatchLimit,
    )
    fragmentAtoms = {
        gram: Counter(dict(atoms.most_common(CORPUS_FRAGMENT_LIMIT))) for gram, atoms in fragmentAtoms.items()
    }
    CORPUS_FRAGMENT_ATOMS = fragmentAtoms
    for entry in entries:
        atoms = corpusAtomsFromFragments(entry.alias, entry.sj, fragmentAtoms)
        for atom, value in atoms.items():
            profileAtoms[entry.snake][atom] += value * 0.42
    atomSnakeDf: Counter[str] = Counter()
    for _snake, atoms in profileAtoms.items():
        for atom in atoms:
            atomSnakeDf[atom] += 1
    totalSnakes = max(1, len(profileAtoms))
    residual: dict[str, Counter[str]] = {}
    for snake, atoms in profileAtoms.items():
        rows = Counter()
        for atom, raw in atoms.items():
            df = atomSnakeDf.get(atom, 1)
            idf = math.log((totalSnakes + 1.0) / (df + 0.5))
            if idf <= 0.18:
                continue
            rows[atom] = math.log1p(float(raw)) * idf
        residual[snake] = Counter(dict(rows.most_common(CORPUS_RESIDUAL_LIMIT)))
        profileAtoms[snake] = Counter(dict(atoms.most_common(CORPUS_PROFILE_LIMIT)))
    stats = CorpusStats(
        docFiles=docFilesUsed,
        allFilingsFiles=filingsUsed,
        rowsScanned=docRows + filingRows,
        aliasMatches=docMatches + filingMatches,
        snakesWithCorpus=len(profileAtoms),
        corpusAtomKeys=len(atomSnakeDf),
    )
    return profileAtoms, residual, stats


def decomposeJamo(ch: str) -> tuple[int, ...]:
    code = ord(ch)
    if not (HANGUL_START <= code <= HANGUL_END):
        return ()
    offset = code - JAMO_BASE
    cho = offset // 588
    jung = (offset % 588) // 28
    jong = offset % 28
    return (cho, jung, jong) if jong else (cho, jung)


def bitIndex(namespace: str, value: object) -> int:
    return int(hashlib.md5(f"{namespace}:{value}".encode("utf-8")).hexdigest()[:8], 16) % 64


def characteristicRegions(value: str) -> tuple[int, int, int, int]:
    r0 = r1 = r2 = r3 = 0
    for ch in value:
        for jamo in decomposeJamo(ch):
            r0 |= 1 << bitIndex("jamo", jamo)
    for ch in value:
        r1 |= 1 << bitIndex("char", ch)
    for gram in ngrams(value, 2):
        r2 |= 1 << bitIndex("bg", gram)
    raw = int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)
    for index in range(8):
        r3 |= 1 << ((raw >> (index * 4)) & 63)
    return r0, r1, r2, r3


def popcount(value: int) -> int:
    return value.bit_count()


def weightedDistance(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> int:
    weights = (1, 2, 2, 0)
    return sum(popcount(left[index] ^ right[index]) * weights[index] for index in range(4))


def minhash(value: str) -> tuple[int, ...]:
    grams = ngrams(value, 2) or frozenset({value})
    rows = [2**32 - 1] * NUM_MH
    for gram in grams:
        for index in range(NUM_MH):
            digest = int(hashlib.md5(f"{index}:{gram}".encode("utf-8")).hexdigest()[:8], 16)
            if digest < rows[index]:
                rows[index] = digest
    return tuple(rows)


def mhSim(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right:
        return 0.0
    return sum(1 for lval, rval in zip(left, right) if lval == rval) / min(len(left), len(right))


def overlap(left: frozenset[str], right: frozenset[str]) -> float:
    denom = min(len(left), len(right))
    if denom <= 0:
        return 0.0
    return len(left & right) / denom


def containMass(query: str, candidate: str) -> float:
    if not query or not candidate:
        return 0.0
    if query in candidate or candidate in query:
        return min(len(query), len(candidate)) / max(len(query), len(candidate))
    return 0.0


def loadClusters() -> tuple[dict[str, list[str]], dict[str, str]]:
    raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    mappings: dict[str, str] = raw.get("mappings", {})
    standard: dict[str, dict] = raw.get("standardAccounts", {})
    aliasToSnakes: dict[str, set[str]] = defaultdict(set)
    for alias, snake in mappings.items():
        clean = cleanSurface(alias)
        if usefulAlias(clean):
            aliasToSnakes[clean].add(str(snake))
    clusters: dict[str, list[str]] = defaultdict(list)
    for alias, snakes in aliasToSnakes.items():
        if len(snakes) != 1:
            continue
        snake = next(iter(snakes))
        clusters[snake].append(alias)
    normalized = {
        snake: sorted(set(aliases), key=lambda item: (stableHashInt(f"{snake}:{item}"), item))
        for snake, aliases in clusters.items()
    }
    sjBySnake = {snake: str(meta.get("sj", "")) for snake, meta in standard.items() if isinstance(meta, dict)}
    return normalized, sjBySnake


def buildSplit() -> tuple[list[HeldoutCase], list[AliasEntry], Counter[str], dict[str, SnakeProfile], CorpusStats]:
    clusters, sjBySnake = loadClusters()
    heldout: list[HeldoutCase] = []
    heldoutAliases: set[str] = set()
    eligible = [
        (snake, aliases)
        for snake, aliases in clusters.items()
        if len(aliases) >= MIN_CLUSTER_SIZE and sjBySnake.get(snake, "")
    ]
    eligible.sort(key=lambda row: stableHashInt(row[0]))
    for snake, aliases in eligible:
        candidates = [alias for alias in aliases if 4 <= len(alias) <= 34]
        if not candidates:
            continue
        alias = sorted(candidates, key=lambda item: stableHashInt(f"heldout:{snake}:{item}"))[0]
        trainSize = len([item for item in aliases if item != alias])
        if trainSize < MIN_CLUSTER_SIZE - 1:
            continue
        heldout.append(
            HeldoutCase(
                alias=alias,
                snake=snake,
                sj=sjBySnake.get(snake, ""),
                trainSize=trainSize,
                clusterSize=len(aliases),
            )
        )
        heldoutAliases.add(alias)
        if len(heldout) >= HELDOUT_LIMIT:
            break

    clusterSizes = Counter({snake: len(aliases) for snake, aliases in clusters.items()})
    entries: list[AliasEntry] = []
    for snake, aliases in clusters.items():
        trainAliases = [alias for alias in aliases if alias not in heldoutAliases]
        trainAliases = sorted(trainAliases, key=lambda item: (stableHashInt(f"train:{snake}:{item}"), item))
        for alias in trainAliases[:MAX_TRAIN_ALIASES_PER_SNAKE]:
            slots = structuralSlots(alias, sjBySnake.get(snake, ""))
            entries.append(
                AliasEntry(
                    alias=alias,
                    snake=snake,
                    sj=sjBySnake.get(snake, ""),
                    clusterSize=clusterSizes[snake],
                    regions=characteristicRegions(alias),
                    mh=minhash(alias),
                    bigrams=ngrams(alias, 2),
                    trigrams=ngrams(alias, 3),
                    chars=frozenset(alias),
                    surfaceTerms=typedSurfaceTerms(alias),
                    canonTokens=canonicalTokensForSnake(snake),
                    slots=slots,
                    coreSlots=coreSlotKeys(slots),
                    pathAtoms=pathAtomsForAlias(alias, sjBySnake.get(snake, "")),
                )
            )
    corpusAtoms, corpusResidualAtoms, corpusStats = buildCorpusProfiles(entries)
    profileCanonTokens, typedTerms, typedAltLinks = buildTypedTokenProof(entries)
    corpusStats = CorpusStats(
        docFiles=corpusStats.docFiles,
        allFilingsFiles=corpusStats.allFilingsFiles,
        rowsScanned=corpusStats.rowsScanned,
        aliasMatches=corpusStats.aliasMatches,
        snakesWithCorpus=corpusStats.snakesWithCorpus,
        corpusAtomKeys=corpusStats.corpusAtomKeys,
        typedTerms=typedTerms,
        typedAltLinks=typedAltLinks,
    )
    profileSlots: dict[str, Counter[str]] = defaultdict(Counter)
    profileAtoms: dict[str, Counter[str]] = defaultdict(Counter)
    profileTermHints: dict[str, set[str]] = defaultdict(set)
    profileCounts: Counter[str] = Counter()
    for entry in entries:
        profileCounts[entry.snake] += 1
        profileTermHints[entry.snake].update(textTermHints(entry.alias))
        for slot, value in entry.slots.items():
            profileSlots[entry.snake][slot] += max(0.0, float(value))
        for atom, value in entry.pathAtoms.items():
            profileAtoms[entry.snake][atom] += max(0.0, float(value))
    atomSnakeDf: Counter[str] = Counter()
    for snake, atoms in profileAtoms.items():
        for atom in atoms:
            atomSnakeDf[atom] += 1
    totalSnakes = max(1, len(profileAtoms))
    residualAtoms: dict[str, Counter[str]] = {}
    for snake, atoms in profileAtoms.items():
        residual: Counter[str] = Counter()
        aliasCount = max(1, profileCounts[snake])
        for atom, raw in atoms.items():
            support = float(raw) / aliasCount
            df = atomSnakeDf.get(atom, 1)
            idf = math.log((totalSnakes + 1.0) / (df + 0.5))
            if idf <= 0.25:
                continue
            residual[atom] = support * idf
        residualAtoms[snake] = Counter(dict(residual.most_common(PATH_RESIDUAL_LIMIT)))
    profiles = {
        snake: SnakeProfile(
            snake=snake,
            sj=sjBySnake.get(snake, ""),
            slots=Counter(dict(slots.most_common(64))),
            coreSlots=coreSlotKeys(slots),
            pathAtoms=Counter(dict(profileAtoms.get(snake, Counter()).most_common(PATH_ATOM_LIMIT))),
            residualAtoms=residualAtoms.get(snake, Counter()),
            corpusAtoms=corpusAtoms.get(snake, Counter()),
            corpusResidualAtoms=corpusResidualAtoms.get(snake, Counter()),
            termHints=frozenset(profileTermHints.get(snake, set())),
            canonTokens=profileCanonTokens.get(snake, Counter()),
            aliasCount=profileCounts[snake],
        )
        for snake, slots in profileSlots.items()
    }
    return heldout, entries, clusterSizes, profiles, corpusStats


def buildPostings(entries: list[AliasEntry]) -> tuple[dict[str, tuple[int, ...]], dict[str, tuple[int, ...]]]:
    bigramRows: dict[str, list[int]] = defaultdict(list)
    charRows: dict[str, list[int]] = defaultdict(list)
    for index, entry in enumerate(entries):
        for gram in entry.bigrams:
            bigramRows[gram].append(index)
        for ch in entry.chars:
            charRows[ch].append(index)
    return (
        {key: tuple(rows[:POSTING_ROW_LIMIT]) for key, rows in bigramRows.items()},
        {key: tuple(rows[:POSTING_ROW_LIMIT]) for key, rows in charRows.items()},
    )


def sjCompatible(querySj: str, candidateSj: str) -> bool:
    if not querySj or querySj == "COMMON":
        return True
    return candidateSj in {"", "COMMON", querySj}


def candidatePool(
    query: str,
    querySj: str,
    entries: list[AliasEntry],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
) -> Counter[int]:
    votes: Counter[int] = Counter()
    for gram in ngrams(query, 2):
        for index in bigramPostings.get(gram, ()):
            if not withSj or sjCompatible(querySj, entries[index].sj):
                votes[index] += 4
    for ch in query:
        for index in charPostings.get(ch, ()):
            if not withSj or sjCompatible(querySj, entries[index].sj):
                votes[index] += 1
    if len(votes) < 20:
        for index, entry in enumerate(entries):
            if not withSj or sjCompatible(querySj, entry.sj):
                votes[index] += 0
    return Counter(dict(votes.most_common(POOL_LIMIT)))


def entryScore(
    query: str,
    qRegions: tuple[int, int, int, int],
    qMh: tuple[int, ...],
    qBigrams: frozenset[str],
    qTrigrams: frozenset[str],
    entry: AliasEntry,
    vote: float,
) -> float:
    hamming = weightedDistance(qRegions, entry.regions)
    mhBonus = mhSim(qMh, entry.mh) * 46.0
    bigramBonus = overlap(qBigrams, entry.bigrams) * 24.0
    trigramBonus = overlap(qTrigrams, entry.trigrams) * 16.0
    contains = containMass(query, entry.alias) * 10.0
    clusterBonus = min(18.0, math.log1p(max(0, entry.clusterSize)) * 2.0)
    voteBonus = math.log1p(max(0.0, vote)) * 1.6
    lengthPenalty = abs(len(query) - len(entry.alias)) * 0.55
    return hamming + lengthPenalty - mhBonus - bigramBonus - trigramBonus - contains - clusterBonus - voteBonus


def structuralCertificateDelta(querySlots: Counter[str], entry: AliasEntry, profile: SnakeProfile | None) -> float:
    if not querySlots:
        return 0.0
    profileSlots = Counter()
    if profile is not None:
        profileSlots.update(profile.slots)
    candidateSlots = Counter(profileSlots)
    candidateSlots.update(entry.slots)

    reward = 0.0
    conflict = 0.0
    queryCore = {slot for slot in querySlots if not slot.startswith("term:") and not slot.startswith("sj:")}
    if not queryCore:
        return 0.0
    for slot in queryCore:
        if candidateSlots.get(slot, 0) > 0:
            reward += 3.6 + min(2.2, math.log1p(candidateSlots[slot]))
    for group in EXCLUSIVE_SLOT_GROUPS:
        present = [slot for slot in group if querySlots.get(slot, 0) > 0]
        if not present:
            continue
        expected = set(present)
        alternatives = set(group) - expected
        if any(candidateSlots.get(slot, 0) > 0 for slot in expected):
            reward += 4.0
        elif any(candidateSlots.get(slot, 0) > 0 for slot in alternatives):
            conflict += 10.0
        elif group[0].split(":", 1)[0] in {"flow", "delta", "transaction"}:
            conflict += 1.8
    if querySlots.get("statement:cashflow", 0) and candidateSlots.get("statement:cashflow", 0) <= 0:
        conflict += 4.8
    if (
        querySlots.get("statement:balance", 0)
        and candidateSlots.get("statement:cashflow", 0) > 0
        and candidateSlots.get("statement:balance", 0) <= 0
    ):
        conflict += 3.2
    if querySlots.get("statement:income", 0) and candidateSlots.get("statement:income", 0) <= 0:
        conflict += 2.4
    objectSlots = [slot for slot in queryCore if slot.startswith("object:")]
    if objectSlots:
        objectHits = sum(1 for slot in objectSlots if candidateSlots.get(slot, 0) > 0)
        reward += objectHits * 4.0
        if objectHits == 0:
            conflict += min(6.0, 2.0 + len(objectSlots) * 1.4)
    termHits = sum(1 for slot in querySlots if slot.startswith("term:") and candidateSlots.get(slot, 0) > 0)
    reward += min(6.0, termHits * 0.8)
    return conflict - reward


def canonicalPathAutomatonDelta(
    queryAtoms: Counter[str],
    queryCoreSlots: frozenset[str],
    entry: AliasEntry,
    profile: SnakeProfile | None,
) -> float:
    if not queryAtoms or profile is None:
        return 0.0
    if not profile.residualAtoms and not entry.pathAtoms:
        return 0.0

    shared = 0.0
    sharedKinds: Counter[str] = Counter()
    for atom, qWeight in queryAtoms.items():
        cWeight = profile.residualAtoms.get(atom, 0.0) + entry.pathAtoms.get(atom, 0.0) * 0.35
        if cWeight <= 0.0:
            continue
        gain = 1.0
        if atom.startswith("slotPair:"):
            gain = 2.0
        elif atom.startswith("slotGram:"):
            gain = 1.7
        elif atom.startswith("preSlot:") or atom.startswith("sufSlot:") or atom.startswith("sjSlot:"):
            gain = 1.55
        elif atom.startswith("cut:"):
            gain = 1.25
        elif atom.startswith("slot:"):
            gain = 1.35
        shared += math.sqrt(max(0.0, qWeight)) * math.sqrt(max(0.0, cWeight)) * gain
        sharedKinds[atom.split(":", 1)[0]] += 1

    conflict = 0.0
    qSlots = queryCoreSlots
    for group in EXCLUSIVE_SLOT_GROUPS:
        queryHits = set(group) & qSlots
        if not queryHits:
            continue
        candidateHits = (set(group) & profile.coreSlots) or (set(group) & entry.coreSlots)
        if candidateHits and not (candidateHits & queryHits):
            conflict += 7.0
        elif not candidateHits:
            conflict += 0.8
    if qSlots and not (qSlots & profile.coreSlots) and not (qSlots & entry.coreSlots):
        conflict += 2.5
    diversity = sum(1 for count in sharedKinds.values() if count > 0)
    reward = min(24.0, shared * 0.34 + diversity * 1.15)
    return conflict - reward


def corpusObjectPathDelta(
    queryAtoms: Counter[str],
    queryCoreSlots: frozenset[str],
    querySj: str,
    entry: AliasEntry,
    profile: SnakeProfile | None,
    *,
    requireSj: bool,
) -> float:
    if profile is None or (not queryAtoms and not queryCoreSlots):
        return 0.0
    if requireSj and querySj not in {"", "COMMON"} and entry.sj not in {"", "COMMON", querySj}:
        return 0.0

    conflict = 0.0
    corpusKeys = set(profile.corpusAtoms)
    if querySj in {"BS", "IS", "CF", "SCE"} and corpusKeys:
        expectedStmt = f"corp:stmt:{querySj}"
        oppositeStmts = {f"corp:stmt:{role}" for role in ("BS", "IS", "CF", "SCE") if role != querySj}
        hasExpected = expectedStmt in corpusKeys
        hasOpposite = bool(corpusKeys & oppositeStmts)
        if hasOpposite and not hasExpected:
            conflict += 3.6
    for group in EXCLUSIVE_SLOT_GROUPS:
        queryHits = set(group) & queryCoreSlots
        if not queryHits:
            continue
        expected = {f"corp:slot:{slot}" for slot in queryHits}
        alternatives = {f"corp:slot:{slot}" for slot in set(group) - queryHits}
        if not (corpusKeys & expected) and corpusKeys & alternatives:
            conflict += 3.4

    if not queryAtoms or not profile.corpusResidualAtoms:
        return conflict

    shared = 0.0
    sharedKinds: Counter[str] = Counter()
    for atom, qWeight in queryAtoms.items():
        cWeight = profile.corpusResidualAtoms.get(atom, 0.0)
        if cWeight <= 0.0:
            continue
        gain = 1.0
        if atom.startswith("corp:slotPair:"):
            gain = 2.0
        elif atom.startswith("corp:sjSlot:"):
            gain = 1.7
        elif atom.startswith("corp:stmt:"):
            gain = 1.5
        elif atom.startswith("corp:slot:"):
            gain = 1.35
        shared += math.sqrt(max(0.0, qWeight)) * math.sqrt(max(0.0, cWeight)) * gain
        sharedKinds[":".join(atom.split(":")[:2])] += 1
    diversity = sum(1 for count in sharedKinds.values() if count > 0)
    if diversity < 2 or shared < 1.2:
        return conflict
    reward = min(6.0, shared * 0.14 + diversity * 0.45)
    return conflict - reward


def counterPathObjectDelta(
    query: str,
    querySlots: Counter[str],
    queryCoreSlots: frozenset[str],
    querySj: str,
    entry: AliasEntry,
    profile: SnakeProfile | None,
    *,
    requireSj: bool,
) -> float:
    if profile is None:
        return 0.0
    if requireSj and querySj not in {"", "COMMON"} and entry.sj not in {"", "COMMON", querySj}:
        return 0.0

    penalty = 0.0
    queryContrast = contrastTermHits(query)
    entryContrast = contrastTermHits(entry.alias)
    for group, queryTerms in queryContrast.items():
        candidateTerms = entryContrast.get(group, frozenset())
        if candidateTerms and not (candidateTerms & queryTerms):
            termPenalty = 14.0 + min(5.0, 1.25 * len(candidateTerms | queryTerms))
            if group not in {"completion", "flowYuip", "delta"} and any(
                profileHasTerm(term, entry, profile) for term in queryTerms
            ):
                termPenalty *= 0.28
            penalty += termPenalty

    return min(28.0, penalty) * COUNTER_SCALE


def typedSiblingDelta(
    query: str,
    queryTokens: Counter[str],
    querySj: str,
    entry: AliasEntry,
    profile: SnakeProfile | None,
    *,
    requireSj: bool,
) -> float:
    if profile is None or not queryTokens:
        return 0.0
    if requireSj and querySj not in {"", "COMMON"} and entry.sj not in {"", "COMMON", querySj}:
        return 0.0

    candidateTokens = set(entry.canonTokens) | set(profile.canonTokens)
    if not candidateTokens:
        return 0.0

    support = 0.0
    penalty = 0.0
    matchedTokens = 0
    for token, weight in queryTokens.most_common(12):
        tokenWeight = max(0.0, float(weight))
        if token in candidateTokens:
            matchedTokens += 1
            support += min(2.2, tokenWeight * 0.10)
            continue
        alternatives = CANON_TOKEN_ALTERNATIVES.get(token, frozenset())
        conflicts = alternatives & candidateTokens
        if conflicts:
            conflictIdf = max(CANON_TOKEN_IDF.get(conflict, 0.0) for conflict in conflicts)
            penalty += min(4.5, tokenWeight * (0.30 + conflictIdf * 0.08))

    queryText = cleanSurface(query)
    entryText = cleanSurface(entry.alias)
    if entryText and entryText in queryText and queryText != entryText:
        for token, weight in queryTokens.most_common(8):
            if token in candidateTokens:
                continue
            if CANON_TOKEN_IDF.get(token, 0.0) < 1.2:
                continue
            penalty += min(2.6, float(weight) * 0.16)
    elif matchedTokens >= 2:
        for token, weight in queryTokens.most_common(8):
            if token in candidateTokens:
                continue
            if CANON_TOKEN_IDF.get(token, 0.0) >= 1.6:
                penalty += min(1.4, float(weight) * 0.07)

    return max(-2.8, min(9.0, penalty * TYPED_SIBLING_SCALE - support * TYPED_SUPPORT_SCALE))


def rankCase(
    case: HeldoutCase,
    entries: list[AliasEntry],
    profiles: dict[str, SnakeProfile],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
    useCertificate: bool,
    useCorpus: bool = False,
    useCounter: bool = False,
) -> tuple[int | None, tuple[tuple[str, float, str], ...], int]:
    query = case.alias
    qRegions = characteristicRegions(query)
    qMh = minhash(query)
    qBigrams = ngrams(query, 2)
    qTrigrams = ngrams(query, 3)
    qSlots = Counter()
    qCoreSlots: frozenset[str] = frozenset()
    qPathAtoms = Counter()
    qCorpusAtoms = Counter()
    if useCertificate:
        qSlots = structuralSlots(query, case.sj)
        qCoreSlots = coreSlotKeys(qSlots)
        qPathAtoms = pathAtomsForAlias(query, case.sj)
    if useCorpus:
        qCorpusAtoms = corpusAtomsFromFragments(query, case.sj, CORPUS_FRAGMENT_ATOMS)
    pool = candidatePool(query, case.sj, entries, bigramPostings, charPostings, withSj=withSj)
    best: dict[str, tuple[float, str]] = {}
    for index, vote in pool.items():
        entry = entries[index]
        score = entryScore(query, qRegions, qMh, qBigrams, qTrigrams, entry, vote)
        if useCertificate:
            score += structuralCertificateDelta(qSlots, entry, profiles.get(entry.snake))
            score += canonicalPathAutomatonDelta(qPathAtoms, qCoreSlots, entry, profiles.get(entry.snake))
        if useCorpus:
            score += corpusObjectPathDelta(
                qCorpusAtoms, qCoreSlots, case.sj, entry, profiles.get(entry.snake), requireSj=withSj
            )
        if useCounter:
            score += counterPathObjectDelta(
                query, qSlots, qCoreSlots, case.sj, entry, profiles.get(entry.snake), requireSj=withSj
            )
        prior = best.get(entry.snake)
        if prior is None or score < prior[0]:
            best[entry.snake] = (score, entry.alias)
    rows = sorted(((snake, score, alias) for snake, (score, alias) in best.items()), key=lambda row: row[1])
    rank: int | None = None
    for index, (snake, _score, _alias) in enumerate(rows, start=1):
        if snake == case.snake:
            rank = index
            break
    return rank, tuple(rows[:TOP_K]), len(best)


def rankedRows(
    expectedSnake: str,
    best: dict[str, tuple[float, str]],
) -> tuple[int | None, tuple[tuple[str, float, str], ...], int]:
    rows = sorted(((snake, score, alias) for snake, (score, alias) in best.items()), key=lambda row: row[1])
    rank: int | None = None
    for index, (snake, _score, _alias) in enumerate(rows, start=1):
        if snake == expectedSnake:
            rank = index
            break
    return rank, tuple(rows[:TOP_K]), len(best)


def rankCaseVariants(
    case: HeldoutCase,
    entries: list[AliasEntry],
    profiles: dict[str, SnakeProfile],
    bigramPostings: dict[str, tuple[int, ...]],
    charPostings: dict[str, tuple[int, ...]],
    *,
    withSj: bool,
) -> dict[str, tuple[int | None, tuple[tuple[str, float, str], ...], int]]:
    query = case.alias
    qRegions = characteristicRegions(query)
    qMh = minhash(query)
    qBigrams = ngrams(query, 2)
    qTrigrams = ngrams(query, 3)
    qSlots = structuralSlots(query, case.sj)
    qCoreSlots = coreSlotKeys(qSlots)
    qPathAtoms = pathAtomsForAlias(query, case.sj)
    qCorpusAtoms = corpusAtomsFromFragments(query, case.sj, CORPUS_FRAGMENT_ATOMS)
    qTokenProof = queryTokenProof(query)
    pool = candidatePool(query, case.sj, entries, bigramPostings, charPostings, withSj=withSj)
    bestByMode: dict[str, dict[str, tuple[float, str]]] = {
        "baseline": {},
        "aliasPath": {},
        "corpusPath": {},
        "counterPath": {},
        "typedSiblingPath": {},
    }
    for index, vote in pool.items():
        entry = entries[index]
        profile = profiles.get(entry.snake)
        baseScore = entryScore(query, qRegions, qMh, qBigrams, qTrigrams, entry, vote)
        aliasScore = baseScore
        aliasScore += structuralCertificateDelta(qSlots, entry, profile)
        aliasScore += canonicalPathAutomatonDelta(qPathAtoms, qCoreSlots, entry, profile)
        corpusScore = aliasScore
        corpusScore += corpusObjectPathDelta(qCorpusAtoms, qCoreSlots, case.sj, entry, profile, requireSj=withSj)
        counterScore = corpusScore
        counterScore += counterPathObjectDelta(query, qSlots, qCoreSlots, case.sj, entry, profile, requireSj=withSj)
        typedScore = counterScore
        typedScore += typedSiblingDelta(query, qTokenProof, case.sj, entry, profile, requireSj=withSj)
        for mode, score in (
            ("baseline", baseScore),
            ("aliasPath", aliasScore),
            ("corpusPath", corpusScore),
            ("counterPath", counterScore),
            ("typedSiblingPath", typedScore),
        ):
            prior = bestByMode[mode].get(entry.snake)
            if prior is None or score < prior[0]:
                bestByMode[mode][entry.snake] = (score, entry.alias)
    return {mode: rankedRows(case.snake, best) for mode, best in bestByMode.items()}


def summarize(ranks: list[int | None]) -> dict[str, float]:
    total = len(ranks) or 1
    return {
        "top1": sum(1 for rank in ranks if rank == 1),
        "top3": sum(1 for rank in ranks if rank is not None and rank <= 3),
        "top5": sum(1 for rank in ranks if rank is not None and rank <= 5),
        "top10": sum(1 for rank in ranks if rank is not None and rank <= 10),
        "miss": sum(1 for rank in ranks if rank is None),
        "mrr": sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / total,
    }


def fmtSummary(label: str, ranks: list[int | None]) -> str:
    row = summarize(ranks)
    total = len(ranks) or 1
    return (
        f"{label} Top1={int(row['top1'])}/{total} "
        f"Top3={int(row['top3'])}/{total} Top5={int(row['top5'])}/{total} "
        f"Top10={int(row['top10'])}/{total} Miss={int(row['miss'])}/{total} MRR={row['mrr']:.4f}"
    )


def main() -> None:
    started = time.perf_counter()
    heldout, entries, clusterSizes, profiles, corpusStats = buildSplit()
    leaked = sorted({case.alias for case in heldout} & {entry.alias for entry in entries})
    print("V190 canonical token typed sibling proof")
    print(
        f"heldout={len(heldout)} trainEntries={len(entries)} snakes={len(clusterSizes)} "
        f"eligibleClusters={sum(1 for _snake, size in clusterSizes.items() if size >= MIN_CLUSTER_SIZE)} leakedAliases={len(leaked)}"
    )
    print(
        f"corpus docFiles={corpusStats.docFiles} allFilingsFiles={corpusStats.allFilingsFiles} "
        f"rowsScanned={corpusStats.rowsScanned} aliasMatches={corpusStats.aliasMatches} "
        f"snakesWithCorpus={corpusStats.snakesWithCorpus} corpusAtomKeys={corpusStats.corpusAtomKeys} "
        f"typedTerms={corpusStats.typedTerms} typedAltLinks={corpusStats.typedAltLinks}"
    )
    if leaked:
        raise RuntimeError(f"held-out aliases leaked into train entries: {leaked[:5]}")
    bigramPostings, charPostings = buildPostings(entries)
    print(f"postings bigrams={len(bigramPostings)} chars={len(charPostings)}")

    baseRanksNoSj: list[int | None] = []
    baseRanksWithSj: list[int | None] = []
    certRanksNoSj: list[int | None] = []
    certRanksWithSj: list[int | None] = []
    corpusRanksNoSj: list[int | None] = []
    corpusRanksWithSj: list[int | None] = []
    counterRanksNoSj: list[int | None] = []
    counterRanksWithSj: list[int | None] = []
    typedRanksNoSj: list[int | None] = []
    typedRanksWithSj: list[int | None] = []
    wrongNoSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    wrongWithSj: list[tuple[HeldoutCase, int | None, tuple[tuple[str, float, str], ...], int]] = []
    poolSizesNoSj: list[int] = []
    poolSizesWithSj: list[int] = []
    improved = worsened = same = 0
    typedImproved = typedWorsened = typedSame = 0

    for case in heldout:
        rowsNoSj = rankCaseVariants(case, entries, profiles, bigramPostings, charPostings, withSj=False)
        rowsWithSj = rankCaseVariants(case, entries, profiles, bigramPostings, charPostings, withSj=True)
        baseNo, _baseRowsNo, candidateCountNo = rowsNoSj["baseline"]
        baseSj, _baseRowsSj, candidateCountSj = rowsWithSj["baseline"]
        rankNo, _rowsNo, _candidateCountNo2 = rowsNoSj["aliasPath"]
        rankSj, _rowsSj, _candidateCountSj2 = rowsWithSj["aliasPath"]
        corpusNo, _corpusRowsNo, _candidateCountNo3 = rowsNoSj["corpusPath"]
        corpusSj, _corpusRowsSj, _candidateCountSj3 = rowsWithSj["corpusPath"]
        counterNo, counterRowsNo, _candidateCountNo4 = rowsNoSj["counterPath"]
        counterSj, counterRowsSj, _candidateCountSj4 = rowsWithSj["counterPath"]
        typedNo, typedRowsNo, _candidateCountNo5 = rowsNoSj["typedSiblingPath"]
        typedSj, typedRowsSj, _candidateCountSj5 = rowsWithSj["typedSiblingPath"]
        baseRanksNoSj.append(baseNo)
        baseRanksWithSj.append(baseSj)
        certRanksNoSj.append(rankNo)
        certRanksWithSj.append(rankSj)
        corpusRanksNoSj.append(corpusNo)
        corpusRanksWithSj.append(corpusSj)
        counterRanksNoSj.append(counterNo)
        counterRanksWithSj.append(counterSj)
        typedRanksNoSj.append(typedNo)
        typedRanksWithSj.append(typedSj)
        poolSizesNoSj.append(candidateCountNo)
        poolSizesWithSj.append(candidateCountSj)
        corpusValue = 999999 if corpusSj is None else corpusSj
        counterValue = 999999 if counterSj is None else counterSj
        typedValue = 999999 if typedSj is None else typedSj
        if counterValue < corpusValue:
            improved += 1
        elif counterValue > corpusValue:
            worsened += 1
        else:
            same += 1
        if typedValue < counterValue:
            typedImproved += 1
        elif typedValue > counterValue:
            typedWorsened += 1
        else:
            typedSame += 1
        if typedNo != 1 and len(wrongNoSj) < 12:
            wrongNoSj.append((case, typedNo, typedRowsNo, candidateCountNo))
        if typedSj != 1 and len(wrongWithSj) < 12:
            wrongWithSj.append((case, typedSj, typedRowsSj, candidateCountSj))

    print(fmtSummary("baselineNoSj", baseRanksNoSj))
    print(fmtSummary("baselineWithSj", baseRanksWithSj))
    print(fmtSummary("aliasPathNoSj", certRanksNoSj))
    print(fmtSummary("aliasPathWithSj", certRanksWithSj))
    print(fmtSummary("corpusPathNoSj", corpusRanksNoSj))
    print(fmtSummary("corpusPathWithSj", corpusRanksWithSj))
    print(fmtSummary("counterPathNoSj", counterRanksNoSj))
    print(fmtSummary("counterPathWithSj", counterRanksWithSj))
    print(fmtSummary("typedSiblingPathNoSj", typedRanksNoSj))
    print(fmtSummary("typedSiblingPathWithSj", typedRanksWithSj))
    print(f"withSj counter-vs-corpus movement improved={improved} same={same} worsened={worsened}")
    print(f"withSj typed-vs-counter movement improved={typedImproved} same={typedSame} worsened={typedWorsened}")
    print(
        f"avgCandidateSnakes noSj={sum(poolSizesNoSj) / max(1, len(poolSizesNoSj)):.1f} "
        f"withSj={sum(poolSizesWithSj) / max(1, len(poolSizesWithSj)):.1f}"
    )
    print("noSj wrong sample")
    for case, rank, rows, candidateCount in wrongNoSj:
        top = ", ".join(f"{snake}:{alias}:{score:.1f}" for snake, score, alias in rows[:3])
        print(
            f"  query={case.alias} expected={case.snake} sj={case.sj} rank={rank} candidates={candidateCount} top={top}"
        )
    print("withSj wrong sample")
    for case, rank, rows, candidateCount in wrongWithSj:
        top = ", ".join(f"{snake}:{alias}:{score:.1f}" for snake, score, alias in rows[:3])
        print(
            f"  query={case.alias} expected={case.snake} sj={case.sj} rank={rank} candidates={candidateCount} top={top}"
        )
    print(f"seconds={time.perf_counter() - started:.1f}")


if __name__ == "__main__":
    main()
