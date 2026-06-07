"""비용상세 × finance 합성 builder — Company 파사드 ``c.panel("expenseDetail")`` 백엔드.

panel 비용상세(panel.expenseDetail, finance import 0)와 손익계산서(finance.pivot.buildAnnual,
무수정)를 *합성 계층*(builder)에서 결합한다. cross-source 제품이라 panel(R1)·finance 어느 쪽도
서로 import 하지 않고, 본 builder 가 sce/ratios 처럼 ``company`` 를 받아 둘을 합성한다. 설계는
DESIGN_DEBATE.md v2~v6:

    - **단위**: panel 선언단위(천원/백만원) 1순위, 없으면 per-year finance 비율 scale(10^n, 순환 0).
    - **status**: detail 합 × scale 을 finance 판관비/매출원가와 band 비교(matched/near/partial/mismatch).
    - **ratio-mode**: mismatch 를 dedupBug(고칠 수 있음) vs honestGap(데이터 한계)으로 분류.
    - **by-nature lane(v6)**: noPanelDetail 회사의 성격별 노트를 영업비용/판관비에 대조해 회복.
      마커가 타깃 결정·finance 는 사후검산(순환 0). reconciledTarget=operatingExpense|sga 로 물리 분리.

레이어: composition(builder). 공개 진입 = ``expenseDetail(company)`` (Company._expenseDetail 호출).
reconcile/expenseBreakdown 등 ``code`` 기반 내부 helper 는 stockCode 단위 재사용.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import polars as pl

from dartlab.core.accounts.expenseDetail import (
    OUTPUT_SCHEMA,
    coarseBucket,
    ratioMode,
    reconciliationStatus,
    resolveByNatureTarget,
    yearUnitScale,
)
from dartlab.providers.dart.panel.expenseDetail import (
    annualCategorySums,
    annualSgaDetailSums,
    expenseDetailRows,
)

_SCHEMA_COLUMNS: tuple[str, ...] = tuple(column.column for column in OUTPUT_SCHEMA)

_LANE_RECONCILE: tuple[tuple[str, str, str], ...] = (
    ("strictSgaDetail", "selling_and_administrative_expenses", "sellingGeneralAdministrativeExpenses"),
    ("strictCostOfSalesDetail", "cost_of_sales", "costOfSales"),
)


def financeAnnualIs(code: str) -> dict[str, dict[str, float | None]] | None:
    """finance.buildAnnual IS → {snakeId: {year: value}}. finance 본체 무수정 호출.

    Args:
        code: 6자리 종목코드.

    Returns:
        dict | None — {snakeId: {year: value}} IS 시계열. finance 없으면 None.

    Example:
        >>> financeAnnualIs("005930")  # doctest: +SKIP

    Raises:
        없음.
    """
    from dartlab.providers.dart.finance.pivot import buildAnnual

    result = buildAnnual(code)
    if result is None:
        return None
    series, years = result
    return {
        snakeId: {year: values[i] if i < len(values) else None for i, year in enumerate(years)}
        for snakeId, values in series.get("IS", {}).items()
    }


def _resolvedAnnual(
    code: str,
    financeByYear: dict[str, float | None],
    *,
    lane: str = "strictSgaDetail",
    single: dict[str, Any] | None = None,
    singleCat: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """연도별 단일/결합 해소 — 단일이 과소추출(<0.6×finance)할 때만 결합 시도, finance×1.10 cap.

    잘 추출되는 회사는 단일(과다추출 0). 판매비+관리비 분할로 과소추출한 회사(기아 2022)만
    결합으로 메우되 finance 총액을 넘지 않게 한다. finance 는 *선택* 아니라 *상한*(C cross-validate).
    single/singleCat 를 pre-read 로 받으면 panel 재읽기를 피한다.
    """
    if single is None:
        single = annualSgaDetailSums(code, lane=lane, scope="consolidated")
    if singleCat is None:
        singleCat = annualCategorySums(code, lane=lane, scope="consolidated")
    combined: dict[str, Any] | None = None
    combinedCat: dict[str, Any] | None = None
    out: dict[str, dict[str, Any]] = {}
    for year, fin in financeByYear.items():
        if fin in (None, 0) or year not in single:
            continue
        ext = float(single[year]["extractedSum"])
        declared = single[year].get("unitFactor")
        scale = float(declared) if declared else yearUnitScale(ext, float(fin))
        mapped = float(single[year]["mappedSum"])
        chosen = {
            "scale": scale,
            "extracted": ext * scale,
            "mapped": mapped,
            "cats": singleCat.get(year, {}),
            "source": "single",
        }
        if ext * scale < 0.6 * float(fin):  # 과소추출 → 결합 fallback.
            if combined is None:
                combined = annualSgaDetailSums(code, lane=lane, scope="consolidated", combine=True)
                combinedCat = annualCategorySums(code, lane=lane, scope="consolidated", combine=True)
            if year in combined:
                cext = float(combined[year]["extractedSum"])
                cdecl = combined[year].get("unitFactor")
                cscale = float(cdecl) if cdecl else yearUnitScale(cext, float(fin))
                if chosen["extracted"] < cext * cscale <= float(fin) * 1.10:
                    chosen = {
                        "scale": cscale,
                        "extracted": cext * cscale,
                        "mapped": float(combined[year]["mappedSum"]),
                        "cats": (combinedCat or {}).get(year, {}),
                        "source": "combined",
                    }
        chosen["finance"] = float(fin)
        chosen["unitFactor"] = declared
        out[year] = chosen
    return out


def reconcileLane(
    code: str, lane: str, snakeId: str, statementKey: str, financeIs: dict[str, dict[str, float | None]]
) -> dict[str, Any]:
    """한 lane(판관비명세/매출원가명세) detail 합을 finance IS 타깃과 연도별 대조 → status/mode/coverage.

    Args:
        code: 6자리 종목코드.
        lane: strictSgaDetail/strictCostOfSalesDetail.
        snakeId: finance IS 타깃 계정(selling_and_administrative_expenses 등).
        statementKey: 출력 lanes dict 키.
        financeIs: financeAnnualIs 결과.

    Returns:
        dict — latestStatus/statusCounts/perYear 등 lane reconcile 결과(없으면 status=noPanelDetail).

    Example:
        >>> reconcileLane("005930", "strictSgaDetail", "selling_and_administrative_expenses",
        ...               "sellingGeneralAdministrativeExpenses", {})  # doctest: +SKIP

    Raises:
        없음.
    """
    single = annualSgaDetailSums(code, lane=lane, scope="consolidated")
    if not single:
        return {"lane": lane, "statementKey": statementKey, "status": "noPanelDetail"}
    finance = financeIs.get(snakeId, {})
    if not finance or all(v is None for v in finance.values()):
        return {"lane": lane, "statementKey": statementKey, "status": "noFinanceTarget"}
    singleCat = annualCategorySums(code, lane=lane, scope="consolidated")
    resolved = _resolvedAnnual(code, finance, lane=lane, single=single, singleCat=singleCat)
    if not resolved:
        return {"lane": lane, "statementKey": statementKey, "status": "noYearOverlap"}

    perYear: list[dict[str, Any]] = []
    statusCounts: dict[str, int] = {}
    modeCounts: dict[str, int] = {}
    scaleSource: set[str] = set()
    for year in sorted(resolved, reverse=True):
        r = resolved[year]
        fin = r["finance"]
        extracted = r["extracted"]
        src = "declared" if r["unitFactor"] else "financeRatio"
        scaleSource.add(src)
        coverage = extracted / fin
        status = reconciliationStatus(extracted, fin)
        mode = ratioMode(coverage) if status not in ("matched", "near") else "matched"
        statusCounts[status] = statusCounts.get(status, 0) + 1
        modeCounts[mode] = modeCounts.get(mode, 0) + 1
        # mapping/coarse coverage = 추출 금액 중 명명/coarse-비교가능 비율(단위 무관 — 같은 분모).
        extractedAbs = extracted / r["scale"] if r["scale"] else 0
        mapCov = r["mapped"] / extractedAbs if extractedAbs else None
        coarseExtracted = sum(amt for k, amt in r["cats"].items() if coarseBucket(k) != "etc")
        coarseCov = coarseExtracted / extractedAbs if extractedAbs else None
        perYear.append(
            {
                "year": year,
                "financeValue": fin,
                "panelExtracted": round(extracted, 2),
                "extractionCoverage": round(coverage, 4),
                "mappingCoverage": round(mapCov, 4) if mapCov is not None else None,
                "coarseCoverage": round(coarseCov, 4) if coarseCov is not None else None,
                "scale": r["scale"],
                "scaleSource": src,
                "status": status,
                "ratioMode": mode,
            }
        )
    if not perYear:
        return {"lane": lane, "statementKey": statementKey, "status": "noYearOverlap"}
    return {
        "lane": lane,
        "statementKey": statementKey,
        "latestStatus": perYear[0]["status"],
        "latestMode": perYear[0]["ratioMode"],
        "latestMappingCoverage": perYear[0]["mappingCoverage"],
        "latestCoarseCoverage": perYear[0]["coarseCoverage"],
        "yearCount": len(perYear),
        "statusCounts": statusCounts,
        "modeCounts": modeCounts,
        "scaleSources": sorted(scaleSource),
        "perYear": perYear[:8],
    }


def reconcileByNatureLane(code: str, financeIs: dict[str, dict[str, float | None]]) -> dict[str, Any]:
    """성격별(by-nature) 노트 → finance 영업비용/판관비 대조. noPanelDetail 회복 lane(DESIGN_DEBATE v6).

    *마커*(원재료/재고변동/상품매입)가 타깃을 결정하고 finance 는 *사후검산*만(순환 0, C 강제조건 ①).
    영업비용 마커 보유 → 매출원가+판관비 대조(opexByNature), 없음 → 판관비 단독 대조(sgaByNature).
    매출원가 없는 회사(플랫폼·지주)는 영업비용=판관비라 sga 타깃으로 판관비 상세 직접 회복.
    consolidated 우선, 없으면 separate 폴백(scope fallback lever).

    Args:
        code: 6자리 종목코드.
        financeIs: financeAnnualIs 결과.

    Returns:
        dict — latestStatus/latestTarget/perYear(reconciledTarget 포함). 노트 없으면 noPanelByNature.

    Example:
        >>> reconcileByNatureLane("000080", {})  # doctest: +SKIP

    Raises:
        없음.
    """
    scope = "consolidated"
    byNature = annualSgaDetailSums(code, lane="strictExpensesByNature", scope=scope)
    if not byNature:
        scope = "separate"
        byNature = annualSgaDetailSums(code, lane="strictExpensesByNature", scope=scope)
    if not byNature:
        return {"lane": "strictExpensesByNature", "status": "noPanelByNature"}
    sgaByYear = financeIs.get("selling_and_administrative_expenses", {})
    cogsByYear = financeIs.get("cost_of_sales", {})

    perYear: list[dict[str, Any]] = []
    statusCounts: dict[str, int] = {}
    targetCounts: dict[str, int] = {}
    for year in sorted(byNature, reverse=True):
        b = byNature[year]
        res = resolveByNatureTarget(b.get("labels", []), sgaByYear.get(year), cogsByYear.get(year))
        target = res["target"]
        checkTotal = res["checkTotal"]
        ratio: float | None = None
        if not checkTotal:
            status = "noFinanceTarget"
        else:
            ext = float(b["extractedSum"])
            declared = b.get("unitFactor")
            scale = float(declared) if declared else yearUnitScale(ext, float(checkTotal))
            scaled = ext * scale
            ratio = round(scaled / checkTotal, 4)
            status = reconciliationStatus(scaled, checkTotal)
        statusCounts[status] = statusCounts.get(status, 0) + 1
        targetCounts[target] = targetCounts.get(target, 0) + 1
        perYear.append(
            {
                "year": year,
                "reconciledTarget": target,  # operatingExpense | sga (C 강제조건 ②: 물리 분리)
                "checkTotal": checkTotal,
                "ratio": ratio,
                "detailCount": b["detailCount"],
                "scaleSource": "declared" if b.get("unitFactor") else "financeRatio",
                "status": status,
            }
        )
    latest = perYear[0]
    return {
        "lane": "strictExpensesByNature",
        "scope": scope,
        "latestStatus": latest["status"],
        "latestTarget": latest["reconciledTarget"],
        "latestRatio": latest["ratio"],
        "yearCount": len(perYear),
        "statusCounts": statusCounts,
        "targetCounts": targetCounts,
        "perYear": perYear[:8],
    }


# sga 명세가 *비어*(아래 상태)일 때만 by-nature 를 회복으로 카운트한다(이중계상 금지, C 강제조건 ②).
_SGA_NO_DETAIL: frozenset[str] = frozenset({"noPanelDetail", "noYearOverlap", "noFinanceTarget"})


def reconcile(code: str) -> dict[str, Any]:
    """한 회사 비용상세 × finance 결합 결과(판관비·매출원가·by-nature lane).

    Args:
        code: 6자리 종목코드.

    Returns:
        dict — sgaLatestStatus/byNatureStatus/byNatureRecovers/lanes(perYear status) 등.

    Example:
        >>> reconcile("005930")["sgaLatestStatus"]  # doctest: +SKIP

    Raises:
        없음.
    """
    financeIs = financeAnnualIs(code)
    if financeIs is None:
        return {"code": code, "status": "noFinance"}
    lanes = {sk: reconcileLane(code, lane, snakeId, sk, financeIs) for lane, snakeId, sk in _LANE_RECONCILE}
    sga = lanes["sellingGeneralAdministrativeExpenses"]
    sgaStatus = sga.get("latestStatus", sga.get("status"))
    byNature = reconcileByNatureLane(code, financeIs)
    # by-nature 는 sga 명세가 없을 때만 *회복*(matched/near)으로 카운트. 셀단위 정직 — 연도별 status 보존.
    byNatureRecovers = sgaStatus in _SGA_NO_DETAIL and byNature.get("latestStatus") in ("matched", "near")
    return {
        "code": code,
        "status": "ok",
        "sgaLatestStatus": sgaStatus,
        "sgaLatestMode": sga.get("latestMode"),
        "sgaLatestMappingCoverage": sga.get("latestMappingCoverage"),
        "sgaLatestCoarseCoverage": sga.get("latestCoarseCoverage"),
        "byNatureStatus": byNature.get("latestStatus", byNature.get("status")),
        "byNatureTarget": byNature.get("latestTarget"),
        "byNatureRatio": byNature.get("latestRatio"),
        "byNatureRecovers": byNatureRecovers,
        "byNatureRecoveryTarget": byNature.get("latestTarget") if byNatureRecovers else None,
        "lanes": {**lanes, "expensesByNature": byNature},
    }


def expenseBreakdown(code: str) -> dict[str, Any]:
    """FnGuide식 완전 분해 — 판관비 총액(finance) = 카테고리 합 + 기타(잔차). 항상 100% 정합.

    공시된 라인은 카테고리로, 나머지(미명명 + 미공시)는 '기타미분류' 잔차로 흡수해 합이
    *정확히* 손익계산서 판관비가 되게 한다. completeness = 1 - 기타/총액(공시 granularity).

    Args:
        code: 6자리 종목코드.

    Returns:
        dict — {years: {year: {financeTotal, categories(+기타미분류), namedCoverage, residualShare}}}.

    Example:
        >>> expenseBreakdown("005930")["years"]  # doctest: +SKIP

    Raises:
        없음.
    """
    financeIs = financeAnnualIs(code)
    if financeIs is None:
        return {"code": code, "status": "noFinance"}
    finance = financeIs.get("selling_and_administrative_expenses", {})
    if not finance or all(v is None for v in finance.values()):
        return {"code": code, "status": "noFinanceTarget"}
    resolved = _resolvedAnnual(code, finance)

    years: dict[str, Any] = {}
    for year in sorted(resolved, reverse=True):
        r = resolved[year]
        total = r["finance"]
        scale = r["scale"]
        scaledCats = {key: round(amt * scale, 2) for key, amt in r["cats"].items()}
        namedSum = sum(scaledCats.values())
        residual = round(total - namedSum, 2)
        # 잔차가 음수(과다추출)면 분해 신뢰 낮음 — 잔차 0.
        scaledCats["기타미분류"] = residual if residual >= 0 else 0.0
        years[year] = {
            "financeTotal": total,
            "categories": scaledCats,
            "namedCoverage": round(namedSum / total, 4),
            "residualShare": round(max(residual, 0.0) / total, 4),
            "source": r["source"],
        }
    return {"code": code, "status": "ok", "years": years}


# sourceLane(panel) → reconcile lanes dict key. 프레임 status 병합용.
_LANE_BY_SOURCE: dict[str, str] = {
    "strictSgaDetail": "sellingGeneralAdministrativeExpenses",
    "strictCostOfSalesDetail": "costOfSales",
    "strictExpensesByNature": "expensesByNature",
}


def _reconcileStatusRows(rec: dict[str, Any]) -> list[dict[str, Any]]:
    """reconcile 결과 → (연도, scope, sourceLane)별 status/reconciledTarget 행 — 프레임 병합 키."""
    rows: list[dict[str, Any]] = []
    lanes = rec.get("lanes", {})
    for sourceLane, laneKey in _LANE_BY_SOURCE.items():
        lane = lanes.get(laneKey, {})
        scope = lane.get("scope", "consolidated")
        for perYear in lane.get("perYear", []) or []:
            rows.append(
                {
                    "_y": str(perYear["year"]),
                    "_s": scope,
                    "_l": sourceLane,
                    "_st": perYear.get("status"),
                    "_rt": perYear.get("reconciledTarget"),
                }
            )
    return rows


def _applyReconcile(frame: pl.DataFrame, statusRows: list[dict[str, Any]]) -> pl.DataFrame:
    """expenseDetailRows 프레임에 reconcile status/reconciledTarget 를 (연도·scope·lane) join 으로 병합."""
    if frame.is_empty() or not statusRows:
        return frame
    mapDf = pl.DataFrame(
        statusRows, schema={"_y": pl.Utf8, "_s": pl.Utf8, "_l": pl.Utf8, "_st": pl.Utf8, "_rt": pl.Utf8}
    )
    out = frame.with_columns(
        pl.col("period").str.slice(0, 4).alias("_y"),
        pl.col("scope").alias("_s"),
        pl.col("sourceLane").alias("_l"),
    ).join(mapDf, on=["_y", "_s", "_l"], how="left")
    out = out.with_columns(
        pl.when((pl.col("rowRole") == "detail") & pl.col("_st").is_not_null())
        .then(pl.col("_st"))
        .otherwise(pl.col("reconciliationStatus"))
        .alias("reconciliationStatus"),
        pl.coalesce(["_rt", "reconciledTarget"]).alias("reconciledTarget"),
    )
    return out.select(_SCHEMA_COLUMNS)


def expenseDetail(company: Any) -> pl.DataFrame | None:
    """Company 비용상세 long DataFrame — panel 추출 + finance reconcile 병합. ``c.panel("expenseDetail")`` 백엔드.

    panel.expenseDetailRows(23컬럼)에 reconcile 결과를 (연도·scope·lane)로 병합해 detail 행의
    reconciliationStatus 를 채우고, by-nature 행엔 reconciledTarget(operatingExpense|sga)을 부여한다.
    sce/ratios builder 와 동형 — ``company`` self 를 받아 panel·finance 를 합성, ``company._cache`` 캐시.

    Args:
        company: DART Company 인스턴스(stockCode·_cache 사용).

    Returns:
        pl.DataFrame | None — OUTPUT_SCHEMA 23컬럼 long(reconciliationStatus·reconciledTarget 채움).

    Example:
        >>> import dartlab; dartlab.Company("005930").panel("expenseDetail")  # doctest: +SKIP

    Raises:
        없음.
    """
    cacheKey = "_expenseDetail"
    cache = getattr(company, "_cache", None)
    if cache is not None and cacheKey in cache:
        return cache[cacheKey]
    frame = expenseDetailRows(str(company.stockCode))
    if not frame.is_empty():
        frame = _applyReconcile(frame, _reconcileStatusRows(reconcile(str(company.stockCode))))
    if cache is not None:
        cache[cacheKey] = frame
    return frame


def expenseBreakdownForCompany(company: Any) -> dict[str, Any]:
    """Company 판관비 완전분해(FnGuide식 기타-잔차) — expenseBreakdown 의 company 래퍼.

    Args:
        company: DART Company 인스턴스.

    Returns:
        dict — expenseBreakdown 결과({years: {...}}).

    Example:
        >>> expenseBreakdownForCompany(dartlab.Company("005930"))  # doctest: +SKIP

    Raises:
        없음.
    """
    return expenseBreakdown(str(company.stockCode))


def main(argv: list[str] | None = None) -> int:
    """CLI — 종목별 reconcile(기본) 또는 ``--breakdown`` 완전분해 출력(개발용).

    Args:
        argv: 종목코드 리스트(없으면 sys.argv 또는 기본 표본).

    Returns:
        int — 종료 코드 0.

    Example:
        >>> main(["005930"])  # doctest: +SKIP

    Raises:
        없음.
    """
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--breakdown":
        for code in args[1:] or ["005930", "000270"]:
            print(json.dumps(expenseBreakdown(str(code).zfill(6)), ensure_ascii=False, indent=2))
        return 0
    for code in args or ["005930", "000700", "035420"]:
        print(json.dumps(reconcile(str(code).zfill(6)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
