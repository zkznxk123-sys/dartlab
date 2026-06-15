// 백테스트 타입·상수 계약 (순수 타입 — 로직 import 0). 변경 이유: 결과/원장 계약.
// 03 §0.5.4 정합: long/flat 단일종목 → 2구조(equity+trades) + reconcile 가드 + exit/deferred 필드.
import type { Candle } from '@dartlab/ui-contracts';

export type BtPresetKey = 'maCross' | 'rsiRevert' | 'bbRevert' | 'macdCross' | 'donchian' | 'momentum';

export interface BtParamDef {
	name: string;
	kr: string;
	en: string;
	min: number;
	max: number;
	step: number;
	def: number;
}
export interface BtPresetDef {
	key: BtPresetKey;
	kr: string;
	en: string;
	descKr: string;
	descEn: string;
	params: BtParamDef[];
	warmup: (p: Record<string, number>) => number;
	// 당일 종가까지의 데이터만으로 계산한 목표 포지션 (0|1). trailing window 만 사용.
	signal: (closes: number[], p: Record<string, number>) => Int8Array;
}

// 비용 기본값 (bp) — opts.costsBp 로 편집 가능. 수수료 양측 + 매도 거래세 + 슬리피지.
export const BT_COSTS = { commissionBp: 1.5, sellTaxBp: 15, slippageBp: 10 };
export type BtCostsBp = { commissionBp: number; sellTaxBp: number; slippageBp: number };

// 엔진 계산 계약 버전 — 체결/비용 모델이 바뀌면 올린다(결과 재현·캐시 무효화 기준).
export const BT_ENGINE_VERSION = 'bt-1';

export interface BtTrade {
	entryT: string; // YYYYMMDD (entry fill 일 = signal 다음 거래일)
	exitT: string | null; // null = 미청산
	entryPx: number; // 비용 반영 유효체결가
	exitPx: number | null;
	retPct: number;
	holdDays: number; // 거래일(봉) 수
	open: boolean;
	// 03 §0.5.4 — 청산 사유 명시(현 open:true 암묵 → 명시). signal=신호청산 / finalMark=미청산 종가 가상평가.
	exitReason: 'signal' | 'finalMark';
	entryDeferredBars: number; // v=0/거래정지로 진입이 이연된 봉 수(0=신호 다음 봉 즉시 체결, 감사용)
}
export interface BtWarning {
	kind: 'fewTrades' | 'shortRange' | 'splitSuspect' | 'costsOff';
	date?: string;
}
export interface BtMetrics {
	retPct: number;
	cagrPct: number | null; // windowBars < 252 → null (연환산 거짓말 차단)
	mddPct: number;
	mddDays: number | null; // 최장 수면(피크→회복) 거래일 — 미회복이면 현재까지
	sharpe: number | null; // 일수익률 연환산 (rf=0), windowBars < 60 → null
	sortino: number | null; // 하방 변동성 기준 — 하락일 0건이면 null
	winRatePct: number | null;
	profitFactor: number | null;
	tradeCount: number;
	avgTradePct: number | null; // 거래당 평균 수익률
	bestTradePct: number | null;
	worstTradePct: number | null;
	avgHoldDays: number | null;
	exposurePct: number;
	costDragPct: number; // 비용 ON 수익률 − 비용 OFF 수익률 (≤0)
}

/**
 * 결과 재현 메타(03 §3 "모든 결과에 RunSpec·기준일·원천·수정주가·배당·비용·벤치마크 부착").
 * 순수 데이터 조립(Date 미사용 — generatedAt 은 export 시 호출측이 부여). 호출측이 opts.spec 으로 입력 주입.
 */
export interface BtRunSpec {
	engineVersion: string;
	symbol: { code: string; name?: string; market?: 'KR' | 'US' };
	dataSource: string; // 예: 'gov/prices'
	dataAsOf: string; // 평가창 마지막 캔들 YYYYMMDD
	adjusted: boolean; // 수정주가 입력 여부
	dividend: 'excluded'; // 배당 미반영(데이터 한계 — totalReturn 미지원)
	range: { from: string; to: string; bars: number }; // 평가창 거래일 범위
	strategy: { id: BtPresetKey; params: Record<string, number> };
	costs: { enabled: boolean; commissionBp: number; sellTaxBp: number; slippageBp: number };
	benchmark: { kind: 'buyAndHold'; sameCosts: true };
}

export interface BtResult {
	status: 'ok' | 'invalid'; // 03 §0.5.4 reconcile 가드 — invalid 면 UI 지표 미노출
	startIdx: number; // 평가창 시작 (candles 인덱스)
	equity: (number | null)[]; // candles 와 같은 길이, 창 밖 = null, equity[startIdx]=100
	bhEquity: (number | null)[];
	trades: BtTrade[];
	metrics: BtMetrics;
	bh: { retPct: number; cagrPct: number | null; mddPct: number; sharpe: number | null };
	mddWindow: { peakIdx: number; troughIdx: number; recoverIdx: number | null } | null; // 에쿼티 페인 음영용
	deferredBars: number; // 평가창 전체 v=0 체결 이연 봉 수(감사·경고 근거)
	warnings: BtWarning[];
	runSpec?: BtRunSpec; // opts.spec 주입 시 — 재현·푸터·export 용 (미주입이면 undefined)
}

/** runBacktest opts.spec 입력 — 호출측(PriceChart)이 아는 종목/데이터 메타. */
export interface BtSpecInput {
	code: string;
	name?: string;
	market?: 'KR' | 'US';
	dataSource?: string; // 기본 'gov/prices'
	adjusted?: boolean;
	dividend?: 'excluded';
}

export type { Candle };
