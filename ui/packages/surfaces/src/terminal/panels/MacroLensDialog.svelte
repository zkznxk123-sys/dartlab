<script lang="ts">
	import { GitBranch, LineChart, ShieldAlert, X } from 'lucide-svelte';
	import type { Lang } from '../lib/types';
	import type { MacroChannel, MacroDriverView, MacroExposureMatrixRow, MacroLensSnapshot, MacroLensTab, MacroTransmissionEdgeView } from '../lib/macroLens';
	import { buildExposureMatrixRows, pickFocusCell } from '../lib/macroLens';
	import { ECON_MAX } from '../charts/chartState.svelte';
	import MacroPathRail from './MacroPathRail.svelte';
	import RegimePlaneHero from './RegimePlaneHero.svelte';
	import MacroCycleRisk from './MacroCycleRisk.svelte';

	interface Props {
		snapshot: MacroLensSnapshot;
		lang: Lang;
		// tab = 초기 스크롤 앵커(레거시 onMacroLens 시그니처 호환). 더 이상 탭 UI 아님 — 단일 캔버스.
		tab?: MacroLensTab;
		focusId?: string;
		activeEcon?: string[];
		onTab?: (tab: MacroLensTab) => void;
		onClose: () => void;
		onToggleEcon?: (id: string) => void;
		onSector?: (industryId: string) => void;
	}
	let { snapshot, lang, tab = 'dashboard', focusId = '', activeEcon = [], onTab, onClose, onToggleEcon, onSector }: Props = $props();
	let localFocus = $state('');
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const focusableSelector = [
		'a[href]',
		'button:not([disabled])',
		'input:not([disabled])',
		'select:not([disabled])',
		'textarea:not([disabled])',
		'summary',
		'[tabindex]:not([tabindex="-1"])'
	].join(',');
	const channels: { k: MacroChannel; kr: string; en: string }[] = [
		{ k: 'revenue', kr: '매출', en: 'Sales' },
		{ k: 'margin', kr: '마진', en: 'Margin' },
		{ k: 'balanceSheet', kr: '차입', en: 'Debt' },
		{ k: 'cashFlow', kr: '현금', en: 'Cash' },
		{ k: 'valuation', kr: '밸류', en: 'Value' }
	];
	const signText: Record<string, string> = { positive: '+', negative: '-', mixed: '±', unknown: '?' };
	const confidenceText: Record<string, string> = { high: 'HIGH', medium: 'MED', low: 'LOW', blocked: 'LOCK' };
	const severityCls: Record<string, string> = { info: 'info', warning: 'warn', blocker: 'block' };
	const pressureTextKr: Record<string, string> = { high: '검토우선', medium: '보조', low: '맥락', blocked: '차단' };
	const pressureTextEn: Record<string, string> = { high: 'REVIEW', medium: 'AUX', low: 'CONTEXT', blocked: 'BLOCKED' };
	const pressureText = (lvl: string): string => T(pressureTextKr[lvl] ?? lvl, pressureTextEn[lvl] ?? lvl);
	const readinessText: Record<string, string> = { ready: 'READY', needsEvidence: 'EVIDENCE', blocked: 'BLOCK' };
	const exposureQualityText: Record<string, string> = { quantCandidate: 'OPEN', qualitativeOnly: 'QUAL', blocked: 'LOCK' };
	const componentStatusText: Record<string, string> = { ok: 'OPEN', watch: 'WATCH', blocked: 'LOCK' };
	// 증거 상태 → CSS 도형 칩 클래스 (색=증거 상태 단일 축, 방향 아님). blocked edge=LOCK.
	const chipState = (edge: MacroTransmissionEdgeView): 'OBS' | 'PRIOR' | 'TPL' | 'LOCK' =>
		edge.confidence === 'blocked' ? 'LOCK' : edge.evidenceLevel === 'observed' ? 'OBS' : edge.evidenceLevel === 'sectorPrior' ? 'PRIOR' : 'TPL';
	const evidenceMicroLabel: Record<'OBS' | 'PRIOR' | 'TPL' | 'LOCK', { kr: string; en: string }> = {
		OBS: { kr: '관측', en: 'obs' },
		PRIOR: { kr: 'prior', en: 'prior' },
		TPL: { kr: '템플', en: 'tpl' },
		LOCK: { kr: '잠금', en: 'lock' }
	};
	const lagText = (edge: MacroTransmissionEdgeView): string => edge.lagMonths ? `${edge.lagMonths[0]}~${edge.lagMonths[1]}M` : '';
	const channelLabel = (ch: MacroChannel): string => {
		const c = channels.find((x) => x.k === ch);
		return c ? T(c.kr, c.en) : ch;
	};
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
	// Exposure Map 행 (view-model 이관 헬퍼). filledCount 내림차순·cap 6.
	const exposureRows = $derived(buildExposureMatrixRows(snapshot.drivers, snapshot.topPressures, snapshot.transmissionEdges, channels.map((c) => c.k)));
	// 초점 전파사슬 셀 (읽기 1차). 결정성 select. 셀 0개면 null → 폴백 카드.
	const focusCell = $derived(pickFocusCell(exposureRows));
	// 채널 열 클러스터: 켜진 채널만 열, 각 driver 칩을 자기 채널 열 아래로 모음(빈 셀 0).
	const mapColumns = $derived(buildMapColumns(exposureRows));
	const pulseDrivers = $derived(exposureRows.length ? exposureRows.slice(0, 6).map((r) => r.driver) : snapshot.topPressures.slice(0, 6));
	// 국면 렌즈(Regime Lens) — S2 MacroCycleRisk 가 시각으로 소비. macro.regime 부재 시 null(폴백).
	const regime = $derived(snapshot.regime);
	const usLens = $derived(regime?.us ?? null);
	const krLens = $derived(regime?.kr ?? null);
	// S5 Gate Strip = evidenceGates 중 quant 제외 4개(데이터·전파·동행·회사).
	const gateRows = $derived(snapshot.evidenceGates.filter((g) => g.id !== 'quant'));
	const exposureQualityClass = $derived(snapshot.exposureQuality.status === 'quantCandidate' ? 'ok' : snapshot.exposureQuality.status === 'qualitativeOnly' ? 'watch' : 'blocked');
	// 정량 LOCK 2케이스 정직 분기 (S5). status로 직접 분기 — UI 추론 0.
	const quantBlocks = $derived(snapshot.exposureQuality.status === 'quantCandidate'
		? [snapshot.exposureQuality.reason]
		: (snapshot.exposureQuality.blockedReason ? [snapshot.exposureQuality.blockedReason] : [snapshot.exposureQuality.reason]).filter(Boolean));
	const quantStatusLabel = $derived(
		snapshot.exposureQuality.status === 'blocked'
			? T('정량 LOCK · 회사 회귀 부재', 'Quant LOCK · company regression absent')
			: snapshot.exposureQuality.status === 'qualitativeOnly'
				? T('정량 QUAL · 정성 경로만', 'Quant QUAL · qualitative path only')
				: T('정량 OPEN', 'Quant OPEN')
	);
	const quantAltValue = $derived(T('대신 → 전파 동행(co-move) 반증·업종 prior 경로로 확인', 'Instead → verify via co-move falsifier / sector prior path'));
	const modelMetricRows = $derived([
		{ label: 'nObs', value: snapshot.exposureQuality.nObs != null ? String(snapshot.exposureQuality.nObs) : '—', status: snapshot.exposureQuality.nObs != null ? 'ok' : 'blocked' },
		{ label: 'R²', value: fmtR2(snapshot.exposureQuality.rSquared), status: snapshot.exposureQuality.rSquared != null ? 'ok' : 'blocked' },
		{ label: 'window', value: snapshot.exposureQuality.window ?? '—', status: snapshot.exposureQuality.window ? 'ok' : 'blocked' },
		{ label: 'freq', value: snapshot.exposureQuality.frequency ?? '—', status: snapshot.exposureQuality.frequency ? 'ok' : 'blocked' },
		{ label: 'lag', value: snapshot.exposureQuality.lagMonths != null ? `${snapshot.exposureQuality.lagMonths}M` : '—', status: snapshot.exposureQuality.lagMonths != null ? 'ok' : 'blocked' },
		{ label: 'coverage', value: snapshot.exposureQuality.coverage, status: snapshot.exposureQuality.coverage === 'company' ? 'ok' : snapshot.exposureQuality.coverage === 'sectorOnly' ? 'watch' : 'blocked' }
	]);
	const econBlocked = (id: string) => !activeEcon.includes(id) && activeEcon.length >= ECON_MAX;
	let dialogEl = $state<HTMLDivElement | null>(null);
	function fmtR2(value: number | null | undefined): string {
		if (value == null) return '—';
		return value.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
	}
	// 채널 열 클러스터 빌드: 켜진 채널만 열로, 각 열 아래 닿는 driver 칩(빈 셀 미렌더).
	function buildMapColumns(rows: MacroExposureMatrixRow[]): { channel: MacroChannel; cells: { driver: MacroDriverView; edge: MacroTransmissionEdgeView }[] }[] {
		const out: { channel: MacroChannel; cells: { driver: MacroDriverView; edge: MacroTransmissionEdgeView }[] }[] = [];
		channels.forEach((ch, i) => {
			const cells: { driver: MacroDriverView; edge: MacroTransmissionEdgeView }[] = [];
			for (const row of rows) {
				const edge = row.cells[i];
				if (edge) cells.push({ driver: row.driver, edge });
			}
			if (cells.length) out.push({ channel: ch.k, cells });
		});
		return out;
	}
	function sparkPoints(vals: number[]): string {
		if (!vals.length) return '';
		const min = Math.min(...vals);
		const max = Math.max(...vals);
		const span = max - min || 1;
		return vals.map((v, i) => `${(i / Math.max(1, vals.length - 1)) * 48},${18 - ((v - min) / span) * 16}`).join(' ');
	}
	const cellClass = (edge: MacroTransmissionEdgeView | null) => edge ? edge.evidenceLevel : 'none';
	const cellTitle = (edge: MacroTransmissionEdgeView, ch: MacroChannel): string => {
		const ev = chipState(edge);
		const evLabel = ev === 'OBS' ? T('섹터 관측(edge OBS·회사 회귀 아님)', 'sector observed (edge OBS · not company regression)')
			: ev === 'PRIOR' ? T('업종 추정(prior)', 'sector prior')
			: ev === 'LOCK' ? T('정량 잠금', 'quant lock')
			: T('표준 템플릿', 'standard template');
		const lag = edge.lagMonths ? `${T('지연', 'lag')} ${lagText(edge)}` : T('지연 직결', 'direct');
		return `${edge.driverLabel} → ${channelLabel(ch)} · ${evLabel} · ${T('부호', 'sign')} ${signText[edge.sign]} · ${lag}`;
	};
	const chipAria = (edge: MacroTransmissionEdgeView, ch: MacroChannel): string => {
		const ev = chipState(edge);
		const evLabel = ev === 'OBS' ? T('섹터 관측(edge OBS·회사 회귀 아님)', 'sector observed (edge OBS, not company regression)')
			: ev === 'PRIOR' ? T('업종 추정', 'sector prior')
			: ev === 'LOCK' ? T('정량 잠금', 'quant lock')
			: T('표준 템플릿', 'standard template');
		const lag = edge.lagMonths ? `${T('지연', 'lag')} ${lagText(edge)}` : T('지연 직결', 'direct');
		return `${edge.driverLabel}→${channelLabel(ch)}, ${evLabel}, ${T('부호', 'sign')} ${signText[edge.sign]}, ${lag}`;
	};
	const gateLabel = (g: MacroLensSnapshot['evidenceGates'][number]) => T(g.labelKr, g.labelEn);
	const gateDetail = (g: MacroLensSnapshot['evidenceGates'][number]) => T(g.detailKr, g.detailEn);
	const pct = (v: number) => `${Math.max(4, Math.min(100, Math.round(v * 100)))}%`;
	const corrLeft = (corr: number | null) => `${Math.max(0, Math.min(100, ((corr ?? 0) + 1) * 50))}%`;
	// 포커스 설정 + 전파 섹션(S4)으로 스크롤 — 옛 goto(tab,id)의 탭 전환을 대체.
	function setFocus(id: string) {
		localFocus = id || activeFocusId;
		if (typeof document !== 'undefined') {
			queueMicrotask(() => dialogEl?.querySelector('#macroS4')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
		}
	}
	function visibleFocusableElements(): HTMLElement[] {
		if (!dialogEl) return [];
		return Array.from(dialogEl.querySelectorAll<HTMLElement>(focusableSelector))
			.filter((el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true' && (el.offsetParent !== null || el === document.activeElement));
	}
	function onDialogKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
			return;
		}
		if (e.key === 'Tab') {
			const focusable = visibleFocusableElements();
			if (!focusable.length) {
				e.preventDefault();
				dialogEl?.focus();
				return;
			}
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
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
				<span>{T(snapshot.company.sector.kr, snapshot.company.sector.en)}</span>
			</div>
			<button class="scrClose" onclick={onClose} aria-label="close"><X size={14} /></button>
		</div>

		<!-- 단일 캔버스(탭 0). 위→아래 매크로 내러티브: 국면 → 사이클·위험 → 드라이버 → 전파 → 출처/한계. -->
		<div class="mlBody">
			<!-- S1 — 국면 평면(히어로): 지금 어디인가 -->
			{#if snapshot.glance}
				<RegimePlaneHero view={snapshot.glance.regime} {lang} />
			{/if}

			<!-- S2 — 사이클 & 침체위험: 어디로 가는가 (probit 다이얼·수익률곡선·사이클 링·신호등) -->
			<MacroCycleRisk us={usLens} kr={krLens} quadrant={snapshot.glance?.regime ?? null} {lang} />

			<!-- S3 — 드라이버 펄스: 무엇이 움직이는가 (클릭=차트 ECON 오버레이) -->
			<section class="mlSection" aria-label={T('거시 펄스', 'Macro pulse')}>
				<div class="mlSecHead"><span class="mlBlockK">DRIVERS</span><b>{T('거시 펄스 — 클릭하면 가격 차트에 겹쳐 봅니다', 'Macro pulse — click to overlay on the price chart')}</b></div>
				<div class="mlPulseStrip">
					{#each pulseDrivers as d (d.id)}
						<button class={'mlPulse ' + d.pressureLevel} class:on={activeEcon.includes(d.id) || activeFocusId === d.id} aria-pressed={activeEcon.includes(d.id)} disabled={econBlocked(d.id)} onclick={() => { localFocus = d.id; onToggleEcon?.(d.id); }} title={econBlocked(d.id) ? T('경제지표는 동시 3개까지', 'max 3 overlays') : `${d.value} · ${d.asOf} · ${d.source}`}>
							<span>{d.label}</span>
							<b>{d.value}</b>
							<em>{d.change} · {d.asOf || d.freshness.label}</em>
							<svg viewBox="0 0 48 20" preserveAspectRatio="none" aria-hidden="true">
								<polyline points={sparkPoints(d.spark)} />
							</svg>
						</button>
					{/each}
				</div>
			</section>

			<!-- S4 — 전파: 이 회사에 어떻게 닿는가 (시각 흐름 + 노출 지도 + 동행 산점도) -->
			<section class="mlSection" id="macroS4" aria-label={T('전파 경로', 'Transmission')}>
				<div class="mlSecHead"><span class="mlBlockK">TRANSMISSION</span><b>{T('이 회사에 어떻게 닿는가 — 거시 → 재무 → 밸류', 'How it reaches this company — macro → financials → value')}</b></div>
				{#if snapshot.macroPath}
					<MacroPathRail view={snapshot.macroPath} {lang} mode="full" onSector={onSector} />
				{/if}

				<!-- 노출 지도 -->
				<section class="mlMap" aria-label={T('노출 지도', 'Exposure Map')}>
					{#if focusCell}
						<div class="mlMapFocus">
							<div class="mlMapChain">
								<b>{focusCell.edge.driverLabel}</b>
								{#if focusCell.edge.lagMonths}<i class="mlChainLag">{lagText(focusCell.edge)}</i>{/if}
								<i class="mlChainArrow" aria-hidden="true">▶</i>
								<b>{focusCell.edge.financialLine}</b>
								<i class="mlChainLever">{focusCell.edge.valuationLever}</i>
								<i class="mlChainArrow" aria-hidden="true">▶</i>
								<b>{channelLabel(focusCell.channel)}</b>
							</div>
							<div class="mlMapEvidence">
								<span class={'mlMapChip ' + chipState(focusCell.edge)} aria-hidden="true"></span>
								<em>{T('증거', 'evidence')}: {chipState(focusCell.edge) === 'OBS' ? T('섹터 관측(edge OBS·회사 회귀 아님)', 'sector observed (edge OBS · not company regression)') : chipState(focusCell.edge) === 'PRIOR' ? T('업종 추정(prior)', 'sector prior') : chipState(focusCell.edge) === 'LOCK' ? T('정량 잠금', 'quant lock') : T('표준 템플릿', 'standard template')}</em>
								<i class="mlMapSign">{signText[focusCell.edge.sign]}</i>
								<i class="mlMapMeta">{focusCell.driver.value} · {focusCell.driver.change} · {focusCell.driver.asOf} · {focusCell.driver.source}</i>
							</div>
						</div>
					{:else}
						<div class="mlMapFocus">
							<div class="mlMapChain"><b>{T('표준 전파 경로 없음 — 아래 닷그리드/심화 확인', 'No mapped transmission path — see dot grid / advanced below')}</b></div>
						</div>
					{/if}

					<div class="mlMapGrid" aria-label={T('채널 닷그리드', 'channel dot grid')}>
						{#if mapColumns.length}
							<div class="mlMapHead">
								{#each mapColumns as col (col.channel)}<span>{channelLabel(col.channel)}</span>{/each}
							</div>
							<div class="mlMapRow">
								{#each mapColumns as col (col.channel)}
									<div class="mlMapCol">
										{#each col.cells as cell (`${cell.driver.id}-${col.channel}`)}
											<button class={'mlMapCell ' + cellClass(cell.edge)} onclick={() => setFocus(cell.edge.driverId)} title={cellTitle(cell.edge, col.channel)} aria-label={chipAria(cell.edge, col.channel)}>
												<span class={'mlMapChip ' + chipState(cell.edge)} aria-hidden="true"></span>
												<b>{cell.driver.label}</b>
												<i class="mlMapSign">{signText[cell.edge.sign]}</i>
												<em>{T(evidenceMicroLabel[chipState(cell.edge)].kr, evidenceMicroLabel[chipState(cell.edge)].en)}</em>
											</button>
										{/each}
									</div>
								{/each}
							</div>
							<div class="mlMapLegend" aria-label={T('증거 칩 범례', 'evidence chip legend')}>
								<span><i class="mlMapChip OBS"></i>{T('관측', 'obs')}</span>
								<span><i class="mlMapChip PRIOR"></i>{T('업종 prior', 'prior')}</span>
								<span><i class="mlMapChip TPL"></i>{T('템플', 'tpl')}</span>
								<span><i class="mlMapChip LOCK"></i>{T('잠금', 'lock')}</span>
							</div>
							<div class="mlMapNote">{T('색=증거 상태(방향 아님) · 닿는 채널만 표시', 'Color = evidence state (not direction) · only mapped channels shown')}</div>
						{:else}
							<div class="mlMapNote">{T('표시 가능한 전파 채널 없음 — 심화 확인', 'No mappable transmission channel — see advanced')}</div>
						{/if}
					</div>
				</section>

				<!-- 동행 산점도 (회사 선택 시) — macro Δ vs 종목 수익률. 인과 아님. -->
				{#if focusCoMove && focusCoMove.points.length}
					<section class={'mlCoMovePanel ' + focusCoMove.status}>
						<div class="mlRailTitle"><span class="mlBlockK">{T('동행성', 'Co-movement')}</span><b>{focusCoMove.label}</b><em>{T('인과 아님', 'not causal')}</em></div>
						<div class="mlScatterPlot" aria-label={T('월별 동행 산점도', 'Monthly co-movement scatter')}>
							<i class="mlZeroX" style={`left:${focusCoMove.xZero}%`}></i>
							<i class="mlZeroY" style={`top:${focusCoMove.yZero}%`}></i>
							<span class="mlAxisLabel x">{T('macro 월말 Δ', 'macro month-end Δ')}</span>
							<span class="mlAxisLabel y">{T('종목 월수익률', 'stock MoM return')}</span>
							{#each focusCoMove.points as p (p.ym)}
								<b class:latest={p.latest} style={`left:${p.px}%;top:${p.py}%`} title={p.label}></b>
							{/each}
						</div>
						<div class="mlMiniList">
							<span>corr {focusCoMove.corr ?? '—'}</span>
							<span>n {focusCoMove.n ?? '—'}</span>
							<span>{focusCoMove.lagLabel}</span>
							<span>{focusCoMove.window}</span>
						</div>
					</section>
				{/if}
			</section>

			<!-- S5 — 출처 · 한계 · 심화 (단일 접힘 fold. 정직 보존, 화면 비지배). -->
			<details class="mlFold">
				<summary><span class="mlBlockK">SOURCES · LIMITS</span><b>{T('출처 · 한계 · 심화 (게이트 · 시나리오 · 지표)', 'Sources · limits · advanced (gates · scenarios · drivers)')}</b><i class="mlFoldCaret" aria-hidden="true">▾</i></summary>
				<div class="mlFoldBody">
					<!-- 증거 게이트 + 릴리즈 레일 -->
					<section class="mlDashGate" aria-label={T('증거 게이트와 릴리즈 레일', 'Evidence gates and release rail')}>
						<div class="mlGateStrip">
							{#each gateRows as g (g.id)}
								<div class={'mlGate ' + g.status}>
									<span>{gateLabel(g)}</span>
									<b>{g.value}</b>
									<em title={g.sourceRef}>{gateDetail(g)}</em>
								</div>
							{/each}
						</div>
						<div class="mlReleaseRail">
							<div class="mlRailTitle"><span class="mlBlockK">{T('갱신 시점', 'Release rail')}</span><b>{T('값을 다시 확인할 시점', 'When to re-check')}</b></div>
							<div class="mlRailRows">
								{#each snapshot.releaseRail.slice(0, 6) as r (r.driverId)}
									<button class={'mlRailItem ' + r.status} class:focused={activeFocusId === r.driverId} onclick={() => setFocus(r.driverId)} title={r.sourceRef}>
										<span>{r.label}</span>
										<b>{r.lastObservation}</b>
										<em>{r.frequency}</em>
										<i>{r.status.toUpperCase()} · next {r.nextCheck}</i>
									</button>
								{/each}
							</div>
						</div>
					</section>

					<!-- 출처 + 한계 -->
					<section class="mlGrid two">
						<div class="mlBlock">
							<div class="mlBlockTop"><span class="mlBlockK">{T('출처', 'Sources')}</span></div>
							{#each snapshot.sourcePackets.slice(0, 8) as p (p.driverId)}
								<button class={'mlSrcPacket ' + p.status} class:focused={activeFocusId === p.driverId} onclick={() => { localFocus = p.driverId; }} title={p.sourceRef}>
									<b>{p.seriesId}</b>
									<span>{p.source} · {p.unit} · {p.frequency}</span>
									<em>{p.asOf} · {p.value} · {p.transform}</em>
									<small>{p.artifactPath}</small>
								</button>
							{/each}
							<div class="mlSrcSep"></div>
							{#each snapshot.sourceRefs.filter((s) => !s.includes('/')) as s, i (`${s}-${i}`)}<div class="mlSrc">{s}</div>{/each}
						</div>
						<div class="mlBlock">
							<div class="mlBlockTop"><span class="mlBlockK">{T('한계·결손', 'Limits')}</span></div>
							<div class={'mlQuantCard ' + exposureQualityClass} aria-label={T('정량 게이트 상태', 'Quant gate status')}>
								<div class="mlQuantTop">
									<span class="mlBlockK">{T('정량 게이트', 'Quant gate')}</span>
									<b>{quantStatusLabel}</b>
								</div>
								{#each quantBlocks as b (b)}<p>{b}</p>{/each}
								{#if snapshot.exposureQuality.status !== 'quantCandidate'}
									<div class="mlQuantAlt">{quantAltValue}</div>
								{/if}
							</div>
							<div class={'mlQualityCard ' + exposureQualityClass} aria-label={T('품질 게이트 모델 카드', 'Quality gate model card')}>
								<div class="mlQualityTop">
									<span class="mlBlockK">{T('품질 게이트', 'Quality gate')}</span>
									<b>{exposureQualityText[snapshot.exposureQuality.status] ?? snapshot.exposureQuality.status}</b>
								</div>
								<p>{snapshot.exposureQuality.reason}</p>
								<div class="mlModelMetrics">
									{#each modelMetricRows as r (r.label)}
										<div class={'mlModelMetric ' + r.status}>
											<span>{r.label}</span>
											<b>{r.value}</b>
										</div>
									{/each}
								</div>
							</div>
							<div class="mlLimitSub">{T('회사 지표', 'Company indicators')}</div>
							<div class="mlIndicatorGrid" aria-label={T('선택 회사 거시 지표', 'Selected company macro indicators')}>
								{#each snapshot.exposureIndicators.slice(0, 4) as x, i (`${x.seriesId}-${x.axis}-${i}`)}
									<div class={'mlIndicatorCard ' + (x.coverage === 'company' ? 'ok' : x.coverage === 'sectorOnly' ? 'watch' : 'blocked')}>
										<div><span>{x.axis}</span><b>{x.seriesId}</b></div>
										<em>{x.label} · {x.frequency ?? '—'} · lag {x.lagMonths ?? '—'}M</em>
										<div class="mlIndicatorStats">
											<span>n {x.nObs ?? '—'}</span>
											<span>R² {fmtR2(x.rSquared)}</span>
											<span>{x.targetMetric ?? x.window ?? '—'}</span>
										</div>
									</div>
								{:else}
									<div class="mlIndicatorCard blocked">
										<div><span>{T('지표', 'indicator')}</span><b>LOCK</b></div>
										<em>{T('선택된 회사별 거시 노출 지표 없음', 'No company-level macro exposure indicator')}</em>
									</div>
								{/each}
							</div>
							<div class="mlLimitSub">{T('결손 항목', 'Missing items')}</div>
							<div class="mlMissingLedger" aria-label={T('결손 증거 원장', 'Missing evidence ledger')}>
								{#each snapshot.exposureQuality.missingEvidence as x (x)}
									<div class="mlMissingItem blocked"><b>{T('필요', 'required')}</b><span>{x}</span></div>
								{/each}
								{#each snapshot.missing as m (m.id)}
									<div class={'mlMissingItem ' + (m.status === 'partial' || m.status === 'staleRisk' ? 'watch' : 'blocked')}><b>{T('한계', 'note')}</b><span>{m.reason}</span></div>
								{/each}
								{#if !snapshot.exposureQuality.missingEvidence.length && !snapshot.missing.length}
									<div class="mlMissingItem ok"><b>OK</b><span>{T('표시 가능한 결손 없음', 'No visible missing item')}</span></div>
								{/if}
							</div>
						</div>
					</section>

					<!-- 심화 — 초점 드릴 · 기여 · edge · 시나리오 · 드라이버 표 · 체크포인트 · 반증 -->
					{#if focusDriver || focusEdge || focusIndicator}
						<section class="mlDrill">
							<div class="mlDrillCard">
								<span class="mlBlockK">{T('전파 경로', 'Transmission chain')}</span>
								<b>{(focusDriver?.label ?? focusEdge?.driverLabel ?? activeFocusId) || '—'}</b>
								<p>{focusEdge ? `${focusEdge.sectorLabel} → ${focusEdge.financialLine} → ${focusEdge.valuationLever}` : T('선택 driver의 표준 전파 경로가 아직 없습니다.', 'No mapped transmission chain for the selected driver yet.')}</p>
								<em>{focusEdge ? `${focusEdge.evidenceLevel} · ${focusEdge.confidence} · lag ${focusEdge.lagMonths ? `${focusEdge.lagMonths[0]}-${focusEdge.lagMonths[1]}M` : '—'}` : focusDriver?.sourceLineage ?? '—'}</em>
								<div class="mlEvidence compact">
									{#each (focusEdge?.requiredCompanyEvidence.length ? focusEdge.requiredCompanyEvidence : snapshot.exposureQuality.missingEvidence).slice(0, 3) as x (x)}<span>{x}</span>{/each}
									{#if !(focusEdge?.requiredCompanyEvidence.length || snapshot.exposureQuality.missingEvidence.length)}<span>OK</span>{/if}
								</div>
							</div>
							<div class="mlDrillCard">
								<span class="mlBlockK">{T('품질 게이트', 'Quality gate')}</span>
								<b>{exposureQualityText[snapshot.exposureQuality.status] ?? snapshot.exposureQuality.status}</b>
								<p>{focusIndicator ? `${focusIndicator.label} · R² ${focusIndicator.rSquared ?? '—'} · nObs ${focusIndicator.nObs ?? '—'}` : snapshot.exposureQuality.reason}</p>
								<em>{focusIndicator?.window ?? snapshot.exposureQuality.window ?? T('window 없음', 'window missing')}</em>
							</div>
							<div class="mlDrillCard">
								<span class="mlBlockK">{T('기여', 'Contribution')}</span>
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
								<span class="mlBlockK">{T('출처', 'Source')}</span>
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
					{/if}
					{#if focusEdge}
						<section class="mlFocus">
							<GitBranch class="mlFocusIcon" size={15} />
							<div><b>{focusEdge.driverLabel} → {focusEdge.financialLine}</b><span>{focusEdge.note}</span></div>
						</section>
					{/if}

					<div class="mlEdgeDetails" role="group">
						<div class="mlEdgeDetailsHead"><span class="mlBlockK">{T('상세 edge 카드', 'Detailed edge cards')} · {snapshot.transmissionEdges.length}</span></div>
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
										<span>{T(evidenceMicroLabel[chipState(e)].kr, evidenceMicroLabel[chipState(e)].en)}</span>
									</div>
									<div class="mlEvidence">
										{#each e.requiredCompanyEvidence.slice(0, 3) as x (x)}<span>{x}</span>{/each}
									</div>
								</div>
							{/each}
						</section>
					</div>

					<div class="mlEdgeDetails" role="group">
						<div class="mlEdgeDetailsHead"><span class="mlBlockK">{T('시나리오 · 상세 지표', 'Scenarios · detailed drivers')}</span></div>
						<section class="mlGrid scenarioGrid">
							{#each snapshot.scenarios as s (s.id)}
								<div class={'mlScenario ' + s.readiness.status}>
									<div class="mlBlockTop"><span class="mlBlockK">{s.shock}</span><em>{readinessText[s.readiness.status]}</em></div>
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
						<div class="mlDriverTable">
							<div class="mlDriverHead">
								<span>{T('Driver', 'Driver')}</span><span>{T('품질', 'Quality')}</span><span>{T('값', 'Value')}</span><span>{T('변화', 'Chg')}</span><span>{T('계보', 'Lineage')}</span><span>{T('동작', 'Action')}</span>
							</div>
							{#each visibleDrivers as d (d.id)}
								<div class={'mlDriverRow ' + d.relevance} class:focused={activeFocusId === d.id}>
									<span class="mlDriverName"><b>{d.label}</b><em>{d.id} · {d.group} · {d.directionSemantics}</em></span>
									<span class="mlDriverScore"><b class={'mlScore ' + d.pressureLevel}>{pressureText(d.pressureLevel)}</b><em>{d.qualityHint}</em></span>
									<span class="mono">{d.value}</span>
									<span class="mono">{d.change}</span>
									<span class="mlDriverLine">{d.sourceLineage}{#if d.coMovement}<em>{d.coMovement.label}</em><small>{T('동행상관 · 인과 아님', 'co-movement · not causal')}</small>{/if}</span>
									<span>
										<button class="mlIconBtn" class:on={activeEcon.includes(d.id)} aria-pressed={activeEcon.includes(d.id)} disabled={econBlocked(d.id)} onclick={() => onToggleEcon?.(d.id)} title={econBlocked(d.id) ? T('동시 3개까지 표시됩니다', 'max 3 overlays') : T('차트 ECON 오버레이 토글', 'toggle chart ECON overlay')}>
											<LineChart size={12} />{activeEcon.includes(d.id) ? 'ON' : econBlocked(d.id) ? 'MAX' : 'ECON'}
										</button>
									</span>
								</div>
							{/each}
						</div>
					</div>

					<section class="mlGrid two">
						<div class="mlBlock">
							<div class="mlBlockTop"><span class="mlBlockK">{T('회사 체크포인트', 'Company checkpoints')}</span></div>
							{#each snapshot.companyCheckpoints as c (c.id)}
								<div class="mlCheck">
									<span>{c.label}</span><b class={c.tone}>{c.value}</b><em>{c.reason}</em>
								</div>
							{/each}
						</div>
						<div class="mlBlock">
							<div class="mlBlockTop"><span class="mlBlockK">{T('반증 조건', 'Falsifiers')}</span></div>
							{#each snapshot.falsifiers as f (f.id)}
								<div class={'mlFalse ' + severityCls[f.severity]}>
									<ShieldAlert class={'mlFalseIcon ' + severityCls[f.severity]} size={13} />
									<div><b>{f.label}</b><span>{f.detail}</span></div>
								</div>
							{/each}
						</div>
					</section>
					<div class="mlSrc">{T('상관은 인과가 아니며, 지표 변화가 회사 실적 변화를 보장하지 않는다.', 'Correlation is not causation; indicator moves do not guarantee company results.')}</div>
				</div>
			</details>
		</div>
	</div>
</div>

<style>
	.mlModal { width: min(960px, 96vw); height: 88vh; }
	.mlHead { flex-wrap: wrap; }
	.mlTitle { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlTitle b { font-size: 14px; }
	.mlTitle .mono, .mlTitle span:last-child { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlKicker { font-family: var(--dl-font-mono); color: var(--amber); font-weight: 800; font-size: 10px; letter-spacing: .06em; }
	.mlBody { flex: 1 1 auto; min-height: 0; overflow: auto; padding: 12px; display: flex; flex-direction: column; gap: 12px; }
	/* 섹션 — 헤더(kicker + 한 줄 안내) + 본문 */
	.mlSection { display: flex; flex-direction: column; gap: 8px; }
	.mlSecHead { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
	.mlSecHead b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 600; color: var(--dim); }
	.mlGrid { display: grid; gap: 10px; }
	.mlGrid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.edgeGrid { grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); }
	.scenarioGrid { grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
	/* Driver Pulse — 데스크톱 가로 스트립(최대 6개 한 줄). */
	.mlPulseStrip, .mlGateStrip { display: grid; gap: 8px; }
	.mlPulseStrip { grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
	.mlGate, .mlPulse { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 9px; }
	.mlGate span, .mlPulse span { display: block; color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	.mlGate b, .mlPulse b { display: block; margin-top: 4px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
	.mlGate em, .mlPulse em { display: block; margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlPulse { color: var(--dl-ink); text-align: left; cursor: pointer; }
	.mlPulse:hover, .mlPulse.on { border-color: rgba(var(--amber-rgb),.55); background: rgba(var(--amber-rgb),.045); }
	.mlPulse:disabled { cursor: not-allowed; opacity: .5; }
	.mlPulse b { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
	.mlPulse svg { width: 100%; height: 20px; margin-top: 5px; overflow: visible; }
	.mlPulse polyline { fill: none; stroke: var(--amber); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
	/* Exposure Map */
	.mlMap { border: 1px solid var(--bd); background: var(--panel); border-radius: 8px; padding: 8px; }
	.mlMapFocus { opacity: 1; border-left: 2px solid var(--amber); background: color-mix(in srgb, var(--dim) 7%, var(--panel)); border-radius: 0 6px 6px 0; padding: 8px 10px; }
	.mlMapChain { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
	.mlMapChain b { font-size: 14px; font-weight: 700; line-height: 1.3; letter-spacing: -0.01em; color: var(--txt); }
	.mlMapChain i { font-style: normal; }
	.mlChainArrow { color: var(--amber); font-size: 12px; }
	.mlChainLag, .mlChainLever { border: 1px solid var(--bd); border-radius: 999px; padding: 1px 7px; color: var(--dl-ink-dim, #5b6473); font-family: var(--dl-font-mono); font-size: 9px; }
	.mlMapEvidence { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin-top: 7px; }
	.mlMapEvidence em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; opacity: 1; }
	.mlMapEvidence .mlMapSign { font-weight: 700; color: var(--txt); }
	.mlMapMeta { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-family: var(--dl-font-mono); font-size: 9.5px; opacity: 1; }
	.mlMapGrid { opacity: 0.82; border-top: 1px solid var(--bd); margin-top: 8px; padding-top: 8px; }
	.mlMapHead, .mlMapRow { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }
	.mlMapHead span { font-size: 11px; font-weight: 600; color: var(--dl-ink-dim, #5b6473); }
	.mlMapRow { margin-top: 6px; align-items: start; }
	.mlMapCol { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
	.mlMapCell { display: flex; align-items: center; gap: 5px; min-height: 28px; min-width: 40px; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.012); color: var(--txt); padding: 3px 7px; cursor: pointer; text-align: left; }
	.mlMapCell:hover { box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--amber) 45%, transparent); }
	.mlMapCell b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
	.mlMapCell .mlMapSign { font-weight: 700; font-size: 11px; color: var(--txt); }
	.mlMapCell em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 8px; }
	.mlMapNote { margin-top: 8px; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.3; }
	.mlMapLegend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
	.mlMapLegend span { display: inline-flex; align-items: center; gap: 5px; color: var(--dl-ink-dim, #5b6473); font-size: 9px; }
	.mlMapChip { display: inline-flex; flex: 0 0 auto; width: 16px; height: 16px; }
	.mlMapChip::before { content: ""; display: block; width: 16px; height: 16px; box-sizing: border-box; }
	.mlMapChip.OBS::before { border-radius: 50%; background: var(--dl-ink, #e8eaef); border: 1.5px solid var(--dl-ink, #e8eaef); }
	.mlMapChip.PRIOR::before { border-radius: 50%; border: 1.5px solid var(--amber); background: transparent; box-shadow: inset 8px 0 0 0 var(--amber); }
	.mlMapChip.TPL::before { border-radius: 50%; background: transparent; border: 1.5px dashed var(--dl-ink-dim, #6b7280); }
	.mlMapChip.LOCK::before { border-radius: 3px; border: 1px solid var(--dl-ink-faint, #4a5160); background: repeating-linear-gradient(45deg, transparent 0 2px, color-mix(in srgb, var(--dl-ink-faint, #4a5160) 45%, transparent) 2px 4px); }
	/* S5 single fold */
	.mlFold { border: 1px solid var(--dl-line, #1b2130); border-radius: 8px; background: rgba(255,255,255,.012); overflow: hidden; }
	.mlFold > summary { cursor: pointer; list-style: none; display: flex; align-items: center; gap: 8px; padding: 10px 12px; }
	.mlFold > summary::-webkit-details-marker { display: none; }
	.mlFold > summary b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 600; color: var(--dim); }
	.mlFold > summary:hover b { color: var(--amber); }
	.mlFoldCaret { font-style: normal; color: var(--amber); font-size: 10px; }
	.mlFold[open] > summary .mlFoldCaret { transform: rotate(180deg); }
	.mlFoldBody { display: flex; flex-direction: column; gap: 12px; padding: 0 12px 12px; border-top: 1px solid var(--dl-line, #1b2130); padding-top: 12px; }
	/* gate / rail */
	.mlDashGate { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.3fr); gap: 10px; align-items: start; }
	.mlGateStrip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.mlGate.ok { border-color: rgba(52,211,153,.42); }
	.mlGate.watch { border-color: rgba(var(--amber-rgb),.42); }
	.mlGate.blocked { border-color: rgba(248,113,113,.42); }
	.mlGate.ok b { color: var(--up); }
	.mlGate.watch b { color: var(--warn); }
	.mlGate.blocked b { color: var(--dn); }
	.mlReleaseRail { padding: 0; }
	.mlRailTitle { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlRailTitle b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
	.mlRailTitle em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlRailRows { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
	.mlRailItem { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.015); color: var(--dl-ink); text-align: left; padding: 7px; cursor: pointer; }
	.mlRailItem:hover, .mlRailItem.focused { border-color: rgba(var(--amber-rgb),.55); background: rgba(var(--amber-rgb),.04); }
	.mlRailItem.fresh { border-color: rgba(52,211,153,.28); }
	.mlRailItem.watch, .mlRailItem.unknown { border-color: rgba(var(--amber-rgb),.36); }
	.mlRailItem.stale { border-color: rgba(248,113,113,.42); }
	.mlRailItem span, .mlRailItem b, .mlRailItem em, .mlRailItem i { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlRailItem span { color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .04em; }
	.mlRailItem b { margin-top: 4px; font-family: var(--dl-font-mono); font-size: 11px; }
	.mlRailItem em, .mlRailItem i { margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; }
	/* drill */
	.mlBlock, .mlEdge, .mlScenario, .mlFocus { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 10px; min-width: 0; }
	.mlDrill { display: grid; grid-template-columns: 1.25fr 1fr 1fr 1.25fr; gap: 8px; }
	.mlDrillCard { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(var(--amber-rgb),.035); padding: 9px; }
	.mlDrillCard b { display: block; margin-top: 5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
	.mlDrillCard p { margin: 6px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlDrillCard em { display: block; margin-top: 5px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9.5px; line-height: 1.3; overflow-wrap: anywhere; }
	.mlStackList { display: flex; flex-direction: column; gap: 5px; margin-top: 7px; }
	.mlStackRow { display: grid; grid-template-columns: 58px 1fr 26px; gap: 6px; align-items: center; min-width: 0; font-size: 9.5px; color: var(--dl-ink-dim, #5b6473); }
	.mlStackRow span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlStackRow em { margin: 0; color: var(--dl-ink-muted, #7b8493); font-size: 9px; text-align: right; }
	.mlStackTrack { height: 7px; border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; overflow: hidden; background: rgba(255,255,255,.025); }
	.mlStackFill { display: block; height: 100%; border-radius: 999px; background: var(--dl-ink-dim, #5b6473); }
	.mlStackFill.ok { background: rgba(52,211,153,.72); }
	.mlStackFill.watch { background: rgba(var(--amber-rgb),.72); }
	.mlStackFill.blocked { background: rgba(248,113,113,.65); }
	.mlPacketGrid { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 4px 7px; margin-top: 7px; align-items: baseline; }
	.mlPacketGrid span { color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlPacketGrid b { display: block; margin: 0; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 10px; }
	/* co-move */
	.mlCoMovePanel { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.015); padding: 9px; }
	.mlCoMovePanel.candidate { border-color: rgba(52,211,153,.38); }
	.mlCoMovePanel.unstable { border-color: rgba(var(--amber-rgb),.36); }
	.mlCoMovePanel.missing { border-color: rgba(248,113,113,.36); }
	.mlScatterPlot { position: relative; height: 126px; margin-top: 8px; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: linear-gradient(180deg, rgba(52,211,153,.035), rgba(255,255,255,.012) 48%, rgba(248,113,113,.035)); overflow: hidden; }
	.mlScatterPlot::before { content: ""; position: absolute; inset: 10px 12px 18px 24px; border-left: 1px solid rgba(255,255,255,.08); border-bottom: 1px solid rgba(255,255,255,.08); pointer-events: none; }
	.mlScatterPlot .mlZeroX, .mlScatterPlot .mlZeroY { position: absolute; display: block; pointer-events: none; background: rgba(255,255,255,.12); }
	.mlScatterPlot .mlZeroX { top: 8px; bottom: 15px; width: 1px; }
	.mlScatterPlot .mlZeroY { left: 20px; right: 10px; height: 1px; }
	.mlScatterPlot b { position: absolute; width: 5px; height: 5px; border: 1px solid rgba(148,163,184,.6); border-radius: 999px; background: rgba(148,163,184,.38); transform: translate(-50%, -50%); }
	.mlScatterPlot b.latest { width: 8px; height: 8px; border-color: var(--amber); background: rgba(var(--amber-rgb),.72); box-shadow: 0 0 0 3px rgba(var(--amber-rgb),.12); }
	.mlAxisLabel { position: absolute; color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlAxisLabel.x { right: 8px; bottom: 3px; }
	.mlAxisLabel.y { left: 5px; top: 8px; writing-mode: vertical-rl; transform: rotate(180deg); }
	.mlBlockTop, .mlEdgeTop { display: flex; align-items: center; gap: 7px; min-width: 0; }
	.mlBlockK { font-size: 9px; font-weight: 800; color: var(--amber); letter-spacing: .06em; text-transform: uppercase; flex: 0 0 auto; }
	.mlMiniList { display: flex; flex-wrap: wrap; gap: 8px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); margin-top: 6px; }
	.mlBlock p, .mlEdge p, .mlScenario p { margin: 7px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 11px; line-height: 1.45; }
	.mlEvidence { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
	.mlEvidence.compact { margin-top: 6px; }
	.mlEvidence span { border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; padding: 2px 7px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.up { color: var(--up); }
	.down { color: var(--dn); }
	.good { color: var(--good); }
	.warn { color: var(--warn); }
	.neutral { color: var(--dl-ink-dim, #5b6473); }
	.mlFocus { display: flex; gap: 8px; align-items: flex-start; border-color: rgba(var(--amber-rgb),.38); background: rgba(var(--amber-rgb),.06); }
	.mlFocusIcon { color: var(--amber); flex: 0 0 auto; margin-top: 1px; }
	.mlFocus div { display: flex; flex-direction: column; gap: 2px; }
	.mlFocus span { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlDriverTable { display: flex; flex-direction: column; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; overflow: hidden; margin-top: 8px; }
	.mlDriverHead, .mlDriverRow { display: grid; grid-template-columns: minmax(190px, 1.7fr) 72px .7fr .6fr minmax(160px, 1.1fr) 86px; gap: 8px; align-items: center; padding: 6px 8px; }
	.mlDriverHead { font-size: 9px; font-weight: 800; color: var(--dl-ink-dim, #5b6473); background: rgba(255,255,255,.025); letter-spacing: .05em; }
	.mlDriverRow { font-size: 11px; border-top: 1px solid rgba(255,255,255,.045); }
	.mlDriverRow.primary { background: rgba(52,211,153,.035); }
	.mlDriverRow.secondary { background: rgba(var(--amber-rgb),.025); }
	.mlDriverRow.focused, .mlEdge.focused { outline: 1px solid var(--amber); outline-offset: -1px; }
	.mlDriverName { display: flex; flex-direction: column; min-width: 0; gap: 1px; }
	.mlDriverName em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverScore { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; min-width: 0; }
	.mlDriverScore em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 8.5px; line-height: 1.2; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlScore { display: inline-flex; align-items: center; justify-content: center; min-width: 54px; height: 18px; border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; font-family: var(--dl-font-mono); font-size: 10px; padding: 0 4px; }
	.mlScore.high { color: var(--up); border-color: rgba(52,211,153,.45); }
	.mlScore.medium { color: var(--amber); border-color: rgba(var(--amber-rgb),.45); }
	.mlScore.low { color: var(--dl-ink-dim, #5b6473); }
	.mlScore.blocked { color: var(--dn); border-color: rgba(248,113,113,.45); }
	.mlDriverLine { display: flex; flex-direction: column; gap: 1px; min-width: 0; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.25; }
	.mlDriverLine em { color: var(--amber); font-style: normal; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverLine small { width: max-content; max-width: 100%; color: var(--warn); border: 1px solid rgba(var(--amber-rgb),.35); border-radius: 999px; padding: 1px 5px; font-size: 8.5px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlIconBtn { display: inline-flex; align-items: center; justify-content: center; gap: 3px; width: 72px; border: 1px solid var(--dl-line, #1b2130); background: var(--dl-bg-base, #080d16); color: var(--dl-ink-dim, #5b6473); border-radius: 3px; padding: 3px 4px; cursor: pointer; font-size: 9px; font-weight: 700; }
	.mlIconBtn:hover, .mlIconBtn.on { color: var(--amber); border-color: var(--amber); }
	.mlIconBtn:disabled { cursor: not-allowed; opacity: .48; color: var(--dl-ink-dim, #5b6473); border-color: var(--dl-line, #1b2130); }
	.mlEdgeDetails { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.012); padding: 10px; overflow: hidden; }
	.mlEdgeDetailsHead { margin-bottom: 8px; }
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
	.mlScenario .mlBlockTop em { font-style: normal; font-family: var(--dl-font-mono); font-size: 10px; color: var(--amber); }
	.mlScenario.needsEvidence { border-color: rgba(var(--amber-rgb),.36); }
	.mlScenario.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.035); }
	.mlScenario em { display: block; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; margin-top: 8px; }
	.mlSrc { padding: 6px 0; border-top: 1px solid rgba(255,255,255,.045); color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlSrc b { color: var(--warn); font-family: var(--dl-font-mono); font-size: 10px; margin-right: 5px; text-transform: uppercase; }
	.mlSrc em { display: block; margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 10px; overflow-wrap: anywhere; }
	.mlQuantCard { margin-top: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.016); padding: 9px; }
	.mlQuantCard.ok { border-color: rgba(52,211,153,.42); }
	.mlQuantCard.watch { border-color: rgba(var(--amber-rgb),.42); }
	.mlQuantCard.blocked { border-color: rgba(248,113,113,.42); }
	.mlQuantTop { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlQuantTop b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dl-ink); font-size: 11px; }
	.mlQuantCard p { margin: 6px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlQuantAlt { margin-top: 7px; border: 1px solid rgba(var(--amber-rgb),.28); border-radius: 5px; background: rgba(var(--amber-rgb),.03); color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.35; padding: 6px 8px; }
	.mlQualityCard { margin-top: 8px; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.016); padding: 9px; }
	.mlQualityCard.ok { border-color: rgba(52,211,153,.42); background: rgba(52,211,153,.035); }
	.mlQualityCard.watch { border-color: rgba(var(--amber-rgb),.42); background: rgba(var(--amber-rgb),.035); }
	.mlQualityCard.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.032); }
	.mlQualityTop { display: grid; grid-template-columns: 82px 60px minmax(0, 1fr); gap: 7px; align-items: center; min-width: 0; }
	.mlQualityTop b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 13px; }
	.mlQualityTop em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; text-align: right; }
	.mlQualityCard.ok .mlQualityTop b { color: var(--up); }
	.mlQualityCard.watch .mlQualityTop b { color: var(--warn); }
	.mlQualityCard.blocked .mlQualityTop b { color: var(--dn); }
	.mlQualityCard p { margin: 7px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlModelMetrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; margin-top: 8px; }
	.mlModelMetric { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.018); padding: 6px; }
	.mlModelMetric.ok { border-color: rgba(52,211,153,.28); }
	.mlModelMetric.watch { border-color: rgba(var(--amber-rgb),.34); }
	.mlModelMetric.blocked { border-color: rgba(248,113,113,.36); }
	.mlModelMetric span, .mlModelMetric b { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlModelMetric span { color: var(--dl-ink-muted, #7b8493); font-size: 8.5px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
	.mlModelMetric b { margin-top: 3px; color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10.5px; }
	.mlIndicatorGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin-top: 6px; }
	.mlIndicatorCard { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.014); padding: 7px; }
	.mlIndicatorCard.ok { border-color: rgba(52,211,153,.28); }
	.mlIndicatorCard.watch { border-color: rgba(var(--amber-rgb),.34); }
	.mlIndicatorCard.blocked { border-color: rgba(248,113,113,.38); }
	.mlIndicatorCard div:first-child { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 6px; align-items: center; min-width: 0; }
	.mlIndicatorCard span, .mlIndicatorCard b, .mlIndicatorCard em, .mlIndicatorCard small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlIndicatorCard span { color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlIndicatorCard b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlIndicatorCard em { display: block; margin-top: 4px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlIndicatorStats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin-top: 5px; }
	.mlIndicatorStats span { border: 1px solid rgba(255,255,255,.055); border-radius: 3px; padding: 2px 4px; color: var(--dl-ink-dim, #5b6473); font-size: 8.5px; text-transform: none; }
	.mlMissingLedger { display: grid; gap: 5px; margin-top: 6px; }
	.mlMissingItem { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 5px 7px; align-items: baseline; min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.012); padding: 6px; }
	.mlMissingItem.ok { border-color: rgba(52,211,153,.28); }
	.mlMissingItem.watch { border-color: rgba(var(--amber-rgb),.34); }
	.mlMissingItem.blocked { border-color: rgba(248,113,113,.36); }
	.mlMissingItem b, .mlMissingItem span, .mlMissingItem em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlMissingItem b { color: var(--warn); font-family: var(--dl-font-mono); font-size: 9px; text-transform: uppercase; }
	.mlMissingItem span { color: var(--dl-ink-dim, #5b6473); font-size: 10px; }
	.mlSrcPacket { width: 100%; border: 0; border-top: 1px solid rgba(255,255,255,.045); background: transparent; color: inherit; text-align: left; padding: 7px 0; cursor: pointer; }
	.mlSrcPacket:hover, .mlSrcPacket.focused { background: rgba(var(--amber-rgb),.035); }
	.mlSrcPacket b, .mlSrcPacket span, .mlSrcPacket em, .mlSrcPacket small { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlSrcPacket b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlSrcPacket span { margin-top: 2px; color: var(--dl-ink-dim, #5b6473); font-size: 10px; }
	.mlSrcPacket em, .mlSrcPacket small { margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; }
	.mlSrcPacket.stale { border-left: 2px solid rgba(248,113,113,.52); padding-left: 6px; }
	.mlSrcPacket.watch, .mlSrcPacket.unknown { border-left: 2px solid rgba(var(--amber-rgb),.52); padding-left: 6px; }
	.mlSrcPacket.fresh { border-left: 2px solid rgba(52,211,153,.48); padding-left: 6px; }
	.mlSrcPacket.missing { border-left: 2px solid rgba(248,113,113,.75); padding-left: 6px; }
	.mlSrcSep { height: 8px; border-top: 1px dashed rgba(255,255,255,.08); }
	.mlLimitSub { margin-top: 8px; color: var(--amber); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	@media (max-width: 760px) {
		.mlModal { height: 92vh; }
		.mlGrid.two, .mlPulseStrip, .mlGateStrip, .mlDrill, .mlRailRows, .mlDashGate { grid-template-columns: 1fr; }
		.mlDriverHead, .mlDriverRow { grid-template-columns: minmax(132px, 1.3fr) 72px 76px; }
		.mlDriverHead span:nth-child(3), .mlDriverHead span:nth-child(4), .mlDriverHead span:nth-child(5), .mlDriverRow > span:nth-child(3), .mlDriverRow > span:nth-child(4), .mlDriverRow > span:nth-child(5) { display: none; }
		.mlQualityTop, .mlIndicatorGrid { grid-template-columns: 1fr; }
		.mlQualityTop em { text-align: left; }
		.mlModelMetrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
	@media (max-width: 560px) {
		.mlPulseStrip { grid-auto-flow: column; grid-auto-columns: minmax(104px, 1fr); grid-template-columns: none; overflow-x: auto; }
		.mlMapHead { display: none; }
		.mlMapRow { display: flex; flex-direction: column; gap: 6px; }
		.mlMapCol { width: 100%; }
		.mlMapCell { width: 100%; }
	}
</style>
