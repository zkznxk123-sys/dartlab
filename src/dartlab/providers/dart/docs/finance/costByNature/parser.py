"""비용의 성격별 분류 파서."""

import re

from dartlab.core.mappers.parserMapper import loadCostByNature
from dartlab.core.tableParser import detectUnit, parseAmount
from dartlab.core.utils.unitNormalize import normalizeFromUnitScale

_CBN = loadCostByNature()
NORMALIZE_MAP = _CBN.get("normalize", [])
TOTAL_PATTERNS = _CBN.get("totalPatterns", [])
_SKIP_KEYWORDS = set(_CBN.get("skipKeywords", []))


def normalizeAccountName(raw: str) -> str:
    cleaned = raw.replace(" ", "")
    for stdName, keywords in NORMALIZE_MAP:
        for kw in keywords:
            if kw in cleaned:
                return stdName
    return raw


def isTotalRow(name: str) -> bool:
    cleaned = name.replace(" ", "")
    for p in TOTAL_PATTERNS:
        if p in cleaned:
            return True
    if re.match(r"^계\(?[\*\d]*\)?$", cleaned):
        return True
    return False


def _isDanggi(text):
    t = text.replace(" ", "")
    return "당기" in t or bool(re.search(r"제\d+\(당\)기", t))


def _isJeongi(text):
    t = text.replace(" ", "")
    return "전기" in t or bool(re.search(r"제\d+\(전\)기", t))


def _isPeriodLabel(text):
    if _isDanggi(text):
        return "당기"
    if _isJeongi(text):
        return "전기"
    return None


def _isSkipRow(name):
    if not name:
        return True
    c = name.replace(" ", "")
    if c in _SKIP_KEYWORDS or name in _SKIP_KEYWORDS:
        return True
    if isTotalRow(name):
        return True
    return False


def _cleanAccountName(name):
    name = name.strip()
    name = re.sub(r"^\d+[\.\)]\s*", "", name)
    name = re.sub(r"\s+", "", name)
    return name


def _findNextSection(lines, fromIdx, pattern):
    for i in range(fromIdx, len(lines)):
        s = lines[i].strip()
        if s.startswith("|"):
            continue
        if re.match(pattern, s):
            return i
    return len(lines)


def _findTableEnd(lines, fromIdx):
    emptyCount, lastTable = 0, fromIdx
    for i in range(fromIdx, len(lines)):
        s = lines[i].strip()
        if s.startswith("|"):
            emptyCount = 0
            lastTable = i + 1
        elif not s:
            emptyCount += 1
            if emptyCount >= 2 and lastTable > fromIdx:
                return lastTable
        else:
            if _isPeriodLabel(s) or re.match(r"^[\d①②③④⑤][\.\)]\s*", s):
                emptyCount = 0
                continue
            if lastTable > fromIdx + 5:
                return lastTable
    return len(lines)


def findCostByNatureSection(contents: list[str]) -> str | None:
    """주석 콘텐츠에서 비용의 성격별 분류 섹션 찾기."""
    for content in contents:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            s = line.strip()
            if s.startswith("|"):
                continue
            m = re.match(r"^(\d{1,2})\.\s+(.+)", s)
            if m and "비용" in m.group(2) and "성격" in m.group(2):
                return "\n".join(lines[i : _findNextSection(lines, i + 1, r"^(\d{1,2})\.\s+")])
            m2 = re.match(r"^\((\d{1,2})\)\s+(.+)", s)
            if m2 and "비용" in m2.group(2) and "성격" in m2.group(2):
                return "\n".join(lines[i : _findNextSection(lines, i + 1, r"^\(\d{1,2}\)\s+")])

    for content in contents:
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "비용의 성격" in line or ("성격별" in line and "비용" in line):
                return "\n".join(lines[max(0, i - 1) : _findTableEnd(lines, i + 1)])

    return None


def parseCostByNature(sectionText: str) -> dict | None:
    """비용의 성격별 분류 섹션 파싱.

    Returns:
        {"당기": {항목: 금액}, "전기": {항목: 금액}, "order": [항목]} 또는 None
    """
    for fn in [_tryParseInlineTable, _tryParseSplitTable, _tryParseMultiColTable]:
        result = fn(sectionText)
        if result:
            return result
    return None


