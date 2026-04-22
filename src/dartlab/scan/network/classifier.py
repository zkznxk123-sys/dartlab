"""5단계 균형 분류 파이프라인 — docs lock → well-known → 경영참여 → 법인주주 → 공유주주 → 키워드."""

from __future__ import annotations

from collections import Counter, defaultdict

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

# ── seed 상수 ─────────────────────────────────────────────

# well-known base seed (007 기반)
_WELL_KNOWN: dict[str, str] = {
    "005930": "삼성",
    "006400": "삼성",
    "009150": "삼성",
    "028260": "삼성",
    "032830": "삼성",
    "018260": "삼성",
    "000810": "삼성",
    "029780": "삼성",
    "016360": "삼성",
    "207940": "삼성",
    "030000": "삼성",
    "068290": "삼성",
    "010140": "삼성",
    "005380": "현대차",
    "000270": "현대차",
    "012330": "현대차",
    "005387": "현대차",
    "004020": "현대차",
    "079160": "현대차",
    "307950": "현대차",
    "267260": "현대차",
    "064350": "현대차",
    "329180": "HD현대",
    "267250": "HD현대",
    "009540": "HD현대",
    "034730": "SK",
    "017670": "SK",
    "000660": "SK",
    "361610": "SK",
    "018670": "SK",
    "034020": "SK",
    "003550": "LG",
    "066570": "LG",
    "051910": "LG",
    "034220": "LG",
    "373220": "LG",
    "011070": "LG",
    "011170": "LG",
    "023530": "롯데",
    "004990": "롯데",
    "071050": "롯데",
    "004000": "롯데",
    "023150": "롯데",
    "004440": "롯데",
    "000880": "한화",
    "009830": "한화",
    "272210": "한화",
    "042660": "한화",
    "012450": "한화",
    "078930": "GS",
    "006360": "GS",
    "001120": "GS",
    "005490": "포스코",
    "047050": "포스코",
    "003670": "포스코",
    "001040": "CJ",
    "097950": "CJ",
    "000120": "CJ",
    "000150": "두산",
    "336260": "두산",
    "042670": "두산",
    "035720": "카카오",
    "293490": "카카오",
    "377300": "카카오",
    "035420": "네이버",
    "004800": "효성",
    "298040": "효성",
    "298050": "효성",
    "298020": "효성",
    "004150": "한솔",
    "213500": "한솔",
    "009180": "한솔",
    "007160": "사조",
    "008060": "사조",
    "006280": "녹십자",
    "005250": "녹십자",
    "136480": "하림",
    "003380": "하림",
    "105560": "KB",
    "055550": "신한",
    "086790": "하나",
    "138930": "BNK",
    "316140": "우리",
    "010950": "S-Oil",
    "180640": "한진칼",
    "003490": "대한항공",
    "004170": "신세계",
    "139480": "신세계",
}

# well-known 확대판 (012 기반)
WELL_KNOWN_EXT: dict[str, str] = {
    **_WELL_KNOWN,
    "001450": "현대차",
    "086280": "현대차",
    "004560": "현대차",
    "011210": "현대차",
    "000720": "현대차",
    "214320": "현대차",
    "001500": "현대차",
    "088350": "한화",
    "272450": "대한항공",
    "020560": "대한항공",
    "005430": "대한항공",
    "002320": "대한항공",
    "267850": "대한항공",
    "298690": "대한항공",
    "069960": "현대백화점",
    "005440": "현대백화점",
    "057050": "현대백화점",
    "079430": "현대백화점",
    "020000": "현대백화점",
    "030200": "KT",
    "161390": "한국타이어",
    "001630": "종근당",
    "185750": "종근당",
    "063160": "종근당",
    "023590": "다우",
    "175250": "다우",
    "016880": "웅진",
    "095720": "웅진",
    "006260": "LS",
    "010120": "LS",
    "086520": "에코프로",
    "247540": "에코프로",
    "383310": "에코프로",
    "068270": "셀트리온",
    "091990": "셀트리온",
    "393890": "셀트리온",
    "028300": "HLB",
    "024850": "HLB",
    "067630": "HLB",
}

