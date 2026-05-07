<!--
	ToolBlock — Ask Workbench 실행 카드.

	- 헤더 + IN + OUT 박스 **항상 보임** (접기/펴기 토글 없음)
	- OUT 은 적정 높이 프레임 (max-h 200px) + 스크롤 — 긴 내용도 레이아웃 깨짐 없음
	- 헤더 클릭 = 전체 확장 (max-h 해제) / 다시 클릭 = 원복
	- running 상태는 진행 로그 실시간 표시
-->
<script>
	import { Loader2, XCircle } from "lucide-svelte";
	import { renderMarkdown } from "$lib/markdown.js";
	import { cleanErrorMessage, describeCallArgs, getToolTitles, TOOL_ICONS } from "$lib/ai/toolSummary.js";
	import { DEFAULT_TOOL_ICON, TOOL_ICON_MAP } from "$lib/ai/toolIcons.js";

	const ICON_MAP = TOOL_ICON_MAP;

	let { seg } = $props();

	let fullExpanded = $state(false);

	let isError = $derived(seg.status === "error");
	let isRunning = $derived(seg.status === "running");
	let isDone = $derived(seg.status === "done");

	let titles = $derived(getToolTitles(seg.name));
	let inArgs = $derived(describeCallArgs({ arguments: seg.args }));
	let allLines = $derived(seg.progressLines || []);
	let outText = $derived.by(() => {
		if (!isDone) return "";
		const r = seg.result;
		if (typeof r === "string") return r;
		if (r === null || r === undefined) return "";
		try { return JSON.stringify(r, null, 2); } catch { return String(r); }
	});
	let errorText = $derived.by(() => {
		if (!isError) return "";
		const r = seg.result;
		return cleanErrorMessage(typeof r === "string" ? r : "");
	});
	let headerSummary = $derived.by(() => {
		if (isError) return "데이터 없음";
		if (isDone && typeof seg.summary === "string" && seg.summary.trim()) return seg.summary.trim();
		return "";
	});
	// OUT 크기 요약
	let outLineCount = $derived(outText ? outText.split("\n").length : 0);
	let fullResultUrl = $derived(seg.fullResultArtifact?.url || "");
	let fullResultSize = $derived(seg.sizeBytes ? `${Math.round(seg.sizeBytes / 1024)} KB` : "");

	function toggleFull() { fullExpanded = !fullExpanded; }
	function truncate(s, max) { return s && s.length > max ? s.slice(0, max) + "..." : (s || ""); }
	function displayToolName(label, name) {
		const raw = label || name || "tool";
		return String(raw).includes("_") ? String(raw).replaceAll("_", " ") : String(raw);
	}

	let toolIcon = $derived(ICON_MAP[TOOL_ICONS[seg.name]] || DEFAULT_TOOL_ICON);
</script>

<div class="tool-block" class:tool-block-error={isError} class:tool-block-full={fullExpanded}>
	<!-- 헤더: 클릭 = 전체 펼침 토글. 접기/펼치기 chevron 없음 (카드 형태) -->
	<button class="tool-header" onclick={toggleFull} type="button" title={fullExpanded ? "접기" : "전체 보기"}>
		{#if isRunning}
			<Loader2 size={12} class="animate-spin flex-shrink-0 text-dl-accent" />
		{:else if isError}
			<XCircle size={12} class="flex-shrink-0 text-dl-primary-light" />
		{:else}
			<svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" class="tool-ok">
				<path d="M6.5 12L2 7.5l1.4-1.4L6.5 9.2l6.1-6.1L14 4.5z"/>
			</svg>
		{/if}
		<svelte:component this={toolIcon} size={12} class="flex-shrink-0 text-dl-text-dim" />
		<span class="tool-name">{displayToolName(seg.label, seg.name)}</span>
		{#if headerSummary}
			<span class="tool-summary" class:tool-summary-error={isError}>{truncate(headerSummary, 80)}</span>
		{:else if isDone && outLineCount > 0}
			<span class="tool-summary tool-line-count">{outLineCount} line{outLineCount > 1 ? "s" : ""} of output</span>
		{/if}
	</button>

	<!-- 본문: 항상 노출. OUT 은 적정 높이 프레임. -->
	<div class="tool-sections">
		{#if inArgs}
			<section class="tool-section">
				<h4 class="tool-section-title">{titles.in}</h4>
				<div class="tool-section-body tool-in">{inArgs}</div>
			</section>
		{/if}

		{#if isRunning && allLines.length > 0}
			<section class="tool-section">
				<h4 class="tool-section-title">진행 로그</h4>
				<div class="tool-section-body tool-log">
					{#each allLines.slice(-5) as ln}
						<div class="tool-progress-line">{ln}</div>
					{/each}
				</div>
			</section>
		{/if}

		{#if isError}
			<section class="tool-section">
				<h4 class="tool-section-title tool-section-title-error">오류</h4>
				<div class="tool-section-body tool-error-body">
					{errorText || "데이터 없음"}
				</div>
			</section>
		{:else if isDone && outText}
			<section class="tool-section">
				<h4 class="tool-section-title">{titles.out}</h4>
				{#if seg.persisted && fullResultUrl}
					<div class="tool-section-body tool-in mb-2">
						전체 결과는 artifact로 저장됨{fullResultSize ? ` (${fullResultSize})` : ""}: {fullResultUrl}
					</div>
				{/if}
				<div class="tool-section-body tool-out prose-dartlab">
					{@html renderMarkdown(outText)}
				</div>
			</section>
		{/if}
	</div>
</div>
