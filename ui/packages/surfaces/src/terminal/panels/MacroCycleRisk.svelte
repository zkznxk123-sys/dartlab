<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { RegimeMarketLensView, RegimeQuadrantView, RegimeMarketView, RegimeTileView } from '../lib/macroLens';

	// S2 사이클 & 침체위험 — 묻어둔 전향 축(probit·Sahm·LEI·수익률곡선·경기국면)을 *시각*으로.
	// 입력은 전부 view-model(macroLens) — 기하만 로컬 계산. 가짜 채움 0(억제/US전용은 정직 회색).
	// ⛔ 위험 색축 = 침체 군집(bucket: 0 낮음 green / 1 상승 warn / 2 높음 red). 가격 등락(--up/--dn 의미)과 다름.
	interface Props {
		us: RegimeMarketLensView | null;
		kr: RegimeMarketLensView | null;
		quadrant: RegimeQuadrantView | null;
		lang: Lang;
	}
	let { us, kr, quadrant, lang }: Props = $props();
	const T = (kr2: string, en: string) => (lang === 'en' ? en : kr2);

	// 위험 군집 → 색(결정론·bucketOf SSOT). null=데이터 없음(회색).
	const zoneColor = (b: 0 | 1 | 2 | null | undefined): string =>
		b === 0 ? 'var(--up)' : b === 1 ? 'var(--warn)' : b === 2 ? 'var(--dn)' : 'var(--dimmer)';

	// ── SVG 호 기하 (다이얼·링 공용) ──
	const pt = (cx: number, cy: number, r: number, deg: number): [number, number] => {
		const a = (deg * Math.PI) / 180;
		return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
	};
	function arc(cx: number, cy: number, r: number, d1: number, d2: number): string {
		const [x1, y1] = pt(cx, cy, r, d1);
		const [x2, y2] = pt(cx, cy, r, d2);
		const large = Math.abs(d2 - d1) > 180 ? 1 : 0;
		const sweep = d2 > d1 ? 1 : 0;
		return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${large} ${sweep} ${x2.toFixed(2)} ${y2.toFixed(2)}`;
	}

	// ── 침체위험 다이얼 (probit) — 반원 호 180°→360°(상단). ──
	const tileOf = (lens: RegimeMarketLensView | null, model: RegimeTileView['model']): RegimeTileView | null =>
		lens?.tiles.find((t) => t.model === model) ?? null;
	const probit = $derived(tileOf(us, 'probit'));
	const probitFrac = $derived(probit && probit.gaugeValue != null ? Math.max(0, Math.min(1, probit.gaugeValue)) : null);
	const dialTrack = arc(60, 60, 46, 180, 360);
	const dialFill = $derived(probitFrac != null ? arc(60, 60, 46, 180, 180 + probitFrac * 180) : '');
	const dialPct = $derived(probitFrac != null ? Math.round(probitFrac * 100) : null);

	// ── 수익률곡선 온도계 — 0(역전선) 기준 ±2%p 범위로 클램프. ──
	const curve = $derived(us?.yieldCurve ?? null);
	const SPREAD_MAX = 2; // 표시 범위 ±2%p (스케일 상한 — 실수치는 라벨에 그대로).
	const thermoX = $derived(curve && curve.spread != null
		? Math.max(2, Math.min(98, 50 + (Math.max(-SPREAD_MAX, Math.min(SPREAD_MAX, curve.spread)) / SPREAD_MAX) * 48))
		: null);
	// 역전(음수)=red, 정상(양수)=green. 0 근처(±0.1)=warn(평탄 위험).
	const curveColor = $derived(curve && curve.spread != null
		? (curve.spread < 0 ? 'var(--dn)' : curve.spread < 0.1 ? 'var(--warn)' : 'var(--up)')
		: 'var(--dimmer)');

	// ── 경기 사이클 링 — 회복→확장→둔화→수축(시계방향). 현재 위치 + 전이 진행 호. ──
	const PHASE_ORDER = [
		{ key: 'recovery', kr: '회복', en: 'Recovery', deg: 270 },
		{ key: 'expansion', kr: '확장', en: 'Expansion', deg: 0 },
		{ key: 'slowdown', kr: '둔화', en: 'Slowdown', deg: 90 },
		{ key: 'contraction', kr: '수축', en: 'Contraction', deg: 180 }
	] as const;
	const usMkt = $derived(quadrant?.markets?.find((m) => m.market === 'US') ?? null);
	const krMkt = $derived(quadrant?.markets?.find((m) => m.market === 'KR') ?? null);

	type Ring = { nodes: { x: number; y: number; on: boolean; kr: string; en: string }[]; progress: string | null; phaseKr: string; phaseEn: string; transKr: string | null; transEn: string | null; pct: number | null };
	function ringOf(mkt: RegimeMarketView | null): Ring | null {
		if (!mkt) return null;
		const idx = PHASE_ORDER.findIndex((p) => p.key === mkt.phase);
		const nodes = PHASE_ORDER.map((p) => {
			const [x, y] = pt(44, 44, 31, p.deg);
			return { x, y, on: p.key === mkt.phase, kr: p.kr, en: p.en };
		});
		let progress: string | null = null;
		let pct: number | null = null;
		if (idx >= 0 && mkt.transition && mkt.transition.progressPct != null) {
			pct = Math.max(0, Math.min(100, mkt.transition.progressPct));
			const startDeg = PHASE_ORDER[idx].deg;
			progress = arc(44, 44, 31, startDeg, startDeg + (pct / 100) * 90);
		}
		const phaseLabel = mkt.phase && idx >= 0 ? PHASE_ORDER[idx] : null;
		return {
			nodes,
			progress,
			phaseKr: phaseLabel?.kr ?? mkt.phaseLabel ?? mkt.phase ?? '—',
			phaseEn: phaseLabel?.en ?? mkt.phase ?? '—',
			transKr: mkt.transition ? mkt.transition.toKr : null,
			transEn: mkt.transition ? mkt.transition.toEn : null,
			pct
		};
	}
	const usRing = $derived(ringOf(usMkt));
	const krRing = $derived(ringOf(krMkt));

	// ── 신호등 (Sahm·LEI) ──
	const usSignals = $derived([tileOf(us, 'sahm'), tileOf(us, 'lei')].filter((t): t is RegimeTileView => !!t && !t.suppressed));
	const krSignals = $derived((kr?.tiles ?? []).filter((t) => !t.suppressed));

	const hasAny = $derived(!!(us || kr || usMkt || krMkt));
</script>

<section class="cr" aria-label={T('사이클과 침체 위험', 'Cycle and recession risk')}>
	<div class="crHead">
		<span class="crK">CYCLE · RISK</span>
		<b>{T('어디로 가는가 — 경기 국면 · 침체 위험', 'Where it heads — cycle phase · recession risk')}</b>
	</div>

	{#if !hasAny}
		<div class="crNone">{T('전향 데이터 미배포 — macro.json regime 재빌드 필요', 'Forward data not deployed — rebuild macro.json regime')}</div>
	{:else}
		<!-- US 행 — 전향 게이지 full(probit·곡선·사이클·신호) -->
		<div class="crRow">
			<span class="crMkt">US</span>
			<!-- 사이클 링 -->
			{#if usRing}
				<div class="crRing" title={T('경기 4국면 시계 — 회복→확장→둔화→수축', 'business-cycle clock — recovery→expansion→slowdown→contraction')}>
					<svg viewBox="0 0 88 88" aria-hidden="true">
						<circle class="crRingBase" cx="44" cy="44" r="31" />
						{#if usRing.progress}<path class="crRingProg" d={usRing.progress} />{/if}
						{#each usRing.nodes as n (n.kr)}
							<circle class={'crNode' + (n.on ? ' on' : '')} cx={n.x} cy={n.y} r={n.on ? 5 : 2.6} />
						{/each}
					</svg>
					<div class="crRingLbl"><b>{T(usRing.phaseKr, usRing.phaseEn)}</b>{#if usRing.transKr && usRing.pct != null}<em>→{T(usRing.transKr, usRing.transEn ?? '')} {usRing.pct}%</em>{/if}</div>
				</div>
			{/if}
			<!-- 침체위험 다이얼 -->
			<div class="crDial" title={probit ? T(probit.note.kr, probit.note.en) : T('probit 미가용', 'probit unavailable')}>
				{#if dialPct != null && probit}
					<svg viewBox="0 0 120 76" aria-hidden="true">
						<path class="crDialTrack" d={dialTrack} />
						<path class="crDialFill" d={dialFill} style={`stroke:${zoneColor(probit.bucket)}`} />
						<text class="crDialNum" x="60" y="54" text-anchor="middle" style={`fill:${zoneColor(probit.bucket)}`}>{dialPct}<tspan class="crDialPct">%</tspan></text>
					</svg>
					<div class="crDialLbl"><b>{T('침체확률', 'recession prob')} · {T(probit.zoneLabel.kr, probit.zoneLabel.en)}</b><em>{T(probit.horizonLabel.kr, probit.horizonLabel.en)}</em></div>
				{:else}
					<div class="crGhost">{T('침체확률', 'recession prob')}<span>{probit?.suppressed ? T(probit.statusText?.kr ?? '보류', probit.statusText?.en ?? 'suppressed') : '—'}</span></div>
				{/if}
			</div>
			<!-- 수익률곡선 온도계 -->
			<div class="crCurve" title={curve ? T(curve.note.kr, curve.note.en) : ''}>
				{#if curve && thermoX != null}
					<div class="crCurveTop"><span>{T('수익률곡선 10Y-3M', 'yield curve 10Y-3M')}</span><b style={`color:${curveColor}`}>{curve.spreadText}</b></div>
					<div class="crThermo">
						<i class="crThermoZero"></i>
						<i class="crThermoMark" style={`left:${thermoX}%;background:${curveColor}`}></i>
					</div>
					<div class="crCurveFoot"><em>{T('역전', 'inverted')}</em><span>{T(curve.curveShapeLabel.kr, curve.curveShapeLabel.en)}</span><em>{T('정상', 'normal')}</em></div>
				{:else}
					<div class="crGhost">{T('수익률곡선', 'yield curve')}<span>—</span></div>
				{/if}
			</div>
			<!-- 신호등 -->
			{#if usSignals.length}
				<div class="crLights">
					{#each usSignals as s (s.model)}
						<span class="crLight" title={T(s.note.kr, s.note.en)}><i style={`background:${zoneColor(s.bucket)}`}></i>{s.modelName} <b>{T(s.zoneLabel.kr, s.zoneLabel.en)}</b></span>
					{/each}
				</div>
			{/if}
		</div>

		<!-- KR 행 — 사이클 + LEI(CLI), probit·곡선은 US 전용(정직 표시) -->
		{#if krRing || krSignals.length}
			<div class="crRow">
				<span class="crMkt">KR</span>
				{#if krRing}
					<div class="crRing" title={T('경기 4국면 시계', 'business-cycle clock')}>
						<svg viewBox="0 0 88 88" aria-hidden="true">
							<circle class="crRingBase" cx="44" cy="44" r="31" />
							{#if krRing.progress}<path class="crRingProg" d={krRing.progress} />{/if}
							{#each krRing.nodes as n (n.kr)}
								<circle class={'crNode' + (n.on ? ' on' : '')} cx={n.x} cy={n.y} r={n.on ? 5 : 2.6} />
							{/each}
						</svg>
						<div class="crRingLbl"><b>{T(krRing.phaseKr, krRing.phaseEn)}</b>{#if krRing.transKr && krRing.pct != null}<em>→{T(krRing.transKr, krRing.transEn ?? '')} {krRing.pct}%</em>{/if}</div>
					</div>
				{/if}
				{#if krSignals.length}
					<div class="crLights">
						{#each krSignals as s (s.model)}
							<span class="crLight" title={T(s.note.kr, s.note.en)}><i style={`background:${zoneColor(s.bucket)}`}></i>{s.modelName} <b>{T(s.zoneLabel.kr, s.zoneLabel.en)}</b></span>
						{/each}
					</div>
				{/if}
				<span class="crNa">{T('probit · 수익률곡선 = US 전용', 'probit · yield curve = US-only')}</span>
			</div>
		{/if}
	{/if}
</section>

<style>
	.cr { border: 1px solid var(--bd); border-radius: 8px; background: var(--panel); padding: 9px 12px 10px; }
	.crHead { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
	.crK { font-family: var(--mono); color: var(--amber); font-weight: 800; font-size: 9px; letter-spacing: .06em; flex: 0 0 auto; }
	.crHead b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 700; color: var(--txt); }
	.crNone { color: var(--dim); font-size: 10px; padding: 14px 4px; text-align: center; }
	/* 시장 행 — 게이지 가로 배치, 좁으면 wrap */
	.crRow { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-top: 9px; padding-top: 9px; border-top: 1px solid var(--bd); }
	.crRow:first-of-type { border-top: 0; }
	.crMkt { flex: 0 0 auto; width: 22px; color: var(--amber); font-family: var(--mono); font-size: 12px; font-weight: 800; }

	/* 사이클 링 */
	.crRing { display: flex; align-items: center; gap: 9px; }
	.crRing svg { width: 64px; height: 64px; flex: 0 0 auto; }
	.crRingBase { fill: none; stroke: var(--bd); stroke-width: 2; }
	.crRingProg { fill: none; stroke: var(--amber); stroke-width: 3; stroke-linecap: round; opacity: .9; }
	.crNode { fill: var(--dimmer); }
	.crNode.on { fill: var(--amber); }
	.crRingLbl { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
	.crRingLbl b { font-size: 13px; font-weight: 700; color: var(--txt); }
	.crRingLbl em { font-style: normal; font-size: 9px; color: var(--dim); font-family: var(--mono); }

	/* 침체위험 다이얼 */
	.crDial { display: flex; flex-direction: column; align-items: center; gap: 2px; }
	.crDial svg { width: 92px; height: 58px; }
	.crDialTrack { fill: none; stroke: var(--bd); stroke-width: 9; stroke-linecap: round; }
	.crDialFill { fill: none; stroke-width: 9; stroke-linecap: round; }
	.crDialNum { font-family: var(--mono); font-size: 23px; font-weight: 800; }
	.crDialPct { font-size: 11px; }
	.crDialLbl { display: flex; flex-direction: column; align-items: center; gap: 1px; text-align: center; }
	.crDialLbl b { font-size: 10px; font-weight: 700; color: var(--txt); }
	.crDialLbl em { font-style: normal; font-size: 8.5px; color: var(--dim); font-family: var(--mono); }

	/* 수익률곡선 온도계 */
	.crCurve { flex: 1 1 160px; min-width: 150px; max-width: 230px; }
	.crCurveTop { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
	.crCurveTop span { font-size: 9.5px; color: var(--dim); }
	.crCurveTop b { font-family: var(--mono); font-size: 13px; font-weight: 800; }
	.crThermo { position: relative; height: 8px; border-radius: 999px; background: linear-gradient(90deg, rgba(240,97,111,.22), rgba(255,255,255,.05) 50%, rgba(52,211,153,.22)); margin: 5px 0 3px; }
	.crThermoZero { position: absolute; left: 50%; top: -2px; bottom: -2px; width: 1px; background: var(--dim); opacity: .6; }
	.crThermoMark { position: absolute; top: 50%; width: 10px; height: 10px; border-radius: 50%; transform: translate(-50%, -50%); box-shadow: 0 0 0 2px var(--panel); }
	.crCurveFoot { display: flex; align-items: baseline; justify-content: space-between; gap: 6px; }
	.crCurveFoot em { font-style: normal; font-size: 8px; color: var(--dimmer); }
	.crCurveFoot span { font-size: 9px; color: var(--txt); font-weight: 600; }

	/* 신호등 */
	.crLights { display: flex; flex-wrap: wrap; gap: 5px 10px; align-items: center; }
	.crLight { display: inline-flex; align-items: center; gap: 5px; font-size: 9.5px; color: var(--dim); }
	.crLight i { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
	.crLight b { color: var(--txt); font-weight: 700; font-size: 10px; }

	/* 정직 placeholder */
	.crGhost { display: flex; flex-direction: column; gap: 2px; font-size: 9px; color: var(--dimmer); min-width: 70px; }
	.crGhost span { font-size: 11px; color: var(--dim); font-family: var(--mono); }
	.crNa { font-size: 8.5px; color: var(--dimmer); margin-left: auto; }

	@media (max-width: 640px) {
		.crRow { gap: 12px; }
		.crCurve { flex-basis: 100%; max-width: none; }
	}
</style>
