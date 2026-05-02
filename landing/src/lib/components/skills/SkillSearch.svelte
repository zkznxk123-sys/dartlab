<script lang="ts">
	import { base } from '$app/paths';
	import { BookOpen, CheckCircle2, Search, SlidersHorizontal } from 'lucide-svelte';
	import { onMount } from 'svelte';

	interface RuntimeEntry {
		status?: string;
		notes?: string[];
		limitations?: string[];
		dataSources?: string[];
	}

	interface SkillDoc {
		id: string;
		title: string;
		category: string;
		categoryTitle?: string;
		status: string;
		purpose: string;
		whenToUse?: string[];
		capabilityRefs?: string[];
		datasetRefs?: string[];
		runtimeCompatibility?: Record<string, RuntimeEntry>;
		sourcePath?: string;
	}

	let skills = $state<SkillDoc[]>([]);
	let query = $state('');
	let activeCategory = $state('all');
	let activeRuntime = $state('all');
	let loadError = $state('');

	const categoryOrder = ['start', 'runtime', 'engines', 'screens', 'finance', 'visuals', 'basic', 'capability'];
	const runtimeOptions = [
		{ id: 'all', label: 'All runtimes' },
		{ id: 'pyodide', label: 'Pyodide' },
		{ id: 'webAi', label: 'Web AI' },
		{ id: 'mcp', label: 'MCP' },
		{ id: 'localPython', label: 'Local Python' }
	];

	const categories = $derived.by(() => {
		const grouped = new Map<string, { id: string; title: string; count: number }>();
		for (const skill of skills) {
			const item = grouped.get(skill.category) ?? {
				id: skill.category,
				title: skill.categoryTitle ?? skill.category,
				count: 0
			};
			item.count += 1;
			grouped.set(skill.category, item);
		}
		return [...grouped.values()].sort((a, b) => {
			const ai = categoryOrder.indexOf(a.id);
			const bi = categoryOrder.indexOf(b.id);
			if (ai === -1 && bi === -1) return a.id.localeCompare(b.id);
			if (ai === -1) return 1;
			if (bi === -1) return -1;
			return ai - bi;
		});
	});

	const filtered = $derived.by(() => {
		const tokens = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
		return skills
			.filter((skill) => activeCategory === 'all' || skill.category === activeCategory)
			.filter((skill) => {
				if (activeRuntime === 'all') return true;
				const status = skill.runtimeCompatibility?.[activeRuntime]?.status ?? 'unknown';
				return status === 'supported' || status === 'limited';
			})
			.map((skill) => ({ skill, score: scoreSkill(skill, tokens) }))
			.filter((item) => tokens.length === 0 || item.score > 0)
			.sort((a, b) => b.score - a.score || a.skill.category.localeCompare(b.skill.category) || a.skill.id.localeCompare(b.skill.id))
			.slice(0, 18);
	});

	onMount(async () => {
		try {
			const response = await fetch(`${base}/skills/index.json`);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const payload = await response.json();
			skills = Array.isArray(payload.skills) ? payload.skills : [];
		} catch (error) {
			loadError = error instanceof Error ? error.message : 'unknown error';
		}
	});

	function scoreSkill(skill: SkillDoc, tokens: string[]) {
		if (tokens.length === 0) return categoryOrder.length - Math.max(categoryOrder.indexOf(skill.category), 0);
		const haystack = [
			skill.id,
			skill.title,
			skill.category,
			skill.categoryTitle ?? '',
			skill.status,
			skill.purpose,
			...(skill.whenToUse ?? []),
			...(skill.capabilityRefs ?? []),
			...(skill.datasetRefs ?? [])
		].join(' ').toLowerCase();
		let score = 0;
		for (const token of tokens) {
			if (skill.id.toLowerCase().includes(token)) score += 10;
			if (skill.title.toLowerCase().includes(token)) score += 8;
			if ((skill.capabilityRefs ?? []).some((ref) => ref.toLowerCase().includes(token))) score += 5;
			if (haystack.includes(token)) score += 2;
		}
		return score;
	}

	function skillHref(skill: SkillDoc) {
		if (skill.sourcePath?.startsWith('src/')) {
			return `https://github.com/eddmpython/dartlab/blob/master/${skill.sourcePath}`;
		}
		if (skill.id.startsWith('capability:')) {
			return 'https://github.com/eddmpython/dartlab/blob/master/CAPABILITIES.md';
		}
		return 'https://github.com/eddmpython/dartlab/tree/master/src/dartlab/skills';
	}

	function isExternalHref(href: string) {
		return href.startsWith('http');
	}
