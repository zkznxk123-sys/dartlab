"""미분해 주석 덩어리 → 항목별 제목 행으로 **분류**(build, 헤딩 분할만 — NT_ 정렬은 READ).

2023+ 보고서는 주석이 항목별 ``NT_*`` 행(XBRL 태깅, native disclosureKey)으로 구체화되나, 그 이전(또는
비표준 회사)은 주석이 disclosureKey 없는 **통짜 블록**으로 들어간다. 그 블록 구조가 연도·회사마다 다르다:
    - 별도 "주석" 섹션 (sectionLeaf="주석" / "3. 연결재무제표 주석")
    - statement+주석 합본 mega-block (sectionLeaf="(첨부)재무제표" / "2. 연결재무제표" — "주석" 없음)

**책임 = 분류(헤딩 분할)만.** 본 모듈은 **재무제표 영역 gate**(chapter/sectionLeaf 의 "재무제표"·"주석")로 노트
블록을 선제한해 사업보고서 TOC 오염을 차단하고, 그 안의 ``N. 제목`` 헤더를 **통합 검출**(``_detectHeaders``)한다
— delimited(`<SPAN>1. 재고자산</SPAN>`)와 옛 concatenated(`…비츠로시스1. 일반사항</P>` — 제목이 산문·본문에
붙음) 양 포맷을 ``_NUMDOT`` 한 패턴으로 후보화하고, **뼈대 사전**(``noteTaxonomyData`` — 전 corpus XBRL 학습,
모호제목 제외) **최장 prefix-match** + **표셀 가드** + **번호 monotonic** 으로 진짜 헤더만 가려 노트 1개당 한 행으로
쪼갠다(``blockLeaf``=제목). **disclosureKey 는 null 로 둔다 — NT_ 정체성 부여(수평화 정렬)는 READ
(``read.alignNotes``)가 회사 최근 XBRL 뼈대로 read-time 처리**(taxonomy·정렬 개선이 재빌드 무관 = 빌드 동결).
헤딩 분할이 잘못됐을 때만 재빌드. 노트 앞 **preamble(재무제표 본표 등)은 원 블록에 보존**(content 무손실 —
preamble + Σ제목행 = 원 블록 byte-exact, slice 경계 strip 0).

LLM Specifications:
    AntiPatterns:
        - BUILD 에서 NT_ 코드 베이킹 금지 — 정렬은 READ(재빌드 분리). BUILD 는 제목 분할만.
        - 택소노미 미매칭 헤더 추정 매핑 금지 — 매칭된 항목만 분할.
        - 노트 앞 preamble 드롭 금지 — mega-block 은 preamble 이 재무제표 본표라 손실되면 안 됨(원 행 보존).
        - 메인 14-col 격자 컬럼 schema 변경 금지 — 행 분할만.
    OutputSchema:
        - ``dechunkNotes(df) -> pl.DataFrame`` (동일 schema; 노트 블록 → preamble 행 + 제목별 null-key 행).
    Prerequisites:
        - horizontalize 후 14-col DataFrame. noteTaxonomyData.NOTE_TAXONOMY(헤더 검출용).
    Freshness:
        - build 단계 (헤딩 분할 — 검출 규칙 변경 시에만 재빌드).
    Dataflow:
        - horizontalize → resolveBatch(native NT_) → dechunkNotes(제목 분할) → write. 정렬은 read.alignNotes.
    TargetMarkets:
        - KR (DART).
"""

from __future__ import annotations

import re
from collections import defaultdict

import polars as pl

from ..mapper import NOTE_TITLE_NORM_PATTERN  # 제목/맥락 정규화 패턴 단일 SSOT (build 검출·read 정렬 공유)
from ..mapper import normalizeTitle as _norm
from .noteTaxonomyData import NOTE_TAXONOMY

