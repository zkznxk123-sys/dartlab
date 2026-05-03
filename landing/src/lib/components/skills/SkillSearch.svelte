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
		inputs?: string[];
		requiredInputs?: string[];
		outputs?: string[];
		apiRefs?: string[];
		toolRefs?: string[];
		datasetRefs?: string[];
		knowledgeRefs?: string[];
		sourceRefs?: string[];
		procedure?: string[];
		requiredEvidence?: string[];
		expectedOutputs?: string[];
		visualGuidance?: string[];
		failureModes?: string[];
		forbidden?: string[];
		examples?: string[];
		runtimeCompatibility?: Record<string, RuntimeEntry>;
	}

	interface SkillIndexMeta {
		entrySkillId?: string;
		canonicalSurface?: string;
		skillCount?: number;
	}

	let skills = $state<SkillDoc[]>([]);
	let meta = $state<SkillIndexMeta>({});
	let query = $state('');
	let activeCategory = $state('all');
	let activeRuntime = $state('all');
	let selectedSkill = $state<SkillDoc | null>(null);
	let loadError = $state('');

	const categoryOrder = ['start', 'runtime', 'operation', 'engines', 'screens', 'finance', 'visuals', 'basic'];
	const runtimeOptions = [
		{ id: 'all', label: 'All runtimes' },
		{ id: 'pyodide', label: 'Pyodide' },
		{ id: 'webAi', label: 'Web AI' },
		{ id: 'mcp', label: 'MCP' },
		{ id: 'localPython', label: 'Local Python' }
	];

	const publicSkills = $derived(skills.filter((skill) => skill.category !== 'capability'));

	const categories = $derived.by(() => {
		const grouped = new Map<string, { id: string; title: string; count: number }>();
		for (const skill of publicSkills) {
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
		return publicSkills
			.filter((skill) => activeCategory === 'all' || skill.category === activeCategory)
			.filter((skill) => {
				if (activeRuntime === 'all') return true;
				const status = skill.runtimeCompatibility?.[activeRuntime]?.status ?? 'unknown';
				return status === 'supported' || status === 'limited';
			})
			.map((skill) => ({ skill, score: scoreSkill(skill, tokens) }))
			.filter((item) => tokens.length === 0 || item.score > 0)
			.sort((a, b) => {
				if (tokens.length === 0) {
					if (a.skill.id === meta.entrySkillId) return -1;
					if (b.skill.id === meta.entrySkillId) return 1;
				}
				return b.score - a.score || a.skill.category.localeCompare(b.skill.category) || a.skill.id.localeCompare(b.skill.id);
			})
			.slice(0, 18);
	});

	$effect(() => {
		const first = filtered[0]?.skill ?? null;
		if (!first) {
			selectedSkill = null;
			return;
		}
		if (!selectedSkill || !filtered.some((item) => item.skill.id === selectedSkill?.id)) {
			selectedSkill = first;
		}
	});

	onMount(async () => {
		try {
			const response = await fetch(`${base}/skills/index.json`);
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const payload = await response.json();
			meta = payload.meta ?? {};
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
			...(skill.inputs ?? []),
			...(skill.requiredInputs ?? []),
			...(skill.outputs ?? []),
			...(skill.procedure ?? []),
			...(skill.examples ?? []),
			...(skill.apiRefs ?? []),
			...(skill.toolRefs ?? []),
			...(skill.datasetRefs ?? []),
			...(skill.knowledgeRefs ?? []),
			...(skill.sourceRefs ?? [])
		].join(' ').toLowerCase();
		let score = 0;
		for (const token of tokens) {
			if (skill.id.toLowerCase().includes(token)) score += 10;
			if (skill.title.toLowerCase().includes(token)) score += 8;
			if (haystack.includes(token)) score += 2;
		}
		return score;
	}

	function selectSkill(skill: SkillDoc) {
		selectedSkill = skill;
	}

	function runtimeRows(skill: SkillDoc) {
		return Object.entries(skill.runtimeCompatibility ?? {})
			.filter(([name]) => ['localPython', 'pyodide', 'webAi', 'mcp', 'server'].includes(name))
			.map(([name, value]) => ({
				name,
				status: value?.status ?? 'unknown',
				notes: [...(value?.notes ?? []), ...(value?.limitations ?? [])].slice(0, 2)
			}));
	}

	function limited(items: string[] | undefined, count = 5) {
		return (items ?? []).filter(Boolean).slice(0, count);
	}

	function combinedInputs(skill: SkillDoc) {
		return [...(skill.requiredInputs ?? []), ...(skill.inputs ?? [])].filter(Boolean);
	}

	function combinedOutputs(skill: SkillDoc) {
		return [...(skill.expectedOutputs ?? []), ...(skill.outputs ?? [])].filter(Boolean);
	}

	function formatExample(example: string) {
		const text = example.trim();
		if (!/[=()#]|(^|\s)(import|from|await|for)\b/.test(text)) return text;
		return text.replace(/\s+(?=(c|dartlab|import|from|await|for)\b)/g, '\n');
	}
</script>

<section class="skill-search" aria-label="Skill 검색">
	<div class="search-head">
		<div>
			<span class="kicker">Skill resolver</span>
			<h2>작업 목적을 먼저 검색한다</h2>
			<p>
				{meta.canonicalSurface ?? 'DartLab Skill OS'}는 분석, 엔진, 런타임, 운영 절차의 공식 진입점이다.
				목적에 맞는 skill을 고르면 필요한 입력, 실행 순서, 검산 기준, API 연결을 바로 읽을 수 있다.
			</p>
		</div>
		<div class="search-count">
			<BookOpen size={18} />
			<strong>{publicSkills.length}</strong>
			<span>skills</span>
		</div>
	</div>

	<div class="search-controls">
		<label class="search-input">
			<Search size={16} />
			<input bind:value={query} placeholder="예: 미국 주식 분석, 테스트 규칙, MCP, 수익성, Pyodide" />
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
			All <span>{publicSkills.length}</span>
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
		<p class="empty">검색 결과가 없다. 더 넓은 목적어나 분석 주제로 다시 검색한다.</p>
	{:else}
		<div class="skill-reader">
			<div class="result-list" aria-label="Skill 목록">
				{#each filtered as item}
					<button
						class="result-card"
						class:active={selectedSkill?.id === item.skill.id}
						onclick={() => selectSkill(item.skill)}
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
					</button>
				{/each}
			</div>

			{#if selectedSkill}
				<article class="skill-detail" aria-label="선택한 Skill 문서">
					<div class="detail-head">
						<div>
							<span class="detail-kicker">{selectedSkill.categoryTitle ?? selectedSkill.category}</span>
							<h3>{selectedSkill.title}</h3>
						</div>
						<span class="detail-status">{selectedSkill.status}</span>
					</div>
					<p class="detail-purpose">{selectedSkill.purpose}</p>

					{#if limited(selectedSkill.examples, 3).length > 0}
						<section class="start-here">
							<h4>바로 써보기</h4>
							{#each limited(selectedSkill.examples, 3) as item}
								<pre>{formatExample(item)}</pre>
							{/each}
						</section>
					{/if}

					{#if limited(combinedInputs(selectedSkill), 8).length > 0}
						<section>
							<h4>필요 입력</h4>
							<div class="chip-row">
								{#each limited(combinedInputs(selectedSkill), 8) as item}
									<span>{item}</span>
								{/each}
							</div>
						</section>
					{/if}

					{#if limited(selectedSkill.whenToUse, 6).length > 0}
						<section>
							<h4>언제 쓰나</h4>
							<ul>
								{#each limited(selectedSkill.whenToUse, 6) as item}
									<li>{item}</li>
								{/each}
							</ul>
						</section>
					{/if}

					{#if limited(selectedSkill.requiredEvidence, 8).length > 0}
						<section>
							<h4>필요한 근거</h4>
							<div class="chip-row">
								{#each limited(selectedSkill.requiredEvidence, 8) as item}
									<span>{item}</span>
								{/each}
							</div>
						</section>
					{/if}

					{#if limited([...(selectedSkill.apiRefs ?? []), ...(selectedSkill.toolRefs ?? [])], 10).length > 0}
						<section>
							<h4>API와 도구</h4>
							<div class="chip-row">
								{#each limited([...(selectedSkill.apiRefs ?? []), ...(selectedSkill.toolRefs ?? [])], 10) as item}
									<span>{item}</span>
								{/each}
							</div>
						</section>
					{/if}

					{#if limited(selectedSkill.procedure, 8).length > 0}
						<section>
							<h4>실행 순서</h4>
							<div class="step-list">
								{#each limited(selectedSkill.procedure, 8) as item, i}
									<div class="step-item">
										<span>{i + 1}</span>
										<p>{item}</p>
									</div>
								{/each}
							</div>
						</section>
					{/if}

					{#if limited(combinedOutputs(selectedSkill), 8).length > 0}
						<section>
							<h4>결과물</h4>
							<ul>
								{#each limited(combinedOutputs(selectedSkill), 8) as item}
									<li>{item}</li>
								{/each}
							</ul>
						</section>
					{/if}

					{#if limited(selectedSkill.visualGuidance, 5).length > 0}
						<section>
							<h4>시각화 기준</h4>
							<ul>
								{#each limited(selectedSkill.visualGuidance, 5) as item}
									<li>{item}</li>
								{/each}
							</ul>
						</section>
					{/if}

					{#if runtimeRows(selectedSkill).length > 0}
						<section>
							<h4>실행 환경</h4>
							<div class="runtime-grid">
								{#each runtimeRows(selectedSkill) as runtime}
									<div>
										<strong>{runtime.name}</strong>
										<span>{runtime.status}</span>
										{#if runtime.notes.length > 0}
											<p>{runtime.notes.join(' ')}</p>
										{/if}
									</div>
								{/each}
							</div>
						</section>
					{/if}

					{#if limited(selectedSkill.failureModes, 5).length > 0 || limited(selectedSkill.forbidden, 5).length > 0}
						<section>
							<h4>주의할 점</h4>
							<ul>
								{#each [...limited(selectedSkill.failureModes, 5), ...limited(selectedSkill.forbidden, 5)] as item}
									<li>{item}</li>
								{/each}
							</ul>
						</section>
					{/if}
				</article>
			{/if}
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

	.skill-reader {
		display: grid;
		grid-template-columns: minmax(280px, 0.82fr) minmax(0, 1.18fr);
		gap: 0.85rem;
		align-items: start;
	}

	.result-list {
		display: grid;
		gap: 0.6rem;
		max-height: 820px;
		overflow: auto;
		padding-right: 0.25rem;
	}

	.result-card {
		display: flex;
		flex-direction: column;
		width: 100%;
		gap: 0.45rem;
		min-height: 142px;
		padding: 0.85rem;
		border: 1px solid rgba(30, 36, 51, 0.72);
		border-radius: 8px;
		background: rgba(15, 18, 25, 0.52);
		text-align: left;
		cursor: pointer;
		transition: border-color 0.14s, transform 0.14s, background 0.14s;
	}

	.result-card:hover,
	.result-card.active {
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
		flex: 0 0 auto;
		white-space: nowrap;
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

	.skill-detail {
		position: sticky;
		top: 4.5rem;
		padding: 1.1rem;
		border: 1px solid rgba(30, 36, 51, 0.82);
		border-radius: 8px;
		background: rgba(3, 5, 9, 0.76);
		box-shadow: 0 18px 48px rgba(0, 0, 0, 0.2);
	}

	.detail-head {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 1rem;
		margin-bottom: 0.6rem;
	}

	.detail-head > div {
		min-width: 0;
	}

	.detail-kicker,
	.detail-status {
		color: #fb923c;
		flex: 0 0 auto;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		white-space: nowrap;
	}

	.skill-detail h3 {
		margin: 0.2rem 0 0 !important;
		color: #f8fafc !important;
		font-size: 1.35rem !important;
		line-height: 1.28;
	}

	.detail-purpose {
		margin: 0 0 1rem !important;
		color: #cbd5e1;
		line-height: 1.65;
	}

	.skill-detail section {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid rgba(30, 36, 51, 0.72);
	}

	.skill-detail section.start-here {
		margin-top: 0.9rem;
		padding: 0.9rem;
		border: 1px solid rgba(234, 70, 71, 0.22);
		border-radius: 8px;
		background: rgba(234, 70, 71, 0.055);
	}

	.skill-detail h4 {
		margin: 0 0 0.55rem !important;
		color: #f1f5f9 !important;
		font-size: 0.9rem !important;
	}

	.start-here pre {
		margin: 0.55rem 0 0 !important;
		padding: 0.75rem 0.85rem;
		border: 1px solid rgba(30, 36, 51, 0.9);
		border-radius: 7px;
		background: rgba(3, 5, 9, 0.72);
		color: #e2e8f0;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.76rem;
		line-height: 1.6;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}

	.step-list {
		display: grid;
		gap: 0.55rem;
	}

	.step-item {
		display: grid;
		grid-template-columns: 1.55rem minmax(0, 1fr);
		gap: 0.65rem;
		align-items: start;
		padding: 0.65rem;
		border: 1px solid rgba(30, 36, 51, 0.78);
		border-radius: 7px;
		background: rgba(15, 18, 25, 0.42);
	}

	.step-item span {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 1.55rem;
		height: 1.55rem;
		border-radius: 6px;
		background: rgba(234, 70, 71, 0.12);
		color: #fca5a5;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.72rem;
		font-weight: 700;
	}

	.step-item p {
		margin: 0 !important;
		color: #94a3b8;
		font-size: 0.84rem;
		line-height: 1.62;
	}

	.skill-detail ul {
		margin: 0 !important;
		padding-left: 1.1rem;
		color: #94a3b8;
		font-size: 0.86rem;
		line-height: 1.65;
	}

	.skill-detail li + li {
		margin-top: 0.32rem;
	}

	.chip-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.chip-row span {
		display: inline-flex;
		align-items: center;
		min-height: 1.65rem;
		padding: 0.2rem 0.55rem;
		border: 1px solid rgba(30, 36, 51, 0.9);
		border-radius: 6px;
		background: rgba(15, 18, 25, 0.68);
		color: #cbd5e1;
		font-size: 0.75rem;
	}

	.runtime-grid {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.55rem;
	}

	.runtime-grid div {
		padding: 0.65rem;
		border: 1px solid rgba(30, 36, 51, 0.78);
		border-radius: 7px;
		background: rgba(15, 18, 25, 0.45);
	}

	.runtime-grid strong,
	.runtime-grid span {
		display: inline-block;
		margin-right: 0.4rem;
		font-size: 0.75rem;
	}

	.runtime-grid strong {
		color: #f8fafc;
	}

	.runtime-grid span {
		color: #86efac;
	}

	.runtime-grid p {
		margin: 0.35rem 0 0 !important;
		color: #94a3b8;
		font-size: 0.76rem;
		line-height: 1.5;
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

		.skill-reader {
			grid-template-columns: 1fr;
		}

		.result-list {
			max-height: none;
			overflow: visible;
			padding-right: 0;
		}

		.skill-detail {
			position: static;
			order: -1;
		}

		.runtime-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
