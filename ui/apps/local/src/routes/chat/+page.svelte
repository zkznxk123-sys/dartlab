<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { base } from '$app/paths';
	import { getLocalRuntime } from '$lib/runtime/localRuntime';
	import { ChatSession } from '$lib/chat/chatSession.svelte';

	// 챗 모드 — AiPort.streamAsk(mode:'chat') 한 포트로 대화. 터미널 모드와 같은 Ask engine 계약 공유(단계-7).
	const runtime = getLocalRuntime();
	const session = new ChatSession(runtime.ai);

	let draft = $state('');
	let composing = $state(false);
	let scroller: HTMLDivElement | null = $state(null);

	const tierLabel: Record<string, string> = {
		advanced: '고급 엔진',
		onDevice: '온디바이스',
		deterministic: '결정론',
		none: '비활성'
	};

	const examples = [
		'005930 회사 개요를 알려줘',
		'최근 분기 매출이 늘어난 코스피 회사는?',
		'반도체 업종 주요 회사를 비교해줘'
	];

	onMount(() => {
		void session.loadCapabilities();
	});

	// 스트리밍·새 메시지마다 하단 고정. 마지막 메시지 텍스트 길이를 의존성으로 추적(델타 누적 반응).
	$effect(() => {
		session.messages.length;
		session.messages.at(-1)?.text;
		session.messages.at(-1)?.activities.length;
		if (scroller) {
			void tick().then(() => {
				if (scroller) scroller.scrollTop = scroller.scrollHeight;
			});
		}
	});

	async function submit() {
		const text = draft.trim();
		if (!text || session.busy) return;
		draft = '';
		await session.send(text);
	}

	function onKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !composing) {
			e.preventDefault();
			void submit();
		}
	}

	function ask(prompt: string) {
		draft = prompt;
		void submit();
	}

	const hasCode = $derived(/^\d{6}$/.test(session.code.trim()));
</script>

<svelte:head>
	<title>챗 — dartlab local</title>
</svelte:head>

