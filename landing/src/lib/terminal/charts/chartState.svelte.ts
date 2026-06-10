// 차트 UI 상태 SSOT — ChartCtl runes 클래스 + 공유 상수. PriceChart(effects)·ChartMenus(일반)·
// ChartRibbon(전체화면)이 같은 인스턴스를 공유한다 — 상태 중복 0. 차트 인스턴스 명령(드로잉 생성 등)은
// 상태가 아니므로 콜백으로 — "상태에 요청 넣고 effect 소비" 안티패턴 금지.
import { browser } from '$app/environment';
import { BT_PRESETS, BT_COSTS, type BtPresetKey, type BtPresetDef, type BtParamDef, type BtCostsBp } from '../data/backtest';
import { IND_DEFS } from './indicatorParams';

export type SubKey = 'VOL' | 'TVAL' | 'MACD' | 'RSI' | 'KDJ' | 'OBV' | 'CCI' | 'WR' | 'DMI' | 'MTM' | 'ROC' | 'TRIX' | 'PSY' | 'VR' | 'BRAR' | 'BIAS' | 'CR' | 'DMA' | 'EMV' | 'AO' | 'PVT' | 'AVP';
export const SUB_ALL: SubKey[] = ['VOL', 'TVAL', 'MACD', 'RSI', 'KDJ', 'OBV', 'CCI', 'WR', 'DMI', 'MTM', 'ROC', 'TRIX', 'PSY', 'VR', 'BRAR', 'BIAS', 'CR', 'DMA', 'EMV', 'AO', 'PVT', 'AVP'];
export type OverlayKey = 'MA' | 'EMA' | 'SMA' | 'BOLL' | 'BBI' | 'SAR' | 'ICHI' | 'ENV';
export const OVERLAY_ALL: OverlayKey[] = ['MA', 'EMA', 'SMA', 'BOLL', 'BBI', 'SAR', 'ICHI', 'ENV'];
// klinecharts YAxisType enum 은 'log' (logarithmic 아님 — 오기 시 조용히 무시되어 로그축이 죽는다)
export type YMode = 'normal' | 'log' | 'percentage';
export type CandleStyle = 'candle_solid' | 'candle_up_stroke' | 'ohlc' | 'area';

// 페인 지표 카탈로그 그룹 — 증권사 지표트리 멘탈모델 (리본 [+] 팝오버 3행)
export const SUB_GROUPS: { kr: string; en: string; keys: SubKey[] }[] = [
	{ kr: '추세', en: 'Trend', keys: ['MACD', 'DMI', 'DMA', 'TRIX'] },
	{ kr: '모멘텀', en: 'Momentum', keys: ['RSI', 'KDJ', 'WR', 'CCI', 'MTM', 'ROC', 'BIAS', 'PSY', 'BRAR', 'CR', 'AO'] },
	{ kr: '거래량', en: 'Volume', keys: ['VOL', 'TVAL', 'OBV', 'VR', 'EMV', 'PVT', 'AVP'] }
];
// 한국식 명칭 병기 (코드 0줄 대체 — 이격도=BIAS·스토캐스틱=KDJ·ADX=DMI)
export const SUB_HINT: Partial<Record<SubKey, string>> = { BIAS: '이격도', KDJ: '스토캐스틱', DMI: 'ADX', TVAL: '거래대금' };
export const OVERLAY_HINT: Partial<Record<OverlayKey, string>> = { ICHI: '일목균형표', ENV: '엔벨로프', BOLL: '볼린저' };

export const PERIODS = ['1M', '3M', '6M', '1Y', '3Y', 'MAX'] as const;
export type PeriodKey = (typeof PERIODS)[number];
export const PERIOD_N: Record<string, number> = { '1M': 22, '3M': 66, '6M': 132, '1Y': 252, '3Y': 750, MAX: 100000 };
// 봉 주기 — 데이터는 일봉, 주/월은 클라이언트 집계(aggregateCandles). TF_DIV = 거래일 환산 제수.
export type TfKey = 'D' | 'W' | 'M';
export const TFS: { v: TfKey; kr: string; en: string }[] = [
	{ v: 'D', kr: '일', en: 'D' },
	{ v: 'W', kr: '주', en: 'W' },
	{ v: 'M', kr: '월', en: 'M' }
];
export const TF_DIV: Record<TfKey, number> = { D: 1, W: 5, M: 21 };
export const YMODES: { v: YMode; kr: string; en: string }[] = [
	{ v: 'normal', kr: '일반', en: 'Linear' },
	{ v: 'log', kr: '로그', en: 'Log' },
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
	{ name: 'priceChannelLine', icon: '⫻', kr: '가격채널', en: 'PriceCh' },
	{ name: 'anchoredVWAP', icon: '⚓', kr: '앵커VWAP', en: 'AVWAP' },
	{ name: 'MEASURE', icon: '📏', kr: '측정', en: 'Measure' }
];

export const ECON_MAX = 3; // 경제지표 동시 표시 상한 (시각·툴팁 밀도)

const PREFS_KEY = 'dlTerm.chart'; // 차트 환경 설정 영속 (전역 1키 — 차트 습관은 회사 무관)

