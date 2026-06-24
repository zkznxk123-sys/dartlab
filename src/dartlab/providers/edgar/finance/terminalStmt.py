"""EDGAR companyfacts → 터미널 재무 artifact (DART ``dart/finance`` 모양 bake).

터미널 브라우저(`ui/.../sources/financeSource.ts`)는 파사드(Python)를 못 돌리므로 raw XBRL 을
직독·표준화할 수 없다. 그래서 파사드 ``Company.panel("IS"/"BS"/"CF")`` 의 표준화 산출(한국어 표준
항목 × 분기)을 **빌드타임에 DART finance 와 동형인 long 행**(`FINANCE_COLUMNS`)으로 구워 발행한다.
터미널은 KR=`dart/finance/{code}`, US=`edgar/financeStmt/{ticker}` 를 같은 reader 로 읽어 16 카드를
**동일 배선**으로 렌더한다 — accounts.ts 매칭·집계 720 줄 무변경.

정합 핵심 — ``account_id`` 채움:
    accounts.ts 의 nm 매칭은 substring(`includes`)이라 EDGAR 표준 항목('비유동자산'이 '유동자산'을
    포함)에서 오매칭한다. DART 는 IFRS ``account_id`` 정확매칭이 1순위라 이를 회피한다. 본 bake 는
    각 행의 ``account_id`` 를 ``viz.display.finance.accounts._STANDARDS`` 의 **항목 정확매칭**으로
    채워(idHit, score 0) 터미널이 DART 와 동일하게 정타하게 한다. 미매핑 항목은 ``account_id=""``
    (nm fallback, 표시 전용).

flow(IS/CF) 분기는 standalone(파사드가 YTD 역산 완료), 연간(`reprt_code` 11011)은 4 분기 합.
BS 는 시점값, 연간은 회계연말(Q4) 잔액. Q4 standalone 은 DART reprt_code 가 없어 미발행 —
터미널이 ``annual − (Q1+Q2+Q3)`` 으로 역산한다.
"""

from __future__ import annotations

import polars as pl

# DART dart/finance 와 동형 — 터미널 financeSource 가 읽는 컬럼(`accounts.ts FINANCE_COLUMNS`).
FINANCE_COLUMNS: tuple[str, ...] = (
    "sj_div",
    "fs_div",
    "reprt_code",
    "rcept_no",
    "bsns_year",
    "account_id",
    "account_nm",
    "account_detail",
    "thstrm_amount",
    "thstrm_add_amount",
    "ord",
)

# DART 정기보고서 분기 코드 — Q_BY_CODE(터미널) 역. 11011=사업보고서(연간 slot).
_Q_TO_REPRT: dict[int, str] = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}

# 파사드가 표준화하는 손익표는 IS 단일(EDGAR 은 CIS 분리 없음) — 터미널 sj_div 와 동형 3 종.
_STMTS: tuple[str, ...] = ("IS", "BS", "CF")


def _stdIdIndex() -> dict[tuple[str, str], str]:
    """`(sjDiv, 정확 항목명) → 첫 IFRS account_id` 역인덱스 (terminal idHit 정타용).

    ``_STANDARDS`` 의 label·nameKeywords 를 모두 키로 펼쳐 항목 정확매칭을 지원한다. 중복 항목명은
    먼저 정의된 표준(=더 일반적 개념)을 우선한다.

    Returns:
        dict — (sjDiv, 항목명) → ifrsIds[0]. ifrsIds 없는 표준(grossProfit 등)은 제외(nm fallback).
    """
    # lazy — 표준계정 카탈로그(viz.display, 미분류 계층)를 bake 시점에만 로드(provider import 무부담).
    from dartlab.viz.display.finance.accounts import _STANDARDS

    idx: dict[tuple[str, str], str] = {}
    for sa in _STANDARDS:
        if not sa.ifrsIds:
            continue
        for nm in {sa.label, *sa.nameKeywords}:
            idx.setdefault((sa.sjDiv, nm), sa.ifrsIds[0])
    return idx


def _parsePeriodCol(col: str) -> tuple[int, int] | None:
    """파사드 panel 기간 컬럼('2026Q2') → (year, quarter). 비-분기 컬럼은 None."""
    if "Q" not in col:
        return None
    try:
        y, q = col.split("Q")
        return int(y), int(q)
    except (ValueError, TypeError):
        return None


