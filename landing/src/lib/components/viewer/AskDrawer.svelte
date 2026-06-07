<script lang="ts">
	// 본진 공시뷰어 우측 AI Q&A 채팅 드로어 — 헤더 아바타 버튼으로 열리고 격자를 밀고 나온다(push).
	// 모델은 명시적 [받기] 버튼+프로그래스바로 1회 다운로드(상태 가시화). 받기 전에도 결정론 답·근거는 즉시(다운로드 0).
	// 받은 뒤엔 질문하면 그 위에서 대화로 자동 응답(멀티턴). 근거 칩 → 부모 onSearchResult(셀 glow) 재사용.
	import { base } from '$app/paths';
	import { Download, Send, Sparkles, X } from 'lucide-svelte';
	import { plainText, search, type SearchHit, type SearchIndex } from '$lib/viewer/searchIndex';
	import { composeAnswer } from '$lib/viewer/answerCompose';
	import { resolveCompanies } from '$lib/viewer/companyNames';
	import { loadCompanyFinanceSignals } from '$lib/viewer/financeAsk';
	import { ask, type EvRef, type NavOption } from '$lib/viewer/askSession.svelte';
	import { routeChat, stripEcho, warmEngine, webgpuUsable, type AskEvidence, type ChatTurn, type Provider } from '$lib/viewer/webllm';
	import { detectOllama } from '$lib/viewer/ollama';
	import type { FinanceSignal } from '$lib/viewer/diff';
	import type { PanelBundle } from '$lib/viewer/types';

	// 로컬 Ollama 연결 안내(툴팁). origin 은 실배포처 고정(환각 URL 금지).
	const OLLAMA_TIP = `로컬 Ollama로 더 좋은 답변 (다운로드 없이 PC의 모델 사용)

1. 설치 — ollama.com 에서 받아 실행
2. 모델 받기 — 터미널에 입력
     ollama pull qwen2.5:3b   (한국어 강함: ollama pull exaone3.5:7.8b)
3. 이 사이트 허용 (한 번만) — 아래 1줄 실행 후 Ollama 재시작
     · Windows: setx OLLAMA_ORIGINS "https://eddmpython.github.io"
     · macOS: launchctl setenv OLLAMA_ORIGINS "https://eddmpython.github.io"
     · Linux: systemctl edit ollama.service → Environment="OLLAMA_ORIGINS=https://eddmpython.github.io"
4. "로컬 Ollama 연결" 클릭 → 브라우저가 "로컬 네트워크 접근 허용?"을 물으면 [허용]

연결되면 PC의 모델로 답합니다. 외부 전송 0, 모두 로컬.`;
	const OLLAMA_NO_MODEL = 'Ollama는 켜졌는데 설치된 모델이 없습니다. 터미널에 "ollama pull qwen2.5:3b" 후 다시 연결하세요.';
	const OLLAMA_BLOCKED =
		'로컬 Ollama에 연결하지 못했습니다. 설치·실행, 사이트 허용(OLLAMA_ORIGINS), 브라우저 "로컬 접근 허용"을 확인하세요(ⓘ). WebLLM으로 계속 쓸 수 있습니다.';

	let {
		code,
		bundle,
		searchIndex,
		corpName,
		carryQ = '',
		onfocus,
		onNavigate,
		onclose
	}: {
		code: string;
		bundle: PanelBundle | null;
		searchIndex: SearchIndex | null;
		indexing?: boolean;
		corpName: string;
		carryQ?: string; // 이동 후 부모가 운반한 질문(새 회사 index 준비되면 1회 자동 ask)
		onfocus: (hit: SearchHit) => void;
		onNavigate: (targetCode: string, carryQuestion: string) => void;
		onclose: () => void;
	} = $props();

	let question = $state('');
	let busy = $state(false);
	let finSignals = $state<FinanceSignal[]>([]);
	let modelProgress = $state(0);
	let inputEl = $state<HTMLTextAreaElement | null>(null);
	let scrollEl = $state<HTMLElement | null>(null);

	// 대화·모델·Ollama 상태는 askSession 모듈 스토어(ask) 에 둔다 — 회사 이동 시 viewer +page 가 bundle 을 잠시
	// null 로 만들어 AskDrawer 가 언마운트돼도 세션이 생존한다(크로스-회사 "AI 화면 그대로" 요구).
	const provider = $derived<Provider>(ask.ollamaState === 'ready' ? 'ollama' : 'webllm');

	$effect(() => {
		void webgpuUsable().then((v) => {
			if (ask.modelState === 'checking') ask.modelState = v ? 'idle' : 'unsupported';
		});
	});
	// [회귀가드] ask.chat·ollama 는 code 변경에 불간섭(크로스-회사 대화 유지 핵심). 여기에 ask.chat=[] 또는
	// {#key code} 추가 시 회사 이동마다 대화 소멸 — 절대 금지. finance prefetch 만 code 따라간다.
	$effect(() => {
		const c = code;
		finSignals = [];
		void loadCompanyFinanceSignals(c).then((s) => {
			if (code === c) finSignals = s; // 경쟁 가드: 도착 시점 code 일치할 때만
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
		if (ask.modelState !== 'idle' && ask.modelState !== 'error') return;
		ask.modelState = 'loading';
		modelProgress = 0;
		try {
			await warmEngine((p) => (modelProgress = p.progress));
			ask.modelState = 'ready';
		} catch {
			ask.modelState = 'error';
		}
	}

	// 사용자 제스처(클릭) 안에서만 — Chrome 142 LNA 팝업이 제스처 직후에만 의미 있게 뜬다($effect/마운트 호출 금지).
	async function connectOllama() {
		ask.ollamaState = 'probing';
		const s = await detectOllama();
		if (s.ok) {
			ask.ollamaState = 'ready';
			ask.ollamaModel = s.pick;
		} else if (s.reason === 'no-model') {
			ask.ollamaState = 'no-model';
		} else {
			ask.ollamaState = 'blocked'; // unreachable/cors/timeout 통합
		}
	}

	// 현재 회사(=code) 패널에서 grounded 답 — 결정론(즉시) + (모델 ready 면) 대화 스트리밍.
	// b/i 를 인자로 받아 이동 직후 stale 클로저를 피한다(항상 현재 reactive 값으로 호출). busy 해제 책임은 여기.
	async function answerOnCompany(q: string, b: PanelBundle, i: SearchIndex) {
		const { hits, added } = search(i, q, { topK: 6, expand: true });
		const evHits: SearchHit[] = [];
		const evItems: EvRef[] = [];
		let n = 1;
		for (const h of hits) {
			const cell = b.gridBySection.get(h.sectionKey)?.[h.rowIndex]?.cells?.[h.period] ?? '';
			const text = plainText(cell).slice(0, 700);
			if (!text) continue;
			evHits.push(h);
			evItems.push({ n: n++, period: h.period, path: [h.chapter, h.section, h.block].filter(Boolean).join(' > '), text, stale: h.stale });
		}
		const sigs = finSignals.length ? finSignals : await loadCompanyFinanceSignals(code);
		if (!finSignals.length && sigs.length) finSignals = sigs;
		const composed = composeAnswer(q, hits, added, sigs);
		const aiReady = provider === 'ollama' ? ask.ollamaState === 'ready' : ask.modelState === 'ready';
		const useAi = aiReady && (evItems.length > 0 || composed.citedSignal != null);

		ask.chat.push({
			q,
			companyName: corpName,
			nav: [],
			det: composed.answer,
			citedLabel: composed.citedSignal?.label ?? null,
			evItems,
			evHits,
			ai: '',
			aiRunning: useAi,
			aiErr: null
		});
		const idx = ask.chat.length - 1;
		scrollBottom();

		if (!useAi) {
			busy = false;
			return;
		}
		const history: ChatTurn[] = [];
		for (let k = 0; k < ask.chat.length; k++) {
			if (ask.chat[k].nav.length) continue; // 이동-칩 turn 은 history 제외
			// 회사 태그 프리픽스 — 이동 후 대명사/비교 맥락 유지("그럼 얘 매출은?" → 현재 회사 해석).
			history.push({ role: 'user', content: `[${ask.chat[k].companyName}] ${ask.chat[k].q}` });
			if (k !== idx) history.push({ role: 'assistant', content: ask.chat[k].ai || ask.chat[k].det });
		}
		const payload: AskEvidence[] = [
			{ n: 0, period: '', path: '결정론 분석(숫자 확정)', text: composed.answer },
			...evItems.map(({ n, period, path, text }) => ({ n, period, path, text }))
		];
		let buf = '';
		let last = 0;
		try {
			await routeChat(history, payload, {
				provider,
				ollamaModel: ask.ollamaModel ?? undefined,
				onToken: (d) => {
					buf += d;
					const now = performance.now();
					if (now - last > 45) {
						ask.chat[idx].ai = stripEcho(buf); // 약한 모델 parroting/마커 누출 제거
						last = now;
						scrollBottom();
					}
				}
			});
			ask.chat[idx].ai = stripEcho(buf);
		} catch (e) {
			ask.chat[idx].aiErr = e instanceof Error ? e.message : String(e);
			if (provider === 'ollama') ask.ollamaState = 'blocked'; // 도중 사망 → 다음 질문 자동 WebLLM 강등
		} finally {
			ask.chat[idx].aiRunning = false;
			busy = false;
			scrollBottom();
		}
	}

	async function submitQuestion() {
		if (!searchIndex || !bundle || !question.trim() || busy) return;
		const q = question.trim();
		question = '';
		busy = true;

		// 0) 결정론 회사 감지(검색 전). 없는 회사·현재 회사·모호 0 → [] → 현재 회사로 정상 답.
		const targets = await resolveCompanies(q, code);
		if (targets.length === 0) {
			await answerOnCompany(q, bundle, searchIndex);
			return;
		}

		// 타 회사 감지(단일·모호 공통) → 답 안 함. 이동 칩 turn push 후 종료(클릭 시 이동+원질문 자동 답).
		const det =
			targets.length === 1
				? `질문에서 '${targets[0].name}'을(를) 봤어요. 이 뷰어는 한 번에 한 회사예요.`
				: `'${q}'에 여러 회사가 보여요. 어디로 갈까요?`;
		ask.chat.push({
			q,
			companyName: corpName,
			nav: targets,
			det,
			citedLabel: null,
			evItems: [],
			evHits: [],
			ai: '',
			aiRunning: false,
			aiErr: null
		});
		scrollBottom();
		busy = false;
	}

	// 이동 칩 클릭 — 부모로 위임(goto + 원질문 운반). 부모가 새 회사 로드 후 carryQ 로 자동 재실행.
	function clickNav(target: NavOption, carryQuestion: string) {
		onNavigate(target.code, carryQuestion);
	}

	// 이동 후 운반된 질문 1회 자동 실행 — carryQ + 새 회사 bundle/index 가 모두 reactive prop 이라,
	// "새 회사 인덱스 준비됨"을 effect 가 자연 감지해 1회 ask. ask.consumedCarry(스토어) 가드로 재실행 방지
	// — 재마운트에도 생존해 수동 종목검색 후 묵은 carryQ 재발화를 막는다.
	$effect(() => {
		const cq = carryQ;
		if (!cq || cq === ask.consumedCarry) return;
		if (!searchIndex || !bundle || !bundle.periods.length) return; // 새 회사 데이터 준비 대기(헛답 방지)
		ask.consumedCarry = cq;
		busy = true;
		void answerOnCompany(cq, bundle, searchIndex); // 이동된 회사(=현재 code)로 답
	});

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
			e.preventDefault();
			void submitQuestion();
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
		{#if ask.ollamaState === 'ready'}<span class="hd-badge" title="로컬 Ollama 사용 중 · 외부 전송 없음">Ollama · {ask.ollamaModel}</span>{/if}
		<button type="button" class="ad-x" onclick={onclose} aria-label="닫기"><X size={15} /></button>
	</header>

	<div class="ad-scroll" bind:this={scrollEl}>
		{#if ask.chat.length === 0}
			<div class="onboard">
				<picture>
					<source srcset="{base}/avatar.webp" type="image/webp" />
					<img class="onboard-ava" src="{base}/avatar.png" alt="" width="76" height="76" />
				</picture>
				{#if ask.modelState === 'idle'}
					<button type="button" class="onboard-dl" onclick={downloadModel}><Download size={15} /> 대화 모델 받기</button>
					<span class="onboard-sub">~705MB · 1회 · 안 받아도 근거·답은 즉시</span>
				{:else if ask.modelState === 'loading'}
					<div class="onboard-bar"><div class="bar-fill" style="width:{Math.round(modelProgress * 100)}%"></div><span class="bar-txt">받는 중 {Math.round(modelProgress * 100)}%</span></div>
				{:else if ask.modelState === 'ready'}
					<span class="onboard-sub">무엇이든 물어보세요</span>
				{:else if ask.modelState === 'error'}
					<button type="button" class="onboard-dl err" onclick={downloadModel}>로드 실패 · 다시</button>
				{:else if ask.modelState === 'unsupported'}
					<span class="onboard-sub">이 브라우저는 대화 미지원 — 근거·결정론 답은 됩니다</span>
				{/if}

				<!-- 로컬 Ollama 옵션 레인 (더 좋은 품질·버벅임0). 자동 프로브 금지 — 클릭 시만. -->
				{#if ask.ollamaState === 'hidden'}
					<button type="button" class="ollama-link" onclick={connectOllama}>
						더 좋은 품질? 로컬 Ollama 연결
						<span class="info" tabindex="0" role="button" aria-label="Ollama 연결 안내">ⓘ<span class="tip">{OLLAMA_TIP}</span></span>
					</button>
				{:else if ask.ollamaState === 'probing'}
					<span class="onboard-sub">Ollama 찾는 중…</span>
				{:else if ask.ollamaState === 'ready'}
					<span class="ollama-on">● Ollama 연결됨 · {ask.ollamaModel}</span>
				{:else if ask.ollamaState === 'no-model'}
					<span class="ollama-warn">{OLLAMA_NO_MODEL} <button type="button" class="retry" onclick={connectOllama}>다시</button></span>
				{:else if ask.ollamaState === 'blocked'}
					<span class="ollama-warn">{OLLAMA_BLOCKED} <button type="button" class="retry" onclick={connectOllama}>다시</button></span>
				{/if}
			</div>
		{/if}
		{#each ask.chat as t, ti (ti)}
			{#if t.nav.length === 0 && ti > 0 && t.companyName !== ask.chat[ti - 1].companyName}
				<div class="co-divider">──── {t.companyName} ────</div>
			{/if}
			<div class="msg user">{t.q}</div>
			<div class="msg bot">
				{#if t.nav.length === 0 && (ti === 0 || t.companyName !== ask.chat[ti - 1].companyName) && t.companyName}
					<span class="co-badge">{t.companyName}</span>
				{/if}
				{#if t.nav.length}
					<!-- 이동 칩 turn — 답 대신 안내 + 칩(클릭 시 이동·원질문 자동 답) -->
					<p class="bot-text">{t.det}</p>
					<div class="ev-row">
						{#each t.nav as opt (opt.code)}
							<button type="button" class="nav-chip" onclick={() => clickNav(opt, t.q)}>→ {opt.name}({opt.code})로 이동해서 답하기</button>
						{/each}
					</div>
				{:else}
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
								<button type="button" class="ev-chip" class:stale={e.stale} onclick={() => onfocus(t.evHits[i])} title={e.stale ? `${e.path} · 이 항목의 최근 언급은 과거 시점입니다` : e.path}>근거 {e.n} · {e.period}{#if e.stale} <span class="stale-tag">과거</span>{/if}</button>
							{/each}
						</div>
					{/if}
				{/if}
			</div>
		{/each}
	</div>

	<!-- 대화 중 모델 strip — 메시지 있고 아직 안 받았을 때만(중앙 온보딩과 중복 방지). ready 면 숨김. -->
	{#if ask.chat.length > 0 && ask.modelState === 'idle' && ask.ollamaState !== 'ready'}
		<button type="button" class="ad-model dl" onclick={downloadModel}>
			<Download size={14} /> 대화 모델 받기 <span class="sz">~705MB · 1회</span>
		</button>
	{:else if ask.chat.length > 0 && ask.modelState === 'loading'}
		<div class="ad-model bar">
			<div class="bar-fill" style="width:{Math.round(modelProgress * 100)}%"></div>
			<span class="bar-txt">대화 모델 받는 중 {Math.round(modelProgress * 100)}%</span>
		</div>
	{:else if ask.chat.length > 0 && ask.modelState === 'error'}
		<button type="button" class="ad-model dl err" onclick={downloadModel}>대화 모델 로드 실패 · 다시</button>
	{/if}

	<div class="ad-askbox">
		<textarea bind:this={inputEl} bind:value={question} rows="1" placeholder="공시에 대해 질문…" onkeydown={onKey}></textarea>
		<button type="button" class="ad-send" onclick={submitQuestion} disabled={!searchIndex || busy || !question.trim()} aria-label="질문">
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
	.ev-chip.stale { border-style: dashed; }
	.stale-tag {
		margin-left: 3px;
		padding: 0 4px;
		border-radius: 6px;
		background: rgba(148, 163, 184, 0.16);
		color: #94a3b8;
		font-size: 9px;
	}
	/* 크로스-회사 이동 — 전환 divider + 회사 배지 + 이동 칩 */
	.co-divider {
		align-self: stretch;
		text-align: center;
		margin: 6px 0 2px;
		color: #475569;
		font-size: 10.5px;
		letter-spacing: 0.04em;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.co-badge {
		display: inline-block;
		margin-bottom: 6px;
		padding: 1px 7px;
		border: 1px solid #1e2433;
		border-radius: 999px;
		background: #050811;
		color: #64748b;
		font-size: 10px;
	}
	.nav-chip {
		max-width: 100%;
		padding: 5px 10px;
		border: 1px solid rgba(251, 146, 60, 0.55);
		border-radius: 999px;
		background: rgba(251, 146, 60, 0.1);
		color: #fb923c;
		font: inherit;
		font-size: 11px;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.nav-chip:hover { background: rgba(251, 146, 60, 0.2); }
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

	/* Ollama 옵션 레인 — 기존 팔레트 재사용(새 색 없음). ready 만 초록, 나머지 muted/warn. */
	.ollama-link {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 0;
		border: none;
		background: transparent;
		color: #64748b;
		font: inherit;
		font-size: 11px;
		cursor: pointer;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.ollama-link:hover { color: #fb923c; }
	.ollama-on { display: inline-flex; align-items: center; gap: 5px; color: #34d399; font-size: 11px; }
	.ollama-warn { color: #94a3b8; font-size: 11px; line-height: 1.5; max-width: 240px; text-align: center; }
	.retry {
		margin-left: 4px;
		padding: 2px 7px;
		border: 1px solid #1e2433;
		border-radius: 6px;
		background: #0a0e18;
		color: #bae6fd;
		font: inherit;
		font-size: 10px;
		cursor: pointer;
	}
	.retry:hover { border-color: rgba(251, 146, 60, 0.5); color: #fb923c; }
	.hd-badge {
		padding: 2px 8px;
		border: 1px solid rgba(52, 211, 153, 0.4);
		border-radius: 999px;
		background: rgba(52, 211, 153, 0.08);
		color: #34d399;
		font-size: 10px;
		font-weight: 700;
	}
	.info {
		position: relative;
		display: inline-grid;
		place-items: center;
		width: 15px;
		height: 15px;
		border-radius: 50%;
		border: 1px solid #1e2433;
		color: #64748b;
		font-size: 9px;
		cursor: help;
	}
	.info:hover, .info:focus-within { color: #fb923c; border-color: rgba(251, 146, 60, 0.5); }
	.info .tip {
		display: none;
		position: absolute;
		bottom: calc(100% + 8px);
		left: 50%;
		transform: translateX(-50%);
		z-index: 20;
		width: 280px;
		max-width: 78vw;
		padding: 10px 12px;
		border: 1px solid #1e2433;
		border-radius: 8px;
		background: #0a0e18;
		color: #cbd5e1;
		font-size: 11px;
		line-height: 1.6;
		white-space: pre-wrap;
		text-align: left;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
	}
	.info:hover .tip, .info:focus-within .tip { display: block; }
</style>
