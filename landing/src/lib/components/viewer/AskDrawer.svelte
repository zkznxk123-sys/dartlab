<script lang="ts">
	// 본진 공시뷰어 우측 AI Q&A 드로어 — 헤더 아바타 버튼으로 열리고 격자를 밀고 나온다(push).
	// 검증된 엔진 재사용: searchIndex(근거검색)·answerCompose(Tier0 결정론 답)·financeAsk(재무신호)·webllm(Tier1 opt-in).
	// 근거 칩 클릭 → onfocus(hit) 로 부모 viewer 의 onSearchResult(섹션·기간 점프 + 셀 glow) 호출(점프 로직 비중복).
	import { base } from '$app/paths';
	import { Send, Sparkles, X } from 'lucide-svelte';
	import { plainText, search, type SearchHit, type SearchIndex } from '$lib/viewer/searchIndex';
	import { composeAnswer, type ComposeResult } from '$lib/viewer/answerCompose';
	import { loadCompanyFinanceSignals } from '$lib/viewer/financeAsk';
	import { answerQuestion, webgpuAvailable, type AskEvidence } from '$lib/viewer/webllm';
	import type { FinanceSignal } from '$lib/viewer/diff';
	import type { PanelBundle } from '$lib/viewer/types';

	let {
		code,
		bundle,
		searchIndex,
		indexing = false,
		onfocus,
		onclose
	}: {
		code: string;
		bundle: PanelBundle | null;
		searchIndex: SearchIndex | null;
		indexing?: boolean;
		onfocus: (hit: SearchHit) => void;
		onclose: () => void;
	} = $props();

	const SAMPLES = ['영업이익 추세는?', '부채 추세는?', '주요 소송이 있나?', '배당 규모는?'];

	let question = $state('');
	let composing = $state(false);
	let composed = $state<ComposeResult | null>(null);
	let evHits = $state<SearchHit[]>([]); // 점프용 원본 hit
	let evItems = $state<{ n: number; period: string; path: string; text: string }[]>([]);
	let searchErr = $state<string | null>(null);
	let finSignals = $state<FinanceSignal[]>([]);
	let webgpuOk = $state(false);
	let llmAnswer = $state('');
	let llmRunning = $state(false);
	let llmErr = $state<string | null>(null);
	let modelProgress = $state(0);
	let modelText = $state('');
	let inputEl = $state<HTMLTextAreaElement | null>(null);

	$effect(() => {
		webgpuOk = webgpuAvailable();
	});
	// 회사 바뀌면 초기화 + 재무 신호 prefetch.
	$effect(() => {
		const c = code;
		composed = null;
		evHits = [];
		evItems = [];
		searchErr = null;
		llmAnswer = '';
		llmErr = null;
		finSignals = [];
		void loadCompanyFinanceSignals(c).then((s) => {
			if (code === c) finSignals = s;
		});
	});
	$effect(() => {
		requestAnimationFrame(() => inputEl?.focus());
	});

	async function ask() {
		if (!searchIndex || !bundle || !question.trim()) return;
		const q = question.trim();
		composing = true;
		composed = null;
		llmAnswer = '';
		llmErr = null;
		searchErr = null;
		evHits = [];
		evItems = [];
		modelProgress = 0;
		modelText = '';
		const { hits, added } = search(searchIndex, q, { topK: 6, expand: true });
		const hs: SearchHit[] = [];
		const its: { n: number; period: string; path: string; text: string }[] = [];
		let n = 1;
		for (const h of hits) {
			const cell = bundle.gridBySection.get(h.sectionKey)?.[h.rowIndex]?.cells?.[h.period] ?? '';
			const text = plainText(cell).slice(0, 700);
			if (!text) continue;
			hs.push(h);
			its.push({ n: n++, period: h.period, path: [h.chapter, h.section, h.block].filter(Boolean).join(' > '), text });
		}
		evHits = hs;
		evItems = its;
		const sigs = finSignals.length ? finSignals : await loadCompanyFinanceSignals(code);
		if (!finSignals.length && sigs.length) finSignals = sigs;
		composed = composeAnswer(q, hits, added, sigs);
		if (!its.length && !composed.citedSignal) searchErr = '관련 근거를 찾지 못했습니다. 다른 표현으로 질문해 보세요.';
		composing = false;
	}

	async function runLlm() {
		if (!composed || !evItems.length || llmRunning || !webgpuOk) return;
		const q = question.trim();
		llmRunning = true;
		llmErr = null;
		llmAnswer = '';
		modelProgress = 0;
		modelText = '';
		const payload: AskEvidence[] = [
			{ n: 0, period: '', path: '결정론 분석(숫자 확정)', text: composed.answer },
			...evItems.map(({ n, period, path, text }) => ({ n, period, path, text }))
		];
		try {
			await answerQuestion(q, payload, {
				onProgress: (p) => {
					modelProgress = p.progress;
					modelText = p.text;
				},
				onToken: (d) => (llmAnswer += d)
			});
		} catch (e) {
			llmErr = e instanceof Error ? e.message : String(e);
		} finally {
			llmRunning = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			void ask();
		}
	}
