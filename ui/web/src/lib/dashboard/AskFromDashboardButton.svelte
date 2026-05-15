<!--
	AskFromDashboardButton — Dashboard 헤더의 "AI 에게 첨부" 버튼.
	클릭 시 snapshot 캡처 + ask 모드 전환 + pendingSnapshot 설정.
-->
<script>
	import { Paperclip } from "lucide-svelte";
	import { getUiMode } from "$lib/stores/uiMode.svelte.js";
	import { getDashboardStore } from "$lib/stores/dashboardStore.svelte.js";
	import { Button } from "$lib/ui/button";

	const ui = getUiMode();
	const dash = getDashboardStore();

	function attachAndSwitch() {
		const snap = dash.snapshot();
		dash.setPendingSnapshot(snap);
		ui.setMode("ask");
	}
</script>

<Button variant="outline" size="sm" onclick={attachAndSwitch}>
	<Paperclip size={13} />
	<span>현재 화면 AI 첨부</span>
</Button>