# 이름 키워드 → 그룹 매칭
GROUP_KEYWORDS: dict[str, list[str]] = {
    "삼성": ["삼성"],
    "현대차": ["현대", "기아"],
    "SK": ["SK", "에스케이"],
    "LG": ["LG", "엘지"],
    "롯데": ["롯데"],
    "한화": ["한화"],
    "GS": ["GS", "지에스"],
    "포스코": ["POSCO", "포스코"],
    "CJ": ["CJ", "씨제이"],
    "두산": ["두산"],
    "HD현대": ["HD현대", "한국조선해양"],
    "효성": ["효성"],
    "한솔": ["한솔"],
    "카카오": ["카카오"],
    "네이버": ["네이버", "NAVER"],
    "현대백화점": ["현대백화점"],
    "KT": ["케이티", "KT"],
    "LS": ["LS"],
    "에코프로": ["에코프로"],
    "셀트리온": ["셀트리온"],
    "HLB": ["HLB"],
    "종근당": ["종근당"],
    "웅진": ["웅진"],
}


# ── 분류 로직 ─────────────────────────────────────────────


def _label_group(members: list[str], code_to_name: dict[str, str]) -> str:
    """컴포넌트 멤버 종목코드 리스트에서 대표 그룹 라벨을 결정한다.

    well-known 매핑 → 공통 접두사 → 첫 번째 종목명 순으로 fallback.

    Parameters
    ----------
    members : list[str]
        그룹에 속한 종목코드 리스트.
    code_to_name : dict[str, str]
        종목코드 → 회사명 매핑.

    Returns
    -------
    str
        그룹 라벨 (예: "삼성", "현대차", 또는 회사명).
    """
    for m in members:
        if m in _WELL_KNOWN:
            return _WELL_KNOWN[m]
    names = [code_to_name.get(m, "") for m in members]
    if len(names) >= 2:
        prefix = names[0]
        for n in names[1:]:
            while prefix and not n.startswith(prefix):
                prefix = prefix[:-1]
            if not prefix:
                break
        if len(prefix) >= 2:
            return prefix.rstrip()
    return code_to_name.get(members[0], members[0])


def _cbPhase0Docs(
    docs_ground_truth: dict[str, str],
    all_node_ids: set[str],
    code_to_group: dict[str, str],
    locked: set[str],
) -> int:
    """Phase 0: docs ground truth lock. 반환: 이번 Phase 에서 lock 된 종목 수."""
    before = len(locked)
    for code, group in docs_ground_truth.items():
        if code in all_node_ids:
            code_to_group[code] = group
            locked.add(code)
    return len(locked) - before


def _cbPhase1WellKnown(
    all_node_ids: set[str],
    code_to_group: dict[str, str],
    locked: set[str],
) -> int:
    """Phase 1: WELL_KNOWN_EXT lock. 반환: 새로 lock 된 수."""
    before = len(locked)
    for code, group in WELL_KNOWN_EXT.items():
        if code in all_node_ids and code not in locked:
            code_to_group[code] = group
            locked.add(code)
    return len(locked) - before


def _cbKnownGroupNames(locked: set[str], code_to_group: dict[str, str]) -> set[str]:
    """locked 에서 2명+ 멤버 보유한 그룹 이름 set."""
    known_groups: dict[str, set[str]] = defaultdict(set)
    for code in locked:
        known_groups[code_to_group[code]].add(code)
    return {g for g, members in known_groups.items() if len(members) >= 2}


def _cbBuildMgmtDirected(invest_edges: pl.DataFrame, all_node_ids: set[str]) -> dict[str, set[str]]:
    """경영참여 엣지 → {from: {to, ...}} directed map."""
    mgmt = invest_edges.filter(
        (pl.col("purpose") == "경영참여") & pl.col("is_listed") & pl.col("to_code").is_not_null()
    )
    mgmt_directed: dict[str, set[str]] = defaultdict(set)
    for row in mgmt.iter_rows(named=True):
        a, b = row["from_code"], row["to_code"]
        if a != b and a in all_node_ids and b in all_node_ids:
            mgmt_directed[a].add(b)
    return mgmt_directed


