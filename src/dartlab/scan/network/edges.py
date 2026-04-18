"""엣지 구축 — investedCompany, majorHolder 원본 → 정제 엣지 테이블."""

from __future__ import annotations

import re

import polars as pl

from dartlab.scan.network.scanner import _normalize_company_name

# ── investedCompany 엣지 ───────────────────────────────────


def build_invest_edges(
    raw: pl.DataFrame,
    name_to_code: dict[str, str],
    code_to_name: dict[str, str],
) -> pl.DataFrame:
    """investedCompany 원본 DataFrame을 정제된 출자 엣지 테이블로 변환한다.

    노이즈 행 제거, 지분율/장부가액 파싱, 투자목적 정규화, 피투자법인
    이름을 상장사 코드에 매칭한다.

    Parameters
    ----------
    raw : pl.DataFrame
        DART investedCompany 원본 DataFrame.
    name_to_code : dict[str, str]
        회사명(정규화 포함) → 종목코드 매핑.
    code_to_name : dict[str, str]
        종목코드 → 회사명 매핑.

    Returns
    -------
    pl.DataFrame
        정제 엣지 테이블. 컬럼:

        - from_code : str — 출자 기업 종목코드
        - from_name : str — 출자 기업명
        - to_name : str — 피투자 법인명 (원본)
        - to_name_norm : str — 피투자 법인명 (정규화)
        - to_code : str | None — 피투자 기업 종목코드 (상장사만)
        - is_listed : bool — 피투자 기업 상장 여부
        - ownership_pct : float | None — 지분율 (%)
        - book_value : float | None — 장부가액 (원)
        - purpose : str — 투자목적 ("경영참여" | "단순투자" | "기타")
        - year : str — 보고 연도
    """
    noise_names = {"-", "합계", "소계", "", " "}
    df = raw.filter(pl.col("inv_prm").is_not_null() & ~pl.col("inv_prm").is_in(list(noise_names)))

    # 지분율
    if df["trmend_blce_qota_rt"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("trmend_blce_qota_rt")
            .str.replace_all(",", "")
            .str.replace_all("-", "")
            .cast(pl.Float64, strict=False)
            .alias("ownership_pct")
        )
    else:
        df = df.with_columns(pl.col("trmend_blce_qota_rt").cast(pl.Float64, strict=False).alias("ownership_pct"))
    df = df.with_columns(
        pl.when(pl.col("ownership_pct").is_between(0, 100))
        .then(pl.col("ownership_pct"))
        .otherwise(None)
        .alias("ownership_pct")
    )

    # 장부가액
    if df["trmend_blce_acntbk_amount"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("trmend_blce_acntbk_amount")
            .str.replace_all(",", "")
            .str.replace_all("-", "")
            .cast(pl.Float64, strict=False)
            .alias("book_value")
        )
    else:
        df = df.with_columns(pl.col("trmend_blce_acntbk_amount").cast(pl.Float64, strict=False).alias("book_value"))

    # 투자목적
    purpose_map = {
        "경영참여": "경영참여",
        "단순투자": "단순투자",
        "일반투자": "단순투자",
        "투자": "단순투자",
    }
    df = df.with_columns(
        pl.col("invstmnt_purps")
        .map_elements(
            lambda v: purpose_map.get(v, "기타") if v and v != "-" else "기타",
            return_dtype=pl.Utf8,
        )
        .alias("purpose")
    )

    # 법인명 매칭
    norms, codes, listed = [], [], []
    for name in df["inv_prm"].to_list():
        norm = _normalize_company_name(name)
        code = name_to_code.get(name) or name_to_code.get(norm)
        norms.append(norm)
        codes.append(code)
        listed.append(code is not None)

    df = df.with_columns(
        pl.Series("to_name_norm", norms),
        pl.Series("to_code", codes),
        pl.Series("is_listed", listed),
        pl.col("stockCode").map_elements(lambda c: code_to_name.get(c, c), return_dtype=pl.Utf8).alias("from_name"),
    )

    return df.select(
        [
            pl.col("stockCode").alias("from_code"),
            "from_name",
            pl.col("inv_prm").alias("to_name"),
            "to_name_norm",
            "to_code",
            "is_listed",
            "ownership_pct",
            "book_value",
            "purpose",
            "year",
        ]
    )


def deduplicate_edges(edges: pl.DataFrame) -> pl.DataFrame:
    """최신 연도만 남기고 (from_code, to_name_norm) 중복을 제거한다.

    동일 쌍이 여러 행이면 ownership_pct가 가장 높은 행을 유지한다.

    Parameters
    ----------
    edges : pl.DataFrame
        build_invest_edges 결과 DataFrame.

    Returns
    -------
    pl.DataFrame
        중복 제거된 DataFrame. 컬럼 구조는 입력과 동일:
        from_code, from_name, to_name, to_name_norm, to_code,
        is_listed, ownership_pct, book_value, purpose, year.
    """
    latest_year = edges["year"].max()
    return (
        edges.filter(pl.col("year") == latest_year)
        .sort("ownership_pct", descending=True, nulls_last=True)
        .unique(subset=["from_code", "to_name_norm"], keep="first")
    )


