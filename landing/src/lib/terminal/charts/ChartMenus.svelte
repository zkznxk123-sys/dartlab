<script lang="ts">
	// 일반(비전체화면) 모드 차트 크롬 — 기간 칩(좌상) + 드롭다운 4개(지표·그리기·표시·백테스트) + 전체화면.
	// 상태는 ChartCtl 단일 SSOT 공유 — 전체화면 리본(ChartRibbon)과 같은 인스턴스.
	import type { Lang } from '../data/types';
	import { type ChartCtl, OVERLAY_ALL, SUB_ALL, PERIODS, YMODES, CANDLES, DRAW_TOOLS, SUB_HINT, OVERLAY_HINT } from './chartState.svelte';
	import { MACRO_SERIES } from '../data/macroSeries';
	import { ECON_COLORS } from './econOverlay';
	import { IND_DEFS, paramSummary } from './indicatorParams';
	import IndParamEditor from './IndParamEditor.svelte';
	import BtConfig from './BtConfig.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		hasBand: boolean;
		onDraw: (name: string) => void;
		onClearDraw: () => void;
	}
	let { ctl, lang, hasBand, onDraw, onClearDraw }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	let menu = $state<'none' | 'ind' | 'draw' | 'view' | 'bt'>('none');
	let editing = $state<string | null>(null); // IND 메뉴 내 인라인 파라미터 편집 대상
	const hasParams = (k: string) => (IND_DEFS[k]?.params.length ?? 0) > 0;
	$effect(() => {
		if (menu !== 'ind') editing = null;
	});
</script>

<svelte:window onclick={() => (menu !== 'none' ? (menu = 'none') : null)} />

<!-- 기간 (좌상) -->
<div class="chartBar">
	{#each PERIODS as p (p)}<button class={ctl.period === p ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.period = p)}>{p}</button>{/each}
</div>

<!-- 우상 도구 -->
<div class="chartTools" onclick={(e) => e.stopPropagation()}>
	<div class="ctWrap">
		<button class={ctl.overlays.length || ctl.subs.length || ctl.econ.length ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'ind' ? 'none' : 'ind')} title={T('지표', 'Indicators')}>{T('지표', 'IND')}</button>
		{#if menu === 'ind'}
			<div class="ctMenu ctMenuWide">
				<div class="ctMenuLbl">{T('주가 오버레이 (다중)', 'Price overlay (multi)')}</div>
				<div class="ctRow ctRowWrap">
					{#each OVERLAY_ALL as o (o)}
						{@const on = ctl.overlays.includes(o)}
						<button class={on ? 'mItem on' : 'mItem'} title={OVERLAY_HINT[o] ?? ''} onclick={() => ctl.toggleOverlay(o)}>{o}</button>
						{#if on && hasParams(o)}<button class="mItem mGear" title={T('파라미터', 'params')} onclick={() => (editing = editing === o ? null : o)}>⚙</button>{/if}
					{/each}
				</div>
				<div class="ctMenuLbl">{T('보조 지표 (다중)', 'Sub indicators (multi)')}</div>
				<div class="ctRow ctRowWrap">
					{#each SUB_ALL as k (k)}
						{@const on = ctl.subs.includes(k)}
						<button class={on ? 'mItem on' : 'mItem'} title={SUB_HINT[k] ?? ''} onclick={() => ctl.toggleSub(k)}>{k}</button>
						{#if on && hasParams(k)}<button class="mItem mGear" title={T('파라미터', 'params')} onclick={() => (editing = editing === k ? null : k)}>⚙</button>{/if}
					{/each}
				</div>
				{#if editing}
					<IndParamEditor {ctl} {lang} name={editing} />
				{/if}
				<div class="ctMenuLbl">{T('경제지표 겹쳐보기 (최대 3 · 자기정규화)', 'Economy overlay (max 3 · self-scaled)')}</div>
				<div class="ctRow ctRowWrap">
					{#each MACRO_SERIES as s (s.id)}
						<button class={ctl.econ.includes(s.id) ? 'mItem on' : 'mItem'}
							style={ctl.econ.includes(s.id) ? `background:transparent;color:${ECON_COLORS[s.id]};border-color:${ECON_COLORS[s.id]};font-weight:600` : ''}
							onclick={() => ctl.toggleEcon(s.id)}>{T(s.kr, s.en)}</button>
					{/each}
				</div>
				{#if ctl.overlays.length || ctl.subs.length || ctl.econ.length}
					<div class="ctRow"><button class="mItem mClear" onclick={() => ctl.clearAllIndicators()}>{T('지표 전체 해제', 'Clear all')}</button></div>
				{/if}
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.drawCount ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'draw' ? 'none' : 'draw')} title={T('그리기', 'Draw')}>{T('그리기', 'DRAW')}</button>
		{#if menu === 'draw'}
			<div class="ctMenu">
				<div class="ctRow ctRowWrap">{#each DRAW_TOOLS as d (d.name)}<button class="mItem" onclick={() => { menu = 'none'; onDraw(d.name); }}>{T(d.kr, d.en)}</button>{/each}</div>
				<div class="ctRow"><button class={ctl.magnet ? 'mItem on' : 'mItem'} onclick={() => (ctl.magnet = !ctl.magnet)} title={T('가까운 봉에 스냅', 'snap to bar')}>{T('자석', 'Magnet')}</button><button class="mItem mClear" onclick={() => { menu = 'none'; onClearDraw(); }}>{T('전체 지우기', 'Clear')}</button></div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.candleStyle !== 'candle_solid' || ctl.yMode !== 'normal' || ctl.showEvents || ctl.showBand ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'view' ? 'none' : 'view')} title={T('표시 설정', 'View')}>{T('표시', 'VIEW')}</button>
		{#if menu === 'view'}
			<div class="ctMenu">
				<div class="ctMenuLbl">{T('캔들', 'Candle')}</div>
				<div class="ctRow">{#each CANDLES as cs (cs.v)}<button class={ctl.candleStyle === cs.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.candleStyle = cs.v)}>{T(cs.kr, cs.en)}</button>{/each}</div>
				<div class="ctMenuLbl">{T('Y축', 'Y axis')}</div>
				<div class="ctRow">{#each YMODES as y (y.v)}<button class={ctl.yMode === y.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.yMode = y.v)}>{T(y.kr, y.en)}</button>{/each}</div>
				<div class="ctMenuLbl">{T('마커', 'Markers')}</div>
				<div class="ctRow"><button class={ctl.showEvents ? 'mItem on' : 'mItem'} onclick={() => (ctl.showEvents = !ctl.showEvents)}>{T('실적 발표', 'Earnings')}</button><button class={ctl.showBand ? 'mItem on' : 'mItem'} disabled={!hasBand} onclick={() => hasBand && (ctl.showBand = !ctl.showBand)}>{T('적정주가 밴드', 'Fair band')}</button></div>
			</div>
		{/if}
	</div>
	<div class="ctWrap">
		<button class={ctl.btKey ? 'chartTool on' : 'chartTool'} onclick={() => (menu = menu === 'bt' ? 'none' : 'bt')} title={T('전략 백테스트', 'Backtest')}>{T('백테스트', 'BT')}</button>
		{#if menu === 'bt'}
			<div class="ctMenu"><BtConfig {ctl} {lang} /></div>
		{/if}
	</div>
	<button class="chartTool" onclick={() => (ctl.full = true)} title={T('전체화면', 'Fullscreen')} aria-label="fullscreen">⤢</button>
</div>
