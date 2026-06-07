<script lang="ts">
	// 공시뷰어 grounded Q&A 코파일럿 — 질문하면 그 회사 패널에서 근거를 검색해 찾고, WebLLM(Qwen3)이 그 근거에
	// 한해서만 한국어로 답한다. 근거 칩 클릭 시 뷰어의 해당 셀로 점프(glow). WebGPU 없으면 근거만 표시(데이터는 찾음).
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { CornerDownLeft, FileSearch, Send, Sparkles } from 'lucide-svelte';
	import CompanyQuickSearch from '$lib/components/search/CompanyQuickSearch.svelte';
	import PanelMatrix from '$lib/components/viewer/PanelMatrix.svelte';
	import PanelTocTree from '$lib/components/viewer/PanelTocTree.svelte';
	import TimelineRibbon from '$lib/components/viewer/TimelineRibbon.svelte';
	import { loadPanelBundle } from '$lib/viewer/panelLoad';
	import { loadCompanies } from '$lib/viewer/companyNames';
	import { buildIndexChunked, plainText, search, type SearchIndex } from '$lib/viewer/searchIndex';
	import { answerQuestion, webgpuAvailable, type AskEvidence } from '$lib/viewer/webllm';
	import type { PanelBundle } from '$lib/viewer/types';

	let { data }: { data: { code: string } } = $props();
	const code = $derived(data.code);

	const COL_CHOICES = [3, 6, 9] as const;
	const SAMPLES = ['주요 소송이 있나?', '올해 재고자산 변화는?', '배당 정책은?', '특수관계자 거래 규모는?', '가장 큰 위험요인은?'];

	interface EvItem extends AskEvidence {
		sectionKey: string;
		rowIndex: number;
	}

	let nameMap = $state<Map<string, string>>(new Map());
	let bundle = $state<PanelBundle | null>(null);
	let loading = $state(true);
	let errorMsg = $state<string | null>(null);
	let activeSectionKey = $state<string | undefined>(undefined);
	let activeBlock = $state<string | null>(null);
	let windowEnd = $state(0);
	let cols = $state(6);
	let glowCell = $state<{ rowIndex: number; period: string } | null>(null);

	let searchIndex = $state<SearchIndex | null>(null);
	let indexing = $state(false);

	// Q&A
	let question = $state('');
	let asking = $state(false);
	let answer = $state('');
	let answerErr = $state<string | null>(null);
	let evidence = $state<EvItem[]>([]);
	let modelProgress = $state(0);
	let modelText = $state('');
	let webgpuOk = $state(false);

	$effect(() => {
		webgpuOk = webgpuAvailable();
		void loadCompanies().then((cs) => (nameMap = new Map(cs.map((c) => [c.code, c.name]))));
	});

	$effect(() => {
		const c = code;
		loading = true;
		errorMsg = null;
		bundle = null;
		searchIndex = null;
		answer = '';
		answerErr = null;
		evidence = [];
		void loadPanelBundle(c)
			.then((next) => {
				if (code !== c) return;
				bundle = next;
				activeSectionKey = next.toc.chapters[0]?.sections[0]?.sectionKey;
				activeBlock = null;
				windowEnd = 0;
				if (!next.periods.length) errorMsg = '이 종목의 panel 데이터가 없습니다.';
			})
			.catch((e) => {
				if (code === c) errorMsg = `로드 실패: ${e instanceof Error ? e.message : String(e)}`;
			})
			.finally(() => {
				if (code === c) loading = false;
			});
	});

	// 검색 인덱스(=근거 찾기 엔진) 빌드 — 패널 바뀌면 재빌드.
	$effect(() => {
		const cur = bundle;
		searchIndex = null;
		if (!cur || !cur.periods.length) {
			indexing = false;
			return;
		}
		let cancelled = false;
		indexing = true;
		void buildIndexChunked(cur).then((idx) => {
			if (cancelled) return;
			searchIndex = idx;
			indexing = false;
		});
		return () => {
			cancelled = true;
		};
	});

	const corpName = $derived(bundle?.corpName || nameMap.get(code) || code);
	const periods = $derived(bundle?.periods ?? []);
	const windowPeriods = $derived(periods.slice(windowEnd, windowEnd + cols));
	const dartUrls = $derived(bundle?.dartUrlByPeriod ?? {});
	const rows = $derived.by(() => {
		if (!activeSectionKey || !bundle) return [];
		const secRows = bundle.gridBySection.get(activeSectionKey) ?? [];
		return activeBlock ? secRows.filter((r) => r.blockLeaf === activeBlock) : secRows;
	});
	const canOlder = $derived(windowEnd + cols < periods.length);
	const canNewer = $derived(windowEnd > 0);
	const ready = $derived(Boolean(bundle && searchIndex && !indexing));

	function gotoCompany(next: string) {
		void goto(`${base}/lab/viewer-ask?code=${next}`);
	}
	function pickSection(sectionKey: string) {
		activeSectionKey = sectionKey;
		activeBlock = null;
	}
	function pickBlock(sectionKey: string, blockLeaf: string) {
		activeSectionKey = sectionKey;
		activeBlock = blockLeaf;
	}
	function pickPeriod(p: string) {
		const idx = periods.indexOf(p);
		if (idx >= 0) windowEnd = Math.min(Math.max(0, idx), Math.max(0, periods.length - cols));
	}
	function moveNewer() {
		windowEnd = Math.max(0, windowEnd - 1);
	}
	function moveOlder() {
		windowEnd = Math.min(Math.max(0, periods.length - cols), windowEnd + 1);
	}
	// 근거 클릭 → 뷰어의 해당 섹션·기간·셀로 점프 + glow
	function focusEvidence(e: EvItem) {
		activeSectionKey = e.sectionKey;
		activeBlock = null;
		pickPeriod(e.period);
		glowCell = { rowIndex: e.rowIndex, period: e.period };
		window.setTimeout(() => (glowCell = null), 2400);
	}

	async function ask() {
		if (!searchIndex || !bundle || !question.trim() || asking) return;
		const q = question.trim();
		asking = true;
		answer = '';
		answerErr = null;
		evidence = [];
		modelProgress = 0;
		modelText = '';
		// 1) 검색으로 근거 찾기 (질문 → 관련 행/셀)
		const { hits } = search(searchIndex, q, { topK: 6, expand: true });
		const ev: EvItem[] = [];
		let n = 1;
		for (const h of hits) {
			const cell = bundle.gridBySection.get(h.sectionKey)?.[h.rowIndex]?.cells?.[h.period] ?? '';
			const text = plainText(cell).slice(0, 700);
			if (!text) continue;
			ev.push({ n: n++, period: h.period, path: [h.chapter, h.section, h.block].filter(Boolean).join(' > '), text, sectionKey: h.sectionKey, rowIndex: h.rowIndex });
		}
		evidence = ev;
		if (!ev.length) {
			answerErr = '관련 데이터를 찾지 못했습니다. 다른 표현으로 질문해 보세요.';
			asking = false;
			return;
		}
		// 2) WebGPU 있으면 그 근거에 한해 LLM 답변 (없으면 근거만 표시 = 데이터는 찾아줌)
		if (!webgpuOk) {
			asking = false;
			return;
		}
		try {
			const payload: AskEvidence[] = ev.map(({ n, period, path, text }) => ({ n, period, path, text }));
			await answerQuestion(q, payload, {
				onProgress: (p) => {
					modelProgress = p.progress;
					modelText = p.text;
				},
				onToken: (d) => (answer += d)
			});
		} catch (e) {
			answerErr = e instanceof Error ? e.message : String(e);
		} finally {
			asking = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
			e.preventDefault();
			void ask();
		}
	}
