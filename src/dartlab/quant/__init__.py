"""종목 레벨 정량분석 엔진 — 31축 7그룹.

기술적 지표부터 팩터 모델, 텍스트 감성, 포트폴리오 최적화까지.
dartlab.quant("축명", "종목코드") 로 접근.

Usage::

    import dartlab

    dartlab.quant()                                # 가이드 (축 카탈로그)
    dartlab.quant("모멘텀", "005930")              # 모멘텀 분석
    dartlab.quant("momentum", "005930")            # 영문 키
    dartlab.quant("팩터", "AAPL")                  # EDGAR 종목
    dartlab.quant("순위")                          # 횡단면 (종목 불필요)
    dartlab.quant("평균분산", ["005930","000660"])  # 포트폴리오
    dartlab.quant.momentum("005930")               # 속성 접근자
"""

from __future__ import annotations

import importlib
import re
import warnings
from dataclasses import dataclass
from typing import Any

import polars as pl

from dartlab.quant.analyzer import enrichWithIndicators, technicalVerdict

__all__ = ["Quant", "enrichWithIndicators", "technicalVerdict"]


# ── Axis Registry ────────────────────────────────────────


@dataclass(frozen=True)
class _AxisEntry:
    """quant 축 메타데이터."""

    module: str
    fn: str
    label: str
    description: str
    example: str
    group: str
    stockRequired: bool = True  # False = 횡단면/시장 레벨
    multiStock: bool = False  # True = 종목 리스트 입력


# ── A: 기술적 (technical) — 가격 전용 ────────────────────

