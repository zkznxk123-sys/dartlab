<script lang="ts">
	/**
	 * Floating card window — Figma/VSCode 스타일 떠있는 패널.
	 *
	 * - 헤더 드래그로 이동
	 * - 우측 하단 모서리 리사이즈 (CSS resize)
	 * - 클릭 시 최상단 (z-index 자동)
	 * - 닫기 버튼
	 * - 모바일(<768px)에서는 숨김 — 기본 우측 패널만 사용
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		id: string;
		title: string;
		subtitle?: string;
		x: number;
		y: number;
		w?: number;
		h?: number;
		z?: number;
		onClose: () => void;
		onFocus?: () => void;
		onMove?: (x: number, y: number) => void;
		onResize?: (w: number, h: number) => void;
		children?: Snippet;
	}

	let {
		id,
		title,
		subtitle = '',
		x = $bindable(),
		y = $bindable(),
		w = $bindable(420),
		h = $bindable(640),
		z = 1,
		onClose,
		onFocus,
		onMove,
		onResize,
		children
	}: Props = $props();

	let rootEl: HTMLDivElement | null = $state(null);
	let dragging = $state(false);
	let dragStart = { mx: 0, my: 0, x: 0, y: 0 };

	function onHeaderMouseDown(e: MouseEvent) {
		// 닫기 버튼 등 내부 인터랙션은 제외
		if ((e.target as Element).closest('.fc-close, .fc-actions')) return;
		e.preventDefault();
		dragging = true;
		dragStart = { mx: e.clientX, my: e.clientY, x, y };
		onFocus?.();
	}

	function onWinMouseMove(e: MouseEvent) {
		if (!dragging) return;
		const nx = dragStart.x + (e.clientX - dragStart.mx);
		const ny = dragStart.y + (e.clientY - dragStart.my);
		// viewport 밖 방지
		const maxX = window.innerWidth - 80;
		const maxY = window.innerHeight - 48;
		x = Math.max(-w + 80, Math.min(maxX, nx));
		y = Math.max(0, Math.min(maxY, ny));
		onMove?.(x, y);
	}

	function onWinMouseUp() {
		dragging = false;
	}

	// ResizeObserver 로 사용자 resize 반영
	function onResizeObserved() {
		if (!rootEl) return;
		const rect = rootEl.getBoundingClientRect();
		if (Math.abs(rect.width - w) > 2 || Math.abs(rect.height - h) > 2) {
			w = rect.width;
			h = rect.height;
			onResize?.(w, h);
		}
	}

	$effect(() => {
		if (!rootEl) return;
		const ro = new ResizeObserver(onResizeObserved);
		ro.observe(rootEl);
		return () => ro.disconnect();
	});
</script>

<svelte:window onmousemove={onWinMouseMove} onmouseup={onWinMouseUp} />

<div
	bind:this={rootEl}
	class="fc"
	class:dragging
	style:left="{x}px"
	style:top="{y}px"
	style:width="{w}px"
	style:height="{h}px"
	style:z-index={z}
	onmousedown={() => onFocus?.()}
	role="dialog"
	aria-label={title}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<header class="fc-head" onmousedown={onHeaderMouseDown}>
		<div class="fc-titles">
			<div class="fc-title">{title}</div>
			{#if subtitle}
				<div class="fc-subtitle">{subtitle}</div>
			{/if}
		</div>
		<div class="fc-actions">
			<button class="fc-close" onclick={onClose} aria-label="닫기" title="닫기">✕</button>
		</div>
	</header>
	<div class="fc-body">
		{#if children}{@render children()}{/if}
	</div>
	<div class="fc-id">#{id}</div>
</div>

<style>
	.fc {
		position: fixed;
		min-width: 340px;
		min-height: 280px;
		max-width: 90vw;
		max-height: 90vh;
		background: #0f1219;
		border: 1px solid #334155;
		border-radius: 10px;
		box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(96, 165, 250, 0.1);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		resize: both;
	}
	.fc.dragging {
		cursor: grabbing;
		opacity: 0.95;
	}

	.fc-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 8px 12px;
		background: linear-gradient(180deg, rgba(96, 165, 250, 0.08), transparent);
		border-bottom: 1px solid #1e2433;
		cursor: grab;
		user-select: none;
		flex-shrink: 0;
	}
	.fc.dragging .fc-head {
		cursor: grabbing;
	}
	.fc-titles {
		min-width: 0;
	}
	.fc-title {
		font-size: 13px;
		font-weight: 600;
		color: #f1f5f9;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.fc-subtitle {
		font-size: 10px;
		color: #64748b;
		font-family: monospace;
	}
	.fc-actions {
		display: flex;
		gap: 4px;
	}
	.fc-close {
		width: 22px;
		height: 22px;
		background: transparent;
		border: none;
		border-radius: 4px;
		color: #64748b;
		cursor: pointer;
		font-size: 12px;
	}
	.fc-close:hover {
		background: rgba(239, 68, 68, 0.12);
		color: #f87171;
	}

	.fc-body {
		flex: 1;
		overflow-y: auto;
		background: #0f1219;
	}
	.fc-id {
		position: absolute;
		bottom: 2px;
		left: 6px;
		font-size: 9px;
		color: #334155;
		font-family: monospace;
		pointer-events: none;
	}

	@media (max-width: 768px) {
		.fc {
			display: none;
		}
	}
</style>
