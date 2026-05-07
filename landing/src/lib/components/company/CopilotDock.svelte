<script lang="ts">
	/**
	 * /company/[stockCode] 우측 인라인 Copilot dock.
	 *
	 * 사용자가 ChartRenderer 의 datapoint 또는 KpiRibbon 카드를 클릭하면
	 * `setContext({sectionId?, chartId?, accountKey?, valueRef?, period?, rcept_no?})`
	 * 가 호출되어 다음 질문에 evidence selection 컨텍스트가 자동 주입된다.
	 *
	 * SSE 응답은 `/api/company/{stockCode}/copilot` 의 chunked event 를 라인 단위로
	 * append. citation 클릭은 EvidencePanel 으로 dispatch (onOpenEvidence prop).
	 */

	export interface CopilotContext {
		sectionId?: string;
		chartId?: string;
		accountKey?: string;
		valueRef?: string;
		period?: string;
		rcept_no?: string;
	}

	export interface CopilotMessage {
		role: 'user' | 'assistant';
		text: string;
		ts: number;
	}

	let {
		stockCode,
		onOpenEvidence
	}: {
		stockCode: string;
		onOpenEvidence?: (ref: { valueRef?: string; rcept_no?: string }) => void;
	} = $props();

	let question = $state('');
	let context = $state<CopilotContext>({});
	let messages = $state<CopilotMessage[]>([]);
	let busy = $state(false);
	let abortCtrl: AbortController | null = null;

	export function setContext(next: CopilotContext) {
		context = { ...context, ...next };
	}

	function clearContext() {
		context = {};
	}

	async function send() {
		const q = question.trim();
		if (!q || busy) return;
		busy = true;
		question = '';
		messages = [...messages, { role: 'user', text: q, ts: Date.now() }];
		messages = [...messages, { role: 'assistant', text: '', ts: Date.now() }];
		const lastIdx = messages.length - 1;

		abortCtrl?.abort();
		abortCtrl = new AbortController();
		try {
			const resp = await fetch(`/api/company/${stockCode}/copilot`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
				body: JSON.stringify({ question: q, ...context, stream: true }),
				signal: abortCtrl.signal
			});
			if (!resp.ok || !resp.body) {
				messages[lastIdx].text = `[copilot] HTTP ${resp.status}. /api 서버 미가동 가능성.`;
				busy = false;
				return;
			}
			const reader = resp.body.getReader();
			const decoder = new TextDecoder();
			let buf = '';
			for (;;) {
				const { value, done } = await reader.read();
				if (done) break;
				buf += decoder.decode(value, { stream: true });
				// SSE: parse `data: ...` lines, ignore comments and other event names.
				const lines = buf.split('\n');
				buf = lines.pop() ?? '';
				for (const line of lines) {
					if (line.startsWith('data:')) {
						const payload = line.slice(5).trim();
						if (payload && payload !== '[DONE]') {
							messages[lastIdx].text += extractText(payload);
							messages = [...messages];
						}
					}
				}
			}
		} catch (err) {
			messages[lastIdx].text += `\n[copilot 오류] ${err instanceof Error ? err.message : String(err)}`;
		} finally {
			busy = false;
		}
	}

	function extractText(payload: string): string {
		// agent_gateway SSE chunk 가 JSON 객체로 올 수도 plain text 일 수도. 안전하게 처리.
		try {
			const obj = JSON.parse(payload);
			if (typeof obj === 'string') return obj;
			if (typeof obj.text === 'string') return obj.text;
			if (typeof obj.delta === 'string') return obj.delta;
			if (typeof obj.content === 'string') return obj.content;
			return '';
		} catch {
			return payload;
		}
	}

	function onCtxChip() {
		if (typeof onOpenEvidence === 'function' && (context.valueRef || context.rcept_no)) {
			onOpenEvidence({ valueRef: context.valueRef, rcept_no: context.rcept_no });
		}
	}
</script>

