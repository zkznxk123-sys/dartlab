// 차트 UI 상태 SSOT — ChartCtl runes 클래스 + 공유 상수. PriceChart(effects)·ChartMenus(일반)·
// ChartRibbon(전체화면)이 같은 인스턴스를 공유한다 — 상태 중복 0. 차트 인스턴스 명령(드로잉 생성 등)은
// 상태가 아니므로 콜백으로 — "상태에 요청 넣고 effect 소비" 안티패턴 금지.
import { BT_PRESETS, BT_COSTS, type BtPresetKey, type BtPresetDef, type BtParamDef, type BtCostsBp } from '../data/backtest';
import { IND_DEFS } from './indicatorParams';

export type SubKey = 'VOL' | 'MACD' | 'RSI' | 'KDJ' | 'OBV' | 'CCI' | 'WR' | 'DMI' | 'MTM' | 'ROC' | 'TRIX' | 'PSY' | 'VR' | 'BRAR' | 'BIAS' | 'CR' | 'DMA' | 'EMV' | 'AO' | 'PVT' | 'AVP';
export const SUB_ALL: SubKey[] = ['VOL', 'MACD', 'RSI', 'KDJ', 'OBV', 'CCI', 'WR', 'DMI', 'MTM', 'ROC', 'TRIX', 'PSY', 'VR', 'BRAR', 'BIAS', 'CR', 'DMA', 'EMV', 'AO', 'PVT', 'AVP'];
export type OverlayKey = 'MA' | 'EMA' | 'SMA' | 'BOLL' | 'BBI' | 'SAR' | 'ICHI' | 'ENV';
export const OVERLAY_ALL: OverlayKey[] = ['MA', 'EMA', 'SMA', 'BOLL', 'BBI', 'SAR', 'ICHI', 'ENV'];
export type YMode = 'normal' | 'logarithmic' | 'percentage';
export type CandleStyle = 'candle_solid' | 'candle_up_stroke' | 'ohlc' | 'area';

// 페인 지표 카탈로그 그룹 — 증권사 지표트리 멘탈모델 (리본 [+] 팝오버 3행)
export const SUB_GROUPS: { kr: string; en: string; keys: SubKey[] }[] = [
	{ kr: '추세', en: 'Trend', keys: ['MACD', 'DMI', 'DMA', 'TRIX'] },
	{ kr: '모멘텀', en: 'Momentum', keys: ['RSI', 'KDJ', 'WR', 'CCI', 'MTM', 'ROC', 'BIAS', 'PSY', 'BRAR', 'CR', 'AO'] },
	{ kr: '거래량', en: 'Volume', keys: ['VOL', 'OBV', 'VR', 'EMV', 'PVT', 'AVP'] }
];
// 한국식 명칭 병기 (코드 0줄 대체 — 이격도=BIAS·스토캐스틱=KDJ·ADX=DMI)
export const SUB_HINT: Partial<Record<SubKey, string>> = { BIAS: '이격도', KDJ: '스토캐스틱', DMI: 'ADX' };
export const OVERLAY_HINT: Partial<Record<OverlayKey, string>> = { ICHI: '일목균형표', ENV: '엔벨로프', BOLL: '볼린저' };

