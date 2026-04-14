<script lang="ts">
	interface SupplyInsights {
		supplierCount: number;
		customerCount: number;
		preciseEdgeCount: number;
		totalSupplyAmount: number;
		hhi: number;
		hhiRisk: string;
		top1Ratio: number;
		top3Ratio: number;
		industryDiversity: number;
		stageDiversity: number;
		topSupplyIndustries: Array<[string, number]>;
		topSupplyStages: Array<[string, number]>;
	}

	let { data }: { data: SupplyInsights } = $props();

	let riskColor = $derived.by(() => {
		if (data.hhi >= 2500) return '#f87171'; // 집중=빨강
		if (data.hhi >= 1500) return '#fb923c'; // 중간=주황
		if (data.hhi > 0) return '#34d399'; // 분산=초록
		return '#64748b';
	});

	function formatAmount(v: number): string {
		if (v >= 10000) return `${(v / 10000).toFixed(1)}조원`;
		return `${v.toLocaleString()}억원`;
	}
</script>

<div class="insight-grid">
	<!-- 집중도 카드 -->
	<div class="card">
		<div class="label">공급망 집중도</div>
		<div class="big-value" style="color: {riskColor}">{data.hhiRisk}</div>
		<div class="sub">
			HHI {data.hhi.toLocaleString()} · 상위 3사 {data.top3Ratio}%
		</div>
	</div>

	<!-- 상위 1사 비중 -->
	<div class="card">
		<div class="label">최대 의존도</div>
		<div class="big-value">{data.top1Ratio}%</div>
		<div class="sub">가장 큰 공급사 비중</div>
	</div>

	<!-- 공급사 수 -->
	<div class="card">
		<div class="label">공급망 규모</div>
		<div class="big-value">{data.supplierCount}사</div>
		<div class="sub">
			정밀 엣지 {data.preciseEdgeCount}건
			{#if data.totalSupplyAmount > 0}
				· {formatAmount(data.totalSupplyAmount)}
			{/if}
		</div>
	</div>

	<!-- 다양성 -->
	<div class="card">
		<div class="label">공급망 다양성</div>
		<div class="big-value">{data.industryDiversity}산업</div>
		<div class="sub">{data.stageDiversity}개 공정 분산</div>
	</div>
</div>

<style>
	.insight-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 12px;
	}
	.card {
		background: #0f1219;
		border: 1px solid #1e2433;
		border-radius: 10px;
		padding: 16px;
	}
	.label {
		font-size: 11px;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 8px;
	}
	.big-value {
		font-size: 24px;
		font-weight: 700;
		color: #f1f5f9;
		line-height: 1.1;
		margin-bottom: 6px;
	}
	.sub {
		font-size: 11px;
		color: #64748b;
		line-height: 1.4;
	}
	@media (max-width: 768px) {
		.insight-grid {
			grid-template-columns: repeat(2, 1fr);
		}
	}
</style>
