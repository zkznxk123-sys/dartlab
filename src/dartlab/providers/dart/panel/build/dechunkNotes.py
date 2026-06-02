"""미분해 주석 덩어리 → 항목별 sub-note 분해 (build, 수평화 정합, 무손실).

2023+ 보고서는 주석이 항목별 ``NT_*`` 행으로 구체화되나, 그 이전(또는 비표준 회사)은 주석이
disclosureKey 없는 **통짜 블록**으로 들어간다. 그 블록 구조가 연도·회사마다 다르다:
    - 별도 "주석" 섹션 (sectionLeaf="주석" / "3. 연결재무제표 주석")
    - statement+주석 합본 mega-block (sectionLeaf="(첨부)재무제표" / "2. 연결재무제표" — "주석" 없음)

본 모듈은 **재무제표 영역 gate**(chapter/sectionLeaf 의 "재무제표"·chapter 의 "재무에관한")로 노트 블록을
선제한해 사업보고서 TOC 오염을 차단하고, 그 안의 ``N. 제목`` 헤더를 **dominant-only 뼈대**
(``noteTaxonomyData`` — 전 corpus XBRL 학습, 모호제목 제외)로 매칭한다. 매칭된 노트만 표준 ``NT_*`` 코드로
분해해 최근 NT_* 행과 **같은 disclosureKey** 로 정합(임계 없음 — 1개라도 매칭되면 itemize), 미매칭/모호 제목은
narrative 유지. 노트 앞 **preamble(재무제표 본표 등)은 원 블록에 보존**(byte 무손실 partition). 표준 NT_* 는
회사 무관(재고자산 연결=NT_D826380·별도=NT_D826385).

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

    # 재무제표 노트 영역 gate — disclosureKey-null + (chapter/sectionLeaf 에 "재무제표" OR sectionLeaf 에 "주석").
    # 옛 "(첨부)재무제표" mega-block·최근 "N.연결재무제표 주석"·mis-chapter("II.사업의내용/3.연결재무제표 주석",
    # READ anchorLatest 가 재-chapter)는 포착하되, "III.재무에관한사항" 챕터 하위 비-노트 절(배당·MD&A·주주)과
    # 사업보고서 TOC 는 제외 — chapter "재무에관한"으로 넓히면 그 절들이 새어들어 phantom 노트 발생(실측 FP).
    _ctxNorm = (pl.col("chapter").fill_null("") + pl.col("sectionLeaf").fill_null("")).str.replace_all(r"[()·\s]", "")
    chunkMask = pl.col("disclosureKey").is_null() & (
        _ctxNorm.str.contains("재무제표") | pl.col("sectionLeaf").fill_null("").str.contains("주석")
    )
    candidates = df.filter(chunkMask)
    if candidates.is_empty():
        return df

    # 순수 분류만 — gate→split→match→preamble. 본문+첨부·전환연도 중복 제거는 READ(dedupKeyed)가
    # (key,scope,period)로 일괄(xbrlClass native 우선) → BUILD 는 dedup 안 함(책임 분리, 덕지덕지 0).
    kept: list[dict] = []  # 노트 블록은 preamble 행, 매칭 0 블록은 원본
    subNotes: list[dict] = []
    changed = False
    for row in candidates.iter_rows(named=True):
        scope = _scopeOf(row)
        cr = row.get("contentRaw") or ""
        # 노트 헤더는 1,2,…N 단조증가. 번호가 역행하면 노트 본문 내 표/목록 항목('<TD>3.배당금</TD>')을
        # 헤더로 오인한 것(phantom) → 거부. 매칭 헤더만 마크하고 번호 단조성으로 표·리스트 항목 차단.
        marks: list[tuple[int, str, str]] = []
        lastNum = 0
        for m in _HEADER_RE.finditer(cr):
            num = int(m.group(1))
            if num <= lastNum:
                continue  # 번호 역행 = 표/목록 항목, 헤더 아님
            key = NOTE_TAXONOMY.get(f"{scope}|{_norm(m.group(2))}")  # dominant-only 뼈대(미등재→narrative)
            if key:
                marks.append((m.start(), m.group(2).strip(), key))
                lastNum = num
        if not marks:
            kept.append(row)  # 매칭 노트 0 (비표준 주석) — 원 블록 보존. 임계 없음.
            continue
        changed = True
        # 노트 앞 preamble(재무제표 본표·섹션 헤더)은 원 블록에 보존 — 비어있지 않으면 행 유지.
        preamble = cr[: marks[0][0]]
        if preamble.strip():
            pre = dict(row)
            pre["contentRaw"] = preamble
            kept.append(pre)
        # 매칭헤더 i → 다음 매칭헤더 사이 = 노트 1개(헤더+본문+테이블). 모두 emit, dedup 은 READ.
        for i, (pos, title, key) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(cr)
            nr = dict(row)
            nr["disclosureKey"] = key
            nr["blockLeaf"] = title
            nr["sectionLeaf"] = _NOTE_SECTION[scope]
            nr["contentRaw"] = cr[pos:end].lstrip("> \n\t")  # 헤더 경계 앵커('>')·여백 제거
            subNotes.append(nr)

    if not changed:
        return df
    nonCand = df.filter(~chunkMask)  # keyed 행 + 비-주석 null 블록(TOC) — 전부 불변 통과
    parts = [nonCand]
    if kept:
        parts.append(pl.DataFrame(kept, schema=df.schema))
    if subNotes:
        parts.append(pl.DataFrame(subNotes, schema=df.schema))
    return pl.concat(parts, how="vertical")
