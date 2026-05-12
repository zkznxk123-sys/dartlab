"""거버넌스 6축 report 스캔."""

from __future__ import annotations

import polars as pl

from dartlab.scan.io.parquet import (
    findLatestYear,
    parseNumStr,
    pickBestQuarter,
    scanParquets,
)


def scanMajorHolderPct() -> dict[str, float]:
    """전종목 최대주주 지분율 스캔.

    majorHolder parquet에서 최신 연도의 최대주주 지분율을 추출한다.
    종목별로 해당 연도 내 가장 높은 지분율 값을 선택한다.

    Returns
    -------
    dict[str, float]
        종목코드 : 최대주주 지분율 (%)
        빈 dict — 데이터 없음
    """
    raw = scanParquets(
        "majorHolder",
        ["stockCode", "year", "quarter", "bsis_posesn_stock_qota_rt"],
    )
    if raw.is_empty():
        return {}

    latest_year = findLatestYear(raw, "bsis_posesn_stock_qota_rt", 1000)
    if latest_year is None:
        return {}

    result: dict[str, float] = {}
    sub = raw.filter(pl.col("year") == latest_year)
    for code, group in sub.group_by("stockCode"):
        vals = []
        for row in group.iter_rows(named=True):
            v = parseNumStr(row.get("bsis_posesn_stock_qota_rt"))
            if v is not None and 0 <= v <= 100:
                vals.append(v)
        if vals:
            result[code[0]] = max(vals)
    return result


def scanOutsideDirectors() -> dict[str, dict]:
    """전종목 사외이사 현황 스캔.

    outsideDirector parquet의 drctr_co/otcmp_drctr_co 집계값을 사용한다.
    해당 parquet이 비어 있으면 executive parquet의 ofcps 문자열을 파싱하여
    fallback 처리한다.

    Returns
    -------
    dict[str, dict]
        종목코드 : dict
            사외이사비율 : float — 사외이사 비율 (%)
            중도사임 : int — 중도사임 인원 (명)
            겸직 : int — 겸직 인원 (명)
        빈 dict — 데이터 없음
    """
    raw = scanParquets(
        "outsideDirector",
        ["stockCode", "year", "quarter", "drctr_co", "otcmp_drctr_co", "mdstrm_resig", "rlsofc"],
    )

    if not raw.is_empty():
        return _outsideFromDedicated(raw)

    # fallback: executive parquet
    return _outsideFromExecutive()


def _outsideFromDedicated(raw: pl.DataFrame) -> dict[str, dict]:
    """outsideDirector parquet에서 사외이사 현황 집계.

    최신 연도의 종목별 이사 수(drctr_co)와 사외이사 수(otcmp_drctr_co)를
    합산하여 비율을 계산하고, 중도사임·겸직 인원을 집계한다.

    Parameters
    ----------
    raw : pl.DataFrame
        outsideDirector parquet 로드 결과

    Returns
    -------
    dict[str, dict]
        종목코드 : dict
            사외이사비율 : float — 사외이사 비율 (%)
            중도사임 : int — 중도사임 인원 (명)
            겸직 : int — 겸직 인원 (명)
    """
    latestYear = findLatestYear(raw, "drctr_co", 500)
    if latestYear is None:
        return {}

    sub = raw.filter(pl.col("year") == latestYear)
    result: dict[str, dict] = {}

    for code, group in sub.group_by("stockCode"):
        codeVal = code[0]
        qdf = pickBestQuarter(group)

        totalDirectors = 0
        outsideDirectors = 0
        resignCount = 0
        concurrentCount = 0

        for row in qdf.iter_rows(named=True):
            d = parseNumStr(row.get("drctr_co"))
            o = parseNumStr(row.get("otcmp_drctr_co"))
            r = parseNumStr(row.get("mdstrm_resig"))
            c = parseNumStr(row.get("rlsofc"))

            if d and d > 0:
                totalDirectors += int(d)
            if o and o > 0:
                outsideDirectors += int(o)
            if r and r > 0:
                resignCount += int(r)
            if c and c > 0:
                concurrentCount += int(c)

        if totalDirectors > 0:
            result[codeVal] = {
                "사외이사비율": outsideDirectors / totalDirectors * 100,
                "중도사임": resignCount,
                "겸직": concurrentCount,
            }

    return result


def _outsideFromExecutive() -> dict[str, dict]:
    """executive parquet fallback으로 사외이사 비율 추정.

    ofcps 컬럼에서 '사외' 문자열을 포함하는 행을 사외이사로 간주한다.
    중도사임·겸직 정보는 executive parquet에 없어 0으로 고정.

    Returns
    -------
    dict[str, dict]
        종목코드 : dict
            사외이사비율 : float — 사외이사 비율 (%)
            중도사임 : int — 항상 0 (명)
            겸직 : int — 항상 0 (명)
    """
    raw = scanParquets(
        "executive",
        ["stockCode", "year", "quarter", "ofcps"],
    )
    if raw.is_empty():
        return {}

    latestYear = findLatestYear(raw, "ofcps", 1000)
    if latestYear is None:
        return {}

    result: dict[str, dict] = {}
    sub = raw.filter(pl.col("year") == latestYear)
    for code, group in sub.group_by("stockCode"):
        total = group.shape[0]
        outside = sum(1 for row in group.iter_rows(named=True) if row.get("ofcps") and "사외" in row["ofcps"])
        result[code[0]] = {
            "사외이사비율": outside / total * 100 if total > 0 else 0,
            "중도사임": 0,
            "겸직": 0,
        }
    return result