def bakeTerminalFinance(ticker: str, *, company=None) -> pl.DataFrame | None:
    """파사드 panel(IS/BS/CF) → 터미널 ``edgar/financeStmt/{ticker}`` long 행 bake.

    Args:
        ticker: US 종목 ticker (예: "AAPL"). company 미지정 시 ``dartlab.Company(ticker)`` 생성.
        company: 사전 생성 Company(수명 관리·재사용). None 이면 내부 생성.

    Returns:
        pl.DataFrame(`FINANCE_COLUMNS` 스키마) — 분기 standalone(Q1~Q3) + 연간(11011). 데이터 없으면
        None(터미널은 정직 폴백으로 카드 비표시).

    Raises:
        없음 — panel 호출 실패는 명세별 격리(빈 결과 → None).

    Example:
        >>> bakeTerminalFinance("AAPL")  # doctest: +SKIP
        shape: (…, 11)

    SeeAlso:
        - ``viz.display.finance.accounts._STANDARDS`` — account_id 정확매칭 SSOT.
        - ``providers.dart.build.saver`` — DART dart/finance 동형 스키마.
        - ``providers.edgar.finance.pivot.buildTimeseries`` — 파사드 panel 내부 standalone 역산.

    Requires:
        - dartlab
        - polars

    Capabilities:
        - EDGAR companyfacts(파사드 표준화)를 DART finance 동형 long 행으로 구워 터미널 16 카드
          동일 배선 렌더를 가능케 한다(브라우저 XBRL 파서 불요).

    Guide:
        - 운영자 빌드 파이프라인(edgar stage)이 universe 별 호출 후 HF 발행. 사용자 직접 호출 X.

    AIContext:
        internal terminal artifact bake — AI 직접 호출 X (파사드 ``Company.panel`` 이 AI 경로).

    LLM Specifications:
        AntiPatterns:
            - account_id 미채움 → 터미널 substring 오매칭(비유동자산↔유동자산).
            - Q4 standalone 발행 → DART reprt_code 부재로 중복/충돌.
        OutputSchema:
            - pl.DataFrame(FINANCE_COLUMNS) | None.
        Prerequisites:
            - 로컬 edgar/finance/{cik}.parquet(companyfacts) 또는 자동 다운로드.
        Freshness:
            - companyfacts 최신 분기 기준(파사드 panel 시점).
        Dataflow:
            - companyfacts → Company.panel(wide 표준) → unpivot long → account_id 정확매칭 → FINANCE_COLUMNS.
        TargetMarkets:
            - US (EDGAR) 터미널 재무.
    """
    if company is None:
        import dartlab

        company = dartlab.Company(ticker)

    idx = _stdIdIndex()
    rows: list[dict] = []
    ordCounter = 0

    for stmt in _STMTS:
        try:
            wide = company.panel(stmt)
        except Exception:  # noqa: BLE001 — 명세별 격리(개별 표 실패 → 그 표만 skip)
            continue
        if not hasattr(wide, "columns") or "항목" not in wide.columns:
            continue
        periodCols = [c for c in wide.columns if c not in ("snakeId", "항목")]

        seen: set[tuple] = set()
        for row in wide.iter_rows(named=True):
            hangmok = row.get("항목")
            if not hangmok:
                continue
            accId = idx.get((stmt, str(hangmok).strip()), "")
            # year → {q: val}
            byYear: dict[int, dict[int, float]] = {}
            for pc in periodCols:
                val = row.get(pc)
                if val is None:
                    continue
                yq = _parsePeriodCol(str(pc))
                if yq is None:
                    continue
                year, q = yq
                dedupKey = (stmt, hangmok, year, q)
                if dedupKey in seen:  # synonym 중복행(revenue+sales→매출액) 첫 행만
                    continue
                seen.add(dedupKey)
                byYear.setdefault(year, {})[q] = float(val)

            for year, qmap in byYear.items():
                # 분기 standalone Q1~Q3 (Q4 는 DART slot 부재 → 터미널 역산)
                for q in (1, 2, 3):
                    if q in qmap:
                        rows.append(_mkRow(stmt, _Q_TO_REPRT[q], year, accId, hangmok, qmap[q], ordCounter))
                        ordCounter += 1
                # 연간 slot(11011): flow=4 분기 합(완전 연도만), BS=회계연말(Q4 우선)
                annual = _annualValue(stmt, qmap)
                if annual is not None:
                    rows.append(_mkRow(stmt, "11011", year, accId, hangmok, annual, ordCounter))
                    ordCounter += 1

    if not rows:
        return None
    return pl.DataFrame(rows).select(list(FINANCE_COLUMNS))


def _annualValue(stmt: str, qmap: dict[int, float]) -> float | None:
    """연간 slot 값 — flow(IS/CF)=4 분기 합(완전 연도만), BS=회계연말(Q4, 없으면 최신 분기)."""
    if stmt == "BS":
        if 4 in qmap:
            return qmap[4]
        return qmap[max(qmap)] if qmap else None
    # flow — 4 분기 모두 있을 때만 연간(부분 연도는 DART 사업보고서 부재와 동형으로 미발행)
    if all(q in qmap for q in (1, 2, 3, 4)):
        return qmap[1] + qmap[2] + qmap[3] + qmap[4]
    return None


def _mkRow(stmt: str, reprtCode: str, year: int, accId: str, hangmok: str, val: float, ordinal: int) -> dict:
    """FINANCE_COLUMNS 단일 행 dict — fs_div=CFS(EDGAR 연결 단일), account_detail='-'(score 우선)."""
    return {
        "sj_div": stmt,
        "fs_div": "CFS",
        "reprt_code": reprtCode,
        "rcept_no": "",
        "bsns_year": str(year),
        "account_id": accId,
        "account_nm": hangmok,
        "account_detail": "-",
        "thstrm_amount": val,
        "thstrm_add_amount": None,
        "ord": ordinal,
    }
