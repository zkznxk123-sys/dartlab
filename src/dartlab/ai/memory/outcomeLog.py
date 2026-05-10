"""Outcome ground truth log — TauricResearch/TradingAgents 패턴 차용.

per-stockCode markdown SSOT (`~/.dartlab/decisions/{market}/{stockCode}.md`).

Entry tag 형식:
- pending: `[YYYY-MM-DD | 005930 | Verdict | pending]`
- resolved: `[YYYY-MM-DD | 005930 | Verdict | resolved | +3.2% | +1.1%vs_KOSPI | 30d]`

각 entry 사이는 HTML 주석 `<!-- ENTRY_END -->` separator (모델 prose 면역).
atomic temp+replace 쓰기 — 크래시 mid-write 시 원본 보존. pending 영구 보존, resolved 만 rotation.

Threat model: stockCode 가 모델이 web_search 결과에서 추출한 값일 수 있어 path 에 들어가기
전 safeStockcode() 가드 통과 필수.
"""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

_SEPARATOR = "\n\n<!-- ENTRY_END -->\n\n"
_TAG_RE = re.compile(r"^\[\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|\s*([^\]]+)\]\s*$")
_DECISION_RE = re.compile(r"^DECISION:\s*\n(.+?)(?=\n(?:REFLECTION:|<!-- ENTRY_END))", re.DOTALL | re.MULTILINE)
_REFLECTION_RE = re.compile(r"^REFLECTION:\s*\n(.+?)(?=\n<!-- ENTRY_END|\Z)", re.DOTALL | re.MULTILINE)

_KR_STOCK_CODE_RE = re.compile(r"^\d{6}$")
_US_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_GENERIC_SAFE_RE = re.compile(r"^[A-Za-z0-9._\-]+$")
_MAX_STOCKCODE_LEN = 16


def safeStockcode(value: str) -> str:
    """path 에 들어가기 전 stockCode 검증.

    KR 6 자리 / US ticker / generic safe (영숫자·점·하이픈·언더스코어) 외 거부.
    all-dot 거부, 길이 16 char 이하. 거부 시 ValueError.
    """
    if not isinstance(value, str):
        raise ValueError(f"stockCode 는 문자열이어야 한다: {type(value)}")
    raw = value.strip()
    if not raw:
        raise ValueError("stockCode 가 비어 있다")
    if len(raw) > _MAX_STOCKCODE_LEN:
        raise ValueError(f"stockCode 길이 초과 (>{_MAX_STOCKCODE_LEN}): {raw!r}")
    if all(ch == "." for ch in raw):
        raise ValueError(f"stockCode all-dot 거부: {raw!r}")
    if _KR_STOCK_CODE_RE.match(raw):
        return raw
    if _US_TICKER_RE.match(raw.upper()):
        return raw.upper()
    if _GENERIC_SAFE_RE.match(raw):
        return raw
    raise ValueError(f"stockCode 형식 거부: {raw!r}")


def _normalizeMarket(market: str | None) -> str:
    raw = (market or "").strip().upper()
    return raw if raw in {"KR", "US"} else "KR"


def _decisionsRoot() -> Path:
    raw = os.environ.get("DARTLAB_HOME")
    base = Path(raw) if raw else Path.home() / ".dartlab"
    return base / "decisions"


def _logPath(market: str, stockCode: str) -> Path:
    safe_market = _normalizeMarket(market)
    safe_code = safeStockcode(stockCode)
    return _decisionsRoot() / safe_market / f"{safe_code}.md"


@dataclass
class Entry:
    """단일 outcome_log entry — pending or resolved."""

    date: str
    stockCode: str
    theme: str
    status: str  # "pending" or "resolved"
    decision: str = ""
    reflection: str = ""
    raw_return: str = ""
    alpha: str = ""
    holding: str = ""

    def isPending(self) -> bool:
        """isPending — TODO 한국어 동작 설명."""
        return self.status == "pending"


