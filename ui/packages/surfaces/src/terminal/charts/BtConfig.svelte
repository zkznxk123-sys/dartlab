<script lang="ts">
	// 백테스트 전략 콘솔 — 다전략(N≤3) 슬롯 리스트. 슬롯=색칩+프리셋 select+제거, 포커스 슬롯만 파라미터 펼침.
	// 비용(bp)·검증(OOS)은 전 슬롯 공유. 선택 즉시 자동 실행(PriceChart $effect). 벤치마크(B&H 동일비용) 읽기전용.
	// 정직(04 §2.2·2.4): N≥2 = selection 경고 + 단일종목 분산 라벨. 체결 모델 캡션 상시.
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
	const presetOf = (key: string) => BT_PRESETS.find((d) => d.key === key) ?? null;
	function addSlot(key: string) {
		const pd = presetOf(key);
		if (pd) ctl.addStrategy(pd);
	}
	function pickSlot(i: number, key: string) {
		const pd = presetOf(key);
		if (pd) ctl.setSlotPreset(i, pd);
	}
	const costsDefault = $derived(
		ctl.btCostsBp.commissionBp === BT_COSTS.commissionBp && ctl.btCostsBp.sellTaxBp === BT_COSTS.sellTaxBp && ctl.btCostsBp.slippageBp === BT_COSTS.slippageBp
	);
</script>

<div class="btConfig">
	<!-- ① 전략 (N≤3) — 슬롯 리스트. 같은 차트에 색별 동시 비교. -->
	<div class="btSection">
		<div class="ctMenuLbl">{T('① 전략 (최대 3 · 같은 차트 비교)', '① Strategies (up to 3)')}</div>
		{#each ctl.btStrategies as s, i (s.id)}
			{@const pd = presetOf(s.preset)}
			<div class="btSlot" class:on={i === ctl.btFocus}>
				<div class="btSlotHd">
					<button class="btSwBtn" onclick={() => ctl.setBtFocus(i)} title={T('이 전략에 포커스 (마커·상세)', 'focus')} aria-label="focus"><i class="btSw" style={`background:${s.color}`}></i></button>
					<select class="btSelect mono" value={s.preset} onchange={(e) => pickSlot(i, e.currentTarget.value)} title={T('전략 프리셋', 'preset')}>
						{#each BT_PRESETS as p (p.key)}<option value={p.key}>{T(p.kr, p.en)}</option>{/each}
					</select>
					<button class="btDel" onclick={() => ctl.removeStrategy(i)} title={T('전략 삭제', 'remove')} aria-label="remove">✕</button>
				</div>
				{#if i === ctl.btFocus && pd}
					{#if pd.descKr}<div class="btDesc">{T(pd.descKr, pd.descEn)} · {T('교육·탐색용 (추천 아님)', 'educational (not advice)')}</div>{/if}
					{#each pd.params as pp (pp.name)}
						<div class="ctRow btParamRow">
							<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
							<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, -1)}>−</button>
							<b class="btParamVal mono">{s.params[pp.name] ?? pp.def}</b>
							<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, 1)}>+</button>
						</div>
					{/each}
				{/if}
			</div>
		{/each}
		{#if ctl.btStrategies.length < 3}
			<select class="btSelect btAdd mono" value="" onchange={(e) => { addSlot(e.currentTarget.value); e.currentTarget.value = ''; }} title={T('전략 추가', 'add strategy')}>
				<option value="">{ctl.btStrategies.length ? T('＋ 전략 추가…', '+ add…') : T('전략 선택…', 'pick strategy…')}</option>
				{#each BT_PRESETS as p (p.key)}<option value={p.key}>{T(p.kr, p.en)}</option>{/each}
			</select>
		{/if}
		{#if ctl.btStrategies.length >= 2}
			<div class="btDesc warn">{T('⚠ 여러 전략 같은 데이터 비교 = 사후선택 편향 · 단일종목 조합 = 타이밍 분산이지 자산 분산 아님', 'selection bias · single-stock combo = timing not asset diversification')}</div>
		{/if}
	</div>

	<!-- ③ 비용 (전 슬롯 공유) -->
	<div class="btSection">
		<div class="ctMenuLbl">{T('③ 비용 (공유)', '③ Costs (shared)')}</div>
		<div class="ctRow">
			<button class={ctl.btCosts ? 'mItem on' : 'mItem'} onclick={() => (ctl.btCosts = !ctl.btCosts)}>{T('수수료·세금 포함', 'include costs')}</button>
			{#if ctl.btStrategies.length}<button class="mItem mClear" onclick={() => ctl.clearBtAll()}>{T('전체 해제', 'clear all')}</button>{/if}
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
	</div>

	<!-- ④ 검증(OOS) — 학습/검증 분할 (공유). walk-forward 아님(§0.5.9-A) -->
	{#if ctl.btStrategies.length}
		<div class="btSection">
			<div class="ctMenuLbl">{T('④ 검증 (학습/검증 분할 · 공유)', '④ Validation (train/test)')}</div>
			<div class="ctRow ctRowWrap">
				{#each [{ v: 0, kr: '없음', en: 'off' }, { v: 0.7, kr: '70:30', en: '70:30' }, { v: 0.6, kr: '60:40', en: '60:40' }] as o (o.v)}
					<button class={ctl.btOosSplit === o.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.btOosSplit = o.v)}>{T(o.kr, o.en)}</button>
				{/each}
			</div>
			{#if ctl.btOosSplit > 0}<div class="btDesc">{T('파란 구간 = 검증(out-of-sample). 검증 성과가 학습보다 나쁘면 과최적화 신호', 'blue = out-of-sample; worse than train = overfit signal')}</div>{/if}
		</div>
	{/if}

	<!-- 벤치마크 — 읽기전용(끌 수 없음 = 공정 비교 약속 노출) -->
	<div class="btBench">{T('비교 기준 · 보유(B&H) · 동일 비용 적용', 'benchmark · buy & hold · same costs')}</div>
	<div class="btModelNote">{T('신호 t일 종가 → t+1일 시가 체결 · 미래참조 차단 · 과거 가정 노출형 시뮬레이션(추천 아님)', 'signal close(t) → fill open(t+1) · no look-ahead · assumption-exposed simulation (not advice)')}</div>
</div>

<style>
	.btSlot { border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; padding: 5px 6px; margin-bottom: 4px; }
	.btSlot.on { border-color: #2a3142; background: rgba(255, 255, 255, 0.02); }
	.btSlotHd { display: flex; align-items: center; gap: 5px; }
	.btSwBtn { background: none; border: none; padding: 2px; cursor: pointer; display: inline-flex; }
	.btSw { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
	.btSelect { flex: 1 1 auto; min-width: 0; }
	.btAdd { width: 100%; margin-top: 2px; }
	.btDel { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 12px; padding: 0 3px; }
	.btDel:hover { color: var(--dn, #f0616f); }
	.btDesc.warn { color: var(--amber, #fb923c); }
</style>
