<script lang="ts">
	import PlaygroundModal from './PlaygroundModal.svelte';

	interface Props {
		code: string;
		label?: string;
		stockCode?: string;
	}

	let { code, label = '실행', stockCode = '005930' }: Props = $props();

	let open = $state(false);
</script>

<div
	class="my-6 rounded-lg border border-dl-border bg-dl-bg-card overflow-hidden not-prose"
>
	<div class="flex items-center justify-between px-4 py-2 border-b border-dl-border text-xs">
		<div class="flex items-center gap-2">
			<span class="text-dl-text-dim">근거 코드</span>
			<span class="text-dl-text font-mono">{label}</span>
			<span class="text-dl-text-dim">· {stockCode}</span>
		</div>
		<button
			onclick={() => (open = true)}
			class="px-3 py-1 rounded border border-dl-primary/40 text-dl-primary hover:bg-dl-primary/10 transition-colors cursor-pointer text-xs font-medium"
		>
			▶ 브라우저에서 실행
		</button>
	</div>
	<pre
		class="m-0 p-4 text-xs font-mono text-dl-text bg-dl-bg-dark whitespace-pre-wrap leading-relaxed overflow-x-auto">{code}</pre>
</div>

<PlaygroundModal {open} {code} {label} {stockCode} onClose={() => (open = false)} />
