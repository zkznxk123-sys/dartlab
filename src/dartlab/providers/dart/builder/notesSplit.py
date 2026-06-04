"""재무제표 주석 sub-topic 수평화 — financialNotes/consolidatedNotes 분할.

DART 사업보고서의 "5. 재무제표 주석" / "3. 연결재무제표 주석" 은 31~32 개의
N. 헤딩 (`1. 일반적 사항`, `2. 중요한 회계처리방침`, ... `32. 보고기간후사건`)
으로 구성된다. 전체가 한 topic 이라 길고 느림 — 본 모듈이 sections frame 의
notes row 들을 N. 패턴으로 sub-topic 분할한다.

알고리즘 (의미 기반 — 회사별 번호 차이 무시):
1. notes row 의 본문 첫 줄에서 ``N. {한글 이름}`` 추출.
2. *한글 이름* 을 normalize + alias map 적용 → NOTES_SUB_SECTIONS 의 standard
   (번호, slug) 매칭. 회사가 임의 N 번호 매겨도 의미가 같으면 같은 standard.
3. 매칭 실패 시 회사 N 번호 fallback (옛 behavior).
4. ``cumsum`` 으로 연속 row 그룹 — 다음 헤딩 만날 때까지 같은 그룹.
5. 각 그룹의 topic 을 ``{parent}_{standardNN}_{slug}`` 로 rewrite.

회귀 사례 (37% mismatch rate across 6 종목 192 topic):
- 005380 "30. 퇴직급여제도" → 표준 14 definedBenefit (회사 30 번이 표준 14)
- 005930 "4. 공정가치금융자산" → 표준 6 fairValueAssets (회사 4 번이 표준 6)
- 005930 "11. 순확정급여부채" → 표준 14 definedBenefit
의미 같으면 standard mapping — period 간 일관.
"""

from __future__ import annotations

import re

import polars as pl

from dartlab.providers.dart.topicStandard import NOTES_SUB_SECTIONS, notesSubTopicKey

# DART 표준 31 주석 번호 → (slug, 한글 label) — O(1) lookup
_NOTES_BY_NUMBER: dict[int, tuple[str, str]] = {num: (slug, korean) for num, slug, korean in NOTES_SUB_SECTIONS}


def _normalizeNoteName(name: str) -> str:
    """주석 한글 이름 normalize — 의미 매칭 위한 정규화.

    - 괄호 안 보조 표기 제거 "(자산)" / "(별도)" 등
    - 한자 정자체 제거
    - 띄어쓰기 통일
    - 비교용 lowercase (한글에는 무영향, 영문 알파벳용)
    """
    s = re.sub(r"\(.*?\)|（.*?）", "", name)
    s = s.replace("및", "").replace(",", "")
    s = re.sub(r"\s+", "", s).strip()
    return s


# 한글 이름 → standard (number, slug) 매핑. NOTES_SUB_SECTIONS 의 정식 이름 우선,
# 회사별 변형 alias 추가.
_NOTES_BY_NAME: dict[str, tuple[int, str]] = {}
for _num, _slug, _korean in NOTES_SUB_SECTIONS:
    _NOTES_BY_NAME[_normalizeNoteName(_korean)] = (_num, _slug)

