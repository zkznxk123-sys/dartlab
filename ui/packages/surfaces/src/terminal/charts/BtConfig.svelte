<script lang="ts">
	// 백테스트 설정 — 전략 프리셋·파라미터·비용(bp 편집). 일반 메뉴·전체화면 리본 양쪽이 공유.
	// 체결 모델 캡션 상시 노출 = 신뢰 표면. 결과 표시는 BacktestStrip (설정/결과 분리).
	import type { Lang } from '../lib/types';
	import type { ChartCtl } from './chartState.svelte';
	import { BT_PRESETS, BT_COSTS } from '../lib/backtest';

	interface Props {
		ctl: ChartCtl;
		lang: Lang;
	}
	let { ctl, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const COST_FIELDS = [
		{ k: 'commissionBp' as const, kr: '수수료', en: 'fee', min: 0, max: 10, step: 0.5 },
		{ k: 'sellTaxBp' as const, kr: '거래세', en: 'tax', min: 0, max: 30, step: 1 },
		{ k: 'slippageBp' as const, kr: '슬리피지', en: 'slip', min: 0, max: 50, step: 5 }
	];
	function stepCost(k: (typeof COST_FIELDS)[number], dir: 1 | -1) {
		const next = Math.max(k.min, Math.min(k.max, +(ctl.btCostsBp[k.k] + dir * k.step).toFixed(1)));
		ctl.btCostsBp = { ...ctl.btCostsBp, [k.k]: next };
	}
	const costsDefault = $derived(
		ctl.btCostsBp.commissionBp === BT_COSTS.commissionBp && ctl.btCostsBp.sellTaxBp === BT_COSTS.sellTaxBp && ctl.btCostsBp.slippageBp === BT_COSTS.slippageBp
	);
</script>

<div class="btConfig">
	<div class="ctMenuLbl">{T('전략 프리셋 — 클릭 즉시 실행', 'Strategy preset — runs on click')}</div>
	<div class="ctRow ctRowWrap">
		{#each BT_PRESETS as pd (pd.key)}
			<button class={ctl.btKey === pd.key ? 'mItem on' : 'mItem'} title={T(pd.descKr, pd.descEn)} onclick={() => ctl.setPreset(pd)}>{T(pd.kr, pd.en)}</button>
		{/each}
	</div>
	{#if ctl.activeBt && ctl.activeBt.params.length}
		<div class="ctMenuLbl">{T('파라미터', 'Params')}</div>
		{#each ctl.activeBt.params as pp (pp.name)}
			<div class="ctRow btParamRow">
				<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
				<button class="mItem" onclick={() => ctl.stepBtParam(pp, -1)}>−</button>
				<b class="btParamVal mono">{ctl.btParams[pp.name] ?? pp.def}</b>
				<button class="mItem" onclick={() => ctl.stepBtParam(pp, 1)}>+</button>
			</div>
		{/each}
	{/if}
	<div class="ctRow">
		<button class={ctl.btCosts ? 'mItem on' : 'mItem'} onclick={() => (ctl.btCosts = !ctl.btCosts)}>{T('수수료·세금 포함', 'Costs')}</button>
		{#if ctl.btKey}<button class="mItem mClear" onclick={() => (ctl.btKey = null)}>{T('전략 해제', 'Clear')}</button>{/if}
	</div>
	{#if ctl.btCosts}
		{#each COST_FIELDS as cf (cf.k)}
			<div class="ctRow btParamRow">
				<span class="btParamLbl">{T(cf.kr, cf.en)}</span>
				<button class="mItem" onclick={() => stepCost(cf, -1)}>−</button>
				<b class="btParamVal mono">{ctl.btCostsBp[cf.k]}</b>
				<span class="btParamLbl">bp</span>
				<button class="mItem" onclick={() => stepCost(cf, 1)}>+</button>
			</div>
		{/each}
		{#if !costsDefault}
			<div class="ctRow"><button class="mItem" onclick={() => (ctl.btCostsBp = { ...BT_COSTS })}>{T('비용 기본값', 'reset costs')}</button></div>
		{/if}
	{/if}
	<div class="btModelNote">{T('신호 t일 종가 → t+1일 시가 체결 · 미래참조 차단 · B&H 동일비용 비교', 'signal close(t) → fill open(t+1) · no look-ahead · B&H same costs')}</div>
</div>
