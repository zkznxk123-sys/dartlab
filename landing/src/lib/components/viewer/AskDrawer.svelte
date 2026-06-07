<script lang="ts">
	// 본진 공시뷰어 우측 AI Q&A 채팅 드로어 — 헤더 아바타 버튼으로 열리고 격자를 밀고 나온다(push).
	// 질문하면: ① 결정론 답+근거 즉시(grounding, 다운로드 0) ② WebGPU 있으면 그 위에서 AI 가 대화로 자동 응답(버튼 0).
	// 멀티턴 대화 맥락 유지. 근거 칩 클릭 → onfocus(hit) 로 부모 onSearchResult(섹션·기간 점프 + 셀 glow) 재사용.
	// 모델은 Web Worker(메인스레드 비차단), 토큰 배칭(재렌더 억제). 검증 엔진 재사용: search·answerCompose·financeAsk·webllm.
	import { base } from '$app/paths';
	import { Send, Sparkles, X } from 'lucide-svelte';
	import { plainText, search, type SearchHit, type SearchIndex } from '$lib/viewer/searchIndex';
	import { composeAnswer } from '$lib/viewer/answerCompose';
	import { loadCompanyFinanceSignals } from '$lib/viewer/financeAsk';
	import { chatAnswer, webgpuUsable, type AskEvidence, type ChatTurn } from '$lib/viewer/webllm';
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

	interface EvRef {
		n: number;
		period: string;
		path: string;
		text: string;
	}
	interface Turn {
		q: string;
		det: string; // 결정론 답(즉시·grounding)
		citedLabel: string | null;
		evItems: EvRef[];
		evHits: SearchHit[];
		ai: string; // AI 대화 답(스트리밍)
		aiRunning: boolean;
		aiErr: string | null;
	}

	let question = $state('');
	let chat = $state<Turn[]>([]);
	let busy = $state(false); // 한 번에 한 질문
	let finSignals = $state<FinanceSignal[]>([]);
	let webgpuOk = $state(false);
	let modelProgress = $state(0);
	let modelText = $state('');
	let inputEl = $state<HTMLTextAreaElement | null>(null);
	let scrollEl = $state<HTMLElement | null>(null);

	$effect(() => {
		void webgpuUsable().then((v) => (webgpuOk = v)); // 실제 어댑터 확인(헛다운로드 방지)
	});
	// 회사 바뀌면 대화 초기화 + 재무 신호 prefetch(질문 시 0ms).
	$effect(() => {
		const c = code;
		chat = [];
		finSignals = [];
		void loadCompanyFinanceSignals(c).then((s) => {
			if (code === c) finSignals = s;
		});
	});
	$effect(() => {
		requestAnimationFrame(() => inputEl?.focus());
	});

	function scrollBottom() {
		requestAnimationFrame(() => {
			if (scrollEl) scrollEl.scrollTop = scrollEl.scrollHeight;
		});
	}

	async function ask() {
		if (!searchIndex || !bundle || !question.trim() || busy) return;
		const q = question.trim();
		question = '';
		busy = true;
		modelProgress = 0;
		modelText = '';

		// ① 결정론 답 + 근거(즉시·다운로드 0)
		const { hits, added } = search(searchIndex, q, { topK: 6, expand: true });
		const evHits: SearchHit[] = [];
		const evItems: EvRef[] = [];
		let n = 1;
		for (const h of hits) {
			const cell = bundle.gridBySection.get(h.sectionKey)?.[h.rowIndex]?.cells?.[h.period] ?? '';
			const text = plainText(cell).slice(0, 700);
			if (!text) continue;
			evHits.push(h);
			evItems.push({ n: n++, period: h.period, path: [h.chapter, h.section, h.block].filter(Boolean).join(' > '), text });
		}
		const sigs = finSignals.length ? finSignals : await loadCompanyFinanceSignals(code);
		if (!finSignals.length && sigs.length) finSignals = sigs;
		const composed = composeAnswer(q, hits, added, sigs);

		chat.push({
			q,
			det: composed.answer,
			citedLabel: composed.citedSignal?.label ?? null,
			evItems,
			evHits,
			ai: '',
			aiRunning: webgpuOk && (evItems.length > 0 || composed.citedSignal != null),
			aiErr: null
		});
		const idx = chat.length - 1;
		scrollBottom();

		// ② WebGPU 있으면 그 위에서 AI 가 대화로 자동 응답(버튼 0)
		if (!chat[idx].aiRunning) {
			busy = false;
			return;
		}
		const history: ChatTurn[] = [];
		for (let i = 0; i < chat.length; i++) {
			history.push({ role: 'user', content: chat[i].q });
			if (i !== idx) history.push({ role: 'assistant', content: chat[i].ai || chat[i].det });
		}
		const payload: AskEvidence[] = [
			{ n: 0, period: '', path: '결정론 분석(숫자 확정)', text: composed.answer },
			...evItems.map(({ n, period, path, text }) => ({ n, period, path, text }))
		];
		let buf = '';
		let lastFlush = 0;
		try {
			await chatAnswer(history, payload, {
				onProgress: (p) => {
					modelProgress = p.progress;
					modelText = p.text;
				},
				onToken: (d) => {
					buf += d;
					const now = performance.now();
					if (now - lastFlush > 45) {
						chat[idx].ai = buf;
						lastFlush = now;
						scrollBottom();
					}
				}
			});
			chat[idx].ai = buf;
		} catch (e) {
			chat[idx].aiErr = e instanceof Error ? e.message : String(e);
		} finally {
			chat[idx].aiRunning = false;
			busy = false;
			scrollBottom();
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
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

	<div class="ad-scroll" bind:this={scrollEl}>
		{#if chat.length === 0}
			<div class="ad-empty">
				이 회사 공시에 질문하세요. 근거를 찾아 <b>즉시 답</b>하고(다운로드 0), {webgpuOk ? 'AI 가 대화로 이어 설명합니다.' : '근거를 보여줍니다.'}<br />
				근거를 누르면 격자의 해당 위치로 이동합니다.
			</div>
		{/if}
		{#each chat as t, ti (ti)}
			<div class="msg user">{t.q}</div>
			<div class="msg bot">
				{#if t.ai}
					<p class="bot-text">{t.ai}</p>
					<div class="det-line">결정론: {t.det}</div>
				{:else}
					<p class="bot-text">{t.det}</p>
					{#if t.aiRunning}
						<div class="gen"><span class="dot"></span>{modelProgress < 1 && modelText ? `대화 모델 준비 ${Math.round(modelProgress * 100)}% (첫 1회 ~705MB)` : '이어서 설명 생성 중…'}</div>
					{/if}
				{/if}
				{#if t.aiErr}<div class="gen err">{t.aiErr}</div>{/if}
				{#if t.citedLabel}<div class="cite">재무: {t.citedLabel}</div>{/if}
				{#if t.evItems.length}
					<div class="ev-row">
						{#each t.evItems as e, i (e.n)}
							<button type="button" class="ev-chip" onclick={() => onfocus(t.evHits[i])} title={e.path}>근거 {e.n} · {e.period}</button>
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<div class="ad-foot-area">
		{#if chat.length === 0}
			<div class="ad-samples">
				{#each SAMPLES as s}
					<button type="button" onclick={() => ((question = s), ask())} disabled={!searchIndex || busy}>{s}</button>
				{/each}
			</div>
		{/if}
		<div class="ad-askbox">
			<textarea
				bind:this={inputEl}
				bind:value={question}
				rows="1"
				placeholder="질문 입력 후 Enter (예: 영업이익 추세는?)"
				onkeydown={onKey}
			></textarea>
			<button type="button" class="ad-send" onclick={ask} disabled={!searchIndex || busy || !question.trim()}>
				{#if busy}<Sparkles size={14} />{:else}<Send size={14} />{/if}
			</button>
		</div>
		<div class="ad-note">{webgpuOk ? '즉시 답=다운로드 0. 대화는 첫 1회 모델(~705MB·캐시) 후 자동.' : '대화형 응답은 WebGPU(Chrome/Edge 데스크톱) 필요 — 지금은 결정론 답·근거.'}{indexing ? ' · 색인 준비 중' : ''}</div>
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
		flex-shrink: 0;
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
	.ad-scroll {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.ad-empty {
		color: #64748b;
		font-size: 12px;
		line-height: 1.6;
		padding: 8px 2px;
	}
	.ad-empty b {
		color: #cbd5e1;
	}
	.msg {
		max-width: 92%;
		font-size: 13px;
		line-height: 1.55;
		white-space: pre-wrap;
		word-break: break-word;
	}
	.msg.user {
		align-self: flex-end;
		padding: 8px 11px;
		border-radius: 12px 12px 3px 12px;
		background: rgba(251, 146, 60, 0.14);
		color: #fde7cf;
	}
	.msg.bot {
		align-self: flex-start;
		width: 100%;
		max-width: 100%;
		padding: 10px 11px;
		border: 1px solid #1e2433;
		border-radius: 12px 12px 12px 3px;
		background: #0a0e18;
	}
	.bot-text {
		margin: 0;
		color: #e2e8f0;
		font-size: 13px;
		line-height: 1.6;
	}
	.det-line {
		margin-top: 7px;
		padding-top: 6px;
		border-top: 1px dashed #1e2433;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.gen {
		display: flex;
		align-items: center;
		gap: 7px;
		margin-top: 7px;
		color: #94a3b8;
		font-size: 11px;
	}
	.gen.err {
		color: #f87171;
	}
	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #38bdf8;
		animation: pulse 1s ease-in-out infinite;
	}
	@keyframes pulse {
		50% {
			opacity: 0.3;
		}
	}
	.cite {
		margin-top: 6px;
		color: #fb923c;
		font-size: 11px;
	}
	.ev-row {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		margin-top: 8px;
	}
	.ev-chip {
		max-width: 100%;
		padding: 4px 8px;
		border: 1px solid #1e2433;
		border-radius: 999px;
		background: #050811;
		color: #94a3b8;
		font: inherit;
		font-size: 10.5px;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.ev-chip:hover {
		border-color: rgba(251, 146, 60, 0.55);
		color: #fb923c;
	}
	.ad-foot-area {
		flex-shrink: 0;
		border-top: 1px solid #1e2433;
		padding: 8px 12px 10px;
	}
	.ad-samples {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
		padding-bottom: 8px;
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
	.ad-askbox {
		display: flex;
		align-items: flex-end;
		gap: 8px;
	}
	.ad-askbox textarea {
		flex: 1 1 auto;
		min-width: 0;
		max-height: 110px;
		height: 38px;
		padding: 9px 10px;
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
		width: 38px;
		height: 38px;
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
	.ad-note {
		margin-top: 6px;
		color: #64748b;
		font-size: 10px;
		line-height: 1.5;
	}
</style>
