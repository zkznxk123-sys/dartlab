<script lang="ts">
	// 회사 검색 — ecosystem(회사 유니버스)에서 회사명/종목코드로 찾아 그 회사 공시뷰어로 이동.
	// scan 검색 스타일(다크 #050811 + 오렌지 포커스). lazy 로드(첫 포커스 시 1회).
	// 키보드: ↑↓ 로 후보 이동, Enter 선택, Esc 닫기. 마우스: hover 하이라이트 + 클릭.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { loadCompanies, type Co } from '$lib/viewer/companyNames';

	// onpick 주면 이동(goto) 대신 콜백 — 비교 모드의 "회사 추가" 재사용.
	let { onpick }: { onpick?: (code: string) => void } = $props();

	let query = $state('');
	let open = $state(false);
	let items = $state<Co[]>([]);
	let active = $state(0); // 키보드 하이라이트 인덱스
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
		active = 0;
		if (onpick) {
			onpick(code);
			return;
		}
		void goto(`${base}/viewer/company/${code}`);
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			open = false;
			return;
		}
		if (!matches.length) return;
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			open = true;
			active = (active + 1) % matches.length;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			open = true;
			active = (active - 1 + matches.length) % matches.length;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			const i = Math.max(0, Math.min(active, matches.length - 1));
			pick(matches[i].code);
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
		autocomplete="off"
		onfocus={() => {
			open = true;
			void ensure();
		}}
		oninput={() => {
			open = true;
			active = 0;
		}}
		onkeydown={onKey}
		onblur={() => setTimeout(() => (open = false), 150)}
	/>
	{#if open && matches.length}
		<div class="dropdown">
			{#each matches as c, i (c.code)}
				<button
					type="button"
					class="opt"
					class:active={i === active}
					onmousedown={(e) => {
						e.preventDefault();
						pick(c.code);
					}}
					onmouseenter={() => (active = i)}
				>
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
	.opt.active,
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
	.opt.active .opt-code,
	.opt:hover .opt-code {
		color: #fb923c;
	}
</style>
