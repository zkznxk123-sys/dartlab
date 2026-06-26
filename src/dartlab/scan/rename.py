"""scan 결과 영문 → 한글 컬럼 변환 + 종목명 join.

`_COLUMN_RENAME` SSOT 사전과 `_enrichWithKorean` 진입점을 분리해 router/Scan 클래스
는 import 한 줄로 사용. scan 축 모듈은 영문 컬럼으로 결과를 만들고, router 가 사용자
반환 직전에 본 모듈로 후처리.
"""

from __future__ import annotations

import polars as pl

_COLUMN_RENAME = {
    "stockCode": "종목코드",
    "opMargin": "영업이익률",
    "netMargin": "순이익률",
    "roe": "ROE",
    "roa": "ROA",
    "grade": "등급",
    "nonRecurring": "비경상",
    "revenueCagr": "매출CAGR",
    "opIncomeCagr": "영업이익CAGR",
    "netIncomeCagr": "순이익CAGR",
    "pattern": "패턴",
    "assetTurnover": "자산회전율",
    "invTurnover": "재고회전율",
    "arTurnover": "매출채권회전율",
    "ppeTurnover": "유형자산회전율",
    "invDays": "재고일수",
    "arDays": "매출채권일수",
    "ccc": "현금전환주기",
    "marketCap": "시가총액",
    "per": "PER",
    "pbr": "PBR",
    "psr": "PSR",
    "dividendYield": "배당수익률",
    "riskLevel": "위험등급",
    "riskFlags": "위험플래그",
    "riskCount": "위험수",
    "presets": "프리셋",
    "presetCount": "프리셋수",
    "ocf": "영업CF",
    "icf": "투자CF",
    "finCf": "재무CF",
    "accrualRatio": "발생액비율",
    "cfToNi": "CF/NI",
    "currentRatio": "유동비율",
    "quickRatio": "당좌비율",
    "holderPct": "최대주주지분",
    "holderChange": "지분변동",
    "treasuryShares": "자기주식",
    "stability": "경영권안정성",
    "opinion": "감사의견",
    "auditor": "감사인",
    "auditorChanged": "감사인변경",
    "hasSpecialMatter": "특기사항",
    "dpsGrowth": "DPS성장",
    # orders (신규수주 flow)
    "ttmOrders": "TTM수주액",
    "recentRevenue": "최근매출액",
    "bookToBill": "수주매출배율",
    "momentum": "수주모멘텀",
    "momentumLabel": "모멘텀구분",
    "topCounterparty": "최대계약상대",
    "topShare": "상대집중도",
    "nContract": "계약건수",
    "nAmend": "정정건수",
    "nCancel": "해지건수",
    "asOf": "기준일",
}


def _enrichWithKorean(df: pl.DataFrame) -> pl.DataFrame:
    """영문 컬럼 → 한글 rename + 종목명 추가.

    Parameters
    ----------
    df : pl.DataFrame
        scan 결과 DataFrame (stockCode 컬럼 필요).

    Returns
    -------
    pl.DataFrame
        종목명 : str — 종목코드에 대응하는 회사명 (join)
        (기존 영문 컬럼) — _COLUMN_RENAME 매핑에 따라 한글로 rename
    """
    # 종목명 매핑
    if "stockCode" in df.columns:
        try:
            # F5: root facade 우회 → _listingDispatch 직접 (정공법 D + submodule 명 충돌 회피)
            from dartlab._listingDispatch import listing as _listing

            listing = _listing()
            if listing is not None:
                name_col = next((c for c in ("종목명", "회사명") if c in listing.columns), None)
                if name_col and "종목코드" in listing.columns:
                    name_map = listing.select(["종목코드", name_col]).rename(
                        {name_col: "_종목명", "종목코드": "stockCode"}
                    )
                    df = df.join(name_map, on="stockCode", how="left")
        except (ImportError, AttributeError, KeyError, ValueError, RuntimeError):
            pass

    # 한글 rename
    renames = {k: v for k, v in _COLUMN_RENAME.items() if k in df.columns}
    if renames:
        df = df.rename(renames)

    # 종목명 배치 (종목코드 바로 뒤)
    if "_종목명" in df.columns:
        df = df.rename({"_종목명": "종목명"})
        cols = df.columns
        if "종목코드" in cols:
            ordered = ["종목코드", "종목명"] + [c for c in cols if c not in ("종목코드", "종목명")]
            df = df.select(ordered)

    return df
