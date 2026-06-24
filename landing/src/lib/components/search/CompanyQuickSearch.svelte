<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { ArrowRight, Search } from 'lucide-svelte';
	import { loadCompanies, type Co } from '@dartlab/ui-surfaces/viewer';

	let {
		onpick,
		placeholder = '회사명·종목코드 검색',
		autofocus = false
	}: {
		onpick?: (code: string) => void;
		placeholder?: string;
		autofocus?: boolean;
	} = $props();

	let query = $state('');
	let open = $state(false);
	let selected = $state(0);
	let items = $state<Co[]>([]);
	let loaded = $state(false);
	let inputEl = $state<HTMLInputElement | null>(null);

	function normalize(text: string): string {
		return text.toLowerCase().replace(/\.(ks|kq)$/i, '').replace(/\s+/g, '');
	}

	async function ensure() {
		if (loaded) return;
		loaded = true;
		items = await loadCompanies();
	}

	const matches = $derived.by(() => {
		const q = normalize(query.trim());
		if (!q) return items.slice(0, 8);
		return items
			.filter((item) => normalize(item.name).includes(q) || normalize(item.code).includes(q))
			.slice(0, 8);
	});

	$effect(() => {
		void query;
		selected = 0;
	});

	$effect(() => {
		if (!autofocus) return;
		requestAnimationFrame(() => inputEl?.focus());
	});

	function pick(code: string) {
		query = '';
		open = false;
		if (onpick) {
			onpick(code);
			return;
		}
		void goto(`${base}/viewer/company/${code}`);
	}

	function onKeydown(event: KeyboardEvent) {
		if (!open) return;
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			selected = Math.min(matches.length - 1, selected + 1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			selected = Math.max(0, selected - 1);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			const item = matches[selected];
			if (item) pick(item.code);
		} else if (event.key === 'Escape') {
			event.preventDefault();
			open = false;
		}
	}
</script>

<div class="company-search">
	<span class="icon"><Search size={14} /></span>
	<input
		bind:this={inputEl}
		bind:value={query}
		type="search"
		role="combobox"
		aria-label="회사명 또는 종목코드 검색"
		aria-expanded={open}
		aria-controls="company-quick-search-results"
		aria-activedescendant={open && matches[selected] ? `company-result-${matches[selected].code}` : undefined}
		class="input"
		{placeholder}
		onfocus={() => {
			open = true;
			void ensure();
		}}
		oninput={() => {
			open = true;
			void ensure();
		}}
		onkeydown={onKeydown}
		onblur={() => window.setTimeout(() => (open = false), 140)}
	/>

	{#if open}
		<div id="company-quick-search-results" class="results" role="listbox" aria-label="회사 검색 결과">
			{#if !loaded}
				<div class="hint">회사 목록 준비 중</div>
			{:else if matches.length === 0}
				<div class="hint">결과 없음</div>
			{:else}
				{#each matches as item, i (item.code)}
					<button
						id={`company-result-${item.code}`}
						type="button"
						role="option"
						aria-selected={i === selected}
						class="row"
						class:selected={i === selected}
						onmousedown={() => pick(item.code)}
						onmouseenter={() => (selected = i)}
					>
						<span class="name">{item.name || item.code}</span>
						<span class="code">{item.code}</span>
						<span class="go"><ArrowRight size={13} /></span>
					</button>
				{/each}
			{/if}
		</div>
	{/if}
</div>

<style>
	.company-search {
		position: relative;
		display: flex;
		align-items: center;
		min-width: 220px;
		height: 32px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #050811;
		color: #f1f5f9;
	}
	.icon {
		margin-left: 9px;
		color: #64748b;
		flex-shrink: 0;
	}
	.input {
		width: 100%;
		min-width: 0;
		height: 100%;
		padding: 0 10px 0 7px;
		border: none;
		background: transparent;
		color: #f1f5f9;
		font: inherit;
		font-size: 12px;
		outline: none;
	}
	.input::placeholder {
		color: #64748b;
	}
	.company-search:focus-within {
		border-color: var(--dl-accent);
	}
	.results {
		position: absolute;
		top: calc(100% + 5px);
		left: 0;
		right: 0;
		z-index: 80;
		max-height: 320px;
		overflow-y: auto;
		padding: 4px;
		border: 1px solid #263145;
		border-radius: 7px;
		background: #0a0e18;
		box-shadow: 0 14px 36px rgba(0, 0, 0, 0.45);
	}
	.row {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		align-items: center;
		gap: 8px;
		width: 100%;
		height: 34px;
		padding: 0 8px;
		border: none;
		border-radius: 5px;
		background: transparent;
		color: #cbd5e1;
		font: inherit;
		font-size: 12px;
		text-align: left;
		cursor: pointer;
	}
	.row:hover,
	.row.selected {
		background: rgba(var(--dl-accent-rgb), 0.11);
		color: #f8fafc;
	}
	.name {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-weight: 650;
	}
	.code {
		font-family: monospace;
		font-size: 10px;
		color: #64748b;
	}
	.go {
		color: #64748b;
	}
	.row:hover .code,
	.row:hover .go,
	.row.selected .code,
	.row.selected .go {
		color: var(--dl-accent);
	}
	.hint {
		padding: 12px;
		color: #64748b;
		font-size: 12px;
		text-align: center;
	}
</style>