# "N. 제목" 노트 헤더 후보 — 번호.만 매칭하고 제목은 **소비 안 함**(lookahead). `.{0,40}` 으로 제목을 삼키면
# finditer 가 40자 내 다음 헤더를 건너뛴다(짧은 노트 누락) → 제목은 _detectHeaders 가 m.end() 슬라이스로 읽는다.
# delimited(`<SPAN>1. 재고자산</SPAN>`)·concatenated(`…비츠로시스1. 일반사항</P>` 번호.제목이 산문에 붙음) 양 포맷
# 흡수. 진짜 헤더 판정 = taxonomy 최장 prefix-match + monotonic + 표셀 가드(_detectHeaders). delimited 의 `>`/`[:<]`
# 경계는 포섭되는 특수경우(SSOT 단일 검출).
_NUMDOT = re.compile(r"(\d{1,2})\s*\.\s*(?=[가-힣A-Za-z(])")
_TITLE_SPAN = 44  # 헤더 위치 뒤 제목 prefix-match 용 슬라이스 길이.
_MINLEN = 3  # 이 길이 미만(2자) 제목은 경계(뒤 char 비-한글)일 때만 — '사채<' 허용, 한글로 이어지면 모호라 거부.
# 분해된 sub-note 의 표시용 section (최근 itemized 구조와 동일 라벨).
_NOTE_SECTION = {"consolidated": "3. 연결재무제표 주석", "standalone": "5. 재무제표 주석"}


def _buildScopeTitles() -> dict[str, list[tuple[str, str]]]:
    """``NOTE_TAXONOMY`` → ``{scope: [(정규화제목, NT_코드), …]}`` 최장제목 우선 인덱스.

    제목이 긴 것부터 매칭해 '유형자산및무형자산'을 '유형자산'보다 먼저 잡는다(최장 prefix). import 시 1회 파생.
    """
    idx: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for key, code in NOTE_TAXONOMY.items():
        scope, title = key.split("|", 1)
        idx[scope].append((title, code))
    for scope in idx:
        idx[scope].sort(key=lambda tc: -len(tc[0]))
    return idx


# scope → 최장우선 (정규화제목, 코드) 뼈대 인덱스 — dechunk 헤더 검출의 prefix 사전.
_SCOPE_TITLES: dict[str, list[tuple[str, str]]] = _buildScopeTitles()


def _scopeOf(row: dict) -> str:
    """era-stable "연결" 마커 — 옛 era 는 chapter("(첨부)연결재무제표"), 분기는 sectionLeaf("3.연결…주석")."""
    return "consolidated" if "연결" in _norm(row.get("chapter")) + _norm(row.get("sectionLeaf")) else "standalone"


def _inTableCell(cr: str, pos: int) -> bool:
    """``pos`` 가 표 셀(``<TD>…</TD>``) 내부인지 — 직전 가장 가까운 ``<TD`` 가 ``</TD>``보다 뒤면 셀 안.

    표 본문의 번호 항목('``<TD>3. 배당금</TD>``')이 taxonomy 와 우연히 prefix-match 해 phantom 헤더가 되는 것을
    차단(전 corpus 유일 오탐 클래스, 실측 7.3%). monotonic 가드와 직교 — 표는 번호가 단조여도 셀이라 거부.
    """
    return cr.rfind("<TD", 0, pos) > cr.rfind("</TD>", 0, pos)


