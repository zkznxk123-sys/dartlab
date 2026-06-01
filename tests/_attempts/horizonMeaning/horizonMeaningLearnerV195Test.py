"""Horizon Meaning Learner V195 - cross-span event capsule.

아이디어:
    V194 는 block 을 local span 으로 쪼개 mixed role 오염을 줄였지만, target 과 action 이 다른 span 에 있을 때
    의미가 끊겼다. `영업권 손상` 은 target(goodwill) 과 action(impairment)이 같은 local span 에 없으면 실패한다.

    V195 는 local span 을 유지하면서 같은 parent block/table 및 가까운 section span 안에서 target/action/modifier 가
    서로를 증명하면 cross-span event capsule 로 다시 묶는다. 수평선 좌표는 여전히 빠른 주소이고, 의미는 작은 span
    경험들이 parent graph 안에서 연결될 때 생기는 sparse proof object 다.

    절차:
    - panel contentRaw 를 sentence/table-row/window span 으로 쪼개고 span text 를 독립 fragment 로 만든다.
    - chapter/section/block/xbrl/order 는 parent context 로 약하게 붙이고, role/action/target 은 local span+표제에서만 뽑는다.
    - allFilings raw filing 도 긴 raw text 전체가 아니라 local event span 으로 잘라 같은 capsule 공간에 넣는다.
    - 같은 parent block/report 안의 span role 을 모아 `event:targetAction`, `event:targetModifier`,
      `event:statementAction` atom 으로 stitch 한다.
    - 같은 section 의 가까운 blockOrder(+/-1)에서도 더 약한 `event:*` bridge 를 만든다.
    - panelCell label/statement/axis 는 전역 label hint 로 만들고, query/fragment text 가 label fragment 를 공유하면
      cell statement/value anchor atom 을 추가한다.
    - query 도 같은 방식으로 capsule 을 만든다.
    - posting 으로 후보를 빠르게 모은 뒤 surface baseline 과 capsule scorer 를 나란히 비교한다.
    - scorer 는 local capsule overlap, 같은 target cohort 안의 contrast contradiction, query core role residual 을 본다.

실행 코드:
    uv run python -X utf8 -m py_compile tests/_attempts/horizonMeaning/horizonMeaningLearnerV195Test.py
    uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV195Test.py
    $env:DARTLAB_HORIZON_V195_PANEL_FILE_LIMIT='220'; $env:DARTLAB_HORIZON_V195_ALL_FILINGS_FILE_LIMIT='32'; uv run python -X utf8 tests/_attempts/horizonMeaning/horizonMeaningLearnerV195Test.py

검증 기준:
    - accountMappings 는 학습 중심이 아니라 보조 guard 로만 사용한다.
    - 문서/공시 의미 probe 8 개를 surface baseline 과 capsule ranker 로 동시에 평가한다.
    - 각 probe 는 topK 의 corp/period/chapter/section/report/rceptNo/snippet/proof 를 출력한다.
    - rubric 은 semantic hit, exact-only, contradiction, boilerplate, cell anchor 사용 여부를 본다.
    - V194 대비 completeRole 과 `영업권 손상` 실패가 개선되는지 본다.

결과:
    첫 실행은 cross-span event 가 `영업권 손상` 을 살려 capsuleTop3Semantic=8/8, capsuleTop1CompleteRole=7/8 로
    올렸지만, `현금 유입 투자활동` 에서 local outflow span 에 sectionNear inflow event 가 붙어 Top1 을 오염시켰다.
    이후 event stitch 를 붙일 때 local span 이 같은 contrast group 의 반대 방향을 직접 말하면 해당 event atom 을
    skip 하고, flow/delta/deal/issueRedeem 같은 방향성 contradiction 은 hard veto 로 처리했다.

    최종 기본 smoke 는 fragments=17,293, panelFiles=120, panelRows=11,428, panelSpans=16,020,
    allFilingFiles=18, allFilingRows=504, allFilingSpans=1,273, blockEventGroups=1,290,
    sectionNearEventSpans=6,112, filingEventGroups=157, cellFiles=0, cellRows=0, cellHintTerms=0,
    atoms=83,344, postings=79,176, buildMs=62,043 이었다. `data/dart/panelCell` 은 현재 로컬에 없어
    cell anchor 는 비활성이다.

    최종 결과는 baselineTop1Semantic=7/8, baselineTop3Semantic=7/8 에서 capsuleTop1Semantic=8/8,
    capsuleTop3Semantic=8/8 로 올라갔다. completeRole 은 baselineTop1CompleteRole=5/8,
    capsuleTop1CompleteRole=7/8 이었다. `영업권 손상` 은 target-only/action-only 분리 실패에서
    cross-span event proof 로 completeRole=True 가 됐다. `현금 유입 투자활동` 은 Top1 semantic 은 맞았지만
    투자활동 modifier 까지는 완성하지 못해 completeRole=False 로 남았다. accountGuard 는 cases=40,
    top5SiblingEvidence=2/40 으로 V194 와 같고 V193 의 4/40 보다 낮다.

결론:
    성공/개념 상승. V193/V194 는 각각 block 오염과 local span 단절을 드러냈고, V195 는 작게 쪼갠 span 을 parent graph
    내부 event capsule 로 다시 묶으면 실제 문서 의미 probe 에서 surface baseline 을 넘는다는 신호를 보였다.
    다만 sectionNear stitch 는 아직 넓고, accountMappings guard 는 약하다. 다음은 모든 가까운 span 을 잇는 방식이 아니라
    table row/label/value/axis 또는 동일 statement 경계가 증명한 edge 만 통과시키는 typed stitch gate 가 필요하다.
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
PANEL_CELL_DIR = ROOT / "data" / "dart" / "panelCell"
ALL_FILINGS_DIR = ROOT / "data" / "dart" / "allFilings"
MAPPING_PATH = ROOT / "src" / "dartlab" / "reference" / "data" / "accountMappings.json"

PANEL_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_FILE_LIMIT", "120"))
PANEL_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_ROWS_PER_FILE", "180"))
PANEL_SPANS_PER_BLOCK = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_SPANS_PER_BLOCK", "4"))
PANEL_SPAN_CHARS = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_SPAN_CHARS", "620"))
PANEL_CELL_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_CELL_FILE_LIMIT", "160"))
PANEL_CELL_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V195_PANEL_CELL_ROWS_PER_FILE", "220"))
ALL_FILINGS_FILE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_ALL_FILINGS_FILE_LIMIT", "18"))
ALL_FILINGS_ROWS_PER_FILE = int(os.environ.get("DARTLAB_HORIZON_V195_ALL_FILINGS_ROWS_PER_FILE", "28"))
ALL_FILINGS_CHARS = int(os.environ.get("DARTLAB_HORIZON_V195_ALL_FILINGS_CHARS", "2600"))
ALL_FILINGS_SPANS_PER_ROW = int(os.environ.get("DARTLAB_HORIZON_V195_ALL_FILINGS_SPANS_PER_ROW", "3"))
MAX_FRAGMENTS = int(os.environ.get("DARTLAB_HORIZON_V195_MAX_FRAGMENTS", "22000"))
POSTING_ATOM_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_POSTING_ATOM_LIMIT", "360"))
CANDIDATE_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_CANDIDATE_LIMIT", "900"))
TOP_K = int(os.environ.get("DARTLAB_HORIZON_V195_TOP_K", "5"))
ACCOUNT_GUARD_LIMIT = int(os.environ.get("DARTLAB_HORIZON_V195_ACCOUNT_GUARD_LIMIT", "40"))

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
    cellHints: dict[str, Counter[str]] | None = None,
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

    if cellHints:
        for term in terms:
            hints = cellHints.get(term)
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


def selectedPanelCellFiles() -> list[Path]:
    files = sorted(PANEL_CELL_DIR.glob("*/*.parquet"), key=lambda path: (path.name, path.parent.name), reverse=True)
    preferred = [
        path for path in files if path.parent.name in {"005930", "000660", "035420", "000270", "005380", "000810"}
    ]
    rest = [path for path in files if path not in set(preferred)]
    return (preferred + rest)[:PANEL_CELL_FILE_LIMIT]


def selectedAllFilingFiles() -> list[Path]:
    files = [path for path in ALL_FILINGS_DIR.glob("*.parquet") if not path.name.endswith("_meta.parquet")]
    return sorted(files, key=lambda path: path.stem, reverse=True)[:ALL_FILINGS_FILE_LIMIT]


def buildCellHints() -> tuple[dict[str, Counter[str]], Counter[str]]:
    hints: dict[str, Counter[str]] = defaultdict(Counter)
    stats: Counter[str] = Counter()
    stats["cellDirExists"] = int(PANEL_CELL_DIR.exists())
    for path in selectedPanelCellFiles():
        try:
            df = (
                pl.scan_parquet(str(path))
                .select(
                    "statement",
                    "label",
                    "axisPath",
                    "valueRaw",
                    "corp",
                    "filingPeriod",
                )
                .head(PANEL_CELL_ROWS_PER_FILE)
                .collect()
            )
        except Exception as exc:  # pragma: no cover - attempts diagnostic
            stats[f"cellError:{type(exc).__name__}"] += 1
            continue
        stats["cellFiles"] += 1
        stats["cellRows"] += df.height
        for row in df.iter_rows(named=True):
            label = cleanText(row.get("label"))
            if len(label) < 2:
                continue
            statement = cleanText(row.get("statement"))
            axis = cleanText(row.get("axisPath"))
            value = cleanText(row.get("valueRaw"))
            labelTerms = normalizedTerms(label)
            labelHits = roleHits(label)
            atoms: Counter[str] = Counter()
            if statement:
                atoms[f"cell:statement:{statement.lower()}"] += 1.6
                if statement.upper() == "CF":
                    atoms["role:statement:cashflow"] += 1.6
                elif statement.upper() == "BS":
                    atoms["role:statement:balance"] += 1.4
                elif statement.upper() in {"IS", "CIS"}:
                    atoms["role:statement:income"] += 1.4
            for atom in roleAtoms(labelHits):
                atoms[f"cell:{atom}"] += 1.2
                atoms[f"role:{atom}"] += 0.9
            for pair, weight in rolePairAtoms(labelHits).items():
                atoms[pair] += min(1.2, float(weight) * 0.25)
            if axis and axis.lower() not in {"", "none", "null"}:
                for term in tuple(normalizedTerms(axis))[:4]:
                    atoms[f"cell:axis:{term}"] += 0.45
            if value:
                atoms["cell:valuePresent"] += 0.3
            for term in labelTerms:
                hints[term].update(atoms)
    return {term: Counter(dict(values.most_common(16))) for term, values in hints.items()}, stats


def readPanelFragments(cellHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
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
                    cellHints=cellHints,
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
                    )
                )
                stats["panelSpans"] += 1
            if len(fragments) >= MAX_FRAGMENTS:
                break
    addNeighborExperience(fragments)
    return fragments, stats


def readAllFilingFragments(cellHints: dict[str, Counter[str]]) -> tuple[list[Fragment], Counter[str]]:
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
                    cellHints=cellHints,
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


def addParentEventExperience(fragments: list[Fragment]) -> Counter[str]:
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
        if len(rows) < 2:
            continue
        hits = mergedRoleHits(rows)
        added = addEventAtoms(rows, hits, weight=1.0, scope="block")
        if added:
            stats["blockEventGroups"] += 1
            stats["blockEventAtoms"] += added

    for rows in filingGroups.values():
        if len(rows) < 2:
            continue
        hits = mergedRoleHits(rows)
        added = addEventAtoms(rows, hits, weight=0.8, scope="filing")
        if added:
            stats["filingEventGroups"] += 1
            stats["filingEventAtoms"] += added

    for rows in sectionGroups.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda item: (item.order, item.spanIndex))
        for index, fragment in enumerate(rows):
            peers = [
                other
                for other in rows[max(0, index - 5) : min(len(rows), index + 6)]
                if abs(other.order - fragment.order) <= 1
            ]
            if len(peers) < 2:
                continue
            hits = mergedRoleHits(peers, maxPerRole=4)
            added = addEventAtoms([fragment], hits, weight=0.32, scope="sectionNear")
            if added:
                stats["sectionNearEventSpans"] += 1
                stats["sectionNearEventAtoms"] += added
    return stats


def buildFragments() -> tuple[list[Fragment], dict[str, Counter[str]], Counter[str]]:
    started = time.perf_counter()
    cellHints, cellStats = buildCellHints()
    panelFragments, panelStats = readPanelFragments(cellHints)
    allFilingFragments, allFilingStats = readAllFilingFragments(cellHints)
    fragments = panelFragments + allFilingFragments
    for index, fragment in enumerate(fragments):
        fragment.idx = index
    stitchStats = addParentEventExperience(fragments)
    stats = Counter()
    stats.update(cellStats)
    stats.update(panelStats)
    stats.update(allFilingStats)
    stats.update(stitchStats)
    stats["fragments"] = len(fragments)
    stats["cellHintTerms"] = len(cellHints)
    stats["buildMs"] = int((time.perf_counter() - started) * 1000)
    return fragments, cellHints, stats


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
    query: str, cellHints: dict[str, Counter[str]], idf: dict[str, float]
) -> tuple[Counter[str], frozenset[str], frozenset[str]]:
    capsule, terms, anchors = capsuleForText(query, source="query", cellHints=cellHints)
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
        elif atom.startswith("cell:"):
            gain = 1.7
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


def missingCoreActions(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    qTargets = roleKeySet(qCapsule, "target")
    fTargets = roleKeySet(fCapsule, "target") | eventRoleKeySet(fCapsule, "target")
    if not (qTargets & fTargets):
        return ()
    qActions = roleKeySet(qCapsule, "action")
    fActions = roleKeySet(fCapsule, "action") | eventRoleKeySet(fCapsule, "action")
    missing = sorted(qActions - fActions)
    return tuple(missing[:4])


def residualAtoms(qCapsule: Counter[str], fCapsule: Counter[str]) -> tuple[str, ...]:
    residual: list[str] = []
    for atom, weight in qCapsule.most_common(20):
        if atom in fCapsule:
            continue
        if (
            atom.startswith(("role:action:", "role:target:", "cap:targetAction:", "cap:targetModifier:"))
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
    cellHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> tuple[list[SearchRow], list[SearchRow], frozenset[str]]:
    qCapsule, qTerms, qAnchors = queryCapsule(query, cellHints, idf)
    pool = candidatePool(query, qCapsule, postings)
    if not pool:
        return [], [], qAnchors
    capsuleRows: list[SearchRow] = []
    baselineRows: list[SearchRow] = []
    for idx, vote in pool.items():
        fragment = fragments[idx]
        fCapsule = weightedCapsule(fragment.capsule, idf)
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
            elif atom.startswith("cell:"):
                gain = 1.5
            elif atom.startswith("neighbor:") or atom.startswith("order:"):
                gain = 0.55
            sharedScore += math.sqrt(float(qWeight) * float(fWeight)) * gain
            if len(sharedAtoms) < 10 and not atom.startswith("stem:"):
                sharedAtoms.append(atom)
        contradictions = contrastAtoms(qCapsule, fCapsule)
        missingActions = missingCoreActions(qCapsule, fCapsule)
        residual = residualAtoms(qCapsule, fCapsule)
        surface = surfaceSimilarity(qTerms, fragment)
        capsuleScore = sharedScore + float(vote) * 0.012 + surface * 1.3
        if contradictions:
            capsuleScore -= len(contradictions) * 7.0
            capsuleScore -= sharedScore * 0.38
            if any(item.startswith(("flow:", "delta:", "deal:", "issueRedeem:")) for item in contradictions):
                capsuleScore -= 38.0
        if missingActions:
            capsuleScore -= len(missingActions) * 8.5
            capsuleScore -= sharedScore * 0.22
        for atom in residual:
            if atom.startswith("role:action:") or atom.startswith("cap:targetAction:"):
                capsuleScore -= 4.2
            elif atom.startswith("role:target:"):
                capsuleScore -= 1.8
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
            residual=tuple(list(missingActions) + list(residual)),
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
        if roleAtom in capsuleAtoms or eventHit or compactText(key) in compact:
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
        "cellAnchored": bool(row.fragment.anchors),
    }


def fmtRow(row: SearchRow) -> str:
    fragment = row.fragment
    location = (
        f"{fragment.source}/{fragment.spanKind}#{fragment.spanIndex}:"
        f"{fragment.corp}:{fragment.period}:{fragment.chapter or fragment.reportNm}:{fragment.section}"
    )
    proof = ",".join(row.sharedAtoms[:5]) or "-"
    contra = ",".join(row.contradiction) or "-"
    return (
        f"{location} score={row.score:.2f} surf={row.surfaceScore:.2f} "
        f"anchors={len(fragment.anchors)} contra={contra} proof={proof} "
        f"snippet={fragment.snippet[:150]}"
    )


def evaluateProbes(
    fragments: list[Fragment],
    cellHints: dict[str, Counter[str]],
    idf: dict[str, float],
    postings: dict[str, tuple[int, ...]],
) -> Counter[str]:
    summary: Counter[str] = Counter()
    for probe in PROBES:
        capsuleRows, baselineRows, queryAnchors = rankRows(probe.query, fragments, cellHints, idf, postings)
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
        summary["capsuleTop1CellAnchored"] += int(bool(capsuleTop.get("cellAnchored")))
        summary["queryCellAnchored"] += int(bool(queryAnchors))
        print(f"\nQUERY {probe.query} queryCellAnchors={','.join(sorted(queryAnchors)) or '-'}")
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
    cellHints: dict[str, Counter[str]],
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
        rows, _baseline, _anchors = rankRows(alias, fragments, cellHints, idf, postings)
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
    fragments, cellHints, buildStats = buildFragments()
    if not fragments:
        raise RuntimeError("no fragments loaded from panel/allFilings")
    idf = atomIdf(fragments)
    postings = buildPostings(fragments, idf)
    print("V195 cross-span event capsule")
    print(
        f"fragments={len(fragments)} panelFiles={buildStats['panelFiles']} panelRows={buildStats['panelRows']} "
        f"panelSpans={buildStats['panelSpans']} "
        f"allFilingFiles={buildStats['allFilingFiles']} allFilingRows={buildStats['allFilingRows']} "
        f"allFilingSpans={buildStats['allFilingSpans']} "
        f"blockEventGroups={buildStats['blockEventGroups']} sectionNearEventSpans={buildStats['sectionNearEventSpans']} "
        f"filingEventGroups={buildStats['filingEventGroups']} "
        f"cellFiles={buildStats['cellFiles']} cellRows={buildStats['cellRows']} cellHintTerms={buildStats['cellHintTerms']} "
        f"cellDirExists={buildStats['cellDirExists']} atoms={len(idf)} postings={len(postings)} buildMs={buildStats['buildMs']}"
    )
    probeStats = evaluateProbes(fragments, cellHints, idf, postings)
    guardStats = accountGuard(fragments, cellHints, idf, postings)
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
        f"capsuleTop1CellAnchored={probeStats['capsuleTop1CellAnchored']} "
        f"queryCellAnchored={probeStats['queryCellAnchored']}"
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
