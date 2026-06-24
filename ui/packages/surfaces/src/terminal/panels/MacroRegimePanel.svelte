<script lang="ts">
	// 거시 국면 — 좌측 최상단 글랜스 카드 (econoVision 개념: 판정 + 근거 + 확신도).
	// 데이터 = buildMacroGlanceView(macro).regime (RegimeQuadrantView) — macro.json 라이브, 이미 산출됨.
	// 옛 RegimeQuadrant(2점 격자)가 버렸던 quadrant·confidence·assets·description 을 살린다. 깊이는 다이얼로그.
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

	// 국면 → tone (색축). 확장·회복=긍정 / 둔화·보합=주의 / 수축·침체·위기=부정.
	function phaseTone(phase: string): string {
		const p = (phase || '').toLowerCase();
		if (/(expansion|recovery|확장|회복)/.test(p)) return 'tUp';
		if (/(contraction|crisis|수축|침체|위기)/.test(p)) return 'tDn';
		if (/(slowdown|둔화|보합)/.test(p)) return 'tWarn';
		return 'tNeu';
	}
	const assetTone = (t: string): string => (t === 'ow' ? 'tUp' : t === 'uw' ? 'tDn' : 'tNeu');
</script>

{#if primary}
	<div class="mrPanel">
		<div class="mrVerdict">
			<span class={'mrPhase ' + phaseTone(primary.phase)}>{primary.phaseLabel || primary.phase}</span>
			{#if primary.confidence}<span class="mrConf">{T('확신', 'conf')} {primary.confidence}</span>{/if}
		</div>
		<div class="mrDir">
			{#if primary.quadrantLabel}<span class="mrQuad">{primary.quadrantLabel}</span>{/if}
			{#if primary.growth}<span class="mrDirItem">{T('성장', 'growth')} {primary.growth}</span>{/if}
			{#if primary.inflation}<span class="mrDirItem">{T('물가', 'infl')} {primary.inflation}</span>{/if}
		</div>
		{#if primary.description}<div class="mrDesc">{primary.description}</div>{/if}
		{#if primary.assets.length}
			<div class="mrAssets">
				{#each primary.assets.slice(0, 4) as a (a.key)}
					<span class={'mrAsset ' + assetTone(a.tone)}>{lang === 'en' ? a.labelEn : a.labelKr}<b>{a.weight}</b></span>
				{/each}
			</div>
		{/if}
		{#if secondary}
			<div class="mrSecondary">
				<span class="mrSecLbl">{T('미국', 'US')}</span>
				<span class={phaseTone(secondary.phase)}>{secondary.phaseLabel || secondary.phase}</span>
				{#if secondary.confidence}<span class="mrSecConf">· {secondary.confidence}</span>{/if}
			</div>
		{/if}
		{#if regime.freshness?.label}<div class="mrFresh">{regime.freshness.label}</div>{/if}
	</div>
{:else}
	<div class="mrEmpty">{T('국면 데이터 미산출', 'no regime data')}</div>
{/if}