def _detectHeaders(cr: str, scope: str) -> list[tuple[int, str, str]]:
    """노트 본문에서 진짜 ``N. 제목`` 헤더만 추출 → ``[(pos, 정규화제목, NT_코드), …]`` (위치순·monotonic).

    delimited/concatenated 양 포맷을 ``_NUMDOT`` 한 패턴으로 후보화한 뒤, (1) 표셀 제외(``_inTableCell``),
    (2) ``_SCOPE_TITLES`` 최장 prefix-match(len ≥ ``_MINLEN``), (3) 번호 monotonic 증가 — 4중 가드로 phantom 억제.
    미매칭(비표준/모호 제목)은 narrative 유지(추정 0). 제목은 정규화형(READ ``anchorLatest`` 가 최신 era 라벨로 재앵커).
    """
    titles = _SCOPE_TITLES.get(scope, ())
    marks: list[tuple[int, str, str]] = []
    lastNum = 0
    for m in _NUMDOT.finditer(cr):
        num = int(m.group(1))
        if num <= lastNum:
            continue  # 번호 역행 = 표/목록 항목, 헤더 아님
        if _inTableCell(cr, m.start()):
            continue  # 표 셀 내부 번호 항목 — phantom 차단
        cand = _norm(cr[m.end() : m.end() + _TITLE_SPAN])  # 제목은 소비 안 한 본문에서 슬라이스
        for title, code in titles:  # 최장 prefix 우선
            if not cand.startswith(title):
                continue
            end = len(title)
            # 3자+ 제목은 concatenated(제목이 한글 본문에 직접 붙음) 분해 허용. 2자 제목은 한글 본문과 구분
            # 불가라 경계(뒤 char 가 비-한글: 태그/괄호/공백/끝)일 때만 — '사채</SPAN>' 허용, '사채권…' 거부.
            if end >= _MINLEN or end >= len(cand) or not ("가" <= cand[end] <= "힣"):
                marks.append((m.start(), title, code))
                lastNum = num
            break  # 최장 매칭에서 판정 — 더 짧은 prefix 로 내려가지 않음
    return marks


def dechunkNotes(df: pl.DataFrame) -> pl.DataFrame:
    """미분해 주석 블록을 N.제목 헤더로 **분할**(제목 행, null key) — NT_ 정렬은 READ(alignNotes).

    Args:
        df: horizontalize+resolveBatch 후 14-col panel DataFrame (한 period).

    Returns:
        동일 schema DataFrame — 노트 블록이 [preamble 행(재무제표 본표 등) + 제목별 행(blockLeaf=제목,
        disclosureKey=null)]으로 분할. 노트 블록 없으면 입력 그대로. preamble + Σ제목행 = 원 블록(byte-exact 무손실).
    """
    if df.is_empty() or "contentRaw" not in df.columns or "sectionLeaf" not in df.columns:
        return df

    # 재무제표 노트 영역 gate — disclosureKey-null + (chapter/sectionLeaf 에 "재무제표" OR sectionLeaf 에 "주석").
    # 옛 "(첨부)재무제표" mega-block·최근 "N.연결재무제표 주석"·mis-chapter("II.사업의내용/3.연결재무제표 주석",
    # READ anchorLatest 가 재-chapter)는 포착하되, "III.재무에관한사항" 챕터 하위 비-노트 절(배당·MD&A·주주)과
    # 사업보고서 TOC 는 제외 — chapter "재무에관한"으로 넓히면 그 절들이 새어들어 phantom 노트 발생(실측 FP).
    _ctxNorm = (pl.col("chapter").fill_null("") + pl.col("sectionLeaf").fill_null("")).str.replace_all(
        NOTE_TITLE_NORM_PATTERN, ""
    )
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
        # 통합 검출 — delimited/concatenated 양 포맷 N.제목 헤더를 taxonomy prefix-match + 표셀가드 + monotonic 로
        # 추출(_detectHeaders). 미매칭/모호 제목은 narrative 유지(추정 0, 임계 없음).
        marks = _detectHeaders(cr, scope)
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
        # 매칭헤더 i → 다음 매칭헤더 사이 = 노트 1개(헤더+본문+테이블). 제목만 박고 disclosureKey 는 null —
        # NT_ 정체성 부여(뼈대 정렬)는 READ(alignNotes)가 회사 최근 XBRL 뼈대로 read-time 처리(재빌드 무관).
        # pos 는 번호('N.') 위치라 cr[pos:end] 는 byte-exact(preamble + Σsub = 원 cr, 무손실). scope 는
        # sectionLeaf(_NOTE_SECTION 의 '연결' 마커)로 READ 가 복원.
        for i, (pos, title, _key) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(cr)
            nr = dict(row)
            nr["disclosureKey"] = None
            nr["blockLeaf"] = title
            nr["sectionLeaf"] = _NOTE_SECTION[scope]
            nr["contentRaw"] = cr[pos:end]
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
