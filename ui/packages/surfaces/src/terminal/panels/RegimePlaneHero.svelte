<script lang="ts">
	import type { Lang } from '../lib/types';
	import type { RegimeMarketView, RegimeQuadrantView } from '../lib/macroLens';

	interface Props {
		view: RegimeQuadrantView;
		lang: Lang;
	}
	let { view, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);

	// ── GIP 4사분면 기하 (Hedgeye/Gavekal Growth×Inflation) — 성장(세로 ↑=rising) × 물가(가로 →=rising).
	// 멤버십 배치(연속좌표 금지·07-visual-research). viewBox 320×240, 축 라벨용 마진.
	const RECT: Record<string, { x: number; y: number; w: number; h: number }> = {
		goldilocks: { x: 8, y: 16, w: 152, h: 100 },
		reflation: { x: 160, y: 16, w: 152, h: 100 },
		deflation: { x: 8, y: 116, w: 152, h: 100 },
		stagflation: { x: 160, y: 116, w: 152, h: 100 }
	};
	const CENTER: Record<string, { cx: number; cy: number }> = {
		goldilocks: { cx: 84, cy: 66 }, reflation: { cx: 236, cy: 66 },
		deflation: { cx: 84, cy: 166 }, stagflation: { cx: 236, cy: 166 }
	};
	// 사분면 이름 + 표준 자산 틸트(국면 교과서 — 추천 아님·라벨 명시). 코너 앵커.
	const QUAD = [
		{ key: 'goldilocks', nameKr: '골디락스', nameEn: 'Goldilocks', tiltKr: '주식·성장주', tiltEn: 'Equity·Growth', lx: 16, ly: 30, anchor: 'start' as const },
		{ key: 'reflation', nameKr: '리플레이션', nameEn: 'Reflation', tiltKr: '주식·원자재·경기민감', tiltEn: 'Equity·Comdty·Cyclical', lx: 304, ly: 30, anchor: 'end' as const },
		{ key: 'deflation', nameKr: '디플레이션', nameEn: 'Deflation', tiltKr: '채권·방어주·현금', tiltEn: 'Bonds·Defensive·Cash', lx: 16, ly: 200, anchor: 'start' as const },
		{ key: 'stagflation', nameKr: '스태그플레이션', nameEn: 'Stagflation', tiltKr: '현금·금·원자재', tiltEn: 'Cash·Gold·Comdty', lx: 304, ly: 200, anchor: 'end' as const }
	] as const;
	const quadName = (k: string) => { const q = QUAD.find((x) => x.key === k); return q ? T(q.nameKr, q.nameEn) : k; };

	const motion = (v: string | null | undefined): string => {
		const raw = (v ?? '').toLowerCase();
		if (raw === 'rising') return T('상승', 'rising');
		if (raw === 'falling') return T('하락', 'falling');
		if (raw === 'stable') return T('횡보', 'stable');
		return v || '—';
	};
	const motionCls = (v: string | null | undefined): string => {
		const raw = (v ?? '').toLowerCase();
		return raw === 'rising' ? 'up' : raw === 'falling' ? 'down' : 'flat';
	};
	// 경기 사이클 phase 라벨 — KR 은 backend 정본 label, EN 은 enum 매핑(SSOT=엔진 label·재유도 금지).
	const PHASE_EN: Record<string, string> = {
		expansion: 'Expansion', slowdown: 'Slowdown', contraction: 'Contraction', recovery: 'Recovery',
		stagflation: 'Stagflation', reflation: 'Reflation', deflation: 'Deflation', goldilocks: 'Goldilocks'
	};
	const phaseTxt = (m: RegimeMarketView): string => (lang === 'en' ? (PHASE_EN[m.phase] ?? m.phase) : (m.phaseLabel || m.phase));

	// 마커 배치 — 같은 사분면의 KR/US 가로 분산(겹침 방지).
	const placed = $derived.by(() => {
		const byCell = new Map<string, RegimeMarketView[]>();
		for (const m of view.markets) {
			if (!m.cellKey) continue;
			const arr = byCell.get(m.cellKey) ?? [];
			arr.push(m);
			byCell.set(m.cellKey, arr);
		}
		const out: { m: RegimeMarketView; x: number; y: number }[] = [];
		for (const [key, ms] of byCell) {
			const base = CENTER[key];
			if (!base) continue;
			ms.forEach((m, i) => {
				const dx = ms.length > 1 ? (i - (ms.length - 1) / 2) * 44 : 0;
				out.push({ m, x: base.cx + dx, y: base.cy });
			});
		}
		return out;
	});
	const activeCells = $derived(new Set(placed.map((p) => p.m.cellKey)));
	const noQuadrant = $derived(view.markets.every((m) => !m.cellKey));
	// 비중확대 자산(view-model assetImplication) — 없으면 표준 틸트로 폴백(둘 다 '교과서' 라벨).
	const overweights = (m: RegimeMarketView): string =>
		m.assets.filter((a) => a.weight === 'overweight').map((a) => T(a.labelKr, a.labelEn)).join(' · ');
	const tiltOf = (cellKey: string | null): string => {
		const q = QUAD.find((x) => x.key === cellKey);
		return q ? T(q.tiltKr, q.tiltEn) : '';
	};
	const freshLabel = $derived(view.freshness?.label ?? '');
