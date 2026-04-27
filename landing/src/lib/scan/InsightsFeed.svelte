<script lang="ts">
	/**
	 * 자동 발굴 신호 카드 4종 — 행 미선택 시 디테일 자리에 표시.
	 *
	 *  1. ROE 급상승 TOP  — roeDelta desc, top 10
	 *  2. 영업이익률 급상승 — opMarginDelta desc, top 10
	 *  3. 부채비율 급증 위험 — debtRatioDelta desc, top 10
	 *  4. 우량주 (qualGrade 우수 + roe 15+ + 부채 100-)
	 *
	 * 카드 → 클릭 = 자동 필터 + 정렬 적용 (onApply).
	 */
	import type { ScanNode, FilterCond, SortKey } from './types';
	import { fmtPct } from '$lib/format/pct';

	interface Props {
		nodes: ScanNode[];
		onApply: (cards: { conds: FilterCond[]; sort: SortKey; cols?: string[] }) => void;
		onCompanyClick: (id: string) => void;
	}

	let { nodes, onApply, onCompanyClick }: Props = $props();

	function topByMetric(
		key: string,
		dir: 'desc' | 'asc' = 'desc',
		limit = 5,
		guard?: (n: ScanNode, v: number) => boolean
	) {
		const list = nodes
			.map((n) => {
				const v = (n as Record<string, unknown>)[key];
				if (typeof v !== 'number' || !Number.isFinite(v)) return null;
				if (guard && !guard(n, v)) return null;
				return { n, v };
			})
			.filter((x): x is { n: ScanNode; v: number } => x !== null);
		return list.sort((a, b) => (dir === 'desc' ? b.v - a.v : a.v - b.v)).slice(0, limit);
	}

	// 극단치 noise 필터:
	//  · base 임계 — 이전 값이 0 근처면 % 변화 폭발하므로 현재값으로 base sanity 검증
	//  · delta cap — 60 %p 이상 ROE/opMargin 변화는 데이터 이상 (자본잠식·일시 비용 등)
	let roeRising = $derived(
		topByMetric('roeDelta', 'desc', 5, (n, v) => {
			const cur = n.roe as number | undefined;
			return v >= 3 && v <= 60 && typeof cur === 'number' && cur >= 5;
		})
	);
	let marginRising = $derived(
		topByMetric('opMarginDelta', 'desc', 5, (n, v) => {
			const cur = n.opMargin as number | undefined;
			return v >= 2 && v <= 40 && typeof cur === 'number' && cur >= 0;
		})
	);
	let debtSurge = $derived(
		topByMetric('debtRatioDelta', 'desc', 5, (n, v) => {
			const cur = n.debtRatio as number | undefined;
			// 부채비율 delta 는 절댓값 폭이 크지만 500% 이상 회사는 이미 자본잠식 — 신호로 의미 없음
			return v >= 10 && v <= 500 && typeof cur === 'number' && cur > 0 && cur <= 500;
		})
	);

	let qualityCompounders = $derived.by(() => {
		const list = nodes
			.filter((n) => {
				const q = n.qualGrade as string | undefined;
				const roe = n.roe as number | undefined;
				const debt = n.debtRatio as number | undefined;
				return (
					(q === '우수' || q === '양호') &&
					typeof roe === 'number' &&
					roe >= 15 &&
					typeof debt === 'number' &&
					debt <= 100
				);
			})
			.map((n) => ({ n, v: n.roe as number }))
			.sort((a, b) => b.v - a.v)
			.slice(0, 5);
		return list;
	});

	function applyRoeRising() {
		onApply({
			conds: [
				{ metric: 'roeDelta', op: 'between', value: 3, value2: 60 },
				{ metric: 'roe', op: '>=', value: 5 }
			],
			sort: { key: 'roeDelta', dir: 'desc' },
			cols: ['roeDelta', 'roe', 'opMargin', 'profGrade']
		});
	}
	function applyMarginRising() {
		onApply({
			conds: [
				{ metric: 'opMarginDelta', op: 'between', value: 2, value2: 40 },
				{ metric: 'opMargin', op: '>=', value: 0 }
			],
			sort: { key: 'opMarginDelta', dir: 'desc' },
			cols: ['opMarginDelta', 'opMargin', 'revenueYoyPct']
		});
	}
	function applyDebtSurge() {
		onApply({
			conds: [
				{ metric: 'debtRatioDelta', op: 'between', value: 10, value2: 500 },
				{ metric: 'debtRatio', op: '<=', value: 500 }
			],
			sort: { key: 'debtRatioDelta', dir: 'desc' },
			cols: ['debtRatioDelta', 'debtRatio', 'icr', 'debtGrade']
		});
	}
	function applyQuality() {
		onApply({
			conds: [
				{ metric: 'roe', op: '>=', value: 15 },
				{ metric: 'debtRatio', op: '<=', value: 100 },
				{ metric: 'qualGrade', op: '!=', value: '주의' },
				{ metric: 'qualGrade', op: '!=', value: '위험' }
			],
			sort: { key: 'roe', dir: 'desc' },
			cols: ['qualGrade', 'roe', 'debtRatio']
		});
	}
</script>

