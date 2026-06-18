"""횡단(cross-industry) 투자 테마 — themes.json 로드·태깅·매출노출 등급.

taxonomy.py(산업 분류)의 형제. 단 테마는 표준 KSIC 업종을 *가로지르므로*(2차전지=화학+
기계+비철+전기) industryId 하위 중첩이 아니라 top-level flat 사전이다. 태깅(recall)은 KIND
주요제품 substring 매칭, 등급(노출%)은 panel(L1) ``segmentRevenueExposure`` × 테마별
``segmentKeywords``. 사전(themes.json)은 사람 큐레이션 SSOT — 자동 생성 도구 금지.

핵심 정직 계약: 등급은 축-태깅 부문공시 회사만 산출. segmentKeywords 미정의 테마·부문공시
부재 회사는 ``exposurePct=None`` + ``basis`` 사유 — pure-play 100% 로 등치하지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import polars as pl

_DATA_DIR = Path(__file__).parent


@dataclass(frozen=True)
class ThemeDef:
    """단일 테마 정의 (themes.json 한 항목)."""

    themeId: str
    name: str
    desc: str
    keywords: list[str]
    negative: list[str] = field(default_factory=list)
    segmentKeywords: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def loadThemes() -> dict[str, ThemeDef]:
    """themes.json 을 로드해 테마ID → ThemeDef 매핑 반환 (lru_cache, 세션 1회 파싱).

    Capabilities:
        ``industry/themes.json`` 의 flat cross-industry 사전을 1 회 파싱. 모든 테마 조회·매칭의
        단일 진입점. taxonomy ``loadTaxonomy`` 와 동일 패턴.

    Returns:
        dict[str, ThemeDef] — 테마ID → 정의 (keywords/negative/segmentKeywords).

    Raises:
        FileNotFoundError: themes.json 부재 시.
        json.JSONDecodeError: 파일 손상 시.

    Example:
        >>> from dartlab.industry.themes import loadThemes
        >>> loadThemes()["secondaryBattery"].name
        '2차전지/배터리'

    Guide:
        ``loadThemes.cache_clear()`` 후 재호출 시 재파싱. 보통 ``matchThemes`` /
        ``themeRevenueExposure`` 가 간접 사용.

    When:
        테마 목록·매칭·등급 함수가 1 회 lazy 호출.

    How:
        JSON 로드 → ``_meta`` 제외 → 각 항목 ThemeDef 변환.

    See Also:
        ``dartlab.industry.taxonomy.loadTaxonomy`` : 산업 분류 형제.
    """
    raw = json.loads((_DATA_DIR / "themes.json").read_text(encoding="utf-8"))
    out: dict[str, ThemeDef] = {}
    for tid, t in raw.get("themes", {}).items():
        out[tid] = ThemeDef(
            themeId=tid,
            name=t.get("name", tid),
            desc=t.get("desc", ""),
            keywords=t.get("keywords", []),
            negative=t.get("negative", []),
            segmentKeywords=t.get("segmentKeywords", []),
        )
    return out


def listThemes() -> list[dict]:
    """등록된 전체 테마 목록 (themeId/name/keyword 수/등급가능 여부)."""
    return [
        {
            "themeId": t.themeId,
            "name": t.name,
            "keywords": len(t.keywords),
            "gradeable": bool(t.segmentKeywords),
        }
        for t in loadThemes().values()
    ]


def matchThemeText(theme: ThemeDef, text: str) -> list[str]:
    """주요제품 텍스트에서 테마 키워드 매칭(negative 제거 후 substring). 매칭 키워드 리스트.

    Capabilities:
        case-insensitive substring 매칭. negative 표현은 본문에서 제거 후 매칭(거짓양성 가드,
        예: '건전지'·'로봇청소기'). taxonomy ``matchStageByKeywords`` 와 동일 substring 철학.

    Parameters
    ----------
    theme : ThemeDef
        테마 정의.
    text : str
        매칭 대상 (KIND 주요제품).

    Returns
    -------
    list[str]
        매칭된 키워드. 없으면 [].

    Raises:
        없음 — 빈 텍스트면 [].

    Example:
        >>> from dartlab.industry.themes import loadThemes, matchThemeText
        >>> matchThemeText(loadThemes()["secondaryBattery"], "2차전지, 양극재")
        ['2차전지', '양극재']

    Guide:
        매칭 0 = 비멤버. 본 함수는 *태깅(recall)* 만 — 등급(노출%)은 ``themeRevenueExposure``.

    When:
        ``Industry.theme(themeId)`` 가 KIND 유니버스 순회 시 행별 호출.

    How:
        negative substring 제거 → keyword substring in 잔여 텍스트.

    See Also:
        ``dartlab.industry.themes.themeRevenueExposure`` : 등급(precision).
    """
    if not text:
        return []
    low = text.lower()
    for neg in theme.negative:
        low = low.replace(neg.lower(), " ")
    return [kw for kw in theme.keywords if kw.lower() in low]


def themeRevenueExposure(themeId: str, code: str) -> dict | None:
    """한 종목의 *해당 테마* 매출 노출% — 테마별 segmentKeywords 로만 등급 (테마-인지).

    Capabilities:
        panel(L1) ``segmentRevenueExposure`` 부문 노출% 를 *그 테마의* ``segmentKeywords`` 로
        필터·합산. 테마마다 자기 세그먼트 키워드로만 등급(2차전지 세그먼트를 태양광 테마에
        적용하던 결함 차단). pure-play vs 희석 정량.

    Parameters
    ----------
    themeId : str
        테마 ID.
    code : str
        6자리 종목코드.

    Returns
    -------
    dict | None
        ``{exposurePct, basis, topSegment}`` 또는 미등록 테마면 None. ``basis``:
        - ``graded`` : 노출% 산출 (exposurePct = 테마 귀속 부문매출% 합).
        - ``theme_no_segment_keywords`` : 테마에 segmentKeywords 미정의 → exposurePct=None.
        - ``no_segment_data`` : 부문 주석 추출 실패 → exposurePct=None.
        - ``pure_play_candidate`` : 축-태깅 부문 0(단일사업 또는 행-라벨) → exposurePct=None.
        **정직 계약**: None basis 를 100% 로 등치 금지.

    Raises:
        없음 — 데이터 부재는 basis 로 표기.

    Example:
        >>> from dartlab.industry.themes import themeRevenueExposure
        >>> themeRevenueExposure("secondaryBattery", "051910")["exposurePct"]  # LG화학
        48.4

    Guide:
        exposurePct >= 50 = pure-play, 10~50 = quasi, <10 = 곁다리(거짓양성 의심). None = 미산출
        (이진 멤버십만 신뢰).

    When:
        ``Industry.theme(themeId, grade=True)`` 가 멤버별 호출. AI 답변의 "테마 순도" 근거.

    How:
        ``loadThemes`` segmentKeywords → ``panel.cell.segmentRevenueExposure`` → 부문토큰 substring
        매칭 합산.

    See Also:
        ``dartlab.providers.dart.panel.cell.segmentRevenueExposure`` : 부문 노출% SSOT.
    """
    theme = loadThemes().get(themeId)
    if theme is None:
        return None
    if not theme.segmentKeywords:
        return {"exposurePct": None, "basis": "theme_no_segment_keywords", "topSegment": None}

    from dartlab.providers.dart.panel.cell import segmentRevenueExposure

    exp = segmentRevenueExposure(code)
    if exp is None:
        return {"exposurePct": None, "basis": "no_segment_data", "topSegment": None}
    if not exp:
        return {"exposurePct": None, "basis": "pure_play_candidate", "topSegment": None}
    segKws = [k.lower() for k in theme.segmentKeywords]
    pct = sum(p for seg, p in exp.items() if any(k in seg.lower() for k in segKws))
    top = max(exp.items(), key=lambda x: x[1])
    return {"exposurePct": round(pct, 1), "basis": "graded", "topSegment": {"name": top[0], "pct": top[1]}}


def companyThemes(code: str) -> pl.DataFrame:
    """한 종목의 소속 테마 도시에 — 근거(주요제품 키워드) + 매출노출%. (``Company(code).themes()`` backend)

    Capabilities:
        회사 스코프 질문 "이 종목 무슨 테마, 왜, 매출 몇%" 의 엔진 SSOT. 주요제품 substring 으로
        소속 테마를 찾고 테마별 노출%(테마-인지)를 등급. 인포스탁 black-box 리스트와 달리 근거
        투명. 테마 스코프(``Industry().theme(themeId)`` = 테마→멤버) 와 쌍을 이루는 회사 스코프 진입.

    Parameters
    ----------
    code : str
        6자리 종목코드.

    Returns
    -------
    pl.DataFrame
        ``themeId, 테마, 근거, 노출%, 등급근거``. 매칭 테마 없으면 빈 DataFrame. ``노출%``=None 은
        미산출(추출실패/단일사업/segmentKeywords 부재) — 100% 등치 금지.

    Raises:
        없음 — 데이터 부재는 빈 결과 + 등급근거 표기.

    Example:
        >>> from dartlab.industry.themes import companyThemes
        >>> companyThemes("051910")["테마"].to_list()  # LG화학
        ['2차전지/배터리']

    Guide:
        ``Company(code).themes()`` 가 본 함수 위임. 답변에 근거(키워드)·등급근거(basis) cite.

    When:
        "이 종목 무슨 테마", "왜 이 테마·매출 몇%" 회사 스코프 답변.

    How:
        KIND 주요제품 → ``matchThemeText`` 소속 판정 → ``themeRevenueExposure`` 등급.

    See Also:
        ``dartlab.industry.Industry.theme`` : 테마 스코프(테마 → 멤버).
        ``dartlab.industry.themes.themeRevenueExposure`` : 등급 위임.
    """
    import gc

    from dartlab.gather.krx.listing.registry import getKindList

    kind = getKindList()
    row = kind.filter(kind["종목코드"] == code)
    product = row["주요제품"][0] if row.height else ""
    schema = {"themeId": pl.Utf8, "테마": pl.Utf8, "근거": pl.Utf8, "노출%": pl.Float64, "등급근거": pl.Utf8}
    rows: list[dict] = []
    for tid, theme in loadThemes().items():
        hits = matchThemeText(theme, product or "")
        if not hits:
            continue
        g = themeRevenueExposure(tid, code) or {}
        rows.append(
            {
                "themeId": tid,
                "테마": theme.name,
                "근거": ", ".join(hits),
                "노출%": g.get("exposurePct"),
                "등급근거": g.get("basis"),
            }
        )
        gc.collect()
    return pl.DataFrame(rows, schema=schema)
