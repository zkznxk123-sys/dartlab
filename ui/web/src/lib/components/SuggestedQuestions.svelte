<!--
	SuggestedQuestions — Perplexity 식 답변 끝 추천 후속 질문 카드 3개.
	props:
	  questions: string[]
	  onSelect: (q) => void
-->
<script>
	import { Sparkles } from "lucide-svelte";

	let { questions = [], onSelect } = $props();
	let visible = $derived(Array.isArray(questions) && questions.length > 0);
</script>

{#if visible}
	<div class="mt-3 space-y-1.5">
		<div class="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-[0.16em] text-dl-text-dim">
			<Sparkles size={11} class="text-dl-accent" />
			<span>이어서 물어보기</span>
		</div>
		<div class="flex flex-col gap-1.5">
			{#each questions.slice(0, 3) as q}
				<button
					type="button"
					class="rounded-lg border border-dl-border/45 bg-dl-bg-card/45 px-3 py-2 text-left text-[12px] text-dl-text-muted transition hover:border-dl-primary/40 hover:bg-dl-bg-card-hover hover:text-dl-text"
					onclick={() => onSelect?.(q)}
				>
					{q}
				</button>
			{/each}
		</div>
	</div>
{/if}