def _cbPhase2Propagate(
    mgmt_directed: dict[str, set[str]],
    code_to_group: dict[str, str],
    locked: set[str],
    known_group_names: set[str],
) -> None:
    """Phase 2a: 방향성 전파 (unknown 그룹 자녀 → 부모 그룹, 3회 반복)."""
    for _round in range(3):
        newly = 0
        for parent in list(code_to_group.keys()):
            pg = code_to_group[parent]
            if pg in known_group_names:
                continue
            for child in mgmt_directed.get(parent, set()):
                if child in locked or child in code_to_group:
                    continue
                code_to_group[child] = pg
                newly += 1
        if newly == 0:
            break


def _cbPhase2Cluster(
    mgmt_directed: dict[str, set[str]],
    code_to_group: dict[str, str],
    locked: set[str],
    known_group_names: set[str],
    code_to_name: dict[str, str],
) -> None:
    """Phase 2b: 미분류 경영참여 클러스터 → _label_group 적용."""
    parent_children: dict[str, set[str]] = defaultdict(set)
    for parent, children in mgmt_directed.items():
        if parent not in code_to_group:
            for child in children:
                if child not in code_to_group:
                    parent_children[parent].add(child)

    for parent in list(code_to_group.keys()):
        if code_to_group[parent] not in known_group_names:
            continue
        uc = [c for c in mgmt_directed.get(parent, set()) if c not in code_to_group and c not in locked]
        if len(uc) < 2:
            continue
        for u in uc:
            if u not in parent_children:
                parent_children[u] = set()
            for u2 in uc:
                if u != u2 and u2 in mgmt_directed.get(u, set()):
                    parent_children[u].add(u2)

    for parent, children in parent_children.items():
        cluster = {parent} | children
        if len(cluster) >= 2:
            label = _label_group(list(cluster), code_to_name)
            for m in cluster:
                if m not in code_to_group:
                    code_to_group[m] = label


def _cbPhase3Corp(
    corp_edges: pl.DataFrame,
    all_node_ids: set[str],
    code_to_group: dict[str, str],
    locked: set[str],
    known_group_names: set[str],
) -> int:
    """Phase 3: majorHolder 법인주주 (known 20%+). 반환: 새 배정 수."""
    matched_corp = corp_edges.filter(pl.col("from_code").is_not_null())
    count = 0
    for row in matched_corp.iter_rows(named=True):
        fc, tc = row["from_code"], row["to_code"]
        pct = row.get("ownership_pct") or 0
        if fc in code_to_group and tc not in code_to_group and tc in all_node_ids and tc not in locked:
            pg = code_to_group[fc]
            if pg in known_group_names and pct < 20:
                continue
            code_to_group[tc] = pg
            count += 1
        elif tc in code_to_group and fc not in code_to_group and fc in all_node_ids and fc not in locked:
            pg = code_to_group[tc]
            if pg in known_group_names and pct < 20:
                continue
            code_to_group[fc] = pg
            count += 1
    return count


def _cbPhase4PersonShares(
    person_edges: pl.DataFrame,
    all_node_ids: set[str],
    code_to_group: dict[str, str],
    locked: set[str],
) -> int:
    """Phase 4: 공유 개인주주. 반환: 새 배정 수."""
    person_groups = (
        person_edges.group_by("person_name")
        .agg(pl.col("to_code").unique().alias("companies"))
        .filter(pl.col("companies").list.len() >= 2)
    )
    count = 0
    for row in person_groups.iter_rows(named=True):
        codes = [c for c in row["companies"] if c in all_node_ids and c not in locked]
        if len(codes) < 2:
            continue
        group_dist: dict[str, list[str]] = defaultdict(list)
        unassigned: list[str] = []
        for c in codes:
            if c in code_to_group:
                group_dist[code_to_group[c]].append(c)
            else:
                unassigned.append(c)
        if not group_dist or not unassigned:
            continue
        best = max(group_dist, key=lambda g: len(group_dist[g]))
        if len(group_dist[best]) >= 2:
            for c in unassigned:
                code_to_group[c] = best
                count += 1
    return count


