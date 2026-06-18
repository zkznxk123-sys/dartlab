<script lang="ts">
	import { GitBranch, LineChart, ShieldAlert, X } from 'lucide-svelte';
	import type { Lang } from '../lib/types';
	import type { MacroChannel, MacroDriverView, MacroLensSnapshot, MacroLensTab, MacroTransmissionEdgeView } from '../lib/macroLens';
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
	let localFocus = $state('');
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const tabs: { k: MacroLensTab; kr: string; en: string }[] = [
		{ k: 'regime', kr: '대시보드', en: 'Dashboard' },
		{ k: 'drivers', kr: '지표·Driver', en: 'Drivers' },
		{ k: 'transmission', kr: '전파 지도', en: 'Transmission' },
		{ k: 'scenario', kr: '시나리오', en: 'Scenario' },
		{ k: 'sources', kr: '출처·한계', en: 'Sources' }
	];
	const channels: { k: MacroChannel; kr: string; en: string }[] = [
		{ k: 'revenue', kr: '매출', en: 'Sales' },
		{ k: 'margin', kr: '마진', en: 'Margin' },
		{ k: 'balanceSheet', kr: '차입', en: 'Debt' },
		{ k: 'cashFlow', kr: '현금', en: 'Cash' },
		{ k: 'valuation', kr: '밸류', en: 'Value' }
	];
	const signText: Record<string, string> = { positive: '+', negative: '-', mixed: '±', unknown: '?' };
	const confidenceText: Record<string, string> = { high: 'HIGH', medium: 'MED', low: 'LOW', blocked: 'LOCK' };
	const evidenceText: Record<string, string> = { observed: 'OBS', sectorPrior: 'PRIOR', template: 'TPL' };
	const severityCls: Record<string, string> = { info: 'info', warning: 'warn', blocker: 'block' };
	const pressureText: Record<string, string> = { high: '검토우선', medium: '보조', low: '맥락', blocked: '차단' };
	const readinessText: Record<string, string> = { ready: 'READY', needsEvidence: 'EVIDENCE', blocked: 'BLOCK' };
	const exposureQualityText: Record<string, string> = { quantCandidate: 'OPEN', qualitativeOnly: 'QUAL', blocked: 'LOCK' };
	const relevantDrivers = $derived(snapshot.drivers.filter((d) => d.relevance !== 'context').slice(0, 16));
	const contextDrivers = $derived(snapshot.drivers.filter((d) => d.relevance === 'context').slice(0, 18));
	const visibleDrivers = $derived([...relevantDrivers, ...contextDrivers]);
	const focusableIds = $derived(new Set([
		...snapshot.drivers.map((d) => d.id),
		...snapshot.transmissionEdges.map((e) => e.driverId),
		...snapshot.releaseRail.map((r) => r.driverId),
		...snapshot.sourcePackets.flatMap((p) => [p.driverId, p.seriesId]),
		...snapshot.contributionStacks.map((c) => c.driverId),
		...snapshot.coMoveGates.map((c) => c.driverId)
	].filter(Boolean)));
	const defaultFocusId = $derived(
		snapshot.topPressures.find((d) => focusableIds.has(d.id))?.id
		?? snapshot.coMoveGates.find((c) => c.points.length)?.driverId
		?? relevantDrivers.find((d) => focusableIds.has(d.id))?.id
		?? snapshot.drivers[0]?.id
		?? ''
	);
	const activeFocusId = $derived(localFocus && focusableIds.has(localFocus) ? localFocus : defaultFocusId);
	const focusDriver = $derived(activeFocusId ? snapshot.drivers.find((d) => d.id === activeFocusId) : null);
	const focusEdge = $derived(activeFocusId ? snapshot.transmissionEdges.find((e) => e.driverId === activeFocusId || e.sectorKey === activeFocusId) : null);
	const focusIndicator = $derived(activeFocusId ? snapshot.exposureIndicators.find((x) => x.seriesId === activeFocusId || x.sourceRefs.includes(activeFocusId)) : null);
	const focusFalsifiers = $derived(activeFocusId ? snapshot.falsifiers.filter((f) => !f.driverId || f.driverId === activeFocusId).slice(0, 3) : snapshot.falsifiers.slice(0, 3));
	const focusRelease = $derived(activeFocusId ? snapshot.releaseRail.find((r) => r.driverId === activeFocusId) : snapshot.releaseRail[0]);
	const focusSource = $derived(activeFocusId ? snapshot.sourcePackets.find((p) => p.driverId === activeFocusId || p.seriesId === activeFocusId) : snapshot.sourcePackets[0]);
	const focusContribution = $derived(activeFocusId ? snapshot.contributionStacks.find((c) => c.driverId === activeFocusId) : snapshot.contributionStacks[0]);
	const focusCoMove = $derived(activeFocusId ? snapshot.coMoveGates.find((c) => c.driverId === activeFocusId) : snapshot.coMoveGates[0]);
	const exposureRows = $derived(buildExposureRows());
	const gateRows = $derived(snapshot.evidenceGates);
	const econBlocked = (id: string) => !activeEcon.includes(id) && activeEcon.length >= ECON_MAX;
	let dialogEl = $state<HTMLDivElement | null>(null);
	function buildExposureRows(): { driver: MacroDriverView; cells: (MacroTransmissionEdgeView | null)[] }[] {
		const seen = new Set<string>();
		const drivers: MacroDriverView[] = [];
		for (const d of [...snapshot.topPressures, ...snapshot.drivers.filter((x) => x.relevance === 'secondary')]) {
			if (seen.has(d.id)) continue;
			seen.add(d.id);
			drivers.push(d);
		}
		return drivers.slice(0, 8).map((driver) => ({
			driver,
			cells: channels.map((ch) => snapshot.transmissionEdges.find((e) => e.driverId === driver.id && e.channel === ch.k) ?? null)
		}));
	}
	function sparkPoints(vals: number[]): string {
		if (!vals.length) return '';
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const span = max - min || 1;
		return vals.map((v, i) => `${(i / Math.max(1, vals.length - 1)) * 48},${18 - ((v - min) / span) * 16}`).join(' ');
	}
	const cellClass = (edge: MacroTransmissionEdgeView | null) => edge ? edge.confidence : 'none';
	const cellLabel = (edge: MacroTransmissionEdgeView) => edge.confidence === 'blocked' ? 'LOCK' : evidenceText[edge.evidenceLevel];
	const cellTitle = (edge: MacroTransmissionEdgeView | null, label: string) => edge ? `${label}: ${edge.financialLine} · ${edge.confidence} · ${edge.evidenceLevel}` : `${label}: 노출 경로 없음`;
	const gateLabel = (g: MacroLensSnapshot['evidenceGates'][number]) => T(g.labelKr, g.labelEn);
	const gateDetail = (g: MacroLensSnapshot['evidenceGates'][number]) => T(g.detailKr, g.detailEn);
	const pct = (v: number) => `${Math.max(4, Math.min(100, Math.round(v * 100)))}%`;
	const corrLeft = (corr: number | null) => `${Math.max(0, Math.min(100, ((corr ?? 0) + 1) * 50))}%`;
	function motionLabel(value: string | null | undefined): string {
		const raw = value ?? '—';
		if (lang === 'en') return raw;
		const key = raw.toLowerCase();
		return key === 'rising' ? '상승' : key === 'falling' ? '하락' : key === 'stable' ? '횡보' : raw;
	}
	function goto(tabName: MacroLensTab, id = '') {
		localFocus = id || activeFocusId;
		onTab(tabName);
	}
	function onDialogKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
		}
		e.stopPropagation();
	}
	$effect(() => {
		localFocus = focusId;
	});
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
			{T('노출 점검표입니다. 정량 민감도·투자 결론·가격 산출은 표시하지 않습니다.', 'Exposure checklist only. No quantitative sensitivity, investment call, or price output.')}
		</div>

		<div class="mlBody">
			{#if tab === 'regime'}
				<section class="mlPhaseStrip" aria-label="Macro phases">
					<div><span>KR</span><b>{snapshot.marketPhase.kr?.label ?? '—'}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.kr?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.kr?.inflation)}</em></div>
					<div><span>US</span><b>{snapshot.marketPhase.us?.label ?? '—'}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.us?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.us?.inflation)}</em></div>
					<div><span>{T('업종', 'Sector')}</span><b>{snapshot.sectorBinding.tailwind?.kr ?? snapshot.company.sector}</b><em>{snapshot.sectorBinding.tailwind ? `${snapshot.sectorBinding.tailwind.label} ${snapshot.sectorBinding.tailwind.blended.toFixed(2)}` : '—'}</em></div>
				</section>
				<section class="mlPulseStrip" aria-label="Macro pulse">
					{#each exposureRows.slice(0, 6) as row (row.driver.id)}
						<button class={'mlPulse ' + row.driver.pressureLevel} class:on={activeEcon.includes(row.driver.id) || activeFocusId === row.driver.id} disabled={econBlocked(row.driver.id)} onclick={() => { localFocus = row.driver.id; onToggleEcon?.(row.driver.id); }} title={econBlocked(row.driver.id) ? T('경제지표는 동시 3개까지', 'max 3 overlays') : T('차트 ECON 오버레이 토글', 'toggle ECON overlay')}>
							<span>{row.driver.label}</span>
							<b>{row.driver.value}</b>
							<em>{row.driver.change}</em>
							<svg viewBox="0 0 48 20" preserveAspectRatio="none" aria-hidden="true">
								<polyline points={sparkPoints(row.driver.spark)} />
							</svg>
						</button>
					{/each}
				</section>
				<section class="mlMatrix" aria-label="Macro exposure matrix">
					<div class="mlMatrixHead">
						<span>{T('변수', 'Driver')}</span>
						{#each channels as ch (ch.k)}<span>{T(ch.kr, ch.en)}</span>{/each}
					</div>
					{#each exposureRows as row (row.driver.id)}
						<div class="mlMatrixRow">
							<button class="mlMatrixDriver" onclick={() => goto('drivers', row.driver.id)} title={row.driver.sourceLineage}>
								<b>{row.driver.label}</b>
								<em>{row.driver.value} · {row.driver.asOf}</em>
							</button>
							{#each row.cells as edge, i (`${row.driver.id}-${channels[i].k}`)}
								<button class={'mlXCell ' + cellClass(edge)} onclick={() => edge && goto('transmission', edge.driverId)} title={cellTitle(edge, T(channels[i].kr, channels[i].en))}>
									{#if edge}
										<b>{signText[edge.sign]}</b><em>{cellLabel(edge)}</em>
									{:else}
										<span>·</span>
									{/if}
								</button>
							{/each}
						</div>
					{/each}
				</section>
				<section class="mlMobileDrillRail" aria-label="Mobile macro drilldown">
					{#each exposureRows.slice(0, 6) as row (row.driver.id)}
						<button class:focused={activeFocusId === row.driver.id} onclick={() => goto('transmission', row.driver.id)} title={row.driver.pressureReason}>
							<span>{row.driver.label}</span>
							<b>{row.driver.coMovement?.status === 'candidate' ? 'Co-move' : row.driver.pressureLevel.toUpperCase()}</b>
							<em>{row.driver.coMovement ? `corr ${row.driver.coMovement.corr > 0 ? '+' : ''}${row.driver.coMovement.corr.toFixed(2)}` : row.driver.freshness.label}</em>
						</button>
					{/each}
				</section>
				<section class="mlGateStrip" aria-label="Evidence gates">
					{#each gateRows as g (g.id)}
						<div class={'mlGate ' + g.status}>
							<span>{gateLabel(g)}</span>
							<b>{g.value}</b>
							<em title={g.sourceRef}>{gateDetail(g)}</em>
						</div>
					{/each}
				</section>
				<section class="mlReleaseRail" aria-label="Release rail">
					<div class="mlRailTitle"><span class="mlBlockK">Release Rail</span><b>{T('값을 다시 확인할 시점', 'When to re-check')}</b></div>
					<div class="mlRailRows">
						{#each snapshot.releaseRail.slice(0, 6) as r (r.driverId)}
							<button class={'mlRailItem ' + r.status} class:focused={activeFocusId === r.driverId} onclick={() => goto('transmission', r.driverId)} title={r.sourceRef}>
								<span>{r.label}</span>
								<b>{r.lastObservation}</b>
								<em>{r.frequency}</em>
								<i>{r.status.toUpperCase()} · next {r.nextCheck}</i>
							</button>
						{/each}
					</div>
				</section>
				<section class="mlLegend" aria-label="Legend">
					<span class="medium">MED/HIGH = {T('업종 경로 존재', 'sector path')}</span>
					<span class="low">LOW = {T('공통 매크로 맥락', 'context')}</span>
					<span class="blocked">BLOCK = {T('시계열 또는 회사 증거 부족', 'missing series/evidence')}</span>
					<span class="none">· = {T('표준 경로 없음', 'no mapped path')}</span>
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
						<div class={'mlDriverRow ' + d.relevance} class:focused={activeFocusId === d.id}>
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
				{#if focusDriver || focusEdge || focusIndicator}
					<section class="mlDrill">
						<div class="mlDrillCard">
							<span class="mlBlockK">{T('전파 chain', 'Transmission chain')}</span>
							<b>{(focusDriver?.label ?? focusEdge?.driverLabel ?? activeFocusId) || '—'}</b>
							<p>{focusEdge ? `${focusEdge.sectorLabel} → ${focusEdge.financialLine} → ${focusEdge.valuationLever}` : T('선택 driver의 표준 전파 경로가 아직 없습니다.', 'No mapped transmission chain for the selected driver yet.')}</p>
							<em>{focusEdge ? `${focusEdge.evidenceLevel} · ${focusEdge.confidence} · lag ${focusEdge.lagMonths ? `${focusEdge.lagMonths[0]}-${focusEdge.lagMonths[1]}M` : '—'}` : focusDriver?.sourceLineage ?? '—'}</em>
							<div class="mlEvidence compact">
								{#each (focusEdge?.requiredCompanyEvidence.length ? focusEdge.requiredCompanyEvidence : snapshot.exposureQuality.missingEvidence).slice(0, 3) as x (x)}<span>{x}</span>{/each}
								{#if !(focusEdge?.requiredCompanyEvidence.length || snapshot.exposureQuality.missingEvidence.length)}<span>OK</span>{/if}
							</div>
						</div>
						<div class="mlDrillCard">
							<span class="mlBlockK">{T('품질 gate', 'Quality gate')}</span>
							<b>{exposureQualityText[snapshot.exposureQuality.status] ?? snapshot.exposureQuality.status}</b>
							<p>{focusIndicator ? `${focusIndicator.label} · R² ${focusIndicator.rSquared ?? '—'} · nObs ${focusIndicator.nObs ?? '—'}` : snapshot.exposureQuality.reason}</p>
							<em>{focusIndicator?.window ?? snapshot.exposureQuality.window ?? T('window 없음', 'window missing')}</em>
						</div>
						<div class="mlDrillCard">
							<span class="mlBlockK">{T('contribution', 'contribution')}</span>
							<b>{focusContribution?.summary ?? '—'}</b>
							<div class="mlStackList">
								{#each focusContribution?.components ?? [] as c (c.id)}
									<div class="mlStackRow">
										<span>{c.label}</span>
										<div class="mlStackTrack"><i class={'mlStackFill ' + c.status} style={`width:${pct(c.value)}`}></i></div>
										<em>{Math.round(c.value * 100)}</em>
									</div>
								{/each}
							</div>
						</div>
						<div class="mlDrillCard">
							<span class="mlBlockK">{T('source packet', 'source packet')}</span>
							<b>{focusSource?.seriesId ?? focusIndicator?.seriesId ?? focusDriver?.seriesId ?? focusEdge?.driverId ?? '—'}</b>
							<div class="mlPacketGrid">
								<span>source</span><b>{focusSource?.source ?? '—'}</b>
								<span>unit</span><b>{focusSource?.unit ?? '—'}</b>
								<span>freq</span><b>{focusSource?.frequency ?? '—'}</b>
								<span>asOf</span><b>{focusSource?.asOf ?? '—'}</b>
								<span>latest</span><b>{focusSource ? `${focusSource.value} / ${focusSource.change}` : '—'}</b>
								<span>release</span><b>{focusRelease ? `${focusRelease.status} · ${focusRelease.nextCheck}` : '—'}</b>
							</div>
							<p>{focusSource?.lineage ?? focusIndicator?.sourceRef ?? focusEdge?.sourceRefs[0] ?? snapshot.exposureQuality.sourceRef}</p>
							{#each focusFalsifiers.slice(0, 1) as f (f.id)}<em>{f.label}: {f.detail}</em>{/each}
						</div>
					</section>
					{#if focusCoMove}
						<section class={'mlCoMovePanel ' + focusCoMove.status}>
							<div class="mlRailTitle"><span class="mlBlockK">Co-movement Gate</span><b>{focusCoMove.label}</b><em>{T('인과 아님', 'not causal')}</em></div>
							{#if focusCoMove.points.length}
								<div class="mlScatterPlot" aria-label="Monthly co-movement scatter">
									<i class="mlZeroX" style={`left:${focusCoMove.xZero}%`}></i>
									<i class="mlZeroY" style={`top:${focusCoMove.yZero}%`}></i>
									<span class="mlAxisLabel x">{T('macro 월말 Δ', 'macro month-end Δ')}</span>
									<span class="mlAxisLabel y">{T('종목 월수익률', 'stock MoM return')}</span>
									{#each focusCoMove.points as p (p.ym)}
										<b class:latest={p.latest} style={`left:${p.px}%;top:${p.py}%`} title={p.label}></b>
									{/each}
								</div>
							{:else}
								<div class="mlCorrPlot" aria-label="Co-movement correlation position">
									<span>-1</span><span>0</span><span>+1</span>
									<i style={`left:${corrLeft(focusCoMove.corr)}`}></i>
								</div>
							{/if}
							<div class="mlMiniList">
								<span>corr {focusCoMove.corr ?? '—'}</span>
								<span>n {focusCoMove.n ?? '—'}</span>
								<span>shown {focusCoMove.displayedPoints}</span>
								<span>{focusCoMove.lagLabel}</span>
								<span>{focusCoMove.window}</span>
								<span>x {focusCoMove.xRange}</span>
								<span>y {focusCoMove.yRange}</span>
								<span>{focusCoMove.status.toUpperCase()}</span>
							</div>
							<div class="mlCoLimits">
								<span>{focusCoMove.formula}</span>
								{#each focusCoMove.limitations as x (x)}<span>{x}</span>{/each}
							</div>
							<p>{focusCoMove.detail}</p>
						</section>
					{/if}
				{/if}
				<section class="mlGrid edgeGrid">
					{#each snapshot.transmissionEdges as e (e.id)}
						<div class="mlEdge" class:focused={activeFocusId === e.driverId || activeFocusId === e.sectorKey}>
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
						<div class="mlBlockTop"><span class="mlBlockK">{T('회사 checkpoint', 'Company checkpoints')}</span><b>{T('정량화 전 확인할 재무 위치', 'Financial checkpoints before quant claim')}</b></div>
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
				<div class="mlNote">{T('시나리오는 명시 가정이다. 예측·추천·가격 산출이 아니며 회사 손익 정량화는 별도 시뮬레이터 영역이다.', 'Scenarios are explicit assumptions, not forecasts, recommendations or price outputs.')}</div>
			{:else}
				<section class="mlGrid two">
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('출처', 'Sources')}</span><b>{T('source/date/value lineage', 'source/date/value lineage')}</b></div>
						{#each snapshot.sourcePackets.slice(0, 8) as p (p.driverId)}
							<button class={'mlSrcPacket ' + p.status} class:focused={activeFocusId === p.driverId} onclick={() => { localFocus = p.driverId; }} title={p.sourceRef}>
								<b>{p.seriesId}</b>
								<span>{p.source} · {p.unit} · {p.frequency}</span>
								<em>{p.asOf} · {p.value} · {p.transform}</em>
								<small>{p.artifactPath}</small>
							</button>
						{/each}
						<div class="mlSrcSep"></div>
						{#each snapshot.sourceRefs as s (s)}<div class="mlSrc">{s}</div>{/each}
					</div>
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('한계', 'Limits')}</span><b>{T('모르는 것은 숨기지 않음', 'Unknowns stay visible')}</b></div>
						<div class="mlLimitSub">{T('Release freshness', 'Release freshness')}</div>
						{#each snapshot.releaseRail.slice(0, 6) as r (r.driverId)}
							<div class={'mlSrc warn ' + r.status}><b>{r.status}</b> {r.label}: last {r.lastObservation} · next {r.nextCheck}<em>{r.frequency} · stale after {r.staleAfterDays}d</em></div>
						{/each}
						{#each snapshot.missing as m (m.id)}<div class="mlSrc warn"><b>{m.status}</b> {m.reason}<em>{m.sourceRef}</em></div>{/each}
						<div class={snapshot.exposureQuality.status === 'quantCandidate' ? 'mlSrc' : 'mlSrc warn'}><b>{exposureQualityText[snapshot.exposureQuality.status] ?? snapshot.exposureQuality.status}</b> {snapshot.exposureQuality.reason}</div>
						<div class="mlSrc warn">nObs/R²/window/frequency/lag: {snapshot.exposureQuality.nObs ?? '—'} / {snapshot.exposureQuality.rSquared ?? '—'} / {snapshot.exposureQuality.window ?? '—'} / {snapshot.exposureQuality.frequency ?? '—'} / {snapshot.exposureQuality.lagMonths ?? '—'}</div>
						<div class="mlSrc warn">{snapshot.exposureQuality.blockedReason || T('정량 후보 조건 충족', 'Quant candidate gate open')} · {snapshot.exposureQuality.sourceRef}</div>
						{#if snapshot.exposureQuality.missingEvidence.length}
							<div class="mlSrc warn">{T('필요 증거', 'Required evidence')}: {snapshot.exposureQuality.missingEvidence.join(' · ')}</div>
						{/if}
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
	.mlDrill { display: grid; grid-template-columns: 1.25fr 1fr 1fr 1.25fr; gap: 8px; }
	.mlDrillCard { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(251,146,60,.035); padding: 9px; }
	.mlDrillCard b { display: block; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
	.mlDrillCard p { margin: 6px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlDrillCard em { display: block; margin-top: 5px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9.5px; line-height: 1.3; overflow-wrap: anywhere; }
	.mlPhaseStrip, .mlPulseStrip, .mlGateStrip, .mlLegend { display: grid; gap: 8px; }
	.mlPhaseStrip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	.mlPhaseStrip div, .mlGate, .mlPulse { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 9px; }
	.mlPhaseStrip span, .mlGate span, .mlPulse span { display: block; color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	.mlPhaseStrip b, .mlGate b, .mlPulse b { display: block; margin-top: 4px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
	.mlPhaseStrip em, .mlGate em, .mlPulse em { display: block; margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlPulseStrip { grid-template-columns: repeat(6, minmax(0, 1fr)); }
	.mlPulse { color: var(--dl-ink); text-align: left; cursor: pointer; }
	.mlPulse:hover, .mlPulse.on { border-color: rgba(251,146,60,.55); background: rgba(251,146,60,.045); }
	.mlPulse:disabled { cursor: not-allowed; opacity: .5; }
	.mlPulse svg { width: 100%; height: 20px; margin-top: 5px; overflow: visible; }
	.mlPulse polyline { fill: none; stroke: var(--amber); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
	.mlMatrix { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; overflow: hidden; }
	.mlMatrixHead, .mlMatrixRow { display: grid; grid-template-columns: minmax(170px, 1.35fr) repeat(5, minmax(68px, .65fr)); gap: 0; align-items: stretch; }
	.mlMatrixHead { background: rgba(255,255,255,.025); color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	.mlMatrixHead span, .mlMatrixDriver, .mlXCell { min-width: 0; border: 0; border-left: 1px solid rgba(255,255,255,.045); border-top: 1px solid rgba(255,255,255,.045); background: transparent; color: var(--dl-ink); padding: 7px 8px; }
	.mlMatrixHead span:first-child, .mlMatrixDriver { border-left: 0; }
	.mlMatrixHead span { border-top: 0; }
	.mlMatrixDriver { text-align: left; cursor: pointer; }
	.mlMatrixDriver:hover { background: rgba(251,146,60,.04); }
	.mlMatrixDriver b, .mlMatrixDriver em { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlMatrixDriver b { font-size: 11px; }
	.mlMatrixDriver em { margin-top: 2px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlXCell { display: flex; align-items: center; justify-content: space-between; gap: 5px; min-height: 42px; cursor: pointer; }
	.mlXCell.none { cursor: default; color: var(--dl-ink-dim, #5b6473); }
	.mlXCell.high { background: rgba(52,211,153,.055); }
	.mlXCell.medium { background: rgba(251,146,60,.055); }
	.mlXCell.low { background: rgba(91,100,115,.13); }
	.mlXCell.blocked { background: rgba(248,113,113,.055); }
	.mlXCell:hover:not(.none) { box-shadow: inset 0 0 0 1px rgba(251,146,60,.45); }
	.mlXCell b { color: var(--amber); font-size: 13px; }
	.mlXCell em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-family: var(--dl-font-mono); font-size: 9px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlMobileDrillRail { display: none; }
	.mlGateStrip { grid-template-columns: repeat(5, minmax(0, 1fr)); }
	.mlGate.ok { border-color: rgba(52,211,153,.42); }
	.mlGate.watch { border-color: rgba(251,146,60,.42); }
	.mlGate.blocked { border-color: rgba(248,113,113,.42); }
	.mlGate.ok b { color: var(--good); }
	.mlGate.watch b { color: var(--warn); }
	.mlGate.blocked b { color: var(--dn); }
	.mlReleaseRail { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.014); padding: 9px; }
	.mlRailTitle { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlRailTitle b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
	.mlRailTitle em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlRailRows { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
	.mlRailItem { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.015); color: var(--dl-ink); text-align: left; padding: 7px; cursor: pointer; }
	.mlRailItem:hover, .mlRailItem.focused { border-color: rgba(251,146,60,.55); background: rgba(251,146,60,.04); }
	.mlRailItem.fresh { border-color: rgba(52,211,153,.28); }
	.mlRailItem.watch, .mlRailItem.unknown { border-color: rgba(251,146,60,.36); }
	.mlRailItem.stale { border-color: rgba(248,113,113,.42); }
	.mlRailItem span, .mlRailItem b, .mlRailItem em, .mlRailItem i { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlRailItem span { color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .04em; }
	.mlRailItem b { margin-top: 4px; font-family: var(--dl-font-mono); font-size: 11px; }
	.mlRailItem em, .mlRailItem i { margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; }
	.mlStackList { display: flex; flex-direction: column; gap: 5px; margin-top: 7px; }
	.mlStackRow { display: grid; grid-template-columns: 58px 1fr 26px; gap: 6px; align-items: center; min-width: 0; font-size: 9.5px; color: var(--dl-ink-dim, #5b6473); }
	.mlStackRow span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlStackRow em { margin: 0; color: var(--dl-ink-muted, #7b8493); font-size: 9px; text-align: right; }
	.mlStackTrack { height: 7px; border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; overflow: hidden; background: rgba(255,255,255,.025); }
	.mlStackFill { display: block; height: 100%; border-radius: 999px; background: var(--dl-ink-dim, #5b6473); }
	.mlStackFill.ok { background: rgba(52,211,153,.72); }
	.mlStackFill.watch { background: rgba(251,146,60,.72); }
	.mlStackFill.blocked { background: rgba(248,113,113,.65); }
	.mlPacketGrid { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 4px 7px; margin-top: 7px; align-items: baseline; }
	.mlPacketGrid span { color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlPacketGrid b { display: block; margin: 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; }
	.mlCoMovePanel { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.015); padding: 9px; }
	.mlCoMovePanel.candidate { border-color: rgba(52,211,153,.38); }
	.mlCoMovePanel.unstable { border-color: rgba(251,146,60,.36); }
	.mlCoMovePanel.missing { border-color: rgba(248,113,113,.36); }
	.mlCorrPlot { position: relative; display: grid; grid-template-columns: repeat(3, 1fr); height: 28px; margin-top: 8px; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: linear-gradient(90deg, rgba(248,113,113,.06), rgba(255,255,255,.02), rgba(52,211,153,.06)); overflow: hidden; }
	.mlCorrPlot span { display: flex; align-items: flex-end; padding: 0 5px 3px; color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 9px; }
	.mlCorrPlot span:nth-child(2) { justify-content: center; border-left: 1px solid rgba(255,255,255,.05); border-right: 1px solid rgba(255,255,255,.05); }
	.mlCorrPlot span:nth-child(3) { justify-content: flex-end; }
	.mlCorrPlot i { position: absolute; top: 5px; width: 8px; height: 18px; border: 1px solid var(--amber); border-radius: 999px; background: rgba(251,146,60,.35); transform: translateX(-50%); }
	.mlScatterPlot { position: relative; height: 126px; margin-top: 8px; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: linear-gradient(180deg, rgba(52,211,153,.035), rgba(255,255,255,.012) 48%, rgba(248,113,113,.035)); overflow: hidden; }
	.mlScatterPlot::before { content: ""; position: absolute; inset: 10px 12px 18px 24px; border-left: 1px solid rgba(255,255,255,.08); border-bottom: 1px solid rgba(255,255,255,.08); pointer-events: none; }
	.mlScatterPlot .mlZeroX, .mlScatterPlot .mlZeroY { position: absolute; display: block; pointer-events: none; background: rgba(255,255,255,.12); }
	.mlScatterPlot .mlZeroX { top: 8px; bottom: 15px; width: 1px; }
	.mlScatterPlot .mlZeroY { left: 20px; right: 10px; height: 1px; }
	.mlScatterPlot b { position: absolute; width: 5px; height: 5px; border: 1px solid rgba(148,163,184,.6); border-radius: 999px; background: rgba(148,163,184,.38); transform: translate(-50%, -50%); }
	.mlScatterPlot b.latest { width: 8px; height: 8px; border-color: var(--amber); background: rgba(251,146,60,.72); box-shadow: 0 0 0 3px rgba(251,146,60,.12); }
	.mlAxisLabel { position: absolute; color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlAxisLabel.x { right: 8px; bottom: 3px; }
	.mlAxisLabel.y { left: 5px; top: 8px; writing-mode: vertical-rl; transform: rotate(180deg); }
	.mlCoLimits { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px; }
	.mlCoLimits span { border: 1px solid rgba(251,146,60,.22); border-radius: 999px; color: var(--dl-ink-dim, #5b6473); background: rgba(251,146,60,.025); padding: 2px 7px; font-size: 9px; line-height: 1.25; }
	.mlCoMovePanel p { margin: 6px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10px; line-height: 1.35; }
	.mlLegend { grid-template-columns: repeat(4, minmax(0, 1fr)); }
	.mlLegend span { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; padding: 4px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlLegend .medium { border-color: rgba(251,146,60,.35); }
	.mlLegend .blocked { border-color: rgba(248,113,113,.35); }
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
	.mlEvidence { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
	.mlEvidence.compact { margin-top: 6px; }
	.mlEvidence span { border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; padding: 2px 7px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.up { color: var(--up); }
	.down { color: var(--dn); }
	.good { color: var(--good); }
	.warn { color: var(--warn); }
	.neutral { color: var(--dl-ink-dim, #5b6473); }
	.mlFocus { display: flex; gap: 8px; align-items: flex-start; border-color: rgba(251,146,60,.38); background: rgba(251,146,60,.06); }
	.mlFocusIcon { color: var(--amber); flex: 0 0 auto; margin-top: 1px; }
	.mlFocus div { display: flex; flex-direction: column; gap: 2px; }
	.mlFocus span { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlDriverTable { display: flex; flex-direction: column; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; overflow: hidden; }
	.mlDriverHead, .mlDriverRow { display: grid; grid-template-columns: minmax(190px, 1.7fr) 72px .7fr .6fr minmax(160px, 1.1fr) 86px; gap: 8px; align-items: center; padding: 6px 8px; }
	.mlDriverHead { font-size: 9px; font-weight: 800; color: var(--dl-ink-dim, #5b6473); background: rgba(255,255,255,.025); letter-spacing: .05em; }
	.mlDriverRow { font-size: 11px; border-top: 1px solid rgba(255,255,255,.045); }
	.mlDriverRow.primary { background: rgba(52,211,153,.035); }
	.mlDriverRow.secondary { background: rgba(251,146,60,.025); }
	.mlDriverRow.focused, .mlEdge.focused { outline: 1px solid var(--amber); outline-offset: -1px; }
	.mlDriverName { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
	.mlDriverName em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverScore { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; min-width: 0; }
	.mlDriverScore em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 8.5px; line-height: 1.2; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlScore { display: inline-flex; align-items: center; justify-content: center; min-width: 54px; height: 18px; border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; font-family: var(--dl-font-mono); font-size: 10px; padding: 0 4px; }
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
	.mlSrc b { color: var(--warn); font-family: var(--dl-font-mono); font-size: 10px; margin-right: 5px; text-transform: uppercase; }
	.mlSrc em { display: block; margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 10px; overflow-wrap: anywhere; }
	.mlSrcPacket { width: 100%; border: 0; border-top: 1px solid rgba(255,255,255,.045); background: transparent; color: inherit; text-align: left; padding: 7px 0; cursor: pointer; }
	.mlSrcPacket:hover, .mlSrcPacket.focused { background: rgba(251,146,60,.035); }
	.mlSrcPacket b, .mlSrcPacket span, .mlSrcPacket em, .mlSrcPacket small { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlSrcPacket b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlSrcPacket span { margin-top: 2px; color: var(--dl-ink-dim, #5b6473); font-size: 10px; }
	.mlSrcPacket em, .mlSrcPacket small { margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; }
	.mlSrcPacket.stale { border-left: 2px solid rgba(248,113,113,.52); padding-left: 6px; }
	.mlSrcPacket.watch, .mlSrcPacket.unknown { border-left: 2px solid rgba(251,146,60,.52); padding-left: 6px; }
	.mlSrcPacket.fresh { border-left: 2px solid rgba(52,211,153,.48); padding-left: 6px; }
	.mlSrcPacket.missing { border-left: 2px solid rgba(248,113,113,.75); padding-left: 6px; }
	.mlSrcSep { height: 8px; border-top: 1px dashed rgba(255,255,255,.08); }
	.mlLimitSub { margin-top: 8px; color: var(--amber); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	.mlNote { color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.45; border: 1px dashed var(--dl-line, #1b2130); border-radius: 5px; padding: 8px 10px; }
	@media (max-width: 760px) {
		.mlModal { height: min(780px, 94vh); }
		.mlGrid.two, .pressureGrid, .mlPhaseStrip, .mlPulseStrip, .mlGateStrip, .mlLegend, .mlDrill, .mlRailRows { grid-template-columns: 1fr; }
		.mlMatrix { overflow-x: auto; }
		.mlMatrixHead, .mlMatrixRow { min-width: 640px; }
		.mlMobileDrillRail { display: grid; grid-template-columns: 1fr; gap: 6px; }
		.mlMobileDrillRail button { display: grid; grid-template-columns: minmax(0, 1fr) 68px 82px; gap: 7px; align-items: center; min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); color: var(--dl-ink); padding: 8px; text-align: left; }
		.mlMobileDrillRail button.focused { border-color: rgba(251,146,60,.58); background: rgba(251,146,60,.045); }
		.mlMobileDrillRail span, .mlMobileDrillRail b, .mlMobileDrillRail em { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
		.mlMobileDrillRail span { font-size: 11px; font-weight: 800; }
		.mlMobileDrillRail b { color: var(--amber); font-family: var(--dl-font-mono); font-size: 9.5px; text-align: right; }
		.mlMobileDrillRail em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-family: var(--dl-font-mono); font-size: 9px; text-align: right; }
		.mlDriverHead, .mlDriverRow { grid-template-columns: minmax(132px, 1.3fr) 72px 76px; }
		.mlDriverHead span:nth-child(3), .mlDriverHead span:nth-child(4), .mlDriverHead span:nth-child(5), .mlDriverRow > span:nth-child(3), .mlDriverRow > span:nth-child(4), .mlDriverRow > span:nth-child(5) { display: none; }
	}
</style>
