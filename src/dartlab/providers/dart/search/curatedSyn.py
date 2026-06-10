"""큐레이션 동의어 — 구어/약어 질의를 공시 본문 용어로 확장 (content lane R* 의 확장축 1).

unifiedSearchRecipe honest-gold 실측으로 확정한 운영자 수동 사전. PMI/공기 자동발굴은
단일코퍼스 동어반복 인공물로 기각(meaning graph +0.010) — 자동 항목 추가 금지, 신규 키는
운영자가 직접 검토 후 추가한다. 어절 경계 매칭으로 substring 오발화를 차단(landing 교훈).

출처 2계보(키 중복은 병합): landing ``viewer/searchIndex.ts SYNONYMS`` 공시 도메인 시드 +
title lane ``ngramIndex._L0_INFORMAL`` 의 content 적합 큐레이션 부분집합.
"""

from __future__ import annotations

import re

# landing viewer/searchIndex.ts SYNONYMS parity (공시 도메인 시드)
_LANDING = {
    "부채": ["차입금", "사채", "우발부채", "지급보증", "리스부채"],
    "차입금": ["사채", "단기차입", "장기차입"],
    "위험": ["리스크", "불확실성", "위험요인"],
    "소송": ["계류", "손해배상", "분쟁", "피소", "제소"],
    "배당": ["배당금", "현금배당", "현물배당", "배당성향"],
    "자사주": ["자기주식", "자기주식취득", "자기주식소각"],
    "스톡옵션": ["주식매수선택권", "주식기준보상"],
    "감사인": ["감사의견", "감사보고서", "내부회계관리", "외부감사"],
    "특수관계자": ["특수관계", "이해관계자", "관계기업", "종속기업"],
    "손상": ["손상차손", "영업권", "회수가능액"],
    "합병": ["인수", "사업결합", "분할"],
    "증자": ["유상증자", "무상증자", "신주발행"],
    "전환사채": ["신주인수권부사채", "교환사채"],
    "리스": ["리스부채", "사용권자산", "운용리스", "금융리스"],
    "충당부채": ["우발부채", "복구충당", "판매보증"],
    "파생": ["파생상품", "선도", "스왑", "헤지"],
}

# ngramIndex._L0_INFORMAL 의 content 적합 부분집합 (구어·약어 → 정규 용어)
_INFORMAL = {
    "사장": ["대표이사", "대표이사변경"],
    "경영진": ["대표이사", "대표이사변경"],
    "대표": ["대표이사"],
    "빚": ["사채", "차입금"],
    "빌렸다": ["사채", "차입"],
    "망하다": ["상장폐지", "관리종목"],
    "파산": ["회생", "관리절차"],
    "팔았다": ["처분", "양도", "매도"],
    "바뀌었다": ["변경", "선임", "해임", "대표이사변경"],
    "자사주": ["자기주식", "자기주식취득"],
    "스톡옵션": ["주식매수선택권"],
    "물적분할": ["분할", "분할결정"],
    "인적분할": ["분할", "분할결정"],
    "유증": ["유상증자", "유상증자결정"],
    "사보": ["사업보고서"],
    "배당금": ["배당", "현금", "현물배당결정"],
    "공장": ["사업장", "시설", "생산설비"],
    "횡령": ["제재", "부정", "소송"],
    "상장폐지": ["관리종목", "기타시장안내"],
    "부도": ["관리종목", "미지급", "채권은행"],
    "증자": ["유상증자", "신주발행"],
    "수주": ["공급계약", "단일판매", "납품"],
    "실적": ["손익구조", "영업이익", "잠정실적"],
}

CURATED: dict[str, list[str]] = {}
for _src in (_LANDING, _INFORMAL):
    for _k, _v in _src.items():
        CURATED.setdefault(_k, [])
        for _s in _v:
            if _s not in CURATED[_k]:
                CURATED[_k].append(_s)

_WORD = re.compile(r"[가-힣a-zA-Z0-9]{2,}")


def expandQuery(query: str) -> list[str]:
    """질의 → 추가할 동의어 리스트. 어절이 key 와 일치하거나 key 로 시작할 때만 발화.

    Args:
        query: 자연어 질의.

    Raises:
        없음.

    Example:
        >>> "자기주식" in expandQuery("자사주 샀어?")
        True

    Returns:
        list[str] — 발화된 동의어 (중복 제거, 발화 0 이면 빈 리스트).
    """
    words = [w.lower() for w in _WORD.findall((query or "").lower())]
    added: list[str] = []
    for key, syns in CURATED.items():
        k = key.lower()
        if any(w == k or w.startswith(k) for w in words):
            for s in syns:
                if s not in added:
                    added.append(s)
    return added
