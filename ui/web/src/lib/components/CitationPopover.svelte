<!--
	CitationPopover — 인용 [1] 호버 시 소스 프리뷰 팝오버 (Perplexity 식 메타데이터 강화).
	300ms hover-in 딜레이, 200ms hover-out 딜레이.

	context 형식:
	  { label?, module?, text|content?, kind? ('skill'|'data'|'web'),
	    refId?, sourceUrl?, sourceTitle? }
-->
<script>
	import { BookOpen, Database, ExternalLink, Globe } from "lucide-svelte";

	let { contexts = [], containerEl = null } = $props();

	let popover = $state({ visible: false, x: 0, y: 0, context: null });
	let hoverInTimer = null;
	let hoverOutTimer = null;

	function showPopover(el, ctx) {
		clearTimeout(hoverOutTimer);
		hoverOutTimer = null;
		if (popover.visible && popover.context === ctx) return;
		clearTimeout(hoverInTimer);
		hoverInTimer = setTimeout(() => {
			const rect = el.getBoundingClientRect();
			const containerRect = containerEl?.getBoundingClientRect() || { left: 0, top: 0 };
			popover = {
				visible: true,
				x: rect.left - containerRect.left + rect.width / 2,
				y: rect.top - containerRect.top - 4,
				context: ctx,
			};
		}, 300);
	}

	function hidePopover() {
		clearTimeout(hoverInTimer);
		hoverInTimer = null;
		hoverOutTimer = setTimeout(() => {
			popover = { ...popover, visible: false, context: null };
		}, 200);
	}

	function keepPopover() {
		clearTimeout(hoverOutTimer);
		hoverOutTimer = null;
	}

	$effect(() => {
		if (!containerEl || !contexts?.length) return;

		function onEnter(e) {
			const citeEl = e.target.closest?.(".cite-ref");
			if (!citeEl) return;
			const idx = parseInt(citeEl.dataset.cite, 10);
			if (isNaN(idx) || idx < 1 || idx > contexts.length) return;
			showPopover(citeEl, contexts[idx - 1]);
		}
		function onLeave(e) {
			const citeEl = e.target.closest?.(".cite-ref");
			if (!citeEl) return;
			hidePopover();
		}

		containerEl.addEventListener("mouseenter", onEnter, true);
		containerEl.addEventListener("mouseleave", onLeave, true);
		return () => {
			containerEl.removeEventListener("mouseenter", onEnter, true);
			containerEl.removeEventListener("mouseleave", onLeave, true);
			clearTimeout(hoverInTimer);
			clearTimeout(hoverOutTimer);
		};
	});

	let previewText = $derived.by(() => {
		if (!popover.context) return "";
		const text = popover.context.text || popover.context.content || "";
		return text.length > 180 ? text.slice(0, 180) + "…" : text;
	});

	let kind = $derived(popover.context?.kind || "skill");
	let title = $derived(
		popover.context?.sourceTitle ||
			popover.context?.label ||
			popover.context?.module ||
			"소스",
	);
	let refLabel = $derived(popover.context?.refId || popover.context?.module || "");
	let sourceUrl = $derived(popover.context?.sourceUrl || "");
</script>

{#if popover.visible && popover.context}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="absolute z-50 w-80 rounded-xl border border-dl-border bg-dl-bg-card p-3 shadow-lg shadow-black/40 text-[12px] leading-relaxed animate-fadeIn"
		style="left: {popover.x}px; top: {popover.y}px; transform: translate(-50%, -100%)"
		role="tooltip"
		onmouseenter={keepPopover}
		onmouseleave={hidePopover}
	>
		<div class="mb-1.5 flex items-center gap-1.5">
			<span class="flex h-5 w-5 items-center justify-center rounded-md bg-dl-primary/15 text-dl-primary-light">
				{#if kind === "web"}
					<Globe size={11} />
				{:else if kind === "data"}
					<Database size={11} />
				{:else}
					<BookOpen size={11} />
				{/if}
			</span>
			<span class="flex-1 truncate text-[11px] font-semibold text-dl-text">{title}</span>
			{#if refLabel}
				<span class="rounded-full border border-dl-border/60 px-1.5 py-0.5 text-[9px] font-medium text-dl-text-dim">
					{refLabel}
				</span>
			{/if}
		</div>
		<div class="text-dl-text-muted leading-[1.6]">{previewText}</div>
		<div class="mt-2 flex items-center justify-between text-[10px] text-dl-text-dim">
			<span>클릭하면 전체 보기</span>
			{#if sourceUrl}
				<a
					href={sourceUrl}
					target="_blank"
					rel="noreferrer"
					class="flex items-center gap-1 text-dl-primary-light hover:underline"
				>
					<ExternalLink size={10} /> 원본
				</a>
			{/if}
		</div>
	</div>
{/if}
