<script lang="ts">
	import { GitBranch, LineChart, ShieldAlert, X } from 'lucide-svelte';
	import type { Lang } from '../lib/types';
	import type { MacroChannel, MacroDriverView, MacroExposureMatrixRow, MacroLensSnapshot, MacroLensTab, MacroTransmissionEdgeView } from '../lib/macroLens';
	import { buildExposureMatrixRows, pickFocusCell } from '../lib/macroLens';
	import { ECON_MAX } from '../charts/chartState.svelte';
	import MacroPathRail from './MacroPathRail.svelte';

	interface Props {
		snapshot: MacroLensSnapshot;
		lang: Lang;
		tab: MacroLensTab;
		focusId?: string;
		activeEcon?: string[];
		onTab: (tab: MacroLensTab) => void;
		onClose: () => void;
		onToggleEcon?: (id: string) => void;
		onSector?: (industryId: string) => void;
	}
	let { snapshot, lang, tab, focusId = '', activeEcon = [], onTab, onClose, onToggleEcon, onSector }: Props = $props();
	let localFocus = $state('');
	let localTab = $state<MacroLensTab>('dashboard');
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const tabs: { k: MacroLensTab; kr: string; en: string }[] = [
		{ k: 'dashboard', kr: '계기판', en: 'Dashboard' },
		{ k: 'transmission', kr: '경로', en: 'Path' },
		{ k: 'sources', kr: '근거', en: 'Sources' }
	];
	const tabButtonId = (k: MacroLensTab) => `macro-lens-tab-${k}`;
	// 단일 패널(내부 {#if} 분기)이라 id 도 1개 고정 — 비활성 탭의 aria-controls 가 없는 id 를 가리키지 않게.
	const tabPanelId = 'macro-lens-panel';
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
	// 국면 렌즈(Regime Lens·초강화) — A블록 inline <details>. macro.regime 부재 시 미가용.
	const regime = $derived(snapshot.regime);
	const usLens = $derived(regime?.us ?? null);
	const krLens = $derived(regime?.kr ?? null);
	const transitionFrac = $derived(regime?.transitionFraction ?? null);
	// 전이 phase 한국어 라벨 — us.transition.from/to 가 영어 phase 코드라 라벨 매핑.
	const phaseKo: Record<string, string> = {
		expansion: '확장', slowdown: '둔화', contraction: '수축', recovery: '회복',
		stagflation: '스태그', reflation: '리플레', deflation: '디플레', goldilocks: '골디락스'
	};
	const phaseLabelKo = (p: string): string => (lang === 'en' ? (phaseEn[p] ?? p) : (phaseKo[p] ?? p));
	// Phase Strip 헤드라인 — KR 은 backend 정본 label(침체 등), EN 은 phase enum(영문). phaseKo 재유도 금지(SSOT=엔진 label).
	const phaseEn: Record<string, string> = {
		expansion: 'Expansion', slowdown: 'Slowdown', contraction: 'Contraction', recovery: 'Recovery',
		stagflation: 'Stagflation', reflation: 'Reflation', deflation: 'Deflation', goldilocks: 'Goldilocks'
	};
	const phaseHeadline = (p?: { label: string; phase: string } | null): string =>
		p ? (lang === 'en' ? (phaseEn[p.phase] ?? p.phase) : (p.label || p.phase)) : '—';
	const transitionText = $derived(transitionFrac ? `${phaseLabelKo(transitionFrac.from)}→${phaseLabelKo(transitionFrac.to)} ${transitionFrac.fraction} ${T('충족', 'met')}` : null);
	let regimeOpen = $state(false);
	// D블록 Gate Strip = evidenceGates 중 quant 제외 4개(데이터·전파·동행·회사).
	const gateRows = $derived(snapshot.evidenceGates.filter((g) => g.id !== 'quant'));
	const exposureQualityClass = $derived(snapshot.exposureQuality.status === 'quantCandidate' ? 'ok' : snapshot.exposureQuality.status === 'qualitativeOnly' ? 'watch' : 'blocked');
	// 정량 LOCK 2케이스 정직 분기 (근거 탭). status로 직접 분기 — UI 추론 0. "분기 누적 시 OPEN" 약속 금지.
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
	const quantAltValue = $derived(T('대신 → 경로 탭 동행(co-move) 반증·업종 prior 경로로 확인', 'Instead → verify via Path tab co-move falsifier / sector prior path'));
	const modelMetricRows = $derived([
		{ label: 'nObs', value: snapshot.exposureQuality.nObs != null ? String(snapshot.exposureQuality.nObs) : '—', status: snapshot.exposureQuality.nObs != null ? 'ok' : 'blocked' },
		{ label: 'R²', value: fmtR2(snapshot.exposureQuality.rSquared), status: snapshot.exposureQuality.rSquared != null ? 'ok' : 'blocked' },
		{ label: 'window', value: snapshot.exposureQuality.window ?? '—', status: snapshot.exposureQuality.window ? 'ok' : 'blocked' },
		{ label: 'freq', value: snapshot.exposureQuality.frequency ?? '—', status: snapshot.exposureQuality.frequency ? 'ok' : 'blocked' },
		{ label: 'lag', value: snapshot.exposureQuality.lagMonths != null ? `${snapshot.exposureQuality.lagMonths}M` : '—', status: snapshot.exposureQuality.lagMonths != null ? 'ok' : 'blocked' },
		{ label: 'coverage', value: snapshot.exposureQuality.coverage, status: snapshot.exposureQuality.coverage === 'company' ? 'ok' : snapshot.exposureQuality.coverage === 'sectorOnly' ? 'watch' : 'blocked' }
	]);
	const modelSpecRows = $derived([
		{ label: 'method', value: snapshot.exposureQuality.method ?? '—', status: snapshot.exposureQuality.method ? 'ok' : 'blocked' },
		{ label: 'version', value: snapshot.exposureQuality.modelVersion ?? '—', status: snapshot.exposureQuality.modelVersion ? 'ok' : 'blocked' },
		{ label: 'target', value: snapshot.exposureQuality.targetMetric ?? '—', status: snapshot.exposureQuality.targetMetric ? 'ok' : 'blocked' },
		{ label: 'minObs', value: snapshot.exposureQuality.minObs != null ? String(snapshot.exposureQuality.minObs) : '—', status: snapshot.exposureQuality.minObs != null ? 'ok' : 'blocked' }
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
	// Hamilton regime band 가로 스파크 — 입력은 이미 0~1 정규화된 침체확률(view-model). 막대 아님·점추정 아님.
	function bandPoints(vals: number[]): string {
		if (!vals.length) return '';
		return vals.map((v, i) => `${(i / Math.max(1, vals.length - 1)) * 100},${16 - Math.max(0, Math.min(1, v)) * 14}`).join(' ');
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
	function motionLabel(value: string | null | undefined): string {
		const raw = value ?? '—';
		if (lang === 'en') return raw;
		const key = raw.toLowerCase();
		return key === 'rising' ? '상승' : key === 'falling' ? '하락' : key === 'stable' ? '횡보' : raw;
	}
	function goto(tabName: MacroLensTab, id = '') {
		localFocus = id || activeFocusId;
		localTab = tabName;
		onTab(tabName);
	}
	function selectTab(tabName: MacroLensTab) {
		localTab = tabName;
		onTab(tabName);
	}
	function focusActiveTab() {
		queueMicrotask(() => dialogEl?.querySelector<HTMLButtonElement>(`#${tabButtonId(localTab)}`)?.focus());
	}
	function selectRelativeTab(delta: number) {
		const idx = tabs.findIndex((t) => t.k === localTab);
		const next = tabs[(idx + delta + tabs.length) % tabs.length]?.k ?? tabs[0].k;
		selectTab(next);
		focusActiveTab();
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
		const target = e.target instanceof HTMLElement ? e.target : null;
		if (target?.closest('.mlTabs') && (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'Home' || e.key === 'End')) {
			e.preventDefault();
			if (e.key === 'ArrowRight') selectRelativeTab(1);
			else if (e.key === 'ArrowLeft') selectRelativeTab(-1);
			else {
				selectTab(e.key === 'Home' ? tabs[0].k : tabs[tabs.length - 1].k);
				focusActiveTab();
			}
			e.stopPropagation();
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
		if (localTab !== tab) localTab = tab;
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
			<div class="mlAsOf">
				<span>macro <b>{snapshot.asOf.macro ?? '—'}</b></span>
				<span>price <b>{snapshot.asOf.price ?? '—'}</b></span>
				<span>fin <b>{snapshot.asOf.finance ?? '—'}</b></span>
			</div>
			<button class="scrClose" onclick={onClose} aria-label="close"><X size={14} /></button>
		</div>

		<div class="mlTabs" role="tablist" aria-label={T('매크로 렌즈 분석 탭', 'Macro Lens analysis tabs')}>
			{#each tabs as t (t.k)}
				<button
					id={tabButtonId(t.k)}
					role="tab"
					class:active={localTab === t.k}
					aria-selected={localTab === t.k}
					aria-controls={tabPanelId}
					tabindex={localTab === t.k ? 0 : -1}
					onclick={() => selectTab(t.k)}
				>{T(t.kr, t.en)}</button>
			{/each}
		</div>
		<div class="mlAlwaysNote">
			{T('노출 점검표입니다. 정량 민감도·투자 결론·가격 산출은 표시하지 않습니다.', 'Exposure checklist only. No quantitative sensitivity, investment call, or price output.')}
		</div>

		<div class="mlBody" class:mlVoid={localTab === 'dashboard' && !focusCell} id={tabPanelId} role="tabpanel" aria-labelledby={tabButtonId(localTab)} tabindex="0">
			{#if localTab === 'dashboard'}
				<!-- 블록 A — Phase Strip (클릭 → 국면 렌즈 toggle) -->
				{#if regime?.available}
					<details class="mlRegimeFold" bind:open={regimeOpen}>
						<summary class="mlPhaseStrip" aria-label={T('Macro 국면 — 클릭하면 국면 렌즈', 'Macro phases — click for Regime Lens')}>
							<div><span>KR</span><b>{phaseHeadline(snapshot.marketPhase.kr)}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.kr?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.kr?.inflation)}</em></div>
							<div><span>US <i class="mlPhaseCaret" aria-hidden="true">{regimeOpen ? '▴' : '▾'}</i></span><b>{phaseHeadline(snapshot.marketPhase.us)}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.us?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.us?.inflation)}{#if transitionText}<span class="mlTransFrac">· {transitionText}</span>{/if}</em></div>
							<div><span>{T('업종', 'Sector')}</span><b>{snapshot.sectorBinding.tailwind ? T(snapshot.sectorBinding.tailwind.kr, snapshot.sectorBinding.tailwind.en) : T(snapshot.company.sector.kr, snapshot.company.sector.en)}</b><em>{snapshot.sectorBinding.tailwind ? `${T(snapshot.sectorBinding.tailwind.label, snapshot.sectorBinding.tailwind.labelEn)} ${snapshot.sectorBinding.tailwind.blended.toFixed(2)}` : T('미산출', 'not computed')}</em></div>
						</summary>
						<!-- 국면 렌즈 (Regime Lens) — 회고는 phase, 검증은 아래 -->
						<div class="mlRegimeLens" aria-label={T('국면 렌즈', 'Regime Lens')}>
							{#if usLens}
								{@const lens = usLens}
								<div class="mlRegimeHead">{T('침체 신호', 'Recession signals')} ({lens.totalCount}{T('모델 중', ' models, ')} {lens.validCount} {T('유효 · 호라이즌·시간성 상이 · 동의', 'valid · horizons/timing differ · agreement')}: {T(lens.agreement.kr, lens.agreement.en)})</div>
								<div class="mlConfluence">
									{#each lens.tiles as tile (tile.model)}
										<div class={'mlTile' + (tile.suppressed ? ' dim' : '')} title={T(tile.note.kr, tile.note.en)}>
											<b>{T(tile.zoneLabel.kr, tile.zoneLabel.en)}{#if tile.secondary}<i class="mlTileSec"> {tile.secondary}</i>{/if}</b>
											<span>{tile.modelName} · {T(tile.horizonLabel.kr, tile.horizonLabel.en)}</span>
											<em>{T(tile.scaleLabel.kr, tile.scaleLabel.en)}</em>
											<em class="mlTileMeta">{#if tile.suppressed}{tile.statusText ? T(tile.statusText.kr, tile.statusText.en) : ''}{:else}{tile.asOf ?? '—'}{#if tile.staleLabel} · {tile.staleLabel}{/if}{/if}</em>
										</div>
									{/each}
								</div>
								<div class="mlRegimeNote">{T("probit=고정계수·SE미산출(점추정) · probit '보통'(moderate)=확장 집계 · LEI=term/claims 내포(부분상관) · Hamilton=동행·회고", "probit=fixed-coef·no SE (point est) · probit 'moderate' counted as expansion · LEI embeds term/claims (partial corr) · Hamilton=coincident·retrospective")}</div>
								{#if lens.yieldCurve}
									<div class="mlRegimeRow" title={T(lens.yieldCurve.note.kr, lens.yieldCurve.note.en)}>
										<b>{T('수익률곡선', 'Yield curve')}</b> {T(lens.yieldCurve.curveShapeLabel.kr, lens.yieldCurve.curveShapeLabel.en)} · 10Y-3M {lens.yieldCurve.spreadText}
										<i class="mlRegimeDim">░{lens.yieldCurve.asOf ?? '—'} · {T('역전≠즉시침체 · 형태=NS·spread=동일곡선', 'inversion≠immediate recession · shape=NS·spread=same curve')}</i>
									</div>
								{/if}
								{#if lens.gar}
									{@const gar = lens.gar}
									<div class="mlGaR" title={T(gar.note.kr, gar.note.en)}>
										<div class="mlGaRTop"><b>GaR {T(gar.horizonLabel.kr, gar.horizonLabel.en)}</b><i class="mlRegimeDim">[{T('조건부 분포·점추정 아님', 'conditional dist · not point est')}] · tail {T(gar.tailRiskLabel.kr, gar.tailRiskLabel.en)}{#if gar.skewness != null} · {T('비대칭', 'skew')} {gar.skewness.toFixed(1)}{/if} · ░{gar.asOf ?? '—'}</i></div>
										<div class="mlGaRBars">
											{#each gar.bars as bar (bar.key)}
												<div class="mlGaRBar" class:tail={bar.key === 'gar5' || bar.key === 'gar95'} class:mid={bar.key === 'median'}><i style={`height:${Math.round(bar.frac * 100)}%`}></i><span>{bar.label}</span><em>{bar.value.toFixed(1)}</em></div>
											{/each}
										</div>
										<div class="mlGaRAxis">{T('막대 = 5분위 상대 위치 · 분위별 GDP 성장률(%)은 아래 숫자 · 높이는 확률 아님', 'bars = relative position across the 5 quantiles · GDP growth (%) is the number below each · height is not probability')}</div>
										<div class="mlRegimeNote">{T(gar.note.kr, gar.note.en)}</div>
									</div>
								{/if}
								{#if lens.band}
									<div class="mlBandRow">
										<b>{T(lens.band.caption.kr, lens.band.caption.en)}</b>
										<svg class="mlBandSpark" viewBox="0 0 100 18" preserveAspectRatio="none" aria-hidden="true">
											<polyline points={bandPoints(lens.band.points)} />
										</svg>
										<i class="mlRegimeDim">░{lens.band.asOf ?? '—'}</i>
									</div>
								{/if}
								{#if lens.quadrant}
									{@const q = lens.quadrant}
									<div class="mlRegimeRow">
										<b>{T('국면 사분면', 'Regime quadrant')}</b> {T(q.growthLabel.kr, q.growthLabel.en)} {T(q.inflationLabel.kr, q.inflationLabel.en)}
										{#if q.assets.length}→ {T('비중확대 함의', 'overweight implication')}: {q.assets.filter((a) => a.weight === 'overweight').map((a) => T(a.label, a.labelEn)).join('·') || T('중립', 'neutral')} <i class="mlRegimeDim">{T('국면 교과서·추천 아님', 'regime textbook · not advice')}</i>{/if}
										<i class="mlRegimeDim">[{T('회고', 'retrospective')}]</i>
										{#if q.alignment}<i class="mlRegimeAlign">· {T(q.alignment.kr, q.alignment.en)}</i>{/if}
									</div>
								{/if}
							{/if}
							{#if krLens}
								{@const lens = krLens}
								<div class="mlRegimeHeadKr">KR — {T('침체 confluence', 'recession confluence')} ({lens.validCount} {T('유효', 'valid')} · {T('동의', 'agreement')}: {T(lens.agreement.kr, lens.agreement.en)})</div>
								<div class="mlConfluence">
									{#each lens.tiles as tile (tile.model)}
										<div class={'mlTile' + (tile.suppressed ? ' dim' : '')} title={T(tile.note.kr, tile.note.en)}>
											<b>{T(tile.zoneLabel.kr, tile.zoneLabel.en)}{#if tile.secondary}<i class="mlTileSec"> {tile.secondary}</i>{/if}</b>
											<span>{tile.modelName} · {T(tile.horizonLabel.kr, tile.horizonLabel.en)}</span>
											<em>{T(tile.scaleLabel.kr, tile.scaleLabel.en)}</em>
											<em class="mlTileMeta">{tile.asOf ?? '—'}{#if tile.staleLabel} · {tile.staleLabel}{/if}</em>
										</div>
									{/each}
								</div>
								{#if lens.notApplicable.length}
									<div class="mlRegimeNote">{#each lens.notApplicable as na (na.id)}<span class="mlNaChip">{na.label}: {T(na.reason.kr, na.reason.en)}</span>{/each}</div>
								{/if}
								{#if lens.quadrant}
									{@const q = lens.quadrant}
									<div class="mlRegimeRow"><b>{T('국면 사분면', 'Regime quadrant')}</b> {T(q.growthLabel.kr, q.growthLabel.en)} {T(q.inflationLabel.kr, q.inflationLabel.en)} <i class="mlRegimeDim">[{T('회고', 'retrospective')}]</i>{#if q.alignment}<i class="mlRegimeAlign">· {T(q.alignment.kr, q.alignment.en)}</i>{/if}</div>
								{/if}
							{/if}
						</div>
					</details>
				{:else}
					<!-- regime 데이터 준비 전 — 기본 Phase Strip (전향 분수만, 이미 라이브) -->
					<section class="mlPhaseStrip" aria-label={T('거시 국면', 'Macro phases')}>
						<div><span>KR</span><b>{phaseHeadline(snapshot.marketPhase.kr)}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.kr?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.kr?.inflation)}</em></div>
						<div><span>US</span><b>{phaseHeadline(snapshot.marketPhase.us)}</b><em>{T('성장', 'growth')} {motionLabel(snapshot.marketPhase.us?.growth)} · {T('물가', 'inflation')} {motionLabel(snapshot.marketPhase.us?.inflation)}{#if transitionText}<span class="mlTransFrac">· {transitionText}</span>{/if}</em></div>
						<div><span>{T('업종', 'Sector')}</span><b>{snapshot.sectorBinding.tailwind ? T(snapshot.sectorBinding.tailwind.kr, snapshot.sectorBinding.tailwind.en) : T(snapshot.company.sector.kr, snapshot.company.sector.en)}</b><em>{snapshot.sectorBinding.tailwind ? `${T(snapshot.sectorBinding.tailwind.label, snapshot.sectorBinding.tailwind.labelEn)} ${snapshot.sectorBinding.tailwind.blended.toFixed(2)}` : T('미산출', 'not computed')}</em></div>
					</section>
				{/if}

				<!-- 블록 B — Driver Pulse -->
				<section class="mlPulseStrip" aria-label={T('거시 펄스', 'Macro pulse')}>
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
				</section>

				<!-- 블록 C — Exposure Map (단일 테두리 주역) -->
				<section class="mlMap" aria-label={T('노출 지도', 'Exposure Map')}>
					{#if focusCell}
						<!-- 읽기 1차 — 초점 전파사슬 -->
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
							<button class="mlMapDrill" onclick={() => goto('transmission', focusCell.driver.id)}>{T('셀 클릭 → 경로 드릴다운(전파·품질·기여·동행·출처)', 'cell → Path drilldown (chain · quality · contribution · co-move · source)')}</button>
						</div>
					{:else}
						<div class="mlMapFocus">
							<div class="mlMapChain"><b>{T('표준 전파 경로 없음 — 경로 탭에서 확인', 'No mapped transmission path — see Path tab')}</b></div>
						</div>
					{/if}

					<!-- 읽기 2차 — 닷그리드 (채널 열 클러스터, opacity .82) -->
					<div class="mlMapGrid" aria-label={T('채널 닷그리드', 'channel dot grid')}>
						{#if mapColumns.length}
							<div class="mlMapHead">
								{#each mapColumns as col (col.channel)}<span>{channelLabel(col.channel)}</span>{/each}
							</div>
							<div class="mlMapRow">
								{#each mapColumns as col (col.channel)}
									<div class="mlMapCol">
										{#each col.cells as cell (`${cell.driver.id}-${col.channel}`)}
											<button class={'mlMapCell ' + cellClass(cell.edge)} onclick={() => goto('transmission', cell.edge.driverId)} title={cellTitle(cell.edge, col.channel)} aria-label={chipAria(cell.edge, col.channel)}>
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
							<div class="mlMapNote">{T('색=증거 상태(방향 아님) · 닿는 채널만 표시(빈 열 생략)', 'Color = evidence state (not direction) · only mapped channels shown (empty columns omitted)')}</div>
						{:else}
							<div class="mlMapNote">{T('표시 가능한 전파 채널 없음 — 경로 탭 확인', 'No mappable transmission channel — see Path tab')}</div>
						{/if}
					</div>
				</section>

				<!-- 블록 D — Evidence Gate(quant 제외 4) + Release Rail -->
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
					</div>
				</section>
				<div class="mlMapNote mlAlwaysNote inline">{T('정량 게이트는 근거 탭. 첫 화면 정량 행 없음.', 'Quant gate is on the Sources tab. No quant row on the first screen.')}</div>
			{:else if localTab === 'transmission'}
				{#if snapshot.macroPath}
					<MacroPathRail view={snapshot.macroPath} {lang} mode="full" onSector={onSector} />
				{/if}
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
					{#if focusContribution}
						<section class="mlContributionPanel" aria-label={T('증거 기여 분해', 'Evidence contribution breakdown')}>
							<div class="mlRailTitle">
								<span class="mlBlockK">Evidence Contribution</span>
								<b>{focusContribution.label}</b>
								<em>{T('재무 기여도 아님 · 합산 금지', 'not financial contribution · not additive')}</em>
							</div>
							<div class="mlEvidenceBreakdown">
								{#each focusContribution.components as c (c.id)}
									<div class={'mlEvidenceStep ' + c.status} title={`${c.detail} · ${c.sourceRef}`}>
										<i style={`height:${pct(c.value)}`}></i>
										<span>{c.label}</span>
										<b>{Math.round(c.value * 100)}%</b>
										<em>{componentStatusText[c.status] ?? c.status.toUpperCase()}</em>
										<small>{c.detail}</small>
										<code>{c.sourceRef}</code>
									</div>
								{/each}
							</div>
							<div class="mlEvidenceMeta">
								<span>{focusContribution.summary}</span>
								<span>{T('최근 변화 / 전파 경로 / 동행 후보 / 신선도 / 회사 품질', 'move / path / co-move / freshness / company quality')}</span>
							</div>
						</section>
					{/if}
					{#if focusCoMove}
						<section class={'mlCoMovePanel ' + focusCoMove.status}>
							<div class="mlRailTitle"><span class="mlBlockK">Co-movement Gate</span><b>{focusCoMove.label}</b><em>{T('인과 아님', 'not causal')}</em></div>
							{#if focusCoMove.points.length}
								<div class="mlScatterPlot" aria-label={T('월별 동행 산점도', 'Monthly co-movement scatter')}>
									<i class="mlZeroX" style={`left:${focusCoMove.xZero}%`}></i>
									<i class="mlZeroY" style={`top:${focusCoMove.yZero}%`}></i>
									<span class="mlAxisLabel x">{T('macro 월말 Δ', 'macro month-end Δ')}</span>
									<span class="mlAxisLabel y">{T('종목 월수익률', 'stock MoM return')}</span>
									{#each focusCoMove.points as p (p.ym)}
										<b class:latest={p.latest} style={`left:${p.px}%;top:${p.py}%`} title={p.label}></b>
									{/each}
								</div>
							{:else}
								<div class="mlCorrPlot" aria-label={T('동행 상관 위치', 'Co-movement correlation position')}>
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
				<details class="mlEdgeDetails">
					<summary>{T('상세 edge 카드', 'Detailed edge cards')} · {snapshot.transmissionEdges.length}</summary>
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
				</details>
				<details class="mlEdgeDetails">
					<summary>{T('심화 (시나리오 · 상세 지표)', 'Advanced (scenarios · detailed drivers)')}</summary>
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
				</details>
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
						{#each snapshot.sourceRefs as s, i (`${s}-${i}`)}<div class="mlSrc">{s}</div>{/each}
					</div>
					<div class="mlBlock">
						<div class="mlBlockTop"><span class="mlBlockK">{T('한계·결손', 'Limits')}</span><b>{T('모르는 것은 숨기지 않음', 'Unknowns stay visible')}</b></div>
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
								<span class="mlBlockK">Quality Gate</span>
								<b>{exposureQualityText[snapshot.exposureQuality.status] ?? snapshot.exposureQuality.status}</b>
								<em>{T('정량 claim gate · 추천/목표가 아님', 'quant claim gate · no recommendation')}</em>
							</div>
							<p>{snapshot.exposureQuality.reason}</p>
							<div class="mlModelSpec" aria-label={T('거시 노출 모델 사양', 'Macro exposure model specification')}>
								{#each modelSpecRows as r (r.label)}
									<div class={'mlModelSpecItem ' + r.status} title={r.value}>
										<span>{r.label}</span>
										<b>{r.value}</b>
									</div>
								{/each}
							</div>
							<div class="mlModelMetrics">
								{#each modelMetricRows as r (r.label)}
									<div class={'mlModelMetric ' + r.status}>
										<span>{r.label}</span>
										<b>{r.value}</b>
									</div>
								{/each}
							</div>
							<div class="mlModelSource"><span>sourceRef</span><b>{snapshot.exposureQuality.sourceRef}</b></div>
						</div>
						<div class="mlLimitSub">Model Card</div>
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
									<small title={x.sourceRefs.join(' · ')}>{x.sourceRef}</small>
								</div>
							{:else}
								<div class="mlIndicatorCard blocked">
									<div><span>indicator</span><b>LOCK</b></div>
									<em>{T('선택된 회사별 macroExposure 지표 없음', 'No selected company macroExposure indicator')}</em>
									<small>{snapshot.exposureQuality.sourceRef}</small>
								</div>
							{/each}
						</div>
						<div class="mlLimitSub">Missing Ledger</div>
						<div class="mlMissingLedger" aria-label={T('결손 증거 원장', 'Missing evidence ledger')}>
							{#each snapshot.exposureQuality.missingEvidence as x (x)}
								<div class="mlMissingItem blocked"><b>required</b><span>{x}</span><em>{snapshot.exposureQuality.sourceRef}</em></div>
							{/each}
							{#each snapshot.missing as m (m.id)}
								<div class={'mlMissingItem ' + (m.status === 'partial' || m.status === 'staleRisk' ? 'watch' : 'blocked')}><b>{m.status}</b><span>{m.reason}</span><em>{m.sourceRef}</em></div>
							{/each}
							{#if !snapshot.exposureQuality.missingEvidence.length && !snapshot.missing.length}
								<div class="mlMissingItem ok"><b>OK</b><span>{T('표시 가능한 결손 없음', 'No visible missing item')}</span><em>{snapshot.exposureQuality.sourceRef}</em></div>
							{/if}
						</div>
						<div class="mlLimitSub">Falsifier Strip</div>
						<div class="mlFalsifierStrip" aria-label={T('거시 반증', 'Macro falsifiers')}>
							{#each snapshot.falsifiers.slice(0, 4) as f (f.id)}
								<div class={'mlFalsifierToken ' + severityCls[f.severity]}>
									<b>{f.label}</b>
									<span>{f.detail}</span>
									<em>{f.sourceRef ?? 'macroLens'}</em>
								</div>
							{/each}
						</div>
						<div class="mlLimitSub">{T('Release freshness', 'Release freshness')}</div>
						{#each snapshot.releaseRail.slice(0, 6) as r (r.driverId)}
							<div class={'mlSrc warn ' + r.status}><b>{r.status}</b> {r.label}: last {r.lastObservation} · next {r.nextCheck}<em>{r.frequency} · stale after {r.staleAfterDays}d</em></div>
						{/each}
						<div class="mlSrc">{T('상관은 인과가 아니며, 지표 변화가 회사 실적 변화를 보장하지 않는다.', 'Correlation is not causation; indicator moves do not guarantee company results.')}</div>
					</div>
				</section>
			{/if}
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
	.mlAsOf { margin-left: auto; display: flex; flex-wrap: wrap; gap: 6px; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.mlAsOf span { border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 1px 5px; }
	.mlAsOf b { color: var(--dl-ink, #c8cfdb); font-family: var(--dl-font-mono); }
	.mlTabs { display: flex; align-items: flex-end; gap: 4px; min-height: 36px; padding: 7px 10px 0; border-bottom: 1px solid var(--dl-line, #1b2130); background: rgba(255,255,255,.016); overflow-x: auto; scrollbar-width: none; }
	.mlTabs::-webkit-scrollbar { display: none; }
	.mlTabs button { flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center; min-height: 28px; line-height: 1; white-space: nowrap; box-sizing: border-box; border: 1px solid transparent; border-bottom: 0; background: rgba(255,255,255,.012); color: var(--dl-ink-muted, #7b8493); font-size: 11px; font-weight: 800; padding: 7px 11px; cursor: pointer; border-radius: 5px 5px 0 0; }
	.mlTabs button:hover { color: var(--amber); }
	.mlTabs button.active { color: var(--dl-ink); border-color: var(--dl-line, #1b2130); background: var(--dl-bg-raised, #0e141f); box-shadow: inset 0 2px 0 var(--amber); }
	.mlAlwaysNote { padding: 6px 12px; border-bottom: 1px solid var(--dl-line, #1b2130); color: var(--dl-ink-dim, #5b6473); background: rgba(251,146,60,.035); font-size: 10.5px; line-height: 1.4; }
	.mlAlwaysNote.inline { border-bottom: 0; border-radius: 5px; background: transparent; padding: 0 2px; }
	.mlBody { flex: 1 1 auto; min-height: 0; overflow: auto; padding: 12px; display: flex; flex-direction: column; gap: 12px; }
	.mlGrid { display: grid; gap: 10px; }
	.mlGrid.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.edgeGrid { grid-template-columns: repeat(auto-fit, minmax(245px, 1fr)); }
	.scenarioGrid { grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); }
	/* 블록 A·B·D 스트립 (테두리 없음) */
	.mlPhaseStrip, .mlPulseStrip, .mlGateStrip { display: grid; gap: 8px; }
	.mlPhaseStrip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
	.mlPhaseStrip div, .mlGate, .mlPulse { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 9px; }
	.mlPhaseStrip span, .mlGate span, .mlPulse span { display: block; color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
	.mlPhaseStrip b, .mlGate b, .mlPulse b { display: block; margin-top: 4px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
	.mlPhaseStrip em, .mlGate em, .mlPulse em { display: block; margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	/* US 칩 em — 전향 분수 inline 시도. 넘치면 자연 줄바꿈으로 .mlTransFrac 가 2번째 줄(9.5px dim)로 강등(A블록 height 재예산 0). */
	.mlPhaseStrip div:nth-child(2) em { white-space: normal; overflow: visible; line-height: 1.35; }
	/* 국면 렌즈 (Regime Lens) — A블록 inline <details>. summary = Phase Strip(클릭 toggle). */
	.mlRegimeFold { display: block; }
	.mlRegimeFold > summary { cursor: pointer; list-style: none; }
	.mlRegimeFold > summary::-webkit-details-marker { display: none; }
	.mlPhaseCaret { font-style: normal; color: var(--amber); font-size: 9px; }
	.mlTransFrac { margin-left: 5px; color: var(--dl-ink-muted, #7b8493); font-size: 9.5px; }
	.mlRegimeLens { margin-top: 10px; display: flex; flex-direction: column; gap: 8px; padding-top: 8px; border-top: 1px dashed var(--bd); }
	.mlRegimeHead, .mlRegimeHeadKr { color: var(--dl-ink-dim, #5b6473); font-size: 10px; font-weight: 700; line-height: 1.4; }
	.mlRegimeHeadKr { margin-top: 4px; border-top: 1px dashed var(--bd); padding-top: 8px; color: var(--amber); }
	/* confluence — 값+zone 텍스트 타일(막대 아님). 타일 내부 px 위계 §5.5(Pulse 밀도 천장 공유). */
	.mlConfluence { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
	.mlTile { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.018); padding: 7px; }
	.mlTile.dim { opacity: .5; }
	.mlTile b { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 700; }
	.mlTileSec { font-style: normal; font-weight: 600; font-size: 10px; color: var(--dl-ink-dim, #5b6473); }
	.mlTile span { display: block; margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-size: 10px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlTile em { display: block; margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlTile .mlTileMeta { color: var(--dl-ink-dim, #5b6473); }
	.mlRegimeNote { color: var(--dl-ink-muted, #7b8493); font-size: 9px; line-height: 1.4; }
	.mlNaChip { display: inline-block; margin-right: 8px; color: var(--dl-ink-dim, #5b6473); }
	.mlRegimeRow { color: var(--dl-ink); font-size: 11px; line-height: 1.4; }
	.mlRegimeRow b { color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; margin-right: 5px; }
	.mlRegimeDim { font-style: normal; color: var(--dl-ink-muted, #7b8493); font-size: 9px; }
	/* 정합 서술은 중립 ink — accent(amber)가 방향=good 으로 읽히는 색 결합 차단(서술만·판정 아님). */
	.mlRegimeAlign { font-style: normal; color: var(--dl-ink-dim, #6b7280); font-size: 10px; }
	/* GaR 분위 막대 — 진짜 5분위 조건부 분포(probit 점확률 아님·fan 정당). */
	.mlGaR { border-top: 1px dashed var(--bd); padding-top: 8px; }
	.mlGaRTop { display: flex; flex-wrap: wrap; align-items: baseline; gap: 7px; }
	.mlGaRTop b { font-size: 11px; font-weight: 700; }
	.mlGaRBars { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; align-items: end; height: 42px; margin: 6px 0 4px; }
	.mlGaRBar { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; min-width: 0; }
	.mlGaRBar i { display: block; width: 60%; min-height: 2px; background: var(--amber); border-radius: 2px 2px 0 0; opacity: .8; }
	/* 분포 시각화: 꼬리(5%·95%) 흐리게·중위 또렷 → '점추정 아닌 분포' 를 라벨 너머 시각으로도 전달. */
	.mlGaRBar.tail i { opacity: .4; }
	.mlGaRBar.mid i { opacity: 1; }
	.mlGaRBar span { margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-size: 9px; }
	.mlGaRBar em { color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 10px; font-variant-numeric: tabular-nums; }
	.mlGaRAxis { margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-size: 9px; line-height: 1.3; }
	/* Hamilton regime band — 가로 스파크 1줄(막대/점추정 아님·회고 라벨). */
	.mlBandRow { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlBandRow b { flex: 0 0 auto; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; font-weight: 700; }
	.mlBandSpark { flex: 1 1 auto; height: 18px; min-width: 0; }
	.mlBandSpark polyline { fill: none; stroke: var(--amber); stroke-width: 1.2; vector-effect: non-scaling-stroke; }
	.mlPulse { color: var(--dl-ink); text-align: left; cursor: pointer; }
	.mlPulse:hover, .mlPulse.on { border-color: rgba(251,146,60,.55); background: rgba(251,146,60,.045); }
	.mlPulse:disabled { cursor: not-allowed; opacity: .5; }
	.mlPulse b { font-size: 13px; font-weight: 600; font-variant-numeric: tabular-nums; }
	.mlPulse svg { width: 100%; height: 20px; margin-top: 5px; overflow: visible; }
	.mlPulse polyline { fill: none; stroke: var(--amber); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
	/* 블록 C — Exposure Map (단일 테두리 주역) */
	.mlMap { border: 1px solid var(--bd); background: var(--panel); border-radius: 8px; padding: 8px; animation: mlFade .15s ease-out; }
	@keyframes mlFade { from { opacity: 0; } to { opacity: 1; } }
	/* §6.2 폴백: 초점 셀 0(macro.json 결손) 극단 — Map 테두리 흐리게 + Pulse 값 13→15px 로 Pulse 를 2차 주역 승격(빈 Map 이 시선 독점 방지). */
	.mlVoid .mlMap { border-color: color-mix(in srgb, var(--bd) 45%, transparent); }
	.mlVoid .mlPulse b { font-size: 15px; }
	/* 읽기 1차 — 초점 사슬 (중립 강조 + amber 좌측선, opacity 1 고정) */
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
	.mlMapDrill { margin-top: 6px; border: 0; background: transparent; color: var(--amber); font-size: 9.5px; font-weight: 700; cursor: pointer; padding: 0; text-align: left; }
	.mlMapDrill:hover { text-decoration: underline; }
	/* 읽기 2차 — 닷그리드 (채널 열 클러스터, 후퇴 opacity .82) */
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
	/* 형태 칩 범례 — 한 줄, 실제 칩 CSS 재사용(색맹 무손실 형태 4종 해독). */
	.mlMapLegend { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
	.mlMapLegend span { display: inline-flex; align-items: center; gap: 5px; color: var(--dl-ink-dim, #5b6473); font-size: 9px; }
	/* CSS 도형 칩 — ::before 16×16, 색=증거 상태(방향 아님), 글리프 폰트 의존 0 */
	.mlMapChip { display: inline-flex; flex: 0 0 auto; width: 16px; height: 16px; }
	.mlMapChip::before { content: ""; display: block; width: 16px; height: 16px; box-sizing: border-box; }
	/* 색=증거 상태(방향 아님): 중립 ink 램프(OBS 밝음→PRIOR amber→TPL dim→LOCK faint). 녹/적(--up/--dn)은 방향 전용이라 칩에서 배제. 형태가 1차 구분자(색맹 무손실). */
	.mlMapChip.OBS::before { border-radius: 50%; background: var(--dl-ink, #e8eaef); border: 1.5px solid var(--dl-ink, #e8eaef); }
	.mlMapChip.PRIOR::before { border-radius: 50%; border: 1.5px solid var(--amber); background: transparent; box-shadow: inset 8px 0 0 0 var(--amber); }
	.mlMapChip.TPL::before { border-radius: 50%; background: transparent; border: 1.5px dashed var(--dl-ink-dim, #6b7280); }
	.mlMapChip.LOCK::before { border-radius: 3px; border: 1px solid var(--dl-ink-faint, #4a5160); background: repeating-linear-gradient(45deg, transparent 0 2px, color-mix(in srgb, var(--dl-ink-faint, #4a5160) 45%, transparent) 2px 4px); }
	/* 블록 D */
	.mlDashGate { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1.3fr); gap: 10px; align-items: start; }
	.mlGateStrip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.mlGate.ok { border-color: rgba(52,211,153,.42); }
	.mlGate.watch { border-color: rgba(251,146,60,.42); }
	.mlGate.blocked { border-color: rgba(248,113,113,.42); }
	.mlGate.ok b { color: var(--up); }
	.mlGate.watch b { color: var(--warn); }
	.mlGate.blocked b { color: var(--dn); }
	/* 테두리·배경 없는 스트립 (mlGateStrip 와 동일 패턴) — Map 이 첫 화면 유일 테두리 패널이 되도록. 내부 mlRailItem 타일만 테두리. */
	.mlReleaseRail { padding: 0; }
	.mlRailTitle { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlRailTitle b { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
	.mlRailTitle em { color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlRailRows { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; margin-top: 8px; }
	.mlRailItem { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.015); color: var(--dl-ink); text-align: left; padding: 7px; cursor: pointer; }
	.mlRailItem:hover, .mlRailItem.focused { border-color: rgba(251,146,60,.55); background: rgba(251,146,60,.04); }
	.mlRailItem.fresh { border-color: rgba(52,211,153,.28); }
	.mlRailItem.watch, .mlRailItem.unknown { border-color: rgba(251,146,60,.36); }
	.mlRailItem.stale { border-color: rgba(248,113,113,.42); }
	.mlRailItem span, .mlRailItem b, .mlRailItem em, .mlRailItem i { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlRailItem span { color: var(--dl-ink-dim, #5b6473); font-size: 9px; font-weight: 800; letter-spacing: .04em; }
	.mlRailItem b { margin-top: 4px; font-family: var(--dl-font-mono); font-size: 11px; }
	.mlRailItem em, .mlRailItem i { margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; }
	/* 경로 탭 drilldown */
	.mlBlock, .mlEdge, .mlScenario, .mlFocus { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 10px; min-width: 0; }
	.mlDrill { display: grid; grid-template-columns: 1.25fr 1fr 1fr 1.25fr; gap: 8px; }
	.mlDrillCard { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(251,146,60,.035); padding: 9px; }
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
	.mlStackFill.watch { background: rgba(251,146,60,.72); }
	.mlStackFill.blocked { background: rgba(248,113,113,.65); }
	.mlContributionPanel { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.014); padding: 9px; }
	.mlEvidenceBreakdown { display: grid; grid-template-columns: repeat(5, minmax(98px, 1fr)); gap: 6px; margin-top: 8px; overflow-x: auto; padding-bottom: 1px; }
	.mlEvidenceStep { position: relative; min-width: 0; height: 112px; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.018); overflow: hidden; padding: 7px; }
	.mlEvidenceStep.ok { border-color: rgba(52,211,153,.36); }
	.mlEvidenceStep.watch { border-color: rgba(251,146,60,.38); }
	.mlEvidenceStep.blocked { border-color: rgba(248,113,113,.42); }
	.mlEvidenceStep i { position: absolute; left: 0; right: 0; bottom: 0; min-height: 4px; opacity: .32; background: var(--dl-ink-dim, #5b6473); }
	.mlEvidenceStep.ok i { background: rgba(52,211,153,.78); }
	.mlEvidenceStep.watch i { background: rgba(251,146,60,.76); }
	.mlEvidenceStep.blocked i { background: rgba(248,113,113,.72); }
	.mlEvidenceStep span, .mlEvidenceStep b, .mlEvidenceStep em, .mlEvidenceStep small, .mlEvidenceStep code { position: relative; z-index: 1; display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlEvidenceStep span { color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; font-weight: 800; }
	.mlEvidenceStep b { margin-top: 6px; font-family: var(--dl-font-mono); font-size: 15px; }
	.mlEvidenceStep em { margin-top: 4px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-family: var(--dl-font-mono); font-size: 9px; }
	.mlEvidenceStep small { margin-top: 6px; color: var(--dl-ink-dim, #5b6473); font-size: 9px; line-height: 1.25; }
	.mlEvidenceStep code { margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; }
	.mlEvidenceMeta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 7px; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; }
	.mlEvidenceMeta span { border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; padding: 2px 7px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
	.mlBlockTop, .mlEdgeTop { display: flex; align-items: center; gap: 7px; min-width: 0; }
	.mlBlockK { font-size: 9px; font-weight: 800; color: var(--amber); letter-spacing: .06em; text-transform: uppercase; }
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
	.mlFocus { display: flex; gap: 8px; align-items: flex-start; border-color: rgba(251,146,60,.38); background: rgba(251,146,60,.06); }
	.mlFocusIcon { color: var(--amber); flex: 0 0 auto; margin-top: 1px; }
	.mlFocus div { display: flex; flex-direction: column; gap: 2px; }
	.mlFocus span { color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlDriverTable { display: flex; flex-direction: column; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; overflow: hidden; margin-top: 8px; }
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
	.mlScore.high { color: var(--up); border-color: rgba(52,211,153,.45); }
	.mlScore.medium { color: var(--amber); border-color: rgba(251,146,60,.45); }
	.mlScore.low { color: var(--dl-ink-dim, #5b6473); }
	.mlScore.blocked { color: var(--dn); border-color: rgba(248,113,113,.45); }
	.mlDriverLine { display: flex; flex-direction: column; gap: 1px; min-width: 0; color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.25; }
	.mlDriverLine em { color: var(--amber); font-style: normal; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlDriverLine small { width: max-content; max-width: 100%; color: var(--warn); border: 1px solid rgba(251,146,60,.35); border-radius: 999px; padding: 1px 5px; font-size: 8.5px; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlIconBtn { display: inline-flex; align-items: center; justify-content: center; gap: 3px; width: 72px; border: 1px solid var(--dl-line, #1b2130); background: var(--dl-bg-base, #080d16); color: var(--dl-ink-dim, #5b6473); border-radius: 3px; padding: 3px 4px; cursor: pointer; font-size: 9px; font-weight: 700; }
	.mlIconBtn:hover, .mlIconBtn.on { color: var(--amber); border-color: var(--amber); }
	.mlIconBtn:disabled { cursor: not-allowed; opacity: .48; color: var(--dl-ink-dim, #5b6473); border-color: var(--dl-line, #1b2130); }
	.mlEdgeDetails { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.012); padding: 0; overflow: hidden; }
	.mlEdgeDetails summary { cursor: pointer; list-style: none; padding: 8px 10px; color: var(--dl-ink-dim, #5b6473); font-size: 10px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
	.mlEdgeDetails summary::-webkit-details-marker { display: none; }
	.mlEdgeDetails summary:hover { color: var(--amber); }
	.mlEdgeDetails[open] { padding-bottom: 10px; }
	.mlEdgeDetails[open] .edgeGrid, .mlEdgeDetails[open] .scenarioGrid, .mlEdgeDetails[open] .mlDriverTable { margin: 0 10px; }
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
	.mlScenario.needsEvidence { border-color: rgba(251,146,60,.36); }
	.mlScenario.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.035); }
	.mlScenario em { display: block; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 10px; margin-top: 8px; }
	.mlSrc { padding: 6px 0; border-top: 1px solid rgba(255,255,255,.045); color: var(--dl-ink-dim, #5b6473); font-size: 11px; }
	.mlSrc b { color: var(--warn); font-family: var(--dl-font-mono); font-size: 10px; margin-right: 5px; text-transform: uppercase; }
	.mlSrc em { display: block; margin-top: 2px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 10px; overflow-wrap: anywhere; }
	.mlQuantCard { margin-top: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.016); padding: 9px; }
	.mlQuantCard.ok { border-color: rgba(52,211,153,.42); }
	.mlQuantCard.watch { border-color: rgba(251,146,60,.42); }
	.mlQuantCard.blocked { border-color: rgba(248,113,113,.42); }
	.mlQuantTop { display: flex; align-items: center; gap: 8px; min-width: 0; }
	.mlQuantTop b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dl-ink); font-size: 11px; }
	.mlQuantCard p { margin: 6px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlQuantAlt { margin-top: 7px; border: 1px solid rgba(251,146,60,.28); border-radius: 5px; background: rgba(251,146,60,.03); color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.35; padding: 6px 8px; }
	.mlQualityCard { margin-top: 8px; border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.016); padding: 9px; }
	.mlQualityCard.ok { border-color: rgba(52,211,153,.42); background: rgba(52,211,153,.035); }
	.mlQualityCard.watch { border-color: rgba(251,146,60,.42); background: rgba(251,146,60,.035); }
	.mlQualityCard.blocked { border-color: rgba(248,113,113,.42); background: rgba(248,113,113,.032); }
	.mlQualityTop { display: grid; grid-template-columns: 82px 60px minmax(0, 1fr); gap: 7px; align-items: center; min-width: 0; }
	.mlQualityTop b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 13px; }
	.mlQualityTop em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9.5px; text-align: right; }
	.mlQualityCard.ok .mlQualityTop b { color: var(--up); }
	.mlQualityCard.watch .mlQualityTop b { color: var(--warn); }
	.mlQualityCard.blocked .mlQualityTop b { color: var(--dn); }
	.mlQualityCard p { margin: 7px 0 0; color: var(--dl-ink-dim, #5b6473); font-size: 10.5px; line-height: 1.35; overflow-wrap: anywhere; }
	.mlModelSpec { display: grid; grid-template-columns: 1.35fr .85fr 1fr .62fr; gap: 5px; margin-top: 8px; }
	.mlModelSpecItem { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.018); padding: 6px; }
	.mlModelSpecItem.ok { border-color: rgba(52,211,153,.28); }
	.mlModelSpecItem.blocked { border-color: rgba(248,113,113,.36); }
	.mlModelSpecItem span, .mlModelSpecItem b { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlModelSpecItem span { color: var(--dl-ink-muted, #7b8493); font-size: 8.5px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
	.mlModelSpecItem b { margin-top: 3px; color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlModelMetrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; margin-top: 8px; }
	.mlModelMetric { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.018); padding: 6px; }
	.mlModelMetric.ok { border-color: rgba(52,211,153,.28); }
	.mlModelMetric.watch { border-color: rgba(251,146,60,.34); }
	.mlModelMetric.blocked { border-color: rgba(248,113,113,.36); }
	.mlModelMetric span, .mlModelMetric b { display: block; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlModelMetric span { color: var(--dl-ink-muted, #7b8493); font-size: 8.5px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
	.mlModelMetric b { margin-top: 3px; color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10.5px; }
	.mlModelSource { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 7px; align-items: center; margin-top: 7px; color: var(--dl-ink-muted, #7b8493); font-size: 9px; }
	.mlModelSource span { font-family: var(--dl-font-mono); text-transform: uppercase; }
	.mlModelSource b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--dl-ink-dim, #5b6473); font-family: var(--dl-font-mono); font-size: 9px; }
	.mlIndicatorGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin-top: 6px; }
	.mlIndicatorCard { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.014); padding: 7px; }
	.mlIndicatorCard.ok { border-color: rgba(52,211,153,.28); }
	.mlIndicatorCard.watch { border-color: rgba(251,146,60,.34); }
	.mlIndicatorCard.blocked { border-color: rgba(248,113,113,.38); }
	.mlIndicatorCard div:first-child { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 6px; align-items: center; min-width: 0; }
	.mlIndicatorCard span, .mlIndicatorCard b, .mlIndicatorCard em, .mlIndicatorCard small { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlIndicatorCard span { color: var(--dl-ink-muted, #7b8493); font-family: var(--dl-font-mono); font-size: 8.5px; text-transform: uppercase; }
	.mlIndicatorCard b { color: var(--dl-ink); font-family: var(--dl-font-mono); font-size: 10px; }
	.mlIndicatorCard em { display: block; margin-top: 4px; color: var(--dl-ink-dim, #5b6473); font-style: normal; font-size: 9px; }
	.mlIndicatorCard small { display: block; margin-top: 4px; color: var(--dl-ink-muted, #7b8493); font-size: 8.5px; }
	.mlIndicatorStats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; margin-top: 5px; }
	.mlIndicatorStats span { border: 1px solid rgba(255,255,255,.055); border-radius: 3px; padding: 2px 4px; color: var(--dl-ink-dim, #5b6473); font-size: 8.5px; text-transform: none; }
	.mlMissingLedger, .mlFalsifierStrip { display: grid; gap: 5px; margin-top: 6px; }
	.mlMissingItem, .mlFalsifierToken { min-width: 0; border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; background: rgba(255,255,255,.012); padding: 6px; }
	.mlMissingItem { display: grid; grid-template-columns: 72px minmax(0, 1fr); gap: 5px 7px; align-items: baseline; }
	.mlMissingItem.ok { border-color: rgba(52,211,153,.28); }
	.mlMissingItem.watch { border-color: rgba(251,146,60,.34); }
	.mlMissingItem.blocked { border-color: rgba(248,113,113,.36); }
	.mlMissingItem b, .mlMissingItem span, .mlMissingItem em, .mlFalsifierToken b, .mlFalsifierToken span, .mlFalsifierToken em { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.mlMissingItem b { color: var(--warn); font-family: var(--dl-font-mono); font-size: 9px; text-transform: uppercase; }
	.mlMissingItem span { color: var(--dl-ink-dim, #5b6473); font-size: 10px; }
	.mlMissingItem em { grid-column: 2; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 8.5px; }
	.mlFalsifierStrip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	.mlFalsifierToken.info { border-color: rgba(52,211,153,.26); }
	.mlFalsifierToken.warn { border-color: rgba(251,146,60,.34); }
	.mlFalsifierToken.block { border-color: rgba(248,113,113,.38); }
	.mlFalsifierToken b { display: block; color: var(--dl-ink); font-size: 10px; }
	.mlFalsifierToken span { display: block; margin-top: 3px; color: var(--dl-ink-dim, #5b6473); font-size: 9px; }
	.mlFalsifierToken em { display: block; margin-top: 3px; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-family: var(--dl-font-mono); font-size: 8.5px; }
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
	@media (max-width: 760px) {
		.mlModal { height: 92vh; }
		.mlGrid.two, .mlPhaseStrip, .mlPulseStrip, .mlGateStrip, .mlDrill, .mlRailRows, .mlDashGate { grid-template-columns: 1fr; }
		.mlTabs { min-height: 38px; padding-left: 8px; padding-right: 8px; }
		.mlTabs button { min-width: 50px; min-height: 30px; padding: 8px 9px; text-align: center; }
		.mlDriverHead, .mlDriverRow { grid-template-columns: minmax(132px, 1.3fr) 72px 76px; }
		.mlDriverHead span:nth-child(3), .mlDriverHead span:nth-child(4), .mlDriverHead span:nth-child(5), .mlDriverRow > span:nth-child(3), .mlDriverRow > span:nth-child(4), .mlDriverRow > span:nth-child(5) { display: none; }
		.mlQualityTop, .mlModelSpec, .mlIndicatorGrid, .mlFalsifierStrip { grid-template-columns: 1fr; }
		.mlQualityTop em { text-align: left; }
		.mlModelMetrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
	}
	@media (max-width: 560px) {
		.mlPulseStrip { grid-auto-flow: column; grid-auto-columns: minmax(104px, 1fr); grid-template-columns: none; overflow-x: auto; }
		/* Map 닷그리드 → driver별 카드 리스트 (채워진 칩만, 빈 채널 생략) */
		.mlMapHead { display: none; }
		.mlMapRow { display: flex; flex-direction: column; gap: 6px; }
		.mlMapCol { width: 100%; }
		.mlMapCell { width: 100%; }
		/* 국면 렌즈 — confluence 가로 스와이프(§5.7), GaR 막대는 가로 전폭 유지(5열). */
		.mlConfluence { grid-auto-flow: column; grid-auto-columns: minmax(118px, 1fr); grid-template-columns: none; overflow-x: auto; }
	}
</style>