</script>

<section class="skill-search" aria-label="Skill 검색">
	<div class="search-head">
		<div>
			<span class="kicker">Skill resolver</span>
			<h2>분석 목적을 먼저 검색한다</h2>
			<p>
				모든 절차 문서는 SkillSpec에서 생성된다. 자체 AI, 외부 AI, MCP, Web UI는 이 catalog에서
				절차를 찾고 capability ref와 runtime compatibility를 확인한다.
			</p>
		</div>
		<div class="search-count">
			<BookOpen size={18} />
			<strong>{skills.length}</strong>
			<span>skills</span>
		</div>
	</div>

	<div class="search-controls">
		<label class="search-input">
			<Search size={16} />
			<input bind:value={query} placeholder="예: 미국 주식 분석, 차트, MCP, 수익성, Pyodide" />
		</label>
		<label class="runtime-filter">
			<SlidersHorizontal size={15} />
			<select bind:value={activeRuntime} aria-label="runtime filter">
				{#each runtimeOptions as option}
					<option value={option.id}>{option.label}</option>
				{/each}
			</select>
		</label>
	</div>

	<div class="category-strip" aria-label="Skill category filter">
		<button class:active={activeCategory === 'all'} onclick={() => (activeCategory = 'all')}>
			All <span>{skills.length}</span>
		</button>
		{#each categories as category}
			<button class:active={activeCategory === category.id} onclick={() => (activeCategory = category.id)}>
				{category.title} <span>{category.count}</span>
			</button>
		{/each}
	</div>

	{#if loadError}
		<p class="empty">Skill index를 불러오지 못했다: {loadError}</p>
	{:else if filtered.length === 0}
		<p class="empty">검색 결과가 없다. 더 넓은 목적어나 capability 이름으로 다시 검색한다.</p>
	{:else}
		<div class="result-grid">
			{#each filtered as item}
				{@const href = skillHref(item.skill)}
				<a
					class="result-card"
					href={href}
					target={isExternalHref(href) ? '_blank' : undefined}
					rel={isExternalHref(href) ? 'noopener' : undefined}
				>
					<div class="result-topline">
						<span>{item.skill.categoryTitle ?? item.skill.category}</span>
						<span class="status">{item.skill.status}</span>
					</div>
					<h3>{item.skill.title}</h3>
					<p>{item.skill.purpose}</p>
					<div class="result-meta">
						<span>{item.skill.id}</span>
						{#if item.skill.runtimeCompatibility?.pyodide?.status === 'supported' || item.skill.runtimeCompatibility?.pyodide?.status === 'limited'}
							<span class="runtime"><CheckCircle2 size={12} /> Pyodide</span>
						{/if}
					</div>
				</a>
			{/each}
		</div>
	{/if}
</section>

<style>
	.skill-search {
		margin: 0 0 1.5rem;
		padding: 1.25rem;
		border: 1px solid rgba(30, 36, 51, 0.86);
		border-radius: 8px;
		background: rgba(10, 14, 23, 0.8);
		box-shadow: 0 18px 48px rgba(0, 0, 0, 0.22);
	}

	.search-head {
		display: flex;
		justify-content: space-between;
		gap: 1.25rem;
		align-items: flex-start;
		margin-bottom: 1rem;
	}

	.kicker {
		display: block;
		margin-bottom: 0.35rem;
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #fb923c;
	}

	.search-head h2 {
		margin: 0 0 0.4rem !important;
		padding: 0 !important;
		border: 0 !important;
		font-size: 1.35rem !important;
	}

	.search-head p {
		margin: 0 !important;
		max-width: 46rem;
		color: #94a3b8;
		font-size: 0.94rem;
		line-height: 1.65;
	}

	.search-count {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.55rem 0.65rem;
		border-radius: 8px;
		border: 1px solid rgba(234, 70, 71, 0.24);
		background: rgba(234, 70, 71, 0.08);
		color: #fca5a5;
		white-space: nowrap;
	}

	.search-count strong {
		color: #f8fafc;
		font-size: 1.05rem;
	}

	.search-count span {
		font-size: 0.72rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #94a3b8;
	}

	.search-controls {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 190px;
		gap: 0.75rem;
		margin-bottom: 0.85rem;
	}

	.search-input,
	.runtime-filter {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		min-width: 0;
		height: 2.5rem;
		padding: 0 0.75rem;
		border: 1px solid rgba(30, 36, 51, 0.9);
		border-radius: 7px;
		background: rgba(3, 5, 9, 0.72);
		color: #64748b;
	}

	.search-input input,
	.runtime-filter select {
		width: 100%;
		min-width: 0;
		border: 0;
		outline: 0;
		background: transparent;
		color: #e2e8f0;
		font: inherit;
		font-size: 0.86rem;
	}

	.search-input input::placeholder {
		color: #64748b;
	}

	.runtime-filter select {
		cursor: pointer;
	}

	.category-strip {
		display: flex;
		flex-wrap: wrap;
		gap: 0.45rem;
		margin-bottom: 1rem;
	}

	.category-strip button {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		height: 1.8rem;
		padding: 0 0.6rem;
		border: 1px solid rgba(30, 36, 51, 0.8);
		border-radius: 6px;
		background: rgba(15, 18, 25, 0.55);
		color: #94a3b8;
		font-size: 0.75rem;
		cursor: pointer;
	}

	.category-strip button:hover,
	.category-strip button.active {
		border-color: rgba(234, 70, 71, 0.45);
		background: rgba(234, 70, 71, 0.1);
		color: #f8fafc;
	}

	.category-strip span {
		color: #64748b;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.68rem;
	}

	.result-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.7rem;
	}

	.result-card {
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		min-height: 154px;
		padding: 0.85rem;
		border: 1px solid rgba(30, 36, 51, 0.72);
		border-radius: 8px;
		background: rgba(15, 18, 25, 0.52);
		text-decoration: none !important;
		transition: border-color 0.14s, transform 0.14s, background 0.14s;
	}

	.result-card:hover {
		border-color: rgba(234, 70, 71, 0.45);
		background: rgba(15, 18, 25, 0.86);
		transform: translateY(-1px);
	}

	.result-topline,
	.result-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
		color: #64748b;
		font-size: 0.69rem;
		font-family: 'JetBrains Mono', monospace;
	}

	.status {
		color: #fb923c;
	}

	.result-card h3 {
		margin: 0 !important;
		color: #f1f5f9 !important;
		font-size: 0.96rem !important;
		line-height: 1.35;
	}

	.result-card p {
		margin: 0 !important;
		color: #94a3b8;
		font-size: 0.78rem;
		line-height: 1.55;
		display: -webkit-box;
		line-clamp: 3;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.result-meta {
		margin-top: auto;
	}

	.runtime {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
		color: #86efac;
	}

	.empty {
		margin: 1rem 0 0 !important;
		padding: 1rem;
		border: 1px solid rgba(30, 36, 51, 0.72);
		border-radius: 8px;
		color: #94a3b8;
		text-align: center;
	}

	@media (max-width: 760px) {
		.search-head,
		.search-controls {
			grid-template-columns: 1fr;
		}

		.search-head {
			display: grid;
		}

		.search-count {
			width: fit-content;
		}

		.result-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
