<script lang="ts">
	// 전체화면 전문가 리본 (증권사 HTS 상단 툴바 표준) — 2단 상시 노출.
	// Row1 = 보는 방법(종목·기간·캔들·축·마커·ECON), Row2 = 분석 작업대(오버레이/페인 활성 칩+카탈로그·그리기·BT).
	// 상태 = ChartCtl 단일 SSOT (일반 메뉴와 공유 — 리본에서 켠 지표가 일반 메뉴에도 켜져 있다).
	import type { Lang } from '../data/types';
	import { type ChartCtl, type OverlayKey, type SubKey, OVERLAY_ALL, SUB_GROUPS, PERIODS, TFS, YMODES, CANDLES, SUB_HINT, OVERLAY_HINT } from './chartState.svelte';
	import { MACRO_SERIES } from '../data/macroSeries';
	import { ECON_COLORS } from './econOverlay';
	import { CMP_COLORS } from './compareOverlay';
	import { paramSummary, IND_DEFS } from './indicatorParams';
	import { loadTemplates, saveTemplate, deleteTemplate, applyTemplate } from './templateStore';
	import IndParamEditor from './IndParamEditor.svelte';
	import BtConfig from './BtConfig.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		hasBand: boolean;
		name: string;
		code: string;
		chgPct: number | null;
		peers?: { code: string; name: string }[];
		onSnapshot?: () => void;
		onReplay?: () => void; // 바 리플레이 진입 (시작점 환산은 PriceChart — viewLen 보유 주체)
	}
	let { ctl, lang, hasBand, name, code, chgPct, peers = [], onSnapshot, onReplay }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	let pop = $state<string>('none'); // 'econ' | 'ovAdd' | 'subAdd' | 'bt' | 'vs' | 'tmpl' | `edit:${지표명}`
	const offOverlays = $derived(OVERLAY_ALL.filter((o) => !ctl.overlays.includes(o)));
	const hasParams = (k: string) => (IND_DEFS[k]?.params.length ?? 0) > 0;
	// 차트틀 — localStorage 다중 슬롯 (templateStore). 목록은 본 컴포넌트 로컬 미러.
	let templates = $state(loadTemplates());
	let tmplName = $state('');
</script>

