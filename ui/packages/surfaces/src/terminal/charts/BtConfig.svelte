<script lang="ts">
	// 백테스트 전략 콘솔 — 다전략(N≤3) + ★전문가급 조건 빌더(규칙 직접 조립).
	// 슬롯이 rule 이면 인라인 조건 에디터(지표+연산자+우변 상수/지표, AND/OR, +조건/삭제) — "프리셋 고르기" 졸업.
	// 추가 메뉴: 직접 조립 / rule 프리셋(OHLCV·편집가능) / 레거시 퀵(종가 6). 비용·OOS 공유.
	// 정직(04): N≥2 selection·단일종목 분산 라벨. 체결 모델 캡션 상시.
	import type { Lang } from '../lib/types';
	import type { ChartCtl } from './chartState.svelte';
	import { BT_PRESETS, BT_COSTS, RULE_PRESETS, SERIES_CATALOG, OP_LABEL } from '../lib/backtest';
	import type { Condition, Op, SeriesKey, StrategyRule } from '../lib/backtest';

	interface Props { ctl: ChartCtl; lang: Lang; }
	let { ctl, lang }: Props = $props();
	const T = (kr: string, en: string) => (lang === 'en' ? en : kr);
	const OPS: Op[] = ['>', '<', '>=', '<=', 'crossUp', 'crossDown'];
	const seriesDef = (key: SeriesKey) => SERIES_CATALOG.find((s) => s.key === key);
	const seriesLbl = (key: SeriesKey) => { const d = seriesDef(key); return d ? T(d.kr, d.en) : key; };

	const COST_FIELDS = [
		{ k: 'commissionBp' as const, kr: '수수료', en: 'fee', min: 0, max: 10, step: 0.5 },
		{ k: 'sellTaxBp' as const, kr: '거래세', en: 'tax', min: 0, max: 30, step: 1 },
		{ k: 'slippageBp' as const, kr: '슬리피지', en: 'slip', min: 0, max: 50, step: 5 }
	];
	function stepCost(k: (typeof COST_FIELDS)[number], dir: 1 | -1) {
		const next = Math.max(k.min, Math.min(k.max, +(ctl.btCostsBp[k.k] + dir * k.step).toFixed(1)));
		ctl.btCostsBp = { ...ctl.btCostsBp, [k.k]: next };
	}
	const costsDefault = $derived(ctl.btCostsBp.commissionBp === BT_COSTS.commissionBp && ctl.btCostsBp.sellTaxBp === BT_COSTS.sellTaxBp && ctl.btCostsBp.slippageBp === BT_COSTS.slippageBp);

	// 추가 메뉴 디스패치 — custom / rule:키 / preset:키
	function addPick(v: string) {
		if (v === 'custom') ctl.addCustomRule();
		else if (v.startsWith('rule:')) { const rp = RULE_PRESETS.find((r) => r.key === v.slice(5)); if (rp) ctl.addRulePreset(rp); }
		else if (v.startsWith('preset:')) { const pd = BT_PRESETS.find((d) => d.key === v.slice(7)); if (pd) ctl.addStrategy(pd); }
	}

	// ── 룰 불변 편집 — 슬롯의 rule 을 clone·변형 후 setSlotRule ──
	function editRule(i: number, fn: (r: StrategyRule) => void) {
		const slot = ctl.btStrategies[i];
		if (!slot?.rule) return;
		const r = structuredClone(slot.rule);
		fn(r);
		ctl.setSlotRule(i, r);
	}
	const sideArr = (r: StrategyRule, side: 'entry' | 'exit') => (side === 'entry' ? r.entry : r.exit);
	function setLeft(i: number, side: 'entry' | 'exit', ci: number, key: SeriesKey) {
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.left = key; c.leftParams = Object.fromEntries((seriesDef(key)?.params ?? []).map((p) => [p.name, p.def])); });
	}
	function stepLeftParam(i: number, side: 'entry' | 'exit', ci: number, name: string, dir: 1 | -1) {
		const pp = seriesDef(sideArr(ctl.btStrategies[i].rule!, side)[ci].left)?.params.find((p) => p.name === name);
		if (!pp) return;
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; const v = c.leftParams[name] ?? pp.def; c.leftParams[name] = Math.max(pp.min, Math.min(pp.max, +(v + dir * pp.step).toFixed(2))); });
	}
	function setOp(i: number, side: 'entry' | 'exit', ci: number, op: Op) { editRule(i, (r) => { sideArr(r, side)[ci].op = op; }); }
	function setRightKind(i: number, side: 'entry' | 'exit', ci: number, kind: 'const' | 'series') {
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.right = kind === 'const' ? { kind: 'const', value: 0 } : { kind: 'series', key: 'ma', params: { period: 60 } }; });
	}
	function setRightConst(i: number, side: 'entry' | 'exit', ci: number, value: number) { editRule(i, (r) => { const c = sideArr(r, side)[ci]; if (c.right.kind === 'const') c.right.value = value; }); }
	function setRightSeries(i: number, side: 'entry' | 'exit', ci: number, key: SeriesKey) { editRule(i, (r) => { const c = sideArr(r, side)[ci]; c.right = { kind: 'series', key, params: Object.fromEntries((seriesDef(key)?.params ?? []).map((p) => [p.name, p.def])) }; }); }
	function stepRightParam(i: number, side: 'entry' | 'exit', ci: number, name: string, dir: 1 | -1) {
		const c0 = sideArr(ctl.btStrategies[i].rule!, side)[ci];
		if (c0.right.kind !== 'series') return;
		const pp = seriesDef(c0.right.key)?.params.find((p) => p.name === name);
		if (!pp) return;
		editRule(i, (r) => { const c = sideArr(r, side)[ci]; if (c.right.kind === 'series') { const v = c.right.params[name] ?? pp.def; c.right.params[name] = Math.max(pp.min, Math.min(pp.max, +(v + dir * pp.step).toFixed(2))); } });
	}
	function addCond(i: number, side: 'entry' | 'exit') { editRule(i, (r) => { sideArr(r, side).push({ left: 'price', leftParams: {}, op: side === 'entry' ? '>' : '<', right: { kind: 'series', key: 'ma', params: { period: 60 } } }); }); }
	function removeCond(i: number, side: 'entry' | 'exit', ci: number) { editRule(i, (r) => { sideArr(r, side).splice(ci, 1); }); }
	function setCombine(i: number, side: 'entry' | 'exit', mode: 'AND' | 'OR') { editRule(i, (r) => { if (side === 'entry') r.entryCombine = mode; else r.exitCombine = mode; }); }
