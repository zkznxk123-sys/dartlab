<script lang="ts">
	import type {
		LiveCompanyChange,
		LiveCompanyDocExcerpt,
		LiveCompanyEvidence,
		LiveCompanyReportFact
	} from '$lib/browser/companyLive';

	let {
		evidence,
		facts = [],
		docs = [],
		changes = []
	}: {
		evidence: LiveCompanyEvidence | null;
		facts?: LiveCompanyReportFact[];
		docs?: LiveCompanyDocExcerpt[];
		changes?: LiveCompanyChange[];
	} = $props();

	function fmt(value: number | string | null, unit: string): string {
		if (typeof value === 'string') return value || '데이터 없음';
		if (value == null || !Number.isFinite(value)) return '데이터 없음';
		if (unit === '%') return `${value.toFixed(1)}%`;
		const abs = Math.abs(value);
		if (abs >= 1e12) return `${(value / 1e12).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}조`;
		if (abs >= 1e8) return `${Math.round(value / 1e8).toLocaleString('ko-KR')}억`;
		return Math.round(value).toLocaleString('ko-KR');
	}
</script>

<aside class="panel">
	<section>
		<div class="eyebrow">근거 추적</div>
		<h3>{evidence ? '선택 계정' : '근거 현황'}</h3>
		{#if evidence}
			<strong>{evidence.accountLabel}</strong>
			<div class="values">
				{#each evidence.values as item}
					<div>
						<span>{item.period}</span>
						<b>{fmt(item.value, item.unit)}</b>
					</div>
				{/each}
			</div>
		{:else}
			<div class="source-stats">
				<div><span>정기보고서</span><b>{facts.length}</b></div>
				<div><span>원문 발췌</span><b>{docs.length}</b></div>
				<div><span>공시 변화</span><b>{changes.length}</b></div>
			</div>
			<p>아래 IS/BS/CF 계정을 누르면 값과 연결 근거가 이 패널에 고정됩니다.</p>
		{/if}
	</section>

	<section>
		<div class="eyebrow">정기보고서</div>
		<h3>정기보고서 근거</h3>
		{#if evidence?.facts.length}
			<div class="cards">
				{#each evidence.facts as fact}
					<article>
						<span>{fact.label}</span>
						<strong>{fact.value}</strong>
						<p>{fact.detail || '세부 값 없음'}</p>
					</article>
				{/each}
			</div>
		{:else if facts.length}
			<div class="cards">
				{#each facts.slice(0, 3) as fact}
					<article>
						<span>{fact.label}</span>
						<strong>{fact.value}</strong>
						<p>{fact.detail || '세부 값 없음'}</p>
					</article>
				{/each}
			</div>
		{:else}
			<p>연결된 정기보고서 팩트가 없습니다.</p>
		{/if}
	</section>

	<section>
		<div class="eyebrow">원문</div>
		<h3>사업보고서 원문</h3>
		{#if evidence?.docs.length}
			<div class="docs">
				{#each evidence.docs.slice(0, 4) as doc}
					<article>
						<strong>{doc.title}</strong>
						<span>{doc.year ?? '연도 없음'} · {doc.reportType ?? '보고서'}</span>
						<p>{doc.excerpt}</p>
					</article>
				{/each}
			</div>
		{:else if docs.length}
			<div class="docs">
				{#each docs.slice(0, 3) as doc}
					<article>
						<strong>{doc.title}</strong>
						<span>{doc.year ?? '연도 없음'} · {doc.reportType ?? '보고서'}</span>
						<p>{doc.excerpt}</p>
					</article>
				{/each}
			</div>
		{:else}
			<p>연결된 원문 발췌가 없습니다.</p>
		{/if}
	</section>
</aside>

<style>
	.panel {
		position: sticky;
		top: 84px;
		display: grid;
		gap: 12px;
	}
	section {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.9);
		padding: 16px;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 800;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		margin-top: 5px;
		font-size: 16px;
	}
	section > strong {
		display: block;
		margin-top: 12px;
	}
	p,
	.values span,
	article span {
		color: #94a3b8;
		font-size: 12px;
	}
	p {
		margin-top: 8px;
		line-height: 1.5;
	}
	.values,
	.source-stats,
	.cards,
	.docs {
		display: grid;
		gap: 8px;
		margin-top: 12px;
	}
	.values div,
	.source-stats div,
	article {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
	}
	.values div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 8px;
	}
	.source-stats {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}
	.source-stats div {
		padding: 8px;
	}
	.source-stats span,
	.source-stats b {
		display: block;
	}
	.source-stats span {
		color: #94a3b8;
		font-size: 11px;
	}
	.source-stats b {
		margin-top: 4px;
		font-size: 18px;
	}
	article {
		padding: 10px;
	}
	article span,
	article strong {
		display: block;
	}
	article strong {
		margin-top: 4px;
	}
	@media (max-width: 1180px) {
		.panel {
			position: static;
		}
	}
</style>
