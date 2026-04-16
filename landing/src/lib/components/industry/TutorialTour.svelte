<script lang="ts">
	import { onMount } from 'svelte';

	interface Step {
		selector?: string;
		title: string;
		body: string;
		// "해보세요" 데모 액션 — 있으면 버튼으로 노출
		demo?: { label: string; run: () => void | Promise<void> };
	}

	interface Props {
		open: boolean;
		onClose: () => void;
		// 부모의 상태에 접근 — 데모 액션용 (bind:)
		colorMetric: string;
		viewMode: string;
		enterIndustryAction: (id: string) => void | Promise<void>;
	}

	let {
		open,
		onClose,
		colorMetric = $bindable(),
		viewMode = $bindable(),
		enterIndustryAction
	}: Props = $props();

	let stepIdx = $state(0);
	let highlight = $state<{ x: number; y: number; w: number; h: number } | null>(null);

	const STEPS: Step[] = [
		{
			title: 'dartlab 산업지도에 오신 걸 환영합니다',
			body:
				'이 투어는 "뭘 클릭하면 뭐가 나오는지" 를 직접 보여드립니다. ←→ 화살표 키 또는 아래 버튼으로 진행하세요.'
		},
		{
			selector: '.brand-bar',
			title: '1. 좌측 상단 — 브랜드 바',
			body:
				'아바타 = 홈 / GitHub = 소스 / 노란 버튼 = 후원 / ? = 이 투어 재시작. 간단히 "빠른 링크 모음"입니다.'
		},
		{
			selector: '.color-switch',
			title: '2. 색상 기준 — 가장 중요',
			body:
				'이 셀렉터가 지도의 모든 색을 바꿉니다. 예) ROE로 바꾸면 우량(초록) / 부진(빨강) 회사가 즉시 드러납니다. 아래 "ROE로 바꿔보기" 를 눌러 직접 확인.',
			demo: {
				label: '▶ ROE로 바꿔보기',
				run: () => {
					colorMetric = 'roe';
				}
			}
		},
		{
			selector: '.color-switch',
			title: '2-1. 다른 기준으로',
			body:
				'매출 CAGR(성장률) — 고성장 회사가 초록. 부채비율 — 위험도 직관적 표시. 원하는 관점으로 지도 전체가 재색상됩니다.',
			demo: {
				label: '▶ 매출 CAGR로 바꾸기',
				run: () => {
					colorMetric = 'revCagr';
				}
			}
		},
		{
			selector: '.view-switch',
			title: '3. 관점 3종',
			body:
				'산업 지도 = 34개 버블 (기본). 전 회사 = 2,664사 한눈에. 산업 내부 = 특정 산업 드릴다운. 지금 "전 회사" 뷰로 옮겨볼까요?',
			demo: {
				label: '▶ 전 회사 뷰로 이동',
				run: () => {
					viewMode = 'companies';
				}
			}
		},
		{
			selector: '.view-switch',
			title: '3-1. 산업 지도로 복귀',
			body: '버블이 많아 복잡하죠? 다시 기본 산업 지도로 돌아갑니다.',
			demo: {
				label: '▶ 산업 지도로 복귀',
				run: () => {
					viewMode = 'atlas';
				}
			}
		},
		{
			title: '4. 산업 버블 클릭 = 내부 보기',
			body:
				'아래 버튼을 누르면 반도체 산업 내부로 들어가서 공정별로 회사가 클러스터링됩니다. 회사들 사이의 공급망 엣지도 함께 보입니다.',
			demo: {
				label: '▶ 반도체 산업 내부 보기',
				run: async () => {
					await enterIndustryAction('semiconductor');
				}
			}
		},
		{
			title: '5. 회사 클릭 = 우측 카드 펼침',
			body:
				'맵에서 회사 노드를 클릭하면 우측 패널이 회사 카드로 열립니다. 6 섹션: 재무 요약 / 5년 추이 / ROE·margin 점수 / 공급망 HHI / 핵심 거래 Top 5 / AI 분석 + 블로그 포스트.'
		},
		{
			title: '6. 비교 — "+ 비교에 추가"',
			body:
				'한 회사 선택 후 카드 하단 "+ 비교에 추가" 버튼 → 다음 회사 클릭하면 우측 패널이 2분할 됩니다. 재무/공급망/AI 분석을 나란히 봅니다.'
		},
		{
			title: '7. 블로그 심층 분석',
			body:
				'블로그 포스트가 있는 회사는 카드 맨 위에 파란 배너로 강조됩니다. verdict + "읽으러 가기 →" 클릭하면 해당 분석 글로 이동. 현재 39사 커버, 점차 확장.'
		},
		{
			title: '8. 공유 / 직접 진입',
			body:
				'URL 에 ?focus=005930 붙이면 삼성전자 카드 자동 펼침. ?compare=005930,000660 이면 비교 모드 진입. 블로그 본문/SNS 에 바로 임베드하세요.'
		},
		{
			title: '끝 — 이제 직접 탐험해보세요',
			body:
				'? 버튼으로 언제든 이 투어 재시작 가능. 잘못된 산업 분류가 보이면 회사 카드의 "🐛 분류 신고" 로 GitHub Issue 제출.'
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

	function next() {
		if (stepIdx < STEPS.length - 1) stepIdx += 1;
		else finish();
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
		onClose();
	}
	function skip() {
		finish();
	}

	async function runDemo() {
		const d = STEPS[stepIdx].demo;
		if (!d) return;
		await d.run();
		// 상태 변화가 렌더에 반영될 시간
		await new Promise((r) => setTimeout(r, 200));
		position();
	}

	function handleKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') skip();
		else if (e.key === 'ArrowRight' || e.key === 'Enter') next();
		else if (e.key === 'ArrowLeft') prev();
	}

	let popStyle = $derived.by(() => {
		if (!highlight) {
			return 'top:50%;left:50%;transform:translate(-50%,-50%);';
		}
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1200;
		const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
		const pw = 380;
		if (highlight.x + highlight.w + pw + 24 < vw) {
			return `top:${Math.min(vh - 260, Math.max(16, highlight.y))}px;left:${highlight.x + highlight.w + 16}px;`;
		}
		const leftPos = Math.max(16, Math.min(highlight.x, vw - pw - 16));
		return `top:${Math.min(vh - 260, highlight.y + highlight.h + 16)}px;left:${leftPos}px;`;
	});
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
			<rect width="100%" height="100%" fill="rgba(5,8,17,0.78)" mask="url(#tour-mask)" />
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
			<div class="step-idx">{stepIdx + 1} / {STEPS.length}</div>
			<h3>{STEPS[stepIdx].title}</h3>
			<p>{STEPS[stepIdx].body}</p>

			{#if STEPS[stepIdx].demo}
				<button class="demo-btn" onclick={runDemo}>
					{STEPS[stepIdx].demo!.label}
				</button>
			{/if}

			<div class="actions">
				<button class="skip" onclick={skip}>건너뛰기</button>
				<div class="nav">
					{#if stepIdx > 0}
						<button class="ghost" onclick={prev}>← 이전</button>
					{/if}
					{#if stepIdx < STEPS.length - 1}
						<button class="primary" onclick={next}>다음 →</button>
					{:else}
						<button class="primary" onclick={finish}>완료</button>
					{/if}
				</div>
			</div>

			<div class="progress">
				<div class="progress-fill" style:width="{((stepIdx + 1) / STEPS.length) * 100}%"></div>
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
		width: 380px;
		background: #0f1219;
		border: 1px solid #334155;
		border-radius: 10px;
		padding: 16px 18px 12px;
		color: #f1f5f9;
		box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
		pointer-events: auto;
	}
	.step-idx {
		font-size: 10px;
		color: #60a5fa;
		font-family: monospace;
		margin-bottom: 6px;
	}
	.popover h3 {
		margin: 0 0 8px;
		font-size: 15px;
	}
	.popover p {
		margin: 0;
		font-size: 12px;
		color: #cbd5e1;
		line-height: 1.7;
	}
	.demo-btn {
		margin-top: 12px;
		width: 100%;
		padding: 10px 14px;
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.2), rgba(52, 211, 153, 0.15));
		border: 1px solid rgba(96, 165, 250, 0.5);
		border-radius: 6px;
		color: #93c5fd;
		font-size: 12px;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}
	.demo-btn:hover {
		background: linear-gradient(135deg, rgba(96, 165, 250, 0.35), rgba(52, 211, 153, 0.25));
		color: #f1f5f9;
		border-color: #60a5fa;
	}
	.actions {
		margin-top: 14px;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}
	.actions button {
		background: none;
		border: 1px solid transparent;
		color: #cbd5e1;
		font-size: 12px;
		padding: 6px 12px;
		border-radius: 6px;
		cursor: pointer;
	}
	.actions .skip {
		color: #64748b;
	}
	.actions .skip:hover {
		color: #cbd5e1;
	}
	.actions .ghost {
		border-color: #334155;
	}
	.actions .ghost:hover {
		background: #1e2433;
	}
	.actions .primary {
		background: #60a5fa;
		color: #050811;
		font-weight: 600;
		border-color: #60a5fa;
	}
	.actions .primary:hover {
		background: #93c5fd;
	}
	.actions .nav {
		display: flex;
		gap: 6px;
	}
	.progress {
		margin-top: 10px;
		height: 3px;
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