_AXIS_REGISTRY: dict[str, _AxisEntry] = {
    "indicators": _AxisEntry(
        module="dartlab.quant._ax_technical",
        fn="calcIndicators",
        label="지표",
        description="45개 기술적 지표 DataFrame (SMA, EMA, MACD, RSI, BB 등)",
        example='quant("지표", "005930")',
        group="technical",
    ),
    "signals": _AxisEntry(
        module="dartlab.quant._ax_technical",
        fn="calcSignals",
        label="신호",
        description="최근 매매 신호 이벤트 (골든크로스, RSI, MACD, 볼린저)",
        example='quant("신호", "005930")',
        group="technical",
    ),
    "verdict": _AxisEntry(
        module="dartlab.quant._ax_technical",
        fn="calcVerdict",
        label="판단",
        description="종합 기술적 판단 (강세/중립/약세) + RSI/SMA/BB",
        example='quant("판단", "005930")',
        group="technical",
    ),
    "momentum": _AxisEntry(
        module="dartlab.quant.momentum",
        fn="calcMomentum",
        label="모멘텀",
        description="12-1개월 횡단면, 시계열 모멘텀, 52주 신고가 비율",
        example='quant("모멘텀", "005930")',
        group="technical",
    ),
    "volatility": _AxisEntry(
        module="dartlab.quant.volatility",
        fn="calcVolatility",
        label="변동성",
        description="GARCH(1,1), HAR-RV 실현변동성, 변동성 기간구조 (forecast=True 면 horizon 일 후 변동성 + 분산 예측 추가)",
        example='quant("변동성", "005930")',
        group="technical",
    ),
    "forecast": _AxisEntry(
        module="dartlab.quant.forecast",
        fn="forecastReturns",
        label="예측",
        description="일별 수익률 horizon-step 예측 + 90% Conformal interval (Naive·AR(1)·ETS-Holt·Theta 자동 dispatch)",
        example='quant("예측", "005930", horizon=5)',
        group="technical",
    ),
    "marketContext": _AxisEntry(
        module="dartlab.quant.marketContext",
        fn="calcMarketContext",
        label="시장맥락",
        description="시장 베타 + 거시 민감도 (USDKRW/금리/CPI/M2) + 외국인+기관 수급 강도 1 행 evidence (price-level OLS, scan.macroBeta 와 책임 분리)",
        example='quant("시장맥락", "005930")',
        group="risk",
    ),
    "regime": _AxisEntry(
        module="dartlab.quant.regime",
        fn="calcRegime",
        label="레짐",
        description="Hamilton 2-state HMM (bull/bear), 추세추종 신호",
        example='quant("레짐", "005930")',
        group="technical",
    ),
    "pattern": _AxisEntry(
        module="dartlab.quant.pattern",
        fn="calcPattern",
        label="패턴",
        description="캔들스틱 10종 + zigzag 기반 지지/저항",
        example='quant("패턴", "005930")',
        group="technical",
    ),
    "chartPatterns": _AxisEntry(
        module="dartlab.quant.chartPatterns",
        fn="calcChartPatterns",
        label="차트패턴",
        description="거시 차트 패턴 — W/M/H&S/삼중/원형 (자동 인식 + 목표가)",
        example='quant("차트패턴", "005930")',
        group="technical",
    ),
    # ── B: 리스크 (risk) — 가격 + 벤치마크 ────────────────
    "beta": _AxisEntry(
        module="dartlab.quant._ax_technical",
        fn="calcBeta",
        label="베타",
        description="시장/섹터/스타일 벤치마크 선택형 베타 + CAPM + 알파 + R²",
        example='quant("베타", "005930", benchmarkMode="sector")',
        group="risk",
    ),
    "benchmark": _AxisEntry(
        module="dartlab.quant.benchmark",
        fn="calcBenchmark",
        label="벤치마크",
        description="종목별 시장·섹터·스타일 KRX 벤치마크 스택과 기간 수익률",
        example='quant("벤치마크", "005930")',
        group="risk",
    ),
    "factor": _AxisEntry(
        module="dartlab.quant.factor",
        fn="decomposeFactor",
        label="팩터",
        description="Fama-French 5 + q-factor 분해 (MKT/SMB/HML/RMW/CMA)",
        example='quant("팩터", "005930")',
        group="risk",
    ),
    "tailrisk": _AxisEntry(
        module="dartlab.quant.tailrisk",
        fn="calcTailrisk",
        label="꼬리위험",
        description="CVaR, 최대낙폭, Sortino, 하방편차",
        example='quant("꼬리위험", "005930")',
        group="risk",
    ),
    "residual": _AxisEntry(
        module="dartlab.quant.residual",
        fn="calcResidual",
        label="잔여수익",
        description="팩터 제거 후 잔여 모멘텀/알파",
        example='quant("잔여수익", "005930")',
        group="risk",
    ),
    # ── C: 미시구조 (microstructure) — 가격 + 거래량/수급 ─
    "liquidity": _AxisEntry(
        module="dartlab.quant.microstructure",
        fn="calcLiquidity",
        label="유동성",
        description="Amihud 비유동성, Roll 스프레드, 회전율",
        example='quant("유동성", "005930")',
        group="microstructure",
    ),
    "flow": _AxisEntry(
        module="dartlab.quant.flowAnalysis",
        fn="calcFlow",
        label="수급",
        description="기관/외국인 매매 분석 (KR전용)",
        example='quant("수급", "005930")',
        group="microstructure",
    ),
    "volume": _AxisEntry(
        module="dartlab.quant.volumeAnalysis",
        fn="calcVolume",
        label="거래량",
        description="OBV 추세, 거래량-가격 괴리, 누적분배",
        example='quant("거래량", "005930")',
        group="microstructure",
    ),
    # ── D: 펀더멘털 퀀트 (fundamental) — scan 프리빌드 ────
    "divergence": _AxisEntry(
        module="dartlab.quant._ax_technical",
        fn="calcDivergence",
        label="괴리",
        description="재무-기술적 괴리 진단",
        example='quant("괴리", "005930")',
        group="fundamental",
    ),
    "quality": _AxisEntry(
        module="dartlab.quant.qualityFactor",
        fn="calcQuality",
        label="퀄리티",
        description="Asness 퀄리티 팩터: 수익성+안전성+성장성 복합",
        example='quant("퀄리티", "005930")',
        group="fundamental",
    ),
    "value": _AxisEntry(
        module="dartlab.quant.valueFactor",
        fn="calcValue",
        label="가치",
        description="가치 신호: PBR/PER/PSR vs 가격 모멘텀",
        example='quant("가치", "005930")',
        group="fundamental",
    ),
    "earnings": _AxisEntry(
        module="dartlab.quant.earningsMomentum",
        fn="calcEarnings",
        label="이익모멘텀",
        description="SUE, PEAD, 이익 수정 모멘텀",
        example='quant("이익모멘텀", "005930")',
        group="fundamental",
    ),
    # ── E: 텍스트/공시 (text) — dartlab 고유 차별화 ───────
    "sentiment": _AxisEntry(
        module="dartlab.quant.textSentiment",
        fn="calcSentiment",
        label="공시심리",
        description="Loughran-McDonald 감성 사전 기반 공시 텍스트 스코어링",
        example='quant("공시심리", "005930")',
        group="text",
    ),
    "toneChange": _AxisEntry(
        module="dartlab.quant.toneChange",
        fn="calcToneChange",
        label="톤변화",
        description="기간별 공시 톤 변화 감지",
        example='quant("톤변화", "005930")',
        group="text",
    ),
    "eventSignal": _AxisEntry(
        module="dartlab.quant.eventSignal",
        fn="calcEventSignal",
        label="이벤트신호",
        description="allFilings 이벤트 기반 신호 (경영진변경, M&A 등)",
        example='quant("이벤트신호", "005930")',
        group="text",
    ),
    "riskText": _AxisEntry(
        module="dartlab.quant.riskText",
        fn="calcRiskText",
        label="리스크텍스트",
        description="리스크 팩터 출현/소멸 텍스트 델타",
        example='quant("리스크텍스트", "005930")',
        group="text",
    ),
    "governanceQuant": _AxisEntry(
        module="dartlab.quant.governanceQuant",
        fn="calcGovernanceQuant",
        label="거버넌스퀀트",
        description="지배구조 품질 정량화 (사외이사비율, 감사의견, 보수)",
        example='quant("거버넌스퀀트", "005930")',
        group="text",
    ),
    # ── F: 횡단면 (crossSection) — 시장 레벨 ─────────────
    "ranking": _AxisEntry(
        module="dartlab.quant.ranking",
        fn="calcRanking",
        label="순위",
        description="멀티팩터 복합 순위 (모멘텀+가치+퀄리티+리스크)",
        example='quant("순위")',
        group="crossSection",
        stockRequired=False,
    ),
    "pairs": _AxisEntry(
        module="dartlab.quant.pairsTrading",
        fn="calcPairs",
        label="페어",
        description="공적분 기반 페어 트레이딩 후보 탐색",
        example='quant("페어")',
        group="crossSection",
        stockRequired=False,
    ),
    "screen": _AxisEntry(
        module="dartlab.quant.screening",
        fn="calcScreen",
        label="스크린",
        description="팩터 스크리닝 프리셋 (가치/모멘텀/퀄리티/저변동)",
        example='quant("스크린")',
        group="crossSection",
        stockRequired=False,
    ),
    # ── Sprint 2 재무 알파 9축 (fundamental + risk) ─────────
    "altman": _AxisEntry(
        module="dartlab.quant.alphas.altman",
        fn="calcAltmanFactor",
        label="Altman Z",
        description="Altman 1968/1995 — 전종목 부실확률 (safe/grey/distress 3 zone) + topSafe/topDistress",
        example='quant("altman")',
        group="fundamental",
        stockRequired=False,
    ),
    "piotroski": _AxisEntry(
        module="dartlab.quant.alphas.piotroski",
        fn="calcPiotroskiFactor",
        label="Piotroski F",
        description="Piotroski 2000 — 9 신호 합 (0~9점) 전종목 분포 + 9 신호 시장 통과율",
        example='quant("piotroski")',
        group="fundamental",
        stockRequired=False,
    ),
    "beneish": _AxisEntry(
        module="dartlab.quant.alphas.beneish",
        fn="calcBeneishFactor",
        label="Beneish M",
        description="Beneish 1999 — 8변수 이익조작 감지, red flag (M > -1.78) 비율 + topFlag",
        example='quant("beneish")',
        group="fundamental",
        stockRequired=False,
    ),
    "accruals": _AxisEntry(
        module="dartlab.quant.alphas.accruals",
        fn="calcAccrualsFactor",
        label="Sloan Accrual",
        description="Sloan 1996 — (NI−CFO)/TA, high/neutral/low 3 그룹 분포",
        example='quant("accruals")',
        group="fundamental",
        stockRequired=False,
    ),
    "qfactor": _AxisEntry(
        module="dartlab.quant.alphas.qFactor",
        fn="calcQFactor",
        label="q-factor",
        description="Hou-Xue-Zhang 2015 — ROE + (−assetGrowth) composite, 수익성×보수투자",
        example='quant("qfactor")',
        group="fundamental",
        stockRequired=False,
    ),
    "qmj": _AxisEntry(
        module="dartlab.quant.alphas.qmj",
        fn="calcQMJ",
        label="QMJ",
        description="Asness-Frazzini-Pedersen 2019 — Profitability + Safety 합성 품질 랭킹",
        example='quant("qmj")',
        group="fundamental",
        stockRequired=False,
    ),
    "bab": _AxisEntry(
        module="dartlab.quant.alphas.bab",
        fn="calcBAB",
        label="BAB 저베타",
        description="Frazzini-Pedersen 2014 — 252일 beta 저베타 랭킹 + 60일 realized vol 보조",
        example='quant("bab")',
        group="risk",
        stockRequired=False,
    ),
    "surprise": _AxisEntry(
        module="dartlab.quant.alphas.earningsSurprise",
        fn="calcEarningsSurprise",
        label="이익서프라이즈",
        description="Bernard-Thomas 1989 PEAD — YoY NI growth z-score, positive SUE drift 후보",
        example='quant("surprise")',
        group="fundamental",
        stockRequired=False,
    ),
    "fundmom": _AxisEntry(
        module="dartlab.quant.alphas.fundamentalMomentum",
        fn="calcFundamentalMomentum",
        label="펀더-가격 모멘텀",
        description="Chordia-Shivakumar 2006 — earnings + 12-1 price 모멘텀 합성 랭킹",
        example='quant("fundmom")',
        group="fundamental",
        stockRequired=False,
    ),
    # ── G: 포트폴리오 (portfolio) — 멀티종목 ─────────────
    "meanvar": _AxisEntry(
        module="dartlab.quant.portfolio",
        fn="optimizeMeanVar",
        label="평균분산",
        description="Markowitz 평균-분산 최적화",
        example='quant("평균분산", ["005930","000660"])',
        group="portfolio",
        multiStock=True,
    ),
    "riskparity": _AxisEntry(
        module="dartlab.quant.portfolio",
        fn="optimizeRiskParity",
        label="리스크패리티",
        description="HRP (Lopez de Prado) 계층적 리스크 패리티",
        example='quant("리스크패리티", ["005930","000660"])',
        group="portfolio",
        multiStock=True,
    ),
    "allocation": _AxisEntry(
        module="dartlab.quant.portfolio",
        fn="allocateERC",
        label="자산배분",
        description="Equal Risk Contribution (Maillard 2010) — 종목별 위험 기여도 균등 배분",
        example='quant("자산배분", ["005930","000660"])',
        group="portfolio",
        multiStock=True,
    ),
    # ── H: Strategy DSL (사용자 컨트롤 boolean rule + 백테스트 + 검증) ────
    "strategy": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runStrategy",
        label="전략",
        description="사용자 정의 boolean rule 백테스트 (Rule + sizing + stop)",
        example='quant("strategy", "005930", rule=myRule)',
        group="strategy",
    ),
    "backtest": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runBacktest",
        label="백테스트",
        description="스타일명 또는 Rule 백테스트 (cpcv 옵션)",
        example='quant("backtest", "005930", style="trendFollow")',
        group="strategy",
    ),
    "style": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runStyle",
        label="스타일",
        description="8 검증된 스타일 프리셋 일괄/단일 백테스트 (시총 의존 0)",
        example='quant("style", "005930", name="all")',
        group="strategy",
        stockRequired=False,  # name 없이 호출 시 카탈로그
    ),
    "entry": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runEntry",
        label="진입진단",
        description="현재 시점 진입/청산/스톱 진단 (백테스트 안 돌림)",
        example='quant("entry", "005930", style="all")',
        group="strategy",
    ),
    "walkforward": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runWalkforward",
        label="워크포워드",
        description="Lopez de Prado 슬라이딩 OOS Sharpe + DSR + PBO",
        example='quant("walkforward", "005930", style="meanReversion")',
        group="strategy",
    ),
    "multi": _AxisEntry(
        module="dartlab.quant._ax_strategy",
        fn="runMultiAsset",
        label="멀티자산",
        description="멀티 종목 포트폴리오 백테스트 (equal/inv_vol/risk_parity 가중)",
        example='quant("multi", ["005930","000660"], style="trendFollow")',
        group="strategy",
        multiStock=True,
    ),
}

