<script lang="ts">
	// 전문 증권사급 주가차트 — klinecharts(v9) CORE + 인-차트 툴바(기간·지표·드로잉·로그·전체화면).
	// 전체 이력(2010~) lazy 로드(setLoadMoreDataCallback, 좌측 팬), 차트 인스턴스 영속(회사전환=applyNewData, dispose 안 함).
	// adapter-static·SSR 안전: $effect 안 동적 import + dispose() cleanup. 화면 브랜딩 없음(Apache-2.0).
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

	type SubKey = 'VOL' | 'RSI' | 'MACD' | 'STOCH' | 'OBV';
	const SUB_ALL: SubKey[] = ['VOL', 'RSI', 'MACD', 'STOCH', 'OBV'];
	const SUB_NAME: Record<SubKey, string> = { VOL: 'VOL', RSI: 'RSI', MACD: 'MACD', STOCH: 'KDJ', OBV: 'OBV' };
	const DRAW_TOOLS: { name: string; kr: string; en: string }[] = [
		{ name: 'segment', kr: '추세선', en: 'Trend' },
		{ name: 'priceLine', kr: '가격선', en: 'Price' },
		{ name: 'horizontalStraightLine', kr: '수평선', en: 'Horiz' },
		{ name: 'verticalStraightLine', kr: '수직선', en: 'Vert' },
		{ name: 'fibonacciLine', kr: '피보나치', en: 'Fib' },
		{ name: 'parallelStraightLine', kr: '채널', en: 'Channel' }
	];
	const PERIOD_N: Record<string, number> = { '3M': 66, '6M': 132, '1Y': 252, '3Y': 750, MAX: 100000 };
	const PERIODS = ['3M', '6M', '1Y', '3Y', 'MAX'] as const;

	let el: HTMLDivElement | null = $state(null);
	let chart = $state<any>(null);
	let full = $state(false);
	let logScale = $state(false);
	let period = $state<(typeof PERIODS)[number]>('1Y');
	let overlay = $state<'MA' | 'BB' | 'NONE'>('MA');
	let subs = $state<SubKey[]>(['VOL', 'RSI']);
	let showEvents = $state(false);
	let showBand = $state(false);
	let menu = $state<'none' | 'ind' | 'draw'>('none');

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
			bar: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', upBorderColor: '#34d399', downBorderColor: '#f0616f', noChangeBorderColor: '#8b919e', upWickColor: '#5eead4', downWickColor: '#fb7185', noChangeWickColor: '#8b919e' },
			priceMark: { high: { color: '#8b919e' }, low: { color: '#8b919e' }, last: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', text: { color: '#0b0e14' } } },
			tooltip: { offsetTop: 26, text: { color: '#cfd3dc', size: 11 }, rect: { color: 'rgba(14,17,23,0.85)', borderColor: '#222b3a' } }
		},
		indicator: { tooltip: { text: { color: '#8b919e', size: 10 } } },
		xAxis: { axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		yAxis: { type: logScale ? 'logarithmic' : 'normal', axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
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
		// 회사 바뀌면 회사별 오버레이(밴드·실적·드로잉) 초기화 → 해당 effect 가 다시 채움
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

	// 메인 오버레이 (MA / BOLL)
	$effect(() => {
		const ov = overlay;
		const c = chart;
		if (!c) return;
		if (mainInd) { c.removeIndicator('candle_pane', mainInd); mainInd = null; }
		if (ov === 'MA') mainInd = c.createIndicator('MA', true, { id: 'candle_pane' }) ? 'MA' : null;
		else if (ov === 'BB') mainInd = c.createIndicator('BOLL', true, { id: 'candle_pane' }) ? 'BOLL' : null;
	});

	// 보조지표 페인 reconcile
	$effect(() => {
		const want = new Set(subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); }
		subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const id = c.createIndicator(SUB_NAME[k], false, { id: `pane_${k}`, height: 78 });
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

	// 로그 스케일
	$effect(() => {
		const lg = logScale;
		const c = chart;
		if (!c) return;
		c.setStyles({ yAxis: { type: lg ? 'logarithmic' : 'normal' } });
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
		try { const id = chart?.createOverlay({ name }); if (id) drawIds.push(id as string); } catch { /* */ }
	}
	function clearDraw() {
		menu = 'none';
		drawIds.forEach((id) => { try { chart?.removeOverlay(id); } catch { /* */ } });
		drawIds = [];
	}
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

	<!-- 인-차트 툴바: 지표·드로잉·토글·로그·전체화면 (우상) -->
	<div class="chartTools" onclick={(e) => e.stopPropagation()}>
		<div class="ctWrap">
			<button class={overlay !== 'NONE' || subs.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'ind' ? 'none' : 'ind')} title="지표">{lang === 'en' ? 'IND' : '지표'}</button>
			{#if menu === 'ind'}
				<div class="ctMenu">
					<div class="ctRow">{#each [['MA', 'MA'], ['BB', 'BB'], ['NONE', lang === 'en' ? 'none' : '없음']] as [v, l] (v)}<button class={overlay === v ? 'mItem on' : 'mItem'} onclick={() => (overlay = v as typeof overlay)}>{l}</button>{/each}</div>
					<div class="ctRow">{#each SUB_ALL as k (k)}<button class={subs.includes(k) ? 'mItem on' : 'mItem'} onclick={() => toggleSub(k)}>{k}</button>{/each}</div>
				</div>
			{/if}
		</div>
		<div class="ctWrap">
			<button class={drawIds.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'draw' ? 'none' : 'draw')} title="그리기">{lang === 'en' ? 'DRAW' : '그리기'}</button>
			{#if menu === 'draw'}
				<div class="ctMenu">
					<div class="ctRow ctRowWrap">{#each DRAW_TOOLS as d (d.name)}<button class="mItem" onclick={() => startDraw(d.name)}>{lang === 'en' ? d.en : d.kr}</button>{/each}</div>
					<div class="ctRow"><button class="mItem mClear" onclick={clearDraw}>{lang === 'en' ? 'clear' : '전체 지우기'}</button></div>
				</div>
			{/if}
		</div>
		<button class={showEvents ? 'chartTool on' : 'chartTool'} onclick={() => (showEvents = !showEvents)} title="실적·공시 시점">{lang === 'en' ? 'EARN' : '실적'}</button>
		<button class={showBand ? 'chartTool on' : 'chartTool'} disabled={!valBand} onclick={() => valBand && (showBand = !showBand)} title="적정주가 밴드">{lang === 'en' ? 'FAIR' : '밸류'}</button>
		<button class={logScale ? 'chartTool on' : 'chartTool'} onclick={() => (logScale = !logScale)} title="로그 스케일">LOG</button>
		<button class="chartTool" onclick={() => (full = !full)} title={lang === 'en' ? 'fullscreen' : '전체화면'} aria-label="fullscreen">{full ? '✕' : '⤢'}</button>
	</div>
</div>