# 회사별 변형 이름 alias (DART 회사들 실측 cell 기준).
_NOTES_NAME_ALIASES: dict[str, tuple[int, str]] = {
    # 표준 1 general — 별도재무제표 주석 sub-heading 부재 시 첫 본문 textPath
    # 가 'sub-section' 없이 바로 '회사의 개요' 인 경우 (000660 sk하이닉스).
    # _NOTES_PARENT_TOPICS = ("financialNotes", "consolidatedNotes") 한정 → companyOverview 토픽과 무관.
    "회사의개요": (1, "general"),
    # 표준 14 definedBenefit — "순확정급여부채(자산)" 외 변형
    "퇴직급여제도": (14, "definedBenefit"),
    "확정급여제도": (14, "definedBenefit"),
    "확정급여부채": (14, "definedBenefit"),
    "순확정급여부채": (14, "definedBenefit"),
    "순확정급여부채자산": (14, "definedBenefit"),
    "퇴직급여": (14, "definedBenefit"),
    # 표준 9 subsidiariesAndAssociates
    "관계기업및공동기업투자": (9, "subsidiariesAndAssociates"),
    "관계기업공동기업투자": (9, "subsidiariesAndAssociates"),
    "종속기업관계기업공동기업투자": (9, "subsidiariesAndAssociates"),
    "종속관계공동기업투자": (9, "subsidiariesAndAssociates"),
    # 표준 6 fairValueAssets (당기손익공정가치측정금융자산)
    "공정가치금융자산": (6, "fairValueAssets"),
    "당기손익공정가치측정금융자산": (6, "fairValueAssets"),
    "당기손익인식금융자산": (6, "fairValueAssets"),
    # 표준 7 tradeReceivables
    "매출채권미수금": (7, "tradeReceivables"),
    "매출채권": (7, "tradeReceivables"),
    # 표준 4 financialInstruments
    "범주별금융상품": (4, "financialInstruments"),
    "금융상품": (4, "financialInstruments"),
    "금융상품범주": (4, "financialInstruments"),
    # 표준 27 cashflow
    "현금흐름표": (27, "cashflow"),
    "현금흐름표주석": (27, "cashflow"),
    "영업으로부터창출된현금흐름": (27, "cashflow"),
    # 표준 28 riskManagement
    "재무위험관리": (28, "riskManagement"),
    "위험관리": (28, "riskManagement"),
    # 표준 29 fairValue
    "공정가치측정": (29, "fairValue"),
    "공정가치공시": (29, "fairValue"),
    "공정가치": (29, "fairValue"),
    # 표준 30 segment
    "부문별보고": (30, "segment"),
    "영업부문": (30, "segment"),
    "사업부문": (30, "segment"),
    # 표준 25 incomeTax
    "법인세비용": (25, "incomeTax"),
    "법인세": (25, "incomeTax"),
    # 표준 11 intangibleAssets
    "무형자산": (11, "intangibleAssets"),
    # 표준 16 contingentAndCommitments
    "우발부채와약정사항": (16, "contingentAndCommitments"),
    "약정사항및우발부채": (16, "contingentAndCommitments"),
    "약정및우발사항": (16, "contingentAndCommitments"),
    "우발사항및약정사항": (16, "contingentAndCommitments"),
    "약정사항및우발상황": (16, "contingentAndCommitments"),
    # 표준 17 contractLiabilities
    "계약부채": (17, "contractLiabilities"),
    # 표준 22 sga
    "판매비와관리비": (22, "sga"),
    "판매비관리비": (22, "sga"),
    # 표준 26 eps
    "주당이익": (26, "eps"),
    "주당손익": (26, "eps"),
}
_NOTES_BY_NAME.update(_NOTES_NAME_ALIASES)

# 주석 분할 대상 parent topic.
_NOTES_PARENT_TOPICS: tuple[str, ...] = ("financialNotes", "consolidatedNotes")

# ``N. {한글 이름}`` 헤딩 매처 — N + ". " + Korean name. &cr; / 줄바꿈 분기 수용.
_NOTES_HEADING_RE = re.compile(r"^\s*(\d{1,2})\.\s+([^\n\r]{2,80})")

# textPath root 에 흔히 붙는 한정자 suffix — `(연결)` / `(별도)` / `(주석)` 등.
# textPath 의 root segment 는 note 이름이지만 한정자 suffix 가 붙어있을 수 있다.
_TEXTPATH_ROOT_SUFFIX_RE = re.compile(r"\s*[\(（][^)）]*[\)）]\s*$")


