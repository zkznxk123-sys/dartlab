<script lang="ts">
	// 백테스트 전략 콘솔 — 전략(드롭다운 셀렉터+설명)·파라미터·비용(bp 편집). 일반 메뉴·전체화면 리본 공유.
	// 칩 6개 평면나열 폐기 → 셀렉터로 "지표 토글"이 아닌 "전략 실행" 위계 부여(03 §0.5.9-E "버튼 약함" 직격).
	// 선택 즉시 자동 실행(PriceChart $effect) — 초보 1클릭 보존 + 즉시 피드백(수동 실행 버튼보다 우수).
	// 벤치마크(B&H 동일비용)는 끌 수 없는 읽기전용 라벨 = 공정 비교가 제품 약속임을 컨트롤에서 전달.
	// 체결 모델 캡션 상시 노출 = 신뢰 표면. 결과 표시는 BacktestStrip/리포트 도크(설정/결과 분리).
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
	function pickPreset(key: string) {
		if (!key) { ctl.btKey = null; return; }
		const pd = BT_PRESETS.find((d) => d.key === key);
		if (pd) ctl.setPreset(pd);
	}
	const costsDefault = $derived(
		ctl.btCostsBp.commissionBp === BT_COSTS.commissionBp && ctl.btCostsBp.sellTaxBp === BT_COSTS.sellTaxBp && ctl.btCostsBp.slippageBp === BT_COSTS.slippageBp
	);
</script>

<div class="btConfig">
	<!-- ① 전략 — 셀렉터 + 설명 (칩 그리드 폐기) -->
	<div class="btSection">
		<div class="ctMenuLbl">{T('① 전략', '① Strategy')}</div>
		<select class="btSelect mono" value={ctl.btKey ?? ''} onchange={(e) => pickPreset(e.currentTarget.value)} title={T('전략 프리셋 — 선택 즉시 실행', 'strategy preset — runs on select')}>
			<option value="">{T('전략 선택…', 'pick strategy…')}</option>
			{#each BT_PRESETS as pd (pd.key)}
				<option value={pd.key}>{T(pd.kr, pd.en)}</option>
			{/each}
		</select>
		{#if ctl.activeBt}<div class="btDesc">{T(ctl.activeBt.descKr, ctl.activeBt.descEn)} · {T('교육·탐색용 (추천 아님)', 'educational (not advice)')}</div>{/if}
	</div>

	<!-- ② 파라미터 -->
	{#if ctl.activeBt && ctl.activeBt.params.length}
		<div class="btSection">
			<div class="ctMenuLbl">{T('② 파라미터', '② Parameters')}</div>
			{#each ctl.activeBt.params as pp (pp.name)}
				<div class="ctRow btParamRow">
					<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
					<button class="mItem" onclick={() => ctl.stepBtParam(pp, -1)}>−</button>
					<b class="btParamVal mono">{ctl.btParams[pp.name] ?? pp.def}</b>
					<button class="mItem" onclick={() => ctl.stepBtParam(pp, 1)}>+</button>
				</div>
			{/each}
		</div>
	{/if}

	<!-- ③ 비용 -->
	<div class="btSection">
		<div class="ctMenuLbl">{T('③ 비용', '③ Costs')}</div>
		<div class="ctRow">
			<button class={ctl.btCosts ? 'mItem on' : 'mItem'} onclick={() => (ctl.btCosts = !ctl.btCosts)}>{T('수수료·세금 포함', 'include costs')}</button>
			{#if ctl.btKey}<button class="mItem mClear" onclick={() => (ctl.btKey = null)}>{T('전략 해제', 'clear')}</button>{/if}
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

	<!-- ④ 검증(OOS) — 학습/검증 분할. 고정 파라미터를 안 본 구간에 적용 (walk-forward 아님, §0.5.9-A) -->
	{#if ctl.btKey}
		<div class="btSection">
			<div class="ctMenuLbl">{T('④ 검증 (학습/검증 분할)', '④ Validation (train/test)')}</div>
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
