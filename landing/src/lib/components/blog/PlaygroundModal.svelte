<script lang="ts">
	import {
		pyodideStore,
		initPyodide,
		runCode,
		ensureCompany,
		type RunResult
	} from '$lib/stores/pyodide.svelte';

	interface Props {
		open: boolean;
		code: string;
		label?: string;
		stockCode?: string;
		onClose: () => void;
	}

	let { open, code, label = 'Playground', stockCode = '005930', onClose }: Props = $props();

	let output = $state('');
	let running = $state(false);
	let autoRan = $state(false);

	$effect(() => {
		if (!open) {
			autoRan = false;
			return;
		}
		void onOpenAsync();
	});

	async function onOpenAsync() {
		if (pyodideStore.status === 'idle') {
			try {
				await initPyodide(stockCode);
			} catch {
				return;
			}
		} else if (pyodideStore.status === 'ready' && pyodideStore.currentStock !== stockCode) {
			try {
				await ensureCompany(stockCode);
			} catch {
				return;
			}
		}
		if (pyodideStore.status === 'ready' && !autoRan) {
			autoRan = true;
			await execute();
		}
	}

	async function retry() {
		pyodideStore.status = 'idle';
		try {
			await initPyodide(stockCode);
		} catch {
			/* state already has error */
		}
	}

	async function execute() {
		if (pyodideStore.status !== 'ready' || running) return;
		running = true;
		output = '';
		const result: RunResult = await runCode(code);
		output = result.output || (result.ok ? '(결과 없음)' : '(오류)');
		running = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && open) onClose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
		onclick={onClose}
		role="dialog"
		aria-modal="true"
		aria-label={label}
		tabindex="-1"
	>
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="w-full max-w-3xl rounded-lg border border-dl-border bg-dl-bg-card shadow-xl overflow-hidden flex flex-col max-h-[90vh]"
			onclick={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-5 py-3 border-b border-dl-border flex-shrink-0">
				<div class="flex items-center gap-2 text-sm">
					<span class="text-dl-text-muted">Playground</span>
					<span class="text-dl-text font-mono">{label}</span>
					<span class="text-dl-text-dim">· {stockCode}</span>
				</div>
				<button
					onclick={onClose}
					class="text-dl-text-muted hover:text-dl-text px-2 cursor-pointer"
					aria-label="닫기">✕</button
				>
			</div>

			<!-- Body -->
			<div class="p-5 space-y-4 overflow-y-auto">
				<!-- Code -->
				<pre
					class="rounded bg-dl-bg-dark border border-dl-border p-3 text-xs font-mono text-dl-text whitespace-pre-wrap leading-relaxed overflow-x-auto">{code}</pre>

				<!-- State -->
				{#if pyodideStore.status === 'idle' || pyodideStore.status === 'loading'}
					<div class="flex flex-col gap-2">
						<div class="flex items-center gap-2 text-sm text-dl-primary">
							<span class="animate-spin">⟳</span>
							<span>{pyodideStore.step || '초기화 중'}...</span>
							<span class="text-dl-text-dim ml-auto"
								>{Math.round(pyodideStore.progress * 100)}%</span
							>
						</div>
						<div class="h-1 bg-dl-bg-dark rounded overflow-hidden">
							<div
								class="h-full bg-dl-primary transition-all"
								style:width="{pyodideStore.progress * 100}%"
							></div>
						</div>
						{#if pyodideStore.logs.length > 0}
							<pre
								class="mt-2 rounded bg-dl-bg-dark border border-dl-border p-3 text-xs font-mono text-dl-text-muted max-h-40 overflow-y-auto whitespace-pre-wrap">{pyodideStore.logs
									.slice(-20)
									.join('\n')}</pre>
						{/if}
						<p class="text-xs text-dl-text-dim">
							최초 1회 약 8~12초 소요. 같은 글의 다른 Playground 는 즉시 실행됩니다.
						</p>
					</div>
				{:else if pyodideStore.status === 'error'}
					<div class="rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-400">
						<div class="font-medium mb-1">초기화 실패</div>
						<div class="text-xs whitespace-pre-wrap">{pyodideStore.errorMsg}</div>
						<button
							onclick={retry}
							class="mt-2 px-3 py-1 rounded text-xs border border-red-500/40 hover:bg-red-500/20 cursor-pointer"
							>다시 시도</button
						>
					</div>
				{:else if pyodideStore.status === 'ready'}
					<div class="flex items-center gap-2">
						<button
							onclick={execute}
							disabled={running}
							class="px-4 py-1.5 rounded text-sm font-medium transition-colors
								{running
								? 'bg-dl-bg-dark text-dl-text-muted cursor-wait'
								: 'bg-dl-primary text-white hover:bg-dl-primary-dark cursor-pointer'}"
						>
							{#if running}실행 중...{:else}▶ 실행{/if}
						</button>
						<span class="text-xs text-dl-text-dim">Company({pyodideStore.currentStock}) 준비됨</span>
					</div>
					{#if output}
						<pre
							class="rounded bg-dl-bg-dark border border-dl-border p-3 text-xs font-mono text-dl-text-muted max-h-[50vh] overflow-y-auto whitespace-pre-wrap leading-relaxed">{output}</pre>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}