export const PERIODS = ['1M', '3M', '6M', '1Y', '3Y', 'MAX'] as const;
export type PeriodKey = (typeof PERIODS)[number];
export const PERIOD_N: Record<string, number> = { '1M': 22, '3M': 66, '6M': 132, '1Y': 252, '3Y': 750, MAX: 100000 };
export const YMODES: { v: YMode; kr: string; en: string }[] = [
	{ v: 'normal', kr: '일반', en: 'Linear' },
	{ v: 'logarithmic', kr: '로그', en: 'Log' },
	{ v: 'percentage', kr: '%', en: '%' }
];
export const CANDLES: { v: CandleStyle; kr: string; en: string }[] = [
	{ v: 'candle_solid', kr: '캔들', en: 'Candle' },
	{ v: 'candle_up_stroke', kr: '속빈', en: 'Hollow' },
	{ v: 'ohlc', kr: '바', en: 'Bar' },
	{ v: 'area', kr: '라인', en: 'Line' }
];
export const DRAW_TOOLS: { name: string; icon: string; kr: string; en: string }[] = [
	{ name: 'segment', icon: '╱', kr: '추세선', en: 'Trend' },
	{ name: 'rayLine', icon: '⟋', kr: '레이', en: 'Ray' },
	{ name: 'priceLine', icon: '─', kr: '가격선', en: 'Price' },
	{ name: 'horizontalStraightLine', icon: '═', kr: '수평선', en: 'Horiz' },
	{ name: 'verticalStraightLine', icon: '║', kr: '수직선', en: 'Vert' },
	{ name: 'fibonacciLine', icon: '⌖', kr: '피보나치', en: 'Fib' },
	{ name: 'parallelStraightLine', icon: '⫽', kr: '평행채널', en: 'Channel' },
	{ name: 'priceChannelLine', icon: '⫻', kr: '가격채널', en: 'PriceCh' }
];

export const ECON_MAX = 3; // 경제지표 동시 표시 상한 (시각·툴팁 밀도)

export class ChartCtl {
	period = $state<PeriodKey>('1Y');
	overlays = $state<OverlayKey[]>(['MA']);
	subs = $state<SubKey[]>(['VOL', 'RSI']);
	econ = $state<string[]>([]);
	yMode = $state<YMode>('normal');
	candleStyle = $state<CandleStyle>('candle_solid');
	showEvents = $state(false);
	showBand = $state(false);
	magnet = $state(false);
	full = $state(false);
	btKey = $state<BtPresetKey | null>(null);
	btParams = $state<Record<string, number>>({});
	btCosts = $state(true);
	btCostsBp = $state<BtCostsBp>({ ...BT_COSTS });
	indParams = $state<Record<string, number[]>>({}); // 지표별 calcParams 오버라이드 (없으면 내장 기본)
	drawCount = $state(0); // 그리기 버튼 하이라이트용 (drawIds 는 PriceChart 로컬)
	activeBt = $derived(this.btKey ? (BT_PRESETS.find((d) => d.key === this.btKey) ?? null) : null);

	toggleSub(k: SubKey) {
		this.subs = this.subs.includes(k) ? this.subs.filter((x) => x !== k) : [...this.subs, k];
	}
	toggleOverlay(k: OverlayKey) {
		this.overlays = this.overlays.includes(k) ? this.overlays.filter((x) => x !== k) : [...this.overlays, k];
	}
	toggleEcon(id: string) {
		this.econ = this.econ.includes(id) ? this.econ.filter((x) => x !== id) : this.econ.length >= ECON_MAX ? this.econ : [...this.econ, id];
	}
	setPreset(pd: BtPresetDef) {
		this.btKey = pd.key;
		this.btParams = Object.fromEntries(pd.params.map((x) => [x.name, x.def]));
	}
	stepBtParam(pp: BtParamDef, dir: 1 | -1) {
		const cur = this.btParams[pp.name] ?? pp.def;
		const next = Math.max(pp.min, Math.min(pp.max, +(cur + dir * pp.step).toFixed(2)));
		const p = { ...this.btParams, [pp.name]: next };
		if (p.fast != null && p.slow != null && p.fast >= p.slow) return; // 단기 < 장기 (maCross·macdCross 공통)
		this.btParams = p;
	}
	// setCalcParams 는 동등성 비교 없이 무조건 전봉 재계산 — same-value 가드 필수.
	setIndParams(name: string, next: number[]) {
		const cur = this.indParams[name] ?? IND_DEFS[name]?.defaults;
		if (cur && cur.length === next.length && cur.every((v, i) => v === next[i])) return;
		this.indParams = { ...this.indParams, [name]: next };
	}
	resetIndParams(name: string) {
		if (!(name in this.indParams)) return;
		const { [name]: _, ...rest } = this.indParams;
		this.indParams = rest;
	}
	clearAllIndicators() {
		this.overlays = [];
		this.subs = [];
		this.econ = [];
	}
}
