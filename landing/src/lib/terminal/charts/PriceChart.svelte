<script lang="ts">
	// 트레이딩뷰급 주가차트 — klinecharts(v9) 본체. 캔들 + 내장 지표(VOL/RSI/MACD/KDJ/OBV/MA/BOLL),
	// 네이티브 줌·팬·크로스헤어·로그스케일 + 전체화면 + 실시간 updateData 경로.
	// adapter-static·SSR 안전: $effect 안 동적 import + dispose() cleanup (콘솔 0). 화면 브랜딩 없음(Apache-2.0).
	import { browser } from '$app/environment';
	import type { Candle } from '../data/priceSeries';
	import type { Lang } from '../data/types';

	export type SubKey = 'VOL' | 'RSI' | 'MACD' | 'STOCH' | 'OBV';
	interface Props {
		candles: Candle[];
		lang: Lang;
		period: '3M' | '5M' | '6M' | '1Y' | 'MAX';
		overlay: 'MA' | 'BB' | 'NONE';
		subs: SubKey[]; // 동시 표시 보조지표 페인 (스택)
		events?: { date: string; label: string }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
	}
	let { candles, lang, period, overlay, subs, events, valBand }: Props = $props();

	let el: HTMLDivElement | null = $state(null);
	let chart = $state<any>(null);
	let full = $state(false); // 전체화면 오버레이
	let logScale = $state(false); // 로그 스케일

	// klinecharts 모듈·상태 보관 (비반응 — effect 가 mutate)
	let kc: any = null;
	const subPanes = new Map<SubKey, string>(); // 활성 보조지표 → paneId
	let mainInd: string | null = null; // 메인 오버레이 (MA/BOLL)
	let bandIds: string[] = [];
	let eventIds: string[] = [];

	const SUB_NAME: Record<SubKey, string> = { VOL: 'VOL', RSI: 'RSI', MACD: 'MACD', STOCH: 'KDJ', OBV: 'OBV' };
	const PERIOD_N: Record<string, number> = { '3M': 66, '5M': 110, '6M': 132, '1Y': 252, MAX: 100000 };
	const SUBH = 78;
	const wrapH = $derived(360 + subs.length * SUBH);

	const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));
	const toK = (c: Candle) => ({ timestamp: toMs(c.t), open: c.o, high: c.h, low: c.l, close: c.c, volume: c.v });

	const themeStyles = () => ({
		grid: { horizontal: { color: 'rgba(38,46,62,0.45)' }, vertical: { color: 'rgba(38,46,62,0.32)' } },
		candle: {
			bar: {
				upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e',
				upBorderColor: '#34d399', downBorderColor: '#f0616f', noChangeBorderColor: '#8b919e',
				upWickColor: '#5eead4', downWickColor: '#fb7185', noChangeWickColor: '#8b919e'
			},
			priceMark: {
				high: { color: '#8b919e' }, low: { color: '#8b919e' },
				last: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', text: { color: '#0b0e14' } }
			},
			tooltip: { text: { color: '#cfd3dc', size: 11 }, rect: { color: 'rgba(14,17,23,0.85)', borderColor: '#222b3a' } }
		},
		indicator: { tooltip: { text: { color: '#8b919e', size: 10 } } },
		xAxis: { axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		yAxis: { type: logScale ? 'logarithmic' : 'normal', axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		separator: { color: '#222b3a', fill: true },
		crosshair: {
			horizontal: { line: { color: 'rgba(251,146,60,0.5)' }, text: { backgroundColor: '#b45309' } },
			vertical: { line: { color: 'rgba(251,146,60,0.5)' }, text: { backgroundColor: '#b45309' } }
		}
	});

	// ── 초기화: 회사(candles) 변경 시에만 재생성 (줌 상태 보존 위해 토글은 별 effect) ──
	$effect(() => {
		const cs = candles;
		void lang;
		if (!browser || !el || !cs || cs.length === 0) return;
		let disposed = false;
		let local: any = null;
		(async () => {
			const mod: any = await import('klinecharts');
			if (disposed || !el) return;
			kc = mod;
			local = mod.init(el, { styles: themeStyles() });
			if (!local) return;
			local.setPriceVolumePrecision(0, 0);
			local.setOffsetRightDistance(8);
			local.applyNewData(cs.map(toK));
			subPanes.clear();
			mainInd = null;
			bandIds = [];
			eventIds = [];
			chart = local; // → 토글 effect 들이 현재 상태로 채워 넣음
		})();
		return () => {
			disposed = true;
			if (local && kc) { try { kc.dispose(local); } catch { /* already */ } }
			subPanes.clear();
			mainInd = null;
			bandIds = [];
			eventIds = [];
			if (chart === local) chart = null;
		};
	});

	// 메인 오버레이 (MA / BOLL / 없음)
	$effect(() => {
		const ov = overlay;
		const c = chart;
		if (!c) return;
		if (mainInd) { c.removeIndicator('candle_pane', mainInd); mainInd = null; }
		if (ov === 'MA') mainInd = c.createIndicator('MA', true, { id: 'candle_pane' }) ? 'MA' : null;
		else if (ov === 'BB') mainInd = c.createIndicator('BOLL', true, { id: 'candle_pane' }) ? 'BOLL' : null;
	});

	// 보조지표 페인 reconcile (추가/제거만)
	$effect(() => {
		const want = new Set(subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) {
			if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); }
		}
		subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const id = c.createIndicator(SUB_NAME[k], false, { id: `pane_${k}`, height: SUBH });
			if (id) subPanes.set(k, id);
		});
	});

	// 적정주가 밴드 → priceLine 오버레이
	$effect(() => {
		const vb = valBand;
		const c = chart;
		if (!c) return;
		bandIds.forEach((id) => c.removeOverlay(id));
		bandIds = [];
		if (vb && vb.hi > vb.lo) {
			const mk = (price: number, color: string, dash: boolean) =>
				c.createOverlay({ name: 'priceLine', points: [{ value: price }], lock: true, styles: { line: { color, style: dash ? 'dashed' : 'solid', size: 1 }, text: { color } } });
			const fair = lang === 'en' ? 'fair' : '적정';
			void fair;
			bandIds = [mk(vb.hi, 'rgba(96,165,250,0.5)', true), mk(vb.mid, 'rgba(96,165,250,0.85)', true), mk(vb.lo, 'rgba(96,165,250,0.5)', true)].filter(Boolean) as string[];
		}
	});

	// 실적·공시 시점 마커 → simpleAnnotation (가장 가까운 거래일 스냅)
	$effect(() => {
		const evs = events;
		const cs = candles;
		const c = chart;
		if (!c || !cs.length) return;
		eventIds.forEach((id) => c.removeOverlay(id));
		eventIds = [];
		if (!evs || !evs.length) return;
		const first = cs[0].t;
		const last = cs[cs.length - 1].t;
		const snap = (d: string) => {
			let best = cs[0];
			let bd = Infinity;
			for (const k of cs) { const dd = Math.abs(Number(k.t) - Number(d)); if (dd < bd) { bd = dd; best = k; } }
			return best;
		};
		const ids: string[] = [];
		for (const ev of evs) {
			if (ev.date < first || ev.date > last) continue;
			const k = snap(ev.date);
			const id = c.createOverlay({
				name: 'simpleAnnotation', extendData: ev.label,
				points: [{ timestamp: toMs(k.t), value: k.h }],
				styles: { text: { color: '#fb923c', backgroundColor: 'rgba(251,146,60,0.12)', borderColor: 'rgba(251,146,60,0.5)' } }
			});
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

	// period → 가시 봉 수 (네이티브 줌/팬 유지)
	$effect(() => {
		const p = period;
		const c = chart;
		if (!c || !el || !candles.length) return;
		const N = Math.min(PERIOD_N[p] ?? candles.length, candles.length);
		const w = el.clientWidth || 800;
		const space = Math.max(1, Math.min(30, w / N));
		try { c.setBarSpace(space); c.scrollToRealTime(0); } catch { /* race */ }
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

	// 실시간 틱 증분 갱신 — 나중 가격 API 연결 시 호출 (마지막 캔들만 갱신/추가)
	export function pushTick(c: Candle) {
		try { chart?.updateData(toK(c)); } catch { /* */ }
	}
</script>

<div class="chartWrap" class:full role="img" aria-label="price chart" style={full ? '' : `height:${wrapH}px;min-height:320px;`}>
	<div class="chartHost" bind:this={el}></div>
	<div class="chartTools">
		<button class={logScale ? 'chartTool on' : 'chartTool'} onclick={() => (logScale = !logScale)} title={lang === 'en' ? 'log scale' : '로그 스케일'}>LOG</button>
		<button class="chartTool" onclick={() => (full = !full)} title={lang === 'en' ? 'fullscreen' : '전체화면'} aria-label="fullscreen">{full ? '✕' : '⤢'}</button>
	</div>
</div>