<aside class="copilot-dock" aria-label="AI Copilot">
	<header>
		<small>AI Copilot</small>
		<h3>{stockCode}</h3>
	</header>

	{#if context.valueRef || context.chartId || context.accountKey}
		<button class="ctx-chip" type="button" onclick={onCtxChip}>
			<span>selection</span>
			<small>{context.chartId ?? context.accountKey ?? context.valueRef ?? ''}</small>
			<i onclick={(e) => { e.stopPropagation(); clearContext(); }}>×</i>
		</button>
	{/if}

	<div class="messages" aria-live="polite">
		{#if !messages.length}
			<p class="hint">차트/표를 클릭한 뒤 질문하면 그 selection 이 컨텍스트로 주입됩니다.</p>
		{/if}
		{#each messages as msg}
			<article class={msg.role}>
				<small>{msg.role === 'user' ? '나' : 'AI'}</small>
				<p>{msg.text}</p>
			</article>
		{/each}
	</div>

	<form
		onsubmit={(e) => {
			e.preventDefault();
			void send();
		}}
	>
		<textarea
			bind:value={question}
			placeholder={busy ? '대기...' : '예: 영업이익 감소의 핵심 원인은?'}
			rows="2"
			disabled={busy}
			onkeydown={(e) => {
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					void send();
				}
			}}
		></textarea>
		<button type="submit" disabled={busy || !question.trim()}>
			{busy ? '...' : '질문'}
		</button>
	</form>
</aside>

<style>
	.copilot-dock {
		position: sticky;
		top: 12px;
		display: grid;
		gap: 10px;
		max-height: calc(100vh - 80px);
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: rgba(8, 13, 23, 0.96);
		padding: 13px;
		color: #f8fafc;
	}
	header small {
		color: #fb923c;
		font-size: 10px;
		font-weight: 800;
		letter-spacing: 0.04em;
		text-transform: uppercase;
	}
	header h3 {
		margin: 4px 0 0;
		font-size: 14px;
		font-weight: 700;
	}
	.ctx-chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		border: 1px solid #fb923c;
		border-radius: 14px;
		background: rgba(251, 146, 60, 0.08);
		color: #fb923c;
		padding: 5px 10px;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
		text-align: left;
		justify-self: start;
	}
	.ctx-chip span {
		font-weight: 700;
	}
	.ctx-chip small {
		color: #fde68a;
		font-size: 10px;
	}
	.ctx-chip i {
		display: grid;
		place-items: center;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: rgba(251, 146, 60, 0.18);
		color: #fb923c;
		font-style: normal;
		font-size: 11px;
	}
	.messages {
		flex: 1 1 auto;
		overflow-y: auto;
		display: grid;
		gap: 8px;
		max-height: 360px;
	}
	.hint {
		margin: 0;
		color: #64748b;
		font-size: 11px;
		line-height: 1.5;
	}
	article {
		border: 1px solid #263145;
		border-radius: 6px;
		background: #060b13;
		padding: 8px 10px;
	}
	article small {
		color: #94a3b8;
		font-size: 10px;
		font-weight: 700;
	}
	article.user small {
		color: #60a5fa;
	}
	article.assistant small {
		color: #fb923c;
	}
	article p {
		margin: 4px 0 0;
		font-size: 12px;
		line-height: 1.5;
		color: #f1f5f9;
		white-space: pre-wrap;
		word-break: break-word;
	}
	form {
		display: grid;
		gap: 6px;
	}
	textarea {
		border: 1px solid #263145;
		border-radius: 5px;
		background: #050811;
		color: #f8fafc;
		font: inherit;
		font-size: 12px;
		padding: 7px 9px;
		resize: vertical;
	}
	textarea:focus {
		outline: 1px solid #fb923c;
	}
	button[type='submit'] {
		border: 1px solid #fb923c;
		border-radius: 5px;
		background: rgba(251, 146, 60, 0.12);
		color: #fb923c;
		font: inherit;
		font-weight: 700;
		font-size: 12px;
		padding: 7px 9px;
		cursor: pointer;
	}
	button[type='submit']:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
