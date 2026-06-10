<script lang="ts">
	// 전체화면 전문가 리본 (증권사 HTS 상단 툴바 표준) — 2단 상시 노출.
	// Row1 = 보는 방법(종목·기간·캔들·축·마커·ECON), Row2 = 분석 작업대(오버레이/페인 활성 칩+카탈로그·그리기·BT).
	// 상태 = ChartCtl 단일 SSOT (일반 메뉴와 공유 — 리본에서 켠 지표가 일반 메뉴에도 켜져 있다).
	import type { Lang } from '../data/types';
	import { type ChartCtl, type OverlayKey, type SubKey, OVERLAY_ALL, SUB_GROUPS, PERIODS, YMODES, CANDLES, DRAW_TOOLS, SUB_HINT, OVERLAY_HINT } from './chartState.svelte';
	import { MACRO_SERIES } from '../data/macroSeries';
	import { ECON_COLORS } from './econOverlay';
	import { paramSummary, IND_DEFS } from './indicatorParams';
	import IndParamEditor from './IndParamEditor.svelte';
	import BtConfig from './BtConfig.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		hasBand: boolean;
		name: string;
		code: string;
		chgPct: number | null;
		onDraw: (name: string) => void;
		onClearDraw: () => void;
	}
	let { ctl, lang, hasBand, name, code, chgPct, onDraw, onClearDraw }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	let pop = $state<string>('none'); // 'econ' | 'ovAdd' | 'subAdd' | 'bt' | `edit:${지표명}`
	const offOverlays = $derived(OVERLAY_ALL.filter((o) => !ctl.overlays.includes(o)));
	const hasParams = (k: string) => (IND_DEFS[k]?.params.length ?? 0) > 0;
</script>

