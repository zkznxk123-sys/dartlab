<script lang="ts">
	// 거시 국면 상세 — 판정 + 자산함의 + 전이 + 모델 합류(probit/sahm/lei/hamilton·금리커브·GaR·Hamilton밴드)
	// + 테마별 고밀도 복합차트(성장/물가/금리/금융조건). KR/US 탭. 차트 = MiniFinChart SSOT(손수 차트 0).
	// 데이터: 판정·타일 = macro.json(라이브) / 시계열 = observations.parquet via loadSeries(rt.macro.getSeries).
	import type { MacroPoint } from '@dartlab/ui-contracts';
	import { MACRO_ATTRIBUTION } from '@dartlab/ui-contracts';
	import type { Lang, MacroFile } from '../lib/types';
	import type { RegimeQuadrantView, MacroRegimeView } from '../lib/macroLens';
	import { buildMacroEvidenceCards, MACRO_EVIDENCE_SPECS } from '../lib/macroLens';
	import MiniFinChart from '../charts/MiniFinChart.svelte';

	interface Props {
		macro: MacroFile;
		regime: RegimeQuadrantView;
		regimeView: MacroRegimeView;
		lang: Lang;
		loadSeries: (id: string) => Promise<MacroPoint[] | null>;
		onClose: () => void;
	}
	let { macro, regime, regimeView, lang, loadSeries, onClose }: Props = $props();
	const T = (kr: string, en: string): string => (lang === 'en' ? en : kr);
	const R = (t: { kr: string; en: string }): string => (lang === 'en' ? t.en : t.kr);

	let market = $state<'KR' | 'US'>('KR');

	$effect(() => {
		const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	const mv = $derived(regime.markets.find((m) => m.market === market) ?? null);
	const lens = $derived(market === 'KR' ? regimeView.kr : regimeView.us);

	function phaseTone(phase: string): string {
		const p = (phase || '').toLowerCase();
		if (/(expansion|recovery|확장|회복)/.test(p)) return 'tUp';
		if (/(contraction|crisis|수축|침체|위기)/.test(p)) return 'tDn';
		if (/(slowdown|둔화|보합)/.test(p)) return 'tWarn';
		return 'tNeu';
	}
	const assetTone = (t: string): string => (t === 'ow' ? 'tUp' : t === 'uw' ? 'tDn' : 'tNeu');
	const wLabel = (t: string): string => (t === 'ow' ? T('확대', 'OW') : t === 'uw' ? T('축소', 'UW') : T('중립', 'NU'));
	const arrow = (s: string): string => (/(ris|up|상승|확장|↑)/i.test(s) ? '↑' : /(fall|down|하락|둔화|↓)/i.test(s) ? '↓' : '→');
	const bucketTone = (b: 0 | 1 | 2 | null): string => (b === 2 ? 'tDn' : b === 1 ? 'tWarn' : b === 0 ? 'tGood' : 'tNeu');

	// ── 근거지표 시계열 로드 — 시장 탭별 필요 id 만 누적 캐시(중복 fetch 0). observations 코어 캐시 공유. ──
	const idsFor = (mk: 'KR' | 'US'): string[] => [...new Set(MACRO_EVIDENCE_SPECS[mk].flatMap((s) => s.series.map((x) => x.id)))];
	let loaded = $state<Record<string, MacroPoint[] | null>>({});
	let loading = $state(true);

	$effect(() => {
		const mk = market;
		const need = idsFor(mk).filter((id) => !(id in loaded));
		if (!need.length) { loading = false; return; }
		loading = true;
		let cancelled = false;
		Promise.all(need.map(async (id) => [id, await loadSeries(id)] as const)).then((pairs) => {
			if (cancelled) return;
			const next = { ...loaded };
			for (const [id, pts] of pairs) next[id] = pts;
			loaded = next;
			loading = false;
		});
		return () => { cancelled = true; };
	});

	const evidence = $derived.by(() => {
		const map: Record<string, MacroPoint[]> = {};
		for (const id of idsFor(market)) { const p = loaded[id]; if (p) map[id] = p; }
		return buildMacroEvidenceCards(market, map, lang);
	});

	// Hamilton 수축확률 밴드 → 가로 스파크 polyline (0~1 고정축).
	const bandPoly = (pts: number[]): string =>
		pts.map((v, i) => `${((i / Math.max(1, pts.length - 1)) * 100).toFixed(1)},${(24 - Math.max(0, Math.min(1, v)) * 24).toFixed(1)}`).join(' ');
</script>

<div class="scrimWrap" role="presentation" onclick={onClose}>
	<div class="scrModal mrModal" role="dialog" aria-modal="true" aria-label={T('거시 국면 상세', 'macro regime detail')} onclick={(e) => e.stopPropagation()}>
		<div class="scrHead">
			<span class="scrTitle">{T('거시 국면', 'MACRO REGIME')}</span>
			<div class="mrTabs">
				<button class={'mrTab' + (market === 'KR' ? ' on' : '')} onclick={() => (market = 'KR')}>{T('한국', 'KOREA')}</button>
				<button class={'mrTab' + (market === 'US' ? ' on' : '')} onclick={() => (market = 'US')}>{T('미국', 'US')}</button>
			</div>
			<button class="scrClose" onclick={onClose} aria-label="close">✕</button>
		</div>

		<div class="mrBody">
			<!-- 상단 2단 — 판정(좌) + 국면 모델 합류(우). 빈 공간 없이 한눈에. -->
			<div class="mrTop" class:two={!!lens}>
			<!-- 1. 판정 -->
			{#if mv}
				<div class="mrSec">
					<div class="mrVerdictBig">
						<span class={'mrPhaseBig ' + phaseTone(mv.phase)}>{mv.phaseLabel || mv.phase}</span>
						{#if mv.quadrantLabel}<span class="mrQuadBig">{mv.quadrantLabel}</span>{/if}
						{#if mv.confidence}<span class="mrConfBig">{T('확신도', 'confidence')} {mv.confidence}</span>{/if}
					</div>
					<div class="mrDirRow">
						{#if mv.growth}<span class="mrDirItem">{T('성장', 'growth')} <b>{arrow(mv.growth)}</b></span>{/if}
						{#if mv.inflation}<span class="mrDirItem">{T('물가', 'inflation')} <b>{arrow(mv.inflation)}</b></span>{/if}
					</div>
					{#if mv.description}<div class="mrDescBig">{mv.description}</div>{/if}
					{#if mv.transition}
						<div class="mrTrans">
							<span class="mrTransLbl">{T('전이', 'transition')}</span>
							<span class="mrTransFlow">{T(mv.transition.fromKr, mv.transition.fromEn)} → {T(mv.transition.toKr, mv.transition.toEn)}</span>
							{#if mv.transition.progressPct != null}
								<span class="mrTransBar"><i style={`width:${Math.max(0, Math.min(100, mv.transition.progressPct))}%`}></i></span>
								<span class="mrTransPct mono">{mv.transition.progressPct.toFixed(0)}%</span>
							{/if}
							<span class="mrTransSig mono">{mv.transition.triggered}/{mv.transition.total}</span>
						</div>
					{/if}
					{#if mv.assets.length}
						<div class="mrAssetsBig">
							{#each mv.assets as a (a.key)}
								<span class={'mrAsset ' + assetTone(a.tone)}>{lang === 'en' ? a.labelEn : a.labelKr}<b>{wLabel(a.tone)}</b></span>
							{/each}
						</div>
					{/if}
				</div>
			{/if}

			<!-- 2. 모델 합류 — probit/sahm/lei/hamilton · 금리커브 · GaR · Hamilton 밴드 -->
			{#if lens}
				<div class="mrSec">
					<div class="mrSecHd">
						<span class="mrSecTitle">{T('국면 모델 합류', 'REGIME MODELS')}</span>
						<span class="mrSecSub">{lens.validCount}/{lens.totalCount} · {R(lens.agreement)}</span>
					</div>
					<div class="mrTiles">
						{#each lens.tiles as t (t.model)}
							<div class={'mrTile' + (t.suppressed ? ' off' : '')}>
								<div class="mrTileHd">{t.modelName}</div>
								<div class={'mrTileZone ' + bucketTone(t.bucket)}>{t.suppressed && t.statusText ? R(t.statusText) : R(t.zoneLabel)}</div>
								{#if t.secondary}<div class="mrTileSec mono">{t.secondary}</div>{/if}
								<div class="mrTileMeta">{R(t.horizonLabel)}{t.stale && t.staleLabel ? ' · ' + t.staleLabel : ''}</div>
							</div>
						{/each}
						{#each lens.notApplicable as na (na.id)}
							<div class="mrTile na"><div class="mrTileHd">{na.label}</div><div class="mrTileNa">{R(na.reason)}</div></div>
						{/each}
					</div>
					<div class="mrModelExtra">
						{#if lens.yieldCurve?.available}
							<div class="mrYc"><span class="mrYcLbl">{T('금리커브', 'yield curve')}</span><span class="mrYcShape">{R(lens.yieldCurve.curveShapeLabel)}</span><span class={'mrYcSpread mono ' + ((lens.yieldCurve.spread ?? 0) < 0 ? 'tDn' : 'tNeu')}>{lens.yieldCurve.spreadText}</span></div>
						{/if}
						{#if lens.gar?.available}
							<div class="mrGar">
								<div class="mrGarHd"><span class="mrYcLbl">GaR</span><span class="mrGarTail">{R(lens.gar.tailRiskLabel)} · {R(lens.gar.horizonLabel)}</span></div>
								<div class="mrGarBars">
									{#each lens.gar.bars as b (b.key)}
										<div class="mrGarRow"><span class="mrGarQ mono">{b.label}</span><span class="mrGarBar"><i style={`width:${Math.max(2, b.frac * 100)}%`}></i></span><span class="mrGarV mono">{b.value.toFixed(1)}</span></div>
									{/each}
								</div>
							</div>
						{/if}
						{#if lens.band?.available && lens.band.points.length}
							<div class="mrBand">
								<span class="mrYcLbl">{R(lens.band.caption)}</span>
								<svg class="mrBandSvg" viewBox="0 0 100 24" preserveAspectRatio="none" role="img" aria-label={R(lens.band.caption)}>
									<line x1="0" y1="12" x2="100" y2="12" class="mrBandMid" />
									<polyline points={bandPoly(lens.band.points)} class="mrBandLine" />
								</svg>
							</div>
						{/if}
					</div>
				</div>
			{/if}

			</div>

			<!-- 3. 근거지표 — 테마별 고밀도 복합차트 (전폭) -->
			<div class="mrSec">
				<div class="mrSecHd">
					<span class="mrSecTitle">{T('근거 지표', 'EVIDENCE INDICATORS')}</span>
					<span class="mrSecSub">{T('월 단위 · 최근 4년 · 호버=수치', 'monthly · last 4y · hover for values')}</span>
				</div>
				{#if evidence.cards.length}
					<div class="finFsGrid mrCharts4">
						{#each evidence.cards as card (card.key)}
							<div class="finMini"><MiniFinChart {card} periods={evidence.periods} /></div>
						{/each}
					</div>
				{:else if loading}
					<div class="mrLoading"><span class="mrSpinner"></span>{T('지표 시계열 불러오는 중', 'loading indicator series')}</div>
				{:else}
					<div class="mrEmpty">{T('지표 시계열 미존재', 'no indicator series')}</div>
				{/if}
			</div>

			<div class="mrFoot">{macro.asOf ? `${T('기준', 'as of')} ${macro.asOf} · ` : ''}{MACRO_ATTRIBUTION}</div>
		</div>
	</div>
</div>
