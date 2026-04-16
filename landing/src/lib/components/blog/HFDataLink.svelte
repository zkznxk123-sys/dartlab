<script lang="ts">
	import { brand } from '$lib/brand';

	type DataKind = keyof typeof brand.data;

	interface Props {
		code: string;
		kind?: DataKind;
		label?: string;
	}

	let { code, kind = 'finance', label }: Props = $props();

	const entry = $derived(brand.data[kind]);
	const url = $derived(
		`https://huggingface.co/datasets/${brand.hfRepo}/resolve/main/${entry.dir}/${code}.parquet`
	);
	const text = $derived(label ?? `원본 parquet · ${entry.label}`);
</script>

<a class="dl-hf-link" href={url} target="_blank" rel="noopener noreferrer">
	<span class="dl-hf-emoji" aria-hidden="true">🤗</span>
	<span class="dl-hf-text">{text}</span>
	<span class="dl-hf-code">{code}.parquet</span>
</a>

<style>
	.dl-hf-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.45rem 0.85rem;
		border: 1px solid var(--border, #1e2433);
		border-radius: 0.5rem;
		background: var(--bg-card, #0f1219);
		color: var(--text, #f1f5f9);
		font-size: 0.875rem;
		text-decoration: none;
		transition: border-color 0.15s, background 0.15s;
	}
	.dl-hf-link:hover {
		border-color: var(--primary, #ea4647);
		background: var(--bg-card-hover, #1a1f2b);
	}
	.dl-hf-emoji {
		font-size: 1rem;
	}
	.dl-hf-code {
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
		font-size: 0.78rem;
		color: var(--text-muted, #94a3b8);
	}
</style>
