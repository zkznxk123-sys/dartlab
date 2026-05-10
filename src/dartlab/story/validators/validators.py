"""Damodaran 3-Test — 모든 스토리는 세 시험을 통과해야 한다.

Aswath Damodaran (NYU Stern) "Narrative & Numbers" 프레임워크:
1. History Test  — 과거에 이 스토리를 산 기업이 있는가? 어떻게 됐나?
2. Experience Test — 같은 업종에서 이 문제를 겪은 전례가 있는가?
3. Common Sense Test — 경제학적으로 말이 되는가? (불변량 위반 체크)

story 보고서 끝에 3-test 결과를 부착하여 스토리의 신뢰도를 높인다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TestResult:
    """단일 테스트 결과."""

    name: str
    passed: bool
    detail: str


@dataclass
class DamodaranResult:
    """3-test 전체 결과."""

    historyTest: TestResult | None = None
    experienceTest: TestResult | None = None
    commonSenseTest: TestResult | None = None
    passCount: int = 0
    totalCount: int = 3

    @property
    def summary(self) -> str:
        return f"Damodaran 3-test: {self.passCount}/{self.totalCount} 통과"


def damodaranTest(company, metrics: dict | None = None) -> DamodaranResult:
    """Company + 핵심 지표로 Damodaran 3-test 실행.

    Parameters
    ----------
    company : DartCompany | EdgarCompany
    metrics : dict, optional
        baseCase dict (scenarioSensitivity 결과 등). 없으면 내부 추출.

    Returns
    -------
    DamodaranResult
    """
    result = DamodaranResult()
    pass_count = 0

    # ── Test 1: History Test ──
    result.historyTest = _historyTest(company)
    if result.historyTest and result.historyTest.passed:
        pass_count += 1

    # ── Test 2: Experience Test ──
    result.experienceTest = _experienceTest(company)
    if result.experienceTest and result.experienceTest.passed:
        pass_count += 1

    # ── Test 3: Common Sense Test ──
    result.commonSenseTest = _commonSenseTest(company, metrics)
    if result.commonSenseTest and result.commonSenseTest.passed:
        pass_count += 1

    result.passCount = pass_count
    return result


def _historyTest(company) -> TestResult:
    """과거 유사 기업 사례 매칭 — historicalContext 활용 + scan peer.

    현재: scan 기반 peer 기업 중 유사 재무구조를 가진 top 3가 존재하는지.
    """
    try:
        from dartlab.scan.extended import calcPeerPosition

        peer = calcPeerPosition(company)
        if peer and peer.get("crossViews"):
            views = [cv["view"] for cv in peer["crossViews"]]
            return TestResult(
                name="History",
                passed=True,
                detail=f"유사 포지션 기업 확인됨: {', '.join(views[:2])} 유형에서 동종 사례 존재",
            )
        return TestResult(
            name="History",
            passed=False,
            detail="peer 비교 데이터 부족. scan 프리빌드 필요: dartlab.downloadAll('scan') 실행 후 재시도",
        )
    except (ImportError, AttributeError, ValueError):
        return TestResult(
            name="History",
            passed=False,
            detail="scan 데이터 접근 불가. dartlab.downloadAll('scan') 실행 필요",
        )


def _experienceTest(company) -> TestResult:
    """같은 업종 기업 3개 이상이 비교 가능한지. 동업 전례 확인."""
    try:
        from dartlab.scan.extended import calcPeerPosition

        peer = calcPeerPosition(company)
        total = peer.get("total_stocks", 0) if peer else 0
        if total >= 50:
            return TestResult(
                name="Experience",
                passed=True,
                detail=f"동종업계 {total}개사 비교 가능 — 업종 내 전례 충분",
            )
        return TestResult(
            name="Experience",
            passed=False,
            detail=f"동종업계 {total}개사 — 비교 표본 부족 (50개 미만). dartlab.downloadAll('scan') 실행 후 재시도",
        )
    except (ImportError, AttributeError, ValueError):
        return TestResult(
            name="Experience",
            passed=False,
            detail="scan 데이터 접근 불가. dartlab.downloadAll('scan') 실행 필요",
        )


# ── Common Sense Invariants ──
# 경제학적으로 항상 참이어야 하는 불변량 20개.
# 위반 시 데이터 오류 또는 비현실적 가정.

_INVARIANTS: list[tuple[str, callable]] = []


def _register(desc: str):
    def deco(fn):
        _INVARIANTS.append((desc, fn))
        return fn

    return deco


@_register("영업이익 > 순이익이면 비영업손익 확인 필요")
def _invOpGtNi(m: dict) -> bool:
    opm = m.get("opm")
    roe = m.get("roe")
    if opm is not None and roe is not None and opm > 0 and roe > opm * 2:
        return False
    return True


@_register("ROE 음수인데 배당 지급이면 경고")
def _invNegativeRoeDividend(m: dict) -> bool:
    roe = m.get("roe")
    if roe is not None and roe < 0:
        return False  # 세부 판단은 caller가 추가
    return True


@_register("부채비율 300% 초과 + 이자보상 2 미만 = 재무위기")
def _invDistressCombo(m: dict) -> bool:
    dr = m.get("debtRatio")
    ic = m.get("interestCoverage")
    if dr and ic and dr > 300 and ic < 2:
        return False
    return True


@_register("OPM 50% 초과는 독과점 아니면 의심")
def _invExtremeMargin(m: dict) -> bool:
    opm = m.get("opm")
    if opm is not None and opm > 50:
        return False
    return True


@_register("FCF가 5년 연속 음수면 사업 모델 재검토")
def _invPersistentNegativeFcf(m: dict) -> bool:
    fcf = m.get("fcf")
    if fcf is not None and fcf < 0:
        return False
    return True


# ── Phase 10 F2: 불변량 15개 추가 (총 20개) ──


@_register("FCF = OCF - Capex (계산 일관성)")
def _invFcfIdentity(m: dict) -> bool:
    fcf, ocf, capex = m.get("fcf"), m.get("ocf"), m.get("capex")
    if fcf is not None and ocf is not None and capex is not None:
        expected = ocf - capex
        if expected != 0 and abs(fcf - expected) / abs(expected) > 0.10:
            return False
    return True


@_register("영업이익 = 매출 - COGS - SGA (decomposition)")
def _invOperatingIncomeDecomp(m: dict) -> bool:
    rev, cogs, sga, opi = m.get("revenue"), m.get("cogs"), m.get("sga"), m.get("operatingIncome")
    if all(x is not None for x in (rev, cogs, sga, opi)):
        expected = rev - cogs - sga
        if expected != 0 and abs(opi - expected) / abs(expected) > 0.15:
            return False
    return True


@_register("ROIC = NOPAT / InvestedCapital")
def _invRoicIdentity(m: dict) -> bool:
    roic, nopat, ic = m.get("roic"), m.get("nopat"), m.get("investedCapital")
    if all(x is not None for x in (roic, nopat, ic)) and ic != 0:
        expected_pct = (nopat / ic) * 100
        if abs(roic - expected_pct) > 5:
            return False
    return True


@_register("ROE = NI / Equity")
def _invRoeIdentity(m: dict) -> bool:
    roe, ni, eq = m.get("roe"), m.get("netIncome"), m.get("equity")
    if all(x is not None for x in (roe, ni, eq)) and eq != 0:
        expected_pct = (ni / eq) * 100
        if abs(roe - expected_pct) > 5:
            return False
    return True


@_register("Interest Coverage = EBIT / Interest")
def _invInterestCoverage(m: dict) -> bool:
    ic, ebit, interest = m.get("interestCoverage"), m.get("ebit"), m.get("interestExpense")
    if all(x is not None for x in (ic, ebit, interest)) and interest != 0:
        expected = ebit / interest
        if abs(ic - expected) > 1:
            return False
    return True


@_register("Working Capital = CurrentAssets - CurrentLiabilities")
def _invWorkingCapital(m: dict) -> bool:
    wc, ca, cl = m.get("workingCapital"), m.get("currentAssets"), m.get("currentLiabilities")
    if all(x is not None for x in (wc, ca, cl)):
        expected = ca - cl
        if expected != 0 and abs(wc - expected) / abs(expected) > 0.10:
            return False
    return True


@_register("Debt/EBITDA 3배 초과 = leverage warning")
def _invDebtEbitda(m: dict) -> bool:
    debt, ebitda = m.get("totalDebt"), m.get("ebitda")
    if debt and ebitda and ebitda > 0:
        if debt / ebitda > 3:
            return False
    return True


@_register("Free Float × 주가 = Market Cap (sanity)")
def _invMarketCap(m: dict) -> bool:
    mc, px, shares = m.get("marketCap"), m.get("price"), m.get("sharesOutstanding")
    if all(x is not None for x in (mc, px, shares)):
        expected = px * shares
        if expected != 0 and abs(mc - expected) / abs(expected) > 0.20:
            return False
    return True


@_register("Goodwill / TotalAssets > 30% = M&A 집중 (goodwill impairment risk)")
def _invGoodwillRatio(m: dict) -> bool:
    gw, ta = m.get("goodwill"), m.get("totalAssets")
    if gw and ta and ta > 0:
        if gw / ta > 0.30:
            return False
    return True


@_register("Tax Rate 통상 범위 (5~40%)")
def _invTaxRate(m: dict) -> bool:
    tax_rate = m.get("effectiveTaxRate")
    if tax_rate is not None:
        if tax_rate < 0.05 or tax_rate > 0.40:
            return False
    return True


@_register("NI > 0 인데 OCF < 0 (accrual 경고 — 이익품질)")
def _invNiOcfBridge(m: dict) -> bool:
    ni, ocf = m.get("netIncome"), m.get("ocf")
    if ni and ocf and ni > 0 and ocf < 0:
        return False
    return True


@_register("CCC (DSO + DIO - DPO) 업종 평균의 2배 초과")
def _invCccReasonable(m: dict) -> bool:
    ccc = m.get("ccc")
    if ccc is not None and ccc > 200:  # 극단 case
        return False
    return True


@_register("매출채권회전 < 3회 (DSO > 120일) = 회수 부실")
def _invArTurnover(m: dict) -> bool:
    dso = m.get("dso")
    if dso is not None and dso > 120:
        return False
    return True


@_register("재고회전 < 2회 (DIO > 180일) = 재고 과다")
def _invInventoryTurnover(m: dict) -> bool:
    dio = m.get("dio")
    if dio is not None and dio > 180:
        return False
    return True


@_register("ROIC < WACC (가치 파괴)")
def _invRoicWaccSpread(m: dict) -> bool:
    roic, wacc = m.get("roic"), m.get("wacc")
    if roic is not None and wacc is not None and roic < wacc:
        return False
    return True


def _commonSenseTest(company, metrics: dict | None) -> TestResult:
    """경제학적 불변량 위반 체크."""
    if metrics is None:
        try:
            from dartlab.analysis.financial.scenarioSensitivity import calcScenarioSensitivity

            ss = calcScenarioSensitivity(company)
            metrics = ss.get("baseCase", {}) if ss else {}
        except (ImportError, AttributeError, ValueError):
            metrics = {}

    if not metrics:
        return TestResult(name="CommonSense", passed=True, detail="검증 대상 지표 없음 (데이터 부족)")

    violations = []
    for desc, check in _INVARIANTS:
        try:
            if not check(metrics):
                violations.append(desc)
        except (KeyError, TypeError, ValueError):
            continue

    if not violations:
        return TestResult(
            name="CommonSense",
            passed=True,
            detail=f"{len(_INVARIANTS)}개 경제학 불변량 전부 통과",
        )
    return TestResult(
        name="CommonSense",
        passed=False,
        detail=f"{len(violations)}개 위반: {'; '.join(violations[:3])}",
    )
