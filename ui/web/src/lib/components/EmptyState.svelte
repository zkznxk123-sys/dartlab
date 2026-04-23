<!--
	EmptyState — 대화 없을 때 첫 진입 화면.

	회사 검색 인풋 · 관심종목 워치리스트는 제거 (AI 채팅이 자연어로 처리).
	아바타 + 안내 문구 + Composer (자유입력) + 예시 prompts 만.
-->
<script>
	import AutocompleteInput from "./AutocompleteInput.svelte";

	let {
		onSend,
		inputText = $bindable(""),
		onCompanySelect,
		onCommand,
	} = $props();
</script>

<div class="flex-1 flex flex-col items-center justify-center px-3 sm:px-5">
	<div class="w-full sm:max-w-[640px] flex flex-col items-center">
		<div class="relative mb-6">
			<div class="absolute inset-0 rounded-full blur-2xl opacity-30" style="background: radial-gradient(circle, rgba(234,70,71,0.5) 0%, rgba(251,146,60,0.2) 50%, transparent 70%); transform: scale(1.8);"></div>
			<img src="/avatar.png" alt="DartLab" class="relative w-14 h-14 rounded-full" />
		</div>

		<h1 class="text-xl font-bold text-dl-text mb-1">AI 금융 분석가</h1>
		<p class="text-[13px] text-dl-text-muted mb-5">종목·업종·매크로 무엇이든 자연어로 물어보세요</p>

		<div class="w-full">
			<AutocompleteInput
				bind:inputText
				large={true}
				enableCompanyAutocomplete={false}
				placeholder="예: '두산밥캣 요즘 어떤가', '반도체 업종 비교해줘'"
				{onSend}
				{onCompanySelect}
				{onCommand}
			/>
		</div>
	</div>
</div>