export class ChartCtl {
	period = $state<PeriodKey>('1Y');
	tf = $state<TfKey>('D'); // 봉 주기 (일/주/월) — MAX 등 바스페이스 1px 미달 시 자동 상향
	adj = $state(true); // 수정주가 (등락률 체이닝 — 분할·병합·권리락 보정) — HTS 기본 ON
	overlays = $state<OverlayKey[]>(['MA']);
	subs = $state<SubKey[]>(['VOL', 'RSI']);
	econ = $state<string[]>([]);
	yMode = $state<YMode>('normal');
	candleStyle = $state<CandleStyle>('candle_solid');
	showEvents = $state(false);
	showBand = $state(false);
	showRefs = $state(false); // 52주 고가·저가·전일종가 기준선
	showVP = $state(false); // 매물대 (Volume Profile)
	magnet = $state(false);
	full = $state(false);
	btKey = $state<BtPresetKey | null>(null);
	btParams = $state<Record<string, number>>({});
	btCosts = $state(true);
	btCostsBp = $state<BtCostsBp>({ ...BT_COSTS });
	indParams = $state<Record<string, number[]>>({}); // 지표별 calcParams 오버라이드 (없으면 내장 기본)
	compares = $state<{ code: string; name: string }[]>([]); // 종목비교 (최대 3, 세션 한정 — 회사 컨텍스트)
	private prevYMode: YMode = 'normal'; // 비교 진입 전 y축 — 마지막 비교 해제 시 복귀
	drawCount = $state(0); // 그리기 버튼 하이라이트용 (드로잉 본체는 PriceChart drawMap)
	activeBt = $derived(this.btKey ? (BT_PRESETS.find((d) => d.key === this.btKey) ?? null) : null);

	constructor() {
		this.hydrate();
	}

	// localStorage 설정 복원 — 화이트리스트 검증 통과 값만 채택 (스키마 드리프트·손상 방어).
	// showBand 는 회사별 valBand 유무에 묶여 제외, btKey 류는 세션 한정이라 제외.
	private hydrate(): void {
		if (!browser) return;
		try {
			const raw = localStorage.getItem(PREFS_KEY);
			if (!raw) return;
			const p = JSON.parse(raw) as Record<string, unknown>;
			if (Array.isArray(p.overlays)) this.overlays = p.overlays.filter((k): k is OverlayKey => OVERLAY_ALL.includes(k as OverlayKey));
			if (Array.isArray(p.subs)) this.subs = p.subs.filter((k): k is SubKey => SUB_ALL.includes(k as SubKey));
			if (Array.isArray(p.econ)) this.econ = p.econ.filter((x): x is string => typeof x === 'string').slice(0, ECON_MAX);
			if (PERIODS.includes(p.period as PeriodKey)) this.period = p.period as PeriodKey;
			if (TFS.some((t) => t.v === p.tf)) this.tf = p.tf as TfKey;
			if (YMODES.some((y) => y.v === p.yMode)) this.yMode = p.yMode as YMode;
			if (CANDLES.some((cd) => cd.v === p.candleStyle)) this.candleStyle = p.candleStyle as CandleStyle;
			if (typeof p.adj === 'boolean') this.adj = p.adj;
			if (typeof p.showEvents === 'boolean') this.showEvents = p.showEvents;
			if (typeof p.showRefs === 'boolean') this.showRefs = p.showRefs;
			if (typeof p.showVP === 'boolean') this.showVP = p.showVP;
			if (typeof p.magnet === 'boolean') this.magnet = p.magnet;
			if (p.indParams && typeof p.indParams === 'object') {
				const ip: Record<string, number[]> = {};
				for (const [k, v] of Object.entries(p.indParams as Record<string, unknown>)) {
					if (IND_DEFS[k] && Array.isArray(v) && v.length && v.every((x) => Number.isFinite(x))) ip[k] = v as number[];
				}
				if (Object.keys(ip).length) this.indParams = ip;
			}
		} catch {
			/* 손상 — 기본값 유지 */
		}
	}

	/** 차트 환경 저장 — PriceChart 의 persist effect 가 변경 시마다 호출. */
	persist(): void {
		if (!browser) return;
		try {
			localStorage.setItem(
				PREFS_KEY,
				JSON.stringify({
					overlays: this.overlays, subs: this.subs, econ: this.econ, period: this.period, tf: this.tf,
					yMode: this.yMode, candleStyle: this.candleStyle, indParams: this.indParams,
					adj: this.adj, showEvents: this.showEvents, showRefs: this.showRefs, showVP: this.showVP, magnet: this.magnet
				})
			);
		} catch {
			/* quota — 무해 */
		}
	}

	toggleSub(k: SubKey) {
		this.subs = this.subs.includes(k) ? this.subs.filter((x) => x !== k) : [...this.subs, k];
	}
	toggleOverlay(k: OverlayKey) {
		this.overlays = this.overlays.includes(k) ? this.overlays.filter((x) => x !== k) : [...this.overlays, k];
	}
	toggleEcon(id: string) {
		this.econ = this.econ.includes(id) ? this.econ.filter((x) => x !== id) : this.econ.length >= ECON_MAX ? this.econ : [...this.econ, id];
	}
	/** 비교 전체 해제 — 회사 전환 시 호출 (이전 회사 기준 비교는 무의미). */
	clearCompares() {
		if (!this.compares.length) return;
		this.compares = [];
		this.yMode = this.prevYMode;
	}
	// 종목비교 토글 — 첫 추가 시 % 축 자동 전환(HTS 동작), 마지막 제거 시 이전 축 복귀
	toggleCompare(p: { code: string; name: string }) {
		if (this.compares.some((x) => x.code === p.code)) {
			this.compares = this.compares.filter((x) => x.code !== p.code);
			if (!this.compares.length) this.yMode = this.prevYMode;
		} else if (this.compares.length < 3) {
			if (!this.compares.length) {
				this.prevYMode = this.yMode;
				this.yMode = 'percentage';
			}
			this.compares = [...this.compares, p];
		}
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
