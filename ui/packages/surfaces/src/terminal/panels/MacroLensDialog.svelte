<script lang="ts">
	import { GitBranch, LineChart, ShieldAlert, X } from 'lucide-svelte';
	import type { Lang } from '../lib/types';
	import type { MacroLensSnapshot, MacroLensTab } from '../lib/macroLens';
	import { ECON_MAX } from '../charts/chartState.svelte';

	interface Props {
		snapshot: MacroLensSnapshot;
		lang: Lang;
		tab: MacroLensTab;
		focusId?: string;
		activeEcon?: string[];
		onTab: (tab: MacroLensTab) => void;
		onClose: () => void;
		onToggleEcon?: (id: string) => void;
	}
	let { snapshot, lang, tab, focusId = '', activeEcon = [], onTab, onClose, onToggleEcon }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const tabs: { k: MacroLensTab; kr: string; en: string }[] = [
		{ k: 'regime', kr: '국면', en: 'Regime' },
		{ k: 'drivers', kr: '지표·Driver', en: 'Drivers' },
		{ k: 'transmission', kr: '전파 지도', en: 'Transmission' },
		{ k: 'scenario', kr: '시나리오', en: 'Scenario' },
		{ k: 'sources', kr: '출처·한계', en: 'Sources' }
	];
	const signText: Record<string, string> = { positive: '+', negative: '-', mixed: '±', unknown: '?' };
	const confidenceText: Record<string, string> = { high: 'HIGH', medium: 'MED', low: 'LOW', blocked: 'BLOCK' };
	const severityCls: Record<string, string> = { info: 'info', warning: 'warn', blocker: 'block' };
	const pressureText: Record<string, string> = { high: '핵심', medium: '검토', low: '맥락', blocked: '차단' };
	const readinessText: Record<string, string> = { ready: 'READY', needsEvidence: 'EVIDENCE', blocked: 'BLOCK' };
	const relevantDrivers = $derived(snapshot.drivers.filter((d) => d.relevance !== 'context').slice(0, 16));
	const contextDrivers = $derived(snapshot.drivers.filter((d) => d.relevance === 'context').slice(0, 18));
	const visibleDrivers = $derived([...relevantDrivers, ...contextDrivers]);
	const focusDriver = $derived(focusId ? snapshot.drivers.find((d) => d.id === focusId) : null);
	const focusEdge = $derived(focusId ? snapshot.transmissionEdges.find((e) => e.driverId === focusId || e.sectorKey === focusId) : null);
	const econBlocked = (id: string) => !activeEcon.includes(id) && activeEcon.length >= ECON_MAX;
	let dialogEl = $state<HTMLDivElement | null>(null);
	function onDialogKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
		}
		e.stopPropagation();
	}
	$effect(() => {
		if (typeof document === 'undefined') return;
		const prev = document.activeElement instanceof HTMLElement ? document.activeElement : null;
		queueMicrotask(() => dialogEl?.focus());
		return () => prev?.focus();
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="scrimWrap macroLensScrim" role="presentation" onclick={onClose}>
	<div bind:this={dialogEl} class="scrModal mlModal" role="dialog" aria-modal="true" aria-label="Macro Lens" tabindex="-1" onclick={(e) => e.stopPropagation()} onkeydown={onDialogKeydown}>
		<div class="scrHead mlHead">
			<div class="mlTitle">
				<span class="mlKicker">MACRO LENS</span>
				<b>{snapshot.company.name}</b>
				<span class="mono">{snapshot.company.code}</span>
				<span>{snapshot.company.sector}</span>
			</div>
			<div class="mlAsOf">
				<span>macro <b>{snapshot.asOf.macro ?? '—'}</b></span>
				<span>price <b>{snapshot.asOf.price ?? '—'}</b></span>
				<span>fin <b>{snapshot.asOf.finance ?? '—'}</b></span>
			</div>
			<button class="scrClose" onclick={onClose} aria-label="close"><X size={14} /></button>
		</div>

		<div class="mlTabs">
			{#each tabs as t (t.k)}
				<button class:active={tab === t.k} onclick={() => onTab(t.k)}>{T(t.kr, t.en)}</button>
			{/each}
		</div>
		<div class="mlAlwaysNote">
			{T('매크로 렌즈는 배치 데이터 기반의 전파 경로 분석입니다. 상관은 인과가 아니며, 지표 변화가 회사 실적 변화를 보장하지 않습니다.', 'Macro Lens is batch-data transmission analysis. Correlation is not causation, and indicator moves do not guarantee company results.')}
		</div>

		<div class="mlBody">
			{#if tab === 'regime'}
				<section class="mlFour">
					<div><span>1</span><b>{T('국면', 'Regime')}</b><em>{snapshot.marketPhase.kr?.label ?? 'KR —'} / {snapshot.marketPhase.us?.label ?? 'US —'}</em></div>
					<div><span>2</span><b>{T('근거 지표', 'Driver')}</b><em>{snapshot.topPressures[0]?.label ?? T('계산 전', 'pending')} · {snapshot.topPressures[0]?.pressureReason ?? T('driver 없음', 'no driver')}</em></div>
					<div><span>3</span><b>{T('전파 경로', 'Path')}</b><em>{snapshot.transmissionEdges[0] ? `${snapshot.transmissionEdges[0].driverLabel} → ${snapshot.transmissionEdges[0].financialLine}` : T('sector edge 없음', 'no sector edge')}</em></div>
					<div><span>4</span><b>{T('약한 점', 'Limit')}</b><em>{snapshot.falsifiers[0]?.label ?? snapshot.exposureQuality.reason}</em></div>
				</section>
				<section class="mlGrid two">
					{#each [snapshot.marketPhase.kr, snapshot.marketPhase.us] as p (p?.market ?? 'x')}
						<div class="mlBlock">
							<div class="mlBlockTop">
								<span class="mlBlockK">{p?.market ?? '—'}</span>
								<b>{p?.label ?? T('국면 없음', 'No phase')}</b>
							</div>
							<div class="mlBig">{p?.quadrant ?? '—'}</div>
							<div class="mlKV">
								<span>{T('성장', 'Growth')} <b>{p?.growth ?? '—'}</b></span>
								<span>{T('물가', 'Inflation')} <b>{p?.inflation ?? '—'}</b></span>
							</div>
							<p>{p?.description ?? T('국면 상세 데이터가 없습니다.', 'Regime detail unavailable.')}</p>
						</div>
					{/each}
				</section>
				<section class="mlGrid pressureGrid" aria-label="Priority Macro Paths">
					{#each snapshot.topPressures as d (d.id)}
						<button class={'mlPressure ' + d.pressureLevel} onclick={() => onTab('drivers')}>
							<div class="mlPressureTop"><span class="mlBlockK">{T('우선 경로', 'Priority path')}</span><b>{d.label}</b><em>{pressureText[d.pressureLevel]}</em></div>
							<p>{d.pressureReason}</p>
							<div class="mlMiniList"><span>{d.qualityHint}</span></div>
						</button>
					{/each}
				</section>
				<section class="mlBlock">
					<div class="mlBlockTop"><span class="mlBlockK">{T('전파 요약', 'Transmission summary')}</span><b>{T('국면은 결론이 아니라 시작점', 'Regime is the starting point')}</b></div>
					<div class="mlChain">
						<span>Macro Driver</span><i>→</i><span>Sector Edge</span><i>→</i><span>Company Checkpoint</span><i>→</i><span>Falsifier</span>
					</div>
					<div class="mlChips">
						{#if snapshot.sectorBinding.tailwind}
							<span class={'mlPill ' + snapshot.sectorBinding.tailwind.tone}>{snapshot.sectorBinding.tailwind.kr} · {snapshot.sectorBinding.tailwind.label} {snapshot.sectorBinding.tailwind.blended.toFixed(2)}</span>
						{/if}
						<span class="mlPill neutral">{snapshot.exposureQuality.reason}</span>
					</div>
				</section>
			{:else if tab === 'drivers'}
				{#if focusDriver}
					<section class="mlFocus">
						<LineChart class="mlFocusIcon" size={15} />
						<div><b>{focusDriver.label}</b><span>{focusDriver.directionSemantics}</span></div>
					</section>
				{/if}
				<section class="mlGrid pressureGrid" aria-label="Priority Macro Paths">
					{#each snapshot.topPressures as d (d.id)}
						<div class={'mlPressure ' + d.pressureLevel}>
							<div class="mlPressureTop"><span class="mlBlockK">{T('우선 경로', 'Priority path')}</span><b>{d.label}</b><em>{pressureText[d.pressureLevel]}</em></div>
							<p>{d.pressureReason}</p>
							<div class="mlMiniList"><span>{d.qualityHint}</span></div>
						</div>
					{/each}
				</section>
				<div class="mlDriverTable">
					<div class="mlDriverHead">
						<span>{T('Driver', 'Driver')}</span><span>{T('품질', 'Quality')}</span><span>{T('값', 'Value')}</span><span>{T('변화', 'Chg')}</span><span>{T('계보', 'Lineage')}</span><span>{T('동작', 'Action')}</span>
					</div>
					{#each visibleDrivers as d (d.id)}
						<div class={'mlDriverRow ' + d.relevance} class:focused={focusId === d.id}>
							<span class="mlDriverName"><b>{d.label}</b><em>{d.id} · {d.group} · {d.directionSemantics}</em></span>
							<span class="mlDriverScore"><b class={'mlScore ' + d.pressureLevel}>{pressureText[d.pressureLevel]}</b><em>{d.qualityHint}</em></span>
							<span class="mono">{d.value}</span>
							<span class="mono">{d.change}</span>
							<span class="mlDriverLine">{d.sourceLineage}{#if d.coMovement}<em>{d.coMovement.label}</em><small>{T('동행상관 · 인과 아님', 'co-movement · not causal')}</small>{/if}</span>
							<span>
								<button class="mlIconBtn" class:on={activeEcon.includes(d.id)} disabled={econBlocked(d.id)} onclick={() => onToggleEcon?.(d.id)} title={econBlocked(d.id) ? T('동시 3개까지 표시됩니다', 'max 3 overlays') : T('차트 ECON 오버레이 토글', 'toggle chart ECON overlay')}>
									<LineChart size={12} />{activeEcon.includes(d.id) ? 'ON' : econBlocked(d.id) ? 'MAX' : 'ECON'}
								</button>
							</span>
						</div>
					{/each}
				</div>
				<div class="mlNote">{T('Driver는 최신값만 보지 않고 방향성 의미·lag·섹터 전파 가능성을 같이 본다.', 'Drivers are read with direction semantics, lag and sector transmission, not just latest values.')}</div>
			{:else if tab === 'transmission'}
				{#if focusEdge}
					<section class="mlFocus">
						<GitBranch class="mlFocusIcon" size={15} />
						<div><b>{focusEdge.driverLabel} → {focusEdge.financialLine}</b><span>{focusEdge.note}</span></div>
					</section>
				{/if}
				<section class="mlGrid edgeGrid">
					{#each snapshot.transmissionEdges as e (e.id)}
						<div class="mlEdge" class:focused={focusId === e.driverId || focusId === e.sectorKey}>
							<div class="mlEdgeTop">
								<span class="mlSign">{signText[e.sign]}</span>
								<b>{e.driverLabel}</b>
								<em>{e.market}</em>
								<span class={'mlConf ' + e.confidence}>{confidenceText[e.confidence]}</span>
							</div>
							<div class="mlEdgePath">{e.sectorLabel} → {e.financialLine} → {e.valuationLever}</div>
							<p>{e.note}</p>
							<div class="mlMiniList">
								<span>{T('lag', 'lag')}: {e.lagMonths ? `${e.lagMonths[0]}-${e.lagMonths[1]}M` : '—'}</span>
								<span>{e.evidenceLevel}</span>
							</div>
							<div class="mlEvidence">
								{#each e.requiredCompanyEvidence.slice(0, 3) as x (x)}<span>{x}</span>{/each}
							</div>
						</div>
					{/each}
				</section>
				<section class="mlGrid two">
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('회사 checkpoint', 'Company checkpoints')}</span><b>{T('정량 확정 전 확인할 재무 위치', 'Financial checkpoints before quant claim')}</b></div>
						{#each snapshot.companyCheckpoints as c (c.id)}
							<div class="mlCheck">
								<span>{c.label}</span><b class={c.tone}>{c.value}</b><em>{c.reason}</em>
							</div>
						{/each}
					</div>
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('반증 조건', 'Falsifiers')}</span><b>{T('강한 연결만 남기기', 'Keep only defensible links')}</b></div>
						{#each snapshot.falsifiers as f (f.id)}
							<div class={'mlFalse ' + severityCls[f.severity]}>
								<ShieldAlert class={'mlFalseIcon ' + severityCls[f.severity]} size={13} />
								<div><b>{f.label}</b><span>{f.detail}</span></div>
							</div>
						{/each}
					</div>
				</section>
			{:else if tab === 'scenario'}
				<section class="mlGrid scenarioGrid">
					{#each snapshot.scenarios as s (s.id)}
						<div class={'mlScenario ' + s.readiness.status}>
							<div class="mlPressureTop"><span class="mlBlockK">{s.shock}</span><em>{readinessText[s.readiness.status]}</em></div>
							<b>{s.label}</b>
							<p>{T('먼저 흔들리는 곳', 'First break')}: {s.firstBreak}</p>
							<p>{T('예상 방향', 'Expected direction')}: {s.expectedDirection}</p>
							<div class="mlMiniList">
								<span>{s.impactedFinancialLine}</span>
								<span>{s.valuationLever}</span>
							</div>
							<div class="mlEvidence">
								{#each s.requiredEvidence as x (x)}<span>{x}</span>{/each}
							</div>
							<p>{T('반증', 'Falsifier')}: {s.falsifier}</p>
							<div class="mlSrc warn">{s.readiness.reason}</div>
							<em>{s.nextSurface}</em>
						</div>
					{/each}
				</section>
				<div class="mlNote">{T('시나리오는 명시 가정이다. 예측·추천·목표주가가 아니며 회사 손익 정량화는 별도 시뮬레이터 영역이다.', 'Scenarios are explicit assumptions, not forecasts, recommendations or target prices.')}</div>
			{:else}
				<section class="mlGrid two">
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('출처', 'Sources')}</span><b>{T('source/date/value lineage', 'source/date/value lineage')}</b></div>
						{#each snapshot.sourceRefs as s (s)}<div class="mlSrc">{s}</div>{/each}
					</div>
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('한계', 'Limits')}</span><b>{T('모르는 것은 숨기지 않음', 'Unknowns stay visible')}</b></div>
						{#each snapshot.missing as m (m)}<div class="mlSrc warn">{m}</div>{/each}
						<div class="mlSrc warn">{snapshot.exposureQuality.reason}</div>
						<div class="mlSrc warn">nObs/R²/window/lag: {snapshot.exposureQuality.nObs ?? '—'} / {snapshot.exposureQuality.rSquared ?? '—'} / {snapshot.exposureQuality.window ?? '—'} / {snapshot.exposureQuality.lagMonths ?? '—'}</div>
						<div class="mlSrc">{T('상관은 인과가 아니며, 지표 변화가 회사 실적 변화를 보장하지 않는다.', 'Correlation is not causation; indicator moves do not guarantee company results.')}</div>
					</div>
				</section>
			{/if}
		</div>
	</div>
</div>

<style>
	.mlModal { width: min(1040px, 96vw); height: min(760px, 90vh); }
	.mlHead { flex-wrap: wrap; }
	.mlTitle { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlTitle b { font-size: 14px; }
	.mlTitle .mono, .mlTitle span:last-child { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlKicker { font-family: var(--dl-font-mono); color: var(--amber); font-weight: 800; font-size: 10px; letter-spacing: .06em; }
	.mlAsOf { margin-left: auto; display: flex; flex-wrap: wrap; gap: 6px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.mlAsOf span { border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 1px 5px; }
	.mlAsOf b { color: var(--dl-ink, #c8cfdb); font-family: var(--dl-font-mono); }
	.mlTabs { display: flex; gap: 3px; padding: 7px 10px 0; border-bottom: 1px solid var(--dl-line, #1b2130); background: rgba(255,255,255,.012); }
	.mlTabs button { border: 1px solid transparent; border-bottom: 0; background: transparent; color: var(--dl-ink-dim, #5b6473); font-size: 11px; font-weight: 700; padding: 6px 10px; cursor: pointer; border-radius: 4px 4px 0 0; }
	.mlTabs button:hover { color: var(--amber); }
	.mlTabs button.active { color: var(--dl-ink); border-color: var(--dl-line, #1b2130); background: var(--dl-bg-raised, #0e141f); }
	.mlAlwaysNote { padding: 6px 12px; border-bottom: 1px solid var(--dl-line, #1b2130); color: var(--dl-ink-dim, #5b6473); background: rgba(251,146,60,.035); font-size: 10.5px; line-height: 1.4; }
	.mlBody { flex: 1 1 auto; min-height: 0; overflow: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
	.mlGrid { display: grid; gap: 10px; }
	.mlGrid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.edgeGrid { grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); }
	.scenarioGrid { grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
	.pressureGrid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	.mlBlock, .mlEdge, .mlScenario, .mlFocus { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 10px; min-width: 0; }
	.mlFour { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
	.mlFour div { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 8px; display: grid; grid-template-columns: 18px minmax(0, 1fr); column-gap: 6px; row-gap: 2px; align-items: start; }
	.mlFour span { grid-row: span 2; width: 18px; height: 18px; border: 1px solid var(--dl-line, #1b2130); border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; color: var(--amber); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlFour b { min-width: 0; font-size: 10.5px; }
	.mlFour em { min-width: 0; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlPressure { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 9px; min-width: 0; text-align: left; color: var(--dl-ink); cursor: pointer; }
	.mlPressure.high { border-color: rgba(52,211,153,.42); background: rgba(52,211,153,.045); }
	.mlPressure.medium { border-color: rgba(251,146,60,.36); background: rgba(251,146,60,.04); }
	.mlPressure.low { border-color: rgba(91,100,115,.55); }
	.mlPressure.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.04); }
	.mlPressureTop { display: flex; align-items: center; gap: 6px; min-width: 0; }
	.mlPressureTop b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlPressureTop em { font-style: normal; font-family: var(--dl-font-mono); font-size: 10px; color: var(--amber); }
	.mlPressure p { margin: 7px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.38; }
	.mlBlockTop, .mlEdgeTop { display: flex; align-items: center; gap: 7px; min-width: 0; }
	.mlBlockK { font-size: 9px; font-weight: 800; color: var(--amber); letter-spacing: .06em; text-transform: uppercase; }
	.mlBig { margin-top: 8px; font-size: 20px; font-weight: 800; }
	.mlKV, .mlMiniList { display: flex; flex-wrap: wrap; gap: 8px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); margin-top: 6px; }
	.mlBlock p, .mlEdge p, .mlScenario p { margin: 7px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 11px; line-height: 1.45; }
	.mlChain { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; margin-top: 9px; }
	.mlChain span { border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 4px 7px; font-size: 11px; }
	.mlChain i { color: var(--amber); font-style: normal; }
	.mlChips, .mlEvidence { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
	.mlPill, .mlEvidence span { border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; padding: 2px 7px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.mlPill.up, .up { color: var(--up); }
	.mlPill.down, .down { color: var(--dn); }
	.good { color: var(--good); }
	.warn { color: var(--warn); }
	.neutral { color: var(--dl-ink-dim, #5b6473); }
	.mlFocus { display: flex; gap: 8px; align-items: flex-start; border-color: rgba(251,146,60,.38); background: rgba(251,146,60,.06); }
	.mlFocusIcon { color: var(--amber); flex: 0 0 auto; margin-top: 1px; }
	.mlFocus div { display: flex; flex-direction: column; gap: 2px; }
	.mlFocus span { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlDriverTable { display: flex; flex-direction: column; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; overflow: hidden; }
	.mlDriverHead, .mlDriverRow { display: grid; grid-template-columns: minmax(190px, 1.7fr) 58px .7fr .6fr minmax(160px, 1.1fr) 86px; gap: 8px; align-items: center; padding: 6px 8px; }
	.mlDriverHead { font-size: 9px; font-weight: 800; color: var(--dl-ink-dim, #5b6473); background: rgba(255,255,255,.025); letter-spacing: .05em; }
	.mlDriverRow { font-size: 11px; border-top: 1px solid rgba(255,255,255,.045); }
	.mlDriverRow.primary { background: rgba(52,211,153,.035); }
	.mlDriverRow.secondary { background: rgba(251,146,60,.025); }
	.mlDriverRow.focused, .mlEdge.focused { outline: 1px solid var(--amber); outline-offset: -1px; }
	.mlDriverName { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
	.mlDriverName em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverScore { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; min-width: 0; }
	.mlDriverScore em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 8.5px; line-height: 1.2; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlScore { display: inline-flex; align-items: center; justify-content: center; min-width: 36px; height: 18px; border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; font-family: var(--dl-font-mono); font-size: 10px; padding: 0 4px; }
	.mlScore.high { color: var(--good); border-color: rgba(52,211,153,.45); }
	.mlScore.medium { color: var(--amber); border-color: rgba(251,146,60,.45); }
	.mlScore.low { color: var(--dl-ink-dim, #5b6473); }
	.mlScore.blocked { color: var(--dn); border-color: rgba(248,113,113,.45); }
	.mlDriverLine { display: flex; flex-direction: column; gap: 1px; min-width: 0; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.25; }
	.mlDriverLine em { color: var(--amber); font-style: normal; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverLine small { width: max-content; max-width: 100%; color: var(--warn); border: 1px solid rgba(251,146,60,.35); border-radius: 999px; padding: 1px 5px; font-size: 8.5px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlIconBtn { display: inline-flex; align-items: center; justify-content: center; gap: 3px; width: 72px; border: 1px solid var(--dl-line, #1b2130); background: var(--dl-bg-base, #080d16); color: var(--dl-ink-dim, #5b6473); border-radius: 3px; padding: 3px 4px; cursor: pointer; font-size: 9px; font-weight: 700; }
	.mlIconBtn:hover, .mlIconBtn.on { color: var(--amber); border-color: var(--amber); }
	.mlIconBtn:disabled { cursor: not-allowed; opacity: .48; color: var(--dl-ink-dim, #5b6473); border-color: var(--dl-line, #1b2130); }
	.mlEdgeTop b { flex: 1 1 auto; min-width: 0; }
	.mlSign { width: 19px; height: 19px; border-radius: 50%; border: 1px solid var(--dl-line, #1b2130); display: inline-flex; align-items: center; justify-content: center; color: var(--amber); font-weight: 800; }
	.mlEdgeTop em { font-style: normal; color: var(--dl-ink-dim, #5b6473); font-size: 10px; }
	.mlConf { font-size: 9px; font-weight: 800; border-radius: 3px; padding: 1px 4px; border: 1px solid var(--dl-line, #1b2130); color: var(--dl-ink-dim, #5b6473); }
	.mlConf.medium { color: var(--good); }
	.mlConf.low { color: var(--warn); }
	.mlConf.high { color: var(--up); }
	.mlEdgePath { margin-top: 7px; color: var(--dl-ink); font-size: 11px; font-weight: 700; }
	.mlCheck { display: grid; grid-template-columns: 108px 72px 1fr; gap: 8px; padding: 6px 0; border-top: 1px solid rgba(255,255,255,.045); font-size: 11px; }
	.mlCheck em { color: var(--dl-ink-dim, #5b6473); font-style: normal; }
	.mlFalse { display: flex; gap: 7px; padding: 7px 0; border-top: 1px solid rgba(255,255,255,.045); }
	.mlFalseIcon { flex: 0 0 auto; margin-top: 1px; }
	.mlFalseIcon.info { color: var(--good); }
	.mlFalseIcon.warn { color: var(--warn); }
	.mlFalseIcon.block { color: var(--dn); }
	.mlFalse div { display: flex; flex-direction: column; gap: 2px; }
	.mlFalse span { color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.35; }
	.mlScenario b { display: block; margin-top: 5px; }
	.mlScenario.needsEvidence { border-color: rgba(251,146,60,.36); }
	.mlScenario.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.035); }
	.mlScenario em { display: block; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; margin-top: 8px; }
	.mlSrc { padding: 6px 0; border-top: 1px solid rgba(255,255,255,.045); color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlNote { color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.45; border: 1px dashed var(--dl-line, #1b2130); border-radius: 5px; padding: 8px 10px; }
	@media (max-width: 760px) {
		.mlModal { height: min(780px, 94vh); }
		.mlGrid.two, .pressureGrid, .mlFour { grid-template-columns: 1fr; }
		.mlDriverHead, .mlDriverRow { grid-template-columns: minmax(132px, 1.3fr) 72px 76px; }
		.mlDriverHead span:nth-child(3), .mlDriverHead span:nth-child(4), .mlDriverHead span:nth-child(5), .mlDriverRow > span:nth-child(3), .mlDriverRow > span:nth-child(4), .mlDriverRow > span:nth-child(5) { display: none; }
	}
</style>