</script>

<div class="btConfig">
	<div class="btSection">
		<div class="ctMenuLbl">{T('① 전략 (최대 3 · 같은 차트 비교)', '① Strategies (up to 3)')}</div>
		{#each ctl.btStrategies as s, i (s.id)}
			<div class="btSlot" class:on={i === ctl.btFocus}>
				<div class="btSlotHd">
					<button class="btSwBtn" onclick={() => ctl.setBtFocus(i)} title={T('포커스', 'focus')} aria-label="focus"><i class="btSw" style={`background:${s.color}`}></i></button>
					<span class="btSlotLbl">{s.label}{#if s.rule}<em class="btRuleTag">{T('규칙', 'rule')}</em>{/if}</span>
					<button class="btDel" onclick={() => ctl.removeStrategy(i)} title={T('삭제', 'remove')} aria-label="remove">✕</button>
				</div>

				{#if i === ctl.btFocus}
					{#if s.rule}
						<!-- ★조건 빌더 — 진입/청산 규칙 직접 조립 -->
						{@const rule = s.rule}
						{#each ['entry', 'exit'] as const as side (side)}
							{@const conds = side === 'entry' ? rule.entry : rule.exit}
							<div class="condBlk">
								<div class="condHd">
									<span>{side === 'entry' ? T('진입 조건', 'ENTRY') : T('청산 조건', 'EXIT')}</span>
									{#if conds.length > 1}
										<div class="combineTg">
											{#each ['AND', 'OR'] as const as m (m)}
												<button class={(side === 'entry' ? rule.entryCombine : rule.exitCombine) === m ? 'on' : ''} onclick={() => setCombine(i, side, m)}>{m}</button>
											{/each}
										</div>
									{/if}
								</div>
								{#each conds as c, ci (ci)}
									<div class="condRow">
										<select class="condSel" value={c.left} onchange={(e) => setLeft(i, side, ci, e.currentTarget.value as SeriesKey)}>
											<optgroup label={T('가격·기술', 'price/technical')}>
												{#each SERIES_CATALOG as sd (sd.key)}<option value={sd.key}>{T(sd.kr, sd.en)}</option>{/each}
											</optgroup>
											<optgroup label={T('펀더게이트 (재무·panel)', 'fundamental gate')}>
												<option value="fundGate">{T('Piotroski F (재무건강 0~9)', 'Piotroski F (0~9)')}</option>
											</optgroup>
										</select>
										{#each seriesDef(c.left)?.params ?? [] as pp (pp.name)}
											<span class="condP"><button onclick={() => stepLeftParam(i, side, ci, pp.name, -1)}>−</button><b>{c.leftParams[pp.name] ?? pp.def}</b><button onclick={() => stepLeftParam(i, side, ci, pp.name, 1)}>+</button></span>
										{/each}
										<select class="condOp" value={c.op} onchange={(e) => setOp(i, side, ci, e.currentTarget.value as Op)}>
											{#each OPS as op (op)}<option value={op}>{OP_LABEL[op]}</option>{/each}
										</select>
										<select class="condKind" value={c.right.kind} onchange={(e) => setRightKind(i, side, ci, e.currentTarget.value as 'const' | 'series')}>
											<option value="const">{T('값', 'const')}</option>
											<option value="series">{T('지표', 'series')}</option>
										</select>
										{#if c.right.kind === 'const'}
											<input class="condNum mono" type="number" value={c.right.value} onchange={(e) => setRightConst(i, side, ci, +e.currentTarget.value)} />
										{:else}
											<select class="condSel" value={c.right.key} onchange={(e) => setRightSeries(i, side, ci, e.currentTarget.value as SeriesKey)}>
												{#each SERIES_CATALOG as sd (sd.key)}<option value={sd.key}>{T(sd.kr, sd.en)}</option>{/each}
											</select>
											{#each seriesDef(c.right.key)?.params ?? [] as pp (pp.name)}
												<span class="condP"><button onclick={() => stepRightParam(i, side, ci, pp.name, -1)}>−</button><b>{c.right.kind === 'series' ? c.right.params[pp.name] ?? pp.def : pp.def}</b><button onclick={() => stepRightParam(i, side, ci, pp.name, 1)}>+</button></span>
											{/each}
										{/if}
										{#if conds.length > 1}<button class="condDel" onclick={() => removeCond(i, side, ci)} aria-label="remove condition">✕</button>{/if}
									</div>
								{/each}
								<button class="condAdd" onclick={() => addCond(i, side)}>＋ {T('조건', 'condition')}</button>
							</div>
						{/each}
						<div class="btDesc">{T('지표·연산자·임계값을 직접 조합 · 교육·탐색용(추천 아님)', 'compose your own rule · educational (not advice)')}</div>
					{:else}
						<!-- 레거시 퀵 프리셋(종가 6) — 셀렉터 + 파라미터 -->
						{@const pd = BT_PRESETS.find((d) => d.key === s.preset)}
						<div class="btSlotHd">
							<select class="btSelect mono" value={s.preset} onchange={(e) => { const p = BT_PRESETS.find((d) => d.key === e.currentTarget.value); if (p) ctl.setSlotPreset(i, p); }}>
								{#each BT_PRESETS as p (p.key)}<option value={p.key}>{T(p.kr, p.en)}</option>{/each}
							</select>
						</div>
						{#if pd}{#each pd.params as pp (pp.name)}
							<div class="ctRow btParamRow">
								<span class="btParamLbl">{T(pp.kr, pp.en)}</span>
								<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, -1)}>−</button>
								<b class="btParamVal mono">{s.params[pp.name] ?? pp.def}</b>
								<button class="mItem" onclick={() => ctl.stepSlotParam(i, pp, 1)}>+</button>
							</div>
						{/each}{/if}
					{/if}
				{/if}
			</div>
		{/each}
		{#if ctl.btStrategies.length < 3}
			<select class="btSelect btAdd mono" value="" onchange={(e) => { addPick(e.currentTarget.value); e.currentTarget.value = ''; }} title={T('전략 추가', 'add')}>
				<option value="">{ctl.btStrategies.length ? T('＋ 전략 추가…', '+ add…') : T('전략 추가…', 'add strategy…')}</option>
				<optgroup label={T('직접 조립', 'custom')}><option value="custom">{T('＋ 커스텀 규칙 빌더', '+ custom rule builder')}</option></optgroup>
				<optgroup label={T('규칙 프리셋 (OHLCV·편집가능)', 'rule presets')}>
					{#each RULE_PRESETS as rp (rp.key)}<option value={`rule:${rp.key}`}>{T(rp.kr, rp.en)}</option>{/each}
				</optgroup>
				<optgroup label={T('퀵 프리셋 (종가)', 'quick presets')}>
					{#each BT_PRESETS as p (p.key)}<option value={`preset:${p.key}`}>{T(p.kr, p.en)}</option>{/each}
				</optgroup>
			</select>
		{/if}
		{#if ctl.btStrategies.length >= 2}
			<div class="btDesc warn">{T('⚠ 여러 전략 같은 데이터 비교 = 사후선택 편향 · 단일종목 조합 = 타이밍 분산이지 자산 분산 아님', 'selection bias · single-stock combo = timing not asset')}</div>
		{/if}
	</div>

	<!-- ③ 비용 (공유) -->
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
			{#if !costsDefault}<div class="ctRow"><button class="mItem" onclick={() => (ctl.btCostsBp = { ...BT_COSTS })}>{T('비용 기본값', 'reset')}</button></div>{/if}
		{/if}
	</div>

	<!-- ④ 검증(OOS) 공유 -->
	{#if ctl.btStrategies.length}
		<div class="btSection">
			<div class="ctMenuLbl">{T('④ 검증 (학습/검증 분할 · 공유)', '④ Validation')}</div>
			<div class="ctRow ctRowWrap">
				{#each [{ v: 0, kr: '없음', en: 'off' }, { v: 0.7, kr: '70:30', en: '70:30' }, { v: 0.6, kr: '60:40', en: '60:40' }] as o (o.v)}
					<button class={ctl.btOosSplit === o.v ? 'mItem on' : 'mItem'} onclick={() => (ctl.btOosSplit = o.v)}>{T(o.kr, o.en)}</button>
				{/each}
			</div>
			{#if ctl.btOosSplit > 0}<div class="btDesc">{T('파란 구간 = 검증. 검증<학습이면 과최적화 신호', 'blue = out-of-sample; worse = overfit')}</div>{/if}
		</div>
	{/if}

	<div class="btBench">{T('비교 기준 · 보유(B&H) · 동일 비용', 'benchmark · buy & hold · same costs')}</div>
	<div class="btModelNote">{T('신호 t일 종가 → t+1일 시가 체결 · 미래참조 차단 · 과거 가정 노출형 시뮬레이션(추천 아님)', 'signal close(t) → fill open(t+1) · no look-ahead · not advice')}</div>
</div>

<style>
	.btSlot { border: 1px solid var(--dl-line, #1b2130); border-radius: 5px; padding: 5px 6px; margin-bottom: 4px; }
	.btSlot.on { border-color: #2a3142; background: rgba(255, 255, 255, 0.02); }
	.btSlotHd { display: flex; align-items: center; gap: 5px; }
	.btSwBtn { background: none; border: none; padding: 2px; cursor: pointer; display: inline-flex; }
	.btSw { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
	.btSlotLbl { flex: 1 1 auto; min-width: 0; font-size: 11.5px; color: var(--dl-ink, #c8cfdb); display: flex; align-items: center; gap: 5px; }
	.btRuleTag { font-style: normal; font-size: 8.5px; color: #a3e635; border: 1px solid rgba(163, 230, 53, 0.4); border-radius: 3px; padding: 0 3px; }
	.btSelect { flex: 1 1 auto; min-width: 0; }
	.btAdd { width: 100%; margin-top: 2px; }
	.btDel { background: none; border: none; color: var(--dimmer); cursor: pointer; font-size: 12px; padding: 0 3px; }
	.btDel:hover { color: var(--dn, #f0616f); }
	.btDesc.warn { color: var(--amber, #fb923c); }
	/* 조건 빌더 */
	.condBlk { margin-top: 5px; padding: 5px; border: 1px solid rgba(27, 33, 48, 0.7); border-radius: 4px; }
	.condHd { display: flex; align-items: center; justify-content: space-between; font-size: 9.5px; font-weight: 700; color: #8b94a3; letter-spacing: 0.04em; margin-bottom: 4px; }
	.combineTg { display: flex; gap: 2px; }
	.combineTg button { font-size: 8.5px; padding: 1px 6px; background: none; border: 1px solid var(--dl-line, #1b2130); color: var(--dimmer); border-radius: 3px; cursor: pointer; font-family: inherit; }
	.combineTg button.on { color: #a3e635; border-color: rgba(163, 230, 53, 0.5); }
	.condRow { display: flex; align-items: center; gap: 3px; flex-wrap: wrap; margin-bottom: 3px; }
	.condSel, .condOp, .condKind { font-size: 10px; background: var(--dl-bg-raised, #0e141f); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 3px; font-family: inherit; }
	.condOp { min-width: 30px; }
	.condNum { width: 56px; font-size: 10px; background: var(--dl-bg-raised, #0e141f); color: var(--dl-ink, #c8cfdb); border: 1px solid var(--dl-line, #1b2130); border-radius: 3px; padding: 2px 4px; }
	.condP { display: inline-flex; align-items: center; gap: 1px; }
	.condP button { font-size: 10px; width: 16px; height: 16px; line-height: 1; background: none; border: 1px solid var(--dl-line, #1b2130); color: #aeb6c2; border-radius: 3px; cursor: pointer; padding: 0; }
	.condP b { font-size: 9.5px; min-width: 20px; text-align: center; font-family: var(--dl-font-mono, monospace); color: var(--dl-ink, #c8cfdb); }
	.condDel { background: none; border: none; color: var(--dimmer); cursor: pointer; font-size: 11px; padding: 0 2px; }
	.condDel:hover { color: var(--dn, #f0616f); }
	.condAdd { font-size: 9.5px; background: none; border: 1px dashed var(--dl-line-strong, #2a3142); color: #8b94a3; border-radius: 3px; padding: 2px 8px; cursor: pointer; font-family: inherit; margin-top: 2px; }
	.condAdd:hover { color: var(--dl-ink, #c8cfdb); }
</style>
