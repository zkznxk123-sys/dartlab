"""증권사 리서치 보드 레지스트리 — 관리 SSOT.

증권사 추가·수정·중단은 이 dict 한 곳만 건든다 (url + 메커니즘 + 카테고리 + enabled).
mechanism: htmlTable(서버렌더 표) · htmlList(서버렌더 ul>li) · spaAjax(JS 셸 — deferred).
categories: {reportType 라벨 → 보드 URL} — 카테고리가 곧 리포트 구분(reportType).
enabled=False = browser 자동화 필요로 deferred (note 참조).
"""

from __future__ import annotations

_MIRAE = "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId="
_NH = "https://m.nhqv.com/research/boardList?rshPprDitCd="
_YUANTA = "https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd006=&cd008=&cd007="

BROKERS: dict[str, dict] = {
    # --- 서버렌더 = 작동 ---
    "miraeasset": {
        "name": "미래에셋",
        "mechanism": "htmlTable",
        "enc": "cp949",
        "enabled": True,
        "categories": {
            "기업분석": _MIRAE + "1800",
            "산업분석": _MIRAE + "1525",
            "투자전략": _MIRAE + "1527",
        },
    },
    "nh": {
        "name": "NH투자",
        "mechanism": "htmlList",
        "enc": None,
        "enabled": True,
        "categories": {
            "기업분석": _NH + "01",
            "시황전략": _NH + "02",
        },
    },
    "yuanta": {
        "name": "유안타",
        "mechanism": "htmlTable",
        "enc": None,
        "enabled": True,
        "categories": {
            "투자전략": _YUANTA + "RB30",
        },
        "note": "메타 작동, 링크는 onclick 역추출 미완 → 카테고리 URL fallback",
    },
    # --- SPA/AJAX = deferred (초기 HTML 에 데이터·엔드포인트 없음 → browser 자동화 필요) ---
    "koreainvestment": {
        "name": "한국투자",
        "mechanism": "spaAjax",
        "enc": None,
        "enabled": False,
        "categories": {"전체": "https://securities.koreainvestment.com/main/research/Main.jsp"},
        "note": "엔드포인트가 외부 JS 번들에 있음",
    },
    "kb": {
        "name": "KB증권",
        "mechanism": "spaAjax",
        "enc": None,
        "enabled": False,
        "categories": {"전체": "https://rc.kbsec.com/"},
        "note": "SPA 셸",
    },
    "kiwoom": {
        "name": "키움",
        "mechanism": "spaAjax",
        "enc": None,
        "enabled": False,
        "categories": {"전체": "https://www.kiwoom.com/h/invest/research/VAnalCRView"},
        "note": "AJAX 로드, 엔드포인트 외부 JS",
    },
    "hana": {
        "name": "하나",
        "mechanism": "spaAjax",
        "enc": None,
        "enabled": False,
        "categories": {"전체": "https://www.hanaw.com/main/research/researchReform/RC_000100_T1.cmd"},
        "note": "AJAX 로드 (필터 셸만 서버렌더)",
    },
}


def enabledBrokers() -> dict[str, dict]:
    """enabled=True 증권사만 추린 dict 반환 (deferred SPA 제외).

    Args:
        없음.

    Returns:
        dict[str, dict] — broker key → 설정 dict (enabled 인 것만).

    Raises:
        없음 — 빈 dict 도 정상 반환.

    Requires:
        모듈 상수 ``BROKERS`` (관리 SSOT).

    Example::

        from dartlab.gather.sources.brokerage.config import enabledBrokers
        list(enabledBrokers())   # ['miraeasset', 'nh', 'yuanta']
    """
    return {k: v for k, v in BROKERS.items() if v.get("enabled")}