def storeDecision(
    *,
    stockCode: str,
    market: str,
    date: str,
    theme: str,
    decisionText: str,
) -> bool:
    """pending entry 추가. 같은 (date, stockCode) pending 이미 있으면 skip (idempotency).

    Returns:
        True 신규 작성. False idempotency skip.
    """
    safe_code = safeStockcode(stockCode)
    safe_date = _normalizeDate(date)
    if not safe_date:
        return False
    target = _logPath(market, safe_code)
    if _hasPendingEntry(target, safe_date, safe_code):
        return False

    body = f"[{safe_date} | {safe_code} | {theme.strip() or 'Verdict'} | pending]\nDECISION:\n{decisionText.strip()}\n"
    _append(target, body)
    return True


def getPendingEntries(stockCode: str, *, market: str = "KR") -> list[Entry]:
    """같은 종목의 pending entry 목록. 없으면 빈 list."""
    safe_code = safeStockcode(stockCode)
    target = _logPath(market, safe_code)
    return [e for e in _loadEntries(target) if e.isPending() and e.stockCode == safe_code]


def getPastContext(
    stockCode: str,
    *,
    market: str = "KR",
    nSame: int = 5,
    nCross: int = 3,
) -> str:
    """비대칭 주입 — same-stockCode {n_same} (full DECISION + REFLECTION) +
    cross-stockCode {n_cross} (REFLECTION 만, decision 300 char truncate).
    역시간순 greedy fill. 빈 문자열이면 호출자가 placeholder 섹션 자체 부재화.
    """
    safe_code = safeStockcode(stockCode)
    safe_market = _normalizeMarket(market)
    same_entries = _loadEntries(_logPath(safe_market, safe_code))
    same_resolved = [e for e in reversed(same_entries) if not e.isPending()][:nSame]

    cross_entries: list[Entry] = []
    base = _decisionsRoot() / safe_market
    if base.is_dir():
        for path in sorted(base.glob("*.md")):
            other_code = path.stem
            if other_code == safe_code:
                continue
            for entry in reversed(_loadEntries(path)):
                if not entry.isPending() and entry.reflection:
                    cross_entries.append(entry)
                    if len(cross_entries) >= nCross * 4:
                        break
            if len(cross_entries) >= nCross * 4:
                break
    cross_resolved = sorted(cross_entries, key=lambda e: e.date, reverse=True)[:nCross]

    parts: list[str] = []
    for entry in same_resolved:
        parts.append(_formatFull(entry))
    for entry in cross_resolved:
        parts.append(_formatReflectionOnly(entry))
    return "\n\n".join(parts).strip()


@dataclass
class Update:
    """resolved entry 갱신 입력."""

    stockCode: str
    market: str
    date: str
    raw_return: str  # 예: "+3.2%"
    alpha: str  # 예: "+1.1%vs_KOSPI"
    holding: str  # 예: "30d"
    reflection: str


def batchUpdateWithOutcomes(updates: list[Update]) -> int:
    """pending entry 들을 resolved 로 일괄 갱신. atomic temp+replace.

    Returns:
        갱신된 entry 수.
    """
    if not updates:
        return 0
    by_path: dict[Path, list[Update]] = {}
    for upd in updates:
        try:
            target = _logPath(upd.market, upd.stockCode)
        except ValueError:
            continue
        by_path.setdefault(target, []).append(upd)

    updated_total = 0
    for path, path_updates in by_path.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        new_text, count = _applyUpdates(text, path_updates)
        if count == 0:
            continue
        _atomicWrite(path, new_text)
        updated_total += count
    return updated_total


# ── 내부 helper ──


def _hasPendingEntry(path: Path, date: str, stockCode: str) -> bool:
    if not path.exists():
        return False
    needle = f"[{date} | {stockCode} |"
    suffix = "| pending]"
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(needle) and stripped.endswith(suffix):
            return True
    return False


