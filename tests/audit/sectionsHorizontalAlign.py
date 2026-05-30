"""sections wide-format 수평화 정합성 검증 (사용자 SSOT 게이트).

docs parquet 본문을 sections() 가 wide-format DataFrame 으로 변환할 때 다음 4
조건을 강제:

1. **분기 disclaimer body = 1 row** — `"※ 기업공시서식 작성기준에 따라 분기보고서에는
   본 항목을 기재하지 아니하였습니다."` 같은 disclaimer 가 occurrence 카운터로
   분산되지 않고 단일 row 로 집계.
2. **표 segmentKey 가 *내용 무관 위치* 가 아닌 *내용 헤더* 기반** — 옛 보고서의
   "1번째 표" 와 최근의 "1번째 표" 가 다른 의미면 다른 row 로 분리. 같은 의미면
   wide-format 의 같은 row 로 align.
3. **같은 의미 heading 은 단일 row** — bracket 헤딩 (`[연결대상 종속회사 현황(요약)]`)
   의 level 매핑 잘못으로 같은 의미 heading 이 다른 textPath 두 row 로 분산되는
   회귀 차단.
4. **textPath 에 raw HTML entity / `@topic > @topic` 중복 없음** — `&cr` 같은 raw
   entity, alias stack push 중복으로 인한 segmentKey 오염 차단.

본 게이트는 SK하이닉스 (000660) 의 companyOverview + companyHistory 두 topic 으로
검증. 사용자 SSOT — 변경 단위 PR 마다 본 케이스 통과 강제.

실행:
    uv run python -X utf8 tests/audit/sectionsHorizontalAlign.py
"""

from __future__ import annotations

import hashlib
import sys

import polars as pl

from dartlab.providers.dart.docs.sections.pipeline import (
    clearPreparedCache,
    sections,
)


def _tableHeaderHash(md: str) -> str:
    """표 markdown 의 첫 데이터 행 (separator 전) cells 의 hash.

    Args:
        md: markdown 표 본문.

    Returns:
        str — blake2b 4-byte hex hash, 또는 `"empty"` (table 형태 아님).

    Example:
        >>> _tableHeaderHash("| a | b |\\n| --- | --- |\\n| 1 | 2 |")
        'd5...'
    """
    for line in md.strip().split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().lower() for c in stripped.strip("|").split("|")]
        if all(set(c) <= {"-", ":"} for c in cells if c):
            continue
        norm = tuple(sorted(c for c in cells if c))
        return hashlib.blake2b(str(norm).encode("utf-8"), digest_size=4).hexdigest()
    return "empty"


def checkSkHynixOverview() -> list[str]:
    """SK하이닉스 (000660) companyOverview 4 조건 검증.

    Returns:
        list[str] — 실패 메시지 list (빈 list = 모두 통과).
    """
    failures: list[str] = []
    df = sections("000660", topics={"companyOverview"})
    if df is None or df.height == 0:
        return ["[companyOverview] sections 출력 없음"]

    periodCols = [c for c in df.columns if c.startswith("20")]
    quarterPeriods = [c for c in periodCols if "Q" in c]

    # 조건 1: 분기 disclaimer = 1 row
    disclaimerRows = []
    for r in df.iter_rows(named=True):
        for p in quarterPeriods:
            v = r.get(p)
            if v and "기업공시서식" in str(v) and "기재하지 아니하였습니다" in str(v):
                disclaimerRows.append((r["blockOrder"], r["segmentKey"]))
                break
    if len(disclaimerRows) != 1:
        failures.append(
            f"[companyOverview] 조건 1 실패 — 분기 disclaimer row {len(disclaimerRows)} 개 "
            f"(기대 = 1). rows: {disclaimerRows}"
        )

    # 조건 3: 같은 의미 heading 의 *최신 annual cell* 시점에서 단일 row.
    # 옛 보고서 (예 2018) 와 최근 본문 구조가 진짜 달라 다른 row 인 건 정상 — 본문 SSOT.
    # 최신 annual (2025) cell 보유 기준으로 같은 textPath 의 row 가 1 개여야 사용자
    # 화면 (최신 위주) 의 heading 비분산.
    overviewHeadingRows = []
    for r in df.iter_rows(named=True):
        if r["blockType"] != "text" or r.get("textNodeType") != "heading":
            continue
        path = str(r.get("textPath") or "")
        if path != "연결대상 종속회사 개황":
            continue
        # 최신 annual period 에 cell 값 있는 row 만 — 옛 본문 구조 차이는 허용
        if r.get("2025") is None:
            continue
        overviewHeadingRows.append((r["blockOrder"], path))
    if len(overviewHeadingRows) > 1:
        failures.append(
            f"[companyOverview] 조건 3 실패 — '연결대상 종속회사 개황' heading 이 최신 "
            f"annual 시점에 {len(overviewHeadingRows)} row 분산 (기대 = 1). rows: {overviewHeadingRows}"
        )

    # 조건 4a: textPath 에 raw HTML entity 없음
    entityRows = []
    for r in df.iter_rows(named=True):
        path = str(r.get("textPath") or "")
        if "&cr" in path or "&amp" in path or "&lt" in path or "&gt" in path:
            entityRows.append((r["blockOrder"], path[:50]))
    if entityRows:
        failures.append(
            f"[companyOverview] 조건 4a 실패 — textPath 에 raw HTML entity 잔존 "
            f"({len(entityRows)} 건). sample: {entityRows[:3]}"
        )

    # 조건 4b: textPath 에 `@topic:X > @topic:X` 중복 없음
    aliasRows = []
    for r in df.iter_rows(named=True):
        path = str(r.get("textPath") or "")
        key = str(r.get("textPathKey") or "")
        if "@topic:" in key and key.count("@topic:") >= 2:
            aliasRows.append((r["blockOrder"], key[:80]))
    if aliasRows:
        failures.append(
            f"[companyOverview] 조건 4b 실패 — textPathKey 에 @topic alias 중복 누적 "
            f"({len(aliasRows)} 건). sample: {aliasRows[:3]}"
        )

    return failures


