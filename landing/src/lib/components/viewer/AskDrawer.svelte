<script lang="ts">
	// 본진 공시뷰어 우측 AI Q&A 채팅 드로어 — 헤더 아바타 버튼으로 열리고 격자를 밀고 나온다(push).
	// 모델은 명시적 [받기] 버튼+프로그래스바로 1회 다운로드(상태 가시화). 받기 전에도 결정론 답·근거는 즉시(다운로드 0).
	// 받은 뒤엔 질문하면 그 위에서 대화로 자동 응답(멀티턴). 근거 칩 → 부모 onSearchResult(셀 glow) 재사용.
	import { base } from '$app/paths';
	import { Download, Send, Sparkles, X } from 'lucide-svelte';
	import { plainText, search, type SearchHit, type SearchIndex } from '$lib/viewer/searchIndex';
	import { composeAnswer } from '$lib/viewer/answerCompose';
	import { loadCompanyFinanceSignals } from '$lib/viewer/financeAsk';
	import { chatAnswer, warmEngine, webgpuUsable, type AskEvidence, type ChatTurn } from '$lib/viewer/webllm';
	import type { FinanceSignal } from '$lib/viewer/diff';
	import type { PanelBundle } from '$lib/viewer/types';

	let {
		code,
		bundle,
		searchIndex,
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

	interface EvRef { n: number; period: string; path: string; text: string }
	interface Turn {
		q: string;
		det: string;
		citedLabel: string | null;
		evItems: EvRef[];
		evHits: SearchHit[];
		ai: string;
		aiRunning: boolean;
		aiErr: string | null;
	}
	type ModelState = 'checking' | 'unsupported' | 'idle' | 'loading' | 'ready' | 'error';

	let question = $state('');
	let chat = $state<Turn[]>([]);
	let busy = $state(false);
	let finSignals = $state<FinanceSignal[]>([]);
	let modelState = $state<ModelState>('checking');
	let modelProgress = $state(0);
	let inputEl = $state<HTMLTextAreaElement | null>(null);
	let scrollEl = $state<HTMLElement | null>(null);

	$effect(() => {
		void webgpuUsable().then((v) => {
			if (modelState === 'checking') modelState = v ? 'idle' : 'unsupported';
		});
	});
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

	async function downloadModel() {
		if (modelState !== 'idle' && modelState !== 'error') return;
		modelState = 'loading';
		modelProgress = 0;
		try {
			await warmEngine((p) => (modelProgress = p.progress));
			modelState = 'ready';
		} catch {
			modelState = 'error';
		}
	}

	async function ask() {
		if (!searchIndex || !bundle || !question.trim() || busy) return;
		const q = question.trim();
		question = '';
		busy = true;

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
		const useAi = modelState === 'ready' && (evItems.length > 0 || composed.citedSignal != null);

		chat.push({ q, det: composed.answer, citedLabel: composed.citedSignal?.label ?? null, evItems, evHits, ai: '', aiRunning: useAi, aiErr: null });
		const idx = chat.length - 1;
		scrollBottom();

		if (!useAi) {
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
		let last = 0;
		try {
			await chatAnswer(history, payload, {
				onToken: (d) => {
					buf += d;
					const now = performance.now();
					if (now - last > 45) {
						chat[idx].ai = buf;
						last = now;
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
		<button type="button" class="ad-x" onclick={onclose} aria-label="닫기"><X size={15} /></button>
	</header>

	<div class="ad-scroll" bind:this={scrollEl}>
		{#if chat.length === 0}
			<div class="onboard">
				<picture>
					<source srcset="{base}/avatar.webp" type="image/webp" />
					<img class="onboard-ava" src="{base}/avatar.png" alt="" width="76" height="76" />
				</picture>
				{#if modelState === 'idle'}
					<button type="button" class="onboard-dl" onclick={downloadModel}><Download size={15} /> 대화 모델 받기</button>
					<span class="onboard-sub">~705MB · 1회 · 안 받아도 근거·답은 즉시</span>
				{:else if modelState === 'loading'}
					<div class="onboard-bar"><div class="bar-fill" style="width:{Math.round(modelProgress * 100)}%"></div><span class="bar-txt">받는 중 {Math.round(modelProgress * 100)}%</span></div>
				{:else if modelState === 'ready'}
					<span class="onboard-sub">무엇이든 물어보세요</span>
				{:else if modelState === 'error'}
					<button type="button" class="onboard-dl err" onclick={downloadModel}>로드 실패 · 다시</button>
				{:else if modelState === 'unsupported'}
					<span class="onboard-sub">이 브라우저는 대화 미지원 — 근거·결정론 답은 됩니다</span>
				{/if}
			</div>
		{/if}
		{#each chat as t, ti (ti)}
			<div class="msg user">{t.q}</div>
			<div class="msg bot">
				{#if t.ai}
					<p class="bot-text">{t.ai}</p>
					<div class="det-line">{t.det}</div>
				{:else}
					<p class="bot-text">{t.det}</p>
					{#if t.aiRunning}<div class="gen"><span class="dot"></span>생성 중…</div>{/if}
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

	<!-- 대화 중 모델 strip — 메시지 있고 아직 안 받았을 때만(중앙 온보딩과 중복 방지). ready 면 숨김. -->
	{#if chat.length > 0 && modelState === 'idle'}
		<button type="button" class="ad-model dl" onclick={downloadModel}>
			<Download size={14} /> 대화 모델 받기 <span class="sz">~705MB · 1회</span>
		</button>
	{:else if chat.length > 0 && modelState === 'loading'}
		<div class="ad-model bar">
			<div class="bar-fill" style="width:{Math.round(modelProgress * 100)}%"></div>
			<span class="bar-txt">대화 모델 받는 중 {Math.round(modelProgress * 100)}%</span>
		</div>
	{:else if chat.length > 0 && modelState === 'error'}
		<button type="button" class="ad-model dl err" onclick={downloadModel}>대화 모델 로드 실패 · 다시</button>
	{/if}

	<div class="ad-askbox">
		<textarea bind:this={inputEl} bind:value={question} rows="1" placeholder="공시에 대해 질문…" onkeydown={onKey}></textarea>
		<button type="button" class="ad-send" onclick={ask} disabled={!searchIndex || busy || !question.trim()} aria-label="질문">
			{#if busy}<Sparkles size={15} />{:else}<Send size={15} />{/if}
		</button>
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
		from { transform: translateX(24px); opacity: 0.4; }
		to { transform: translateX(0); opacity: 1; }
	}
	.ad-head {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px;
		border-bottom: 1px solid #1e2433;
		flex-shrink: 0;
	}
	.ad-head img { border-radius: 50%; }
	.ad-head strong { font-size: 13px; color: #f1f5f9; font-weight: 800; }
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
	.ad-x:hover { border-color: rgba(251, 146, 60, 0.5); color: #fb923c; }
	.ad-scroll {
		flex: 1 1 auto;
		min-height: 0;
		overflow-y: auto;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	.msg {
		font-size: 13px;
		line-height: 1.55;
		white-space: pre-wrap;
		word-break: break-word;
	}
	.msg.user {
		align-self: flex-end;
		max-width: 92%;
		padding: 8px 11px;
		border-radius: 12px 12px 3px 12px;
		background: rgba(251, 146, 60, 0.14);
		color: #fde7cf;
	}
	.msg.bot {
		align-self: stretch;
		padding: 10px 11px;
		border: 1px solid #1e2433;
		border-radius: 12px 12px 12px 3px;
		background: #0a0e18;
	}
	.bot-text { margin: 0; color: #e2e8f0; font-size: 13px; line-height: 1.6; }
	.det-line {
		margin-top: 7px;
		padding-top: 6px;
		border-top: 1px dashed #1e2433;
		color: #94a3b8;
		font-size: 11px;
		line-height: 1.5;
	}
	.gen { display: flex; align-items: center; gap: 7px; margin-top: 7px; color: #94a3b8; font-size: 11px; }
	.gen.err { color: #f87171; }
	.dot { width: 7px; height: 7px; border-radius: 50%; background: #38bdf8; animation: pulse 1s ease-in-out infinite; }
	@keyframes pulse { 50% { opacity: 0.3; } }
	.cite { margin-top: 6px; color: #fb923c; font-size: 11px; }
	.ev-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
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
	.ev-chip:hover { border-color: rgba(251, 146, 60, 0.55); color: #fb923c; }
	/* 중앙 온보딩 — 빈 대화 시 아바타 + 모델 받기 정중앙 */
	.onboard {
		margin: auto;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 12px;
		text-align: center;
		padding: 20px 12px;
	}
	.onboard-ava {
		border-radius: 50%;
	}
	.onboard-dl {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		padding: 9px 16px;
		border: 1px solid rgba(56, 189, 248, 0.5);
		border-radius: 10px;
		background: rgba(14, 165, 233, 0.1);
		color: #bae6fd;
		font: inherit;
		font-size: 13px;
		font-weight: 700;
		cursor: pointer;
	}
	.onboard-dl:hover {
		background: rgba(14, 165, 233, 0.2);
	}
	.onboard-dl.err {
		border-color: rgba(248, 113, 113, 0.5);
		color: #fca5a5;
		background: rgba(248, 113, 113, 0.08);
	}
	.onboard-sub {
		color: #64748b;
		font-size: 11px;
		line-height: 1.5;
	}
	.onboard-bar {
		position: relative;
		width: 200px;
		max-width: 80%;
		height: 30px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #0a0e18;
		overflow: hidden;
		display: grid;
		place-items: center;
	}
	/* model strip */
	.ad-model {
		flex-shrink: 0;
		margin: 0 12px 8px;
		font: inherit;
		font-size: 12px;
	}
	.ad-model.dl {
		display: inline-flex;
		align-items: center;
		gap: 7px;
		align-self: flex-start;
		padding: 8px 12px;
		border: 1px solid rgba(56, 189, 248, 0.5);
		border-radius: 8px;
		background: rgba(14, 165, 233, 0.1);
		color: #bae6fd;
		cursor: pointer;
	}
	.ad-model.dl:hover { background: rgba(14, 165, 233, 0.18); }
	.ad-model.dl .sz { color: #64748b; font-size: 10px; }
	.ad-model.dl.err { border-color: rgba(248, 113, 113, 0.5); color: #fca5a5; background: rgba(248, 113, 113, 0.08); }
	.ad-model.bar {
		position: relative;
		height: 28px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #0a0e18;
		overflow: hidden;
		display: grid;
		place-items: center;
	}
	.bar-fill { position: absolute; left: 0; top: 0; bottom: 0; background: rgba(56, 189, 248, 0.22); transition: width 0.2s; }
	.bar-txt { position: relative; color: #bae6fd; font-size: 11px; }
	.ad-askbox {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		flex-shrink: 0;
		padding: 0 12px 12px;
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
	.ad-askbox textarea:focus { border-color: #fb923c; }
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
	.ad-send:disabled { opacity: 0.45; cursor: default; }
</style>
