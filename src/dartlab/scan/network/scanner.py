"""DART report parquet 스캔 — investedCompany, majorHolder, 계열회사 현황."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import polars as pl

_SCAN_CORP_RE = re.compile(r"[\(（]주[\)）]|㈜|주식회사")
_SCAN_REGNUM_RE = re.compile(r"\d{6}-?\d{7}")

# ── 공통 유틸 ──────────────────────────────────────────────


def _normalizeCompanyName(name: str) -> str:
    """법인명 정규화: 접두/접미사 제거."""
    if not name:
        return name
    s = name.strip()
    for pat in [
        r"^\(주\)\s*",
        r"^㈜\s*",
        r"^주식회사\s*",
        r"\s*\(주\)$",
        r"\s*㈜$",
        r"\s*주식회사$",
        r"\s*\(유\)$",
        r"^유한회사\s*",
        r"\s*유한회사$",
        r"\s*㈜",
        r"\(주\)",
    ]:
        s = re.sub(pat, "", s)
    return s.strip()


def loadListing() -> tuple[dict[str, str], dict[str, str], set[str], dict[str, dict]]:
    """상장사 목록 로드.

    Returns
    -------
    tuple
        (name_to_code, code_to_name, listing_codes, listing_meta)
        name_to_code : dict — 회사명 (정규화 포함) → 종목코드
        code_to_name : dict — 종목코드 → 회사명
        listing_codes : set[str] — 전체 상장사 종목코드
        listing_meta : dict — 종목코드 → {name, market, industry}

    Raises
    ------
    KeyError
        listing DataFrame 에 "회사명" · "종목코드" 컬럼 누락 시.

    Examples
    --------
    >>> from dartlab.scan.network.scanner import loadListing
    >>> n2c, c2n, codes, meta = loadListing()
    >>> c2n["005930"]
    '삼성전자'
    """
    import dartlab

    listing = dartlab.listing()
    nameToCode: dict[str, str] = {}
    codeToName: dict[str, str] = {}
    listing_meta: dict[str, dict] = {}

    for row in listing.iter_rows(named=True):
        name = row["회사명"]
        code = row["종목코드"]
        codeToName[code] = name
        nameToCode[name] = code
        norm = _normalizeCompanyName(name)
        if norm != name:
            nameToCode[norm] = code
        for prefix in ["㈜", "(주)", "주식회사 ", "주식회사"]:
            nameToCode[f"{prefix}{name}"] = code
        for suffix in [" ㈜", "㈜", " (주)", "(주)", " 주식회사", "주식회사"]:
            nameToCode[f"{name}{suffix}"] = code
        listing_meta[code] = {
            "name": name,
            "market": row.get("시장구분", ""),
            "industry": row.get("업종", ""),
        }

    listing_codes = set(listing["종목코드"].to_list())
    return nameToCode, codeToName, listing_codes, listing_meta


# ── parquet 스캔 ───────────────────────────────────────────


def _scanParquets(apiType: str, keepCols: list[str]) -> pl.DataFrame:
    """report parquet에서 특정 apiType만 LazyFrame 스캔."""
    from dartlab.core.dataLoader import _dataDir

    report_dir = Path(_dataDir("report"))
    parquet_files = sorted(report_dir.glob("*.parquet"))

    frames: list[pl.LazyFrame] = []
    for pf in parquet_files:
        try:
            lf = pl.scan_parquet(str(pf))
            if "apiType" not in lf.collect_schema().names():
                continue
            lf = lf.filter(pl.col("apiType") == apiType)
            available = [c for c in keepCols if c in lf.collect_schema().names()]
            lf = lf.select(available)
            frames.append(lf)
        except (pl.exceptions.ComputeError, OSError):
            continue

    all_cols: set[str] = set()
    for lf in frames:
        all_cols.update(lf.collect_schema().names())
    unified: list[pl.LazyFrame] = []
    for lf in frames:
        missing = all_cols - set(lf.collect_schema().names())
        if missing:
            lf = lf.with_columns([pl.lit(None).alias(c) for c in missing])
        unified.append(lf.select(sorted(all_cols)))

    return pl.concat(unified).collect(engine="streaming")


def scanInvested() -> pl.DataFrame:
    """전종목 investedCompany 스캔.

    Returns
    -------
    pl.DataFrame
        report parquet 의 investedCompany apiType 행 (stockCode/year/inv_prm/
        invstmnt_purps/trmend_blce_qota_rt/trmend_blce_acntbk_amount/trmend_blce_qy).

    Raises
    ------
    polars.PolarsError
        report parquet 손상 또는 schema 불일치 시.

    Examples
    --------
    >>> from dartlab.scan.network.scanner import scanInvested
    >>> df = scanInvested()
    >>> df.height > 0
    True
    """
    return _scanParquets(
        "investedCompany",
        [
            "stockCode",
            "year",
            "inv_prm",
            "invstmnt_purps",
            "trmend_blce_qota_rt",
            "trmend_blce_acntbk_amount",
            "trmend_blce_qy",
        ],
    )


def scanMajorHolders() -> pl.DataFrame:
    """전종목 majorHolder 스캔.

    Returns
    -------
    pl.DataFrame
        report parquet 의 majorHolder apiType 행 (stockCode/year/nm/relate/
        trmend_posesn_stock_co/trmend_posesn_stock_qota_rt).

    Raises
    ------
    polars.PolarsError
        report parquet 손상 또는 schema 불일치 시.

    Examples
    --------
    >>> from dartlab.scan.network.scanner import scanMajorHolders
    >>> df = scanMajorHolders()
    >>> df.height > 0
    True
    """
    return _scanParquets(
        "majorHolder",
        [
            "stockCode",
            "year",
            "nm",
            "relate",
            "trmend_posesn_stock_co",
            "trmend_posesn_stock_qota_rt",
        ],
    )


# ── docs 계열회사 ground truth ─────────────────────────────


class UnionFind:
    """서로소 집합 자료구조 — 경로 압축 + 랭크 기반 합침.

    계열회사 그룹핑에 사용. find/union/components 3개 연산 제공.
    """

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.rank: dict[str, int] = {}

    def find(self, x: str) -> str:
        """루트 노드 탐색 (경로 압축 적용).

        Parameters
        ----------
        x : str
            대상 노드.

        Returns
        -------
        str
            루트 노드.

        Raises
        ------
        없음.

        Examples
        --------
        >>> uf = UnionFind()
        >>> uf.find("A")
        'A'
        """
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        """두 노드를 같은 집합으로 병합.

        Parameters
        ----------
        a, b : str
            병합할 노드 쌍.

        Returns
        -------
        None — 내부 상태 변경.

        Raises
        ------
        없음.

        Examples
        --------
        >>> uf = UnionFind()
        >>> uf.union("A", "B")
        """
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1

    def components(self) -> dict[str, list[str]]:
        """연결 요소별 노드 목록 반환.

        Returns
        -------
        dict[str, list[str]]
            루트 노드 → 자식 노드 list.

        Raises
        ------
        없음.

        Examples
        --------
        >>> uf = UnionFind()
        >>> uf.union("A", "B")
        >>> uf.components()
        {'A': ['A', 'B']}
        """
        groups: dict[str, list[str]] = defaultdict(list)
        for x in self.parent:
            groups[self.find(x)].append(x)
        return dict(groups)


def scanAffiliateDocs(
    nameToCode: dict[str, str],
    codeToName: dict[str, str],
) -> dict[str, str]:
    """docs parquet의 '계열회사 현황'에서 ground truth 그룹 매핑 추출.

    Parameters
    ----------
    nameToCode : dict[str, str]
        회사명 → 종목코드 매핑.
    codeToName : dict[str, str]
        종목코드 → 회사명 매핑.

    Returns
    -------
    dict[str, str]
        종목코드 → 그룹명 매핑 (계열회사 표 ground truth 기반).

    Raises
    ------
    polars.PolarsError
        docs parquet 손상 또는 schema 불일치 시.

    Examples
    --------
    >>> from dartlab.scan.network.scanner import loadListing, scanAffiliateDocs
    >>> n2c, c2n, _, _ = loadListing()
    >>> gt = scanAffiliateDocs(n2c, c2n)
    >>> gt.get("005930")
    """
    from dartlab.core.dataLoader import _dataDir

    docs_dir = Path(_dataDir("docs"))
    parquet_files = sorted(docs_dir.glob("*.parquet"))

    _TABLE_NOISE = {
        "상장",
        "비상장",
        "합계",
        "소계",
        "---",
        "기업명",
        "회사수",
        "법인등록번호",
        "상장여부",
        "비고",
        "단위",
        "기준일",
        "☞",
        "본문",
    }

    def _extractCompanies(text: str) -> list[str]:
        companies: list[str] = []
        for line in text.split("\n"):
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if not any(_SCAN_REGNUM_RE.search(c) for c in cells):
                continue
            for cell in cells:
                if _SCAN_REGNUM_RE.search(cell):
                    continue
                if re.match(r"^[\d,.\-\s]+$", cell):
                    continue
                if cell in _TABLE_NOISE or len(cell) < 2:
                    continue
                companies.append(cell)
        if not companies:
            for line in text.split("\n"):
                if "|" not in line:
                    continue
                cells = [c.strip() for c in line.split("|") if c.strip()]
                for cell in cells:
                    if _SCAN_CORP_RE.search(cell) and len(cell) >= 3:
                        if not re.match(r"^[\d,.\-\s]+$", cell):
                            companies.append(cell)
        return companies

    def _normalizeCorp(name: str) -> str:
        name = re.sub(r"[\(（]주[\)）]", "", name)
        return name.replace("㈜", "").replace("주식회사", "").strip()

    code_to_affiliate_set: dict[str, set[str]] = {}
    for pf in parquet_files:
        code = pf.stem
        try:
            affiliate = (
                pl.scan_parquet(str(pf))
                .filter(
                    pl.col("section_title").str.contains("계열회사 현황")
                    | pl.col("section_title").str.contains("계열회사에 관한 사항")
                )
                .collect(engine="streaming")
            )
        except (pl.exceptions.PolarsError, OSError):
            continue
        if len(affiliate) == 0:
            continue
        if "year" in affiliate.columns:
            affiliate = affiliate.filter(pl.col("year") == affiliate["year"].max())
        full_text = "\n".join(c for c in affiliate["section_content"].to_list() if c)
        if not full_text:
            continue
        companies = _extractCompanies(full_text)
        matched: set[str] = {code}
        for comp in companies:
            norm = _normalizeCorp(comp)
            c = nameToCode.get(comp) or nameToCode.get(norm)
            if c:
                matched.add(c)
        code_to_affiliate_set[code] = matched

    # Union-Find 클러스터링 (상장사 3개+ 겹침)
    uf = UnionFind()
    codes_list = list(code_to_affiliate_set.keys())
    for i in range(len(codes_list)):
        for j in range(i + 1, len(codes_list)):
            ci, cj = codes_list[i], codes_list[j]
            if len(code_to_affiliate_set[ci] & code_to_affiliate_set[cj]) >= 3:
                uf.union(ci, cj)

    _GROUP_ALIASES = {
        "에스케이": "SK",
        "엘지": "LG",
        "지에스": "GS",
        "씨제이": "CJ",
        "에이치디현대": "HD현대",
        "케이씨씨": "KCC",
    }
    _WELL_KNOWN_LABELS = {
        "005930": "삼성",
        "006400": "삼성",
        "032830": "삼성",
        "005380": "현대차",
        "000270": "현대차",
        "012330": "현대차",
        "034730": "SK",
        "000660": "SK",
        "017670": "SK",
        "003550": "LG",
        "066570": "LG",
        "051910": "LG",
        "023530": "롯데",
        "004990": "롯데",
        "000880": "한화",
        "009830": "한화",
        "078930": "GS",
        "006360": "GS",
        "005490": "포스코",
        "047050": "포스코",
        "001040": "CJ",
        "097950": "CJ",
        "000150": "두산",
        "042670": "두산",
        "329180": "HD현대",
        "267250": "HD현대",
        "035720": "카카오",
        "293490": "카카오",
        "035420": "네이버",
        "004800": "효성",
        "298040": "효성",
        "004150": "한솔",
        "213500": "한솔",
        "003490": "대한항공",
        "180640": "한진칼",
        "069960": "현대백화점",
        "005440": "현대백화점",
        "010120": "LS",
        "006260": "LS",
        "105560": "KB",
        "055550": "신한",
        "086790": "하나",
        "138930": "BNK",
        "316140": "우리",
    }

    codeToGroup: dict[str, str] = {}
    for _root, members in uf.components().items():
        all_affiliates: set[str] = set()
        for m in members:
            all_affiliates.update(code_to_affiliate_set.get(m, set()))
        if len(all_affiliates) < 2:
            continue

        group_name = None
        for c in all_affiliates:
            if c in _WELL_KNOWN_LABELS:
                group_name = _WELL_KNOWN_LABELS[c]
                break
        if not group_name:
            names = sorted(codeToName.get(c, "") for c in all_affiliates if c in codeToName)
            if len(names) >= 2:
                prefix = names[0]
                for n in names[1:]:
                    while prefix and not n.startswith(prefix):
                        prefix = prefix[:-1]
                if len(prefix) >= 2:
                    group_name = prefix.rstrip()
            if not group_name:
                group_name = codeToName.get(members[0], members[0])

        for c in all_affiliates:
            codeToGroup[c] = group_name

    return codeToGroup