<div class="chat">
	<header>
		<a class="back" href={base || '/'}>← local</a>
		<div class="title">
			<h1>챗</h1>
			{#if session.capabilitiesLoaded}
				<span class="tier" class:adv={session.capabilities?.tier === 'advanced'}>
					{tierLabel[session.capabilities?.tier ?? 'none'] ?? '비활성'}
				</span>
			{/if}
		</div>
		<div class="ctx">
			<input
				class="code"
				bind:value={session.code}
				placeholder="종목 컨텍스트 (선택, 6자리)"
				inputmode="numeric"
				maxlength="6"
				aria-label="종목 컨텍스트 코드"
			/>
			{#if hasCode}
				<a class="goterm" href={`${base}/terminal/${session.code.trim()}`}>터미널 →</a>
			{/if}
		</div>
	</header>

	{#if session.capabilities?.upgradeHint}
		<div class="hint">{session.capabilities.upgradeHint}</div>
	{/if}

	<div class="stream" bind:this={scroller}>
		{#if session.messages.length === 0}
			<div class="empty">
				<p class="lead">DartLab 챗 — 회사·재무·시장을 질문하세요.</p>
				<p class="note">근거 기반 Ask 엔진이 답하고, 사용한 출처를 함께 표시합니다.</p>
				<div class="examples">
					{#each examples as ex (ex)}
						<button class="ex" onclick={() => ask(ex)}>{ex}</button>
					{/each}
				</div>
			</div>
		{/if}

		{#each session.messages as m (m.id)}
			<div class="msg" class:user={m.role === 'user'} class:assistant={m.role === 'assistant'}>
				{#if m.role === 'assistant' && m.activities.length}
					<div class="acts">
						{#each m.activities as a (a.id)}
							<span class="act" class:running={a.status === 'running'}>
								{a.status === 'running' ? '⋯' : '✓'} {a.summary}
							</span>
						{/each}
					</div>
				{/if}

				{#if m.text}
					<div class="bubble">{m.text}{#if m.streaming}<span class="caret"></span>{/if}</div>
				{:else if m.role === 'assistant' && m.streaming && !m.error}
					<div class="bubble thinking"><span class="caret"></span></div>
				{/if}

				{#if m.error}
					<div class="err">응답 오류: {m.error}</div>
				{/if}

				{#if m.refs.length}
					<div class="refs">
						{#each m.refs as r (r.id)}
							<span class="ref" title={`${r.kind} · ${r.source}`}>{r.title || r.kind}</span>
						{/each}
					</div>
				{/if}

				{#if m.suggested.length}
					<div class="suggest">
						{#each m.suggested as s (s)}
							<button class="sug" onclick={() => ask(s)} disabled={session.busy}>{s}</button>
						{/each}
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<form class="composer" onsubmit={(e) => { e.preventDefault(); void submit(); }}>
		<textarea
			bind:value={draft}
			onkeydown={onKeydown}
			oncompositionstart={() => (composing = true)}
			oncompositionend={() => (composing = false)}
			placeholder={hasCode ? `${session.code.trim()} 에 대해 질문…` : '질문을 입력하세요…  (Enter 전송 · Shift+Enter 줄바꿈)'}
			rows="1"
			disabled={session.busy}
		></textarea>
		<button type="submit" disabled={session.busy || !draft.trim()}>
			{session.busy ? '…' : '전송'}
		</button>
	</form>
</div>

<style>
	.chat {
		display: flex;
		flex-direction: column;
		height: 100vh;
		max-width: 860px;
		margin: 0 auto;
		padding: 0 1rem;
	}
	header {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 0 0.75rem;
		border-bottom: 1px solid var(--dl-bd, #2a2c33);
	}
	.back {
		color: var(--dl-ink-dim, #9aa0aa);
		text-decoration: none;
		font-size: 0.85rem;
	}
	.title {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
	}
	h1 {
		font-size: 1.25rem;
		margin: 0;
	}
	.tier {
		font-size: 0.7rem;
		padding: 0.1rem 0.45rem;
		border-radius: 999px;
		border: 1px solid var(--dl-bd, #2a2c33);
		color: var(--dl-ink-mute, #6b7280);
	}
	.tier.adv {
		color: var(--dl-accent, #ff5a36);
		border-color: var(--dl-accent, #ff5a36);
	}
	.ctx {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.code {
		width: 11rem;
		padding: 0.35rem 0.6rem;
		border: 1px solid var(--dl-bd, #2a2c33);
		border-radius: 6px;
		background: var(--dl-bg-raised, #16171a);
		color: var(--dl-ink, #e7e7ea);
		font-family: var(--dl-font-mono, ui-monospace, monospace);
		font-size: 0.8rem;
	}
	.goterm {
		font-size: 0.78rem;
		color: var(--dl-info, #6ab0ff);
		text-decoration: none;
		white-space: nowrap;
	}
	.hint {
		font-size: 0.78rem;
		color: var(--dl-ink-mute, #6b7280);
		padding: 0.5rem 0;
	}
	.stream {
		flex: 1;
		overflow-y: auto;
		padding: 1.25rem 0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.empty {
		margin: auto 0;
		text-align: center;
		color: var(--dl-ink-dim, #9aa0aa);
	}
	.empty .lead {
		font-size: 1.05rem;
		color: var(--dl-ink, #e7e7ea);
		margin: 0 0 0.3rem;
	}
	.empty .note {
		font-size: 0.85rem;
		margin: 0 0 1.5rem;
	}
	.examples {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		align-items: center;
	}
	.ex {
		padding: 0.5rem 0.9rem;
		border: 1px solid var(--dl-bd, #2a2c33);
		border-radius: 999px;
		background: var(--dl-bg-raised, #16171a);
		color: var(--dl-ink-dim, #9aa0aa);
		cursor: pointer;
		font-size: 0.82rem;
	}
	.ex:hover {
		border-color: var(--dl-accent, #ff5a36);
		color: var(--dl-ink, #e7e7ea);
	}
	.msg {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		max-width: 88%;
	}
	.msg.user {
		align-self: flex-end;
		align-items: flex-end;
	}
	.msg.assistant {
		align-self: flex-start;
	}
	.bubble {
		padding: 0.65rem 0.9rem;
		border-radius: 12px;
		white-space: pre-wrap;
		word-break: break-word;
		line-height: 1.55;
		font-size: 0.92rem;
	}
	.user .bubble {
		background: var(--dl-accent, #ff5a36);
		color: #fff;
	}
	.assistant .bubble {
		background: var(--dl-bg-raised, #16171a);
		border: 1px solid var(--dl-bd, #2a2c33);
		color: var(--dl-ink, #e7e7ea);
	}
	.thinking {
		min-height: 1.2rem;
	}
	.caret {
		display: inline-block;
		width: 0.5rem;
		height: 1rem;
		margin-left: 1px;
		vertical-align: text-bottom;
		background: currentColor;
		opacity: 0.6;
		animation: blink 1s step-start infinite;
	}
	@keyframes blink {
		50% {
			opacity: 0;
		}
	}
	.acts {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	.act {
		font-size: 0.72rem;
		padding: 0.15rem 0.5rem;
		border-radius: 6px;
		background: var(--dl-bg-raised, #16171a);
		border: 1px solid var(--dl-bd, #2a2c33);
		color: var(--dl-ink-mute, #6b7280);
		font-family: var(--dl-font-mono, ui-monospace, monospace);
	}
	.act.running {
		color: var(--dl-info, #6ab0ff);
	}
	.err {
		font-size: 0.82rem;
		color: var(--dl-bad, #ff6b6b);
	}
	.refs {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	.ref {
		font-size: 0.72rem;
		padding: 0.15rem 0.5rem;
		border-radius: 6px;
		background: transparent;
		border: 1px solid var(--dl-bd, #2a2c33);
		color: var(--dl-ink-dim, #9aa0aa);
		cursor: default;
	}
	.suggest {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		margin-top: 0.2rem;
	}
	.sug {
		font-size: 0.78rem;
		padding: 0.3rem 0.7rem;
		border-radius: 999px;
		background: transparent;
		border: 1px dashed var(--dl-bd, #2a2c33);
		color: var(--dl-info, #6ab0ff);
		cursor: pointer;
	}
	.sug:hover:not(:disabled) {
		border-style: solid;
	}
	.sug:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.composer {
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem 0 1rem;
		border-top: 1px solid var(--dl-bd, #2a2c33);
	}
	textarea {
		flex: 1;
		resize: none;
		max-height: 8rem;
		padding: 0.6rem 0.8rem;
		border: 1px solid var(--dl-bd, #2a2c33);
		border-radius: 10px;
		background: var(--dl-bg-raised, #16171a);
		color: var(--dl-ink, #e7e7ea);
		font: inherit;
		line-height: 1.5;
	}
	textarea:focus {
		outline: none;
		border-color: var(--dl-accent, #ff5a36);
	}
	.composer button {
		padding: 0 1.2rem;
		border: 1px solid var(--dl-accent, #ff5a36);
		border-radius: 10px;
		background: var(--dl-accent, #ff5a36);
		color: #fff;
		cursor: pointer;
		font-weight: 600;
	}
	.composer button:disabled {
		opacity: 0.45;
		cursor: default;
	}
</style>