def scanPayRatio() -> dict[str, float]:
    """전종목 임원-직원 보수 배율 스캔.

    executivePayAllTotal parquet에서 임원 평균보수를, employee parquet에서
    직원 평균급여를 산출한 뒤 비율을 계산한다. 500배 초과는 데이터 오류로
    판단하여 제외한다.

    Returns
    -------
    dict[str, float]
        종목코드 : 임원/직원 보수 배율 (배)
        빈 dict — 데이터 없음
    """
    raw_pay = scanParquets(
        "executivePayAllTotal",
        ["stockCode", "year", "quarter", "nmpr", "jan_avrg_mendng_am"],
    )
    raw_emp = scanParquets(
        "employee",
        ["stockCode", "year", "quarter", "sm", "jan_salary_am"],
    )
    if raw_pay.is_empty() or raw_emp.is_empty():
        return {}

    # 임원 평균보수
    pay_map: dict[str, float] = {}
    latest = findLatestYear(raw_pay, "jan_avrg_mendng_am", 500)
    if latest:
        sub = raw_pay.filter(pl.col("year") == latest)
        for code, group in sub.group_by("stockCode"):
            qdf = pickBestQuarter(group)
            wsum, tnmpr = 0.0, 0
            for row in qdf.iter_rows(named=True):
                n = parseNumStr(row.get("nmpr"))
                p = parseNumStr(row.get("jan_avrg_mendng_am"))
                if n and n > 0 and p and p > 0:
                    wsum += n * p
                    tnmpr += int(n)
            if tnmpr > 0:
                pay_map[code[0]] = wsum / tnmpr

    # 직원 평균급여
    salMap: dict[str, float] = {}
    latest = findLatestYear(raw_emp, "jan_salary_am", 500)
    if latest:
        sub = raw_emp.filter(pl.col("year") == latest)
        for code, group in sub.group_by("stockCode"):
            qdf = pickBestQuarter(group)
            wsum, temp = 0.0, 0
            for row in qdf.iter_rows(named=True):
                e = parseNumStr(row.get("sm"))
                s = parseNumStr(row.get("jan_salary_am"))
                if e and e > 0 and s and s > 0:
                    wsum += e * s
                    temp += int(e)
            if temp > 0:
                salMap[code[0]] = wsum / temp

    result: dict[str, float] = {}
    for code in pay_map:
        if code in salMap and salMap[code] > 0:
            ratio = pay_map[code] / salMap[code]
            # pay_ratio 극단값 cap: 500배 초과는 데이터 오류
            if ratio > 500:
                continue
            result[code] = ratio
    return result


def scanAuditOpinion() -> dict[str, str]:
    """전종목 감사의견 스캔.

    auditOpinion parquet에서 유효 데이터가 500건 이상인 최신 연도를 선택하고,
    종목별로 가장 나쁜 감사의견(의견거절 > 부적정 > 한정 > 적정)을 반환한다.

    Returns
    -------
    dict[str, str]
        종목코드 : 감사의견 문자열 (적정의견 | 한정의견 | 부적정의견 | 의견거절)
        빈 dict — 데이터 없음
    """
    raw = scanParquets(
        "auditOpinion",
        ["stockCode", "year", "quarter", "adt_opinion"],
    )
    if raw.is_empty():
        return {}

    opinion_rank = {"의견거절": 4, "부적정의견": 3, "한정의견": 2, "적정의견": 1}
    result: dict[str, str] = {}
    years_desc = sorted(raw["year"].unique().to_list(), reverse=True)
    for y in years_desc:
        sub = raw.filter(pl.col("year") == y)
        if sub.filter(pl.col("adt_opinion").is_not_null()).shape[0] < 500:
            continue
        for code, group in sub.group_by("stockCode"):
            valid_rows = group.filter(pl.col("adt_opinion").is_not_null())
            if valid_rows.is_empty():
                continue
            worst, worst_op = 0, None
            for row in valid_rows.iter_rows(named=True):
                op = row.get("adt_opinion")
                if op:
                    r = opinion_rank.get(op, 0)
                    if r > worst:
                        worst = r
                        worst_op = op
                    elif worst_op is None:
                        worst_op = op
            if worst_op:
                result[code[0]] = worst_op
        break
    return result


def scanMinorityHolder() -> dict[str, float]:
    """전종목 소액주주 지분율 스캔.

    minorityHolder parquet에서 hold_stock_rate를 추출한다.
    값이 높을수록 주주 분산이 양호함을 의미한다.

    Returns
    -------
    dict[str, float]
        종목코드 : 소액주주 지분율 (%)
        빈 dict — 데이터 없음
    """
    raw = scanParquets(
        "minorityHolder",
        ["stockCode", "year", "quarter", "hold_stock_rate"],
    )
    if raw.is_empty():
        return {}

    latestYear = findLatestYear(raw, "hold_stock_rate", 500)
    if latestYear is None:
        return {}

    sub = raw.filter(pl.col("year") == latestYear)
    result: dict[str, float] = {}

    for code, group in sub.group_by("stockCode"):
        codeVal = code[0]
        qdf = pickBestQuarter(group)
        vals = []
        for row in qdf.iter_rows(named=True):
            raw_val = row.get("hold_stock_rate")
            if raw_val is not None:
                cleaned = str(raw_val).strip().rstrip("%")
                v = parseNumStr(cleaned)
                if v is not None and 0 <= v <= 100:
                    vals.append(v)
        if vals:
            result[codeVal] = max(vals)

    return result
