<script lang="ts">
	import {
		formatTableValue,
		type BalanceStructureView,
		type StructurePart
	} from '$lib/browser/companyDashboardModel';

	let { view }: { view: BalanceStructureView } = $props();

	const W = 900;
	const H = 388;
	const colY = 48;
	const colH = 210;
	const colW = 148;
	const assetX = 126;
	const fundingX = 458;
	const insetX = 126;
	const insetY = 310;
	const insetW = 480;
	const insetH = 18;

	function finite(value: number | null | undefined): value is number {
		return typeof value === 'number' && Number.isFinite(value);
	}
	function pct(value: number | null): string {
		if (!finite(value)) return '—';
		return `${value.toFixed(Math.abs(value) >= 10 ? 0 : 1)}%`;
	}
	function fill(part: StructurePart): string {
		if (part.id === 'cash' || part.id === 'equity' || part.id === 'retainedEarnings') return '#34d399';
		if (part.id === 'inventory' || part.id === 'treasuryStock') return '#fbbf24';
		if (part.id === 'tangible') return '#fb923c';
		if (part.id === 'interestDebt' || part.id === 'otherLiabilities') return '#ef4444';
		if (part.id === 'tradePayables') return '#64748b';
		return '#475569';
	}
	function opacity(part: StructurePart): number {
		if (part.missing) return 0.18;
		if (part.id === 'cash' || part.id === 'equity' || part.id === 'interestDebt') return 0.86;
		return 0.62;
	}
	function stack(parts: StructurePart[]) {
		let cursor = colY + colH;
		return parts
			.filter((part) => finite(part.value) && finite(part.share) && Math.max(0, part.share) > 0.01)
			.map((part) => {
				const h = Math.max(1, Math.min(100, Math.max(0, part.share ?? 0)) / 100 * colH);
				cursor -= h;
				return { part, y: cursor, h };
			});
	}
	function equitySegments(parts: StructurePart[]) {
		let cursor = insetX;
		return parts
			.filter((part) => finite(part.value) && finite(part.share) && (part.share ?? 0) > 0.01)
			.map((part) => {
				const w = Math.max(2, Math.min(100, part.share ?? 0) / 100 * insetW);
				const x = cursor;
				cursor += w;
				return { part, x, w };
			});
	}
	function largeEnough(share: number | null): boolean {
		return finite(share) && share >= 8;
	}
	function visibleParts(parts: StructurePart[]): StructurePart[] {
		return parts.filter((part) => !part.missing || part.id === 'otherAssets' || part.id === 'otherLiabilities' || part.id === 'otherEquity');
	}
</script>

