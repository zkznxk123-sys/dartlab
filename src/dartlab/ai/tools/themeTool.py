"""ThemeExposure — 근거있는 횡단 테마 노출 (인포스탁 리스트와 달리 증거·매출% 투명).

두 모드: stockCode → 그 종목의 소속 테마 + 노출%(왜 이 테마, 매출 몇%); themeId →
테마 멤버 종목(태깅 근거 + 선택 등급/발견). 산출은 dartlab 내부 결정론(주요제품 매칭 +
panel 부문 노출%)이라 외부 untrusted wrap 불요.

graph 회귀 방지: agent.py 본체·고정노드 추가 0. LLM 자율 호출 도구.
"""

from __future__ import annotations

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .types import ToolResult


def themeTool(
    themeId: str | None = None,
    stockCode: str | None = None,
    *,
    grade: bool = False,
    discover: bool = False,
) -> ToolResult:
    """근거있는 테마 노출 — 종목→테마(왜·매출%) 또는 테마→멤버.

    Capabilities:
        ``stockCode`` 지정 시 그 종목의 소속 테마별 근거(주요제품 키워드)+매출노출%(테마-인지)
        를 낸다(인포스탁 black-box 와 달리 *왜 이 테마*를 증거로). ``themeId`` 지정 시 테마 멤버
        종목 표(+grade 노출%·discover 공급망 발견). 둘 다 없으면 등록 테마 목록.

    Parameters
    ----------
    themeId : str | None
        테마 ID (예: "secondaryBattery"). stockCode 와 함께면 stockCode 우선.
    stockCode : str | None
        6자리 종목코드. 지정 시 그 종목의 테마 도시에.
    grade : bool
        themeId 모드에서 멤버별 노출% 등급 추가(느림 — 멤버별 panel 조회).
    discover : bool
        themeId 모드에서 공급망 거래엣지 발견 종목 추가.

    Returns
    -------
    ToolResult
        ok=True, refs=[tableRef], data 에 themes/members. ``exposurePct``=None 은 미산출
        (추출실패/단일사업/segmentKeywords 부재) — 100% 등치 금지.

    Raises:
        없음 — 데이터 부재는 빈 결과 + basis 표기.

    Example:
        >>> from dartlab.ai.tools.themeTool import themeTool
        >>> themeTool(stockCode="006400").data["themes"][0]["theme"]  # 삼성SDI
        '2차전지/배터리'

    Guide:
        답변 시 ``근거``(키워드)·``exposurePct``/``basis`` 를 evidence 로 cite. 노출% None 은
        "부문 미공시 — 순도 미산출"로 정직 표기.

    When:
        "삼성SDI 2차전지 노출?", "이 테마 종목·순도", "왜 이 테마" 류 LLM 자율 호출.

    How:
        ``industry.themes`` (loadThemes/matchThemeText/themeRevenueExposure) + ``Industry.theme`` verb.

    Requires:
        - ``industry/themes.json`` + KIND 상장목록. grade/stockCode: panel 주석.

    See Also:
        - ``dartlab.industry.Industry.theme`` : 테마 멤버 verb.
        - ``dartlab.industry.themes.themeRevenueExposure`` : 등급 위임.

    AIContext:
        근거투명 테마층 — 인포스탁/네이버가 못 주는 "왜·매출%·동종"을 cite. None 노출 정직 표기.
    """
    from dartlab.industry import Industry

    confidence = baseScore("ratio")

    if stockCode:
        from dartlab.gather.krx.listing.registry import getKindList
        from dartlab.industry.themes import loadThemes, matchThemeText, themeRevenueExposure

        kind = getKindList()
        row = kind.filter(kind["종목코드"] == stockCode)
        corpName = row["회사명"][0] if row.height else stockCode
        product = row["주요제품"][0] if row.height else ""
        themes = []
        for tid, theme in loadThemes().items():
            hits = matchThemeText(theme, product or "")
            if not hits:
                continue
            g = themeRevenueExposure(stockCode, tid) or {}
            themes.append(
                {
                    "themeId": tid,
                    "theme": theme.name,
                    "근거": ", ".join(hits),
                    "exposurePct": g.get("exposurePct"),
                    "basis": g.get("basis"),
                }
            )
        payload = {"stockCode": stockCode, "corpName": corpName, "themes": themes, "confidence": confidence}
        ref = Ref(
            id=f"theme:{stockCode}",
            kind="tableRef",
            title=f"{corpName} 테마 노출",
            source="themeTool",
            payload=payload,
        )
        msg = f"{corpName} 소속 테마 {len(themes)}개 (근거+매출노출%)" if themes else f"{corpName} 매칭 테마 없음"
        return ToolResult(True, msg, refs=[ref], data=payload)

    if themeId:
        df = Industry().theme(themeId, grade=grade, discover=discover)
        rows = df.to_dicts()
        payload = {"themeId": themeId, "members": rows, "count": len(rows), "confidence": confidence}
        ref = Ref(
            id=f"theme:{themeId}",
            kind="tableRef",
            title=f"테마 {themeId} 멤버",
            source="themeTool",
            payload=payload,
        )
        return ToolResult(True, f"테마 '{themeId}' 멤버 {len(rows)}종목", refs=[ref], data=payload)

    rows = Industry().theme().to_dicts()
    payload = {"themes": rows, "confidence": confidence}
    ref = Ref(id="theme:list", kind="tableRef", title="테마 목록", source="themeTool", payload=payload)
    return ToolResult(True, f"등록 테마 {len(rows)}개", refs=[ref], data=payload)


__all__ = ["themeTool"]
