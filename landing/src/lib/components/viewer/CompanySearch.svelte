<script lang="ts">
	// 회사 검색 — ecosystem(회사 유니버스)에서 회사명/종목코드로 찾아 그 회사 공시뷰어로 이동.
	// scan 검색 스타일(다크 #050811 + 오렌지 포커스). lazy 로드(첫 포커스 시 1회).
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { loadCompanies, type Co } from '$lib/viewer/companyNames';

	let query = $state('');
	let open = $state(false);
	let items = $state<Co[]>([]);
	let loaded = false;

	async function ensure() {
		if (loaded) return;
		loaded = true;
		items = await loadCompanies();
	}

	const matches = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!q) return [];
		return items.filter((c) => c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q)).slice(0, 8);
	});

	function pick(code: string) {
		query = '';
		open = false;
		void goto(`${base}/viewer/company/${code}`);
	}
	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && matches.length) {
			e.preventDefault();
			pick(matches[0].code);
		} else if (e.key === 'Escape') {
			open = false;
		}
	}
</script>

<div class="search-wrap">
	<input
		class="search-input"
		type="text"
		bind:value={query}
		placeholder="회사명 / 종목코드 검색"
		aria-label="회사 검색"
		onfocus={() => {
			open = true;
			void ensure();
		}}
		oninput={() => (open = true)}
		onkeydown={onKey}
		onblur={() => setTimeout(() => (open = false), 150)}
	/>
	{#if open && matches.length}
		<div class="dropdown">
			{#each matches as c (c.code)}
				<button type="button" class="opt" onmousedown={() => pick(c.code)}>
					<span class="opt-name">{c.name}</span>
					<span class="opt-code">{c.code}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.search-wrap {
		position: relative;
	}
	.search-input {
		width: 240px;
		height: 30px;
		padding: 0 10px;
		background: #050811;
		border: 1px solid #1e2433;
		border-radius: 5px;
		color: #f1f5f9;
		font-size: 12px;
		font-family: inherit;
		line-height: 1;
	}
	.search-input::placeholder {
		color: #475569;
	}
	.search-input:focus {
		outline: none;
		border-color: #fb923c;
	}
	.dropdown {
		position: absolute;
		top: calc(100% + 4px);
		right: 0;
		z-index: 50;
		width: 280px;
		max-height: 320px;
		overflow-y: auto;
		background: #0a0e18;
		border: 1px solid #263145;
		border-radius: 6px;
		padding: 4px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
	}
	.opt {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		width: 100%;
		padding: 6px 8px;
		border: none;
		border-radius: 4px;
		background: transparent;
		color: #cbd5e1;
		font: inherit;
		font-size: 12px;
		text-align: left;
		cursor: pointer;
	}
	.opt:hover {
		background: rgba(251, 146, 60, 0.1);
		color: #f8fafc;
	}
	.opt-code {
		flex-shrink: 0;
		font-family: monospace;
		font-size: 10px;
		color: #64748b;
	}
	.opt:hover .opt-code {
		color: #fb923c;
	}
</style>