def _resolveNoteIdentityFromTextPath(textPath: str | None) -> tuple[int, str] | None:
    """row 의 ``textPath`` 의 *모든 level* 을 스캔해 note 이름 매칭. 더 깊은 (더 구체적) 매치 우선.

    textPath 는 note 의 heading 구조에서 빌드된다. 새 reporting 양식은 root segment 가 곧
    note 이름 (`판매비와관리비 (연결)` → (22, sga)). 옛 quarterly 양식은 모든 note 를
    `1. 일반적 사항` 한 parent 안에 sub-heading 으로 넣어서 root 는 `일반적 사항` 이지만 *진짜*
    note 는 level 2 segment 에 있다:
    - `일반적 사항 > 공정가치 측정` → (29, fairValue)
    - `일반적 사항 > 부문별 정보` → (30, segment)
    - `일반적 사항 > 희석주당순이익` → (26, eps)
    - `판매비와관리비 (연결)` → root match → (22, sga)

    deepest segment 우선 (more specific) — 옛 양식의 nested 구조도 정확히 분류된다.

    body heading 검출보다 *훨씬* 신뢰:
    - row 가 sub-table 본문만 있고 `N. 헤딩` 행이 다른 row 에 박힌 경우
    - 옛 quarterly cell 만 있고 annual empty → annual heading 못 봄
    """
    if not isinstance(textPath, str) or not textPath:
        return None
    segments = [s.strip() for s in textPath.split(" > ")]
    deepestMatch: tuple[int, str] | None = None
    for seg in segments:
        if not seg:
            continue
        # `(연결)` / `(별도)` / `(주석)` 등 한정자 suffix 제거
        clean = _TEXTPATH_ROOT_SUFFIX_RE.sub("", seg).strip()
        if not clean:
            continue
        norm = _normalizeNoteName(clean)
        if not norm:
            continue
        hit = _NOTES_BY_NAME.get(norm)
        if hit is not None:
            deepestMatch = hit
    return deepestMatch


def _resolveNoteIdentity(body: str | None) -> tuple[int, str] | None:
    """body 첫 줄에서 ``N. {한글 이름}`` 추출 후 한글 이름 → standard (NN, slug) 매핑.

    1. 한글 이름 normalize + alias map lookup → standard (NN, slug). 회사별 N 번호 무시.
    2. lookup 실패 시 회사 N 번호 → _NOTES_BY_NUMBER fallback (옛 behavior).
    3. 둘 다 실패 시 None.
    """
    if not isinstance(body, str) or not body:
        return None
    match = _NOTES_HEADING_RE.match(body)
    if not match:
        return None
    raw_n = match.group(1)
    raw_name = match.group(2).strip()

    # 1. 한글 이름 우선
    norm = _normalizeNoteName(raw_name)
    if norm in _NOTES_BY_NAME:
        return _NOTES_BY_NAME[norm]

    # 2. 회사 N 번호 fallback
    try:
        company_n = int(raw_n)
    except ValueError:
        return None
    if company_n in _NOTES_BY_NUMBER:
        slug, _korean = _NOTES_BY_NUMBER[company_n]
        return (company_n, slug)
    return None


# 옛 API 호환 wrapper (caller 가 있을 수 있음).
def _extractNoteNumber(body: str | None) -> int | None:
    res = _resolveNoteIdentity(body)
    return res[0] if res else None