<article class="balance-chart">
	<header>
		<div>
			<h3>{view.title}</h3>
			<p>{view.subtitle}</p>
		</div>
		<div class="source">
			<span>{view.sourceMode}</span>
			<strong>{view.sourceLabel}</strong>
		</div>
	</header>

	<svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={view.title}>
		<rect x="0" y="0" width={W} height={H} rx="8" fill="#070c15" />
		<text x={assetX + colW / 2} y="26" text-anchor="middle" class="title">자산 배치</text>
		<text x={fundingX + colW / 2} y="26" text-anchor="middle" class="title">조달 구조</text>
		<text x="326" y="151" text-anchor="middle" class="equation">=</text>
		<text x="326" y="172" text-anchor="middle" class="equation-small">총자산 기준</text>

		<rect x={assetX} y={colY} width={colW} height={colH} rx="8" fill="#050811" stroke="#1e2433" />
		{#each stack(view.assetParts) as segment}
			<rect x={assetX} y={segment.y} width={colW} height={segment.h} fill={fill(segment.part)} opacity={opacity(segment.part)} />
			{#if largeEnough(segment.part.share)}
				<text x={assetX + colW / 2} y={segment.y + segment.h / 2 + 4} text-anchor="middle" class="inside">
					{segment.part.label} {pct(segment.part.share)}
				</text>
			{/if}
		{/each}
		<rect x={fundingX} y={colY} width={colW} height={colH} rx="8" fill="#050811" stroke="#1e2433" />
		{#each stack(view.fundingParts) as segment}
			<rect x={fundingX} y={segment.y} width={colW} height={segment.h} fill={fill(segment.part)} opacity={opacity(segment.part)} />
			{#if largeEnough(segment.part.share)}
				<text x={fundingX + colW / 2} y={segment.y + segment.h / 2 + 4} text-anchor="middle" class="inside">
					{segment.part.label} {pct(segment.part.share)}
				</text>
			{/if}
		{/each}

		<text x={assetX} y={colY + colH + 22} class="total">총자산 {formatTableValue(view.totalAssets, 'KRW')}</text>
		<text x={fundingX} y={colY + colH + 22} class="total">부채+자본 {formatTableValue(view.totalFunding, 'KRW')}</text>
		<text x={fundingX} y={colY + colH + 40} class:watch={(view.debtRatio ?? 0) > 200} class="caption">
			부채비율 {formatTableValue(view.debtRatio, '%')}
		</text>

		<text x={insetX} y={insetY - 13} class="title">자본 구조</text>
		<rect x={insetX} y={insetY} width={insetW} height={insetH} rx="4" fill="#050811" stroke="#1e2433" />
		{#each equitySegments(view.equityParts) as segment}
			<rect x={segment.x} y={insetY} width={segment.w} height={insetH} rx="3" fill={fill(segment.part)} opacity={opacity(segment.part)} />
		{/each}
		<text x={insetX + insetW + 18} y={insetY + 13} class="caption">총자본 대비</text>

		<foreignObject x="636" y="46" width="238" height="284">
			<div class="part-list" xmlns="http://www.w3.org/1999/xhtml">
				<div class="list-title">비중 · 금액</div>
				{#each visibleParts(view.assetParts) as part}
					<div class="part">
						<span><i style:background={fill(part)}></i>{part.label}</span>
						<strong>{part.missing ? '상세 계정 없음' : `${pct(part.share)} · ${formatTableValue(part.value, part.unit)}`}</strong>
					</div>
				{/each}
				<div class="divider"></div>
				{#each visibleParts(view.fundingParts) as part}
					<div class="part">
						<span><i style:background={fill(part)}></i>{part.label}</span>
						<strong>{part.missing ? '상세 계정 없음' : `${pct(part.share)} · ${formatTableValue(part.value, part.unit)}`}</strong>
					</div>
				{/each}
			</div>
		</foreignObject>
	</svg>

	<div class="equity-list">
		{#each visibleParts(view.equityParts) as part}
			<span class:missing={part.missing}>
				<i style:background={fill(part)}></i>{part.label}
				<strong>{part.missing ? '—' : `${pct(part.share)} · ${formatTableValue(part.value, part.unit)}`}</strong>
			</span>
		{/each}
	</div>

	{#if view.coverageNotes.length}
		<div class="notes">
			{#each view.coverageNotes as note}
				<span class={note.tone}>{note.label}</span>
			{/each}
		</div>
	{/if}
</article>

<style>
	.balance-chart {
		min-width: 0;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #050811;
		padding: 12px;
	}
	header {
		display: flex;
		justify-content: space-between;
		gap: 16px;
		align-items: flex-start;
		margin-bottom: 8px;
	}
	h3,
	p {
		margin: 0;
	}
	h3 {
		color: #f8fafc;
		font-size: 15px;
		font-weight: 820;
		line-height: 1.25;
	}
	p {
		margin-top: 4px;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.45;
	}
	.source {
		display: grid;
		gap: 2px;
		min-width: 120px;
		text-align: right;
	}
	.source span,
	.source strong {
		color: #94a3b8;
		font-size: 10px;
		font-weight: 700;
	}
	.source strong {
		color: #cbd5e1;
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
		min-height: 332px;
	}
	text {
		fill: #94a3b8;
		font-size: 10px;
	}
	.title,
	.total {
		fill: #cbd5e1;
		font-size: 12px;
		font-weight: 820;
	}
	.caption {
		fill: #94a3b8;
		font-size: 10px;
	}
	.caption.watch {
		fill: #fbbf24;
	}
	.inside {
		fill: #f8fafc;
		font-size: 10px;
		font-weight: 800;
		pointer-events: none;
	}
	.equation {
		fill: #f8fafc;
		font-size: 34px;
		font-weight: 900;
	}
	.equation-small {
		fill: #64748b;
		font-size: 10px;
		font-weight: 700;
	}
	.part-list {
		display: grid;
		gap: 5px;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #050811;
		padding: 8px;
		color: #cbd5e1;
		font-family: inherit;
	}
	.list-title {
		color: #64748b;
		font-size: 10px;
		font-weight: 800;
	}
	.part {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 2px;
		min-width: 0;
	}
	.part span,
	.equity-list span {
		display: inline-flex;
		min-width: 0;
		gap: 5px;
		align-items: center;
		color: #94a3b8;
		font-size: 10px;
	}
	.part strong,
	.equity-list strong {
		overflow: hidden;
		color: #f8fafc;
		font-size: 11px;
		font-weight: 760;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	i {
		width: 9px;
		height: 9px;
		border-radius: 2px;
		flex: 0 0 auto;
	}
	.divider {
		height: 1px;
		background: #1e2433;
	}
	.equity-list,
	.notes {
		display: flex;
		flex-wrap: wrap;
		gap: 8px 12px;
		margin-top: 8px;
	}
	.equity-list span {
		border: 1px solid #1e2433;
		border-radius: 5px;
		background: #070c15;
		padding: 6px 8px;
	}
	.equity-list span.missing strong {
		color: #64748b;
	}
	.notes span {
		color: #94a3b8;
		font-size: 11px;
	}
	.notes .watch {
		color: #fbbf24;
	}
	@media (max-width: 720px) {
		header {
			display: grid;
		}
		.source {
			text-align: left;
		}
		svg {
			min-height: 300px;
		}
		.equity-list span {
			width: 100%;
			justify-content: space-between;
		}
	}
</style>