# ── Alias 테이블 ─────────────────────────────────────────

_ALIASES: dict[str, str] = {
    # A: 기술적
    "지표": "indicators",
    "기술지표": "indicators",
    "신호": "signals",
    "매매신호": "signals",
    "판단": "verdict",
    "종합": "verdict",
    "종합판단": "verdict",
    "기술판단": "verdict",
    "모멘텀": "momentum",
    "추세": "momentum",
    "변동성": "volatility",
    "vol": "volatility",
    "예측": "forecast",
    "수익률예측": "forecast",
    "forecastReturns": "forecast",
    "returnsForecast": "forecast",
    "시장맥락": "marketContext",
    "맥락": "marketContext",
    "calcMarketContext": "marketContext",
    "레짐": "regime",
    "국면": "regime",
    "패턴": "pattern",
    "캔들": "pattern",
    "캔들패턴": "pattern",
    "차트패턴": "chartPatterns",
    "거시패턴": "chartPatterns",
    "쌍바닥": "chartPatterns",
    "쌍봉": "chartPatterns",
    "헤드앤숄더": "chartPatterns",
    # B: 리스크
    "베타": "beta",
    "시장베타": "beta",
    "벤치마크": "benchmark",
    "시장지수": "benchmark",
    "benchmarkIndex": "benchmark",
    "팩터": "factor",
    "팩터분해": "factor",
    "꼬리위험": "tailrisk",
    "테일리스크": "tailrisk",
    "CVaR": "tailrisk",
    "최대낙폭": "tailrisk",
    "잔여수익": "residual",
    "잔여모멘텀": "residual",
    "알파": "residual",
    # C: 미시구조
    "유동성": "liquidity",
    "비유동성": "liquidity",
    "수급": "flow",
    "외국인": "flow",
    "기관": "flow",
    "거래량": "volume",
    "OBV": "volume",
    # D: 펀더멘털 퀀트
    "괴리": "divergence",
    "재무괴리": "divergence",
    "퀄리티": "quality",
    "품질": "quality",
    "가치": "value",
    "밸류": "value",
    "valuation": "value",
    "valueFactor": "value",
    "이익모멘텀": "earnings",
    "SUE": "earnings",
    "PEAD": "earnings",
    # E: 텍스트/공시
    "공시심리": "sentiment",
    "감성": "sentiment",
    "톤변화": "toneChange",
    "이벤트신호": "eventSignal",
    "이벤트": "eventSignal",
    "리스크텍스트": "riskText",
    "거버넌스퀀트": "governanceQuant",
    "거버넌스": "governanceQuant",
    "지배구조": "governanceQuant",
    # F: 횡단면
    "순위": "ranking",
    "랭킹": "ranking",
    "페어": "pairs",
    "페어트레이딩": "pairs",
    "스크린": "screen",
    "스크리닝": "screen",
    "필터": "screen",
    # G: 포트폴리오
    "평균분산": "meanvar",
    "마코위츠": "meanvar",
    "리스크패리티": "riskparity",
    "HRP": "riskparity",
    "자산배분": "allocation",
    "ERC": "allocation",
    "리스크균등": "allocation",
    # H: Strategy DSL
    "전략": "strategy",
    "백테스트": "backtest",
    "스타일": "style",
    "진입": "entry",
    "진입진단": "entry",
    "워크포워드": "walkforward",
    "전진검증": "walkforward",
    "멀티자산": "multi",
    "포트폴리오백테스트": "multi",
    "multiasset": "multi",
    # Sprint 2 신규 alpha 한글 alias
    "알트만": "altman",
    "Altman": "altman",
    "부실": "altman",
    "Z스코어": "altman",
    "피오트로스키": "piotroski",
    "Piotroski": "piotroski",
    "F스코어": "piotroski",
    "재무건강": "piotroski",
    "베니쉬": "beneish",
    "Beneish": "beneish",
    "M스코어": "beneish",
    "이익조작": "beneish",
    "발생액": "accruals",
    "Sloan": "accruals",
    "발생액품질": "accruals",
    "q팩터": "qfactor",
    "Q팩터": "qfactor",
    "QMJ": "qmj",
    "품질마이너스쓰레기": "qmj",
    "BAB": "bab",
    "저변동성": "bab",
    "저변동": "bab",
    "서프라이즈": "surprise",
    "이익서프라이즈": "surprise",
    "earningsSurprise": "surprise",
    "펀더모멘텀": "fundmom",
    "fundamentalMomentum": "fundmom",
}

