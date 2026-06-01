"""옛 단일 "주석" 덩어리 → 항목별 sub-note 분해 (build, 수평화 정합).

2023 이전 보고서는 주석이 단일 "주석" 덩어리 한 행(`(첨부)재무제표␟주석`, disclosureKey 없음)으로
들어가고, 2023+ 는 항목별 ``NT_*`` 행으로 구체화된다. 두 era 의 rowIdentity 가 달라 수평화가 경계에서
끊긴다. 본 모듈이 옛 덩어리를 ``<SPAN>N. 제목</SPAN>`` 헤더로 분해해 각 sub-note 에 정부 표준
``NT_*`` 코드(``noteTaxonomyData``)를 부여 → 최근 NT_* 주석 행과 **같은 disclosureKey** 로 정합.

가산(additive) 설계: rowIdentity/spine/메인 격자 로직 불변 — 옛 덩어리 행을 항목별 행으로 *치환*만 한다.
표준 NT_* 코드는 회사 무관(재고자산 연결=NT_D826380·별도=NT_D826385)이라 글로벌 택소노미 1개로 충분.

LLM Specifications:
    AntiPatterns:
        - rowIdentity/spine 규칙 변경 금지 — 표준 NT_* 부여로 기존 keyed identity 가 자동 정렬.
        - 택소노미 미매칭 헤더 추정 매핑 금지 — 매칭된 항목만 sub-note 화(나머지는 덩어리째 드롭).
        - 메인 14-col 격자 컬럼 schema 변경 금지 — 행 치환만.
    OutputSchema:
        - ``dechunkNotes(df) -> pl.DataFrame`` (동일 schema, 주석 덩어리 행 → sub-note 행 치환).
    Prerequisites:
        - horizontalize 후 14-col DataFrame. noteTaxonomyData.NOTE_TAXONOMY.
    Freshness:
        - build 단계 (panel.parquet 생산 시 1회).
    Dataflow:
        - horizontalize → dechunkNotes → resolveBatch → write.
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

import re

import polars as pl

from .noteTaxonomyData import NOTE_TAXONOMY

_NORM_RE = re.compile(r"[()·\s]")
# "N. 제목" 노트 헤더 — 태그 무관(SPAN/P/B), 콜론 허용, 태그경계(`>`) 앵커로 본문 중간
# 숫자열 오탐 차단. 연도별 포맷차(2015 `<SPAN>N.제목</SPAN>` · 2022 `>N.제목:`)를 한 패턴으로 흡수.
_HEADER_RE = re.compile(r">\s*(\d{1,2})\.\s*([가-힣A-Za-z][^<:]{0,23}?)\s*[:<]")
# 분해된 sub-note 의 표시용 section (최근 itemized 구조와 동일 라벨).
_NOTE_SECTION = {"consolidated": "3. 연결재무제표 주석", "standalone": "5. 재무제표 주석"}


def _norm(s: str | None) -> str:
    return _NORM_RE.sub("", s or "")


def dechunkNotes(df: pl.DataFrame) -> pl.DataFrame:
    """옛 "주석" 덩어리 행을 N.제목 헤더로 분해 → 표준 NT_* sub-note 행 치환.

    Args:
        df: horizontalize 후 14-col panel DataFrame (한 period).

    Returns:
        동일 schema DataFrame — 옛 주석 덩어리 행이 항목별 sub-note 행(disclosureKey=NT_*)으로 치환.
        덩어리 없거나 매칭 0 이면 입력 그대로.
    """
    if df.is_empty() or "sectionLeaf" not in df.columns or "contentRaw" not in df.columns:
        return df
    chunkMask = (pl.col("sectionLeaf") == "주석") & pl.col("disclosureKey").is_null()
    chunks = df.filter(chunkMask)
    if chunks.is_empty():
        return df

    newRows: list[dict] = []
    for row in chunks.iter_rows(named=True):
        scope = "consolidated" if "연결" in _norm(row.get("chapter")) else "standalone"
        cr = row.get("contentRaw") or ""
        # 택소노미 매칭 헤더만 경계 — (pos, 제목, NT_*). 본문 중간 숫자열은 매칭 0 이라 경계 안 됨.
        marks: list[tuple[int, str, str]] = []
        for m in _HEADER_RE.finditer(cr):
            key = NOTE_TAXONOMY.get(f"{scope}|{_norm(m.group(2))}")
            if key:  # 미등재 항목은 추정 매핑 안 함
                marks.append((m.start(), m.group(2).strip(), key))
        # 매칭헤더 i → 다음 매칭헤더 사이 = 노트 1개(헤더+본문+테이블). 중복키는 최장 본문 채택.
        best: dict[str, dict] = {}
        for i, (pos, title, key) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(cr)
            seg = cr[pos:end]
            prev = best.get(key)
            if prev is not None and len(prev["contentRaw"]) >= len(seg):
                continue  # TOC 등 짧은 중복 — 본문 섹션(최장) 우선
            nr = dict(row)
            nr["disclosureKey"] = key
            nr["blockLeaf"] = title
            nr["sectionLeaf"] = _NOTE_SECTION[scope]
            nr["contentRaw"] = seg
            best[key] = nr
        newRows.extend(best.values())

    if not newRows:
        return df  # 매칭 0 — 덩어리 보존(graceful)
    rest = df.filter(~chunkMask)
    sub = pl.DataFrame(newRows, schema=df.schema)
    return pl.concat([rest, sub], how="vertical")