def checkSkHynixHistory() -> list[str]:
    """SK하이닉스 (000660) companyHistory 조건 2 (옛/최근 표 분리) 검증.

    Returns:
        list[str] — 실패 메시지 list.
    """
    failures: list[str] = []
    df = sections("000660", topics={"companyHistory"})
    if df is None or df.height == 0:
        return ["[companyHistory] sections 출력 없음"]

    periodCols = [c for c in df.columns if c.startswith("20")]

    # 조건 2: 옛 회사 연혁 표 (2016~2021Q1, hash A) 와 최근 본점소재지 표
    # (2021Q2~2025, hash B) 가 다른 row 로 분리되어야.
    oldGroupCells = ["2016Q1", "2016Q2", "2016", "2017", "2018", "2019", "2020", "2021Q1"]
    newGroupCells = ["2021Q2", "2021", "2022Q2", "2022", "2023", "2024", "2025"]

    # 각 row 의 cell 들 중 옛 group 과 새 group 의 hash 가 *둘 다* 한 row 에 등장 → fail
    mixedRows = []
    for r in df.iter_rows(named=True):
        if r["blockType"] != "table":
            continue
        oldHashes: set[str] = set()
        newHashes: set[str] = set()
        for p in oldGroupCells:
            v = r.get(p)
            if v is not None:
                oldHashes.add(_tableHeaderHash(str(v)))
        for p in newGroupCells:
            v = r.get(p)
            if v is not None:
                newHashes.add(_tableHeaderHash(str(v)))
        # 같은 row 에 옛·새 그룹의 다른 hash 둘 다 등장하면 다른 의미 표 mix
        allHashes = (oldHashes | newHashes) - {"empty"}
        if len(allHashes) >= 2 and oldHashes and newHashes and (oldHashes - newHashes) and (newHashes - oldHashes):
            mixedRows.append((r["blockOrder"], r["segmentKey"], sorted(allHashes)))
    if mixedRows:
        failures.append(
            f"[companyHistory] 조건 2 실패 — 표 row {len(mixedRows)} 개에 옛·최근 *다른* "
            f"표가 mix (다른 hash 둘 다 등장). sample: {mixedRows[:3]}"
        )

    return failures


def main() -> int:
    """sections 수평화 게이트 — 4 조건 검증.

    Returns:
        int — exit code (0 = pass, 1 = fail).
    """
    clearPreparedCache()
    allFailures: list[str] = []
    allFailures.extend(checkSkHynixOverview())
    allFailures.extend(checkSkHynixHistory())

    if not allFailures:
        print("[sections-horizontal-align] OK — 4 조건 모두 통과 (SK하이닉스 companyOverview + companyHistory)")
        return 0

    print(f"[sections-horizontal-align] FAIL — {len(allFailures)} 건:")
    for msg in allFailures:
        print(f"  - {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