# 기존 metric 이름 (하위호환용)
_OLD_METRICS = {"indicators", "signals", "beta", "divergence", "flags", "verdict"}


# ── 축 해석 ──────────────────────────────────────────────


def _resolve(axis: str) -> str:
    """축 정식 이름 또는 명시 alias → 정규 축 이름.

    consistency_no_alias 원칙: case-insensitive 매칭 (``axis.lower()``) 은 silent
    alias 라 인정하지 않는다. 사용자는 정식 표기 (camelCase: ``"toneChange"``,
    ``"eventSignal"``) 또는 ``_ALIASES`` 등록 한글/영문 alias 만 사용한다.
    """
    stripped = axis.strip()
    if stripped in _AXIS_REGISTRY:
        return stripped
    if stripped in _ALIASES:
        return _ALIASES[stripped]
    # fuzzy hint
    axis_names = sorted(set(list(_AXIS_REGISTRY.keys()) + list(_ALIASES.keys())))
    hint = ", ".join(axis_names[:20])
    msg = f"'{axis}' 축을 찾을 수 없습니다. 사용 가능: {hint}..."
    raise KeyError(msg)


def _isStockCode(value: str) -> bool:
    """값이 종목코드처럼 보이는지 판별.

    consistency_no_alias 원칙: case-insensitive lookup 안 함. ``s in _AXIS_REGISTRY``
    strict 매칭으로 axis 와 ticker 충돌 검사 (예: ``"price"`` 는 axis, ``"PRICE"`` 는
    ticker 후보 — registry strict 매칭이 ``False`` 라 ticker 로 판정).
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    # 6자리 숫자 (한국)
    if re.match(r"^\d{6}$", s):
        return True
    # 알파벳 1-5자 (미국 ticker, US ticker 표준은 uppercase)
    if re.match(r"^[A-Z]{1,5}$", s) and s not in _AXIS_REGISTRY and s not in _ALIASES:
        return True
    return False


# ── 그룹 정의 ────────────────────────────────────────────

_GROUPS = {
    "technical": "기술적",
    "risk": "리스크",
    "microstructure": "미시구조",
    "fundamental": "펀더멘털",
    "text": "텍스트/공시",
    "crossSection": "횡단면",
    "portfolio": "포트폴리오",
    "strategy": "전략 DSL",
}


# ── Quant 클래스 ─────────────────────────────────────────


class Quant:
    """종목 레벨 정량분석 엔진 — 31축 7그룹.

    dartlab.quant("축명", "종목코드") 로 접근.
    """

    def __call__(
        self,
        axis: str | list | None = None,
        stockCode: str | list | None = None,
        **kwargs: Any,
    ) -> pl.DataFrame | dict | Any:
        """가격 기반 정량 분석 — 8 그룹 30+ 축 (기술·리스크·팩터·백테스트·알파).

        Parameters
        ----------
        axis : str | None
            분석 축 또는 별칭. None 이면 가이드 DataFrame 반환.
            주요 축: "판단"(verdict), "모멘텀", "변동성", "시뮬레이션",
            "가치평가"(valuation), "altman", "piotroski", "bab" 등 30+ 축.
        stockCode : str | list | None
            종목코드/ticker. 두 번째 인자: quant("모멘텀", "005930").
            market 자동 감지 (6자리→KR, 알파벳→US).
        **kwargs
            축별 추가 파라미터. 리스크 축은 ``benchmarkMode="market"|"sector"|"style"|"auto"``
            와 ``benchmark="코스피 200"`` 명시 override를 받는다.

        Returns
        -------
        dict
            종목 지정 시 축별 분석 결과:
                verdict(판단): signal, confidence, indicators (매수/매도/중립)
                momentum(모멘텀): returns, rsi, macd, moving_averages
                volatility(변동성): realized, garch, regime
                benchmark(벤치마크): benchmarkUsed, benchmarkStack, 기간 수익률 (%)
                simulation(시뮬레이션): paths, expectedReturn, var (%)
                altman: zScore, zone (safe/grey/distress)
                piotroski: fScore (0~9점)
        pl.DataFrame
            axis=None: 가이드 — 축 목록 + 설명 + 예시.
            횡단면 축 (market="KR"): 전종목 DataFrame.

        Raises
        ------
        ValueError
            축 이름이 등록되지 않은 경우.
            종목 필수 축에서 stockCode 누락 시.
        TypeError
            axis 에 list 전달 시.

        Examples
        --------
        >>> c.quant()                          # 가이드
        >>> c.quant("판단")                     # 종합 매수/매도 판단
        >>> c.quant("모멘텀")                   # 모멘텀 지표
        >>> dartlab.quant("altman", "005930")   # Altman Z-Score
        >>> dartlab.quant("piotroski", "005930")  # Piotroski F-Score

        Notes
        -----
        주가 데이터는 gather("price") 경유 자동 수집. API 키 불필요 (Naver/Yahoo).

        Guide
        -----
        AI 역할: AI는 quant를 가격·팩터·시계열 신호 엔진으로 보고 기간, benchmark, 수익률/변동성 근거를 분리한다.
        When: 주가 기반 기술적 신호·팩터·리스크를 정량 분석할 때.
        How: quant("판단") 으로 종합 신호 확인 → 세부 축으로 근거 파악.
            quant("벤치마크") 로 시장·섹터·스타일 benchmarkStack 을 확인한다.
            beta/residual/factor/BAB 는 기본 market mode를 유지하고,
            benchmarkMode="sector" 또는 "style" 로 상대 기준을 명시 전환한다.
            analysis(재무) + quant(기술) 조합이 story full/valuation 타입의 핵심.
            credit 과 함께 사용 시 altman/piotroski 로 부도 위험 교차 검증.
        Verified:
            - quant("판단") → RSI/ADX/MACD/볼린저/상대강도 + 종합 판정 (observed via ai-ask, 2026-04-25 — 정식 Phase P 판정 아님)
            - quant("베타", benchmarkMode="sector") → KRX 섹터 지수 대비 beta.

        See Also
        --------
        analysis : 재무 인과 분석 — quant 기술 + analysis 재무 조합.
        gather : 주가·수급 데이터 수집 — quant 의 데이터 원천.
        scan : 전종목 횡단 비교.

        LLM Specifications:
            AntiPatterns:
                - axis 추측 (한글 — 판단 / 모멘텀 / 변동성 / 가치 / 베타 / altman / piotroski 등)
                - stockCode 형식 혼동 — KR 6 자리 숫자 / US ticker 알파벳
                - axis="베타" 호출 시 benchmarkMode 미지정 (default market — 섹터 의도면 명시)
                - quant("005930", "판단") deprecated 형식 (axis 가 첫 인자)
            OutputSchema:
                - axis="판단": dict — signal / confidence / indicators
                - axis="모멘텀": dict — returns / rsi / macd / moving_averages
                - axis="베타": dict — beta / benchmarkUsed / benchmarkStack
                - axis="altman": dict — zScore / zone (safe / grey / distress)
                - axis="piotroski": dict — fScore (0~9)
                - axis 미지정: 가이드 DataFrame
            Prerequisites:
                - 주가 데이터 (gather("price") 자동 수집) — 첫 호출 시간 소요
            Freshness:
                price 데이터 — T+1 (전일 종가).
            TargetMarkets:
                - KR (Naver Finance)
                - US (Yahoo Finance)
        """
        if axis is None and stockCode is None:
            return self._guide()

        # ── 하위호환 브릿지 ──
        # 기존: quant("005930", "indicators") → 새: quant("indicators", "005930")
        if axis is not None and isinstance(axis, str) and _isStockCode(axis):
            if stockCode is not None and isinstance(stockCode, str):
                if stockCode in _AXIS_REGISTRY or stockCode in _ALIASES or stockCode in _OLD_METRICS:
                    # swap: quant("005930", "indicators") → quant("indicators", "005930")
                    warnings.warn(
                        f'dartlab.quant("{axis}", "{stockCode}") 호출 방식은 deprecated입니다. '
                        f'dartlab.quant("{stockCode}", "{axis}") 형태를 사용하세요.',
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    # flags → verdict로 매핑
                    actual_axis = stockCode if stockCode != "flags" else "verdict"
                    return self._dispatch(actual_axis, axis, **kwargs)
            elif stockCode is None:
                # quant("005930") → verdict
                warnings.warn(
                    f'dartlab.quant("{axis}") 호출 방식은 deprecated입니다. '
                    f'dartlab.quant("verdict", "{axis}") 형태를 사용하세요.',
                    DeprecationWarning,
                    stacklevel=2,
                )
                return self._dispatch("verdict", axis, **kwargs)

        # ── 정상 경로 ──
        if isinstance(axis, str):
            return self._dispatch(axis, stockCode, **kwargs)

        # axis가 list면 포트폴리오 가이드 없이 에러
        msg = f"축 이름(str) 또는 None을 전달하세요. 받은 값: {type(axis)}"
        raise TypeError(msg)

    def _dispatch(self, axis: str, stockCode: str | list | None, **kwargs: Any) -> Any:
        """축을 해석하고 해당 모듈의 함수를 호출."""
        key = _resolve(axis)
        entry = _AXIS_REGISTRY[key]

        # 종목 필수인데 없으면 에러
        if entry.stockRequired and not entry.multiStock and stockCode is None:
            msg = f'quant("{entry.label}") 축은 종목코드가 필요합니다.\n  사용법: {entry.example}'
            raise ValueError(msg)

        # 멀티종목인데 리스트가 아니면 안내
        if entry.multiStock and stockCode is not None and not isinstance(stockCode, list):
            stockCode = [stockCode]

        # lazy import + 호출
        mod = importlib.import_module(entry.module)
        fn = getattr(mod, entry.fn)

        if entry.multiStock:
            return fn(stockCodes=stockCode or [], **kwargs)
        elif entry.stockRequired:
            return fn(stockCode=stockCode, **kwargs)
        else:
            # 횡단면: 종목 불필요, 있으면 필터
            if stockCode is not None:
                return fn(stockCode=stockCode, **kwargs)
            return fn(**kwargs)

    def _guide(self) -> pl.DataFrame:
        """축 카탈로그 — 통일 컬럼 (axis, label, description, example, group)."""
        from dartlab.core.axisGuide import buildAxisGuideDataFrame

        def _desc(_k: str, entry) -> str:
            if not entry.stockRequired:
                return entry.description + " (종목 불필요)"
            if entry.multiStock:
                return entry.description + " (종목 리스트)"
            return entry.description

        return buildAxisGuideDataFrame(
            _AXIS_REGISTRY,
            groupExtractor=lambda _k, e: _GROUPS.get(e.group, e.group),
            descriptionExtractor=_desc,
            apiKey=None,
        )

    def __repr__(self) -> str:
        # 그룹별 축 이름 수집
        grouped: dict[str, list[str]] = {}
        for key, entry in _AXIS_REGISTRY.items():
            g = _GROUPS.get(entry.group, entry.group)
            grouped.setdefault(g, []).append(key)

        lines = [
            f"Quant — {len(_AXIS_REGISTRY)}축 종목 레벨 정량분석",
            "",
            "━━━ 그룹별 축 ━━━",
        ]
        for g, axes in grouped.items():
            lines.append(f"  {g} ({len(axes)}): {', '.join(axes)}")

        lines += [
            "",
            "━━━ 빠른 시작 ━━━",
            '  c = dartlab.Company("005930")',
            "  c.quant()                             # 이 가이드",
            '  c.quant("종합")                        # 기술적 종합 판정',
            '  c.quant("모멘텀")                      # 모멘텀 분석',
            '  c.quant("베타")                        # 시장 베타 + CAPM',
            "",
            "━━━ 데이터 ━━━",
            "  주가 OHLCV: 자동 수집 (네이버/Yahoo, API 키 불필요)",
            "  재무 데이터: scan/finance.parquet (자동 다운로드)",
            "",
            "  노트북: https://marimo.app/github.com/eddmpython/dartlab/blob/master/notebooks/marimo/04_quant.py",
        ]
        return "\n".join(lines)

    # scan → quant 폐쇄 루프 — axis 미등록 (top-level helper)
    def scanBacktest(self, scanResult, **kwargs):
        """scan 결과 universe + signalFn / style → multi-asset backtest.

        ``runScanBacktest`` 를 ``dartlab.quant`` attribute 로 노출. axis 미등록 —
        registry dispatcher 의 ``fn(stockCode, **kw)`` 계약과 시그니처가 어긋나기 때문.
        세부 시그니처는 ``dartlab.quant.scanBacktest.runScanBacktest`` 참고.
        """
        from dartlab.quant.scanBacktest import runScanBacktest

        return runScanBacktest(scanResult, **kwargs)

    # accessor 패턴: quant.momentum("005930")
    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            key = _resolve(name)
        except KeyError:
            raise AttributeError(f"Quant has no axis '{name}'") from None

        entry = _AXIS_REGISTRY[key]

        def _run(stockCode=None, **kw):
            return self._dispatch(key, stockCode, **kw)

        _run.__doc__ = f"{entry.label}: {entry.description}"
        return _run


# scanBacktest top-level helper — 서브모듈과 같은 이름이라 module attribute 를
# 함수 binding 으로 덮어쓰기 (dl.quant.scanBacktest(scanResult, ...) 호출 가능).
from dartlab.quant.scanBacktest import runScanBacktest as scanBacktest  # noqa: E402, F401