def splitNotesSections(df: pl.DataFrame) -> pl.DataFrame:
    """sections frame 의 notes row 들을 sub-topic 으로 분할.

    Args:
        df: sections frame (``c.sections`` 의 raw — chapter/topic/blockOrder/period... 컬럼).

    Returns:
        분할 후 sections frame. notes 외 topic 은 변경 0. parent topic key (예
        ``financialNotes``) 은 row 별로 sub-topic key (``financialNotes_05_xyz``) 로
        rewrite, ``sourceTopic`` 에 원래 parent 보존.

    Raises:
        없음.

    Example:
        >>> splitNotesSections(c.sections)  # financialNotes 113 rows → 31 sub-topic 으로 분할

    동작 보장:
        - 분할 대상 topic 에서 ``N.`` 헤딩 추출 실패 (예 옛 보고서 형식) row 는
          그대로 parent topic 유지.
        - 분할 후 sub-topic 의 blockOrder 는 그 sub-topic 안에서 0-based 재할당.
    """
    if df is None or df.height == 0 or "topic" not in df.columns:
        return df
    if "sourceTopic" not in df.columns:
        df = df.with_columns(pl.col("topic").alias("sourceTopic"))
    notes_mask = pl.col("topic").is_in(_NOTES_PARENT_TOPICS)
    if not df.filter(notes_mask).height:
        return df

    # 본문 추출용 period 컬럼 — annual (사업보고서, `2024` 등) 만 사용.
    # 이유: 분기보고서와 사업보고서가 동일 주석에도 *다른* N 번호를 매김 (분기엔
    # 일부 sub-section 생략). NOTES_SUB_SECTIONS SSOT 는 사업보고서 표준 번호 기준
    # 이므로 분기 본문으로 N 추출하면 잘못된 sub-topic key 생성. annual 우선.
    annual_cols = [c for c in df.columns if re.fullmatch(r"\d{4}", c)]
    quarter_cols = [c for c in df.columns if re.fullmatch(r"\d{4}Q[1-4]", c)]
    # annual 최신부터 (예 2025 > 2024 > 2023), 없으면 quarter Q4 (사업보고서 동치) → 그 외 quarter.
    annual_cols_sorted = sorted(annual_cols, reverse=True)
    q4_cols_sorted = sorted([c for c in quarter_cols if c.endswith("Q4")], reverse=True)
    other_q_cols_sorted = sorted([c for c in quarter_cols if not c.endswith("Q4")], reverse=True)
    period_cols_sorted = annual_cols_sorted + q4_cols_sorted + other_q_cols_sorted

    # (topic, blockOrder) 정렬 — cumsum 그룹화의 정확성을 위해 보고서 흐름 순서 강제.
    # docsSec frame 의 default 순서는 입력 데이터 순서이지 보고서 흐름이 아닐 수 있다.
    notes_df = df.filter(notes_mask).sort(["topic", "blockOrder"])
    other_df = df.filter(~notes_mask)

    # 본문 추출 — period 컬럼 중 첫 non-empty 가 대표 본문.
    def _firstNonEmptyBody(row: dict) -> str | None:
        for p in period_cols_sorted:
            v = row.get(p)
            if isinstance(v, str) and v.strip():
                return v
        return None

    # to_dicts 로 row iteration — 의미 기반 (NN, slug) 추출.
    #
    # identity 우선순위 (2026-05-26 회귀 fix):
    #   1. row 의 ``textPath`` root segment — heading 구조에서 빌드된 SSOT.
    #      `판매비와관리비 (연결)` → (22, sga). `일반적 사항 > 주요 관계기업` → (1, general).
    #      옛 quarterly cell 만 있고 annual empty 인 ghost row 도 올바른 note 로 분류.
    #   2. body `N. {한글}` 헤딩 검출 — 옛 fallback. textPath 없는 row.
    #   3. cumsum inherit — 위 둘 다 실패 시 직전 row 의 identity 흡수.
    #      *단* inherit 은 같은 textPath root 안에서만 — root 가 바뀌면 chain 끊김.
    #      이 차이가 005930 SGA 토픽 68 row 중 66 row 오분류 회귀 fix 의 핵심.
    rows = notes_df.to_dicts()
    last_identity: dict[str, tuple[int, str] | None] = {p: None for p in _NOTES_PARENT_TOPICS}
    last_root: dict[str, str | None] = {p: None for p in _NOTES_PARENT_TOPICS}
    note_identities: list[tuple[int, str] | None] = []
    for row in rows:
        parent = row.get("topic")
        textPath = row.get("textPath")
        rootSeg: str | None = None
        if isinstance(textPath, str) and textPath:
            rootSeg = textPath.split(" > ", 1)[0].strip()

        # (1) textPath root 우선
        ident = _resolveNoteIdentityFromTextPath(textPath)

        # (2) body heading fallback
        if ident is None:
            body = _firstNonEmptyBody(row)
            ident = _resolveNoteIdentity(body)

        # (3) cumsum inherit — 같은 root 안에서만
        if ident is None and rootSeg is not None and rootSeg == last_root.get(parent):
            ident = last_identity.get(parent)

        # last_identity / last_root 갱신
        if ident is not None:
            last_identity[parent] = ident
        if rootSeg is not None:
            last_root[parent] = rootSeg

        note_identities.append(ident)

    # 새 topic key 계산 — None 이면 그대로 parent (매칭 못한 옛 row).
    new_topics: list[str] = []
    for row, ident in zip(rows, note_identities, strict=False):
        parent = row["topic"]
        if ident is None:
            new_topics.append(parent)
            continue
        nn, slug = ident
        new_topics.append(notesSubTopicKey(parent, nn, slug))

    # notes_df 의 topic 컬럼 rewrite. blockOrder 재할당은 보조 처리.
    notes_df = notes_df.with_columns(pl.Series("topic", new_topics, dtype=notes_df.schema["topic"]))

    # blockOrder 재할당 — sub-topic 안에서 0-based.
    notes_df = notes_df.sort("blockOrder").with_columns(
        (pl.cum_count("blockOrder").over("topic", mapping_strategy="group_to_rows") - 1)
        .cast(pl.Int64)
        .alias("blockOrder")
    )

    return pl.concat([other_df, notes_df], how="vertical_relaxed").sort(["topic", "blockOrder"])