</script>

<section class="rh" aria-label={T('국면 평면', 'Regime plane')}>
	<div class="rhHead">
		<span class="rhK">REGIME PLANE</span>
		<b>{T('성장 × 물가 국면', 'Growth × Inflation regime')}</b>
		<em class="rhAsOf">{#if view.asOf}░{view.asOf}{/if}{#if freshLabel} · {freshLabel}{/if}</em>
	</div>

	<div class="rhBody">
		<svg class="rhPlane" viewBox="0 0 320 240" role="img"
			aria-label={T('성장×물가 4사분면 평면, KR·US 위치', 'growth×inflation four-quadrant plane with KR·US positions')}>
			<!-- 사분면 칸 -->
			{#each QUAD as q (q.key)}
				<rect class={'rhQuad' + (activeCells.has(q.key) ? ' on' : '')} x={RECT[q.key].x} y={RECT[q.key].y} width={RECT[q.key].w} height={RECT[q.key].h} rx="4" />
			{/each}
			<!-- 십자축 -->
			<line class="rhCross" x1="160" y1="16" x2="160" y2="216" />
			<line class="rhCross" x1="8" y1="116" x2="312" y2="116" />
			<!-- 사분면 이름 + 교과서 틸트 -->
			{#each QUAD as q (q.key)}
				<text class={'rhQuadName' + (activeCells.has(q.key) ? ' on' : '')} x={q.lx} y={q.ly} text-anchor={q.anchor}>{T(q.nameKr, q.nameEn)}</text>
				<text class="rhQuadTilt" x={q.lx} y={q.ly + 13} text-anchor={q.anchor}>{T(q.tiltKr, q.tiltEn)}</text>
			{/each}
			<!-- 축 큐 -->
			<text class="rhAxis" x="160" y="11" text-anchor="middle">↑ {T('성장', 'growth')}</text>
			<text class="rhAxis" x="160" y="236" text-anchor="middle">{T('물가', 'inflation')} →</text>
			<!-- 시장 마커 -->
			{#each placed as p (p.m.market)}
				<circle class="rhMark" cx={p.x} cy={p.y} r="9" />
				<text class="rhMarkLbl" x={p.x} y={p.y + 3.5} text-anchor="middle">{p.m.market}</text>
			{/each}
		</svg>

		<!-- 컨텍스트 레일 — 시장별 사이클 국면 · 모션 · 전이 진행 · 비중확대 -->
		<div class="rhRail">
			{#each view.markets as m (m.market)}
				<div class="rhCard" title={m.description}>
					<div class="rhCardTop">
						<b class="rhMkt">{m.market}</b>
						<span class="rhPhase">{m.cellKey ? quadName(m.cellKey) : phaseTxt(m)}</span>
					</div>
					<div class="rhMotion">
						<span class={'rhMo ' + motionCls(m.growth)}>{T('성장', 'growth')} {motion(m.growth)}</span>
						<span class={'rhMo ' + motionCls(m.inflation)}>{T('물가', 'inflation')} {motion(m.inflation)}</span>
						<span class="rhCycle" class:conflict={m.lensConflict} title={m.lensConflict ? T('GIP 국면(성장×물가)과 경기 사이클 렌즈가 상이', 'GIP regime (growth×inflation) and business-cycle lens differ') : ''}>{T('사이클', 'cycle')} {phaseTxt(m)}{#if m.lensConflict} ≠{/if}</span>
					</div>
					{#if m.transition}
						<div class="rhTrans">
							<div class="rhTransLine">
								<span>{T(m.transition.fromKr, m.transition.fromEn)}</span>
								<i aria-hidden="true">→</i>
								<span>{T(m.transition.toKr, m.transition.toEn)}</span>
								<em>{m.transition.triggered}/{m.transition.total} {T('신호', 'signals')}</em>
							</div>
							{#if m.transition.progressPct != null}
								<div class="rhBar"><i style={`width:${Math.max(3, Math.min(100, m.transition.progressPct))}%`}></i></div>
							{/if}
						</div>
					{/if}
					{#if overweights(m) || tiltOf(m.cellKey)}
						<div class="rhTilt"><span>{T('비중확대', 'overweight')}</span><b>{overweights(m) || tiltOf(m.cellKey)}</b></div>
					{/if}
				</div>
			{/each}
			{#if noQuadrant}
				<div class="rhNa">{T('국면 격자 미산출 — 사분면은 참조 지도', 'No regime grid — quadrants shown as reference map')}</div>
			{/if}
		</div>
	</div>
	<div class="rhFoot">{T('국면 교과서 · 추천 아님 · 위치는 회고적', 'Regime textbook · not advice · position is retrospective')}</div>
</section>

<style>
	.rh { border: 1px solid var(--bd); border-radius: 8px; background: var(--panel); padding: 10px 12px 9px; }
	.rhHead { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
	.rhK { font-family: var(--dl-font-mono); color: var(--amber); font-weight: 800; font-size: 9px; letter-spacing: .06em; }
	.rhHead b { flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 700; }
	.rhAsOf { margin-left: auto; color: var(--dl-ink-muted, #7b8493); font-style: normal; font-size: 9px; font-family: var(--dl-font-mono); white-space: nowrap; }
	.rhBody { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr); gap: 12px; margin-top: 8px; align-items: stretch; }
	/* 평면 — element 종횡비=viewBox(320:240) 라 왜곡·letterbox 0 */
	.rhPlane { display: block; width: 100%; aspect-ratio: 320 / 240; }
	.rhQuad { fill: rgba(255,255,255,.015); stroke: rgba(255,255,255,.04); stroke-width: 1; }
	.rhQuad.on { fill: rgba(var(--amber-rgb),.10); stroke: rgba(var(--amber-rgb),.32); }
	.rhCross { stroke: var(--bd); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 2 3; opacity: .8; }
	.rhQuadName { fill: var(--dim); font-size: 10px; font-weight: 700; opacity: .62; }
	.rhQuadName.on { fill: var(--amber); opacity: 1; }
	.rhQuadTilt { fill: var(--dl-ink-muted, #7b8493); font-size: 7.5px; font-family: var(--mono); opacity: .72; }
	.rhAxis { fill: var(--dim); font-size: 8px; font-family: var(--mono); opacity: .82; }
	.rhMark { fill: var(--amber); stroke: var(--panel); stroke-width: 2; }
	.rhMarkLbl { fill: var(--dl-bg-base, #0f0f10); font-size: 8.5px; font-weight: 800; font-family: var(--mono); }
	/* 레일 */
	.rhRail { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
	.rhCard { border: 1px solid var(--dl-line, #1b2130); border-radius: 6px; background: rgba(255,255,255,.018); padding: 8px 9px; min-width: 0; }
	.rhCardTop { display: flex; align-items: baseline; gap: 7px; min-width: 0; }
	.rhMkt { flex: 0 0 auto; color: var(--amber); font-family: var(--mono); font-size: 11px; font-weight: 800; }
	.rhPhase { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); font-size: 13px; font-weight: 700; }
	.rhMotion { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
	.rhMo { font-size: 9.5px; color: var(--dl-ink-dim, #5b6473); border: 1px solid var(--dl-line, #1b2130); border-radius: 999px; padding: 1px 7px; }
	.rhMo.up { color: var(--up); border-color: rgba(228,63,63,.32); }
	.rhMo.down { color: var(--down); border-color: rgba(29,100,220,.32); }
	/* 사이클 phase 칩 — GIP 국면과 구분(2차). 상이(lensConflict) 시 dim + ≠ 표기(과장·경보 아님). */
	.rhCycle { font-size: 9.5px; color: var(--dl-ink-muted, #7b8493); border: 1px dashed var(--dl-line, #1b2130); border-radius: 999px; padding: 1px 7px; }
	.rhCycle.conflict { color: var(--dl-ink-dim, #5b6473); border-color: rgba(var(--amber-rgb),.34); }
	.rhTrans { margin-top: 7px; }
	.rhTransLine { display: flex; align-items: baseline; flex-wrap: wrap; gap: 5px; font-size: 10px; color: var(--fg); }
	.rhTransLine i { font-style: normal; color: var(--amber); }
	.rhTransLine em { margin-left: auto; font-style: normal; color: var(--dl-ink-muted, #7b8493); font-size: 8.5px; font-family: var(--mono); }
	.rhBar { height: 5px; border-radius: 999px; background: rgba(255,255,255,.05); overflow: hidden; margin-top: 4px; }
	.rhBar i { display: block; height: 100%; border-radius: 999px; background: var(--amber); opacity: .82; }
	.rhTilt { display: flex; align-items: baseline; gap: 6px; margin-top: 7px; min-width: 0; }
	.rhTilt span { flex: 0 0 auto; color: var(--dl-ink-dim, #5b6473); font-size: 8px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
	.rhTilt b { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--fg); font-size: 10px; font-weight: 600; }
	.rhNa { color: var(--dl-ink-dim, #5b6473); font-size: 9.5px; line-height: 1.4; }
	.rhFoot { margin-top: 8px; color: var(--dl-ink-muted, #7b8493); font-size: 9px; line-height: 1.3; }
	@media (max-width: 760px) {
		.rhBody { grid-template-columns: 1fr; }
	}
</style>
