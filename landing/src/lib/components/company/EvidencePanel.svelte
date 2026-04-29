<script lang="ts">
	import { Dialog } from 'bits-ui';
	import { X } from 'lucide-svelte';
	import type {
		LiveCompanyChange,
		LiveCompanyDocExcerpt,
		LiveCompanyEvidence,
		LiveCompanyReportFact,
		LiveCompanySourceStatus
	} from '$lib/browser/companyLive';
	import { formatTableValue } from '$lib/browser/companyDashboardModel';

	let {
		open = $bindable(false),
		evidence,
		facts = [],
		docs = [],
		changes = [],
		sourceStatus = []
	}: {
		open?: boolean;
		evidence: LiveCompanyEvidence | null;
		facts?: LiveCompanyReportFact[];
		docs?: LiveCompanyDocExcerpt[];
		changes?: LiveCompanyChange[];
		sourceStatus?: LiveCompanySourceStatus[];
	} = $props();

	function statusText(status: LiveCompanySourceStatus['status']): string {
		if (status === 'ready') return '준비됨';
		if (status === 'lazy') return '필요 시 로드';
		if (status === 'fallback') return '요약 사용';
		return '대기';
	}

	function cleanSource(source: string): string {
		if (!source) return '대기';
		if (source.includes('finance')) return '재무제표';
		if (source.includes('docs')) return '사업보고서 원문';
		if (source.includes('report')) return '정기보고서';
		if (source.includes('map') || source.includes('dashboard')) return '산업지도';
		if (source.includes('price')) return '시장가격';
		return '원본 데이터';
	}
</script>

<Dialog.Root bind:open>
	<Dialog.Portal>
		<Dialog.Overlay class="backdrop" />
		<Dialog.Content class="drawer" aria-describedby="evidence-desc">
			<header>
				<div>
					<div class="eyebrow">근거 추적</div>
					<Dialog.Title class="title">{evidence ? evidence.accountLabel : '데이터 소스 현황'}</Dialog.Title>
					<Dialog.Description class="desc" id="evidence-desc">
						재무제표 값, 정기보고서 팩트, 사업보고서 원문, 공시 변화를 한곳에서 확인합니다.
					</Dialog.Description>
				</div>
				<Dialog.Close class="close" aria-label="닫기">
					<X size={17} />
				</Dialog.Close>
			</header>

			{#if evidence}
				<section>
					<h4>계정 값</h4>
					<div class="values">
						{#each evidence.values as item}
							<div>
								<span>{item.period}</span>
								<b>{formatTableValue(item.value, item.unit)}</b>
							</div>
						{/each}
					</div>
				</section>
			{:else}
				<section>
					<h4>소스 준비 상태</h4>
					<div class="source-list">
						{#each sourceStatus as source}
							<div class={source.status}>
								<span>{source.label}</span>
								<b>{statusText(source.status)}</b>
								<small>{cleanSource(source.source)}</small>
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<section>
				<h4>정기보고서</h4>
				<div class="cards">
					{#each (evidence?.facts.length ? evidence.facts : facts.slice(0, 6)) as fact}
						<article>
							<span>{fact.label}</span>
							<strong>{fact.value}</strong>
							<p>{fact.detail || '세부 값 없음'}</p>
						</article>
					{:else}
						<p>연결된 정기보고서 팩트가 없습니다.</p>
					{/each}
				</div>
			</section>

			<section>
				<h4>사업보고서 원문</h4>
				<div class="docs">
					{#each (evidence?.docs.length ? evidence.docs : docs.slice(0, 6)) as doc}
						<article>
							<strong>{doc.title}</strong>
							<span>{doc.year ?? '연도 없음'} · {doc.reportType ?? '보고서'}</span>
							<p>{doc.excerpt}</p>
						</article>
					{:else}
						<p>연결된 원문 발췌가 없습니다.</p>
					{/each}
				</div>
			</section>

			<section>
				<h4>공시 변화</h4>
				<div class="docs">
					{#each changes.slice(0, 5) as change}
						<article>
							<strong>{change.sectionTitle}</strong>
							<span>{change.fromPeriod} → {change.toPeriod}</span>
							<p>{change.preview ?? change.changeType}</p>
						</article>
					{:else}
						<p>공시 변화 데이터가 대기 중입니다.</p>
					{/each}
				</div>
			</section>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>

<style>
	:global(.backdrop) {
		position: fixed;
		inset: 0;
		z-index: 80;
		background: rgba(3, 5, 9, 0.58);
		backdrop-filter: blur(2px);
	}
	:global(.drawer) {
		position: fixed;
		top: 0;
		right: 0;
		z-index: 81;
		display: grid;
		align-content: start;
		gap: 12px;
		width: min(480px, 100vw);
		height: 100vh;
		overflow-y: auto;
		border-left: 1px solid #1e2433;
		background: #050811;
		color: #f8fafc;
		padding: 18px;
		box-shadow: -24px 0 60px rgba(0, 0, 0, 0.35);
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		align-items: flex-start;
	}
	.close {
		display: grid;
		place-items: center;
		width: 34px;
		height: 34px;
		border: 1px solid #263145;
		border-radius: 6px;
		background: #070c15;
		color: #f8fafc;
		cursor: pointer;
	}
	.eyebrow {
		color: #fb923c;
		font-size: 11px;
		font-weight: 900;
		letter-spacing: 0;
	}
	h4,
	p {
		margin: 0;
	}
	.title {
		display: block;
		margin-top: 5px;
		color: #f8fafc;
		font-size: 20px;
		font-weight: 820;
	}
	.desc {
		margin-top: 6px;
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.45;
	}
	h4 {
		font-size: 14px;
	}
	section {
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.94);
		padding: 14px;
	}
	.values,
	.source-list,
	.cards,
	.docs {
		display: grid;
		gap: 8px;
		margin-top: 12px;
	}
	.values div,
	.source-list div,
	article {
		border: 1px solid #172033;
		border-radius: 7px;
		background: #070c15;
		padding: 10px;
	}
	.values div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
	}
	.source-list span,
	.source-list b,
	.source-list small,
	article span,
	article strong {
		display: block;
	}
	.source-list span,
	.source-list small,
	article span,
	p {
		color: #94a3b8;
		font-size: 12px;
		line-height: 1.45;
	}
	.source-list b,
	article strong {
		margin-top: 4px;
	}
	.source-list div.ready b {
		color: #34d399;
	}
	.source-list div.missing b {
		color: #f87171;
	}
	article p {
		margin-top: 6px;
	}
</style>
