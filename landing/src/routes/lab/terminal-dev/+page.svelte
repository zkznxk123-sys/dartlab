<script lang="ts">
	// 터미널 격리 개발 라우트 — DevTerminal(WIP 조립 셸) 마운트. 본진 /terminal 은 본 라우트·
	// $lib/terminal/dev/ 와 import 가 단절돼 있어 (checkDevIsolation 빌드 가드) 여기서 무엇을
	// 부수든 공개 터미널은 무중단이다.
	import type { PageData } from './$types';
	import { createEngine } from '$lib/terminal/data/engine';
	import type { RawData } from '$lib/terminal/data/types';
	import DevTerminal from '$lib/terminal/dev/DevTerminal.svelte';
	import { getPublicRuntime } from '$lib/runtime/publicRuntime';
	import { loadDartDb } from '$lib/data/duckdb';

	// DuckDB-WASM 프리워밍 — 본진과 동일 (주가 차트 체감속도).
	void loadDartDb();

	// 본진과 동일한 공개 셸 runtime 주입 (dev 셸도 포트만 본다)
	const runtime = getPublicRuntime();
	// 뷰어 컴포넌트 lazy 로더 주입 — 본진 route 와 동일 (4a-3 역의존 제거)
	const hosts = {
		viewerStudio: () => import('$lib/components/viewer/ViewerStudio.svelte'),
		financeDialog: () => import('$lib/components/viewer/FinanceDialog.svelte')
	};

	let { data }: { data: PageData } = $props();
	const eng = $derived(createEngine(data.raw as RawData));
	const ready = $derived(!!data.raw.finance.years.length && Object.keys(data.raw.prices.data).length > 0);
</script>

<svelte:head>
	<title>Terminal DEV 작업대 | dartlab</title>
	<meta name="robots" content="noindex" />
</svelte:head>

{#if ready}
	<DevTerminal {eng} {runtime} {hosts} initial="005930" />
{:else}
	<main class="devEmpty">
		<p>터미널 씨데이터를 불러오지 못했습니다. 본진은 <a href="../terminal">/terminal</a>.</p>
	</main>
{/if}

<style>
	.devEmpty {
		min-height: 40vh;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #8b919e;
		font-size: 13px;
	}
</style>