<aside class="insights" aria-label="자동 발굴 신호">
	<header class="i-head">
		<span class="i-eyebrow">자동 발굴 신호</span>
		<span class="i-sub">회사 클릭 = 디테일 / 카드 → 클릭 = 그리드 필터</span>
	</header>

	<div class="i-grid">
		<!-- ROE 급상승 -->
		<div class="card good">
			<div class="card-head">
				<span class="card-title">ROE 급상승 회사</span>
				<button type="button" class="card-cta" onclick={applyRoeRising}>전체 보기 →</button>
			</div>
			<div class="card-desc">전기 대비 ROE 가장 많이 개선 (현재 5%↑ · +3~60%p 범위)</div>
			<ul class="card-list">
				{#each roeRising as r (r.n.id)}
					<li>
						<button type="button" class="r-row" onclick={() => onCompanyClick(r.n.id)}>
							<span class="r-dot" style:background={(r.n.color as string) || '#475569'}></span>
							<span class="r-label">{r.n.label}</span>
							<span class="r-val good">{fmtPct(r.v, { withSign: true, suffix: '%p' })}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>

		<!-- 영업이익률 급상승 -->
		<div class="card good">
			<div class="card-head">
				<span class="card-title">영업이익률 개선</span>
				<button type="button" class="card-cta" onclick={applyMarginRising}>전체 보기 →</button>
			</div>
			<div class="card-desc">전기 대비 영업이익률 가장 많이 개선 (흑자 유지 · +2~40%p)</div>
			<ul class="card-list">
				{#each marginRising as r (r.n.id)}
					<li>
						<button type="button" class="r-row" onclick={() => onCompanyClick(r.n.id)}>
							<span class="r-dot" style:background={(r.n.color as string) || '#475569'}></span>
							<span class="r-label">{r.n.label}</span>
							<span class="r-val good">{fmtPct(r.v, { withSign: true, suffix: '%p' })}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>

		<!-- 부채비율 급증 (위험 신호) -->
		<div class="card bad">
			<div class="card-head">
				<span class="card-title">부채비율 급증 위험</span>
				<button type="button" class="card-cta" onclick={applyDebtSurge}>전체 보기 →</button>
			</div>
			<div class="card-desc">전기 대비 부채비율 급등 (현재 부채 500%↓ · +10~500%p)</div>
			<ul class="card-list">
				{#each debtSurge as r (r.n.id)}
					<li>
						<button type="button" class="r-row" onclick={() => onCompanyClick(r.n.id)}>
							<span class="r-dot" style:background={(r.n.color as string) || '#475569'}></span>
							<span class="r-label">{r.n.label}</span>
							<span class="r-val bad">{fmtPct(r.v, { withSign: true, suffix: '%p' })}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>

		<!-- 우량주 (Quality Compounder) -->
		<div class="card good">
			<div class="card-head">
				<span class="card-title">Quality Compounder</span>
				<button type="button" class="card-cta" onclick={applyQuality}>전체 보기 →</button>
			</div>
			<div class="card-desc">ROE 15%↑ + 부채 100%↓ + 이익질 양호↑ — 장기 우량주</div>
			<ul class="card-list">
				{#each qualityCompounders as r (r.n.id)}
					<li>
						<button type="button" class="r-row" onclick={() => onCompanyClick(r.n.id)}>
							<span class="r-dot" style:background={(r.n.color as string) || '#475569'}></span>
							<span class="r-label">{r.n.label}</span>
							<span class="r-val good">{fmtPct(r.v)}</span>
						</button>
					</li>
				{/each}
			</ul>
		</div>
	</div>
</aside>

<style>
	.insights {
		flex-shrink: 0;
		background: #0a0e18;
		border: 1px solid #1e2433;
		border-radius: 6px;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 10px;
		max-height: 32vh;
		overflow-y: auto;
	}
	.i-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 8px;
	}
	.i-eyebrow {
		font-size: 10px;
		font-weight: 600;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}
	.i-sub {
		font-size: 10px;
		color: #64748b;
	}
	.i-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 8px;
	}
	@media (max-width: 1280px) {
		.i-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (max-width: 768px) {
		.i-grid {
			grid-template-columns: 1fr;
		}
	}

	.card {
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 5px;
		padding: 10px 12px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		min-width: 0;
		position: relative;
	}
	.card.good::before {
		content: '';
		position: absolute;
		left: 0;
		top: 12px;
		bottom: 12px;
		width: 2px;
		background: #22c55e;
		border-radius: 2px;
		opacity: 0.6;
	}
	.card.bad::before {
		content: '';
		position: absolute;
		left: 0;
		top: 12px;
		bottom: 12px;
		width: 2px;
		background: #ef4444;
		border-radius: 2px;
		opacity: 0.6;
	}
	.card-head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		padding-left: 8px;
	}
	.card-title {
		font-size: 12px;
		font-weight: 600;
		color: #f1f5f9;
		letter-spacing: -0.01em;
	}
	.card-cta {
		font-size: 10px;
		background: transparent;
		border: none;
		color: #fb923c;
		cursor: pointer;
		font-family: inherit;
		padding: 0;
	}
	.card-cta:hover {
		text-decoration: underline;
	}
	.card-desc {
		font-size: 10px;
		color: #64748b;
		line-height: 1.5;
		padding-left: 8px;
	}

	.card-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}
	.r-row {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 3px 4px 3px 8px;
		background: transparent;
		border: none;
		border-radius: 3px;
		cursor: pointer;
		text-align: left;
		font-family: inherit;
		color: inherit;
		width: 100%;
	}
	.r-row:hover {
		background: rgba(251, 146, 60, 0.06);
	}
	.r-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.r-label {
		flex: 1;
		font-size: 10px;
		color: #cbd5e1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.r-val {
		font-family: monospace;
		font-size: 9px;
		font-variant-numeric: tabular-nums;
	}
	.r-val.good {
		color: #22c55e;
	}
	.r-val.bad {
		color: #ef4444;
	}
</style>