def _append(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8").strip():
        existing = path.read_text(encoding="utf-8").rstrip()
        new_text = existing + _SEPARATOR + body.rstrip() + _SEPARATOR
    else:
        new_text = body.rstrip() + _SEPARATOR
    _atomicWrite(path, new_text)


def _atomicWrite(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def _loadEntries(path: Path) -> list[Entry]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    blocks = [block.strip() for block in text.split(_SEPARATOR.strip()) if block.strip()]
    out: list[Entry] = []
    for block in blocks:
        entry = _parseEntry(block)
        if entry is not None:
            out.append(entry)
    return out


def _parseEntry(block: str) -> Entry | None:
    lines = block.strip().splitlines()
    if not lines:
        return None
    tag_match = _TAG_RE.match(lines[0])
    if not tag_match:
        return None
    date = tag_match.group(1).strip()
    stockCode = tag_match.group(2).strip()
    theme = tag_match.group(3).strip()
    rest = tag_match.group(4).strip()
    fields = [f.strip() for f in rest.split("|")]
    status = "pending" if fields[0] == "pending" else "resolved"

    full = block
    decision_match = _DECISION_RE.search(full + "\n<!-- ENTRY_END -->")
    decision = decision_match.group(1).strip() if decision_match else ""
    reflection_match = _REFLECTION_RE.search(full + "\n<!-- ENTRY_END -->")
    reflection = reflection_match.group(1).strip() if reflection_match else ""

    # fields[0] 은 status 문자열 자체. raw_return/alpha/holding 은 fields[1:].
    raw_return = fields[1] if status == "resolved" and len(fields) >= 2 else ""
    alpha = fields[2] if status == "resolved" and len(fields) >= 3 else ""
    holding = fields[3] if status == "resolved" and len(fields) >= 4 else ""

    return Entry(
        date=date,
        stockCode=stockCode,
        theme=theme,
        status=status,
        decision=decision,
        reflection=reflection,
        raw_return=raw_return,
        alpha=alpha,
        holding=holding,
    )


def _applyUpdates(text: str, updates: list[Update]) -> tuple[str, int]:
    """text 안 pending entry 를 (date, stockCode) 매칭으로 resolved 갱신."""
    update_map: dict[tuple[str, str], Update] = {(u.date, _safeOrSkip(u.stockCode)): u for u in updates}
    update_map = {k: v for k, v in update_map.items() if k[1] is not None}
    if not update_map:
        return text, 0

    blocks = text.split(_SEPARATOR.strip())
    rewritten: list[str] = []
    count = 0
    for block in blocks:
        stripped = block.strip()
        if not stripped:
            continue
        entry = _parseEntry(stripped)
        if entry is None or not entry.isPending():
            rewritten.append(stripped)
            continue
        key = (entry.date, entry.stockCode)
        upd = update_map.get(key)
        if upd is None:
            rewritten.append(stripped)
            continue
        new_block = (
            f"[{entry.date} | {entry.stockCode} | {entry.theme} | resolved | "
            f"{upd.raw_return} | {upd.alpha} | {upd.holding}]\n"
            f"DECISION:\n{entry.decision}\n\n"
            f"REFLECTION:\n{upd.reflection.strip()}"
        )
        rewritten.append(new_block.strip())
        count += 1
    new_text = _SEPARATOR.join(rewritten) + _SEPARATOR
    return new_text.lstrip("\n"), count


def _safeOrSkip(stockCode: str) -> str | None:
    try:
        return safeStockcode(stockCode)
    except ValueError:
        return None


def _formatFull(entry: Entry) -> str:
    head = f"[{entry.date} | {entry.stockCode} | {entry.theme} | {entry.status}"
    if entry.status == "resolved":
        head += f" | {entry.raw_return} | {entry.alpha} | {entry.holding}"
    head += "]"
    parts = [head]
    if entry.decision:
        parts.append(f"DECISION: {entry.decision}")
    if entry.reflection:
        parts.append(f"REFLECTION: {entry.reflection}")
    return "\n".join(parts)


def _formatReflectionOnly(entry: Entry) -> str:
    head = f"[{entry.date} | {entry.stockCode} | {entry.theme}]"
    if entry.reflection:
        return f"{head}\nREFLECTION: {entry.reflection}"
    decision_short = entry.decision[:300] + ("..." if len(entry.decision) > 300 else "")
    return f"{head}\n{decision_short}"


def _normalizeDate(value: str) -> str:
    raw = (value or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return ""


__all__ = [
    "Entry",
    "Update",
    "batchUpdateWithOutcomes",
    "getPastContext",
    "getPendingEntries",
    "safeStockcode",
    "storeDecision",
]
