"""미분해 주석 덩어리 → 항목별 sub-note 분해 (build, 수평화 정합, 무손실).

2023+ 보고서는 주석이 항목별 ``NT_*`` 행으로 구체화되나, 그 이전(또는 비표준 회사)은 주석이
disclosureKey 없는 **통짜 블록**으로 들어간다. 그 블록 구조가 연도·회사마다 다르다:
    - 별도 "주석" 섹션 (sectionLeaf="주석" / "3. 연결재무제표 주석")
    - statement+주석 합본 mega-block (sectionLeaf="(첨부)재무제표" / "2. 연결재무제표" — "주석" 없음)

본 모듈은 sectionLeaf 문자열이 아니라 **본문의 ``N. 제목`` 노트 헤더**(택소노미 매칭 ≥ ``_MIN_HEADERS``)
로 노트 블록을 구조 무관 감지한다. 각 노트를 표준 ``NT_*`` 코드(``noteTaxonomyData``)로 분해해 최근
NT_* 행과 **같은 disclosureKey** 로 정합하고, 노트 앞 **preamble(재무제표 본표 등)은 원 블록에 보존**
(byte 무손실 partition). 표준 NT_* 는 회사 무관(재고자산 연결=NT_D826380·별도=NT_D826385).

LLM Specifications:
    AntiPatterns:
        - rowIdentity/spine 규칙 변경 금지 — 표준 NT_* 부여로 기존 keyed identity 가 자동 정렬.
        - 택소노미 미매칭 헤더 추정 매핑 금지 — 매칭된 항목만 sub-note 화.
        - 노트 앞 preamble 드롭 금지 — mega-block 은 preamble 이 재무제표 본표라 손실되면 안 됨(원 행 보존).
        - 메인 14-col 격자 컬럼 schema 변경 금지 — 행 분할만.
    OutputSchema:
        - ``dechunkNotes(df) -> pl.DataFrame`` (동일 schema; 노트 블록 → preamble 행 + 항목별 sub-note 행).
    Prerequisites:
        - horizontalize 후 14-col DataFrame. noteTaxonomyData.NOTE_TAXONOMY.
    Freshness:
        - build 단계 (panel.parquet 생산 시 1회).
    Dataflow:
        - horizontalize → resolveBatch → dechunkNotes → write.
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
# 노트 블록 판정 최소 매칭 헤더 수 — 본문이 우연히 노트 제목을 언급한 블록(매칭 0~2) 오탐 차단.
_MIN_HEADERS = 3


def _norm(s: str | None) -> str:
    return _NORM_RE.sub("", s or "")


def _scopeOf(row: dict) -> str:
    """era-stable "연결" 마커 — 옛 era 는 chapter("(첨부)연결재무제표"), 분기는 sectionLeaf("3.연결…주석")."""
    return "consolidated" if "연결" in _norm(row.get("chapter")) + _norm(row.get("sectionLeaf")) else "standalone"


def dechunkNotes(df: pl.DataFrame) -> pl.DataFrame:
    """미분해 주석 블록을 N.제목 헤더로 분해 → preamble 보존 + 표준 NT_* sub-note 행.

    Args:
        df: horizontalize+resolveBatch 후 14-col panel DataFrame (한 period).

    Returns:
        동일 schema DataFrame — 노트 블록이 [preamble 행(재무제표 본표 등) + 항목별 NT_* sub-note 행]으로
        분할. 노트 블록 없으면 입력 그대로. preamble + sub-note = 원 블록(byte 무손실 partition).
    """
    if df.is_empty() or "contentRaw" not in df.columns or "sectionLeaf" not in df.columns:
        return df

    # 이미 itemized native NT_*(xbrlClass NT_C_/NT_S_) 가 있는 scope 는 그 블록을 건드리지 않는다
    # — 전환연도(본문 NT_* + (첨부)덩어리 공존) 이중수록 차단.
    nativeScopes: set[str] = set()
    if "xbrlClass" in df.columns:
        native = df.filter(pl.col("disclosureKey").str.starts_with("NT_") & pl.col("xbrlClass").is_not_null())
        for xc in native["xbrlClass"].to_list():
            nativeScopes.add("standalone" if "_S" in (xc or "")[:5] else "consolidated")

    nullMask = pl.col("disclosureKey").is_null()
    candidates = df.filter(nullMask)
    if candidates.is_empty():
        return df

    kept: list[dict] = []  # disclosureKey-null 후보 행 (노트블록은 preamble 로 치환, 그 외 원본)
    # df-level dedup — 같은 표준 NT_* 가 본문("III.재무")·첨부("(첨부)재무제표") 여러 블록에 중복
    # 수록되므로, disclosureKey 당 **최장 본문 1개**만 채택. 안 하면 READ collapse 가 같은 노트를
    # join 해 셀 content 가 2~3배 증식한다(연결/별도는 NT_ D-code 가 달라 자동 분리).
    best: dict[str, dict] = {}
    changed = False
    for row in candidates.iter_rows(named=True):
        scope = _scopeOf(row)
        cr = row.get("contentRaw") or ""
        marks: list[tuple[int, str, str]] = []
        if scope not in nativeScopes:
            for m in _HEADER_RE.finditer(cr):
                key = NOTE_TAXONOMY.get(f"{scope}|{_norm(m.group(2))}")
                if key:  # 미등재 항목은 추정 매핑 안 함
                    marks.append((m.start(), m.group(2).strip(), key))
        if len(marks) < _MIN_HEADERS:
            kept.append(row)  # 노트 블록 아님(또는 native 존재) — 원본 보존
            continue
        changed = True
        # 노트 앞 preamble(재무제표 본표·섹션 헤더)은 원 블록에 보존 — 비어있지 않으면 행 유지.
        preamble = cr[: marks[0][0]]
        if preamble.strip():
            pre = dict(row)
            pre["contentRaw"] = preamble
            kept.append(pre)
        # 매칭헤더 i → 다음 매칭헤더 사이 = 노트 1개(헤더+본문+테이블).
        for i, (pos, title, key) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(cr)
            seg = cr[pos:end].lstrip("> \n\t")  # 헤더 경계 앵커('>')·여백 제거
            prev = best.get(key)
            if prev is not None and len(prev["contentRaw"]) >= len(seg):
                continue  # 다른 블록/ TOC 의 짧은 중복 — 최장 본문 우선
            nr = dict(row)
            nr["disclosureKey"] = key
            nr["blockLeaf"] = title
            nr["sectionLeaf"] = _NOTE_SECTION[scope]
            nr["contentRaw"] = seg
            best[key] = nr

    if not changed:
        return df
    nonCand = df.filter(~nullMask)
    parts = [nonCand]
    if kept:
        parts.append(pl.DataFrame(kept, schema=df.schema))
    if best:
        parts.append(pl.DataFrame(list(best.values()), schema=df.schema))
    return pl.concat(parts, how="vertical")