</script>

<svelte:head>
	<title>{corpName} 공시 Q&A lab · dartlab</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<main class="page">
	<header class="topbar">
		<a class="brand" href={`${base}/lab`}>dartlab / lab</a>
		<div class="company-slot">
			<CompanyQuickSearch onpick={gotoCompany} placeholder="회사명·종목코드로 Q&A lab 열기" />
		</div>
		<a class="viewer-link" href={`${base}/viewer/company/${code}`}>본진 viewer</a>
	</header>

	<section class="hero">
		<div>
			<div class="eyebrow">disclosure Q&A copilot · 근거 검색 + 온디바이스 답변</div>
			<h1>{corpName}</h1>
			<div class="meta">{code} · 기간 {periods.length} · {indexing ? '근거 인덱스 준비 중…' : searchIndex ? `근거 ${searchIndex.rows.length}행 색인` : '-'}</div>
		</div>
	</section>

	<!-- ASK 바 — 핵심 -->
	<section class="askbar">
		<div class="askbox">
			<FileSearch size={18} />
			<textarea
				bind:value={question}
				rows="1"
				placeholder="이 회사 공시에 대해 질문하세요. 예: 주요 소송이 있나? (⌘/Ctrl+Enter)"
				onkeydown={onKey}
			></textarea>
			<button type="button" class="ask-go" onclick={ask} disabled={!ready || asking || !question.trim()}>
				{#if asking}<Sparkles size={15} />{:else}<Send size={15} />{/if}
				{asking ? '분석 중' : '질문'}
			</button>
		</div>
		<div class="samples">
			{#each SAMPLES as s}
				<button type="button" onclick={() => ((question = s), ask())} disabled={!ready || asking}>{s}</button>
			{/each}
		</div>
		{#if !webgpuOk}
			<div class="gpu-note">이 브라우저는 WebGPU 미지원 — 근거 검색(데이터 찾기)은 되지만 온디바이스 답변 생성은 비활성입니다. (Chrome/Edge 데스크톱 권장)</div>
		{/if}
	</section>

	{#if loading}
		<div class="state"><div class="spinner"></div><p>{corpName} panel 로드 중</p></div>
	{:else if errorMsg}
		<div class="state error"><p>{errorMsg}</p></div>
	{:else if bundle}
		<section class="workspace">
			<aside class="left">
				<div class="panel-title">TOC</div>
				<PanelTocTree toc={bundle.toc} {activeSectionKey} {activeBlock} onpick={pickSection} onpickBlock={pickBlock} />
			</aside>

			<section class="center">
				<div class="ribbon">
					<TimelineRibbon {periods} {windowPeriods} onpick={pickPeriod} onnewer={moveNewer} onolder={moveOlder} {canNewer} {canOlder} />
					<div class="view-controls">
						{#each COL_CHOICES as choice}
							<button type="button" class:active={cols === choice} onclick={() => (cols = choice)}>{choice}</button>
						{/each}
					</div>
				</div>
				<PanelMatrix {rows} periods={windowPeriods} dartUrlByPeriod={dartUrls} glow={glowCell} />
			</section>

			<aside class="right">
				<!-- 답변 -->
				<div class="group">
					<div class="panel-title">답변 <span>{webgpuOk ? '온디바이스' : '근거검색'}</span></div>
					{#if asking && !answer && webgpuOk}
						<div class="answering">
							<div class="spinner sm"></div>
							<span>{modelProgress < 1 && modelText ? `모델 준비 ${Math.round(modelProgress * 100)}%` : '근거 읽고 답하는 중…'}</span>
						</div>
					{/if}
					{#if answer}
						<p class="answer">{answer}</p>
					{:else if !asking && !answerErr && evidence.length && !webgpuOk}
						<p class="answer muted">아래 근거를 찾았습니다. (답변 생성은 WebGPU 브라우저에서)</p>
					{:else if !asking && !answer && !answerErr && !evidence.length}
						<div class="empty">질문하면 이 회사 공시에서 근거를 찾아 답합니다.</div>
					{/if}
					{#if answerErr}
						<div class="empty err">{answerErr}</div>
					{/if}
				</div>

				<!-- 찾은 근거 -->
				<div class="group">
					<div class="panel-title">찾은 근거 <span>{evidence.length}</span></div>
					{#if evidence.length === 0}
						<div class="empty">{indexing ? '근거 인덱스 준비 중' : '질문하면 관련 공시 근거가 여기에'}</div>
					{:else}
						{#each evidence as e (e.n)}
							<button type="button" class="ev" onclick={() => focusEvidence(e)}>
								<div class="ev-head"><span class="ev-n">근거 {e.n}</span><code>{e.period}</code></div>
								<strong>{e.path}</strong>
								<p>{e.text.slice(0, 160)}{e.text.length > 160 ? '…' : ''}</p>
							</button>
						{/each}
						<div class="note">근거 클릭 → 뷰어에서 해당 위치로 이동(glow). 답변은 이 근거 안에서만.</div>
					{/if}
				</div>
			</aside>
		</section>
	{/if}
</main>

<style>
	.page {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		background: #050811;
		color: #f1f5f9;
	}
	.topbar {
		position: sticky;
		top: 0;
		z-index: 90;
		display: grid;
		grid-template-columns: auto minmax(240px, 420px) auto;
		align-items: center;
		gap: 14px;
		height: 54px;
		padding: 0 16px;
		border-bottom: 1px solid #1e2433;
		background: rgba(5, 8, 17, 0.94);
		backdrop-filter: blur(10px);
	}
	.brand,
	.viewer-link {
		color: #cbd5e1;
		text-decoration: none;
		font-size: 13px;
		font-weight: 700;
		white-space: nowrap;
	}
	.viewer-link {
		justify-self: end;
		color: #fb923c;
	}
	.company-slot {
		min-width: 0;
	}
	.hero {
		padding: 16px 16px 12px;
		border-bottom: 1px solid #1e2433;
	}
	.eyebrow {
		color: #64748b;
		font-size: 10px;
		font-weight: 800;
		text-transform: uppercase;
	}
	h1 {
		margin: 4px 0;
		font-size: 24px;
		font-weight: 850;
	}
	.meta {
		color: #94a3b8;
		font-size: 12px;
	}
	.askbar {
		display: flex;
		flex-direction: column;
		gap: 8px;
		padding: 12px 16px;
		border-bottom: 1px solid #1e2433;
		background: #070b14;
	}
	.askbox {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 12px;
		border: 1px solid #263145;
		border-radius: 10px;
		background: #0a0e18;
	}
	.askbox:focus-within {
		border-color: #fb923c;
	}
	.askbox > :global(svg) {
		color: #64748b;
		flex-shrink: 0;
	}
	.askbox textarea {
		flex: 1 1 auto;
		min-width: 0;
		max-height: 120px;
		border: none;
		background: transparent;
		color: #f1f5f9;
		font: inherit;
		font-size: 14px;
		line-height: 1.5;
		resize: none;
		outline: none;
	}
	.ask-go {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		height: 34px;
		padding: 0 14px;
		border: none;
		border-radius: 7px;
		background: #fb923c;
		color: #1a1206;
		font: inherit;
		font-size: 13px;
		font-weight: 700;
		cursor: pointer;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.ask-go:disabled {
		opacity: 0.45;
		cursor: default;
	}
	.samples {
		display: flex;
		gap: 6px;
		flex-wrap: wrap;
	}
	.samples button {
		height: 28px;
		padding: 0 10px;
		border: 1px solid #1e2433;
		border-radius: 999px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.samples button:hover:not(:disabled) {
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
	}
	.samples button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.gpu-note {
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.workspace {
		flex: 1 1 auto;
		min-height: 0;
		display: grid;
		grid-template-columns: 240px minmax(0, 1fr) 400px;
	}
	.left,
	.right {
		min-height: 0;
		overflow-y: auto;
		background: #050811;
	}
	.left {
		border-right: 1px solid #1e2433;
	}
	.right {
		border-left: 1px solid #1e2433;
		padding: 10px;
	}
	.center {
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
	.ribbon {
		flex-shrink: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 8px;
		align-items: center;
		padding: 7px 10px;
		border-bottom: 1px solid #1e2433;
	}
	.view-controls {
		display: flex;
		gap: 4px;
	}
	.view-controls button {
		height: 30px;
		padding: 0 10px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.view-controls button.active {
		border-color: rgba(251, 146, 60, 0.55);
		color: #fb923c;
		background: rgba(251, 146, 60, 0.09);
	}
	.panel-title {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 7px 4px;
		color: #94a3b8;
		font-size: 11px;
		font-weight: 800;
		text-transform: uppercase;
	}
	.panel-title span {
		color: #fb923c;
	}
	.group + .group {
		margin-top: 12px;
		padding-top: 8px;
		border-top: 1px solid #1e2433;
	}
	.answering {
		display: flex;
		align-items: center;
		gap: 8px;
		color: #94a3b8;
		font-size: 12px;
		padding: 6px 2px;
	}
	.answer {
		margin: 0;
		padding: 12px;
		border: 1px solid rgba(56, 189, 248, 0.3);
		border-radius: 8px;
		background: rgba(14, 165, 233, 0.06);
		color: #e2e8f0;
		font-size: 13px;
		line-height: 1.65;
		white-space: pre-wrap;
	}
	.answer.muted {
		border-color: #1e2433;
		background: #0a0e18;
		color: #94a3b8;
	}
	.ev {
		display: flex;
		flex-direction: column;
		gap: 5px;
		width: 100%;
		margin-bottom: 6px;
		padding: 9px;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #0a0e18;
		color: #cbd5e1;
		text-align: left;
		cursor: pointer;
	}
	.ev:hover {
		border-color: rgba(251, 146, 60, 0.55);
	}
	.ev-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		color: #64748b;
		font-size: 10px;
	}
	.ev-n {
		color: #fb923c;
		font-weight: 700;
	}
	.ev strong {
		font-size: 12px;
		color: #e2e8f0;
		line-height: 1.35;
	}
	.ev p {
		margin: 0;
		color: #94a3b8;
		font-size: 11.5px;
		line-height: 1.5;
	}
	.note {
		color: #64748b;
		font-size: 10px;
		padding-top: 4px;
	}
	.empty {
		padding: 12px;
		text-align: center;
		color: #64748b;
		font-size: 12px;
	}
	.err {
		color: #f87171;
	}
	.state {
		flex: 1 1 auto;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		color: #64748b;
		font-size: 12px;
	}
	.state.error {
		color: #f87171;
	}
	.spinner {
		width: 24px;
		height: 24px;
		border: 2px solid #1e2433;
		border-top-color: #fb923c;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}
	.spinner.sm {
		width: 15px;
		height: 15px;
		border-width: 2px;
	}
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	@media (max-width: 1180px) {
		.workspace {
			grid-template-columns: 220px minmax(0, 1fr);
		}
		.right {
			grid-column: 1 / -1;
			border-left: none;
			border-top: 1px solid #1e2433;
			max-height: 400px;
		}
	}
	@media (max-width: 760px) {
		.topbar {
			grid-template-columns: 1fr auto;
			height: auto;
			padding: 10px;
		}
		.company-slot {
			grid-column: 1 / -1;
			order: 3;
		}
		.workspace {
			grid-template-columns: 1fr;
		}
		.left {
			max-height: 160px;
			border-right: none;
			border-bottom: 1px solid #1e2433;
		}
		.ribbon {
			grid-template-columns: 1fr;
		}
	}
</style>