# ── majorHolder 엣지 ──────────────────────────────────────


_CORP_PATTERNS = re.compile(
    r"㈜|주식회사|\(주\)|법인|조합|재단|기금|공사|은행|증권|보험|캐피탈|투자|펀드|"
    r"[A-Z]{2,}|Co\.|Corp|Ltd|Inc|LLC|PTE|Fund|Trust|Bank"
)
_NOISE_NAMES = {"합계", "-", "소계", "", "계", "기타"}


def _classify_holder(name: str) -> str:
    """주주명으로 유형을 분류한다.

    법인 패턴(㈜, 주식회사, Corp 등), 한글 이름 길이, 전체 문자열
    길이를 기준으로 판별한다.

    Parameters
    ----------
    name : str
        주주명 원본 문자열.

    Returns
    -------
    str
        주주 유형. "corp" (법인) | "person" (개인) | "noise" (노이즈).
    """
    if not name or name in _NOISE_NAMES:
        return "noise"
    if _CORP_PATTERNS.search(name):
        return "corp"
    hangul = re.sub(r"[^가-힣]", "", name)
    if 2 <= len(hangul) <= 4 and len(name) <= 6:
        return "person"
    if len(name) > 8:
        return "corp"
    return "person"


def build_holder_edges(
    raw: pl.DataFrame,
    name_to_code: dict[str, str],
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """majorHolder 원본을 법인 엣지와 개인 엣지로 분리한다.

    최신 연도만 사용하며, 각 주주를 _classify_holder로 분류한 뒤
    법인은 상장사 코드 매칭을 시도한다.

    Parameters
    ----------
    raw : pl.DataFrame
        DART majorHolder 원본 DataFrame.
    name_to_code : dict[str, str]
        회사명(정규화 포함) → 종목코드 매핑.

    Returns
    -------
    tuple[pl.DataFrame, pl.DataFrame]
        (corp_edges, person_edges) 튜플.

        corp_edges 컬럼:

        - from_code : str | None — 법인주주 종목코드 (상장사만 매칭)
        - from_name : str — 법인주주명
        - to_code : str — 대상 기업 종목코드
        - relate : str — 관계 (최대주주/특수관계인 등)
        - ownership_pct : float | None — 지분율 (%)
        - year : str — 보고 연도

        person_edges 컬럼:

        - person_name : str — 개인주주명
        - to_code : str — 대상 기업 종목코드
        - relate : str — 관계
        - ownership_pct : float | None — 지분율 (%)
        - year : str — 보고 연도
    """
    df = raw.filter(pl.col("nm").is_not_null() & ~pl.col("nm").is_in(list(_NOISE_NAMES)))
    latest_year = df["year"].max()
    df = df.filter(pl.col("year") == latest_year)

    # 지분율
    if df["trmend_posesn_stock_qota_rt"].dtype == pl.Utf8:
        df = df.with_columns(
            pl.col("trmend_posesn_stock_qota_rt")
            .str.replace_all(",", "")
            .str.replace_all("-", "")
            .cast(pl.Float64, strict=False)
            .alias("ownership_pct")
        )
    else:
        df = df.with_columns(
            pl.col("trmend_posesn_stock_qota_rt").cast(pl.Float64, strict=False).alias("ownership_pct")
        )

    types, holder_codes = [], []
    for row in df.iter_rows(named=True):
        nm = row["nm"]
        t = _classify_holder(nm)
        types.append(t)
        if t == "corp":
            norm = _normalize_company_name(nm)
            holder_codes.append(name_to_code.get(nm) or name_to_code.get(norm))
        else:
            holder_codes.append(None)

    df = df.with_columns(
        pl.Series("holder_type", types),
        pl.Series("holder_code", holder_codes),
    )

    corp = df.filter(pl.col("holder_type") == "corp")
    corp_edges = corp.select(
        [
            pl.col("holder_code").alias("from_code"),
            pl.col("nm").alias("from_name"),
            pl.col("stockCode").alias("to_code"),
            pl.col("relate"),
            pl.col("ownership_pct"),
            pl.col("year"),
        ]
    )

    person = df.filter(pl.col("holder_type") == "person")
    person_edges = person.select(
        [
            pl.col("nm").alias("person_name"),
            pl.col("stockCode").alias("to_code"),
            pl.col("relate"),
            pl.col("ownership_pct"),
            pl.col("year"),
        ]
    )

    return corp_edges, person_edges