</script>

<aside class="ask-drawer">
	<header class="ad-head">
		<picture>
			<source srcset="{base}/avatar-detective.webp" type="image/webp" />
			<img src="{base}/avatar-detective.png" alt="" width="22" height="22" />
		</picture>
		<strong>공시 Q&A</strong>
		<button type="button" class="ad-x" onclick={onclose} title="닫기" aria-label="닫기"><X size={15} /></button>
	</header>

	<div class="ad-askbox">
		<textarea
			bind:this={inputEl}
			bind:value={question}
			rows="1"
			placeholder="이 회사 공시에 질문 (예: 영업이익 추세는?)"
			onkeydown={onKey}
		></textarea>
		<button type="button" class="ad-send" onclick={ask} disabled={!searchIndex || composing || !question.trim()}>
			{#if composing}<Sparkles size={14} />{:else}<Send size={14} />{/if}
		</button>
	</div>
	<div class="ad-samples">
		{#each SAMPLES as s}
			<button type="button" onclick={() => ((question = s), ask())} disabled={!searchIndex || composing}>{s}</button>
		{/each}
	</div>

	<div class="ad-body">
		{#if composed}
			<p class="ad-answer">{composed.answer}</p>
			{#if composed.citedSignal}
				<div class="ad-cited">재무 근거: {composed.citedSignal.label} · 최근 {composed.citedSignal.points[0]?.period}</div>
			{/if}
			{#if webgpuOk}
				{#if llmAnswer}
					<div class="ad-llm"><span class="ad-llm-tag">AI 확장</span><p class="ad-answer llm">{llmAnswer}</p></div>
				{:else if llmRunning}
					<div class="ad-wait"><span class="dot"></span>{modelProgress < 1 && modelText ? `모델 준비 ${Math.round(modelProgress * 100)}% (첫 1회 ~705MB)` : '근거 읽고 서술 중…'}</div>
				{:else}
					<button type="button" class="ad-llm-run" onclick={runLlm}><Sparkles size={12} /> AI로 더 자세히 (왜·종합)</button>
				{/if}
				{#if llmErr}<div class="ad-note err">{llmErr}</div>{/if}
			{/if}
		{:else if composing}
			<div class="ad-wait"><span class="dot"></span>공시에서 근거 찾는 중…</div>
		{:else if searchErr}
			<div class="ad-note err">{searchErr}</div>
		{:else}
			<div class="ad-empty">질문하면 이 회사 공시에서 근거를 찾아 즉시 답합니다(다운로드 0). 근거를 누르면 격자의 해당 위치로 이동합니다.</div>
		{/if}

		{#if evItems.length}
			<div class="ad-ev-title">찾은 근거 {evItems.length}</div>
			{#each evItems as e, i (e.n)}
				<button type="button" class="ad-ev" onclick={() => onfocus(evHits[i])}>
					<div class="ad-ev-head"><span>근거 {e.n}</span><code>{e.period}</code></div>
					<strong>{e.path}</strong>
					<p>{e.text.slice(0, 120)}{e.text.length > 120 ? '…' : ''}</p>
				</button>
			{/each}
		{/if}

		<div class="ad-foot">{webgpuOk ? '즉시 답은 다운로드 0. "더 자세히"만 첫 1회 모델(~705MB·캐시) 다운로드.' : '즉시 답·근거 검색은 모든 브라우저. 대화형 확장은 WebGPU(Chrome/Edge 데스크톱) 필요.'}{indexing ? ' · 색인 준비 중' : ''}</div>
	</div>
</aside>

<style>
	.ask-drawer {
		min-width: 0;
		min-height: 0;
		height: 100%;
		display: flex;
		flex-direction: column;
		border-left: 1px solid #1e2433;
		background: #070b14;
		animation: adslide 0.18s ease-out;
	}
	@keyframes adslide {
		from {
			transform: translateX(24px);
			opacity: 0.4;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}
	.ad-head {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px;
		border-bottom: 1px solid #1e2433;
	}
	.ad-head img {
		border-radius: 50%;
	}
	.ad-head strong {
		font-size: 13px;
		color: #f1f5f9;
		font-weight: 800;
	}
	.ad-x {
		margin-left: auto;
		display: grid;
		place-items: center;
		width: 26px;
		height: 26px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: transparent;
		color: #94a3b8;
		cursor: pointer;
	}
	.ad-x:hover {
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
	}
	.ad-askbox {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		padding: 10px 12px 6px;
	}
	.ad-askbox textarea {
		flex: 1 1 auto;
		min-width: 0;
		max-height: 96px;
		height: 36px;
		padding: 8px 10px;
		border: 1px solid #263145;
		border-radius: 8px;
		background: #0a0e18;
		color: #f1f5f9;
		font: inherit;
		font-size: 13px;
		line-height: 1.4;
		resize: none;
		outline: none;
	}
	.ad-askbox textarea:focus {
		border-color: #fb923c;
	}
	.ad-send {
		display: grid;
		place-items: center;
		width: 36px;
		height: 36px;
		flex-shrink: 0;
		border: none;
		border-radius: 8px;
		background: #fb923c;
		color: #1a1206;
		cursor: pointer;
	}
	.ad-send:disabled {
		opacity: 0.45;
		cursor: default;
	}
	.ad-samples {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		padding: 0 12px 8px;
	}
	.ad-samples button {
		height: 26px;
		padding: 0 9px;
		border: 1px solid #1e2433;
		border-radius: 999px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
	}
	.ad-samples button:hover:not(:disabled) {
		border-color: rgba(251, 146, 60, 0.5);
		color: #fb923c;
	}
	.ad-samples button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.ad-body {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
		padding: 8px 12px 12px;
	}
	.ad-answer {
		margin: 0;
		padding: 11px;
		border: 1px solid rgba(56, 189, 248, 0.3);
		border-radius: 8px;
		background: rgba(14, 165, 233, 0.06);
		color: #e2e8f0;
		font-size: 13px;
		line-height: 1.6;
		white-space: pre-wrap;
	}
	.ad-cited {
		margin-top: 6px;
		color: #fb923c;
		font-size: 11px;
	}
	.ad-llm {
		margin-top: 10px;
	}
	.ad-llm-tag {
		color: #bae6fd;
		font-size: 10px;
		font-weight: 800;
		text-transform: uppercase;
	}
	.ad-answer.llm {
		margin-top: 4px;
		border-color: rgba(56, 189, 248, 0.4);
		background: rgba(14, 165, 233, 0.1);
		color: #dbeafe;
	}
	.ad-llm-run {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		margin-top: 10px;
		height: 30px;
		padding: 0 12px;
		border: 1px solid rgba(56, 189, 248, 0.45);
		border-radius: 7px;
		background: rgba(14, 165, 233, 0.08);
		color: #bae6fd;
		font: inherit;
		font-size: 12px;
		cursor: pointer;
	}
	.ad-llm-run:hover {
		background: rgba(14, 165, 233, 0.16);
	}
	.ad-wait {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 2px;
		color: #94a3b8;
		font-size: 12px;
	}
	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #fb923c;
		animation: pulse 1s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.3;
		}
	}
	.ad-empty {
		color: #64748b;
		font-size: 12px;
		line-height: 1.5;
		padding: 10px 2px;
	}
	.ad-note {
		font-size: 11px;
		padding: 6px 2px;
	}
	.ad-note.err {
		color: #f87171;
	}
	.ad-ev-title {
		margin: 14px 0 6px;
		color: #94a3b8;
		font-size: 11px;
		font-weight: 800;
		text-transform: uppercase;
	}
	.ad-ev {
		display: flex;
		flex-direction: column;
		gap: 4px;
		width: 100%;
		margin-bottom: 6px;
		padding: 8px 9px;
		border: 1px solid #1e2433;
		border-radius: 7px;
		background: #0a0e18;
		color: #cbd5e1;
		text-align: left;
		cursor: pointer;
	}
	.ad-ev:hover {
		border-color: rgba(251, 146, 60, 0.55);
	}
	.ad-ev-head {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		color: #64748b;
		font-size: 10px;
	}
	.ad-ev-head span {
		color: #fb923c;
		font-weight: 700;
	}
	.ad-ev strong {
		font-size: 12px;
		color: #e2e8f0;
		line-height: 1.35;
	}
	.ad-ev p {
		margin: 0;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.45;
	}
	.ad-foot {
		margin-top: 12px;
		color: #64748b;
		font-size: 10px;
		line-height: 1.5;
	}
</style>
