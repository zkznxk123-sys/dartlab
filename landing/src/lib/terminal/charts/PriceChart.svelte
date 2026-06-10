<script lang="ts">
	// 전문 증권사급 주가차트 — klinecharts(v9) CORE + 인-차트 툴바.
	// klinecharts CORE 는 네이티브 툴바/기간 위젯이 없다(캔버스=차트뿐) — TradingView lightweight-charts·Highcharts stock core 와 동일.
	// 따라서 차트 크롬은 통합 측 자체 구성이 표준. 본 컴포넌트가 기간·지표·드로잉·표시(캔들/축/마커)·전체화면을 제공.
	// 전체 이력(2010~) lazy 로드(setLoadDataCallback, 좌측 팬), 인스턴스 영속(회사전환=applyNewData, dispose 안 함).
	// adapter-static·SSR 안전: $effect 안 동적 import + dispose cleanup. 화면 브랜딩 없음(Apache-2.0).
	import { browser } from '$app/environment';
	import { KRX_MIN_YEAR, type Candle } from '../data/priceSeries';
	import { price as wbPrice } from '../data/workbench';
	import type { Lang } from '../data/types';
	import { runBacktest, BT_PRESETS, type BtParamDef, type BtPresetKey, type BtResult } from '../data/backtest';
	import { registerBtIndicators, publishBt, applyBt, clearBt } from './btLayer';
	import { MACRO_SERIES, loadMacroSeries, MACRO_ATTRIBUTION } from '../data/macroSeries';
	import { registerEconIndicator, ECON_INDICATOR, ECON_COLORS, type EconExtend } from './econOverlay';
	import BacktestStrip from './BacktestStrip.svelte';

	interface Props {
		candles: Candle[]; // 초기(현재+직전 연도)
		code: string;
		lang: Lang;
		events?: { date: string; label: string }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
	}
	let { candles, code, lang, events, valBand }: Props = $props();

	// 보조지표 — klinecharts 내장 페인 지표 전종(21) 노출. 키 = klinecharts 지표명 그대로(매핑표 불필요).
	type SubKey = 'VOL' | 'MACD' | 'RSI' | 'KDJ' | 'OBV' | 'CCI' | 'WR' | 'DMI' | 'MTM' | 'ROC' | 'TRIX' | 'PSY' | 'VR' | 'BRAR' | 'BIAS' | 'CR' | 'DMA' | 'EMV' | 'AO' | 'PVT' | 'AVP';
	const SUB_ALL: SubKey[] = ['VOL', 'MACD', 'RSI', 'KDJ', 'OBV', 'CCI', 'WR', 'DMI', 'MTM', 'ROC', 'TRIX', 'PSY', 'VR', 'BRAR', 'BIAS', 'CR', 'DMA', 'EMV', 'AO', 'PVT', 'AVP'];
	// 주가 오버레이 — 다중 토글(candle_pane 스택). klinecharts 내장 6종 전부.
	type OverlayKey = 'MA' | 'EMA' | 'SMA' | 'BOLL' | 'BBI' | 'SAR';
	const OVERLAY_ALL: OverlayKey[] = ['MA', 'EMA', 'SMA', 'BOLL', 'BBI', 'SAR'];
	const DRAW_TOOLS: { name: string; kr: string; en: string }[] = [
		{ name: 'segment', kr: '추세선', en: 'Trend' },
		{ name: 'rayLine', kr: '레이', en: 'Ray' },
		{ name: 'priceLine', kr: '가격선', en: 'Price' },
		{ name: 'horizontalStraightLine', kr: '수평선', en: 'Horiz' },
		{ name: 'verticalStraightLine', kr: '수직선', en: 'Vert' },
		{ name: 'fibonacciLine', kr: '피보나치', en: 'Fib' },
		{ name: 'parallelStraightLine', kr: '평행채널', en: 'Channel' },
		{ name: 'priceChannelLine', kr: '가격채널', en: 'PriceCh' }
	];
	const PERIOD_N: Record<string, number> = { '1M': 22, '3M': 66, '6M': 132, '1Y': 252, '3Y': 750, MAX: 100000 };
	const PERIODS = ['1M', '3M', '6M', '1Y', '3Y', 'MAX'] as const;
	type YMode = 'normal' | 'logarithmic' | 'percentage';
	type CandleStyle = 'candle_solid' | 'area' | 'ohlc';
	const YMODES: { v: YMode; kr: string; en: string }[] = [
		{ v: 'normal', kr: '일반', en: 'Linear' },
		{ v: 'logarithmic', kr: '로그', en: 'Log' },
		{ v: 'percentage', kr: '%', en: '%' }
	];
	const CANDLES: { v: CandleStyle; kr: string; en: string }[] = [
		{ v: 'candle_solid', kr: '캔들', en: 'Candle' },
		{ v: 'area', kr: '라인', en: 'Line' },
		{ v: 'ohlc', kr: '바', en: 'Bar' }
	];

	let el: HTMLDivElement | null = $state(null);
	let chart = $state<any>(null);
	let full = $state(false);
	let yMode = $state<YMode>('normal');
	let candleStyle = $state<CandleStyle>('candle_solid');
	let period = $state<(typeof PERIODS)[number]>('1Y');
	let overlays = $state<OverlayKey[]>(['MA']);
	let subs = $state<SubKey[]>(['VOL', 'RSI']);
	let showEvents = $state(false);
	let showBand = $state(false);
	let magnet = $state(false);
	let menu = $state<'none' | 'ind' | 'draw' | 'view' | 'bt'>('none');

	// 백테스트 — 프리셋 sticky(회사전환에도 유지), 계산 <1ms 동기 (워커·debounce 불필요 실측).
	let btKey = $state<BtPresetKey | null>(null);
	let btParams = $state<Record<string, number>>({});
	let btCosts = $state(true);
	let btResult = $state<BtResult | null>(null);
	// ⛔ 불변식: chart.applyNewData 를 호출하는 모든 지점은 bumpDataRev() 동행 (현재 2곳:
	//    회사전환 데이터 적용 effect + backfillForPeriod). pushTick 은 제외.
	// dataRev++ 직접 사용 금지 — $effect 안 증감은 읽기+쓰기라 self-dep 무한루프(effect_update_depth_exceeded).
	let dataRev = $state(0);
	let dataRevSeq = 0; // 비반응 카운터 — bumpDataRev 는 dataRev 를 쓰기만 한다
	const bumpDataRev = () => (dataRev = ++dataRevSeq);
	let btRunSeq = 0; // 비반응 — calcParams 재계산 트리거용 단조 증가
	const activeBt = $derived(btKey ? (BT_PRESETS.find((d) => d.key === btKey) ?? null) : null);
	function stepParam(pp: BtParamDef, dir: 1 | -1) {
		const cur = btParams[pp.name] ?? pp.def;
		const next = Math.max(pp.min, Math.min(pp.max, cur + dir * pp.step));
		const p = { ...btParams, [pp.name]: next };
		if (btKey === 'maCross' && p.fast != null && p.slow != null && p.fast >= p.slow) return; // 단기 < 장기 강제
		btParams = p;
	}

	// 경제지표 캔들 오버레이 — 최대 3종 (시각·툴팁 밀도 상한, 덕지덕지 방지)
	const ECON_MAX = 3;
	let econ = $state<string[]>([]);
	let econOn = false; // indicator 생성 여부 (비반응)
	let econToken = 0; // stale async 가드
	const toggleEcon = (id: string) => (econ = econ.includes(id) ? econ.filter((x) => x !== id) : econ.length >= ECON_MAX ? econ : [...econ, id]);

	let kc: any = null;
	const subPanes = new Map<SubKey, string>();
	const mainOn = new Set<OverlayKey>();
	let bandIds: string[] = [];
	let eventIds: string[] = [];
	let drawIds: string[] = [];
	// load-more 상태 (비반응 — 콜백이 읽음). oldestYear↔newestYear = 현재 로드된 이력 범위.
	const hist = { code: '', oldestYear: 9999, newestYear: 0, loading: false };

	const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));
	const toK = (c: Candle) => ({ timestamp: toMs(c.t), open: c.o, high: c.h, low: c.l, close: c.c, volume: c.v });
	const toggleSub = (k: SubKey) => (subs = subs.includes(k) ? subs.filter((x) => x !== k) : [...subs, k]);
	const toggleOverlay = (k: OverlayKey) => (overlays = overlays.includes(k) ? overlays.filter((x) => x !== k) : [...overlays, k]);

	const themeStyles = () => ({
		grid: { horizontal: { color: 'rgba(38,46,62,0.45)' }, vertical: { color: 'rgba(38,46,62,0.32)' } },
		candle: {
			type: candleStyle,
			bar: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', upBorderColor: '#34d399', downBorderColor: '#f0616f', noChangeBorderColor: '#8b919e', upWickColor: '#5eead4', downWickColor: '#fb7185', noChangeWickColor: '#8b919e' },
			area: { lineColor: '#5b9bf0', lineSize: 1.4, backgroundColor: [{ offset: 0, color: 'rgba(91,155,240,0.22)' }, { offset: 1, color: 'rgba(91,155,240,0.01)' }] },
			priceMark: { high: { color: '#8b919e' }, low: { color: '#8b919e' }, last: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', text: { color: '#0b0e14' } } },
			tooltip: { offsetTop: 26, text: { color: '#cfd3dc', size: 11 }, rect: { color: 'rgba(14,17,23,0.85)', borderColor: '#222b3a' } }
		},
		indicator: { tooltip: { text: { color: '#8b919e', size: 10 } } },
		xAxis: { axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		yAxis: { type: yMode, axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		separator: { color: '#222b3a', fill: true },
		crosshair: { horizontal: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309' } }, vertical: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309' } } }
	});

	// ── 차트 인스턴스 생성 (mount 1 회, el 기준) ──
	$effect(() => {
		const node = el;
		if (!browser || !node) return;
		let disposed = false;
		let local: any = null;
		(async () => {
			const mod: any = await import('klinecharts');
			if (disposed || !node) return;
			kc = mod;
			registerBtIndicators(mod);
			registerEconIndicator(mod);
			local = mod.init(node, { styles: themeStyles() });
			if (!local) return;
			local.setPriceVolumePrecision(0, 0);
			local.setOffsetRightDistance(12);
			// 전체 이력 lazy 로드 — 좌측(LoadDataType.Forward='forward') 도달 시 더 오래된 연도 prepend
			local.setLoadDataCallback((p: any) => {
				const done = (rows: any[], more: boolean) => { try { p.callback(rows, more); } catch { /* */ } };
				if (p.type !== 'forward' || hist.loading) return done([], hist.oldestYear - 1 >= KRX_MIN_YEAR);
				const next = hist.oldestYear - 1;
				if (next < KRX_MIN_YEAR) return done([], false);
				hist.loading = true;
				wbPrice.older(hist.code, next)
					.then((older) => { hist.oldestYear = next; hist.loading = false; done(older.map(toK), next - 1 >= KRX_MIN_YEAR); })
					.catch(() => { hist.loading = false; done([], false); });
			});
			chart = local;
		})();
		return () => {
			disposed = true;
			if (local && kc) { try { kc.dispose(local); } catch { /* */ } }
			subPanes.clear();
			mainOn.clear();
			econOn = false;
			bandIds = [];
			eventIds = [];
			drawIds = [];
			if (chart === local) chart = null;
		};
	});

	// ── 데이터 적용 (회사전환 = applyNewData, dispose 안 함 = 영속) ──
	$effect(() => {
		const cs = candles;
		const c = chart;
		if (!c || !cs || cs.length === 0) return;
		hist.code = code;
		hist.oldestYear = +cs[0].t.slice(0, 4);
		hist.newestYear = +cs[cs.length - 1].t.slice(0, 4);
		hist.loading = false;
		const hasMore = hist.oldestYear - 1 >= KRX_MIN_YEAR;
		c.applyNewData(cs.map(toK), hasMore);
		bumpDataRev();
		bandIds.forEach((id) => c.removeOverlay(id));
		eventIds.forEach((id) => c.removeOverlay(id));
		drawIds.forEach((id) => c.removeOverlay(id));
		bandIds = [];
		eventIds = [];
		drawIds = [];
		applyPeriodFull(c);
	});

	// 가시 봉 수 재배치 — 현재 로드된 전체 캔들 길이 기준(백필 후 늘어난 길이 반영).
	function applySpacing(c: any) {
		const len = wbPrice.loaded(hist.code).length || candles.length || 1;
		const N = Math.min(PERIOD_N[period] ?? len, len);
		const w = el?.clientWidth || 800;
		try { c.setBarSpace(Math.max(0.5, Math.min(30, w / Math.max(1, N)))); c.scrollToRealTime(0); } catch { /* */ }
	}

	// 기간(특히 3Y/MAX)·줌아웃 시 필요한 과거연도까지 능동 백필 → 전체 재적용 → 재배치.
	// 좌측 드래그(Forward 콜백)에만 의존하지 않아 버튼만으로 전체 이력 도달. hist.loading = Forward 와 공유 mutex.
	const yearsForPeriod = (p: string): number => (p === 'MAX' ? 999 : Math.ceil((PERIOD_N[p] ?? 252) / 252) + 1);
	async function backfillForPeriod(c: any) {
		const code0 = hist.code;
		if (!code0) return;
		const target = period === 'MAX' ? KRX_MIN_YEAR : Math.max(KRX_MIN_YEAR, hist.newestYear - yearsForPeriod(period) + 1);
		let changed = false;
		while (hist.oldestYear > target && !hist.loading) {
			const y = hist.oldestYear - 1;
			if (y < KRX_MIN_YEAR) break;
			hist.loading = true;
			try { await wbPrice.older(code0, y); } catch { hist.loading = false; break; }
			hist.loading = false;
			if (hist.code !== code0 || chart !== c) return; // 회사 전환·차트 교체 → 중단
			hist.oldestYear = y;
			changed = true;
		}
		if (changed && chart === c && hist.code === code0) {
			c.applyNewData(wbPrice.loaded(code0).map(toK), hist.oldestYear - 1 >= KRX_MIN_YEAR);
			bumpDataRev();
			applySpacing(c);
		}
	}

	function applyPeriodFull(c: any) {
		applySpacing(c);
		void backfillForPeriod(c);
	}

	// 메인 오버레이 reconcile (다중 — candle_pane 스택)
	$effect(() => {
		const want = new Set(overlays);
		const c = chart;
		if (!c) return;
		for (const k of [...mainOn]) if (!want.has(k)) { c.removeIndicator('candle_pane', k); mainOn.delete(k); }
		overlays.forEach((k) => {
			if (mainOn.has(k)) return;
			if (c.createIndicator(k, true, { id: 'candle_pane' })) mainOn.add(k);
		});
	});

	// 보조지표 페인 reconcile
	$effect(() => {
		const want = new Set(subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); }
		subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const id = c.createIndicator(k, false, { id: `pane_${k}`, height: 78 });
			if (id) subPanes.set(k, id);
		});
	});

	// 적정주가 밴드 → priceLine 오버레이 (토글)
	$effect(() => {
		const vb = valBand;
		const on = showBand;
		const c = chart;
		if (!c) return;
		bandIds.forEach((id) => c.removeOverlay(id));
		bandIds = [];
		if (on && vb && vb.hi > vb.lo) {
			const mk = (price: number, color: string) => c.createOverlay({ name: 'priceLine', points: [{ value: price }], lock: true, styles: { line: { color, style: 'dashed', size: 1 }, text: { color } } });
			bandIds = [mk(vb.hi, 'rgba(96,165,250,0.5)'), mk(vb.mid, 'rgba(96,165,250,0.85)'), mk(vb.lo, 'rgba(96,165,250,0.5)')].filter(Boolean) as string[];
		}
	});

	// 실적·공시 시점 마커 → simpleAnnotation (토글, 가장 가까운 거래일 스냅)
	$effect(() => {
		const evs = events;
		const on = showEvents;
		const cs = candles;
		const c = chart;
		if (!c || !cs.length) return;
		eventIds.forEach((id) => c.removeOverlay(id));
		eventIds = [];
		if (!on || !evs || !evs.length) return;
		const first = cs[0].t;
		const last = cs[cs.length - 1].t;
		const snap = (d: string) => { let best = cs[0]; let bd = Infinity; for (const k of cs) { const dd = Math.abs(Number(k.t) - Number(d)); if (dd < bd) { bd = dd; best = k; } } return best; };
		const ids: string[] = [];
		for (const ev of evs) {
			if (ev.date < first || ev.date > last) continue;
			const k = snap(ev.date);
			const id = c.createOverlay({ name: 'simpleAnnotation', extendData: ev.label, points: [{ timestamp: toMs(k.t), value: k.h }], styles: { text: { color: '#fb923c', backgroundColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.5)' } } });
			if (id) ids.push(id as string);
		}
		eventIds = ids;
	});

	// Y축 모드 (일반 / 로그 / %)
	$effect(() => {
		const m = yMode;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ yAxis: { type: m } }); } catch { /* */ }
	});

	// 캔들 스타일 (캔들 / 라인 / 바)
	$effect(() => {
		const t = candleStyle;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ candle: { type: t } }); } catch { /* */ }
	});

	// period 변경 → 가시 봉 수 + 필요 시 과거 백필
	$effect(() => {
		void period;
		const c = chart;
		if (c && candles.length) applyPeriodFull(c);
	});

	// 백테스트 — 추가 effect 1개. 의존: 프리셋·파라미터·비용·기간·dataRev(applyNewData 동행).
	// 기간 변경 → 백필 후 dataRev++ 로 늘어난 이력에서 정확히 1회 재실행. 팬/줌·지표 토글 = 재실행 0회.
	$effect(() => {
		const c = chart;
		const key = btKey;
		const p = btParams;
		const wc = btCosts;
		void dataRev;
		void period;
		if (!c) return;
		if (!key) {
			clearBt(c);
			btResult = null;
			return;
		}
		const all = wbPrice.loaded(hist.code);
		if (!all.length) return;
		const win = Math.min(PERIOD_N[period] ?? all.length, all.length);
		const res = runBacktest(all, key, p, { windowBars: win, withCosts: wc });
		btResult = res;
		publishBt(res, all);
		if (res) applyBt(c, ++btRunSeq);
		else clearBt(c);
	});

	// 경제지표 오버레이 — 선택 → 로드 → 생성/override (figures:[] = 캔들 y축 무왜곡, econOverlay.ts)
	$effect(() => {
		const ids = econ;
		const c = chart;
		const lg = lang;
		if (!c) return;
		if (!ids.length) {
			if (econOn) {
				try { c.removeIndicator('candle_pane', ECON_INDICATOR); } catch { /* */ }
				econOn = false;
			}
			return;
		}
		const token = ++econToken;
		Promise.all(ids.map((id) => loadMacroSeries(id))).then((lists) => {
			if (token !== econToken || chart !== c) return; // 선택 변경·인스턴스 교체 → 폐기
			const series = ids
				.map((id, i) => ({ def: MACRO_SERIES.find((s) => s.id === id)!, points: lists[i] ?? [] }))
				.filter((s) => s.points.length);
			const extendData: EconExtend = { lang: lg, series }; // 항상 새 참조 → setExtendData 재계산 보장
			if (econOn) c.overrideIndicator({ name: ECON_INDICATOR, extendData }, 'candle_pane');
			else econOn = !!c.createIndicator({ name: ECON_INDICATOR, extendData }, true, { id: 'candle_pane' });
		});
	});

	// 전체화면 토글 → resize + ESC
	$effect(() => {
		if (!browser) return;
		const c = chart;
		void full;
		requestAnimationFrame(() => { try { c?.resize(); } catch { /* */ } });
		if (!full) return;
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') full = false; };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	function startDraw(name: string) {
		menu = 'none';
		try { const id = chart?.createOverlay({ name, mode: magnet ? 'weak_magnet' : 'normal' }); if (id) drawIds.push(id as string); } catch { /* */ }
	}
	function clearDraw() {
		menu = 'none';
		drawIds.forEach((id) => { try { chart?.removeOverlay(id); } catch { /* */ } });
		drawIds = [];
	}
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	// 실시간 틱 (나중 가격 API 연결 시 호출)
	export function pushTick(c: Candle) { try { chart?.updateData(toK(c)); } catch { /* */ } }
</script>

<svelte:window onclick={() => (menu !== 'none' ? (menu = 'none') : null)} />
<div class="chartWrap" class:full role="img" aria-label="price chart" style={full ? '' : 'height:480px;min-height:360px;'}>
	<div class="chartHost" bind:this={el}></div>

	<!-- 인-차트 툴바: 기간(좌상) -->
	<div class="chartBar">
		{#each PERIODS as p (p)}<button class={period === p ? 'cbtn on' : 'cbtn'} onclick={() => (period = p)}>{p}</button>{/each}
	</div>

	<!-- 인-차트 툴바: 지표·드로잉·표시·전체화면 (우상) -->
	<div class="chartTools" onclick={(e) => e.stopPropagation()}>
		<div class="ctWrap">
			<button class={overlays.length || subs.length || econ.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'ind' ? 'none' : 'ind')} title={T('지표', 'Indicators')}>{T('지표', 'IND')}</button>
			{#if menu === 'ind'}
				<div class="ctMenu ctMenuWide">
					<div class="ctMenuLbl">{T('주가 오버레이 (다중)', 'Price overlay (multi)')}</div>
					<div class="ctRow ctRowWrap">{#each OVERLAY_ALL as o (o)}<button class={overlays.includes(o) ? 'mItem on' : 'mItem'} onclick={() => toggleOverlay(o)}>{o}</button>{/each}</div>
					<div class="ctMenuLbl">{T('보조 지표 (다중)', 'Sub indicators (multi)')}</div>
					<div class="ctRow ctRowWrap">{#each SUB_ALL as k (k)}<button class={subs.includes(k) ? 'mItem on' : 'mItem'} onclick={() => toggleSub(k)}>{k}</button>{/each}</div>
					<div class="ctMenuLbl">{T('경제지표 겹쳐보기 (최대 3 · 자기정규화)', 'Economy overlay (max 3 · self-scaled)')}</div>
					<div class="ctRow ctRowWrap">
						{#each MACRO_SERIES as s (s.id)}
							<button class={econ.includes(s.id) ? 'mItem on' : 'mItem'}
								style={econ.includes(s.id) ? `background:transparent;color:${ECON_COLORS[s.id]};border-color:${ECON_COLORS[s.id]};font-weight:600` : ''}
								onclick={() => toggleEcon(s.id)}>{T(s.kr, s.en)}</button>
						{/each}
					</div>
					{#if overlays.length || subs.length || econ.length}
						<div class="ctRow"><button class="mItem mClear" onclick={() => { overlays = []; subs = []; econ = []; }}>{T('지표 전체 해제', 'Clear all')}</button></div>
					{/if}
				</div>
			{/if}
		</div>
		<div class="ctWrap">
			<button class={drawIds.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'draw' ? 'none' : 'draw')} title={T('그리기', 'Draw')}>{T('그리기', 'DRAW')}</button>
			{#if menu === 'draw'}
				<div class="ctMenu">
					<div class="ctRow ctRowWrap">{#each DRAW_TOOLS as d (d.name)}<button class="mItem" onclick={() => startDraw(d.name)}>{T(d.kr, d.en)}</button>{/each}</div>
					<div class="ctRow"><button class={magnet ? 'mItem on' : 'mItem'} onclick={() => (magnet = !magnet)} title={T('가까운 봉에 스냅', 'snap to bar')}>{T('자석', 'Magnet')}</button><button class="mItem mClear" onclick={clearDraw}>{T('전체 지우기', 'Clear')}</button></div>
				</div>
			{/if}
		</div>
		<div class="ctWrap">
			<button class={candleStyle !== 'candle_solid' || yMode !== 'normal' || showEvents || showBand ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'view' ? 'none' : 'view')} title={T('표시 설정', 'View')}>{T('표시', 'VIEW')}</button>
			{#if menu === 'view'}
				<div class="ctMenu">
					<div class="ctMenuLbl">{T('캔들', 'Candle')}</div>
					<div class="ctRow">{#each CANDLES as cs (cs.v)}<button class={candleStyle === cs.v ? 'mItem on' : 'mItem'} onclick={() => (candleStyle = cs.v)}>{T(cs.kr, cs.en)}</button>{/each}</div>
					<div class="ctMenuLbl">{T('Y축', 'Y axis')}</div>
					<div class="ctRow">{#each YMODES as y (y.v)}<button class={yMode === y.v ? 'mItem on' : 'mItem'} onclick={() => (yMode = y.v)}>{T(y.kr, y.en)}</button>{/each}</div>
					<div class="ctMenuLbl">{T('마커', 'Markers')}</div>
					<div class="ctRow"><button class={showEvents ? 'mItem on' : 'mItem'} onclick={() => (showEvents = !showEvents)}>{T('실적 발표', 'Earnings')}</button><button class={showBand ? 'mItem on' : 'mItem'} disabled={!valBand} onclick={() => valBand && (showBand = !showBand)}>{T('적정주가 밴드', 'Fair band')}</button></div>
				</div>
			{/if}
		</div>
		<div class="ctWrap">
			<button class={btKey ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'bt' ? 'none' : 'bt')} title={T('전략 백테스트', 'Backtest')}>{T('백테스트', 'BT')}</button>
			{#if menu === 'bt'}
				<div class="ctMenu">
					<div class="ctMenuLbl">{T('전략 프리셋 — 클릭 즉시 실행', 'Strategy preset — runs on click')}</div>
					<div class="ctRow ctRowWrap">
						{#each BT_PRESETS as pd (pd.key)}
							<button class={btKey === pd.key ? 'mItem on' : 'mItem'} title={T(pd.descKr, pd.descEn)}
								onclick={() => { btKey = pd.key; btParams = Object.fromEntries(pd.params.map((x) => [x.name, x.def])); }}>{T(pd.kr, pd.en)}</button>
						{/each}
					</div>
					{#if activeBt && activeBt.params.length}
						<div class="ctMenuLbl">{T('파라미터', 'Params')}</div>
						{#each activeBt.params as pp (pp.name)}
							<div class="ctRow btParamRow">
								<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
								<button class="mItem" onclick={() => stepParam(pp, -1)}>−</button>
								<b class="btParamVal mono">{btParams[pp.name] ?? pp.def}</b>
								<button class="mItem" onclick={() => stepParam(pp, 1)}>+</button>
							</div>
						{/each}
					{/if}
					<div class="ctRow">
						<button class={btCosts ? 'mItem on' : 'mItem'} title={T('수수료 0.015%+거래세 0.15%+슬리피지 0.1%', 'fees+tax+slippage')} onclick={() => (btCosts = !btCosts)}>{T('수수료·세금 포함', 'Costs')}</button>
						{#if btKey}<button class="mItem mClear" onclick={() => (btKey = null)}>{T('지우기', 'Clear')}</button>{/if}
					</div>
				</div>
			{/if}
		</div>
		<button class="chartTool" onclick={() => (full = !full)} title={T('전체화면', 'Fullscreen')} aria-label="fullscreen">{full ? '✕' : '⤢'}</button>
	</div>

	<!-- 데이터 출처 상시 표기 (공공누리 출처표시 의무, ECON 활성 시 ECOS·FRED 병기) -->
	<div class="chartSrc">{T('출처: 금융위원회·한국거래소 (공공데이터포털)', 'Source: FSC · KRX (data.go.kr)')}{econ.length ? ' · ' + MACRO_ATTRIBUTION : ''}</div>

	{#if btResult && btKey}
		<BacktestStrip result={btResult} presetLabel={activeBt ? T(activeBt.kr, activeBt.en) : ''} {period} withCosts={btCosts} {lang} onClear={() => (btKey = null)} />
	{/if}
</div>
