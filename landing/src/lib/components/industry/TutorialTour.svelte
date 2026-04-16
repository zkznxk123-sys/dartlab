<script lang="ts">
	import { onMount } from 'svelte';

	interface Step {
		selector?: string;
		title: string;
		body: string;
		fallback?: { x: number; y: number; w: number; h: number };
	}

	interface Props {
		open: boolean;
		onClose: () => void;
	}

	let { open, onClose }: Props = $props();

	const STEPS: Step[] = [
		{
			title: 'dartlab 산업지도에 오신 걸 환영합니다',
			body:
				'한국 상장사 2,664사 × 34개 산업 × 18,418 공급망 엣지를 한 화면에서 탐색합니다. 7단계 간단 투어를 시작할까요?'
		},
		{
			selector: '.brand-bar',
			title: '좌측 상단: 브랜드 바',
			body:
				'아바타 = 홈으로 돌아가기 / GitHub = 소스 / Buy Me A Coffee = 후원 / ? = 이 화면 가이드 / ▶ = 이 튜토리얼 재실행.'
		},
		{
			selector: '.color-switch',
			title: '색상 기준',
			body:
				'노드 색상을 바꿔보세요. ROE·영업이익률·부채비율·성장률 중 하나를 선택하면 전체 지도가 빨→초 그라디언트로 재색상됩니다. "어느 산업이 지금 우량한가" 한눈에 답합니다.'
		},
		{
			selector: '.view-switch',
			title: '관점 3종',
			body:
				'산업 지도(34개 버블) ↔ 전 회사(2,664사 그래프) ↔ 산업 내부(드릴다운). 산업 버블을 클릭하면 자동으로 내부 뷰로 진입합니다.'
		},
		{
			title: '회사 카드',
			body:
				'회사 노드 클릭 시 우측 패널이 열리며 6 섹션으로 구성됩니다: 재무 요약 / 5년 추이 / scan 스코어 + 산업 내 분위 / 공급망 HHI / 핵심 거래 Top 5 / AI 분석 + 블로그 포스트.'
		},
		{
			title: '비교',
			body:
				'첫 회사 선택 후 "+ 비교에 추가" → 다음 회사 클릭하면 우측 패널이 2분할로 확장됩니다. 공통 공급사/고객사, 재무 차이를 나란히 봅니다.'
		},
		{
			title: '외부 진입 / 공유',
			body:
				'URL 에 ?focus=005930 을 붙이면 그 회사 카드가 자동 펼쳐집니다. ?compare=005930,000660 으로 비교 링크 공유 가능. 블로그 본문에서 자유롭게 임베드하세요.'
		}
	];

	let stepIdx = $state(0);
	let highlight = $state<{ x: number; y: number; w: number; h: number } | null>(null);

	function position() {
		const step = STEPS[stepIdx];
		if (!step?.selector) {
			highlight = null;
			return;
		}
		const el = document.querySelector(step.selector);
		if (!el) {
			highlight = step.fallback || null;
			return;
		}
		const r = (el as HTMLElement).getBoundingClientRect();
		highlight = { x: r.left - 6, y: r.top - 6, w: r.width + 12, h: r.height + 12 };
	}

	$effect(() => {
		// open 또는 stepIdx 변경 시 리포지셔닝
		if (open) {
			// 다음 프레임에 위치 잡기
			requestAnimationFrame(() => {
				void stepIdx;
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

	function handleKey(e: KeyboardEvent) {
		if (!open) return;
		if (e.key === 'Escape') skip();
		else if (e.key === 'ArrowRight' || e.key === 'Enter') next();
		else if (e.key === 'ArrowLeft') prev();
	}

	// 팝오버 위치 계산 (하이라이트 주변 or 중앙)
	let popStyle = $derived.by(() => {
		if (!highlight) {
			return 'top:50%;left:50%;transform:translate(-50%,-50%);';
		}
		const vw = typeof window !== 'undefined' ? window.innerWidth : 1200;
		const vh = typeof window !== 'undefined' ? window.innerHeight : 800;
		const pw = 360;
		// 하이라이트 오른쪽에 배치, 공간 부족하면 아래
		if (highlight.x + highlight.w + pw + 24 < vw) {
			return `top:${Math.min(vh - 220, Math.max(16, highlight.y))}px;left:${highlight.x + highlight.w + 16}px;`;
		}
		return `top:${Math.min(vh - 220, highlight.y + highlight.h + 16)}px;left:${Math.max(16, Math.min(highlight.x, vw - pw - 16))}px;`;
	});
</script>

<svelte:window onkeydown={handleKey} />

{#if open}
	<div class="tour-root" role="dialog" aria-modal="true" aria-label="튜토리얼">
		<!-- backdrop with hole -->
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
			<rect width="100%" height="100%" fill="rgba(5,8,17,0.75)" mask="url(#tour-mask)" />
			{#if highlight}
				<rect
					x={highlight.x}
					y={highlight.y}
					width={highlight.w}
					height={highlight.h}
					rx="10"
					fill="none"
					stroke="#60a5fa"
					stroke-width="2"
				/>
			{/if}
		</svg>

		<div class="popover" style={popStyle}>
			<div class="step-idx">{stepIdx + 1} / {STEPS.length}</div>
			<h3>{STEPS[stepIdx].title}</h3>
			<p>{STEPS[stepIdx].body}</p>
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
		width: 360px;
		background: #0f1219;
		border: 1px solid #334155;
		border-radius: 10px;
		padding: 16px 18px;
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
</style>
