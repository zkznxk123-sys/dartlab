<script lang="ts">
	import type { PageData } from './$types';
	import { createEngine, TerminalSurface, type RawData } from '@dartlab/ui-surfaces/terminal';
	import { getPublicRuntime } from '$lib/runtime/publicRuntime';
	import { terminalHosts, terminalLinks } from '$lib/terminal-shell/terminalShell';
	import { loadDartDb } from '$lib/data/duckdb';

	// DuckDB-WASM 프리워밍 — JSON 데이터 로드와 병렬로 미리 인스턴스화 (주가 차트 체감속도↑)
	void loadDartDb();

	// 공개 셸 runtime 주입 — surface 는 포트만 본다 (전역 locator·silent fallback 철거, 4a-2)
	const runtime = getPublicRuntime();

	let { data }: { data: PageData } = $props();
	const eng = $derived(createEngine(data.raw as RawData));
	const ready = $derived(!!data.raw.finance.years.length && Object.keys(data.raw.prices.data).length > 0);
</script>

<svelte:head>
	<title>Terminal — 시세·재무·공시 데이터 워크벤치 | dartlab</title>
	<meta
		name="description"
		content="상장사 주가 차트(보조지표·백테스팅·경제지표 오버레이), 재무제표 전 기간, 정기보고서 팩트, 공시 추적을 한 화면에 모은 DartLab Terminal."
	/>
</svelte:head>

{#if ready}
	<TerminalSurface {eng} {runtime} hosts={terminalHosts} links={terminalLinks} initial="005930" />
{:else}
	<div class="loading">HuggingFace · dartlab-data 연결 중 …</div>
{/if}

<style>
	.loading {
		height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--dl-bg-base);
		color: var(--dl-ink-mute);
		font-family: var(--dl-font-mono);
		font-size: 12px;
	}
</style>
