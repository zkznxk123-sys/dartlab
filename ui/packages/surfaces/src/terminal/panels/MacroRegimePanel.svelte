<script lang="ts">
	// 거시 국면 — 좌측 최상단 글랜스 (판정 + 근거 + 확신도). 한 줄씩 간결.
	// 데이터 = buildMacroGlanceView(macro).regime (macro.json 라이브). 깊이는 다이얼로그.
	import type { Lang } from '../lib/types';
	import type { RegimeQuadrantView } from '../lib/macroLens';

	interface Props {
		regime: RegimeQuadrantView;
		lang: Lang;
	}
	let { regime, lang }: Props = $props();
	const T = (kr: string, en: string): string => (lang === 'en' ? en : kr);

	const primary = $derived(regime.markets.find((m) => m.market === 'KR') ?? regime.markets[0] ?? null);
	const secondary = $derived(regime.markets.find((m) => m.market === 'US') ?? null);
	const ow = $derived(primary ? primary.assets.filter((a) => a.tone === 'ow') : []);
	const uw = $derived(primary ? primary.assets.filter((a) => a.tone === 'uw') : []);

	function phaseTone(phase: string): string {
		const p = (phase || '').toLowerCase();
		if (/(expansion|recovery|확장|회복)/.test(p)) return 'tUp';
		if (/(contraction|crisis|수축|침체|위기)/.test(p)) return 'tDn';
		if (/(slowdown|둔화|보합)/.test(p)) return 'tWarn';
		return 'tNeu';
	}
	const arrow = (s: string): string => (/(ris|up|상승|확장|↑)/i.test(s) ? '↑' : /(fall|down|하락|둔화|↓)/i.test(s) ? '↓' : '→');
	const names = (arr: { labelKr: string; labelEn: string }[]): string => arr.map((a) => (lang === 'en' ? a.labelEn : a.labelKr)).join('·');
</script>

{#if primary}
	<div class="mrPanel">
		<div class="mrLine">
			<span class={'mrPhase ' + phaseTone(primary.phase)}>{primary.phaseLabel || primary.phase}</span>
			{#if primary.confidence}<span class="mrConf">{primary.confidence}</span>{/if}
		</div>
		<div class="mrLine mrDim">
			{#if primary.quadrantLabel}<span class="mrQuad">{primary.quadrantLabel}</span>{/if}
			{#if primary.growth}<span>{T('성장', 'growth')} {arrow(primary.growth)}</span>{/if}
			{#if primary.inflation}<span>{T('물가', 'infl')} {arrow(primary.inflation)}</span>{/if}
		</div>
		{#if ow.length}<div class="mrLine"><span class="mrW tUp">{T('확대', 'OW')}</span><span class="mrWv">{names(ow)}</span></div>{/if}
		{#if uw.length}<div class="mrLine"><span class="mrW tDn">{T('축소', 'UW')}</span><span class="mrWv">{names(uw)}</span></div>{/if}
		{#if secondary}
			<div class="mrLine mrDim">
				<span class="mrSecLbl">{T('미국', 'US')}</span>
				<span class={phaseTone(secondary.phase)}>{secondary.phaseLabel || secondary.phase}</span>
				{#if secondary.confidence}<span class="mrDimmer">{secondary.confidence}</span>{/if}
			</div>
		{/if}
	</div>
{:else}
	<div class="mrEmpty">{T('국면 데이터 미산출', 'no regime data')}</div>
{/if}