def _cbPhase5KeywordAndIndep(
    all_node_ids: set[str],
    code_to_group: dict[str, str],
    code_to_name: dict[str, str],
) -> tuple[int, set[str]]:
    """Phase 5: 키워드 + 나머지 독립. 반환: (키워드 배정 수, 최종 독립 set)."""
    kw_count = 0
    for node in list(all_node_ids - set(code_to_group.keys())):
        name = code_to_name.get(node, "")
        for group, keywords in GROUP_KEYWORDS.items():
            if any(kw in name for kw in keywords):
                code_to_group[node] = group
                kw_count += 1
                break
    still = all_node_ids - set(code_to_group.keys())
    for node in still:
        code_to_group[node] = code_to_name.get(node, node)
    return kw_count, still


def classify_balanced(
    invest_edges: pl.DataFrame,
    corp_edges: pl.DataFrame,
    person_edges: pl.DataFrame,
    all_node_ids: set[str],
    code_to_name: dict[str, str],
    docs_ground_truth: dict[str, str],
    *,
    verbose: bool = True,
) -> dict[str, str]:
    """5단계 균형 분류 orchestrator — 상장사를 그룹(재벌/독립)으로 배정.

    Phase 0: docs ground truth lock
    Phase 1: well-known ext lock
    Phase 2: 경영참여 방향 확장 (propagate + cluster)
    Phase 3: majorHolder 법인주주
    Phase 4: 공유 개인주주
    Phase 5: 이름 키워드 + 나머지 독립

    Parameters
    ----------
    invest_edges : pl.DataFrame
        investedCompany 정제 엣지 (build_invest_edges 결과).
    corp_edges : pl.DataFrame
        majorHolder 중 법인 엣지 (build_holder_edges 결과의 첫 번째).
    person_edges : pl.DataFrame
        majorHolder 중 개인 엣지 (build_holder_edges 결과의 두 번째).
    all_node_ids : set[str]
        분류 대상 전체 종목코드 집합.
    code_to_name : dict[str, str]
        종목코드 → 회사명 매핑.
    docs_ground_truth : dict[str, str]
        공시 기반 확정 그룹 매핑 {종목코드: 그룹명}.
    verbose : bool
        True이면 각 Phase 진행 로그를 출력한다.

    Returns
    -------
    dict[str, str]
        종목코드 → 그룹명 매핑. all_node_ids 전체를 커버한다.
        그룹에 1개만 속하면 독립 기업(회사명이 그룹명).
    """
    code_to_group: dict[str, str] = {}
    locked: set[str] = set()

    def _log(msg: str) -> None:
        if verbose:
            _log.info(msg)

    phase0 = _cbPhase0Docs(docs_ground_truth, all_node_ids, code_to_group, locked)
    phase1 = _cbPhase1WellKnown(all_node_ids, code_to_group, locked)
    _log(f"  Phase 0+1 (docs+well-known lock): {len(locked)} ({phase0} docs + {phase1} well-known)")

    known_group_names = _cbKnownGroupNames(locked, code_to_group)
    _log(f"  known 그룹: {len(known_group_names)}개")

    mgmt_directed = _cbBuildMgmtDirected(invest_edges, all_node_ids)
    _cbPhase2Propagate(mgmt_directed, code_to_group, locked, known_group_names)
    _cbPhase2Cluster(mgmt_directed, code_to_group, locked, known_group_names, code_to_name)
    phase2 = len(code_to_group) - len(locked)
    _log(f"  Phase 2 (경영참여 확장): +{phase2}")

    phase3 = _cbPhase3Corp(corp_edges, all_node_ids, code_to_group, locked, known_group_names)
    _log(f"  Phase 3 (법인주주): +{phase3}")

    phase4 = _cbPhase4PersonShares(person_edges, all_node_ids, code_to_group, locked)
    _log(f"  Phase 4 (공유주주): +{phase4}")

    kw_count, still = _cbPhase5KeywordAndIndep(all_node_ids, code_to_group, code_to_name)
    group_counts = Counter(code_to_group[n] for n in all_node_ids)
    real_indep = sum(1 for c in group_counts.values() if c == 1)
    _log(f"  Phase 5 (키워드): +{kw_count}, 독립: {len(still)}")
    _log(f"  최종: {len(all_node_ids)} nodes, 독립 {real_indep} ({real_indep / len(all_node_ids):.0%})")

    return code_to_group