<svelte:window onclick={() => (pop !== 'none' ? (pop = 'none') : null)} />
<header class="chartRibbon" onclick={(e) => e.stopPropagation()}>
	<div class="crRow">
		<div class="crGrp crSym">
			<b>{name}</b><span class="mono dim">{code}</span>
			{#if chgPct != null}<span class={'mono ' + (chgPct >= 0 ? 'tUp' : 'tDn')}>{chgPct >= 0 ? '+' : ''}{chgPct.toFixed(1)}%</span>{/if}
		</div>
		<div class="crGrp" role="radiogroup">{#each PERIODS as p (p)}<button class={ctl.period === p ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.period = p)}>{p}</button>{/each}</div>
		<div class="crGrp" role="radiogroup">{#each CANDLES as cs (cs.v)}<button class={ctl.candleStyle === cs.v ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.candleStyle = cs.v)}>{T(cs.kr, cs.en)}</button>{/each}</div>
		<div class="crGrp" role="radiogroup">{#each YMODES as y (y.v)}<button class={ctl.yMode === y.v ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.yMode = y.v)}>{T(y.kr, y.en)}</button>{/each}</div>
		<div class="crGrp">
			<button class={ctl.showEvents ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.showEvents = !ctl.showEvents)} title={T('실적 발표 마커', 'earnings markers')}>{T('실적', 'EARN')}</button>
			<button class={ctl.showBand ? 'cbtn on' : 'cbtn'} disabled={!hasBand} onclick={() => hasBand && (ctl.showBand = !ctl.showBand)} title={T('적정주가 밴드', 'fair-value band')}>{T('밴드', 'BAND')}</button>
		</div>
		<div class="crGrp crPop">
			<button class={ctl.econ.length ? 'cbtn on' : 'cbtn'} onclick={() => (pop = pop === 'econ' ? 'none' : 'econ')}>ECON ▾</button>
			{#if pop === 'econ'}
				<div class="crMenu">
					<div class="ctMenuLbl">{T('경제지표 (최대 3 · 자기정규화)', 'Economy (max 3 · self-scaled)')}</div>
					<div class="ctRow ctRowWrap">
						{#each MACRO_SERIES as s (s.id)}
							<button class={ctl.econ.includes(s.id) ? 'mItem on' : 'mItem'}
								style={ctl.econ.includes(s.id) ? `background:transparent;color:${ECON_COLORS[s.id]};border-color:${ECON_COLORS[s.id]};font-weight:600` : ''}
								onclick={() => ctl.toggleEcon(s.id)}>{T(s.kr, s.en)}</button>
						{/each}
					</div>
				</div>
			{/if}
		</div>
		<button class="crClose cbtn" onclick={() => (ctl.full = false)} title="ESC">✕</button>
	</div>
	<div class="crRow">
		<div class="crGrp crChips">
			<span class="crLbl">{T('오버레이', 'OVERLAY')}</span>
			{#each ctl.overlays as k (k)}
				<span class="crPop crChipPair">
					<button class="crChip" title={OVERLAY_HINT[k] ?? ''} disabled={!hasParams(k)} onclick={() => (pop = pop === `edit:${k}` ? 'none' : `edit:${k}`)}>{k}{paramSummary(k, ctl.indParams[k])}</button>
					<button class="crChip x" title={T('제거', 'remove')} onclick={() => ctl.toggleOverlay(k)}>×</button>
					{#if pop === `edit:${k}`}<div class="crMenu"><IndParamEditor {ctl} {lang} name={k} onRemove={() => { ctl.toggleOverlay(k as OverlayKey); pop = 'none'; }} /></div>{/if}
				</span>
			{/each}
			<span class="crPop">
				<button class="crAdd" onclick={() => (pop = pop === 'ovAdd' ? 'none' : 'ovAdd')}>＋</button>
				{#if pop === 'ovAdd'}
					<div class="crMenu">
						<div class="ctRow ctRowWrap">{#each offOverlays as o (o)}<button class="mItem" title={OVERLAY_HINT[o] ?? ''} onclick={() => { ctl.toggleOverlay(o); pop = 'none'; }}>{o}{OVERLAY_HINT[o] ? ` ${OVERLAY_HINT[o]}` : ''}</button>{/each}</div>
					</div>
				{/if}
			</span>
		</div>
		<div class="crGrp crChips">
			<span class="crLbl">{T('페인', 'PANE')}</span>
			{#each ctl.subs as k (k)}
				<span class="crPop crChipPair">
					<button class="crChip" title={SUB_HINT[k] ?? ''} disabled={!hasParams(k)} onclick={() => (pop = pop === `edit:${k}` ? 'none' : `edit:${k}`)}>{k}{paramSummary(k, ctl.indParams[k])}</button>
					<button class="crChip x" title={T('제거', 'remove')} onclick={() => ctl.toggleSub(k)}>×</button>
					{#if pop === `edit:${k}`}<div class="crMenu"><IndParamEditor {ctl} {lang} name={k} onRemove={() => { ctl.toggleSub(k as SubKey); pop = 'none'; }} /></div>{/if}
				</span>
			{/each}
			<span class="crPop">
				<button class="crAdd" onclick={() => (pop = pop === 'subAdd' ? 'none' : 'subAdd')}>＋</button>
				{#if pop === 'subAdd'}
					<div class="crMenu crMenuWideR">
						{#each SUB_GROUPS as g (g.kr)}
							<div class="ctMenuLbl">{T(g.kr, g.en)}</div>
							<div class="ctRow ctRowWrap">
								{#each g.keys.filter((k) => !ctl.subs.includes(k)) as k (k)}
									<button class="mItem" onclick={() => { ctl.toggleSub(k); pop = 'none'; }}>{k}{SUB_HINT[k] ? ` ${SUB_HINT[k]}` : ''}</button>
								{/each}
							</div>
						{/each}
					</div>
				{/if}
			</span>
		</div>
		<div class="crGrp">
			{#each DRAW_TOOLS as d (d.name)}<button class="cbtn" title={T(d.kr, d.en)} onclick={() => onDraw(d.name)}>{d.icon}</button>{/each}
			<button class={ctl.magnet ? 'cbtn on' : 'cbtn'} title={T('자석 스냅', 'magnet snap')} onclick={() => (ctl.magnet = !ctl.magnet)}>🧲</button>
			<button class="cbtn" disabled={!ctl.drawCount} title={T('그리기 전체 지우기', 'clear drawings')} onclick={onClearDraw}>🗑</button>
		</div>
		<div class="crGrp crPop">
			<button class={ctl.btKey ? 'crChip on' : 'crAdd'} onclick={() => (pop = pop === 'bt' ? 'none' : 'bt')}>
				{ctl.activeBt ? T(ctl.activeBt.kr, ctl.activeBt.en) : `＋ ${T('전략 백테스트', 'Backtest')}`}
			</button>
			{#if pop === 'bt'}<div class="crMenu crMenuR"><BtConfig {ctl} {lang} /></div>{/if}
		</div>
	</div>
</header>
