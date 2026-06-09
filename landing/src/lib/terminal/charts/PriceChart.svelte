<script lang="ts">
	// 전문 증권사급 주가차트 — klinecharts(v9) CORE + 인-차트 툴바.
	// klinecharts CORE 는 네이티브 툴바/기간 위젯이 없다(캔버스=차트뿐) — TradingView lightweight-charts·Highcharts stock core 와 동일.
	// 따라서 차트 크롬은 통합 측 자체 구성이 표준. 본 컴포넌트가 기간·지표·드로잉·표시(캔들/축/마커)·전체화면을 제공.
	// 전체 이력(2010~) lazy 로드(setLoadDataCallback, 좌측 팬), 인스턴스 영속(회사전환=applyNewData, dispose 안 함).
	// adapter-static·SSR 안전: $effect 안 동적 import + dispose cleanup. 화면 브랜딩 없음(Apache-2.0).
	import { browser } from '$app/environment';
	import { loadOlderYear, KRX_MIN_YEAR, type Candle } from '../data/priceSeries';
	import type { Lang } from '../data/types';

	interface Props {
		candles: Candle[]; // 초기(현재+직전 연도)
		code: string;
		lang: Lang;
		events?: { date: string; label: string }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
	}
	let { candles, code, lang, events, valBand }: Props = $props();

	type SubKey = 'VOL' | 'RSI' | 'MACD' | 'STOCH' | 'OBV' | 'CCI' | 'WR';
	const SUB_ALL: SubKey[] = ['VOL', 'RSI', 'MACD', 'STOCH', 'OBV', 'CCI', 'WR'];
	const SUB_IND: Record<SubKey, string> = { VOL: 'VOL', RSI: 'RSI', MACD: 'MACD', STOCH: 'KDJ', OBV: 'OBV', CCI: 'CCI', WR: 'WR' };
	const SUB_LABEL: Record<SubKey, string> = { VOL: 'VOL', RSI: 'RSI', MACD: 'MACD', STOCH: 'KDJ', OBV: 'OBV', CCI: 'CCI', WR: 'WR' };
	type OverlayKey = 'MA' | 'EMA' | 'BB' | 'SAR' | 'NONE';
	const OVERLAYS: { k: OverlayKey; ind: string | null; label: string }[] = [
		{ k: 'MA', ind: 'MA', label: 'MA' },
		{ k: 'EMA', ind: 'EMA', label: 'EMA' },
		{ k: 'BB', ind: 'BOLL', label: 'BOLL' },
		{ k: 'SAR', ind: 'SAR', label: 'SAR' },
		{ k: 'NONE', ind: null, label: lang === 'en' ? 'none' : '없음' }
	];
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
	let overlay = $state<OverlayKey>('MA');
	let subs = $state<SubKey[]>(['VOL', 'RSI']);
	let showEvents = $state(false);
	let showBand = $state(false);
	let magnet = $state(false);
	let menu = $state<'none' | 'ind' | 'draw' | 'view'>('none');

	let kc: any = null;
	const subPanes = new Map<SubKey, string>();
	let mainInd: string | null = null;
	let bandIds: string[] = [];
	let eventIds: string[] = [];
	let drawIds: string[] = [];
	// load-more 상태 (비반응 — 콜백이 읽음)
	const hist = { code: '', oldestYear: 9999, loading: false };

	const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));
	const toK = (c: Candle) => ({ timestamp: toMs(c.t), open: c.o, high: c.h, low: c.l, close: c.c, volume: c.v });
	const toggleSub = (k: SubKey) => (subs = subs.includes(k) ? subs.filter((x) => x !== k) : [...subs, k]);

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
				loadOlderYear(hist.code, next)
					.then((older) => { hist.oldestYear = next; hist.loading = false; done(older.map(toK), next - 1 >= KRX_MIN_YEAR); })
					.catch(() => { hist.loading = false; done([], false); });
			});
			chart = local;
		})();
		return () => {
			disposed = true;
			if (local && kc) { try { kc.dispose(local); } catch { /* */ } }
			subPanes.clear();
			mainInd = null;
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
		hist.loading = false;
		const hasMore = hist.oldestYear - 1 >= KRX_MIN_YEAR;
		c.applyNewData(cs.map(toK), hasMore);
		bandIds.forEach((id) => c.removeOverlay(id));
		eventIds.forEach((id) => c.removeOverlay(id));
		drawIds.forEach((id) => c.removeOverlay(id));
		bandIds = [];
		eventIds = [];
		drawIds = [];
		applyPeriod(c);
	});

	function applyPeriod(c: any) {
		const N = Math.min(PERIOD_N[period] ?? candles.length, candles.length);
		const w = el?.clientWidth || 800;
		try { c.setBarSpace(Math.max(0.5, Math.min(30, w / N))); c.scrollToRealTime(0); } catch { /* */ }
	}

	// 메인 오버레이 (MA / EMA / BOLL / SAR)
	$effect(() => {
		const ov = overlay;
		const c = chart;
		if (!c) return;
		if (mainInd) { c.removeIndicator('candle_pane', mainInd); mainInd = null; }
		const def = OVERLAYS.find((o) => o.k === ov);
		if (def?.ind) mainInd = c.createIndicator(def.ind, true, { id: 'candle_pane' }) ? def.ind : null;
	});

	// 보조지표 페인 reconcile
	$effect(() => {
		const want = new Set(subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); }
		subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const id = c.createIndicator(SUB_IND[k], false, { id: `pane_${k}`, height: 78 });
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

	// period 변경 → 가시 봉 수
	$effect(() => {
		void period;
		const c = chart;
		if (c && candles.length) applyPeriod(c);
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
			<button class={overlay !== 'NONE' || subs.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'ind' ? 'none' : 'ind')} title={T('지표', 'Indicators')}>{T('지표', 'IND')}</button>
			{#if menu === 'ind'}
				<div class="ctMenu">
					<div class="ctMenuLbl">{T('주가 오버레이', 'Price overlay')}</div>
					<div class="ctRow ctRowWrap">{#each OVERLAYS as o (o.k)}<button class={overlay === o.k ? 'mItem on' : 'mItem'} onclick={() => (overlay = o.k)}>{o.label}</button>{/each}</div>
					<div class="ctMenuLbl">{T('보조 지표', 'Sub indicators')}</div>
					<div class="ctRow ctRowWrap">{#each SUB_ALL as k (k)}<button class={subs.includes(k) ? 'mItem on' : 'mItem'} onclick={() => toggleSub(k)}>{SUB_LABEL[k]}</button>{/each}</div>
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
		<button class="chartTool" onclick={() => (full = !full)} title={T('전체화면', 'Fullscreen')} aria-label="fullscreen">{full ? '✕' : '⤢'}</button>
	</div>
</div>
