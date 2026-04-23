<!--
	데이터 투명성 뱃지 — LLM이 보는 모든 데이터를 사용자에게 표시.
	meta/context/snapshot/tool 뱃지 + 스냅샷 카드 + 도구 이벤트 타임라인.
-->
<script>
	import { formatEvidenceLabel } from "$lib/ai/evidenceLabels.js";
	import { Badge } from "$lib/components/ui/badge/index.js";
	import {
		Database, AlertTriangle, Activity
	} from "lucide-svelte";

	let {
		message,
		companyName = null,
		dataYearRange = null,
		dialogueModeLabel = null,
		dataReadyInfo = null,
		activityBadges = [],
		onOpenContextModal,
		onOpenSnapshotModal,
		onOpenToolEventModal,
		onOpenSystemPromptModal,
		onOpenUserContentModal,
		onOpenEvidence,
	} = $props();
</script>

<!-- ── 상단 메타 뱃지 (데이터 투명성) ── -->
{#if companyName || dataYearRange || dataReadyInfo || message.contexts?.length > 0 || message.meta?.includedModules || activityBadges.length > 0}
	<div class="message-section-slot message-transparency-slot mb-3 rounded-2xl border border-dl-border/40 bg-dl-bg-card/20 p-3">
		<div class="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-dl-text-dim">
			<Activity size={11} />
			투명성
		</div>
		<div class="mb-2 text-[11px] leading-relaxed text-dl-text-dim">
			이 응답을 만들 때 실제로 참조한 회사, 기간, 컨텍스트, 툴 활동을 바로 열어볼 수 있습니다.
		</div>
		{#if dataReadyInfo}
			<div class="mb-2 rounded-xl border px-2.5 py-2 text-[11px] leading-relaxed {dataReadyInfo.allReady ? 'border-emerald-500/20 bg-emerald-500/[0.06] text-emerald-300' : 'border-amber-500/20 bg-amber-500/[0.06] text-amber-200'}">
				<span class="font-medium">{dataReadyInfo.label}</span>
				<span class="ml-1 text-dl-text-muted">{dataReadyInfo.summary}</span>
			</div>
		{/if}
		<div class="flex flex-wrap items-center gap-1.5">
		{#if companyName}
			<Badge variant="muted">{companyName}</Badge>
		{/if}
		{#if message.meta?.market}
			<Badge variant="muted">{message.meta.market.toUpperCase()}</Badge>
		{/if}
		{#if dialogueModeLabel}
			<Badge variant="accent">{dialogueModeLabel}</Badge>
		{/if}
		{#if message.meta?.topicLabel}
			<Badge variant="muted">{message.meta.topicLabel}</Badge>
		{/if}
		{#if dataYearRange}
			<Badge variant="accent">{dataYearRange}</Badge>
		{/if}
		{#if message.contexts?.length > 0}
			{#each message.contexts as ctx, i}
				<button
					class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-dl-border/50 bg-dl-bg-card/40 text-[11px] text-dl-text-muted hover:text-dl-text hover:border-dl-primary/40 hover:bg-dl-primary/[0.05] transition-all cursor-pointer"
					onclick={() => onOpenContextModal?.(i)}
				>
					<Database size={10} class="flex-shrink-0" />
					{formatEvidenceLabel(ctx.label || ctx.module, ctx.label || "관련 데이터")}
				</button>
			{/each}
		{:else if message.meta?.includedModules?.length > 0}
			<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-dl-border/50 bg-dl-bg-card/40 text-[11px] text-dl-text-dim">
				<Database size={10} class="flex-shrink-0" />
				모듈 {message.meta.includedModules.length}개
			</span>
		{/if}
		{#each activityBadges as badge}
			<button
				class="inline-flex items-center gap-1 rounded-full border border-dl-border/50 bg-dl-bg-card/35 px-2 py-0.5 text-[10px] text-dl-text-dim transition-colors hover:border-dl-primary/30 hover:text-dl-text"
				onclick={() => {
					if (badge.label.startsWith("컨텍스트")) onOpenContextModal?.(0);
					else if (badge.label.startsWith("툴 ")) onOpenEvidence ? onOpenEvidence("tool-calls", 0) : onOpenToolEventModal?.(0);
					else if (badge.label === "시스템 프롬프트") onOpenSystemPromptModal?.();
					else if (badge.label === "LLM 입력") onOpenUserContentModal?.();
				}}
			>
				<badge.icon size={10} class="flex-shrink-0" />
				{badge.label}
			</button>
		{/each}
		</div>
	</div>
{/if}

<!-- ── Snapshot 카드 ── -->
{#if message.snapshot?.items?.length > 0}
	<button
		class="message-section-slot mb-3 rounded-xl border border-dl-border/60 bg-dl-bg-card/40 overflow-hidden animate-fadeIn shadow-sm shadow-black/10 w-full text-left cursor-pointer hover:border-dl-primary/30 transition-colors"
		onclick={() => onOpenSnapshotModal?.()}
	>
		<div class="grid gap-px" style="grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));">
			{#each message.snapshot.items as item}
				{@const statusColor = item.status === "good" ? "text-dl-success" : item.status === "danger" ? "text-dl-primary-light" : item.status === "caution" ? "text-amber-400" : "text-dl-text"}
				<div class="px-3 py-2 bg-dl-bg-card/50">
					<div class="text-[10px] text-dl-text-dim leading-tight">{item.label}</div>
					<div class={cn("text-[14px] font-semibold leading-snug mt-0.5", statusColor)}>
						{item.value}
					</div>
				</div>
			{/each}
		</div>
		{#if message.snapshot.warnings?.length > 0}
			<div class="px-3 py-1.5 border-t border-dl-border/30 flex flex-wrap gap-2">
				{#each message.snapshot.warnings as warn}
					<span class="flex items-center gap-1 text-[10px] text-amber-400">
						<AlertTriangle size={10} />
						{warn}
					</span>
				{/each}
			</div>
		{/if}
		{#if message.snapshot.grades}
			{@const gradeLabels = { performance: "실적", profitability: "수익성", health: "건전성", cashflow: "현금흐름", governance: "지배구조", risk: "리스크", opportunity: "기회" }}
			<div class="px-3 py-1.5 border-t border-dl-border/30 flex flex-wrap gap-1.5">
				{#each Object.entries(message.snapshot.grades) as [key, grade]}
					{@const color = grade === "A" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" : grade === "B" ? "bg-blue-500/15 text-blue-400 border-blue-500/30" : grade === "C" ? "bg-amber-500/15 text-amber-400 border-amber-500/30" : grade === "D" ? "bg-orange-500/15 text-orange-400 border-orange-500/30" : grade === "F" ? "bg-red-500/15 text-red-400 border-red-500/30" : "bg-dl-border/10 text-dl-text-dim border-dl-border/20"}
					<span class="px-1.5 py-0.5 rounded text-[9px] font-bold border {color}">
						{gradeLabels[key] || key} {grade}
					</span>
				{/each}
				{#if message.snapshot.anomalyCount > 0}
					<span class="px-1.5 py-0.5 rounded text-[9px] font-bold border bg-red-500/10 text-red-400 border-red-500/20">
						이상치 {message.snapshot.anomalyCount}건
					</span>
				{/if}
			</div>
		{/if}
	</button>
{/if}

<!--
	Tool Events 타임라인 (기존 "보고 있는 것 / 하고 있는 것") 제거.
	MessageBubble 의 Claude Code 스타일 아코디언이 상위호환 (헤더 1줄 + summary + IN/OUT expand).
	투명성 원칙은 상단 activityBadges "툴 N건" + 아코디언 으로 유지.
-->

