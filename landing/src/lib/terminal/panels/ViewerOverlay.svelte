<script lang="ts">
	// 공시뷰어 인터미널 오버레이 — ViewerStudio 를 fixed 전체화면에 lazy 마운트(한몸두입구의 터미널 입구).
	// ⛔ 정적 import 금지: 터미널 초기 청크에 viewer 가 실리면 평소 비용 0 원칙이 깨진다. dynamic import 로
	// Vite 가 별도 청크로 분리 — ⤢ 클릭 전엔 1바이트도 안 내려온다. 회사 이동·비교는 내부 state(URL 불변).
	let { code, onclose }: { code: string; onclose: () => void } = $props();

	// 내부 항해 전엔 터미널 종목을 따라가고(prop 반응), 뷰어 안에서 이동하면 그때부터 내부 state 가 잡는다.
	let nav = $state<{ code: string; vs: string[] } | null>(null);
	const view = $derived(nav ?? { code, vs: [] as string[] });
	function onNavigate(c: string, v: string[]) {
		nav = { code: c, vs: v };
	}

	const mod = import('$lib/components/viewer/ViewerStudio.svelte');

	// ESC 닫기 — 입력 필드(검색·질문) 안의 Esc 는 그 위젯 몫(팝오버 닫기)이라 오버레이는 무시.
	$effect(() => {
		const onKey = (e: KeyboardEvent) => {
			if (e.key !== 'Escape') return;
			const t = e.target as HTMLElement | null;
			if (t?.closest('input, textarea, [contenteditable]')) return;
			onclose();
		};
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});
</script>

<div class="dlViewerFs">
	{#await mod}
		<div class="dlViewerLoad"><span class="dlViewerSpin"></span>공시뷰어 여는 중…</div>
	{:then m}
		{@const Studio = m.default}
		<Studio code={view.code} vs={view.vs} embedded {onNavigate} {onclose} />
	{:catch}
		<div class="dlViewerLoad">뷰어 모듈 로드 실패 — 네트워크 확인 후 다시 열어주세요.</div>
	{/await}
</div>