<svelte:window onclick={() => (pop !== 'none' ? (pop = 'none') : null)} />
<header class="chartRibbon" onclick={(e) => e.stopPropagation()}>
	<div class="crRow">
		<div class="crGrp crSym">
			<b>{name}</b><span class="mono dim">{code}</span>
			{#if chgPct != null}<span class={'mono ' + (chgPct >= 0 ? 'tUp' : 'tDn')}>{chgPct >= 0 ? '+' : ''}{chgPct.toFixed(1)}%</span>{/if}
		</div>
		<div class="crGrp" role="radiogroup">{#each PERIODS as p (p)}<button class={ctl.period === p ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.period = p)}>{p}</button>{/each}</div>
		<div class="crGrp" role="radiogroup">{#each TFS as t (t.v)}<button class={ctl.tf === t.v ? 'cbtn on' : 'cbtn'} title={T('봉 주기', 'timeframe')} onclick={() => (ctl.tf = t.v)}>{T(t.kr, t.en)}</button>{/each}</div>
		<div class="crGrp" role="radiogroup">{#each CANDLES as cs (cs.v)}<button class={ctl.candleStyle === cs.v ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.candleStyle = cs.v)}>{T(cs.kr, cs.en)}</button>{/each}</div>
		<div class="crGrp" role="radiogroup">{#each YMODES as y (y.v)}<button class={ctl.yMode === y.v ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.yMode = y.v)}>{T(y.kr, y.en)}</button>{/each}</div>
		<div class="crGrp">
			<button class={ctl.adj ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.adj = !ctl.adj)} title={T('수정주가 (분할·증자 보정)', 'adjusted price')}>{T('수정', 'ADJ')}</button>
			<button class={ctl.showEvents ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.showEvents = !ctl.showEvents)} title={T('실적 발표 마커', 'earnings markers')}>{T('실적', 'EARN')}</button>
			<button class={ctl.showBand ? 'cbtn on' : 'cbtn'} disabled={!hasBand} onclick={() => hasBand && (ctl.showBand = !ctl.showBand)} title={T('적정주가 밴드', 'fair-value band')}>{T('밴드', 'BAND')}</button>
			<button class={ctl.showRefs ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.showRefs = !ctl.showRefs)} title={T('52주 고저·전일종가 기준선', '52w hi/lo · prev close')}>{T('기준', 'REF')}</button>
			<button class={ctl.showVP ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.showVP = !ctl.showVP)} title={T('매물대 (가시구간 거래대금 가중 + POC)', 'volume profile (visible range)')}>{T('매물대', 'VP')}</button>
		</div>
		<div class="crGrp crPop">
			<button class={ctl.compares.length ? 'cbtn on' : 'cbtn'} onclick={() => (pop = pop === 'vs' ? 'none' : 'vs')}>VS ▾</button>
			{#if pop === 'vs'}
				<div class="crMenu">
					<div class="ctMenuLbl">{T('종목비교 (최대 3 · % 축 자동)', 'Compare (max 3 · % axis)')}</div>
					<div class="ctRow ctRowWrap">
						{#if peers.length}
							{#each peers as p (p.code)}
								{@const ci = ctl.compares.findIndex((x) => x.code === p.code)}
								<button class={ci >= 0 ? 'mItem on' : 'mItem'}
									style={ci >= 0 ? `background:transparent;color:${CMP_COLORS[ci]};border-color:${CMP_COLORS[ci]};font-weight:600` : ''}
									onclick={() => ctl.toggleCompare(p)}>{p.name}</button>
							{/each}
						{:else}
							<span class="dim" style="font-size:9px">{T('동종업계 데이터 없음', 'no peer data')}</span>
						{/if}
					</div>
				</div>
			{/if}
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
		<div class="crGrp">
			{#if ctl.replay.on}
				<button class="cbtn" onclick={() => ctl.replayRestart()} title={T('시작점 복귀', 'restart')}>⏮</button>
				<button class={ctl.replay.playing ? 'cbtn on' : 'cbtn'} onclick={() => (ctl.replay.playing = !ctl.replay.playing)} title={T('자동재생 (400ms)', 'auto-play')}>{ctl.replay.playing ? '⏸' : '▶'}</button>
				<button class="cbtn" onclick={() => ctl.replayStep()} title={T('한 봉 전진 (→·스페이스)', 'step (→/space)')}>▶▶</button>
				<span class="mono dim rpPos">{ctl.replay.idx + 1}/{ctl.replay.len}</span>
				<button class="cbtn" onclick={() => ctl.replayExit()} title={T('리플레이 종료 (ESC)', 'exit replay (ESC)')}>✕</button>
			{:else}
				<button class="cbtn" onclick={() => onReplay?.()} title={T('바 리플레이 — 과거 시점부터 한 봉씩 재생', 'bar replay')}>{T('리플레이', 'Replay')}</button>
			{/if}
		</div>
		<button class="crClose cbtn" onclick={() => onSnapshot?.()} title={T('차트 PNG 저장 (S)', 'save PNG (S)')}>📷</button>
		<button class="cbtn" onclick={() => (ctl.full = false)} title="ESC">✕</button>
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
		<div class="crGrp crPop">
			<button class={ctl.btKey ? 'crChip on' : 'crAdd'} disabled={ctl.tf !== 'D'} title={ctl.tf !== 'D' ? T('일봉 전용', 'daily only') : ''} onclick={() => (pop = pop === 'bt' ? 'none' : 'bt')}>
				{ctl.activeBt ? T(ctl.activeBt.kr, ctl.activeBt.en) : `＋ ${T('전략 백테스트', 'Backtest')}`}
			</button>
			{#if pop === 'bt'}<div class="crMenu crMenuR"><BtConfig {ctl} {lang} /></div>{/if}
		</div>
		<div class="crGrp crPop">
			<button class={templates.length ? 'cbtn on' : 'cbtn'} onclick={() => (pop = pop === 'tmpl' ? 'none' : 'tmpl')} title={T('차트틀 — 지표·축·봉주기 설정 저장/적용', 'chart templates')}>{T('틀', 'TMPL')} ▾</button>
			{#if pop === 'tmpl'}
				<div class="crMenu crMenuR">
					<div class="ctMenuLbl">{T('차트틀 (지표·파라미터·축·캔들·봉주기 · 최대 12)', 'Templates (indicators · axis · tf · max 12)')}</div>
					<input
						class="tmplInput"
						placeholder={T('현재 설정 이름 입력 후 Enter', 'name current setup + Enter')}
						bind:value={tmplName}
						onkeydown={(e) => {
							if (e.key === 'Enter' && tmplName.trim()) {
								templates = saveTemplate(ctl, tmplName.trim());
								tmplName = '';
							}
						}}
					/>
					{#each templates as t (t.name)}
						<div class="tmplRow">
							<button class="mItem" title={`${t.overlays.join('·') || '—'} / ${t.subs.join('·') || '—'} · ${t.tf}`} onclick={() => { applyTemplate(ctl, t); pop = 'none'; }}>{t.name}</button>
							<button class="crChip x" title={T('삭제', 'delete')} onclick={() => (templates = deleteTemplate(t.name))}>×</button>
						</div>
					{:else}
						<span class="dim" style="font-size:9px">{T('저장된 틀 없음 — 위에 이름 입력', 'no templates yet')}</span>
					{/each}
				</div>
			{/if}
		</div>
	</div>
</header>
