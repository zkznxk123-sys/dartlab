"""Horizon Meaning Learner V198 - residual edge ledger capsule.

아이디어:
    V197 은 panel.contentRaw/allFilings.content_raw 텍스트만으로 textual chain 을 만들었지만, chain event 를
    capsule/postings 의 1 차 proof 로 직접 넣자 block/report 반복 표제와 broad 경험이 의미를 덮어 V196 의 8/8 을
    잃었다. 결론은 chain 자체를 버리는 것이 아니라 쓰는 위치를 바꾸는 것이다.

    V198 은 local span capsule 을 1 차 의미로 유지하고, 같은 block/report 안의 텍스트 사건 사슬은 후보 생성 proof 가
    아니라 "빠진 역할을 보강하거나 못 보강했음을 기록하는 residual edge ledger" 로만 둔다. 수평선 좌표는 여전히 빠른
    주소이고, 의미는 local 경험 + residual ledger 의 충족/미충족 비교다.

    절차:
    - panel.contentRaw 와 allFilings.content_raw 를 sentence/window/span 단위로 쪼갠다.
    - 각 span 에 stem, fixed addr, order shingle, role atom, left/right neighbor, parent text anchor 를 만든다.
    - 같은 block/report 안에서 target/action/modifier 가 떨어져 있으면 event atom 을 capsule 에 넣지 않고,
      텍스트 거리, 반복 anchor, 방향성 일관성을 통과한 peer role 을 fragment.ledger 에만 기록한다.
    - ranker 는 먼저 local capsule overlap 과 contradiction 을 본 뒤, query 의 missing target/action/modifier 가
      ledger 로 보강되는지 확인한다. 보강되지 않은 residual 은 penalty 로 남긴다.
    - allFilings report_nm 은 사건 제목 경험, content_raw 는 사건 설명 경험으로 넣는다.
    - local span 의미가 우선이고 parent/report ledger 는 보조 경험이다. parent 가 local 반대 의미를 덮어쓰지 못한다.
    - query 도 같은 capsule 공간에서 만들고 posting 후보를 capsule overlap + contradiction + residual ledger 로 rerank 한다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV198Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV198Test.py
    $env:DARTLAB_HORIZON_V198_PANEL_FILE_LIMIT='220'; $env:DARTLAB_HORIZON_V198_ALL_FILINGS_FILE_LIMIT='32'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV198Test.py

검증 기준:
    - accountMappings 는 학습 중심이 아니라 보조 guard 로만 사용한다.
    - 문서/공시 의미 probe 8 개를 surface baseline 과 capsule ranker 로 동시에 평가한다.
    - 각 probe 는 topK 의 corp/period/chapter/section/report/rceptNo/snippet/proof 를 출력한다.
    - rubric 은 semantic hit, completeRole, exact-only, contradiction, boilerplate, residual ledger 사용 여부를 본다.
    - V196 의 capsuleTop1Semantic=8/8 을 회복하면서 completeRole 7/8 을 넘길 수 있는지 본다.

결과:
    기본 smoke 실행:
    - fragments=17,293, panelFiles=120, panelRows=11,428, panelSpans=16,020
    - allFilingFiles=18, allFilingRows=504, allFilingSpans=1,273
    - residualLedgerSpans=16,480, residualLedgerAtoms=875,423
    - residualLedgerBlockGroups=2,213, residualLedgerSectionSpans=8,799,
      residualLedgerSectionRejectedSpans=4,961, residualLedgerFilingGroups=422
    - textHintFiles=18, textHintRows=504, textHintTerms=3,210
    - atoms=235,614, postings=226,827, buildMs=268,127, totalSeconds=453.7
    - baselineTop1Semantic=6/8, baselineTop3Semantic=6/8
    - capsuleTop1Semantic=5/8, capsuleTop3Semantic=6/8
    - baselineTop1CompleteRole=4/8, capsuleTop1CompleteRole=5/8
    - capsuleTop1Contradiction=2, capsuleTop1TextAnchored=8, capsuleTop1LedgerAnchored=7
    - accountGuard top5SiblingEvidence=1/40

    `유상증자 발행 조건` 은 mixed issue/redeem 후보가 top1 이고, `자기주식 취득` 은 교환대상 자기주식/처분 계열에
    밀렸으며, `영업권 손상` 은 기타영업외비용의 자산손상차손환입으로 샜다. ledger 를 capsule/postings 에 직접 넣지
    않았는데도 ledger 자체가 너무 넓어 의미 보강보다 broad role 증폭 신호가 강했다.

결론:
    실패/진단 성공. residual edge ledger 를 별도 필드로 분리한 것은 V197 보다 구조적으로 낫지만, object/target
    cohort 없이 block/report peer role 을 ledger 에 적으면 87 만 atom 규모의 넓은 경험장이 생긴다. 다음은 local target
    object 를 먼저 확정한 뒤 같은 target cohort 내부의 빠진 action/modifier 만 ledger 로 보강해야 한다. 즉 V199 는
    "target-cohort residual ledger" 로 가야 하고, 모든 block/report peer 를 ledger 로 쓰는 방식은 폐기한다.
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
PANEL_DIR = ROOT / "data" / "dart" / "panel"
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

PANEL_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V198_PANEL_FILE_LIMIT", "120"))
PANEL_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V198_PANEL_ROWS_PER_FILE", "180"))
PANEL_SPANS_PER_BLOCK = int(os.environ.get("DARTLAB_HORIZON_V198_PANEL_SPANS_PER_BLOCK", "4"))
PANEL_SPAN_CHARS = int(os.environ.get("DARTLAB_HORIZON_V198_PANEL_SPAN_CHARS", "620"))
ALL_FILINGS_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V198_ALL_FILINGS_FILE_LIMIT", "18"))
ALL_FILINGS_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V198_ALL_FILINGS_ROWS_PER_FILE", "28"))
ALL_FILINGS_CHARS = int(os.environ.get("DARTLAB_HORIZON_V198_ALL_FILINGS_CHARS", "2600"))
ALL_FILINGS_SPANS_PER_ROW = int(os.environ.get("DARTLAB_HORIZON_V198_ALL_FILINGS_SPANS_PER_ROW", "3"))
MAX_FRAGMENTS = int(os.environ.get("DARTLAB_HORIZON_V198_MAX_FRAGMENTS", "22000"))
POSTING_ATOM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V198_POSTING_ATOM_LIMIT", "360"))
CANDIDATE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V198_CANDIDATE_LIMIT", "900"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V198_TOP_K", "5"))
ACCOUNT_GUARD_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V198_ACCOUNT_GUARD_LIMIT", "40"))

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d")
HANGUL_RE = re.compile(r"[가-힣]+")
TOKEN_RE = re.compile(r"[가-힣A-Za-z0-9]+")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.?!;]|다|요|음|임|함|됨|음)\s+")


@dataclass(frozen=True)
class Probe:
    query: str
    expected: frozenset[str]
    anti: frozenset[str]


@dataclass
class Fragment:
    idx: int
    source: str
    corp: str
    period: str
    rceptNo: str
    reportNm: str
    chapter: str
    section: str
    block: str
    order: int
    spanKind: str
    spanIndex: int
    text: str
    snippet: str
    capsule: Counter[str]
    terms: frozenset[str]
    anchors: frozenset[str]
    ledger: Counter[str]


@dataclass(frozen=True)
class SearchRow:
    fragment: Fragment
    score: float
    surfaceScore: float
    sharedAtoms: tuple[str, ...]
    contradiction: tuple[str, ...]
    residual: tuple[str, ...]


ROLE_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("action", "issue", ("발행", "유상증자", "신주", "공모", "사모")),
    ("action", "redeem", ("상환", "소각", "조기상환", "만기상환")),
    ("action", "change", ("변경", "변동", "교체", "정정")),
    ("action", "acquire", ("취득", "매입", "인수", "매수", "보유")),
    ("action", "dispose", ("처분", "매각", "양도", "제거")),
    ("action", "payment", ("지급", "배당", "지출", "상환", "납부")),
    ("action", "inflow", ("유입", "수입", "입금", "수취", "회수")),
    ("action", "outflow", ("유출", "지출", "지급", "상환", "납부")),
    ("action", "increase", ("증가", "증대", "증액", "확대")),
    ("action", "decrease", ("감소", "감액", "축소", "차감")),
    ("action", "impairment", ("손상", "손상차손", "감액손실")),
    ("action", "lawsuit", ("소송", "피소", "분쟁", "청구")),
    ("target", "capitalIncrease", ("유상증자", "증자", "신주", "자본금")),
    ("target", "majorShareholder", ("최대주주", "주요주주", "대주주")),
    ("target", "treasuryStock", ("자기주식", "자사주")),
    ("target", "convertibleBond", ("전환사채", "전환사채권", "cb")),
    ("target", "bond", ("사채", "채권", "회사채")),
    ("target", "dividend", ("배당", "현금배당", "현물배당")),
    ("target", "cash", ("현금", "예금", "현금및현금성자산")),
    ("target", "litigation", ("소송", "분쟁", "우발", "청구")),
    ("target", "provision", ("충당부채", "충당금", "충당")),
    ("target", "goodwill", ("영업권", "영업권손상")),
    ("target", "investment", ("투자", "투자활동", "관계기업", "종속기업")),
    ("target", "asset", ("자산", "유형자산", "무형자산", "금융자산")),
    ("target", "debt", ("부채", "차입", "차입금", "채무")),
    ("statement", "cashflow", ("현금흐름", "영업활동", "투자활동", "재무활동", "cf")),
    ("statement", "balance", ("재무상태표", "자산", "부채", "자본", "bs")),
    ("statement", "income", ("손익계산서", "포괄손익", "매출", "수익", "비용", "is")),
    ("modifier", "condition", ("조건", "발행가액", "행사가액", "만기", "이율", "기간")),
    ("modifier", "investing", ("투자활동", "투자")),
    ("modifier", "operating", ("영업활동", "영업")),
    ("modifier", "financing", ("재무활동", "재무")),
    ("modifier", "current", ("유동", "단기")),
    ("modifier", "noncurrent", ("비유동", "장기")),
    ("modifier", "amount", ("금액", "가액", "총액", "액면")),
)

NO_DATA_TERMS = (
    "해당사항 없습니다",
    "해당사항없습니다",
    "해당 사항 없습니다",
    "내역 없음",
    "내역없음",
    "발행내용은 없습니다",
    "변동사항 없음",
    "없습니다",
    "없음",
)

CONTRAST_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("flow", ("inflow", "outflow")),
    ("delta", ("increase", "decrease")),
    ("deal", ("acquire", "dispose")),
    ("issueRedeem", ("issue", "redeem")),
    ("activity", ("operating", "investing", "financing")),
    ("maturity", ("current", "noncurrent")),
)

PROBES: tuple[Probe, ...] = (
    Probe(
        "유상증자 발행 조건",
        frozenset({"action:issue", "target:capitalIncrease", "modifier:condition"}),
        frozenset({"action:redeem"}),
    ),
    Probe("최대주주 변경", frozenset({"action:change", "target:majorShareholder"}), frozenset()),
    Probe(
        "현금 유입 투자활동",
        frozenset({"action:inflow", "target:cash", "modifier:investing"}),
        frozenset({"action:outflow", "modifier:financing"}),
    ),
    Probe("소송 충당부채", frozenset({"action:lawsuit", "target:litigation", "target:provision"}), frozenset()),
    Probe("자기주식 취득", frozenset({"action:acquire", "target:treasuryStock"}), frozenset({"action:dispose"})),
    Probe("전환사채 발행", frozenset({"action:issue", "target:convertibleBond"}), frozenset({"action:redeem"})),
    Probe("배당 지급", frozenset({"action:payment", "target:dividend"}), frozenset()),
    Probe("영업권 손상", frozenset({"action:impairment", "target:goodwill"}), frozenset()),
)


def cleanText(value: object, *, limit: int | None = None) -> str:
    text = "" if value is None else str(value)
    if limit is not None and len(text) > limit:
        text = text[:limit]
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    text = text.replace("\u00a0", " ")
    text = SPACE_RE.sub(" ", text).strip()
    return text


def compactText(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "", value).lower()


def stableHashInt(value: str) -> int:
    return int(hashlib.blake2b(value.encode("utf-8"), digest_size=8).hexdigest(), 16)


def normalizedTerms(value: str) -> frozenset[str]:
    terms: set[str] = set()
    for token in TOKEN_RE.findall(value.lower()):
        if len(token) < 2:
            continue
        if NUM_RE.fullmatch(token):
            continue
        if HANGUL_RE.fullmatch(token):
            if len(token) <= 12:
                terms.add(token)
            for size in (2, 3, 4, 5):
                if len(token) < size:
                    continue
                for index in range(len(token) - size + 1):
                    gram = token[index : index + size]
                    if not NUM_RE.search(gram):
                        terms.add(gram)
        else:
            terms.add(token[:24])
    return frozenset(terms)


def orderedTokens(value: str) -> list[str]:
    tokens: list[str] = []
    for token in TOKEN_RE.findall(value.lower()):
        if len(token) < 2 or NUM_RE.fullmatch(token):
            continue
        compact = compactText(token)
        if not compact:
            continue
        if HANGUL_RE.fullmatch(compact) and len(compact) > 8:
            for size in (3, 4):
                for index in range(max(0, len(compact) - size + 1)):
                    gram = compact[index : index + size]
                    if len(gram) >= 2:
                        tokens.append(gram)
                        if len(tokens) >= 48:
                            return tokens
        else:
            tokens.append(compact[:16])
        if len(tokens) >= 48:
            break
    return tokens


def roleHits(value: str) -> dict[str, set[str]]:
    compact = compactText(value)
    hits: dict[str, set[str]] = defaultdict(set)
    for role, key, terms in ROLE_RULES:
        for term in terms:
            normalized = compactText(term)
            if normalized and normalized in compact:
                hits[role].add(key)
                break
    return hits


def hasNoDataEvidence(value: str) -> bool:
    compact = compactText(value)
    return any(compactText(term) in compact for term in NO_DATA_TERMS)


def splitLongWindow(text: str, *, maxChars: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    windows: list[str] = []
    current: list[str] = []
    currentLen = 0
    for word in words:
        nextLen = currentLen + len(word) + int(bool(current))
        if current and nextLen > maxChars:
            windows.append(" ".join(current))
            current = current[-10:] if len(current) > 14 else []
            currentLen = len(" ".join(current))
        current.append(word)
        currentLen += len(word) + int(currentLen > 0)
    if current:
        windows.append(" ".join(current))
    return windows


def spanKindFor(text: str) -> str:
    digits = sum(1 for char in text if char.isdigit())
    digitRatio = digits / max(1, len(text))
    roleCount = sum(len(keys) for keys in roleHits(text).values())
    if digitRatio >= 0.08 or roleCount >= 4:
        return "tableRow"
    if len(text) >= PANEL_SPAN_CHARS:
        return "window"
    return "sentence"


def splitLocalSpans(text: str, *, maxChars: int, limit: int) -> list[tuple[str, str]]:
    cleaned = cleanText(text)
    if len(cleaned) < 24:
        return []
    rawPieces = [piece.strip() for piece in SENTENCE_BOUNDARY_RE.split(cleaned) if len(piece.strip()) >= 18]
    if not rawPieces:
        rawPieces = [cleaned]
    spans: list[str] = []
    buffer = ""
    for piece in rawPieces:
        if len(piece) > maxChars:
            if buffer:
                spans.append(buffer)
                buffer = ""
            spans.extend(splitLongWindow(piece, maxChars=maxChars))
            continue
        if not buffer:
            buffer = piece
            continue
        if len(buffer) < 80 and len(buffer) + len(piece) + 1 <= maxChars:
            buffer = f"{buffer} {piece}"
        else:
            spans.append(buffer)
            buffer = piece
    if buffer:
        spans.append(buffer)
    if len(spans) <= 1 and len(cleaned) > maxChars:
        spans = splitLongWindow(cleaned, maxChars=maxChars)
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for span in spans:
        compact = compactText(span)
        if len(compact) < 16 or compact in seen:
            continue
        seen.add(compact)
        deduped.append((spanKindFor(span), span[:maxChars]))
        if len(deduped) >= limit:
            break
    return deduped


def roleAtoms(hits: dict[str, set[str]]) -> set[str]:
    return {f"{role}:{key}" for role, keys in hits.items() for key in keys}


def rolePairAtoms(hits: dict[str, set[str]]) -> Counter[str]:
    atoms: Counter[str] = Counter()
    targets = sorted(hits.get("target", ()))
    actions = sorted(hits.get("action", ()))
    modifiers = sorted(hits.get("modifier", ()))
    statements = sorted(hits.get("statement", ()))
    for target in targets:
        for action in actions:
            atoms[f"cap:targetAction:{target}|{action}"] += 4.0
        for modifier in modifiers:
            atoms[f"cap:targetModifier:{target}|{modifier}"] += 2.8
        for statement in statements:
            atoms[f"cap:targetStatement:{target}|{statement}"] += 2.2
    for statement in statements:
        for action in actions:
            atoms[f"cap:statementAction:{statement}|{action}"] += 2.6
        for modifier in modifiers:
            atoms[f"cap:statementModifier:{statement}|{modifier}"] += 1.8
    return atoms


def eventPairAtoms(hits: dict[str, set[str]], *, weight: float = 1.0, prefix: str = "event") -> Counter[str]:
    atoms: Counter[str] = Counter()
    targets = sorted(hits.get("target", ()))
    actions = sorted(hits.get("action", ()))
    modifiers = sorted(hits.get("modifier", ()))
    statements = sorted(hits.get("statement", ()))
    for target in targets:
        for action in actions:
            atoms[f"{prefix}:targetAction:{target}|{action}"] += 3.2 * weight
        for modifier in modifiers:
            atoms[f"{prefix}:targetModifier:{target}|{modifier}"] += 1.8 * weight
        for statement in statements:
            atoms[f"{prefix}:targetStatement:{target}|{statement}"] += 1.4 * weight
    for statement in statements:
        for action in actions:
            atoms[f"{prefix}:statementAction:{statement}|{action}"] += 1.7 * weight
        for modifier in modifiers:
            atoms[f"{prefix}:statementModifier:{statement}|{modifier}"] += 1.1 * weight
    return atoms


def contrastStateAtoms(hits: dict[str, set[str]]) -> Counter[str]:
    atoms: Counter[str] = Counter()
    actionModifierKeys = set(hits.get("action", ())) | set(hits.get("modifier", ()))
    for group, keys in CONTRAST_GROUPS:
        active = [key for key in keys if key in actionModifierKeys]
        if len(active) == 1:
            atoms[f"state:{group}:{active[0]}"] += 1.2
        elif len(active) > 1:
            atoms[f"state:{group}:mixed"] += 2.4
            for key in active:
                atoms[f"mixed:{group}:{key}"] += 1.0
    return atoms


def capsuleForText(
    text: str,
    *,
    source: str,
    chapter: str = "",
    section: str = "",
    block: str = "",
    reportNm: str = "",
    xbrlClass: str = "",
    xbrlMatched: bool = False,
    textHints: dict[str, Counter[str]] | None = None,
    roleText: str | None = None,
    parentText: str = "",
    spanKind: str = "",
) -> tuple[Counter[str], frozenset[str], frozenset[str]]:
    joined = " ".join(item for item in (text, chapter, section, block, reportNm, xbrlClass) if item)
    roleSource = roleText if roleText is not None else joined
    terms = normalizedTerms(joined)
    hits = roleHits(roleSource)
    capsule: Counter[str] = Counter()
    anchors: set[str] = set()

    capsule[f"src:{source}"] += 0.7
    if spanKind:
        capsule[f"span:{spanKind}"] += 0.8
    if xbrlMatched:
        capsule["xbrl:matched"] += 1.2
    if xbrlClass:
        for term in normalizedTerms(xbrlClass):
            capsule[f"xbrl:{term}"] += 0.8
    for field, value in (("chapter", chapter), ("section", section), ("block", block), ("report", reportNm)):
        for term in tuple(normalizedTerms(value))[:12]:
            capsule[f"meta:{field}:{term}"] += 0.55
    for term in terms:
        if len(term) < 2:
            continue
        weight = 0.38
        if len(term) >= 4:
            weight += 0.12
        capsule[f"stem:{term}"] += weight
        capsule[f"addr:{stableHashInt(term) % 4096}"] += 0.03
    sequence = orderedTokens(roleSource)
    for left, right in zip(sequence, sequence[1:]):
        if left != right:
            capsule[f"seq:{left}>{right}"] += 0.18
    for left, mid, right in zip(sequence, sequence[1:], sequence[2:]):
        if left != right:
            capsule[f"seq3:{left}>{mid}>{right}"] += 0.08
    for term in tuple(normalizedTerms(parentText))[:18]:
        capsule[f"parent:{term}"] += 0.16
    for atom in roleAtoms(hits):
        capsule[f"role:{atom}"] += 3.0
    capsule.update(rolePairAtoms(hits))
    capsule.update(eventPairAtoms(hits, weight=1.0))
    capsule.update(contrastStateAtoms(hits))
    if hasNoDataEvidence(text):
        capsule["role:negation:noData"] += 5.0
        for role, keys in hits.items():
            for key in keys:
                capsule[f"negated:{role}:{key}"] += 2.5

    if textHints:
        for term in terms:
            hints = textHints.get(term)
            if not hints:
                continue
            anchors.add(term)
            for atom, weight in hints.items():
                capsule[atom] += min(3.0, float(weight))
    return capsule, terms, frozenset(anchors)


def selectedPanelFiles() -> list[Path]:
    files = sorted(PANEL_DIR.glob("*/*.parquet"), key=lambda path: (path.name, path.parent.name), reverse=True)
    preferred = [
        path for path in files if path.parent.name in {"005930", "000660", "035420", "000270", "005380", "000810"}
    ]
    rest = [path for path in files if path not in set(preferred)]
    return (preferred + rest)[:PANEL_FILE_LIMIT]


def selectedAllFilingFiles() -> list[Path]:
    files = [path for path in ALL_FILINGS_DIR.glob("*.parquet") if not path.name.endswith("_meta.parquet")]
    return sorted(files, key=lambda path: path.stem, reverse=True)[:ALL_FILINGS_FILE_LIMIT]


def buildTextHints() -> tuple[dict[str, Counter[str]], Counter[str]]:
    hints: dict[str, Counter[str]] = defaultdict(Counter)
    stats: Counter[str] = Counter()
    for path in selectedAllFilingFiles():
        try:
            df = (
                pl.scan_parquet(str(path))
                .select("report_nm", "content_raw", "fetch_status")
                .filter(pl.col("fetch_status").fill_null("") == "ok")
                .head(ALL_FILINGS_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"textHintError:{type(exc).__name__}"] += 1
            continue
        stats["textHintFiles"] += 1
        stats["textHintRows"] += df.height
        for row in df.iter_rows(named=True):
            report = cleanText(row.get("report_nm"))
            if len(report) < 3:
                continue
            reportHits = roleHits(report)
            atoms: Counter[str] = Counter()
            atoms["hint:source:allFilingsReport"] += 1.0
            for atom in roleAtoms(reportHits):
                atoms[f"hint:{atom}"] += 1.0
                atoms[f"role:{atom}"] += 0.45
            for pair, weight in eventPairAtoms(reportHits, weight=0.35, prefix="hintEvent").items():
                atoms[pair] += weight
            for term in normalizedTerms(report):
                hints[term].update(atoms)
    return {term: Counter(dict(values.most_common(12))) for term, values in hints.items()}, stats


def readPanelFragments(textHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
    fragments: list[Fragment] = []
    stats: Counter[str] = Counter()
    for path in selectedPanelFiles():
        if len(fragments) >= MAX_FRAGMENTS:
            break
        try:
            df = (
                pl.scan_parquet(str(path))
                .select(
                    "chapter",
                    "sectionLeaf",
                    "blockLeaf",
                    "xbrlClass",
                    "xbrlMatched",
                    "blockOrder",
                    "contentRaw",
                    "period",
                    "corp",
                    "rceptNo",
                    "disclosureKey",
                )
                .head(PANEL_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"panelError:{type(exc).__name__}"] += 1
            continue
        stats["panelFiles"] += 1
        stats["panelRows"] += df.height
        for row in df.iter_rows(named=True):
            text = cleanText(row.get("contentRaw"), limit=2400)
            if len(text) < 24:
                continue
            chapter = cleanText(row.get("chapter"))
            section = cleanText(row.get("sectionLeaf"))
            block = cleanText(row.get("blockLeaf"))
            roleHeader = " ".join(item for item in (chapter, section, block) if item)
            for spanIndex, (spanKind, spanText) in enumerate(
                splitLocalSpans(text, maxChars=PANEL_SPAN_CHARS, limit=PANEL_SPANS_PER_BLOCK)
            ):
                if len(fragments) >= MAX_FRAGMENTS:
                    break
                capsule, terms, anchors = capsuleForText(
                    spanText,
                    source="panelSpan",
                    chapter=chapter,
                    section=section,
                    block=block,
                    xbrlClass=cleanText(row.get("xbrlClass")),
                    xbrlMatched=bool(row.get("xbrlMatched")),
                    textHints=textHints,
                    roleText=f"{spanText} {roleHeader}",
                    parentText=text[:900],
                    spanKind=spanKind,
                )
                capsule[f"span:index:{min(spanIndex, 8)}"] += 0.12
                fragments.append(
                    Fragment(
                        idx=len(fragments),
                        source="panelSpan",
                        corp=cleanText(row.get("corp")),
                        period=cleanText(row.get("period")),
                        rceptNo=cleanText(row.get("rceptNo")),
                        reportNm="",
                        chapter=chapter,
                        section=section,
                        block=block,
                        order=int(row.get("blockOrder") or 0),
                        spanKind=spanKind,
                        spanIndex=spanIndex,
                        text=spanText,
                        snippet=spanText[:260],
                        capsule=capsule,
                        terms=terms,
                        anchors=anchors,
                        ledger=Counter(),
                    )
                )
                stats["panelSpans"] += 1
            if len(fragments) >= MAX_FRAGMENTS:
                break
    addNeighborExperience(fragments)
    return fragments, stats


def readAllFilingFragments(textHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
    fragments: list[Fragment] = []
    stats: Counter[str] = Counter()
    for path in selectedAllFilingFiles():
        if len(fragments) >= MAX_FRAGMENTS:
            break
        try:
            df = (
                pl.scan_parquet(str(path))
                .select("stock_code", "corp_name", "rcept_no", "report_nm", "content_raw", "fetch_status")
                .filter(pl.col("fetch_status").fill_null("") == "ok")
                .head(ALL_FILINGS_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"allFilingError:{type(exc).__name__}"] += 1
            continue
        stats["allFilingFiles"] += 1
        stats["allFilingRows"] += df.height
        for row in df.iter_rows(named=True):
            report = cleanText(row.get("report_nm"))
            raw = cleanText(row.get("content_raw"), limit=ALL_FILINGS_CHARS)
            text = cleanText(f"{report} {raw}")
            if len(text) < 40:
                continue
            for spanIndex, (spanKind, spanText) in enumerate(
                splitLocalSpans(text, maxChars=ALL_FILINGS_CHARS // 3, limit=ALL_FILINGS_SPANS_PER_ROW)
            ):
                if len(fragments) >= MAX_FRAGMENTS:
                    break
                capsule, terms, anchors = capsuleForText(
                    spanText,
                    source="allFilingsSpan",
                    reportNm=report,
                    textHints=textHints,
                    roleText=f"{spanText} {report}",
                    parentText=text[:900],
                    spanKind=spanKind,
                )
                fragments.append(
                    Fragment(
                        idx=-1,
                        source="allFilingsSpan",
                        corp=cleanText(row.get("stock_code")),
                        period=path.stem,
                        rceptNo=cleanText(row.get("rcept_no")),
                        reportNm=report,
                        chapter=report,
                        section=cleanText(row.get("corp_name")),
                        block="",
                        order=spanIndex,
                        spanKind=spanKind,
                        spanIndex=spanIndex,
                        text=spanText,
                        snippet=spanText[:260],
                        capsule=capsule,
                        terms=terms,
                        anchors=anchors,
                        ledger=Counter(),
                    )
                )
                stats["allFilingSpans"] += 1
            if len(fragments) >= MAX_FRAGMENTS:
                break
    return fragments, stats


def addNeighborExperience(fragments: list[Fragment]) -> None:
    grouped: dict[tuple[str, str, str], list[Fragment]] = defaultdict(list)
    for fragment in fragments:
        if not fragment.source.startswith("panel"):
            continue
        grouped[(fragment.corp, fragment.period, fragment.rceptNo)].append(fragment)
    for rows in grouped.values():
        rows.sort(key=lambda item: (item.order, item.spanIndex))
        for index, fragment in enumerate(rows):
            leftTerms = rows[index - 1].terms if index > 0 else frozenset()
            rightTerms = rows[index + 1].terms if index + 1 < len(rows) else frozenset()
            for term in tuple(sorted(leftTerms))[:10]:
                fragment.capsule[f"neighbor:left:{term}"] += 0.18
            for term in tuple(sorted(rightTerms))[:10]:
                fragment.capsule[f"neighbor:right:{term}"] += 0.18
            for roleAtom in sorted(atom for atom in fragment.capsule if atom.startswith("role:"))[:8]:
                if leftTerms:
                    fragment.capsule[f"order:leftRole:{roleAtom[5:]}"] += 0.25
                if rightTerms:
                    fragment.capsule[f"order:rightRole:{roleAtom[5:]}"] += 0.25


def capsuleRoleHits(capsule: Counter[str]) -> dict[str, set[str]]:
    hits: dict[str, set[str]] = defaultdict(set)
    for role in ("target", "action", "modifier", "statement"):
        hits[role].update(roleKeySet(capsule, role))
    return hits


def mergedRoleHits(fragments: list[Fragment], *, maxPerRole: int = 6) -> dict[str, set[str]]:
    merged: dict[str, set[str]] = defaultdict(set)
    for fragment in fragments:
        hits = capsuleRoleHits(fragment.capsule)
        for role, keys in hits.items():
            for key in sorted(keys):
                if len(merged[role]) < maxPerRole:
                    merged[role].add(key)
    return merged


def eventAtomRoleKeys(atom: str) -> dict[str, set[str]]:
    keys: dict[str, set[str]] = defaultdict(set)
    if atom.startswith("event:targetAction:"):
        target, _, action = atom.split(":", 2)[2].partition("|")
        if target:
            keys["target"].add(target)
        if action:
            keys["action"].add(action)
    elif atom.startswith("event:targetModifier:"):
        target, _, modifier = atom.split(":", 2)[2].partition("|")
        if target:
            keys["target"].add(target)
        if modifier:
            keys["modifier"].add(modifier)
    elif atom.startswith("event:statementAction:"):
        statement, _, action = atom.split(":", 2)[2].partition("|")
        if statement:
            keys["statement"].add(statement)
        if action:
            keys["action"].add(action)
    elif atom.startswith("event:statementModifier:"):
        statement, _, modifier = atom.split(":", 2)[2].partition("|")
        if statement:
            keys["statement"].add(statement)
        if modifier:
            keys["modifier"].add(modifier)
    return keys


def locallyContradictsEvent(fragment: Fragment, atom: str) -> bool:
    localHits = capsuleRoleHits(fragment.capsule)
    localDirection = set(localHits.get("action", set())) | set(localHits.get("modifier", set()))
    eventKeys = eventAtomRoleKeys(atom)
    eventDirection = set(eventKeys.get("action", set())) | set(eventKeys.get("modifier", set()))
    if not localDirection or not eventDirection:
        return False
    for _group, keys in CONTRAST_GROUPS:
        keySet = set(keys)
        localGroup = localDirection & keySet
        eventGroup = eventDirection & keySet
        if localGroup and eventGroup and not (localGroup & eventGroup):
            return True
    return False


GENERIC_STITCH_TERMS = {
    "공시",
    "공시금액",
    "금액",
    "단위",
    "당기",
    "전기",
    "당분기",
    "전분기",
    "당반기",
    "전반기",
    "합계",
    "기초",
    "기말",
    "내역",
    "변동",
    "대한",
    "사항",
}


def stitchBoundaryTerms(fragment: Fragment) -> set[str]:
    terms: set[str] = set()
    for term in fragment.terms:
        if len(term) < 3 or term in GENERIC_STITCH_TERMS:
            continue
        if NUM_RE.search(term):
            continue
        terms.add(term)
        if len(terms) >= 24:
            break
    for value in (fragment.block, fragment.section):
        for term in normalizedTerms(value):
            if len(term) >= 3 and term not in GENERIC_STITCH_TERMS:
                terms.add(term)
    return terms


def localStitchTerms(fragment: Fragment) -> set[str]:
    terms: set[str] = set()
    for term in normalizedTerms(fragment.text):
        if len(term) < 3 or term in GENERIC_STITCH_TERMS:
            continue
        if NUM_RE.search(term):
            continue
        terms.add(term)
        if len(terms) >= 32:
            break
    return terms


def roleDirectionKeys(fragment: Fragment) -> set[str]:
    hits = capsuleRoleHits(fragment.capsule)
    return set(hits.get("action", set())) | set(hits.get("modifier", set()))


def directionCompatible(left: Fragment, right: Fragment) -> bool:
    leftDirection = roleDirectionKeys(left)
    rightDirection = roleDirectionKeys(right)
    if not leftDirection or not rightDirection:
        return True
    for _group, keys in CONTRAST_GROUPS:
        keySet = set(keys)
        leftGroup = leftDirection & keySet
        rightGroup = rightDirection & keySet
        if leftGroup and rightGroup and not (leftGroup & rightGroup):
            return False
    return True


def textualChainAllowed(anchor: Fragment, peer: Fragment, *, maxOrderDistance: int) -> bool:
    if anchor.idx == peer.idx:
        return True
    if "role:negation:noData" in anchor.capsule or "role:negation:noData" in peer.capsule:
        return False
    if abs(anchor.order - peer.order) > maxOrderDistance:
        return False
    if not directionCompatible(anchor, peer):
        return False
    anchorHits = capsuleRoleHits(anchor.capsule)
    peerHits = capsuleRoleHits(peer.capsule)
    anchorRoles = {role for role, keys in anchorHits.items() if keys}
    peerRoles = {role for role, keys in peerHits.items() if keys}
    if not (anchorRoles and peerRoles):
        return False
    complement = ("target" in anchorRoles and ("action" in peerRoles or "modifier" in peerRoles)) or (
        "target" in peerRoles and ("action" in anchorRoles or "modifier" in anchorRoles)
    )
    if not complement and not (anchorHits.get("statement", set()) & peerHits.get("statement", set())):
        return False
    shared = localStitchTerms(anchor) & localStitchTerms(peer)
    if len(shared) >= 2:
        return True
    if anchor.block and anchor.block == peer.block and shared:
        return True
    anchorStatements = anchorHits.get("statement", set())
    peerStatements = peerHits.get("statement", set())
    if complement and anchorStatements and anchorStatements & peerStatements:
        return True
    if anchor.source.startswith("allFilings") and anchor.reportNm == peer.reportNm:
        reportTerms = normalizedTerms(anchor.reportNm)
        if complement and reportTerms & (localStitchTerms(anchor) | localStitchTerms(peer)):
            return True
    return False


def addEventAtoms(
    fragments: list[Fragment],
    hits: dict[str, set[str]],
    *,
    weight: float,
    scope: str,
) -> int:
    targets = hits.get("target", set())
    actions = hits.get("action", set())
    if not targets or not actions:
        return 0
    atoms = eventPairAtoms(hits, weight=weight)
    if not atoms:
        return 0
    added = 0
    for fragment in fragments:
        for atom, value in atoms.items():
            if locallyContradictsEvent(fragment, atom):
                fragment.capsule[f"eventConflictSkipped:{scope}"] += 0.1
                continue
            fragment.capsule[atom] += value
            added += 1
            if atom.startswith("event:targetAction:"):
                fragment.capsule[f"eventScope:{scope}"] += 0.18 * weight
    return added


def ledgerAtomsForHits(hits: dict[str, set[str]], *, weight: float, scope: str) -> Counter[str]:
    atoms: Counter[str] = Counter()
    for role in ("target", "action", "modifier", "statement"):
        for key in sorted(hits.get(role, ())):
            atoms[f"ledger:{role}:{key}"] += weight
    for atom, value in eventPairAtoms(hits, weight=weight, prefix="ledgerEvent").items():
        atoms[atom] += value * 0.7
    atoms[f"ledgerScope:{scope}"] += 0.5 * weight
    return atoms


def ledgerAtomContradicts(fragment: Fragment, atom: str) -> bool:
    if not atom.startswith("ledgerEvent:"):
        return False
    return locallyContradictsEvent(fragment, atom.replace("ledgerEvent:", "event:", 1))


def addResidualLedgerEdges(
    rows: list[Fragment],
    *,
    scope: str,
    weight: float,
    maxOrderDistance: int,
) -> Counter[str]:
    stats: Counter[str] = Counter()
    if len(rows) < 2:
        return stats
    rows.sort(key=lambda item: (item.order, item.spanIndex, item.idx))
    for index, fragment in enumerate(rows):
        if "role:negation:noData" in fragment.capsule:
            stats[f"{scope}RejectedSpans"] += 1
            continue
        lower = max(0, index - 8)
        upper = min(len(rows), index + 9)
        peers = [
            other
            for other in rows[lower:upper]
            if textualChainAllowed(fragment, other, maxOrderDistance=maxOrderDistance)
        ]
        if len(peers) < 2:
            stats[f"{scope}RejectedSpans"] += 1
            continue
        hits = mergedRoleHits(peers, maxPerRole=4)
        atoms = ledgerAtomsForHits(hits, weight=weight, scope=scope)
        added = 0
        for atom, value in atoms.items():
            if ledgerAtomContradicts(fragment, atom):
                fragment.ledger[f"ledgerConflictSkipped:{scope}"] += 0.1
                continue
            fragment.ledger[atom] += value
            added += 1
        if added:
            stats[f"{scope}Spans"] += 1
            stats[f"{scope}Atoms"] += added
            stats["residualLedgerSpans"] += 1
            stats["residualLedgerAtoms"] += added
    return stats


def addResidualEdgeLedger(fragments: list[Fragment]) -> Counter[str]:
    stats: Counter[str] = Counter()
    blockGroups: dict[tuple[str, ...], list[Fragment]] = defaultdict(list)
    sectionGroups: dict[tuple[str, ...], list[Fragment]] = defaultdict(list)
    filingGroups: dict[tuple[str, ...], list[Fragment]] = defaultdict(list)
    for fragment in fragments:
        if fragment.source.startswith("panel"):
            blockGroups[
                (
                    fragment.corp,
                    fragment.period,
                    fragment.rceptNo,
                    fragment.chapter,
                    fragment.section,
                    fragment.block,
                    str(fragment.order),
                )
            ].append(fragment)
            sectionGroups[
                (
                    fragment.corp,
                    fragment.period,
                    fragment.rceptNo,
                    fragment.chapter,
                    fragment.section,
                )
            ].append(fragment)
        elif fragment.source.startswith("allFilings"):
            filingGroups[(fragment.corp, fragment.period, fragment.rceptNo, fragment.reportNm)].append(fragment)

    for rows in blockGroups.values():
        ledgerStats = addResidualLedgerEdges(
            rows,
            scope="ledgerBlock",
            weight=1.0,
            maxOrderDistance=0,
        )
        stats.update(ledgerStats)
        if ledgerStats.get("ledgerBlockAtoms"):
            stats["residualLedgerBlockGroups"] += 1

    for rows in filingGroups.values():
        ledgerStats = addResidualLedgerEdges(
            rows,
            scope="ledgerFiling",
            weight=0.8,
            maxOrderDistance=2,
        )
        stats.update(ledgerStats)
        if ledgerStats.get("ledgerFilingAtoms"):
            stats["residualLedgerFilingGroups"] += 1

    for rows in sectionGroups.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda item: (item.order, item.spanIndex))
        for index, fragment in enumerate(rows):
            nearby = [
                other
                for other in rows[max(0, index - 5) : min(len(rows), index + 6)]
                if abs(other.order - fragment.order) <= 1
            ]
            peers = [other for other in nearby if textualChainAllowed(fragment, other, maxOrderDistance=1)]
            if len(peers) < 2:
                stats["residualLedgerSectionRejectedSpans"] += 1
                continue
            hits = mergedRoleHits(peers, maxPerRole=4)
            atoms = ledgerAtomsForHits(hits, weight=0.32, scope="ledgerSection")
            added = 0
            for atom, value in atoms.items():
                if ledgerAtomContradicts(fragment, atom):
                    fragment.ledger["ledgerConflictSkipped:ledgerSection"] += 0.1
                    continue
                fragment.ledger[atom] += value
                added += 1
            if added:
                stats["residualLedgerSectionSpans"] += 1
                stats["residualLedgerSectionAtoms"] += added
                stats["residualLedgerSpans"] += 1
                stats["residualLedgerAtoms"] += added
    return stats


def buildFragments() -> tuple[list[Fragment], dict[str, Counter[str]], Counter[str]]:
    started = time.perf_counter()
    textHints, textStats = buildTextHints()
    panelFragments, panelStats = readPanelFragments(textHints)
    allFilingFragments, allFilingStats = readAllFilingFragments(textHints)
    fragments = panelFragments + allFilingFragments
    for index, fragment in enumerate(fragments):
        fragment.idx = index
    ledgerStats = addResidualEdgeLedger(fragments)
    stats = Counter()
    stats.update(textStats)
    stats.update(panelStats)
    stats.update(allFilingStats)
    stats.update(ledgerStats)
    stats["fragments"] = len(fragments)
    stats["textHintTerms"] = len(textHints)
    stats["buildMs"] = int((time.perf_counter() - started) * 1000)
    return fragments, textHints, stats


def atomIdf(fragments: list[Fragment]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for fragment in fragments:
        for atom in fragment.capsule:
            df[atom] += 1
    total = max(1, len(fragments))
    return {atom: math.log((total + 1.0) / (count + 0.5)) for atom, count in df.items()}


def weightedCapsule(capsule: Counter[str], idf: dict[str, float]) -> Counter[str]:
    weighted: Counter[str] = Counter()
    for atom, raw in capsule.items():
        atomIdfValue = max(0.05, idf.get(atom, 0.35))
        if atom.startswith("addr:"):
            atomIdfValue = min(atomIdfValue, 0.05)
        weighted[atom] = float(raw) * atomIdfValue
    return weighted


def capsuleForScoring(capsule: Counter[str]) -> Counter[str]:
    if "role:negation:noData" not in capsule:
        return capsule.copy()
    filtered: Counter[str] = Counter()
    for atom, weight in capsule.items():
        if atom.startswith(("role:action:", "cap:", "event:", "hintEvent:", "state:", "mixed:")):
            continue
        filtered[atom] = weight
    filtered["meaningInvalid:noData"] += 8.0
    return filtered


def buildPostings(fragments: list[Fragment], idf: dict[str, float]) -> dict[str, tuple[int, ...]]:
    postings: dict[str, list[int]] = defaultdict(list)
    for fragment in fragments:
        weighted = weightedCapsule(fragment.capsule, idf)
        for atom, _weight in weighted.most_common(POSTING_ATOM_LIMIT):
            if atom.startswith("addr:"):
                continue
            postings[atom].append(fragment.idx)
    return {atom: tuple(values) for atom, values in postings.items()}


def queryCapsule(
    query: str, textHints: dict[str, Counter[str]], idf: dict[str, float]
) -> tuple[Counter[str], frozenset[str], frozenset[str]]:
    capsule, terms, anchors = capsuleForText(query, source="query", textHints=textHints)
    return weightedCapsule(capsule, idf), terms, anchors


def candidatePool(query: str, qCapsule: Counter[str], postings: dict[str, tuple[int, ...]]) -> dict[int, float]:
    votes: Counter[int] = Counter()
    for atom, weight in qCapsule.most_common(80):
        if atom.startswith("addr:"):
            continue
        rows = postings.get(atom)
        if not rows:
            continue
        gain = 1.0
        if atom.startswith("cap:"):
            gain = 2.4
        elif atom.startswith("role:"):
            gain = 2.0
        elif atom.startswith("event:"):
            gain = 2.1
        elif atom.startswith("hint:") or atom.startswith("hintEvent:"):
            gain = 1.3
        elif atom.startswith("seq:") or atom.startswith("seq3:"):
            gain = 0.65
        elif atom.startswith("stem:"):
            gain = 0.8
        for idx in rows[:900]:
            votes[idx] += float(weight) * gain
    if not votes:
        return {}
    return dict(votes.most_common(CANDIDATE_LIMIT))


def roleKeySet(capsule: Counter[str], role: str) -> set[str]:
    prefix = f"role:{role}:"
    return {atom[len(prefix) :] for atom in capsule if atom.startswith(prefix)}


def eventRoleKeySet(capsule: Counter[str], role: str) -> set[str]:
    keys: set[str] = set()
    for atom in capsule:
        if atom.startswith("event:targetAction:"):
            pair = atom.split(":", 2)[2]
            target, _, action = pair.partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "action" and action:
                keys.add(action)
        elif atom.startswith("event:targetModifier:"):
            pair = atom.split(":", 2)[2]
            target, _, modifier = pair.partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "modifier" and modifier:
                keys.add(modifier)
        elif atom.startswith("event:targetStatement:"):
            pair = atom.split(":", 2)[2]
            target, _, statement = pair.partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "statement" and statement:
                keys.add(statement)
        elif atom.startswith("event:statementAction:"):
            pair = atom.split(":", 2)[2]
            statement, _, action = pair.partition("|")
            if role == "statement" and statement:
                keys.add(statement)
            elif role == "action" and action:
                keys.add(action)
        elif atom.startswith("event:statementModifier:"):
            pair = atom.split(":", 2)[2]
            statement, _, modifier = pair.partition("|")
            if role == "statement" and statement:
                keys.add(statement)
            elif role == "modifier" and modifier:
                keys.add(modifier)
    return keys


def ledgerRoleKeySet(ledger: Counter[str], role: str) -> set[str]:
    keys: set[str] = set()
    prefix = f"ledger:{role}:"
    keys.update(atom[len(prefix) :] for atom in ledger if atom.startswith(prefix))
    for atom in ledger:
        if atom.startswith("ledgerEvent:targetAction:"):
            target, _, action = atom.split(":", 2)[2].partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "action" and action:
                keys.add(action)
        elif atom.startswith("ledgerEvent:targetModifier:"):
            target, _, modifier = atom.split(":", 2)[2].partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "modifier" and modifier:
                keys.add(modifier)
        elif atom.startswith("ledgerEvent:targetStatement:"):
            target, _, statement = atom.split(":", 2)[2].partition("|")
            if role == "target" and target:
                keys.add(target)
            elif role == "statement" and statement:
                keys.add(statement)
        elif atom.startswith("ledgerEvent:statementAction:"):
            statement, _, action = atom.split(":", 2)[2].partition("|")
            if role == "statement" and statement:
                keys.add(statement)
            elif role == "action" and action:
                keys.add(action)
        elif atom.startswith("ledgerEvent:statementModifier:"):
            statement, _, modifier = atom.split(":", 2)[2].partition("|")
            if role == "statement" and statement:
                keys.add(statement)
            elif role == "modifier" and modifier:
                keys.add(modifier)
    return keys


def contrastAtoms(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    qTargets = roleKeySet(qCapsule, "target")
    fTargets = roleKeySet(fCapsule, "target") | eventRoleKeySet(fCapsule, "target")
    targetOverlap = qTargets & fTargets
    if not targetOverlap:
        return ()
    contradictions: list[str] = []
    for group, keys in CONTRAST_GROUPS:
        qKeys = {key for key in keys if f"role:action:{key}" in qCapsule or f"role:modifier:{key}" in qCapsule}
        fKeys = {
            key
            for key in keys
            if f"role:action:{key}" in fCapsule
            or f"role:modifier:{key}" in fCapsule
            or key in eventRoleKeySet(fCapsule, "action")
            or key in eventRoleKeySet(fCapsule, "modifier")
        }
        if qKeys and f"state:{group}:mixed" in fCapsule:
            contradictions.append(f"{group}:{'/'.join(sorted(qKeys))}!=mixed")
            continue
        if qKeys and fKeys:
            foreign = fKeys - qKeys
            if foreign:
                contradictions.append(f"{group}:{'/'.join(sorted(qKeys))}!={'/'.join(sorted(foreign))}")
    return tuple(contradictions[:4])


def missingCoreRoles(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    qTargets = roleKeySet(qCapsule, "target")
    fTargets = roleKeySet(fCapsule, "target") | eventRoleKeySet(fCapsule, "target")
    qActions = roleKeySet(qCapsule, "action")
    fActions = roleKeySet(fCapsule, "action") | eventRoleKeySet(fCapsule, "action")
    qModifiers = roleKeySet(qCapsule, "modifier")
    fModifiers = roleKeySet(fCapsule, "modifier") | eventRoleKeySet(fCapsule, "modifier")
    missing = [f"target:{key}" for key in sorted(qTargets - fTargets)]
    if qTargets & fTargets:
        missing.extend(f"action:{key}" for key in sorted(qActions - fActions))
        missing.extend(f"modifier:{key}" for key in sorted(qModifiers - fModifiers))
    return tuple(missing[:5])


def ledgerSupportedMissing(
    missingRoles: tuple[str, ...],
    ledger: Counter[str],
    *,
    localRoleOverlap: bool,
) -> tuple[str, ...]:
    if not localRoleOverlap:
        return ()
    supported: list[str] = []
    for item in missingRoles:
        role, _, key = item.partition(":")
        if key and key in ledgerRoleKeySet(ledger, role):
            supported.append(item)
    return tuple(supported)


def residualAtoms(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    residual: list[str] = []
    for atom, weight in qCapsule.most_common(20):
        if atom in fCapsule:
            continue
        if (
            atom.startswith(
                ("role:action:", "role:target:", "role:modifier:", "cap:targetAction:", "cap:targetModifier:")
            )
            and weight > 0.8
        ):
            residual.append(atom)
    return tuple(residual[:5])


def surfaceSimilarity(queryTerms: frozenset[str], fragment: Fragment) -> float:
    if not queryTerms or not fragment.terms:
        return 0.0
    shared = queryTerms & fragment.terms
    return len(shared) / max(1, min(len(queryTerms), len(fragment.terms)))


def rankRows(
    query: str,
    fragments: list[Fragment],
    textHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> tuple[list[SearchRow], list[SearchRow], frozenset[str]]:
    qCapsule, qTerms, qAnchors = queryCapsule(query, textHints, idf)
    pool = candidatePool(query, qCapsule, postings)
    if not pool:
        return [], [], qAnchors
    capsuleRows: list[SearchRow] = []
    baselineRows: list[SearchRow] = []
    for idx, vote in pool.items():
        fragment = fragments[idx]
        fCapsule = weightedCapsule(capsuleForScoring(fragment.capsule), idf)
        sharedScore = 0.0
        sharedAtoms: list[str] = []
        for atom, qWeight in qCapsule.items():
            fWeight = fCapsule.get(atom, 0.0)
            if fWeight <= 0:
                continue
            gain = 1.0
            if atom.startswith("cap:"):
                gain = 2.4
            elif atom.startswith("role:"):
                gain = 2.0
            elif atom.startswith("event:"):
                gain = 2.2
            elif atom.startswith("hint:") or atom.startswith("hintEvent:"):
                gain = 1.25
            elif atom.startswith("seq:") or atom.startswith("seq3:"):
                gain = 0.62
            elif atom.startswith("neighbor:") or atom.startswith("order:"):
                gain = 0.55
            sharedScore += math.sqrt(float(qWeight) * float(fWeight)) * gain
            if len(sharedAtoms) < 10 and not atom.startswith("stem:"):
                sharedAtoms.append(atom)
        contradictions = contrastAtoms(qCapsule, fCapsule)
        missingRoles = missingCoreRoles(qCapsule, fCapsule)
        qRoleKeys = (
            {("target", key) for key in roleKeySet(qCapsule, "target")}
            | {("action", key) for key in roleKeySet(qCapsule, "action")}
            | {("modifier", key) for key in roleKeySet(qCapsule, "modifier")}
        )
        fRoleKeys = (
            {("target", key) for key in roleKeySet(fCapsule, "target")}
            | {("action", key) for key in roleKeySet(fCapsule, "action")}
            | {("modifier", key) for key in roleKeySet(fCapsule, "modifier")}
        )
        supportedMissing = ledgerSupportedMissing(
            missingRoles,
            fragment.ledger,
            localRoleOverlap=bool(qRoleKeys & fRoleKeys),
        )
        unsupportedMissing = tuple(item for item in missingRoles if item not in supportedMissing)
        residual = residualAtoms(qCapsule, fCapsule)
        surface = surfaceSimilarity(qTerms, fragment)
        capsuleScore = sharedScore + float(vote) * 0.012 + surface * 1.3
        if contradictions:
            capsuleScore -= len(contradictions) * 7.0
            capsuleScore -= sharedScore * 0.38
            if any(item.startswith(("flow:", "delta:", "deal:", "issueRedeem:")) for item in contradictions):
                capsuleScore -= 38.0
        if unsupportedMissing:
            targetMisses = sum(1 for item in unsupportedMissing if item.startswith("target:"))
            actionMisses = sum(1 for item in unsupportedMissing if item.startswith("action:"))
            modifierMisses = sum(1 for item in unsupportedMissing if item.startswith("modifier:"))
            capsuleScore -= targetMisses * 6.5
            capsuleScore -= actionMisses * 8.5
            capsuleScore -= modifierMisses * 5.0
            capsuleScore -= sharedScore * 0.22
        if supportedMissing:
            capsuleScore += min(4.5, len(supportedMissing) * 1.8)
            for item in supportedMissing:
                if len(sharedAtoms) < 10:
                    sharedAtoms.append(f"ledgerSupport:{item}")
        for atom in residual:
            if atom.startswith("role:action:") or atom.startswith("cap:targetAction:"):
                capsuleScore -= 4.2
            elif atom.startswith("role:modifier:") or atom.startswith("cap:targetModifier:"):
                capsuleScore -= 2.6
            elif atom.startswith("role:target:"):
                capsuleScore -= 4.0
            else:
                capsuleScore -= 0.65
        if "role:negation:noData" in fCapsule and any(atom.startswith("role:action:") for atom in qCapsule):
            capsuleScore -= 18.0
        if fragment.anchors:
            capsuleScore += min(1.8, len(fragment.anchors) * 0.28)
        surfaceScore = surface * 9.0 + float(vote) * 0.004
        if "role:negation:noData" in fCapsule and any(atom.startswith("role:action:") for atom in qCapsule):
            surfaceScore -= 7.5
        if contradictions:
            surfaceScore -= 4.0
        row = SearchRow(
            fragment=fragment,
            score=capsuleScore,
            surfaceScore=surfaceScore,
            sharedAtoms=tuple(sharedAtoms),
            contradiction=contradictions,
            residual=tuple(list(unsupportedMissing) + list(residual)),
        )
        capsuleRows.append(row)
        baselineRows.append(row)
    capsuleRows.sort(key=lambda row: row.score, reverse=True)
    baselineRows.sort(key=lambda row: row.surfaceScore, reverse=True)
    return capsuleRows[:TOP_K], baselineRows[:TOP_K], qAnchors


def semanticEvidence(probe: Probe, row: SearchRow) -> dict[str, object]:
    capsuleAtoms = set(row.fragment.capsule)
    compact = compactText(
        " ".join((row.fragment.text, row.fragment.reportNm, row.fragment.chapter, row.fragment.section))
    )
    expectedHits = 0
    antiHits = 0
    for expected in probe.expected:
        roleAtom = f"role:{expected}"
        role, key = expected.split(":", 1)
        eventHit = key in eventRoleKeySet(row.fragment.capsule, role)
        ledgerHit = key in ledgerRoleKeySet(row.fragment.ledger, role)
        if roleAtom in capsuleAtoms or eventHit or ledgerHit or compactText(key) in compact:
            expectedHits += 1
    for anti in probe.anti:
        roleAtom = f"role:{anti}"
        key = anti.split(":", 1)[1]
        if roleAtom in capsuleAtoms or compactText(key) in compact:
            antiHits += 1
    exact = compactText(probe.query) in compact
    noData = "role:negation:noData" in capsuleAtoms or hasNoDataEvidence(row.fragment.text)
    boilerplate = len(row.fragment.snippet) < 40 or "document" in row.fragment.snippet.lower()[:80] or noData
    needed = max(1, min(len(probe.expected), 2))
    semantic = expectedHits >= needed and antiHits == 0 and not boilerplate
    completeRole = expectedHits >= len(probe.expected) and antiHits == 0 and not boilerplate
    return {
        "semantic": semantic,
        "completeRole": completeRole,
        "expectedHits": expectedHits,
        "antiHits": antiHits,
        "exact": exact,
        "exactOnly": exact and not semantic,
        "boilerplate": boilerplate,
        "noData": noData,
        "textAnchored": bool(row.fragment.anchors),
        "ledgerAnchored": bool(row.fragment.ledger),
    }


def fmtRow(row: SearchRow) -> str:
    fragment = row.fragment
    location = (
        f"{fragment.source}/{fragment.spanKind}#{fragment.spanIndex}:"
        f"{fragment.corp}:{fragment.period}:{fragment.chapter or fragment.reportNm}:{fragment.section}"
    )
    proof = ",".join(row.sharedAtoms[:5]) or "-"
    contra = ",".join(row.contradiction) or "-"
    ledger = ",".join(atom for atom, _value in row.fragment.ledger.most_common(3)) or "-"
    return (
        f"{location} score={row.score:.2f} surf={row.surfaceScore:.2f} "
        f"anchors={len(fragment.anchors)} ledger={ledger} contra={contra} proof={proof} "
        f"snippet={fragment.snippet[:150]}"
    )


def evaluateProbes(
    fragments: list[Fragment],
    textHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> Counter[str]:
    summary: Counter[str] = Counter()
    for probe in PROBES:
        capsuleRows, baselineRows, queryAnchors = rankRows(probe.query, fragments, textHints, idf, postings)
        capsuleHit = any(bool(semanticEvidence(probe, row)["semantic"]) for row in capsuleRows[:3])
        baselineHit = any(bool(semanticEvidence(probe, row)["semantic"]) for row in baselineRows[:3])
        capsuleTop = semanticEvidence(probe, capsuleRows[0]) if capsuleRows else {}
        baselineTop = semanticEvidence(probe, baselineRows[0]) if baselineRows else {}
        summary["probes"] += 1
        summary["capsuleTop3Semantic"] += int(capsuleHit)
        summary["baselineTop3Semantic"] += int(baselineHit)
        summary["capsuleTop1Semantic"] += int(bool(capsuleTop.get("semantic")))
        summary["baselineTop1Semantic"] += int(bool(baselineTop.get("semantic")))
        summary["capsuleTop1CompleteRole"] += int(bool(capsuleTop.get("completeRole")))
        summary["baselineTop1CompleteRole"] += int(bool(baselineTop.get("completeRole")))
        summary["capsuleTop1ExactOnly"] += int(bool(capsuleTop.get("exactOnly")))
        summary["capsuleTop1Contradiction"] += int(bool(capsuleTop.get("antiHits")))
        summary["capsuleTop1TextAnchored"] += int(bool(capsuleTop.get("textAnchored")))
        summary["capsuleTop1LedgerAnchored"] += int(bool(capsuleTop.get("ledgerAnchored")))
        summary["queryTextAnchored"] += int(bool(queryAnchors))
        print(f"\nQUERY {probe.query} queryTextAnchors={','.join(sorted(queryAnchors)) or '-'}")
        print(
            "  baselineTop1 "
            f"semantic={baselineTop.get('semantic', False)} exact={baselineTop.get('exact', False)} "
            f"complete={baselineTop.get('completeRole', False)} "
            f"expected={baselineTop.get('expectedHits', 0)} anti={baselineTop.get('antiHits', 0)}"
        )
        if baselineRows:
            print("    " + fmtRow(baselineRows[0]))
        print(
            "  capsuleTop1 "
            f"semantic={capsuleTop.get('semantic', False)} exact={capsuleTop.get('exact', False)} "
            f"complete={capsuleTop.get('completeRole', False)} "
            f"expected={capsuleTop.get('expectedHits', 0)} anti={capsuleTop.get('antiHits', 0)}"
        )
        for index, row in enumerate(capsuleRows[:3], start=1):
            evidence = semanticEvidence(probe, row)
            print(
                f"    #{index} semantic={evidence['semantic']} exact={evidence['exact']} "
                f"complete={evidence['completeRole']} expected={evidence['expectedHits']} anti={evidence['antiHits']} "
                + fmtRow(row)
            )
    return summary


def accountGuard(
    fragments: list[Fragment],
    textHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> Counter[str]:
    stats: Counter[str] = Counter()
    if not MAPPING_PATH.exists():
        return stats
    try:
        import json

        raw = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - attempts diagnostic
        stats[f"mappingError:{type(exc).__name__}"] += 1
        return stats
    mappings: dict[str, str] = raw.get("mappings", {})
    clusters: dict[str, list[str]] = defaultdict(list)
    for alias, snake in mappings.items():
        cleaned = cleanText(alias)
        if 3 <= len(cleaned) <= 24:
            clusters[str(snake)].append(cleaned)
    cases: list[tuple[str, str, frozenset[str]]] = []
    for snake, aliases in sorted(clusters.items(), key=lambda item: stableHashInt(item[0])):
        unique = sorted(set(aliases), key=lambda item: stableHashInt(f"{snake}:{item}"))
        if len(unique) < 4:
            continue
        heldout = unique[0]
        siblings = frozenset(unique[1:12])
        cases.append((heldout, snake, siblings))
        if len(cases) >= ACCOUNT_GUARD_LIMIT:
            break
    for alias, _snake, siblings in cases:
        rows, _baseline, _anchors = rankRows(alias, fragments, textHints, idf, postings)
        stats["accountCases"] += 1
        compactSiblings = {compactText(item) for item in siblings if len(item) >= 3}
        hit = False
        for row in rows[:5]:
            rowCompact = compactText(row.fragment.text)
            if any(sibling and sibling in rowCompact for sibling in compactSiblings):
                hit = True
                break
        stats["accountTop5SiblingEvidence"] += int(hit)
    return stats


def main() -> None:
    started = time.perf_counter()
    fragments, textHints, buildStats = buildFragments()
    if not fragments:
        raise RuntimeError("no fragments loaded from panel/allFilings")
    idf = atomIdf(fragments)
    postings = buildPostings(fragments, idf)
    print("V198 residual edge ledger capsule")
    print(
        f"fragments={len(fragments)} panelFiles={buildStats['panelFiles']} panelRows={buildStats['panelRows']} "
        f"panelSpans={buildStats['panelSpans']} "
        f"allFilingFiles={buildStats['allFilingFiles']} allFilingRows={buildStats['allFilingRows']} "
        f"allFilingSpans={buildStats['allFilingSpans']} "
        f"residualLedgerSpans={buildStats['residualLedgerSpans']} "
        f"residualLedgerAtoms={buildStats['residualLedgerAtoms']} "
        f"residualLedgerBlockGroups={buildStats['residualLedgerBlockGroups']} "
        f"residualLedgerSectionSpans={buildStats['residualLedgerSectionSpans']} "
        f"residualLedgerSectionRejectedSpans={buildStats['residualLedgerSectionRejectedSpans']} "
        f"residualLedgerFilingGroups={buildStats['residualLedgerFilingGroups']} "
        f"textHintFiles={buildStats['textHintFiles']} textHintRows={buildStats['textHintRows']} "
        f"textHintTerms={buildStats['textHintTerms']} atoms={len(idf)} postings={len(postings)} buildMs={buildStats['buildMs']}"
    )
    probeStats = evaluateProbes(fragments, textHints, idf, postings)
    guardStats = accountGuard(fragments, textHints, idf, postings)
    print("\nSUMMARY")
    print(
        f"baselineTop1Semantic={probeStats['baselineTop1Semantic']}/{probeStats['probes']} "
        f"baselineTop3Semantic={probeStats['baselineTop3Semantic']}/{probeStats['probes']} "
        f"capsuleTop1Semantic={probeStats['capsuleTop1Semantic']}/{probeStats['probes']} "
        f"capsuleTop3Semantic={probeStats['capsuleTop3Semantic']}/{probeStats['probes']} "
        f"baselineTop1CompleteRole={probeStats['baselineTop1CompleteRole']}/{probeStats['probes']} "
        f"capsuleTop1CompleteRole={probeStats['capsuleTop1CompleteRole']}/{probeStats['probes']} "
        f"capsuleTop1ExactOnly={probeStats['capsuleTop1ExactOnly']} "
        f"capsuleTop1Contradiction={probeStats['capsuleTop1Contradiction']} "
        f"capsuleTop1TextAnchored={probeStats['capsuleTop1TextAnchored']} "
        f"capsuleTop1LedgerAnchored={probeStats['capsuleTop1LedgerAnchored']} "
        f"queryTextAnchored={probeStats['queryTextAnchored']}"
    )
    if guardStats:
        print(
            f"accountGuard cases={guardStats['accountCases']} "
            f"top5SiblingEvidence={guardStats['accountTop5SiblingEvidence']}/{max(1, guardStats['accountCases'])}"
        )
    else:
        print("accountGuard cases=0 top5SiblingEvidence=0/0")
    print(f"seconds={time.perf_counter() - started:.1f}")


if __name__ == "__main__":
    main()
