<script lang="ts">
	import { onMount } from 'svelte';

	interface Step {
		selector?: string;
		title: string;
		// 본문 단락 배열 — 각각 한 문단
		body: string[];
		// 핵심 가치 한 줄 (왜 유용한지)
		why?: string;
		// "직접 해보기" 데모 (옵션)
		demo?: { label: string; run: () => void | Promise<void> };
	}

	interface Props {
		open: boolean;
		onClose: () => void;
		colorMetric: string;
		viewMode: string;
		enterIndustryAction: (id: string) => void | Promise<void>;
		selectCompanyAction: (stockCode: string) => void | Promise<void>;
		addCompareAction: (stockCode: string) => void | Promise<void>;
		clearSelectionAction: () => void;
	}

	let {
		open,
		onClose,
		colorMetric = $bindable(),
		viewMode = $bindable(),
		enterIndustryAction,
		selectCompanyAction,
		addCompareAction,
		clearSelectionAction
	}: Props = $props();

	let stepIdx = $state(0);
	let highlight = $state<{ x: number; y: number; w: number; h: number } | null>(null);
	// 퀵투어(3스텝) vs 풀투어(12스텝)
	const QUICK_COUNT = 3;
	let fullMode = $state(false);

	const STEPS: Step[] = [
		{
			title: '산업지도에 오신 걸 환영합니다',
			body: [
				'한국 상장사 2,664사 · 34개 산업 · 공급망 18,418 관계를 한 화면에서 분석하는 도구입니다.',
				'이 투어는 "무엇을 클릭하면 무엇이 보이는지" 를 **실제로 보여드립니다.** 단순한 설명이 아니라 화면이 같이 바뀝니다.',
				'좌우 화살표 키 · Enter / Esc 또는 아래 버튼으로 진행. 각 스텝의 **"▶ 실제로 해보기"** 버튼이 있으면 꼭 눌러보세요.'
			],
			why: '5분이면 이 지도의 전부를 쓸 줄 알게 됩니다.'
		},
		{
			selector: '.brand-bar',
			title: '1 / 12  ·  좌측 상단 — 빠른 액션 바',
			body: [
				'이 작은 아이콘들이 자주 쓰는 액션입니다.',
				'• **아바타** — 언제든 dartlab 홈 랜딩으로 복귀\n• **GitHub** — 전체 소스·이슈 트래커\n• **커피 컵** — 후원 (오픈소스 유지에 도움)\n• **?** — 지금 보고 있는 이 투어를 다시 시작'
			],
			why: '투어는 ? 버튼으로 언제든 재실행 가능 — 기능 추가될 때마다 다시 돌려 보세요.'
		},
		{
			selector: '.color-switch',
			title: '2 / 12  ·  색상 기준 — 이 지도의 핵심',
			body: [
				'**이 하나의 셀렉터가 지도 전체의 색을 바꿉니다.** 단순히 산업별 색상만 있는 게 아니라, 재무 지표 기반 스코어를 색으로 투사합니다.',
				'기본 "산업 팔레트" 는 34개 산업 고유 색 — 어디가 무슨 산업인지 구분용.',
				'**ROE 로 바꾸면** 산업 내에서 누가 주주 돈을 잘 굴리는지 빨강→초록 그라디언트로 즉시 드러납니다. 산업 전체에 적용되므로 한눈에 우량/부진이 보여요.',
				'지금 직접 눌러 보세요 — 화면 전체 색이 바뀌는 게 보입니다.'
			],
			why: '"어느 산업·어느 회사가 우량한가" 에 1초 안에 답하는 도구입니다.',
			demo: {
				label: '▶ ROE 로 바꿔보기 (화면 색 변화)',
				run: () => {
					colorMetric = 'roe';
				}
			}
		},
		{
			selector: '.color-switch',
			title: '3 / 12  ·  다른 관점 — 성장률',
			body: [
				'ROE는 수익성. 그런데 "돈 안 벌어도 커지는 회사" 는 CAGR 로 보여야 합니다.',
				'**매출 CAGR 3년** 으로 바꾸면 고성장 기업(바이오·IT) 이 초록으로, 정체·역성장 기업이 빨강으로 바뀝니다.',
				'다른 옵션:\n• **영업이익률** — 본업 마진 경쟁력\n• **부채비율** — 재무 건전성 (역방향: 낮을수록 초록)\n• **매출 규모** — 대기업 vs 중소 구분',
				'5개 관점으로 같은 지도를 5가지 다른 질문에 활용 가능합니다.'
			],
			why: '한 화면에서 관점만 바꾸면 5개의 서로 다른 분석이 됩니다.',
			demo: {
				label: '▶ 매출 CAGR 로 바꾸기',
				run: () => {
					colorMetric = 'revCagr';
				}
			}
		},
		{
			selector: '.view-switch',
			title: '4 / 12  ·  관점 3종 — 산업 / 전회사 / 드릴다운',
			body: [
				'같은 데이터를 세 가지 배율로 봅니다.',
				'• **산업 지도** (기본) — 34개 버블. 거시적 탐색, 공급 플로우 파악.\n• **전 회사** — 2,664사 전부를 한 그래프에. 밀도 높아 필터링 필요.\n• **산업 내부** — 산업 하나만 열어 공정별 클러스터링. 중범위 분석의 주력.',
				'지금 "전 회사" 뷰로 이동해 밀도를 확인하고, 다시 산업 지도로 돌아오겠습니다.'
			],
			why: '거시(산업) → 중범위(산업 내부) → 미시(회사) 로 자연스럽게 내려가는 구조.',
			demo: {
				label: '▶ 전 회사 뷰로 이동 (2,664사)',
				run: () => {
					viewMode = 'companies';
				}
			}
		},
		{
			selector: '.view-switch',
			title: '5 / 12  ·  산업 지도로 복귀',
			body: [
				'2,664 노드는 너무 많아 주요 분석은 산업 지도 → 산업 내부 순으로 드릴다운하는 게 더 효과적입니다.',
				'기본 뷰(산업 지도) 로 돌아가서 실제 드릴다운을 시연하겠습니다.'
			],
			demo: {
				label: '▶ 산업 지도로 복귀',
				run: () => {
					viewMode = 'atlas';
				}
			}
		},
		{
			title: '6 / 12  ·  산업 버블 클릭 = 내부 보기',
			body: [
				'산업 지도에서 **버블을 클릭하면 그 산업 안으로 드릴다운** 됩니다.',
				'예시로 반도체 산업을 열어 보겠습니다. 공정별(설계 / FAB / 패키징 / 장비 / 소재) 로 회사가 자동 클러스터링되고, 공급망 엣지가 함께 표시됩니다.',
				'버튼 누른 뒤 **왼쪽 사이드바의 공정 토글** 로 원하는 공정만 필터할 수 있고, **마우스 휠**로 줌, **드래그**로 팬 됩니다.'
			],
			why: '한 산업 안의 "누가 공급하고 누가 받는가" 밸류체인 관계가 가장 명확히 보이는 뷰.',
			demo: {
				label: '▶ 반도체 산업 내부 진입',
				run: async () => {
					await enterIndustryAction('semiconductor');
				}
			}
		},
		{
			title: '7 / 12  ·  회사 클릭 = 우측 카드 펼침',
			body: [
				'**회사 노드를 클릭하면 우측 패널이 열립니다.** 삼성전자를 자동 선택해서 실제 카드를 보여드리겠습니다.',
				'카드는 **6 섹션** 구조:\n**① 재무 한눈에** — 매출 · 영업이익 · 순이익 · 총자산 (최신년)\n**② 5년 추이 sparkline** — 3 라인(매출/영업이익/순이익) 한 그림으로\n**③ 재무 스코어** — ROE · 영업이익률 · 부채비율 · CAGR + 산업 내 분위(%)\n**④ 공급망 구조** — HHI 집중도 게이지 · Top1/3 의존도 · 상위 공급 산업 막대\n**⑤ 핵심 거래 Top 5** — 금액 기준 정밀 공급사/고객사 (예: "삼성디스플레이 ← 코닝 8조")\n**⑥ AI 분석 + 블로그** — dartlab AI 서술 + 강점/약점 칩 + 심층 분석 글',
				'블로그 포스트가 있는 회사는 **카드 맨 위에 파란 배너**로 강조됩니다.'
			],
			why: '회사 하나의 "정체성 + 수익성 + 공급망 + 정성 분석" 을 한 카드에 통합 — /company 같은 별도 페이지 안 만듭니다.',
			demo: {
				label: '▶ 삼성전자 카드 펼치기',
				run: async () => {
					await selectCompanyAction('005930');
				}
			}
		},
		{
			title: '8 / 12  ·  peer 분위 — 절대값보다 상대값',
			body: [
				'카드의 재무 스코어 섹션을 주목하세요. **"산업 내 분위" 배지**가 있습니다.',
				'ROE 10% 는 유통업에선 우량, 바이오에선 평범. 그래서 dartlab 은 **같은 산업 peer 대비 분위(percentile)** 을 함께 계산합니다.',
				'"1위 / 125사 · 점유율 27%" 같은 표시가 절대 숫자보다 훨씬 의미 있습니다.'
			],
			why: '"절대값 trap" 을 피하기 위해 항상 peer 대비로 해석하세요.'
		},
		{
			title: '9 / 12  ·  비교 — 우측 패널 2분할',
			body: [
				'한 회사 카드 하단 **"+ 비교에 추가"** 를 누르고 다음 회사를 클릭하면 우측 패널이 **760px 폭 2분할**로 확장됩니다.',
				'지금 SK하이닉스를 자동으로 추가해서 삼성전자 vs SK하이닉스 비교를 보여드립니다.',
				'비교 모드에서 양쪽의 **같은 행(재무/공급망/AI)** 이 나란히 있으므로, 공통 공급사·고객사가 자연스럽게 드러납니다.',
				'별도 `/compare` 페이지 안 만들고 이 패널에서 끝 — URL `?compare=A,B` 로 공유도 가능합니다.'
			],
			why: '"비교" 는 이 도구의 핵심 사용법. 두 회사의 차이가 즉시 눈에 들어옵니다.',
			demo: {
				label: '▶ SK하이닉스 비교 추가',
				run: async () => {
					await addCompareAction('000660');
				}
			}
		},
		{
			title: '10 / 12  ·  블로그 심층 분석',
			body: [
				'카드 상단 **파란 배너**가 있으면 이 회사에 대한 **dartlab 블로그 심층 분석 글**이 존재한다는 뜻입니다.',
				'배너에는 verdict 한 줄(예: "bullish · 보수적 성장 지속"), direction 태그(상승/하락), archetype(가치/성장/리스크 유형) 이 있습니다.',
				'**"읽으러 가기 →"** 클릭하면 해당 분석 글로 이동합니다. 현재 커버된 회사는 39개이며 점차 확장됩니다.'
			],
			why: '지도에서 찾은 회사 → 곧바로 심층 분석 글로 연결. 정량 + 정성 결합.'
		},
		{
			title: '11 / 12  ·  공유 — URL 쿼리로 직접 진입',
			body: [
				'지금 본 상태를 URL 로 공유 가능합니다.',
				'• `/map?focus=005930` — 페이지 열자마자 삼성전자 카드 펼쳐짐\n• `/map?compare=005930,000660` — 비교 모드 진입\n• `/map` 기본 URL — 투어 처음부터',
				'블로그 본문·SNS·슬랙에 바로 임베드하세요. 별도 페이지 없어도 모든 분석이 이 URL 하나로 표현됩니다.',
				'비교 상태는 곧 복잡해지니까, 뷰를 초기화하고 넘어가겠습니다.'
			],
			why: '"링크 하나로 분석 공유" — 이게 진짜 웹 네이티브 분석 도구의 모습.',
			demo: {
				label: '▶ 선택 해제 (뷰 초기화)',
				run: () => {
					clearSelectionAction();
				}
			}
		},
		{
			title: '12 / 12  ·  끝 — 이제 직접 탐험해보세요',
			body: [
				'**투어 끝났습니다.** ? 버튼으로 언제든 재시작 가능합니다.',
				'가장 빠르게 쓰는 법 (3가지 습관):\n\n**1. 색상 기준 먼저 바꿔 보세요** — ROE / 성장률 / 부채 중 질문에 맞게.\n**2. 산업 버블 → 드릴다운** — 전 회사 뷰는 가끔, 드릴다운이 주력.\n**3. 회사 카드 = 다 여기에** — 별도 페이지로 안 나가도 6 섹션 전부.',
				'잘못된 산업 분류나 엣지를 발견하면 회사 카드 하단 **"🐛 분류 신고"** 로 GitHub Issue 즉시 제출해주세요. 주간 단위로 반영합니다.',
				'이 지도 만든 사람에게 후원하고 싶으면 커피 아이콘 클릭 — 반갑습니다 ☕'
			],
			why: '툴은 만들었고, 인사이트는 당신이 찾아내는 겁니다.'
		}
	];

	function position() {
		const step = STEPS[stepIdx];
		if (!step?.selector) {
			highlight = null;
			return;
		}
		const el = document.querySelector(step.selector);
		if (!el) {
			highlight = null;
			return;
		}
		const r = (el as HTMLElement).getBoundingClientRect();
		highlight = { x: r.left - 6, y: r.top - 6, w: r.width + 12, h: r.height + 12 };
	}

	$effect(() => {
		if (open) {
			void stepIdx;
			requestAnimationFrame(() => {
				position();
			});
		}
	});

	onMount(() => {
		const ro = new ResizeObserver(() => open && position());
		ro.observe(document.body);
		const onScroll = () => open && position();
		window.addEventListener('scroll', onScroll, true);
		return () => {
			ro.disconnect();
			window.removeEventListener('scroll', onScroll, true);
		};
	});

	function maxStep(): number {
		return fullMode ? STEPS.length - 1 : QUICK_COUNT - 1;
	}
	function next() {
		if (stepIdx < maxStep()) stepIdx += 1;
		else if (!fullMode) {
			// 퀵투어 끝 → "더 알아보기" 선택지 (finish 에서 처리)
			finish();
		} else {
			finish();
		}
	}
	function expandToFull() {
		fullMode = true;
		// 3스텝 끝에서 4스텝으로 이어서 진행
		stepIdx = QUICK_COUNT;
	}
	function prev() {
		if (stepIdx > 0) stepIdx -= 1;
	}
	function finish() {
		try {
			localStorage.setItem('dartlab.map.tour.done', '1');
		} catch {
			/* noop */
		}
		stepIdx = 0;
		fullMode = false;
		onClose();
	}
	function skip() {
		finish();
	}

	async function runDemo() {
		const d = STEPS[stepIdx].demo;
		if (!d) return;
		await d.run();
		await new Promise((r) => setTimeout(r, 200));
		position();
	}

	function handleKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') skip();
		else if (e.key === 'ArrowRight' || e.key === 'Enter') next();
		else if (e.key === 'ArrowLeft') prev();
	}

	const POP_W = 560;
	let popStyle = $derived.by(() => {
		if (!highlight) {
			return 'top:50%;left:50%;transform:translate(-50%,-50%);';
		}
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1200;
		const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
		if (highlight.x + highlight.w + POP_W + 24 < vw) {
			return `top:${Math.min(vh - 360, Math.max(16, highlight.y))}px;left:${highlight.x + highlight.w + 16}px;`;
		}
		const leftPos = Math.max(16, Math.min(highlight.x, vw - POP_W - 16));
		return `top:${Math.min(vh - 360, highlight.y + highlight.h + 16)}px;left:${leftPos}px;`;
	});

	function renderBody(body: string[]): string {
		// simple inline format: **bold** -> <strong>, \n -> <br>
		return body
			.map((p) =>
				p
					.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
					.replace(/\n/g, '<br />')
			)
			.map((p) => `<p>${p}</p>`)
			.join('');
	}
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<div class="tour-root" role="dialog" aria-modal="true" aria-label="가이드 투어">
		<svg class="mask-svg" xmlns="http://www.w3.org/2000/svg">
			<defs>
				<mask id="tour-mask">
					<rect width="100%" height="100%" fill="white" />
					{#if highlight}
						<rect
							x={highlight.x}
							y={highlight.y}
							width={highlight.w}
							height={highlight.h}
							rx="10"
							fill="black"
						/>
					{/if}
				</mask>
			</defs>
			<rect width="100%" height="100%" fill="rgba(5,8,17,0.82)" mask="url(#tour-mask)" />
			{#if highlight}
				<rect
					x={highlight.x}
					y={highlight.y}
					width={highlight.w}
					height={highlight.h}
					rx="10"
					fill="none"
					stroke="#60a5fa"
					stroke-width="2.5"
				/>
			{/if}
		</svg>

		<div class="popover" style={popStyle}>
			<div class="header-row">
				<div class="step-idx">STEP {stepIdx + 1} / {maxStep() + 1}{#if !fullMode} (퀵투어){/if}</div>
				<button class="skip" onclick={skip} title="튜토리얼 건너뛰기">건너뛰기</button>
			</div>

			<h3>{STEPS[stepIdx].title}</h3>

			<div class="body">
				{@html renderBody(STEPS[stepIdx].body)}
			</div>

			{#if STEPS[stepIdx].why}
				<div class="why">
					<span class="why-label">💡 왜 유용한가</span>
					<span>{STEPS[stepIdx].why}</span>
				</div>
			{/if}

			{#if STEPS[stepIdx].demo}
				<button class="demo-btn" onclick={runDemo}>
					{STEPS[stepIdx].demo!.label}
				</button>
			{/if}

			<div class="actions">
				<div class="nav">
					{#if stepIdx > 0}
						<button class="ghost" onclick={prev}>← 이전</button>
					{:else}
						<span class="nav-placeholder"></span>
					{/if}
					{#if !fullMode && stepIdx === QUICK_COUNT - 1}
						<!-- 퀵투어 마지막 → 풀투어 선택 -->
						<button class="ghost" onclick={finish}>여기서 끝내기</button>
						<button class="primary" onclick={expandToFull}>더 알아보기 ({STEPS.length - QUICK_COUNT}스텝) →</button>
					{:else if stepIdx < maxStep()}
						<button class="primary" onclick={next}>다음 →</button>
					{:else}
						<button class="primary" onclick={finish}>완료</button>
					{/if}
				</div>
			</div>

			<div class="progress">
				<div class="progress-fill" style:width="{((stepIdx + 1) / (maxStep() + 1)) * 100}%"></div>
			</div>
		</div>
	</div>
{/if}

<style>
	.tour-root {
		position: fixed;
		inset: 0;
		z-index: 110;
		pointer-events: none;
	}
	.mask-svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		pointer-events: auto;
	}
	.popover {
		position: absolute;
		width: 560px;
		max-height: calc(100vh - 32px);
		overflow-y: auto;
		background: #0f1219;
		border: 1px solid #334155;
		border-radius: 12px;
		padding: 24px 28px 18px;
		color: #f1f5f9;
		box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
		pointer-events: auto;
	}
	@media (max-width: 640px) {
		.popover {
			width: 100vw;
			max-height: 60vh;
			position: fixed;
			bottom: 0;
			left: 0;
			top: auto !important;
			border-radius: 16px 16px 0 0;
			transform: none !important;
		}
	}
	.header-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 10px;
	}
	.step-idx {
		font-size: 10px;
		color: #60a5fa;
		font-family: monospace;
		font-weight: 700;
		letter-spacing: 0.08em;
	}
	.skip {
		background: none;
		border: none;
		color: #64748b;
		font-size: 11px;
		cursor: pointer;
		padding: 4px 8px;
		border-radius: 4px;
	}
	.skip:hover {
		color: #cbd5e1;
		background: #1e2433;
	}
	.popover h3 {
		margin: 0 0 12px;
		font-size: 20px;
		font-weight: 700;
		color: #f1f5f9;
		line-height: 1.4;
	}
	.body {
		font-size: 15px;
		line-height: 1.8;
		color: #cbd5e1;
	}
	.body :global(p) {
		margin: 0 0 10px;
	}
	.body :global(p:last-child) {
		margin-bottom: 0;
	}
	.body :global(strong) {
		color: #f1f5f9;
		font-weight: 600;
	}
	.why {
		margin-top: 14px;
		padding: 10px 12px;
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.1), rgba(52, 211, 153, 0.06));
		border: 1px solid rgba(96, 165, 250, 0.25);
		border-radius: 8px;
		font-size: 14px;
		line-height: 1.6;
		color: #cbd5e1;
	}
	.why-label {
		display: inline-block;
		color: #60a5fa;
		font-weight: 600;
		margin-right: 6px;
	}
	.demo-btn {
		margin-top: 14px;
		width: 100%;
		padding: 12px 16px;
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.22), rgba(52, 211, 153, 0.15));
		border: 1px solid rgba(96, 165, 250, 0.5);
		border-radius: 8px;
		color: #93c5fd;
		font-size: 13px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.demo-btn:hover {
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.38), rgba(52, 211, 153, 0.25));
		color: #f1f5f9;
		border-color: #60a5fa;
		transform: translateY(-1px);
	}
	.actions {
		margin-top: 16px;
	}
	.nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 8px;
	}
	.nav-placeholder {
		flex: 1;
	}
	.actions button {
		font-size: 13px;
		padding: 8px 16px;
		border-radius: 6px;
		cursor: pointer;
	}
	.actions .ghost {
		background: none;
		border: 1px solid #334155;
		color: #cbd5e1;
	}
	.actions .ghost:hover {
		background: #1e2433;
		color: #f1f5f9;
	}
	.actions .primary {
		background: #60a5fa;
		color: #050811;
		font-weight: 600;
		border: 1px solid #60a5fa;
		margin-left: auto;
	}
	.actions .primary:hover {
		background: #93c5fd;
	}
	.progress {
		margin-top: 14px;
		height: 4px;
		background: #1e2433;
		border-radius: 2px;
		overflow: hidden;
	}
	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, #60a5fa, #34d399);
		transition: width 0.3s;
	}
</style>
