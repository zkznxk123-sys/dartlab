<script lang="ts">
	// 전문 증권사급 주가차트 — klinecharts(v9) CORE. 차트 크롬은 모드별 컴포넌트로 분리:
	//   일반 = ChartMenus(칩+드롭다운) / 전체화면 = ChartRibbon(2단 전문 리본). 상태는 ChartCtl 단일 SSOT.
	// 본 컴포넌트 = 차트 인스턴스 수명주기 + 데이터(lazy 백필) + 상태→차트 반영 effect 들만.
	// 전체 이력(2010~) lazy 로드, 인스턴스 영속(회사전환=applyNewData, dispose 안 함). SSR 안전.
	import { browser } from '$app/environment';
	import { KRX_MIN_YEAR, type Candle } from '../data/priceSeries';
	import { price as wbPrice } from '../data/workbench';
	import type { Lang } from '../data/types';
	import { runBacktest, type BtResult } from '../data/backtest';
	import { registerBtIndicators, publishBt, applyBt, clearBt } from './btLayer';
	import { MACRO_SERIES, loadMacroSeries, MACRO_ATTRIBUTION } from '../data/macroSeries';
	import { registerEconIndicator, ECON_INDICATOR, type EconExtend } from './econOverlay';
	import { registerExtraIndicators } from './extraIndicators';
	import { ChartCtl, PERIOD_N, type OverlayKey, type SubKey } from './chartState.svelte';
	import { IND_DEFS } from './indicatorParams';
	import ChartMenus from './ChartMenus.svelte';
	import ChartRibbon from './ChartRibbon.svelte';
	import BacktestStrip from './BacktestStrip.svelte';

	interface Props {
		candles: Candle[]; // 초기(현재+직전 연도)
		code: string;
		name?: string;
		lang: Lang;
		events?: { date: string; label: string }[];
		valBand?: { lo: number; mid: number; hi: number } | null;
	}
	let { candles, code, name = '', lang, events, valBand }: Props = $props();

	const ctl = new ChartCtl();
	let el: HTMLDivElement | null = $state(null);
	let chart = $state<any>(null);
	let btResult = $state<BtResult | null>(null);
	// ⛔ 불변식: chart.applyNewData 를 호출하는 모든 지점은 bumpDataRev() 동행 (현재 2곳:
	//    회사전환 데이터 적용 effect + backfillForPeriod). pushTick 은 제외.
	// dataRev++ 직접 사용 금지 — $effect 안 증감은 읽기+쓰기라 self-dep 무한루프(effect_update_depth_exceeded).
	let dataRev = $state(0);
	let dataRevSeq = 0;
	const bumpDataRev = () => (dataRev = ++dataRevSeq);
	let btRunSeq = 0; // 비반응 — BT calcParams 재계산 트리거용 단조 증가
	let econOn = false; // ECON indicator 생성 여부 (비반응)
	let econToken = 0; // stale async 가드

	let kc: any = null;
	const subPanes = new Map<SubKey, string>();
	const mainOn = new Set<OverlayKey>();
	const appliedParams: Record<string, number[]> = {}; // indParams diff 스냅샷 (비반응)
	let bandIds: string[] = [];
	let eventIds: string[] = [];
	let drawIds: string[] = [];
	// load-more 상태 (비반응 — 콜백이 읽음). oldestYear↔newestYear = 현재 로드된 이력 범위.
	const hist = { code: '', oldestYear: 9999, newestYear: 0, loading: false };

	const toMs = (t: string) => Date.UTC(+t.slice(0, 4), +t.slice(4, 6) - 1, +t.slice(6, 8));
	const toK = (c: Candle) => ({ timestamp: toMs(c.t), open: c.o, high: c.h, low: c.l, close: c.c, volume: c.v });
	const chgPct = $derived.by<number | null>(() => {
		const n = candles.length;
		return n >= 2 && candles[n - 2].c ? ((candles[n - 1].c / candles[n - 2].c) - 1) * 100 : null;
	});

	// 캔들 툴팁 — 한국어 압축형 + 등락률({change} 내장 placeholder, 전일종가 대비 자동색).
	// 배열은 wholesale 교체(라이브러리 명시 특례) — 기본 6줄을 우리 줄로 완전 대체.
	const tooltipCustom = (lg: Lang) =>
		lg === 'en'
			? [
					{ title: 'O', value: '{open}' }, { title: 'H', value: '{high}' }, { title: 'L', value: '{low}' },
					{ title: 'C', value: '{close}' }, { title: 'Vol', value: '{volume}' }, { title: 'Chg', value: '{change}' }
				]
			: [
					{ title: '시', value: '{open}' }, { title: '고', value: '{high}' }, { title: '저', value: '{low}' },
					{ title: '종', value: '{close}' }, { title: '량', value: '{volume}' }, { title: '등락', value: '{change}' }
				];
	const themeStyles = () => ({
		grid: { horizontal: { color: 'rgba(48,58,78,0.55)' }, vertical: { color: 'rgba(38,46,62,0.3)' } },
		candle: {
			type: ctl.candleStyle,
			bar: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', upBorderColor: '#34d399', downBorderColor: '#f0616f', noChangeBorderColor: '#8b919e', upWickColor: '#5eead4', downWickColor: '#fb7185', noChangeWickColor: '#8b919e' },
			area: { lineColor: '#5b9bf0', lineSize: 1.4, backgroundColor: [{ offset: 0, color: 'rgba(91,155,240,0.22)' }, { offset: 1, color: 'rgba(91,155,240,0.01)' }] },
			priceMark: { high: { color: '#8b919e' }, low: { color: '#8b919e' }, last: { upColor: '#34d399', downColor: '#f0616f', noChangeColor: '#8b919e', text: { color: '#0b0e14' } } },
			tooltip: { offsetTop: 26, custom: tooltipCustom(lang), text: { color: '#cfd3dc', size: 11 }, rect: { color: 'rgba(14,17,23,0.85)', borderColor: '#222b3a' } }
		},
		indicator: { tooltip: { text: { color: '#8b919e', size: 10 } } },
		xAxis: { axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		yAxis: { type: ctl.yMode, axisLine: { color: '#222b3a' }, tickLine: { color: '#222b3a' }, tickText: { color: '#8b919e' } },
		separator: { color: '#222b3a', fill: true, activeBackgroundColor: 'rgba(251,146,60,0.1)' },
		crosshair: { horizontal: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309' } }, vertical: { line: { color: 'rgba(251,146,60,0.45)' }, text: { backgroundColor: '#b45309' } } }
	});

	// 보조 페인 높이 — 컨테이너 비례(16%) 적응. 전체화면 진입 시 78px 고정 납작 페인 방지.
	function subPaneHeight(): number {
		const h = el?.clientHeight || 480;
		return Math.max(72, Math.min(240, Math.round(h * 0.16)));
	}

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
			registerExtraIndicators(mod);
			local = mod.init(node, { styles: themeStyles() });
			if (!local) return;
			local.setPriceVolumePrecision(0, 0);
			local.setOffsetRightDistance(12);
			// 일봉 날짜 포맷 — 기본 'YYYY-MM-DD HH:mm' 하드코딩이 일봉에 09:00 같은 무의미 시각 노출.
			// Tooltip(0)·Crosshair(1) 만 날짜로, XAxis 등은 라이브러리 기본 유지.
			const fmtYmd = (ts: number) => {
				const d = new Date(ts);
				const p = (n: number) => String(n).padStart(2, '0');
				return `${d.getUTCFullYear()}-${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())}`;
			};
			try {
				local.setCustomApi({
					formatDate: (dtf: unknown, ts: number, format: string, type: number) => {
						if (type === 0 || type === 1) return fmtYmd(ts);
						try { return mod.utils.formatDate(dtf, ts, format); } catch { return fmtYmd(ts); }
					}
				});
			} catch { /* setCustomApi 미지원 빌드 — 기본 포맷 유지 */ }
			// 전체 이력 lazy 로드 — 좌측(forward) 도달 시 더 오래된 연도 prepend
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
			for (const k of Object.keys(appliedParams)) delete appliedParams[k];
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
		ctl.drawCount = 0;
		applyPeriodFull(c);
	});

	// 가시 봉 수 재배치 — 현재 로드된 전체 캔들 길이 기준(백필 후 늘어난 길이 반영).
	function applySpacing(c: any) {
		const len = wbPrice.loaded(hist.code).length || candles.length || 1;
		const N = Math.min(PERIOD_N[ctl.period] ?? len, len);
		const w = el?.clientWidth || 800;
		try { c.setBarSpace(Math.max(0.5, Math.min(30, w / Math.max(1, N)))); c.scrollToRealTime(0); } catch { /* */ }
	}

	// 기간(특히 3Y/MAX)·줌아웃 시 필요한 과거연도까지 능동 백필 → 전체 재적용 → 재배치.
	const yearsForPeriod = (p: string): number => (p === 'MAX' ? 999 : Math.ceil((PERIOD_N[p] ?? 252) / 252) + 1);
	async function backfillForPeriod(c: any) {
		const code0 = hist.code;
		if (!code0) return;
		const target = ctl.period === 'MAX' ? KRX_MIN_YEAR : Math.max(KRX_MIN_YEAR, hist.newestYear - yearsForPeriod(ctl.period) + 1);
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

	// 메인 오버레이 reconcile (다중 — candle_pane 스택). ICHI 활성 시 선행스팬용 우측 여백 확보.
	$effect(() => {
		const want = new Set(ctl.overlays);
		const c = chart;
		if (!c) return;
		for (const k of [...mainOn]) if (!want.has(k)) { c.removeIndicator('candle_pane', k); mainOn.delete(k); delete appliedParams[k]; }
		ctl.overlays.forEach((k) => {
			if (mainOn.has(k)) return;
			// 커스텀 없으면 IND_DEFS 기본 명시 전달 — RSI 14 등 전문가 표준 교정값 적용
			const cp = ctl.indParams[k] ?? (IND_DEFS[k]?.defaults.length ? IND_DEFS[k].defaults : undefined);
			if (c.createIndicator(cp ? { name: k, calcParams: cp } : k, true, { id: 'candle_pane' })) {
				mainOn.add(k);
				if (cp) appliedParams[k] = cp;
			}
		});
		try {
			if (want.has('ICHI')) c.setOffsetRightDistance(Math.max(12, Math.ceil((ctl.indParams.ICHI?.[1] ?? 26) * c.getBarSpace())));
			else c.setOffsetRightDistance(12);
		} catch { /* */ }
	});

	// 보조지표 페인 reconcile
	$effect(() => {
		const want = new Set(ctl.subs);
		const c = chart;
		if (!c) return;
		for (const [k, paneId] of [...subPanes]) if (!want.has(k)) { c.removeIndicator(paneId); subPanes.delete(k); delete appliedParams[k]; }
		ctl.subs.forEach((k) => {
			if (subPanes.has(k)) return;
			const cp = ctl.indParams[k] ?? (IND_DEFS[k]?.defaults.length ? IND_DEFS[k].defaults : undefined);
			const id = c.createIndicator(cp ? { name: k, calcParams: cp } : k, false, { id: `pane_${k}`, height: subPaneHeight(), minHeight: 48, dragEnabled: true });
			if (id) {
				subPanes.set(k, id);
				if (cp) appliedParams[k] = cp;
			}
		});
	});

	// 지표 파라미터 적용 — appliedParams 스냅샷과 diff, 변경분만 overrideIndicator.
	// ⚠ override 에 minValue/maxValue 절대 전달 금지 (klinecharts 내부 오배선 — calcParams 만).
	$effect(() => {
		const ip = ctl.indParams;
		const c = chart;
		if (!c) return;
		const names = new Set([...Object.keys(ip), ...Object.keys(appliedParams)]);
		for (const k of names) {
			const next = ip[k] ?? IND_DEFS[k]?.defaults;
			const prev = appliedParams[k];
			if (!next || (prev && prev.length === next.length && prev.every((v, i) => v === next[i]))) continue;
			const paneId = mainOn.has(k as OverlayKey) ? 'candle_pane' : subPanes.get(k as SubKey);
			if (!paneId) continue;
			try { c.overrideIndicator({ name: k, calcParams: next }, paneId); } catch { /* */ }
			if (ip[k]) appliedParams[k] = next;
			else delete appliedParams[k];
			if (k === 'ICHI') { try { c.setOffsetRightDistance(Math.max(12, Math.ceil((next[1] ?? 26) * c.getBarSpace()))); } catch { /* */ } }
		}
	});

	// 적정주가 밴드 → priceLine 오버레이 (토글)
	$effect(() => {
		const vb = valBand;
		const on = ctl.showBand;
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
		const on = ctl.showEvents;
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

	// Y축 모드 / 캔들 스타일
	$effect(() => {
		const m = ctl.yMode;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ yAxis: { type: m } }); } catch { /* */ }
	});
	$effect(() => {
		const t = ctl.candleStyle;
		const lg = lang;
		const c = chart;
		if (!c) return;
		try { c.setStyles({ candle: { type: t, tooltip: { custom: tooltipCustom(lg) } } }); } catch { /* */ }
	});

	// period 변경 → 가시 봉 수 + 필요 시 과거 백필
	$effect(() => {
		void ctl.period;
		const c = chart;
		if (c && candles.length) applyPeriodFull(c);
	});

	// 백테스트 — 의존: 프리셋·파라미터·비용(토글+bp)·기간·dataRev(applyNewData 동행).
	$effect(() => {
		const c = chart;
		const key = ctl.btKey;
		const p = ctl.btParams;
		const wc = ctl.btCosts;
		const bp = ctl.btCostsBp;
		void dataRev;
		void ctl.period;
		if (!c) return;
		if (!key) {
			clearBt(c);
			btResult = null;
			return;
		}
		const all = wbPrice.loaded(hist.code);
		if (!all.length) return;
		const win = Math.min(PERIOD_N[ctl.period] ?? all.length, all.length);
		const res = runBacktest(all, key, p, { windowBars: win, withCosts: wc, costsBp: bp });
		btResult = res;
		publishBt(res, all);
		if (res) applyBt(c, ++btRunSeq);
		else clearBt(c);
	});

	// 경제지표 오버레이 — 선택 → 로드 → 생성/override (figures:[] = 캔들 y축 무왜곡, econOverlay.ts)
	$effect(() => {
		const ids = ctl.econ;
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

	// 전체화면 토글 → resize + 보조 페인 비례 재배분 + ESC
	$effect(() => {
		if (!browser) return;
		const c = chart;
		void ctl.full;
		requestAnimationFrame(() => {
			try {
				c?.resize();
				const ph = subPaneHeight();
				for (const paneId of subPanes.values()) c?.setPaneOptions({ id: paneId, height: ph });
			} catch { /* */ }
		});
		if (!ctl.full) return;
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') ctl.full = false; };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	function startDraw(toolName: string) {
		try {
			const id = chart?.createOverlay({ name: toolName, mode: ctl.magnet ? 'weak_magnet' : 'normal' });
			if (id) { drawIds.push(id as string); ctl.drawCount = drawIds.length; }
		} catch { /* */ }
	}
	function clearDraw() {
		drawIds.forEach((id) => { try { chart?.removeOverlay(id); } catch { /* */ } });
		drawIds = [];
		ctl.drawCount = 0;
	}
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	// 실시간 틱 (나중 가격 API 연결 시 호출)
	export function pushTick(c: Candle) { try { chart?.updateData(toK(c)); } catch { /* */ } }
</script>

<div class="chartWrap" class:full={ctl.full} role="img" aria-label="price chart" style={ctl.full ? '' : 'height:480px;min-height:360px;'}>
	<div class="chartHost" bind:this={el}></div>

	{#if ctl.full}
		<ChartRibbon {ctl} {lang} hasBand={!!valBand} {name} {code} {chgPct} onDraw={startDraw} onClearDraw={clearDraw} />
	{:else}
		<ChartMenus {ctl} {lang} hasBand={!!valBand} onDraw={startDraw} onClearDraw={clearDraw} />
	{/if}

	<!-- 데이터 출처 상시 표기 (공공누리 출처표시 의무, ECON 활성 시 ECOS·FRED 병기) -->
	<div class="chartSrc">{T('출처: 금융위원회·한국거래소 (공공데이터포털)', 'Source: FSC · KRX (data.go.kr)')}{ctl.econ.length ? ' · ' + MACRO_ATTRIBUTION : ''}</div>

	{#if btResult && ctl.btKey}
		<BacktestStrip result={btResult} presetLabel={ctl.activeBt ? T(ctl.activeBt.kr, ctl.activeBt.en) : ''} period={ctl.period} withCosts={ctl.btCosts} {lang} onClear={() => (ctl.btKey = null)} />
	{/if}
</div>
