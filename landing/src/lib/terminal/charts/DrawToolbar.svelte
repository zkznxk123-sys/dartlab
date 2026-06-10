<script lang="ts">
	// 전체화면 좌측 세로 그리기 툴바 (TradingView 좌측 툴바 멘탈모델) — 상시 노출 위젯.
	// 상태는 ChartCtl 공유, 도형 생성은 onDraw 콜백 (chartState "명령은 콜백" 규약).
	import type { Lang } from '../data/types';
	import { type ChartCtl, DRAW_TOOLS } from './chartState.svelte';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
		onDraw: (name: string) => void;
		onClearDraw: () => void;
	}
	let { ctl, lang, onDraw, onClearDraw }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	// 마지막 선택 도구 — 시각 피드백 (다음 클릭 도형). 영속 아님.
	let lastTool = $state<string | null>(null);
</script>

<div class="drawBar" role="toolbar" aria-label={T('그리기 도구', 'draw tools')}>
	{#each DRAW_TOOLS as d (d.name)}
		<button class={lastTool === d.name ? 'dbBtn on' : 'dbBtn'} title={T(d.kr, d.en)} onclick={() => { lastTool = d.name; onDraw(d.name); }}>{d.icon}</button>
	{/each}
	<span class="dbDiv"></span>
	<button class={ctl.magnet ? 'dbBtn on' : 'dbBtn'} title={T('자석 스냅', 'magnet snap')} onclick={() => (ctl.magnet = !ctl.magnet)}>🧲</button>
	<button class={ctl.stayDraw ? 'dbBtn on' : 'dbBtn'} title={T('연속 그리기 — 완성 후 같은 도구 유지', 'stay in drawing mode')} onclick={() => (ctl.stayDraw = !ctl.stayDraw)}>🔏</button>
	<button class="dbBtn dbClear" disabled={!ctl.drawCount} title={T('그리기 전체 지우기', 'clear all drawings')} onclick={() => { lastTool = null; onClearDraw(); }}>🗑{#if ctl.drawCount}<i class="dbCount">{ctl.drawCount}</i>{/if}</button>
</div>