def _tryParseInlineTable(text):
    lines = text.split("\n")
    unit = detectUnit(text)
    tableLines = [l for l in lines if l.strip().startswith("|") and "---" not in l]
    if len(tableLines) < 3:
        return None

    headerLine, dataLines = None, []
    for line in tableLines:
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue
        if "단위" in " ".join(cells):
            continue
        if headerLine is None:
            if any(_isPeriodLabel(c) for c in cells) and len(cells) >= 2:
                headerLine = cells
                continue
        if headerLine and len(cells) >= 2:
            dataLines.append(cells)

    if not headerLine or not dataLines:
        return None

    danggiIdx = jeongiIdx = None
    for j, h in enumerate(headerLine):
        if _isDanggi(h) and danggiIdx is None:
            danggiIdx = j
        if _isJeongi(h) and jeongiIdx is None:
            jeongiIdx = j
    if danggiIdx is None and jeongiIdx is None:
        return None

    danggiData, jeongiData, order = {}, {}, []
    for cells in dataLines:
        name = _cleanAccountName(cells[0])
        if not name or _isSkipRow(name):
            continue
        if danggiIdx is not None and danggiIdx < len(cells):
            danggiData[name] = normalizeFromUnitScale(parseAmount(cells[danggiIdx]), unit)
        if jeongiIdx is not None and jeongiIdx < len(cells):
            jeongiData[name] = normalizeFromUnitScale(parseAmount(cells[jeongiIdx]), unit)
        if name not in order:
            order.append(name)

    return {"당기": danggiData, "전기": jeongiData, "order": order} if order else None


def _tryParseSplitTable(text):
    lines = text.split("\n")
    unit = detectUnit(text)
    blocks, cur, cl = [], None, []
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            p = _isPeriodLabel(s)
            if p:
                if cur and cl:
                    blocks.append((cur, cl))
                cur = p
                cl = []
            continue
        cells = [c.strip() for c in s.split("|") if c.strip()]
        if not cells:
            continue
        p = _isPeriodLabel("".join(cells).replace(" ", ""))
        if p and len(cells) <= 2:
            if cur and cl:
                blocks.append((cur, cl))
            cur = p
            cl = []
            continue
        if cur:
            cl.append(s)
    if cur and cl:
        blocks.append((cur, cl))

    if len(blocks) < 2:
        return None

    pd2, aa = {}, []
    for p, tl in blocks:
        acc = _parseSimpleRows(tl, unit)
        if not acc:
            continue
        pd2[p] = acc
        for n in acc:
            if n not in aa:
                aa.append(n)
    if not pd2 or not aa:
        return None
    return {"당기": pd2.get("당기", {}), "전기": pd2.get("전기", {}), "order": aa}


def _parseSimpleRows(tableLines, unit):
    accounts = {}
    for line in tableLines:
        if "---" in line:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        name = _cleanAccountName(cells[0])
        if not name or _isSkipRow(name):
            continue
        val = normalizeFromUnitScale(parseAmount(cells[-1]), unit)
        if name:
            accounts[name] = val
    return accounts


def _tryParseMultiColTable(text):
    lines = text.split("\n")
    unit = detectUnit(text)
    blocks, cur, cl = [], None, []
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            if cur:
                cl.append(s)
            continue
        p = _isPeriodLabel(s)
        if p:
            if cur and cl:
                blocks.append((cur, cl))
            cur = p
            cl = []
    if cur and cl:
        blocks.append((cur, cl))

    if len(blocks) < 2:
        return None

    pd2, aa = {}, []
    for p, tl in blocks:
        acc = _parseMultiColRows(tl, unit)
        if not acc:
            continue
        pd2[p] = acc
        for n in acc:
            if n not in aa:
                aa.append(n)
    if not pd2 or not aa:
        return None
    return {"당기": pd2.get("당기", {}), "전기": pd2.get("전기", {}), "order": aa}


def _parseMultiColRows(tableLines, unit):
    accounts, hp = {}, False
    for line in tableLines:
        if "---" in line:
            hp = True
            continue
        if not hp:
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 3:
            continue
        name = _cleanAccountName(cells[0])
        if not name or _isSkipRow(name) or "단위" in name:
            continue
        val = normalizeFromUnitScale(parseAmount(cells[-1]), unit)
        if name:
            accounts[name] = val
    return accounts
