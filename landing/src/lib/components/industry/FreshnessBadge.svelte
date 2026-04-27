<script lang="ts">
	interface Props {
		// meta.json.dataAsOf { dart, finance, reviews, taxonomy }
		dataAsOf: Record<string, string | null | undefined> | null | undefined;
		// "compact" (4 소스 abbr) | "dot" (한 점만) | "full" (상세 툴팁)
		variant?: 'compact' | 'dot' | 'full';
		title?: string;
	}

	let { dataAsOf, variant = 'compact', title = '' }: Props = $props();

	function ageHours(iso: string | null | undefined): number | null {
		if (!iso) return null;
		const t = new Date(iso).getTime();
		if (Number.isNaN(t)) return null;
		return (Date.now() - t) / 3_600_000;
	}

	function ageLabel(hours: number | null): string {
		if (hours === null) return '-';
		if (hours < 1) return '방금';
		if (hours < 24) return `${Math.floor(hours)}h`;
		const days = Math.floor(hours / 24);
		if (days < 7) return `${days}d`;
		const weeks = Math.floor(days / 7);
		if (weeks < 5) return `${weeks}w`;
		const months = Math.floor(days / 30);
		return `${months}mo`;
	}

	function ageColor(hours: number | null): string {
		if (hours === null) return '#64748b';
		if (hours < 24) return '#10b981'; // 녹: 24h
		if (hours < 24 * 7) return '#fbbf24'; // 황: 1주
		return '#94a3b8'; // 회: 오래
	}

	// 소스별 레이블
	const LABELS: Record<string, string> = {
		dart: 'DART',
		finance: '재무',
		reviews: '분석글',
		taxonomy: '분류',
		scan: 'Scan'
	};

	let sources = $derived.by(() => {
		if (!dataAsOf) return [];
		return Object.entries(dataAsOf)
			.filter(([, v]) => !!v)
			.map(([k, v]) => {
				const h = ageHours(v);
				return {
					key: k,
					label: LABELS[k] || k,
					iso: v as string,
					hours: h,
					ageStr: ageLabel(h),
					color: ageColor(h)
				};
			});
	});

	// "대표" 나이 = 가장 오래된 소스 (보수적)
	let representative = $derived(
		sources.length ? sources.reduce((a, b) => ((a.hours ?? 0) > (b.hours ?? 0) ? a : b)) : null
	);

	let tooltip = $derived(
		sources.map((s) => `${s.label}: ${s.iso?.slice(0, 10)} (${s.ageStr})`).join('\n') ||
			'데이터 정보 없음'
	);
</script>

{#if variant === 'dot'}
	<span class="dot" style:background={representative?.color || '#64748b'} title={title || tooltip} aria-label="데이터 신선도">●</span>
{:else if variant === 'compact'}
	<div class="compact" title={title || tooltip}>
		{#if representative}
			<span class="chip">
				<span class="chip-k">데이터 업데이트</span>
				<span class="chip-v" style:color={representative.color}>{representative.ageStr}</span>
			</span>
		{/if}
	</div>
{:else}
	<div class="full">
		<div class="full-head">데이터 신선도</div>
		{#each sources as s (s.key)}
			<div class="row">
				<span class="k">{s.label}</span>
				<span class="iso">{s.iso?.slice(0, 16).replace('T', ' ')}</span>
				<span class="age" style:color={s.color}>{s.ageStr}</span>
			</div>
		{/each}
	</div>
{/if}

<style>
	.dot {
		display: inline-block;
		line-height: 1;
		font-size: 9px;
		cursor: help;
	}
	.compact {
		display: inline-flex;
		gap: 6px;
		align-items: center;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 3px;
		font-size: 10px;
		background: rgba(5, 8, 17, 0.6);
		border: 1px solid #1e2433;
		border-radius: 4px;
		padding: 2px 6px;
		font-family: monospace;
	}
	.chip-k {
		color: #64748b;
	}
	.chip-v {
		font-weight: 600;
	}
	.full {
		font-size: 12px;
		padding: 8px 12px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 6px;
	}
	.full-head {
		color: #94a3b8;
		font-size: 10px;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		margin-bottom: 6px;
	}
	.row {
		display: grid;
		grid-template-columns: 60px 1fr 48px;
		gap: 8px;
		align-items: center;
		padding: 3px 0;
		font-family: monospace;
	}
	.k {
		color: #94a3b8;
	}
	.iso {
		color: #cbd5e1;
		font-size: 11px;
	}
	.age {
		text-align: right;
		font-weight: 600;
	}
</style>
