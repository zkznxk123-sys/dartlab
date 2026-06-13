<script lang="ts">
	interface Props {
		open: boolean;
		nodes: any[];
		onSelect: (stockCode: string) => void;
		onClose: () => void;
	}

	let { open, nodes, onSelect, onClose }: Props = $props();
	let query = $state('');
	let inputEl: HTMLInputElement | null = $state(null);
	let selectedIdx = $state(0);

	const RECENT_KEY = 'dartlab.map.recent';
	const MAX_RECENT = 5;

	function loadRecent(): string[] {
		if (typeof localStorage === 'undefined') return [];
		try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); }
		catch { return []; }
	}
	function saveRecent(code: string) {
		if (typeof localStorage === 'undefined') return;
		const arr = loadRecent().filter((c) => c !== code);
		arr.unshift(code);
		localStorage.setItem(RECENT_KEY, JSON.stringify(arr.slice(0, MAX_RECENT)));
	}

	let results = $derived.by(() => {
		if (!query.trim()) {
			const recent = loadRecent();
			return nodes
				.filter((n: any) => recent.includes(n.id))
				.sort((a: any, b: any) => recent.indexOf(a.id) - recent.indexOf(b.id))
				.slice(0, MAX_RECENT);
		}
		const q = query.toLowerCase();
		return nodes
			.filter((n: any) =>
				n.label?.toLowerCase().includes(q) ||
				n.id?.includes(query) ||
				n.industryName?.toLowerCase().includes(q)
			)
			.sort((a: any, b: any) => (b.revenue || 0) - (a.revenue || 0))
			.slice(0, 12);
	});

	$effect(() => {
		if (open) {
			query = '';
			selectedIdx = 0;
			setTimeout(() => inputEl?.focus(), 50);
		}
	});

	function handleKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') { onClose(); return; }
		if (e.key === 'ArrowDown') { e.preventDefault(); selectedIdx = Math.min(selectedIdx + 1, results.length - 1); }
		if (e.key === 'ArrowUp') { e.preventDefault(); selectedIdx = Math.max(selectedIdx - 1, 0); }
		if (e.key === 'Enter' && results[selectedIdx]) {
			const code = results[selectedIdx].id;
			saveRecent(code);
			onSelect(code);
			onClose();
		}
	}

	function pick(code: string) {
		saveRecent(code);
		onSelect(code);
		onClose();
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<div class="backdrop" onclick={onClose} onkeydown={() => {}} role="dialog" tabindex="-1" aria-label="회사 검색">
		<div class="palette" onclick={(e) => e.stopPropagation()} onkeydown={() => {}} role="search" tabindex="-1">
			<div class="search-row">
				<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
					<circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
				</svg>
				<input
					bind:this={inputEl}
					type="text"
					bind:value={query}
					placeholder="회사명, 종목코드, 산업명…"
					autocomplete="off"
					spellcheck="false"
				/>
				<kbd>ESC</kbd>
			</div>
			{#if results.length > 0}
				<ul class="results">
					{#each results as r, i (r.id)}
						<li
							class:active={i === selectedIdx}
							onmouseenter={() => (selectedIdx = i)}
							onclick={() => pick(r.id)}
							role="option"
							aria-selected={i === selectedIdx}
						>
							<span class="r-dot" style:background={r.color}></span>
							<span class="r-name">{r.label}</span>
							<span class="r-code">{r.id}</span>
							<span class="r-ind">{r.industryName}</span>
						</li>
					{/each}
				</ul>
			{:else if query.trim()}
				<div class="empty">결과 없음</div>
			{:else}
				<div class="empty">최근 검색 없음 · 회사명이나 종목코드를 입력하세요</div>
			{/if}
			<div class="footer">
				<span>↑↓ 이동 · Enter 선택 · Esc 닫기</span>
				<span class="shortcut">Ctrl+K</span>
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(5, 8, 17, 0.6);
		backdrop-filter: blur(4px);
		z-index: 120;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 15vh;
	}
	.palette {
		width: 560px;
		max-width: 90vw;
		background: #0f1219;
		border: 1px solid #334155;
		border-radius: 12px;
		overflow: hidden;
		box-shadow: 0 24px 48px rgba(0, 0, 0, 0.5);
	}
	.search-row {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 14px 18px;
		border-bottom: 1px solid #1e2433;
		color: #94a3b8;
	}
	.search-row input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		color: #f1f5f9;
		font-size: 16px;
		font-family: inherit;
	}
	.search-row input::placeholder {
		color: #64748b;
	}
	.search-row kbd {
		padding: 2px 6px;
		background: #1e2433;
		border-radius: 4px;
		color: #64748b;
		font-size: 11px;
		font-family: monospace;
	}
	.results {
		list-style: none;
		padding: 0;
		margin: 0;
		max-height: 360px;
		overflow-y: auto;
	}
	.results li {
		display: grid;
		grid-template-columns: 10px 1fr 70px auto;
		gap: 10px;
		align-items: center;
		padding: 10px 18px;
		cursor: pointer;
		color: #cbd5e1;
		font-size: 14px;
	}
	.results li:hover,
	.results li.active {
		background: rgba(96, 165, 250, 0.08);
		color: #f1f5f9;
	}
	.r-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}
	.r-name {
		font-weight: 600;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.r-code {
		font-family: monospace;
		font-size: 12px;
		color: #64748b;
	}
	.r-ind {
		font-size: 11px;
		color: #94a3b8;
		text-align: right;
	}
	.empty {
		padding: 24px 18px;
		color: #64748b;
		font-size: 13px;
		text-align: center;
	}
	.footer {
		display: flex;
		justify-content: space-between;
		padding: 8px 18px;
		border-top: 1px solid #1e2433;
		font-size: 11px;
		color: #475569;
	}
	.shortcut {
		font-family: monospace;
		color: #64748b;
	}
</style>
